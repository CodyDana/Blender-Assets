import sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

rgb = load_rgb()
L = rgb.mean(-1)
def zoom(a, x0, y0, x1, y1, S):
    return np.repeat(np.repeat(a[y0:y1, x0:x1], S, 0), S, 1)
# dark-range stretch: 0..0.35 -> 0..1 (per channel), gamma to lift shadows
g = np.clip(rgb / 0.35, 0, 1) ** 0.7
save_png(zoom(g, 420, 60, 540, 130, 6), OUT + "dark_top_x420.png")
save_png(zoom(g, 420, 560, 540, 615, 6), OUT + "dark_holebot_x420.png")
save_png(zoom(g, 180, 60, 300, 140, 6), OUT + "dark_top_x180.png")
# print column profiles at several x across the top edge and hole bottom, 1 px
for x in (200, 350, 500, 650, 800):
    col = L[60:130, x - 2:x + 3].mean(1)
    print("TOPCOL x=%d" % x, " ".join("%d:%.2f" % (60 + i, v) for i, v in enumerate(col)))
for x in (420, 500, 580):
    col = L[560:612, x - 2:x + 3].mean(1)
    print("HBCOL x=%d" % x, " ".join("%d:%.2f" % (560 + i, v) for i, v in enumerate(col)))
for x in (300, 500, 700):
    col = L[820:870, x - 2:x + 3].mean(1)
    print("BOTCOL x=%d" % x, " ".join("%d:%.2f" % (820 + i, v) for i, v in enumerate(col)))
for y in (250, 470, 700):
    row = L[y - 2:y + 3, 100:170].mean(0)
    print("LEFTROW y=%d" % y, " ".join("%d:%.2f" % (100 + i, v) for i, v in enumerate(row)))
    row = L[y - 2:y + 3, 840:920].mean(0)
    print("RIGHTROW y=%d" % y, " ".join("%d:%.2f" % (840 + i, v) for i, v in enumerate(row)))
