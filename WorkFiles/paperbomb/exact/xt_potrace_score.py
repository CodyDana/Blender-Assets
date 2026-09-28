import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "Scripts", "props")); sys.path.insert(0, HERE)
import numpy as np
from props_lib import trace as T
import xt_emblem_bench as EB
src = T.read_source(); fit = T.fit_card(src); ak, behind, unm = T.ink_layers(src, fit)
x0, y0, x1, y1 = EB.WIN
keep = EB.component_mask(ak, EB.WIN)
scored = np.zeros_like(ak, bool); scored[y0:y1, x0:x1] = T.dilate(keep, 3)
obs = np.where(scored, ak, 0.0)
H, W = ak.shape
z = np.load(os.path.join(HERE, "potrace_loops.npz"))
ref_loops, ref_curves, _ = EB.trace_variant(ak, keep, "bspline", 8, 0.5)
rb = np.vstack(ref_loops); print("ours bbox", rb.min(0).round(3), rb.max(0).round(3))
out = {}
for tag in ("x1", "x8"):
    loops = [z[k] for k in sorted(z.files) if k.startswith(tag + "_")]
    allp = np.vstack(loops); print(tag, "bbox", allp.min(0).round(3), allp.max(0).round(3), "pts", len(allp))
    pred = T.fill_polys(loops, H, W, ss=16)
    sc = EB.score(pred[y0:y1, x0:x1], obs[y0:y1, x0:x1], scored[y0:y1, x0:x1])
    out["potrace_" + tag] = sc
    print(tag, json.dumps(sc))
json.dump(out, open(os.path.join(HERE, "emblem_bench_potrace.json"), "w"), indent=1)

# fairness: calibrate each Potrace result with the best axis scale+offset against OUR contour
ours = np.vstack([T.resample_closed(l, 0.05) for l in ref_loops])
def nn_idx(a, b):
    idx = np.empty(len(a), np.int64)
    for i in range(0, len(a), 2000):
        d = (a[i:i+2000, None, 0] - b[None, :, 0])**2 + (a[i:i+2000, None, 1] - b[None, :, 1])**2
        idx[i:i+2000] = d.argmin(1)
    return idx
for tag in ("x1", "x8"):
    loops = [z[k] for k in sorted(z.files) if k.startswith(tag + "_")]
    allp = np.vstack(loops)
    cx, cy = allp.mean(0)
    A = np.eye(2); t = np.zeros(2)
    for it in range(8):
        q = (allp - [cx, cy]) * np.diag(A) + [cx, cy] + t
        tgt = ours[nn_idx(q, ours)]
        for k in range(2):
            M = np.stack([allp[:, k] - (cx, cy)[k], np.ones(len(allp))], 1)
            sol, *_ = np.linalg.lstsq(M, tgt[:, k] - (cx, cy)[k], rcond=None)
            A[k, k] = sol[0]; t[k] = sol[1]
    print(tag, "calibration scale", np.diag(A).round(5), "offset", t.round(4))
    cal = [(l - [cx, cy]) * np.diag(A) + [cx, cy] + t for l in loops]
    pred = T.fill_polys(cal, H, W, ss=16)
    sc = EB.score(pred[y0:y1, x0:x1], obs[y0:y1, x0:x1], scored[y0:y1, x0:x1])
    out["potrace_%s_calibrated" % tag] = sc
    print(tag, "calibrated", json.dumps(sc))
json.dump(out, open(os.path.join(HERE, "emblem_bench_potrace.json"), "w"), indent=1)
