"""Pass 3: Unreal exports the SAVED asset back to FBX, in a third fresh process.

UE 5.8's Python cannot read a convex element's points (``vertex_data`` does not exist on
KConvexElem), so the hull is checked by ROUND TRIP: Unreal writes its own FBX of the
package it loaded (collision included) and a fourth process (Blender,
``sfu_roundtrip_compare.py``) measures it against the shipped file.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealCheck")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import sfu_common as C                                          # noqa: E402

OUT = C.HERE / "pass3.json"
FBX_OUT = C.HERE / "unreal_roundtrip.fbx"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET, "fbx_out": str(FBX_OUT)}
    try:
        mesh = unreal.load_asset(C.ASSET)
        if mesh is None:
            report["error"] = f"{C.ASSET} did not load"
        else:
            options = unreal.FbxExportOption()
            options.set_editor_property("collision", True)
            options.set_editor_property("level_of_detail", True)
            options.set_editor_property("vertex_color", False)
            options.set_editor_property("ascii", False)
            task = unreal.AssetExportTask()
            task.set_editor_property("object", mesh)
            task.set_editor_property("filename", str(FBX_OUT))
            task.set_editor_property("automated", True)
            task.set_editor_property("prompt", False)
            task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
            task.set_editor_property("options", options)
            report["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
            report["fbx_bytes"] = FBX_OUT.stat().st_size if FBX_OUT.is_file() else 0
            report["shipped_fbx_sha256"] = C.sha256(C.FBX)
            report["report_fbx_sha256"] = C.REPORT["export"]["sha256"]["fbx"]
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("SFU_PASS3_DONE " + str(OUT))


main()
