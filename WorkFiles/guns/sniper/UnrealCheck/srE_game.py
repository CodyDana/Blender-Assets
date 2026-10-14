"""SR01 W5, pass E (a fresh UnrealEditor-Cmd -game -RenderOffscreen playing <dest>/L_SR01_Check, built by pass A2;
run as -ExecCmds="py srE_game.py" by run_game_ue.ps1 (SMG copy)). Nothing is imported or saved; writes srE_game.json and
renders/e_*.png. One Slate post-tick state machine:

  U7  physics: every SM_PHYS_* actor (SM_SR01 level and rolled 70 deg, SM_SR01_Mag, SK_SR01 with PHYS_SR01, and a
      second SK_SR01 holding the StockFold clip's last frame) was placed
      1 m up with Simulate Physics; each one's world transform, bounds and speed are sampled every tick for 8 s
      (srE_physics_samples.json, with each component's runtime bounds and the SKs' Shoulder socket): it rests (speed < 1 cm/s over the last second); the analysis places the read-back
      LOD0 at every sampled transform for the lowest vertex against the ground top (z = 0): no tunnelling;
  U12 texture residency: texture streaming on (the default), the view on CAM_Hip then CAM_ADS (the texture-area gun, not
      simulating) for 8 s each, then ListStreamingTextures into the log between SM_STREAM markers (parsed by
      srF_summary.py) and a HighResShot.
"""
import json
import math
import time
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).resolve().parent
OUT = HERE / "srE_game.json"
RDIR = HERE / "renders"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "events": []}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "pc": None, "handle": None, "samples": [], "before": set()}


def log(msg):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {msg}")
    unreal.log(f"SM_GAME {msg}")


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
    unreal.log(f"SM_GAME_DONE ok={ok}")
    if ST["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def support_traces():
    """What each dropped actor rests on: vertical line traces (visibility and the physics-body object types) from 2 m
    above to 0.5 m below the ground on a 5 x 5 grid over its final bounds; every hit actor / component is listed."""
    out = {}
    for k, a in ST["phys"].items():
        c = comp_of(a)
        o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
        hits = {}
        for i in range(5):
            for j in range(5):
                x = o.x - e.x + 2 * e.x * i / 4.0
                y = o.y - e.y + 2 * e.y * j / 4.0
                for tt in (unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, unreal.TraceTypeQuery.TRACE_TYPE_QUERY2):
                    r = unreal.SystemLibrary.line_trace_multi(ST["pc"], unreal.Vector(x, y, 200.0), unreal.Vector(x, y, -50.0), tt,
                                                              False, [], unreal.DrawDebugTrace.NONE, True)
                    parts = list(r) if isinstance(r, tuple) else [r]
                    hl = []
                    for part in parts:
                        try:
                            hl += [h for h in part if isinstance(h, unreal.HitResult)]
                        except TypeError:
                            pass
                    REP.setdefault("trace_return_type", str(type(r)))
                    for h in hl or []:
                        t_ = h.to_tuple()
                        ha = next((v for v in t_ if isinstance(v, unreal.Actor)), None)
                        hc = next((v for v in t_ if isinstance(v, unreal.PrimitiveComponent)), None)
                        loc = next((v for v in t_ if isinstance(v, unreal.Vector)), None)
                        key = f"{(str(ha.get_name()) + str([str(t) for t in ha.tags])) if ha else None}/{hc.get_name() if hc else None}"
                        hits.setdefault(key, []).append(round(loc.z, 2) if loc else None)
        out[k] = {kk: [min(v), max(v), len(v)] for kk, v in hits.items()}
    return out


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
                  "speed": round(math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z), 4) if not isinstance(v, dict) else None,
                  # the component's runtime bounds (world AABB) and, on the SKs, the stock's Shoulder socket (the fold check)
                  "bounds": [o.x, o.y, o.z, e.x, e.y, e.z, r]}
        if isinstance(c, unreal.SkeletalMeshComponent):
            sh = c.get_socket_transform("Shoulder", unreal.RelativeTransformSpace.RTS_WORLD)
            cw = c.get_world_transform()
            row[k]["shoulder"] = [sh.translation.x, sh.translation.y, sh.translation.z, sh.rotation.x, sh.rotation.y, sh.rotation.z, sh.rotation.w]
            row[k]["component"] = [cw.translation.x, cw.translation.y, cw.translation.z, cw.rotation.x, cw.rotation.y, cw.rotation.z, cw.rotation.w]
            row[k]["fixed_skel_bounds"] = bool(safe(lambda c=c: c.get_editor_property("component_use_fixed_skel_bounds")) is True)
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
                ST["phys"] = tagged("SM_PHYS_")
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
                (HERE / "srE_physics_samples.json").write_text(json.dumps(ST["samples"]), encoding="utf-8")
                REP["physics_samples_file"] = "srE_physics_samples.json"
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
                REP["U7_support"] = safe(support_traces)
                log("physics done")
                dump()
                view("CAM_Hip")
                ST["phase"], ST["t"] = "hip_wait", now
        elif ph == "hip_wait":
            if el > 8.0:
                unreal.log("SM_STREAM_BEGIN hip")
                cmd("ListStreamingTextures")
                unreal.log("SM_STREAM_END hip")
                shot("e_u12_hip")
                ST["phase"], ST["t"] = "hip_shot", now
        elif ph == "hip_shot":
            if (el > 1.5 and shot_done()) or el > 60:
                view("CAM_ADS")
                ST["phase"], ST["t"] = "ads_wait", now
        elif ph == "ads_wait":
            if el > 8.0:
                unreal.log("SM_STREAM_BEGIN ads")
                cmd("ListStreamingTextures")
                unreal.log("SM_STREAM_END ads")
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
