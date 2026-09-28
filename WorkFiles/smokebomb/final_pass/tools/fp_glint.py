"""fp_glint: luminance p99/p50 and CV over the ball (pixels differing from the backdrop) for each image."""
import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import read_png
out = {}
for p in sys.argv[1:]:
    a = read_png(p)[..., :3].astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    L = lin @ np.array([0.2126, 0.7152, 0.0722])
    # backdrop: the corner colour; the ball = pixels far from it, eroded
    bg = np.median(np.concatenate([a[:20, :20].reshape(-1, 3), a[-20:, -20:].reshape(-1, 3)]), 0)
    m = np.abs(a - bg).max(-1) > 0.08
    from numpy.lib.stride_tricks import sliding_window_view as sw
    mm = m.copy()
    for _ in range(6):
        mm[1:-1, 1:-1] &= m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:]
        m = mm.copy()
    v = L[mm]
    out[p[-60:]] = {"p99_p50": round(float(np.percentile(v, 99) / np.percentile(v, 50)), 2),
                             "cv": round(float(v.std() / v.mean()), 3), "px": int(mm.sum())}
print(json.dumps(out, indent=0))
