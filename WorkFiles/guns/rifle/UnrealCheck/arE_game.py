"""AR-01 stage 8, pass E (a fresh UnrealEditor-Cmd -game -RenderOffscreen playing <dest>/L_AR01_Check, built by pass A2;
run as -ExecCmds="py arE_game.py" by run_game_ue.ps1). Nothing is imported or saved; writes arE_game.json and
renders/e_*.png. One Slate post-tick state machine:

  U7  physics: every AR_PHYS_* actor (SM_AR01 level and rolled 70 deg, SM_AR01_Mag, SK_AR01 with PHYS_AR01) was placed
      1 m up with Simulate Physics; each one's world transform, bounds and speed are sampled every tick for 8 s
      (arE_physics_samples.json): it rests (speed < 1 cm/s over the last second); the analysis places the read-back
      LOD0 at every sampled transform for the lowest vertex against the ground top (z = 0): no tunnelling;
  U12 texture residency: texture streaming on (the default), the view on CAM_Hip then CAM_ADS (the texture-area gun, not
      simulating) for 8 s each, then ListStreamingTextures into the log between AR_STREAM markers (parsed by
      arF_summary.py) and a HighResShot.
"""
import json
import math
import time
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).resolve().parent
OUT = HERE / "arE_game.json"
RDIR = HERE / "renders"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "events": []}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "pc": None, "handle": None, "samples": [], "before": set()}


def log(msg):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {msg}")
    unreal.log(f"AR_GAME {msg}")


def dump():
    OUT.write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")


def cmd(c):
    unreal.SystemLibrary.execute_console_command(ST["pc"], c, ST["pc"])


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def find_pc():
    for pc in unreal.ObjectIterator(unreal.PlayerController):
        try:
            if pc.get_name().startswith("Default__") or pc.get_world() is None:
                continue
            return pc
        except Exception:  # noqa: BLE001
            continue
    return None


def finish(ok):
    REP["passed_script"] = ok
    REP["sec"] = round(time.time() - ST["t0"], 1)
    dump()
    unreal.log(f"AR_GAME_DONE ok={ok}")
    if ST["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def tagged(prefix):
    out = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor):
        for t in a.get_editor_property("tags"):
            if str(t).startswith(prefix):
                out[str(t)] = a
    return out


def comp_of(a):
    for k in ("static_mesh_component", "skeletal_mesh_component"):
        c = safe(lambda k=k: a.get_editor_property(k))
        if c is not None and not isinstance(c, dict):
            return c
    return None


def v3(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


def sample(now):
    row = {"t": round(now - ST["tphys"], 3)}
    for k, a in ST["phys"].items():
        c = comp_of(a)
        o, e, r = unreal.SystemLibrary.get_component_bounds(c)
        v = safe(lambda c=c: c.get_physics_linear_velocity())
        # a simulating skeletal mesh moves its body, not necessarily its component: take the 'body' bone (world)
        tr = (c.get_socket_transform("body", unreal.RelativeTransformSpace.RTS_WORLD)
              if isinstance(c, unreal.SkeletalMeshComponent) else c.get_world_transform())
        q = tr.rotation
        row[k] = {"lowest_z": round(o.z - e.z, 4), "centre": v3(o), "simulating": bool(safe(lambda c=c: c.is_simulating_physics())),
                  "xform": [tr.translation.x, tr.translation.y, tr.translation.z, q.x, q.y, q.z, q.w],
                  "speed": round(math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z), 4) if not isinstance(v, dict) else None}
    ST["samples"].append(row)


def pngs():
    return {p.name for p in RDIR.glob("*.png")}


def shot(name):
    ST["before"] = pngs()
    ST["shot_name"] = name
    ST["last_size"] = None
    cmd(f"HighResShot filename={(RDIR / name).as_posix()} 1280x720")


def shot_done():
    new = sorted(pngs() - ST["before"])
    if not new:
        return False
    p = RDIR / new[0]
    size = p.stat().st_size
    if size > 0 and size == ST.get("last_size"):
        want = RDIR / (ST["shot_name"] + ".png")
        if p != want:
            if want.exists():
                want.unlink()
            p.rename(want)
        REP.setdefault("shots", []).append(want.name)
        return True
    ST["last_size"] = size
    return False


def view(name):
    cam = ST["cams"].get(name)
    if cam is None:
        return False
    ST["pc"].set_view_target_with_blend(cam, 0.0)
    return True


def tick(_dt):
    try:
        now = time.time()
        el = now - ST["t"]
        ph = ST["phase"]
        if ph == "wait_world":
            pc = find_pc()
            if pc is not None:
                ST["pc"] = pc
                ST["phys"] = tagged("AR_PHYS_")
                ST["cams"] = tagged("CAM_")
                ST["tphys"] = now
                REP["phys_actors"] = sorted(ST["phys"])
                REP["cameras"] = sorted(ST["cams"])
                REP["streaming_cvar"] = safe(lambda: unreal.SystemLibrary.get_console_variable_int_value("r.TextureStreaming"))
                REP["vsm_cvar"] = safe(lambda: unreal.SystemLibrary.get_console_variable_int_value("r.Shadow.Virtual.Enable"))
                log("world ready")
                ST["phase"], ST["t"] = "physics", now
            elif el > 180:
                log("no PlayerController after 180 s")
                finish(False)
        elif ph == "physics":
            sample(now)
            if el > 8.0:
                (HERE / "arE_physics_samples.json").write_text(json.dumps(ST["samples"]), encoding="utf-8")
                REP["physics_samples_file"] = "arE_physics_samples.json"
                last = [s for s in ST["samples"] if s["t"] >= ST["samples"][-1]["t"] - 1.0]
                res = {}
                for k in ST["phys"]:
                    lows = [s[k]["lowest_z"] for s in ST["samples"]]
                    speeds = [s[k]["speed"] for s in last if s[k]["speed"] is not None]
                    res[k] = {"start_lowest_z_cm": lows[0], "min_lowest_z_cm": min(lows), "final_lowest_z_cm": lows[-1],
                              "fell_cm": round(lows[0] - lows[-1], 3), "max_speed_last_1s_cm_s": max(speeds) if speeds else None,
                              "simulating": ST["samples"][-1][k]["simulating"], "final_centre": ST["samples"][-1][k]["centre"]}
                REP["U7"] = res
                REP["U7_ticks"] = len(ST["samples"])
                log("physics done")
                dump()
                view("CAM_Hip")
                ST["phase"], ST["t"] = "hip_wait", now
        elif ph == "hip_wait":
            if el > 8.0:
                unreal.log("AR_STREAM_BEGIN hip")
                cmd("ListStreamingTextures")
                unreal.log("AR_STREAM_END hip")
                shot("e_u12_hip")
                ST["phase"], ST["t"] = "hip_shot", now
        elif ph == "hip_shot":
            if (el > 1.5 and shot_done()) or el > 60:
                view("CAM_ADS")
                ST["phase"], ST["t"] = "ads_wait", now
        elif ph == "ads_wait":
            if el > 8.0:
                unreal.log("AR_STREAM_BEGIN ads")
                cmd("ListStreamingTextures")
                unreal.log("AR_STREAM_END ads")
                shot("e_u12_ads")
                ST["phase"], ST["t"] = "ads_shot", now
        elif ph == "ads_shot":
            if (el > 1.5 and shot_done()) or el > 60:
                finish(True)
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        finish(False)


ST["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
