"""INDEPENDENT VERIFIER (ninja port, 2026-10-02): my own -game probe of L_Dojo. Read-only for the project: writes only
PNGs + the report under WorkFiles/dojo/build/ninja_character/verify/game/<tag>/ and the log.

Config: env V_CFG -> {"mode": "ninja"|"gasp", "tag": str, "warm_s": float}
ninja: spawn record (pawn, game mode, capsule, CMC numbers, camera cvar/offset, MetaHuman body/cloak/grooms visible,
       cloth interactor), perf windows at the spawn (gameplay camera), gaits (W / Shift+W / Ctrl walk), the centred
       camera while running, two GASP traversals (Cistern_E, Wall_E_S) chosen by me (not the tester's filmed ones),
       the four jutsu by their IMC keys standing + one while running, with per-frame UpperBody / DefaultSlot checks
       against the jutsu's own seal / finisher assets and the component's delegates, and the results resolved
       (clone actor + AI, fireball actor travel, ground seal, hand effect).
gasp:  spawn record + the same perf windows (reference).
"""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

CFG = json.loads(Path(os.environ["V_CFG"]).read_text(encoding="utf-8"))
OUT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/verify/game") / CFG["tag"]
OUT.mkdir(parents=True, exist_ok=True)
V = unreal.Vector
REP = {"cfg": CFG, "engine": unreal.SystemLibrary.get_engine_version(), "log": [], "res": {}}
G = {"pc": None, "pawn": None, "gen": None, "wait_until": 0.0, "frame_cb": None, "t0": time.time(), "dts": None,
     "last": None, "handle": None, "events": [], "keep": []}


def log(m):
    REP["log"].append(f"{time.time() - G['t0']:.2f} {m}")
    unreal.log(f"VPROBE {m}")


def cmd(c):
    unreal.SystemLibrary.execute_console_command(G["pc"], c, G["pc"])


def key(k, down):
    cmd(f"Input.{'+' if down else '-'}key {k}")


def r1(x):
    return round(float(x), 1)


def v3(v):
    return [r1(v.x), r1(v.y), r1(v.z)]


def comp(actor, cls_name):
    for c in actor.get_components_by_class(unreal.ActorComponent):
        if c.get_class().get_name() == cls_name:
            return c
    return None


def cvar_i(n):
    return unreal.SystemLibrary.get_console_variable_int_value(n)


def cam():
    p, pc = G["pawn"], G["pc"]
    cm = pc.player_camera_manager
    cl = cm.get_camera_location()
    yaw = math.radians(pc.get_control_rotation().yaw)
    off = cl - p.get_actor_location()
    return {"lateral_cm": r1(-off.x * math.sin(yaw) + off.y * math.cos(yaw)),
            "behind_cm": r1(-(off.x * math.cos(yaw) + off.y * math.sin(yaw))), "above_cm": r1(off.z),
            "fov": r1(cm.get_fov_angle()), "cvar": cvar_i("DDCVar.NewGameplayCameraSystem.Enable")}


def cmc_rec(p):
    m = p.get_component_by_class(unreal.CharacterMovementComponent)
    cap = p.get_component_by_class(unreal.CapsuleComponent)
    out = {"class": p.get_class().get_name(), "capsule_r": r1(cap.get_scaled_capsule_radius()),
           "capsule_hh": r1(cap.get_scaled_capsule_half_height())}
    for n in ("max_walk_speed", "jump_z_velocity", "max_step_height", "max_acceleration", "braking_deceleration_walking",
              "ground_friction", "gravity_scale", "air_control"):
        try:
            out[n] = r1(m.get_editor_property(n))
        except Exception as e:  # noqa: BLE001
            out[n] = str(e)[:40]
    try:
        out["jump_max_count"] = int(p.get_editor_property("jump_max_count"))
    except Exception as e:  # noqa: BLE001
        out["jump_max_count"] = str(e)[:40]
    return out


def visual():
    p = G["pawn"]
    rec = {"components": sorted(f"{c.get_name()}:{c.get_class().get_name()}"
                                for c in p.get_components_by_class(unreal.ActorComponent))}
    rec["gasp_mesh_visible"] = bool(p.mesh.is_visible()) if p.mesh else None
    rec["gasp_mesh_hidden_in_game"] = bool(p.mesh.get_editor_property("hidden_in_game")) if p.mesh else None
    va = None
    for c in p.get_components_by_class(unreal.ChildActorComponent):
        a = c.get_editor_property("child_actor")
        rec.setdefault("child_actors", []).append(f"{c.get_name()}->{a.get_class().get_name() if a else None}")
        if a is not None and a.get_class().get_name().startswith("BP_NinjaVisual"):
            va = a
    if va is None:
        return rec
    vb = comp(va, "NinjaVisualBodyComponent")
    rec["visual_actor"] = va.get_class().get_name()
    if vb is None:
        return rec
    body, host = vb.get_meta_human_body(), vb.get_host_mesh()
    rec["metahuman_active"] = bool(vb.is_meta_human_active())
    if host is not None:
        rec["host"] = {"mesh": host.get_skeletal_mesh_asset().get_name(), "visible": bool(host.is_visible()),
                       "hidden_in_game": bool(host.get_editor_property("hidden_in_game"))}
    if body is not None:
        mh = body.get_owner()
        rec["body"] = {"mesh": body.get_skeletal_mesh_asset().get_name(), "visible": bool(body.is_visible()),
                       "owner": mh.get_class().get_path_name(), "hidden_owner": bool(mh.is_hidden_ed()) if hasattr(mh, "is_hidden_ed") else None}
        rec["mh_skeletal"] = []
        for c in mh.get_components_by_class(unreal.SkeletalMeshComponent):
            sm = c.get_skeletal_mesh_asset()
            rec["mh_skeletal"].append(f"{c.get_name()}:{sm.get_name() if sm else None}:vis={bool(c.is_visible())}")
        rec["grooms"] = []
        for c in mh.get_components_by_class(unreal.ActorComponent):
            if c.get_class().get_name() == "GroomComponent":
                try:
                    ga = c.get_editor_property("groom_asset")
                except Exception:  # noqa: BLE001
                    ga = None
                rec["grooms"].append(f"{c.get_name()}:{ga.get_name() if ga else None}:vis={bool(c.is_visible())}")
    rec["garments"] = []
    for g in vb.get_meta_human_garments() or []:
        sm = g.get_skeletal_mesh_asset()
        lp = g.get_editor_property("leader_pose_component")
        gi = {"name": g.get_name(), "mesh": sm.get_name() if sm else None, "visible": bool(g.is_visible()),
              "leader": lp.get_name() if lp else None, "attach": g.get_attach_parent().get_name() if g.get_attach_parent() else None}
        try:
            gi["cloth_suspended"] = bool(g.is_clothing_simulation_suspended())
        except Exception as e:  # noqa: BLE001
            gi["cloth_suspended"] = str(e)[:60]
        rec["garments"].append(gi)
        G["cloak"] = g
    G["vis_mesh"] = None
    j = comp(p, "NinjaJutsuComponent")
    if j is not None:
        G["vis_mesh"] = j.get_visual_mesh()
        rec["jutsu_visual_mesh"] = f"{G['vis_mesh'].get_name()}:{G['vis_mesh'].get_skeletal_mesh_asset().get_name()}" if G["vis_mesh"] else None
    return rec


def cloth():
    g = G.get("cloak")
    if g is None:
        return None
    out = {"p.ClothPhysics": cvar_i("p.ClothPhysics")}
    try:
        it = g.get_clothing_simulation_interactor()
        out["interactor"] = it.get_class().get_name() if it else None
        if it:
            for n in ("get_num_cloths", "get_num_dynamic_particles", "get_num_kinematic_particles", "get_simulation_time"):
                try:
                    out[n[4:]] = round(float(getattr(it, n)()), 4)
                except Exception as e:  # noqa: BLE001
                    out[n[4:]] = str(e)[:40]
    except Exception as e:  # noqa: BLE001
        out["err"] = str(e)[:80]
    try:
        out["suspended"] = bool(g.is_clothing_simulation_suspended())
    except Exception:  # noqa: BLE001
        pass
    return out


def slots():
    m = G.get("vis_mesh")
    ai = m.get_anim_instance() if m else None
    if ai is None:
        return {}
    out = {}
    try:
        out["upper_active"] = bool(ai.is_slot_active("UpperBody"))
        out["default_active"] = bool(ai.is_slot_active("DefaultSlot"))
    except Exception as e:  # noqa: BLE001
        out["slot_err"] = str(e)[:50]
    try:
        out["seal_w"] = round(float(ai.get_editor_property("NinjaSealWeight")), 3)
    except Exception as e:  # noqa: BLE001
        out["seal_w"] = str(e)[:40]
    j = comp(G["pawn"], "NinjaJutsuComponent")
    cj = j.get_casting_jutsu() if j else None
    fj = j.get_finishing_jutsu() if j else None
    out["casting"] = cj.get_name() if cj else None
    out["finishing"] = fj.get_name() if fj else None
    if cj is not None:
        seals = list(cj.get_editor_property("seals"))
        up = [s.get_name() for s in seals if s and pslot(ai, s, "UpperBody")]
        dn = [s.get_name() for s in seals if s and pslot(ai, s, "DefaultSlot")]
        out["seal_on_upper"] = up
        out["seal_on_default"] = dn
        op = cj.get_editor_property("opening_animation")
        if op is not None and pslot(ai, op, "UpperBody"):
            out["opening_on_upper"] = op.get_name()
    if fj is not None:
        fa = fj.get_editor_property("finisher_animation")
        out["finisher_on_default"] = bool(fa and pslot(ai, fa, "DefaultSlot"))
        out["finisher_on_upper"] = bool(fa and pslot(ai, fa, "UpperBody"))
    return out


def pslot(ai, asset, slot):
    try:
        r = ai.is_playing_slot_animation(asset, slot)
    except Exception:  # noqa: BLE001
        return False
    if isinstance(r, tuple):
        r = r[0]
    return bool(r)


def gasp_montage():
    p = G["pawn"]
    ai = p.mesh.get_anim_instance() if p.mesh else None
    m = ai.get_current_active_montage() if ai else None
    return m.get_name() if m else None


def counts():
    out = {}
    for n in ("NinjaFireball", "NinjaGroundSeal", "NinjaHandEffect"):
        cls = getattr(unreal, n, None)
        out[n] = len(unreal.GameplayStatics.get_all_actors_of_class(G["pc"], cls)) if cls else None
    ninjas = unreal.GameplayStatics.get_all_actors_of_class(G["pc"], G["pawn"].get_class())
    out["pawns_of_class"] = len(ninjas)
    cl = []
    for a in ninjas:
        j = comp(a, "NinjaJutsuComponent")
        if j is not None and j.is_shadow_clone():
            ctrl = a.get_controller()
            vis = None
            for c in a.get_components_by_class(unreal.ChildActorComponent):
                ca = c.get_editor_property("child_actor")
                if ca is not None:
                    vb = comp(ca, "NinjaVisualBodyComponent")
                    if vb is not None and vb.get_meta_human_body() is not None:
                        vis = bool(vb.get_meta_human_body().is_visible())
            cl.append({"name": a.get_name(), "ctrl": ctrl.get_class().get_name() if ctrl else None,
                       "leader": j.get_clone_leader().get_name() if j.get_clone_leader() else None,
                       "loc": v3(a.get_actor_location()), "mh_visible": vis})
    out["clones"] = cl
    fb = getattr(unreal, "NinjaFireball", None)
    if fb:
        out["fireball_locs"] = [v3(a.get_actor_location()) for a in unreal.GameplayStatics.get_all_actors_of_class(G["pc"], fb)]
    he = getattr(unreal, "NinjaHandEffect", None)
    if he:
        hs = unreal.GameplayStatics.get_all_actors_of_class(G["pc"], he)
        out["hand_effect"] = [{"cls": a.get_class().get_name(), "parent": a.get_attach_parent_actor().get_class().get_name() if a.get_attach_parent_actor() else None,
                               "loc": v3(a.get_actor_location())} for a in hs]
    gs = getattr(unreal, "NinjaGroundSeal", None)
    if gs:
        out["ground_seal"] = [{"cls": a.get_class().get_name(), "loc": v3(a.get_actor_location())}
                              for a in unreal.GameplayStatics.get_all_actors_of_class(G["pc"], gs)]
    return out


def shot(name, w=1920, h=1080):
    cmd(f"HighResShot filename={(OUT / name).as_posix()} {w}x{h}")
    REP.setdefault("shots", []).append(name)


def teleport_bl(x, y, z, face):
    p = G["pawn"]
    hh = p.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
    yaw = math.degrees(math.atan2(-face[1], face[0]))
    try:
        p.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
    except Exception:  # noqa: BLE001
        pass
    p.set_actor_location_and_rotation(V(x * 100.0, -y * 100.0, z * 100.0 + hh + 2.0), unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False, True)
    G["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=-10.0, yaw=yaw))
    return yaw


def ctrl_yaw(yaw, pitch=-10.0):
    G["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))


def speed():
    return r1(G["pawn"].get_velocity().length())


# ---------------------------------------------------------------- frame recorder
def rec_start(fn):
    G["frame_cb"] = fn
    G["rows"] = []


def rec_stop():
    G["frame_cb"] = None
    return G.pop("rows", [])


# ---------------------------------------------------------------- jutsu event binding
def bind_jutsu(j):
    def on_seal(jutsu, idx):
        G["events"].append(["seal", jutsu.get_name() if jutsu else None, int(idx), round(time.time() - G["cast_t0"], 3)])

    def on_done(jutsu):
        G["events"].append(["completed", jutsu.get_name() if jutsu else None, -1, round(time.time() - G["cast_t0"], 3)])

    def on_cancel(jutsu, idx):
        G["events"].append(["cancelled", jutsu.get_name() if jutsu else None, int(idx), round(time.time() - G["cast_t0"], 3)])

    def on_plant(jutsu, loc, rot):
        G["events"].append(["hand_planted", jutsu.get_name() if jutsu else None, v3(loc), round(time.time() - G["cast_t0"], 3)])

    def on_clone(c):
        G["events"].append(["clone_spawned", c.get_name() if c else None, -1, round(time.time() - G["cast_t0"], 3)])

    ok = {}
    for dn, fn in (("on_jutsu_seal", on_seal), ("on_jutsu_completed", on_done), ("on_jutsu_cancelled", on_cancel),
                   ("on_jutsu_hand_planted", on_plant), ("on_clone_spawned", on_clone)):
        try:
            getattr(j, dn).add_callable(fn)
            G["keep"].append(fn)
            ok[dn] = True
        except Exception as e:  # noqa: BLE001
            ok[dn] = str(e)[:80]
    return ok


# ---------------------------------------------------------------- the script
def perf_window(tag, secs):
    G["dts"] = []
    yield secs
    d = sorted(G["dts"])
    G["dts"] = None
    n = len(d)
    if n:
        REP["res"].setdefault("perf", {})[tag] = {"frames": n, "mean_ms": round(sum(d) / n, 3), "median_ms": round(d[n // 2], 3),
                                                  "p95_ms": round(d[min(n - 1, int(0.95 * n))], 3), "p99_ms": round(d[min(n - 1, int(0.99 * n))], 3),
                                                  "max_ms": round(d[-1], 3)}
        log(f"perf {tag} {REP['res']['perf'][tag]}")


def gait(tag, keys, hold, face_bl, start_bl):
    yaw = teleport_bl(start_bl[0], start_bl[1], 0.0, face_bl)
    yield 1.0
    rows = []
    rec_start(lambda: rows.append({"t": round(time.time() - G["g0"], 2), "v": speed(), "cam": cam()}))
    G["g0"] = time.time()
    for k in keys:
        key(k, True)
        yield 0.05
    t = time.time()
    while time.time() - t < hold:
        ctrl_yaw(yaw)
        yield None
    for k in reversed(keys):
        key(k, False)
    yield 1.0
    rec_stop()
    vs = [r["v"] for r in rows]
    lat = [abs(r["cam"]["lateral_cm"]) for r in rows]
    REP["res"].setdefault("gaits", {})[tag] = {"max_speed": max(vs) if vs else None,
                                               "speed_last_held": [r["v"] for r in rows if r["t"] <= hold][-1:] if rows else None,
                                               "cam_lateral_abs_max_cm": max(lat) if lat else None,
                                               "cam_behind_cm": rows[len(rows) // 2]["cam"]["behind_cm"] if rows else None}
    log(f"gait {tag} {REP['res']['gaits'][tag]}")


def traverse(tag, stance, face, floor_z, marker_top, shot_name=None):
    back = 2.0
    start = (stance[0] - back * face[0], stance[1] - back * face[1])
    yaw = teleport_bl(start[0], start[1], floor_z, face)
    yield 1.2
    p = G["pawn"]
    z0 = p.get_actor_location().z
    rows = []
    rec_start(lambda: rows.append({"z": p.get_actor_location().z, "m": gasp_montage(), "mode": str(p.get_component_by_class(unreal.CharacterMovementComponent).movement_mode)}))
    key("W", True)
    pressed = None
    t = time.time()
    shot_done = False
    while time.time() - t < 4.0:
        ctrl_yaw(yaw)
        loc = p.get_actor_location()
        along = ((loc.x / 100.0 - start[0]) * face[0] + (-loc.y / 100.0 - start[1]) * face[1])
        if pressed is None and along >= back - 0.3:
            key("SpaceBar", True)
            pressed = time.time()
        if pressed is not None and time.time() - pressed > 0.12:
            key("SpaceBar", False)
        if shot_name and not shot_done and pressed is not None and time.time() - pressed > 0.45:
            shot(shot_name)
            shot_done = True
        if pressed is not None and time.time() - pressed > 2.0:
            break
        yield None
    key("W", False)
    yield 1.5
    rec_stop()
    cap = p.get_component_by_class(unreal.CapsuleComponent)
    feet = (p.get_actor_location().z - cap.get_scaled_capsule_half_height()) / 100.0
    res = {"marker_top_m": marker_top, "end_feet_m": round(feet, 3), "rise_cm": r1(max(r["z"] for r in rows) - z0) if rows else None,
           "gasp_montages": sorted({r["m"] for r in rows if r["m"]}), "modes": sorted({r["mode"] for r in rows}),
           "space_pressed": pressed is not None, "on_top": abs(feet - marker_top) < 0.15}
    REP["res"].setdefault("traversal", {})[tag] = res
    log(f"traversal {tag} {res}")


def cast(tag, keyname, run_keys=(), front_shot=None, shot_at=0.5, max_s=9.0):
    p = G["pawn"]
    j = comp(p, "NinjaJutsuComponent")
    G["events"] = []
    rows = []
    c0 = counts()
    G["cast_t0"] = time.time()
    rec_start(lambda: rows.append({"t": round(time.time() - G["cast_t0"], 3), "v": speed(), **slots(), "n": counts()}))
    for k in run_keys:
        key(k, True)
    if run_keys:
        t = time.time()
        while time.time() - t < 1.2:
            yield None
        G["cast_t0"] = time.time()
        rows.clear()
    key(keyname, True)
    yield 0.12
    key(keyname, False)
    shot_done = front_shot is None
    t = time.time()
    while time.time() - t < max_s:
        if not shot_done and time.time() - t >= shot_at:
            shot(front_shot)
            shot_done = True
        if (time.time() - t > 2.0 and not j.is_casting_jutsu() and not j.is_finishing()
                and any(e[0] in ("completed", "cancelled") for e in G["events"]) and time.time() - t > 4.5):
            break
        yield None
    for k in run_keys:
        key(k, False)
    yield 0.5
    rec_stop()
    cast_rows = [r for r in rows if r.get("casting")]
    fin_rows = [r for r in rows if r.get("finishing")]
    res = {"key": keyname, "run_keys": list(run_keys),
           "events": G["events"][:], "seal_events": sum(1 for e in G["events"] if e[0] == "seal"),
           "completed": any(e[0] == "completed" for e in G["events"]), "cancelled": any(e[0] == "cancelled" for e in G["events"]),
           "casting_rows": len(cast_rows),
           "casting_rows_seal_on_upper": sum(1 for r in cast_rows if r.get("seal_on_upper") or r.get("opening_on_upper")),
           "casting_rows_upper_active": sum(1 for r in cast_rows if r.get("upper_active")),
           "casting_rows_seal_on_default": sum(1 for r in cast_rows if r.get("seal_on_default")),
           "seal_assets_seen": sorted({s for r in cast_rows for s in (r.get("seal_on_upper") or [])}),
           "seal_w_max": max([r.get("seal_w") for r in rows if isinstance(r.get("seal_w"), float)] or [None]),
           "finish_rows": len(fin_rows), "finish_rows_on_default": sum(1 for r in fin_rows if r.get("finisher_on_default")),
           "speed_while_casting": [min([r["v"] for r in cast_rows] or [0]), max([r["v"] for r in cast_rows] or [0])],
           "counts_before": {k: v for k, v in c0.items() if k in ("NinjaFireball", "NinjaGroundSeal", "NinjaHandEffect", "pawns_of_class")},
           "max_counts": {k: max([r["n"].get(k) or 0 for r in rows] or [0]) for k in ("NinjaFireball", "NinjaGroundSeal", "NinjaHandEffect", "pawns_of_class")},
           "counts_end": {k: v for k, v in counts().items() if k in ("NinjaFireball", "NinjaGroundSeal", "NinjaHandEffect", "pawns_of_class")},
           "clones_end": counts().get("clones")}
    fbs = [loc for r in rows for loc in r["n"].get("fireball_locs", [])]
    if fbs:
        pl = p.get_actor_location()
        res["fireball_max_dist_cm"] = r1(max(math.hypot(f[0] - pl.x, f[1] - pl.y) for f in fbs))
        res["fireball_rows"] = sum(1 for r in rows if r["n"].get("fireball_locs"))
    he = [h for r in rows for h in r["n"].get("hand_effect", [])]
    if he:
        res["hand_effect_classes"] = sorted({h["cls"] for h in he})
        res["hand_effect_parent"] = sorted({str(h["parent"]) for h in he})
        res["hand_effect_rows"] = sum(1 for r in rows if r["n"].get("hand_effect"))
    gs = [h for r in rows for h in r["n"].get("ground_seal", [])]
    if gs:
        res["ground_seal_classes"] = sorted({h["cls"] for h in gs})
        res["ground_seal_loc_first"] = gs[0]["loc"]
    REP["res"].setdefault("jutsu", {})[tag] = res
    log(f"jutsu {tag}: seals {res['seal_events']} completed {res['completed']} upper {res['casting_rows_seal_on_upper']}/{res['casting_rows']} max {res['max_counts']}")


def script():
    p = G["pawn"]
    pc = G["pc"]
    gm = unreal.GameplayStatics.get_game_mode(pc)
    REP["res"]["spawn"] = {"pawn": p.get_class().get_path_name(), "game_mode": gm.get_class().get_path_name() if gm else None,
                           "map": unreal.GameplayStatics.get_current_level_name(pc), "loc": v3(p.get_actor_location()),
                           "yaw": r1(p.get_actor_rotation().yaw)}
    REP["res"]["cmc_spawn"] = cmc_rec(p)
    REP["res"]["cam_spawn"] = cam()
    if CFG["mode"] == "ninja":
        REP["res"]["visual_spawn"] = visual()
        REP["res"]["cloth_spawn"] = cloth()
        j = comp(p, "NinjaJutsuComponent")
        REP["res"]["bind"] = bind_jutsu(j)
        REP["res"]["jutsu_list"] = [f"{x.get_name()}:{x.get_editor_property('input_action').get_name() if x.get_editor_property('input_action') else None}" for x in j.get_editor_property("jutsus")]
        imc = j.get_editor_property("input_mapping_context")
        try:
            REP["res"]["imc"] = [[str(m.get_editor_property("key").get_editor_property("key_name")), m.get_editor_property("action").get_name()]
                                 for m in imc.get_editor_property("mappings")]
        except Exception as e:  # noqa: BLE001
            REP["res"]["imc"] = str(e)[:100]
    log(f"spawn {REP['res']['spawn']}")
    yield float(CFG.get("warm_s", 90))
    REP["res"]["cam_after_warm"] = cam()
    # ---- perf at the spawn, gameplay camera (the state the player starts in), 3 windows
    for i in range(3):
        yield from perf_window(f"spawn_{i}", 10.0)
        yield 1.0
    if CFG["mode"] != "ninja":
        return
    REP["res"]["visual_after_warm"] = visual()
    # ---- cloth: idle sample, then run -> stop with side shots
    cl = []
    for _ in range(10):
        cl.append(cloth())
        yield 0.1
    REP["res"]["cloth_idle"] = cl
    yaw = teleport_bl(8.0, 12.0, 0.0, (1, 0))
    yield 1.5
    shot("C00_idle_back.png")
    yield 1.0
    cl = []
    # camera looks along yaw-90, so D (camera right = yaw) runs him east while the camera sees his right side
    ctrl_yaw(yaw - 90.0, -5.0)
    yield 0.5
    key("D", True)
    t = time.time()
    while time.time() - t < 2.5:
        ctrl_yaw(yaw - 90.0, -5.0)
        cl.append(cloth())
        yield 0.1
    key("D", False)
    REP["res"]["cloth_run"] = cl
    yield 0.25
    shot("C01_stop_0.25s_side.png")
    yield 2.0
    shot("C02_stop_2.3s_side.png")
    # ---- gaits + camera while running
    yield from gait("run_W", ["W"], 2.5, (1, 0), (8.0, 12.0))
    yield from gait("sprint_Shift_W", ["LeftShift", "W"], 2.2, (1, 0), (8.0, 12.0))
    key("LeftControl", True)
    yield 0.1
    key("LeftControl", False)
    yield from gait("walk_Ctrl_W", ["W"], 2.5, (1, 0), (8.0, 12.0))
    key("LeftControl", True)
    yield 0.1
    key("LeftControl", False)
    yield 0.5
    # ---- traversals (my picks)
    yield from traverse("Cistern_E", (30.35, 18.94), (0, 1), 0.0, 1.25, "T01_cistern_mid.png")
    yield from traverse("Wall_E_S", (43.64, 10.0), (1, 0), 0.0, 2.0)
    yield from traverse("Pavilion_Plinth", (38.64, 3.0), (1, 0), 0.0, 1.0)
    # ---- jutsu: standing at the courtyard centre facing east; the camera turned to the front for the hand shots
    jl = {"ShadowClone": "F", "GreatFireball": "Two", "Summoning": "Three", "Chidori": "Four"}
    for name, k in jl.items():
        yaw = teleport_bl(16.0, 14.0, 0.0, (1, 0))
        yield 1.5
        ctrl_yaw(yaw + 180.0, -8.0)      # look at his front
        yield 0.8
        yield from cast(f"stand_{name}", k, front_shot=f"J_{name}_seal_front.png", shot_at=0.45)
        yield 0.5
        if name == "ShadowClone":
            ctrl_yaw(yaw + 150.0, -12.0)
            yield 0.6
            shot("J_ShadowClone_result.png")
            REP["res"]["clones_after_F"] = counts()
            yield 0.5
        if name == "Summoning":
            ctrl_yaw(yaw + 180.0, -35.0)
            yield 0.3
            shot("J_Summoning_result.png")
        yield 2.0
    # running cast (seal layer over the run)
    yaw = teleport_bl(6.0, 12.0, 0.0, (1, 0))
    yield 1.5
    yield from cast("run_GreatFireball", "Two", run_keys=("W",))
    yaw = teleport_bl(6.0, 12.0, 0.0, (1, 0))
    yield 1.5
    yield from cast("run_ShadowClone", "F", run_keys=("W",))
    REP["res"]["counts_end"] = counts()
    REP["res"]["cmc_end"] = cmc_rec(p)
    REP["res"]["cam_end"] = cam()


def finish(ok):
    REP["passed_run"] = ok
    REP["sec"] = round(time.time() - G["t0"], 1)
    (OUT / "report.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"VPROBE_DONE ok={ok}")
    if G["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(G["handle"])
        G["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def find_pc():
    for pc in unreal.ObjectIterator(unreal.PlayerController):
        try:
            if pc.get_name().startswith("Default__") or pc.get_world() is None:
                continue
            return pc
        except Exception:  # noqa: BLE001
            continue
    return None


def tick(dt):
    now = time.time()
    try:
        if G["last"] is not None and G["dts"] is not None:
            G["dts"].append((now - G["last"]) * 1000.0)
        G["last"] = now
        if G["pc"] is None:
            pc = find_pc()
            pawn = pc.get_controlled_pawn() if pc else None
            if pawn is not None and now - G["t0"] > 3.0:
                G["pc"], G["pawn"] = pc, pawn
                cmd("au.MuteAudio 1")
                G["gen"] = script()
                G["wait_until"] = 0.0
            elif now - G["t0"] > 300:
                log("no pawn after 300 s")
                finish(False)
            return
        if G["frame_cb"] is not None:
            G["frame_cb"]()
        if now < G["wait_until"]:
            return
        try:
            w = next(G["gen"])
        except StopIteration:
            finish(True)
            return
        G["wait_until"] = now + (w or 0.0)
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        log("ERROR " + REP["error"][-400:])
        finish(False)


G["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
