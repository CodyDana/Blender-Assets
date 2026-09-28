"""compose.py <ctx_dir> <out_dir>: bay_ctx_hero.png (front | persp) and bay_vs_reference.png (back_wall.png bay | front)"""
import sys
import numpy as np
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0].rsplit("\\", 1)[0])
from pngio import read_png, write_png
C, O = sys.argv[1], sys.argv[2]
REF = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/reference/back_wall.png"
def rgb(a):
    return a[..., :3] if a.shape[2] >= 3 else np.repeat(a, 3, 2)
def resize(a, h):
    H, W = a.shape[:2]; w = int(round(W * h / H))
    ys = (np.arange(h) + 0.5) * H / h - 0.5; xs = (np.arange(w) + 0.5) * W / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 1); x0 = np.clip(np.floor(xs).astype(int), 0, W - 1)
    y1 = np.clip(y0 + 1, 0, H - 1); x1 = np.clip(x0 + 1, 0, W - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]; fx = np.clip(xs - x0, 0, 1)[None, :, None]
    a = a.astype(np.float32)
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return (top * (1 - fy) + bot * fy).round().astype(np.uint8)
f = rgb(read_png(C + "/ctx_front.png")); p = rgb(read_png(C + "/ctx_persp.png"))
gap = np.full((f.shape[0], 12, 3), 90, np.uint8)
write_png(O + "/bay_ctx_hero.png", np.concatenate([f, gap, p], 1))
r = rgb(read_png(REF))[15:475, 300:890]
a = resize(r, 600); b = resize(f, 600)
gap = np.full((600, 12, 3), 90, np.uint8)
write_png(O + "/bay_vs_reference.png", np.concatenate([a, gap, b], 1))
print("composed", a.shape, b.shape)
