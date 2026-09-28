"""Tip angles with windows referenced to the extrapolated (line-intersection) apex, top-tip extrapolation,
spans, and neck->blade inflection (max slope of the half-width profile). Usage: tips_inflection.py [contour] [json_out]"""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
CF = sys.argv[1] if len(sys.argv) > 1 else "contour_refined.npy"
OUT = sys.argv[2] if len(sys.argv) > 2 else "tips_inflection.json"
OM = sys.argv[3] if len(sys.argv) > 3 else "outline_measurements.json"
Q = np.load(ROOT + CF)
O = json.load(open(ROOT + OM))
c0 = np.array(O["centre_px"])
axes = {k: np.array([np.cos(np.radians(v["dir_deg_imagecoords"])), np.sin(np.radians(v["dir_deg_imagecoords"]))]) for k, v in O["axes"].items()}
border = Q[:, 1] < 2.5
R = {"contour": CF}
def uv(name):
    d = axes[name]; p = np.array([-d[1], d[0]]); rel = Q - c0; return rel @ d, rel @ p
def line_pair(u, v, lo_u, hi_u):
    a = np.stack([u, v], 1)
    A = a[(v < 0) & (u >= lo_u) & (u <= hi_u) & ~border]; B = a[(v > 0) & (u >= lo_u) & (u <= hi_u) & ~border]
    if len(A) < 6 or len(B) < 6: return None
    ca, da, ra = fit_line(A); cb, db, rb = fit_line(B)
    if da[0] < 0: da = -da
    if db[0] < 0: db = -db
    inc = abs(np.degrees(np.arctan2(da[1], da[0]) - np.arctan2(db[1], db[0])))
    st = np.linalg.solve(np.array([da, -db]).T, cb - ca); apex = ca + st[0] * da
    return inc, apex, ra, rb, len(A), len(B), np.degrees(np.arctan2(da[1], da[0])), np.degrees(np.arctan2(db[1], db[0]))
tips = {}
for name in axes:
    u, v = uv(name)
    sel = (np.abs(v) < 60) & ~border
    u_cont = float(u[sel].max())                 # rounded apex on the contour (or the last non-border point)
    trunc = bool(O["tips"][name]["truncated"])
    u_last = float(u[(np.abs(v) < 120) & ~border].max())
    # reference apex: line fit 10..60 px back from the last available edge point, iterate to the line apex
    fit = line_pair(u, v, u_last - 60, u_last - 10)
    apex_u = fit[1][0]
    for _ in range(5):
        base = min(apex_u, u_last + 1e9)
        fit = line_pair(u, v, apex_u - 70, apex_u - 15) if not trunc else line_pair(u, v, u_last - 60, u_last - 5)
        apex_u = fit[1][0]
    res = {"truncated_by_image_edge": trunc, "u_contour_apex_px": round(u_cont, 1), "u_line_apex_px": round(float(apex_u), 1),
           "apex_rounding_px": None if trunc else round(float(apex_u - u_cont), 1), "windows": {}}
    for lo, hi in ((10, 30), (15, 45), (15, 60), (20, 80), (30, 100), (40, 130)):
        if trunc and apex_u - hi < 0: continue
        f = line_pair(u, v, apex_u - hi, apex_u - lo)
        if f is None or (trunc and apex_u - lo > u_last + 0.5):
            res["windows"][f"{lo}-{hi}"] = None; continue
        res["windows"][f"{lo}-{hi}"] = {"included_deg": round(f[0], 2), "edge_dir_deg": [round(f[6], 2), round(f[7], 2)],
                                          "rms_px": [round(f[2], 2), round(f[3], 2)], "n": [f[4], f[5]], "apex_v_px": round(float(f[1][1]), 1)}
    tips[name] = res
# top tip: estimate the rounded-apex position = its line apex minus the mean rounding of the other three tips
rounding = [tips[k]["apex_rounding_px"] for k in tips if tips[k]["apex_rounding_px"] is not None]
mr = float(np.mean(rounding))
for k in tips:
    if tips[k]["truncated_by_image_edge"]:
        tips[k]["u_contour_apex_estimated_px"] = round(tips[k]["u_line_apex_px"] - mr, 1)
        tips[k]["u_visible_to_image_edge_px"] = O["tips"][k]["R_contour_px"]
R["mean_apex_rounding_px"] = round(mr, 2)
R["tips"] = tips
def Ru(k, which):
    t = tips[k]
    if which == "line": return t["u_line_apex_px"]
    return t.get("u_contour_apex_estimated_px", t["u_contour_apex_px"])
R["span_horizontal_contour_px"] = round(Ru("left", "c") + Ru("right", "c"), 1)
R["span_vertical_contour_px_top_estimated"] = round(Ru("top", "c") + Ru("bottom", "c"), 1)
R["span_vertical_visible_px_to_image_edge"] = round(O["tips"]["top"]["R_contour_px"] + Ru("bottom", "c"), 1)
R["span_horizontal_line_apex_px"] = round(Ru("left", "line") + Ru("right", "line"), 1)
R["span_vertical_line_apex_px"] = round(Ru("top", "line") + Ru("bottom", "line"), 1)
# ---- inflection: max slope of the smoothed half-width profile between neck minimum and blade maximum ----
infl = {}
for name in axes:
    u, v = uv(name)
    out = {}
    for side, sg in (("neg_v", -1), ("pos_v", 1)):
        sel = (np.sign(v) == sg) & (np.abs(v) < 130) & (u > 60) & ~border
        uu, vv = u[sel], np.abs(v[sel]); o = np.argsort(uu); uu, vv = uu[o], vv[o]
        grid = np.arange(np.ceil(uu.min()), np.floor(uu.max()))
        vg = np.interp(grid, uu, vv)
        k = np.exp(-np.arange(-30, 31) ** 2 / (2 * 12.0 ** 2)); k /= k.sum()
        vs = np.convolve(np.pad(vg, 30, mode="edge"), k, "valid")
        d1 = np.gradient(vs); d2 = np.gradient(d1)
        bm = (grid > 300) & (grid < grid.max() - 60)
        ubm = grid[bm][np.argmax(vs[bm])]
        nk = (grid > 110) & (grid < ubm)
        unm = grid[nk][np.argmin(vs[nk])]
        seg = (grid > unm) & (grid < ubm)
        ui = grid[seg][np.argmax(d1[seg])]
        # convex part: where d2<0 beyond inflection; concave where d2>0 before it
        out[side] = {"u_neck_min": float(unm), "u_inflection_max_slope": float(ui), "max_slope_dv_du": round(float(d1[seg].max()), 3),
                     "flank_angle_at_inflection_deg": round(float(np.degrees(np.arctan(d1[seg].max()))), 1), "u_blade_max": float(ubm),
                     "half_width_neck_px": round(float(vs[grid == unm][0]), 1), "half_width_blade_px": round(float(vs[grid == ubm][0]), 1)}
    infl[name] = out
R["inflection"] = infl
json.dump(R, open(ROOT + OUT, "w"), indent=1)
print(json.dumps(R, indent=1))
