"""HALL + ARMORY VERIFIER: the landscape verifier's v10 -game perf script with the hall+armory views (incl. 3 interior
cameras and the GASP pawn eye), 1920x1080 and 2560x1440 at the configured screen percentage, no A/B toggles."""
"""VERIFY LANDSCAPE ROUND (independent verifier; the verify_r9 script + landscape views + A/B content toggles; r8 script with the configured screen percentage = r.ScreenPercentage 0): GPU frame time of L_Dojo in a real -game frame (UnrealEditor-Cmd -game
-RenderOffscreen -dx12, launched by run_v9_game_perf.ps1 as -ExecCmds="py <this file>"). Read-only for the project
content: writes only verify_r9/game_perf.json (+ the engine's own CSV profiles in DojoLab/Saved/Profiling/CSV and its log).

Per view (CAM_PlayerEyeSand, CAM_Overview, and the GASP pawn's own camera) and per output config (1920x1080 @100 %,
2560x1440 @100 / 75 / 67 %): r.setres + r.ScreenPercentage, set view target, settle, then sample every frame's delta
(Slate post-tick) for SAMPLE_S with `csvprofile start/stop` around it (GPU stats on), then one `ProfileGPU` (log dump).
Also records the RUNTIME environment twice (start and end): every directional / sky light / fog / atmosphere / cloud /
point light component, the UDS Time of Day and the Sun direction (time-of-day lock check).
Gameplay preset: `scalability 3` (Epic, research 5.1), t.MaxFPS 0, no vsync; everything else as the level/PPV sets it.
"""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/verify/perf/game_perf.json")
WARM_S, WARM_PER_S, SETTLE_S, SAMPLE_S, PROF_S = 40.0, 6.0, 9.0, 10.0, 4.0
VIEWS = ["CAM_PlayerEyeSand", "CAM_Overview", "CAM_RiverRapids", "CAM_StairPath", "CAM_AK_CW_WestAisle", "CAM_DoorwayIn",
         "CAM_AK_CX_FromPlatform", "CAM_RearExtension", "CAM_LandscapeRef", "PAWN"]
CONFIGS = [(1920, 1080, 0), (2560, 1440, 0)]   # 0 = the project-configured (display-based) screen percentage
CVARS = ["scalability 3", "t.MaxFPS 0", "r.VSync 0", "r.GPUCsvStatsEnabled 1", "r.GPUStatsEnabled 1"]
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "segments": [], "events": [], "cvars": CVARS,
       "views": VIEWS, "configs": CONFIGS}
ST = {"phase": "wait_world", "t": time.time(), "t0": time.time(), "i": 0, "pc": None, "cams": {}, "handle": None, "dts": []}
STARTUP_CV = ["sg.ResolutionQuality", "r.ScreenPercentage", "r.ScreenPercentage.Default", "r.ScreenPercentage.Default.Desktop.Mode",
              "sg.ShadowQuality", "sg.GlobalIlluminationQuality", "r.VolumetricFog.GridPixelSize", "r.VolumetricFog.GridSizeZ",
              "r.Nanite.Foliage", "r.AntiAliasingMethod", "r.DynamicGlobalIlluminationMethod", "r.Lumen.HardwareRayTracing"]
PLAN = [(v, c, None) for v in VIEWS for c in CONFIGS]
TOGGLED = []
# VERIFIER walk-through starts (Blender frame m, floor z): veranda in front of each door, due north
WALKS = [("door_W_x20.0_to_west_aisle_and_dais", (20.0, 22.7, 0.5), 9.0),
         ("door_C_x22.0_into_case1", (22.0, 22.7, 0.5), 5.0),
         ("door_E_x24.0_to_east_aisle_and_dais", (24.0, 22.7, 0.5), 9.0),
         ("courtyard_x20.4_up_the_steps_through_door_W", (20.4, 18.5, 0.0), 11.0)]


def set_toggle(tg):
    """hide one content group at runtime (nothing is saved): foliage = every instanced (H)ISM component (forest, grass,
    bushes, pebbles) + the pine / cypress actors' mesh components; niagara = every NiagaraComponent; water = the water
    body and zone actors."""
    for c, kind in TOGGLED:
        try:
            if kind == "actor":
                c.set_actor_hidden_in_game(False)
            else:
                c.set_visibility(True, True)
        except Exception:  # noqa: BLE001
            pass
    TOGGLED.clear()
    if tg in (None, "base"):
        return 0
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor):
        cls = a.get_class().get_name()
        if tg == "no_water" and cls in ("WaterBodyRiver", "WaterZone"):
            a.set_actor_hidden_in_game(True)
            TOGGLED.append((a, "actor"))
            n += 1
            continue
        comps = []
        if tg == "no_niagara":
            comps = list(a.get_components_by_class(unreal.NiagaraComponent))
        elif tg == "no_foliage":
            comps = list(a.get_components_by_class(unreal.InstancedStaticMeshComponent))
            lab = a.get_name().lower()
            if any(k in lab for k in ("pine", "cypress", "dkn_")):
                comps += [c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c not in comps]
        for c in comps:
            if c.is_visible():
                c.set_visibility(False, True)
                TOGGLED.append((c, "comp"))
                n += 1
    return n


def log(msg):
    REP["events"].append(f"{time.time() - ST['t0']:.1f}s {msg}")
    unreal.log(f"V8PERF {msg}")


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


def env_state():
    kinds = {"directional": unreal.DirectionalLightComponent, "skylight": unreal.SkyLightComponent,
             "fog": unreal.ExponentialHeightFogComponent, "atmosphere": unreal.SkyAtmosphereComponent,
             "cloud": unreal.VolumetricCloudComponent, "point": unreal.PointLightComponent,
             "rect": unreal.RectLightComponent, "postprocess": unreal.PostProcessComponent}
    out = {k: [] for k in kinds}
    uds = None
    for a in unreal.GameplayStatics.get_all_actors_of_class(ST["pc"], unreal.Actor):
        if a.get_class().get_name() == "Ultra_Dynamic_Sky_C":
            uds = a
        for k, cls in kinds.items():
            for c in a.get_components_by_class(cls):
                r = {"actor": a.get_name(), "comp": c.get_name()}
                for p in ("intensity", "visible", "affects_world", "cast_shadows", "enabled", "unbound", "priority"):
                    try:
                        v = c.get_editor_property(p)
                        r[p] = round(v, 4) if isinstance(v, float) else v if isinstance(v, bool) else str(v)
                    except Exception:  # noqa: BLE001
                        pass
                if k == "directional":
                    f = c.get_forward_vector()
                    r["elev_deg"] = round(math.degrees(math.asin(max(-1.0, min(1.0, -f.z)))), 4)
                    r["az_from_x_blender_deg"] = round(math.degrees(math.atan2(f.y, -f.x)) % 360, 4)
                out[k].append(r)
    for k in ("Time of Day", "Animate Time of Day", "Apply Exposure Settings", "Project Mode", "Sky Mode"):
        try:
            out.setdefault("uds", {})[k] = str(uds.get_editor_property(k)) if uds else None
        except Exception as e:  # noqa: BLE001
            out.setdefault("uds", {})[k] = "ERR " + str(e)[:60]
    out["active"] = {k: sum(1 for r in v if r.get("visible", True) and r.get("affects_world", True) is not False
                            and (r.get("intensity", 1.0) or 0) > 0)
                     for k, v in out.items() if isinstance(v, list)}
    out["t_s"] = round(time.time() - ST["t0"], 1)
    return out


def view(name, w, h, sp):
    cmd(f"r.setres {w}x{h}w")
    cmd(f"r.ScreenPercentage {sp}")   # 0: <=0 hands the fraction to r.ScreenPercentage.Default.* (the project curve)
    tgt = ST["pc"].get_controlled_pawn() if name == "PAWN" else ST["cams"].get(name)
    if tgt is None:
        return False
    ST["pc"].set_view_target_with_blend(tgt, 0.0)
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
    unreal.log(f"V8PERF_DONE ok={ok} segments={len(REP['segments'])}")
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
            if pc is not None and el > 2.0:
                ST["pc"] = pc
                for a in unreal.GameplayStatics.get_all_actors_of_class(pc, unreal.CineCameraActor):
                    ST["cams"][a.get_actor_label()] = a
                REP["missing_cams"] = [v for v in VIEWS if v != "PAWN" and v not in ST["cams"]]
                REP["startup_cvars"] = {k: cv(k) for k in STARTUP_CV}
                for c in CVARS:
                    cmd(c)
                REP["after_scalability_cvars"] = {k: cv(k) for k in STARTUP_CV}
                pc.set_ignore_move_input(True)
                pc.set_ignore_look_input(True)
                REP["env_start"] = env_state()
                log(f"world ready, cams {len(ST['cams'])}, missing {REP['missing_cams']}")
                ST["phase"], ST["t"], ST["i"] = "warm0", now, 0
            elif el > 180:
                log("no PlayerController")
                finish(False)
        elif ph == "warm0":
            if el >= WARM_S:
                ST["phase"], ST["t"], ST["i"] = "warm", now, 0
                view(VIEWS[0], 2560, 1440, 100)
        elif ph == "warm":
            if el >= WARM_PER_S:
                ST["i"] += 1
                ST["t"] = now
                if ST["i"] >= len(VIEWS):
                    ST["phase"], ST["i"] = "aim", 0
                else:
                    view(VIEWS[ST["i"]], 2560, 1440, 100)
        elif ph == "aim":
            if ST["i"] >= len(PLAN):
                set_toggle(None)
                REP["env_end"] = env_state()
                ST["phase"], ST["t"], ST["w"] = "walk_start", now, 0
                return
            v, (w, h, sp), tg = PLAN[ST["i"]]
            ok = view(v, w, h, sp)
            ST["toggled_n"] = set_toggle(tg)
            log(f"segment {ST['i']} {v} {w}x{h}@{sp} {tg} view_ok={ok} toggled={ST['toggled_n']}")
            ST["phase"], ST["t"] = "settle", now
        elif ph == "settle":
            if el >= SETTLE_S:
                v, (w, h, sp), tg = PLAN[ST["i"]]
                ST["dts"] = []
                cmd("csvprofile start")
                log(f"SAMPLE_START {ST['i']} {v} {w}x{h}@{sp}")
                ST["phase"], ST["t"] = "sample", now
                ST["seg_t0"] = now
        elif ph == "sample":
            ST["dts"].append(float(dt))
            if el >= SAMPLE_S:
                cmd("csvprofile stop")
                v, (w, h, sp), tg = PLAN[ST["i"]]
                seg = {"i": ST["i"], "view": v, "res": [w, h], "screen_pct": sp, "toggle": tg, "toggled_n": ST.get("toggled_n"),
                       "cvar_screen_pct": cv("r.ScreenPercentage"), "wall_s": round(now - ST["seg_t0"], 2),
                       "frames": stats(ST["dts"][2:]), "t_s": round(now - ST["t0"], 1)}
                REP["segments"].append(seg)
                log(f"SAMPLE_END {ST['i']} {v} {w}x{h}@{sp} {seg['frames']}")
                log(f"PROFILEGPU_BEGIN {ST['i']} {v} {w}x{h}@{sp}")
                cmd("ProfileGPU")
                ST["phase"], ST["t"] = "prof", now
        elif ph == "prof":
            if el >= PROF_S:
                log(f"PROFILEGPU_END {ST['i']}")
                ST["i"] += 1
                ST["phase"], ST["t"] = "aim", now
        elif ph == "walk_start":
            # VERIFIER in-game walk-through: the real GASP pawn + CMC, AddMovementInput due north (UE -Y)
            if ST["w"] >= len(WALKS):
                finish(True)
                return
            name, (x, y, z), secs = WALKS[ST["w"]]
            pc = ST["pc"]
            pc.set_ignore_move_input(False)
            pawn = pc.get_controlled_pawn()
            pc.set_view_target_with_blend(pawn, 0.0)
            pawn.set_actor_location(unreal.Vector(x * 100, -y * 100, z * 100 + 100.0), False, True)
            r = unreal.Rotator()
            r.yaw = -90.0
            pc.set_control_rotation(r)
            ST["walk"] = {"name": name, "start_bl_m": [x, y, z], "secs": secs, "track": []}
            ST["phase"], ST["t"] = "walking", now
        elif ph == "walking":
            pawn = ST["pc"].get_controlled_pawn()
            name, (x, y, z), secs = WALKS[ST["w"]]
            if el < 1.0:
                return   # settle on the floor
            pawn.add_movement_input(unreal.Vector(0.0, -1.0, 0.0), 1.0, False)
            l = pawn.get_actor_location()
            ST["walk"]["track"].append([round(l.x / 100, 2), round(-l.y / 100, 2), round(l.z / 100, 2)])
            if el >= secs + 1.0:
                tr = ST["walk"]["track"]
                ST["walk"]["end_bl_m"] = tr[-1]
                ST["walk"]["max_y"] = max(t[1] for t in tr)
                ST["walk"]["max_z_capsule_centre"] = max(t[2] for t in tr)
                ST["walk"]["track"] = tr[::10]
                REP.setdefault("walks", []).append(ST["walk"])
                log(f"WALK {name} end {ST['walk']['end_bl_m']} max_y {ST['walk']['max_y']}")
                ST["w"] += 1
                ST["phase"], ST["t"] = "walk_start", now
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        finish(False)


ST["handle"] = unreal.register_slate_post_tick_callback(tick)
log("registered")
