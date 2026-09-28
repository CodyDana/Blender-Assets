import sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

rgb = load_rgb()
crops = {
    "top_mid": (460, 60, 540, 140),
    "hole_bottom": (380, 540, 460, 620),
    "hole_top": (440, 330, 520, 410),
    "hole_left": (360, 430, 440, 510),
    "hole_right": (580, 430, 660, 510),
    "left_mid": (100, 440, 180, 520),
    "right_mid": (840, 440, 920, 520),
    "bottom_mid": (460, 800, 540, 880),
    "corner_tl": (50, 50, 130, 130),
    "corner_tr": (850, 20, 930, 100),
    "corner_bl": (80, 850, 160, 930),
    "corner_br": (880, 830, 960, 910),
}
S = 5
for nm, (x0, y0, x1, y1) in crops.items():
    c = rgb[y0:y1, x0:x1]
    # contrast stretch for visibility
    lo, hi = np.percentile(c, 1), np.percentile(c, 99)
    c = (c - lo) / max(hi - lo, 1e-3)
    big = np.repeat(np.repeat(c, S, 0), S, 1)
    save_png(big, OUT + "crop_%s.png" % nm)
print("DONE")
