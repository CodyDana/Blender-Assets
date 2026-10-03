"""DojoLab ninja, voices_paper stage (2026-10-02): REMOVE THE JUTSU VOICE-OVERS (owner rule). Pythonscript commandlet,
-nullrhi, run by run_ninja_port.sh novoice. See dj_ninja_voice_lib.py for what and why.
Result: $DJ_NINJA_OUT/novoice.json (default WorkFiles/dojo/build/ninja_character/voices_paper/novoice.json).
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

import unreal

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal")
import dj_ninja_voice_lib as VL  # noqa: E402

OUT = Path(os.environ.get("DJ_NINJA_OUT", r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\voices_paper"))
REP = {"engine": unreal.SystemLibrary.get_engine_version()}
t0 = time.time()
ok = False
try:
    ok = VL.remove_voices(REP, delete=True)
except Exception:  # noqa: BLE001
    REP["error"] = traceback.format_exc()[-3000:]
try:   # read-only side record for part B (window paper): the DojoLab children and their armory parents
    MEL = unreal.MaterialEditingLibrary
    REP["paper_mi"] = {}
    for n in ("MI_DJA_AK_HWinPaperW", "MI_DJA_AK_HWinPaperE"):
        mi = unreal.load_asset(f"/Game/ArmoryHall/Materials/{n}")
        par = mi.get_editor_property("parent")
        rec = {"parent": par.get_path_name()}
        for tag, m in (("child", mi), ("parent", par)):
            rec[tag + "_scalars"] = {str(k): MEL.get_material_instance_scalar_parameter_value(m, k)
                                     for k in MEL.get_scalar_parameter_names(m)}
            vv = {}
            for k in MEL.get_vector_parameter_names(m):
                c = MEL.get_material_instance_vector_parameter_value(m, k)
                vv[str(k)] = [round(c.r, 4), round(c.g, 4), round(c.b, 4)]
            rec[tag + "_vectors"] = vv
        REP["paper_mi"][n] = rec
except Exception:  # noqa: BLE001
    REP["paper_mi_error"] = traceback.format_exc()[-1500:]
REP["sec"] = round(time.time() - t0, 1)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "novoice.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
unreal.log(f"DJ_STEP_DONE ninja_novoice passed={ok}")
