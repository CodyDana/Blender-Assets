"""DojoLab ninja character port: -game smoke probe (UnrealEditor-Cmd -game -RenderOffscreen, run by run_ninja_probe.ps1 as
`-ExecCmds="py <this file>"`). Read-only for the project content: writes only PNGs, the report and the log.

Config: the JSON file named by env DJ_NINJA_PROBE_CFG:
  {"mode": "ninja" | "gasp", "out_dir": abs dir, "report": abs json, "warm_s": 120, "shots": true}
mode "ninja" (L_Dojo with its own world game mode, GM_DojoNinja):
  spawn record (pawn / game mode / camera cvar / active camera / centred view / MetaHuman body / cloak / grooms),
  then real keys through Enhanced Input (`Input.+key`): W run, LeftShift+W sprint (the ninja run clips), F shadow clone,
  Two great fireball, Three summoning, Four chidori; each step samples the jutsu state and counts the spawned effect
  actors, and a HighResShot of the gameplay view is taken at the readable moment.
mode "gasp" (L_Dojo?game=GM_Dojo): the reference route; records the pawn class and the camera cvar, then the sprint
  check (SPRINT_TIMELINE). mode "sprint": the sprint check on the ninja (after warm_s).
"""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

CFG = json.loads(Path(os.environ["DJ_NINJA_PROBE_CFG"]).read_text(encoding="utf-8"))
OUT = Path(CFG["out_dir"])
OUT.mkdir(parents=True, exist_ok=True)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "mode": CFG["mode"], "events": [], "samples": [],
       "shots": [], "cfg": CFG}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "pc": None, "pawn": None, "handle": None, "step": 0,
      "step_t": 0.0, "pass": 0}
CLASSES = {
    "BP_NinjaGasp_C": "/Game/Ninja/Blueprints/BP_NinjaGasp.BP_NinjaGasp_C",
    "BP_GreatFireball_C": "/Game/Ninja/Jutsu/BP_GreatFireball.BP_GreatFireball_C",
    "BP_SummoningSeal_C": "/Game/Ninja/Jutsu/BP_SummoningSeal.BP_SummoningSeal_C",
    "BP_ChidoriLightning_C": "/Game/Ninja/Jutsu/BP_ChidoriLightning.BP_ChidoriLightning_C",
}
LOADED = {}


def log(msg):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {msg}")
    unreal.log(f"DJ_NINJA_PROBE {msg}")


def cmd(c):
    unreal.SystemLibrary.execute_console_command(ST["pc"], c, ST["pc"])


def find_pc():
    for pc in unreal.ObjectIterator(unreal.PlayerController):
        try:
            if pc.get_name().startswith("Default__") or pc.get_world() is None:
                continue
            return pc
        except Exception:  # noqa: BLE001
            continue
    return None


def v3(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def count(name):
    cls = LOADED.get(name)
    if cls is None:
        return None
    return len(unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], cls))


def comp_of(actor, cls_name):
    for c in actor.get_components_by_class(unreal.ActorComponent):
        if c.get_class().get_name() == cls_name:
            return c
    return None


def camera_state():
    pawn, pc = ST["pawn"], ST["pc"]
    cm = pc.player_camera_manager
    cam_loc = cm.get_camera_location()
    rot = pc.get_control_rotation()
    yaw = math.radians(rot.yaw)
    right = unreal.Vector(-math.sin(yaw), math.cos(yaw), 0.0)
    fwd = unreal.Vector(math.cos(yaw), math.sin(yaw), 0.0)
    pl = pawn.get_actor_location()
    off = cam_loc - pl
    out = {"cvar_NewGameplayCameraSystem": unreal.SystemLibrary.get_console_variable_int_value(
               "DDCVar.NewGameplayCameraSystem.Enable"),
           "camera_loc": v3(cam_loc), "pawn_loc": v3(pl), "control_yaw": round(rot.yaw, 1),
           "lateral_cm": round(off.x * right.x + off.y * right.y, 1),
           "behind_cm": round(-(off.x * fwd.x + off.y * fwd.y), 1), "above_cm": round(off.z, 1),
           "fov": round(cm.get_fov_angle(), 2), "active": {}}
    for c in pawn.get_components_by_class(unreal.ActorComponent):
        n = c.get_class().get_name()
        if n in ("CameraComponent", "GameplayCameraComponent", "SpringArmComponent"):
            try:
                out["active"][c.get_name()] = bool(c.is_active())
            except Exception:  # noqa: BLE001
                pass
    return out


def visual_state():
    pawn = ST["pawn"]
    rec = {"pawn_components": sorted(f"{c.get_name()}:{c.get_class().get_name()}"
                                     for c in pawn.get_components_by_class(unreal.ActorComponent))}
    vis_actor = None
    for c in pawn.get_components_by_class(unreal.ChildActorComponent):
        a = c.get_editor_property("child_actor")
        rec.setdefault("child_actors", []).append(f"{c.get_name()}:{a.get_class().get_name() if a else None}")
        if a is not None and a.get_class().get_name().startswith("BP_NinjaVisual"):
            vis_actor = a
    if vis_actor is None:
        rec["visual"] = None
        return rec
    vb = comp_of(vis_actor, "NinjaVisualBodyComponent")
    rec["visual"] = vis_actor.get_class().get_name()
    if vb is None:
        rec["visual_body"] = None
        return rec
    body, host = vb.get_meta_human_body(), vb.get_host_mesh()
    rec["metahuman_active"] = bool(vb.is_meta_human_active())
    if body is not None:
        ai = body.get_anim_instance()
        rec["body"] = {"mesh": body.get_skeletal_mesh_asset().get_name() if body.get_skeletal_mesh_asset() else None,
                       "visible": bool(body.is_visible()), "anim": ai.get_class().get_name() if ai else None,
                       "owner": body.get_owner().get_class().get_name()}
        mh = body.get_owner()
        grooms = [c for c in mh.get_components_by_class(unreal.ActorComponent) if c.get_class().get_name() == "GroomComponent"]
        rec["grooms"] = []
        for g in grooms:
            try:
                ga = g.get_editor_property("groom_asset")
            except Exception:  # noqa: BLE001
                ga = None
            rec["grooms"].append({"name": g.get_name(), "visible": bool(g.is_visible()),
                                  "groom": ga.get_name() if ga else None})
        # the head bone of the visible body vs the hidden host (same pose, different skeleton proportions)
        try:
            rec["body_head_z"] = round(body.get_socket_location("head").z - ST["pawn"].get_actor_location().z, 1)
            rec["host_head_z"] = round(host.get_socket_location("head").z - ST["pawn"].get_actor_location().z, 1)
        except Exception:  # noqa: BLE001
            pass
    if host is not None:
        rec["host"] = {"mesh": host.get_skeletal_mesh_asset().get_name() if host.get_skeletal_mesh_asset() else None,
                       "visible": bool(host.is_visible())}
    garments = vb.get_meta_human_garments()
    rec["garments"] = []
    for g in garments or []:
        lp = g.get_editor_property("leader_pose_component")
        par = g.get_attach_parent()
        rec["garments"].append({"name": g.get_name(),
                                "mesh": g.get_skeletal_mesh_asset().get_name() if g.get_skeletal_mesh_asset() else None,
                                "visible": bool(g.is_visible()), "attach_parent": par.get_name() if par else None,
                                "leader": lp.get_name() if lp else None})
    return rec


def sample(tag):
    pawn = ST["pawn"]
    rec = {"tag": tag, "t": round(time.time() - ST["t0"], 2)}
    try:
        rec["speed"] = round(pawn.get_velocity().length(), 1)
        rec["loc"] = v3(pawn.get_actor_location())
        j = comp_of(pawn, "NinjaJutsuComponent")
        if j is not None:
            cj, fj = j.get_casting_jutsu(), j.get_finishing_jutsu()
            rec["casting"] = cj.get_name() if cj else None
            rec["finishing"] = fj.get_name() if fj else None
        rs = comp_of(pawn, "NinjaRunStyleComponent")
        if rs is not None:
            rec["run_style"] = bool(rs.is_run_style_active())
        for n in CLASSES:
            rec[n] = count(n)
    except Exception as exc:  # noqa: BLE001
        rec["error"] = str(exc)[:200]
    REP["samples"].append(rec)
    return rec


def shot(name):
    if not CFG.get("shots", True):
        return
    p = (OUT / name).as_posix()
    cmd(f"HighResShot filename={p} 1920x1080")
    REP["shots"].append(name)
    log(f"shot {name}")


# The ninja timeline: (seconds after the previous step, action). Key names are FKey names. It runs twice: pass 0 warms
# every shader / Niagara system the steps touch (no shots), pass 1 samples and shoots.
def k(press, key):
    return lambda: cmd(f"Input.{'+' if press else '-'}key {key}")


def turn(delta_yaw, pitch=None):
    def fn():
        r = ST["pc"].get_control_rotation()
        ST["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch if pitch is None else pitch,
                                                     yaw=r.yaw + delta_yaw))
    return fn


def arm(length):
    def fn():
        for c in ST["pawn"].get_components_by_class(unreal.SpringArmComponent):
            c.target_arm_length = float(length)   # attribute write: no PostEditChange, no construction-script re-run
    return fn


def S(tag):
    return lambda: sample(f"p{ST['pass']}:{tag}")


def H(name):
    return lambda: shot(name) if ST["pass"] == 1 else None


TIMELINE = [
    (0.0, S("idle")),
    (0.0, H("01_idle_back")),
    (0.5, turn(180.0, -8.0)),
    (2.0, H("02_idle_front")),
    (0.2, arm(200)),
    (2.0, H("03_front_close")),
    (0.2, lambda: camera_rec("front_close")),
    (0.0, arm(375)),
    (0.0, turn(180.0, -10.0)),
    (2.0, S("ready")),
    # W = run (the ninja run clip), then LeftShift+W = sprint (the ninja sprint clip); out and back
    (0.0, k(True, "W")),
    (1.3, S("run_1.3s")),
    (0.0, H("04_run")),
    (0.2, k(True, "LeftShift")),
    (0.9, S("sprint_0.9s")),
    (0.0, H("05_sprint")),
    (0.1, k(False, "LeftShift")),
    (0.0, k(False, "W")),
    (2.0, S("stopped_out")),
    (0.0, turn(180.0)),
    (0.3, k(True, "W")),
    (1.5, k(True, "LeftShift")),
    (1.0, k(False, "LeftShift")),
    (0.0, k(False, "W")),
    (2.0, turn(180.0)),
    (1.5, S("back")),
    # F = shadow clone (Ram, Snake, Tiger)
    (0.0, k(True, "F")),
    (0.15, k(False, "F")),
    (0.25, S("F_0.4s")),
    (0.0, H("06_seal_F")),
    (2.0, S("F_2.4s")),
    (0.6, H("07_clone")),
    (0.1, S("F_3.1s")),
    (6.0, S("F_9s")),
    # Two = great fireball (6 seals)
    (0.0, k(True, "Two")),
    (0.15, k(False, "Two")),
    (0.6, S("2_0.75s")),
    (0.0, H("08_seal_2")),
    (0.9, S("2_1.65s")),
    (0.3, S("2_1.95s")),
    (0.0, H("09_fireball")),
    (0.6, S("2_2.55s")),
    (4.0, S("2_6.5s")),
    # Three = summoning (thumb bite + 5 seals + palm slam)
    (0.0, k(True, "Three")),
    (0.15, k(False, "Three")),
    (0.8, S("3_0.95s")),
    (0.0, H("10_seal_3")),
    (1.5, S("3_2.45s")),
    (0.6, S("3_3.05s")),
    (1.0, S("3_4.05s")),
    (0.0, H("11_summoning_seal")),
    (5.0, S("3_9s")),
    # Four = chidori (3 seals, then the 4 s charge stance with the lightning on hand_r)
    (0.0, k(True, "Four")),
    (0.15, k(False, "Four")),
    (0.4, S("4_0.55s")),
    (1.0, S("4_1.55s")),
    (0.5, S("4_2.05s")),
    (0.0, H("12_chidori")),
    (1.5, S("4_3.55s")),
    (4.0, S("4_7.5s")),
]


SPRINT_TIMELINE = [
    (0.0, S("sprint_idle")),
    (0.0, k(True, "LeftShift")),
    (0.1, k(True, "W")),
    (1.5, S("shift_first_1.5s")),
    (0.0, k(False, "W")),
    (0.0, k(False, "LeftShift")),
    (2.5, turn(180.0)),
    (0.3, k(True, "W")),
    (1.0, S("w_only_1.0s")),
    (0.0, k(True, "LeftShift")),
    (1.0, S("w_then_shift_1.0s")),
    (0.0, k(False, "LeftShift")),
    (0.0, k(False, "W")),
    (2.0, S("stopped")),
]


def camera_rec(tag):
    REP.setdefault("camera_samples", {})[f"p{ST['pass']}:{tag}"] = camera_state()


def finish(ok):
    REP["passed"] = ok
    REP["sec"] = round(time.time() - ST["t0"], 1)
    Path(CFG["report"]).write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ninja_probe passed={ok}")
    if ST["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def tick(_dt):
    try:
        now = time.time()
        el = now - ST["t"]
        ph = ST["phase"]
        if ph == "wait_world":
            pc = find_pc()
            pawn = pc.get_controlled_pawn() if pc is not None else None
            if pc is not None and pawn is not None and el > 2.0:
                ST["pc"], ST["pawn"] = pc, pawn
                gm = unreal.GameplayStatics.get_game_mode(pc)
                REP["spawn"] = {"pawn_class": pawn.get_class().get_path_name(),
                                "game_mode": gm.get_class().get_path_name() if gm else None,
                                "controller": pc.get_class().get_path_name(),
                                "map": unreal.GameplayStatics.get_current_level_name(pc)}
                for n, p in CLASSES.items():
                    LOADED[n] = unreal.load_class(None, p)
                REP["camera_at_spawn"] = camera_state()
                log(f"world ready, pawn {REP['spawn']['pawn_class']} gm {REP['spawn']['game_mode']}")
                if CFG["mode"] == "gasp":
                    ST["phase"], ST["t"] = "gasp_wait", now
                elif CFG["mode"] == "sprint":
                    REP["visual_at_spawn"] = visual_state()
                    cmd("ninja.run.debug 1")
                    ST["phase"], ST["t"] = "warm", now
                else:
                    REP["visual_at_spawn"] = visual_state()
                    cmd("ninja.run.debug 1")
                    ST["phase"], ST["t"] = "warm", now
            elif el > 240:
                log("no PlayerController / pawn after 240 s")
                finish(False)
        elif ph == "gasp_wait":
            if el >= 5.0:
                REP["camera_after_5s"] = camera_state()
                ST["pass"] = 1
                ST["phase"], ST["t"], ST["step"], ST["step_t"] = "run", now, 0, now
        elif ph == "warm":
            if el >= float(CFG.get("warm_s", 120)):
                REP["camera_after_warm"] = camera_state()
                REP["visual_after_warm"] = visual_state()
                ST["phase"], ST["t"], ST["step"], ST["step_t"] = "run", now, 0, now
        elif ph == "run":
            tl = TIMELINE if CFG["mode"] == "ninja" else SPRINT_TIMELINE
            if CFG["mode"] != "ninja":
                ST["pass"] = 1
            while ST["step"] < len(tl):
                wait, fn = tl[ST["step"]]
                if now - ST["step_t"] < wait:
                    return
                fn()
                ST["step"] += 1
                ST["step_t"] = now
            if ST["pass"] == 0:
                log("pass 0 (warm) done")
                ST["pass"], ST["phase"], ST["t"] = 1, "between", now
                return
            REP["camera_end"] = camera_state()
            finish(True)
        elif ph == "between":
            if el >= float(CFG.get("between_s", 45)):
                REP["visual_pass1"] = visual_state()
                ST["phase"], ST["t"], ST["step"], ST["step_t"] = "run", now, 0, now
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        log("ERROR " + REP["error"][-300:])
        finish(False)


ST["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
