from solve import *
import json, sys
CASES = {"SF": (1.2, 0.8, 0.40, 0.50), "S": (1.2, 0.9, 0.55, 0.70), "Tall": (1.0, 0.85, 0.50, 1.70),
         "L": (1.8, 1.3, 0.50, 0.70), "M": (1.8, 1.2, 0.70, 0.55), "LN": (1.6, 1.0, 0.45, 0.75)}
T = [("1", "L", 6.0, 4.00, 0), ("2", "M", 6.0, 8.70, 0), ("3", "LN", 6.0, 13.40, 0),
     ("5", "SF", 2.70, 3.75, 90), ("4", "Tall", 1.555, 8.35, 90), ("G3", "Tall", 1.575, 12.45, 90), ("G1", "S", 2.50, 14.30, 90),
     ("8", "SF", 9.30, 3.75, -90), ("6", "Tall", 10.445, 8.35, -90), ("G2", "Tall", 10.425, 12.45, -90), ("7", "S", 9.50, 14.30, -90)]
KE = dict(KEEP); KE.update({k + "_E": [1448 - v[1], 1448 - v[0], v[2], v[3]] for k, v in KEEP.items()})
fp, B = {}, {}
for lab, t, x, y, r in T:
    W, D, H, G = CASES[t]
    hx, hy = (D / 2, W / 2) if r in (90, -90) else (W / 2, D / 2)
    fp[lab] = (x - hx, x + hx, y - hy, y + hy)
    B[lab] = box(*fp[lab], H + G)
for k, v in B.items(): print(k, [round(a, 3) for a in fp[k]], [round(a) for a in v])
print("screen gaps (px) < 60:")
labs = list(B)
for i, a in enumerate(labs):
    for b in labs[i + 1:]:
        g = gap(B[a], B[b])
        if g < 60: print(" ", a, b, round(g, 1), "plan", round(plan_gap(fp[a], fp[b]), 2))
print("keep-clear:")
for a in labs:
    for k, kb in KE.items():
        g = gap(B[a], kb)
        if g < 40: print(" ", a, k, round(g, 1))
