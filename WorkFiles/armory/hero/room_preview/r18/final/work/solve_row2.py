"""r18 final fix: the west side row on the C1 projection (1448 x 1086), with the cases' real silhouettes (plinth prism
full footprint + glass prism inset 3.2 cm) and a separating-axis gap over 72 directions (a lower bound on the true
on-screen distance). Finds the straightest, most even inward diagonal of the judge's measure (inner plinth edge x at
the plinth foot y: bounding box x1 @ y1) with >= M px between the cases and >= K px to the rear keep-clear pieces.
Usage: py -3 solve_row2.py M K [tall_D tall_W]"""
import sys, json
import numpy as np
F, CX, CY, CAMY, CAMZ = 1608.9, 724.0, 87.0, -4.18, 3.39
ANG = np.radians(np.arange(0, 180, 2.5)); DIRS = np.stack([np.cos(ANG), np.sin(ANG)], 1)  # 72 axes
GI = 0.032
def corners(x0, x1, y0, y1, h, g):
    """(..., 16, 3) world corners of plinth + inset glass"""
    pts = []
    for (a0, a1, b0, b1, z0, z1) in ((x0, x1, y0, y1, 0.0, h), (x0 + GI, x1 - GI, y0 + GI, y1 - GI, h, h + g)):
        for X in (a0, a1):
            for Y in (b0, b1):
                for Z in (z0, z1):
                    pts.append(np.stack(np.broadcast_arrays(X, Y, Z), -1))
    return np.stack(pts, -2)
def proj(P):
    d = P[..., 1] - CAMY
    return np.stack([CX + F * (P[..., 0] - 6.0) / d, CY + F * (CAMZ - P[..., 2]) / d], -1)
def shape(x0, x1, y0, y1, h, g):
    q = proj(corners(x0, x1, y0, y1, h, g))          # (..., 16, 2)
    q = q.copy(); q[..., 0] = np.maximum(q[..., 0], 40.0)   # the door post hides x < 40
    pr = q @ DIRS.T                                  # (..., 16, 72)
    bb = np.stack([q[..., 0].min(-1), q[..., 0].max(-1), q[..., 1].min(-1), q[..., 1].max(-1)], -1)
    # judge's measure: the plinth's inner (aisle-side) foot edge: x of the plinth's inner back-bottom corner,
    # y of the plinth's front foot
    return pr.min(-2), pr.max(-2), bb
def rect(b):
    q = np.array([[b[0], b[2]], [b[1], b[2]], [b[0], b[3]], [b[1], b[3]]], float); pr = q @ DIRS.T
    return pr.min(0), pr.max(0)
def sgap(A, B):   # A, B = (min, max) arrays (..., 72)
    return np.maximum(B[0] - A[1], A[0] - B[1]).max(-1)
KEEP = {"niche": [365, 413, 165, 232], "foot_lantern": [489, 521, 280, 359], "deck_lantern": [534, 566, 238, 282],
        "alcove": [436, 506, 70, 232]}
KEEPS = {k: rect(v) for k, v in KEEP.items()}
CEN = {k: shape(*v)[:2] for k, v in {"1": (5.1, 6.9, 3.35, 4.65, 0.72, 0.48), "2": (5.1, 6.9, 8.1, 9.3, 0.72, 0.53),
                                     "3": (5.2, 6.8, 12.9, 13.9, 0.72, 0.48)}.items()}
M = float(sys.argv[1]); K = float(sys.argv[2])
TD, TW = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.85, 1.0)
SFX = (2.30, 3.10, 3.15, 4.35)
SF = shape(*SFX, 0.40, 0.50)
def fr(a, b, s): return np.round(np.arange(a, b + 1e-9, s), 3)
def cands(xs, ys, D, W, h, g, keeps=True):
    X, Y = np.meshgrid(xs, ys, indexing="ij"); X = X.ravel(); Y = Y.ravel()
    lo, hi, bb = shape(X, X + D, Y, Y + W, h, g)
    ok = np.ones(X.shape, bool)
    for k in CEN: ok &= sgap((lo, hi), CEN[k]) >= K
    if keeps:
        for k in KEEPS: ok &= sgap((lo, hi), KEEPS[k]) >= K
    ok &= (X + D) <= 4.40
    return dict(X=X[ok], Y=Y[ok], D=D, W=W, lo=lo[ok], hi=hi[ok], bb=bb[ok])
T4 = cands(fr(1.13, 3.0, 0.05), fr(6.0, 11.0, 0.05), TD, TW, 0.50, 1.70)
m = sgap((T4["lo"], T4["hi"]), SF) >= M
T4 = {k: (v[m] if isinstance(v, np.ndarray) else v) for k, v in T4.items()}
TG = cands(fr(1.13, 3.0, 0.05), fr(9.0, 14.1, 0.05), TD, TW, 0.50, 1.70)
SS = [cands(fr(1.13, 3.6, 0.05), fr(10.0, 15.10 - sw, 0.05), sd, sw, 0.55, 0.70) for (sw, sd) in ((1.2, 0.9), (0.9, 1.2))]
for s in SS:
    mm = sgap((s["lo"], s["hi"]), SF) >= M
    for k in ("X", "Y", "lo", "hi", "bb"): s[k] = s[k][mm]
print("cands", len(T4["X"]), len(TG["X"]), [len(s["X"]) for s in SS], flush=True)
def pgap(A, i, B):
    return np.maximum(np.maximum(B["X"] - (A["X"][i] + A["D"]), A["X"][i] - (B["X"] + B["D"])),
                      np.maximum(B["Y"] - (A["Y"][i] + A["W"]), A["Y"][i] - (B["Y"] + B["W"])))
p5 = np.array([SF[2][1], SF[2][3]])
res = []
for i in range(len(T4["X"])):
    a4 = (T4["lo"][i], T4["hi"][i])
    jj = np.where((sgap(a4, (TG["lo"], TG["hi"])) >= M) & (pgap(T4, i, TG) >= 0.75))[0]
    if not len(jj): continue
    for s in SS:
        base = (sgap(a4, (s["lo"], s["hi"])) >= M) & (pgap(T4, i, s) >= 0.75)
        if not base.any(): continue
        for j in jj:
            ag = (TG["lo"][j], TG["hi"][j])
            ok = base & (sgap(ag, (s["lo"], s["hi"])) >= M) & (pgap(TG, j, s) >= 0.75)
            kk = np.where(ok)[0]
            if not len(kk): continue
            n = len(kk)
            P = np.zeros((4, 2, n))
            P[0] = p5[:, None]; P[1] = T4["bb"][i][[1, 3]][:, None]; P[2] = TG["bb"][j][[1, 3]][:, None]
            P[3] = s["bb"][kk][:, [1, 3]].T
            o = np.argsort(-P[:, 1, :], 0); P = np.take_along_axis(P, o[:, None, :], 0)
            st = P[1:] - P[:-1]
            inward = (st[:, 0] > 5).all(0) & (st[:, 1] < -5).all(0)
            if not inward.any(): continue
            ln = np.hypot(st[:, 0], st[:, 1])
            a, b = P[0], P[3]; dv = b - a; nr = np.hypot(dv[0], dv[1])
            dev = np.maximum(abs((P[1, 0] - a[0]) * dv[1] - (P[1, 1] - a[1]) * dv[0]),
                             abs((P[2, 0] - a[0]) * dv[1] - (P[2, 1] - a[1]) * dv[0])) / nr
            even = ln.max(0) / ln.min(0)
            score = dev + 40 * (even - 1)
            score[~inward] = 1e9
            q = np.argmin(score)
            res.append((float(score[q]), float(dev[q]), float(even[q]), float(T4["X"][i]), float(T4["Y"][i]),
                        float(TG["X"][j]), float(TG["Y"][j]), s["W"], s["D"], float(s["X"][kk[q]]),
                        float(s["Y"][kk[q]]), P[:, :, q].round().astype(int).tolist()))
res.sort()
print(len(res))
for r in res[:25]: print([round(v, 3) if isinstance(v, float) else v for v in r])
json.dump(res[:200], open(f"solve2_{int(M)}_{int(K)}_{TD}_{TW}.json", "w"))
