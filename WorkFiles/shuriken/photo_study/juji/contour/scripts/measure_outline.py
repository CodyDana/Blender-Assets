"""Outline measurements on the refined contour (method B: contour + primitive fitting).
Usage: measure_outline.py [contour_file] [json_out]"""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
CF = sys.argv[1] if len(sys.argv) > 1 else "contour_refined.npy"
OUT = sys.argv[2] if len(sys.argv) > 2 else "outline_measurements.json"
Q = np.load(ROOT + CF)
H, W = 1363, 1370
border = Q[:, 1] < 2.5          # top tip truncated by the image edge
R = {}
# ---------- 1. arm axes from mid-points of cross-sections ----------
c0 = np.array([690.0, 660.0])   # rough centre, refined below
def mids_along(axis_dir, origin, u_range, step=2.0):
    perp = np.array([-axis_dir[1], axis_dir[0]])
    pts = []
    for u in np.arange(u_range[0], u_range[1], step):
        o = origin + u * axis_dir
        t = line_poly_intersections(Q, o, perp)
        if len(t) < 2: continue
        neg = t[t < 0]; pos = t[t > 0]
        if len(neg) == 0 or len(pos) == 0: continue
        a, b = neg.max(), pos.min()
        if b - a > 400: continue
        pts.append(o + 0.5 * (a + b) * perp)
    return np.array(pts)
arms = {"right": np.array([1.0, 0.0]), "left": np.array([-1.0, 0.0]), "bottom": np.array([0.0, 1.0]), "top": np.array([0.0, -1.0])}
for it in range(3):
    axes = {}
    for name, d in arms.items():
        mp = mids_along(d, c0, (130, 560))
        c, dd, rms = fit_line(mp)
        if dd @ d < 0: dd = -dd
        axes[name] = (c, dd, rms, len(mp))
    # centre: least-squares intersection of the four axis lines
    A = []; b = []
    for name, (c, dd, rms, n) in axes.items():
        nrm = np.array([-dd[1], dd[0]]); A.append(nrm); b.append(nrm @ c)
    c0 = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)[0]
def ang(v): return np.degrees(np.arctan2(v[1], v[0]))
def angdiff(a, b):
    d = (a - b + 180) % 360 - 180; return d
R["centre_px"] = c0.round(2).tolist()
R["axes"] = {k: {"dir_deg_imagecoords": round(float(ang(v[1])), 3), "midline_rms_px": round(v[2], 2), "n": v[3]} for k, v in axes.items()}
# residual distance of each axis line from the common centre
for k, (c, dd, rms, n) in axes.items():
    nrm = np.array([-dd[1], dd[0]]); R["axes"][k]["axis_offset_from_centre_px"] = round(float(nrm @ (c0 - c)), 2)
a_r, a_l, a_b, a_t = (ang(axes[k][1]) for k in ("right", "left", "bottom", "top"))
R["axis_angles"] = {
    "right_vs_left_colinearity_dev_deg": round(float(angdiff(a_l, a_r + 180)), 3),
    "top_vs_bottom_colinearity_dev_deg": round(float(angdiff(a_t, a_b + 180)), 3),
    "right_to_bottom_deg": round(float(angdiff(a_b, a_r)), 3), "bottom_to_left_deg": round(float(angdiff(a_l, a_b)), 3),
    "left_to_top_deg": round(float(angdiff(a_t, a_l)), 3), "top_to_right_deg": round(float(angdiff(a_r, a_t)), 3)}
# ---------- 2. tips ----------
tips = {}
for name, (c, dd, rms, n) in axes.items():
    rel = Q - c0
    u = rel @ dd; v = rel @ np.array([-dd[1], dd[0]])
    sel = np.abs(v) < 60
    i = np.argmax(np.where(sel, u, -1e9))
    tips[name] = {"apex_contour_px": Q[i].round(2).tolist(), "R_contour_px": float(u[i]), "truncated": bool(border[i])}
# ---------- 3. width profiles & tip-angle line fits in arm frames ----------
def arm_frame(name):
    c, dd, rms, n = axes[name]; perp = np.array([-dd[1], dd[0]]); return dd, perp
def edge_points(name, u0, u1):
    """contour points of this arm with u in [u0,u1], split by side (v<0 / v>0)"""
    dd, perp = arm_frame(name)
    rel = Q - c0; u = rel @ dd; v = rel @ perp
    sel = (u >= u0) & (u <= u1) & (np.abs(v) < 150) & ~border
    return (np.stack([u[sel & (v < 0)], v[sel & (v < 0)]], 1), np.stack([u[sel & (v > 0)], v[sel & (v > 0)]], 1))
profiles = {}
for name in arms:
    dd, perp = arm_frame(name)
    us = np.arange(60, 700, 1.0); wv = []
    for u in us:
        t = line_poly_intersections(Q, c0 + u * dd, perp)
        neg = t[t < 0]; pos = t[t > 0]
        if len(neg) == 0 or len(pos) == 0: wv.append((u, np.nan, np.nan)); continue
        wv.append((u, neg.max(), pos.min()))
    wv = np.array(wv)
    profiles[name] = wv
np.save(ROOT + "width_profiles.npy", profiles, allow_pickle=True)
span = {}
arm_res = {}
for name in arms:
    wv = profiles[name]; u = wv[:, 0]; width = wv[:, 2] - wv[:, 1]
    ok = ~np.isnan(width)
    Rc = tips[name]["R_contour_px"]
    # tip line fits: windows measured back from apex (or from the image border for a truncated tip)
    dd, perp = arm_frame(name)
    s_neg, s_pos = edge_points(name, 0, 2000)
    u_end = min(s_neg[:, 0].max(), s_pos[:, 0].max())
    fits = {}
    for lo, hi in ((4, 20), (4, 30), (6, 45), (8, 60), (10, 80)):
        a = s_neg[(s_neg[:, 0] >= u_end - hi) & (s_neg[:, 0] <= u_end - lo)]
        b = s_pos[(s_pos[:, 0] >= u_end - hi) & (s_pos[:, 0] <= u_end - lo)]
        if len(a) < 5 or len(b) < 5: continue
        ca, da, ra = fit_line(a); cb, db, rb = fit_line(b)
        if da[0] < 0: da = -da
        if db[0] < 0: db = -db
        inc = abs(np.degrees(np.arctan2(da[1], da[0]) - np.arctan2(db[1], db[0])))
        # apex = intersection of the two lines (u,v frame)
        M_ = np.array([da, -db]).T
        try:
            st = np.linalg.solve(M_, cb - ca); apex = ca + st[0] * da
        except np.linalg.LinAlgError:
            apex = np.array([np.nan, np.nan])
        # bisector deviation from axis
        bis = np.degrees(np.arctan2(da[1], da[0]) + np.arctan2(db[1], db[0])) / 2
        fits[f"{lo}-{hi}px_back"] = {"included_deg": round(float(inc), 2), "apex_u_px": round(float(apex[0]), 1), "apex_v_px": round(float(apex[1]), 1),
                                    "bisector_vs_axis_deg": round(float(bis), 2), "rms_px": [round(ra, 2), round(rb, 2)], "n": [len(a), len(b)]}
    arm_res[name] = {"R_apex_contour_px": round(Rc, 1), "u_end_edges_px": round(float(u_end), 1), "tip_line_fits": fits}
    # blade maximum width and neck minimum
    blade = ok & (u > 0.45 * Rc) & (u < Rc - 5)
    ib = np.nanargmax(np.where(blade, width, np.nan))
    neck = ok & (u > 110) & (u < u[ib])
    ineck = np.nanargmin(np.where(neck, width, np.nan))
    arm_res[name].update({"blade_max_width_px": round(float(width[ib]), 1), "blade_max_at_u_px": float(u[ib]),
                          "neck_min_width_px": round(float(width[ineck]), 1), "neck_min_at_u_px": float(u[ineck]),
                          "blade_max_v_extent_px": [round(float(wv[ib, 1]), 1), round(float(wv[ib, 2]), 1)],
                          "neck_v_extent_px": [round(float(wv[ineck, 1]), 1), round(float(wv[ineck, 2]), 1)]})
    # widths at fixed fractions of R
    arm_res[name]["width_at_fraction_px"] = {}
    for f in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        j = np.argmin(np.abs(u - f * Rc))
        arm_res[name]["width_at_fraction_px"][str(f)] = None if np.isnan(width[j]) else round(float(width[j]), 1)
R["tips"] = tips
R["arms"] = arm_res
json.dump(R, open(ROOT + OUT, "w"), indent=1)
print(json.dumps({k: R[k] for k in ("centre_px", "axes", "axis_angles", "tips")}, indent=1))
for k, v in arm_res.items():
    print(k, {kk: vv for kk, vv in v.items() if kk != "tip_line_fits"})
    for kk, vv in v["tip_line_fits"].items(): print("    ", kk, vv)
