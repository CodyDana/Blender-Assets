"""UnrealCheck9 step 4 (its own fresh process, after the read-back): export the SAVED asset back to FBX with its
LODs and its STORED collision (the only way to read the hull and the generated UV1). Saves no asset.
Writes roundtrip/SM_Shuriken_SixPoint_from_unreal.fbx and s4_export.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck9_SixPoint")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import u9_common as C  # noqa: E402

OUT = C.HERE / "roundtrip" / f"{C.MESH}_from_unreal.fbx"


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET, "fbx_out": str(OUT)}
    try:
        if OUT.exists():
            OUT.unlink()
        mesh = unreal.load_asset(C.ASSET)
        opts = unreal.FbxExportOption()
        for key, val in (("ascii", False), ("force_front_x_axis", False), ("level_of_detail", True),
                         ("collision", True), ("vertex_color", False)):
            opts.set_editor_property(key, val)
        task = unreal.AssetExportTask()
        task.set_editor_property("object", mesh)
        task.set_editor_property("filename", str(OUT))
        task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        task.set_editor_property("options", opts)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        rep["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
        rep["bytes"] = OUT.stat().st_size if OUT.exists() else 0
        rep["sha256"] = C.sha256(OUT) if OUT.exists() else None
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    C.write(C.HERE / "s4_export.json", rep)
    unreal.log("U9_S4_DONE")


main()
