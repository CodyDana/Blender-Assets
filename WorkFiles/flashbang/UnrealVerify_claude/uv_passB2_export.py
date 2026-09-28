"""PASS B2 (fresh process, -nullrhi): re-export each saved mesh WITH its collision and LODs, because the convex
hull points (KConvexElem.VertexData) are not exposed to Python.  The re-exported UCX hulls and LOD0 are measured
offline (uv_analyse.py): hull convexity, hull vs shipped UCX, and every LOD0 vertex inside the hulls."""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealVerify_claude")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import uv_common as C  # noqa: E402

OUT = HERE / "passB2.json"
RT = HERE / "roundtrip"
RT.mkdir(exist_ok=True)
rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "exports": {}}
for name in C.MESHES:
    r = {}
    try:
        mesh = unreal.load_asset(f"{C.DEST}/{name}")
        fn = RT / f"{name}_ue_roundtrip.fbx"
        if fn.exists():
            fn.unlink()
        opt = unreal.FbxExportOption()
        opt.set_editor_property("collision", True)
        opt.set_editor_property("level_of_detail", True)
        opt.set_editor_property("vertex_color", False)
        opt.set_editor_property("ascii", False)
        task = unreal.AssetExportTask()
        task.set_editor_property("object", mesh)
        task.set_editor_property("filename", str(fn))
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
        task.set_editor_property("options", opt)
        r["ok"] = bool(unreal.Exporter.run_asset_export_task(task))
        r["bytes"] = fn.stat().st_size if fn.is_file() else 0
    except Exception:  # noqa: BLE001
        r["error"] = traceback.format_exc()
    rep["exports"][name] = r
OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
unreal.log("UV_PASSB2_DONE")
