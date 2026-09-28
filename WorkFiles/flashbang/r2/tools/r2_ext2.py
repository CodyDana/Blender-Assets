"""ring-side extents over H 2.5-3.7 D, ref vs ours (alpha png)"""
import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
import numpy as np
from r2png import read_png
exec(open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools/r2_extents.py").read().split("a = read_png")[0])
a = read_png(sys.argv[1]); ours = a[..., 3] > 127
for v in VIEW_CX:
    ref = poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"])
    bx0, by0, bx1, by1 = VIEW_BOX[v]
    line = []
    for Hd in np.arange(2.5, 3.75, 0.1):
        y = int(round(VIEW_BOTTOM[v] - Hd * D_PX))
        o = []
        for m in (ref, ours):
            row = np.nonzero(m[y, bx0:bx1])[0]
            o.append((round((bx0 + row.min() - VIEW_CX[v]) / MMPX, 1), round((bx0 + row.max() + 1 - VIEW_CX[v]) / MMPX, 1)) if len(row) else None)
        line.append(f"{Hd:.1f}:{o[0][0]:.0f},{o[0][1]:.0f}/{o[1][0]:.0f},{o[1][1]:.0f}")
    print(v, " ".join(line))
