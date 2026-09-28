"""UnrealCheck7 pass 3 (diagnostic, not a gate process): export the SAVED asset back to FBX.

Unreal's legacy FBX exporter writes the built render data (all texcoord channels, so the
generated lightmap UV1 becomes visible) and, with Collision ON, the convex hull from the
body setup (hull geometry is otherwise unreadable from Python, ASSET_GUIDELINES 6.5).
roundtrip_compare.py then re-imports it in Blender. Also records which StaticMesh editor
properties mention LOD screen size, from the class docstring. Runs in its own fresh
process after pass 2; its log is reported separately from gate 7.
"""
import json
import re
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck7")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc7_common as C  # noqa: E402

OUT = C.HERE / f"{C.FORM}_pass3.json"
FBX_OUT = C.HERE / "roundtrip" / f"{C.MESH}_from_unreal.fbx"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": C.FORM, "asset": C.ASSET,
              "fbx_out": str(FBX_OUT)}
    try:
        mesh = unreal.load_asset(C.ASSET)
        doc = unreal.StaticMesh.__doc__ or ""
        report["staticmesh_props_mentioning_screen_or_auto"] = sorted(set(
            re.findall(r"``(\w*(?:screen|auto)\w*)``", doc)))
        for name in report["staticmesh_props_mentioning_screen_or_auto"]:
            try:
                report.setdefault("prop_values", {})[name] = str(mesh.get_editor_property(name))
            except Exception as exc:  # noqa: BLE001
                report.setdefault("prop_values", {})[name] = f"{type(exc).__name__}: {exc}"[:160]
        FBX_OUT.parent.mkdir(parents=True, exist_ok=True)
        opts = unreal.FbxExportOption()
        for key, val in (("ascii", False), ("force_front_x_axis", False), ("level_of_detail", True),
                         ("collision", True), ("vertex_color", False)):
            try:
                opts.set_editor_property(key, val)
            except Exception as exc:  # noqa: BLE001
                report.setdefault("option_errors", {})[key] = str(exc)[:160]
        task = unreal.AssetExportTask()
        task.set_editor_property("object", mesh)
        task.set_editor_property("filename", str(FBX_OUT))
        task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        task.set_editor_property("options", opts)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        report["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
        report["fbx_exists"] = FBX_OUT.exists()
        report["fbx_bytes"] = FBX_OUT.stat().st_size if FBX_OUT.exists() else 0
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS3_DONE " + str(OUT))


main()
