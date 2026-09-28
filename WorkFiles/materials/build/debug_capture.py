import json, traceback
from pathlib import Path
import unreal
OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/build/debug_capture.json")
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
R = {}
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
R["world"] = w.get_path_name()
mi = unreal.load_asset("/Game/NinjaPack/MaterialInstances/MI_BlackHat_Straw")
R["stats"] = unreal.MaterialEditingLibrary.get_statistics(mi).get_editor_property("num_pixel_shader_instructions")
plane = unreal.load_asset("/Engine/BasicShapes/Plane")
def trial(label, x, scale, camz, ortho, res, rotator):
    acts = []
    try:
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, 0, 0), unreal.Rotator(0, 0, 0))
        acts.append(a)
        smc = a.get_editor_property("static_mesh_component")
        smc.set_static_mesh(plane); smc.set_material(0, mi)
        if scale != 1:
            a.set_actor_scale3d(unreal.Vector(scale, scale, 1))
        cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(x, 0, camz), rotator)
        acts.append(cap)
        R.setdefault("cap_rot", {})[label] = str(cap.get_actor_rotation())
        cc = cap.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(w, res, res, unreal.TextureRenderTargetFormat.RTF_RGBA32F)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        cc.set_editor_property("ortho_width", float(ortho))
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        cc.capture_scene(); cc.capture_scene()
        px = RL.read_render_target_raw_pixel(w, rt, res // 2, res // 2, False)
        R[label] = [px.r, px.g, px.b]
    except Exception:
        R[label] = traceback.format_exc()[-600:]
    finally:
        for a in acts: EAS.destroy_actor(a)
r_pos = unreal.Rotator(0, -90, 0)
r_kw = unreal.Rotator(); r_kw.pitch = -90.0
trial("probe_like", 1000, 1, 300, 80, 64, r_pos)
trial("probe_like_kwrot", 3000, 1, 300, 80, 64, r_kw)
trial("scaled20", 20000, 20.48, 300, 2048, 256, r_kw)
trial("scaled20_z1000", 40000, 20.48, 1000, 2048, 256, r_kw)
trial("big_res", 60000, 20.48, 1000, 2048, 2048, r_kw)
OUT.write_text(json.dumps(R, indent=1, default=str))
R["compiling_api"] = [n for n in dir(unreal) if "ompil" in n]
OUT.write_text(json.dumps(R, indent=1, default=str))
