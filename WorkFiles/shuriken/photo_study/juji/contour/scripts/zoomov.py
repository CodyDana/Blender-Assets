import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load()
m5 = np.load(ROOT + "mask_t5.0.npy"); m35 = np.load(ROOT + "mask_t3.5.npy")
def up(a, k): return np.repeat(np.repeat(a, k, 0), k, 1)
def crop(name, y0, y1, x0, x1, k):
    c = rgb[y0:y1, x0:x1].copy()
    lo, hi = np.percentile(c, 1), np.percentile(c, 99.5); c = np.clip((c - lo) / (hi - lo), 0, 1)
    c = up(c, k)
    for m, col in ((m35, [0, 1, 1]), (m5, [1, 0, 0])):
        mm = up(m[y0:y1, x0:x1], k)
        e = mm & ~erode(mm, 1)
        c[e] = col
    write_png(ROOT + name, c)
crop("zoom_toparm_neck.png", 240, 520, 590, 770, 3)
crop("zoom_right_tip.png", 520, 780, 1150, 1370, 3)
crop("zoom_top_blade.png", 0, 260, 560, 800, 3)
