"""Render one group's traced shape at 16x for several fits, side by side, over a crop.
usage: python pbt_knot_view.py group layer x0 y0 x1 y1 out.png cfg1 cfg2 ... (cfg = knot:smooth:iters, 'raw' = half-level contour)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props"); sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from props_lib import trace as T
from props_lib import paperbomb_trace as PT
import xt_io
grp, layer = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(int, sys.argv[3:7]); out = sys.argv[7]; cfgs = sys.argv[8:]
F = 16
L = PT.load_layers(); masks = PT.group_masks(L); region = PT.group_regions(L, masks)[(grp, layer)]
panels = []
ref = []
for c in range(3):
    fine, *_ = T.upsample_window(L.src.rgb[..., c], x0, y0, x1, y1, F, "catmull")
    ref.append(fine)
panels.append(np.clip(np.stack(ref, -1), 0, 1))
for cfg in cfgs:
    if cfg == "raw":
        f = np.where(region, PT.layer_field(L, layer, True) / L.density[layer], 0.0)
        win = PT._window(region, 3, f.shape)
        fine, gx0, gy0, st = T.upsample_window(f, *win, 8, "bspline")
        polys = [np.stack([gx0 + l[:, 0] * st, gy0 + l[:, 1] * st], 1) for l in T.marching_squares(fine, 0.5)]
    else:
        bits = cfg.split(":")
        k, s, it = bits[:3]
        arm = float(bits[3]) if len(bits) > 3 else None; deg = float(bits[4]) if len(bits) > 4 else None
        curves, info = PT.trace_contour(L, layer, region, refine=int(it) > 0, knot=float(k), smooth=float(s), iters=max(1, int(it)), corner_arm=arm, corner_deg=deg, two_pass=(bits[5] != "0") if len(bits) > 5 else True)
        print(cfg, info["corners"], info["refine_residual"][-1:] )
        polys = [c.sample(0.02) for c in curves]
    cov = T.fill_polys([(p - [x0, y0]) * F for p in polys], (y1 - y0) * F, (x1 - x0) * F, ss=4).astype(np.float64)
    panels.append(np.repeat((1 - 0.92 * cov)[..., None], 3, -1))
sep = np.ones((panels[0].shape[0], 8, 3))
row = [panels[0]]
for p in panels[1:]:
    row += [sep, p]
xt_io.write(out, np.concatenate(row, 1))
print("wrote", out)
