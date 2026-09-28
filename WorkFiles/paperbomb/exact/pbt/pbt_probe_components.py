import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from props_lib import trace as T
import xt_io
src = T.read_source(); fit = T.fit_card(src); ak, behind, unm = T.ink_layers(src, fit)
ar = unm.alpha_r
H, W = ak.shape
for name, a in (("black", ak), ("red", ar)):
    lab, n = T.label(a > 0.5)
    rows = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) < 3: continue
        x0, y0 = fit.px_to_mm(xs.min(), ys.min()); x1, y1 = fit.px_to_mm(xs.max() + 1, ys.max() + 1)
        rows.append((len(ys), float(x0), float(y0), float(x1), float(y1), int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)))
    rows.sort(key=lambda r: (r[2], r[1]))
    print(name, n)
    for r in rows:
        print("  n=%5d mm x %.1f-%.1f y %.1f-%.1f   px x %d-%d y %d-%d" % (r[0], r[1], r[3], r[2], r[4], r[5], r[7], r[6], r[8]))
img = np.stack([1 - ar * 0.2 - ak, 1 - ar - ak, 1 - ar - ak], -1)
xt_io.write(os.path.join(HERE, "pbt_layers_x2.png"), img, 2)
