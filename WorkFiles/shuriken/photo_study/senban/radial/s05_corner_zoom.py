import sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

rgb = load_rgb()
def zoom(a, x0, y0, x1, y1, S):
    c = a[y0:y1, x0:x1]
    return np.repeat(np.repeat(c, S, 0), S, 1)
g = np.clip(rgb / 0.72, 0, 1)
save_png(zoom(g, 55, 55, 135, 135, 8), OUT + "zoom_tl.png")
save_png(zoom(g, 845, 20, 925, 100, 8), OUT + "zoom_tr.png")
save_png(zoom(g, 300, 60, 400, 140, 6), OUT + "zoom_top_x300.png")
save_png(zoom(g, 440, 560, 540, 620, 6), OUT + "zoom_holebot.png")
print("DONE")
