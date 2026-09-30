"""Pareto search: the judge's two row complaints (5 -> 4 inner edge barely moves inward; G3 / G1 feet level) under
margins. Usage: py -3 solve_row3.py M K Kn TD TW [sfglass]"""
import sys, json
import numpy as np
exec(open("solve_row2.py").read().split("M = float")[0])
M, K, KN, TD, TW = map(float, sys.argv[1:6])
SFG = float(sys.argv[6]) if len(sys.argv) > 6 else 0.50
SFW = float(sys.argv[7]) if len(sys.argv) > 7 else 1.2
KEEPS2 = dict(KEEPS)
SF = shape(2.30, 3.10, 3.75 - SFW / 2, 3.75 + SFW / 2, 0.40, SFG)
def fr(a, b, s): return np.round(np.arange(a, b + 1e-9, s), 3)
def cands(xs, ys, D, W, h, g):
    X, Y = np.meshgrid(xs, ys, indexing="ij"); X = X.ravel(); Y = Y.ravel()
    lo, hi, bb = shape(X, X + D, Y, Y + W, h, g)
    ok = np.ones(X.shape, bool)
    for k in CEN: ok &= sgap((lo, hi), CEN[k]) >= K
    for k in KEEPS2: ok &= sgap((lo, hi), KEEPS2[k]) >= (KN if k == "niche" else K)
    ok &= (X + D) <= 4.40
    ok &= sgap((lo, hi), SF) >= M
    return dict(X=X[ok], Y=Y[ok], D=D, W=W, lo=lo[ok], hi=hi[ok], bb=bb[ok])
T4 = cands(fr(1.13, 2.6, 0.025), fr(6.5, 10.5, 0.05), TD, TW, 0.50, 1.70)
TG = cands(fr(1.13, 2.6, 0.025), fr(9.5, 14.2, 0.05), TD, TW, 0.50, 1.70)
SS = [cands(fr(1.13, 3.6, 0.05), fr(12.0, 15.10 - sw, 0.05), sd, sw, 0.55, 0.70) for (sw, sd) in ((1.2, 0.9), (0.9, 1.2), (1.0, 0.8), (0.8, 1.0))]
print("cands", len(T4["X"]), len(TG["X"]), [len(s["X"]) for s in SS], flush=True)
def pgap(A, i, B):
    return np.maximum(np.maximum(B["X"] - (A["X"][i] + A["D"]), A["X"][i] - (B["X"] + B["D"])),
                      np.maximum(B["Y"] - (A["Y"][i] + A["W"]), A["Y"][i] - (B["Y"] + B["W"])))
# for each S candidate, best G3 then 4: objective = (x1_4 - 177) + (y1_G3 - y1_G1) - dev
best = {}
p5 = np.array([SF[2][1], SF[2][3]])
for i in range(len(T4["X"])):
    a4 = (T4["lo"][i], T4["hi"][i])
    jj = np.where((sgap(a4, (TG["lo"], TG["hi"])) >= M) & (pgap(T4, i, TG) >= 0.70) & (TG["Y"] > T4["Y"][i]))[0]
    for s in SS:
        base = (sgap(a4, (s["lo"], s["hi"])) >= M) & (pgap(T4, i, s) >= 0.70)
        for j in jj:
            ag = (TG["lo"][j], TG["hi"][j])
            kk = np.where(base & (sgap(ag, (s["lo"], s["hi"])) >= M) & (pgap(TG, j, s) >= 0.70) & (s["Y"] > TG["Y"][j]))[0]
            if not len(kk): continue
            P4 = T4["bb"][i][[1, 3]]; PG = TG["bb"][j][[1, 3]]; PS = s["bb"][kk][:, [1, 3]]
            inward = (P4[0] > p5[0]) & (PG[0] > P4[0]) & (PS[:, 0] > PG[0]) & (PS[:, 1] < PG[1]) & (PG[1] < P4[1])
            if not inward.any(): continue
            a, b = p5, PS; dv = b - a; nr = np.hypot(dv[:, 0], dv[:, 1])
            dev = np.maximum(abs((P4[0] - a[0]) * dv[:, 1] - (P4[1] - a[1]) * dv[:, 0]),
                             abs((PG[0] - a[0]) * dv[:, 1] - (PG[1] - a[1]) * dv[:, 0])) / nr
            st = np.array([[P4[0] - p5[0], P4[1] - p5[1]], [PG[0] - P4[0], PG[1] - P4[1]]])
            sc = (P4[0] - p5[0]) + (PG[1] - PS[:, 1]) - 0.5 * dev
            sc[~inward] = -1e9
            q = int(np.argmax(sc))
            key = (round(float(P4[0] - p5[0]) / 10), round(float(PG[1] - PS[q, 1]) / 10))
            r = (float(sc[q]), float(dev[q]), float(T4["X"][i]), float(T4["Y"][i]), float(TG["X"][j]), float(TG["Y"][j]),
                 s["W"], s["D"], float(s["X"][kk[q]]), float(s["Y"][kk[q]]),
                 [p5.round().tolist(), P4.round().tolist(), PG.round().tolist(), PS[q].round().tolist()])
            if key not in best or best[key][0] < r[0]: best[key] = r
res = sorted(best.values(), reverse=True)
for r in res[:20]: print([round(v, 3) if isinstance(v, float) else v for v in r])
