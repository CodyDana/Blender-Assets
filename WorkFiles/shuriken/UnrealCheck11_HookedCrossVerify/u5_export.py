"""UnrealCheck11 process 5 (fresh, after the read-back): export the SAVED hooked-cross mesh back to FBX with its LODs
and its stored collision, so b2_roundtrip.py can compare the stored hull with the shipped UCX, read Unreal's
generated lightmap UV1 (neither is readable from Python) and read the re-export's handedness in Blender.
Writes roundtrip/SM_Shuriken_HookedCross_from_unreal.fbx, u5_export.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck11_HookedCrossVerify")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc11_common as C  # noqa: E402


def main():
    out = C.HERE / "roundtrip" / f"{C.MESH}_from_unreal.fbx"
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET[C.MESH], "fbx_out": str(out)}
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        mesh = unreal.load_asset(C.ASSET[C.MESH])
        opts = unreal.FbxExportOption()
        for key, val in (("ascii", False), ("force_front_x_axis", False), ("level_of_detail", True),
                         ("collision", True), ("vertex_color", False)):
            opts.set_editor_property(key, val)
        task = unreal.AssetExportTask()
        task.set_editor_property("object", mesh)
        task.set_editor_property("filename", str(out))
        task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        task.set_editor_property("options", opts)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        rep["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
        rep["bytes"] = out.stat().st_size if out.exists() else 0
        rep["sha256"] = C.sha256(out) if out.exists() else None
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    C.write(C.HERE / "u5_export.json", rep)
    unreal.log("UC11_U5_DONE")


main()
