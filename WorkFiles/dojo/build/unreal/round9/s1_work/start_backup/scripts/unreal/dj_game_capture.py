"""DojoLab ROUND 8 stills from a real -game frame (UnrealEditor-Cmd -game -RenderOffscreen, run by run_game_capture.ps1 as
`-ExecCmds="py <this file>"`). Unlike dj_sc_capture.py (SceneCapture2D in an offscreen editor), this renders the real
game viewport, so UE's VolumetricCloud (Ultra Dynamic Sky's volumetric clouds), Lumen at full surface-cache scale and
the real post chain all show (CINEMATIC_LOOK_RESEARCH.md 3.7).

Config: the JSON file named by env DJ_GAME_CAPTURE_CFG (a shot may add "out": file stem and "cmds": console
commands run before it):
  {"out_dir": abs dir, "report": abs json, "shots": [{"name": "CAM_Overview", "w": 1920, "h": 1080}, ...],
   "warm_s": 25, "warm_per_cam_s": 5, "settle_s": 10, "cvars": ["sg.ShadowQuality 3", ...], "hide_pawn": true,
   "shot_timeout_s": 60, "warm_pass": true}
Flow (one Slate post-tick state machine): wait for the game world's PlayerController -> console cvars -> hide the GASP
pawn -> a warm pass over every camera (shader compiles, Lumen, clouds) -> per camera: r.setres WxH, SetViewTarget,
settle, `HighResShot filename=<out>/<name> WxH`, wait for the PNG -> report -> quit.
Read-only for the project content: writes only the PNGs, the report and the log.
"""
import json
import os
import time
import traceback
from pathlib import Path

import unreal

CFG = json.loads(Path(os.environ["DJ_GAME_CAPTURE_CFG"]).read_text(encoding="utf-8"))
OUT = Path(CFG["out_dir"])
OUT.mkdir(parents=True, exist_ok=True)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "shots": {}, "events": [], "cfg": CFG}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "i": 0, "pc": None, "cams": {}, "handle": None,
      "shot_t": 0.0, "before": set()}


def log(msg):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {msg}")
    unreal.log(f"DJ_GAME_CAPTURE {msg}")


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


def finish(ok):
    REP["passed"] = ok
    REP["sec"] = round(time.time() - ST["t0"], 1)
    Path(CFG["report"]).write_text(json.dumps(REP, indent=1), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE game_capture passed={ok} shots={sum(1 for v in REP['shots'].values() if v.get('ok'))}"
               f"/{len(CFG['shots'])}")
    if ST["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def view(name, w, h):
    cam = ST["cams"].get(name)
    if cam is None:
        return False
    cmd(f"r.setres {w}x{h}w")
    ST["pc"].set_view_target_with_blend(cam, 0.0)
    return True


def sun_state():
    """The Ultra Dynamic Sky sun / sky light as rendered (probe record)."""
    import math
    for x in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor):
        if x.get_class().get_name() != "Ultra_Dynamic_Sky_C":
            continue
        out = {}
        for c in x.get_components_by_class(unreal.LightComponentBase):
            if c.get_name() in ("Sun", "Captured Scene Sky Light"):
                d = {"intensity": round(float(c.get_editor_property("intensity")), 4)}
                if c.get_name() == "Sun":
                    f = c.get_forward_vector()
                    d["elev_deg"] = round(math.degrees(math.asin(max(-1.0, min(1.0, -f.z)))), 2)
                    d["az_from_x_blender_deg"] = round(math.degrees(math.atan2(f.y, -f.x)), 2)
                    lc = c.get_editor_property("light_color")
                    d["color"] = [lc.r, lc.g, lc.b]
                out[c.get_name()] = d
        return out
    return None


def pngs():
    return {p.name for p in OUT.glob("*.png")}


def tick(_dt):
    try:
        now = time.time()
        el = now - ST["t"]
        ph = ST["phase"]
        shots = CFG["shots"]
        if ph == "wait_world":
            pc = find_pc()
            if pc is not None and el > 2.0:
                ST["pc"] = pc
                for a in unreal.GameplayStatics.get_all_actors_of_class(pc, unreal.CineCameraActor):
                    try:
                        ST["cams"][a.get_actor_label()] = a
                    except Exception:  # noqa: BLE001
                        ST["cams"][a.get_name()] = a
                REP["cameras_found"] = sorted(ST["cams"])
                REP["missing"] = [s["name"] for s in shots if s["name"] not in ST["cams"]]
                for c in CFG.get("cvars", []):
                    cmd(c)
                if CFG.get("hide_pawn", True):
                    pawn = pc.get_controlled_pawn()
                    if pawn is not None:
                        pawn.set_actor_hidden_in_game(True)
                        REP["pawn_hidden"] = pawn.get_name()
                    pc.set_ignore_move_input(True)
                    pc.set_ignore_look_input(True)
                log(f"world ready, {len(ST['cams'])} cameras, missing {REP['missing']}")
                ST["phase"], ST["t"], ST["i"] = "warm0", now, 0
            elif el > 180:
                log("no PlayerController after 180 s")
                finish(False)
        elif ph == "warm0":
            if el >= float(CFG.get("warm_s", 25)):
                ST["phase"], ST["t"], ST["i"] = ("warm" if CFG.get("warm_pass", True) else "aim"), now, 0
                if ST["phase"] == "warm" and shots:
                    view(shots[0]["name"], shots[0]["w"], shots[0]["h"])
        elif ph == "warm":
            if el >= float(CFG.get("warm_per_cam_s", 5)):
                ST["i"] += 1
                ST["t"] = now
                if ST["i"] >= len(shots):
                    ST["phase"], ST["i"] = "aim", 0
                else:
                    view(shots[ST["i"]]["name"], shots[ST["i"]]["w"], shots[ST["i"]]["h"])
        elif ph == "aim":
            if ST["i"] >= len(shots):
                finish(all(v.get("ok") for v in REP["shots"].values()) and not REP.get("missing"))
                return
            s = shots[ST["i"]]
            for c in s.get("cmds", []):   # per-shot console commands (e.g. an r.ExposureOffset sweep)
                cmd(c)
            if s.get("uds"):   # probe only: set Ultra Dynamic Sky variables at runtime (its tick re-reads them)
                uds = ST.get("uds")
                if uds is None:
                    for x in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor):
                        if x.get_class().get_name() == "Ultra_Dynamic_Sky_C":
                            uds = ST["uds"] = x
                for k, v in s["uds"].items():
                    try:
                        if isinstance(v, list):
                            v = unreal.LinearColor(*[float(x) for x in (v + [1.0])[:4]])
                        elif isinstance(v, dict) and "enum" in v:   # Blueprint enum: the value's own type (as dj_sc_level)
                            t = type(uds.get_editor_property(k))
                            REP.setdefault("enum_members", {})[k] = [m for m in dir(t) if m.isupper()]
                            v = getattr(t, v["enum"].split(".")[1])
                        uds.set_editor_property(k, v)
                    except Exception as exc:  # noqa: BLE001   (probe: record and go on)
                        REP.setdefault("uds_set_errors", {})[f"{s.get('out', s['name'])}:{k}"] = str(exc)[:160]
            if s.get("read"):   # probe only: record UDS variable values
                uds = ST.get("uds") or next(x for x in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor)
                                            if x.get_class().get_name() == "Ultra_Dynamic_Sky_C")
                ST["uds"] = uds
                vals = {}
                for k in s["read"]:
                    try:
                        vals[k] = str(uds.get_editor_property(k))[:300]
                    except Exception as exc:  # noqa: BLE001
                        vals[k] = "ERR " + str(exc)[:80]
                REP.setdefault("uds_read", {})[s.get("out", s["name"])] = vals
            if not view(s["name"], s["w"], s["h"]):
                REP["shots"][s.get("out", s["name"])] = {"ok": False, "why": "camera missing"}
                ST["i"] += 1
                return
            ST["phase"], ST["t"] = "settle", now
        elif ph == "settle":
            if el >= float(CFG.get("settle_s", 10)):
                s = shots[ST["i"]]
                ST["before"] = pngs()
                cmd(f"HighResShot filename={(OUT / s.get('out', s['name'])).as_posix()} {s['w']}x{s['h']}")
                ST["phase"], ST["t"], ST["shot_t"] = "wait_png", now, now
        elif ph == "wait_png":
            s = shots[ST["i"]]
            new = sorted(pngs() - ST["before"])
            if new and el > 1.5:
                p = OUT / new[0]
                size = p.stat().st_size
                if size > 0 and size == ST.get("last_size"):
                    want = OUT / (s.get("out", s["name"]) + ".png")
                    if p != want:
                        if want.exists():
                            want.unlink()
                        p.rename(want)
                    REP["shots"][s.get("out", s["name"])] = {"ok": True, "file": str(want), "w": s["w"], "h": s["h"],
                                                             "cmds": s.get("cmds", []), "uds": s.get("uds"),
                                                             "sun": sun_state(),
                                                             "t_s": round(ST["shot_t"] - ST["t0"], 1)}
                    log(f"shot {s.get('out', s['name'])} {s['w']}x{s['h']} ok")
                    ST["last_size"] = None
                    ST["i"] += 1
                    ST["phase"], ST["t"] = "aim", now
                else:
                    ST["last_size"] = size
            elif el > float(CFG.get("shot_timeout_s", 60)):
                REP["shots"][s.get("out", s["name"])] = {"ok": False, "why": "no png"}
                log(f"shot {s['name']} timed out")
                ST["i"] += 1
                ST["phase"], ST["t"] = "aim", now
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        finish(False)


ST["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
