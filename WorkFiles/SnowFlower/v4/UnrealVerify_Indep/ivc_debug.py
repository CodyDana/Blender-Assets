"""Render debug: why do captures come back empty?  Cube vs sheath, with/without material overrides, persp camera."""
import json, os, time, traceback
from pathlib import Path
import unreal

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep")
RDIR = HERE / "renders_debug"
RDIR.mkdir(parents=True, exist_ok=True)
DEST = os.environ["IV_DEST"]
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
res = {}
sp = []
try:
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cubem = unreal.load_asset("/Engine/BasicShapes/Cube")
    shm = unreal.load_asset(f"{DEST}/SM_SnowFlower_Sheath")
    for m in (cubem, shm):
        m.get_bounding_box(); m.get_num_triangles(0)  # forces the async mesh build to finish before any component uses it
    res["world"] = w.get_name() if w else None
    la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100), ML.make_rot_from_x(unreal.Vector(0.3, 0.5, -1.0)))
    la.get_editor_property("directional_light_component").set_editor_property("intensity", 5.0)
    sp.append(la)
    cube = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
    cube.static_mesh_component.set_static_mesh(cubem)
    sp.append(cube)
    sh = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 150, 0), unreal.Rotator())
    sh.static_mesh_component.set_static_mesh(shm)
    sp.append(sh)
    cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(-400, 75, 50), ML.make_rot_from_x(unreal.Vector(1, 0, -0.1)))
    sp.append(cam)
    cc = cam.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(w, 512, 512, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    cc.set_editor_property("fov_angle", 60.0)
    for _ in range(3):
        cc.capture_scene()
    RL.export_render_target(w, rt, str(RDIR), "dbg_basecolor.png")
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    for _ in range(3):
        cc.capture_scene()
    RL.export_render_target(w, rt, str(RDIR), "dbg_final.png")
    res["ok"] = True
except Exception:
    res["error"] = traceback.format_exc()
finally:
    for a in sp:
        try:
            EAS.destroy_actor(a)
        except Exception:
            pass
(HERE / "ivC_debug.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
