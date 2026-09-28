"""Per-side scanline edge detection (perpendicular to each chord), to cross-check the radial r(theta)
boundary near the tips where radial rays graze the edge. Writes senban_sides.json + overlays."""
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

R0 = json.load(open(OUT + "senban_radial.json"))
rgb = load_rgb()
H, W, _ = rgb.shape
L = rgb.mean(-1).astype(np.float64)
mu = np.array(R0["image"]["bg_rgb_mean"])
D = np.sqrt(((rgb - mu) ** 2).sum(-1)).astype(np.float64)
cx, cy = R0["outer_boundary"]["centre_polygon_centroid"]
corners0 = [tuple(p) for p in R0["corners_virtual_px"]]
names = [s["name"] for s in R0["sides"]]


def bilinear(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def gs(a, s):
    r = int(3 * s) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    p = np.pad(a, ((0, 0), (r, r)), mode='edge')
    o = np.zeros_like(a)
    for i, kv in enumerate(k):
        o += kv * p[:, i:i + a.shape[1]]
    return o


STEP = 0.25
T = 0.25
out = {"sides": {}}
edge_pts = {}
for q in range(4):
    P0 = np.array(corners0[q]); P1 = np.array(corners0[(q + 1) % 4])
    ch = P1 - P0; c = np.linalg.norm(ch); u = ch / c
    n = np.array([-u[1], u[0]])
    if np.dot(np.array([cx, cy]) - (P0 + P1) / 2, n) < 0: n = -n
    ss = np.arange(0.0, c + 0.01, 1.0)           # position along chord, px
    ns = np.arange(-25, 130, STEP)                # inward depth
    Lp = np.zeros((len(ss), len(ns))); Dp = np.zeros_like(Lp)
    for o in (-1.0, 0.0, 1.0):
        X = P0[0] + (ss[:, None] + o) * u[0] + ns[None, :] * n[0]
        Y = P0[1] + (ss[:, None] + o) * u[1] + ns[None, :] * n[1]
        Lp += bilinear(L, X, Y) / 3; Dp += bilinear(D, X, Y) / 3
    Ls = gs(Lp, 1.0 / STEP)
    dL = np.gradient(Ls, axis=1) / STEP
    depth = np.full(len(ss), np.nan); dthr = np.full(len(ss), np.nan)
    for i in range(len(ss)):
        above = np.nonzero(Dp[i] > T)[0]
        if len(above) == 0: continue
        j0 = above[0]                              # first plate sample going inward
        if j0 == 0: continue
        dthr[i] = ns[j0]
        lo = max(j0 - int(4 / STEP), 1); hi = min(j0 + int(16 / STEP), len(ns) - 2)
        k = lo + int(np.argmin(dL[i, lo:hi]))      # steepest drop of L going inward (lid -> plate)
        a, b, cc = dL[i, k - 1], dL[i, k], dL[i, k + 1]
        den = a - 2 * b + cc
        off = 0.5 * (a - cc) / den if abs(den) > 1e-12 else 0.0
        depth[i] = ns[k] + max(-1, min(1, off)) * STEP
    t = ss / c
    ok = np.isfinite(depth)
    X = P0[0] + ss * u[0] + depth * n[0]; Y = P0[1] + ss * u[1] + depth * n[1]
    edge_pts[q] = (t, ss, depth, X, Y, u, n, P0, c, dthr)
    out["sides"][names[q]] = {"chord_px_input": round(c, 2), "valid": int(ok.sum()), "n": int(len(ss))}

# --- fit circles on t in [0.1,0.9]; residual profile; also fit on [0.25,0.75]
fits = {}
for q in range(4):
    t, ss, depth, X, Y, u, n, P0, c, dthr = edge_pts[q]
    res_ = {}
    for lo, hi in ((0.1, 0.9), (0.2, 0.8), (0.3, 0.7)):
        s = (t > lo) & (t < hi) & np.isfinite(depth)
        fcx, fcy, R, rms = fit_circle(X[s], Y[s])
        res_["%.1f-%.1f" % (lo, hi)] = {"R": round(R, 1), "rms": round(rms, 3), "centre": [round(fcx, 1), round(fcy, 1)]}
        if lo == 0.1:
            fits[q] = (fcx, fcy, R)
    # residual profile vs the 0.1-0.9 circle, every 0.05
    fcx, fcy, R = fits[q]
    resid = np.hypot(X - fcx, Y - fcy) - R
    prof = []
    for tt in np.arange(0.0, 1.001, 0.025):
        s = (np.abs(t - tt) < 0.0125) & np.isfinite(depth)
        prof.append([round(float(tt), 3), round(float(np.nanmedian(depth[s])), 2) if s.any() else None,
                     round(float(np.nanmedian(resid[s])), 2) if s.any() else None])
    out["sides"][names[q]]["circle_fits"] = res_
    out["sides"][names[q]]["t_depth_resid_vs_circle_0.1-0.9"] = prof
    # smooth-depth profile features: max depth, t at max
    s = np.isfinite(depth) & (t > 0.02) & (t < 0.98)
    dd = depth[s]; tt = t[s]
    k = 10
    dsm = np.convolve(np.r_[dd[:k][::-1], dd, dd[-k:][::-1]], np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    j = int(np.argmax(dsm))
    out["sides"][names[q]]["max_depth_from_input_chord_px"] = round(float(dsm[j]), 2)
    out["sides"][names[q]]["t_at_max_depth"] = round(float(tt[j]), 3)
    # polynomial (even+odd) fit depth(t) degree 4 on [0.03,0.97]
    s2 = np.isfinite(depth) & (t > 0.03) & (t < 0.97)
    pc = np.polyfit(t[s2], depth[s2], 4)
    out["sides"][names[q]]["poly4_rms"] = round(float(np.sqrt(np.mean((np.polyval(pc, t[s2]) - depth[s2]) ** 2))), 3)

# --- local tip: fit lines to each side's edge points within 8..45 px (along chord) of the tip,
#     intersect them; compare with the extreme plate point along the corner direction.
tips = []
for q in range(4):
    qa = (q - 1) % 4   # side ending at corner q
    qb = q             # side starting at corner q
    ta, ssa, da, Xa, Ya, ua, na, P0a, ca, _ = edge_pts[qa]
    tb, ssb, db, Xb, Yb, ub, nb, P0b, cb, _ = edge_pts[qb]
    angs = {}
    local = None
    for lo, hi in ((8, 40), (15, 60), (20, 100), (40, 150)):
        sa = (ca - ssa > lo) & (ca - ssa < hi) & np.isfinite(da)
        sb = (ssb > lo) & (ssb < hi) & np.isfinite(db)
        (m1x, m1y), (u1x, u1y), r1 = fit_line(Xa[sa], Ya[sa])
        (m2x, m2y), (u2x, u2y), r2 = fit_line(Xb[sb], Yb[sb])
        ix, iy = line_intersect((m1x, m1y), (u1x, u1y), (m2x, m2y), (u2x, u2y))
        v1 = np.array([m1x - ix, m1y - iy]); v1 /= np.linalg.norm(v1)
        v2 = np.array([m2x - ix, m2y - iy]); v2 /= np.linalg.norm(v2)
        ang = math.degrees(math.acos(np.clip(np.dot(v1, v2), -1, 1)))
        angs["%d-%dpx" % (lo, hi)] = {"angle_deg": round(ang, 2), "apex": [round(ix, 2), round(iy, 2)],
                                      "line_rms": [round(r1, 3), round(r2, 3)]}
        if lo == 15: local = (ix, iy, v1, v2)
    # extreme plate point along bisector direction (outward), low threshold D>0.15 and D>0.25
    ix, iy, v1, v2 = local
    bis = -(v1 + v2); bis /= np.linalg.norm(bis)
    ext = {}
    for thr in (0.15, 0.25, 0.35):
        best = None
        for off in np.arange(-3, 3.01, 0.5):
            perp = np.array([-bis[1], bis[0]])
            rr = np.arange(-40, 30, 0.25)
            xs = ix + rr * bis[0] + off * perp[0]; ys = iy + rr * bis[1] + off * perp[1]
            dv = bilinear(D, xs, ys)
            inside = np.nonzero(dv > thr)[0]
            if len(inside) == 0: continue
            rmax = rr[inside[-1]]
            if best is None or rmax > best: best = rmax
        ext["D>%.2f" % thr] = round(float(best), 2) if best is not None else None
    tips.append({"corner": q, "local_line_fits": angs, "extreme_plate_along_bisector_rel_apex_px": ext,
                 "bisector": [round(bis[0], 4), round(bis[1], 4)]})
out["tips"] = tips
json.dump(out, open(OUT + "senban_sides.json", "w"), indent=1)

# overlay of scanline edges
ov = rgb * 0.75
def put(x, y, col, r=0):
    x = np.atleast_1d(np.round(x).astype(int)); y = np.atleast_1d(np.round(y).astype(int))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ov[np.clip(y + dy, 0, H - 1), np.clip(x + dx, 0, W - 1)] = col
for q in range(4):
    t, ss, depth, X, Y, u, n, P0, c, dthr = edge_pts[q]
    ok = np.isfinite(depth)
    put(X[ok], Y[ok], (0.1, 1.0, 0.1))
    fcx, fcy, R = fits[q]
    aa = np.linspace(0, 2 * np.pi, 40000)
    xx = fcx + R * np.cos(aa); yy = fcy + R * np.sin(aa)
    s = (xx > -5) & (xx < W + 5) & (yy > -5) & (yy < H + 5)
    put(xx[s], yy[s], (0.0, 0.8, 1.0))
for tp in tips:
    a = tp["local_line_fits"]["15-60px"]["apex"]
    put(a[0], a[1], (1, 0, 0), 1)
def zoom(a, x0, y0, x1, y1, S):
    return np.repeat(np.repeat(a[y0:y1, x0:x1], S, 0), S, 1)
save_png(ov, OUT + "senban_overlay_sides.png")
for q in range(4):
    a = tips[q]["local_line_fits"]["15-60px"]["apex"]
    x0 = max(0, min(W - 80, int(a[0]) - 40)); y0 = max(0, min(H - 80, int(a[1]) - 40))
    save_png(zoom(ov, x0, y0, x0 + 80, y0 + 80, 6), OUT + "senban_sides_tip%d.png" % q)
print(json.dumps(out, indent=0)[:6000])
