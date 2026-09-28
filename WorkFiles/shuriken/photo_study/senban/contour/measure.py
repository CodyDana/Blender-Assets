# Method B measurement of Senban.jpg: Moore contour -> sub-pixel refinement -> Douglas-Peucker
# -> circle fits to the four concave sides, line fits to the square hole, corner/tip analysis,
# hole fillet/orientation/centring.  Pixel coords: x right, y DOWN (top-origin rows).
import sys, json, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from seg import segment
from geom import (moore_trace, douglas_peucker, fit_line, fit_circle, line_intersect,
                  circle_circle, bilinear)


def smooth_closed(p, k):
    out = np.zeros_like(p)
    for j in range(-k, k + 1):
        out += np.roll(p, j, 0)
    return out / (2 * k + 1)


def tangents(p, k=5):
    t = np.roll(p, -k, 0) - np.roll(p, k, 0)
    return t / np.linalg.norm(t, axis=1, keepdims=True)


def refine(p, L, tL, rng=3.0):
    """Move each contour point along its outward normal to the L == tL crossing nearest to it."""
    t = tangents(smooth_closed(p, 2), 4)
    n = np.c_[t[:, 1], -t[:, 0]]            # outward normal for a clockwise (on-screen) contour
    s = np.arange(-rng, rng + 1e-9, 0.1)
    out = p.copy(); moved = 0
    for i in range(len(p)):
        xs = p[i, 0] + s * n[i, 0]; ys = p[i, 1] + s * n[i, 1]
        v = bilinear(L, xs, ys) - tL
        sg = np.sign(v)
        idx = np.nonzero(sg[:-1] * sg[1:] < 0)[0]
        if len(idx):
            j = idx[np.argmin(np.abs(s[idx]))]
            f = v[j] / (v[j] - v[j + 1])
            ss = s[j] + f * (s[j + 1] - s[j])
            out[i] = p[i] + ss * n[i]; moved += 1
    return out, n, moved


def arclen(p):
    return np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]


def angle_deg(u, v):
    c = np.clip(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1)
    return math.degrees(math.acos(c))


def dirangle(u):
    """Direction angle in degrees on screen (y down), folded to (-90, 90]."""
    a = math.degrees(math.atan2(u[1], u[0]))
    while a <= -90: a += 180
    while a > 90: a -= 180
    return a


def side_segments(c, cidx):
    n = len(c); out = []
    for k in range(4):
        a, b = cidx[k], cidx[(k + 1) % 4]
        out.append(np.arange(a, b + 1) if b > a else np.r_[np.arange(a, n), np.arange(0, b + 1)])
    return out


CN = ["TL", "TR", "BR", "BL"]
SN = ["top", "right", "bottom", "left"]


def outer_analysis(c_ref, trim=0.08):
    x, y = c_ref[:, 0], c_ref[:, 1]
    cidx = [int(np.argmin(x + y)), int(np.argmax(x - y)), int(np.argmax(x + y)), int(np.argmin(x - y))]
    tips = c_ref[cidx]
    sides = side_segments(c_ref, cidx)
    fits = []
    for k, si in enumerate(sides):
        p = c_ref[si]; s = arclen(p); s /= s[-1]
        sel = (s >= trim) & (s <= 1 - trim)
        core = p[sel]
        cx, cy, Rr, rms, res = fit_circle(core)
        lp, ld, lrms, lmax = fit_line(core)
        sc = s[sel]
        edges = np.linspace(trim, 1 - trim, 6)
        bins = [float(res[(sc >= edges[i]) & (sc < edges[i + 1])].mean()) for i in range(5)]
        fits.append(dict(side=SN[k], cx=cx, cy=cy, R=Rr, rms=rms, maxres=float(np.abs(res).max()),
                         line_rms=lrms, line_max=lmax, resid_bins=[round(v, 2) for v in bins], npts=int(len(core))))
    corners = []
    for k in range(4):
        f0 = fits[(k - 1) % 4]; f1 = fits[k]
        p1, p2 = circle_circle((f0["cx"], f0["cy"]), f0["R"], (f1["cx"], f1["cy"]), f1["R"])
        corners.append(p1 if np.hypot(*(p1 - tips[k])) < np.hypot(*(p2 - tips[k])) else p2)
    corners = np.array(corners)
    adj = [float(np.hypot(*(corners[(k + 1) % 4] - corners[k]))) for k in range(4)]
    diag = [float(np.hypot(*(corners[2] - corners[0]))), float(np.hypot(*(corners[3] - corners[1])))]
    adj_tip = [float(np.hypot(*(tips[(k + 1) % 4] - tips[k]))) for k in range(4)]
    diag_tip = [float(np.hypot(*(tips[2] - tips[0]))), float(np.hypot(*(tips[3] - tips[1])))]
    quad_ang = [angle_deg(corners[(k - 1) % 4] - corners[k], corners[(k + 1) % 4] - corners[k]) for k in range(4)]
    cen = line_intersect(corners[0], corners[2] - corners[0], corners[1], corners[3] - corners[1])
    side_out = []
    for k, f in enumerate(fits):
        A, B = corners[k], corners[(k + 1) % 4]
        chord = float(np.hypot(*(B - A))); u = (B - A) / chord; nin = np.array([-u[1], u[0]])
        C = np.array([f["cx"], f["cy"]])
        dC = float((C - A) @ nin)
        sag_circle = f["R"] - abs(dC) if dC < 0 else float("nan")
        p = c_ref[sides[k]]
        depth = (p - A) @ nin; along = (p - A) @ u / chord
        j = int(np.argmax(depth))
        # position of the circle's deepest point along the chord (0..1)
        foot = float(((C - A) @ u) / chord)
        sag_formula = f["R"] - math.sqrt(max(f["R"] ** 2 - (chord / 2) ** 2, 0))
        side_out.append(dict(side=f["side"], chord_px=chord, R_px=f["R"], sagitta_circle_px=sag_circle,
                             sagitta_formula_px=sag_formula, sagitta_contour_px=float(depth[j]),
                             deepest_contour_at_frac=float(along[j]), deepest_circle_at_frac=foot,
                             chord_dir_deg=dirangle(u),
                             circle_rms_px=f["rms"], circle_max_px=f["maxres"], line_rms_px=f["line_rms"],
                             line_max_px=f["line_max"], resid_bins_px=f["resid_bins"], fit_pts=f["npts"],
                             R_over_chord=f["R"] / chord, sag_over_chord=sag_circle / chord,
                             sag_contour_over_chord=float(depth[j]) / chord))
    tip_out = []
    for k in range(4):
        q = corners[k]
        f_in = fits[(k - 1) % 4]; f_out = fits[k]

        def tan_at(f, toward):
            r = q - np.array([f["cx"], f["cy"]]); t = np.array([-r[1], r[0]]); t /= np.linalg.norm(t)
            return t if t @ (toward - q) > 0 else -t

        t1 = tan_at(f_in, corners[(k - 1) % 4]); t2 = tan_at(f_out, corners[(k + 1) % 4])

        def local_line(side_idx, from_start, lo=0.015, hi=0.08):
            p = c_ref[side_idx]; s = arclen(p); s /= s[-1]
            if not from_start: s = 1 - s
            sel = p[(s >= lo) & (s <= hi)]
            lp, ld, _, _ = fit_line(sel)
            far = sel[np.argmax(np.hypot(*(sel - q).T))]
            return ld if ld @ (far - q) > 0 else -ld

        l1 = local_line(sides[(k - 1) % 4], False); l2 = local_line(sides[k], True)
        tip_out.append(dict(corner=CN[k], x=float(q[0]), y=float(q[1]), tip_contour_x=float(tips[k][0]),
                            tip_contour_y=float(tips[k][1]),
                            tip_to_intersection_px=float(np.hypot(*(tips[k] - q))),
                            angle_circle_tangents_deg=angle_deg(t1, t2), angle_local_lines_deg=angle_deg(l1, l2),
                            quad_interior_deg=quad_ang[k]))
    return dict(corners=tip_out, adjacent_px=adj, adjacent_tip_px=adj_tip, diag_px=diag, diag_tip_px=diag_tip,
                S_ref_px=float(np.mean(adj)), center=[float(cen[0]), float(cen[1])], sides=side_out), \
        dict(corners=corners, tips=tips, fits=fits, sides=sides, cen=cen)


def hole_analysis(h_ref, corners, cen, trim=0.15):
    hx, hy = h_ref[:, 0], h_ref[:, 1]
    hidx = [int(np.argmin(hx + hy)), int(np.argmax(hx - hy)), int(np.argmax(hx + hy)), int(np.argmin(hx - hy))]
    hsides = side_segments(h_ref, hidx)
    hlines = []
    for k, si in enumerate(hsides):
        p = h_ref[si]; s = arclen(p); s /= s[-1]
        core = p[(s >= trim) & (s <= 1 - trim)]
        lp, ld, lrms, lmax = fit_line(core)
        _, _, Rr, crms, _ = fit_circle(core)
        hlines.append(dict(p=lp, d=ld, rms=lrms, max=lmax, npts=int(len(core)), circR=Rr, circ_rms=crms))
    hcor = np.array([line_intersect(hlines[(k - 1) % 4]["p"], hlines[(k - 1) % 4]["d"], hlines[k]["p"], hlines[k]["d"])
                     for k in range(4)])
    hside_len = [float(np.hypot(*(hcor[(k + 1) % 4] - hcor[k]))) for k in range(4)]
    hang = [angle_deg(hcor[(k - 1) % 4] - hcor[k], hcor[(k + 1) % 4] - hcor[k]) for k in range(4)]
    hcen = hcor.mean(0)
    hcen_diag = line_intersect(hcor[0], hcor[2] - hcor[0], hcor[1], hcor[3] - hcor[1])

    def dist_line(l, P):
        nn = np.array([-l["d"][1], l["d"][0]]); return np.abs((P - l["p"]) @ nn)

    fil = []
    for k in range(4):
        q = hcor[k]; phi = math.radians(hang[k])
        dmin = float(np.hypot(*(h_ref - q).T).min())
        r_est = dmin / (1 / math.sin(phi / 2) - 1)
        l0, l1 = hlines[(k - 1) % 4], hlines[k]
        near = np.hypot(*(h_ref - q).T) < 35
        P = h_ref[near]
        z = P[(dist_line(l0, P) > 0.75) & (dist_line(l1, P) > 0.75)]
        rfit = float("nan"); rrms = float("nan")
        if len(z) >= 5:
            _, _, rfit, rrms, _ = fit_circle(z)
        fil.append(dict(corner=CN[k], sharp_x=float(q[0]), sharp_y=float(q[1]), corner_angle_deg=hang[k],
                        gap_to_contour_px=dmin, r_from_gap_px=r_est, r_circlefit_px=rfit, fit_pts=int(len(z)),
                        r_fit_rms=rrms))
    orient = []
    for k in range(4):
        hd = hcor[(k + 1) % 4] - hcor[k]; od = corners[(k + 1) % 4] - corners[k]
        orient.append(dict(side=SN[k], hole_dir_deg=dirangle(hd), outer_chord_dir_deg=dirangle(od),
                           rel_deg=dirangle(hd) - dirangle(od)))
    ux = (corners[1] - corners[0]) / np.linalg.norm(corners[1] - corners[0]) + \
         (corners[2] - corners[3]) / np.linalg.norm(corners[2] - corners[3])
    ux /= np.linalg.norm(ux); uy = np.array([-ux[1], ux[0]])
    off = hcen - cen
    return dict(sharp_corners=hcor.tolist(), side_len_px=hside_len, corner_angles_deg=hang,
                line_rms_px=[l["rms"] for l in hlines], line_max_px=[l["max"] for l in hlines],
                side_circle_R_px=[l["circR"] for l in hlines],
                center=[float(hcen[0]), float(hcen[1])], center_diag=[float(hcen_diag[0]), float(hcen_diag[1])],
                offset_px_image=[float(off[0]), float(off[1])],
                offset_px_plate_frame=[float(off @ ux), float(off @ uy)],
                fillets=fil, orientation=orient,
                bbox_wh=[float(hx.max() - hx.min()), float(hy.max() - hy.min())]), \
        dict(hcor=hcor, hlines=hlines, hcen=hcen)


def run(tL=None, tY=None):
    seg = segment(tL, tY)
    L, tL, tY = seg["L"], seg["tL"], seg["tY"]
    plate, hole = seg["plate"], seg["hole"]
    R = dict(thresholds=dict(L=tL, Yw=tY, otsuL=seg["otsuL"], otsuYw=seg["otsuY"]))
    c_raw = moore_trace(plate | hole)
    c_ref, nrm, moved = refine(c_raw, L, tL)
    dp, _ = douglas_peucker(np.r_[c_ref, c_ref[:1]], 1.5)
    R["outer_contour"] = dict(points=len(c_raw), refined_points=moved, dp_vertices=len(dp) - 1)
    R["outer"], OA = outer_analysis(c_ref)
    h_raw = moore_trace(hole)
    h_ref, _, hmoved = refine(h_raw, L, tL)
    hdp, _ = douglas_peucker(np.r_[h_ref, h_ref[:1]], 1.5)
    R["hole_contour"] = dict(points=len(h_raw), refined_points=hmoved, dp_vertices=len(hdp) - 1, area_px=int(hole.sum()))
    R["hole"], HA = hole_analysis(h_ref, OA["corners"], OA["cen"])
    R["_arrays"] = dict(c_raw=c_raw, c_ref=c_ref, h_raw=h_raw, h_ref=h_ref, dp=dp, hdp=hdp, nrm=nrm,
                        plate=plate, hole=hole, L=L, Yw=seg["Yw"], **OA, **HA)
    return R


if __name__ == "__main__":
    R = run()
    A = R.pop("_arrays")
    np.save(D + "cache/outer_contour_refined.npy", A["c_ref"]); np.save(D + "cache/hole_contour_refined.npy", A["h_ref"])
    print(json.dumps(R, indent=1, default=float))
