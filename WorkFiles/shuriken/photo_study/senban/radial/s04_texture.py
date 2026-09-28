import sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

rgb = load_rgb()
L = rgb.mean(-1)
h, w = L.shape

def box(a, r):
    # box filter via cumulative sums
    p = np.pad(a, r + 1, mode='edge')
    c = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return s[:h, :w] / (k * k)

m = box(L, 2); m2 = box(L * L, 2)
sd = np.sqrt(np.maximum(m2 - m * m, 0))
save_png(np.clip(sd / 0.06, 0, 1), OUT + "dbg_localstd.png")
# gradient magnitude of smoothed L
Ls = box(L, 1)
gy, gx = np.gradient(Ls)
g = np.hypot(gx, gy)
save_png(np.clip(g / 0.05, 0, 1), OUT + "dbg_gradmag.png")
# hole zoom of both, 3x
def zoom(a, x0, y0, x1, y1, S=3):
    c = a[y0:y1, x0:x1]
    return np.repeat(np.repeat(c, S, 0), S, 1)
save_png(zoom(np.clip(sd / 0.05, 0, 1), 360, 330, 650, 620), OUT + "dbg_hole_localstd.png")
save_png(zoom(np.clip(g / 0.04, 0, 1), 360, 330, 650, 620), OUT + "dbg_hole_grad.png")
c = rgb[330:620, 360:650]
save_png(zoom(np.clip((c - 0.0) / 0.7, 0, 1), 0, 0, 290, 290), OUT + "dbg_hole_rgb.png")
print("DONE")
