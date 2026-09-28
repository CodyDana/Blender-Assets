import json, traceback
import unreal
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
MEL = unreal.MaterialEditingLibrary
out = {}
try:
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    out["world"] = w.get_name() if w else None
    plane = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, -4.0, -3.0), unreal.Rotator())
    pc = plane.get_editor_property("static_mesh_component")
    pc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    ok = pc.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    out["set_mesh"] = ok
    out["mesh"] = str(pc.get_editor_property("static_mesh"))
    out["mobility"] = str(pc.get_editor_property("mobility"))
    o, e, r = unreal.SystemLibrary.get_component_bounds(pc)
    out["plane_bounds"] = [o.x, o.y, o.z, e.x, e.y, e.z]
    la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100), unreal.MathLibrary.make_rot_from_x(unreal.Vector(0.25, 0.55, -1.0)))
    lc = la.get_editor_property("directional_light_component")
    lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property("intensity", 3.0)
    for zc, pitch, tag in ((60.0, -90.0, "above"), (-60.0, 90.0, "below")):
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0.5, -6.0, zc), unreal.Rotator(roll=0.0, pitch=pitch, yaw=-90.0))
        cc = cam.get_editor_property("capture_component2d")
        for src, fmt, nm in ((unreal.SceneCaptureSource.SCS_BASE_COLOR, unreal.TextureRenderTargetFormat.RTF_RGBA16F, "base"),
                             (unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR, unreal.TextureRenderTargetFormat.RTF_RGBA16F, "hdr")):
            rt = RL.create_render_target2d(w, 64, 64, fmt)
            cc.set_editor_property("texture_target", rt)
            cc.set_editor_property("capture_source", src)
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            cc.set_editor_property("ortho_width", 44.0)
            cc.set_editor_property("auto_calculate_ortho_planes", False)
            for _ in range(3):
                cc.capture_scene()
            px = RL.read_render_target_raw_uv(w, rt, 0.5, 0.5)
            out[f"{tag}_{nm}"] = [px.r, px.g, px.b]
        cam_rot = cam.get_actor_rotation()
        fwd = cam.get_actor_forward_vector()
        out[f"{tag}_fwd"] = [fwd.x, fwd.y, fwd.z]
        EAS.destroy_actor(cam)
except Exception:
    out["error"] = traceback.format_exc()
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck\probe9.json", "w").write(json.dumps(out, indent=1, default=str))
