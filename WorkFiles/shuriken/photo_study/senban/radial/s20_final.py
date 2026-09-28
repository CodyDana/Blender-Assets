"""Senban.jpg - final measurement pass (run in Blender 5.2 headless, numpy only).

Method A (radial profile) for centre, periodicity, tip/notch radii; per-side scanlines normal to each
chord for the side geometry (radial rays graze the edge near the tips); hole by rays from its centre.

Edge rules (derived from 1-px profiles, see s14_darkzoom.py):
  * outer edge, any side: going inward, first local max of -dL/dn >= max(0.02/px, 25% of window max)
    in [n_thr-6, n_thr+18], n_thr = first sample with colour distance to background > 0.25.
  * TOP side only (edges whose steel lies at +y of the lid, the direction the scanner casts a hard
    shadow): the first drop is a soft ramp + grey zone (L~0.17). Variant 'inner' puts the edge at the
    crisp drop into the near-black facet (steepest -dL/dn in [ramp+3, ramp+22]); variant 'outer'
    keeps the ramp. 'inner' is the primary interpretation (see JSON notes).
  * bevel inner edge: steepest steel-to-steel step in [edge+5, edge+32] (descent for the lighter
    bands, ascent for the dark top band), profiles smoothed +-5 px along the side.
"""
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

res = {"photo": "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Senban.jpg"}
rgb = load_rgb().astype(np.float64)
H, W, _ = rgb.shape
L = rgb.mean(-1)
Bw = 12
border = np.concatenate([rgb[:Bw].reshape(-1, 3), rgb[-Bw:].reshape(-1, 3),
                         rgb[:, :Bw].reshape(-1, 3), rgb[:, -Bw:].reshape(-1, 3)])
mu = border.mean(0)
D = np.sqrt(((rgb - mu) ** 2).sum(-1))
T = 0.25


def bilinear(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def gs_cols(a, s):          # gaussian along axis 1
    r = int(3 * s) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    p = np.pad(a, ((0, 0), (r, r)), mode='edge')
    o = np.zeros_like(a)
    for i, kv in enumerate(k):
        o += kv * p[:, i:i + a.shape[1]]
    return o


def gs_rows(a, s):          # gaussian along axis 0
    return gs_cols(a.T, s).T


def parab(arr, k):
    a, b, c = arr[k - 1], arr[k], arr[k + 1]
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return max(-1.0, min(1.0, off))


def first_peak(g, thr):
    """index of first local max of g with g>=thr (g already restricted to window)"""
    idx = np.nonzero(g >= thr)[0]
    if len(idx) == 0: return None
    k = int(idx[0])
    while k + 1 < len(g) and g[k + 1] > g[k]: k += 1
    return k


# ======================================================== coarse silhouette + centre
fg = opening(D > T, 2)
lab, sizes = label(fg)
big = int(np.argmax(sizes[1:]) + 1)
fg = lab == big
bl, _ = label(~fg)
edge_labels = set(np.unique(np.concatenate([bl[0], bl[-1], bl[:, 0], bl[:, -1]])).tolist()) - {0}
filled = ~np.isin(bl, list(edge_labels))
ys, xs = np.nonzero(filled)
cx, cy = float(xs.mean()), float(ys.mean())
res["segmentation"] = {"bg_rgb_mean_srgb": mu.round(4).tolist(), "colour_distance_threshold": T,
                       "components_after_opening": int(len(sizes) - 1),
                       "filled_silhouette_centroid_px": [round(cx, 2), round(cy, 2)]}

# ======================================================== METHOD A: radial r(theta)
STEP = 0.25
NT = 3600
thetas = np.deg2rad(np.arange(NT) * 0.1)


def radial(cx, cy):
    rs = np.arange(150, 720, STEP)
    ct = np.cos(thetas)[:, None]; st = np.sin(thetas)[:, None]
    Dp = bilinear(D, cx + rs * ct, cy + rs * st)
    Lp = np.zeros_like(Dp)
    for p in (-1.0, 0.0, 1.0):
        Lp += bilinear(L, cx + rs * ct - p * st, cy + rs * st + p * ct) / 3
    Ls = gs_cols(Lp, 1.0 / STEP)
    g = -np.gradient(Ls, axis=1) / STEP     # >0 where L drops going OUTWARD? no: we want drop going inward
    g = -g                                    # g = dL/dr ; L rises outward at the edge
    r_edge = np.full(NT, np.nan); r_thr = np.full(NT, np.nan)
    for i in range(NT):
        above = np.nonzero(Dp[i] > T)[0]
        if len(above) == 0: continue
        j0 = above[-1]; r_thr[i] = rs[j0]
        hi = min(j0 + int(6 / STEP), len(rs) - 2); lo = max(j0 - int(18 / STEP), 1)
        seg = g[i, lo:hi + 1][::-1]            # walk inward from outside
        thr = max(0.02, 0.25 * seg.max())
        k = first_peak(seg, thr)
        if k is None: continue
        kk = hi - k
        r_edge[i] = rs[kk] + parab(g[i], kk) * STEP
    return r_edge, r_thr


n_nan_rays = []
for it in range(2):
    r_out, r_thr = radial(cx, cy)
    bad = ~np.isfinite(r_out)
    n_nan_rays.append(int(bad.sum()))
    if bad.any():
        good = np.nonzero(~bad)[0]
        r_out[bad] = np.interp(np.nonzero(bad)[0], np.r_[good - NT, good, good + NT], np.r_[r_out[good]] .repeat(1).tolist() * 3)
    bx = cx + r_out * np.cos(thetas); by = cy + r_out * np.sin(thetas)
    A2 = bx * np.roll(by, -1) - np.roll(bx, -1) * by
    A = 0.5 * A2.sum()
    cx, cy = float(((bx + np.roll(bx, -1)) * A2).sum() / (6 * A)), float(((by + np.roll(by, -1)) * A2).sum() / (6 * A))
rr = r_out - np.nanmean(r_out)
F = np.fft.rfft(np.nan_to_num(rr))
amp = 2 * np.abs(F) / NT
kdom = int(np.argmax(amp[1:40]) + 1)
rsm = np.convolve(np.r_[r_out[-30:], r_out, r_out[:30]], np.ones(21) / 21, mode='same')[30:-30]
phase = np.angle(F[kdom]); per = NT // kdom
tips_i = []
for q in range(kdom):
    ic = int(round(np.rad2deg((-phase + 2 * np.pi * q) / kdom) * 10)) % NT
    win = [(ic + o) % NT for o in range(-per // 3, per // 3)]
    tips_i.append(win[int(np.nanargmax(r_out[win]))])
tips_i = sorted(tips_i)
notch_i = []
for q in range(kdom):
    a_, b_ = tips_i[q], tips_i[(q + 1) % kdom]
    if b_ <= a_: b_ += NT
    idx = [(i % NT) for i in range(a_ + 30, b_ - 30)]
    notch_i.append(idx[int(np.nanargmin(rsm[idx]))])
# widths of each point: angular extent where r > f * r_tip, measured around each tip
widths = {}
for f in (0.95, 0.90, 0.80, 0.70):
    wq = []
    for q, it_ in enumerate(tips_i):
        rt = r_out[it_]
        # walk both ways
        n1 = 0
        while r_out[(it_ - n1) % NT] > f * rt and n1 < per: n1 += 1
        n2 = 0
        while r_out[(it_ + n2) % NT] > f * rt and n2 < per: n2 += 1
        wq.append(round((n1 + n2) * 0.1, 1))
    widths["r>%.2f*r_tip" % f] = wq
rmean = float(np.nanmean(r_out))
res["method_A_radial"] = {
    "centre_boundary_polygon_centroid_px": [round(cx, 2), round(cy, 2)],
    "samples": NT, "step_deg": 0.1,
    "edge_rule": "steepest-first dL/dr peak >= max(0.02/px, 25% of window max) walking inward from r_thr+6 to r_thr-18; r_thr = outermost colour distance > 0.25 (top edge here = OUTER ramp; see per_side for the inner variant)",
    "edge_minus_threshold_px_p5_p50_p95": np.nanpercentile(r_out - r_thr, [5, 50, 95]).round(2).tolist(),
    "rays_without_edge_interpolated": n_nan_rays,
    "dominant_harmonic": kdom,
    "harmonic_amplitude_px_1to12": amp[1:13].round(2).tolist(),
    "harmonic_amplitude_over_mean_r_k4_k8_k12": [round(amp[4] / rmean, 4), round(amp[8] / rmean, 4), round(amp[12] / rmean, 4)],
    "mean_r_px": round(rmean, 2),
    "tip_theta_deg_image_frame": [round(i / 10, 1) for i in tips_i],
    "tip_spacing_deg": [round(((tips_i[(q + 1) % 4] - tips_i[q]) % NT) / 10, 1) for q in range(4)],
    "tip_r_px_raw": [round(float(r_out[i]), 2) for i in tips_i],
    "notch_theta_deg": [round(i / 10, 1) for i in notch_i],
    "notch_r_px_smoothed21": [round(float(rsm[i]), 2) for i in notch_i],
    "notch_over_tip_r": round(float(np.mean([rsm[i] for i in notch_i]) / np.mean([r_out[i] for i in tips_i])), 4),
    "point_angular_width_deg": widths,
    "note": "radial rays graze the edge within ~20 px of each tip, so raw tip radii under-read; per-side scanlines below are used for corners",
}
radial_pts = (bx.copy(), by.copy())

# ======================================================== per-side scanlines
# initial corners from radial tips
corners0 = [np.array([bx[i], by[i]]) for i in tips_i]


def side_frame(P0, P1):
    ch = P1 - P0; c = float(np.linalg.norm(ch)); u = ch / c
    n = np.array([-u[1], u[0]])
    if np.dot(np.array([cx, cy]) - (P0 + P1) / 2, n) < 0: n = -n
    return u, n, c


def scan_side(P0, P1, ext=25.0):
    u, n, c = side_frame(P0, P1)
    ss = np.arange(-ext, c + ext + 0.01, 1.0)
    ns = np.arange(-30, 140, STEP)
    Lp = np.zeros((len(ss), len(ns))); Dp = np.zeros_like(Lp)
    for o in (-1.0, 0.0, 1.0):
        X = P0[0] + (ss[:, None] + o) * u[0] + ns[None, :] * n[0]
        Y = P0[1] + (ss[:, None] + o) * u[1] + ns[None, :] * n[1]
        Lp += bilinear(L, X, Y) / 3; Dp += bilinear(D, X, Y) / 3
    return u, n, c, ss, ns, Lp, Dp


def detect_outer(ns, Lp, Dp, top_inner=False):
    Ls = gs_cols(Lp, 1.0 / STEP)
    g = -np.gradient(Ls, axis=1) / STEP          # >0 where L drops going inward
    e_out = np.full(Lp.shape[0], np.nan); e_in = np.full(Lp.shape[0], np.nan)
    for i in range(Lp.shape[0]):
        above = np.nonzero(Dp[i] > T)[0]
        if len(above) == 0 or above[0] == 0: continue
        j0 = above[0]
        lo = max(j0 - int(6 / STEP), 1); hi = min(j0 + int(18 / STEP), len(ns) - 2)
        seg = g[i, lo:hi + 1]
        k = first_peak(seg, max(0.02, 0.25 * seg.max()))
        if k is None: continue
        kk = lo + k
        e_out[i] = ns[kk] + parab(g[i], kk) * STEP
        if top_inner:
            # end of the soft ramp: first sample after the ramp edge with L < 0.24, then the crisp
            # drop into the near-black facet = steepest descent within the next 16 px
            after = np.nonzero(Ls[i, kk:] < 0.24)[0]
            if len(after) == 0: continue
            lo2 = kk + int(after[0]); hi2 = min(lo2 + int(16 / STEP), len(ns) - 2)
            seg2 = g[i, lo2:hi2 + 1]
            k2 = lo2 + int(np.argmax(seg2))
            e_in[i] = ns[k2] + parab(g[i], k2) * STEP
    return e_out, e_in


def robust_circle(X, Y, it=3):
    s = np.isfinite(X) & np.isfinite(Y)
    X, Y = X[s], Y[s]
    keep = np.ones(len(X), bool)
    for _ in range(it):
        fcx, fcy, R, rms = fit_circle(X[keep], Y[keep])
        d = np.abs(np.hypot(X - fcx, Y - fcy) - R)
        keep = d < max(3 * rms, 1.5)
    fcx, fcy, R, rms = fit_circle(X[keep], Y[keep])
    return fcx, fcy, R, rms, int(keep.sum()), int(len(X))


def robust_line(X, Y, it=3):
    s = np.isfinite(X) & np.isfinite(Y)
    X, Y = X[s], Y[s]
    keep = np.ones(len(X), bool)
    for _ in range(it):
        (mx, my), (ux, uy), rms = fit_line(X[keep], Y[keep])
        d = np.abs((X - mx) * (-uy) + (Y - my) * ux)
        keep = d < max(3 * rms, 1.0)
    (mx, my), (ux, uy), rms = fit_line(X[keep], Y[keep])
    return (mx, my), (ux, uy), rms, int(keep.sum())


scans = {}
for q in range(4):
    P0 = corners0[q]; P1 = corners0[(q + 1) % 4]
    u, n, c, ss, ns, Lp, Dp = scan_side(P0, P1)
    mid = (P0 + P1) / 2
    name = ("top" if mid[1] < cy - 200 else "bottom" if mid[1] > cy + 200 else "left" if mid[0] < cx else "right")
    e_out, e_in = detect_outer(ns, Lp, Dp, top_inner=(name == "top"))
    scans[q] = dict(name=name, P0=P0, P1=P1, u=u, n=n, c=c, ss=ss, ns=ns, Lp=Lp, e_out=e_out, e_in=e_in)
names = [scans[q]["name"] for q in range(4)]


def build(variant):
    """variant 'inner' or 'outer' (only changes the top side). Returns geometry dict."""
    pts = {}
    for q in range(4):
        S = scans[q]
        e = S["e_in"] if (S["name"] == "top" and variant == "inner") else S["e_out"]
        X = S["P0"][0] + S["ss"] * S["u"][0] + e * S["n"][0]
        Y = S["P0"][1] + S["ss"] * S["u"][1] + e * S["n"][1]
        # smooth along the side (median of 5) to suppress single-scanline jumps
        pts[q] = (X, Y)
    # circles on t in [0.1, 0.9] of the provisional chord
    circ = {}
    for q in range(4):
        S = scans[q]; X, Y = pts[q]
        t = S["ss"] / S["c"]
        s = (t > 0.1) & (t < 0.9)
        circ[q] = robust_circle(X[s], Y[s])
    # local apex at each corner: lines fitted to each side's edge points 15..60 px from the provisional corner
    apex = {}; tipang = {}
    for q in range(4):
        qa, qb = (q - 1) % 4, q
        Sa, Sb = scans[qa], scans[qb]
        Xa, Ya = pts[qa]; Xb, Yb = pts[qb]
        est = np.array(Sb["P0"], float)
        for _it in range(4):
            out = {}
            # distance of each edge point from the current apex estimate; only points on the
            # correct side of the apex (inside the chord direction) are used
            da = np.hypot(Xa - est[0], Ya - est[1]); db = np.hypot(Xb - est[0], Yb - est[1])
            ina = ((Xa - est[0]) * (-Sa["u"][0]) + (Ya - est[1]) * (-Sa["u"][1])) > 0
            inb = ((Xb - est[0]) * Sb["u"][0] + (Yb - est[1]) * Sb["u"][1]) > 0
            for lo, hi in ((10, 40), (15, 60), (20, 100), (40, 160)):
                sa = (da > lo) & (da < hi) & ina; sb = (db > lo) & (db < hi) & inb
                (m1, v1, r1, n1) = robust_line(Xa[sa], Ya[sa])
                (m2, v2, r2, n2) = robust_line(Xb[sb], Yb[sb])
                ix, iy = line_intersect(m1, v1, m2, v2)
                w1 = np.array(m1) - (ix, iy); w1 /= np.linalg.norm(w1)
                w2 = np.array(m2) - (ix, iy); w2 /= np.linalg.norm(w2)
                out["%d-%dpx" % (lo, hi)] = dict(apex=(ix, iy), angle=math.degrees(math.acos(np.clip(np.dot(w1, w2), -1, 1))),
                                                 rms=(round(r1, 2), round(r2, 2)))
            est = np.array(out["15-60px"]["apex"])
        apex[q] = est
        # arc tangents at circle intersection
        a = circ[qa]; b = circ[qb]
        x1, y1, r1 = a[0], a[1], a[2]; x2, y2, r2 = b[0], b[1], b[2]
        dd = math.hypot(x2 - x1, y2 - y1)
        aa = (r1 * r1 - r2 * r2 + dd * dd) / (2 * dd); hh = math.sqrt(max(r1 * r1 - aa * aa, 0))
        xm = x1 + aa * (x2 - x1) / dd; ym = y1 + aa * (y2 - y1) / dd
        cands = [(xm + hh * (y2 - y1) / dd, ym - hh * (x2 - x1) / dd), (xm - hh * (y2 - y1) / dd, ym + hh * (x2 - x1) / dd)]
        vc = min(cands, key=lambda p: math.dist(p, apex[q]))
        P = np.array(vc)
        def tan_dir(fit, towards):
            rv = P - np.array([fit[0], fit[1]]); tv = np.array([-rv[1], rv[0]]); tv /= np.linalg.norm(tv)
            return tv if np.dot(tv, towards - P) > 0 else -tv
        ta = tan_dir(a, np.array([cx, cy])); tb = tan_dir(b, np.array([cx, cy]))
        # choose tangent pointing along each side away from corner
        tipang[q] = dict(line_fits={k: dict(angle_deg=round(v["angle"], 2), apex_px=[round(v["apex"][0], 2), round(v["apex"][1], 2)], line_rms_px=v["rms"]) for k, v in out.items()},
                         arc_intersection_px=[round(vc[0], 2), round(vc[1], 2)],
                         arc_intersection_minus_apex_px=round(math.dist(vc, apex[q]), 2))
    # arc tangent angle at the arc-intersection corner
    for q in range(4):
        a = circ[(q - 1) % 4]; b = circ[q]
        P = np.array(tipang[q]["arc_intersection_px"])
        def tdir(fit, other_corner):
            rv = P - np.array([fit[0], fit[1]]); tv = np.array([-rv[1], rv[0]]); tv /= np.linalg.norm(tv)
            return tv if np.dot(tv, other_corner - P) > 0 else -tv
        ta = tdir(a, apex[(q - 1) % 4]); tb = tdir(b, apex[(q + 1) % 4])
        tipang[q]["arc_tangent_angle_deg"] = round(math.degrees(math.acos(np.clip(np.dot(ta, tb), -1, 1))), 2)
    # sides relative to apex chords
    sides = {}
    for q in range(4):
        S = scans[q]; X, Y = pts[q]
        P0, P1 = apex[q], apex[(q + 1) % 4]
        ch = P1 - P0; c = float(np.linalg.norm(ch)); u = ch / c
        n = np.array([-u[1], u[0]])
        if np.dot(np.array([cx, cy]) - (P0 + P1) / 2, n) < 0: n = -n
        ok = np.isfinite(X)
        t = ((X - P0[0]) * u[0] + (Y - P0[1]) * u[1]) / c
        dep = (X - P0[0]) * n[0] + (Y - P0[1]) * n[1]
        s = ok & (t > 0.0) & (t < 1.0)
        ts, ds = t[s], dep[s]
        o = np.argsort(ts); ts, ds = ts[o], ds[o]
        # running median (11) then mean (11)
        k = 5
        dmed = np.array([np.median(ds[max(0, i - k):i + k + 1]) for i in range(len(ds))])
        dsm = np.convolve(np.r_[dmed[:k][::-1], dmed, dmed[-k:][::-1]], np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
        jm = int(np.argmax(dsm))
        fcx, fcy, R, rms, nk, nn = circ[q]
        s_arc = R - math.sqrt(max(R * R - (c / 2) ** 2, 0))
        # circle distance from chord at mid (the circle may not pass exactly through the apexes)
        mid = (P0 + P1) / 2
        # intersection of mid-normal with circle, nearest the side
        dcen = np.array([fcx, fcy]) - mid
        along = np.dot(dcen, n); perp = np.dot(dcen, u)
        depth_circle_mid = along - math.sqrt(max(R * R - perp * perp, 0)) if along > 0 else along + math.sqrt(max(R * R - perp * perp, 0))
        prof = []
        for tt in np.arange(0.05, 0.951, 0.05):
            j = int(np.argmin(np.abs(ts - tt)))
            prof.append(round(float(dsm[j]), 2))
        # residuals vs circle by t-band
        rX = P0[0] + ts * c * u[0] + ds * n[0]; rY = P0[1] + ts * c * u[1] + ds * n[1]
        resid = np.hypot(rX - fcx, rY - fcy) - R
        rb = []
        for lo_, hi_ in ((0.02, 0.1), (0.1, 0.3), (0.3, 0.45), (0.45, 0.55), (0.55, 0.7), (0.7, 0.9), (0.9, 0.98)):
            sel = (ts >= lo_) & (ts < hi_)
            rb.append(round(float(np.median(resid[sel])), 2) if sel.any() else None)
        sides[S["name"]] = dict(
            chord_apex_to_apex_px=round(c, 2),
            chord_heading_deg=round(math.degrees(math.atan2(u[1], u[0])), 3),
            sagitta_direct_px=round(float(dsm[jm]), 2), sagitta_direct_at_t=round(float(ts[jm]), 3),
            depth_at_mid_chord_px=round(float(dsm[int(np.argmin(np.abs(ts - 0.5)))]), 2),
            depth_profile_t005_to_095_px=prof,
            arc_radius_px=round(R, 1), arc_fit_rms_px=round(rms, 3), arc_fit_kept=[nk, nn],
            sagitta_from_arc_and_apex_chord_px=round(s_arc, 2),
            arc_depth_at_mid_chord_px=round(float(depth_circle_mid), 2),
            arc_resid_px_by_t_band_002_01_03_045_055_07_09_098=rb,
        )
    ch = [sides[nm]["chord_apex_to_apex_px"] for nm in names]
    diag = [float(np.linalg.norm(apex[0] - apex[2])), float(np.linalg.norm(apex[1] - apex[3]))]
    p1 = apex[0]; d1 = apex[2] - apex[0]; p2 = apex[1]; d2 = apex[3] - apex[1]
    dix, diy = line_intersect(p1, d1, p2, d2)
    quad = []
    for q in range(4):
        a = apex[(q - 1) % 4] - apex[q]; b = apex[(q + 1) % 4] - apex[q]
        quad.append(round(math.degrees(math.acos(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))), 3))
    return dict(pts=pts, circ=circ, apex=apex, tipang=tipang, sides=sides, chords=ch, diag=diag,
                diag_int=(dix, diy), quad=quad)


G = {v: build(v) for v in ("inner", "outer")}

# ======================================================== hole
hb = filled & (L > 0.55) & (np.abs(rgb[..., 0] - rgb[..., 2]) < 0.05)
hl, hsz = label(hb)
ks = int(np.argmax(hsz[1:]) + 1)
hys, hxs = np.nonzero(hl == ks)
hcx, hcy = float(hxs.mean()), float((hys.min() + hys.max()) / 2.0)
NH = 3600
phis = np.deg2rad(np.arange(NH) * 0.1)
rsH = np.arange(5, 200, STEP)
ctH = np.cos(phis)[:, None]; stH = np.sin(phis)[:, None]
LpH = np.zeros((NH, len(rsH)))
for p in (-1.0, 0.0, 1.0):
    LpH += bilinear(L, hcx + rsH * ctH - p * stH, hcy + rsH * stH + p * ctH) / 3
LsH = gs_cols(LpH, 0.75 / STEP)
dLH = np.gradient(LsH, axis=1) / STEP
r_h = np.full(NH, np.nan); r_band_top = np.full(NH, np.nan); kind = np.zeros(NH, int)
for i in range(NH):
    prof = LsH[i]
    lid = np.median(prof[(rsH > 20) & (rsH < 60)])
    js = np.nonzero((prof < 0.85 * lid) & (rsH > 30))[0]
    if len(js) == 0: continue
    j0 = js[0]; j1 = min(j0 + int(32 / STEP), len(rsH) - 2)
    seg = prof[j0:j1]; dseg = dLH[i, j0:j1]
    down = math.sin(phis[i]) > 0.25
    if down and seg.min() < 0.16:
        jmin = int(np.argmin(seg))
        kk = jmin + int(np.argmax(dseg[jmin:]))
        kind[i] = 2
        # top of the shadow band: steepest descent before the minimum
        kb = int(np.argmin(dseg[:max(jmin, 1)]))
        r_band_top[i] = rsH[j0 + kb]
    else:
        kk = int(np.argmin(dseg))            # steepest lid -> steel drop
        kind[i] = 1
    k = j0 + kk
    r_h[i] = rsH[k] + parab(dLH[i], k) * STEP
hx = hcx + r_h * np.cos(phis); hy = hcy + r_h * np.sin(phis)
ang = (np.rad2deg(phis) + 360) % 360
secs = {"right": (ang > 335) | (ang < 25), "bottom": (ang > 65) & (ang < 115),
        "left": (ang > 155) & (ang < 205), "top": (ang > 245) & (ang < 295)}
hlines_ray = {nm: robust_line(hx[s], hy[s]) for nm, s in secs.items()}
# ---- refine each hole side with scanlines normal to the ray-fitted line, averaged +-2 px along the edge
hole_scan = {}
hlines = {}
band_top_pts = None
for nm, ((mx, my), (ux, uy), _, _) in hlines_ray.items():
    u = np.array([ux, uy]); n = np.array([-uy, ux])
    if np.dot(np.array([mx - hcx, my - hcy]), n) < 0: n = -n        # n points out of the hole, into steel
    # foot of the hole centre on the line
    f = np.array([mx, my]) + np.dot(np.array([hcx - mx, hcy - my]), u) * u
    ss = np.arange(-80, 80.01, 1.0)
    ns = np.arange(-45, 25, STEP)
    Lp = np.zeros((len(ss), len(ns))); RBp = np.zeros_like(Lp)
    for o in (-2.0, -1.0, 0.0, 1.0, 2.0):
        X = f[0] + (ss[:, None] + o) * u[0] + ns[None, :] * n[0]
        Y = f[1] + (ss[:, None] + o) * u[1] + ns[None, :] * n[1]
        Lp += bilinear(L, X, Y) / 5
        RBp += bilinear(rgb[..., 0] - rgb[..., 2], X, Y) / 5
    Ls = gs_cols(Lp, 0.75 / STEP)
    RBs = gs_cols(RBp, 1.0 / STEP)
    # chroma edge: lid is neutral, steel (and its orange rim) is warm; crossing of the midpoint between
    # lid chroma (ns -45..-30) and steel chroma (ns +8..+20), searched outward from ns=-25
    e_rb = np.full(len(ss), np.nan)
    for i in range(len(ss)):
        lid_c = np.median(RBs[i, (ns > -45) & (ns < -30)]); st_c = np.median(RBs[i, (ns > 8) & (ns < 20)])
        if st_c - lid_c < 0.03: continue
        mid_c = 0.5 * (lid_c + st_c)
        j = np.nonzero((RBs[i] > mid_c) & (ns > -25))[0]
        if len(j) == 0: continue
        j = j[0]
        a, b = RBs[i, j - 1], RBs[i, j]
        e_rb[i] = ns[j - 1] + STEP * (mid_c - a) / (b - a) if b != a else ns[j]
    g = np.gradient(Ls, axis=1) / STEP      # dL/dn outward
    e = np.full(len(ss), np.nan); eb = np.full(len(ss), np.nan)
    for i in range(len(ss)):
        prof = Ls[i]
        lid = np.median(prof[(ns > -45) & (ns < -30)])
        js = np.nonzero((prof < 0.85 * lid) & (ns > -32))[0]
        if len(js) == 0: continue
        j0 = js[0]; j1 = min(j0 + int(30 / STEP), len(ns) - 2)
        seg = prof[j0:j1]; dseg = g[i, j0:j1]
        if nm == "bottom" and seg.min() < 0.16:
            jmin = int(np.argmin(seg))
            k = j0 + jmin + int(np.argmax(dseg[jmin:]))
            kb = j0 + int(np.argmin(dseg[:max(jmin, 1)]))
            eb[i] = ns[kb] + parab(g[i], kb) * STEP
        else:
            # first significant lid -> steel drop (the orange rim on the hole's right side is steel)
            kf = first_peak(-dseg, 0.5 * (-dseg).max())
            k = j0 + (kf if kf is not None else int(np.argmin(dseg)))
        e[i] = ns[k] + parab(g[i], k) * STEP
    X = f[0] + ss * u[0] + e * n[0]; Y = f[1] + ss * u[1] + e * n[1]
    Xc = f[0] + ss * u[0] + e_rb * n[0]; Yc = f[1] + ss * u[1] + e_rb * n[1]
    hole_edge_variants = globals().setdefault("hole_edge_variants", {})
    hole_edge_variants[nm] = {"L_rule": robust_line(X, Y), "chroma_rule": robust_line(Xc, Yc) if np.isfinite(Xc).sum() > 20 else None,
                              "L_minus_chroma_median_px": round(float(np.nanmedian(e - e_rb)), 2) if np.isfinite(e_rb).sum() > 20 else None}
    # rim-anchored rule: the hole edge carries a thin warm (orange) rim that is steel. Find the rim as the
    # R-B maximum in ns -12..+14, then the edge = steepest outward L drop in [rim-12px, rim].
    e_rim = np.full(len(ss), np.nan)
    gL = np.gradient(Ls, axis=1) / STEP
    for i in range(len(ss)):
        w = np.nonzero((ns > -12) & (ns < 14))[0]
        jr = w[int(np.argmax(RBs[i, w]))]
        lo = max(jr - int(12 / STEP), 1); hi = jr
        if hi - lo < 4: continue
        k = lo + int(np.argmin(gL[i, lo:hi + 1]))
        e_rim[i] = ns[k] + parab(gL[i], k) * STEP
    Xr = f[0] + ss * u[0] + e_rim * n[0]; Yr = f[1] + ss * u[1] + e_rim * n[1]
    hole_edge_variants[nm]["rim_rule"] = robust_line(Xr, Yr)
    hole_edge_variants[nm]["L_minus_rim_median_px"] = round(float(np.nanmedian(e - e_rim)), 2)
    if nm == "left":
        hlines[nm] = robust_line(Xr, Yr)      # left: rim-anchored (the soft lid-shadow ramp confuses the plain L rule)
        X, Y = Xr, Yr
    else:
        hlines[nm] = robust_line(X, Y)
    hole_scan[nm] = (X, Y, e)
    if nm == "bottom":
        band_top_pts = (f[0] + ss * u[0] + eb * n[0], f[1] + ss * u[1] + eb * n[1], e - eb)
# alternative bottom line: top of the shadow band (band treated as steel)
hbx, hby, band_w_scan = band_top_pts
sb = np.isfinite(hbx)
hline_bottom_alt = robust_line(hbx[sb], hby[sb])


def hole_geom(lines):
    hc = {}
    for a_, b_ in (("top", "left"), ("top", "right"), ("bottom", "left"), ("bottom", "right")):
        hc[a_ + "_" + b_] = np.array(line_intersect(lines[a_][0], lines[a_][1], lines[b_][0], lines[b_][1]))
    sides = {"top": float(np.linalg.norm(hc["top_left"] - hc["top_right"])),
             "bottom": float(np.linalg.norm(hc["bottom_left"] - hc["bottom_right"])),
             "left": float(np.linalg.norm(hc["top_left"] - hc["bottom_left"])),
             "right": float(np.linalg.norm(hc["top_right"] - hc["bottom_right"]))}
    # perpendicular separations of opposite lines at their midpoints
    def sep(a, b):
        (mx, my), (ux, uy) = lines[a][0], lines[a][1]
        (nx_, ny_), (vx, vy) = lines[b][0], lines[b][1]
        nrm = np.array([-uy, ux])
        return abs((nx_ - mx) * nrm[0] + (ny_ - my) * nrm[1])
    cen = np.mean(list(hc.values()), axis=0)
    return hc, sides, {"top_to_bottom": sep("top", "bottom"), "left_to_right": sep("left", "right")}, cen


def headmod(u):
    a = math.degrees(math.atan2(u[1], u[0]))
    while a > 45: a -= 90
    while a <= -45: a += 90
    return a


hc, hsides, hsep, hcen = hole_geom(hlines)
lines_alt = dict(hlines); lines_alt["bottom"] = hline_bottom_alt
hc_alt, hsides_alt, hsep_alt, hcen_alt = hole_geom(lines_alt)
# fillets: circle fit to edge points within 30 px of each virtual corner that sit > 1.5 px off both lines
fil = {}
RBimg = rgb[..., 0] - rgb[..., 2]
for kname, P in hc.items():
    bdir = P - hcen; bdir /= np.linalg.norm(bdir)          # outward along the bisector (approx.)
    pdir = np.array([-bdir[1], bdir[0]])
    ss_ = np.arange(-45, 12, STEP)                          # 0 = virtual corner, + = beyond it
    Lb = np.zeros(len(ss_)); Rb = np.zeros(len(ss_))
    for o in (-1.0, 0.0, 1.0):
        Lb += bilinear(L, P[0] + ss_ * bdir[0] + o * pdir[0], P[1] + ss_ * bdir[1] + o * pdir[1]) / 3
        Rb += bilinear(RBimg, P[0] + ss_ * bdir[0] + o * pdir[0], P[1] + ss_ * bdir[1] + o * pdir[1]) / 3
    Lbs = gs_cols(Lb[None, :], 0.75 / STEP)[0]; Rbs = gs_cols(Rb[None, :], 1.0 / STEP)[0]
    gb = np.gradient(Lbs) / STEP
    lid = np.median(Lbs[ss_ < -35])
    j0 = np.nonzero((Lbs < 0.85 * lid) & (ss_ > -35))[0]
    entry = {}
    if len(j0):
        j0 = j0[0]
        seg = Lbs[j0:]; dseg = gb[j0:]
        if kname.startswith("bottom") and seg.min() < 0.16:
            jm = int(np.argmin(seg)); k = j0 + jm + int(np.argmax(dseg[jm:]))
            kb = j0 + int(np.argmin(dseg[:max(jm, 1)]))
            entry["gap_band_as_steel_px"] = round(float(-ss_[kb]), 2)
        else:
            kf = first_peak(-dseg, 0.5 * (-dseg).max()); k = j0 + (kf if kf is not None else int(np.argmin(dseg)))
        entry["gap_L_rule_px"] = round(float(-ss_[k]), 2)
        entry["radius_from_gap_L_rule_px"] = round(float(-ss_[k]) / (math.sqrt(2) - 1), 2)
    lid_c = np.median(Rbs[ss_ < -35]); st_c = np.median(Rbs[ss_ > 6])
    jc = np.nonzero((Rbs > 0.5 * (lid_c + st_c)) & (ss_ > -30))[0]
    if len(jc) and st_c - lid_c > 0.03:
        entry["gap_chroma_rule_px"] = round(float(-ss_[jc[0]]), 2)
        entry["radius_from_gap_chroma_rule_px"] = round(float(-ss_[jc[0]]) / (math.sqrt(2) - 1), 2)
    fil[kname] = entry
    continue
    near = np.hypot(hx - P[0], hy - P[1]) < 35
    devs = []
    for nm in kname.split("_"):
        (mx, my), (ux, uy) = hlines[nm][0], hlines[nm][1]
        devs.append(np.abs((hx - mx) * (-uy) + (hy - my) * ux))
    sel = near & (devs[0] > 1.5) & (devs[1] > 1.5) & np.isfinite(hx)
    # gap along the ray through the corner
    phi = math.atan2(P[1] - hcy, P[0] - hcx)
    i = int(round(math.degrees(phi) * 10)) % NH
    rc = np.nanmedian(r_h[[(i + o) % NH for o in range(-5, 6)]])
    gap = math.hypot(P[0] - hcx, P[1] - hcy) - rc
    entry = {"gap_corner_to_edge_along_ray_px": round(gap, 2), "radius_from_gap_px": round(gap / (math.sqrt(2) - 1), 2),
             "edge_points_off_both_lines": int(sel.sum())}
    if sel.sum() >= 6:
        fx_, fy_, fr, frms = fit_circle(hx[sel], hy[sel])
        entry["circle_fit_radius_px"] = round(fr, 2); entry["circle_fit_rms_px"] = round(frms, 2)
    fil[kname] = entry
# shadow band width along the bottom
band_w = band_w_scan[np.isfinite(band_w_scan)]
res["hole_ray_lines_first_pass"] = {k: {"heading_mod90": round(headmod(v[1]), 3), "rms": round(v[2], 3)} for k, v in hlines_ray.items()}
res["hole"] = {
    "seed_centre_px": [round(hcx, 2), round(hcy, 2)],
    "edge_rule": "rays every 0.1 deg from hole centre; steepest lid->steel drop within 32 px after L<0.85*lid; rays toward image-bottom whose window dips below L=0.16 cross the dark band, edge = steepest rise after its minimum (band counted as opening)",
    "primary_band_as_opening": {
        "corners_px": {k: [round(v[0], 2), round(v[1], 2)] for k, v in hc.items()},
        "side_lengths_px": {k: round(v, 2) for k, v in hsides.items()},
        "opposite_line_separation_px": {k: round(v, 2) for k, v in hsep.items()},
        "centre_px": [round(hcen[0], 2), round(hcen[1], 2)],
        "height_over_width": round(hsep["top_to_bottom"] / hsep["left_to_right"], 4),
    },
    "alternative_band_as_steel": {
        "side_lengths_px": {k: round(v, 2) for k, v in hsides_alt.items()},
        "opposite_line_separation_px": {k: round(v, 2) for k, v in hsep_alt.items()},
        "centre_px": [round(hcen_alt[0], 2), round(hcen_alt[1], 2)],
        "height_over_width": round(hsep_alt["top_to_bottom"] / hsep_alt["left_to_right"], 4),
    },
    "bottom_dark_band_width_px_median_p10_p90": [round(float(np.median(band_w)), 2)] + np.percentile(band_w, [10, 90]).round(2).tolist(),
    "line_heading_deg_mod90": {k: round(headmod(v[1]), 3) for k, v in hlines.items()},
    "line_fit_rms_px": {k: round(v[2], 3) for k, v in hlines.items()},
    "line_fit_kept": {k: v[3] for k, v in hlines.items()},
    "fillets": fil,
    "fillet_rule": "scan from hole interior along the corner bisector through the virtual corner (line intersection); gap = virtual corner to detected edge; radius = gap/(sqrt2-1) for a tangent fillet on a 90 deg corner",
    "edge_rule_variants": {k: {"L_rule_heading_mod90": round(headmod(v["L_rule"][1]), 3), "L_rule_rms": round(v["L_rule"][2], 3),
                               "chroma_rule_heading_mod90": (round(headmod(v["chroma_rule"][1]), 3) if v["chroma_rule"] else None),
                               "chroma_rule_rms": (round(v["chroma_rule"][2], 3) if v["chroma_rule"] else None),
                               "L_minus_chroma_edge_px": v["L_minus_chroma_median_px"],
                               "rim_rule_heading_mod90": round(headmod(v["rim_rule"][1]), 3), "rim_rule_rms": round(v["rim_rule"][2], 3),
                               "L_minus_rim_edge_px": v["L_minus_rim_median_px"]} for k, v in hole_edge_variants.items()},
    "side_rule_used": "top/right: L first-significant rule (lowest line rms); bottom: L rule through the dark band; left: rim-anchored L rule (lowest rms there)",
}

# ======================================================== bevel band
def bevel(variant):
    geo = G[variant]
    out = {}
    for q in range(4):
        S = scans[q]
        e = S["e_in"] if (S["name"] == "top" and variant == "inner") else S["e_out"]
        ns = S["ns"]; Lp = S["Lp"]
        rows = np.nonzero(np.isfinite(e))[0]
        # re-sample each row relative to its edge
        rel = np.arange(-6, 45, STEP)
        A = np.array([np.interp(rel + e[i], ns, Lp[i]) for i in rows])
        A = gs_rows(A, 5.0)                    # +-5 px along the side
        As = gs_cols(A, 1.0 / STEP)
        g = np.gradient(As, axis=1) / STEP
        body = np.median(As[:, (rel > 34) & (rel < 44)], axis=1)
        band = np.median(As[:, (rel > 3) & (rel < 9)], axis=1)
        tone = np.median(band - body)
        win = np.nonzero((rel > 5) & (rel < 32))[0]
        wv = np.array([rel[win[int(np.argmin(g[i, win]))]] if tone > 0 else rel[win[int(np.argmax(g[i, win]))]] for i in range(len(rows))])
        t = S["ss"][rows] / S["c"]
        mid = (t > 0.15) & (t < 0.85)
        prof = []
        for tt in np.arange(0.0, 1.001, 0.05):
            s = np.abs(t - tt) < 0.025
            prof.append(round(float(np.median(wv[s])), 1) if s.any() else None)
        con = []
        for tt in np.arange(0.0, 1.001, 0.05):
            s = np.abs(t - tt) < 0.025
            con.append(round(float(np.median((band - body)[s])), 3) if s.any() else None)
        out[S["name"]] = dict(tone="lighter than body" if tone > 0 else "darker than body",
                              band_minus_body_L=round(float(tone), 3),
                              width_px_median_t015_085=round(float(np.median(wv[mid])), 2),
                              width_px_p10_p90_t015_085=np.percentile(wv[mid], [10, 90]).round(2).tolist(),
                              width_px_by_t_0_to_1_step005=prof,
                              band_contrast_by_t_0_to_1_step005=con,
                              _rows=rows, _w=wv)
    return out


BEV = {v: bevel(v) for v in ("inner", "outer")}

# ======================================================== assemble results
def pack(variant):
    geo = G[variant]
    adj = float(np.mean(geo["chords"]))
    tips = geo["tipang"]
    sag_d = [geo["sides"][nm]["sagitta_direct_px"] for nm in names]
    sag_a = [geo["sides"][nm]["sagitta_from_arc_and_apex_chord_px"] for nm in names]
    radii = [geo["sides"][nm]["arc_radius_px"] for nm in names]
    ang15 = [tips[q]["line_fits"]["15-60px"]["angle_deg"] for q in range(4)]
    ang40 = [tips[q]["line_fits"]["40-160px"]["angle_deg"] for q in range(4)]
    angarc = [tips[q]["arc_tangent_angle_deg"] for q in range(4)]
    bev = BEV[variant]
    bw = {nm: bev[nm]["width_px_median_t015_085"] for nm in names}
    dix, diy = geo["diag_int"]
    hole_side = float(np.mean(list(hsep.values())))
    hole_side_alt = float(np.mean(list(hsep_alt.values())))
    outer_heads = []
    for nm in names:
        a = geo["sides"][nm]["chord_heading_deg"]
        while a > 45: a -= 90
        while a <= -45: a += 90
        outer_heads.append(a)
    hole_heads = [headmod(v[1]) for v in hlines.values()]
    return {
        "apex_corners_px": {names[q] + "->" + names[(q + 1) % 4] if False else "corner_%d" % q: [round(geo["apex"][q][0], 2), round(geo["apex"][q][1], 2)] for q in range(4)},
        "corner_order_note": "corner_q sits between side %s" % ", ".join("%d:%s|%s" % (q, names[(q - 1) % 4], names[q]) for q in range(4)),
        "adjacent_corner_px_by_side": {nm: geo["sides"][nm]["chord_apex_to_apex_px"] for nm in names},
        "adjacent_corner_mean_px": round(adj, 2), "adjacent_corner_sd_px": round(float(np.std(geo["chords"])), 2),
        "corner_to_corner_px": [round(d, 2) for d in geo["diag"]],
        "corner_to_corner_over_adjacent": round(float(np.mean(geo["diag"])) / adj, 4),
        "chord_quad_interior_angles_deg": geo["quad"],
        "sides": geo["sides"],
        "sagitta_direct_px": sag_d, "sagitta_direct_mean_px": round(float(np.mean(sag_d)), 2), "sagitta_direct_sd_px": round(float(np.std(sag_d)), 2),
        "sagitta_over_chord_direct": [round(s / c, 4) for s, c in zip(sag_d, [geo["sides"][nm]["chord_apex_to_apex_px"] for nm in names])],
        "sagitta_over_chord_direct_mean": round(float(np.mean([s / geo["sides"][nm]["chord_apex_to_apex_px"] for s, nm in zip(sag_d, names)])), 4),
        "sagitta_arc_mean_px": round(float(np.mean(sag_a)), 2), "sagitta_arc_sd_px": round(float(np.std(sag_a)), 2),
        "arc_radius_over_adjacent": [round(r / adj, 3) for r in radii],
        "arc_radius_over_adjacent_mean": round(float(np.mean(radii)) / adj, 3), "arc_radius_over_adjacent_sd": round(float(np.std(radii)) / adj, 3),
        "tip_angle_deg_line_fit_15_60px": ang15, "tip_angle_line_15_60_mean": round(float(np.mean(ang15)), 2), "tip_angle_line_15_60_sd": round(float(np.std(ang15)), 2),
        "tip_angle_deg_line_fit_40_160px": ang40, "tip_angle_line_40_160_mean": round(float(np.mean(ang40)), 2),
        "tip_angle_deg_arc_tangents": angarc, "tip_angle_arc_mean": round(float(np.mean(angarc)), 2), "tip_angle_arc_sd": round(float(np.std(angarc)), 2),
        "tip_detail": tips,
        "diagonal_intersection_px": [round(dix, 2), round(diy, 2)],
        "hole_centre_offset_from_diag_intersection_px": [round(hcen[0] - dix, 2), round(hcen[1] - diy, 2)],
        "hole_centre_offset_over_adjacent": round(math.hypot(hcen[0] - dix, hcen[1] - diy) / adj, 4),
        "hole_side_over_adjacent_band_as_opening": round(hole_side / adj, 4),
        "hole_side_over_adjacent_band_as_steel": round(hole_side_alt / adj, 4),
        "hole_side_over_corner_to_corner_band_as_opening": round(hole_side / float(np.mean(geo["diag"])), 4),
        "hole_rotation_vs_outer_deg": round(float(np.mean(hole_heads) - np.mean(outer_heads)), 3),
        "outer_side_headings_mod90_deg": [round(a, 3) for a in outer_heads],
        "hole_side_headings_mod90_deg": [round(a, 3) for a in hole_heads],
        "bevel": {nm: {k: v for k, v in bev[nm].items() if not k.startswith("_")} for nm in names},
        "bevel_width_over_adjacent": {nm: round(bw[nm] / adj, 4) for nm in names},
        "bevel_width_over_adjacent_mean": round(float(np.mean(list(bw.values()))) / adj, 4),
        "bevel_width_px_mean_sd": [round(float(np.mean(list(bw.values()))), 2), round(float(np.std(list(bw.values()))), 2)],
    }


res["per_side_primary_top_edge_inner"] = pack("inner")
res["per_side_alt_top_edge_outer"] = pack("outer")
res["notes"] = [
    "Image frame: x right, y down, angles atan2(dy,dx) in image frame (clockwise on screen).",
    "The plate lies with its sides roughly along the image axes (tilted about -2 deg); it is photographed on a side, not on a corner.",
    "Scanner lighting casts a hard shadow on the lid next to steel edges whose steel lies at +y of the opening (hole bottom edge, outer top edge) and a soft wide halo at +x (outer right edge, hole left edge).",
    "Top edge ambiguity: 'inner' (primary) treats the ~17-21 px ramp+grey zone above the near-black band as lid shadow, consistent with (a) the hole's bottom edge showing a ~20 px dark band of the same orientation, (b) the top near-black band then being ~12 px wide like the 14-17 px bands on the other three sides, (c) the grey zone lacking the left bevel's tone at the top-left tip. 'outer' treats it as steel.",
]
json.dump(res, open(OUT + "senban_final.json", "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))

# ======================================================== mask (primary variant)
geo = G["inner"]
poly = []
for q in range(4):
    X, Y = geo["pts"][q]
    S = scans[q]
    t = S["ss"] / S["c"]
    P0, P1 = geo["apex"][q], geo["apex"][(q + 1) % 4]
    u, _, c = side_frame(P0, P1)
    tt = ((X - P0[0]) * u[0] + (Y - P0[1]) * u[1]) / c
    s = np.isfinite(X) & (tt > 0.0) & (tt < 1.0)
    o = np.argsort(tt[s])
    poly.append(np.array([P0[0], P0[1]])[None, :])
    poly.append(np.column_stack([X[s][o], Y[s][o]]))
poly = np.concatenate(poly, 0)
pa = (np.degrees(np.arctan2(poly[:, 1] - cy, poly[:, 0] - cx)) + 360) % 360
pr = np.hypot(poly[:, 0] - cx, poly[:, 1] - cy)
o = np.argsort(pa); pa, pr = pa[o], pr[o]
yy, xx = np.mgrid[0:H, 0:W]
th = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
rho = np.hypot(xx - cx, yy - cy)
rb_ = np.interp(th.ravel(), np.r_[pa - 360, pa, pa + 360], np.r_[pr, pr, pr]).reshape(H, W)
inside = rho <= rb_
rhf = r_h.copy(); bad = ~np.isfinite(rhf)
if bad.any(): rhf[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], rhf[~bad])
thh = (np.degrees(np.arctan2(yy - hcy, xx - hcx)) + 360) % 360
rhoh = np.hypot(xx - hcx, yy - hcy)
rhb = np.interp(thh.ravel(), np.r_[np.arange(NH) * 0.1, 360.0], np.r_[rhf, rhf[0]]).reshape(H, W)
mask = inside & ~(rhoh <= rhb)
save_png(mask.astype(np.float32), OUT + "senban_mask.png")

# ======================================================== overlay
ov = rgb * 0.8
def put(x, y, col, r=0):
    x = np.atleast_1d(np.round(np.asarray(x, float)).astype(int)); y = np.atleast_1d(np.round(np.asarray(y, float)).astype(int))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ov[np.clip(y + dy, 0, H - 1), np.clip(x + dx, 0, W - 1)] = col
# radial boundary (blue), outer-variant top (yellow), primary edges (green)
put(radial_pts[0], radial_pts[1], (0.3, 0.5, 1.0))
X, Y = G["outer"]["pts"][[q for q in range(4) if names[q] == "top"][0]]
put(X[np.isfinite(X)], Y[np.isfinite(Y)], (1.0, 1.0, 0.0))
for q in range(4):
    X, Y = geo["pts"][q]
    put(X[np.isfinite(X)], Y[np.isfinite(Y)], (0.1, 1.0, 0.1))
    fcx, fcy, R = geo["circ"][q][:3]
    P0, P1 = geo["apex"][q], geo["apex"][(q + 1) % 4]
    a0 = math.atan2(P0[1] - fcy, P0[0] - fcx); a1 = math.atan2(P1[1] - fcy, P1[0] - fcx)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    aa = a0 + np.linspace(0, 1, 3000) * da
    put(fcx + R * np.cos(aa), fcy + R * np.sin(aa), (0.0, 0.9, 1.0))
    tt = np.linspace(0, 1, 3000)
    put(P0[0] + tt * (P1[0] - P0[0]), P0[1] + tt * (P1[1] - P0[1]), (1.0, 1.0, 0.3))
# bevel inner edge (orange), primary
for q in range(4):
    S = scans[q]; b = BEV["inner"][S["name"]]
    e = S["e_in"] if S["name"] == "top" else S["e_out"]
    rows = b["_rows"]; wv = b["_w"]
    X = S["P0"][0] + S["ss"][rows] * S["u"][0] + (e[rows] + wv) * S["n"][0]
    Y = S["P0"][1] + S["ss"][rows] * S["u"][1] + (e[rows] + wv) * S["n"][1]
    put(X[::3], Y[::3], (1.0, 0.55, 0.0))
for q in range(4):
    put(geo["apex"][q][0], geo["apex"][q][1], (1, 0, 0), 2)
for a_, b_ in ((0, 2), (1, 3)):
    tt = np.linspace(0, 1, 4000)
    put(geo["apex"][a_][0] + tt * (geo["apex"][b_][0] - geo["apex"][a_][0]), geo["apex"][a_][1] + tt * (geo["apex"][b_][1] - geo["apex"][a_][1]), (0.7, 0.7, 0.0))
put(hx[kind == 1], hy[kind == 1], (1.0, 0.0, 1.0))
put(hx[kind == 2], hy[kind == 2], (1.0, 0.4, 0.4))
put(hbx[sb], hby[sb], (0.3, 1.0, 1.0))
for nm, (X, Y, e) in hole_scan.items():
    s = np.isfinite(X)
    put(X[s], Y[s], (1.0, 1.0, 0.0))
for nm, ((mx, my), (ux, uy), rms, n) in hlines.items():
    tt = np.linspace(-140, 140, 1200)
    put(mx + tt * ux, my + tt * uy, (1.0, 0.0, 0.0))
put(cx, cy, (0.1, 1.0, 0.1), 2)
put(hcen[0], hcen[1], (1.0, 0.0, 1.0), 2)
save_png(ov, OUT + "senban_overlay.png")
def zoom(a, x0, y0, x1, y1, S):
    return np.repeat(np.repeat(a[y0:y1, x0:x1], S, 0), S, 1)
save_png(zoom(ov, 360, 330, 650, 620, 3), OUT + "senban_overlay_hole.png")
for q in range(4):
    P = geo["apex"][q]
    x0 = max(0, min(W - 90, int(P[0]) - 45)); y0 = max(0, min(H - 90, int(P[1]) - 45))
    save_png(zoom(ov, x0, y0, x0 + 90, y0 + 90, 6), OUT + "senban_overlay_corner%d.png" % q)
save_png(zoom(ov, 420, 50, 600, 140, 4), OUT + "senban_overlay_topedge.png")
save_png(zoom(ov, 90, 380, 180, 560, 4), OUT + "senban_overlay_leftedge.png")
save_png(zoom(ov, 850, 380, 940, 560, 4), OUT + "senban_overlay_rightedge.png")
save_png(zoom(ov, 420, 800, 600, 890, 4), OUT + "senban_overlay_bottomedge.png")
print("NAMES", names)
p = res["per_side_primary_top_edge_inner"]
for k in ("adjacent_corner_px_by_side", "adjacent_corner_mean_px", "corner_to_corner_px", "corner_to_corner_over_adjacent",
          "chord_quad_interior_angles_deg", "sagitta_direct_px", "sagitta_over_chord_direct", "sagitta_arc_mean_px",
          "arc_radius_over_adjacent", "tip_angle_deg_line_fit_15_60px", "tip_angle_deg_line_fit_40_160px", "tip_angle_deg_arc_tangents",
          "hole_centre_offset_from_diag_intersection_px", "hole_side_over_adjacent_band_as_opening", "hole_side_over_adjacent_band_as_steel",
          "hole_rotation_vs_outer_deg", "bevel_width_px_mean_sd"):
    print(k, p[k])
for nm in names:
    s = p["sides"][nm]
    print(nm, "arc rms", s["arc_fit_rms_px"], "resid", s["arc_resid_px_by_t_band_002_01_03_045_055_07_09_098"], "sag@t", s["sagitta_direct_at_t"])
    print("  bevel", p["bevel"][nm]["tone"], p["bevel"][nm]["width_px_median_t015_085"], p["bevel"][nm]["width_px_by_t_0_to_1_step005"])
print("HOLE", json.dumps(res["hole"], default=str)[:3000])
print("RADIAL", json.dumps(res["method_A_radial"], default=str)[:2500])
