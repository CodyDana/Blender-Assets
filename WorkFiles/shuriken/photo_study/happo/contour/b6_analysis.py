# Method B step 6: silhouette lines per edge, tips, notches, centre, star-polygon comparison.
# Inputs: b5_edges.json (outer + face edge points / robust line fits at 0.030 threshold)
import sys, os, json, numpy as np
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour")
from common import *
rgb = np.load(os.path.join(OUT, "rgb.npy")).astype(np.float64)
L = np.load(os.path.join(OUT, "L.npy")).astype(np.float64)
Yc = (rgb[..., 0] + rgb[..., 1]) / 2 - rgb[..., 2]
H, W = L.shape
R = json.load(open(os.path.join(OUT, "b5_edges.json")))
names = list(R.keys())
res = dict(edges={}, tips={}, notches={})

def stations_along(e, key="pts_outer"):
    P = np.array([p for p in e[key] if p[0] == p[0]])
    return P

# ---------------------------------------------------------------- yellowness-based outer boundary (lit bevels)
def yellow_outer(e, step=2.0):
    m = np.array(e["outer_pt"]); dv = np.array(e["outer_dir"]); n = np.array(e["outer_n"])
    P = stations_along(e); s = (P - m) @ dv
    TS = np.arange(-12, 22.01, 0.25); SS = np.arange(-4, 4.01, 1.0)
    pts = []
    for s0 in np.arange(s.min(), s.max(), step):
        base = m + dv * s0
        xs = base[0] + TS[None, :] * n[0] + SS[:, None] * dv[0]; ys = base[1] + TS[None, :] * n[1] + SS[:, None] * dv[1]
        py = smooth1d(bil(Yc, xs, ys).mean(0), 1.0, 0.25)
        ybg = np.median(py[TS >= 14]); win = (TS >= -6) & (TS <= 8)
        i0 = np.nonzero(win)[0][np.argmax(py[win])]; ymax = py[i0]
        if ymax - ybg < 0.03: continue
        half = (ymax + ybg) / 2
        j = i0
        while j < len(TS) - 1 and py[j] > half: j += 1
        if j >= len(TS) - 1: continue
        t = TS[j - 1] + (py[j - 1] - half) / (py[j - 1] - py[j]) * 0.25
        pts.append(base + n * t)
    return np.array(pts)

edge_lines = {}
for name in names:
    e = R[name]
    Po = stations_along(e, "pts_outer"); Pf = stations_along(e, "pts_face")
    mo, do, ko, ro = robust_line(Po); mf, df, kf, rf = robust_line(Pf)
    u = np.array(e["outer_dir"])
    if np.dot(do, u) < 0: do = -do
    if np.dot(df, u) < 0: df = -df
    n = np.array(e["outer_n"])
    info = dict(n=n.tolist(), outer_pts=int(ko.sum()), outer_rms=float(np.sqrt(np.mean(ro ** 2))),
                face_pts=int(kf.sum()), face_rms=float(np.sqrt(np.mean(rf ** 2))))
    Py = yellow_outer(e)
    if len(Py) > 20:
        my, dy, ky, ry = robust_line(Py)
        if np.dot(dy, u) < 0: dy = -dy
        off = float(np.median((Py[ky] - mo) @ n))
        info.update(yellow_pts=int(ky.sum()), yellow_rms=float(np.sqrt(np.mean(ry ** 2))),
                    yellow_minus_outer_px=off, yellow_vs_outer_deg=float(np.degrees(np.arcsin(do[0] * dy[1] - do[1] * dy[0]))))
    else:
        my = dy = None
    edge_lines[name] = dict(outer=(mo, do), face=(mf, df), yellow=(my, dy) if my is not None else None, Po=Po[ko], Pf=Pf[kf])
    res["edges"][name] = info

# silhouette line choice per edge
SIL = {}
for name in names:
    SIL[name] = ("outer", edge_lines[name]["outer"])
# T5-N4: lit bevel of low luminance contrast -> yellowness boundary
if edge_lines["T5-N4"]["yellow"] is not None:
    SIL["T5-N4"] = ("yellow", edge_lines["T5-N4"]["yellow"])
for name in names:
    res["edges"][name]["sil_line"] = [np.asarray(SIL[name][1][0]).tolist(), np.asarray(SIL[name][1][1]).tolist()]
    res["edges"][name]["face_line"] = [edge_lines[name]["face"][0].tolist(), edge_lines[name]["face"][1].tolist()]

# ---------------------------------------------------------------- straightness (quadratic sagitta, circle fit)
for name in names:
    kind, (m, d) = SIL[name]
    P = edge_lines[name]["Po"] if kind == "outer" else yellow_outer(R[name])
    n = np.array([-d[1], d[0]])
    s = (P - m) @ d; r = (P - m) @ n
    c2 = np.polyfit(s, r, 2)
    span = s.max() - s.min()
    sag = abs(c2[0]) * (span / 2) ** 2
    C, rad, cres = circle_fit(P)
    res["edges"][name].update(sil_kind=kind, sil_len_px=float(span), sagitta_px=float(sag),
                              quad_sign=("convex" if np.sign(c2[0]) * np.sign(np.dot(n, R[name]["outer_n"])) < 0 else "concave"),
                              circlefit_radius_px=rad)

# ---------------------------------------------------------------- tips
def profile_along(P0, dvec, t0, t1, half=0.5, dt=0.25):
    TS = np.arange(t0, t1 + 1e-9, dt); nvec = np.array([-dvec[1], dvec[0]])
    SS = np.arange(-half, half + 1e-9, 0.5)
    xs = P0[0] + TS[None, :] * dvec[0] + SS[:, None] * nvec[0]; ys = P0[1] + TS[None, :] * dvec[1] + SS[:, None] * nvec[1]
    return TS, bil(L, xs, ys).mean(0), xs.mean(0), ys.mean(0)

tipV = {}; tipEnd = {}
for k in range(8):
    ea = "T%d-N%d" % (k, k); eb = "T%d-N%d" % (k, (k - 1) % 8)
    (ma, da) = SIL[ea][1]; (mb, db) = SIL[eb][1]
    V = intersect(ma, da, mb, db)
    # unit vectors from vertex toward the notches
    ua = da if np.dot(da, R[ea]["outer_dir"]) > 0 else -da
    ub = db if np.dot(db, R[eb]["outer_dir"]) > 0 else -db
    ang = angle_between(ua, ub)
    bis = -(ua + ub); bis /= np.linalg.norm(bis)
    # face-line tip angle for comparison
    (fa_m, fa_d) = edge_lines[ea]["face"]; (fb_m, fb_d) = edge_lines[eb]["face"]
    ang_face = angle_between(fa_d if np.dot(fa_d, ua) > 0 else -fa_d, fb_d if np.dot(fb_d, ub) > 0 else -fb_d)
    # actual tip end along bisector: half level between material (inside) and background (outside)
    TS, p, xs, ys = profile_along(V, bis, -45, 25, half=0.5)
    ps = smooth1d(p, 0.75, 0.25)
    inside = np.median(ps[(TS > -40) & (TS < -25)]); outside = np.median(ps[TS > 12])
    half = (inside + outside) / 2
    # outermost crossing from inside->outside level
    idx = np.nonzero(np.diff(np.sign(ps - half)) != 0)[0]
    tend = float(TS[idx[-1]]) if len(idx) else float('nan')
    inimg = (0 <= V[0] < W) and (0 <= V[1] < H)
    clipped = bool(V[1] > H - 1 or V[0] > W - 1 or V[0] < 0 or V[1] < 0 or tend != tend)
    tipV[k] = V; tipEnd[k] = V + bis * tend if tend == tend else V
    res["tips"][k] = dict(vertex=V.tolist(), angle_sil_deg=ang, angle_face_deg=ang_face, bisector=bis.tolist(),
                          end_offset_px=tend, end_pt=(V + bis * tend).tolist() if tend == tend else None,
                          vertex_inside_image=inimg, inside_level=float(inside), outside_level=float(outside),
                          edges=[ea, eb], edge_kinds=[SIL[ea][0], SIL[eb][0]])

# ---------------------------------------------------------------- notches
def first_crisp_from_inside(P0, dvec, t0, t1, half=1.0):
    TS, p, xs, ys = profile_along(P0, dvec, t0, t1, half=half)
    ps = smooth1d(p, 1.0, 0.25); d = np.gradient(ps, 0.25)
    cand = [dict(q, s=+1) for q in peaks(d, TS, 0.03, +1) if q["fwhm"] <= 6] + \
           [dict(q, s=-1) for q in peaks(d, TS, 0.03, -1) if q["fwhm"] <= 6]
    cand = [c for c in cand if c["t"] > t0 + 3]
    return (min(cand, key=lambda c: c["t"]) if cand else None), TS, ps

notchV = {}
for k in range(8):
    ea = "T%d-N%d" % (k, k); eb = "T%d-N%d" % ((k + 1) % 8, k)
    (ma, da) = SIL[ea][1]; (mb, db) = SIL[eb][1]
    V = intersect(ma, da, mb, db)
    # unit vectors from the notch vertex toward the tips
    ua = -np.array(da) if np.dot(da, R[ea]["outer_dir"]) > 0 else np.array(da)
    ub = -np.array(db) if np.dot(db, R[eb]["outer_dir"]) > 0 else np.array(db)
    beta = angle_between(ua, ub)                   # opening angle of the empty notch
    bis = ua + ub; bis /= np.linalg.norm(bis)      # points out of the notch (away from centre)
    # face-line notch
    (fa_m, fa_d) = edge_lines[ea]["face"]; (fb_m, fb_d) = edge_lines[eb]["face"]
    Vf = intersect(fa_m, fa_d, fb_m, fb_d)
    beta_face = angle_between(-fa_d if np.dot(fa_d, R[ea]["outer_dir"]) > 0 else fa_d,
                              -fb_d if np.dot(fb_d, R[eb]["outer_dir"]) > 0 else fb_d)
    # material boundary along the bisector (first crisp step leaving the material)
    c, TS, ps = first_crisp_from_inside(V, bis, -25, 30, half=1.0)
    gap = c["t"] if c else float('nan')
    # rays from a point inside the notch opening toward the material -> local boundary points
    Q = V + bis * 22.0
    pts = []
    for phi in np.arange(-40, 40.01, 1.0):
        a = np.radians(phi)
        dr = -np.array([bis[0] * np.cos(a) - bis[1] * np.sin(a), bis[0] * np.sin(a) + bis[1] * np.cos(a)])  # toward material
        start = Q + dr * 70.0                          # deep in material
        cc, TS2, ps2 = first_crisp_from_inside(start, -dr, 0, 70, half=0.5)
        if cc: pts.append(start - dr * cc["t"])
    pts = np.array(pts)
    dist_bottom = np.hypot(*(pts - (V + bis * gap)).T) if gap == gap else np.hypot(*(pts - V).T)
    fits = {}
    for rr in (8, 12, 16, 24):
        sel = pts[dist_bottom <= rr]
        if len(sel) >= 6:
            C, rad, cres = circle_fit(sel)
            # is the fitted centre on the material side (a rounded notch bottom)?
            side = float(np.dot(C - V, bis))
            fits[rr] = dict(n=len(sel), radius_px=rad, rms_px=float(np.sqrt(np.mean(cres ** 2))), centre_along_bisector_px=side)
    # V-model residual near the bottom: distance of boundary points to the nearest of the two silhouette lines
    def dline(P, m, d):
        nn = np.array([-d[1], d[0]]); return np.abs((P - m) @ nn)
    dv_ = np.minimum(dline(pts, ma, da), dline(pts, mb, db))
    near = dist_bottom <= 12
    notchV[k] = V
    rho_from_gap = gap / (1 / np.sin(np.radians(beta / 2)) - 1) if gap == gap and gap > 0 else 0.0
    res["notches"][k] = dict(vertex=V.tolist(), opening_deg=beta, opening_face_deg=beta_face, face_vertex=Vf.tolist(),
                             bisector=bis.tolist(), bottom_gap_px=gap, bottom_step_sign=(c["s"] if c else None),
                             bottom_pt=((V + bis * gap).tolist() if gap == gap else None),
                             fillet_radius_from_gap_px=float(rho_from_gap), circle_fits=fits,
                             vmodel_resid_near_bottom_px=dict(median=float(np.median(dv_[near])) if near.any() else None,
                                                             max=float(np.max(dv_[near])) if near.any() else None),
                             ray_pts=pts.tolist(), edges=[ea, eb], edge_kinds=[SIL[ea][0], SIL[eb][0]])

# ---------------------------------------------------------------- centre, radii, span
unclipped = [k for k in range(8) if res["tips"][k]["vertex_inside_image"] and res["tips"][k]["end_offset_px"] == res["tips"][k]["end_offset_px"]]
TV = np.array([tipV[k] for k in range(8)])
NV = np.array([notchV[k] for k in range(8)])
Ct, Rt, rest = circle_fit(TV[unclipped])
Cn, Rn, resn = circle_fit(NV)
Ct8, Rt8, _ = circle_fit(TV)
# opposite-tip distances (vertex based)
opp = {"T%d-T%d" % (k, k + 4): float(np.hypot(*(TV[k] - TV[k + 4]))) for k in range(4)}
res["centre"] = dict(tip_circle_centre=Ct.tolist(), tip_circle_R=Rt, tip_circle_rms=float(np.sqrt(np.mean(rest ** 2))),
                     tip_circle_used=unclipped, tip_circle_all8_R=Rt8, tip_circle_all8_centre=Ct8.tolist(),
                     notch_circle_centre=Cn.tolist(), notch_circle_R=Rn, notch_circle_rms=float(np.sqrt(np.mean(resn ** 2))),
                     centre_offset_tip_vs_notch_px=float(np.hypot(*(Ct - Cn))), opposite_tip_vertex_dist=opp)
C0 = Ct
for k in range(8):
    v = TV[k] - C0
    res["tips"][k]["r_vertex_px"] = float(np.hypot(*v))
    res["tips"][k]["polar_deg"] = float(np.degrees(np.arctan2(-v[1], v[0])) % 360)
    if res["tips"][k]["end_pt"]:
        res["tips"][k]["r_end_px"] = float(np.hypot(*(np.array(res["tips"][k]["end_pt"]) - C0)))
    # skew of point axis vs radial direction
    bis = np.array(res["tips"][k]["bisector"]); rad = v / np.linalg.norm(v)
    res["tips"][k]["axis_skew_deg"] = float(np.degrees(np.arctan2(rad[0] * bis[1] - rad[1] * bis[0], np.dot(rad, bis))))
for k in range(8):
    v = NV[k] - C0
    res["notches"][k]["r_vertex_px"] = float(np.hypot(*v))
    res["notches"][k]["polar_deg"] = float(np.degrees(np.arctan2(-v[1], v[0])) % 360)
    if res["notches"][k]["bottom_gap_px"] == res["notches"][k]["bottom_gap_px"]:
        res["notches"][k]["r_bottom_px"] = float(np.hypot(*(NV[k] + np.array(res["notches"][k]["bisector"]) * res["notches"][k]["bottom_gap_px"] - C0)))
json.dump(res, open(os.path.join(OUT, "b6_results.json"), "w"), indent=1, default=float)

# ---------------------------------------------------------------- print summary
print("edges:")
for name in names:
    e = res["edges"][name]
    print("  %-6s n=(%+.2f,%+.2f) sil=%-6s pts %3d rms %.2f | face pts %3d rms %.2f | yellow-outer %s | sagitta %.2f px (%s) circleR %.0f" % (
        name, e["n"][0], e["n"][1], e["sil_kind"], e["outer_pts"], e["outer_rms"], e["face_pts"], e["face_rms"],
        ("%+.1fpx %+.2fdeg" % (e["yellow_minus_outer_px"], e["yellow_vs_outer_deg"])) if "yellow_minus_outer_px" in e else "-",
        e["sagitta_px"], e["quad_sign"], e["circlefit_radius_px"]))
print("centre", res["centre"])
print("tips:")
for k in range(8):
    t = res["tips"][k]
    print("  T%d V=(%.1f,%.1f) r=%.1f polar=%.1f angle_sil=%.2f angle_face=%.2f end_off=%.1f skew=%.2f inimg=%s kinds=%s" % (
        k, t["vertex"][0], t["vertex"][1], t["r_vertex_px"], t["polar_deg"], t["angle_sil_deg"], t["angle_face_deg"],
        t["end_offset_px"], t["axis_skew_deg"], t["vertex_inside_image"], t["edge_kinds"]))
print("notches:")
for k in range(8):
    t = res["notches"][k]
    print("  N%d V=(%.1f,%.1f) r=%.1f polar=%.1f opening=%.2f face_opening=%.2f gap=%.2f sign=%s rho_gap=%.1f fits=%s vres=%s" % (
        k, t["vertex"][0], t["vertex"][1], t["r_vertex_px"], t["polar_deg"], t["opening_deg"], t["opening_face_deg"],
        t["bottom_gap_px"], t["bottom_step_sign"], t["fillet_radius_from_gap_px"],
        {r: "%.1f/%.2f/%+.1f" % (f["radius_px"], f["rms_px"], f["centre_along_bisector_px"]) for r, f in t["circle_fits"].items()},
        t["vmodel_resid_near_bottom_px"]))

