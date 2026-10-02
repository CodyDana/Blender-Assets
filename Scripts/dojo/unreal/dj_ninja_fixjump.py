"""DojoLab ninja character port, PLAY-TEST fix T1 (pythonscript commandlet, -nullrhi, run by run_ninja_port.sh fixjump).

The -game play test (2026-10-02) measured a plain engine DOUBLE JUMP on the ninja: a second SpaceBar in the air rose to
244 cm (single jump 127.6 cm). Cause: DemoGame_1's double jump is two pieces, the flip (UNinjaAirJumpComponent, removed
by the build stage as the owner asked) and `jump_max_count` 2 written on the BP_NinjaGasp CDO by DemoGame_1's
Tools/Claude/GASP/setup_ninja_gasp.py (line 201). The second piece survived the removal, so the ninja kept an un-animated
double jump that neither GASP's reference pawn nor the owner's request has.

Fix (idempotent): BP_NinjaGasp CDO jump_max_count = the value of GASP's SandboxCharacter_CMC CDO (read here, not
assumed). Compiled and saved. Nothing else in the Blueprint changes. Result: build/fixjump.json
"""
import json
import time
import traceback
from pathlib import Path

import unreal

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\build")
BP_NINJA = "/Game/Ninja/Blueprints/BP_NinjaGasp"
BP_GASP = "/Game/Blueprints/SandboxCharacter_CMC"
REP = {"engine": unreal.SystemLibrary.get_engine_version()}


def cdo(path):
    bp = unreal.load_asset(path)
    if bp is None:
        raise RuntimeError(f"{path} did not load")
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def main():
    t0 = time.time()
    ok = False
    try:
        gbp, g = cdo(BP_GASP)
        want = int(g.get_editor_property("jump_max_count"))
        bp, n = cdo(BP_NINJA)
        before = int(n.get_editor_property("jump_max_count"))
        REP.update({"gasp_jump_max_count": want, "ninja_before": before})
        if before != want:
            n.set_editor_property("jump_max_count", want)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            REP["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(bp, False))
        else:
            REP["saved"] = "unchanged"
        _, n2 = cdo(BP_NINJA)
        REP["ninja_after"] = int(n2.get_editor_property("jump_max_count"))
        ok = REP["ninja_after"] == want and REP["saved"] in (True, "unchanged")
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
    REP["passed"] = ok
    REP["sec"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fixjump.json").write_text(json.dumps(REP, indent=1), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ninja_fixjump passed={ok} {REP}")


main()
