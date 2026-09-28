"""ArmoryLab step 5: offscreen stills of the saved L_Armory (never saves anything).

Runs INSIDE a full offscreen editor (UnrealEditor-Cmd ArmoryLab.uproject -RenderOffscreen -dx12 -ExecutePythonScript=this,
started by run_capture.ps1), driven by a Slate post-tick generator so every capture gets real engine frames: shaders finish
compiling, distance fields build, the real-time sky light recaptures and Lumen / TSR / volumetric fog accumulate history
(the BlackCloak review pattern). A -run=pythonscript commandlet never ticks the engine, which is why it is not used here.

For each camera (default C1_EntryReveal, C10_Hero, CW_WestAisle; the CAM_<name> actors saved in the level, so the saved
camera transforms are what is captured): a SceneCapture2D at the camera with its horizontal FOV, FINAL_COLOR_LDR into a
1600x900 RGBA8 target, persistent rendering state ON (Lumen / TSR history), captured once per engine tick for FRAMES ticks.
Checkpoints are exported to captures/sequence/<cam>_fNNN.png (convergence is measured from them) and the LAST frame is
captures/<cam>.png. The world's unbound PostProcessVolume sets the exposure (the capture adds no override).
Diagnostics on C1 (captures/diag/): Lumen GI off, volumetric fog off, and (AK_SWEEP=1) an exposure-bias sweep.
Unreal rebuild (2026-09-27): the default camera list is EVERY layout.json camera, plus C1 at the reference's
1448 x 1086 (captures/<cam>_ref_aspect.png, AK_REF_ASPECT, default C1_EntryReveal). A shift-lens camera (layout.json
shift_y, f1's level C1) is captured level into a TALL target of the same horizontal FOV that holds the shifted window,
and the capture step crops it afterwards (ak_crop.py; the rows are in capture.json "crop"); the raw frame is
captures/raw/<name>.png. A camera with its own review exposure (layout.json exposure_ev, the garden) gets the level
bias + (its EV - the golden EV) as a capture-only exposure override.
Env: AK_CAMS (comma list), AK_FRAMES (default 96), AK_WARM (warm-up ticks, default 600), AK_SWEEP (0/1).
Result: WorkFiles/armory/build/unreal/capture.json
"""
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\unreal")))
import unreal as ue  # noqa: E402
import ak_common as C  # noqa: E402

EAS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
RL = ue.RenderingLibrary
MEL = ue.MaterialEditingLibrary
LAYOUT_CAMS = {c["name"]: c for c in C.load_layout()["cameras"]}
CAMS = [c for c in os.environ.get("AK_CAMS", ",".join(LAYOUT_CAMS)).split(",") if c]
REF_ASPECT = [c for c in os.environ.get("AK_REF_ASPECT", "C1_EntryReveal").split(",") if c]
REF_WH = (1448, 1086)   # reference/armory3_reference2.png
FRAMES = int(os.environ.get("AK_FRAMES", "96"))
WARM = int(os.environ.get("AK_WARM", "600"))
WARM_MIN_SEC = float(os.environ.get("AK_WARM_SEC", "20"))
SWEEP = os.environ.get("AK_SWEEP", "0") == "1"
LADDER = os.environ.get("AK_LADDER", "0") == "1"
CHECKPOINTS = sorted({1, 4, 16, 32, 64, FRAMES} | set(range(0, FRAMES + 1, 32)) - {0})
W, H = 1600, 900
SEQ = C.CAPTURES / "sequence"
DIAG = C.CAPTURES / "diag"
REP = {"engine": ue.SystemLibrary.get_engine_version(), "cams": CAMS, "frames": FRAMES, "warm_ticks": WARM,
       "res": [W, H], "captures": {}, "diag": {}, "notes": [], "errors": []}
T0 = time.time()


def log(*a):
    ue.log("[AK_CAPTURE] " + " ".join(str(x) for x in a))


def save_rep():
    C.write_json(C.OUT / "capture.json", REP)


def world():
    return ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"setp {type(obj).__name__}.{k}: {str(exc)[:160]}")
        return False


def target_size(lay, w, h):
    """-> (target w, target h, crop rows [top, bottom) or None). A Blender shift_y (units of the frame width) moves the
    window by shift_y * w pixels; a level capture of height 2 * ceil(h / 2 + |shift| * w) with the same horizontal FOV
    holds it, and rows top..top + h are the shifted frame (negative shift = below the centre)."""
    sh = float(lay.get("shift_y", 0.0))
    if not sh:
        return w, h, None
    ht = 2 * math.ceil(h / 2.0 + abs(sh) * w)
    top = int(round(ht / 2.0 - sh * w - h / 2.0))
    return w, ht, [top, top + h]


def make_capture(cam_actor, lay, w, h):
    # the horizontal FOV of the Blender lens on a 36 mm sensor (the CineCamera's own FOV is the same, ak_level)
    fov = C.hfov_deg(lay["lens_mm"])
    cap = EAS.spawn_actor_from_class(ue.SceneCapture2D, cam_actor.get_actor_location(), cam_actor.get_actor_rotation())
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world(), w, h, ue.TextureRenderTargetFormat.RTF_RGBA8)
    setp(cc, "texture_target", rt)
    setp(cc, "capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    setp(cc, "capture_every_frame", False)
    setp(cc, "capture_on_movement", False)
    setp(cc, "always_persist_rendering_state", True)
    setp(cc, "fov_angle", fov)
    # UE 5.8 SceneCaptureRendering.cpp: "By default, Lumen is disabled in scene captures" (GI and reflection method None,
    # surface cache 0.5) unless the component's post-process settings re-enable them. Re-enable both at full cache
    # resolution so the capture shows what the level's main view shows. Exposure is NOT overridden: the level's unbound
    # PostProcessVolume sets it.
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_dynamic_global_illumination_method", True),
                 ("dynamic_global_illumination_method", ue.DynamicGlobalIlluminationMethod.LUMEN),
                 ("override_reflection_method", True), ("reflection_method", ue.ReflectionMethod.LUMEN),
                 ("override_lumen_surface_cache_resolution", True), ("lumen_surface_cache_resolution", 1.0),
                 ("override_lumen_front_layer_translucency_reflections", True),
                 ("lumen_front_layer_translucency_reflections", True)):
        setp(pp, k, v)
    setp(cc, "post_process_settings", pp)
    setp(cc, "post_process_blend_weight", 1.0)
    return cap, cc, rt, fov


def export(rt, folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    RL.export_render_target(world(), rt, str(folder), name)
    return str(folder / name)


def show_flag(cc, name, enabled):
    s = ue.EngineShowFlagsSetting()
    s.set_editor_property("show_flag_name", name)
    s.set_editor_property("enabled", enabled)
    setp(cc, "show_flag_settings", [s])


def pp_bias(cc, bias):
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", float(bias)),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False)):
        setp(pp, k, v)
    setp(cc, "post_process_settings", pp)
    setp(cc, "post_process_blend_weight", 1.0)


def run_frames(cc, n):
    for _ in range(n):
        cc.capture_scene()
        yield


def ladder():
    """Tone-ladder calibration (Unreal half of blender_tone_ladder.py): 13 unlit quads of scene radiance K * 0.18 * 2^k,
    k = -6..6, 300 m under the room (the transient editor world; nothing is saved), captured orthographically through
    the level's own exposure (unbound PPV) and tonemapper, with bloom off, vignette 0 and neutral local exposure so
    each quad centre shows the global curve. Display values -> REP["ladder"]."""
    mat = ue.new_object(ue.Material, name="AK_LadderMat")
    mat.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
    e = MEL.create_material_expression(mat, ue.MaterialExpressionVectorParameter, -400, 0)
    e.set_editor_property("parameter_name", "E")
    MEL.connect_material_property(e, "", ue.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(mat)
    plane = ue.load_asset("/Engine/BasicShapes/Plane")
    z0 = -30000.0
    acts = []
    ks = list(range(-6, 7))
    for i, k in enumerate(ks):
        a = EAS.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0.0, (i - 6) * 100.0, z0), ue.Rotator())
        smc = a.static_mesh_component
        smc.set_static_mesh(plane)
        mid = ue.MaterialLibrary.create_dynamic_material_instance(world(), mat, f"AK_L{i}")
        v = C.K_LUX * 0.18 * 2.0 ** k
        mid.set_vector_parameter_value("E", ue.LinearColor(v, v, v, 1.0))
        smc.set_material(0, mid)
        acts.append(a)
    r = ue.Rotator()
    r.pitch, r.yaw, r.roll = -90.0, 0.0, 0.0
    cap = EAS.spawn_actor_from_class(ue.SceneCapture2D, ue.Vector(0.0, 0.0, z0 + 1000.0), r)
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world(), 1300, 100, ue.TextureRenderTargetFormat.RTF_RGBA8)
    setp(cc, "texture_target", rt)
    setp(cc, "capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    setp(cc, "capture_every_frame", False)
    setp(cc, "always_persist_rendering_state", True)
    setp(cc, "projection_type", ue.CameraProjectionMode.ORTHOGRAPHIC)
    setp(cc, "ortho_width", 1300.0)
    pp = cc.get_editor_property("post_process_settings")
    for k_, v_ in (("override_vignette_intensity", True), ("vignette_intensity", 0.0),
                   ("override_local_exposure_highlight_contrast_scale", True), ("local_exposure_highlight_contrast_scale", 1.0),
                   ("override_local_exposure_shadow_contrast_scale", True), ("local_exposure_shadow_contrast_scale", 1.0),
                   ("override_bloom_intensity", True), ("bloom_intensity", 0.0)):
        setp(pp, k_, v_)
    setp(cc, "post_process_settings", pp)
    setp(cc, "post_process_blend_weight", 1.0)
    flags = []
    for name in ("Fog", "VolumetricFog", "Bloom"):
        f = ue.EngineShowFlagsSetting()
        f.set_editor_property("show_flag_name", name)
        f.set_editor_property("enabled", False)
        flags.append(f)
    setp(cc, "show_flag_settings", flags)
    yield from run_frames(cc, 24)
    export(rt, DIAG, "tone_ladder_unreal.png")
    rows = {}
    for i, k in enumerate(ks):
        c = RL.read_render_target_pixel(world(), rt, int((i + 0.5) * 100), 50)
        rows[str(k)] = {"radiance_unreal": C.K_LUX * 0.18 * 2.0 ** k,
                        "display": [round(c.r / 255.0, 4), round(c.g / 255.0, 4), round(c.b / 255.0, 4)]}
    REP["ladder"] = {"exposure_bias_level": REP.get("level_exposure_bias"), "rows": rows}
    # light-unit check: a grey (0.18) Lambertian quad 2 m under a 1000 cd point light, and one under a 10 x 10 cm rect
    # light of 1000 cd, inside a closed black box (no sun, sky or bounce). Expected radiance 0.18 * 250 / pi = 14.3 nits
    # for both; the display is inverted through the ladder above (same capture settings).
    black = ue.new_object(ue.Material, name="AK_BlackBox")
    black.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
    black.set_editor_property("two_sided", True)
    MEL.recompile_material(black)
    grey = ue.new_object(ue.Material, name="AK_Grey18")
    for prop, val in ((ue.MaterialProperty.MP_BASE_COLOR, 0.18), (ue.MaterialProperty.MP_ROUGHNESS, 1.0),
                      (ue.MaterialProperty.MP_SPECULAR, 0.0)):
        cst = MEL.create_material_expression(grey, ue.MaterialExpressionConstant, -300, 0)
        cst.set_editor_property("r", val)
        MEL.connect_material_property(cst, "", prop)
    MEL.recompile_material(grey)
    zc = z0 - 5000.0
    box = EAS.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(5000.0, 0.0, zc + 400.0), ue.Rotator())
    box.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Cube"))
    box.static_mesh_component.set_material(0, black)
    box.set_actor_scale3d(ue.Vector(16.0, 16.0, 10.0))
    rig = [box]
    for dy, kind in ((-500.0, "point"), (500.0, "rect")):
        q = EAS.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(5000.0, dy, zc), ue.Rotator())
        q.static_mesh_component.set_static_mesh(plane)
        q.static_mesh_component.set_material(0, grey)
        rig.append(q)
        down = ue.Rotator()
        down.pitch = -90.0
        cls = ue.PointLight if kind == "point" else ue.RectLight
        lt = EAS.spawn_actor_from_class(cls, ue.Vector(5000.0, dy, zc + 200.0), down)
        lc = lt.get_component_by_class(ue.LightComponent)
        setp(lc, "intensity_units", ue.LightUnits.CANDELAS)
        setp(lc, "intensity", 1000.0)
        setp(lc, "attenuation_radius", 5000.0)
        setp(lc, "cast_shadows", False)
        if kind == "rect":
            setp(lc, "source_width", 10.0)
            setp(lc, "source_height", 10.0)
            setp(lc, "barn_door_length", 0.0)
        else:
            setp(lc, "source_radius", 0.0)
        rig.append(lt)
    cap.set_actor_location(ue.Vector(5000.0, 0.0, zc + 300.0), False, False)
    yield from run_frames(cc, 32)
    export(rt, DIAG, "light_units_unreal.png")
    lad = sorted((math.log2(v["radiance_unreal"]), sum(v["display"]) / 3.0) for v in rows.values())

    def invert(d):
        for (x0, y0), (x1, y1) in zip(lad, lad[1:]):
            if y0 <= d <= y1 and y1 > y0:
                return 2.0 ** (x0 + (x1 - x0) * (d - y0) / (y1 - y0))
        return None
    units = {"expected_nits": round(0.18 * 250.0 / math.pi, 3)}
    for dy, kind in ((-500.0, "point"), (500.0, "rect")):
        c = RL.read_render_target_pixel(world(), rt, int(650 + dy), 50)
        d = (c.r + c.g + c.b) / 3.0 / 255.0
        units[kind] = {"display": round(d, 4), "radiance_nits_via_ladder": invert(d)}
    for k in ("point", "rect"):
        r = units[k]["radiance_nits_via_ladder"]
        units[k]["ratio_to_expected"] = round(r / units["expected_nits"], 3) if r else None
    REP["light_units"] = units
    for a in acts + rig + [cap]:
        EAS.destroy_actor(a)


def program():
    les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    for _ in range(5):
        yield
    ok = les.load_level(C.LEVEL)
    REP["level_loaded"] = bool(ok)
    REP["world"] = world().get_path_name()
    log("level loaded", ok, REP["world"])
    # compile every kit material's shaders now (get_statistics blocks until they exist), then let the engine settle
    t = time.time()
    stats = {}
    for a in ue.EditorAssetLibrary.list_assets(C.MAT_DEST, recursive=False, include_folder=False):
        m = ue.load_asset(a.split(".")[0])
        try:
            s = MEL.get_statistics(m)
            stats[m.get_name()] = {"vs": int(s.num_vertex_shader_instructions), "ps": int(s.num_pixel_shader_instructions)}
        except Exception as exc:  # noqa: BLE001
            stats[m.get_name()] = str(exc)[:120]
    REP["material_statistics"] = stats
    REP["compile_sec"] = round(time.time() - t, 1)
    save_rep()
    t = time.time()
    n = 0
    while n < WARM or time.time() - t < WARM_MIN_SEC:
        n += 1
        yield
    REP["warm_ticks_done"] = n
    REP["warm_done_sec"] = round(time.time() - T0, 1)
    actors = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
    ppv = next((a for a in actors.values() if a.get_class().get_name() == "PostProcessVolume"), None)
    if ppv is not None:
        REP["level_exposure_bias"] = float(ppv.get_editor_property("settings").get_editor_property("auto_exposure_bias"))
    jobs = [(cam, cam, W, H) for cam in CAMS] + [(cam, f"{cam}_ref_aspect", REF_WH[0], REF_WH[1])
                                                  for cam in REF_ASPECT if cam in CAMS]
    for cam, name, w0, h0 in jobs:
        ca = actors.get("CAM_" + cam)
        lay = LAYOUT_CAMS.get(cam)
        if ca is None or lay is None:
            REP["errors"].append(f"camera actor CAM_{cam} not in the level or not in layout.json")
            continue
        tw, th, crop = target_size(lay, w0, h0)
        cap, cc, rt, fov = make_capture(ca, lay, tw, th)
        off = C.camera_exposure_offset(lay)
        if off:
            pp_bias(cc, REP.get("level_exposure_bias", C.EXPOSURE_BIAS) + off)
        rec = {"fov_deg": round(fov, 3), "loc": [round(v, 2) for v in (ca.get_actor_location().x, ca.get_actor_location().y,
                                                                      ca.get_actor_location().z)],
               "rot": [round(ca.get_actor_rotation().pitch, 3), round(ca.get_actor_rotation().yaw, 3)], "checkpoints": {},
               "camera": cam, "out_wh": [w0, h0], "target_wh": [tw, th], "crop": crop, "exposure_offset_ev": off}
        t = time.time()
        done = 0
        for cp in CHECKPOINTS:
            yield from run_frames(cc, cp - done)
            done = cp
            rec["checkpoints"][cp] = export(rt, SEQ, f"{name}_f{cp:03d}.png")
        if crop:   # the capture step crops raw/<name>.png into <name>.png (ak_crop.py)
            rec["raw"] = export(rt, C.CAPTURES / "raw", f"{name}.png")
            rec["final"] = str(C.CAPTURES / f"{name}.png")
        else:
            rec["final"] = export(rt, C.CAPTURES, f"{name}.png")
        rec["sec"] = round(time.time() - t, 1)
        REP["captures"][name] = rec
        save_rep()
        log("CAPTURED", name, rec["sec"], "s")
        if name == CAMS[0]:
            # diagnostics on the first camera: is Lumen GI / volumetric fog actually in the capture?
            for flag in [f for f in os.environ.get("AK_DIAG", "LumenGlobalIllumination,LumenReflections,VolumetricFog").split(",") if f]:
                show_flag(cc, flag, False)
                yield from run_frames(cc, 32)
                REP["diag"][f"{flag}_off"] = export(rt, DIAG, f"{cam}_{flag}_off.png")
                show_flag(cc, flag, True)
                setp(cc, "show_flag_settings", [])
                yield from run_frames(cc, 32)
            if SWEEP:
                base = REP.get("level_exposure_bias", C.EXPOSURE_BIAS)
                offs = [float(x) for x in os.environ.get("AK_SWEEP_OFFSETS", "-1,-0.5,0,0.5,1,1.5,2,2.5").split(",")]
                for off in offs:
                    pp_bias(cc, base + off)
                    yield from run_frames(cc, int(os.environ.get("AK_SWEEP_FRAMES", "48")))   # 8 was unconverged
                    REP["diag"][f"bias_{base + off:+.2f}"] = export(rt, DIAG, f"{cam}_bias_{base + off:+.2f}.png")
            save_rep()
        EAS.destroy_actor(cap)
    if LADDER:
        yield from ladder()
        save_rep()
    REP["passed"] = (len(REP["captures"]) == len(jobs) and not REP["errors"]
                     and all(Path(r.get("raw", r["final"])).exists() for r in REP["captures"].values()))
    REP["sec"] = round(time.time() - T0, 1)
    save_rep()
    log(f"AK_STEP_DONE capture passed={REP['passed']}")
    ue.log(f"AK_STEP_DONE capture passed={REP['passed']} cams={len(REP['captures'])}")


GEN = program()
STATE = {}


def tick(dt):
    if STATE.get("busy") or STATE.get("finished"):
        return
    STATE["busy"] = True
    try:
        next(GEN)
    except StopIteration:
        STATE["finished"] = True
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    except Exception:  # noqa: BLE001
        STATE["finished"] = True
        REP["errors"].append(traceback.format_exc()[-3000:])
        REP["passed"] = False
        save_rep()
        ue.log_error(traceback.format_exc())
        ue.log("AK_STEP_DONE capture passed=False")
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    finally:
        STATE["busy"] = False


STATE["cb"] = ue.register_slate_post_tick_callback(tick)
try:
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    pass
log("registered; cams", CAMS)
