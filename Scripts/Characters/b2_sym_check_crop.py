"""b2_sym_check_crop.py - PRIVATE / DO NOT SHIP. Checker helper: crop the same box (pixel coords, top-left origin) from
several PNGs, scale by an integer factor, and place them side by side.

  blender -b --factory-startup -P b2_sym_check_crop.py -- <abs out png> <x0> <y0> <x1> <y1> <scale> <abs in png> ...
"""
import bpy, sys, os
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
outp = a[0]; x0, y0, x1, y1, sc = map(int, a[1:6]); ins = a[6:]
assert os.path.isabs(outp)
tiles = []
for p in ins:
    im = bpy.data.images.load(p)
    w, h = im.size
    px = np.array(im.pixels[:]).reshape(h, w, 4)[::-1]  # top row first
    c = px[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, sc, 0), sc, 1)
    tiles.append(c)
    tiles.append(np.ones((c.shape[0], 6, 4)))
img = np.concatenate(tiles[:-1], 1)[::-1]
H, W = img.shape[:2]
o = bpy.data.images.new("crop", W, H, alpha=True)
o.pixels = img.ravel().tolist()
o.filepath_raw = outp; o.file_format = 'PNG'; o.save()
print("[crop]", outp, W, H)
