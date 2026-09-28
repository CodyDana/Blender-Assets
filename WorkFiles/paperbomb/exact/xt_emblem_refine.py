import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "Scripts", "props")); sys.path.insert(0, HERE)
import numpy as np
from props_lib import trace as T
import xt_emblem_bench as EB
import xt_io
src = T.read_source(); fit = T.fit_card(src); ak, behind, unm = T.ink_layers(src, fit)
x0, y0, x1, y1 = EB.WIN
keep = EB.component_mask(ak, EB.WIN)
H, W = ak.shape
region = np.zeros_like(ak, bool); region[y0:y1, x0:x1] = T.dilate(keep, 3)
obs = np.where(region, ak, 0.0)
core = np.zeros_like(ak, bool); core[y0:y1, x0:x1] = T.erode(keep, 1)
density = T.norm_conv(ak, core.astype(float), 1.5, 0.98)
out = {}
variants = [(0.5, 1e-3), (0.75, 1e-3), (1.0, 1e-3), (1.0, 0.05), (1.5, 1e-3)]
if len(sys.argv) > 1:
    variants = [(float(sys.argv[1]), float(sys.argv[2]))]
for knot, smooth in variants:
    t0 = time.time()
    loops, curves, stats = EB.trace_variant(ak, keep, "bspline", 8, knot)
    pred0 = T.render_source_grid(curves, H, W, 0.0)
    s0 = EB.score(pred0[y0:y1, x0:x1], obs[y0:y1, x0:x1], region[y0:y1, x0:x1])
    cur2, hist = T.refine_curves(curves, obs, density, region, knot, smooth, iters=12)
    pred = T.render_source_grid(cur2, H, W, 0.0)
    s1 = EB.score(pred[y0:y1, x0:x1], obs[y0:y1, x0:x1], region[y0:y1, x0:x1])
    predp = T.render_source_grid(cur2, H, W, T.SOURCE_PSF_SIGMA_PX) * density
    s2 = EB.score(predp[y0:y1, x0:x1], obs[y0:y1, x0:x1], region[y0:y1, x0:x1])
    key = "knot%.2f_s%g" % (knot, smooth)
    out[key] = {"before": s0, "after_box": s1, "after_psf": s2, "residual_hist": [round(h, 4) for h in hist], "secs": round(time.time() - t0, 1)}
    print(key, json.dumps(out[key]))
    np.save(os.path.join(HERE, "_curves_%s.npy" % key), np.array([c.to_json() for c in cur2], dtype=object), allow_pickle=True)
json.dump(out, open(os.path.join(HERE, "emblem_refine.json"), "w"), indent=1)
