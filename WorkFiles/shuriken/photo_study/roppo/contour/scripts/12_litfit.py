# Lit-side-only circle fits for hub and hole, then locate the shadow-side dark-band boundaries relative to those circles.
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seg = np.load(os.path.join(OUT, "seg.npz")); Lm = seg["L"]
Hh, Ww = Lm.shape
Lb = gauss_blur(Lm, 0.7)
FN = pickle.load(open(os.path.join(OUT, "final.pkl"), "rb")); RAW, COR = FN["RAW"], FN["COR"]
sdir = FN["sdir"]
cz = np.load(os.path.join(OUT, "contours.npz")); outer, hole = cz["outer"], cz["hole"]


def normals(P, win=5):
    t = np.roll(P, -win, 0) - np.roll(P, win, 0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    return np.c_[t[:, 1], -t[:, 0]]


def bil(img, x, y):
    x = np.clip(x, 0, Ww - 1.001); y = np.clip(y, 0, Hh - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


out = {}
# ---------------- hub: arcs from the RAW analysis, keep points whose outward normal has n.s <= 0.1
N = normals(outer)
arc_idx = np.concatenate([g["idx"] for g in RAW["gaps"]])
ns = N[arc_idx] @ sdir
for thr in (0.1, -0.2):
    sel = arc_idx[ns <= thr]
    P = outer[sel] + 0.5 * N[sel]
    f = fit_circle(P)
    angs = np.degrees(np.arctan2(-(P[:, 1] - f["cy"]), P[:, 0] - f["cx"]))
    print(f"hub lit fit (n.s<={thr}): n {len(sel)} c({f['cx']:.2f},{f['cy']:.2f}) r {f['r']:.2f} rms {f['rms']:.2f} max {f['maxres']:.2f}; angular coverage {np.ptp(np.sort(angs)):.0f} deg; arcs used "
          f"{sorted(set(gi for gi, g in enumerate(RAW['gaps']) for i in g['idx'] if i in set(sel.tolist())))}")
    out[f"hub_lit_{thr}"] = f
hubL = out["hub_lit_0.1"]
C = np.array([hubL["cx"], hubL["cy"]]); R = hubL["r"]
# shadow-side arcs: radial profile relative to lit circle
print("\nshadow-side hub arcs: radial positions (r - R_lit) of Otsu edge, dark-band outer edge, face/dark inner edge")
for gi in range(6):
    g = RAW["gaps"][gi]
    P = outer[g["idx"]]
    a_ = np.arctan2(-(P[:, 1] - C[1]), P[:, 0] - C[0])
    angs = np.linspace(np.percentile(a_, 15), np.percentile(a_, 85), 25)
    rr = R + np.arange(-30, 30.01, 0.25)
    X = C[0] + np.cos(angs)[:, None] * rr[None]; Y = C[1] - np.sin(angs)[:, None] * rr[None]
    prof = bil(Lb, X, Y)
    res = []
    for pr in prof:
        io = np.flatnonzero(pr < 0.486); r_otsu = rr[io.max()] if len(io) else np.nan
        dk = np.flatnonzero(pr < 0.18)
        r_dark_out = rr[dk.max()] if len(dk) else np.nan
        r_dark_in = rr[dk.min()] if len(dk) else np.nan
        # steepest descent location (edge) closest inside of otsu
        res.append((r_otsu - R, r_dark_out - R, r_dark_in - R, float(pr.min())))
    res = np.array(res)
    nrm = np.array([np.cos(angs.mean()), -np.sin(angs.mean())])
    print(f" arc {g['between']} n.s {nrm @ sdir:+.2f}: otsu {np.nanmedian(res[:,0]):+.1f}  dark_out {np.nanmedian(res[:,1]):+.1f}  dark_in {np.nanmedian(res[:,2]):+.1f}  "
          f"(dark found in {np.sum(~np.isnan(res[:,1]))}/{len(res)}) minL {np.median(res[:,3]):.2f}")
    out[f"arc{gi}"] = dict(ns=float(nrm @ sdir), otsu=float(np.nanmedian(res[:, 0])), dark_out=float(np.nanmedian(res[:, 1])) if np.any(~np.isnan(res[:, 1])) else None,
                           dark_in=float(np.nanmedian(res[:, 2])) if np.any(~np.isnan(res[:, 2])) else None)

# ---------------- hole: lit part = material normal (pointing into hole) with n.s <= thr
Nh_mat = -normals(hole)
nsh = Nh_mat @ sdir
for thr in (0.0, -0.3):
    sel = nsh <= thr
    P = hole[sel] + 0.5 * (-Nh_mat[sel])  # true edge 0.5 px toward material
    f = fit_circle(P)
    angs = np.degrees(np.arctan2(-(P[:, 1] - f["cy"]), P[:, 0] - f["cx"]))
    print(f"\nhole lit fit (n.s<={thr}): n {sel.sum()} c({f['cx']:.2f},{f['cy']:.2f}) r {f['r']:.2f} rms {f['rms']:.2f} max {f['maxres']:.2f}; angle range {angs.min():.0f}..{angs.max():.0f}")
    out[f"hole_lit_{thr}"] = f
hL = out["hole_lit_0.0"]
Ch = np.array([hL["cx"], hL["cy"]]); Rh = hL["r"]
print("hole: radial positions relative to lit circle, by sector (material side = larger r)")
for lo in range(0, 360, 30):
    angs = np.radians(np.linspace(lo, lo + 30, 20))
    rr = Rh + np.arange(-30, 30.01, 0.25)
    X = Ch[0] + np.cos(angs)[:, None] * rr[None]; Y = Ch[1] - np.sin(angs)[:, None] * rr[None]
    prof = bil(Lb, X, Y)
    res = []
    for pr in prof:
        io = np.flatnonzero(pr > 0.486); r_otsu = rr[io.max()] if len(io) else np.nan  # outermost bright (hole) sample
        dk = np.flatnonzero(pr < 0.18)
        res.append((r_otsu - Rh, (rr[dk.min()] - Rh) if len(dk) else np.nan, (rr[dk.max()] - Rh) if len(dk) else np.nan))
    res = np.array(res)
    mat_n = -np.array([np.cos(np.radians(lo + 15)), -np.sin(np.radians(lo + 15))])
    print(f" sector {lo:3d}-{lo+30:3d} mat n.s {mat_n @ sdir:+.2f}: otsu {np.nanmedian(res[:,0]):+.1f} dark_in(hole side) {np.nanmedian(res[:,1]) if np.any(~np.isnan(res[:,1])) else float('nan'):+.1f} dark_out(material side) {np.nanmedian(res[:,2]) if np.any(~np.isnan(res[:,2])) else float('nan'):+.1f}")
pickle.dump(out, open(os.path.join(OUT, "litfit.pkl"), "wb"))
