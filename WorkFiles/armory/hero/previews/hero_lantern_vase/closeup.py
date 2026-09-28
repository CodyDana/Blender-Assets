"""Close-up render of one hero piece of hero_lantern_vase (development helper, previews folder only).
blender -b --factory-startup --python closeup.py -- <piece> <cx,cy,cz> <dir x,y,z> <ortho_scale> <out.png> [samples]"""
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

A = sys.argv[sys.argv.index("--") + 1:]
os.environ["ARMORY_HERO_ONLY"] = "hero_lantern_vase"
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "armory"))
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_armory_kit as K  # noqa: E402

sc = bpy.context.scene
for n in K.MATERIALS:
    K.build_material(n)
hero = {p.name: p for m in K.HERO.MODULES for p in m.pieces(K.HERO.G)}
coll = bpy.data.collections.new("H")
sc.collection.children.link(coll)
o = hero[A[0]].build(coll)
for ch in o.children:
    ch.hide_render = True
c = Vector([float(t) for t in A[1].split(",")])
d = Vector([float(t) for t in A[2].split(",")]).normalized()
sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = True
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.cycles.samples = int(A[5]) if len(A) > 5 else 32
sc.render.resolution_x, sc.render.resolution_y = 900, 900
sc.view_settings.view_transform = "AgX"
w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.2, 0.2, 0.2, 1)
bg.inputs["Strength"].default_value = 0.8
for name, dd, e in (("Key", d + Vector((0.6, 0, 0.8)), 60), ("Fill", d + Vector((-0.8, 0, 0.2)), 25)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = e
    ld.size = 1.0
    lo = bpy.data.objects.new(name, ld)
    lo.location = c + dd.normalized() * 2.0
    lo.rotation_euler = (c - lo.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
cd = bpy.data.cameras.new("C")
cd.type = "ORTHO"
cd.ortho_scale = float(A[3])
cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam)
cam.location = c + d * 3
cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam
sc.render.filepath = A[4]
bpy.ops.render.render(write_still=True)
