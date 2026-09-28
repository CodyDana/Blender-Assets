"""Crop + nearest/bilinear upscale PNGs headlessly (Blender numpy). args: src out x0 y0 x1 y1 scale [src2 ...]"""
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
def load(p):
    im = bpy.data.images.load(p); w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[::-1]
def save(arr, p):
    h, w = arr.shape[:2]
    im = bpy.data.images.new("o", w, h, alpha=True); im.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).ravel())
    im.filepath_raw = p; im.file_format = "PNG"; im.save()
i = 0
while i + 6 < len(a) + 1 and i < len(a):
    src, out, x0, y0, x1, y1, s = a[i:i + 7]; i += 7
    A = load(src)[int(y0):int(y1), int(x0):int(x1)]
    s = int(s)
    A = np.repeat(np.repeat(A, s, 0), s, 1)
    save(A, out)
