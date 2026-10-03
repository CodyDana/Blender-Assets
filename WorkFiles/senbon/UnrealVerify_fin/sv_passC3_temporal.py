"""PASS C3 (fresh process, REAL RHI): does a scene capture with a persisted view state run the project's temporal AA
(TSR/TAA) here?  Static camera, 1920x1080, 90 deg H-FOV, unlit mask, FINAL_COLOR_LDR, always_persist_rendering_state
ON, 48 captures; frames kept at capture 1, 8, 24, 48.  If temporal AA runs, the thin needle's pixels become fractional
and its line continuous; if not, they stay binary (that is reported, not assumed).  Nothing is saved.
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\senbon\UnrealVerify_fin")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import sv_common as C  # noqa: E402

OUT = HERE / "passC3.json"
MDIR = HERE / "renders_mask"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
res = {"engine": unreal.SystemLibrary.get_engine_version(), "t0": time.time(), "runs": [],
       "cvars": {}}
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for cv in ("r.AntiAliasingMethod", "r.TemporalAA.Upsampling", "r.SceneCapture.EnableViewExtensions"):
        res["cvars"][cv] = str(unreal.SystemLibrary.get_console_variable_int_value(cv))
    mask = unreal.load_asset(f"{C.MATDEST}/M_SV_Mask")
    needle = unreal.load_asset(f"{C.DEST}/SM_Senbon_Needle")
    for dm in (2.63, 4.0):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        comp = a.get_editor_property("static_mesh_component")
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_static_mesh(needle)
        comp.set_material(0, mask)
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -dm * 100.0, 0),
                                         unreal.Rotator(roll=0.0, pitch=0.0, yaw=90.0))
        cc = cam.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("always_persist_rendering_state", True)
        cc.set_editor_property("fov_angle", 90.0)
        pp = cc.get_editor_property("post_process_settings")
        for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
                     ("override_auto_exposure_apply_physical_camera_exposure", True),
                     ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.0)):
            pp.set_editor_property(k, v)
        cc.set_editor_property("post_process_settings", pp)
        files = {}
        for i in range(1, 49):
            cc.capture_scene()
            if i in (1, 8, 24, 48):
                fn = f"temporal_needle_{dm:.2f}_c{i}.png"
                RL.export_render_target(world, rt, str(MDIR), fn)
                files[i] = fn
        res["runs"].append({"distance_m": dm, "files": files})
        EAS.destroy_actor(cam)
        EAS.destroy_actor(a)
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - res["t0"], 1)
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
unreal.log("SV_PASSC3_DONE")
