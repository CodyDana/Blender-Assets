# Final mask: morphological clean-up of the refined mask, then geometric tip patches. Near each hook tip the
# normal-offset refinement is unreliable (normals rotate, thin tips cast short shadows), so each tip zone is rebuilt
# from the two flank lines (least-squares, fitted 70..260 px back from the tip) closed at the apparent tip, which is
# located on the image along the flank bisector (half-way luminance crossing between metal and background levels).
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy"); H, W = px.shape[:2]
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
coarse = np.load(BASE + "/mask_solid.npy")
m = np.load(BASE + "/mask_refined.npy")
def dil(a, r): return box_mean(a.astype(np.float32), r) > 1e-3
def ero(a, r): return box_mean(a.astype(np.float32), r) > 1 - 1e-3
m = ero(dil(m, 1), 1)          # closing 3x3
m = dil(ero(m, 3), 3)          # opening 7x7 square: removes thin slivers left by self-crossing offset polygons;
                               # near-axis-aligned 90-degree corners survive a square element, tips are rebuilt below
lab, n = label_runs(m); sz = np.bincount(lab.ravel()); sz[0] = 0; m = lab == int(np.argmax(sz))
c = moore_trace(m)
def fit_line(P):
    mu = P.mean(0); U, S, Vt = np.linalg.svd(P - mu, full_matrices=False)
    d = Vt[0]; nrm = np.array([-d[1], d[0]]); res = (P - mu) @ nrm
    return mu, d, res
def robust_line(P, it=3, k=2.5):
    keep = np.ones(len(P), bool)
    for _ in range(it):
        mu, d, res = fit_line(P[keep])
        r_all = (P - mu) @ np.array([-d[1], d[0]])
        s = 1.4826 * np.median(np.abs(r_all[keep] - np.median(r_all[keep])))
        keep = np.abs(r_all) < max(k * s, 0.75)
    mu, d, res = fit_line(P[keep])
    return mu, d, float(np.sqrt(np.mean(res ** 2))), int(keep.sum())
def intersect(p1, d1, p2, d2):
    A = np.array([d1, -d2]).T; t = np.linalg.solve(A, p2 - p1); return p1 + t[0] * d1
ys, xs = np.nonzero(coarse)
approx = {}
sel = ys < 1000; i = np.argmin(xs[sel]); approx["top"] = np.array([xs[sel][i], ys[sel][i]], float)
sel = xs > 1600; i = np.argmin(ys[sel]); approx["right"] = np.array([xs[sel][i], ys[sel][i]], float)
sel = ys > 1600; i = np.argmax(xs[sel]); approx["bottom"] = np.array([xs[sel][i], ys[sel][i]], float)
sel = xs < 1000; i = np.argmax(ys[sel]); approx["left"] = np.array([xs[sel][i], ys[sel][i]], float)
info = {}
patch_all = np.zeros_like(m); zone_all = np.zeros_like(m)
YY, XX = np.mgrid[0:H, 0:W]
for name, a in approx.items():
    d = np.hypot(*(c - a).T); i0 = int(np.argmin(d)); Nc = len(c)
    idx = (i0 + np.arange(-900, 901)) % Nc  # contour neighbourhood of the tip
    dd = d[idx]
    before = idx[:900][(dd[:900] > 70) & (dd[:900] < 260)]
    after = idx[901:][(dd[901:] > 70) & (dd[901:] < 260)]
    # flank fitting range (distance from the approximate tip). The top hook's refined contour is unreliable within
    # ~140 px of its tip (defocused bevel band, luminance path truncated there), so its range starts further back.
    dlo, dhi = (150, 420) if name == "top" else (110, 360)
    before = idx[:900][(dd[:900] > dlo) & (dd[:900] < dhi)]
    after = idx[901:][(dd[901:] > dlo) & (dd[901:] < dhi)]
    # quadratic flank fits in a local frame (u along the flank chord toward the tip, v across), robust trimming
    fl = []
    for ch in (before, after):
        P = c[ch]; mu, dv, rms_l, nk = robust_line(P)
        if (a - mu) @ dv < 0: dv = -dv
        nv = np.array([-dv[1], dv[0]]); u = (P - mu) @ dv; v = (P - mu) @ nv
        keep = np.ones(len(u), bool)
        for _ in range(3):
            co = np.polyfit(u[keep], v[keep], 2); r = v - np.polyval(co, u)
            sd = 1.4826 * np.median(np.abs(r[keep])); keep = np.abs(r) < max(2.5 * sd, 0.75)
        co = np.polyfit(u[keep], v[keep], 2); rms = float(np.sqrt(np.mean((v[keep] - np.polyval(co, u[keep])) ** 2)))
        fl.append(dict(mu=mu, dv=dv, nv=nv, co=co, rms=rms, n=int(keep.sum()), umax=float(u.max())))
    def curve(f, uu): return f["mu"][None, :] + uu[:, None] * f["dv"][None, :] + np.polyval(f["co"], uu)[:, None] * f["nv"][None, :]
    uu = np.arange(0, 400, 0.25)
    C0 = curve(fl[0], fl[0]["umax"] + uu); C1 = curve(fl[1], fl[1]["umax"] + uu)
    D = np.hypot(C0[:, None, 0] - C1[None, ::8, 0], C0[:, None, 1] - C1[None, ::8, 1])
    i0_, j0_ = np.unravel_index(np.argmin(D), D.shape)
    V = 0.5 * (C0[i0_] + C1[j0_ * 8])
    t0 = C0[min(i0_ + 1, len(C0) - 1)] - C0[max(i0_ - 1, 0)]; t1 = C1[min(j0_ * 8 + 1, len(C1) - 1)] - C1[max(j0_ * 8 - 1, 0)]
    t0 /= np.hypot(*t0); t1 /= np.hypot(*t1)
    bis = t0 + t1; bis /= np.hypot(*bis)
    tip_angle = float(np.degrees(np.arccos(np.clip(t0 @ t1, -1, 1))))
    s = np.arange(-120, 60.01, 0.5)
    perp = np.array([-bis[1], bis[0]])
    prof = np.mean([bilinear(L, V[0] + s * bis[0] + q * perp[0], V[1] + s * bis[1] + q * perp[1]) for q in (-1, 0, 1)], 0)
    metal = float(np.median(prof[(s > -110) & (s < -50)])); bgl = float(np.median(prof[(s > 35)]))
    half = 0.5 * (metal + bgl)
    k = len(s) - 1
    while k > 0 and prof[k] >= half: k -= 1
    s_tip = float(s[k] + (half - prof[k]) / (prof[k + 1] - prof[k]) * 0.5) if k < len(s) - 1 else float(s[k])
    T = V + s_tip * bis
    info[name] = dict(approx=a.tolist(), virtual_tip=V.tolist(), apparent_tip=T.tolist(), apparent_minus_virtual_px=s_tip,
                      tip_angle_deg=tip_angle, flank_rms_px=[fl[0]["rms"], fl[1]["rms"]], flank_n=[fl[0]["n"], fl[1]["n"]],
                      metal_L=metal, bg_L=bgl)
    print(name, "V", V.round(1), "T", T.round(1), "s_tip %.1f" % s_tip, "tip angle %.1f" % tip_angle,
          "flank rms", round(fl[0]["rms"], 2), round(fl[1]["rms"], 2), "metal/bg L %.2f/%.2f" % (metal, bgl))
    # patch zone: beyond the cut line 130 px back from the apparent tip along the bisector
    cut = T - 130 * bis
    zone = ((XX - cut[0]) * bis[0] + (YY - cut[1]) * bis[1] > 0) & (np.hypot(XX - T[0], YY - T[1]) < 260)
    # wedge polygon: flank lines between the cut and the apparent tip (blunt end if T short of V)
    def upto(Cfull):
        pr = (Cfull - T[None, :]) @ bis
        return Cfull[(pr <= 0) & (pr >= -170)]
    Cf0 = curve(fl[0], np.arange(-300, fl[0]["umax"] + 400, 0.5)); Cf1 = curve(fl[1], np.arange(-300, fl[1]["umax"] + 400, 0.5))
    A = upto(Cf0); Bc = upto(Cf1)
    poly = np.concatenate([A, [T], Bc[::-1]])
    wedge = fill_polygon(poly, H, W)
    zone_all |= zone; patch_all |= (wedge & zone)
    info[name]["patch_polygon"] = poly.tolist()
m2 = (m & ~zone_all) | patch_all
lab, n = label_runs(m2); sz = np.bincount(lab.ravel()); sz[0] = 0; m2 = lab == int(np.argmax(sz))
lab2, n2 = label_runs(~m2)
border = np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])); border = border[border > 0]
m2 = ~np.isin(lab2, border)
np.save(BASE + "/mask_final.npy", m2)
write_png(BASE + "/manji_mask.png", m2.astype(np.float32))
json.dump(info, open(BASE + "/tips_info.json", "w"), indent=1)
print("final area", int(m2.sum()))
