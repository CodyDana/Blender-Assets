"""DojoLab SHOWCASE captures: offscreen stills of the saved L_Dojo from the showcase cameras (never saves anything).
(dj_capture.py's proven pattern, pointed at showcase/layout_showcase.json and unreal/showcase/captures.)

Runs INSIDE a full offscreen editor (UnrealEditor-Cmd DojoLab.uproject -RenderOffscreen -dx12 -ExecutePythonScript=this,
started by run_capture.ps1), driven by a Slate post-tick generator so every capture gets real engine frames (shaders,
distance fields, the real-time sky light, Lumen / TSR history, auto exposure) - the armory's ak_capture pattern.
For each layout.json camera (CAM_* actors saved in the level): a SceneCapture2D at the camera, its horizontal FOV,
FINAL_COLOR_LDR into the camera's out_wh RGBA8 target, persistent rendering state, Lumen GI + reflections re-enabled in
the capture's post-process (UE 5.8 scene captures disable Lumen by default), captured once per tick for FRAMES ticks. The
invisible gameplay actors (the 1v1 boundary, the GASP traversal markers) are in the capture's hidden-actor list, as in
game. Out: captures/<cam>.png (+ sequence checkpoints). Env: DJ_FRAMES (default 96), DJ_WARM (warm-up ticks, 400).
Result: WorkFiles/dojo/build/unreal/showcase/capture.json
"""
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal")))
import unreal as ue  # noqa: E402
import dj_common as C  # noqa: E402
import dj_sc_common as S  # noqa: E402

EAS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
RL = ue.RenderingLibrary
LAYOUT = S.load()
CAMS = {c["name"]: c for c in LAYOUT["cameras"]}
# round 3: DJ_CAMS (comma list) captures a subset (look iterations); DJ_CAPTURE_DIR writes the stills elsewhere
if os.environ.get("DJ_CAMS"):
    _want = [c.strip() for c in os.environ["DJ_CAMS"].split(",") if c.strip()]
    CAMS = {k: CAMS[k] for k in _want if k in CAMS}
CAPDIR = Path(os.environ.get("DJ_CAPTURE_DIR", str(S.SC_CAPTURES)))
FRAMES = int(os.environ.get("DJ_FRAMES", "96"))
WARM = int(os.environ.get("DJ_WARM", "400"))
WARM_MIN_SEC = float(os.environ.get("DJ_WARM_SEC", "20"))
CHECKPOINTS = sorted({1, 16, 48, FRAMES})
SEQ = CAPDIR / "sequence"
REP = {"engine": ue.SystemLibrary.get_engine_version(), "capture_dir": str(CAPDIR), "cams": list(CAMS), "frames": FRAMES, "warm_ticks": WARM, "captures": {},
       "notes": [], "errors": []}
T0 = time.time()


def log(*a):
    ue.log("[DJ_CAPTURE] " + " ".join(str(x) for x in a))


def save_rep():
    C.write_json(S.SC_OUT / "capture.json", REP)
    if CAPDIR != S.SC_CAPTURES:
        C.write_json(CAPDIR / "capture.json", REP)


def world():
    return ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"setp {type(obj).__name__}.{k}: {str(exc)[:160]}")
        return False


def make_capture(cam_actor, lay, hidden):
    w, h = lay["out_wh"]
    cap = EAS.spawn_actor_from_class(ue.SceneCapture2D, cam_actor.get_actor_location(), cam_actor.get_actor_rotation())
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world(), w, h, ue.TextureRenderTargetFormat.RTF_RGBA8)
    for k, v in (("texture_target", rt), ("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                 ("capture_every_frame", False), ("capture_on_movement", False),
                 ("always_persist_rendering_state", True), ("fov_angle", float(lay["hfov_deg"]))):
        setp(cc, k, v)
    flags = [ue.EngineShowFlagsSetting(show_flag_name=f, enabled=True) for f in S.CAPTURE_SHOW_FLAGS]
    if flags:   # round 3 fix f1: e.g. the volumetric cloud layer
        setp(cc, "show_flag_settings", flags)
    for a in hidden:   # as in game: the invisible gameplay actors stay out of the picture
        cc.hide_actor_components(a, True)
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_dynamic_global_illumination_method", True),
                 ("dynamic_global_illumination_method", ue.DynamicGlobalIlluminationMethod.LUMEN),
                 ("override_reflection_method", True), ("reflection_method", ue.ReflectionMethod.LUMEN),
                 ("override_lumen_surface_cache_resolution", True), ("lumen_surface_cache_resolution", 1.0)):
        setp(pp, k, v)
    setp(cc, "post_process_settings", pp)
    setp(cc, "post_process_blend_weight", 1.0)
    return cap, cc, rt


def export(rt, folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    RL.export_render_target(world(), rt, str(folder), name)
    return str(folder / name)


def program():
    les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    for _ in range(5):
        yield
    REP["level_loaded"] = bool(les.load_level(C.LEVEL))
    for cv in S.CAPTURE_CVARS:   # round 3 fix f1 (look_r3.ENV capture_cvars)
        ue.SystemLibrary.execute_console_command(world(), cv)
    REP["cvars"] = list(S.CAPTURE_CVARS)
    log("level loaded", REP["level_loaded"])
    t = time.time()
    n = 0
    while n < WARM or time.time() - t < WARM_MIN_SEC:
        n += 1
        yield
    REP["warm_ticks_done"] = n
    actors = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
    hidden = [a for lab, a in actors.items() if lab.startswith("TRV_") or lab.startswith("SM_DGB_Boundary_1v1")]
    REP["hidden_in_capture"] = len(hidden)
    for name, lay in CAMS.items():
        ca = actors.get(name)
        if ca is None:
            REP["errors"].append(f"camera actor {name} not in the level")
            continue
        cap, cc, rt = make_capture(ca, lay, hidden)
        rec = {"hfov": lay["hfov_deg"], "out_wh": lay["out_wh"], "checkpoints": {}}
        done = 0
        t = time.time()
        for cp in CHECKPOINTS:
            for _ in range(cp - done):
                cc.capture_scene()
                yield
            done = cp
            rec["checkpoints"][cp] = export(rt, SEQ, f"{name}_f{cp:03d}.png")
        rec["final"] = export(rt, CAPDIR, f"{name}.png")
        rec["sec"] = round(time.time() - t, 1)
        REP["captures"][name] = rec
        save_rep()
        log("CAPTURED", name)
        EAS.destroy_actor(cap)
    REP["passed"] = len(REP["captures"]) == len(CAMS) and not REP["errors"] and all(
        Path(r["final"]).exists() for r in REP["captures"].values())
    REP["sec"] = round(time.time() - T0, 1)
    save_rep()
    ue.log(f"DJ_STEP_DONE sc_capture passed={REP['passed']} cams={len(REP['captures'])}")


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
        ue.log("DJ_STEP_DONE sc_capture passed=False")
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    finally:
        STATE["busy"] = False


STATE["cb"] = ue.register_slate_post_tick_callback(tick)
try:
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    pass
log("registered; cams", list(CAMS))
