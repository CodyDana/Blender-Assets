# -*- coding: utf-8 -*-
"""Diagnostic: pick ink/red thresholds from the data and list elements."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402
import metro as M  # noqa: E402

SCRATCH = os.environ["PB_SCRATCH"]
key = sys.argv[-1] if sys.argv[-1] in ("V1", "V2") else "V1"
rect = np.load(os.path.join(SCRATCH, "rect_%s.npy" % key)).astype(np.float64)
H, W = rect.shape[:2]
print("%s rect %dx%d" % (key, W, H))

warm = rect[..., 0] - rect[..., 2]
val = np.max(rect, axis=-1)
sup0 = (warm > 0.10) | (val < 0.80)
# row/column fill to close the ink holes and keep the chamfers out
sup = np.zeros_like(sup0)
for y in range(H):
    xs = np.flatnonzero(sup0[y])
    if xs.size:
        sup[y, xs[0]:xs[-1] + 1] = True
supc = np.zeros_like(sup0)
for x in range(W):
    ys = np.flatnonzero(sup0[:, x])
    if ys.size:
        supc[ys[0]:ys[-1] + 1, x] = True
sup = sup & supc
print("support frac", round(float(sup.mean()), 4))

lin = P.srgb_to_linear(rect)
h, s, v = P.rgb_to_hsv(rect)
paper0 = sup & (v > 0.72) & (s < 0.45)
print("paper0 frac of support", round(float(paper0.sum() / sup.sum()), 4))

rc = 0.045 * W
PC = np.stack([M.masked_blur(lin[..., c], paper0, rc)[0] for c in range(3)], -1)
c = lin / np.maximum(PC, 1e-5)
alphaG = np.clip(1.0 - c[..., 1], 0, 1)
redness = np.clip(c[..., 0] - c[..., 1], -1, 1)

print("\n-- joint histogram: rows = alphaG bin, cols = redness bin --")
ab = np.linspace(0, 1, 11)
rb = np.linspace(-0.1, 0.7, 9)
ai = np.clip(np.digitize(alphaG[sup], ab) - 1, 0, 9)
ri = np.clip(np.digitize(redness[sup], rb) - 1, 0, 7)
Hh = np.zeros((10, 8))
np.add.at(Hh, (ai, ri), 1)
Hh = Hh / Hh.sum() * 100
print("        " + "".join("%7.2f" % x for x in 0.5 * (rb[:-1] + rb[1:])))
for i in range(10):
    print("a=%.2f  " % (0.5 * (ab[i] + ab[i + 1])) + "".join("%7.3f" % x for x in Hh[i]))

for at in (0.25, 0.35, 0.45, 0.55):
    ink = sup & (alphaG > at)
    print("alphaG>%.2f -> ink area frac of tag = %.4f" % (at, ink.sum() / sup.sum()))

INK = sup & (alphaG > 0.35)
for rt in (0.08, 0.12, 0.16, 0.20):
    red = INK & (redness > rt)
    print("redness>%.2f -> red frac of ink = %.4f" % (rt, red.sum() / INK.sum()))

black = INK & (redness <= 0.12)
red = INK & (redness > 0.12)
for nm, m in (("black", black), ("red", red)):
    lab, n = M.label_cc(M.closing(m, 3))
    st = M.cc_stats(lab, n)
    st.sort(key=lambda d: -d["area_px"])
    print("\n== %s: %d comps; top 14 by area (bbox in tag fractions) ==" % (nm, n))
    for d in st[:14]:
        x0, y0, x1, y1 = d["bbox_px"]
        print("   area=%8.0f (%.4f of tag)  bbox u[%.3f,%.3f] v[%.3f,%.3f]  centroid(%.3f,%.3f)"
              % (d["area_px"], d["area_px"] / sup.sum(), x0 / W, x1 / W, y0 / H, y1 / H,
                 d["cx_px"] / W, d["cy_px"] / H))
