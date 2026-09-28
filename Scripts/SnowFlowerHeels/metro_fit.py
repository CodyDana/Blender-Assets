"""Two-view weak-perspective fit of the Snow Flower heel reference.
Both shoes stand on one ground plane under one camera: shared elevation e, per-shoe yaw and scale.
World: X toward toe, Y toward the shoe's left (the visible side), Z up. Image u right, v down."""
import numpy as np, json, sys, itertools
L = {  # name: (A_xy, B_xy)
 "toe_tip":            ((869, 1172), (1234, 1027)),
 "toplift_bottom":     ((108, 917),  (632, 792)),
 "heel_silver_end":    ((104, 882),  (620, 760)),
 "spike_tip":          ((118, 8),    (686, 37)),
 "buckle_blossom":     ((201, 221),  (750, 230)),
 "strap_stud":         ((308, 244),  (835, 249)),
 "strap_fold":         ((470, 240),  (1013, 263)),
 "toe_apex":           ((625, 818),  (1062, 743)),
 "toe_blossom":        ((672, 913),  (1095, 832)),
 "emblem_top":         ((163, 405),  (720, 427)),
 "emblem_bottom":      ((248, 535),  (792, 523)),
}
names = list(L); A = np.array([L[k][0] for k in names], float); B = np.array([L[k][1] for k in names], float)
def proj_mats(e, th):
    c, s = np.cos(th), np.sin(th)
    Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    # camera: u = x_r ; v = -(y_r sin e + z cos e)   (y_r = away from camera after yaw)
    P = np.array([[1, 0, 0], [0, -np.sin(e), -np.cos(e)]])
    return P @ Rz
def solve(e, tA, tB, sB):
    MA = proj_mats(e, tA); MB = sB * proj_mats(e, tB)
    M = np.vstack([MA, MB])                       # 4x3
    Ac = A - A.mean(0); Bc = B - B.mean(0)
    Y = np.hstack([Ac, Bc])                       # N x 4
    X, *_ = np.linalg.lstsq(M, Y.T, rcond=None)   # 3 x N
    R = (M @ X).T - Y
    return X.T, np.sqrt((R**2).sum(1).mean() / 2)
best = []
for e in np.radians(np.arange(2, 80, 3)):
    for tA in np.radians(np.arange(-180, 180, 6)):
        for tB in np.radians(np.arange(-180, 180, 6)):
            for sB in np.arange(0.6, 1.05, 0.05):
                X, r = solve(e, tA, tB, sB); best.append((r, e, tA, tB, sB))
best.sort(key=lambda t: t[0])
def refine(p):
    p = np.array(p, float); step = np.array([0.02, 0.03, 0.03, 0.01]); f = solve(*p)[1]
    for it in range(400):
        improved = False
        for i in range(4):
            for sg in (1, -1):
                q = p.copy(); q[i] += sg*step[i]; fq = solve(*q)[1]
                if fq < f: p, f, improved = q, fq, True
        if not improved: step *= 0.5
        if step.max() < 1e-6: break
    return p, f
sols = []
for r, *p in best[:60]:
    q, f = refine(p); sols.append((f, q))
sols.sort(key=lambda t: t[0])
seen = []
for f, q in sols:
    key = tuple(np.round(np.degrees(q[:3]))) + (round(q[3], 2),)
    if any(np.allclose(key, s, atol=2) for s in seen): continue
    seen.append(key)
    X, _ = solve(*q)
    print("rms %.2f px  elev %.1f  yawA %.1f  yawB %.1f  sB %.3f" % (f, *np.degrees(q[:3]), q[3]))
    if len(seen) >= 6: break
f, q = sols[0]; X, rms = solve(*q)
z0 = X[names.index("toplift_bottom"), 2]
out = {"rms_px": rms, "elev_deg": float(np.degrees(q[0])), "yawA_deg": float(np.degrees(q[1])), "yawB_deg": float(np.degrees(q[2])), "scaleB_over_A": float(q[3]),
       "points_px_units": {n: (X[i] - [0, 0, z0]).round(2).tolist() for i, n in enumerate(names)}}
MA = proj_mats(q[0], q[1]); MB = q[3]*proj_mats(q[0], q[2])
for i, n in enumerate(names):
    ra = MA @ X[i] + A.mean(0) - A[i]; rb = MB @ X[i] + B.mean(0) - B[i]
    print("%-16s X %7.1f Y %7.1f Z %7.1f   resA %5.1f %5.1f  resB %5.1f %5.1f" % (n, *(X[i] - [0, 0, z0]), *ra, *rb))
json.dump(out, open(sys.argv[1], "w"), indent=1)
