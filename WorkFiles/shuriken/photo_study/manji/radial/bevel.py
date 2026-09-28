"""Bevel-band tables: mean luminance vs depth into the metal, at stations along each edge."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
rgb, info = C.load_rgb(C.IMG); h, w = rgb.shape[:2]
mask = np.unpackbits(np.load(os.path.join(C.OUT, "mask.npy")))[:h * w].reshape(h, w).astype(bool)
R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
G = json.load(open(os.path.join(C.OUT, "geometry_internal.json")))
cont = np.load(os.path.join(C.OUT, "contour_final.npy"))
cx, cy = G["centre"]
CX = cont[:, 0] - cx; CY = -(cont[:, 1] - cy)
seg = np.hypot(np.diff(cont[:, 0], append=cont[0, 0]), np.diff(cont[:, 1], append=cont[0, 1]))
arc = np.concatenate([[0], np.cumsum(seg)[:-1]]); L_total = float(seg.sum())
lumw = np.array([0.2126, 0.7152, 0.0722])
depths = np.arange(0, 42, 1.0)

def fwd(i0, i1):
    L = (arc[i1] - arc[i0]) % L_total
    ds = (arc - arc[i0]) % L_total
    idx = np.nonzero((ds > 0) & (ds < L))[0]
    return idx[np.argsort(ds[idx])], L

def profile_at(i0, i1, s0, tang_avg=6):
    idx, L = fwd(i0, i1)
    dsl = (arc[idx] - arc[i0]) % L_total
    k = idx[np.argmin(np.abs(dsl - s0))]
    ka = idx[np.argmin(np.abs(dsl - (s0 - 10)))]; kb = idx[np.argmin(np.abs(dsl - (s0 + 10)))]
    t = np.array([CX[kb] - CX[ka], CY[kb] - CY[ka]], float); t /= np.linalg.norm(t) + 1e-9
    n = np.array([-t[1], t[0]])
    base = np.array([CX[k], CY[k]])
    p = base + 8 * n
    if not mask[int(round(cy - p[1])) % h, int(round(cx + p[0])) % w]:
        n = -n
    acc = np.zeros((len(depths), 3))
    offs = np.arange(-tang_avg, tang_avg + 1, 2.0)
    for o in offs:
        P = base[None, :] + depths[:, None] * n[None, :] + o * t[None, :]
        acc += C.bilinear(rgb, cx + P[:, 0], cy - P[:, 1])
    return (acc / len(offs)) @ lumw, L

for q in range(4):
    Q = R1["quarters_contour_idx"][q]; Qp = R1["quarters_contour_idx"][(q - 1) % 4]
    edges = dict(outer=(Q["tip"], Q["armend"]), hookinner=(Qp["next_root"], Q["tip"]),
                 hookside=(Qp["junction"], Qp["next_root"]), trailing=(Q["armend"], Q["junction"]))
    for nm, (i0, i1) in edges.items():
        _, L = fwd(i0, i1)
        fr = [0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95]
        print("EDGE q%d %-10s len %4.0f  (station: lum at depth 0,2,4,...,40)" % (q, nm, L))
        for f in fr:
            p, _ = profile_at(i0, i1, f * L)
            print("   s=%4.0f (%.2f): " % (f * L, f) + " ".join("%.2f" % v for v in p[::2]))
