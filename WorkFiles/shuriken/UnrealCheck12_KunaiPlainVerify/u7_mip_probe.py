"""UnrealCheck12 probe (evidence for a finding, not a gate): does T_Kunai_Lettering get a mip chain in Unreal?

The saved lettering mask (imported by Scripts/shuriken/ue_import_textures.py) reads MipGenSettings = TMGS_NO_MIPMAPS
although the script and LETTERING_HOWTO.md set "Stretch to power of two" precisely so that Unreal builds mips.  This
probe imports the same PNG twice into a throwaway fresh path, both with the script's four Lettering flags; copy B also
sets mip_gen_settings = TMGS_FROM_TEXTURE_GROUP.  Mode "import" writes, mode "verify" (a second fresh process) reads
back the saved flags and whatever mip count the Python API exposes.
    SHURIKEN_UC12_PROBE_MODE = import | verify
Writes u7_mip_probe_<mode>.json.
"""
import os
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck12_KunaiPlainVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc12_common as C  # noqa: E402

MODE = os.environ.get("SHURIKEN_UC12_PROBE_MODE", "import")
DEST = "/Game/KunaiPlainVerify12/MipProbe"
PNG = C.TEX_DIR / "T_Kunai_Lettering.png"
COPIES = {"T_Kunai_Lettering_ScriptFlags": False, "T_Kunai_Lettering_PlusMipGen": True}


def mip_info(tex):
    out = {"mip_gen_settings": str(C.safe(lambda: tex.get_editor_property("mip_gen_settings"))),
           "power_of_two_mode": str(C.safe(lambda: tex.get_editor_property("power_of_two_mode"))),
           "never_stream": str(C.safe(lambda: tex.get_editor_property("never_stream"))),
           "api_names_with_mip": sorted(n for n in dir(tex) if "mip" in n.lower())}
    for name in ("get_num_mips", "blueprint_get_num_mips", "get_num_mips_allowed"):
        fn = getattr(tex, name, None)
        if fn is not None:
            out[name] = C.safe(lambda fn=fn: int(fn()))
    return out


def main():
    rep = {"mode": MODE, "dest": DEST, "png": str(PNG), "png_sha256": C.sha256(PNG), "copies": {}}
    try:
        for name, plus in COPIES.items():
            path = f"{DEST}/{name}"
            if MODE == "import":
                task = unreal.AssetImportTask()
                task.set_editor_property("filename", str(PNG))
                task.set_editor_property("destination_path", DEST)
                task.set_editor_property("destination_name", name)
                task.set_editor_property("automated", True)
                task.set_editor_property("replace_existing", True)
                task.set_editor_property("save", False)
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                tex = unreal.load_asset(path)
                rec = {"as_imported": mip_info(tex)}
                tex.set_editor_property("srgb", False)
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
                tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
                tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
                tex.set_editor_property("power_of_two_mode", unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
                if plus:
                    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
                rec["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
                rec["after_in_process"] = mip_info(tex)
            else:
                tex = unreal.load_asset(path)
                rec = {"fresh_process": mip_info(tex) if tex is not None else {"error": "not found"}}
            rep["copies"][name] = rec
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    C.write(C.HERE / f"u7_mip_probe_{MODE}.json", rep)
    unreal.log("UC12_U7_DONE")


main()
