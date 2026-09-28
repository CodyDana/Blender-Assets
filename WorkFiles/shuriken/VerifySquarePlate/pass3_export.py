"""Verifier pass 3 (a third fresh process): export the SAVED asset back to FBX for the hull / UV1 round trip.

Unreal's legacy FBX exporter writes the built render data (UV0 and the generated lightmap UV1) and, with
Collision ON, the convex hull stored in the body setup, which Python cannot otherwise read
(ASSET_GUIDELINES 6.5). roundtrip.py compares it with the shipped FBX in headless Blender.
The asset is only loaded and exported, never saved; the runner hashes the .uasset around this pass.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\VerifySquarePlate")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import vsp_unreal as U  # noqa: E402

V, S = U.V, U.S
OUT = HERE / f"{V.FORM}_vpass3.json"
FBX_OUT = HERE / "roundtrip" / f"{S['mesh']}_from_unreal.fbx"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": V.FORM, "asset": S["asset"],
              "fbx_out": str(FBX_OUT)}
    try:
        mesh = unreal.load_asset(S["asset"])
        FBX_OUT.parent.mkdir(parents=True, exist_ok=True)
        if FBX_OUT.exists():
            FBX_OUT.unlink()
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
        report["fbx_sha256"] = V.sha256(FBX_OUT) if FBX_OUT.exists() else None
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("VPASS3_DONE " + str(OUT))


main()
