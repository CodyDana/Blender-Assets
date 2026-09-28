"""Pass 3: ask Unreal to export the SAVED asset back to FBX, in a third fresh process.

The round trip is the only way to see the collision hull and the LOD positions as the
ENGINE holds them rather than as its Python API reports them.  Unreal writes its own FBX
from the package it loaded; a fourth process (Blender, ``roundtrip_compare.py``) then
compares that file with the one that shipped: every hull vertex, every LOD's positions,
and the UV0-keyed positions.

    UnrealEditor-Cmd.exe <ShurikenValidation.uproject> -run=pythonscript \
        -script=pass3_export.py -unattended -nop4 -nosplash -nullrhi -nosound -stdout \
        -FullStdOutLogOutput
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealCheck")
sys.path.insert(0, str(HERE))

import unreal                                                   # noqa: E402
import uc_common as C                                           # noqa: E402

OUT = C.HERE / "pass3.json"
FBX_OUT = C.HERE / "unreal_roundtrip.fbx"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET,
              "fbx_out": str(FBX_OUT)}
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
            report["fbx_sha256"] = C.sha256(FBX_OUT) if FBX_OUT.is_file() else None
            report["shipped_fbx_sha256"] = C.sha256(C.FBX)
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS3_DONE " + str(OUT))


main()
