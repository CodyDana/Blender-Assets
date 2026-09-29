# crop.py <in> <out> x0 y0 x1 y1 [scale]: crop (pixel coords, top-left origin), optional integer upscale, PNG
import sys, numpy as np, bpy
a = sys.argv[sys.argv.index("--") + 1:]
src, out, x0, y0, x1, y1 = a[0], a[1], *map(int, a[2:6]); k = int(a[6]) if len(a) > 6 else 1
im = bpy.data.images.load(src); w, h = im.size
px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
c = px[y0:y1, x0:x1]
if k > 1: c = c.repeat(k, 0).repeat(k, 1)
c = c[::-1]
o = bpy.data.images.new("c", c.shape[1], c.shape[0], alpha=False); o.pixels[:] = c.ravel()
o.filepath_raw = out; o.file_format = "PNG"; o.save(); print("saved", out, c.shape)
