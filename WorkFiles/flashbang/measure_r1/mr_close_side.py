import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *; from mr_png import write_png
PANELS = {"p1": (6, 756, 318, 1220), "p2": (323, 756, 629, 1220), "p3": (634, 756, 939, 1220), "p4": (946, 756, 1249, 1220)}
R = ref(); tiles = []
W = ROOT + "WorkFiles/flashbang/measure_r1/"
for k, (x0, y0, x1, y1) in PANELS.items():
    a = R[y0:y1, x0:x1]; b = load_png(W + f"mr_{k}.png")[..., :3] * 255
    b = b[:a.shape[0], :a.shape[1]]
    tiles.append(np.concatenate([a, np.full((a.shape[0], 4, 3), 230.), b, np.full((a.shape[0], 12, 3), 0.)], 1))
write_png(W + "mr_close_side.png", np.concatenate(tiles, 1))
