import sys, json
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

rgb = load_rgb()
h, w, _ = rgb.shape
print("SIZE", w, h)
B = 12
border = np.concatenate([rgb[:B].reshape(-1, 3), rgb[-B:].reshape(-1, 3),
                         rgb[:, :B].reshape(-1, 3), rgb[:, -B:].reshape(-1, 3)])
mu = border.mean(0); sd = border.std(0)
print("BORDER mean", mu.round(4), "std", sd.round(4))
# per-edge means (gradient check)
for nm, a in [("top", rgb[:B]), ("bot", rgb[-B:]), ("left", rgb[:, :B]), ("right", rgb[:, -B:])]:
    print("EDGE", nm, a.reshape(-1, 3).mean(0).round(4))
d = np.sqrt(((rgb - mu) ** 2).sum(-1))
bd = np.sqrt(((border - mu) ** 2).sum(-1))
print("BORDER dist pctl 50/99/99.9/max", np.percentile(bd, [50, 99, 99.9, 100]).round(4))
hist, edges = np.histogram(d, bins=40, range=(0, 1.0))
for c, e in zip(hist, edges):
    print("HIST %.3f %d" % (e, c))
save_png(np.clip(d / 0.6, 0, 1), OUT + "dbg_distance_map.png")
# horizontal profile through middle row across left edge and hole
y = h // 2
for x in range(90, 170, 2):
    print("ROWMID x=%d" % x, rgb[y, x].round(3), round(float(d[y, x]), 3))
# vertical profile through centre column across top edge
x = w // 2
for yy in range(60, 130, 2):
    print("COLMID y=%d" % yy, rgb[yy, x].round(3), round(float(d[yy, x]), 3))
for yy in range(800, 880, 2):
    print("COLMIDB y=%d" % yy, rgb[yy, x].round(3), round(float(d[yy, x]), 3))
