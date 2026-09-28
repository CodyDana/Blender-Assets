# -*- coding: utf-8 -*-
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
arr, info = P.read_png(ROOT + "/References/PaperBomb/paperbomb_guide.png")
f = P.to_float(arr, info)[..., :3]
H, W = f.shape[:2]
r, g, b = f[..., 0], f[..., 1], f[..., 2]
warm = r - b
val = np.max(f, axis=-1)

print("image %dx%d" % (W, H))
print("\n-- warm (R-B) horizontal profiles, every 16th px --")
for y in [70, 200, 700, 1200, 1340, 1360, 1380, 1400, 1420, 1430, 1440]:
    row = warm[y]
    s = "".join("%d" % min(9, max(0, int(v * 40))) for v in row[::16])
    print("y=%4d |%s|" % (y, s))

print("\n-- warm vertical profiles at several x --")
for x in [210, 240, 300, 512, 700, 780, 800]:
    col = warm[:, x]
    s = "".join("%d" % min(9, max(0, int(v * 40))) for v in col[::24])
    print("x=%4d |%s|" % (x, s))

print("\n-- value (max RGB) rows --")
for y in [1360, 1400, 1430, 1450, 1470]:
    row = val[y]
    s = "".join("%d" % min(9, max(0, int((1.0 - v) * 30))) for v in row[::16])
    print("y=%4d |%s|" % (y, s))

print("\n-- raw samples --")
for (y, x) in [(1200, 210), (1200, 220), (1200, 230), (1200, 240),
               (1420, 210), (1420, 230), (1420, 260), (1420, 300),
               (1380, 500), (1400, 500), (1420, 500), (1440, 500),
               (60, 500), (70, 500), (80, 500)]:
    print("  (%4d,%4d) rgb=%s warm=%.4f" % (y, x, [int(v) for v in arr[y, x, :3]], warm[y, x]))
