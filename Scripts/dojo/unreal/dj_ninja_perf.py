"""DojoLab ninja character port: frame time in -game with the player pawn IN VIEW (run by run_ninja_playtest.ps1
-Script dj_ninja_perf.py, config env DJ_PT_CFG). Method = the hall + armory finish stage's fp_game_perf.py (perf_cool:
`scalability 3`, t.MaxFPS 0, no vsync, 1920x1080 at the configured screen percentage r.ScreenPercentage 0, every
frame's delta from the Slate post-tick over a fixed sample window after a settle, no ProfileGPU), plus: before each camera
view the controlled pawn (the ninja under GM_DojoNinja, SandboxCharacter_CMC under ?game=GM_Dojo) is teleported onto the
floor DIST cm in front of the camera, facing it, so the character's own cost (MetaHuman, grooms, cloak cloth, the
retarget) is in the frame. View "PAWN" = the pawn's own gameplay camera where it spawned. Read-only for the project.

Config: {"out": abs json, "views": ["CAM_PlayerEyeSand", "CAM_AK_CW_WestAisle", "PAWN"], "rounds": 2, "warm_s": 60,
         "sample_s": 10, "settle_s": 8, "dist": {"CAM_PlayerEyeSand": 450, "CAM_AK_CW_WestAisle": 350}}
"""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

CFG = json.loads(Path(os.environ["DJ_PT_CFG"]).read_text(encoding="utf-8"))
OUT = Path(CFG["out"])
V = unreal.Vector
CVARS = ["scalability 3", "t.MaxFPS 0", "r.VSync 0", "r.ScreenPercentage 0", "r.setres 1920x1080w"]
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "segments": [], "events": [], "cfg": CFG, "placements": {}}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "i": 0, "pc": None, "cams": {}, "handle": None,
      "dts": [], "home": None}
PLAN = [v for _ in range(int(CFG.get("rounds", 2))) for v in CFG["views"]]


def log(m):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {m}")
    unreal.log(f"DJ_NPERF {m}")


def cmd(c):
    unreal.SystemLibrary.execute_console_command(ST["pc"], c, ST["pc"])


def cv(name):
    try:
        return unreal.SystemLibrary.get_console_variable_float_value(name)
    except Exception:  # noqa: BLE001
        return None


def find_pc():
    for pc in unreal.ObjectIterator(unreal.PlayerController):
        try:
            if pc.get_name().startswith("Default__") or pc.get_world() is None:
                continue
            return pc
        except Exception:  # noqa: BLE001
            continue
    return None


def hit_tuple(h):
    t = h.to_tuple() if h else None
    if not t or not t[0]:
        return None
    return t


def place_pawn(cam_name):
    """the pawn on the floor DIST cm in front of the camera (horizontal), facing it; first spot where the capsule fits"""
    p = ST["pc"].get_controlled_pawn()
    cam = ST["cams"][cam_name]
    cl = cam.get_actor_location()
    f = cam.get_actor_forward_vector()
    fl = math.hypot(f.x, f.y) or 1.0
    fx, fy = f.x / fl, f.y / fl
    cap = p.get_component_by_class(unreal.CapsuleComponent)
    r, hh = cap.get_scaled_capsule_radius(), cap.get_scaled_capsule_half_height()
    base = float(CFG.get("dist", {}).get(cam_name, 450.0))
    tried = []
    for d in (base, base - 75, base + 75, base - 150, base + 150, base + 250):
        x, y = cl.x + fx * d, cl.y + fy * d
        h = hit_tuple(unreal.SystemLibrary.line_trace_single_by_profile(
            p, V(x, y, cl.z + 50.0), V(x, y, cl.z - 1500.0), "Pawn", False, [p], unreal.DrawDebugTrace.NONE, True))
        if h is None:
            tried.append([d, "no floor"])
            continue
        fz = h[4].z
        c = V(x, y, fz + hh + 2.0)
        blk = hit_tuple(unreal.SystemLibrary.capsule_trace_single_by_profile(
            p, c, V(c.x + 0.1, c.y, c.z), r, hh, "Pawn", False, [p], unreal.DrawDebugTrace.NONE, True))
        if blk is not None:
            tried.append([d, "blocked"])
            continue
        yaw = math.degrees(math.atan2(-fy, -fx))
        try:
            p.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
        except Exception:  # noqa: BLE001
            pass
        p.set_actor_location_and_rotation(c, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False, True)
        REP["placements"][cam_name] = {"dist_cm": d, "loc": [round(c.x, 1), round(c.y, 1), round(fz, 1)],
                                       "yaw": round(yaw, 1), "tried": tried}
        return True
    REP["placements"][cam_name] = {"failed": tried}
    return False


def view(name):
    if name == "PAWN":
        p = ST["pc"].get_controlled_pawn()
        loc, rot = ST["home"]
        p.set_actor_location_and_rotation(loc, rot, False, True)
        ST["pc"].set_control_rotation(rot)
        ST["pc"].set_view_target_with_blend(p, 0.0)
        return True
    if name not in ST["cams"]:
        return False
    place_pawn(name)
    ST["pc"].set_view_target_with_blend(ST["cams"][name], 0.0)
    return True


def stats(d):
    d = sorted(d)
    n = len(d)
    if not n:
        return None
    return {"n": n, "mean_ms": round(1000 * sum(d) / n, 3), "median_ms": round(1000 * d[n // 2], 3),
            "p95_ms": round(1000 * d[min(n - 1, int(0.95 * n))], 3), "p99_ms": round(1000 * d[min(n - 1, int(0.99 * n))], 3),
            "max_ms": round(1000 * d[-1], 3), "fps_mean": round(n / sum(d), 2)}


def finish(ok):
    REP["passed_run"] = ok
    REP["sec"] = round(time.time() - ST["t0"], 1)
    OUT.write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_NPERF_DONE ok={ok} segments={len(REP['segments'])}")
    if ST["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def tick(dt):
    try:
        now = time.time()
        el = now - ST["t"]
        ph = ST["phase"]
        if ph == "wait_world":
            pc = find_pc()
            p = pc.get_controlled_pawn() if pc is not None else None
            if pc is not None and p is not None and el > 2.0:
                ST["pc"] = pc
                ST["home"] = (p.get_actor_location(), p.get_actor_rotation())
                for a in unreal.GameplayStatics.get_all_actors_of_class(pc, unreal.CineCameraActor):
                    ST["cams"][a.get_actor_label()] = a
                REP["pawn"] = p.get_class().get_path_name()
                REP["missing_cams"] = [v for v in CFG["views"] if v != "PAWN" and v not in ST["cams"]]
                for c in CVARS:
                    cmd(c)
                REP["cvars_after"] = {k: cv(k) for k in ("r.ScreenPercentage", "sg.ResolutionQuality",
                                                         "r.ScreenPercentage.Default", "r.AntiAliasingMethod")}
                pc.set_ignore_move_input(True)
                pc.set_ignore_look_input(True)
                log(f"world ready pawn {REP['pawn']} cams {len(ST['cams'])} missing {REP['missing_cams']}")
                ST["phase"], ST["t"] = "warm0", now
            elif el > 300:
                finish(False)
        elif ph == "warm0":
            if el >= float(CFG.get("warm_s", 60)):
                ST["phase"], ST["t"], ST["i"] = "warm", now, 0
                view(CFG["views"][0])
        elif ph == "warm":
            if el >= 6.0:
                ST["i"] += 1
                ST["t"] = now
                if ST["i"] >= len(CFG["views"]):
                    ST["phase"], ST["i"] = "aim", 0
                else:
                    view(CFG["views"][ST["i"]])
        elif ph == "aim":
            if ST["i"] >= len(PLAN):
                finish(True)
                return
            ok = view(PLAN[ST["i"]])
            log(f"segment {ST['i']} {PLAN[ST['i']]} view_ok={ok}")
            ST["phase"], ST["t"] = "settle", now
        elif ph == "settle":
            if el >= float(CFG.get("settle_s", 8)):
                ST["dts"] = []
                ST["phase"], ST["t"] = "sample", now
                ST["seg_t0"] = now
        elif ph == "sample":
            ST["dts"].append(float(dt))
            if el >= float(CFG.get("sample_s", 10)):
                v = PLAN[ST["i"]]
                p = ST["pc"].get_controlled_pawn()
                seg = {"i": ST["i"], "view": v, "res": [1920, 1080], "screen_pct": 0,
                       "cvar_screen_pct": cv("r.ScreenPercentage"), "wall_s": round(now - ST["seg_t0"], 2),
                       "frames": stats(ST["dts"][2:]), "t_s": round(now - ST["t0"], 1),
                       "pawn_loc": [round(p.get_actor_location().x, 1), round(p.get_actor_location().y, 1),
                                    round(p.get_actor_location().z, 1)]}
                REP["segments"].append(seg)
                log(f"SAMPLE_END {ST['i']} {v} {seg['frames']}")
                ST["i"] += 1
                ST["phase"], ST["t"] = "aim", now
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        finish(False)


ST["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
