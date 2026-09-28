"""UnrealCheck11 process 3: FRESH-process read-back of the saved hooked-cross mesh (and the six-point control) and the
three saved hooked-cross maps.  Imports nothing and writes to no asset.  Every gate is evaluated in summarize.py
against b1_truth.json.  Writes u3_readback.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck11_HookedCrossVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc11_common as C  # noqa: E402


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "assets": C.ASSET,
           "fbx_sha256_now": {m: C.sha256(p) for m, p in C.FBX.items()},
           "fbx_md5_now": {m: C.md5(p) for m, p in C.FBX.items()},
           "sidecar_sha256_now": {m: C.sha256(p) for m, p in C.SIDECAR.items()}}
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    rep["uasset_on_disk"] = {m: str(content / C.DEST[len("/Game/"):] / f"{m}.uasset") for m in C.ASSET}
    rep["uasset_exists"] = {m: Path(p).exists() for m, p in rep["uasset_on_disk"].items()}
    rep["dest_assets"] = [str(a) for a in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
    rep["mesh"] = {}
    for m, path in C.ASSET.items():
        try:
            mesh = unreal.load_asset(path)
            rep["mesh"][m] = C.inspect_mesh(mesh) if mesh is not None else {"error": "not found"}
        except Exception:  # noqa: BLE001
            rep["mesh"][m] = {"error": traceback.format_exc()}
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
    unreal.log("UC11_U3_DONE")


main()
