"""Interior features: dark unground panels (central diamond + blade lenses), bevel band widths, ridge, hole check, colours."""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
rgb = load().astype(np.float64)
h, w, _ = rgb.shape
v_, S = hsv(rgb)
L = rgb @ np.array([0.2126, 0.7152, 0.0722])
Fs = np.load(ROOT + "Fs.npy").astype(np.float64)
m = np.load(ROOT + "mask_refined.npy")
Q = np.load(ROOT + "contour_refined.npy")
O = json.load(open(ROOT + "outline_measurements.json"))
c0 = np.array(O["centre_px"])
axes = {k: np.array([np.cos(np.radians(v["dir_deg_imagecoords"])), np.sin(np.radians(v["dir_deg_imagecoords"]))]) for k, v in O["axes"].items()}
SPAN = O["tips"]["left"]["R_contour_px"] + O["tips"]["right"]["R_contour_px"]
FT = float(sys.argv[1]) if len(sys.argv) > 1 else 0.035
R = {"panel_F_threshold": FT, "span_ref_px": SPAN}
panel = (Fs < FT) & m & (L < 0.33)
panel = dilate(erode(panel, 2), 2)
panel = erode(dilate(panel, 3), 3) & m
lab, n = label(panel)
sizes = np.bincount(lab.ravel()); sizes[0] = 0
comps = [k for k in range(1, n + 1) if sizes[k] > 300]
np.save(ROOT + "panel_mask.npy", panel)
# ---------- central diamond ----------
cy, cx = int(round(c0[1])), int(round(c0[0]))
kd = lab[cy, cx]
dia = lab == kd
R["diamond_area_px"] = int(dia.sum())
yy, xx = np.nonzero(dia)
R["diamond_centroid_px"] = [round(float(xx.mean()), 1), round(float(yy.mean()), 1)]
R["diamond_centroid_offset_from_axes_centre_px"] = round(float(np.hypot(xx.mean() - c0[0], yy.mean() - c0[1])), 1)
P = moore_trace(dia)
Pd = resample_closed(smooth_closed(P, 1.5), 1.0)
np.save(ROOT + "diamond_contour.npy", Pd)
rel = Pd - c0
verts = {}
for name, d in axes.items():
    u = rel @ d; i = int(np.argmax(u)); verts[name] = (i, Pd[i], float(u[i]))
R["diamond_vertex_dist_from_centre_px"] = {k: round(v[2], 1) for k, v in verts.items()}
R["diamond_diagonal_horizontal_px"] = round(float(np.linalg.norm(verts["left"][1] - verts["right"][1])), 1)
R["diamond_diagonal_vertical_px"] = round(float(np.linalg.norm(verts["top"][1] - verts["bottom"][1])), 1)
# sides between consecutive vertices (right->bottom->left->top) along the contour
order = ["right", "bottom", "left", "top"]
sides = {}
for a, b in zip(order, order[1:] + order[:1]):
    ia, ib = verts[a][0], verts[b][0]
    # walk the shorter way that stays in the sector between the two axes
    idx1 = np.arange(ia, ib + (len(Pd) if ib < ia else 0) + 1) % len(Pd)
    idx2 = np.arange(ib, ia + (len(Pd) if ia < ib else 0) + 1) % len(Pd)
    bis = axes[a] + axes[b]; bis /= np.linalg.norm(bis)
    idx = idx1 if ((Pd[idx1] - c0) @ bis).mean() > ((Pd[idx2] - c0) @ bis).mean() else idx2
    k = len(idx); core = idx[int(0.12 * k):int(0.88 * k)]
    pts = Pd[core]
    c, r, rms = fit_circle(pts); cl, dl, rl = fit_line(pts)
    A = Pd[idx[0]]; B = Pd[idx[-1]]
    dd = (B - A) / np.linalg.norm(B - A); nn = np.array([-dd[1], dd[0]])
    if nn @ (c0 - (A + B) / 2) < 0: nn = -nn     # nn points toward diamond centre
    sag = (Pd[idx] - A) @ nn
    s = float(sag[np.argmax(np.abs(sag))])
    # concave side: curve bulges toward the centre (positive sagitta toward centre)
    sides[f"{a}-{b}"] = {"chord_px": round(float(np.linalg.norm(B - A)), 1), "sagitta_toward_centre_px": round(s, 2),
                         "circle_radius_px": round(r, 1), "circle_rms_px": round(rms, 2), "line_rms_px": round(rl, 2),
                         "circle_centre_px": c.round(1).tolist(), "arc_centre_dist_from_piece_centre_px": round(float(np.linalg.norm(c - c0)), 1)}
    # interior angle at vertex a from lines fitted to 25% of each adjacent side
R["diamond_sides"] = sides
# vertex angles: lines fitted to the first 30% of each side leaving the vertex
vang = {}
for name in order:
    i = verts[name][0]
    fw = Pd[(i + np.arange(3, 25)) % len(Pd)]; bw = Pd[(i - np.arange(3, 25)) % len(Pd)]
    c1, d1, _ = fit_line(fw); c2, d2, _ = fit_line(bw)
    if d1 @ (fw.mean(0) - Pd[i]) < 0: d1 = -d1
    if d2 @ (bw.mean(0) - Pd[i]) < 0: d2 = -d2
    vang[name] = round(float(np.degrees(np.arccos(np.clip(d1 @ d2, -1, 1)))), 1)
R["diamond_vertex_angles_deg_3to25px"] = vang
# ---------- lens panels per arm ----------
lens = {}; lensmask = {}
for name, d in axes.items():
    p = np.array([-d[1], d[0]])
    best = None
    for k in comps:
        if k == kd: continue
        ys, xs = np.nonzero(lab == k)
        rel = np.stack([xs, ys], 1) - c0
        u = rel @ d; vv = rel @ p
        if u.mean() > 150 and np.abs(vv).mean() < 100:
            if best is None or sizes[k] > best[0]:
                best = (sizes[k], k, u, vv)
    if best is None:
        lens[name] = None; continue
    s, k, u, vv = best
    ub = np.round(u).astype(int)
    widths = {}
    for uu in range(ub.min(), ub.max() + 1):
        sel = ub == uu
        if sel.sum(): widths[uu] = (vv[sel].min(), vv[sel].max())
    us = np.array(sorted(widths)); wd = np.array([widths[x][1] - widths[x][0] + 1 for x in us])
    im = int(np.argmax(wd))
    lensmask[name] = lab == k
    lens[name] = {"area_px": int(s), "u_start_px": int(us.min()), "u_end_px": int(us.max()), "length_px": int(us.max() - us.min()),
                  "max_width_px": int(wd[im]), "max_width_at_u_px": int(us[im]),
                  "v_extent_at_max_px": [round(float(widths[us[im]][0]), 1), round(float(widths[us[im]][1]), 1)],
                  "centroid_v_px": round(float(vv.mean()), 1)}
R["lens_panels"] = lens
# ---------- bevel band widths along arms ----------
bands = {}
for name, d in axes.items():
    p = np.array([-d[1], d[0]])
    Rt = O["tips"][name]["R_contour_px"]
    rows = []
    for uu in np.arange(100, Rt - 5, 5.0):
        t = line_poly_intersections(Q, c0 + uu * d, p)
        neg = t[t < 0]; pos = t[t > 0]
        if len(neg) == 0 or len(pos) == 0: continue
        e0, e1 = neg.max(), pos.min()
        vs = np.arange(e0, e1, 0.5)
        X = c0[0] + uu * d[0] + vs * p[0]; Y = c0[1] + uu * d[1] + vs * p[1]
        pm_ = (lensmask[name] if name in lensmask else np.zeros_like(panel)) | dia
        pn = bilinear(pm_.astype(float), X, Y) > 0.5
        if pn.any():
            a0 = vs[pn].min(); a1 = vs[pn].max()
            rows.append((uu, e0, e1, a0, a1, a0 - e0, e1 - a1))
        else:
            rows.append((uu, e0, e1, np.nan, np.nan, np.nan, np.nan))
    rows = np.array(rows)
    bands[name] = rows
np.save(ROOT + "band_rows.npy", bands, allow_pickle=True)
bsum = {}
for name, rows in bands.items():
    Rt = O["tips"][name]["R_contour_px"]
    has = ~np.isnan(rows[:, 3])
    out = {"panel_present_u_ranges_px": []}
    # contiguous ranges
    if has.any():
        idx = np.nonzero(has)[0]
        groups = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
        out["panel_present_u_ranges_px"] = [[float(rows[g[0], 0]), float(rows[g[-1], 0])] for g in groups if len(g) >= 2]
    for f in (0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9):
        j = np.argmin(np.abs(rows[:, 0] - f * Rt))
        r_ = rows[j]
        out[f"at_{f}R"] = {"u": float(r_[0]), "width": round(float(r_[2] - r_[1]), 1),
                           "band_neg_v": None if np.isnan(r_[5]) else round(float(r_[5]), 1),
                           "band_pos_v": None if np.isnan(r_[6]) else round(float(r_[6]), 1),
                           "panel_width": None if np.isnan(r_[3]) else round(float(r_[4] - r_[3]), 1)}
    bsum[name] = out
R["bevel_bands"] = bsum
# ---------- ridge line in the necks (horizontal arms: shadow bevel vs lit bevel boundary via luminance step) ----------
ridge = {}
Ls = L.copy()
for name in ("left", "right", "top", "bottom"):
    d = axes[name]; p = np.array([-d[1], d[0]])
    rr = []
    for uu in np.arange(120, 330, 10.0):
        t = line_poly_intersections(Q, c0 + uu * d, p)
        neg = t[t < 0]; pos = t[t > 0]
        if len(neg) == 0 or len(pos) == 0: continue
        e0, e1 = neg.max(), pos.min()
        vs = np.arange(e0 + 4, e1 - 4, 0.5)
        X = c0[0] + uu * d[0] + vs * p[0]; Y = c0[1] + uu * d[1] + vs * p[1]
        prof = bilinear(Ls, X, Y)
        k = np.exp(-np.arange(-6, 7) ** 2 / 8.0); k /= k.sum()
        ps = np.convolve(np.pad(prof, 6, mode="edge"), k, "valid")
        g = np.gradient(ps)
        j = int(np.argmax(np.abs(g)))
        rr.append((uu, e0, e1, vs[j], g[j] * 2, ps[:len(ps)//3].mean(), ps[-len(ps)//3:].mean()))
    rr = np.array(rr)
    ridge[name] = {"ridge_v_mean_px": round(float(rr[:, 3].mean()), 1), "ridge_v_sd_px": round(float(rr[:, 3].std()), 1),
                   "edge_mid_v_mean_px": round(float(((rr[:, 1] + rr[:, 2]) / 2).mean()), 1),
                   "max_L_step_per_px_mean": round(float(np.abs(rr[:, 4]).mean()), 4),
                   "L_side_neg_mean": round(float(rr[:, 5].mean()), 3), "L_side_pos_mean": round(float(rr[:, 6].mean()), 3)}
R["neck_ridge"] = ridge
# ---------- centre hole check ----------
Mq = np.load(ROOT + "Mqs.npy").astype(np.float64)
bgf = np.load(ROOT + "bgfit.npy").astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
bglike = (Mq < 3.0) & (np.abs(L - bgf) < 0.06)
inner = erode(m, 3)
cand = bglike & inner
lab2, n2 = label(cand)
s2 = np.bincount(lab2.ravel()); s2[0] = 0
R["hole_check"] = {"bg_like_pixels_inside_piece": int(cand.sum()), "largest_bg_like_component_px": int(s2.max()) if n2 else 0,
                   "bg_like_pixels_within_60px_of_centre": int(cand[cy - 60:cy + 61, cx - 60:cx + 61].sum()),
                   "centre_region_mean_srgb": rgb[cy - 25:cy + 26, cx - 25:cx + 26].reshape(-1, 3).mean(0).round(3).tolist(),
                   "centre_region_L": round(float(L[cy - 25:cy + 26, cx - 25:cx + 26].mean()), 3),
                   "local_background_L_fit": round(float(bgf[cy, cx]), 3)}
if n2:
    kk = int(np.argmax(s2)); ys, xs = np.nonzero(lab2 == kk)
    R["hole_check"]["largest_component_centroid_px"] = [round(float(xs.mean()), 1), round(float(ys.mean()), 1)]
# ---------- colours ----------
def hexc(c): return "#" + "".join(f"{int(round(x * 255)):02x}" for x in c)
cls = {"panel (dark flat)": panel & erode(m, 3)}
lit = m & ~panel & (L > 0.36) & (Fs > 0.06)
shade = m & ~panel & (L < 0.26) & (Fs > 0.12)
cls["lit bevel faces"] = lit; cls["shadow-side bevel faces"] = shade
cls["whole piece"] = m
col = {}
for k, mm in cls.items():
    c = rgb[mm].mean(0); med = np.median(rgb[mm], 0)
    col[k] = {"mean_srgb": c.round(3).tolist(), "hex_mean": hexc(c), "hex_median": hexc(med), "frac_of_piece": round(float(mm.sum() / m.sum()), 3)}
R["colours"] = col
json.dump(R, open(ROOT + f"interior_measurements_F{FT}.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in R.items()}, indent=1, default=float))
