"""UnrealCheck6 pass 2: load the SAVED /Game/ShurikenCheck6/<mesh> in a FRESH process and gate it.

Nothing is imported or written to the asset here. Gates 1-6 are computed in this process;
gate 7 (zero Warning/Error lines in both commandlet logs) is added by attach_engine_check.py from the
captured logs. Writes <form>_pass2.json next to this file.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck6")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import uc6_common as C  # noqa: E402

OUT = C.HERE / f"{C.FORM}_pass2.json"


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": C.FORM, "asset": C.ASSET}
    try:
        rel = C.DEST[len("/Game/"):]
        report["uasset_on_disk"] = str(Path(unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_content_dir())) / rel / f"{C.MESH}.uasset")
        report["uasset_exists"] = Path(report["uasset_on_disk"]).exists()
        mesh = unreal.load_asset(C.ASSET)
        info = C.inspect(mesh)
        report.update(info)
        g, detail = C.gates(info)
        report["gates"] = g
        report["gate_detail"] = detail
        report["passed_1_to_6"] = all(g.values())
    except Exception:
        report["error"] = traceback.format_exc()
        report["passed_1_to_6"] = False
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS2_DONE " + str(OUT))


main()
