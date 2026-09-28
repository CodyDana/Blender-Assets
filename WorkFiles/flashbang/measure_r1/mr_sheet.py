import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *; from mr_png import write_png
W = ROOT + "WorkFiles/flashbang/measure_r1/"
PANELS = {"p1": (6, 756, 318, 1220), "p2": (323, 756, 629, 1220), "p3": (634, 756, 939, 1220), "p4": (946, 756, 1249, 1220)}
R = ref(); S = R.copy()
row = load_png(W + "mr_row.png")[..., :3] * 255
S[:748] = row[:748]
for k, (x0, y0, x1, y1) in PANELS.items():
    b = load_png(W + f"mr_{k}.png")[..., :3] * 255
    S[y0:y1, x0:x1] = b[:y1 - y0, :x1 - x0]
write_png(W + "mr_eight_views.png", S)
write_png(W + "mr_side_by_side.png", np.concatenate([R, np.full((1254, 12, 3), 230.), S], 1))
