"""r18 final fix: search the west side row on the C1 projection (1448 x 1086) for the straightest, most even inward
diagonal of the inner-back foot corners (the judge's measure: box x1 @ y1) with >= M px between every case box and
>= K px to the rear keep-clear pieces. Order kept 5 (SF, fixed) -> 4 (Tall) -> G3 (Tall) -> G1 (S)."""
import itertools, sys
import numpy as np
F, CX, CY, CAMY, CAMZ = 1608.9, 724.0, 87.0, -4.18, 3.39
def px(X, Y, Z):
    d = Y - CAMY
    return CX + F * (X - 6.0) / d, CY + F * (CAMZ - Z) / d
def box(x0, x1, y0, y1, z1):
    xs, ys = [], []
    for X in (x0, x1):
        for Y in (y0, y1):
            for Z in (0.0, z1):
                a, b = px(X, Y, Z); xs.append(a); ys.append(b)
    return np.array([np.maximum(40, np.min(xs, 0)), np.max(xs, 0), np.min(ys, 0), np.max(ys, 0)])
def gap(a, b):
    return np.maximum.reduce([a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3]])
KEEP = {"niche": [365, 413, 165, 232], "foot_lantern": [489, 521, 280, 359], "deck_lantern": [534, 566, 238, 282],
        "alcove": [436, 506, 70, 232]}
CEN = {"1": box(5.1, 6.9, 3.35, 4.65, 1.2), "2": box(5.1, 6.9, 8.1, 9.3, 1.25), "3": box(5.2, 6.8, 12.9, 13.9, 1.2)}
M = float(sys.argv[1]) if len(sys.argv) > 1 else 35
K = float(sys.argv[2]) if len(sys.argv) > 2 else 25
TD, TW = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.85, 1.0)  # tall depth X, width Y
SF = box(2.30, 3.10, 3.15, 4.35, 0.90)
def fr(a, b, s): return np.round(np.arange(a, b + 1e-9, s), 3)
# candidates
def cands(xs, ys, D, W, H):
    X, Y = np.meshgrid(xs, ys, indexing="ij"); X = X.ravel(); Y = Y.ravel()
    return X, Y, box(X, X + D, Y, Y + W, H)
X4, Y4, B4 = cands(fr(1.13, 3.2, 0.025), fr(6.0, 11.0, 0.05), TD, TW, 2.2)
ok4 = gap(B4, SF[:, None]) >= M
for k in CEN: ok4 &= gap(B4, CEN[k][:, None]) >= K
X4, Y4, B4 = X4[ok4], Y4[ok4], B4[:, ok4]
Xg, Yg, Bg = cands(fr(1.13, 3.2, 0.025), fr(9.0, 14.2, 0.05), TD, TW, 2.2)
okg = np.ones(Xg.shape, bool)
for k in KEEP: okg &= gap(Bg, np.array(KEEP[k])[:, None]) >= K
for k in CEN: okg &= gap(Bg, CEN[k][:, None]) >= K
Xg, Yg, Bg = Xg[okg], Yg[okg], Bg[:, okg]
S = []
for (sw, sd) in ((1.2, 0.9), (0.9, 1.2), (1.1, 0.8), (0.8, 1.1)):   # (Y extent, X extent)
    X, Y, B = cands(fr(1.13, 4.4, 0.025), fr(11.0, 15.10 - sw, 0.05), sd, sw, 1.25)
    ok = np.ones(X.shape, bool)
    for k in KEEP: ok &= gap(B, np.array(KEEP[k])[:, None]) >= K
    for k in CEN: ok &= gap(B, CEN[k][:, None]) >= K
    ok &= (X + sd) <= 4.40
    S.append((sw, sd, X[ok], Y[ok], B[:, ok]))
print("cands", len(X4), len(Xg), [len(s[2]) for s in S])
P5 = np.array([SF[1], SF[3]])
best = []
for i in range(len(X4)):
    b4 = B4[:, i]
    if X4[i] + TD > 4.40: continue
    g = gap(Bg, b4[:, None]) >= M
    pg = np.maximum(np.maximum(Xg - (X4[i] + TD), X4[i] - (Xg + TD)), np.maximum(Yg - (Y4[i] + TW), Y4[i] - (Yg + TW))) >= 0.75
    idx = np.where(g & pg)[0]
    if not len(idx): continue
    for (sw, sd, Xs, Ys, Bs) in S:
        for j in idx:
            bg = Bg[:, j]
            gs = (gap(Bs, bg[:, None]) >= M) & (gap(Bs, b4[:, None]) >= M) & (gap(Bs, SF[:, None]) >= M)
            pgs = np.maximum(np.maximum(Xs - (Xg[j] + TD), Xg[j] - (Xs + sd)), np.maximum(Ys - (Yg[j] + TW), Yg[j] - (Ys + sw))) >= 0.75
            pgs &= np.maximum(np.maximum(Xs - (X4[i] + TD), X4[i] - (Xs + sd)), np.maximum(Ys - (Y4[i] + TW), Y4[i] - (Ys + sw))) >= 0.75
            k = np.where(gs & pgs)[0]
            if not len(k): continue
            # points sorted by foot (y1 desc)
            pts = np.stack([np.broadcast_to(P5[:, None], (2, len(k))), np.broadcast_to(b4[[1, 3]][:, None], (2, len(k))),
                            np.broadcast_to(bg[[1, 3]][:, None], (2, len(k))), Bs[[1, 3]][:, k]], 0)  # 4,2,n
            order = np.argsort(-pts[:, 1, :], axis=0)
            pts = np.take_along_axis(pts, order[:, None, :], 0)
            st = pts[1:] - pts[:-1]                   # 3 steps
            ln = np.hypot(st[:, 0], st[:, 1])
            ang = np.degrees(np.arctan2(-st[:, 1], st[:, 0]))
            inward = (st[:, 0] > 0).all(0) & (st[:, 1] < 0).all(0)
            straight = ang.max(0) - ang.min(0)
            even = ln.max(0) / ln.min(0)
            # distance of the middle points from the line 5 -> last
            a, b = pts[0], pts[3]; dvec = b - a; nrm = np.hypot(dvec[0], dvec[1])
            dev = np.maximum(abs((pts[1, 0] - a[0]) * dvec[1] - (pts[1, 1] - a[1]) * dvec[0]),
                             abs((pts[2, 0] - a[0]) * dvec[1] - (pts[2, 1] - a[1]) * dvec[0])) / nrm
            score = dev + 0.0 * straight
            for q in np.where(inward)[0][np.argsort(score[inward])[:3]]:
                kk = k[q]
                best.append((round(float(score[q]), 1), round(float(straight[q]), 1), round(float(even[q]), 2),
                             (X4[i], Y4[i]), (Xg[j], Yg[j]), (sw, sd, Xs[kk], Ys[kk]),
                             pts[:, :, q].round().astype(int).tolist()))
best.sort(key=lambda r: r[0])
print(len(best))
seen = set()
for r in best[:40]:
    print(r)
