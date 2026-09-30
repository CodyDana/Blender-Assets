"""r19 b: case 8 (rot -90 kept: the tray's orientation) as reference 2's compact shuriken cube: fit x0 1260, the RAW
right glass edge 1407 (reference 2 shows the case's right edge just inside the jamb), top y 627; the foot is hidden
behind the entry lantern (lower bound y1 >= 850). Tray: 0.541 along world Y, local Y -0.186..+0.252 along world -X..+X
(rot -90), so W >= 0.62 and D >= 0.58. Usage: py -3 solve_sf.py"""
import numpy as np
from solve_b import box
res = []
for W in (0.62, 0.64, 0.66, 0.70, 0.75):
    for D in (0.58, 0.60, 0.62, 0.66):
        for G in (0.45, 0.50, 0.55, 0.60, 0.65):
            dims = (W, D, 0.40, G)
            for x in np.arange(8.5, 9.6, 0.01):
                for y in np.arange(2.6, 4.2, 0.01):
                    b = box(dims, x, y, -90, clamp=False)
                    e = np.sqrt(((max(b[0], 40) - 1260) ** 2 + (b[1] - 1407) ** 2 + (b[2] - 627) ** 2) / 3)
                    if b[3] < 850:
                        e += (850 - b[3])
                    res.append((round(e, 1), W, D, G, round(x, 2), round(y, 2), [round(v) for v in b]))
res.sort(key=lambda a: a[0])
seen = set()
for r in res:
    if (r[1], r[2], r[3]) in seen:
        continue
    seen.add((r[1], r[2], r[3]))
    print(r)
    if len(seen) > 30:
        break
