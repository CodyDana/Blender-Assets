"""DojoLab ninja port, perf2 stage (CLEAN PERF PROFILE + lever scratch tests). ONE offscreen UnrealEditor-Cmd -game run
of L_Dojo (launched by WorkFiles/dojo/build/ninja_character/perf2/tools/run_perf2.ps1 with -ExecCmds="py <this>",
config env DJ_PT_CFG). Read-only for the project: every lever is a RUNTIME change in this -game session (component
properties / cvars / visibility), restored after its window; nothing is saved (a -game world is never saved).

Method = dj_ninja_perf.py (the finish stage's perf_cool): `scalability 3`, t.MaxFPS 0, no vsync, r.setres 1920x1080w,
r.ScreenPercentage 0 (the project curve: 100 % at 1080p), the controlled pawn placed on the floor DIST cm in front of a
camera facing it; plus per sample window `csvprofile start/stop` (-csvGpuStats: FrameTime / GameThread / RenderThread /
RHI / GPU and the per-pass GPU and render-thread stats), optional HighResShot after the window (visual cost of a lever),
optional ProfileGPU (log dump), optional jutsu cast by its real key (Input.+key) with the window inside the effect.

Config: {"out": abs json, "shots": abs dir, "warm_s": 45, "warm_views": [...], "warm_per_s": 6, "settle_s": 8,
         "sample_s": 10, "dist": {cam: cm}, "steps": [{"view", "toggles": [], "label", "kind": "sample"|"visit"|"probe",
         "settle_s", "sample_s", "shot": name, "profilegpu": bool, "cast": key, "cast_delay_s", "post_s"}],
         "light_dist_cm": 2500, "light_fade_cm": 500, "groom_lod": 2}
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
SHOTS = Path(CFG.get("shots", str(OUT.parent / "shots")))
V = unreal.Vector
CVARS = ["scalability 3", "t.MaxFPS 0", "r.VSync 0", "r.ScreenPercentage 0", "r.setres 1920x1080w",
         "r.GPUCsvStatsEnabled 1", "r.GPUStatsEnabled 1"]
WATCH_CV = ["r.ScreenPercentage", "sg.ResolutionQuality", "r.ScreenPercentage.Default", "r.ScreenPercentage.Default.Desktop.Mode",
            "r.AntiAliasingMethod", "r.SkinCache.Mode", "r.SkinCache.CompileShaders", "r.SkinCache.DefaultBehavior",
            "r.HairStrands.Enable", "r.HairStrands.Strands", "r.HairStrands.Simulation", "r.HairStrands.Binding",
            "p.ClothPhysics", "r.RayTracing", "r.RayTracing.Enable", "r.RayTracing.Geometry.NiagaraSprites",
            "r.RayTracing.Geometry.NiagaraRibbons", "r.RayTracing.Geometry.NiagaraMeshes", "r.RayTracing.Culling.Radius",
            "r.Lumen.HardwareRayTracing", "r.MegaLights.Allow", "r.MegaLights.EnableForProject",
            "r.Shadow.Virtual.Enable", "sg.ShadowQuality", "sg.ViewDistanceQuality", "r.SkeletalMeshLODBias"]
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "segments": [], "events": [], "cfg": CFG, "placements": {},
       "toggle_log": [], "probes": []}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "i": 0, "pc": None, "cams": {}, "handle": None,
      "dts": [], "home": None, "restore": [], "cast_t": None, "released": False, "shot_path": None}
STEPS = CFG["steps"]


def log(m):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {m}")
    unreal.log(f"DJ_NPERF2 {m}")


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


def all_actors(cls=unreal.Actor):
    return unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], cls)


# ------------------------------------------------------------------------------------------------ the pawn's actor tree
def pawn_tree():
    p = ST["pc"].get_controlled_pawn()
    seen, todo = [], [p]
    while todo:
        a = todo.pop()
        if a is None or a in seen:
            continue
        seen.append(a)
        for c in a.get_components_by_class(unreal.ChildActorComponent):
            todo.append(c.get_editor_property("child_actor"))
        try:
            todo.extend(a.get_attached_actors())
        except Exception:  # noqa: BLE001
            pass
    return seen


def tree_comps(cls):
    out = []
    for a in pawn_tree():
        out.extend(a.get_components_by_class(cls))
    return out


def has_cloth(skm):
    try:
        it = skm.get_clothing_simulation_interactor()
        return it is not None and int(it.get_num_cloths()) > 0
    except Exception:  # noqa: BLE001
        return False


def pawn_inventory():
    """what the controlled pawn renders: skeletal meshes (LODs, cloth), grooms, Niagara"""
    inv = {"actors": [a.get_class().get_name() for a in pawn_tree()], "skm": [], "groom": [], "niagara": []}
    for c in tree_comps(unreal.SkeletalMeshComponent):
        m = None
        try:
            m = c.get_editor_property("skeletal_mesh_asset")
        except Exception:  # noqa: BLE001
            try:
                m = c.get_editor_property("skeletal_mesh")
            except Exception:  # noqa: BLE001
                pass
        r = {"comp": c.get_name(), "owner": c.get_owner().get_class().get_name(), "mesh": m.get_name() if m else None,
             "visible": bool(c.is_visible()), "cloth": has_cloth(c)}
        try:
            r["num_lods"] = int(c.get_num_lods())
        except Exception:  # noqa: BLE001
            pass
        try:
            r["predicted_lod"] = int(c.get_predicted_lod_level())
        except Exception:  # noqa: BLE001
            pass
        inv["skm"].append(r)
    for c in tree_comps(unreal.GroomComponent):
        g = None
        try:
            g = c.get_editor_property("groom_asset")
        except Exception:  # noqa: BLE001
            pass
        r = {"comp": c.get_name(), "groom": g.get_name() if g else None, "visible": bool(c.is_visible())}
        try:
            r["num_lods"] = int(c.get_num_lods())
        except Exception as e:  # noqa: BLE001
            r["num_lods_err"] = str(e)[:80]
        try:
            r["desired_lod"] = int(c.get_desired_lod())
        except Exception:  # noqa: BLE001
            pass
        inv["groom"].append(r)
    for c in tree_comps(unreal.NiagaraComponent):
        inv["niagara"].append({"comp": c.get_name(), "rt": bool(c.get_editor_property("visible_in_ray_tracing")),
                               "active": bool(c.is_active())})
    return inv


def niagara_rt_census():
    """every Niagara component in the world: how many are in the ray tracing scene (visible_in_ray_tracing True)"""
    n = rt = act = act_rt = 0
    names = {}
    for c in unreal.ObjectIterator(unreal.NiagaraComponent):
        try:
            if c.get_world() is None or c.get_name().startswith("Default__"):
                continue
            n += 1
            a = bool(c.is_active())
            r = bool(c.get_editor_property("visible_in_ray_tracing"))
            act += a
            rt += r
            if r and a:
                act_rt += 1
                s = c.get_asset()
                k = s.get_name() if s else "None"
                names[k] = names.get(k, 0) + 1
        except Exception:  # noqa: BLE001
            continue
    return {"niagara": n, "active": act, "rt_flag": rt, "active_rt": act_rt, "active_rt_systems": names}


# --------------------------------------------------------------------------------------------------- level pieces
def interior_lights():
    out = []
    for a in all_actors():
        if unreal.Name("DJ_ArmoryHall") not in list(a.tags):
            continue
        out.extend(a.get_components_by_class(unreal.LocalLightComponent))
    return out


def winpaper_smcs():
    out = []
    for a in all_actors(unreal.StaticMeshActor):
        c = a.static_mesh_component
        m = c.static_mesh
        if m is not None and ("Window_Paper" in m.get_name() or "WinPaper" in m.get_name()):
            out.append(c)
    return out


# ---------------------------------------------------------------------------------------------------------- toggles
def undo_all():
    for fn in reversed(ST["restore"]):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            log(f"restore error {e}")
    ST["restore"].clear()


def set_cvar(k, v):
    before = cv(k)
    cmd(f"{k} {v}")
    ST["restore"].append(lambda k=k, b=before: cmd(f"{k} {b if b is not None else 0}"))
    return {k: [before, cv(k)]}


def refresh(c):
    c.set_visibility(False, False)
    c.set_visibility(True, False)


def apply_toggle(tg):
    info = {"toggle": tg}
    if tg == "pawn_hidden":
        n = 0
        for a in pawn_tree():
            a.set_actor_hidden_in_game(True)
            ST["restore"].append(lambda a=a: a.set_actor_hidden_in_game(False))
            n += 1
        info["actors"] = n
    elif tg == "cloth_suspended":
        n = 0
        for c in tree_comps(unreal.SkeletalMeshComponent):
            if has_cloth(c):
                c.suspend_clothing_simulation()
                ST["restore"].append(lambda c=c: c.resume_clothing_simulation())
                n += 1
        info["cloth_comps"] = n
    elif tg == "cloth_physics_cvar_off":
        info["cvars"] = set_cvar("p.ClothPhysics", 0)
    elif tg == "groom_hidden":
        n = 0
        for c in tree_comps(unreal.GroomComponent):
            if c.is_visible():
                c.set_visibility(False, False)
                ST["restore"].append(lambda c=c: c.set_visibility(True, False))
                n += 1
        info["grooms"] = n
    elif tg.startswith("groom_lod"):
        lod = int(tg[len("groom_lod"):] or CFG.get("groom_lod", 2))
        n, errs = 0, []
        for c in tree_comps(unreal.GroomComponent):
            try:
                if c.get_editor_property("groom_asset") is None:
                    continue
            except Exception:  # noqa: BLE001
                pass
            try:
                c.set_forced_lod(lod)
                ST["restore"].append(lambda c=c: c.set_forced_lod(-1))
                n += 1
            except Exception as e:  # noqa: BLE001
                errs.append(str(e)[:100])
        info.update({"grooms": n, "errors": errs[:3]})
    elif tg.startswith("groom_minlod"):   # GroomComponent.SetForcedLOD is not exposed to Python: the engine cvar instead
        info["cvars"] = set_cvar("r.HairStrands.MinLOD", int(tg[len("groom_minlod"):]))
    elif tg == "groom_cards":
        info["cvars"] = set_cvar("r.HairStrands.UseCardsInsteadOfStrands", 1)
    elif tg == "groom_sim_off":
        info["cvars"] = set_cvar("r.HairStrands.Simulation", 0)
    elif tg.startswith("mh_lod"):
        lod = int(tg[len("mh_lod"):])
        n = 0
        for c in tree_comps(unreal.SkeletalMeshComponent):
            c.set_forced_lod(lod + 1)
            ST["restore"].append(lambda c=c: c.set_forced_lod(0))
            n += 1
        info["skm"] = n
    elif tg == "skin_cache_off":
        info["cvars"] = set_cvar("r.SkinCache.Mode", 0)
    elif tg == "niagara_rt_cvars_off":
        info["cvars"] = {}
        for k in ("r.RayTracing.Geometry.NiagaraSprites", "r.RayTracing.Geometry.NiagaraRibbons",
                  "r.RayTracing.Geometry.NiagaraMeshes"):
            info["cvars"].update(set_cvar(k, 0))
    elif tg.startswith("rt_cull"):
        info["cvars"] = set_cvar("r.RayTracing.Culling.Radius", int(tg[len("rt_cull"):]))
    elif tg == "niagara_hidden_all":
        n = 0
        for c in unreal.ObjectIterator(unreal.NiagaraComponent):
            try:
                if c.get_world() is None or c.get_name().startswith("Default__") or not c.is_visible():
                    continue
                c.set_visibility(False, False)
                ST["restore"].append(lambda c=c: c.set_visibility(True, False))
                n += 1
            except Exception:  # noqa: BLE001
                continue
        info["niagara"] = n
    elif tg.startswith("interior_light_dist"):
        d = float(tg[len("interior_light_dist"):] or CFG.get("light_dist_cm", 2500))
        fade = float(CFG.get("light_fade_cm", 500))
        cam = ST["pc"].player_camera_manager.get_camera_location()
        n = far = 0
        for c in interior_lights():
            b_d, b_f = c.get_editor_property("max_draw_distance"), c.get_editor_property("max_distance_fade_range")
            c.set_editor_property("max_draw_distance", d)
            c.set_editor_property("max_distance_fade_range", fade)
            refresh(c)

            def back(c=c, b_d=b_d, b_f=b_f):
                c.set_editor_property("max_draw_distance", b_d)
                c.set_editor_property("max_distance_fade_range", b_f)
                refresh(c)
            ST["restore"].append(back)
            n += 1
            far += (c.get_world_location() - cam).length() > d
        info.update({"lights": n, "beyond_dist_from_camera": far, "dist_cm": d, "fade_cm": fade})
    elif tg == "interior_lights_off":
        n = 0
        for c in interior_lights():
            if c.is_visible():
                c.set_visibility(False, False)
                ST["restore"].append(lambda c=c: c.set_visibility(True, False))
                n += 1
        info["lights"] = n
    elif tg == "interior_shadows_off":
        n = 0
        for c in interior_lights():
            if c.get_editor_property("cast_shadows"):
                c.set_cast_shadows(False)
                ST["restore"].append(lambda c=c: c.set_cast_shadows(True))
                n += 1
        info["lights"] = n
    elif tg == "winpaper_hidden":
        n = 0
        for c in winpaper_smcs():
            c.set_visibility(False, False)
            ST["restore"].append(lambda c=c: c.set_visibility(True, False))
            n += 1
        info["meshes"] = n
    elif tg == "winpaper_noshadow":
        n = 0
        for c in winpaper_smcs():
            if c.get_editor_property("cast_shadow"):
                c.set_cast_shadow(False)
                ST["restore"].append(lambda c=c: c.set_cast_shadow(True))
                n += 1
        info["meshes"] = n
    else:
        info["unknown"] = True
    REP["toggle_log"].append(info)
    return info


def apply_toggles(tgs):
    undo_all()
    return [apply_toggle(t) for t in (tgs or [])]


# -------------------------------------------------------------------------------------------------------- the views
def place_pawn(cam_name):
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
        ST["pc"].set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
        REP["placements"].setdefault(cam_name, {"dist_cm": d, "loc": [round(c.x, 1), round(c.y, 1), round(fz, 1)],
                                                "yaw": round(yaw, 1), "tried": tried})
        return True
    REP["placements"].setdefault(cam_name, {"failed": tried})
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
    if CFG.get("place_pawn", True):
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
    try:
        undo_all()
    except Exception:  # noqa: BLE001
        pass
    REP["passed_run"] = ok
    REP["sec"] = round(time.time() - ST["t0"], 1)
    REP["cvars_end"] = {k: cv(k) for k in WATCH_CV}
    OUT.write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")
    unreal.log(f"DJ_NPERF2_DONE ok={ok} segments={len(REP['segments'])}")
    if ST["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(ST["handle"])
        ST["handle"] = None
    try:
        cmd("quit")
    except Exception:  # noqa: BLE001
        pass


def step():
    return STEPS[ST["i"]]


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
                for a in all_actors(unreal.CineCameraActor):
                    ST["cams"][a.get_actor_label()] = a
                REP["pawn"] = p.get_class().get_path_name()
                REP["cvars_startup"] = {k: cv(k) for k in WATCH_CV}
                for c in CVARS:
                    cmd(c)
                REP["cvars_after"] = {k: cv(k) for k in WATCH_CV}
                pc.set_ignore_move_input(True)
                pc.set_ignore_look_input(True)
                REP["missing_cams"] = sorted({s["view"] for s in STEPS if s["view"] != "PAWN" and s["view"] not in ST["cams"]})
                REP["interior_lights"] = len(interior_lights())
                REP["winpaper"] = [{"actor": c.get_owner().get_actor_label(), "mesh": c.static_mesh.get_name(),
                                    "cast_shadow": bool(c.get_editor_property("cast_shadow")),
                                    "mats": [m.get_name() if m else None for m in c.get_materials()]}
                                   for c in winpaper_smcs()]
                log(f"world ready pawn {REP['pawn']} cams {len(ST['cams'])} missing {REP['missing_cams']}")
                v0 = CFG.get("warm_views", [STEPS[0]["view"]])[0]
                view(v0)
                ST["phase"], ST["t"] = "warm0", now
            elif el > 300:
                finish(False)
        elif ph == "warm0":
            if el >= float(CFG.get("warm_s", 45)):
                REP["pawn_inventory"] = pawn_inventory()
                REP["niagara_census_start"] = niagara_rt_census()
                ST["phase"], ST["t"], ST["wi"] = "warm", now, 0
                wv = CFG.get("warm_views", [])
                if wv:
                    view(wv[0])
        elif ph == "warm":
            wv = CFG.get("warm_views", [])
            if ST["wi"] >= len(wv) or el >= float(CFG.get("warm_per_s", 6)):
                ST["wi"] += 1
                ST["t"] = now
                if ST["wi"] >= len(wv):
                    ST["phase"], ST["i"] = "aim", 0
                else:
                    view(wv[ST["wi"]])
        elif ph == "aim":
            if ST["i"] >= len(STEPS):
                REP["niagara_census_end"] = niagara_rt_census()
                finish(True)
                return
            s = step()
            ok = view(s["view"])
            ST["tg_info"] = apply_toggles(s.get("toggles"))
            ST["cast_t"], ST["released"] = None, False
            log(f"step {ST['i']} {s.get('label', '')} {s['view']} {s.get('toggles')} view_ok={ok}")
            ST["phase"], ST["t"] = "settle", now
        elif ph == "settle":
            s = step()
            if el >= float(s.get("settle_s", CFG.get("settle_s", 8))):
                if s.get("kind") == "visit":
                    ST["i"] += 1
                    ST["phase"], ST["t"] = "aim", now
                    return
                if s.get("cast"):
                    cmd(f"Input.+key {s['cast']}")
                    ST["cast_t"] = now
                    ST["phase"], ST["t"] = "cast", now
                    return
                ST["dts"] = []
                if s.get("csv", True):
                    cmd("csvprofile start")
                ST["phase"], ST["t"], ST["seg_t0"] = "sample", now, now
        elif ph == "cast":
            s = step()
            if not ST["released"] and el >= 0.15:
                cmd(f"Input.-key {s['cast']}")
                ST["released"] = True
            if el >= float(s.get("cast_delay_s", 1.2)):
                ST["dts"] = []
                if s.get("csv", True):
                    cmd("csvprofile start")
                ST["phase"], ST["t"], ST["seg_t0"] = "sample", now, now
        elif ph == "sample":
            ST["dts"].append(float(dt))
            s = step()
            if el >= float(s.get("sample_s", CFG.get("sample_s", 10))):
                if s.get("csv", True):
                    cmd("csvprofile stop")
                p = ST["pc"].get_controlled_pawn()
                seg = {"i": ST["i"], "label": s.get("label"), "view": s["view"], "toggles": s.get("toggles") or [],
                       "toggle_info": ST.get("tg_info"), "cast": s.get("cast"), "csv": s.get("csv", True),
                       "cvar_screen_pct": cv("r.ScreenPercentage"), "wall_s": round(now - ST["seg_t0"], 2),
                       "frames": stats(ST["dts"][2:]), "t_s": round(now - ST["t0"], 1),
                       "pawn_loc": [round(p.get_actor_location().x, 1), round(p.get_actor_location().y, 1),
                                    round(p.get_actor_location().z, 1)]}
                if s.get("cast") or s.get("census"):
                    seg["niagara_census"] = niagara_rt_census()
                REP["segments"].append(seg)
                log(f"SAMPLE_END {ST['i']} {s.get('label')} {s['view']} {seg['frames']}")
                ST["phase"], ST["t"] = "post", now
                if s.get("shot"):
                    SHOTS.mkdir(parents=True, exist_ok=True)
                    path = SHOTS / s["shot"]
                    if path.exists():
                        path.unlink()
                    cmd(f"HighResShot filename={path.as_posix()} 1920x1080")
                    ST["shot_path"] = path
                if s.get("profilegpu"):
                    log(f"PROFILEGPU_BEGIN {ST['i']}")
                    cmd("ProfileGPU")
        elif ph == "post":
            s = step()
            sp = ST.get("shot_path")
            if sp is not None and not (sp.exists() and sp.stat().st_size > 0) and el < 20.0:
                return
            if el >= float(s.get("post_s", 4.0 if s.get("profilegpu") else 0.5)):
                if sp is not None:
                    REP.setdefault("shots", []).append({"i": ST["i"], "file": sp.name, "ok": sp.exists()})
                    ST["shot_path"] = None
                if s.get("profilegpu"):
                    log(f"PROFILEGPU_END {ST['i']}")
                ST["i"] += 1
                ST["phase"], ST["t"] = "aim", now
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        finish(False)


ST["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
