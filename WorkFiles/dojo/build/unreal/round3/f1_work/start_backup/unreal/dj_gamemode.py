"""DojoLab (pythonscript commandlet, -nullrhi): /Game/Dojo/Blueprints/GM_Dojo, a Blueprint child of GASP's GM_Sandbox whose
default pawn is SandboxCharacter_CMC (the CharacterMovementComponent character the game's BP_NinjaGasp is copied from).

Why a child: GM_Sandbox's own DefaultPawnClass is SandboxCharacter_Mover (read by dj_gasp_inspect.py). Its
GetDefaultPawnClassForController returns PawnClasses[DDCvar.PawnClass] when that cvar is set and DefaultPawnClass
otherwise (DDCvar.PawnClass defaults to -1 in Config/DefaultEngine.ini), so the child's DefaultPawnClass decides.
The GASP assets themselves are not edited. Idempotent: an existing GM_Dojo is reused and re-set.
Result: WorkFiles/dojo/build/unreal/gamemode.json
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()


def main():
    t0 = time.time()
    rep = {"engine": unreal.SystemLibrary.get_engine_version()}
    try:
        parent = EAL.load_blueprint_class(C.GASP_GAME_MODE)
        pawn = EAL.load_blueprint_class(C.GASP_CHARACTER)
        path = C.DOJO_GAME_MODE
        if EAL.does_asset_exist(path):
            bp = unreal.load_asset(path)
            rep["existed"] = True
        else:
            folder, name = path.rsplit("/", 1)
            f = unreal.BlueprintFactory()
            f.set_editor_property("parent_class", parent)
            bp = AT.create_asset(name, folder, unreal.Blueprint, f)
            rep["existed"] = False
        if bp is None:
            raise RuntimeError("GM_Dojo could not be created")
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        gen = unreal.BlueprintEditorLibrary.generated_class(bp)
        cdo = unreal.get_default_object(gen)
        cdo.set_editor_property("default_pawn_class", pawn)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
        if cdo.get_editor_property("default_pawn_class") != pawn:
            cdo.set_editor_property("default_pawn_class", pawn)
        rep["saved"] = bool(EAL.save_loaded_asset(bp, False))
        rep["default_pawn"] = cdo.get_editor_property("default_pawn_class").get_path_name()
        rep["controller"] = cdo.get_editor_property("player_controller_class").get_path_name()
        rep["parent"] = parent.get_path_name()
        rep["passed"] = rep["saved"] and rep["default_pawn"].endswith("SandboxCharacter_CMC_C")
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()[-2000:]
        rep["passed"] = False
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "gamemode.json", rep)
    unreal.log(f"DJ_STEP_DONE gamemode passed={rep['passed']}")


main()
