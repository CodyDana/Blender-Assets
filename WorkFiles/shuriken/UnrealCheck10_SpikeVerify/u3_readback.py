"""UnrealCheck10 process 3: FRESH-process read-back of the saved spike mesh and its three saved maps. Imports nothing
and writes to no asset. Only reads; every gate is evaluated in summarize.py against b1_truth.json.
Writes u3_readback.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck10_SpikeVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc10_common as C  # noqa: E402


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "asset": C.ASSET,
           "fbx_sha256_now": C.sha256(C.FBX), "fbx_md5_now": C.md5(C.FBX), "sidecar_sha256_now": C.sha256(C.SIDECAR)}
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
    for kind, png in C.TEXTURES.items():
        rec = {"png": str(png), "png_sha256_now": C.sha256(png), "png_md5_now": C.md5(png),
               "asset": f"{C.TEX_DEST}/{png.stem}"}
        try:
            tex = unreal.load_asset(rec["asset"])
            rec["info"] = C.inspect_texture(tex) if tex is not None else {"error": "not found"}
        except Exception:  # noqa: BLE001
            rec["info"] = {"error": traceback.format_exc()}
        rep["textures"][kind] = rec
    C.write(C.HERE / "u3_readback.json", rep)
    unreal.log("UC10_U3_DONE")


main()
