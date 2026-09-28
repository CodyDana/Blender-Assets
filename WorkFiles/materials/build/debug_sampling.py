"""Debug (nothing saved): is the isolated-texel contamination in the UV captures a sampling artefact?
Transient material: BaseColor = Detail16.r (straw), captured 1:1 like np_render; variants: default filter, and the
texture's filter switched to Nearest IN MEMORY (never saved)."""
import json, sys
from pathlib import Path
import unreal
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials")
import np_render
OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/build/debug_sampling")
OUT.mkdir(parents=True, exist_ok=True)
MEL = unreal.MaterialEditingLibrary
EAS = np_render.EAS
w = np_render.world()
tex = unreal.load_asset("/Game/NinjaPack/Textures/BlackHat/T_BlackHat_Straw_Detail16")
mat = unreal.new_object(unreal.Material, name="NP_DebugSample")
ts = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -300, 0)
ts.set_editor_property("texture", tex)
ts.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
MEL.connect_material_property(ts, "R", unreal.MaterialProperty.MP_BASE_COLOR)
MEL.recompile_material(mat)
MEL.get_statistics(mat)
plane = unreal.load_asset("/Engine/BasicShapes/Plane")
R = {}
def cap(label, x0):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x0, 0, 0), np_render.rot())
    smc = a.get_editor_property("static_mesh_component"); smc.set_static_mesh(plane); smc.set_material(0, mat)
    a.set_actor_scale3d(unreal.Vector(20.48, 20.48, 1.0))
    c, cc, rt = np_render._capture(w, 2048, 2048, unreal.SceneCaptureSource.SCS_BASE_COLOR,
                                   unreal.TextureRenderTargetFormat.RTF_RGBA16F, unreal.Vector(x0, 0, 1000.0),
                                   np_render.rot(pitch=-90.0), ortho_width=2048)
    cc.capture_scene(); cc.capture_scene()
    R[label] = np_render._export(w, rt, OUT, label + ".exr")
    EAS.destroy_actor(c); EAS.destroy_actor(a)
def cap_tiles(label, x0, n):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x0, 0, 0), np_render.rot())
    smc = a.get_editor_property("static_mesh_component"); smc.set_static_mesh(plane); smc.set_material(0, mat)
    a.set_actor_scale3d(unreal.Vector(20.48, 20.48, 1.0))
    t = 2048 // n
    for i in range(n):
        for j in range(n):
            cx = x0 - 1024 + t * (i + 0.5); cy = -1024 + t * (j + 0.5)
            c, cc, rt = np_render._capture(w, t, t, unreal.SceneCaptureSource.SCS_BASE_COLOR,
                                           unreal.TextureRenderTargetFormat.RTF_RGBA16F, unreal.Vector(cx, cy, 1000.0),
                                           np_render.rot(pitch=-90.0), ortho_width=t)
            cc.capture_scene(); cc.capture_scene()
            R[f"{label}_{i}_{j}"] = np_render._export(w, rt, OUT, f"{label}_{i}_{j}.exr")
            EAS.destroy_actor(c)
    EAS.destroy_actor(a)
cap("origin_default", 0)
cap_tiles("tiles4", 0, 4)
(OUT / "debug_sampling.json").write_text(json.dumps(R, indent=1))
print("NP_DEBUG_SAMPLING_DONE")
