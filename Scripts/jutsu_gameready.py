import bpy, os, math
from mathutils import Vector

scene=bpy.context.scene
BASE=r"C:\Users\Cody\Desktop\Blender_Projects"
os.makedirs(BASE+r"\Exports", exist_ok=True)

# ---- §1 scale & units ----
scene.unit_settings.system='METRIC'
scene.unit_settings.length_unit='CENTIMETERS'

# ---- §3 bake: render the fully-revealed seal to a 4K RGBA decal texture ----
scene.frame_set(78)                      # reveal Front at max -> whole seal visible
floor=bpy.data.objects["Floor"]
floor.hide_render=True                   # ink only, transparent background = alpha mask
cam=bpy.data.objects["Cam"]
cam.data.type='ORTHO'; cam.data.ortho_scale=4.0
cam.location=(0,0,3.0); cam.rotation_euler=(0,0,0)
scene.render.film_transparent=True
scene.render.resolution_x=4096; scene.render.resolution_y=4096
scene.cycles.samples=64
scene.render.image_settings.media_type='IMAGE'
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
TEX=BASE+r"\Exports\T_SummoningJutsu_D.png"
scene.render.filepath=TEX
bpy.ops.render.render(write_still=True)
floor.hide_render=False
scene.render.film_transparent=False
print("BAKED texture")

# ---- §2/§4/§5 game-ready decal plane with proper UVs and UE naming ----
old=bpy.data.objects.get("SM_SummoningJutsu")
if old: bpy.data.objects.remove(old, do_unlink=True)
bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0,0,0.0005))
plane=bpy.context.active_object; plane.name="SM_SummoningJutsu"
img=bpy.data.images.load(TEX, check_existing=True)
img.colorspace_settings.name='sRGB'
img.pack()
m=bpy.data.materials.get("M_SummoningJutsu") or bpy.data.materials.new("M_SummoningJutsu")
m.use_nodes=True; nt=m.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
out=nt.nodes.new("ShaderNodeOutputMaterial"); b=nt.nodes.new("ShaderNodeBsdfPrincipled")
tex=nt.nodes.new("ShaderNodeTexImage"); tex.image=img
nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
b.inputs["Roughness"].default_value=0.9
nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
try: m.surface_render_method='BLENDED'
except Exception: pass
plane.data.materials.append(m)
# transforms applied by construction (scale 1,1,1 at origin)
print("SM_SummoningJutsu decal plane built")

# ---- §6 FBX export (-Y forward, Z up, selected only) ----
bpy.ops.object.select_all(action='DESELECT')
plane.select_set(True)
bpy.context.view_layer.objects.active=plane
bpy.ops.export_scene.fbx(
    filepath=BASE+r"\Exports\SM_SummoningJutsu.fbx",
    use_selection=True,
    axis_forward='-Y', axis_up='Z',
    apply_unit_scale=True, global_scale=1.0,
    mesh_smooth_type='FACE',
    bake_space_transform=True,
    path_mode='COPY', embed_textures=False)
print("FBX exported")

# ---- §8 verify: render decal-plane version for comparison vs geometry ----
seal=bpy.data.objects["SealScript"]
seal.hide_render=True
scene.render.resolution_x=1200; scene.render.resolution_y=800
scene.render.filepath=BASE+r"\Renders\jutsu_gameready_check.png"
cam.data.ortho_scale=4.2
bpy.ops.render.render(write_still=True)
seal.hide_render=False
plane.hide_render=True                   # hi-res stays default-visible for renders
bpy.ops.wm.save_mainfile()
print("GAMEREADY_OK")
