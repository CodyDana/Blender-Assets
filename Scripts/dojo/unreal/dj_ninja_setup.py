"""DojoLab ninja character port, stage BUILD steps B4 + B5 (pythonscript commandlet, -nullrhi, AFTER the DojoLab module
is built and the CoreRedirect /Script/DemoGame_1 -> /Script/DojoLab is in Config/DefaultEngine.ini).

What it changes (all idempotent, every change recorded in the report):
  1. /Game/Ninja/Blueprints/BP_NinjaGasp (the 43fd6ce male-era copy): removes the SCS components the owner does not want
     now: NinjaAirJump (double jump / flips), NinjaLockOn (Tab), NinjaStance (crouch run / prone), NinjaFreeLook (Alt),
     NinjaCombat (taijutsu). The jutsu component reaches Stance / LockOn only through null-safe FindComponentByClass, so
     the jutsu need none of them. Play-test fix T1: the CDO's jump_max_count (DemoGame_1 wrote 2 for the removed flip) =
     SandboxCharacter_CMC's. Compiled and saved.
  2. /Game/Ninja/Input/IMC_NinjaGasp: trimmed to the jutsu rows (IA_Jutsu, IA_Jutsu_GreatFireball, IA_Jutsu_Summoning,
     IA_Jutsu_Chidori). Every other row (LMB, RMB, E, Q, C, Z, Tab, LeftAlt, 1, 5, F1 ...) is unmapped so the keys reach
     GASP's IMC_Sandbox again (C crouch, RMB aim). Saved.
  3. /Game/Dojo/Blueprints/GM_DojoNinja: new Blueprint child of GM_Dojo, DefaultPawnClass = BP_NinjaGasp_C. Saved.
     GM_Dojo itself is NOT changed (it still gives SandboxCharacter_CMC: the reference-pawn route).
  4. /Game/Dojo/Maps/L_Dojo: World Settings GameMode override GM_Dojo -> GM_DojoNinja. Nothing else in the level
     changes (the PlayerStarts P1 / P2 stay where they are). Saved.
  5. NO JUTSU VOICE-OVERS (owner rule 2026-10-02; dj_ninja_voice_lib.py): StartVoice = None on every jutsu, the
     /Game/Ninja/Audio/Voice packages deleted when nothing references them (a re-sync must never copy them: the survey /
     copy tools block that folder), redirectors fixed up. Idempotent: nothing is saved when no jutsu has a voice.
The project default (GlobalDefaultGameMode in Config/DefaultEngine.ini) is switched by the runner (plain text) after
this step passes.
Result: WorkFiles/dojo/build/ninja_character/build/setup.json
"""
import json
import sys
import time
import traceback
from pathlib import Path

import unreal

sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/unreal")
import dj_ninja_voice_lib as VL  # noqa: E402

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character\build")
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
LIB = unreal.SubobjectDataBlueprintFunctionLibrary

BP_NINJA = "/Game/Ninja/Blueprints/BP_NinjaGasp"
BP_VISUAL = "/Game/Ninja/Blueprints/BP_NinjaVisual"
IMC = "/Game/Ninja/Input/IMC_NinjaGasp"
GM_DOJO = "/Game/Dojo/Blueprints/GM_Dojo"
GM_NINJA = "/Game/Dojo/Blueprints/GM_DojoNinja"
LEVEL = "/Game/Dojo/Maps/L_Dojo"
REMOVE = ["NinjaAirJump", "NinjaLockOn", "NinjaStance", "NinjaFreeLook", "NinjaCombat"]
KEEP_ACTIONS = ["IA_Jutsu", "IA_Jutsu_GreatFireball", "IA_Jutsu_Summoning", "IA_Jutsu_Chidori"]
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": []}


def handles_of(bp):
    out = {}
    for h in SUB.k2_gather_subobject_data_for_blueprint(bp):
        d = LIB.get_data(h)
        obj = LIB.get_object(d)
        out[str(LIB.get_variable_name(d))] = (h, obj)
    return out


def comp_table(bp):
    return {n: (o.get_class().get_path_name() if o else None) for n, (h, o) in handles_of(bp).items()}


def imc_rows(imc):
    rows = []
    for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
        a = m.get_editor_property("action")
        rows.append([str(m.get_editor_property("key").get_editor_property("key_name")), a.get_name() if a else None])
    return rows


def step_module():
    names = ("NinjaJutsuComponent", "NinjaVisualBodyComponent", "NinjaRunStyleComponent", "NinjaTurnComponent",
             "NinjaJutsu", "NinjaFireball", "NinjaHandEffect", "NinjaGroundSeal", "DojoNinjaCameraSubsystem")
    REP["module_classes"] = {c: bool(unreal.load_class(None, f"/Script/DojoLab.{c}")) for c in names}
    REP["python_names"] = {c: hasattr(unreal, c) for c in names}
    ok = all(REP["module_classes"].values())
    cls = unreal.load_class(None, "/Script/DojoLab.NinjaJutsuComponent")
    REP["class_by_new_path"] = cls.get_path_name() if cls else None
    old = unreal.load_class(None, "/Script/DemoGame_1.NinjaJutsuComponent")
    REP["class_by_old_path_redirected"] = old.get_path_name() if old else None
    return ok and cls is not None and old is not None


def step_bp():
    bp = unreal.load_asset(BP_NINJA)
    if bp is None:
        raise RuntimeError("BP_NinjaGasp did not load")
    before = comp_table(bp)
    REP["bp_components_before"] = before
    removed = []
    for name in REMOVE:
        hs = handles_of(bp)
        if name not in hs:
            continue
        root = SUB.k2_gather_subobject_data_for_blueprint(bp)[0]
        n = SUB.delete_subobject(root, hs[name][0], bp)
        removed.append([name, int(n) if n is not None else None])
    REP["bp_removed"] = removed
    # play-test fix T1 (2026-10-02): DemoGame_1's setup_ninja_gasp.py wrote jump_max_count 2 on the CDO for the air-jump
    # flip removed above; without the component it is a plain engine double jump. Match GASP's SandboxCharacter_CMC.
    gasp = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(
        unreal.load_asset("/Game/Blueprints/SandboxCharacter_CMC")))
    ncdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    REP["jump_max_count"] = [int(ncdo.get_editor_property("jump_max_count")), int(gasp.get_editor_property("jump_max_count"))]
    if REP["jump_max_count"][0] != REP["jump_max_count"][1]:
        ncdo.set_editor_property("jump_max_count", REP["jump_max_count"][1])
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    after = comp_table(bp)
    REP["bp_components_after"] = after
    REP["bp_saved"] = bool(EAL.save_loaded_asset(bp, False))
    vis = unreal.load_asset(BP_VISUAL)
    REP["visual_components"] = comp_table(vis) if vis else None
    jutsu = None
    cdo_cls = unreal.BlueprintEditorLibrary.generated_class(bp)
    for n, (h, o) in handles_of(bp).items():
        if o is not None and o.get_class().get_name() == "NinjaJutsuComponent":
            jutsu = o
    REP["jutsu_list"] = [j.get_path_name() for j in jutsu.get_editor_property("jutsus")] if jutsu else None
    REP["bp_generated_class"] = cdo_cls.get_path_name() if cdo_cls else None
    gone = all(n not in after for n in REMOVE)
    keep = all(n in after for n in ("NinjaJutsu", "VisualOverride"))
    return gone and keep and REP["bp_saved"] and bool(REP["jutsu_list"])


def step_imc():
    imc = unreal.load_asset(IMC)
    REP["imc_before"] = imc_rows(imc)
    seen = {}
    for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
        a = m.get_editor_property("action")
        if a is not None:
            seen.setdefault(a.get_name(), a)
    unmapped = []
    for name, a in seen.items():
        if name not in KEEP_ACTIONS:
            imc.unmap_all_keys_from_action(a)
            unmapped.append(name)
    REP["imc_unmapped_actions"] = sorted(unmapped)
    REP["imc_after"] = imc_rows(imc)
    REP["imc_saved"] = bool(EAL.save_loaded_asset(imc, False))
    acts = sorted({r[1] for r in REP["imc_after"]})
    return REP["imc_saved"] and acts == sorted(KEEP_ACTIONS) and len(REP["imc_after"]) == 8


def step_gm():
    parent = EAL.load_blueprint_class(GM_DOJO)
    pawn = EAL.load_blueprint_class(BP_NINJA)
    if EAL.does_asset_exist(GM_NINJA):
        bp = unreal.load_asset(GM_NINJA)
        REP["gm_existed"] = True
    else:
        folder, name = GM_NINJA.rsplit("/", 1)
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", parent)
        bp = AT.create_asset(name, folder, unreal.Blueprint, f)
        REP["gm_existed"] = False
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    cdo.set_editor_property("default_pawn_class", pawn)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    if cdo.get_editor_property("default_pawn_class") != pawn:
        cdo.set_editor_property("default_pawn_class", pawn)
    REP["gm_saved"] = bool(EAL.save_loaded_asset(bp, False))
    REP["gm_default_pawn"] = cdo.get_editor_property("default_pawn_class").get_path_name()
    REP["gm_parent"] = parent.get_path_name()
    gm_dojo_pawn = unreal.get_default_object(parent).get_editor_property("default_pawn_class")
    REP["gm_dojo_default_pawn"] = gm_dojo_pawn.get_path_name() if gm_dojo_pawn else None
    return (REP["gm_saved"] and REP["gm_default_pawn"].endswith("BP_NinjaGasp_C")
            and REP["gm_dojo_default_pawn"].endswith("SandboxCharacter_CMC_C"))


def step_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["level_open"] = bool(les.load_level(LEVEL))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = world.get_world_settings()
    old = ws.get_editor_property("default_game_mode")
    REP["world_game_mode_before"] = old.get_path_name() if old else None
    starts = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart):
        l, r = a.get_actor_location(), a.get_actor_rotation()
        starts.append({"label": a.get_actor_label(), "tag": str(a.get_editor_property("player_start_tag")),
                       "loc": [round(l.x, 2), round(l.y, 2), round(l.z, 2)], "yaw": round(r.yaw, 2)})
    REP["player_starts"] = starts
    new = EAL.load_blueprint_class(GM_NINJA)
    if old is None or old.get_path_name() != new.get_path_name():
        ws.set_editor_property("default_game_mode", new)
        saved = False
        try:
            saved = bool(les.save_current_level())
        except Exception as exc:  # noqa: BLE001
            REP["notes"].append(f"save_current_level: {exc}")
        if not saved:
            saved = bool(unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL))
        REP["level_saved"] = saved
    else:
        REP["level_saved"] = "skipped (already GM_DojoNinja)"
    cur = ws.get_editor_property("default_game_mode")
    REP["world_game_mode_after"] = cur.get_path_name() if cur else None
    return bool(REP["level_saved"]) and REP["world_game_mode_after"].endswith("GM_DojoNinja_C") and len(starts) == 2


def step_novoice():
    REP["novoice"] = {}
    return VL.remove_voices(REP["novoice"], delete=True)


def main():
    t0 = time.time()
    steps = {}
    try:
        for name, fn in (("module", step_module), ("bp", step_bp), ("imc", step_imc), ("gm", step_gm),
                         ("level", step_level), ("novoice", step_novoice)):
            steps[name] = bool(fn())
            unreal.log(f"DJ_NINJA step {name} ok={steps[name]}")
            if not steps[name]:
                break
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
    REP["steps"] = steps
    REP["passed"] = len(steps) == 6 and all(steps.values()) and "error" not in REP
    REP["sec"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "setup.json").write_text(json.dumps(REP, indent=1), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ninja_setup passed={REP['passed']}")


main()
