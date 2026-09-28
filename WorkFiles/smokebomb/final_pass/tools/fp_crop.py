"""fp_crop OUT.png x0 y0 w h scale img1 [img2 ...]  (png or npy, side by side)"""
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import write_png, read_png
out = sys.argv[1]; x0, y0, w, h, s = map(int, sys.argv[2:7])
cols = []
for p in sys.argv[7:]:
    gain = 1.0
    if "@" in p:
        p, g = p.split("@"); gain = float(g)
    a = np.load(p) if p.endswith(".npy") else read_png(p) / 255.0
    a = np.asarray(a, np.float64)[..., :3]
    if a.max() > 1.5: a = a / 255.0
    c = a[y0:y0 + h, x0:x0 + w] * gain
    c = np.repeat(np.repeat(c, s, 0), s, 1)
    cols += [c, np.full((c.shape[0], 6, 3), 0.5)]
write_png(out, np.clip(np.concatenate(cols[:-1], 1), 0, 1))
