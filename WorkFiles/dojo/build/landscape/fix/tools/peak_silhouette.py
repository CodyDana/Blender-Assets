"""The far skyline through CAM_LandscapeRef from the LS_Far heightmap itself (the exact data the landscape is built
from): per column of the 1024 x 1536 frame, the highest projected terrain row (rays marched 1.5-14 km). Reports each
peak's silhouette width on the rows 40 / 80 / 120 px under its summit (contiguous run around the summit column), and
the same numbers measured BY HAND on the reference (its peak outlines). usage: peak_silhouette.py <LS_Far.r16> [label]"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\landscape")
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\fix\tools")
import ls_geo as G  # noqa: E402
from proj import CAMS  # noqa: E402

F = G.u16_to_z(np.fromfile(sys.argv[1], dtype="<u2").reshape(2017, 2017), G.LS_FAR)
fx, fy = G.grid_axes(G.LS_FAR)
c = CAMS["CAM_LandscapeRef"]
o = np.array(c["loc"], float)
f = np.array(c["look_at"], float) - o
f /= np.linalg.norm(f)
r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
u = np.cross(r, f)
W, H = 1024, 1536
k = (W / 2) / math.tan(math.radians(c["hfov_deg"]) / 2)
d = np.arange(1500.0, 14000.0, 15.0)
sil = np.full(W, H, float)
for col in range(120, 760):
    ray = f + r * (col + 0.5 - W / 2) / k
    hdir = ray[:2] / np.linalg.norm(ray[:2])
    X, Y = o[0] + hdir[0] * d, o[1] + hdir[1] * d
    cc = np.clip((X - fx[0]) / 8.0, 0, 2015.999); rr = np.clip((fy[0] - Y) / 8.0, 0, 2015.999)
    c0, r0 = cc.astype(int), rr.astype(int)
    a, b = cc - c0, rr - r0
    z = (F[r0, c0] * (1 - a) * (1 - b) + F[r0, c0 + 1] * a * (1 - b) + F[r0 + 1, c0] * (1 - a) * b + F[r0 + 1, c0 + 1] * a * b)
    P = np.c_[X, Y, z] - o
    row = H / 2 - k * (P @ u) / (P @ f)
    sil[col] = row.min()
out = {}
for name, (sx, sy) in (("A", (348, 460)), ("B", (566, 496))):
    win = range(max(120, sx - (230 if name == "A" else 60)), min(760, sx + (230 if name == "A" else 60)))
    top = min(win, key=lambda x: sil[x])
    rec = {"summit_px": [int(top), round(float(sil[top]), 1)]}
    for dy in (40, 80, 120):
        lvl = sil[top] + dy
        lo = top
        while lo > 120 and sil[lo - 1] < lvl:
            lo -= 1
        hi = top
        while hi < 759 and sil[hi + 1] < lvl:
            hi += 1
        rec[str(dy)] = int(hi - lo)
    out[name] = rec
# the reference's peak outlines, read off a 2x crop of dojo_landscape_ref.png (1024 x 1536) with the 40 / 80 / 120 px
# rows drawn (fix/analysis/refpeaks.png): A under (348, 457): 155 / 290 / >= 330 (its left flank goes behind the trees);
# B under (567, 493): 100 / 185 / 275
out["reference_by_eye"] = {"A": {"40": 155, "80": 290, "120": ">=330"}, "B": {"40": 100, "80": 185, "120": 275}}
print(sys.argv[2] if len(sys.argv) > 2 else "", json.dumps(out))
