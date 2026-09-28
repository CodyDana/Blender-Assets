"""Texture intent for SM_PaperBomb, and the reader that checks it.

Same rules as Scripts/shuriken/ue_import_textures.py, with the pack's fourth map
added: the pack's script has no "M" kind and would silently SKIP T_PaperBomb_M,
so the mask would ship with the TextureFactory's defaults (sRGB ON, TC_Default).

    BC   sRGB ON,  TC_Default
    ORM  sRGB OFF, TC_Masks
    N    sRGB OFF, TC_Normalmap, flip_green_channel OFF (DirectX on disk)
    M    sRGB OFF, TC_Masks                (R tear/fibre fringe, G scorch, B ink mask)

Every map is additionally required to carry a MIP CHAIN: a non-power-of-two PNG
imports with TMGS_NoMipmaps and does not texture-stream at all (the kunai shipped
that bug).  All four are 2048 square so this should be belt and braces - the gate
exists precisely to prove it.
"""
from pathlib import Path

import unreal

INTENT = {
    "BC": {"srgb": True, "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT,
           "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
    "ORM": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS,
            "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
    "N": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP,
          "flip_green_channel": False,
          "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
    "M": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS,
          "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
}


def kind_of(stem):
    return stem.rsplit("_", 1)[-1]


def _prop(tex, name):
    try:
        return tex.get_editor_property(name)
    except Exception as exc:  # noqa: BLE001
        return f"<{type(exc).__name__}: {exc}>"[:120]


def inspect(tex):
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for name in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "mip_gen_settings",
                 "compression_no_alpha", "address_x", "address_y", "power_of_two_mode", "never_stream"):
        info[name] = str(_prop(tex, name))
    try:
        info["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
    except Exception as exc:  # noqa: BLE001
        info["size"] = f"<{type(exc).__name__}: {exc}>"[:120]
    try:
        info["num_mips"] = int(len(tex.get_editor_property("platform_data").mips)) \
            if hasattr(tex, "get_editor_property") else None
    except Exception:  # noqa: BLE001
        info["num_mips"] = None
    return info


def matches(info, kind):
    want = INTENT[kind]
    out = {"srgb": str(info.get("srgb")) == str(want["srgb"]),
           "compression": str(info.get("compression_settings")) == str(want["compression_settings"])}
    if "flip_green_channel" in want:
        out["flip_green"] = str(info.get("flip_green_channel")) == str(want["flip_green_channel"])
    out["mip_gen"] = str(info.get("mip_gen_settings")) == str(want["mip_gen_settings"])
    # never ship with NoMipmaps whatever else matched
    out["has_mips"] = "NO_MIPMAPS" not in str(info.get("mip_gen_settings", "")).upper()
    size = info.get("size")
    out["power_of_two_square_2048"] = isinstance(size, list) and size == [2048, 2048]
    out["all"] = all(out.values())
    return out


def apply_intent(tex):
    kind = kind_of(tex.get_name())
    applied = {}
    for key, value in INTENT[kind].items():
        tex.set_editor_property(key, value)
        applied[key] = str(value)
    return applied


def import_one(png, name, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    return paths, [t for t in (unreal.load_asset(p) for p in paths) if isinstance(t, unreal.Texture2D)]


def verify(dest, stems):
    report = {"dest": dest, "maps": {}}
    for stem in stems:
        entry = {"kind": kind_of(stem), "asset": f"{dest}/{stem}"}
        try:
            tex = unreal.load_asset(entry["asset"])
            if tex is None:
                entry["error"] = "asset not found"
            else:
                entry["flags"] = inspect(tex)
                entry["matches_intent"] = matches(entry["flags"], entry["kind"])
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
        report["maps"][stem] = entry
    report["passed"] = bool(report["maps"]) and all(
        (m.get("matches_intent") or {}).get("all") for m in report["maps"].values())
    return report
