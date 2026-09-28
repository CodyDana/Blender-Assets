"""DEV preview (not shipped): workbench-ish renders of the work blend: LOD0 low parts and the high-poly, front + side."""
import bpy, sys, math
from mathutils import Euler, Vector
out = sys.argv[sys.argv.index("--") + 1]
what = sys.argv[sys.argv.index("--") + 2]
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.film_transparent = False
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = True
col = {"low0": "LOD0_parts", "low1": "LOD1_parts", "low2": "LOD2_parts", "high": "HIGH"}[what]
for o in bpy.data.collections[col].objects:
    o.hide_render = False
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
if what.startswith("low"):
    m = bpy.data.materials.new("grey"); m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.3, 0.32, 0.36, 1); bs.inputs["Roughness"].default_value = 0.5
    for o in bpy.data.collections[col].objects:
        for i in range(len(o.data.materials)):
            o.data.materials[i] = m
L = bpy.data.lights.new("k", "SUN"); L.energy = 3; lo = bpy.data.objects.new("k", L); sc.collection.objects.link(lo)
lo.rotation_euler = (math.radians(50), math.radians(-30), math.radians(-20))
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"
views = sys.argv[sys.argv.index("--") + 3].split(",")
for v in views:
    name, zc, scale, rx, rz = v.split(":")
    zc, scale = float(zc) / 1000, float(scale) / 1000
    cam.data.ortho_scale = scale
    if rz == "front":
        cam.location = (0, -2, zc); cam.rotation_euler = Euler((math.pi / 2, 0, 0)); cam.rotation_euler.rotate_axis("Z", math.pi)
    elif rz == "side":
        cam.location = (2, 0, zc); cam.rotation_euler = Euler((math.pi / 2, 0, math.pi / 2)); cam.rotation_euler.rotate_axis("Z", math.pi)
    elif rz == "persp":
        cam.data.type = "PERSP"; cam.data.lens = 60
        cam.location = (0.25, -0.45, zc - 0.12); cam.rotation_euler = (Vector((0, 0, zc)) - cam.location).to_track_quat("-Z", "Y").to_euler(); cam.rotation_euler.rotate_axis("Z", math.pi)
    sc.render.resolution_x, sc.render.resolution_y = int(rx.split("x")[0]), int(rx.split("x")[1])
    sc.render.filepath = f"{out}_{name}.png"
    bpy.ops.render.render(write_still=True)
    cam.data.type = "ORTHO"
