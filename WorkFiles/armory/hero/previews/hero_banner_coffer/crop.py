"""Crop + upscale a region of an image: blender -b --factory-startup --python crop.py -- in out x0 y0 x1 y1 scale"""
import sys, bpy, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
src, dst = a[0], a[1]
x0, y0, x1, y1, s = map(int, a[2:7])
im = bpy.data.images.load(src)
W, H = im.size
px = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)[::-1]   # top row first
c = px[y0:y1, x0:x1]
c = np.repeat(np.repeat(c, s, axis=0), s, axis=1)[::-1]
h, w = c.shape[:2]
out = bpy.data.images.new("c", w, h, alpha=True)
out.pixels.foreach_set(c.ravel())
out.filepath_raw = dst
out.file_format = "PNG"
out.save()
