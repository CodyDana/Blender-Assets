"""Grip inspection renders (headless Blender, Workbench studio light): the review blend's pistol_grip (+ the guard and
receiver for context) from front-right 3/4, front, left side and below -> scratch/detail_grip/views_<tag>.png.

    blender -b scratch/detail_grip/AR01_grip.blend --factory-startup --python Scripts/guns/rifle/parts/grip_views.py -- --tag r2_i6
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
tag = argv[argv.index("--tag") + 1] if "--tag" in argv else "x"
HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "WorkFiles" / "guns" / "rifle" / "scratch" / "detail_grip"
keep = {"pistol_grip", "trigger_guard", "receiver", "pistol_grip_checker"}
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o.name not in keep
g = bpy.data.objects["pistol_grip"]
c = sum((g.matrix_world @ Vector(b) for b in g.bound_box), Vector()) / 8.0
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "OBJECT"
sc.display.shading.show_cavity = False
for o in bpy.data.objects:
    if o.type == "MESH":
        o.color = (0.75, 0.55, 0.42, 1) if o.name.startswith("pistol_grip") else (0.25, 0.25, 0.27, 1)
sc.render.resolution_x, sc.render.resolution_y = 700, 900
cam_d = bpy.data.cameras.new("insp")
cam_d.type = "ORTHO"
cam_d.ortho_scale = 0.125
cam = bpy.data.objects.new("insp", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
views = {"q34": (0.75, -0.55, 0.25), "front": (1.0, -0.05, 0.05), "left": (0.05, 1.0, 0.05), "below": (0.35, -0.3, -0.89)}
files = []
for name, d in views.items():
    dv = Vector(d).normalized()
    cam.location = c + dv * 0.5
    cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
    p = OUT / f"_v_{name}.png"
    sc.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    files.append(p)
# stitch
imgs = [bpy.data.images.load(str(p)) for p in files]
W, H = 700, 900
out = bpy.data.images.new("sheet", W * len(imgs), H)
import numpy as np
buf = np.zeros((H, W * len(imgs), 4), np.float32)
for i, im in enumerate(imgs):
    a = np.array(im.pixels[:], np.float32).reshape(H, W, 4)
    buf[:, i * W:(i + 1) * W] = a
out.pixels = buf.ravel()
out.filepath_raw = str(OUT / f"views_{tag}.png")
out.file_format = "PNG"
out.save()
print("VIEWS_DONE", OUT / f"views_{tag}.png")
