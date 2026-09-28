"""Stage 2: Method A (radial profile) measurements of the manji photo from the final mask.
All lengths in px here; ratios to the tip-to-tip span are computed at the end.
Frames: image (x right, y down); math (X = x - cx, Y = cy - y, angles CCW, as seen by the viewer).
"""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

t0 = time.time()
rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
lum = (rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)).astype(np.float32)
mask = np.unpackbits(np.load(os.path.join(C.OUT, "mask.npy")))[:h * w].reshape(h, w).astype(bool)
cmask = np.unpackbits(np.load(os.path.join(C.OUT, "mask_colour.npy")))[:h * w].reshape(h, w).astype(bool)
R = {}  # results

# ---------------- holes / centre ----------------
rb, rtb, ab, tb = C.label_runs(~mask, False)
encl = [float(ab[c]) for c in np.unique(rtb) if not tb[c]]
R["enclosed_background_components_px"] = encl


def box(a, r):
    k = 2 * r + 1
    P = np.pad(a, r, mode='edge').astype(np.float64)
    S = np.zeros((P.shape[0] + 1, P.shape[1] + 1)); S[1:, 1:] = P.cumsum(0).cumsum(1)
    return ((S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]) / (k * k)).astype(np.float32)


# bright (background-like) spots strictly inside the piece: a through-hole would show the lid colour
inner = C.erode(mask, 15)
l3 = box(lum, 1)
bright_in = inner & (l3 > 0.55)
if bright_in.any():
    r_, ro_, ar_, _ = C.label_runs(bright_in, True)
    R["interior_bright_spots_largest_px"] = float(ar_.max())
    R["interior_bright_spots_count"] = int((ar_ > 0).sum())
else:
    R["interior_bright_spots_largest_px"] = 0.0
    R["interior_bright_spots_count"] = 0
R["interior_lum_p01_p50_p99"] = [float(v) for v in np.percentile(lum[inner], [1, 50, 99])]

yy, xx = np.nonzero(mask)
cx, cy = float(xx.mean()), float(yy.mean())
area = float(mask.sum())
R["centroid_xy_px"] = [cx, cy]
R["area_px"] = area
# second moments (a C4 shape must be isotropic)
Xc = xx - cx; Yc = -(yy - cy)
Ixx, Iyy, Ixy = float((Xc * Xc).mean()), float((Yc * Yc).mean()), float((Xc * Yc).mean())
R["second_moment_anisotropy"] = float(math.hypot(Ixx - Iyy, 2 * Ixy) / (Ixx + Iyy))


def inside(x, y):
    xi = np.round(x).astype(np.int64); yi = np.round(y).astype(np.int64)
    ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
    out = np.zeros(xi.shape, bool)
    out[ok] = mask[yi[ok], xi[ok]]
    return out


def to_img(X, Y):
    return cx + X, cy - Y


# ---------------- contour ----------------
cont = C.trace_contour(mask).astype(np.float64)
N = len(cont)
CX = cont[:, 0] - cx; CY = -(cont[:, 1] - cy)
crad = np.hypot(CX, CY)
cang = np.degrees(np.arctan2(CY, CX)) % 360
seglen = np.hypot(np.diff(cont[:, 0], append=cont[0, 0]), np.diff(cont[:, 1], append=cont[0, 1]))
arc = np.concatenate([[0], np.cumsum(seglen)[:-1]])
L_total = float(seglen.sum())
R["perimeter_px"] = L_total

# ---------------- radial profile r(theta) at 0.1 deg ----------------
TH = np.arange(0, 360, 0.1)
rmax = crad.max() + 5
rs = np.arange(0, rmax, 0.25)
r_out = np.zeros(len(TH)); r_first_exit = np.zeros(len(TH)); n_cross = np.zeros(len(TH), int)
for i0 in range(0, len(TH), 200):
    th = np.radians(TH[i0:i0 + 200])[:, None]
    X = rs[None, :] * np.cos(th); Y = rs[None, :] * np.sin(th)
    xi, yi = to_img(X, Y)
    m = inside(xi, yi)
    last = len(rs) - 1 - np.argmax(m[:, ::-1], axis=1)
    r_out[i0:i0 + 200] = np.where(m.any(1), rs[last], 0)
    fe = np.argmax(~m, axis=1)
    r_first_exit[i0:i0 + 200] = rs[fe]
    n_cross[i0:i0 + 200] = (np.diff(m.astype(np.int8), axis=1) == -1).sum(1)
np.save(os.path.join(C.OUT, "r_theta.npy"), np.column_stack([TH, r_out, r_first_exit, n_cross]))

# dominant periodicity
F = np.fft.rfft(r_out - r_out.mean())
amp = np.abs(F)
k_dom = int(np.argmax(amp[1:60]) + 1)
R["fft_dominant_harmonic"] = k_dom
R["fft_top5_harmonics"] = [int(k) for k in (np.argsort(amp[1:60])[::-1][:5] + 1)]
R["fft_amp_ratio_k4_over_next"] = float(amp[4] / np.max(np.delete(amp[1:60], 3)))

# ---------------- tips: farthest contour point in each quadrant around the 4 largest r_out maxima -------
order = np.argsort(r_out)[::-1]
peaks = []
for i in order:
    if all(min(abs(TH[i] - p), 360 - abs(TH[i] - p)) > 45 for p in peaks):
        peaks.append(TH[i])
    if len(peaks) == 4:
        break
peaks = sorted(peaks)
tips = []
for p in peaks:
    dd = np.minimum(np.abs(cang - p), 360 - np.abs(cang - p))
    cand = np.nonzero(dd < 20)[0]
    j = cand[np.argmax(crad[cand])]
    tips.append(int(j))
tip_xy = np.array([[CX[j], CY[j]] for j in tips])
tip_r = np.array([crad[j] for j in tips])
tip_ang = np.array([cang[j] for j in tips])
R["tips_math_xy_px"] = tip_xy.tolist()
R["tips_radius_px"] = tip_r.tolist()
R["tips_angle_deg"] = tip_ang.tolist()
R["tips_angle_spacing_deg"] = [float((tip_ang[(i + 1) % 4] - tip_ang[i]) % 360) for i in range(4)]
d02 = float(np.hypot(*(tip_xy[0] - tip_xy[2]))); d13 = float(np.hypot(*(tip_xy[1] - tip_xy[3])))
SPAN = (d02 + d13) / 2
R["tip_to_tip_px"] = [d02, d13]
R["SPAN_px"] = SPAN
# adjacent tip distances
adj = [float(np.hypot(*(tip_xy[i] - tip_xy[(i + 1) % 4]))) for i in range(4)]
R["adjacent_tip_distance_px"] = adj

# r(theta) asymmetry at each tip: which side does r drop steeply?
asym = []
for a in tip_ang:
    def rat(t):
        return float(np.interp(t % 360, TH, r_out, period=360))
    asym.append(dict(tip_deg=float(a), r_ccw_plus3=rat(a + 3), r_cw_minus3=rat(a - 3),
                     r_ccw_plus10=rat(a + 10), r_cw_minus10=rat(a - 10)))
R["r_theta_asymmetry_at_tips"] = asym

# r(theta) minima (notches): local minima of r_out
mins = []
rr_s = np.convolve(np.concatenate([r_out[-5:], r_out, r_out[:5]]), np.ones(11) / 11, mode='valid')
for i in range(len(TH)):
    a, b, c = rr_s[i - 1], rr_s[i], rr_s[(i + 1) % len(TH)]
    if b <= a and b <= c:
        win = rr_s[np.arange(i - 100, i + 101) % len(TH)]
        if b <= win.min() + 1e-9:
            mins.append((float(TH[i]), float(r_out[i])))
R["r_theta_local_minima_deg_px"] = mins

# ---------------- corners from turning angle on the ordered contour ----------------
K = 20  # px of arc on each side


def arc_index(i, ds):
    tgt = (arc[i] + ds) % L_total
    return int(np.searchsorted(arc, tgt) % N)


fwd = np.array([arc_index(i, K) for i in range(N)])
bwd = np.array([arc_index(i, -K) for i in range(N)])
v1 = cont - cont[bwd]; v2 = cont[fwd] - cont
a1 = np.arctan2(v1[:, 1], v1[:, 0]); a2 = np.arctan2(v2[:, 1], v2[:, 0])
turn = np.degrees((a2 - a1 + np.pi) % (2 * np.pi) - np.pi)  # image coords (y down): + = clockwise turn on screen
# contour is traced clockwise on screen, so convex corners turn +, concave corners turn -
corner_idx = []
absT = np.abs(turn)
for i in np.argsort(absT)[::-1]:
    if absT[i] < 35:
        break
    if all(min(abs(arc[i] - arc[j]), L_total - abs(arc[i] - arc[j])) > 60 for j in corner_idx):
        corner_idx.append(int(i))
corner_idx = sorted(corner_idx, key=lambda i: arc[i])
R["n_corners_detected"] = len(corner_idx)
corners = [dict(i=i, x=float(cont[i, 0]), y=float(cont[i, 1]), turn=float(turn[i]),
                r=float(crad[i]), ang=float(cang[i])) for i in corner_idx]

# classify: tips are the 4 tips; for each tip, walking forward (clockwise on screen) along the contour:
# tip -> outer edge -> arm-end corner (convex) -> trailing edge -> junction (concave) -> next arm's hook-side edge
# -> hook root (concave) -> hook inner edge -> next tip
tipset = set()
for j in tips:
    # snap each tip to nearest detected corner if within 30 px arc
    tipset.add(j)


def next_corner(i, convex=None, exclude=()):
    best = None
    for c in corners:
        if c['i'] in exclude:
            continue
        if convex is True and c['turn'] <= 0:
            continue
        if convex is False and c['turn'] >= 0:
            continue
        ds = (arc[c['i']] - arc[i]) % L_total
        if ds < 30:
            continue
        if best is None or ds < best[0]:
            best = (ds, c['i'])
    return best[1] if best else None


# order tips along the contour; find corners geometrically (robust to small segmentation notches)
tips_sorted = sorted(tips, key=lambda j: arc[j])


def fwd_range(i0, i1):
    L = (arc[i1] - arc[i0]) % L_total
    ds = (arc - arc[i0]) % L_total
    idx = np.nonzero((ds > 0) & (ds < L))[0]
    return idx[np.argsort(ds[idx])]


def farthest_from_chord(i0, i1):
    idx = fwd_range(i0, i1)
    p0 = np.array([CX[i0], CY[i0]]); p1 = np.array([CX[i1], CY[i1]])
    d = p1 - p0; d /= np.linalg.norm(d)
    nrm_ = np.array([-d[1], d[0]])
    dist = np.abs((mathpts(idx) - p0) @ nrm_)
    return int(idx[np.argmax(dist)])


def mathpts(idx):
    return np.column_stack([CX[idx], CY[idx]])


quarters = []
for qi, jt in enumerate(tips_sorted):
    jt_next = tips_sorted[(qi + 1) % 4]
    idx = fwd_range(jt, jt_next)
    j_junc = int(idx[np.argmin(crad[idx])])           # innermost point between two tips = junction corner
    j_armend = farthest_from_chord(jt, j_junc)       # convex arm-end corner
    j_root = farthest_from_chord(j_junc, jt_next)    # concave hook-root corner of the next arm
    quarters.append(dict(tip=int(jt), armend=j_armend, junction=j_junc, next_root=j_root, next_tip=int(jt_next)))
R["quarters_contour_idx"] = quarters
R["quarters_xy_img"] = [{k: [float(cont[v, 0]), float(cont[v, 1])] for k, v in q.items()} for q in quarters]


def pts_between(i0, i1, m0=15.0, m1=15.0):
    """contour points strictly between index i0 and i1 going forward, trimmed by arc margins"""
    L = (arc[i1] - arc[i0]) % L_total
    ds = (arc - arc[i0]) % L_total
    sel = (ds > m0) & (ds < L - m1)
    idx = np.nonzero(sel)[0]
    idx = idx[np.argsort(ds[idx])]
    return idx


def tls(P, iters=3):
    keep = np.ones(len(P), bool)
    for it in range(iters + 1):
        c = P[keep].mean(0)
        U, S, Vt = np.linalg.svd(P[keep] - c, full_matrices=False)
        d = Vt[0]
        resid = (P - c) @ Vt[1]
        mad = np.median(np.abs(resid[keep])) + 1e-6
        if it < iters:
            keep = np.abs(resid) < max(3.5 * 1.4826 * mad, 1.0)
    return c, d, float(np.sqrt((resid[keep] ** 2).mean())), float(np.abs(resid[keep]).max())


def line_intersect(c1, d1, c2, d2):
    A = np.array([d1, -d2]).T
    t = np.linalg.solve(A, c2 - c1)
    return c1 + t[0] * d1


# per-arm structures. In contour order: [tip_q] outer edge -> armend_q -> trailing edge (arm q) -> junction_q ->
# hook-side edge of arm q+1 -> root of arm q+1 -> hook inner edge of arm q+1 -> tip_{q+1}
arms = []
for q in range(4):
    Q = quarters[q]
    Qp = quarters[(q - 1) % 4]  # previous quarter provides this arm's hook-side edge and root
    arm = {}
    arm['tip_i'] = Q['tip']
    # hook-side edge of this arm: from previous junction to this arm's root (previous quarter's next_root)
    arm['root_i'] = Qp['next_root']
    arm['junc_prev_i'] = Qp['junction']
    arm['armend_i'] = Q['armend']
    arm['junc_i'] = Q['junction']
    arm['idx_hookside'] = pts_between(arm['junc_prev_i'], arm['root_i'], 25, 25)
    arm['idx_hookinner'] = pts_between(arm['root_i'], arm['tip_i'], 25, 25)
    arm['idx_outer'] = pts_between(arm['tip_i'], arm['armend_i'], 10, 20)
    arm['idx_trailing'] = pts_between(arm['armend_i'], arm['junc_i'], 25, 25)
    arms.append(arm)

# arm frames from the two long edges
arm_out = []
for k, arm in enumerate(arms):
    Ph = mathpts(arm['idx_hookside']); Pt = mathpts(arm['idx_trailing'])
    ch, dh, rms_h, max_h = tls(Ph); ct, dt, rms_t, max_t = tls(Pt)
    # orient both directions outward (away from centre)
    tipv = np.array([CX[arm['tip_i']], CY[arm['tip_i']]])
    if dh @ (ch) < 0: dh = -dh
    if dt @ (ct) < 0: dt = -dt
    a = dh + dt; a /= np.linalg.norm(a)
    b = np.array([-a[1], a[0]])  # a rotated +90 deg CCW (math frame)
    # the hook-side edge should lie on +b or -b side
    side_hook = float(np.sign((ch @ b)))
    arm_out.append(dict(a=a, b=b, ch=ch, dh=dh, ct=ct, dt=dt, rms_h=rms_h, rms_t=rms_t, max_h=max_h, max_t=max_t,
                        side_hook=side_hook))

# handedness: tip lateral side relative to arm axis
hand = []
for k, arm in enumerate(arms):
    a, b = arm_out[k]['a'], arm_out[k]['b']
    tipv = np.array([CX[arm['tip_i']], CY[arm['tip_i']]])
    hand.append(dict(arm_axis_deg=float(math.degrees(math.atan2(a[1], a[0])) % 360),
                     tip_v_on_ccw_side=float(tipv @ b), hookside_edge_on_ccw_side=arm_out[k]['side_hook']))
R["handedness_per_arm"] = hand

# ---------------- arm cross-sections (mask) ----------------
results_arms = []
for k, arm in enumerate(arms):
    A = arm_out[k]
    a, b = A['a'], A['b']
    # centreline offset: foot of the two edge lines
    vh = float(A['ch'] @ b); vt = float(A['ct'] @ b)
    vmid = 0.5 * (vh + vt)
    # stations
    root = np.array([CX[arm['root_i']], CY[arm['root_i']]])
    armend = np.array([CX[arm['armend_i']], CY[arm['armend_i']]])
    tipv = np.array([CX[arm['tip_i']], CY[arm['tip_i']]])
    u_root = float(root @ a); u_armend = float(armend @ a); u_tip = float(tipv @ a); v_tip = float(tipv @ b)
    half = abs(vh - vt) / 2
    stations = np.linspace(half + 40, u_root - 30, 25)
    vv = np.arange(-600, 600, 0.25)
    widths = []; vplus = []; vminus = []
    for u in stations:
        P = u * a[None, :] + (vmid + vv)[:, None] * b[None, :]
        xi, yi = to_img(P[:, 0], P[:, 1])
        m = inside(xi, yi)
        c0 = np.argmin(np.abs(vv))
        if not m[c0]:
            continue
        lo = c0
        while lo > 0 and m[lo - 1]: lo -= 1
        hi = c0
        while hi < len(vv) - 1 and m[hi + 1]: hi += 1
        widths.append(vv[hi] - vv[lo] + 0.25); vplus.append(vmid + vv[hi]); vminus.append(vmid + vv[lo])
    widths = np.array(widths); vplus = np.array(vplus); vminus = np.array(vminus)
    # hook-side edge in (u,v): the side with same sign as side_hook
    s = A['side_hook']
    v_hookedge = vplus if s > 0 else vminus
    v_trailedge = vminus if s > 0 else vplus
    # along-arm outer end on the centreline and on the trailing side
    uu = np.arange(0, 2000, 0.25)
    P = uu[:, None] * a[None, :] + vmid * b[None, :]
    m = inside(*to_img(P[:, 0], P[:, 1]))
    u_end_centre = float(uu[len(uu) - 1 - np.argmax(m[::-1])])
    # hook: lines of constant v beyond the arm's hook-side edge; hook extent measured parallel to arm axis
    v_edge_end = float(np.median(v_hookedge[-5:]))
    hook_prof = []
    vtip_rel = (v_tip - v_edge_end) * s
    for f in [0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        vline = v_edge_end + s * f * vtip_rel
        uu2 = np.arange(u_root - 200, u_end_centre + 200, 0.25)
        P = uu2[:, None] * a[None, :] + vline * b[None, :]
        mm = inside(*to_img(P[:, 0], P[:, 1]))
        if not mm.any():
            hook_prof.append(dict(f=f, width=0.0)); continue
        # longest run
        d = np.diff(np.concatenate([[0], mm.astype(np.int8), [0]]))
        st = np.nonzero(d == 1)[0]; en = np.nonzero(d == -1)[0]
        L = en - st; j = int(np.argmax(L))
        hook_prof.append(dict(f=f, v=float(vline), u_in=float(uu2[st[j]]), u_out=float(uu2[en[j] - 1]),
                              width=float(L[j] * 0.25)))
    results_arms.append(dict(
        k=k, axis_deg=float(math.degrees(math.atan2(a[1], a[0])) % 360),
        edge_angle_hookside_deg=float(math.degrees(math.atan2(A['dh'][1], A['dh'][0])) % 360),
        edge_angle_trailing_deg=float(math.degrees(math.atan2(A['dt'][1], A['dt'][0])) % 360),
        taper_deg=float(math.degrees(math.acos(np.clip(A['dh'] @ A['dt'], -1, 1)))),
        edge_fit_rms_px=[A['rms_h'], A['rms_t']], edge_fit_maxdev_px=[A['max_h'], A['max_t']],
        centreline_offset_px=float(vmid), side_hook=s,
        stations_u=stations.tolist(), widths=widths.tolist(),
        width_root=float(np.median(widths[:5])), width_end=float(np.median(widths[-5:])),
        width_mean=float(widths.mean()), width_std=float(widths.std()),
        u_root=u_root, u_armend=u_armend, u_end_centre=u_end_centre, u_tip=u_tip, v_tip=v_tip,
        v_hookedge_end=v_edge_end, v_trailedge_end=float(np.median(v_trailedge[-5:])),
        hook_len_beyond_arm=float((v_tip - v_edge_end) * s),
        hook_len_from_centreline=float((v_tip - vmid) * s),
        hook_len_from_trailing_edge=float((v_tip - float(np.median(v_trailedge[-5:]))) * s),
        hook_profile=hook_prof))

R["arms"] = results_arms

# ---------------- edge line fits and corners ----------------
edge_fits = []
corner_meas = []
for k, arm in enumerate(arms):
    d = {}
    for name in ('idx_hookside', 'idx_hookinner', 'idx_outer', 'idx_trailing'):
        idx = arm[name]
        P = mathpts(idx)
        c, dd, rms, mx = tls(P)
        # chord & sagitta (curvature) of this edge
        chord = P[-1] - P[0]
        L = float(np.linalg.norm(chord))
        nrm_ = np.array([-chord[1], chord[0]]) / (L + 1e-9)
        sag = (P - P[0]) @ nrm_
        d[name] = dict(n=len(idx), angle_deg=float(math.degrees(math.atan2(dd[1], dd[0])) % 180), rms=rms, maxdev=mx,
                       chord_len=L, sagitta_max=float(sag[np.argmax(np.abs(sag))]))
    edge_fits.append(d)
R["edge_fits"] = edge_fits


def local_line(i_corner, direction, a0=12, a1=80):
    """TLS line through contour points at arc distance [a0,a1] from the corner, forward(+1)/backward(-1)"""
    ds = ((arc - arc[i_corner]) * direction) % L_total
    sel = np.nonzero((ds >= a0) & (ds <= a1))[0]
    P = mathpts(sel)
    c, dd, rms, mx = tls(P)
    # orient away from corner
    if (P.mean(0) - np.array([CX[i_corner], CY[i_corner]])) @ dd < 0:
        dd = -dd
    return c, dd, rms


def corner_measure(i, kind, a0=60, a1=250):
    cb, db, rb_ = local_line(i, -1, a0, a1)
    cf, df, rf_ = local_line(i, +1, a0, a1)
    X = line_intersect(cb, db, cf, df)
    ang = float(math.degrees(math.acos(np.clip(db @ df, -1, 1))))  # angle between the two edges at the corner
    # nearest contour point to the ideal intersection
    dist = np.hypot(CX - X[0], CY - X[1])
    near = int(np.argmin(dist))
    gap = float(dist[near])
    # equivalent fillet radius for a round of radius r in a corner of interior angle ang:
    # distance from vertex to arc = r * (1/sin(ang/2) - 1)
    s2 = math.sin(math.radians(ang) / 2)
    r_eq = gap / (1 / s2 - 1) if s2 < 0.999 else float('nan')
    return dict(kind=kind, contour_i=int(i), angle_between_edges_deg=ang, ideal_vertex_math=X.tolist(),
                gap_px=gap, equiv_fillet_radius_px=r_eq, fit_rms=[rb_, rf_])


for k, arm in enumerate(arms):
    corner_meas.append(corner_measure(arm['root_i'], 'hook_root(concave)'))
    corner_meas.append(corner_measure(arm['armend_i'], 'arm_end(convex)'))
    corner_meas.append(corner_measure(arm['junc_i'], 'junction(concave)'))
R["corners"] = corner_meas
# central square from the junction ideal vertices
jv = np.array([c["ideal_vertex_math"] for c in corner_meas if c["kind"] == "junction(concave)"])
if len(jv) == 4:
    ang = np.degrees(np.arctan2(jv[:, 1], jv[:, 0])) % 360
    o = np.argsort(ang); jv = jv[o]
    R["junction_vertices_math"] = jv.tolist()
    R["junction_vertex_radius_px"] = [float(np.hypot(*p)) for p in jv]
    R["junction_vertex_adjacent_dist_px"] = [float(np.hypot(*(jv[i] - jv[(i + 1) % 4]))) for i in range(4)]
    R["junction_vertex_diagonal_px"] = [float(np.hypot(*(jv[0] - jv[2]))), float(np.hypot(*(jv[1] - jv[3])))]

# ---------------- tip angles at several fitting windows ----------------
tipang = []
for k, arm in enumerate(arms):
    i = arm['tip_i']
    row = dict(k=k)
    for (a0, a1) in ((8, 40), (10, 80), (15, 150), (20, 300)):
        cb, db, _ = local_line(i, -1, a0, a1)
        cf, df, _ = local_line(i, +1, a0, a1)
        row["%d-%d" % (a0, a1)] = float(math.degrees(math.acos(np.clip(db @ df, -1, 1))))
    # whole-edge chords: tip->root and tip->armend
    tipv = np.array([CX[i], CY[i]])
    rootv = np.array([CX[arm['root_i']], CY[arm['root_i']]]); endv = np.array([CX[arm['armend_i']], CY[arm['armend_i']]])
    u1 = (rootv - tipv) / np.linalg.norm(rootv - tipv); u2 = (endv - tipv) / np.linalg.norm(endv - tipv)
    row["chord_root_armend"] = float(math.degrees(math.acos(np.clip(u1 @ u2, -1, 1))))
    # tip bluntness: mask width at 3, 6, 10, 20 px back along the tip bisector
    bis = -(db + df); bis /= np.linalg.norm(bis)  # pointing outward from body toward tip
    perp = np.array([-bis[1], bis[0]])
    wid = {}
    for back in (3, 6, 10, 20, 40):
        base = tipv - back * bis
        tt = np.arange(-80, 80, 0.25)
        P = base[None, :] + tt[:, None] * perp[None, :]
        mm = inside(*to_img(P[:, 0], P[:, 1]))
        wid[str(back)] = float(mm.sum() * 0.25)
    row["width_behind_tip_px"] = wid
    tipang.append(row)
R["tip_angles"] = tipang

# ---------------- overall extents in the mean arm frame ----------------
axes = np.array([r['axis_deg'] for r in results_arms])
rot = np.array([(ax - 90 * round(ax / 90)) for ax in axes])
R["arm_axis_deviation_from_90grid_deg"] = rot.tolist()
theta0 = math.radians(float(np.mean(rot)))
ca, sa = math.cos(theta0), math.sin(theta0)
U = CX * ca + CY * sa; V = -CX * sa + CY * ca
R["extent_along_mean_axes_px"] = dict(u_min=float(U.min()), u_max=float(U.max()), v_min=float(V.min()), v_max=float(V.max()),
                                      width_u=float(U.max() - U.min()), width_v=float(V.max() - V.min()))
# across-the-arms: outer end of opposite arms on their centrelines
R["across_arms_centreline_px"] = [results_arms[0]['u_end_centre'] + results_arms[2]['u_end_centre'],
                                  results_arms[1]['u_end_centre'] + results_arms[3]['u_end_centre']]

json.dump(R, open(os.path.join(C.OUT, "measure_raw.json"), "w"), indent=1, default=float)
np.save(os.path.join(C.OUT, "contour_final.npy"), cont)
json.dump(dict(arms=[{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in a.items() if not k.startswith('idx_')} for a in arms],
               frames=[{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in f.items()} for f in arm_out],
               corners=corners, tips=tips, centre=[cx, cy]),
          open(os.path.join(C.OUT, "geometry_internal.json"), "w"), indent=1, default=float)
print("SPAN", SPAN, "tips r", tip_r, "angles", tip_ang, "corners", len(corners))
print("done", time.time() - t0)
