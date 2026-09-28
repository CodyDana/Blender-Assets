"""UnrealCheck12 process 3: FRESH-process read-back of the SAVED SM_Kunai_Plain and of every saved map in
/Game/KunaiPlainVerify12/Run1/Textures.  Imports nothing, writes to no asset.  Gates are evaluated in summarize.py.
Writes u3_readback.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck12_KunaiPlainVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc12_common as C  # noqa: E402


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "asset": C.ASSET,
           "fbx_sha256_now": C.sha256(C.FBX), "fbx_md5_now": C.md5(C.FBX), "sidecar_sha256_now": C.sha256(C.SIDECAR),
           "dirty_packages_at_start": C.dirty_packages()}
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    rep["uasset_on_disk"] = str(content / C.DEST[len("/Game/"):] / f"{C.MESH}.uasset")
    rep["uasset_exists"] = Path(rep["uasset_on_disk"]).exists()
    rep["dest_assets"] = [str(a) for a in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
    try:
        mesh = unreal.load_asset(C.ASSET)
        rep["mesh"] = C.inspect_mesh(mesh) if mesh is not None else {"error": "not found"}
    except Exception:  # noqa: BLE001
        rep["mesh"] = {"error": traceback.format_exc()}
    rep["textures"] = {}
    for png in sorted(C.TEX_DIR.glob("T_*.png")):
        rec = {"png": str(png), "png_sha256_now": C.sha256(png), "png_md5_now": C.md5(png),
               "asset": f"{C.TEX_DEST}/{png.stem}", "kunai": png.stem in C.KUNAI_MAPS}
        try:
            tex = unreal.load_asset(rec["asset"]) if unreal.EditorAssetLibrary.does_asset_exist(rec["asset"]) else None
            rec["info"] = C.inspect_texture(tex) if tex is not None else {"error": "not found"}
        except Exception:  # noqa: BLE001
            rec["info"] = {"error": traceback.format_exc()}
        rep["textures"][png.stem] = rec
    rep["dirty_packages_at_end"] = C.dirty_packages()
    C.write(C.HERE / "u3_readback.json", rep)
    unreal.log("UC12_U3_DONE")


main()
