"""CardShopKit showcase room: offscreen stills of the saved L_CSK_Shop (never saves anything).

Runs INSIDE a full offscreen editor (UnrealEditor-Cmd CardShopKit.uproject -RenderOffscreen -dx12
-ExecutePythonScript=this, started by run_shop.sh), driven by a Slate post-tick generator so every capture gets real
engine frames: shaders compile, distance fields build, the real-time sky light recaptures and Lumen / TSR accumulate
history (the ArmoryLab ak_capture.py pattern; a -run=pythonscript commandlet never ticks the engine).

For each CAM_<name> actor in the level: a SceneCapture2D at the camera with its FOV, FINAL_COLOR_LDR into a
1600 x 900 RGBA8 target, persistent rendering state on, captured once per tick for FRAMES ticks; the last frame is
WorkFiles/cardshop/shop/captures/<name>.png. The level's unbound PostProcessVolume sets the exposure.
Env: CSK_CAMS (comma list, default every CAM_), CSK_FRAMES (default 64), CSK_WARM (warm-up ticks, default 400).
Result: WorkFiles/cardshop/shop/capture.json
"""
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal as ue  # noqa: E402
import csk_common as C  # noqa: E402

EAS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
RL = ue.RenderingLibrary
FRAMES = int(os.environ.get("CSK_FRAMES", "64"))
WARM = int(os.environ.get("CSK_WARM", "400"))
WARM_MIN_SEC = float(os.environ.get("CSK_WARM_SEC", "20"))
CAMS = [c for c in os.environ.get("CSK_CAMS", "").split(",") if c]
W, H = 1600, 900
OUT = C.SHOP_OUT / "captures"
REP = {"engine": ue.SystemLibrary.get_engine_version(), "frames": FRAMES, "warm_ticks": WARM, "res": [W, H],
       "captures": {}, "notes": [], "errors": []}
T0 = time.time()


def log(*a):
    ue.log("[CSK_CAPTURE] " + " ".join(str(x) for x in a))


def save_rep():
    C.write_json(C.SHOP_OUT / "capture.json", REP)


def world():
    return ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"setp {type(obj).__name__}.{k}: {str(exc)[:160]}")


def make_capture(cam):
    cap = EAS.spawn_actor_from_class(ue.SceneCapture2D, cam.get_actor_location(), cam.get_actor_rotation())
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world(), W, H, ue.TextureRenderTargetFormat.RTF_RGBA8)
    setp(cc, "texture_target", rt)
    setp(cc, "capture_source", getattr(ue.SceneCaptureSource, os.environ.get("CSK_SOURCE", "SCS_FINAL_COLOR_LDR")))
    setp(cc, "capture_every_frame", False)
    setp(cc, "capture_on_movement", False)
    setp(cc, "always_persist_rendering_state", True)
    fov = float(cam.get_component_by_class(ue.CameraComponent).get_editor_property("field_of_view"))
    setp(cc, "fov_angle", fov)
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_dynamic_global_illumination_method", True),
                 ("dynamic_global_illumination_method", ue.DynamicGlobalIlluminationMethod.LUMEN),
                 ("override_reflection_method", True), ("reflection_method", ue.ReflectionMethod.LUMEN),
                 ("override_lumen_front_layer_translucency_reflections", True),
                 ("lumen_front_layer_translucency_reflections", True)):
        setp(pp, k, v)
    setp(cc, "post_process_settings", pp)
    setp(cc, "post_process_blend_weight", 1.0)
    flag = os.environ.get("CSK_SHOWFLAG")                  # a diagnostic view, e.g. VisualizeMeshDistanceFields
    if flag:
        f = ue.EngineShowFlagsSetting()
        f.set_editor_property("show_flag_name", flag)
        f.set_editor_property("enabled", True)
        setp(cc, "show_flag_settings", [f])
    return cap, cc, rt, fov


def program():
    les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    for _ in range(5):
        yield
    ok = les.load_level(C.SHOP_LEVEL)
    REP["level_loaded"] = bool(ok)
    log("level loaded", ok)
    t = time.time()                    # compile every kit material now (get_statistics compiles), as ak_capture.py
    for a in ue.EditorAssetLibrary.list_assets(C.MAT_DEST, recursive=False, include_folder=False):
        try:
            ue.MaterialEditingLibrary.get_statistics(ue.load_asset(a.split(".")[0]))
        except Exception as exc:  # noqa: BLE001
            REP["notes"].append(f"stats {a}: {str(exc)[:120]}")
    REP["compile_sec"] = round(time.time() - t, 1)
    save_rep()
    t = time.time()
    n = 0
    while n < WARM or time.time() - t < WARM_MIN_SEC:
        n += 1
        yield
    REP["warm_ticks_done"] = n
    REP["warm_sec"] = round(time.time() - t, 1)
    cams = {a.get_actor_label()[4:]: a for a in EAS.get_all_level_actors() if a.get_actor_label().startswith("CAM_")}
    names = CAMS or sorted(cams, key=lambda s: int(s.split("_")[0][1:]) if s.split("_")[0][1:].isdigit() else 99)
    for name in names:
        cam = cams.get(name)
        if cam is None:
            REP["errors"].append(f"no CAM_{name} in the level")
            continue
        cap, cc, rt, fov = make_capture(cam)
        t = time.time()
        for _ in range(FRAMES):
            cc.capture_scene()
            yield
        OUT.mkdir(parents=True, exist_ok=True)
        RL.export_render_target(world(), rt, str(OUT), f"{name}.png")
        REP["captures"][name] = {"file": str(OUT / f"{name}.png"), "fov": round(fov, 2),
                                 "sec": round(time.time() - t, 1)}
        EAS.destroy_actor(cap)
        save_rep()
        log("captured", name)
    REP["passed"] = not REP["errors"] and all(Path(c["file"]).exists() for c in REP["captures"].values()) \
        and len(REP["captures"]) > 0
    REP["sec"] = round(time.time() - T0, 1)
    save_rep()
    ue.log(f"CSK_STEP_DONE capture passed={REP['passed']} cams={len(REP['captures'])}")


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
        ue.log("CSK_STEP_DONE capture passed=False")
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    finally:
        STATE["busy"] = False


STATE["cb"] = ue.register_slate_post_tick_callback(tick)
try:
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    pass
log("registered")
