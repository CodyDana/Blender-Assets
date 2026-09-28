"""Side-by-side comparison sheet: the reference image next to a render (same height), with a gap.
Run: blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <left.png> <right.png> <out.png>
"""
import sys

import bpy
import numpy as np

left, right, out = sys.argv[sys.argv.index("--") + 1:][:3]


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    return px


a, b = load(left), load(right)
h = min(a.shape[0], b.shape[0])


def fit(px):
    if px.shape[0] == h:
        return px
    idx = (np.arange(h) * px.shape[0] / h).astype(int)
    cols = (np.arange(int(px.shape[1] * h / px.shape[0])) * px.shape[0] / h).astype(int)
    return px[idx][:, cols]


a, b = fit(a), fit(b)
gap = np.ones((h, 24, 4), dtype=np.float32)
sheet = np.concatenate([a, gap, b], axis=1)
img = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0], alpha=False)
img.pixels[:] = sheet.ravel()
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("saved", out, sheet.shape)
