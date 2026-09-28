"""args: a.png b.png out.png x0 y0 x1 y1 scale  -> side-by-side a | b | 4x|a-b| crop (alpha composited on grey)."""
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
def load(p):
    im = bpy.data.images.load(p); w, h = im.size
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px)
    x = px.reshape(h, w, 4)[::-1]
    return x[..., :3] + (1 - x[..., 3:4]) * 0.18
A, B = load(a[0]), load(a[1]); x0, y0, x1, y1, s = map(int, a[3:8])
A, B = A[y0:y1, x0:x1], B[y0:y1, x0:x1]
D = np.clip(np.abs(A - B).max(2, keepdims=True) * 4, 0, 1).repeat(3, 2)
M = np.concatenate([A, B, D], 1)
M = np.repeat(np.repeat(M, s, 0), s, 1)
h, w = M.shape[:2]
im = bpy.data.images.new("o", w, h, alpha=True)
im.pixels.foreach_set(np.concatenate([M, np.ones((h, w, 1))], 2)[::-1].astype(np.float32).ravel())
im.filepath_raw = a[2]; im.file_format = "PNG"; im.save()
