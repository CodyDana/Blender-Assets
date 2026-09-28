"""Stage 3: radial-profile measurement of the roppo silhouette.

blender -b --factory-startup --python s3_radial.py -- <photo> <outdir> <tag e.g. T65> [overlay 0/1]
Needs solid_<tag>.npy / holes_<tag>.npy / t.npy / chx.npy from s2_mask.py.
Image coordinates: x right, y down. Polar angle theta: 0 deg = +x, counter-clockwise AS SEEN
(theta = atan2(-(y-cy), x-cx)).
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir, tag = argv[0], argv[1], argv[2]
do_overlay = len(argv) > 3 and argv[3] == "1"
T = int(tag[1:]) / 100.0

rgb = imgio.load_rgb(photo).astype(np.float64)
H, W, _ = rgb.shape
lum = rgb.mean(2)
chroma = rgb.max(2) - rgb.min(2)
solid = np.load(os.path.join(outdir, f"solid_{tag}.npy"))
holes = np.load(os.path.join(outdir, f"holes_{tag}.npy"))
tf = np.load(os.path.join(outdir, "t.npy")).astype(np.float64)
sil = solid | holes
R = {}


def boundary(m):
    """pixels of m with a 4-neighbour outside m (image border counts as outside)."""
    p = np.pad(m, 1, constant_values=False)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner


def fit_circle(x, y, iters=30):
    A = np.stack([x, y, np.ones_like(x)], 1)
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0] / 2, c[1] / 2
    r = math.sqrt(c[2] + cx * cx + cy * cy)
    for _ in range(iters):  # Gauss-Newton geometric refinement
        dx, dy = x - cx, y - cy
        d = np.sqrt(dx * dx + dy * dy)
        res = d - r
        J = np.stack([-dx / d, -dy / d, -np.ones_like(d)], 1)
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx += step[0]; cy += step[1]; r += step[2]
        if np.abs(step).max() < 1e-6:
            break
    res = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - r
    return cx, cy, r, float(np.sqrt((res ** 2).mean())), res


def fit_line(px, py):
    """total least squares. returns (point, unit dir, rms, signed residuals)."""
    mx, my = px.mean(), py.mean()
    M = np.stack([px - mx, py - my], 1)
    _, s, vt = np.linalg.svd(M, full_matrices=False)
    d = vt[0]
    n = np.array([-d[1], d[0]])
    res = M @ n
    return np.array([mx, my]), d, float(np.sqrt((res ** 2).mean())), res


def line_intersect(p1, d1, p2, d2):
    A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
    s = np.linalg.solve(A, p2 - p1)
    return p1 + s[0] * d1


def line_circle(p, d, cx, cy, r):
    """intersections of line p + s d with circle; returns list of points."""
    fx, fy = p[0] - cx, p[1] - cy
    b = 2 * (fx * d[0] + fy * d[1]); c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * c
    if disc < 0:
        return []
    sq = math.sqrt(disc)
    return [p + ((-b - sq) / 2) * d, p + ((-b + sq) / 2) * d]


def theta_of(x, y, cx, cy):
    return np.degrees(np.arctan2(-(y - cy), x - cx)) % 360.0


def angdiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0

# ------------------------------------------------------------------ centres
ys, xs = np.nonzero(sil)
cen_sil = (float(xs.mean()), float(ys.mean()))
hb = boundary(holes)
hy, hx = np.nonzero(hb)
hx = hx.astype(float); hy = hy.astype(float)
hcx, hcy, hr, hrms, hres = fit_circle(hx, hy)
# crisp half of the hole rim (top + right: the scanner shadow falls up/right, so the
# hole rim's left + bottom sides are the soft ones)
phi = np.degrees(np.arctan2(hy - hcy, hx - hcx))  # image-y-down angle
crisp = np.sin(np.radians(phi)) < np.cos(np.radians(phi))
ccx, ccy, cr, crms, _ = fit_circle(hx[crisp], hy[crisp])
# roundness: fit an ellipse-ish measure via radial residual spread and max-min radius
hd = np.sqrt((hx - hcx) ** 2 + (hy - hcy) ** 2)
# diameter in several directions (through fitted centre) from the hole mask
dia_dirs = {}
for ang in range(0, 180, 15):
    a = math.radians(ang)
    dx, dy = math.cos(a), -math.sin(a)
    tot = 0.0
    for sgn in (1, -1):
        s = 0.0
        while True:
            xi = int(round(hcx + sgn * s * dx)); yi = int(round(hcy + sgn * s * dy))
            if not holes[yi, xi]:
                break
            s += 0.25
        tot += s
    dia_dirs[ang] = tot
dvals = np.array(list(dia_dirs.values()))
R["centres"] = {
    "silhouette_centroid": cen_sil,
    "hole_fit_all": [hcx, hcy], "hole_fit_crisp_half": [ccx, ccy],
}
R["hole_px"] = {"r_fit_all": hr, "rms_all": hrms, "r_fit_crisp_half": cr, "rms_crisp": crms,
                "r_min_rim": float(hd.min()), "r_max_rim": float(hd.max()),
                "diam_by_dir_deg": dia_dirs, "diam_max_over_min": float(dvals.max() / dvals.min()),
                "area_px": int(holes.sum()), "equiv_diam": float(2 * math.sqrt(holes.sum() / math.pi))}

cx, cy = hcx, hcy   # polar origin = hole circle centre (all rim points)

# ------------------------------------------------------------------ r(theta)
thetas = np.arange(0, 360, 0.1)
rs = np.arange(0, 820, 0.25)
TH = np.radians(thetas)[:, None]
X = cx + rs[None, :] * np.cos(TH)
Y = cy - rs[None, :] * np.sin(TH)
inside_img = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= H - 1)
Xi = np.clip(np.round(X).astype(int), 0, W - 1)
Yi = np.clip(np.round(Y).astype(int), 0, H - 1)
S = sil[Yi, Xi] & inside_img
idx_last = S.shape[1] - 1 - np.argmax(S[:, ::-1], axis=1)
r_out = rs[idx_last] + 0.125
# ray clipped by image frame: the sample just beyond the last inside sample is outside the image
nxt = np.minimum(idx_last + 1, S.shape[1] - 1)
clipped = ~inside_img[np.arange(len(thetas)), nxt]
# inner (hole) radius: first solid sample from the centre
Ssol = solid[Yi, Xi] & inside_img
r_in = rs[np.argmax(Ssol, axis=1)]
np.save(os.path.join(outdir, f"rtheta_{tag}.npy"), np.stack([thetas, r_out, r_in, clipped], 1))

# periodicity
rr = r_out - r_out.mean()
F = np.abs(np.fft.rfft(rr)) / len(rr) * 2
harm = {int(k): float(F[k]) for k in range(1, 19)}
dom = int(np.argmax(F[1:40]) + 1)
R["periodicity"] = {"dominant_harmonic": dom, "amplitudes_px": harm}

# tips: local maxima with separation
def smooth(v, n):
    k = np.ones(n) / n
    return np.convolve(np.concatenate([v[-n:], v, v[:n]]), k, mode="same")[n:-n]

rsm = smooth(r_out, 5)
order = np.argsort(-rsm)
tips = []
for i in order:
    if all(abs(angdiff(thetas[i], thetas[j])) > 30 for j in tips):
        tips.append(i)
    if len(tips) == 6:
        break
tips = sorted(tips, key=lambda i: thetas[i])
# refine: farthest raw boundary pixel within +-4 deg
ob = boundary(sil)
oy, ox = np.nonzero(ob)
ox = ox.astype(float); oy = oy.astype(float)
oth = theta_of(ox, oy, cx, cy)
orad = np.sqrt((ox - cx) ** 2 + (oy - cy) ** 2)
tip_info = []
for i in tips:
    sel = np.abs(angdiff(oth, thetas[i])) < 4
    j = np.argmax(np.where(sel, orad, -1))
    near_frame = (ox[j] <= 1 or oy[j] <= 1 or ox[j] >= W - 2 or oy[j] >= H - 2)
    tip_info.append({"theta": float(oth[j]), "r": float(orad[j]), "x": float(ox[j]), "y": float(oy[j]),
                     "clipped_by_frame": bool(near_frame or clipped[max(0, i - 20):i + 20].any())})
R["tips_raw"] = tip_info

# minima between consecutive tips
mins = []
for k in range(6):
    a = tips[k]; b = tips[(k + 1) % 6]
    idx = np.arange(a, b if b > a else b + len(thetas)) % len(thetas)
    j = idx[np.argmin(r_out[idx])]
    mins.append({"theta": float(thetas[j]), "r": float(r_out[j])})
R["minima_between_tips"] = mins

# hub arc: flat part of r(theta) in each gap
dr = np.gradient(smooth(r_out, 9), 0.1)  # px per degree
hub_pts_x, hub_pts_y, gaps = [], [], []
for k in range(6):
    a = tips[k]; b = tips[(k + 1) % 6]
    idx = np.arange(a, b if b > a else b + len(thetas)) % len(thetas)
    rmin = r_out[idx].min()
    flat = (np.abs(dr[idx]) < 1.5) & (r_out[idx] < rmin + 25)
    # keep the largest contiguous run
    runs, cur = [], []
    for ii, f in zip(idx, flat):
        if f:
            cur.append(ii)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    run = max(runs, key=len)
    # trim 1 deg each side
    run = run[10:-10] if len(run) > 40 else run
    th = np.radians(thetas[run])
    hub_pts_x.append(cx + r_out[run] * np.cos(th)); hub_pts_y.append(cy - r_out[run] * np.sin(th))
    gaps.append({"theta_start": float(thetas[run[0]]), "theta_end": float(thetas[run[-1]]),
                 "extent_deg": float(len(run) * 0.1), "r_mean": float(r_out[run].mean()),
                 "r_std": float(r_out[run].std())})
hx_all = np.concatenate(hub_pts_x); hy_all = np.concatenate(hub_pts_y)
ucx, ucy, ur, urms, ures = fit_circle(hx_all, hy_all)
R["hub_circle_px"] = {"cx": ucx, "cy": ucy, "r": ur, "rms": urms, "gaps": gaps}
R["centres"]["hub_fit"] = [ucx, ucy]

# circle through unclipped tips
tipx = np.array([t["x"] for t in tip_info if not t["clipped_by_frame"]])
tipy = np.array([t["y"] for t in tip_info if not t["clipped_by_frame"]])
tcx, tcy, tr, trms, _ = fit_circle(tipx, tipy)
R["centres"]["tip_circle_unclipped"] = [tcx, tcy]
R["tip_circle_px"] = {"r": tr, "rms": trms}

# ------------------------------------------------------------------ flanks
# for each tip k: the flank toward the previous gap (CW side, lower theta) and toward the
# next gap (CCW side). Flank points = outer-boundary pixels with theta between the hub-arc end
# and the tip, radius between hub_r + 15 px and tip_r - 15 px.
points = []
for k in range(6):
    tk = tip_info[k]
    prev_gap = gaps[(k - 1) % 6]; next_gap = gaps[k]
    pk = {"k": k, "tip": tk}
    for side, g_end in (("cw", prev_gap["theta_end"]), ("ccw", next_gap["theta_start"])):
        if side == "cw":
            span_ok = (angdiff(oth, g_end) > 0) & (angdiff(tk["theta"], oth) > 0)
        else:
            span_ok = (angdiff(g_end, oth) > 0) & (angdiff(oth, tk["theta"]) > 0)
        rlo = ur + 15; rhi = tk["r"] - 15
        sel = span_ok & (orad > rlo) & (orad < rhi) & (ox > 1) & (oy > 1) & (ox < W - 2) & (oy < H - 2)
        px, py = ox[sel], oy[sel]
        # drop points of the hub rim itself (should be excluded by rlo) and root cut interiors
        p0, d, rms, res = fit_line(px, py)
        # robust refit (drop >3 sigma)
        keep = np.abs(res) < max(3 * rms, 1.5)
        p0, d, rms, res = fit_line(px[keep], py[keep])
        px, py = px[keep], py[keep]
        # orient d from root to tip
        tipv = np.array([tk["x"], tk["y"]])
        if np.dot(tipv - p0, d) < 0:
            d = -d
        # straightness: inner half vs outer half angles, quadratic bow
        s_along = (px - p0[0]) * d[0] + (py - p0[1]) * d[1]
        n = np.array([-d[1], d[0]])
        off = (px - p0[0]) * n[0] + (py - p0[1]) * n[1]
        smid = np.median(s_along)
        halves = {}
        for hn, hs in (("inner", s_along < smid), ("outer", s_along >= smid)):
            q0, qd, qrms, _ = fit_line(px[hs], py[hs])
            if np.dot(qd, d) < 0:
                qd = -qd
            halves[hn] = {"dir": qd.tolist(), "rms": qrms}
        dang = math.degrees(math.atan2(np.cross(halves["inner"]["dir"], halves["outer"]["dir"]),
                                       np.dot(halves["inner"]["dir"], halves["outer"]["dir"])))
        L = s_along.max() - s_along.min()
        u = (s_along - s_along.min()) / L
        qc = np.polyfit(u, off, 2)
        bow = -qc[0] / 4.0  # sagitta of the quadratic over the fitted length, px
        # outward-normal sign relative to centre (for shadow side labelling)
        mid = p0
        rad = mid - np.array([cx, cy])
        nout = n if np.dot(n, rad - np.dot(rad, d) * d) > 0 else -n
        pk[side] = {"p0": p0.tolist(), "dir": d.tolist(), "rms": rms, "n_pts": int(len(px)),
                    "fit_len_px": float(L), "inner_vs_outer_angle_deg": float(dang),
                    "bow_sagitta_px": float(bow), "outward_normal": nout.tolist(),
                    "r_range": [float(rlo), float(rhi)], "halves": halves}
    # geometry from the two flank lines
    a, b = pk["cw"], pk["ccw"]
    da, db = np.array(a["dir"]), np.array(b["dir"])
    inc = math.degrees(math.acos(np.clip(np.dot(da, db), -1, 1)))
    gtip = line_intersect(np.array(a["p0"]), da, np.array(b["p0"]), db)
    # outer-half-only tip angle
    oa, ob_ = np.array(a["halves"]["outer"]["dir"]), np.array(b["halves"]["outer"]["dir"])
    inc_outer = math.degrees(math.acos(np.clip(np.dot(oa, ob_), -1, 1)))
    ia, ib = np.array(a["halves"]["inner"]["dir"]), np.array(b["halves"]["inner"]["dir"])
    inc_inner = math.degrees(math.acos(np.clip(np.dot(ia, ib), -1, 1)))
    # bisector direction (tip -> root, i.e. pointing inward) vs radial direction
    bis = -(da + db); bis /= np.linalg.norm(bis)
    radial_in = np.array([cx, cy]) - gtip; radial_in /= np.linalg.norm(radial_in)
    lean = math.degrees(math.atan2(np.cross(radial_in, bis), np.dot(radial_in, bis)))
    # each flank's angle to the radial line through the geometric tip
    fa = math.degrees(math.acos(np.clip(np.dot(-da, radial_in), -1, 1)))
    fb = math.degrees(math.acos(np.clip(np.dot(-db, radial_in), -1, 1)))
    # base: where each flank line meets the hub circle (the root point nearer the tip side)
    roots = []
    for fl, dd in ((a, da), (b, db)):
        pts = line_circle(np.array(fl["p0"]), dd, ucx, ucy, ur)
        if pts:
            # choose the intersection closest to the tip along the flank but still on the hub
            pts = sorted(pts, key=lambda q: -np.dot(q - np.array(fl["p0"]), dd))
            roots.append(pts[0])
        else:
            roots.append(None)
    base_w = float(np.linalg.norm(roots[0] - roots[1])) if roots[0] is not None and roots[1] is not None else None
    base_ang = None
    if base_w is not None:
        t0 = float(theta_of(roots[0][0], roots[0][1], cx, cy)); t1 = float(theta_of(roots[1][0], roots[1][1], cx, cy))
        base_ang = abs(angdiff(t1, t0))
    pk["geom"] = {"included_angle_deg": inc, "included_angle_outer_half_deg": inc_outer,
                  "included_angle_inner_half_deg": inc_inner,
                  "geometric_tip": gtip.tolist(), "geometric_tip_r": float(np.hypot(gtip[0] - cx, gtip[1] - cy)),
                  "geometric_tip_theta": float(theta_of(gtip[0], gtip[1], cx, cy)),
                  "bisector_lean_from_radial_deg": lean,
                  "flank_cw_to_radial_deg": fa, "flank_ccw_to_radial_deg": fb,
                  "root_cw": None if roots[0] is None else roots[0].tolist(),
                  "root_ccw": None if roots[1] is None else roots[1].tolist(),
                  "base_chord_px": base_w, "base_angular_deg": base_ang}
    points.append(pk)
R["points"] = points

# widths across each point at several radii (angular extent of r_out > Rr around the tip)
width_tab = []
for k, pk in enumerate(points):
    ti = tips[k]
    rowk = {}
    for f in (0.1, 0.25, 0.5, 0.75, 0.9):
        Rr = ur + f * (pk["geom"]["geometric_tip_r"] - ur)
        # walk from the tip index both ways while r_out > Rr
        n = len(thetas)
        lo = ti
        while r_out[(lo - 1) % n] > Rr and (ti - lo) < 600:
            lo -= 1
        hi = ti
        while r_out[(hi + 1) % n] > Rr and (hi - ti) < 600:
            hi += 1
        dth = (hi - lo + 1) * 0.1
        rowk[str(f)] = {"R_px": float(Rr), "ang_deg": float(dth), "chord_px": float(2 * Rr * math.sin(math.radians(dth) / 2)),
                        "clipped": bool(clipped[np.arange(lo, hi + 1) % n].any())}
    width_tab.append(rowk)
R["widths"] = width_tab

# root cuts: how far r_out dips below the hub circle near each root
cuts = []
hub_r_theta = lambda th: None
for k in range(6):
    g = gaps[k]
    for end, sgn in (("start", -1), ("end", 1)):
        th0 = g["theta_" + end]
        # region from the hub-arc end toward the flank, 6 deg
        rng = th0 + sgn * np.arange(0, 60) * 0.1
        ii = (np.round((rng % 360) / 0.1).astype(int)) % len(thetas)
        # hub circle radius at those angles (from the fitted hub circle, seen from origin)
        thr = np.radians(thetas[ii])
        # distance along ray from origin to hub circle
        ex, ey = np.cos(thr), -np.sin(thr)
        fx, fy = cx - ucx, cy - ucy
        bq = 2 * (fx * ex + fy * ey); cq = fx * fx + fy * fy - ur * ur
        rh = (-bq + np.sqrt(bq * bq - 4 * cq)) / 2
        dev = r_out[ii] - rh
        cuts.append({"gap": k, "end": end, "theta0": float(th0), "min_dev_px": float(dev.min()),
                     "theta_at_min": float(thetas[ii[np.argmin(dev)]])})
R["root_dips"] = cuts

# spans
tp = [(t["x"], t["y"]) for t in tip_info]
spans = []
for k in range(3):
    a, b = tp[k], tp[k + 3]
    spans.append({"pair": [k, k + 3], "dist_px": float(math.hypot(a[0] - b[0], a[1] - b[1])),
                  "clipped": tip_info[k]["clipped_by_frame"] or tip_info[k + 3]["clipped_by_frame"]})
gt = [p["geom"]["geometric_tip"] for p in points]
gspans = [float(math.hypot(gt[k][0] - gt[k + 3][0], gt[k][1] - gt[k + 3][1])) for k in range(3)]
R["spans_raw_tips"] = spans
R["spans_geometric_tips"] = gspans

json.dump(R, open(os.path.join(outdir, f"radial_{tag}.json"), "w"), indent=1, default=float)

# ------------------------------------------------------------------ console summary
print("TAG", tag)
print("centres", {k: [round(v[0], 1), round(v[1], 1)] if isinstance(v, (list, tuple)) else v for k, v in R["centres"].items()})
print("hole r all %.2f rms %.2f | crisp-half r %.2f rms %.2f | diam max/min %.4f | equiv diam %.1f"
      % (hr, hrms, cr, crms, R["hole_px"]["diam_max_over_min"], R["hole_px"]["equiv_diam"]))
print("hole diam by dir", {k: round(v, 1) for k, v in dia_dirs.items()})
print("dominant harmonic", dom, "amps", {k: round(v, 1) for k, v in list(harm.items())[:13]})
print("hub circle c=(%.1f,%.1f) r=%.2f rms=%.2f" % (ucx, ucy, ur, urms))
for g in gaps:
    print("  gap", {k: round(v, 2) for k, v in g.items()})
print("tip circle unclipped c=(%.1f,%.1f) r=%.1f rms=%.2f" % (tcx, tcy, tr, trms))
for t in tip_info:
    print("tip", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in t.items()})
for m in mins:
    print("min", {k: round(v, 1) for k, v in m.items()})
for pk in points:
    g = pk["geom"]
    print("point %d tip th %.1f | inc %.2f (outer %.2f inner %.2f) | gtip r %.1f | lean %.2f | flank-rad cw %.2f ccw %.2f | base %.1f px %.1f deg"
          % (pk["k"], pk["tip"]["theta"], g["included_angle_deg"], g["included_angle_outer_half_deg"],
             g["included_angle_inner_half_deg"], g["geometric_tip_r"], g["bisector_lean_from_radial_deg"],
             g["flank_cw_to_radial_deg"], g["flank_ccw_to_radial_deg"], g["base_chord_px"] or -1, g["base_angular_deg"] or -1))
    for side in ("cw", "ccw"):
        f = pk[side]
        print("    %s rms %.2f n %d len %.0f in/out ang %.2f bow %.2f normal %s" % (
            side, f["rms"], f["n_pts"], f["fit_len_px"], f["inner_vs_outer_angle_deg"], f["bow_sagitta_px"],
            np.round(f["outward_normal"], 2).tolist()))
for k, w in enumerate(width_tab):
    print("widths pt", k, {f: (round(v["R_px"]), round(v["chord_px"], 1), v["clipped"]) for f, v in w.items()})
for c in cuts:
    print("rootdip", c)
print("spans raw", spans)
print("spans geometric", gspans)

# ------------------------------------------------------------------ overlay
if do_overlay:
    ov = rgb.copy() * 0.8
    def dot(x, y, col, rad=1):
        xi, yi = int(round(x)), int(round(y))
        ov[max(0, yi - rad):yi + rad + 1, max(0, xi - rad):xi + rad + 1] = col
    ov[ob] = [0, 1, 1]
    ov[hb] = [0, 1, 1]
    for th in np.arange(0, 360, 0.5):
        a = math.radians(th)
        dot(ucx + ur * math.cos(a), ucy - ur * math.sin(a), [1, 0, 1], 0)
        dot(hcx + hr * math.cos(a), hcy - hr * math.sin(a), [1, 1, 0], 0)
    for x, y in zip(hx_all, hy_all):
        dot(x, y, [1, 0.5, 0], 1)
    for pk in points:
        for side, col in (("cw", [1, 0, 0]), ("ccw", [0, 1, 0])):
            f = pk[side]
            p0 = np.array(f["p0"]); d = np.array(f["dir"])
            for s in np.arange(-450, 450, 0.5):
                q = p0 + s * d
                if 0 <= q[0] < W and 0 <= q[1] < H:
                    ov[int(q[1]), int(q[0])] = col
        gtp = pk["geom"]["geometric_tip"]
        dot(gtp[0], gtp[1], [0, 0, 1], 3)
        for rt in ("root_cw", "root_ccw"):
            if pk["geom"][rt] is not None:
                dot(pk["geom"][rt][0], pk["geom"][rt][1], [1, 1, 1], 3)
    dot(cx, cy, [1, 1, 0], 3); dot(ucx, ucy, [1, 0, 1], 3); dot(tcx, tcy, [0, 0, 1], 3)
    imgio.save_rgb(os.path.join(outdir, f"overlay_{tag}.png"), ov)
    # r(theta) plot
    PH, PW = 500, 1800
    plot = np.ones((PH, PW, 3))
    rmax = 700
    for i, (th, r) in enumerate(zip(thetas, r_out)):
        x = int(th / 360 * (PW - 1)); y = int(PH - 1 - r / rmax * (PH - 1))
        plot[max(0, y - 1):y + 2, x] = [0.8, 0, 0] if clipped[i] else [0, 0, 0]
        yi = int(PH - 1 - r_in[i] / rmax * (PH - 1))
        plot[yi, x] = [0, 0, 0.8]
    yh = int(PH - 1 - ur / rmax * (PH - 1)); plot[yh, :] = [1, 0, 1]
    for tt in tip_info:
        plot[:, int(tt["theta"] / 360 * (PW - 1))] = [0, 0.7, 0]
    imgio.save_rgb(os.path.join(outdir, f"rtheta_{tag}.png"), plot)
