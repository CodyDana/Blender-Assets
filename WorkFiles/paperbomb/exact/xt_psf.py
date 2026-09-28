import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "Scripts", "props")); sys.path.insert(0, HERE)
import numpy as np
from props_lib import trace as T
import xt_emblem_bench as EB
src = T.read_source(); fit = T.fit_card(src); ak, behind, unm = T.ink_layers(src, fit)
x0, y0, x1, y1 = EB.WIN
keep = EB.component_mask(ak, EB.WIN)
core = T.erode(keep, 2)
sub = ak[y0:y1, x0:x1]
print("interior alpha (eroded 2): p5 %.3f p25 %.3f p50 %.3f p75 %.3f p95 %.3f mean %.3f" % tuple(list(np.percentile(sub[core], [5, 25, 50, 75, 95])) + [sub[core].mean()]))
print("interior luma of V2 core:", np.percentile((src.rgb[y0:y1, x0:x1] @ [0.2126, 0.7152, 0.0722])[core], [5, 50, 95]))
# PSF: render traced shape box-filtered at V2 grid, then blur by sigma, compare in edge band
loops, curves, stats = EB.trace_variant(ak, keep, "bspline", 8, 0.5)
H, W = ak.shape
pred = EB.render(curves, H, W)[y0:y1, x0:x1].astype(np.float64)
band = T.dilate(keep, 1) & ~T.erode(keep, 1)
dens = np.median(sub[core])
for s in (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8):
    pb = T.gauss_blur(pred, s) * dens
    r = (pb - sub)[band]
    print("sigma %.1f  band MAE %.4f  RMS %.4f  bias %.4f" % (s, np.abs(r).mean(), np.sqrt((r**2).mean()), r.mean()))
