import sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *
rgb = load_rgb().astype(np.float64)
L = rgb.mean(-1); RB = rgb[..., 0] - rgb[..., 2]
for y in (380, 420, 470, 520, 570):
    l = L[y - 2:y + 3, 372:416].mean(0); r = RB[y - 2:y + 3, 372:416].mean(0)
    print("Y%d L " % y + " ".join("%d:%.2f" % (372 + i, v) for i, v in enumerate(l)))
    print("Y%d RB" % y + " ".join("%d:%.2f" % (372 + i, v) for i, v in enumerate(r)))
for y in (380, 470, 570):
    l = L[y - 2:y + 3, 600:640].mean(0); r = RB[y - 2:y + 3, 600:640].mean(0)
    print("R%d L " % y + " ".join("%d:%.2f" % (600 + i, v) for i, v in enumerate(l)))
    print("R%d RB" % y + " ".join("%d:%.2f" % (600 + i, v) for i, v in enumerate(r)))
def zoom(a, x0, y0, x1, y1, S):
    return np.repeat(np.repeat(a[y0:y1, x0:x1], S, 0), S, 1)
save_png(zoom(np.clip(rgb / 0.7, 0, 1), 360, 350, 430, 610, 3), OUT + "zoom_hole_left_edge.png")
