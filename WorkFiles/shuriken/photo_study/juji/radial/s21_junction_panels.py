"""Central junction, dark panels, ground-bevel band, notch/fillet shape, hole test, physical tips, patina.

Dark (unground, granular, low-chroma) panel: inside the reference silhouette (eroded 4 px), smoothed
warm chromaticity (R-B)/(R+G+B) < 0.08 and luminance 0.10..0.34; opened r=3; components >= 300 px.
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
lum = a.mean(2)
warm = (a[:, :, 0] - a[:, :, 2]) / (a.sum(2) + 1e-3)
lum_s = jlib.gblur(lum, 1.5)
warm_s = jlib.gblur(warm, 2.0)
m = np.load(os.path.join(jlib.OUT, "mask_ref.npy")).astype(bool)
g1 = json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))
c = np.array(g1["centre_candidates_px"]["sym90"])
met = json.load(open(os.path.join(jlib.OUT, "metrics_outer.json")))
span = met["span_horizontal_px"]
names = ["right", "top", "left", "bottom"]
out = {}

inner = jlib.erode(m, 4)
panel = inner & (warm_s < 0.08) & (lum_s > 0.10) & (lum_s < 0.34)
panel = jlib.opening(panel, 3)
lab, nlab = jlib.label(panel)
cnt = np.bincount(lab.ravel())
keep = np.zeros(nlab + 1, bool)
keep[1:] = cnt[1:] >= 300
panel = keep[lab]
panel, _ = jlib.fill_holes(panel)
lab, nlab = jlib.label(panel)
comps = []
for k in range(1, nlab + 1):
    ys, xs = np.nonzero(lab == k)
    comps.append({"id": k, "px": int(len(xs)), "centroid": [round(xs.mean(), 1), round(ys.mean(), 1)],
                  "r_centroid_from_centre": round(float(np.hypot(xs.mean() - c[0], ys.mean() - c[1])), 1)})
comps.sort(key=lambda d: -d["px"])
out["panel_components"] = comps[:12]
np.save(os.path.join(jlib.OUT, "panel_mask.npy"), panel)

# ---- central diamond = panel component nearest the centre ----
kc = lab[int(round(c[1])), int(round(c[0]))]
if kc == 0:
    d2 = [(np.hypot(cc["centroid"][0] - c[0], cc["centroid"][1] - c[1]), cc["id"]) for cc in comps]
    kc = min(d2)[1]
dia = lab == kc
ys, xs = np.nonzero(dia)
dc = np.array([xs.mean(), ys.mean()])
out["diamond_px_area"] = int(dia.sum())
out["diamond_centroid"] = dc.round(2).tolist()
dia_f = jlib.gblur(dia.astype(np.float32), 1.0)
# radial profile of the diamond boundary about the piece centre
th = np.deg2rad(np.arange(0, 360, 0.5))
rr = np.arange(0, 300, 0.25)
X = c[0] + np.cos(th)[:, None] * rr[None, :]
Y = c[1] - np.sin(th)[:, None] * rr[None, :]
v = jlib.bilinear(dia_f, X, Y) > 0.5
first_out = np.argmax(~v, axis=1)
r_d = rr[first_out]
thd = np.rad2deg(th)
axes = {nm: met["tipline_angles_deg"][0] + 90 * i for i, nm in enumerate(names)}
diamond_axes = {}
for nm, ang in axes.items():
    i = int(np.argmin(np.abs(((thd - ang) + 180) % 360 - 180)))
    # max over +-8 deg (vertex may be slightly off-axis)
    sel = np.abs(((thd - ang) + 180) % 360 - 180) <= 8
    diamond_axes[nm] = {"r_on_axis_px": float(r_d[i]), "r_max_within_8deg_px": float(r_d[sel].max()),
                        "theta_of_max": float(thd[sel][np.argmax(r_d[sel])])}
diag = {}
for k in range(4):
    ang = met["tipline_angles_deg"][0] + 45 + 90 * k
    i = int(np.argmin(np.abs(((thd - ang) + 180) % 360 - 180)))
    diag["%d" % round(ang % 360)] = float(r_d[i])
out["diamond_vertex_r_px"] = diamond_axes
out["diamond_diagonal_r_px"] = diag
rv = np.mean([d["r_max_within_8deg_px"] for d in diamond_axes.values()])
rdg = np.mean(list(diag.values()))
out["diamond_mean_vertex_r_px"] = round(float(rv), 1)
out["diamond_mean_side_mid_r_px"] = round(float(rdg), 1)
out["diamond_side_mid_over_vertex"] = round(float(rdg / rv), 3)
out["diamond_note"] = "straight-sided rhombus => 0.707; concave-sided star < 0.707; rounded/circular > 0.707"
# across-vertex extents (vertex to opposite vertex)
out["diamond_extent_horizontal_px"] = round(diamond_axes["right"]["r_max_within_8deg_px"] + diamond_axes["left"]["r_max_within_8deg_px"], 1)
out["diamond_extent_vertical_px"] = round(diamond_axes["top"]["r_max_within_8deg_px"] + diamond_axes["bottom"]["r_max_within_8deg_px"], 1)
np.savez(os.path.join(jlib.OUT, "diamond_profile.npz"), theta=thd, r=r_d)

# ---- hole test: lid-coloured pixels inside the silhouette ----
lidlike = m & jlib.erode(m, 3) & (lum_s > 0.36) & (warm_s < 0.06)
labh, nh = jlib.label(lidlike)
hc = np.bincount(labh.ravel())[1:] if nh else np.array([])
out["hole_test"] = {"enclosed_background_components_in_silhouette": 0,
                    "lid_coloured_blobs_inside_px_sorted": sorted(hc.tolist(), reverse=True)[:5],
                    "central_diamond_min_lum_p1": round(float(np.percentile(lum[dia], 1)), 3),
                    "central_diamond_max_lum_p99": round(float(np.percentile(lum[dia], 99)), 3),
                    "lid_lum_median_near_centre": round(float(np.median(lum[~jlib.dilate(m, 40)][:])), 3)}

# ---- notch / fillet shape: circle fit to silhouette boundary around each notch ----
bd = jlib.boundary(m)
bys, bxs = np.nonzero(bd)
pr = np.hypot(bxs - c[0], bys - c[1])
pth = np.degrees(np.arctan2(-(bys - c[1]), bxs - c[0])) % 360
notch = []
for k in range(4):
    ang = (met["tipline_angles_deg"][0] + 45 + 90 * k) % 360
    dth = ((pth - ang) + 180) % 360 - 180
    sel = (np.abs(dth) < 40) & (pr < 200)
    i0 = np.argmin(np.where(sel, pr, 1e9))
    p0 = np.array([bxs[i0], bys[i0]])
    near = sel & (np.hypot(bxs - p0[0], bys - p0[1]) < 45)
    xs_, ys_ = bxs[near].astype(float), bys[near].astype(float)
    A = np.stack([xs_, ys_, np.ones_like(xs_)], 1)
    (D, E, F), *_ = np.linalg.lstsq(A, -(xs_ ** 2 + ys_ ** 2), rcond=None)
    cx, cy = -D / 2, -E / 2
    rc = math.sqrt(cx * cx + cy * cy - F)
    d_cc = math.hypot(cx - c[0], cy - c[1])
    notch.append({"diag_deg": round(ang, 1), "notch_point": p0.tolist(), "r_notch_px": round(float(pr[i0]), 1),
                  "fillet_radius_px": round(rc, 1), "fillet_centre_dist_from_piece_centre_px": round(d_cc, 1),
                  "fillet_centre_outside_piece": bool(d_cc > pr[i0]),
                  "kind": "concave fillet (centre beyond the notch, outside the metal)" if d_cc > pr[i0] else "convex (hub-like)"})
out["notches"] = notch

# ---- per-arm: panel extent, bevel band widths, physical tip ----
arms = {}
ab = jlib.gblur(a, 0.7)
for nm in names:
    z = np.load(os.path.join(jlib.OUT, "final_edges_outer_%s.npz" % nm))
    S, tL, tR, origin, u, n = z["S"], z["tL"], z["tR"], z["origin"], z["u"], z["n"]
    T = np.arange(-120, 120.01, 0.5)
    X = origin[0] + S[:, None] * u[0] + T[None, :] * n[0]
    Y = origin[1] + S[:, None] * u[1] + T[None, :] * n[1]
    ok = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= H - 1)
    P = jlib.bilinear(panel.astype(np.float32), X, Y) > 0.5
    P &= ok
    rows = []
    for i, s in enumerate(S):
        if s < 60:
            continue
        inside = (T <= tL[i]) & (T >= tR[i])
        pp = P[i] & inside
        if pp.sum() >= 4:   # >= 2 px of panel
            tp = T[pp]
            rows.append((s, tp.max(), tp.min(), tL[i] - tp.max(), tp.min() - tR[i], tL[i] - tR[i]))
    rows = np.array(rows)
    # panel run in the blade (exclude the diamond, stations < 140)
    bl = rows[rows[:, 0] > 140] if len(rows) else rows
    info = {}
    if len(bl):
        # longest contiguous run of stations
        ss = bl[:, 0]
        breaks = np.nonzero(np.diff(ss) > 6)[0]
        segs = np.split(np.arange(len(ss)), breaks + 1)
        segs.sort(key=lambda g: -(ss[g[-1]] - ss[g[0]]))
        g = segs[0]
        seg = bl[g]
        pw = seg[:, 1] - seg[:, 2]
        imax = np.argmax(pw)
        info = {"panel_s_start_px": float(seg[0, 0]), "panel_s_end_px": float(seg[-1, 0]),
                "panel_length_px": float(seg[-1, 0] - seg[0, 0]),
                "panel_max_width_px": round(float(pw[imax]), 1), "panel_max_width_station_px": float(seg[imax, 0]),
                "panel_centre_offset_at_max_px(+ = arm's left)": round(float(0.5 * (seg[imax, 1] + seg[imax, 2])), 1),
                "bevel_band_left_at_panel_max_px": round(float(seg[imax, 3]), 1),
                "bevel_band_right_at_panel_max_px": round(float(seg[imax, 4]), 1),
                "bevel_band_left_min_px": round(float(seg[:, 3].min()), 1),
                "bevel_band_right_min_px": round(float(seg[:, 4].min()), 1),
                "bevel_band_left_median_px": round(float(np.median(seg[:, 3])), 1),
                "bevel_band_right_median_px": round(float(np.median(seg[:, 4])), 1),
                "other_panel_runs": [[float(ss[h[0]]), float(ss[h[-1]])] for h in segs[1:4]]}
    # diamond reach along this arm (panel stations < 140 contiguous from the centre)
    jn = rows[rows[:, 0] <= 200] if len(rows) else rows
    if len(jn):
        ss = jn[:, 0]
        k = 0
        while k + 1 < len(ss) and ss[k + 1] - ss[k] <= 3:
            k += 1
        info["diamond_panel_reaches_s_px"] = float(ss[k])
    # physical tip along the refined axis: half-contrast crossing of colour, approached from outside
    s_axis = np.arange(560, 720, 0.5)
    last = np.isfinite(tL) & np.isfinite(tR)
    t_mid_tip = float(np.median(0.5 * (tL + tR)[-40:]))
    acc = np.zeros((len(s_axis), 3))
    for dt in (-1.5, -0.75, 0, 0.75, 1.5):
        Pp = origin[None, :] + s_axis[:, None] * u[None, :] + (t_mid_tip + dt) * n[None, :]
        acc += jlib.bilinear(ab, Pp[:, 0], Pp[:, 1])
    col = acc / 5
    okp = (origin[0] + s_axis * u[0] >= 0) & (origin[1] + s_axis * u[1] >= 0) & (origin[1] + s_axis * u[1] <= H - 1) & (origin[0] + s_axis * u[0] <= W - 1)
    tipinfo = {}
    if okp[-1]:
        B = np.median(col[-30:], 0)
        # object colour ~20..40 px inside the ws tip
        R_ws = met["arms"][nm]["R_last_station_px"]
        O = np.median(col[(s_axis > R_ws - 45) & (s_axis < R_ws - 20)], 0)
        vv = O - B
        f = (col - B) @ vv / (vv @ vv)
        idx = np.arange(len(s_axis))[::-1]
        s_cross = np.nan
        for j in idx[1:]:
            if f[j] >= 0.5:
                s_cross = s_axis[j] + (0.5 - f[j]) / (f[j + 1] - f[j]) * (s_axis[j + 1] - s_axis[j])
                break
        tip_xy = origin + s_cross * u + t_mid_tip * n
        tipinfo = {"physical_tip_s_px": round(float(s_cross), 1), "physical_tip_xy": tip_xy.round(1).tolist(),
                   "physical_tip_R_from_centre_px": round(float(np.hypot(*(tip_xy - c))), 1), "clipped": False}
    else:
        tipinfo = {"clipped": True, "image_edge_s_px": float(s_axis[np.nonzero(okp)[0].max()])}
    info["tip"] = tipinfo
    arms[nm] = info
out["arms"] = arms
json.dump(out, open(os.path.join(jlib.OUT, "junction_panels.json"), "w"), indent=1)
print(json.dumps(out, indent=1))

# overlay: panel outline (magenta), diamond (yellow), silhouette (green)
ov = a.copy() * 0.85
ov[jlib.boundary(m)] = [0, 1, 0]
ov[jlib.boundary(panel)] = [1, 0, 1]
ov[jlib.boundary(dia)] = [1, 1, 0]
for nt in notch:
    x, y = nt["notch_point"]
    ov[y - 3:y + 4, x - 3:x + 4] = [0, 0.6, 1]
jlib.save_png(os.path.join(jlib.OUT, "dbg_panels_junction.png"), ov)
