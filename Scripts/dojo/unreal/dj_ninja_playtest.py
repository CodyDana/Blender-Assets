"""DojoLab ninja character port, PLAY TESTS in -game (UnrealEditor-Cmd -game -RenderOffscreen on L_Dojo, run by
run_ninja_playtest.ps1 as -ExecCmds="py <this file>"). Read-only for the project content: writes only PNG frames, the
report JSON and the log. Pattern from DemoGame_1's Tools/Claude/GASP/gasp_ninja_test.ps1 + gasp_ninja_probe.py and
Character/mh_cam.py (real keys through `Input.+key`, camera moved by plain attribute writes, never set_editor_property on
the pawn: that re-runs BP_NinjaGasp's construction script and re-creates the visual child actor).

Config (JSON file named by env DJ_PT_CFG):
  {"suite": "look" | "move" | "jutsu" | "routes", "out_dir": abs, "report": abs json, "warm_s": 90,
   "frames": true, "routes": [names] (optional subset), "pawn": "ninja" | "gasp" (what the URL spawns; informational)}

Every suite records, at 10 Hz game time while a recorder runs ("rows"): speed, location, movement mode, the jutsu state,
the visual host's slots (UpperBody / DefaultSlot active, montage, NinjaSealWeight), the GASP mesh montage (traversal),
the effect actors, the cloak (bounds relative to the MetaHuman pelvis, cloth interactor: cloths / dynamic particles /
sim time, suspended), the pose check (MetaHuman bones vs the hidden Manny host: hands, feet, head; MetaHuman hand span),
the camera (lateral / behind / above vs the pawn), ninja audio components playing and active Niagara systems near the
pawn (new against a baseline).

Suites:
  look   DemoGame_1's beauty framing (cloak_mh_test.ps1 Cam(): arm 300 / pitch -8 / FOV 70 / no lag, 1600x900): front, side
         a, back, side b, close (yaw 160, arm 130, z +40, pitch -5), three-quarter close (120, 170, -20, -3); the gameplay
         camera back view; cloth: idle, run -> stop settle, SUSPENDED (frozen control) and resumed; a slow-motion frame
         sequence of a run -> stop (side view).
  move   CMC / capsule numbers; walk (LeftControl toggle), run, sprint, standing jump, double-press jump, sprint jump:
         speed and height traces, gameplay-camera stills; the GASP traversal sample on the layout's climb routes (stance
         - 2 m, run in, SpaceBar), with frame sequences for two of them.
  jutsu  each jutsu standing (warm cast first), then while walking and while running; events from the component's own
         delegates (OnJutsuSeal / Completed / Cancelled / HandPlanted / CloneSpawned); slow-motion frame sequences.
  routes the layout's walk routes walked by the pawn with real keys (W, walk gait, steered by the control yaw), BR routes
         with the 'Dojo/Boundary_1v1' group's collision off; then run / sprint jump attempts at the 1v1 CONTROLs and the
         ring (leak = the pawn's centre in the forbidden region at any tick).
Blender frame (x east, y north, metres) -> UE cm (x*100, -y*100, z*100).
"""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

CFG = json.loads(Path(os.environ["DJ_PT_CFG"]).read_text(encoding="utf-8"))
OUT = Path(CFG["out_dir"])
OUT.mkdir(parents=True, exist_ok=True)
SUITE = CFG["suite"]
LAYOUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/showcase/layout_showcase.json"
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "suite": SUITE, "cfg": CFG, "events": [], "results": {},
       "recordings": {}, "sequences": {}, "shots": []}
G = {"pc": None, "pawn": None, "gen": None, "wait": None, "handle": None, "t0": time.time(), "rec": None,
     "pending_shot": None, "niagara_base": set(), "delegates": [], "jutsu_events": [], "boundary": [],
     "key_down": set()}
V = unreal.Vector
CLASSES = {
    "BP_NinjaGasp_C": "/Game/Ninja/Blueprints/BP_NinjaGasp.BP_NinjaGasp_C",
    "BP_GreatFireball_C": "/Game/Ninja/Jutsu/BP_GreatFireball.BP_GreatFireball_C",
    "BP_SummoningSeal_C": "/Game/Ninja/Jutsu/BP_SummoningSeal.BP_SummoningSeal_C",
    "BP_ChidoriLightning_C": "/Game/Ninja/Jutsu/BP_ChidoriLightning.BP_ChidoriLightning_C",
}
LOADED = {}
BONES = ("hand_l", "hand_r", "foot_l", "foot_r", "head")


# ----------------------------------------------------------------------------------------------------------- basics
def now_s():
    return round(time.time() - G["t0"], 2)


def log(msg):
    REP["events"].append(f"{now_s():.1f}s {msg}")
    unreal.log(f"DJ_PT {msg}")


def mark(msg):
    """a log marker the scanner uses to attribute log lines to a test window"""
    unreal.log(f"DJ_PT_MARK {msg}")
    REP["events"].append(f"{now_s():.1f}s MARK {msg}")


def cmd(c):
    unreal.SystemLibrary.execute_console_command(G["pc"], c, G["pc"])


def gtime():
    return unreal.GameplayStatics.get_time_seconds(G["pc"])


def key(name, down):
    cmd(f"Input.{'+' if down else '-'}key {name}")
    (G["key_down"].add if down else G["key_down"].discard)(name)


def release_all():
    for k in list(G["key_down"]):
        key(k, False)


def slomo(x):
    unreal.GameplayStatics.set_global_time_dilation(G["pc"], float(x))


def bl2ue(x, y, z=0.0):
    return V(x * 100.0, -y * 100.0, z * 100.0)


def ue2bl(v):
    return (round(v.x / 100.0, 3), round(-v.y / 100.0, 3), round(v.z / 100.0, 3))


def v3(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def find_pc():
    for pc in unreal.ObjectIterator(unreal.PlayerController):
        try:
            if pc.get_name().startswith("Default__") or pc.get_world() is None:
                continue
            return pc
        except Exception:  # noqa: BLE001
            continue
    return None


def comp_of(actor, cls_name):
    for c in actor.get_components_by_class(unreal.ActorComponent):
        if c.get_class().get_name() == cls_name:
            return c
    return None


def count(name):
    cls = LOADED.get(name)
    if cls is None:
        return None
    return len(unreal.GameplayStatics.get_all_actors_of_class(G["pc"], cls))


# waits: the generator yields ("g", game seconds) / ("w", wall seconds) / ("p", predicate, wall timeout) / None (next tick)
def wg(s):
    return ("g", gtime() + float(s))


def ww(s):
    return ("w", time.time() + float(s))


def until(pred, timeout_s):
    return ("p", pred, time.time() + float(timeout_s))


# ----------------------------------------------------------------------------------------------------------- the pawn
def pawn():
    p = G["pc"].get_controlled_pawn()
    if p is not None:
        G["pawn"] = p
    return G["pawn"]


def cmc_of(p):
    return p.get_component_by_class(unreal.CharacterMovementComponent)


def is_ninja(p):
    return comp_of(p, "NinjaJutsuComponent") is not None


def parts(p):
    """visual pieces of a ninja (MetaHuman body, Manny host, cloak) or of the GASP pawn (its own mesh)"""
    out = {"gasp_mesh": p.get_editor_property("mesh"), "body": None, "host": None, "cloak": None, "visual": None,
           "vb": None}
    for c in p.get_components_by_class(unreal.ChildActorComponent):
        a = c.get_editor_property("child_actor")
        if a is not None and a.get_class().get_name().startswith("BP_NinjaVisual"):
            out["visual"] = a
    if out["visual"] is not None:
        vb = comp_of(out["visual"], "NinjaVisualBodyComponent")
        out["vb"] = vb
        if vb is not None:
            out["body"], out["host"] = vb.get_meta_human_body(), vb.get_host_mesh()
            for g in vb.get_meta_human_garments() or []:
                out["cloak"] = g
    return out


def bone(c, b):
    try:
        return c.get_socket_location(b)
    except Exception:  # noqa: BLE001
        return None


def pose_check(pp):
    """MetaHuman body bones against the hidden Manny host the retarget follows (a T / reference pose on the visible body
    shows as a large hand delta and a ~170 cm hand span)"""
    body, host = pp["body"], pp["host"]
    if body is None or host is None:
        return None
    d = {}
    for b in BONES:
        a, h = bone(body, b), bone(host, b)
        if a is not None and h is not None:
            d[b] = round((a - h).length(), 1)
    hl, hr = bone(body, "hand_l"), bone(body, "hand_r")
    span = round((hl - hr).length(), 1) if hl is not None and hr is not None else None
    hhl, hhr = bone(host, "hand_l"), bone(host, "hand_r")
    span_host = round((hhl - hhr).length(), 1) if hhl is not None and hhr is not None else None
    return {"max_delta": max(d.values()) if d else None, "delta": d, "span_mh": span, "span_host": span_host}


def cloak_state(pp):
    c, body = pp["cloak"], pp["body"]
    if c is None:
        return None
    out = {"visible": bool(c.is_visible())}
    try:
        org, ext, rad = unreal.SystemLibrary.get_component_bounds(c)
        ref = bone(body, "pelvis") if body is not None else None
        out["ext"] = v3(ext)
        if ref is not None:
            rel = org - ref
            out["org_rel_pelvis"] = v3(rel)
    except Exception as exc:  # noqa: BLE001
        out["bounds_err"] = str(exc)[:80]
    try:
        out["suspended"] = bool(c.is_clothing_simulation_suspended())
    except Exception:  # noqa: BLE001
        pass
    try:
        it = c.get_clothing_simulation_interactor()
        if it is not None:
            out["cloths"] = int(it.get_num_cloths())
            out["dyn"] = int(it.get_num_dynamic_particles())
            out["kin"] = int(it.get_num_kinematic_particles())
            out["sim_ms"] = round(float(it.get_simulation_time()), 3)
        else:
            out["interactor"] = None
    except Exception as exc:  # noqa: BLE001
        out["interactor_err"] = str(exc)[:80]
    return out


def camera_state():
    p, pc = pawn(), G["pc"]
    cm = pc.player_camera_manager
    cam_loc = cm.get_camera_location()
    rot = cm.get_camera_rotation()
    yaw = math.radians(rot.yaw)
    right = V(-math.sin(yaw), math.cos(yaw), 0.0)
    fwd = V(math.cos(yaw), math.sin(yaw), 0.0)
    off = cam_loc - p.get_actor_location()
    return {"lateral_cm": round(off.x * right.x + off.y * right.y, 1),
            "behind_cm": round(-(off.x * fwd.x + off.y * fwd.y), 1), "above_cm": round(off.z, 1),
            "fov": round(cm.get_fov_angle(), 2),
            "cvar": unreal.SystemLibrary.get_console_variable_int_value("DDCVar.NewGameplayCameraSystem.Enable")}


def audio_playing():
    out = []
    try:
        for a in unreal.ObjectIterator(unreal.AudioComponent):
            try:
                if a.get_world() is None or not a.is_playing():
                    continue
                s = a.get_editor_property("sound")
                if s is not None and s.get_path_name().startswith("/Game/Ninja"):
                    out.append(s.get_name())
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    return sorted(out)


def audio_all():
    """voices_paper stage (no jutsu voice-overs): EVERY AudioComponent in the game world, playing or not, with its sound;
    'voice' = any whose sound is under /Game/Ninja/Audio/Voice or is named *Voice* (must stay empty)."""
    seen, voice = [], []
    try:
        for a in unreal.ObjectIterator(unreal.AudioComponent):
            try:
                if a.get_world() is None or a.get_name().startswith("Default__"):
                    continue
                s = a.get_editor_property("sound")
                path = s.get_path_name() if s is not None else None
                seen.append(path.split(".")[-1] if path else None)
                if path and ("/Audio/Voice/" in path or "voice" in path.lower()):
                    voice.append(path)
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    return sorted({x for x in seen if x}), sorted(set(voice))


def niagara_near(radius_cm=3000.0):
    p = pawn()
    pl = p.get_actor_location()
    out = set()
    try:
        for n in unreal.ObjectIterator(unreal.NiagaraComponent):
            try:
                if n.get_world() is None or not n.is_active():
                    continue
                if (n.get_world_location() - pl).length() > radius_cm:
                    continue
                a = n.get_asset()
                out.add(a.get_name() if a else "None")
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    return out


def anim_slots(pp):
    host = pp["host"]
    out = {}
    if host is None:
        return out
    ai = host.get_anim_instance()
    if ai is None:
        return {"anim": None}
    try:
        out["upper"] = bool(ai.is_slot_active("UpperBody"))
        out["default"] = bool(ai.is_slot_active("DefaultSlot"))
    except Exception as exc:  # noqa: BLE001
        out["slot_err"] = str(exc)[:60]
    try:
        m = ai.get_current_active_montage()
        if m is not None:
            tr = m.get_editor_property("slot_anim_tracks")
            out["montage"] = m.get_name()
            out["montage_slot"] = str(tr[0].get_editor_property("slot_name")) if tr else None
    except Exception:  # noqa: BLE001
        pass
    try:
        out["seal_w"] = round(float(ai.get_editor_property("NinjaSealWeight")), 3)
    except Exception:  # noqa: BLE001
        pass
    return out


def gasp_montage(pp):
    m = pp["gasp_mesh"]
    try:
        ai = m.get_anim_instance()
        mm = ai.get_current_active_montage() if ai else None
        return mm.get_name() if mm else None
    except Exception:  # noqa: BLE001
        return None


def snap(tag="", full=True):
    p = pawn()
    rec = {"tag": tag, "t": round(gtime(), 3), "w": now_s()}
    try:
        v = p.get_velocity()
        rec["speed"] = round(math.hypot(v.x, v.y), 1)
        rec["vz"] = round(v.z, 1)
        loc = p.get_actor_location()
        rec["loc"] = v3(loc)
        rec["bl"] = ue2bl(loc)
        rec["yaw"] = round(p.get_actor_rotation().yaw, 1)
        cmc = cmc_of(p)
        rec["mode"] = str(cmc.get_editor_property("movement_mode")).split(".")[-1].split(":")[0]
        j = comp_of(p, "NinjaJutsuComponent")
        if j is not None:
            cj, fj = j.get_casting_jutsu(), j.get_finishing_jutsu()
            rec["casting"] = cj.get_name() if cj else None
            rec["finishing"] = fj.get_name() if fj else None
        rs = comp_of(p, "NinjaRunStyleComponent")
        if rs is not None:
            rec["run_style"] = bool(rs.is_run_style_active())
        pp = parts(p)
        rec["gasp_montage"] = gasp_montage(pp)
        if full:
            rec["slots"] = anim_slots(pp)
            rec["pose"] = pose_check(pp)
            rec["cloak"] = cloak_state(pp)
            rec["cam"] = camera_state()
            rec["counts"] = {n: count(n) for n in CLASSES}
            rec["audio"] = audio_playing()
            rec["audio_comps"], rec["voice_comps"] = audio_all()
            nn = niagara_near()
            rec["niagara_new"] = sorted(nn - G["niagara_base"])
            rec["clones"] = clone_states()
    except Exception as exc:  # noqa: BLE001
        rec["error"] = traceback.format_exc()[-400:]
    return rec


def clone_states():
    out = []
    lead = pawn()
    for a in unreal.GameplayStatics.get_all_actors_of_class(G["pc"], LOADED["BP_NinjaGasp_C"]) if LOADED.get("BP_NinjaGasp_C") else []:
        if a == lead:
            continue
        pp = parts(a)
        body = pp["body"]
        out.append({"name": a.get_name(), "loc_bl": ue2bl(a.get_actor_location()),
                    "body_visible": bool(body.is_visible()) if body else None,
                    "cloak_visible": bool(pp["cloak"].is_visible()) if pp["cloak"] else None,
                    "pose_max_delta": (pose_check(pp) or {}).get("max_delta"),
                    "controller": a.get_controller().get_class().get_name() if a.get_controller() else None})
    return out


# ----------------------------------------------------------------------------------------------------------- recorder
def rec_start(name, every=0.1, full=True):
    G["rec"] = {"name": name, "every": every, "next": gtime(), "rows": [], "full": full}


def rec_stop():
    r = G["rec"]
    G["rec"] = None
    if r is not None:
        REP["recordings"][r["name"]] = r["rows"]
        return r["rows"]
    return []


def rec_tick():
    r = G["rec"]
    if r is None:
        return
    t = gtime()
    if t >= r["next"]:
        r["rows"].append(snap(r["name"], r["full"]))
        r["next"] = t + r["every"]


# ----------------------------------------------------------------------------------------------------------- camera / shots
def arm_comp(p=None):
    p = p or pawn()
    return p.get_component_by_class(unreal.SpringArmComponent)


def active_cam(p=None):
    p = p or pawn()
    for c in p.get_components_by_class(unreal.CameraComponent):
        if c.is_active():
            return c
    return None


def cam_set(yaw_rel=None, arm=300.0, z=0.0, pitch=-8.0, fov=70.0, lag=False):
    """DemoGame_1 mh_cam.py: plain attribute writes / setters only"""
    p = pawn()
    a = arm_comp(p)
    if a is not None:
        a.target_arm_length = float(arm)
        a.set_relative_location(V(0.0, 0.0, 70.0 + float(z)), False, False)
        a.enable_camera_lag = bool(lag)
        a.enable_camera_rotation_lag = False
    c = active_cam(p)
    if c is not None:
        c.set_field_of_view(float(fov))
    if yaw_rel is not None:
        G["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=float(pitch),
                                                    yaw=p.get_actor_rotation().yaw + float(yaw_rel)))


def cam_reset():
    cam_set(None, 375.0, 0.0, -8.0, 85.0, True)


def shot(name, w=1600, h=900):
    if not CFG.get("frames", True):
        return
    path = OUT / "shots" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    cmd(f"HighResShot filename={path.as_posix()} {w}x{h}")
    REP["shots"].append(f"shots/{name}")
    log(f"shot {name}")


def shot_wait(name, w=1600, h=900, timeout=20.0):
    """issue a still and wait for its file"""
    shot(name, w, h)
    path = OUT / "shots" / name
    yield until(lambda: (not CFG.get("frames", True)) or (path.exists() and path.stat().st_size > 0), timeout)


def seq_runner(seq, w=1280, h=720):
    """call every tick while a frame sequence runs: one HighResShot in flight at a time; records game time per frame"""
    s = REP["sequences"].setdefault(seq, [])
    pend = G["pending_shot"]
    if pend is not None:
        if pend["path"].exists() and pend["path"].stat().st_size > 0:
            G["pending_shot"] = None
        elif time.time() - pend["w"] > 5.0:
            G["pending_shot"] = None
        else:
            return
    i = len(s)
    path = OUT / "frames" / seq / f"{i:04d}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd(f"HighResShot filename={path.as_posix()} {w}x{h}")
    s.append({"i": i, "t": round(gtime(), 4), "file": f"frames/{seq}/{i:04d}.png"})
    G["pending_shot"] = {"path": path, "w": time.time()}


def run_seq(seq, dur_game, w=1280, h=720, stop_pred=None):
    """frame sequence for dur_game game seconds (or until stop_pred) - a generator to `yield from`"""
    if not CFG.get("frames", True):
        yield wg(dur_game)
        return
    t_end = gtime() + dur_game
    while gtime() < t_end and not (stop_pred and stop_pred()):
        seq_runner(seq, w, h)
        yield None
    yield until(lambda: G["pending_shot"] is None or G["pending_shot"]["path"].exists(), 5.0)
    G["pending_shot"] = None


# ----------------------------------------------------------------------------------------------------------- movement helpers
def teleport_bl(x, y, floor_z, face_bl=None, yaw=None, lift=3.0):
    p = pawn()
    hh = p.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
    if yaw is None and face_bl is not None:
        yaw = math.degrees(math.atan2(-face_bl[1], face_bl[0]))
    yaw = p.get_actor_rotation().yaw if yaw is None else yaw
    cmc = cmc_of(p)
    try:
        cmc.stop_movement_immediately()
    except Exception:  # noqa: BLE001
        pass
    p.set_actor_location_and_rotation(V(x * 100.0, -y * 100.0, floor_z * 100.0 + hh + lift),
                                      unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False, True)
    G["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=-10.0, yaw=yaw))
    return yaw


def face_yaw(yaw, pitch=-10.0):
    G["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))


def cmc_numbers(p):
    cmc = cmc_of(p)
    cap = p.get_component_by_class(unreal.CapsuleComponent)
    out = {"pawn": p.get_class().get_name(), "capsule_r": round(cap.get_scaled_capsule_radius(), 2),
           "capsule_hh": round(cap.get_scaled_capsule_half_height(), 2)}
    for k in ("max_walk_speed", "max_walk_speed_crouched", "jump_z_velocity", "gravity_scale", "max_step_height",
              "air_control", "max_acceleration", "braking_deceleration_walking", "ground_friction",
              "braking_deceleration_falling", "min_analog_walk_speed", "orient_rotation_to_movement",
              "use_controller_desired_rotation", "rotation_rate", "perch_radius_threshold", "walkable_floor_z"):
        try:
            v = cmc.get_editor_property(k)
            out[k] = round(v, 3) if isinstance(v, float) else (str(v) if not isinstance(v, (int, bool)) else v)
        except Exception as exc:  # noqa: BLE001
            out[k] = f"n/a {str(exc)[:40]}"
    try:
        out["walkable_floor_angle"] = round(cmc.get_walkable_floor_angle(), 3)
    except Exception:  # noqa: BLE001
        pass
    try:
        out["jump_max_count"] = int(p.get_editor_property("jump_max_count"))
    except Exception as exc:  # noqa: BLE001
        out["jump_max_count"] = f"n/a {str(exc)[:40]}"
    g = 980.0 * float(out.get("gravity_scale", 1.0) if isinstance(out.get("gravity_scale"), float) else 1.0)
    jz = out.get("jump_z_velocity")
    if isinstance(jz, float):
        out["single_jump_apex_cm"] = round(jz * jz / (2.0 * g), 1)
    return out


def imc_dump():
    out = {}
    for path in ("/Game/Input/IMC_Sandbox", "/Game/Ninja/Input/IMC_NinjaGasp"):
        a = unreal.load_asset(path)
        rows = []
        try:
            try:
                maps = a.get_editor_property("mappings")
            except Exception:  # noqa: BLE001
                maps = a.get_editor_property("default_key_mappings").get_editor_property("mappings")
            for m in maps:
                act = m.get_editor_property("action")
                k = m.get_editor_property("key")
                try:
                    kn = str(k.get_editor_property("key_name"))
                except Exception:  # noqa: BLE001
                    kn = str(k)
                rows.append([act.get_name() if act else None, kn])
        except Exception as exc:  # noqa: BLE001
            rows.append(["error", str(exc)[:120]])
        out[path] = rows
    return out


# ----------------------------------------------------------------------------------------------------------- jutsu delegates
def bind_jutsu(p):
    j = comp_of(p, "NinjaJutsuComponent")
    if j is None:
        return None

    def ev(kind, nargs):
        def rec_args(*args):
            names = []
            for a in args:
                try:
                    names.append(a.get_name())
                except Exception:  # noqa: BLE001
                    names.append(str(a) if not isinstance(a, unreal.Vector) else v3(a))
            G["jutsu_events"].append({"kind": kind, "t": round(gtime(), 3), "args": names})
        # UE's Python delegates check the callable's declared parameter count, so *args is refused
        if nargs == 1:
            return lambda a: rec_args(a)
        if nargs == 2:
            return lambda a, b: rec_args(a, b)
        return lambda a, b, c: rec_args(a, b, c)
    for attr, kind, nargs in (("on_jutsu_seal", "seal", 2), ("on_jutsu_completed", "completed", 1),
                              ("on_jutsu_cancelled", "cancelled", 2), ("on_jutsu_hand_planted", "hand_planted", 3),
                              ("on_clone_spawned", "clone_spawned", 1)):
        try:
            fn = ev(kind, nargs)
            getattr(j, attr).add_callable(fn)
            G["delegates"].append(fn)   # keep the callable alive
        except Exception as exc:  # noqa: BLE001
            log(f"bind {attr} failed: {str(exc)[:120]}")
    jl = []
    for ju in j.get_editor_property("jutsus"):
        d = {"name": ju.get_name()}
        for k in ("seals", "release", "opening_animation", "finisher_animation", "start_voice", "complete_sound",
                  "play_complete_sound", "finisher_effect_class", "hand_planted_effect_class", "fireball_class",
                  "input_action"):
            try:
                v = ju.get_editor_property(k)
                if k == "seals":
                    d["n_seals"] = len(v)
                elif isinstance(v, bool):
                    d[k] = v
                else:
                    d[k] = v.get_name() if hasattr(v, "get_name") else str(v)
            except Exception:  # noqa: BLE001
                pass
        jl.append(d)
    out = {"jutsus": jl}
    for k in ("seal_sound", "jutsu_complete_sound", "clone_smoke_effect", "clone_dispel_sound", "clone_lifetime",
              "clone_reveal_delay", "max_clones", "seal_hold_time", "seal_blend_time", "final_seal_hold_time",
              "seal_layer_blend_time", "input_mapping_priority"):
        try:
            v = j.get_editor_property(k)
            out[k] = v.get_name() if hasattr(v, "get_name") else (round(v, 3) if isinstance(v, float) else v)
        except Exception:  # noqa: BLE001
            pass
    return out


# ----------------------------------------------------------------------------------------------------------- suites
def suite_look():
    p = pawn()
    REP["results"]["cmc"] = cmc_numbers(p)
    cam_reset()
    yield wg(1.0)
    rec_start("look_idle_gameplay_cam", 0.1)
    yield wg(3.0)
    rec_stop()
    yield from shot_wait("L00_gameplay_back.png", 1920, 1080)
    # DemoGame_1 cloak_mh_test.ps1 framing
    for name, yaw, arm, z, pitch in (("L01_front", 180, 300, 0, -8), ("L02_side_a", 90, 300, 0, -8),
                                     ("L03_back", 0, 300, 0, -8), ("L04_side_b", 270, 300, 0, -8),
                                     ("L05_close", 160, 130, 40, -5), ("L06_close_threequarter", 120, 170, -20, -3)):
        cam_set(yaw, arm, z, pitch, 70.0, False)
        yield wg(1.5)
        REP["results"].setdefault("look_cam", {})[name] = camera_state()
        yield from shot_wait(f"{name}.png", 1600, 900)
    cam_reset()
    yield wg(1.0)
    # cloth: run -> stop -> settle, then the frozen control (suspended) and resumed
    yaw0 = p.get_actor_rotation().yaw
    face_yaw(yaw0)
    yield wg(0.5)
    rec_start("look_cloth_run_stop", 0.05)
    key("W", True)
    yield wg(2.0)
    key("W", False)
    yield wg(3.0)
    rec_stop()
    cloak = parts(p)["cloak"]
    rec_start("look_cloth_idle_running_sim", 0.05)
    yield wg(2.0)
    rec_stop()
    try:
        cloak.suspend_clothing_simulation()
        REP["results"]["suspend_called"] = True
    except Exception as exc:  # noqa: BLE001
        REP["results"]["suspend_called"] = str(exc)[:120]
    rec_start("look_cloth_SUSPENDED", 0.05)
    key("W", True)
    yield wg(1.0)
    key("W", False)
    yield wg(1.5)
    rec_stop()
    try:
        cloak.resume_clothing_simulation()
    except Exception:  # noqa: BLE001
        pass
    rec_start("look_cloth_resumed_run_stop", 0.05)
    key("W", True)
    yield wg(1.0)
    key("W", False)
    yield wg(2.0)
    rec_stop()
    # slow-motion side view of run -> stop (cloth swing)
    face_yaw(p.get_actor_rotation().yaw + 180.0)
    yield wg(0.3)
    key("W", True)
    yield wg(0.8)
    key("W", False)
    yield wg(2.5)
    cam_set(90, 330, -10, -6, 70.0, False)
    yield wg(1.0)
    slomo(0.25)
    rec_start("look_seq_run_stop", 0.05)
    # run across the view: D = the control yaw's right, perpendicular to the camera's view; the arm follows the pawn
    key("D", True)
    yield from run_seq("look_run_stop_side", 0.9)
    key("D", False)
    yield from run_seq("look_run_stop_side", 1.6)
    rec_stop()
    slomo(1.0)
    cam_reset()
    yield wg(1.0)
    yield from shot_wait("L07_after.png", 1600, 900)


def gait_trace(name, keys, hold_s, shot_at=None, shot_name=None):
    rec_start(name, 0.05, full=False)
    for k in keys:
        key(k, True)
        yield wg(0.05)
    t0 = gtime()
    shot_done = False
    while gtime() - t0 < hold_s:
        if shot_at is not None and not shot_done and gtime() - t0 >= shot_at:
            shot(shot_name, 1600, 900)
            shot_done = True
        yield None
    for k in reversed(keys):
        key(k, False)
    yield wg(1.5)
    rows = rec_stop()
    sp = [r.get("speed", 0) for r in rows]
    REP["results"].setdefault("gaits", {})[name] = {"max_speed": max(sp) if sp else None,
                                                     "speed_at_end_of_hold": steady(rows, t0 + hold_s - 0.4, t0 + hold_s),
                                                     "run_style_any": any(r.get("run_style") for r in rows)}


def steady(rows, ta, tb):
    v = [r["speed"] for r in rows if ta <= r["t"] <= tb and "speed" in r]
    return round(sum(v) / len(v), 1) if v else None


def jump_trace(name, presses, run_keys=(), run_s=0.0, shot_name=None):
    p = pawn()
    rec_start(name, 0.02, full=False)
    for k in run_keys:
        key(k, True)
    if run_s:
        yield wg(run_s)
    z0 = p.get_actor_location().z
    b0 = ue2bl(p.get_actor_location())
    t0 = gtime()
    i = 0
    apex = z0
    shot_done = False
    while gtime() - t0 < 2.5:
        if i < len(presses) and gtime() - t0 >= presses[i]:
            key("SpaceBar", True)
            G["space_t"] = gtime()
            i += 1
        if G.get("space_t") and gtime() - G["space_t"] > 0.1 and "SpaceBar" in G["key_down"]:
            key("SpaceBar", False)
        z = p.get_actor_location().z
        if z > apex:
            apex = z
        if shot_name and not shot_done and p.get_velocity().z < 0 and apex - z0 > 30:
            shot(shot_name, 1600, 900)
            shot_done = True
        yield None
    for k in run_keys:
        key(k, False)
    if "SpaceBar" in G["key_down"]:
        key("SpaceBar", False)
    yield wg(1.0)
    rows = rec_stop()
    b1 = ue2bl(p.get_actor_location())
    REP["results"].setdefault("jumps", {})[name] = {
        "apex_cm": round(apex - z0, 1), "presses": presses, "run_keys": list(run_keys),
        "horiz_m": round(math.hypot(b1[0] - b0[0], b1[1] - b0[1]), 2),
        "falling_rows": sum(1 for r in rows if r.get("mode") == "MOVE_FALLING"),
        "gasp_montages": sorted({r.get("gasp_montage") for r in rows if r.get("gasp_montage")})}


def traverse(cr, tag, seq=None):
    """GASP traversal sample: 2 m behind the stance, run in (W), SpaceBar at the stance, keep W 1.6 s"""
    p = pawn()
    fx, fy = cr["face"]
    sx, sy = cr["stance"]
    back = 2.0 if cr["floor_z"] < 0.05 else 0.45      # on a prop top there is no room for a run-in
    back = {"Pavilion_Plinth": 0.9}.get(cr.get("marker"), back)   # the pavilion crate stands 1.3 m behind its stance
    start = (sx - back * fx, sy - back * fy)
    yaw = teleport_bl(start[0], start[1], cr["floor_z"], (fx, fy))
    yield wg(0.8)
    z_floor = p.get_actor_location().z
    rec_start(f"trav_{tag}", 0.05, full=True)
    key("W", True)
    t0 = gtime()
    pressed = None
    while gtime() - t0 < 2.5:
        loc = ue2bl(p.get_actor_location())
        along = (loc[0] - start[0]) * fx + (loc[1] - start[1]) * fy
        face_yaw(yaw)
        if pressed is None and along >= back - 0.25:
            key("SpaceBar", True)
            pressed = gtime()
        if pressed is not None and "SpaceBar" in G["key_down"] and gtime() - pressed > 0.1:
            key("SpaceBar", False)
        if seq:
            seq_runner(seq)
        if pressed is not None and gtime() - pressed > 1.8:
            break
        yield None
    key("W", False)
    if seq:
        t1 = gtime()
        while gtime() - t1 < 1.2:
            seq_runner(seq)
            yield None
        yield until(lambda: G["pending_shot"] is None or G["pending_shot"]["path"].exists(), 5.0)
        G["pending_shot"] = None
    yield wg(1.2)
    rows = rec_stop()
    zs = [r["loc"][2] for r in rows if "loc" in r]
    end = ue2bl(p.get_actor_location())
    mk = marker_top(cr.get("marker"))
    montages = sorted({r.get("gasp_montage") for r in rows if r.get("gasp_montage")})
    poses = [r["pose"]["max_delta"] for r in rows if r.get("pose") and r["pose"].get("max_delta") is not None]
    spans = [r["pose"]["span_mh"] for r in rows if r.get("pose") and r["pose"].get("span_mh") is not None]
    res = {"step": cr["step"], "marker": cr.get("marker"), "marker_top_m": mk, "start_floor_m": cr["floor_z"],
           "end_bl": end, "end_feet_m": round(end[2] - p.get_component_by_class(unreal.CapsuleComponent)
                                               .get_scaled_capsule_half_height() / 100.0, 3),
           "rise_cm": round(max(zs) - z_floor, 1) if zs else None, "gasp_montages": montages,
           "flying_rows": sum(1 for r in rows if r.get("mode") in ("MOVE_FLYING", "MOVE_CUSTOM")),
           "space_pressed": pressed is not None, "pose_max_delta": max(poses) if poses else None,
           "span_mh_max": max(spans) if spans else None}
    if mk is not None:
        res["on_top"] = abs(res["end_feet_m"] - mk) < 0.15
    REP["results"].setdefault("traversal", {})[tag] = res
    log(f"traversal {tag}: rise {res['rise_cm']} end feet {res['end_feet_m']} montages {montages}")


MARKERS = {}


def marker_top(name):
    return MARKERS.get(name)


def suite_move():
    p = pawn()
    REP["results"]["cmc"] = cmc_numbers(p)
    REP["results"]["imc"] = imc_dump()
    cam_reset()
    # an open lane: the courtyard at y 12 from x 8 eastwards (P1 -> P2 line is clear; racks end at y 9.55)
    teleport_bl(8.0, 12.0, 0.0, (1, 0))
    yield wg(1.5)
    REP["results"]["cam_idle"] = camera_state()
    yield from gait_trace("run_W", ["W"], 3.0, 2.0, "M01_run.png")
    REP["results"]["cam_after_run"] = camera_state()
    # camera while running: lateral offset over the run
    teleport_bl(36.0, 12.0, 0.0, (-1, 0))
    yield wg(1.0)
    rec_start("cam_run", 0.05, full=True)
    key("W", True)
    yield wg(2.5)
    key("W", False)
    yield wg(1.0)
    rows = rec_stop()
    lat = [abs(r["cam"]["lateral_cm"]) for r in rows if r.get("cam")]
    REP["results"]["cam_run_lateral_abs_max_cm"] = max(lat) if lat else None
    teleport_bl(8.0, 12.0, 0.0, (1, 0))
    yield wg(1.0)
    yield from gait_trace("sprint_shift_then_W", ["LeftShift", "W"], 3.0, 2.2, "M02_sprint.png")
    teleport_bl(36.0, 12.0, 0.0, (-1, 0))
    yield wg(1.0)
    # W first, Shift 1.5 s later (the build probe's order that stayed at 575)
    rec_start("sprint_W_then_shift", 0.05, full=False)
    key("W", True)
    yield wg(1.2)
    key("LeftShift", True)
    yield wg(1.6)
    key("LeftShift", False)
    key("W", False)
    yield wg(1.5)
    rows = rec_stop()
    REP["results"].setdefault("gaits", {})["sprint_W_then_shift"] = {
        "max_speed": max(r.get("speed", 0) for r in rows),
        "speed_trace_after_shift": [(round(r["t"] - rows[0]["t"], 2), r.get("speed")) for r in rows][::3]}
    # walk: LeftControl toggles GASP's gait
    teleport_bl(8.0, 12.0, 0.0, (1, 0))
    yield wg(1.0)
    key("LeftControl", True)
    yield wg(0.1)
    key("LeftControl", False)
    yield wg(0.3)
    yield from gait_trace("walk_ctrl_toggle_W", ["W"], 3.0, 2.0, "M03_walk.png")
    key("LeftControl", True)
    yield wg(0.1)
    key("LeftControl", False)
    yield wg(0.5)
    # jumps (open courtyard)
    teleport_bl(20.0, 12.0, 0.0, (1, 0))
    yield wg(1.2)
    yield from jump_trace("jump_standing", [0.0], shot_name="M04_jump.png")
    teleport_bl(20.0, 12.0, 0.0, (1, 0))
    yield wg(1.2)
    yield from jump_trace("jump_double_press", [0.0, 0.35])
    teleport_bl(6.0, 12.0, 0.0, (1, 0))
    yield wg(1.2)
    yield from jump_trace("jump_sprinting", [0.0], run_keys=("LeftShift", "W"), run_s=1.8, shot_name="M05_sprint_jump.png")
    teleport_bl(6.0, 12.0, 0.0, (1, 0))
    yield wg(1.2)
    yield from jump_trace("jump_sprinting_double_press", [0.0, 0.35], run_keys=("LeftShift", "W"), run_s=1.8)
    # traversal sample: every climb route with a marker from a floor the pawn can stand on (courtyard routes)
    L = json.loads(Path(LAYOUT).read_text(encoding="utf-8"))
    for m in L["traversal_markers"]:
        MARKERS[m["name"]] = m["box"][5]
    picks = [cr for cr in L["climb_routes"] if cr.get("marker") and cr["route"] in ("1", "4", "7", "8", "-")]
    for i, cr in enumerate(picks):
        tag = f"{i:02d}_{cr['marker']}_{cr['floor_z']}"
        seq = None
        if CFG.get("frames", True) and cr["marker"] in ("Wall_S_W1", "WeaponRack_W"):
            seq = f"trav_{cr['marker']}"
            cam_set(None, 375.0, 0.0, -8.0, 85.0, False)
            slomo(0.35)
        yield from traverse(cr, tag, seq)
        if seq:
            slomo(1.0)
            cam_reset()
    REP["results"]["cmc_end"] = cmc_numbers(pawn())


def jutsu_cast(name, keyname, seq=None, run_keys=(), walk=False, seq_cam=(150, 320, 0, -8), max_game_s=12.0):
    """press a jutsu key (optionally while moving) and follow it to the end: casting -> finishing -> effects gone"""
    p = pawn()
    mark(f"{name} begin")
    G["jutsu_events"] = []
    G["niagara_base"] = niagara_near()
    if seq:
        cam_set(seq_cam[0], seq_cam[1], seq_cam[2], seq_cam[3], 70.0, False)
        yield wg(0.8)
        slomo(0.25)
    if walk:
        key("LeftControl", True)
        yield wg(0.05)
        key("LeftControl", False)
    for k in run_keys:
        key(k, True)
    if run_keys:
        yield wg(1.0)
    rec_start(f"jutsu_{name}", 0.1, full=True)
    t0 = gtime()
    key(keyname, True)
    kt = gtime()
    started = False
    done_t = None
    while gtime() - t0 < max_game_s:
        if keyname in G["key_down"] and gtime() - kt > 0.12:
            key(keyname, False)
        if seq:
            seq_runner(seq)
        busy = False
        try:
            j = comp_of(p, "NinjaJutsuComponent")
            busy = bool(j.is_casting_jutsu() or j.is_finishing())
        except Exception:  # noqa: BLE001
            pass
        if busy:
            started = True
        if run_keys and started and not busy and gtime() - t0 > 2.5:
            for k in run_keys:
                if k in G["key_down"]:
                    key(k, False)
        effects = sum((count(n) or 0) for n in ("BP_GreatFireball_C", "BP_SummoningSeal_C", "BP_ChidoriLightning_C"))
        clones = max(0, (count("BP_NinjaGasp_C") or 1) - 1)
        if started and not busy and effects == 0 and clones == 0:
            if done_t is None:
                done_t = gtime()
            elif gtime() - done_t > 0.8:
                break
        else:
            done_t = None
        yield None
    release_all()
    if walk:
        key("LeftControl", True)
        yield wg(0.05)
        key("LeftControl", False)
    if seq:
        yield until(lambda: G["pending_shot"] is None or G["pending_shot"]["path"].exists(), 5.0)
        G["pending_shot"] = None
        slomo(1.0)
        cam_reset()
    rows = rec_stop()
    mark(f"{name} end")
    REP["results"].setdefault("jutsu", {})[name] = summarize_jutsu(rows, t0, list(G["jutsu_events"]), started,
                                                                   gtime() - t0)
    yield wg(1.0)


def summarize_jutsu(rows, t0, events, started, dur):
    def first(pred):
        for r in rows:
            if pred(r):
                return round(r["t"] - t0, 2)
        return None

    def last(pred):
        out = None
        for r in rows:
            if pred(r):
                out = round(r["t"] - t0, 2)
        return out
    cast_rows = [r for r in rows if r.get("casting")]
    moving_cast = [r.get("speed", 0) for r in cast_rows]
    res = {"started": started, "duration_game_s": round(dur, 2),
           "events": [{**e, "t": round(e["t"] - t0, 3)} for e in events],
           "n_seal_events": sum(1 for e in events if e["kind"] == "seal"),
           "completed": any(e["kind"] == "completed" for e in events),
           "cancelled": any(e["kind"] == "cancelled" for e in events),
           "casting_from_to": [first(lambda r: r.get("casting")), last(lambda r: r.get("casting"))],
           "finishing_from_to": [first(lambda r: r.get("finishing")), last(lambda r: r.get("finishing"))],
           "upperbody_slot_active_rows": sum(1 for r in rows if r.get("slots", {}).get("upper")),
           "upperbody_while_casting": sum(1 for r in cast_rows if r.get("slots", {}).get("upper")),
           "cast_rows": len(cast_rows),
           "defaultslot_active_rows": sum(1 for r in rows if r.get("slots", {}).get("default")),
           "montages": sorted({f"{r['slots'].get('montage')}@{r['slots'].get('montage_slot')}" for r in rows
                               if r.get("slots", {}).get("montage")}),
           "seal_weight_max": max([r["slots"].get("seal_w", 0) or 0 for r in rows if r.get("slots")] or [0]),
           "speed_while_casting_min_max": [min(moving_cast), max(moving_cast)] if moving_cast else None,
           "audio": sorted({a for r in rows for a in r.get("audio", [])}),
           "audio_components_seen": sorted({a for r in rows for a in r.get("audio_comps", [])}),
           "voice_components": sorted({a for r in rows for a in r.get("voice_comps", [])}),
           "niagara_new": sorted({a for r in rows for a in r.get("niagara_new", [])}),
           "max_counts": {n: max([(r.get("counts") or {}).get(n) or 0 for r in rows] or [0]) for n in CLASSES},
           "first_seen": {n: first(lambda r, n=n: ((r.get("counts") or {}).get(n) or 0) > (1 if n == "BP_NinjaGasp_C" else 0))
                          for n in CLASSES},
           "last_seen": {n: last(lambda r, n=n: ((r.get("counts") or {}).get(n) or 0) > (1 if n == "BP_NinjaGasp_C" else 0))
                         for n in CLASSES},
           "pose_max_delta": max([r["pose"]["max_delta"] for r in rows
                                  if r.get("pose") and r["pose"].get("max_delta") is not None] or [-1]),
           "span_mh_max": max([r["pose"]["span_mh"] for r in rows
                               if r.get("pose") and r["pose"].get("span_mh") is not None] or [-1]),
           "clone_rows": [c for r in rows for c in r.get("clones", [])][:3] + [c for r in rows for c in r.get("clones", [])][-2:],
           "errors": [r["error"] for r in rows if r.get("error")][:3]}
    return res


def suite_jutsu():
    p = pawn()
    REP["results"]["cmc"] = cmc_numbers(p)
    REP["results"]["jutsu_setup"] = bind_jutsu(p)
    keys = [("ShadowClone", "F"), ("GreatFireball", "Two"), ("Summoning", "Three"), ("Chidori", "Four")]
    cam_reset()
    # warm cast of each (shaders / Niagara / audio first use), no frames
    for name, k in keys:
        teleport_bl(22.0, 9.0, 0.0, (0, -1))
        yield wg(1.0)
        yield from jutsu_cast(f"warm_{name}", k)
    # standing, slow-motion frame sequences from the front three-quarter (the fireball faces the camera's yaw on release)
    for name, k in keys:
        teleport_bl(22.0, 9.0, 0.0, (0, -1))
        yield wg(1.5)
        cam = (150, 320, 0, -8) if name != "GreatFireball" else (200, 380, 10, -8)
        yield from jutsu_cast(f"stand_{name}", k, seq=f"jutsu_{name}" if CFG.get("frames", True) else None, seq_cam=cam)
    # while walking (GASP walk gait) and while running, from the gameplay camera; lanes along the courtyard
    for mode in ("walk", "run"):
        for name, k in keys:
            teleport_bl(6.0, 12.0 if mode == "run" else 15.0, 0.0, (1, 0))
            yield wg(1.2)
            yield from jutsu_cast(f"{mode}_{name}", k, run_keys=("W",), walk=(mode == "walk"))
    # a still mid-seal while running (gameplay camera)
    teleport_bl(6.0, 12.0, 0.0, (1, 0))
    yield wg(1.0)
    key("W", True)
    yield wg(1.0)
    key("F", True)
    yield wg(0.12)
    key("F", False)
    yield wg(0.4)
    yield from shot_wait("J01_seal_while_running.png", 1600, 900)
    yield wg(1.0)
    key("W", False)
    yield wg(7.0)


def walk_route(name, rt, ign_group, gait_speed_hint=200.0):
    p = pawn()
    pts = [tuple(x) for x in rt["points"]]
    fz = rt["floor_z"]
    seglen = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(seglen)
    for a in G["boundary"]:
        a.set_actor_enable_collision(not ign_group)
    d0 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    teleport_bl(pts[0][0], pts[0][1], fz, d0)
    yield wg(0.7)

    seg0 = [0]   # waypoint order: only the current segment is projected on; the next one starts within 0.45 m of the
    #              current segment's end vertex (a route that folds back on itself, ARM_deck_strip..., ties otherwise)

    def project(x, y):
        i = seg0[0]
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        L = seglen[i] or 1e-6
        t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / (L * L)))
        px, py = ax + t * (bx - ax), ay + t * (by - ay)
        res = (math.hypot(x - px, y - py), sum(seglen[:i]) + t * L, i)
        if i < len(pts) - 2 and math.hypot(x - bx, y - by) < 0.45:
            seg0[0] = i + 1
        return res

    def point_at(s):
        acc = 0.0
        for i in range(len(pts) - 1):
            L = seglen[i]
            if s <= acc + L or i == len(pts) - 2:
                t = 0.0 if L == 0 else max(0.0, min(1.0, (s - acc) / L))
                return (pts[i][0] + t * (pts[i + 1][0] - pts[i][0]), pts[i][1] + t * (pts[i + 1][1] - pts[i][1]))
            acc += L
        return pts[-1]
    key("W", True)
    t0 = gtime()
    best_s = 0.0
    best_t = t0
    max_dev = 0.0
    zmax = -1e9
    timeout = total / (gait_speed_hint / 100.0) + 8.0
    status = "timeout"
    while True:
        loc = p.get_actor_location()
        x, y, z = ue2bl(loc)
        zmax = max(zmax, z)
        dev, s, _ = project(x, y)
        max_dev = max(max_dev, dev)
        if s > best_s + 0.05:
            best_s, best_t = s, gtime()
        tx, ty = point_at(min(total, s + 0.6))
        if total - s < 0.6:
            tx, ty = pts[-1]
        G["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=-10.0, yaw=math.degrees(math.atan2(-(ty - y), tx - x))))
        if math.hypot(pts[-1][0] - x, pts[-1][1] - y) < 0.3:
            status = "reached"
            break
        if gtime() - best_t > 2.5:
            status = "blocked"
            break
        if gtime() - t0 > timeout:
            break
        yield None
    key("W", False)
    yield wg(0.4)
    end = ue2bl(p.get_actor_location())
    hh = p.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height() / 100.0
    for a in G["boundary"]:
        a.set_actor_enable_collision(True)
    res = {"status": status, "len_m": round(total, 2), "progress_m": round(best_s, 2), "max_dev_m": round(max_dev, 2),
           "end_bl": end, "end_feet_m": round(end[2] - hh, 3), "dist_to_end_m": round(math.hypot(pts[-1][0] - end[0],
                                                                                                pts[-1][1] - end[1]), 2),
           "time_s": round(gtime() - t0, 2), "mode": "br" if ign_group else "1v1"}
    control = name.startswith("CONTROL")
    res["expected"] = "blocked" if control else "clear"
    res["as_expected"] = (status != "reached") if control else (status == "reached")
    return res


ATTEMPTS = [
    # name, start (bl), floor, face, held keys, SpaceBar presses: ("d", m along the face from the start) or ("dt", s after
    # the previous press), duration (game s), leak region (the pawn's centre, Blender metres)
    {"name": "ring_open_gate_sprint_jump", "start": (22.0, 12.0), "floor": 0.0, "face": (0, -1),
     "keys": ("LeftShift", "W"), "space": [("d", 10.6), ("dt", 0.35)], "dur": 3.5, "leak": {"y_lt": -1.1}},
    {"name": "ring_open_gate_run_jump", "start": (22.0, 8.0), "floor": 0.0, "face": (0, -1),
     "keys": ("W",), "space": [("d", 6.6), ("dt", 0.35)], "dur": 3.0, "leak": {"y_lt": -1.1}},
    {"name": "west_wall_mantle_then_jump_outward", "start": (6.0, 10.0), "floor": 0.0, "face": (-1, 0),
     "keys": ("LeftShift", "W"), "space": [("d", 4.6), ("dt", 1.4), ("dt", 0.35)], "dur": 4.5, "leak": {"x_lt": -1.1}},
    {"name": "west_wall_top_jump_outward", "start": (-0.5, 10.0), "floor": 2.0, "face": (-1, 0),
     "keys": ("W",), "space": [("d", 0.0), ("dt", 0.35)], "dur": 2.5, "leak": {"x_lt": -1.1}},
    {"name": "south_wall_mantle_then_jump_outward", "start": (10.0, 5.0), "floor": 0.0, "face": (0, -1),
     "keys": ("LeftShift", "W"), "space": [("d", 3.6), ("dt", 1.4), ("dt", 0.35)], "dur": 4.5, "leak": {"y_lt": -1.1}},
    {"name": "east_wall_mantle_then_jump_outward", "start": (38.0, 10.0), "floor": 0.0, "face": (1, 0),
     "keys": ("LeftShift", "W"), "space": [("d", 4.6), ("dt", 1.4), ("dt", 0.35)], "dur": 4.5, "leak": {"x_gt": 45.1}},
    {"name": "alley_fence_W_from_veranda_sprint_jump", "start": (12.1, 24.5), "floor": 0.5, "face": (0, 1),
     "keys": ("LeftShift", "W"), "space": [("d", 8.3), ("dt", 0.35)], "dur": 3.5,
     "leak": {"y_gt": 34.3, "x_in": (8.0, 15.5)}},
    {"name": "alley_fence_E_from_veranda_sprint_jump", "start": (31.9, 24.5), "floor": 0.5, "face": (0, 1),
     "keys": ("LeftShift", "W"), "space": [("d", 8.3), ("dt", 0.35)], "dur": 3.5,
     "leak": {"y_gt": 34.3, "x_in": (28.5, 36.0)}},
    {"name": "alley_fence_W_ground_jump", "start": (10.75, 33.6), "floor": 0.0, "face": (0, 1),
     "keys": ("W",), "space": [("d", 0.0), ("dt", 0.35)], "dur": 2.5, "leak": {"y_gt": 34.3, "x_in": (8.0, 15.5)}},
    {"name": "alley_fence_E_ground_jump", "start": (33.25, 33.6), "floor": 0.0, "face": (0, 1),
     "keys": ("W",), "space": [("d", 0.0), ("dt", 0.35)], "dur": 2.5, "leak": {"y_gt": 34.3, "x_in": (28.5, 36.0)}},
    {"name": "veranda_W_corner_into_rear_yard_jump", "start": (12.1, 33.2), "floor": 0.5, "face": (0.6, 0.8),
     "keys": ("W",), "space": [("d", 0.0), ("dt", 0.35)], "dur": 2.5, "leak": {"y_gt": 34.3, "x_in": (8.0, 16.0)}},
    {"name": "veranda_E_corner_into_rear_yard_jump", "start": (31.9, 33.2), "floor": 0.5, "face": (-0.6, 0.8),
     "keys": ("W",), "space": [("d", 0.0), ("dt", 0.35)], "dur": 2.5, "leak": {"y_gt": 34.3, "x_in": (28.0, 36.0)}},
]


def in_leak(lk, x, y):
    if "x_in" in lk and not (lk["x_in"][0] <= x <= lk["x_in"][1]):
        return False
    if "y_gt" in lk and y > lk["y_gt"]:
        return True
    if "y_lt" in lk and y < lk["y_lt"]:
        return True
    if "x_lt" in lk and x < lk["x_lt"]:
        return True
    if "x_gt" in lk and x > lk["x_gt"]:
        return True
    return False


def attempt(at):
    p = pawn()
    yaw = teleport_bl(at["start"][0], at["start"][1], at["floor"], at["face"])
    yield wg(0.8)
    rec_start(f"attempt_{at['name']}", 0.05, full=False)
    for k in at["keys"]:
        key(k, True)
    t0 = gtime()
    i = 0
    leak_at = None
    zmax = -1e9
    ext = {"x": [1e9, -1e9], "y": [1e9, -1e9]}
    fx, fy = at["face"]
    sx, sy = at["start"]
    last_press = None
    presses = []
    while gtime() - t0 < at["dur"]:
        face_yaw(yaw)
        x, y, z = ue2bl(p.get_actor_location())
        if i < len(at["space"]):
            kind, val = at["space"][i]
            along = (x - sx) * fx + (y - sy) * fy
            fire = (along >= val) if kind == "d" else (last_press is not None and gtime() - last_press >= val)
            if fire:
                key("SpaceBar", True)
                last_press = G["space_t"] = gtime()
                presses.append([round(gtime() - t0, 2), round(x, 2), round(y, 2), round(z, 2)])
                i += 1
        if "SpaceBar" in G["key_down"] and gtime() - G["space_t"] > 0.1:
            key("SpaceBar", False)
        zmax = max(zmax, z)
        ext["x"] = [min(ext["x"][0], x), max(ext["x"][1], x)]
        ext["y"] = [min(ext["y"][0], y), max(ext["y"][1], y)]
        if leak_at is None and in_leak(at["leak"], x, y):
            leak_at = [round(x, 2), round(y, 2), round(z, 2)]
        yield None
    release_all()
    yield wg(1.5)
    x, y, z = ue2bl(p.get_actor_location())
    if leak_at is None and in_leak(at["leak"], x, y):
        leak_at = [round(x, 2), round(y, 2), round(z, 2)]
    rows = rec_stop()
    hh = p.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height() / 100.0
    REP["results"].setdefault("attempts", {})[at["name"]] = {
        "leak": leak_at is not None, "leak_at": leak_at, "end_bl": [round(x, 2), round(y, 2), round(z - hh, 2)],
        "max_feet_m": round(zmax - hh, 2), "extent": ext, "max_speed": max([r.get("speed", 0) for r in rows] or [0]),
        "gasp_montages": sorted({r.get("gasp_montage") for r in rows if r.get("gasp_montage")}), "presses": presses}
    log(f"attempt {at['name']}: leak {leak_at} end {x:.2f},{y:.2f},{z - hh:.2f}")


def suite_routes():
    p = pawn()
    REP["results"]["cmc"] = cmc_numbers(p)
    for a in unreal.GameplayStatics.get_all_actors_of_class(G["pc"], unreal.Actor):
        try:
            if any(str(t) == "Dojo/Boundary_1v1" for t in a.tags):
                G["boundary"].append(a)
        except Exception:  # noqa: BLE001
            pass
    REP["results"]["boundary_group_actors"] = len(G["boundary"])
    cam_reset()
    L = json.loads(Path(LAYOUT).read_text(encoding="utf-8"))
    names = CFG.get("routes") or list(L["walk_routes"].keys())
    # walk gait (LeftControl toggles GASP's walk) for the routes: steering precision
    teleport_bl(20.0, 12.0, 0.0, (1, 0))
    yield wg(1.0)
    key("LeftControl", True)
    yield wg(0.05)
    key("LeftControl", False)
    yield wg(0.3)
    key("W", True)
    yield wg(1.5)
    REP["results"]["walk_speed"] = round(math.hypot(p.get_velocity().x, p.get_velocity().y), 1)
    key("W", False)
    yield wg(0.5)
    out = {}
    for n in names:
        rt = L["walk_routes"][n]
        mark(f"route {n}")
        res = yield from walk_route(n, rt, rt.get("leaves") == "open", max(REP["results"]["walk_speed"], 100.0))
        out[n] = res
        log(f"route {n}: {res['status']} ({res['expected']}) progress {res['progress_m']}/{res['len_m']} dev {res['max_dev_m']}")
    REP["results"]["routes"] = out
    REP["results"]["routes_not_as_expected"] = [k for k, v in out.items() if not v["as_expected"]]
    key("LeftControl", True)
    yield wg(0.05)
    key("LeftControl", False)
    yield wg(0.5)
    for at in ATTEMPTS:
        mark(f"attempt {at['name']}")
        yield from attempt(at)
    REP["results"]["attempt_leaks"] = [k for k, v in REP["results"].get("attempts", {}).items() if v["leak"]]


SUITES = {"look": suite_look, "move": suite_move, "jutsu": suite_jutsu, "routes": suite_routes}


def main_gen():
    warm = float(CFG.get("warm_s", 90))
    yield ww(warm)
    log("warm done")
    REP["visual_at_start"] = {k: (v.get_name() if v is not None else None) for k, v in parts(pawn()).items()}
    yield from SUITES[SUITE]()


# ----------------------------------------------------------------------------------------------------------- driver
def finish(ok):
    release_all()
    REP["passed_run"] = ok
    REP["sec"] = now_s()
    Path(CFG["report"]).write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_PT_DONE suite={SUITE} ok={ok}")
    if G["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(G["handle"])
        G["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def wait_done(w):
    if w is None:
        return True
    kind = w[0]
    if kind == "g":
        return gtime() >= w[1]
    if kind == "w":
        return time.time() >= w[1]
    if kind == "p":
        return bool(w[1]()) or time.time() >= w[2]
    return True


def tick(_dt):
    try:
        if G["gen"] is None:
            pc = find_pc()
            p = pc.get_controlled_pawn() if pc is not None else None
            if pc is not None and p is not None:
                if "ready_t" not in G:
                    G["ready_t"] = time.time()
                if time.time() - G["ready_t"] < 2.0:
                    return
                G["pc"], G["pawn"] = pc, p
                for n, path in CLASSES.items():
                    LOADED[n] = unreal.load_class(None, path)
                gm = unreal.GameplayStatics.get_game_mode(pc)
                REP["spawn"] = {"pawn_class": p.get_class().get_path_name(),
                                "game_mode": gm.get_class().get_path_name() if gm else None,
                                "map": unreal.GameplayStatics.get_current_level_name(pc),
                                "is_ninja": is_ninja(p)}
                cmd("au.MuteAudio 1")
                log(f"world ready {REP['spawn']}")
                G["gen"] = main_gen()
                G["wait"] = None
            elif time.time() - G["t0"] > 300:
                log("no PlayerController / pawn after 300 s")
                finish(False)
            return
        rec_tick()
        if not wait_done(G["wait"]):
            return
        try:
            G["wait"] = next(G["gen"])
        except StopIteration:
            finish(True)
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        log("ERROR " + REP["error"][-400:])
        finish(False)


G["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
