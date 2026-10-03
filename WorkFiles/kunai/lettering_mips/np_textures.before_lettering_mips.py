"""Texture import with the right flags, the black hat's ORM composite step, and the flag check (inside Unreal).

The flags for the kinds the line's own importers already know (BC, ORM, N, M, Lettering) are taken FROM those
importers, so there is one definition of each: ``Scripts/props/props_lib/ue_import_textures.py`` (BC / ORM / N / M)
and ``Scripts/shuriken/ue_import_textures.py`` (Lettering). Both run their ``main()`` when imported, so they are
loaded with their environment pointed at a harmless VERIFY run over an empty folder (it loads no asset and writes its
small report into WorkFiles/materials/build/logs/, never into Exports/). The kinds they do not know (Detail16,
PaperDetail_sRGB, InkWeights_linear) and the extra keys (compression_no_alpha, the composite texture) come from
material_spec.json ``texture_import``; the build asserts the spec agrees with the importers where both speak.

The black hat's ORM composite (per-mip Toksvig roughness from the part's normal map) is the same three properties
``WorkFiles/blackhat/UnrealCheck/bhu_tex_composite.py`` sets, driven by the spec's ``orm_texture_settings``.
"""
from __future__ import annotations

import importlib.util
import os
import traceback
from pathlib import Path

import unreal

import np_spec

EAL = unreal.EditorAssetLibrary
TC = unreal.TextureCompressionSettings
TMGS = unreal.TextureMipGenSettings
TA = unreal.TextureAddress

IMPORTERS = {
    "props": (np_spec.PROJECT / "Scripts/props/props_lib/ue_import_textures.py", "PROPS_TEXTURE"),
    "shuriken": (np_spec.PROJECT / "Scripts/shuriken/ue_import_textures.py", "SHURIKEN_TEXTURE"),
}


def _load_importer(key):
    path, prefix = IMPORTERS[key]
    empty = np_spec.WORK / "build" / "_importer_selftest_empty"
    empty.mkdir(parents=True, exist_ok=True)
    env = {f"{prefix}_MODE": "verify", f"{prefix}_DIR": str(empty), f"{prefix}_DEST": "/Game/NinjaPack/_importer_selftest",
           f"{prefix}_OUT": str(np_spec.WORK / "build" / "logs" / f"importer_selftest_{key}.json")}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        spec = importlib.util.spec_from_file_location(f"np_importer_{key}", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return mod


_IMPORTER_CACHE = {}


def importers():
    if not _IMPORTER_CACHE:
        for key in IMPORTERS:
            _IMPORTER_CACHE[key] = _load_importer(key)
    return _IMPORTER_CACHE


def _enum(enum_cls, name):
    return getattr(enum_cls, name)


def intents(spec: dict) -> dict:
    """kind -> {editor property: value}. Importer flags where the importer knows the kind, spec for the rest."""
    imp = importers()
    props, shur = imp["props"].INTENT, imp["shuriken"].INTENT
    borrowed = {"BC": props["BC"], "ORM_rgb": props["ORM"], "ORM_rgba": props["ORM"], "N": props["N"],
                "M_paperbomb": props["M"], "Lettering": shur["Lettering"]}
    out, agreement = {}, {}
    for kind, t in spec["texture_import"].items():
        if not isinstance(t, dict) or "compression" not in t or kind in ("Detail_sRGB8_shipped", "PaperWeights"):
            continue
        want = {"srgb": bool(t["srgb"]), "compression_settings": _enum(TC, t["compression"].split(" ")[0])}
        if t.get("mips", "").startswith("TMGS_FROM_TEXTURE_GROUP"):
            want["mip_gen_settings"] = TMGS.TMGS_FROM_TEXTURE_GROUP
        if "compression_no_alpha" in t:
            want["compression_no_alpha"] = bool(t["compression_no_alpha"])
        if "flip_green_channel" in t:
            want["flip_green_channel"] = bool(t["flip_green_channel"])
        if kind in borrowed:
            base = dict(borrowed[kind])
            agreement[kind] = {k: str(base[k]) == str(want[k]) for k in ("srgb", "compression_settings") if k in base}
            merged = dict(base)
            for k, v in want.items():
                merged.setdefault(k, v)
            out[kind] = merged
        else:
            out[kind] = want
    bad = {k: v for k, v in agreement.items() if not all(v.values())}
    if bad:
        raise ValueError(f"material_spec texture_import disagrees with the line's importers: {bad}")
    return out


def inspect(tex) -> dict:
    info = importers()["props"].inspect(tex)
    for name in ("composite_texture", "composite_texture_mode", "composite_power"):
        try:
            v = tex.get_editor_property(name)
            info[name] = v.get_path_name() if hasattr(v, "get_path_name") else str(v)
        except Exception as exc:  # noqa: BLE001
            info[name] = f"<{type(exc).__name__}>"
    return info


def _import_png(png: Path, folder: str, name: str):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png))
    task.set_editor_property("destination_path", folder)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    tex = next((t for t in (unreal.load_asset(p) for p in paths) if isinstance(t, unreal.Texture2D)), None)
    return paths, tex


def matches(info: dict, want: dict, extra: dict) -> dict:
    out = {}
    for k, v in want.items():
        out[k] = str(info.get(k)) == str(v)
    out["has_mips"] = "NO_MIPMAPS" not in str(info.get("mip_gen_settings", "")).upper()
    size = info.get("size")
    if isinstance(size, list) and len(size) == 2 and "power_of_two_mode" not in want:
        # an NPOT source is allowed only when the kind stretches it (the lettering mask, 1536 x 256)
        out["power_of_two"] = all(v > 0 and (v & (v - 1)) == 0 for v in size)
    comp = extra.get("composite")
    if comp:
        out["composite_texture"] = str(info.get("composite_texture", "")).split(".")[0] == comp["composite_texture"]
        out["composite_texture_mode"] = str(info.get("composite_texture_mode")) == str(
            _enum(unreal.CompositeTextureMode, comp["composite_texture_mode"]))
        try:
            out["composite_power"] = abs(float(info.get("composite_power")) - comp["composite_power"]) < 1e-6
        except (TypeError, ValueError):
            out["composite_power"] = False
    out["all"] = all(out.values())
    return out


def run_import(plan: dict) -> dict:
    spec = plan["spec"]
    want_by_kind = intents(spec)
    report = {"mode": "import_textures", "textures": {}, "intents": {k: {kk: str(vv) for kk, vv in v.items()}
                                                                     for k, v in want_by_kind.items()},
              "accounting": np_spec.export_pngs_accounted(plan)}
    # pass 1: import + flags (every texture), pass 2: composite textures (they reference the N maps)
    for asset, t in sorted(plan["textures"].items()):
        entry = {"png": t["png"], "kind": t["kind"], "sha256": np_spec.sha256(np_spec.PROJECT / t["png"]),
                 "used_by": t["used_by"]}
        try:
            folder, name = asset.rsplit("/", 1)
            paths, tex = _import_png(np_spec.PROJECT / t["png"], folder, name)
            entry["imported_object_paths"] = paths
            if tex is None:
                entry["error"] = "import produced no Texture2D"
            else:
                entry["as_imported"] = inspect(tex)
                for k, v in want_by_kind[t["kind"]].items():
                    tex.set_editor_property(k, v)
                entry["applied"] = {k: str(v) for k, v in want_by_kind[t["kind"]].items()}
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        report["textures"][asset] = entry
    for asset, t in sorted(plan["textures"].items()):
        comp = t["extra"].get("composite")
        entry = report["textures"][asset]
        if not comp or entry.get("error"):
            continue
        tex = unreal.load_asset(asset)
        nrm = unreal.load_asset(comp["composite_texture"])
        if nrm is None:
            entry["error"] = f"composite normal {comp['composite_texture']} missing"
            continue
        tex.set_editor_property("composite_texture", nrm)
        tex.set_editor_property("composite_texture_mode", _enum(unreal.CompositeTextureMode, comp["composite_texture_mode"]))
        tex.set_editor_property("composite_power", float(comp["composite_power"]))
        entry["composite_applied"] = comp
    for asset, t in sorted(plan["textures"].items()):
        entry = report["textures"][asset]
        if entry.get("error"):
            continue
        tex = unreal.load_asset(asset)
        entry["saved"] = bool(EAL.save_loaded_asset(tex, only_if_is_dirty=False))
        entry["in_process"] = inspect(tex)
        entry["in_process_matches"] = matches(entry["in_process"], want_by_kind[t["kind"]], t["extra"])
    report["count"] = len(plan["textures"])
    report["saved"] = sum(1 for e in report["textures"].values() if e.get("saved"))
    report["passed"] = (report["saved"] == report["count"] and report["accounting"]["passed"]
                        and all((e.get("in_process_matches") or {}).get("all") for e in report["textures"].values()))
    return report


def verify(plan: dict) -> dict:
    want_by_kind = intents(plan["spec"])
    out = {"textures": {}}
    for asset, t in sorted(plan["textures"].items()):
        tex = unreal.load_asset(asset)
        if tex is None:
            out["textures"][asset] = {"error": "missing"}
            continue
        info = inspect(tex)
        m = matches(info, want_by_kind[t["kind"]], t["extra"])
        imported_from = None
        try:
            aid = tex.get_editor_property("asset_import_data")
            imported_from = [str(f) for f in aid.extract_filenames()] if aid else None
        except Exception:  # noqa: BLE001
            pass
        out["textures"][asset] = {"kind": t["kind"], "png": t["png"], "flags": info, "matches": m,
                                  "source_files": imported_from}
    out["count"] = len(plan["textures"])
    out["passed"] = all((v.get("matches") or {}).get("all") for v in out["textures"].values())
    return out
