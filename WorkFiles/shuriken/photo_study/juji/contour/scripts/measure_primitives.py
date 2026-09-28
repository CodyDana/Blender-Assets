"""Primitive fitting on the refined contour: DP simplification, curvature sign runs, circle fits to crotch arcs,
neck flanks and blade edges, line fits to the last part of each edge. Writes primitives.json."""
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
CF = sys.argv[1] if len(sys.argv) > 1 else "contour_refined.npy"
OM = sys.argv[2] if len(sys.argv) > 2 else "outline_measurements.json"
OUT = sys.argv[3] if len(sys.argv) > 3 else "primitives.json"
Q = np.load(ROOT + CF)
O = json.load(open(ROOT + OM))
c0 = np.array(O["centre_px"])
border = Q[:, 1] < 2.5
axes = {k: np.array([np.cos(np.radians(v["dir_deg_imagecoords"])), np.sin(np.radians(v["dir_deg_imagecoords"]))]) for k, v in O["axes"].items()}
R = {}
# ---- DP simplification (closed) ----
keep = dp_closed(Q, 1.5)
D = Q[keep]
R["dp_eps_px"] = 1.5; R["dp_vertices"] = int(len(D)); R["contour_points"] = int(len(Q))
# signed turning at DP vertices; orientation of polygon
area = signed_area(Q); orient = np.sign(area)
v1 = D - np.roll(D, 1, 0); v2 = np.roll(D, -1, 0) - D
turn = np.degrees(np.arctan2(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0], (v1 * v2).sum(1))) * orient  # + = convex
R["dp_turn_total_deg"] = round(float(turn.sum()), 1)
# convex / concave runs along DP polyline
runs = []; cur = [0]
for i in range(1, len(D)):
    if np.sign(turn[i]) == np.sign(turn[cur[-1]]) or abs(turn[i]) < 0.5:
        cur.append(i)
    else:
        runs.append(cur); cur = [i]
runs.append(cur)
R["dp_sign_runs"] = len(runs)
# ---- per-arm-side analysis in arm frames ----
def frame_pts(name):
    d = axes[name]; p = np.array([-d[1], d[0]])
    rel = Q - c0; return rel @ d, rel @ p
def fit_circle_uv(u, v):
    c, r, rms = fit_circle(np.stack([u, v], 1)); return c, r, rms
arms = {}
for name in axes:
    u, v = frame_pts(name)
    Rt = O["tips"][name]["R_contour_px"]
    if O["tips"][name]["truncated"]:
        Rt = None
    res = {}
    for side, sgn in (("neg_v", -1), ("pos_v", 1)):
        sel = (np.sign(v) == sgn) & (np.abs(v) < 130) & (u > 60) & ~border
        uu, vv = u[sel], np.abs(v[sel])
        o = np.argsort(uu); uu, vv = uu[o], vv[o]
        # resample v(u) on a 1 px grid (take outermost |v| per bin -> edge of this arm)
        grid = np.arange(np.ceil(uu.min()), np.floor(uu.max()))
        vg = np.interp(grid, uu, vv)
        # smooth and curvature
        k = np.exp(-np.arange(-12, 13) ** 2 / (2 * 5.0 ** 2)); k /= k.sum()
        vs = np.convolve(np.pad(vg, 12, mode="edge"), k, "valid")
        d1 = np.gradient(vs); d2 = np.gradient(d1)
        curv = d2 / (1 + d1 ** 2) ** 1.5    # >0: |v| bends away from axis (concave flank), <0: convex blade
        # inflection between neck and blade: last sign change from + to - before blade max
        umax = grid[np.argmax(np.where(grid > 300, vs, -1))]
        cand = np.nonzero((curv[:-1] > 0) & (curv[1:] <= 0) & (grid[:-1] > 150) & (grid[:-1] < umax))[0]
        u_infl = float(grid[cand[-1]]) if len(cand) else float("nan")
        # neck minimum of |v|
        nk = (grid > 110) & (grid < umax)
        u_nmin = float(grid[nk][np.argmin(vs[nk])]); v_nmin = float(vs[nk].min())
        # circle fits
        def cfit(a, b):
            m = (grid >= a) & (grid <= b)
            if m.sum() < 10: return None
            c, r, rms = fit_circle(np.stack([grid[m], vg[m]], 1))
            cl, dl, rl = fit_line(np.stack([grid[m], vg[m]], 1))
            # sagitta of the chord
            A = np.array([grid[m][0], vg[m][0]]); B = np.array([grid[m][-1], vg[m][-1]])
            dd = (B - A) / np.linalg.norm(B - A); nn = np.array([-dd[1], dd[0]])
            sag = ((np.stack([grid[m], vg[m]], 1) - A) @ nn)
            s = sag[np.argmax(np.abs(sag))]
            return {"u_range": [float(a), float(b)], "radius_px": round(r, 1), "circle_rms_px": round(rms, 2),
                    "line_rms_px": round(rl, 2), "sagitta_px": round(float(s), 2), "chord_px": round(float(np.linalg.norm(B - A)), 1),
                    "centre_uv": [round(float(c[0]), 1), round(float(c[1]), 1)]}
        uend = grid.max()
        side_res = {"u_inflection_px": u_infl, "u_neck_min_px": u_nmin, "neck_half_width_px": round(v_nmin, 1),
                    "u_blade_max_px": float(umax), "blade_half_width_px": round(float(vs[grid == umax][0]), 1),
                    "fit_concave_flank_neckmin_to_inflection": cfit(u_nmin - 40, u_infl) if np.isfinite(u_infl) else None,
                    "fit_concave_flank_110_to_inflection": cfit(110, u_infl) if np.isfinite(u_infl) else None,
                    "fit_convex_blade_inflection_to_tip-10": cfit(u_infl, uend - 10) if np.isfinite(u_infl) else None,
                    "fit_convex_blade_max_to_tip-10": cfit(umax, uend - 10),
                    "fit_convex_blade_inflection_to_max": cfit(u_infl, umax) if np.isfinite(u_infl) else None,
                    "fit_last_60px_before_end": cfit(uend - 70, uend - 10),
                    "u_end_px": float(uend)}
        # curvature sign summary along the edge
        side_res["curvature_sign_changes_110_to_end-15"] = int(np.sum(np.diff(np.sign(curv[(grid > 110) & (grid < uend - 15)])) != 0))
        res[side] = side_res
    arms[name] = res
R["arm_edges"] = arms
# ---- crotch arcs ----
names = ["right", "bottom", "left", "top"]
crotch = {}
for a, b in zip(names, names[1:] + names[:1]):
    bis = axes[a] + axes[b]; bis /= np.linalg.norm(bis)
    rel = Q - c0; dist = np.linalg.norm(rel, axis=1)
    cosang = (rel @ bis) / np.maximum(dist, 1e-9)
    sel = np.nonzero((cosang > np.cos(np.radians(44))) & (dist < 320))[0]
    i0 = sel[np.argmin(dist[sel])]
    out = {"closest_point_px": Q[i0].round(1).tolist(), "closest_dist_from_centre_px": round(float(dist[i0]), 1)}
    fits = {}
    for half in (15, 30, 45, 60, 90, 120, 160):
        idx = np.arange(i0 - half, i0 + half + 1) % len(Q)
        c, r, rms = fit_circle(Q[idx])
        fits[f"+-{half}px_arc"] = {"radius_px": round(r, 1), "rms_px": round(rms, 2), "centre_px": c.round(1).tolist(),
                                   "centre_dist_from_piece_centre_px": round(float(np.linalg.norm(c - c0)), 1)}
    out["circle_fits"] = fits
    crotch[f"{a}-{b}"] = out
R["crotch_arcs"] = crotch
json.dump(R, open(ROOT + OUT, "w"), indent=1)
print("DP:", R["dp_vertices"], "vertices; total turn", R["dp_turn_total_deg"], "; sign runs", R["dp_sign_runs"])
for k, v in arms.items():
    for s, sv in v.items():
        print(k, s, {kk: vv for kk, vv in sv.items() if not kk.startswith("fit_")})
        for kk, vv in sv.items():
            if kk.startswith("fit_"): print("     ", kk, vv)
for k, v in crotch.items():
    print("crotch", k, v["closest_point_px"], v["closest_dist_from_centre_px"])
    for kk, vv in v["circle_fits"].items(): print("     ", kk, vv)
