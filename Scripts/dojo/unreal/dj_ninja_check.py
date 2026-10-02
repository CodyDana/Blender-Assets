"""DojoLab ninja character port: headless load check (pythonscript commandlet, -nullrhi, a FRESH process after
dj_ninja_setup.py). Read-only: saves nothing.

Gates (each recorded in WorkFiles/dojo/build/ninja_character/build/check.json; the runner's log scan adds the log
gates, tools/scan_log.py -> scan.json):
  A modules     the DojoLab classes are loaded; /Script/DemoGame_1.<Class> resolves through the CoreRedirect
  B packages    every ported package (copy_log_content.json, 510) loads; none is a redirector
  C deps        the hard /Game dependency closure of GM_DojoNinja, BP_NinjaGasp, BP_NinjaVisual, IMC_NinjaGasp, the
                four DA_Jutsu_* and L_Dojo's game mode chain exists on disk (asset registry)
  D character   BP_NinjaGasp components: no unwanted component, every component class valid (no None), NinjaJutsu with
                4 jutsu, NinjaTurn + NinjaRunStyle present; BP_NinjaVisual has NinjaVisualBody, MetaHuman, CloakMH;
                the capsule equals the SandboxCharacter_CMC CDO's; the SpringArm (375, socket 0) / Camera FOV as
                DemoGame_1's centred camera; GameplayCamera auto-activate off, the plain camera on
  E gamemode    ini GlobalDefaultGameMode = GM_DojoNinja; GM_DojoNinja -> BP_NinjaGasp; GM_Dojo -> SandboxCharacter_CMC
                (the reference route); L_Dojo world override = GM_DojoNinja; two PlayerStarts as before the port
  F input       IMC_NinjaGasp has exactly the 8 jutsu rows
"""
import json
import time
import traceback
from pathlib import Path

import unreal

NC = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\ninja_character")
OUT = NC / "build"
PROJ = Path(r"C:\Users\Cody\Documents\Unreal Projects\DojoLab")
EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
SUB = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
LIB = unreal.SubobjectDataBlueprintFunctionLibrary
LEVEL = "/Game/Dojo/Maps/L_Dojo"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "gates": {}}
UNWANTED = ["NinjaAirJump", "NinjaLockOn", "NinjaStance", "NinjaFreeLook", "NinjaCombat"]


def handles_of(bp):
    out = {}
    for h in SUB.k2_gather_subobject_data_for_blueprint(bp):
        d = LIB.get_data(h)
        out[str(LIB.get_variable_name(d))] = LIB.get_object(d)
    return out


def deps(pkg, seen):
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False,
                                                 include_hard_package_references=True)
    for d in AR.get_dependencies(pkg, opts) or []:
        d = str(d)
        if d.startswith("/Game") and d not in seen:
            seen.add(d)
            deps(d, seen)
    return seen


def gate_modules():
    names = ["NinjaJutsuComponent", "NinjaJutsu", "NinjaVisualBodyComponent", "NinjaRunStyleComponent",
             "NinjaTurnComponent", "NinjaFireball", "NinjaHandEffect", "NinjaGroundSeal", "NinjaStanceComponent",
             "NinjaLockOnComponent", "NinjaCombatComponent", "NinjaAirJumpComponent", "NinjaFreeLookComponent",
             "NinjaLockOnCameraModifier", "DojoNinjaCameraSubsystem"]
    # every class by its /Script/DojoLab path (the camera subsystem is not BlueprintType, so Python has no name for it)
    res = {"classes": {n: bool(unreal.load_class(None, f"/Script/DojoLab.{n}")) for n in names},
           "python_names": {n: hasattr(unreal, n) for n in names}, "redirected": {}}
    for n in names[:-1]:
        c = unreal.load_class(None, f"/Script/DemoGame_1.{n}")
        res["redirected"][n] = c.get_path_name() if c else None
    res["passed"] = all(res["classes"].values()) and all(
        v and v.startswith("/Script/DojoLab.") for v in res["redirected"].values())
    return res


def gate_packages():
    log = json.loads((OUT / "copy_log_content.json").read_text(encoding="utf-8"))
    pkgs = sorted({f["package"] for f in log["files"]})
    failed, redirectors, classes = [], [], {}
    for p in pkgs:
        name = p.rsplit("/", 1)[1]
        try:
            a = unreal.load_asset(f"{p}.{name}")
        except Exception as exc:  # noqa: BLE001
            a = None
            failed.append([p, str(exc)[:200]])
            continue
        if a is None:
            failed.append([p, "None"])
            continue
        cn = a.get_class().get_name()
        classes[cn] = classes.get(cn, 0) + 1
        if cn == "ObjectRedirector":
            redirectors.append(p)
    return {"n_packages": len(pkgs), "loaded": len(pkgs) - len(failed), "failed": failed, "redirectors": redirectors,
            "classes": dict(sorted(classes.items(), key=lambda kv: -kv[1])),
            "passed": not failed and not redirectors and len(pkgs) == 510}


def gate_deps():
    roots = ["/Game/Dojo/Blueprints/GM_DojoNinja", "/Game/Dojo/Blueprints/GM_Dojo", "/Game/Ninja/Blueprints/BP_NinjaGasp",
             "/Game/Ninja/Blueprints/BP_NinjaVisual", "/Game/Ninja/Input/IMC_NinjaGasp",
             "/Game/Ninja/Jutsu/DA_Jutsu_ShadowClone", "/Game/Ninja/Jutsu/DA_Jutsu_GreatFireball",
             "/Game/Ninja/Jutsu/DA_Jutsu_Summoning", "/Game/Ninja/Jutsu/DA_Jutsu_Chidori"]
    seen = set()
    for r in roots:
        deps(r, seen)
    missing = sorted(p for p in seen if not EAL.does_asset_exist(p))
    private = sorted(p for p in seen if any(t in p.lower() for t in ("playerfemale", "hiyuki", "_private", "catwalk")))
    return {"roots": roots, "n_hard_deps": len(seen), "missing": missing, "private": private,
            "passed": not missing and not private}


def comp_props(o):
    out = {"class": o.get_class().get_path_name() if o else None}
    if o is None:
        return out
    for prop in ("auto_activate", "target_arm_length", "socket_offset", "target_offset", "enable_camera_lag",
                 "camera_lag_speed", "field_of_view", "child_actor_class", "component_tags", "hidden_in_game",
                 "visible"):
        try:
            v = o.get_editor_property(prop)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(v, unreal.Vector):
            v = [round(v.x, 2), round(v.y, 2), round(v.z, 2)]
        elif isinstance(v, unreal.Class):
            v = v.get_path_name()
        elif isinstance(v, unreal.Array):
            v = [str(x) for x in v]
        elif hasattr(v, "get_path_name"):
            v = v.get_path_name()
        elif isinstance(v, float):
            v = round(v, 3)
        out[prop] = v
    return out


def gate_character():
    bp = unreal.load_asset("/Game/Ninja/Blueprints/BP_NinjaGasp")
    comps = handles_of(bp)
    res = {"components": {n: comp_props(o) for n, o in comps.items()}}
    res["unwanted_present"] = [n for n in UNWANTED if n in comps]
    res["null_class"] = [n for n, o in comps.items() if o is None]
    jutsu = next((o for o in comps.values() if o and o.get_class().get_name() == "NinjaJutsuComponent"), None)
    res["jutsus"] = [j.get_name() for j in jutsu.get_editor_property("jutsus")] if jutsu else None
    have = {o.get_class().get_name() for o in comps.values() if o}
    res["has_turn_runstyle"] = {"NinjaTurnComponent": "NinjaTurnComponent" in have,
                                "NinjaRunStyleComponent": "NinjaRunStyleComponent" in have}
    vis = unreal.load_asset("/Game/Ninja/Blueprints/BP_NinjaVisual")
    vcomps = handles_of(vis)
    res["visual_components"] = {n: comp_props(o) for n, o in vcomps.items()}
    vhave = {o.get_class().get_name() for o in vcomps.values() if o}
    res["visual_ok"] = ("NinjaVisualBodyComponent" in vhave and "MetaHuman" in vcomps and "CloakMH" in vcomps
                        and not [n for n, o in vcomps.items() if o is None])
    mh = vcomps.get("MetaHuman")
    res["metahuman_class"] = comp_props(mh).get("child_actor_class") if mh else None
    # capsule vs GASP's CMC character (the traversal checks' reference)
    ninja_cdo = unreal.get_default_object(EAL.load_blueprint_class("/Game/Ninja/Blueprints/BP_NinjaGasp"))
    gasp_cdo = unreal.get_default_object(EAL.load_blueprint_class("/Game/Blueprints/SandboxCharacter_CMC"))
    caps = {}
    for tag, cdo in (("ninja", ninja_cdo), ("gasp", gasp_cdo)):
        c = cdo.get_editor_property("capsule_component")
        caps[tag] = [round(c.get_unscaled_capsule_radius(), 3), round(c.get_unscaled_capsule_half_height(), 3)]
    res["capsule"] = caps
    arm = next((comps[n] for n in comps if comps[n] and comps[n].get_class().get_name() == "SpringArmComponent"), None)
    cams = {n: comp_props(o) for n, o in comps.items() if o and o.get_class().get_name() == "CameraComponent"}
    gcam = {n: comp_props(o) for n, o in comps.items() if o and "GameplayCamera" in o.get_class().get_name()}
    res["spring_arm"] = comp_props(arm) if arm else None
    res["cameras"] = cams
    res["gameplay_cameras"] = gcam
    arm_ok = bool(arm) and abs(arm.get_editor_property("target_arm_length") - 375) < 0.5 and \
        arm.get_editor_property("socket_offset").length() < 0.01
    cam_ok = any(v.get("auto_activate") is True for v in cams.values()) and \
        all(v.get("auto_activate") is False for v in gcam.values())
    res["camera_ok"] = arm_ok and cam_ok
    res["passed"] = (not res["unwanted_present"] and not res["null_class"] and res["jutsus"] is not None
                     and len(res["jutsus"]) == 4 and all(res["has_turn_runstyle"].values()) and res["visual_ok"]
                     and caps["ninja"] == caps["gasp"] and res["camera_ok"]
                     and (res["metahuman_class"] or "").endswith("BP_MH_PlayerDefault_C"))
    return res


def gate_gamemode():
    ini = (PROJ / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
    res = {"ini_global": "GlobalDefaultGameMode=/Game/Dojo/Blueprints/GM_DojoNinja.GM_DojoNinja_C" in ini,
           "ini_maps": "GameDefaultMap=/Game/Dojo/Maps/L_Dojo.L_Dojo" in ini,
           "ini_redirect": '+PackageRedirects=(OldName="/Script/DemoGame_1",NewName="/Script/DojoLab")' in ini}
    for tag, path in (("GM_DojoNinja", "/Game/Dojo/Blueprints/GM_DojoNinja"), ("GM_Dojo", "/Game/Dojo/Blueprints/GM_Dojo")):
        cls = EAL.load_blueprint_class(path)
        cdo = unreal.get_default_object(cls)
        p = cdo.get_editor_property("default_pawn_class")
        res[tag] = {"default_pawn": p.get_path_name() if p else None,
                    "controller": cdo.get_editor_property("player_controller_class").get_path_name()}
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    res["level_open"] = bool(les.load_level(LEVEL))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = world.get_world_settings()
    gm = ws.get_editor_property("default_game_mode")
    res["world_game_mode"] = gm.get_path_name() if gm else None
    starts = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart):
        l, r = a.get_actor_location(), a.get_actor_rotation()
        starts.append({"label": a.get_actor_label(), "tag": str(a.get_editor_property("player_start_tag")),
                       "loc": [round(l.x, 2), round(l.y, 2), round(l.z, 2)], "yaw": round(r.yaw, 2)})
    res["player_starts"] = sorted(starts, key=lambda s: s["label"])
    before = json.loads((OUT / "setup.json").read_text(encoding="utf-8")).get("player_starts", [])
    res["player_starts_unchanged"] = sorted(before, key=lambda s: s["label"]) == res["player_starts"]
    res["n_actors"] = len(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
    res["passed"] = (res["ini_global"] and res["ini_maps"] and res["ini_redirect"]
                     and res["GM_DojoNinja"]["default_pawn"].endswith("BP_NinjaGasp_C")
                     and res["GM_Dojo"]["default_pawn"].endswith("SandboxCharacter_CMC_C")
                     and (res["world_game_mode"] or "").endswith("GM_DojoNinja_C")
                     and len(starts) == 2 and res["player_starts_unchanged"])
    return res


def gate_input():
    imc = unreal.load_asset("/Game/Ninja/Input/IMC_NinjaGasp")
    rows = []
    for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings"):
        a = m.get_editor_property("action")
        rows.append([str(m.get_editor_property("key").get_editor_property("key_name")), a.get_name() if a else None])
    want = {"IA_Jutsu", "IA_Jutsu_GreatFireball", "IA_Jutsu_Summoning", "IA_Jutsu_Chidori"}
    return {"rows": rows, "passed": len(rows) == 8 and {r[1] for r in rows} == want}


def main():
    t0 = time.time()
    try:
        for name, fn in (("A_modules", gate_modules), ("B_packages", gate_packages), ("C_deps", gate_deps),
                         ("D_character", gate_character), ("E_gamemode", gate_gamemode), ("F_input", gate_input)):
            try:
                REP[name] = fn()
            except Exception:  # noqa: BLE001
                REP[name] = {"passed": False, "error": traceback.format_exc()[-2000:]}
            REP["gates"][name] = bool(REP[name].get("passed"))
            unreal.log(f"DJ_NINJA gate {name} passed={REP['gates'][name]}")
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
    REP["passed"] = len(REP["gates"]) == 6 and all(REP["gates"].values())
    REP["sec"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "check.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ninja_check passed={REP['passed']} gates={REP['gates']}")


main()
