"""Shared texture helpers for UnrealCheck7 passes 4 and 5 (inside the UE 5.8.2 pythonscript commandlet).

The pack's intent (study 4, ASSET_GUIDELINES 3, shuriken_lib.bake): BC is sRGB base colour; ORM is
linear (R AO, G roughness, B metallic); N is a linear tangent-space normal map in DirectX convention
(green already flipped on disk, so Unreal's "Flip Green Channel" must stay OFF).
"""
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
TEXTURES = PROJ / "Exports" / "Shuriken" / "Textures"
DEST = os.environ.get("SHURIKEN_DEST", "/Game/ShurikenCheck7/Indep")
FORMS = ("FourPoint", "EightPoint", "SquarePlate")
SUFFIXES = ("BC", "ORM", "N")
PNGS = {f"T_Shuriken_{form}_{suffix}": TEXTURES / f"T_Shuriken_{form}_{suffix}.png"
        for form in FORMS for suffix in SUFFIXES}

INTENT = {
    "BC": {"srgb": True, "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT},
    "ORM": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS},
    "N": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP,
          "flip_green_channel": False},
}


def kind_of(stem):
    return stem.rsplit("_", 1)[-1]


def _prop(tex, name):
    try:
        return tex.get_editor_property(name)
    except Exception as exc:  # noqa: BLE001
        return f"<{type(exc).__name__}: {exc}>"[:120]


def inspect(tex):
    """Flags that decide how a map is sampled, read from a loaded Texture2D."""
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for name in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "mip_gen_settings",
                 "never_stream", "virtual_texture_streaming", "compression_no_alpha", "filter", "address_x", "address_y"):
        info[name] = str(_prop(tex, name))
    try:
        info["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
    except Exception as exc:  # noqa: BLE001
        info["size"] = f"<{type(exc).__name__}: {exc}>"[:120]
    try:
        src = tex.get_editor_property("source")
        info["source_format"] = str(src.get_editor_property("format")) if src else None
    except Exception:  # noqa: BLE001 - TextureSource is not exposed on every build
        info["source_format"] = None
    try:
        data = tex.get_editor_property("asset_import_data")
        info["asset_import_source_file"] = str(data.get_first_filename()) if data else None
    except Exception:  # noqa: BLE001
        info["asset_import_source_file"] = None
    return info


def flags_match_intent(info, kind):
    """True when the read-back flags equal the pack's intent for this map kind."""
    want = INTENT[kind]
    srgb_ok = str(info.get("srgb")) == str(want["srgb"])
    comp_ok = str(info.get("compression_settings")) == str(want["compression_settings"])
    flip_ok = True
    if "flip_green_channel" in want:
        flip_ok = str(info.get("flip_green_channel")) == str(want["flip_green_channel"])
    return {"srgb": srgb_ok, "compression": comp_ok, "flip_green": flip_ok, "all": srgb_ok and comp_ok and flip_ok}


def apply_intent(tex):
    kind = kind_of(tex.get_name())
    applied = {}
    for key, val in INTENT[kind].items():
        tex.set_editor_property(key, val)
        applied[key] = str(val)
    return applied
