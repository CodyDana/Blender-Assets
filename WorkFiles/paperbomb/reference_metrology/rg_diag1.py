# -*- coding: utf-8 -*-
"""Diagnostic: what does the tag mask actually look like? METROLOGY ONLY."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402

a, info = R.read_stored(R.RG)
print("shape", a.shape, info.get("bit_depth"), info.get("colour_type"))
w = R.warmth(a)
print("warmth percentiles", [round(float(np.percentile(w, p)), 4) for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)])
lu = R.luma(a)
print("luma percentiles", [round(float(np.percentile(lu, p)), 4) for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)])
print("corner pixels TL", a[0, 0], "TR", a[0, -1], "BL", a[-1, 0], "BR", a[-1, -1])
print("centre-left row 300:", [tuple(np.round(a[300, x], 3)) for x in range(0, 24, 2)])
print("row300 warmth:", [round(float(w[300, x]), 3) for x in range(0, 30)])
print("col150 warmth top:", [round(float(w[y, 150]), 3) for y in range(0, 30)])
print("col150 warmth bot:", [round(float(w[y, 150]), 3) for y in range(653 - 30, 653)])
print("row300 warmth right:", [round(float(w[300, x]), 3) for x in range(300 - 30, 300)])

lo = float(np.percentile(w, 1.0)); hi = float(np.percentile(w, 99.0))
for f in (0.25, 0.5, 0.8):
    m = w > (lo + f * (hi - lo))
    m2 = R.fill_holes(R.open_(R.close_(m, 2), 2))
    lab, comps = R.label(m2)
    print("f", f, "thr", round(lo + f * (hi - lo), 4), "raw", int(m.sum()),
          "ncomp", len(comps), "top3", [(c['n'], c['x0'], c['x1'], c['y0'], c['y1']) for c in comps[:3]])
    mm = R.fill_holes(lab == comps[0]['label'])
    ys = np.flatnonzero(mm.any(1)); xs = np.flatnonzero(mm.any(0))
    print("   bbox x", xs[0], xs[-1], "y", ys[0], ys[-1], "area", int(mm.sum()))
    # per-row extents
    print("   row extents y=5,20,100,326,600,640:",
          [(y, int(np.flatnonzero(mm[y])[0]) if mm[y].any() else None,
            int(np.flatnonzero(mm[y])[-1]) if mm[y].any() else None) for y in (5, 20, 100, 326, 600, 640, 648)])
