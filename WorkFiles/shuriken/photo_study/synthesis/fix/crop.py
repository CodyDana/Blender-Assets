"""Crop + nearest-neighbour upscale helper. Args after --: src x0 y0 x1 y1 scale out"""
import bpy, numpy as np, os, sys
a = sys.argv[sys.argv.index("--") + 1:]
src, x0, y0, x1, y1, s, out = a[0], *map(int, a[1:6]), a[6]
img = bpy.data.images.load(src); W, H = img.size
b = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(b)
im = b.reshape(H, W, 4)[::-1, :, :3][y0:y1, x0:x1]
im = np.repeat(np.repeat(im, s, 0), s, 1)
h, w, _ = im.shape
o = bpy.data.images.new(os.path.basename(out), width=w, height=h, alpha=False)
buf = np.ones((h, w, 4), np.float32); buf[..., :3] = im
o.pixels.foreach_set(buf[::-1].ravel()); o.filepath_raw = out; o.file_format = 'PNG'; o.save()
print("wrote", out, W, H)
