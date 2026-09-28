"""Senban (Senban.jpg) radial-profile measurement. Run in Blender 5.2 headless.

Outputs (all in this folder):
  senban_mask.png          final plate mask (white = steel), hole cut out
  senban_overlay.png       debug overlay
  senban_radial.json       all numbers
"""
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

OUTJ = OUT + "senban_radial.json"
res = {}

rgb = load_rgb()
H, W, _ = rgb.shape
L = rgb.mean(-1)
Bw = 12
border = np.concatenate([rgb[:Bw].reshape(-1, 3), rgb[-Bw:].reshape(-1, 3),
                         rgb[:, :Bw].reshape(-1, 3), rgb[:, -Bw:].reshape(-1, 3)])
mu = border.mean(0)
D = np.sqrt(((rgb - mu) ** 2).sum(-1))
res["image"] = {"w": W, "h": H, "bg_rgb_mean": mu.round(4).tolist()}

# ---------------------------------------------------------------- coarse mask
T = 0.25
fg = D > T
fg = opening(fg, 2)
lab, sizes = label(fg)
big = np.argmax(sizes[1:]) + 1
fg = lab == big
res["coarse"] = {"threshold": T, "n_components": int(len(sizes) - 1),
                 "largest_px": int(sizes[big]), "second_px": int(np.sort(sizes[1:])[-2]) if len(sizes) > 2 else 0}
bl, bsz = label(~fg)
edge_labels = set(np.unique(np.concatenate([bl[0], bl[-1], bl[:, 0], bl[:, -1]])).tolist()) - {0}
outside = np.isin(bl, list(edge_labels))
filled = ~outside
enclosed = (~fg) & filled
el, esz = label(enclosed)
res["coarse"]["enclosed_bg_components"] = int(len(esz) - 1)
res["coarse"]["enclosed_bg_sizes_top5"] = sorted(esz[1:].tolist(), reverse=True)[:5]
ys, xs = np.nonzero(filled)
cx0, cy0 = xs.mean(), ys.mean()
res["coarse"]["filled_centroid"] = [round(cx0, 2), round(cy0, 2)]
save_png(fg.astype(np.float32), OUT + "dbg_coarse_mask.png")


# ---------------------------------------------------------------- samplers
def bilinear(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def gsmooth1d(a, sigma_samples):
    r = int(3 * sigma_samples) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_samples) ** 2); k /= k.sum()
    p = np.pad(a, ((0, 0), (r, r)), mode='edge')
    out = np.zeros_like(a)
    for i, kv in enumerate(k):
        out += kv * p[:, i:i + a.shape[1]]
    return out


def ray_profiles(cx, cy, thetas, r0, r1, step, img, perp=(-1.0, 0.0, 1.0)):
    rs = np.arange(r0, r1, step)
    ct = np.cos(thetas)[:, None]; st = np.sin(thetas)[:, None]
    acc = np.zeros((len(thetas), len(rs)))
    for p in perp:
        X = cx + rs[None, :] * ct - p * st
        Y = cy + rs[None, :] * st + p * ct
        acc += bilinear(img, X, Y)
    return rs, acc / len(perp)


# ---------------------------------------------------------------- outer boundary r(theta)
STEP = 0.25
NT = 3600
thetas = np.deg2rad(np.arange(NT) * 0.1)
cx, cy = cx0, cy0
for it in range(2):
    rs, Dp = ray_profiles(cx, cy, thetas, 150, 720, STEP, D.astype(np.float64), perp=(0.0,))
    _, Lp = ray_profiles(cx, cy, thetas, 150, 720, STEP, L.astype(np.float64))
    Ls = gsmooth1d(Lp, 1.0 / STEP)
    dL = np.gradient(Ls, axis=1) / STEP
    r_out = np.zeros(NT); r_thr = np.zeros(NT)
    for i in range(NT):
        above = np.nonzero(Dp[i] > T)[0]
        j0 = above[-1]
        r_thr[i] = rs[j0]
        lo = max(j0 - int(16 / STEP), 1); hi = min(j0 + int(4 / STEP), len(rs) - 2)
        seg = dL[i, lo:hi]
        k = lo + int(np.argmax(seg))
        a, b, c = dL[i, k - 1], dL[i, k], dL[i, k + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
        off = max(-1, min(1, off))
        r_out[i] = rs[k] + off * STEP
    bx = cx + r_out * np.cos(thetas); by = cy + r_out * np.sin(thetas)
    # refine centre = area centroid of the boundary polygon
    A = 0.5 * np.sum(bx * np.roll(by, -1) - np.roll(bx, -1) * by)
    ccx = np.sum((bx + np.roll(bx, -1)) * (bx * np.roll(by, -1) - np.roll(bx, -1) * by)) / (6 * A)
    ccy = np.sum((by + np.roll(by, -1)) * (bx * np.roll(by, -1) - np.roll(bx, -1) * by)) / (6 * A)
    cx, cy = ccx, ccy
res["outer_boundary"] = {"centre_polygon_centroid": [round(cx, 2), round(cy, 2)],
                         "area_px": round(abs(A), 1),
                         "edge_rule": "steepest dL/dr in [r_thr-16px, r_thr+4px], r_thr = outermost colour-distance>0.25",
                         "mean_shift_edge_vs_threshold_px": round(float(np.mean(r_out - r_thr)), 2)}
# boundary sanity: compare with threshold boundary
res["outer_boundary"]["edge_minus_threshold_px_pctl_5_50_95"] = np.percentile(r_out - r_thr, [5, 50, 95]).round(2).tolist()

# ---------------------------------------------------------------- periodicity
rr = r_out - r_out.mean()
F = np.abs(np.fft.rfft(rr))
kdom = int(np.argmax(F[1:40]) + 1)
res["periodicity"] = {"dominant_harmonic": kdom,
                      "harmonic_amplitudes_px_1to12": (2 * F[1:13] / NT).round(2).tolist()}

# ---------------------------------------------------------------- corners (maxima) and notches (minima)
rsm = np.convolve(np.r_[r_out[-50:], r_out, r_out[:50]], np.ones(21) / 21, mode='same')[50:-50]
per = NT // kdom
maxima = []; minima = []
for q in range(kdom):
    # find maxima by searching windows around the harmonic phase
    pass
phase = np.angle(np.fft.rfft(rr)[kdom])
# peaks of cos(k*theta + phase)
for q in range(kdom):
    tc = (-phase + 2 * np.pi * q) / kdom
    ic = int(round(np.rad2deg(tc) * 10)) % NT
    win = [(ic + o) % NT for o in range(-per // 3, per // 3)]
    im = win[int(np.argmax(r_out[win]))]
    maxima.append(im)
maxima = sorted(maxima)
for q in range(kdom):
    a_, b_ = maxima[q], maxima[(q + 1) % kdom]
    if b_ <= a_: b_ += NT
    idx = [(i % NT) for i in range(a_ + 20, b_ - 20)]
    minima.append(idx[int(np.argmin(rsm[idx]))])
tip_raw = [(float(bx[i]), float(by[i])) for i in maxima]
res["radial"] = {
    "tip_theta_deg": [round(i / 10, 1) for i in maxima],
    "tip_r_px": [round(float(r_out[i]), 2) for i in maxima],
    "notch_theta_deg": [round(i / 10, 1) for i in minima],
    "notch_r_px_smoothed": [round(float(rsm[i]), 2) for i in minima],
}

# ---------------------------------------------------------------- side arcs
def pts_between(i0, i1):
    if i1 <= i0: i1 += NT
    idx = np.array([(i % NT) for i in range(i0, i1 + 1)])
    return bx[idx], by[idx], idx

corners = list(tip_raw)
sides = []
for it in range(4):
    fits = []
    for q in range(4):
        i0, i1 = maxima[q], maxima[(q + 1) % 4]
        X, Y, idx = pts_between(i0, i1)
        P0 = np.array(corners[q]); P1 = np.array(corners[(q + 1) % 4])
        ch = P1 - P0; c = np.linalg.norm(ch); u = ch / c
        t = ((X - P0[0]) * u[0] + (Y - P0[1]) * u[1]) / c
        sel = (t > 0.08) & (t < 0.92)
        fcx, fcy, R, rms = fit_circle(X[sel], Y[sel])
        fits.append((fcx, fcy, R, rms, sel.sum()))
    # new corners = intersection of adjacent circles, nearest to old corner
    newc = []
    for q in range(4):
        a = fits[(q - 1) % 4]; b = fits[q]
        x1, y1, r1 = a[0], a[1], a[2]; x2, y2, r2 = b[0], b[1], b[2]
        dd = math.hypot(x2 - x1, y2 - y1)
        aa = (r1 * r1 - r2 * r2 + dd * dd) / (2 * dd)
        hh = math.sqrt(max(r1 * r1 - aa * aa, 0))
        xm = x1 + aa * (x2 - x1) / dd; ym = y1 + aa * (y2 - y1) / dd
        c1 = (xm + hh * (y2 - y1) / dd, ym - hh * (x2 - x1) / dd)
        c2 = (xm - hh * (y2 - y1) / dd, ym + hh * (x2 - x1) / dd)
        old = corners[q]
        newc.append(c1 if math.dist(c1, old) < math.dist(c2, old) else c2)
    corners = newc

side_names = []
side_res = []
for q in range(4):
    P0 = np.array(corners[q]); P1 = np.array(corners[(q + 1) % 4])
    fcx, fcy, R, rms, n = fits[q]
    ch = P1 - P0; c = float(np.linalg.norm(ch)); u = ch / c
    nrm = np.array([-u[1], u[0]])
    mid = (P0 + P1) / 2
    # orient nrm towards plate centre
    if np.dot(np.array([cx, cy]) - mid, nrm) < 0: nrm = -nrm
    s_fit = R - math.sqrt(max(R * R - (c / 2) ** 2, 0))
    X, Y, idx = pts_between(maxima[q], maxima[(q + 1) % 4])
    t = ((X - P0[0]) * u[0] + (Y - P0[1]) * u[1]) / c
    dep = (X - P0[0]) * nrm[0] + (Y - P0[1]) * nrm[1]
    sel = (t > 0.02) & (t < 0.98)
    # smooth depth for direct sagitta
    order = np.argsort(t[sel]); ts = t[sel][order]; ds = dep[sel][order]
    k = 15
    dsm = np.convolve(np.r_[ds[:k][::-1], ds, ds[-k:][::-1]], np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    jm = int(np.argmax(dsm))
    # depth at mid-chord (t in 0.45..0.55)
    midsel = (ts > 0.45) & (ts < 0.55)
    # asymmetry: depth at t=0.25 vs 0.75
    def dat(tt):
        s = (ts > tt - 0.02) & (ts < tt + 0.02)
        return float(np.mean(ds[s])) if s.any() else float('nan')
    # parabola vs circle residual comparison
    pc = np.polyfit(ts, ds, 2)
    prms = float(np.sqrt(np.mean((np.polyval(pc, ts) - ds) ** 2)))
    heading = math.degrees(math.atan2(u[1], u[0]))
    mx, my = mid
    name = ("top" if my < cy and abs(u[0]) > abs(u[1]) else
            "bottom" if my > cy and abs(u[0]) > abs(u[1]) else
            "left" if mx < cx else "right")
    side_names.append(name)
    side_res.append({
        "name": name,
        "from_corner": q, "to_corner": (q + 1) % 4,
        "chord_px": round(c, 2),
        "chord_heading_deg": round(heading, 3),
        "arc_radius_px": round(R, 1), "arc_fit_rms_px": round(rms, 3), "arc_fit_n": int(n),
        "arc_centre_px": [round(fcx, 1), round(fcy, 1)],
        "sagitta_from_arc_px": round(s_fit, 2),
        "sagitta_direct_max_px": round(float(dsm[jm]), 2),
        "sagitta_direct_max_at_t": round(float(ts[jm]), 3),
        "depth_mid_chord_px": round(float(np.mean(ds[midsel])), 2),
        "depth_t025_px": round(dat(0.25), 2), "depth_t075_px": round(dat(0.75), 2),
        "parabola_rms_px": round(prms, 3),
    })
res["sides"] = side_res
res["corners_virtual_px"] = [[round(p[0], 2), round(p[1], 2)] for p in corners]
res["tips_raw_max_r_px"] = [[round(p[0], 2), round(p[1], 2)] for p in tip_raw]
res["tip_bluntness_px"] = [round(math.dist(corners[q], tip_raw[q]), 2) for q in range(4)]

# chords, diagonals
chords = [s["chord_px"] for s in side_res]
diag = [math.dist(corners[0], corners[2]), math.dist(corners[1], corners[3])]
adj = float(np.mean(chords))
res["square"] = {
    "adjacent_corner_mean_px": round(adj, 2),
    "adjacent_corner_spread_sd_px": round(float(np.std(chords)), 2),
    "adjacent_corner_min_max_px": [round(min(chords), 2), round(max(chords), 2)],
    "diagonals_px": [round(d_, 2) for d_ in diag],
    "diagonal_over_side": round(float(np.mean(diag)) / adj, 4),
    "diagonal_intersection_px": None,
}
# diagonal intersection
p1 = corners[0]; d1 = (corners[2][0] - p1[0], corners[2][1] - p1[1])
p2 = corners[1]; d2 = (corners[3][0] - p2[0], corners[3][1] - p2[1])
dix, diy = line_intersect(p1, d1, p2, d2)
res["square"]["diagonal_intersection_px"] = [round(dix, 2), round(diy, 2)]
# corner interior angles of the chord quadrilateral
qa = []
for q in range(4):
    a = np.array(corners[(q - 1) % 4]) - np.array(corners[q])
    b = np.array(corners[(q + 1) % 4]) - np.array(corners[q])
    qa.append(math.degrees(math.acos(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))))
res["square"]["chord_quad_interior_angles_deg"] = [round(v, 3) for v in qa]
sag_fit = [s["sagitta_from_arc_px"] for s in side_res]
sag_dir = [s["sagitta_direct_max_px"] for s in side_res]
radii = [s["arc_radius_px"] for s in side_res]

# ---------------------------------------------------------------- tip angles
tip = []
for q in range(4):
    a = fits[(q - 1) % 4]; b = fits[q]
    P = np.array(corners[q])
    # tangent directions pointing away from corner along each side
    def tangent(fit, towards):
        rvec = P - np.array([fit[0], fit[1]])
        tvec = np.array([-rvec[1], rvec[0]]); tvec /= np.linalg.norm(tvec)
        if np.dot(tvec, np.array(towards) - P) < 0: tvec = -tvec
        return tvec
    ta = tangent(a, corners[(q - 1) % 4]); tb = tangent(b, corners[(q + 1) % 4])
    ang_arc = math.degrees(math.acos(np.clip(np.dot(ta, tb), -1, 1)))
    # line fits to boundary points 15..70 px from the corner along each side
    angs = {}
    for lo_, hi_ in ((10, 50), (15, 70), (20, 100)):
        dirs = []
        for nb in ((q - 1) % 4, (q + 1) % 4):
            if nb == (q - 1) % 4:
                X, Y, _ = pts_between(maxima[nb], maxima[q])
            else:
                X, Y, _ = pts_between(maxima[q], maxima[nb])
            dd = np.hypot(X - P[0], Y - P[1])
            s = (dd > lo_) & (dd < hi_)
            (mx, my), (ux, uy), rms = fit_line(X[s], Y[s])
            v = np.array([ux, uy])
            if np.dot(v, np.array([mx, my]) - P) < 0: v = -v
            dirs.append(v)
        angs["%d-%dpx" % (lo_, hi_)] = round(math.degrees(math.acos(np.clip(np.dot(dirs[0], dirs[1]), -1, 1))), 2)
    tip.append({"corner": q, "xy": [round(P[0], 1), round(P[1], 1)],
                "angle_arc_tangents_deg": round(ang_arc, 2), "angle_line_fits_deg": angs})
res["tip_angles"] = tip

# ---------------------------------------------------------------- hole
# rough hole centre: bright neutral pixels inside the filled silhouette
hb = filled & (L > 0.55) & (np.abs(rgb[..., 0] - rgb[..., 2]) < 0.05)
hl, hsz = label(hb)
ks = int(np.argmax(hsz[1:]) + 1)
hys, hxs = np.nonzero(hl == ks)
hcx, hcy = hxs.mean(), (hys.min() + hys.max()) / 2.0
NH = 3600
phis = np.deg2rad(np.arange(NH) * 0.1)
rsH, LpH = ray_profiles(hcx, hcy, phis, 5, 200, STEP, L.astype(np.float64))
LsH = gsmooth1d(LpH, 0.75 / STEP)
dLH = np.gradient(LsH, axis=1) / STEP
r_h = np.full(NH, np.nan); kind = np.zeros(NH, int)
for i in range(NH):
    prof = LsH[i]
    lid = np.median(prof[(rsH > 20) & (rsH < 60)])
    js = np.nonzero(prof < 0.85 * lid)[0]
    js = js[rsH[js] > 30]
    if len(js) == 0: continue
    j0 = js[0]
    j1 = min(j0 + int(30 / STEP), len(rsH) - 2)
    seg = prof[j0:j1]; dseg = dLH[i, j0:j1]
    down = math.sin(phis[i]) > 0.25  # ray heads toward the image-bottom side, where the shadow band is
    if down and seg.min() < 0.16:
        jmin = int(np.argmin(seg))
        # steepest ascent after the dark minimum
        kk = jmin + int(np.argmax(dseg[jmin:])) if jmin < len(dseg) - 1 else jmin
        kind[i] = 2
    else:
        mneg = -dseg
        thr = 0.6 * mneg.max()
        cand = np.nonzero(mneg >= thr)[0]
        # first local peak at/after first candidate
        kk = cand[0]
        while kk + 1 < len(mneg) and mneg[kk + 1] > mneg[kk]:
            kk += 1
        kind[i] = 1
    k = j0 + kk
    a, b, c = dLH[i, k - 1], dLH[i, k], dLH[i, k + 1]
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    off = max(-1, min(1, off))
    r_h[i] = rsH[k] + off * STEP
hx = hcx + r_h * np.cos(phis); hy = hcy + r_h * np.sin(phis)
# shadow band inner (top) edge along the bottom side, for reporting
# assign points to sides by angle relative to hole centre
ang = (np.rad2deg(phis) + 360) % 360
secs = {"right": (ang > 330) | (ang < 30), "bottom": (ang > 60) & (ang < 120),
        "left": (ang > 150) & (ang < 210), "top": (ang > 240) & (ang < 300)}
hlines = {}
for nm, s in secs.items():
    s = s & np.isfinite(r_h)
    X, Y = hx[s], hy[s]
    for _ in range(3):
        (mx, my), (ux, uy), rms = fit_line(X, Y)
        nn = np.array([-uy, ux])
        rr_ = (X - mx) * nn[0] + (Y - my) * nn[1]
        keep = np.abs(rr_) < max(3 * rms, 1.0)
        X, Y = X[keep], Y[keep]
    (mx, my), (ux, uy), rms = fit_line(X, Y)
    hlines[nm] = ((mx, my), (ux, uy), rms, len(X))
hc = {}
for a_, b_ in (("top", "left"), ("top", "right"), ("bottom", "left"), ("bottom", "right")):
    hc[a_ + "_" + b_] = line_intersect(hlines[a_][0], hlines[a_][1], hlines[b_][0], hlines[b_][1])
hs = {"top": math.dist(hc["top_left"], hc["top_right"]), "bottom": math.dist(hc["bottom_left"], hc["bottom_right"]),
      "left": math.dist(hc["top_left"], hc["bottom_left"]), "right": math.dist(hc["top_right"], hc["bottom_right"])}
hcen = np.mean([hc[k] for k in hc], axis=0)
def line_heading(u):
    a = math.degrees(math.atan2(u[1], u[0]))
    while a > 45: a -= 90
    while a <= -45: a += 90
    return a
hole_head = {nm: round(line_heading(hlines[nm][1]), 3) for nm in hlines}
outer_head = [s["chord_heading_deg"] for s in side_res]
outer_head_n = []
for a in outer_head:
    while a > 45: a -= 90
    while a <= -45: a += 90
    outer_head_n.append(a)
# fillet: along ray from hole centre through each virtual corner
fil = {}
for kname, P in hc.items():
    phi = math.atan2(P[1] - hcy, P[0] - hcx)
    i = int(round(math.degrees(phi) * 10)) % NH
    win = [(i + o) % NH for o in range(-3, 4)]
    rr_c = np.nanmedian(r_h[win])
    gap = math.hypot(P[0] - hcx, P[1] - hcy) - rr_c
    # circle fit to points near the corner that deviate from both lines by > 1px
    near = np.hypot(hx - P[0], hy - P[1]) < 40
    dev = []
    for nm in kname.split("_"):
        (mx, my), (ux, uy), _, _ = hlines[nm]
        nn = np.array([-uy, ux])
        dev.append(np.abs((hx - mx) * nn[0] + (hy - my) * nn[1]))
    sel = near & (dev[0] > 1.0) & (dev[1] > 1.0) & np.isfinite(hx)
    cf = None
    if sel.sum() >= 5:
        fx, fy, fr, frms = fit_circle(hx[sel], hy[sel])
        cf = {"radius_px": round(fr, 2), "rms_px": round(frms, 2), "n": int(sel.sum())}
    fil[kname] = {"gap_along_ray_px": round(gap, 2), "radius_from_gap_px": round(gap / (math.sqrt(2) - 1), 2),
                  "circle_fit": cf}
# shadow band: along the bottom side, first steep descent (lid -> shadow) vs plate edge
sb = []
for i in np.nonzero(secs["bottom"])[0]:
    prof = LsH[i]
    lid = np.median(prof[(rsH > 20) & (rsH < 60)])
    js = np.nonzero(prof < 0.85 * lid)[0]; js = js[rsH[js] > 30]
    if len(js) == 0 or not np.isfinite(r_h[i]): continue
    j0 = js[0]; j1 = j0 + int(30 / STEP)
    k = j0 + int(np.argmin(dLH[i, j0:j1]))
    sb.append(r_h[i] - rsH[k])
res["hole"] = {
    "centre_from_corners_px": [round(hcen[0], 2), round(hcen[1], 2)],
    "corners_px": {k: [round(v[0], 2), round(v[1], 2)] for k, v in hc.items()},
    "side_lengths_px": {k: round(v, 2) for k, v in hs.items()},
    "side_mean_px": round(float(np.mean(list(hs.values()))), 2),
    "width_over_height": round((hs["top"] + hs["bottom"]) / (hs["left"] + hs["right"]), 4),
    "line_heading_deg_mod90": hole_head,
    "line_fit_rms_px": {k: round(v[2], 3) for k, v in hlines.items()},
    "line_fit_n": {k: int(v[3]) for k, v in hlines.items()},
    "fillet": fil,
    "shadow_band_bottom_width_px_median": round(float(np.median(sb)), 2) if sb else None,
    "shadow_band_bottom_width_px_p10_p90": np.percentile(sb, [10, 90]).round(2).tolist() if sb else None,
    "edge_rule": "rays from hole centre; lid->plate steepest descent (first peak >=60% of max) within 30px after L<0.85*lid; for rays toward the image bottom whose window reaches L<0.16 the plate edge is the steepest ascent after the dark minimum (shadow band counted as opening)",
}
res["outer_heading_deg_mod90"] = [round(a, 3) for a in outer_head_n]

# ---------------------------------------------------------------- bevel band per side
bev = {}
for q, s in enumerate(side_res):
    fcx, fcy, R = fits[q][0], fits[q][1], fits[q][2]
    P0 = np.array(corners[q]); P1 = np.array(corners[(q + 1) % 4])
    ch = P1 - P0; c = np.linalg.norm(ch); u = ch / c
    X, Y, idx = pts_between(maxima[q], maxima[(q + 1) % 4])
    t = ((X - P0[0]) * u[0] + (Y - P0[1]) * u[1]) / c
    stations = np.arange(0.03, 0.975, 0.01)
    widths = []; prof_acc = []; used_t = []
    ns = np.arange(-10, 45, 0.5)
    for tt in stations:
        j = int(np.argmin(np.abs(t - tt)))
        Px, Py = X[j], Y[j]
        nv = np.array([Px - fcx, Py - fcy]); nv /= np.linalg.norm(nv)   # inward (away from arc centre)
        if np.dot(nv, np.array([cx - Px, cy - Py])) < 0: nv = -nv
        tv = np.array([-nv[1], nv[0]])
        acc = np.zeros(len(ns))
        offs = np.arange(-4, 4.01, 1.0)
        for o in offs:
            acc += bilinear(L.astype(np.float64), Px + ns * nv[0] + o * tv[0], Py + ns * nv[1] + o * tv[1])
        acc /= len(offs)
        prof_acc.append(acc); used_t.append(tt)
    prof_acc = np.array(prof_acc)
    ps = gsmooth1d(prof_acc, 2.0)          # 1 px smoothing
    dP = np.gradient(ps, axis=1) / 0.5
    body = np.median(ps[:, (ns > 32) & (ns < 44)], axis=1)
    band = np.median(ps[:, (ns > 3) & (ns < 8)], axis=1)
    bright = np.median(band - body) > 0
    win = (ns > 5) & (ns < 35)
    wi = np.nonzero(win)[0]
    for r_ in range(len(stations)):
        # smooth along side over +-2 stations
        lo, hi = max(0, r_ - 2), min(len(stations), r_ + 3)
        g = dP[lo:hi].mean(0)
        k = wi[int(np.argmin(g[wi]))] if bright else wi[int(np.argmax(g[wi]))]
        widths.append(float(ns[k]))
    widths = np.array(widths)
    mid = (stations > 0.15) & (stations < 0.85)
    ends = (stations < 0.10) | (stations > 0.90)
    avgp = ps[mid].mean(0)
    bev[s["name"]] = {
        "band_tone": "lighter than body" if bright else "darker than body",
        "band_minus_body_L_median": round(float(np.median(band - body)), 3),
        "width_px_median_mid70pct": round(float(np.median(widths[mid])), 2),
        "width_px_p10_p90_mid70pct": np.percentile(widths[mid], [10, 90]).round(2).tolist(),
        "width_px_median_end10pct": round(float(np.median(widths[ends])), 2),
        "width_px_by_station_every5pct": [round(float(widths[i]), 1) for i in range(0, len(stations), 5)],
        "stations_every5pct": [round(float(stations[i]), 2) for i in range(0, len(stations), 5)],
        "band_contrast_by_station_every5pct": [round(float(band[i] - body[i]), 3) for i in range(0, len(stations), 5)],
        "avg_profile_mid70_L_every1px_from_-4": [round(float(v), 3) for v in avgp[(ns >= -4) & (np.abs(ns - np.round(ns)) < 1e-6)]],
    }
    s["_bevel_widths"] = widths.tolist(); s["_stations"] = stations.tolist()
res["bevel"] = bev

# ---------------------------------------------------------------- summary ratios
tip_to_tip = float(np.mean(diag))
res["summary"] = {
    "adjacent_corner_px": round(adj, 2),
    "corner_to_corner_px": round(tip_to_tip, 2),
    "sagitta_arc_mean_px": round(float(np.mean(sag_fit)), 2), "sagitta_arc_sd_px": round(float(np.std(sag_fit)), 2),
    "sagitta_direct_mean_px": round(float(np.mean(sag_dir)), 2), "sagitta_direct_sd_px": round(float(np.std(sag_dir)), 2),
    "sagitta_over_chord_arc": [round(sf / s["chord_px"], 4) for sf, s in zip(sag_fit, side_res)],
    "sagitta_over_chord_mean": round(float(np.mean([sf / s["chord_px"] for sf, s in zip(sag_fit, side_res)])), 4),
    "arc_radius_over_side": [round(r / adj, 3) for r in radii],
    "arc_radius_over_side_mean": round(float(np.mean(radii)) / adj, 3),
    "hole_side_over_outer_side": round(res["hole"]["side_mean_px"] / adj, 4),
    "hole_side_over_corner_to_corner": round(res["hole"]["side_mean_px"] / tip_to_tip, 4),
    "hole_centre_offset_from_outer_diag_intersection_px": [round(hcen[0] - dix, 2), round(hcen[1] - diy, 2)],
    "hole_centre_offset_over_side": round(math.hypot(hcen[0] - dix, hcen[1] - diy) / adj, 4),
    "hole_centre_offset_from_polygon_centroid_px": [round(hcen[0] - cx, 2), round(hcen[1] - cy, 2)],
    "hole_rotation_vs_outer_deg": round(float(np.mean(list(hole_head.values())) - np.mean(outer_head_n)), 3),
    "tip_angle_arc_mean_deg": round(float(np.mean([t_["angle_arc_tangents_deg"] for t_ in tip])), 2),
    "tip_angle_arc_sd_deg": round(float(np.std([t_["angle_arc_tangents_deg"] for t_ in tip])), 2),
}

# ---------------------------------------------------------------- mask
yy, xx = np.mgrid[0:H, 0:W]
th = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
rho = np.hypot(xx - cx, yy - cy)
rb_ = np.interp(th.ravel(), np.r_[np.arange(NT) * 0.1, 360.0], np.r_[r_out, r_out[0]]).reshape(H, W)
inside = rho <= rb_
rhf = r_h.copy()
bad = ~np.isfinite(rhf)
if bad.any():
    rhf[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], rhf[~bad])
thh = (np.degrees(np.arctan2(yy - hcy, xx - hcx)) + 360) % 360
rhoh = np.hypot(xx - hcx, yy - hcy)
rhb = np.interp(thh.ravel(), np.r_[np.arange(NH) * 0.1, 360.0], np.r_[rhf, rhf[0]]).reshape(H, W)
hole_in = rhoh <= rhb
mask = inside & ~hole_in
save_png(mask.astype(np.float32), OUT + "senban_mask.png")
res["mask"] = {"plate_px": int(mask.sum()), "hole_px": int((inside & hole_in).sum()),
               "hole_area_over_side_sq": round(float((inside & hole_in).sum()) / (res["hole"]["side_mean_px"] ** 2), 4)}

# ---------------------------------------------------------------- overlay
ov = rgb * 0.75
def put(x, y, col, r=0):
    x = np.atleast_1d(np.round(x).astype(int)); y = np.atleast_1d(np.round(y).astype(int))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            xx_ = np.clip(x + dx, 0, W - 1); yy_ = np.clip(y + dy, 0, H - 1)
            ov[yy_, xx_] = col
# threshold boundary (blue) and refined boundary (green)
put(cx + r_thr * np.cos(thetas), cy + r_thr * np.sin(thetas), (0.2, 0.4, 1.0))
put(bx, by, (0.1, 1.0, 0.1))
# fitted arcs (cyan) between corners
for q in range(4):
    fcx, fcy, R = fits[q][0], fits[q][1], fits[q][2]
    P0 = corners[q]; P1 = corners[(q + 1) % 4]
    a0 = math.atan2(P0[1] - fcy, P0[0] - fcx); a1 = math.atan2(P1[1] - fcy, P1[0] - fcx)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    aa = a0 + np.linspace(0, 1, 2000) * da
    put(fcx + R * np.cos(aa), fcy + R * np.sin(aa), (0.0, 1.0, 1.0))
    # chord (yellow)
    tt = np.linspace(0, 1, 2000)
    put(P0[0] + tt * (P1[0] - P0[0]), P0[1] + tt * (P1[1] - P0[1]), (1.0, 1.0, 0.0))
# diagonals (dim yellow)
for a_, b_ in ((0, 2), (1, 3)):
    tt = np.linspace(0, 1, 3000)
    put(corners[a_][0] + tt * (corners[b_][0] - corners[a_][0]), corners[a_][1] + tt * (corners[b_][1] - corners[a_][1]), (0.6, 0.6, 0.0))
# bevel inner edge (orange)
for q, s in enumerate(side_res):
    fcx, fcy = fits[q][0], fits[q][1]
    X, Y, idx = pts_between(maxima[q], maxima[(q + 1) % 4])
    P0 = np.array(corners[q]); P1 = np.array(corners[(q + 1) % 4])
    ch = P1 - P0; c = np.linalg.norm(ch); u = ch / c
    t = ((X - P0[0]) * u[0] + (Y - P0[1]) * u[1]) / c
    for tt, wv in zip(s["_stations"], s["_bevel_widths"]):
        j = int(np.argmin(np.abs(t - tt)))
        nv = np.array([X[j] - fcx, Y[j] - fcy]); nv /= np.linalg.norm(nv)
        if np.dot(nv, np.array([cx - X[j], cy - Y[j]])) < 0: nv = -nv
        put(X[j] + wv * nv[0], Y[j] + wv * nv[1], (1.0, 0.5, 0.0), 1)
    del s["_bevel_widths"]; del s["_stations"]
# hole edge points (magenta), lines (red)
put(hx[kind == 1], hy[kind == 1], (1.0, 0.0, 1.0))
put(hx[kind == 2], hy[kind == 2], (1.0, 0.3, 0.3))
for nm, ((mx, my), (ux, uy), rms, n) in hlines.items():
    tt = np.linspace(-150, 150, 1200)
    put(mx + tt * ux, my + tt * uy, (1.0, 0.0, 0.0))
# corners (red), centres
for P in corners:
    put(P[0], P[1], (1.0, 0.0, 0.0), 3)
put(cx, cy, (0.1, 1.0, 0.1), 3)
put(dix, diy, (1.0, 1.0, 0.0), 2)
put(hcen[0], hcen[1], (1.0, 0.0, 1.0), 2)
save_png(ov, OUT + "senban_overlay.png")
# zoomed overlay crops
def zoom(a, x0, y0, x1, y1, S):
    c = a[y0:y1, x0:x1]
    return np.repeat(np.repeat(c, S, 0), S, 1)
save_png(zoom(ov, 360, 330, 650, 620, 3), OUT + "senban_overlay_hole.png")
for q, P in enumerate(corners):
    x0 = int(P[0]) - 50; y0 = int(P[1]) - 50
    x0 = max(0, min(W - 100, x0)); y0 = max(0, min(H - 100, y0))
    save_png(zoom(ov, x0, y0, x0 + 100, y0 + 100, 5), OUT + "senban_overlay_corner%d.png" % q)

json.dump(res, open(OUTJ, "w"), indent=1)
print("WROTE", OUTJ)
print(json.dumps(res["summary"], indent=1))
