"""ArmoryLab performance probe (2026-10-02). Runs INSIDE Unreal, started by ak_perf.ps1, in one of two modes:

  game  UnrealEditor-Cmd ArmoryLab.uproject /Game/Armory/Maps/L_Armory -game ... -ExecutePythonScript=this
        (a fresh standalone game run of the SAVED level, the way a player sees it)
  pie   UnrealEditor-Cmd ArmoryLab.uproject -RenderOffscreen ... -ExecutePythonScript=this
        (an offscreen editor that starts Play-In-Editor on the saved level, the way the owner plays it)

Read-only: it never saves a package or the level. Driven by a Slate post-tick generator (real engine frames), it
  1 waits for the world and the player pawn, reads the render cvars and an inventory of the level (local lights and their
    shadows, the shell actors tagged AH_Shell, triangles, Niagara components and their ray-tracing flag); game mode sets
    the resolution with r.SetRes (an offscreen game window ignores -ResX / -ResY);
  2 warms up AK_PERF_WARM seconds at the player's start view (shaders, PSOs, Lumen / TSR history);
  3 for every view in AK_PERF_VIEWS ("spawn" = the player's own view; a layout camera name = its CAM_<name> actor, set as
    the view target): settles, then one CSV-profiler segment of AK_PERF_SEG seconds (stat unit's numbers: frame / game /
    render / RHI / GPU ms; draw calls, primitives; GPU passes with r.GPUCsvStatsEnabled=1) plus the Python-side frame
    deltas, with NO stat overlay on screen (stat gpu's overlay alone costs ~1800 Slate draws); a HighResShot of each
    camera view (the before / after look);
  4 (AK_PERF_AB, diagnosis only: runtime toggles, reverted after each, never saved) one more segment per toggle on each
    AK_PERF_AB_VIEW view, the base segment repeated at the end ('noop' = an interleaved base segment); AK_PERF_AB_SHOTS=1
    adds a HighResShot per toggle on camera views;
  5 last, with stat unit + stat gpu on screen: a 'shot showui', the stat scenerendering / initviews / rhi dump
    ('stat dumpframe') and one ProfileGPU per view in AK_PERF_PROFILE_VIEWS (into the log);
  then quits. The launcher parses the log + CSVs into perf.json (ak_perf_parse.py).

Env: AK_PERF_MODE (game|pie), AK_PERF_OUT (folder), AK_PERF_RES (game, "1600x900"), AK_PERF_PIE_RES (pie window,
     "1630x910"), AK_PERF_WARM (s, 20), AK_PERF_SETTLE (s, 4), AK_PERF_SEG (s, 10), AK_PERF_VIEWS (default
     "spawn,C1_EntryReveal,C10_Hero"), AK_PERF_PROFILE_VIEWS (default "spawn,C10_Hero"), AK_PERF_AB (comma list of the
     TOGGLES below), AK_PERF_AB_VIEW (comma list, default C10_Hero), AK_PERF_AB_SHOTS (0/1).
Log markers: AK_PERF_SEG_BEGIN <name> / AK_PERF_SEG_END <name>, AK_PERF_PROFILE_BEGIN/END <view>, AK_PERF_DONE.
"""
import json
import os
import time
import traceback
from pathlib import Path

import unreal as ue

MODE = os.environ.get("AK_PERF_MODE", "game")
OUT = Path(os.environ.get("AK_PERF_OUT", r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\perf\_adhoc"))
WARM = float(os.environ.get("AK_PERF_WARM", "20"))
SETTLE = float(os.environ.get("AK_PERF_SETTLE", "4"))
SEG = float(os.environ.get("AK_PERF_SEG", "10"))
VIEWS = [v for v in os.environ.get("AK_PERF_VIEWS", "spawn,C1_EntryReveal,C10_Hero").split(",") if v]
PROFILE_VIEWS = [v for v in os.environ.get("AK_PERF_PROFILE_VIEWS", "spawn,C10_Hero").split(",") if v]
AB = [v for v in os.environ.get("AK_PERF_AB", "").split(",") if v]
AB_VIEWS = [v for v in os.environ.get("AK_PERF_AB_VIEW", "C10_Hero").split(",") if v]
RES = os.environ.get("AK_PERF_RES", "1600x900")
PIE_RES = os.environ.get("AK_PERF_PIE_RES", "1630x910")   # the owner's PIE viewport (his log: TSR ... -> 1630x910)
SHELL_TAG = "AH_Shell"

# diagnosis toggles: (commands to apply, commands to revert); "@shell_hidden" is done in Python
TOGGLES = {
    "rt_off": (["r.RayTracing.Enable 0"], ["r.RayTracing.Enable 1"]),
    "lumen_hwrt_off": (["r.Lumen.HardwareRayTracing 0"], ["r.Lumen.HardwareRayTracing 1"]),
    "lumen_gi_refl_off": (["r.Lumen.DiffuseIndirect.Allow 0", "r.Lumen.Reflections.Allow 0"],
                          ["r.Lumen.DiffuseIndirect.Allow 1", "r.Lumen.Reflections.Allow 1"]),
    "shadows_off": (["ShowFlag.DynamicShadows 0"], ["ShowFlag.DynamicShadows 2"]),
    "local_lights_off": (["ShowFlag.PointLights 0", "ShowFlag.SpotLights 0", "ShowFlag.RectLights 0"],
                         ["ShowFlag.PointLights 2", "ShowFlag.SpotLights 2", "ShowFlag.RectLights 2"]),
    "translucency_off": (["ShowFlag.Translucency 0"], ["ShowFlag.Translucency 2"]),
    "particles_off": (["ShowFlag.Particles 0"], ["ShowFlag.Particles 2"]),
    "shell_hidden": (["@shell_hidden 1"], ["@shell_hidden 0"]),
    "shell_noshadow": (["@shell_shadow 0"], ["@shell_shadow 1"]),
    "local_shadows_off": (["@local_shadows 0"], ["@local_shadows 1"]),
    "atten_8m": (["@atten 800"], ["@atten restore"]),
    "atten_6m": (["@atten 600"], ["@atten restore"]),
    "case_ch1": (["@case_channel 1"], ["@case_channel 0"]),
    "noop": ([], []),   # a base segment between toggles (A/B/A/B against drift from other load on the machine)
    "atten_soft": (["@atten_roles glow=600,panel=800,lantern=600,down=1200"], ["@atten restore"]),
    "case_ch1_atten_soft": (["@case_channel 1", "@atten_roles glow=600,panel=800,lantern=600,down=1200"],
                            ["@case_channel 0", "@atten restore"]),
    "tsr_50": (["r.ScreenPercentage 50"], ["r.ScreenPercentage 100"]),
}
CVARS_INT = ["r.RayTracing", "r.RayTracing.Enable", "r.RayTracing.EnableOnDemand", "r.Lumen.HardwareRayTracing",
             "r.Lumen.HardwareRayTracing.LightingMode", "r.Lumen.TraceMeshSDFs", "r.DynamicGlobalIlluminationMethod",
             "r.ReflectionMethod", "r.Shadow.Virtual.Enable", "r.PSOPrecaching", "r.PSOPrecache.Components",
             "r.PSOPrecache.ProxyCreationWhenPSOReady", "r.ShaderPipelineCache.Enabled", "r.Nanite",
             "r.MegaLights.Enable", "r.Lumen.DiffuseIndirect.Allow", "r.Lumen.Reflections.Allow",
             "r.RayTracing.Shadows", "r.Lumen.ScreenProbeGather.ScreenTraces", "r.Lumen.Reflections.HardwareRayTracing",
             "r.Lumen.HardwareRayTracing.HitLighting.Allowed", "r.RayTracing.Geometry.SkeletalMeshes",
             "r.RayTracing.Nanite.Mode", "r.Lumen.DirectLighting.MaxLightsPerTile", "r.Lumen.SurfaceCache.CardCaptureRefreshFraction",
             "sg.ResolutionQuality", "sg.ViewDistanceQuality", "sg.AntiAliasingQuality", "sg.ShadowQuality",
             "sg.GlobalIlluminationQuality", "sg.ReflectionQuality", "sg.PostProcessQuality", "sg.TextureQuality",
             "sg.EffectsQuality", "sg.FoliageQuality", "sg.ShadingQuality", "r.VSync", "t.MaxFPS",
             "r.Shadow.Virtual.Cache", "r.GPUCsvStatsEnabled", "r.TextureStreaming", "r.AntiAliasingMethod",
             "r.Lumen.TranslucencyReflections.FrontLayer.Allow"]
CVARS_FLOAT = ["r.ScreenPercentage", "r.Lumen.ScreenProbeGather.DownsampleFactor"]

REP = {"mode": MODE, "views": VIEWS, "ab": AB, "warm_s": WARM, "seg_s": SEG, "settle_s": SETTLE, "segments": [],
       "notes": [], "errors": [], "shots": []}
STATE = {"dt": []}
T0 = time.time()


def log(*a):
    ue.log("[AK_PERF] " + " ".join(str(x) for x in a))


def save():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probe.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")


def world():
    if MODE == "pie":
        try:
            w = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
            if w is not None:
                return w
        except Exception:  # noqa: BLE001
            pass
        return None
    for path in ("/Game/Armory/Maps/L_Armory.L_Armory",):
        try:
            w = ue.find_object(None, path)
            if w is not None:
                return w
        except Exception:  # noqa: BLE001
            pass
    return None


def cmd(w, c):
    log("exec", c)
    ue.SystemLibrary.execute_console_command(w, c)


def wait(sec):
    t = time.time()
    while time.time() - t < sec:
        yield


def label(a):
    try:
        return a.get_actor_label()
    except Exception:  # noqa: BLE001
        return a.get_name()


def cvars():
    out = {}
    for n in CVARS_INT:
        try:
            out[n] = ue.SystemLibrary.get_console_variable_int_value(n)
        except Exception as exc:  # noqa: BLE001
            out[n] = f"n/a {str(exc)[:60]}"
    for n in CVARS_FLOAT:
        try:
            out[n] = round(ue.SystemLibrary.get_console_variable_float_value(n), 3)
        except Exception as exc:  # noqa: BLE001
            out[n] = f"n/a {str(exc)[:60]}"
    return out


def gp(obj, k, default=None):
    try:
        return obj.get_editor_property(k)
    except Exception:  # noqa: BLE001
        return default


def inventory(w):
    GS = ue.GameplayStatics
    actors = GS.get_all_actors_of_class(w, ue.Actor)
    inv = {"actors": len(actors), "local_lights": [], "directional": [], "niagara": [], "shell": {}, "ours": {},
           "mesh_triangles_by_mesh": {}}
    shell = {"actors": 0, "visible_mesh_actors": 0, "tris_lod0": 0, "nanite_actors": 0, "rt_visible": 0,
             "cast_shadow": 0, "df_lighting": 0, "lights": 0, "lights_visible": 0, "lights_shadowed": 0}
    ours = {"visible_mesh_actors": 0, "tris_lod0": 0, "nanite_actors": 0, "rt_visible": 0, "hidden_exterior": 0,
            "translucent_mesh_actors": 0}
    tri_cache = {}
    for a in actors:
        tags = [str(t) for t in a.tags]
        is_shell = SHELL_TAG in tags
        if is_shell:
            shell["actors"] += 1
        if "AH_ExteriorHidden" in tags:
            ours["hidden_exterior"] += 1
        for c in a.get_components_by_class(ue.LightComponent):
            vis = bool(c.is_visible()) if hasattr(c, "is_visible") else bool(gp(c, "visible", True))
            rec = {"actor": label(a), "class": type(c).__name__, "visible": vis,
                   "cast_shadows": bool(gp(c, "cast_shadows", False)), "intensity": round(float(gp(c, "intensity", 0.0)), 3),
                   "mobility": str(gp(c, "mobility", "")), "shell": is_shell,
                   "attenuation_cm": round(float(gp(c, "attenuation_radius", 0.0) or 0.0), 1)}
            if isinstance(c, ue.DirectionalLightComponent):
                inv["directional"].append(rec)
            else:
                inv["local_lights"].append(rec)
            if is_shell:
                shell["lights"] += 1
                shell["lights_visible"] += int(vis and rec["intensity"] > 0)
                shell["lights_shadowed"] += int(vis and rec["cast_shadows"])
        try:
            ncls = ue.NiagaraComponent
        except Exception:  # noqa: BLE001
            ncls = None
        if ncls is not None:
            for c in a.get_components_by_class(ncls):
                inv["niagara"].append({"actor": label(a), "visible": bool(gp(c, "visible", True)),
                                       "visible_in_ray_tracing": gp(c, "visible_in_ray_tracing"),
                                       "asset": str(gp(c, "asset", ""))})
        for c in a.get_components_by_class(ue.StaticMeshComponent):
            mesh = c.static_mesh
            if mesh is None:
                continue
            vis =bool(gp(c, "visible", True)) and not bool(gp(a, "hidden", False))
            if not vis:
                continue
            mn = mesh.get_name()
            if mn not in tri_cache:
                try:
                    tris = int(mesh.get_num_triangles(0))
                except Exception:  # noqa: BLE001
                    tris = -1
                nan = None
                try:
                    nan = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
                except Exception:  # noqa: BLE001
                    pass
                tri_cache[mn] = (tris, nan)
            tris, nan = tri_cache[mn]
            rtv = bool(gp(c, "visible_in_ray_tracing", True))
            tgt = shell if is_shell else ours
            tgt["visible_mesh_actors"] += 1
            tgt["tris_lod0"] += max(tris, 0)
            tgt["nanite_actors"] += int(bool(nan))
            tgt["rt_visible"] += int(rtv)
            if is_shell:
                shell["cast_shadow"] += int(bool(gp(c, "cast_shadow", True)))
                shell["df_lighting"] += int(bool(gp(c, "affect_distance_field_lighting", True)))
            elif "Glass" in mn:
                ours["translucent_mesh_actors"] += 1
            e = inv["mesh_triangles_by_mesh"].setdefault(mn, {"tris_lod0": tris, "nanite": nan, "actors": 0,
                                                                "shell": is_shell})
            e["actors"] += 1
    ll = inv["local_lights"]
    inv["local_light_summary"] = {
        "total": len(ll), "visible": sum(1 for x in ll if x["visible"]),
        "visible_nonzero": sum(1 for x in ll if x["visible"] and x["intensity"] > 0),
        "shadowed_visible": sum(1 for x in ll if x["visible"] and x["cast_shadows"] and x["intensity"] > 0),
        "shadowed_names": sorted(x["actor"] for x in ll if x["visible"] and x["cast_shadows"] and x["intensity"] > 0),
        "shell_backers": sum(1 for x in ll if x["shell"]),
        "shell_backers_visible": sum(1 for x in ll if x["shell"] and x["visible"]),
        "shell_backers_shadowed": sum(1 for x in ll if x["shell"] and x["cast_shadows"])}
    inv["shell"], inv["ours"] = shell, ours
    top = sorted(inv["mesh_triangles_by_mesh"].items(), key=lambda kv: -kv[1]["tris_lod0"] * kv[1]["actors"])[:25]
    inv["top_meshes_by_total_tris"] = [{"mesh": k, **v, "total": v["tris_lod0"] * v["actors"]} for k, v in top]
    del inv["mesh_triangles_by_mesh"]
    return inv


def viewport_size(w):
    try:
        v = ue.WidgetLayoutLibrary.get_viewport_size(w)
        return [round(v.x), round(v.y)]
    except Exception as exc:  # noqa: BLE001
        return f"n/a {str(exc)[:80]}"


def find_cam(w, name):
    want = "CAM_" + name
    for a in ue.GameplayStatics.get_all_actors_of_class(w, ue.CameraActor):
        if label(a) == want:
            return a
    return None


def set_view(w, view):
    pc = ue.GameplayStatics.get_player_controller(w, 0)
    if view == "spawn":
        pawn = pc.get_controlled_pawn() if pc else None
        if pawn is not None:
            pc.set_view_target_with_blend(pawn, 0.0)
        return True
    cam = find_cam(w, view)
    if cam is None or pc is None:
        REP["notes"].append(f"view {view}: camera CAM_{view} not found")
        return False
    pc.set_view_target_with_blend(cam, 0.0)
    return True


def shell_hidden(w, on):
    n = 0
    for a in ue.GameplayStatics.get_all_actors_with_tag(w, SHELL_TAG):
        a.set_actor_hidden_in_game(bool(on))
        n += 1
    return n


SAVED = {}
try:   # light name -> role, from the level step's own report (the saved level's lights)
    ROLE = {x["name"]: x["role"] for x in json.loads(Path(
        "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/build/unreal/level.json").read_text(encoding="utf-8"))["local_lights"]}
except Exception:  # noqa: BLE001
    ROLE = {}


def local_lights(w):
    for a in ue.GameplayStatics.get_all_actors_of_class(w, ue.Light):
        for c in a.get_components_by_class(ue.LocalLightComponent):
            yield a, c


def apply(w, cmds):
    """Runtime diagnosis toggles (never saved). '@...' are done on the components here."""
    for c in cmds:
        if c.startswith("@shell_hidden"):
            n = shell_hidden(w, c.endswith("1"))
            log("shell_hidden", c[-1], "actors", n)
        elif c.startswith("@shell_shadow"):
            n = 0
            for a in ue.GameplayStatics.get_all_actors_with_tag(w, SHELL_TAG):
                for m in a.get_components_by_class(ue.StaticMeshComponent):
                    m.set_cast_shadow(c.endswith("1"))
                    n += 1
            log("shell cast_shadow", c[-1], "components", n)
        elif c.startswith("@local_shadows"):
            on = c.endswith("1")
            n = 0
            for a, lc in local_lights(w):
                key = ("sh", lc.get_path_name())
                if not on:
                    SAVED[key] = bool(gp(lc, "cast_shadows", False))
                    lc.set_cast_shadows(False)
                elif key in SAVED:
                    lc.set_cast_shadows(SAVED.pop(key))
                n += 1
            log("local light shadows", c[-1], "lights", n)
        elif c.startswith("@case_channel"):
            on = c.endswith("1")
            n = 0
            for a, lc in local_lights(w):
                if ROLE.get(label(a)) == "case" and bool(gp(lc, "cast_shadows", False)):
                    lc.set_lighting_channels(not on, True, False)
                    n += 1
            t = 0
            for a in ue.GameplayStatics.get_all_actors_with_tag(w, SHELL_TAG):
                if label(a).startswith("SM_AK_"):      # the hall variant's floor tiles AKI_9001..9008 are room kit
                    a.static_mesh_component.set_lighting_channels(True, on, False)
                    t += 1
            log("case lights channel-1 only", on, "lights", n, "tiles", t)
        elif c.startswith("@atten_roles"):
            tab = {k: float(v) for k, v in (kv.split("=") for kv in c.split()[1].split(","))}
            n = 0
            for a, lc in local_lights(w):
                r = ROLE.get(label(a))
                if r in tab:
                    key = ("at", lc.get_path_name())
                    SAVED.setdefault(key, float(gp(lc, "attenuation_radius", 0.0)))
                    lc.set_attenuation_radius(min(tab[r], SAVED[key]))
                    n += 1
            log("attenuation by role", tab, "lights", n)
        elif c.startswith("@atten"):
            arg = c.split()[1]
            n = 0
            for a, lc in local_lights(w):
                key = ("at", lc.get_path_name())
                if arg == "restore":
                    if key in SAVED:
                        lc.set_attenuation_radius(SAVED.pop(key))
                else:
                    SAVED.setdefault(key, float(gp(lc, "attenuation_radius", 0.0)))
                    lc.set_attenuation_radius(min(float(arg), SAVED[key]))
                n += 1
            log("attenuation", arg, "lights", n)
        else:
            cmd(w, c)


def segment(w, name):
    STATE["dt"] = []
    STATE["rec"] = True
    cmd(w, "csvprofile start")
    log("AK_PERF_SEG_BEGIN", name)
    t = time.time()
    yield from wait(SEG)
    log("AK_PERF_SEG_END", name)
    cmd(w, "csvprofile stop")
    STATE["rec"] = False
    d = sorted(STATE["dt"])
    seg = {"name": name, "wall_s": round(time.time() - t, 2), "frames": len(d)}
    if d:
        seg["py_frame_ms_mean"] = round(1000.0 * sum(d) / len(d), 2)
        seg["py_frame_ms_p95"] = round(1000.0 * d[int(0.95 * (len(d) - 1))], 2)
        seg["py_fps"] = round(len(d) / max(sum(d), 1e-6), 1)
    REP["segments"].append(seg)
    save()
    yield from wait(2.0)   # let the CSV writer finish


def program():
    while True:
        w = world()
        pc = ue.GameplayStatics.get_player_controller(w, 0) if w else None
        if w is not None and pc is not None and pc.get_controlled_pawn() is not None:
            break
        if time.time() - T0 > 300:
            raise RuntimeError("no game world / pawn after 300 s")
        yield
    REP["t_world_s"] = round(time.time() - T0, 1)
    REP["world"] = w.get_path_name()
    log("world", REP["world"], "after", REP["t_world_s"], "s")
    REP["cvars_start"] = cvars()
    try:
        REP["inventory"] = inventory(w)
    except Exception:  # noqa: BLE001
        REP["errors"].append("inventory: " + traceback.format_exc()[-1500:])
    save()
    if MODE == "game":
        cmd(w, f"r.SetRes {RES}w")   # -ResX/-ResY are not honoured by an offscreen game window
    yield from wait(1.0)
    REP["viewport"] = viewport_size(w)
    log("viewport", REP["viewport"])
    log("AK_PERF_WARM_BEGIN")
    yield from wait(WARM)
    log("AK_PERF_WARM_END")
    REP["viewport_after_warm"] = viewport_size(w)
    # 1 the measured segments: NO on-screen stats (the stat overlays cost game / render thread time and ~1800 Slate draws)
    for view in VIEWS:
        if not set_view(w, view):
            continue
        yield from wait(SETTLE)
        yield from segment(w, view)
        if view != "spawn":
            cmd(w, "HighResShot 1")
            REP["shots"].append({"view": view, "t": time.time()})
            yield from wait(3.0)
    # 2 diagnosis toggles (same process), the base segment repeated at the end to show drift
    for AB_VIEW in (AB_VIEWS if AB else []):
        set_view(w, AB_VIEW)
        yield from wait(SETTLE)
        yield from segment(w, f"AB_base@{AB_VIEW}")
        for t in AB:
            if t not in TOGGLES:
                REP["notes"].append(f"unknown toggle {t}")
                continue
            on, off = TOGGLES[t]
            apply(w, on)
            yield from wait(SETTLE)
            yield from segment(w, f"AB_{t}@{AB_VIEW}")
            if os.environ.get("AK_PERF_AB_SHOTS", "0") == "1" and AB_VIEW != "spawn":
                cmd(w, "HighResShot 1")
                REP["shots"].append({"view": f"AB_{t}@{AB_VIEW}", "t": time.time()})
                yield from wait(3.0)
            apply(w, off)
            yield from wait(2.0)
        yield from wait(SETTLE)
        yield from segment(w, f"AB_base_end@{AB_VIEW}")
    # 3 evidence with the stats on screen, after every measurement: stat unit + stat gpu screenshot, the stat
    # scenerendering / initviews / rhi dump and one ProfileGPU per profiled view
    for view in PROFILE_VIEWS:
        if not set_view(w, view):
            continue
        cmd(w, "stat unit")
        cmd(w, "stat gpu")
        yield from wait(SETTLE)
        cmd(w, "shot showui")
        yield from wait(2.0)
        for g in ("scenerendering", "initviews", "rhi"):
            cmd(w, f"stat {g}")
        yield from wait(2.0)
        log("AK_PERF_PROFILE_BEGIN", view)
        cmd(w, "stat dumpframe -ms=0.05")
        yield
        cmd(w, "ProfileGPU")
        yield from wait(3.0)
        log("AK_PERF_PROFILE_END", view)
        cmd(w, "stat none")
        yield from wait(1.0)
    REP["cvars_end"] = cvars()
    REP["sec"] = round(time.time() - T0, 1)
    REP["passed"] = not REP["errors"]
    save()
    log("AK_PERF_DONE passed=" + str(REP["passed"]))


GEN = program()


def quit_now():
    w = world()
    try:
        if MODE == "pie":
            ue.SystemLibrary.quit_editor()
        else:
            ue.SystemLibrary.execute_console_command(w, "quit")
    except Exception:  # noqa: BLE001
        ue.SystemLibrary.execute_console_command(None, "quit")


def tick(dt):
    if STATE.get("rec"):
        STATE["dt"].append(dt)
    if STATE.get("busy") or STATE.get("finished"):
        return
    STATE["busy"] = True
    try:
        next(GEN)
    except StopIteration:
        STATE["finished"] = True
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        quit_now()
    except Exception:  # noqa: BLE001
        STATE["finished"] = True
        REP["errors"].append(traceback.format_exc()[-3000:])
        REP["passed"] = False
        save()
        ue.log_error(traceback.format_exc())
        log("AK_PERF_DONE passed=False")
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        quit_now()
    finally:
        STATE["busy"] = False


def start_pie():
    """pie mode: start Play-In-Editor once the editor ticks (as the owner's 'Play' button)."""
    # AK_PERF_PIE_FLOAT=1: a floating PIE window at the owner's viewport size (the offscreen editor's own level viewport
    # is 1083 x 550). Default OFF: the 2026-10-02 before / after pair ran PIE in that level viewport.
    try:
        if os.environ.get("AK_PERF_PIE_FLOAT", "0") != "1":
            raise RuntimeError("floating PIE window off (AK_PERF_PIE_FLOAT=0)")
        cls = ue.load_class(None, "/Script/UnrealEd.LevelEditorPlaySettings")
        ps = ue.get_default_object(cls)
        wx, wy = (int(v) for v in PIE_RES.split("x"))
        pm = getattr(ue, "PlayModeType", None)
        mode = getattr(pm, "PLAY_MODE_IN_EDITOR_FLOATING", 1) if pm else 1
        for k, v in (("new_window_width", wx), ("new_window_height", wy), ("last_executed_play_mode_type", mode)):
            try:
                ps.set_editor_property(k, v)
            except Exception as exc:  # noqa: BLE001
                REP["notes"].append(f"play setting {k}: {str(exc)[:120]}")
        REP["pie_settings"] = {k: str(gp(ps, k)) for k in ("new_window_width", "new_window_height",
                                                            "last_executed_play_mode_type")}
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"play settings: {str(exc)[:160]}")
    les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    les.editor_request_begin_play()
    log("requested PIE")


if MODE == "pie":
    _pie = {"n": 0}

    def _pie_tick(dt):
        _pie["n"] += 1
        if _pie["n"] == 30:
            try:
                start_pie()
            except Exception:  # noqa: BLE001
                REP["errors"].append("start_pie: " + traceback.format_exc()[-1500:])
            ue.unregister_slate_post_tick_callback(_pie["cb"])
    _pie["cb"] = ue.register_slate_post_tick_callback(_pie_tick)

STATE["cb"] = ue.register_slate_post_tick_callback(tick)
try:
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    pass
log("registered mode", MODE, "views", VIEWS, "ab", AB)
