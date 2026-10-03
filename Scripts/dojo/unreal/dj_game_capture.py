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


# ---- round 9 probe-only options (per shot; runtime overrides of the loaded level, nothing is saved) -------------------
def _actors(cls=unreal.Actor):
    return unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], cls)


def _label(a):
    try:
        return a.get_actor_label()
    except Exception:  # noqa: BLE001
        return a.get_name()


def probe_mat(spec):
    """{"<MI name>": {"s": {param: value}, "s_mul": {param: x}, "v": {param: [r, g, b]}}}: every mesh slot that uses the
    MI gets a MaterialInstanceDynamic (made once, reused); s_mul multiplies the MI's own value."""
    if "mids" not in ST:
        ST["mids"] = {}
        for a in _actors():
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                try:
                    n = c.get_num_materials()
                except Exception:  # noqa: BLE001
                    continue
                for i in range(n):
                    m = c.get_material(i)
                    if m is not None:
                        ST["mids"].setdefault(m.get_name(), []).append([c, i, m, None])
    rec = {}
    for name, sp in spec.items():
        mname, _, owner = name.partition("@")   # "MI@actor label prefix": only those actors' slots
        rows = [r for r in ST["mids"].get(mname, []) if not owner or _label(r[0].get_owner()).startswith(owner)]
        for row in rows:
            c, i, mi, mid = row
            if mid is None:
                mid = row[3] = c.create_dynamic_material_instance(i, mi)
            for k, v in sp.get("s", {}).items():
                mid.set_scalar_parameter_value(k, float(v))
            for k, x in sp.get("s_mul", {}).items():
                mid.set_scalar_parameter_value(k, float(mi.get_scalar_parameter_value(k)) * float(x))
            for k, v in sp.get("v", {}).items():
                mid.set_vector_parameter_value(k, unreal.LinearColor(*[float(t) for t in (list(v) + [1.0])[:4]]))
        rec[name] = len(rows)
    return rec


def probe_lamps(spec):
    """{"<label prefix>": {"mult": x (on the level value), "radius_cm": r, "kelvin": k}} (point, spot and rect lights)"""
    if "lamps" not in ST:
        ST["lamps"] = []
        for cls in (unreal.PointLight, unreal.SpotLight, unreal.RectLight):   # fix round 2026-10-01: every local light
            for a in _actors(cls):
                c = a.get_component_by_class(unreal.LocalLightComponent)
                if c is None:
                    continue
                ST["lamps"].append([_label(a), c, float(c.get_editor_property("intensity")),
                                    float(c.get_editor_property("attenuation_radius"))])
    rec = {}
    for pre, sp in spec.items():
        n = 0
        for lab, c, i0, r0 in ST["lamps"]:
            if not lab.startswith(pre):
                continue
            c.set_intensity(i0 * float(sp.get("mult", 1.0)))
            c.set_attenuation_radius(float(sp.get("radius_cm", r0)))
            if "kelvin" in sp:
                c.set_temperature(float(sp["kelvin"]))
            n += 1
        rec[pre] = n
    return rec


def probe_pp(spec):
    """{"<PostProcessSettings field>": value} on the level's PostProcess_Dojo (override flag set); fix round: the key
    "__label" picks another volume by label (e.g. "PostProcess_ArmoryHall", the bounded interior PPV)."""
    spec = dict(spec)
    want = spec.pop("__label", "PostProcess_Dojo")
    ppv = next((a for a in _actors(unreal.PostProcessVolume) if _label(a) == want), None)
    if ppv is None:
        return "no " + want
    s = ppv.get_editor_property("settings")
    for k, v in spec.items():
        if isinstance(v, list):
            v = unreal.Vector4(*[float(t) for t in v]) if len(v) == 4 else unreal.LinearColor(*[float(t) for t in v], 1.0)
        elif isinstance(v, dict) and "enum" in v:
            cls, mem = v["enum"].split(".")
            v = getattr(getattr(unreal, cls), mem)
        try:
            s.set_editor_property("override_" + k, True)
        except Exception:  # noqa: BLE001
            pass
        s.set_editor_property(k, v)
    ppv.set_editor_property("settings", s)
    return sorted(spec)


def probe_pose(cam, sp):
    """voices_paper stage: {"loc_cm": [x, y, z], "rot": [pitch, yaw], "fov": horizontal deg} moves the named
    CineCameraActor at runtime (probe only, nothing is saved): views of the upper windows no level camera has."""
    rec = {}
    try:
        root = cam.get_editor_property("root_component")
        root.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    except Exception as exc:  # noqa: BLE001
        rec["mobility_err"] = str(exc)[:120]
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(sp["rot"][0]), float(sp["rot"][1]), 0.0
    cam.set_actor_location_and_rotation(unreal.Vector(*[float(v) for v in sp["loc_cm"]]), r, False, True)
    if sp.get("fov"):
        import math
        cc = cam.get_cine_camera_component()
        fb = cc.get_editor_property("filmback")
        sw = float(fb.get_editor_property("sensor_width"))
        cc.set_editor_property("current_focal_length", sw / 2.0 / math.tan(math.radians(float(sp["fov"]) / 2.0)))
        rec["focal_mm"] = round(float(cc.get_editor_property("current_focal_length")), 3)
    l = cam.get_actor_location()
    rec["loc_now"] = [round(l.x, 1), round(l.y, 1), round(l.z, 1)]
    return rec


def read_cvars(names):
    out = {}
    for n in names:
        try:
            out[n] = unreal.SystemLibrary.get_console_variable_float_value(n)
        except Exception as exc:  # noqa: BLE001
            out[n] = "ERR " + str(exc)[:60]
    return out


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
                if CFG.get("census_prefixes"):   # voices_paper stage: read-only record of mesh actors as loaded
                    cen = {}
                    for x in unreal.GameplayStatics.get_all_actors_of_class(pc, unreal.Actor):
                        lab = _label(x)
                        if not any(lab.startswith(pf) for pf in CFG["census_prefixes"]):
                            continue
                        for c in x.get_components_by_class(unreal.StaticMeshComponent):
                            mats = []
                            for i in range(c.get_num_materials()):
                                m = c.get_material(i)
                                mats.append(m.get_name() if m else None)
                            n = c.get_instance_count() if isinstance(c, unreal.InstancedStaticMeshComponent) else 1
                            cen.setdefault(lab, []).append({"cast_shadow": bool(c.get_editor_property("cast_shadow")),
                                                            "materials": mats, "instances": n})
                    REP["census"] = cen
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
            key = s.get("out", s["name"])
            for opt, fn in (("mat", probe_mat), ("lamps", probe_lamps), ("pp", probe_pp)):   # round 9 probe options
                if s.get(opt):
                    try:
                        REP.setdefault("probe_" + opt, {})[key] = fn(s[opt])
                    except Exception as exc:  # noqa: BLE001
                        REP.setdefault("probe_errors", {})[f"{key}:{opt}"] = str(exc)[:300]
            if s.get("read_cvars"):
                REP.setdefault("cvars_read", {})[key] = read_cvars(s["read_cvars"])
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
            if s.get("pose") and s["name"] in ST["cams"]:
                REP.setdefault("probe_pose", {})[s.get("out", s["name"])] = probe_pose(ST["cams"][s["name"]], s["pose"])
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
