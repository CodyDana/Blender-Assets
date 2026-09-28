"""Import the pack's baked maps into Unreal with the RIGHT texture flags, and verify them.

Why (UnrealCheck7, UE 5.8.2 commandlet, measured): ``unreal.AssetImportTask`` imports every
PNG through the TextureFactory with sRGB ON and TC_Default.  The BC map wants exactly that, and
the ``_N`` suffix is auto-detected as a normal map (sRGB off, TC_Normalmap, flip green OFF -
correct, the pack's N is DirectX on disk), but Unreal has no mask detection: the ORM arrives
sRGB / TC_Default, so roughness 0.32 decodes as 0.084 (mirror steel), bare 0.25 as 0.051 and
AO 0.5 as 0.21.  This is the texture half of the post-import step (``pipeline.ue_import_sockets``
is the mesh half): it imports each T_<Pack>_<Form>_{BC,ORM,N}.png, sets the flags by suffix,
saves, and (in a SECOND fresh process, ``verify`` mode) reads them back.

    BC   sRGB ON,  TC_Default
    ORM  sRGB OFF, TC_Masks                 (R AO, G roughness, B metallic; linear)
    N    sRGB OFF, TC_Normalmap, flip_green_channel OFF   (DirectX convention on disk)

Buyers importing by hand: untick sRGB on every ORM and set its Compression Settings to Masks
(no alpha); leave the N map's Flip Green Channel OFF.

Library 3.10 (the plain kunai): its second material slot's maps (T_Kunai_Wrap_BC / _ORM / _N and the undyed
T_Kunai_Wrap_Natural_BC) are BC / ORM / N like any other, with one more requirement: they are sampled in UV tile u 1..2, so
their Address X / Y must stay Wrap (Unreal's default; checked, never changed).  T_Kunai_Lettering, the single-channel ink
mask of the grip's lettering band, is a new kind:

    Lettering  sRGB OFF, TC_Grayscale, Address Clamp (X and Y: the band's rectangle is remapped to 0..1 and must not
               tile into its neighbours), Power Of Two Mode "Stretch to power of two" (1536 x 256 is the band's 6:1 at
               square texels, not a power of two) AND Mip Gen Settings "From Texture Group"

3.10.1, measured in UE 5.8.2 twice in fresh processes (the plain kunai's Unreal review): a non-power-of-two PNG is
imported with MipGenSettings = TMGS_NoMipmaps, and the Stretch setting does NOT reset it - the texture ships with a
single mip however square the stretched size is.  Both flags are set here, and ``verify`` fails on NoMipmaps.

Runs inside the pythonscript commandlet, one mode per process (never mix import and verify in
one process - the verify must prove the flags PERSISTED):

    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" <project.uproject> \
        -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput

Environment: SHURIKEN_TEXTURE_MODE = import | verify (default import)
             SHURIKEN_TEXTURE_DIR  = folder of the PNGs (default Exports/Shuriken/Textures)
             SHURIKEN_TEXTURE_DEST = content path (default /Game/Shuriken/Textures)
             SHURIKEN_TEXTURE_OUT  = JSON result path (default <texture dir>/../ue_textures_<mode>.json)
Exit: the JSON's ``passed`` says whether every map carries its intended flags (verify mode reads
them from the SAVED assets in a fresh process; import mode reads them in-process, informational).
"""
import hashlib
import json
import os
import traceback
from pathlib import Path

import unreal

PROJECT = Path(__file__).resolve().parents[2]
MODE = os.environ.get("SHURIKEN_TEXTURE_MODE", "import").strip().lower()
TEXTURE_DIR = Path(os.environ.get("SHURIKEN_TEXTURE_DIR") or (PROJECT / "Exports" / "Shuriken" / "Textures"))
DEST = os.environ.get("SHURIKEN_TEXTURE_DEST", "/Game/Shuriken/Textures")
OUT = Path(os.environ.get("SHURIKEN_TEXTURE_OUT") or (TEXTURE_DIR.parent / f"ue_textures_{MODE}.json"))

def _pot_stretch():
    """ETexturePowerOfTwoSetting::StretchToPowerOfTwo, by whatever name this engine's Python gives it (or None)."""
    enum = getattr(unreal, "TexturePowerOfTwoSetting", None)
    for name in ("STRETCH_TO_POWER_OF_TWO", "STRETCH_TO_POWER_OF2", "STRETCH_TO_POW2"):
        if enum is not None and hasattr(enum, name):
            return getattr(enum, name)
    return None


INTENT = {
    "BC": {"srgb": True, "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT},
    "ORM": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS},
    "N": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP,
          "flip_green_channel": False},
    "Lettering": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_GRAYSCALE,
                  "address_x": unreal.TextureAddress.TA_CLAMP, "address_y": unreal.TextureAddress.TA_CLAMP,
                  # 3.10.1 (the plain kunai's Unreal review): the texture factory imports a NON-POWER-OF-TWO PNG with
                  # MipGenSettings = TMGS_NoMipmaps, and setting Power Of Two Mode to Stretch afterwards does NOT undo
                  # that - measured in a fresh process, twice.  The mask ships blank, so nothing shows today; lettering
                  # painted into it would be sampled without mips (the 72 mm band is ~78 px wide at the LOD1 switch and
                  # ~27 px at 2.54 m, 20:1 and 56:1 minification) and shimmer.  Set it, and gate it below.
                  "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,
                  **({"power_of_two_mode": _pot_stretch()} if _pot_stretch() is not None else {})},
}
# checked on the named maps, never set: the kunai's wrap maps are sampled in UV tile u 1..2 (Wrap addressing)
CHECK_ONLY = {"T_Kunai_Wrap_": {"address_x": unreal.TextureAddress.TA_WRAP, "address_y": unreal.TextureAddress.TA_WRAP}}


def kind_of(stem: str) -> str:
    return stem.rsplit("_", 1)[-1]


def pngs() -> dict:
    return {p.stem: p for p in sorted(TEXTURE_DIR.glob("T_*_*.png")) if kind_of(p.stem) in INTENT}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prop(tex, name):
    try:
        return tex.get_editor_property(name)
    except Exception as exc:  # noqa: BLE001
        return f"<{type(exc).__name__}: {exc}>"[:120]


def inspect(tex) -> dict:
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for name in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "mip_gen_settings",
                 "compression_no_alpha", "address_x", "address_y", "power_of_two_mode"):
        info[name] = str(_prop(tex, name))
    try:
        info["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
    except Exception as exc:  # noqa: BLE001
        info["size"] = f"<{type(exc).__name__}: {exc}>"[:120]
    return info


def matches(info: dict, kind: str, stem: str = "") -> dict:
    want = INTENT[kind]
    out = {"srgb": str(info.get("srgb")) == str(want["srgb"]),
           "compression": str(info.get("compression_settings")) == str(want["compression_settings"])}
    if "flip_green_channel" in want:
        out["flip_green"] = str(info.get("flip_green_channel")) == str(want["flip_green_channel"])
    for key in ("address_x", "address_y", "power_of_two_mode", "mip_gen_settings"):
        if key in want:
            out[key] = str(info.get(key)) == str(want[key])
    if kind == "Lettering":
        # never ship the mask with NoMipmaps, whatever else matched (the import default for a non-power-of-two PNG)
        out["has_mips"] = "NO_MIPMAPS" not in str(info.get("mip_gen_settings", "")).upper()
        if "power_of_two_mode" not in want:
            out["power_of_two_mode_available"] = False      # this engine has no stretch setting: a real gap
    for prefix, checks in CHECK_ONLY.items():
        if stem.startswith(prefix):
            for key, value in checks.items():
                out[f"{key}_wrap_tile"] = str(info.get(key)) == str(value)
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
    textures = [t for t in (unreal.load_asset(p) for p in paths) if isinstance(t, unreal.Texture2D)]
    return paths, textures


def run_import() -> dict:
    report = {"mode": "import", "engine": unreal.SystemLibrary.get_engine_version(), "dest": DEST,
              "texture_dir": str(TEXTURE_DIR), "maps": {}}
    for stem, png in pngs().items():
        entry = {"png": str(png), "sha256": sha256(png), "kind": kind_of(stem)}
        try:
            paths, textures = import_one(png, stem)
            entry["imported_object_paths"] = paths
            if textures:
                tex = textures[0]
                entry["as_imported"] = inspect(tex)
                entry["as_imported_matches_intent"] = matches(entry["as_imported"], entry["kind"], stem)
                entry["applied"] = apply_intent(tex)
                entry["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
                entry["after_apply_in_process"] = inspect(tex)
                entry["in_process_matches_intent"] = matches(entry["after_apply_in_process"], entry["kind"], stem)
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        report["maps"][stem] = entry
    report["passed"] = bool(report["maps"]) and all(
        m.get("saved") and (m.get("in_process_matches_intent") or {}).get("all") for m in report["maps"].values())
    report["note"] = "in-process reads; run MODE=verify in a fresh process for the authoritative check"
    return report


def run_verify() -> dict:
    report = {"mode": "verify", "engine": unreal.SystemLibrary.get_engine_version(), "dest": DEST, "maps": {}}
    for stem in pngs():
        entry = {"kind": kind_of(stem), "asset": f"{DEST}/{stem}"}
        try:
            tex = unreal.load_asset(entry["asset"])
            if tex is None:
                entry["error"] = "asset not found"
            else:
                entry["flags"] = inspect(tex)
                entry["matches_intent"] = matches(entry["flags"], entry["kind"], stem)
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        report["maps"][stem] = entry
    report["passed"] = bool(report["maps"]) and all(
        (m.get("matches_intent") or {}).get("all") for m in report["maps"].values())
    return report


def main() -> None:
    report = run_verify() if MODE == "verify" else run_import()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log(f"UE_IMPORT_TEXTURES_{MODE.upper()} passed={report['passed']} {OUT}")


main()
