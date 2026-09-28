"""Render the saved hero_entrance assembly (Assets/Armory/Hero/hero_entrance.blend, opened read-only: never saved) from
four cameras framed like entrance.png's quadrants, compose a 2x2 sheet. Args: -- <out.png> <samples>"""
import math, sys
import bpy, numpy as np
from mathutils import Vector
out, samples = sys.argv[sys.argv.index("--") + 1:][:2]
sc = bpy.context.scene
sc.cycles.samples = int(samples)
W, H = 768, 512
sc.render.resolution_x, sc.render.resolution_y = W, H
VIEWS = [  # (location, target, lens, shift_y)
    ((6.0, 13.2, 1.75), (6.0, 0.0, 1.75), 42, 0.13),     # TL: level eye-height elevation, floor in front
    ((6.0, 24.0, 1.40), (6.0, 0.0, 1.40), 70, 0.11),     # TR: distant low elevation
    ((6.0, 7.2, 11.0), (6.0, 0.35, 0.8), 38, 0.0),       # BL: the high view down onto the step and mat
    ((12.6, 8.4, 1.9), (5.4, 0.2, 1.85), 36, 0.08),      # BR: 3/4 from the right front
]
tiles = []
for i, (loc, tgt, lens, sy) in enumerate(VIEWS):
    cd = bpy.data.cameras.new(f"RF{i}")
    cd.lens, cd.shift_y, cd.clip_end = lens, sy, 200
    cam = bpy.data.objects.new(f"RF{i}", cd)
    sc.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    tmp = out[:-4] + f"_v{i}.png"
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(tmp)
    tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4))
top = np.concatenate([tiles[0], tiles[1]], axis=1)
bot = np.concatenate([tiles[2], tiles[3]], axis=1)
sheet = np.concatenate([bot, top], axis=0)
sheet[:, W - 1:W + 1, :3] = 0.55
sheet[H - 1:H + 1, :, :3] = 0.55
img = bpy.data.images.new("sheet", 2 * W, 2 * H, alpha=True)
img.pixels.foreach_set(sheet.ravel())
img.filepath_raw = out
img.file_format = "PNG"
img.save()
import os
for i in range(len(VIEWS)):
    os.remove(out[:-4] + f"_v{i}.png")
