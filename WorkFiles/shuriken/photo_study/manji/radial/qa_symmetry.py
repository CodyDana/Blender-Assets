"""C4 cross-check: each edge type has 4 copies, lit / shadow-corrected / ramp-corrected differently.
Compare the perpendicular distance from the centroid to each fitted edge line: the spread between the two
LIT copies is the measurement noise; the offset of the corrected copies is the residual correction bias."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
G = json.load(open(os.path.join(C.OUT, "geometry_internal.json")))
cont = np.load(os.path.join(C.OUT, "contour_final.npy"))
cx, cy = G["centre"]
CX = cont[:, 0] - cx; CY = -(cont[:, 1] - cy)
seg = np.hypot(np.diff(cont[:, 0], append=cont[0, 0]), np.diff(cont[:, 1], append=cont[0, 1]))
arc = np.concatenate([[0], np.cumsum(seg)[:-1]]); L_total = float(seg.sum())

def fwd(i0, i1, m=30):
    L = (arc[i1] - arc[i0]) % L_total
    ds = (arc - arc[i0]) % L_total
    return np.nonzero((ds > m) & (ds < L - m))[0]

def tls(P):
    c = P.mean(0)
    U, S, Vt = np.linalg.svd(P - c, full_matrices=False)
    n = Vt[1]
    return float(abs(c @ n)), float(np.sqrt(((P - c) @ n) ** 2 .mean() if False else np.mean(((P - c) @ n) ** 2)))

# lighting class of an edge from its outward normal in IMAGE coords: up(-y) = shadow, right(+x) = ramp, else lit
def lighting(P, i0, i1):
    c = P.mean(0)
    U, S, Vt = np.linalg.svd(P - c, full_matrices=False)
    n = Vt[1]
    if c @ n < 0:
        n = -n                       # outward (away from the centre)
    nx, ny_img = n[0], -n[1]         # image-frame normal (y down)
    if ny_img < -0.5:
        return "shadow(up-facing)"
    if nx > 0.5:
        return "ramp(right-facing)"
    return "lit"

rows = {}
for q in range(4):
    Q = R1["quarters_contour_idx"][q]; Qp = R1["quarters_contour_idx"][(q - 1) % 4]
    edges = dict(hookside=(Qp["junction"], Qp["next_root"]), hookinner=(Qp["next_root"], Q["tip"]),
                 trailing=(Q["armend"], Q["junction"]), outer=(Q["tip"], Q["armend"]))
    for nm, (i0, i1) in edges.items():
        idx = fwd(i0, i1)
        P = np.column_stack([CX[idx], CY[idx]])
        d, rms = tls(P)
        rows.setdefault(nm, []).append((q, d, rms, lighting(P, i0, i1)))
out = {}
for nm, lst in rows.items():
    print("EDGE TYPE", nm)
    lit = [d for q, d, r, c in lst if c == "lit"]
    for q, d, r, c in lst:
        print("   q%d  dist_from_centre %8.2f px  rms %.2f  %s  (dev from lit mean %+.2f)" %
              (q, d, r, c, d - np.mean(lit) if lit else float('nan')))
    out[nm] = dict(values=[dict(q=q, dist=d, rms=r, lighting=c) for q, d, r, c in lst],
                   lit_mean=float(np.mean(lit)) if lit else None,
                   lit_spread=float(np.ptp(lit)) if len(lit) > 1 else None,
                   dev_of_corrected={c: float(d - np.mean(lit)) for q, d, r, c in lst if c != "lit"})
json.dump(out, open(os.path.join(C.OUT, "qa_symmetry.json"), "w"), indent=1)
