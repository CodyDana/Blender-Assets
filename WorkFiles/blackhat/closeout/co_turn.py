"""Close-out flicker probe (as measure_r2): EEVEE 1 sample, 3.2 m, 85 mm, 16 frames x 0.25 deg, RGBA EXR.
blender -b BLEND --factory-startup --python co_turn.py -- OUTDIR"""
import bpy, math, sys, os
from mathutils import Vector
OUT = sys.argv[sys.argv.index("--") + 1]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.view_settings.view_transform = 'Standard'
sc.render.film_transparent = True
w = bpy.data.worlds.new("coW"); sc.world = w; w.use_nodes = True
bg = [n for n in w.node_tree.nodes if n.type == 'BACKGROUND'][0]; bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1); bg.inputs[1].default_value = 0.6
objs = {o.name: o for o in bpy.data.objects}
for n, o in objs.items():
    if n.startswith("UCX") or n.startswith("SOCKET"): o.hide_render = True
for i in range(3): objs[f"SM_BlackHat_LOD{i}"].hide_render = (i != 0)
sun = bpy.data.objects.new("coSun", bpy.data.lights.new("coSun", 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 4.0; sun.data.angle = math.radians(3)
sun.rotation_euler = (math.radians(90 - 45), 0, math.radians(140))
cam = bpy.data.objects.new("coCam", bpy.data.cameras.new("coCam")); sc.collection.objects.link(cam); sc.camera = cam
root = objs["SM_BlackHat_LodGroup"]
tgt = (0, 0, 0.07)
e = math.radians(18); a = math.radians(180)
cam.location = Vector((3.2 * math.cos(e) * math.sin(a), -3.2 * math.cos(e) * math.cos(a), tgt[2] + 3.2 * math.sin(e)))
cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 85
sc.render.resolution_x, sc.render.resolution_y = 960, 540; sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = 1
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_mode = 'RGBA'
BASE = float(os.environ.get("CO_BASE_YAW", "0"))
N = int(os.environ.get("CO_FRAMES", "16"))
for i in range(N):
    root.rotation_euler = (0, 0, math.radians(BASE + i * 0.25))
    sc.render.filepath = os.path.join(OUT, f"f_{i:02d}.exr"); bpy.ops.render.render(write_still=True)
print("TURN DONE")
