"""crop tool: args: out.png x0 y0 x1 y1 scale [grid_step]  (ref pixel coords, top-down). Nearest upscale. Optional grid lines every grid_step ref px (labelled by tick colour)."""
import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
a = sys.argv[sys.argv.index('--')+1:]
ref = load_srgb()
jobs = [a[i:i+7] for i in range(0, len(a), 7)]
for j in jobs:
    out, x0, y0, x1, y1, k, g = j[0], *map(int, j[1:7])
    c = ref[y0:y1, x0:x1].copy()
    if k > 1:
        c = upscale(c, k)
    if g > 0:
        for gx in range(((x0 + g - 1)//g)*g, x1, g):
            col = (gx - x0)*k
            c[:, col] = [1, 0, 0] if gx % (g*5) == 0 else [0, 0.8, 1]
        for gy in range(((y0 + g - 1)//g)*g, y1, g):
            row = (gy - y0)*k
            c[row, :] = [1, 0, 0] if gy % (g*5) == 0 else [0, 0.8, 1]
    save_png(out, c)
