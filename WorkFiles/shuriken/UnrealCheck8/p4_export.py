"""UnrealCheck8 process 4 (fresh, after the read-back): export each SAVED mesh back to FBX with its LODs and
its stored collision, so b2_roundtrip.py can compare the stored hull with the shipped UCX and read the
generated lightmap UV1 (neither is readable from Python). Writes roundtrip/<mesh>_from_unreal.fbx, p4_export.json.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck8")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc8_common as C  # noqa: E402


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "forms": {}}
    for form, spec in C.FORMS.items():
        out = C.HERE / "roundtrip" / f"{spec['mesh']}_from_unreal.fbx"
        rec = {"asset": C.asset(form), "fbx_out": str(out)}
        try:
            if out.exists():
                out.unlink()
            mesh = unreal.load_asset(C.asset(form))
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
            rec["export_ok"] = bool(unreal.Exporter.run_asset_export_task(task))
            rec["bytes"] = out.stat().st_size if out.exists() else 0
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()
        report["forms"][form] = rec
    C.write(C.HERE / "p4_export.json", report)
    unreal.log("UC8_P4_DONE")


main()
