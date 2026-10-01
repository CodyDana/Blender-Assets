"""r20 look: the floor material under NEUTRAL white light, old (r19: HPlank BC x tint 1.8) against new (r20 BC, tint 1.0).
Run: blender -b --factory-startup --python floor_swatch.py -- --src <blend with M_AK_Plank> --bc <new BC png> --tint 1.0
     --out <dir> [--tag new]
Renders two views of a 2 x 2 m patch (UV = metres / 4, the kit's tile):
  <tag>_albedo.png  top-down orthographic, uniform white world strength 1, specular 0, Standard view: pixel = albedo
  <tag>_studio.png  an oblique view under a neutral 6500 K-free white area key + a dim white world, AgX Medium
                    High Contrast, specular as built (the satin sheen included)."""
import sys
from pathlib import Path

import bpy

A = sys.argv[sys.argv.index("--") + 1:]


def arg(n, d=None):
    return A[A.index(n) + 1] if n in A else d


src, out, tag = arg("--src"), Path(arg("--out")), arg("--tag", "new")
bc_path, tint = arg("--bc"), arg("--tint")
with bpy.data.libraries.load(src, link=False) as (fr, to):
    to.materials = ["M_AK_Plank"]
mat = to.materials[0]
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
for n in nt.nodes:
    if n.type == "TEX_IMAGE" and n.image and n.image.name.endswith("_BC.png") and bc_path:
        n.image = bpy.data.images.load(bc_path, check_existing=False)
    if n.type == "VECT_MATH" and n.operation == "MULTIPLY" and tint is not None:
        n.inputs[1].default_value = (float(tint),) * 3
for n in nt.nodes:
    if n.type == "TEX_IMAGE":
        print("image", n.image.filepath)
    if n.type == "VECT_MATH":
        print("tint", tuple(n.inputs[1].default_value))

sc = bpy.context.scene
for o in list(sc.objects):
    bpy.data.objects.remove(o)
bpy.ops.mesh.primitive_plane_add(size=2.0)
pl = bpy.context.active_object
pl.data.materials.append(mat)
uv = pl.data.uv_layers.active.data
for lp in pl.data.loops:
    co = pl.data.vertices[lp.vertex_index].co
    uv[lp.index].uv = ((co.x + 1) / 4.0, (co.y + 1) / 4.0)   # 2 m = half the 4 m tile, boards along U (X)

sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
except Exception as exc:  # noqa: BLE001
    print("GPU setup failed:", exc)
sc.cycles.samples = 64
sc.cycles.use_denoising = True
world = bpy.data.worlds.new("W")
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
sc.world = world
cd = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cd)
sc.collection.objects.link(cam)
sc.camera = cam

# 1. albedo: top-down ortho, uniform white world, specular 0, Standard
spec_in = bsdf.inputs.get("Specular IOR Level")
spec0 = spec_in.default_value if spec_in else None
if spec_in:
    spec_in.default_value = 0.0
bg.inputs["Color"].default_value = (1, 1, 1, 1)
bg.inputs["Strength"].default_value = 1.0
cd.type = "ORTHO"
cd.ortho_scale = 2.0
cam.location = (0, 0, 3)
cam.rotation_euler = (0, 0, 0)
sc.render.resolution_x = sc.render.resolution_y = 512
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = 0.0
sc.render.filepath = str(out / f"{tag}_albedo.png")
bpy.ops.render.render(write_still=True)

# 2. studio: oblique, a white area key + dim white world, AgX, sheen on
if spec_in:
    spec_in.default_value = spec0
bg.inputs["Strength"].default_value = 0.15
ld = bpy.data.lights.new("Key", "AREA")
ld.energy = 400.0
ld.size = 1.5
ld.color = (1, 1, 1)
key = bpy.data.objects.new("Key", ld)
sc.collection.objects.link(key)
key.location = (-1.5, -2.0, 2.6)
key.rotation_euler = (0.65, 0, -0.6)
cd.type = "PERSP"
cd.lens = 40
cam.location = (0.0, -2.4, 1.5)
cam.rotation_euler = (1.05, 0, 0)
sc.render.resolution_x, sc.render.resolution_y = 800, 500
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.filepath = str(out / f"{tag}_studio.png")
bpy.ops.render.render(write_still=True)
print("swatch done", tag)
