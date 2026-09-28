"""pb_verify_saved.py -- reopen the SAVED /Game/Characters/MetaHumans/MH_PlayerBase in a fresh editor session,
read its body measurements and capture a front body + face shot, then quit WITHOUT saving anything.
Proves the conform persisted on disk (attempt 4's editor process hit an access violation after its log closed).

Run through pb_run_conform.ps1-style launch (one editor at a time):
    UnrealEditor.exe CharacterLab.uproject -ExecutePythonScript=<this> -RenderOffscreen -Unattended -NoSplash
        -NoSound -NoTextureStreaming -NoMetaHumanAccountPortalLoginFallback -abslog=<log>
Writes WorkFiles/MetaHuman/player_base/verify_saved.json + captures/verify_*.png.
"""
import json
import sys
import time
import traceback
from pathlib import Path

import unreal as ue

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_base"
CAP = OUT / "captures"
CHAR_PATH = "/Game/Characters/MetaHumans/MH_PlayerBase"
REPORT = {"asset": CHAR_PATH, "status": "starting", "steps": []}
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline import lock  # noqa: E402

lock.assert_owner("MH_PlayerBase", "claude")


def note(msg):
    REPORT["steps"].append(msg)
    (OUT / "verify_saved.json").write_text(json.dumps(REPORT, indent=2, default=str), encoding="utf-8")
    ue.log("PB_VERIFY " + msg)


state = {"frame": 0, "shot": 0, "busy": False, "done": False}


def finish(ok):
    state["done"] = True
    ue.unregister_slate_post_tick_callback(state["handle"])
    try:
        if mhs.is_object_added_for_editing(ch):
            mhs.remove_object_to_edit(ch)
    except Exception:  # noqa: BLE001
        REPORT["teardown_error"] = traceback.format_exc()
    REPORT["status"] = "done" if ok else "failed"
    note("finished (nothing saved)")
    ue.SystemLibrary.quit_editor()


try:
    ue.EditorLoadingAndSavingUtils.new_blank_map(False)
    world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    ch = ue.load_asset(CHAR_PATH)
    REPORT["loaded_class"] = ch.get_class().get_name() if ch else None
    mhs = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    assert isinstance(ch, ue.MetaHumanCharacter), "MH_PlayerBase did not load as a MetaHumanCharacter"
    assert mhs.try_add_object_to_edit(ch), "try_add_object_to_edit failed"
    REPORT["constraints"] = {str(c.name): round(float(c.target_measurement), 2)
                             for c in mhs.get_body_constraints(ch, False)}
    REPORT["face_model_coefficients"] = len(mhs.get_face_model_coefficients(ch))
    REPORT["rigging_state"] = str(mhs.get_rigging_state(ch)) if hasattr(mhs, "get_rigging_state") else "n/a"
    REPORT["can_build_meta_human"] = bool(mhs.can_build_meta_human(ch, False))
    note("loaded + opened for edit")
    for pitch, yaw, inten, shadows in ((-27.0, -117.0, 4.0, True), (-12.0, -58.0, 2.0, False), (-37.0, 90.0, 2.0, False)):
        light = actors.spawn_actor_from_class(ue.DirectionalLight, ue.Vector(0, 0, 0), ue.Rotator(roll=0, pitch=pitch, yaw=yaw))
        light.light_component.set_intensity(inten)
        light.light_component.set_cast_shadows(shadows)
    sky = actors.spawn_actor_from_class(ue.SkyLight, ue.Vector(0, 0, 0), ue.Rotator())
    sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(1.5)
    sky.light_component.recapture_sky()
    actor = mhs.spawn_meta_human_actor(ch, True)
    mhs.assemble_for_preview(ch)
    origin, extent = actor.get_actor_bounds(False)
    REPORT["bounds"] = {"origin": [origin.x, origin.y, origin.z], "extent": [extent.x, extent.y, extent.z]}
    cam = actors.spawn_actor_from_class(ue.SceneCapture2D, ue.Vector(0, 0, 0), ue.Rotator())
    cap = cam.get_component_by_class(ue.SceneCaptureComponent2D)
    rt = ue.RenderingLibrary.create_render_target2d(world, 1000, 1200, ue.TextureRenderTargetFormat.RTF_RGBA8)
    rt.set_editor_property("target_gamma", 2.2)
    cap.set_editor_property("texture_target", rt)
    cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cap.set_editor_property("capture_every_frame", False)
    cap.set_editor_property("always_persist_rendering_state", True)
    pp = cap.get_editor_property("post_process_settings")
    for key, value in [("override_auto_exposure_method", True), ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                       ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
                       ("override_auto_exposure_apply_physical_camera_exposure", True),
                       ("auto_exposure_apply_physical_camera_exposure", False)]:
        pp.set_editor_property(key, value)
    cap.set_editor_property("post_process_settings", pp)
    top = REPORT["constraints"].get("Height", 185.6)
    shots = [("verify_Body_Front.png", (0, 380, 93), (0, 0, 93)),
             ("verify_Face_Front.png", (0, 76, top - 12), (0, 6, top - 12))]

    def aim(i):
        loc = ue.Vector(*shots[i][1])
        cam.set_actor_location_and_rotation(loc, ue.MathLibrary.find_look_at_rotation(loc, ue.Vector(*shots[i][2])), False, False)
        cap.set_editor_property("fov_angle", 30.0)

    aim(0)

    def tick(_dt):
        if state["busy"] or state["done"]:
            return
        state["busy"] = True
        try:
            state["frame"] += 1
            cap.capture_scene()
            if state["frame"] in (30, 140):
                ue.AutomationLibrary.finish_loading_before_screenshot()
            if state["frame"] >= 150 + 60 * state["shot"]:
                ue.RenderingLibrary.export_render_target(world, rt, str(CAP), shots[state["shot"]][0])
                note("captured " + shots[state["shot"]][0])
                state["shot"] += 1
                if state["shot"] >= len(shots):
                    finish(True)
                else:
                    aim(state["shot"])
        except Exception:  # noqa: BLE001
            REPORT["error"] = traceback.format_exc()
            finish(False)
        finally:
            state["busy"] = False

    state["handle"] = ue.register_slate_post_tick_callback(tick)
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    REPORT["error"] = traceback.format_exc()
    REPORT["status"] = "failed"
    note("failed in setup")
    ue.SystemLibrary.quit_editor()
