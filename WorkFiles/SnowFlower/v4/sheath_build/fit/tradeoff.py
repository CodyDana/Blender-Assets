"""Trade-off of the seat tilt vs wall/clearance/throat widening, on the shipped sword vertices (dev study)."""
import sys, math, json, os
sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import numpy as np
import shv4_spec as S, shv4_fit as F
verts, rep = F.load_sword_vertices()
allv = np.vstack([verts[0], verts[1], verts[2]])
hilt = allv[allv[:, 2] <= 128.6]; blade_all = allv[allv[:, 2] > 90.0]
base_outer = F.outer_half_at
res = {}
for wall, clr, extra in ((1.5, 0.75, 0.0), (1.5, 0.75, 1.5), (1.2, 0.6, 0.0), (1.2, 0.6, 1.5), (1.0, 0.5, 1.5)):
    S.MIN_WALL, S.CLEARANCE = wall, clr
    F.outer_half_at = (lambda z, e=extra: base_outer(z) + (e if S.row_of(z) < 169 else 0.0))
    rows = []
    for phi_deg in np.arange(-0.9, -0.29, 0.05):
        b = max((F.lateral_margin(math.radians(phi_deg), tx, hilt, blade_all)[:2] + (tx,) for tx in np.arange(-3, 4.01, 0.25)), key=lambda r: r[0])
        rows.append((round(float(phi_deg), 2), round(b[0], 2), float(b[2]), round(b[1])))
    key = f"wall{wall}_clr{clr}_throat+{extra}"
    res[key] = rows
    print(key, [r for r in rows], flush=True)
json.dump(res, open(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sheath_build/fit/tradeoff.json', 'w'), indent=0)
