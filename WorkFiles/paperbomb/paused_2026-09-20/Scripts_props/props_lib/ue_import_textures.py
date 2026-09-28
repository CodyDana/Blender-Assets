"""Import the prop line's baked maps into Unreal with the right flags, and verify them.

A COPY of ``Scripts/shuriken/ue_import_textures.py``, as the brief requires: that file
and everything else under ``Scripts/shuriken/**`` is frozen, so a behaviour change is
made here instead of there.  What changed, and why each change exists:

    ADDED "M"        The paper bomb ships a fourth map, ``T_PaperBomb_M``.  The pack's
                     importer holds intents for BC / ORM / N / Lettering only, and
                     ``pngs()`` FILTERS OUT anything whose suffix is not in that table -
                     so running the pack's script over Exports/PaperBomb/Textures
                     processed three maps, never mentioned the fourth, and reported
                     ``"passed": true``.  Measured, not inferred, in UE 5.8.2.  And the
                     skipped map is the one that most needs the flags: imported naively
                     into a never-written content path it arrives sRGB = True,
                     TC_Default, so a linear fringe / burn-order / ink mask is decoded
                     through a gamma curve.

    UNKNOWN SUFFIX   is now a hard FAILURE instead of a silent filter.  A map this tool
    RAISES           does not recognise must stop the build, not vanish from a green
                     report.  ``pngs()`` returns everything and ``run_*`` marks the
                     unknown ones; ``passed`` is False while any exists.

    COUNT GATE       ``expected`` is the number of PNGs in the folder, and the report
                     carries ``processed == expected``.  The build asserts it.

The flags, all measured in UE 5.8.2 in a second fresh process:

    BC   sRGB ON,  TC_Default
    ORM  sRGB OFF, TC_Masks, mips from the texture group   (R AO, G roughness, B metallic)
    N    sRGB OFF, TC_Normalmap, flip_green_channel OFF    (the map on disk is DirectX)
    M    sRGB OFF, TC_Masks, mips from the texture group   (R fibre-fringe alpha,
         G burn ORDER 0 at the Fuse socket rising to 1 at the far end, B ink mask)

``mip_gen_settings`` is belt and braces on a 2048 square map, but the gate has to exist:
the pack measured a non-power-of-two PNG importing as TMGS_NoMipmaps, silently, and an
NPOT texture does not stream at all.

Runs inside the pythonscript commandlet, ONE MODE PER PROCESS - the verify has to prove
the flags persisted, so it must not share a process with the import::

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
        <project.uproject> -run=pythonscript -script=<this file> \
        -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput

Environment: PROPS_TEXTURE_MODE = import | verify   (default import)
             PROPS_TEXTURE_DIR  = folder of the PNGs (default Exports/PaperBomb/Textures)
             PROPS_TEXTURE_DEST = content path       (default /Game/PropsCheck/PaperBomb/Textures)
             PROPS_TEXTURE_OUT  = JSON result path
"""
import hashlib
import json
import os
import traceback
from pathlib import Path

import unreal

PROJECT = Path(__file__).resolve().parents[3]
MODE = os.environ.get("PROPS_TEXTURE_MODE", "import").strip().lower()
TEXTURE_DIR = Path(os.environ.get("PROPS_TEXTURE_DIR")
                   or (PROJECT / "Exports" / "PaperBomb" / "Textures"))
DEST = os.environ.get("PROPS_TEXTURE_DEST", "/Game/PropsCheck/PaperBomb/Textures")
OUT = Path(os.environ.get("PROPS_TEXTURE_OUT")
           or (TEXTURE_DIR.parent / f"ue_textures_{MODE}.json"))

INTENT = {
    "BC": {"srgb": True,
           "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT},
    "ORM": {"srgb": False,
            "compression_settings": unreal.TextureCompressionSettings.TC_MASKS,
            "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
    "N": {"srgb": False,
          "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP,
          "flip_green_channel": False},
    # the map the pack's importer silently dropped
    "M": {"srgb": False,
          "compression_settings": unreal.TextureCompressionSettings.TC_MASKS,
          "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
}


def kind_of(stem: str) -> str:
    return stem.rsplit("_", 1)[-1]


def pngs() -> dict:
    """EVERY PNG in the folder, known suffix or not.  Filtering is what hid the fourth map."""
    return {p.stem: p for p in sorted(TEXTURE_DIR.glob("*.png"))}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prop(tex, name):
    try:
        return tex.get_editor_property(name)
    except Exception as exc:  # noqa: BLE001
        return f"<{type(exc).__name__}: {exc}>"[:120]


def inspect(tex) -> dict:
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for name in ("srgb", "compression_settings", "flip_green_channel", "lod_group",
                 "mip_gen_settings", "compression_no_alpha", "address_x", "address_y",
                 "power_of_two_mode"):
        info[name] = str(_prop(tex, name))
    try:
        info["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
    except Exception as exc:  # noqa: BLE001
        info["size"] = f"<{type(exc).__name__}: {exc}>"[:120]
    return info


def matches(info: dict, kind: str) -> dict:
    want = INTENT[kind]
    out = {"srgb": str(info.get("srgb")) == str(want["srgb"]),
           "compression": str(info.get("compression_settings")) == str(want["compression_settings"])}
    if "flip_green_channel" in want:
        out["flip_green"] = str(info.get("flip_green_channel")) == str(want["flip_green_channel"])
    if "mip_gen_settings" in want:
        out["mip_gen"] = str(info.get("mip_gen_settings")) == str(want["mip_gen_settings"])
    # never ship any map with NoMipmaps, whatever else matched
    out["has_mips"] = "NO_MIPMAPS" not in str(info.get("mip_gen_settings", "")).upper()
    size = info.get("size")
    if isinstance(size, list) and len(size) == 2:
        out["power_of_two"] = all(v > 0 and (v & (v - 1)) == 0 for v in size)
    out["all"] = all(out.values())
    return out


def apply_intent(tex) -> dict:
    kind = kind_of(tex.get_name())
    applied = {}
    for key, value in INTENT[kind].items():
        tex.set_editor_property(key, value)
        applied[key] = str(value)
    return applied


def import_one(png: Path, name: str):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png))
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    textures = [t for t in (unreal.load_asset(p) for p in paths)
                if isinstance(t, unreal.Texture2D)]
    return paths, textures


def _unknown(found: dict) -> list:
    return sorted(stem for stem in found if kind_of(stem) not in INTENT)


def run_import() -> dict:
    found = pngs()
    unknown = _unknown(found)
    report = {"mode": "import", "engine": unreal.SystemLibrary.get_engine_version(),
              "dest": DEST, "texture_dir": str(TEXTURE_DIR),
              "expected": len(found), "unrecognised_suffixes": unknown, "maps": {}}
    for stem, png in found.items():
        kind = kind_of(stem)
        entry = {"png": str(png), "sha256": sha256(png), "kind": kind}
        if kind not in INTENT:
            entry["error"] = (f"no import intent for suffix {kind!r}: a map this tool "
                              f"does not recognise must fail the build, not be skipped")
            report["maps"][stem] = entry
            continue
        try:
            paths, textures = import_one(png, stem)
            entry["imported_object_paths"] = paths
            if textures:
                tex = textures[0]
                entry["as_imported"] = inspect(tex)
                entry["as_imported_matches_intent"] = matches(entry["as_imported"], kind)
                entry["applied"] = apply_intent(tex)
                entry["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
                entry["after_apply_in_process"] = inspect(tex)
                entry["in_process_matches_intent"] = matches(entry["after_apply_in_process"], kind)
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        report["maps"][stem] = entry
    report["processed"] = sum(1 for m in report["maps"].values() if m.get("saved"))
    report["passed"] = bool(report["maps"]) and not unknown and (
        report["processed"] == report["expected"]) and all(
        m.get("saved") and (m.get("in_process_matches_intent") or {}).get("all")
        for m in report["maps"].values())
    report["note"] = ("in-process reads; run MODE=verify in a fresh process for the "
                      "authoritative check.  processed == expected is a gate.")
    return report


def run_verify() -> dict:
    found = pngs()
    unknown = _unknown(found)
    report = {"mode": "verify", "engine": unreal.SystemLibrary.get_engine_version(),
              "dest": DEST, "expected": len(found),
              "unrecognised_suffixes": unknown, "maps": {}}
    for stem in found:
        kind = kind_of(stem)
        entry = {"kind": kind, "asset": f"{DEST}/{stem}"}
        if kind not in INTENT:
            entry["error"] = f"no import intent for suffix {kind!r}"
            report["maps"][stem] = entry
            continue
        try:
            tex = unreal.load_asset(entry["asset"])
            if tex is None:
                entry["error"] = "asset not found"
            else:
                entry["flags"] = inspect(tex)
                entry["matches_intent"] = matches(entry["flags"], kind)
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        report["maps"][stem] = entry
    report["processed"] = sum(1 for m in report["maps"].values() if m.get("flags"))
    report["passed"] = bool(report["maps"]) and not unknown and (
        report["processed"] == report["expected"]) and all(
        (m.get("matches_intent") or {}).get("all") for m in report["maps"].values())
    return report


def main() -> None:
    report = run_verify() if MODE == "verify" else run_import()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log(f"PROPS_IMPORT_TEXTURES_{MODE.upper()} passed={report['passed']} "
               f"processed={report.get('processed')}/{report.get('expected')} {OUT}")


main()
