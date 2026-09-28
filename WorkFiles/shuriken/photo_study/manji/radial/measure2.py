"""Stage 3: corner circle fits, outer-edge arc fits, bevel-band profiles, debug overlay and r(theta) plot."""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
lum = (rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)).astype(np.float32)
mask = np.unpackbits(np.load(os.path.join(C.OUT, "mask.npy")))[:h * w].reshape(h, w).astype(bool)
cmask = np.unpackbits(np.load(os.path.join(C.OUT, "mask_colour.npy")))[:h * w].reshape(h, w).astype(bool)
R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
G = json.load(open(os.path.join(C.OUT, "geometry_internal.json")))
cont = np.load(os.path.join(C.OUT, "contour_final.npy"))
rth = np.load(os.path.join(C.OUT, "r_theta.npy"))
cx, cy = G["centre"]
N = len(cont)
CX = cont[:, 0] - cx; CY = -(cont[:, 1] - cy)
seglen = np.hypot(np.diff(cont[:, 0], append=cont[0, 0]), np.diff(cont[:, 1], append=cont[0, 1]))
arc = np.concatenate([[0], np.cumsum(seglen)[:-1]])
L_total = float(seglen.sum())
SPAN = R1["SPAN_px"]
OUT = {}


def fwd_range(i0, i1):
    L = (arc[i1] - arc[i0]) % L_total
    ds = (arc - arc[i0]) % L_total
    idx = np.nonzero((ds > 0) & (ds < L))[0]
    return idx[np.argsort(ds[idx])]


def mathpts(idx):
    return np.column_stack([CX[idx], CY[idx]])


def circle_fit(P):
    """Kasa algebraic circle fit -> centre, radius, rms residual"""
    A = np.column_stack([P[:, 0], P[:, 1], np.ones(len(P))])
    b = P[:, 0] ** 2 + P[:, 1] ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    xc, yc = sol[0] / 2, sol[1] / 2
    rr = math.sqrt(max(sol[2] + xc * xc + yc * yc, 1e-9))
    res = np.hypot(P[:, 0] - xc, P[:, 1] - yc) - rr
    return (xc, yc), rr, float(np.sqrt((res ** 2).mean()))


# ---------------- corner fillet fits (circle through the rounded part only) ----------------
def local_line(i_corner, direction, a0=12, a1=80):
    ds = ((arc - arc[i_corner]) * direction) % L_total
    sel = np.nonzero((ds >= a0) & (ds <= a1))[0]
    P = mathpts(sel)
    c = P.mean(0)
    U, S, Vt = np.linalg.svd(P - c, full_matrices=False)
    return c, Vt[0], Vt[1]


corner_fits = []
for ci, cinfo in enumerate(R1["corners"]):
    i = cinfo["contour_i"]
    X = np.array(cinfo["ideal_vertex_math"])
    cb, db, nb = local_line(i, -1)
    cf, df, nf = local_line(i, +1)
    d = np.hypot(CX - X[0], CY - X[1])
    ds = np.minimum((arc - arc[i]) % L_total, (arc[i] - arc) % L_total)
    near = np.nonzero((d < 60) & (ds < 120))[0]
    P = mathpts(near)
    d1 = np.abs((P - cb) @ nb); d2 = np.abs((P - cf) @ nf)
    off = (d1 > 2.0) & (d2 > 2.0)          # points that belong to neither straight edge
    rec = dict(kind=cinfo["kind"], angle_deg=cinfo["angle_between_edges_deg"], vertex_gap_px=cinfo["gap_px"],
               n_offline=int(off.sum()))
    if off.sum() >= 10:
        ctr, rr, rms = circle_fit(P[off])
        rec.update(fillet_radius_px=float(rr), fillet_rms_px=rms, fillet_ratio_span=float(rr / SPAN),
                   arc_len_px=float(off.sum()))
    corner_fits.append(rec)
OUT["corner_fillet_fits"] = corner_fits

# ---------------- outer-edge arc fits (arm end + hook outer edge) ----------------
outer_fits = []
for q in range(4):
    Q = R1["quarters_contour_idx"][q]
    idx = fwd_range(Q["tip"], Q["armend"])
    idx = idx[(arc[idx] - arc[Q["tip"]]) % L_total > 25]
    idx = idx[:-25] if len(idx) > 60 else idx
    P = mathpts(idx)
    ctr, rr, rms = circle_fit(P)
    # is the arc bulging away from the centre?
    bulge_out = bool(np.hypot(*ctr) < rr)
    outer_fits.append(dict(q=q, radius_px=float(rr), rms_px=rms, n=len(idx), bulge_outward=bulge_out,
                           radius_ratio_span=float(rr / SPAN)))
OUT["outer_edge_arc_fits"] = outer_fits

# ---------------- bevel band profiles along every edge ----------------
DEPTH = 70.0
ds_step = 0.5
depths = np.arange(0, DEPTH, ds_step)


def edge_strip(i0, i1, m0=25, m1=25, nbins=40):
    """unrolled strip of the original image inside the edge: (nbins positions) x (depths) x 3"""
    idx = fwd_range(i0, i1)
    L = (arc[i1] - arc[i0]) % L_total
    pos = np.linspace(m0, L - m1, nbins)
    strip = np.zeros((nbins, len(depths), 3), np.float32)
    lum_s = np.zeros((nbins, len(depths)), np.float32)
    for j, s0 in enumerate(pos):
        k = idx[np.argmin(np.abs(((arc[idx] - arc[i0]) % L_total) - s0))]
        # local tangent from +-8 px of arc
        ka = idx[np.argmin(np.abs(((arc[idx] - arc[i0]) % L_total) - (s0 - 8)))]
        kb = idx[np.argmin(np.abs(((arc[idx] - arc[i0]) % L_total) - (s0 + 8)))]
        t = np.array([CX[kb] - CX[ka], CY[kb] - CY[ka]], float)
        t /= np.linalg.norm(t) + 1e-9
        n_in = np.array([-t[1], t[0]])
        base = np.array([CX[k], CY[k]])
        probe = base + 8 * n_in
        if not mask[int(round(cy - probe[1])) % h, int(round(cx + probe[0])) % w]:
            n_in = -n_in
        acc = np.zeros((len(depths), 3))
        for off in (-3, 0, 3):
            P = base[None, :] + (depths[:, None] * n_in[None, :]) + off * t[None, :]
            xs = cx + P[:, 0]; ys = cy - P[:, 1]
            acc += C.bilinear(rgb, xs, ys)
        strip[j] = acc / 3
        lum_s[j] = strip[j] @ np.array([0.2126, 0.7152, 0.0722])
    # check inward orientation: interior should be darker than the outside background
    if lum_s[:, :6].mean() > 0.55:
        return None, None, None
    return strip, lum_s, pos


def band_measure(lum_s):
    """near-edge band: level at depth 3-9 px vs interior 35-65 px; band width = mid-level crossing"""
    out = []
    i_near = (depths >= 3) & (depths <= 9)
    i_far = (depths >= 35) & (depths <= 65)
    for j in range(lum_s.shape[0]):
        near = float(lum_s[j, i_near].mean()); far = float(lum_s[j, i_far].mean())
        diff = near - far
        wdt = float('nan')
        if abs(diff) > 0.04:
            half = (near + far) / 2
            k = np.nonzero((depths > 4) & ((lum_s[j] - half) * np.sign(diff) < 0))[0]
            if len(k):
                wdt = float(depths[k[0]])
        out.append(dict(near=near, far=far, diff=diff, band_width_px=wdt))
    return out


names = ["hookside", "hookinner", "outer", "trailing"]
bevel = {}
strips_for_png = []
for q in range(4):
    Q = R1["quarters_contour_idx"][q]
    Qp = R1["quarters_contour_idx"][(q - 1) % 4]
    edges = dict(hookside=(Qp["junction"], Qp["next_root"]),
                 hookinner=(Qp["next_root"], Q["tip"]),
                 outer=(Q["tip"], Q["armend"]),
                 trailing=(Q["armend"], Q["junction"]))
    for nm, (i0, i1) in edges.items():
        strip, lum_s, pos = edge_strip(i0, i1)
        if strip is None:
            bevel["q%d_%s" % (q, nm)] = dict(error="orientation")
            continue
        bm = band_measure(lum_s)
        bevel["q%d_%s" % (q, nm)] = dict(
            edge_len_px=float((arc[i1] - arc[i0]) % L_total),
            band_diff_median=float(np.median([b["diff"] for b in bm])),
            band_width_px=[None if math.isnan(b["band_width_px"]) else round(b["band_width_px"], 1) for b in bm],
            band_diff=[round(b["diff"], 3) for b in bm],
            near=[round(b["near"], 3) for b in bm], far=[round(b["far"], 3) for b in bm])
        strips_for_png.append(("q%d_%s" % (q, nm), strip))
OUT["bevel_edges"] = bevel

# strip montage: rows = edge type (hookside, hookinner, outer, trailing), columns = quarter.
# Inside each tile: vertical axis = position along the edge (tip end at top for 'outer'/'hookinner'),
# horizontal axis = depth into the metal from the silhouette edge (0.5 px per column, 0..70 px).
SC = 4
order = ["hookside", "hookinner", "outer", "trailing"]
dct = dict(strips_for_png)
tiles = []
for nm in order:
    row = []
    for q in range(4):
        key = "q%d_%s" % (q, nm)
        st = dct.get(key)
        img = np.repeat(st, SC, axis=0) if st is not None else np.zeros((40 * SC, len(depths), 3), np.float32)
        row.append(img)
        row.append(np.ones((40 * SC, 8, 3), np.float32))
    tiles.append(np.concatenate(row, 1))
    tiles.append(np.ones((8, tiles[-1].shape[1], 3), np.float32))
M = np.concatenate(tiles, 0)
M = np.repeat(np.repeat(M, 2, 0), 2, 1)
C.save_png(M, os.path.join(C.OUT, "edge_strips.png"))
json.dump(dict(rows=order, cols=["q0", "q1", "q2", "q3"], depth_px_per_col=float(ds_step),
               positions_per_tile=40, scale=2), open(os.path.join(C.OUT, "edge_strips_key.json"), "w"), indent=1)

# ---------------- debug overlay ----------------
ov = (rgb * 0.75).copy()
e = mask & ~C.erode(mask, 2)
ov[e] = [1, 0, 0]
ec = cmask & ~C.erode(cmask, 2)
ov[ec & ~e] = [1.0, 0.85, 0.0]


def draw_line(p0, p1, col, thick=2):
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1])) * 2) + 2
    t = np.linspace(0, 1, n)
    xs = np.round(p0[0] + (p1[0] - p0[0]) * t).astype(int)
    ys = np.round(p0[1] + (p1[1] - p0[1]) * t).astype(int)
    for dx in range(-thick, thick + 1):
        for dy in range(-thick, thick + 1):
            X = np.clip(xs + dx, 0, w - 1); Y = np.clip(ys + dy, 0, h - 1)
            ov[Y, X] = col


def draw_cross(p, col, s=18, thick=2):
    draw_line((p[0] - s, p[1]), (p[0] + s, p[1]), col, thick)
    draw_line((p[0], p[1] - s), (p[0], p[1] + s), col, thick)


draw_cross((cx, cy), [1, 1, 0], 60, 3)
for q in range(4):
    Q = R1["quarters_xy_img"][q]
    draw_cross(Q["tip"], [0, 1, 1], 30, 3)
    draw_cross(Q["armend"], [1, 0, 1], 22, 2)
    draw_cross(Q["junction"], [0.2, 0.6, 1], 22, 2)
    draw_cross(Q["next_root"], [0.2, 1, 0.2], 22, 2)
    # arm axis
    a = np.array(G["frames"][q]["a"])
    draw_line((cx, cy), (cx + a[0] * 1250, cy - a[1] * 1250), [1, 1, 0], 1)
C.save_png(ov[::2, ::2], os.path.join(C.OUT, "debug_overlay_half.png"))
C.save_png(ov, os.path.join(C.OUT, "debug_overlay_full.png"))

# ---------------- r(theta) plot ----------------
TH, r_out, r_fe, ncr = rth[:, 0], rth[:, 1], rth[:, 2], rth[:, 3]
PW, PH = 1800, 700
plot = np.ones((PH, PW, 3), np.float32)
rmaxp = r_out.max() * 1.05
for i in range(len(TH)):
    xp = int(i * PW / len(TH))
    yp = PH - 1 - int(r_out[i] / rmaxp * (PH - 40))
    plot[max(yp - 1, 0):yp + 2, xp] = [0.8, 0.1, 0.1]
    yf = PH - 1 - int(r_fe[i] / rmaxp * (PH - 40))
    plot[max(yf - 1, 0):yf + 2, xp] = [0.1, 0.3, 0.9]
for g in range(0, 361, 45):  # grid every 45 deg
    xp = int(g / 360 * PW) % PW
    plot[:, xp] = [0.75, 0.75, 0.75]
for t in R1["tips_angle_deg"]:
    xp = int(t / 360 * PW) % PW
    plot[:, max(xp - 1, 0):xp + 2] = [0, 0.7, 0.7]
C.save_png(plot, os.path.join(C.OUT, "r_theta_plot.png"))

json.dump(OUT, open(os.path.join(C.OUT, "measure2.json"), "w"), indent=1, default=float)
print("corner fillets", [(c['kind'][:9], c['n_offline'], round(c.get('fillet_radius_px', -1), 1), round(c.get('fillet_rms_px', -1), 2)) for c in corner_fits])
print("outer arcs", [(f['q'], round(f['radius_px'], 1), round(f['rms_px'], 2), f['bulge_outward']) for f in outer_fits])
for k, v in bevel.items():
    if 'error' in v:
        print(k, v); continue
    print(k, "len %.0f diff_med %+.3f widths" % (v["edge_len_px"], v["band_diff_median"]), v["band_width_px"][::5])
