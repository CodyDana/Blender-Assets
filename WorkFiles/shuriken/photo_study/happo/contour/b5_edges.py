# Method B step 5: per-station edge localisation along each of the 16 star edges and line fitting.
# Features per normal profile (t outward, smoothed luminance, tangential average 11 px):
#   OUTER  = outermost crisp rising step (piece material -> background/halo)
#   FACE   = innermost crisp step leaving the flat textured face (up to lit bevel, or down to dark band)
# Two passes: pass 1 profiles are normal to the Otsu tip->notch chord; pass 2 normal to the pass-1 fitted line.
import numpy as np, os, json
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
L = np.load(os.path.join(OUT, "L.npy")).astype(np.float64)
info = json.load(open(os.path.join(OUT, "b3_contour_mask_filled.json")))
cx, cy = info["centroid"]
tips = [np.array((t["x"], t["y"])) for t in info["tips"]]
notches = [np.array((n["x"], n["y"])) for n in info["notches"]]
H, W = L.shape

def bil(A, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy) + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)

import sys
UPTHR = float(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 0.030
OUTNAME = sys.argv[sys.argv.index("--") + 2] if "--" in sys.argv else "b5_edges.json"
DT = 0.25
TS = np.arange(-50, 30.001, DT)
SS = np.arange(-5, 5.01, 1.0)
gk = np.exp(-0.5 * (np.arange(-6, 6.01, DT) / 1.0) ** 2); gk /= gk.sum()   # sigma 1 px along t

def profile(base, u, n):
    xs = base[0] + TS[None, :] * n[0] + SS[:, None] * u[0]
    ys = base[1] + TS[None, :] * n[1] + SS[:, None] * u[1]
    p = bil(L, xs, ys).mean(0)
    ps = np.convolve(np.pad(p, len(gk) // 2, mode='edge'), gk, mode='valid')
    d = np.gradient(ps, DT)
    return ps, d

def peaks(d, thr, sign=1):
    s = sign * d
    idx = np.nonzero((s[1:-1] > s[:-2]) & (s[1:-1] >= s[2:]) & (s[1:-1] > thr))[0] + 1
    out = []
    for i in idx:
        # sub-sample parabola
        a, b, c = s[i - 1], s[i], s[i + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den != 0 else 0
        # half-width of the peak (samples above half max)
        hm = s[i] / 2; j0 = i; j1 = i
        while j0 > 0 and s[j0] > hm: j0 -= 1
        while j1 < len(s) - 1 and s[j1] > hm: j1 += 1
        out.append(dict(t=TS[i] + off * DT, g=float(s[i]), fwhm=(j1 - j0) * DT))
    return out

def analyse(base, u, n, tmin=-50):
    ps, d = profile(base, u, n)
    ok = TS >= tmin
    # background level = far outside; face level = median well inside
    bgv = ps[-8:].mean()
    up = [p for p in peaks(d, UPTHR, +1) if p["t"] >= tmin]
    dn = [p for p in peaks(d, 0.030, -1) if p["t"] >= tmin]
    # OUTER: outermost rising crisp step (fwhm <= 5 px) whose far side is not followed by another crisp rise
    crisp_up = [p for p in up if p["fwhm"] <= 5.5]
    outer = max(crisp_up, key=lambda p: p["t"]) if crisp_up else None
    # FACE: innermost crisp step of either sign
    crisp = [dict(p, s=+1) for p in crisp_up] + [dict(p, s=-1) for p in dn if p["fwhm"] <= 5.5]
    crisp = [p for p in crisp if p["g"] >= 0.030]
    face = min(crisp, key=lambda p: p["t"]) if crisp else None
    return ps, d, outer, face, up, dn

def fit_line(P, w=None):
    # total least squares; returns point, direction, rms, max residual
    if w is None: w = np.ones(len(P))
    m = (P * w[:, None]).sum(0) / w.sum()
    Q = (P - m) * np.sqrt(w[:, None])
    _, s, vt = np.linalg.svd(Q, full_matrices=False)
    dvec = vt[0]; nvec = np.array([-dvec[1], dvec[0]])
    res = (P - m) @ nvec
    return m, dvec, res

def robust_line(P):
    keep = np.ones(len(P), bool)
    for _ in range(5):
        m, dv, res = fit_line(P[keep])
        r_all = (P - m) @ np.array([-dv[1], dv[0]])
        s = 1.4826 * np.median(np.abs(r_all[keep] - np.median(r_all[keep])))
        newkeep = np.abs(r_all) < max(3 * s, 1.0)
        if (newkeep == keep).all(): break
        keep = newkeep
    m, dv, res = fit_line(P[keep])
    return m, dv, keep, res

edges = []
for k in range(8):
    edges.append(dict(name="T%d-N%d" % (k, k), tip=k, notch=k))
    edges.append(dict(name="T%d-N%d" % ((k + 1) % 8, k), tip=(k + 1) % 8, notch=k))

results = {}
for e in edges:
    A = tips[e["tip"]].astype(float); B = notches[e["notch"]].astype(float)
    u = (B - A) / np.hypot(*(B - A)); n = np.array([u[1], -u[0]])
    if np.dot((A + B) / 2 - np.array([cx, cy]), n) < 0: n = -n
    base0 = A.copy(); Ln = np.hypot(*(B - A))
    fr = np.arange(0.12, 0.92, 0.005)
    for pas in (1, 2):
        pts_o = []; pts_f = []; rec = []
        for f in fr:
            base = base0 + u * f * Ln
            # limit inward reach so the profile does not cross to the opposite edge near the tip
            tmin = max(-50, -0.30 * f * Ln)
            ps, d, outer, face, up, dn = analyse(base, u, n, tmin)
            r = dict(f=float(f), outer=outer, face=face)
            if outer: pts_o.append(base + n * outer["t"])
            else: pts_o.append([np.nan, np.nan])
            if face: pts_f.append(base + n * face["t"])
            else: pts_f.append([np.nan, np.nan])
            # bevel/stripe: when face step is inside outer step
            r["band"] = (outer["t"] - face["t"]) if (outer and face and outer["t"] - face["t"] > 1.5) else 0.0
            r["face_sign"] = face.get("s") if face else 0
            rec.append(r)
        pts_o = np.array(pts_o, float); pts_f = np.array(pts_f, float)
        good = ~np.isnan(pts_o[:, 0])
        m, dv, keep, res = robust_line(pts_o[good])
        if np.dot(dv, u) < 0: dv = -dv
        # re-base: pass 2 uses the fitted outer line
        nn = np.array([dv[1], -dv[0]])
        if np.dot(nn, n) < 0: nn = -nn
        # project A onto fitted line for new base
        base0 = m + dv * np.dot(A - m, dv); u = dv; n = nn
        Ln = abs(np.dot(B - base0, u))
    gf = ~np.isnan(pts_f[:, 0])
    mf, dvf, keepf, resf = robust_line(pts_f[gf])
    if np.dot(dvf, u) < 0: dvf = -dvf
    results[e["name"]] = dict(tip=e["tip"], notch=e["notch"],
        outer_pt=m.tolist(), outer_dir=dv.tolist(), outer_n=n.tolist(),
        outer_rms=float(np.sqrt(np.mean(res ** 2))), outer_maxres=float(np.max(np.abs(res))),
        outer_kept=int(keep.sum()), outer_total=int(good.sum()),
        face_pt=mf.tolist(), face_dir=dvf.tolist(),
        face_rms=float(np.sqrt(np.mean(resf ** 2))), face_kept=int(keepf.sum()), face_total=int(gf.sum()),
        pts_outer=pts_o.tolist(), pts_face=pts_f.tolist(),
        stations=[dict(f=r["f"], band=r["band"], face_sign=r["face_sign"],
                       outer_t=(r["outer"]["t"] if r["outer"] else None),
                       outer_g=(r["outer"]["g"] if r["outer"] else None),
                       face_t=(r["face"]["t"] if r["face"] else None)) for r in rec])
    print("%-7s outer: rms %.2f max %.2f kept %d/%d   face: rms %.2f kept %d/%d   angle(outer,face) %.2f deg" % (
        e["name"], results[e["name"]]["outer_rms"], results[e["name"]]["outer_maxres"], keep.sum(), good.sum(),
        results[e["name"]]["face_rms"], keepf.sum(), gf.sum(),
        np.degrees(np.arcsin(np.clip(dv[0] * dvf[1] - dv[1] * dvf[0], -1, 1)))))
json.dump(results, open(os.path.join(OUT, OUTNAME), "w"))

