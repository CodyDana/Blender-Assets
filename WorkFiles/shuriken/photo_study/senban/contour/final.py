# Senban.jpg, method B (contour + primitive fitting): primary threshold outline (P), shadow-corrected
# outline (S), threshold sensitivity, bevel-crease widths along every side, debug overlay + JSON.
import sys, json, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from measure import run, outer_analysis, hole_analysis, arclen
from geom import bilinear, fit_circle, fit_line
from pngio import write_png

SN = ["top", "right", "bottom", "left"]


def smooth_cols(M, k):
    out = np.empty_like(M)
    for c in range(M.shape[1]):
        out[:, c] = M[:, max(0, c - k):c + k + 1].mean(1)
    return out


def arc_frame(fit, P0, P1, ncol):
    C = np.array([fit["cx"], fit["cy"]]); Rr = fit["R"]
    a0 = math.atan2(P0[1] - C[1], P0[0] - C[0]); a1 = math.atan2(P1[1] - C[1], P1[0] - C[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    ts = np.linspace(0, 1, ncol); ang = a0 + ts * da
    return C, Rr, ts, np.cos(ang), np.sin(ang)


def sample_strip(L, fit, P0, P1, ds, ncol):
    C, Rr, ts, ux, uy = arc_frame(fit, P0, P1, ncol)
    X = C[0] + (Rr + ds[:, None]) * ux[None, :]; Y = C[1] + (Rr + ds[:, None]) * uy[None, :]
    return ts, bilinear(L, X.ravel(), Y.ravel()).reshape(X.shape), (C, Rr, ux, uy)


def locate(prof_cols, ds, lo, hi, mode, level=None):
    """per column: 'drop' = steepest descent of L with depth in [lo,hi]; 'rise' = steepest ascent;
    'level' = first crossing below `level` in [lo,hi]. Returns depth (nan if none)."""
    g = np.diff(prof_cols, axis=0); dm = 0.5 * (ds[1:] + ds[:-1])
    sel = (dm >= lo) & (dm <= hi)
    out = np.full(prof_cols.shape[1], np.nan); strength = np.zeros(prof_cols.shape[1])
    for c in range(prof_cols.shape[1]):
        if mode == "drop":
            gi = np.where(sel, g[:, c], np.inf); j = int(np.argmin(gi)); out[c] = dm[j]; strength[c] = -g[j, c]
        elif mode == "rise":
            gi = np.where(sel, g[:, c], -np.inf); j = int(np.argmax(gi)); out[c] = dm[j]; strength[c] = g[j, c]
        else:
            p = prof_cols[:, c]; idx = np.nonzero((ds[:-1] >= lo) & (ds[:-1] <= hi) & (p[:-1] >= level) & (p[1:] < level))[0]
            if len(idx):
                j = idx[0]; f = (p[j] - level) / (p[j] - p[j + 1]); out[c] = ds[j] + f; strength[c] = p[j] - p[j + 1]
    return out, strength


def shadow_corrected_outer(A):
    """S outline: top side relocated to the crisp outer edge of the black bevel band (L=35 crossing),
    right side to the steepest drop (end of the soft x-shadow ramp); left/bottom kept (lit, crisp)."""
    L = A["L"]; fits = A["fits"]; corners = A["corners"]
    ds = np.arange(-15, 30.01, 0.25)
    pts_by_side = []
    rules = {0: ("level", 2, 20, 35.0), 1: ("drop", -3, 9, None), 2: ("drop", -4, 4, None), 3: ("drop", -4, 4, None)}
    info = {}
    for k in range(4):
        ncol = int(np.hypot(*(corners[(k + 1) % 4] - corners[k])))
        ts, S, (C, Rr, ux, uy) = sample_strip(L, fits[k], corners[k], corners[(k + 1) % 4], ds, ncol)
        S = smooth_cols(S, 5)
        mode, lo, hi, lev = rules[k]
        dep, _ = locate(S, ds, lo, hi, mode, lev)
        keep = (ts >= 0.08) & (ts <= 0.92) & np.isfinite(dep)
        X = C[0] + (Rr + dep) * ux; Y = C[1] + (Rr + dep) * uy
        pts_by_side.append(np.c_[X[keep], Y[keep]])
        info[SN[k]] = dict(rule=mode, median_shift_px=float(np.nanmedian(dep[(ts >= 0.08) & (ts <= 0.92)])),
                           shift_at=[round(float(np.nanmedian(dep[(ts >= t - 0.02) & (ts <= t + 0.02)])), 1)
                                     for t in (0.1, 0.3, 0.5, 0.7, 0.9)])
    return pts_by_side, info


def outer_from_side_points(pts_by_side):
    """fit circles to given per-side point sets and rebuild the outer metrics."""
    from geom import circle_circle, line_intersect
    from measure import angle_deg, dirangle, CN
    fits = []
    for k, p in enumerate(pts_by_side):
        cx, cy, Rr, rms, res = fit_circle(p)
        fits.append(dict(side=SN[k], cx=cx, cy=cy, R=Rr, rms=rms, maxres=float(np.abs(res).max())))
    guess = [p for p in pts_by_side]
    corners = []
    for k in range(4):
        f0 = fits[(k - 1) % 4]; f1 = fits[k]
        p1, p2 = circle_circle((f0["cx"], f0["cy"]), f0["R"], (f1["cx"], f1["cy"]), f1["R"])
        ref = 0.5 * (guess[(k - 1) % 4][-1] + guess[k][0])
        corners.append(p1 if np.hypot(*(p1 - ref)) < np.hypot(*(p2 - ref)) else p2)
    corners = np.array(corners)
    adj = [float(np.hypot(*(corners[(k + 1) % 4] - corners[k]))) for k in range(4)]
    diag = [float(np.hypot(*(corners[2] - corners[0]))), float(np.hypot(*(corners[3] - corners[1])))]
    cen = line_intersect(corners[0], corners[2] - corners[0], corners[1], corners[3] - corners[1])
    sides = []
    tips = []
    for k, f in enumerate(fits):
        A0, B0 = corners[k], corners[(k + 1) % 4]
        chord = float(np.hypot(*(B0 - A0))); u = (B0 - A0) / chord; nin = np.array([-u[1], u[0]])
        Cc = np.array([f["cx"], f["cy"]]); dC = float((Cc - A0) @ nin)
        sag = f["R"] - abs(dC)
        sides.append(dict(side=SN[k], chord_px=chord, R_px=f["R"], sagitta_px=sag, sag_over_chord=sag / chord,
                          R_over_chord=f["R"] / chord, circle_rms_px=f["rms"], circle_max_px=f["maxres"]))
    for k in range(4):
        q = corners[k]

        def tan_at(f, toward):
            r = q - np.array([f["cx"], f["cy"]]); t = np.array([-r[1], r[0]]); t /= np.linalg.norm(t)
            return t if t @ (toward - q) > 0 else -t
        t1 = tan_at(fits[(k - 1) % 4], corners[(k - 1) % 4]); t2 = tan_at(fits[k], corners[(k + 1) % 4])
        tips.append(dict(corner=CN[k], x=float(q[0]), y=float(q[1]), angle_circle_tangents_deg=angle_deg(t1, t2),
                         quad_interior_deg=angle_deg(corners[(k - 1) % 4] - q, corners[(k + 1) % 4] - q)))
    return dict(corners=tips, adjacent_px=adj, diag_px=diag, S_ref_px=float(np.mean(adj)),
                center=[float(cen[0]), float(cen[1])], sides=sides), dict(fits=fits, corners=corners, cen=cen)


def shadow_corrected_hole(A):
    """S hole: left side moved out to the end of the soft in-hole shadow ramp (steepest drop in [0,14]),
    bottom side moved out to the start of the black chamfer band (L=35 crossing in [0,16]),
    right side to steepest drop in [-3,6], top kept (crisp)."""
    from hole_strips import hole_unwrap
    L = A["L"]
    rules = {0: ("drop", -3, 2.5, None), 1: ("drop", -3, 2.5, None), 2: ("level", 0, 16, 35.0), 3: ("drop", 0, 14, None)}
    lines = []; info = {}
    for k in range(4):
        ts, ds, o, nout, u = hole_unwrap(A, k, d0=-30, d1=25, img=dict(L=L))
        # finer depth sampling
        dsf = np.arange(-30, 25.01, 0.25)
        P0 = A["hcor"][k]
        X = P0[0] + ts[None, :] * u[0] + dsf[:, None] * nout[0]; Y = P0[1] + ts[None, :] * u[1] + dsf[:, None] * nout[1]
        S = smooth_cols(bilinear(L, X.ravel(), Y.ravel()).reshape(X.shape), 5)
        mode, lo, hi, lev = rules[k]
        dep, _ = locate(S, dsf, lo, hi, mode, lev)
        n = len(ts); keep = (ts >= 0.15 * ts[-1]) & (ts <= 0.85 * ts[-1]) & np.isfinite(dep)
        pts = np.c_[P0[0] + ts[keep] * u[0] + dep[keep] * nout[0], P0[1] + ts[keep] * u[1] + dep[keep] * nout[1]]
        lp, ld, rms, mx = fit_line(pts)
        lines.append(dict(p=lp, d=ld, rms=rms, max=mx))
        info[SN[k]] = dict(rule=mode, median_shift_px=float(np.nanmedian(dep[keep])))
    from geom import line_intersect
    from measure import angle_deg
    hcor = np.array([line_intersect(lines[(k - 1) % 4]["p"], lines[(k - 1) % 4]["d"], lines[k]["p"], lines[k]["d"]) for k in range(4)])
    side = [float(np.hypot(*(hcor[(k + 1) % 4] - hcor[k]))) for k in range(4)]
    ang = [angle_deg(hcor[(k - 1) % 4] - hcor[k], hcor[(k + 1) % 4] - hcor[k]) for k in range(4)]
    return dict(side_len_px=side, corner_angles_deg=ang, center=hcor.mean(0).tolist(), line_rms_px=[l["rms"] for l in lines],
                shift=info, sharp_corners=hcor.tolist()), hcor


def bevel_creases(A, outer_S_top_edge=None):
    """crease depth (from the threshold outline) per column for each side."""
    L = A["L"]; fits = A["fits"]; corners = A["corners"]
    ds = np.arange(-10, 50.01, 0.5)
    res = {}; pts = {}
    for k in range(4):
        ncol = int(np.hypot(*(corners[(k + 1) % 4] - corners[k])))
        ts, S, (C, Rr, ux, uy) = sample_strip(L, fits[k], corners[k], corners[(k + 1) % 4], ds, ncol)
        S = smooth_cols(S, 6)
        if k == 0:
            edge, _ = locate(S, ds, 2, 20, "level", 35.0)
            crease = np.full(len(ts), np.nan); strength = np.zeros(len(ts))
            g = np.diff(S, axis=0); dm = 0.5 * (ds[1:] + ds[:-1])
            for c in range(len(ts)):
                e = edge[c] if np.isfinite(edge[c]) else 10.0
                sel = (dm > e + 3) & (dm <= 45)
                gi = np.where(sel, g[:, c], -np.inf); j = int(np.argmax(gi)); crease[c] = dm[j]; strength[c] = g[j, c]
        elif k == 1:
            # right side: low-contrast bevel; the crease shows as a faint light line -> peak of L
            # (heavier along-edge smoothing), metal edge = end of the soft x-shadow ramp (steepest drop)
            S2 = smooth_cols(S, 15)
            edge, _ = locate(S2, ds, -3, 9, "drop")
            crease = np.full(len(ts), np.nan); strength = np.zeros(len(ts))
            for c in range(len(ts)):
                sel = (ds >= 8) & (ds <= 26)
                j = int(np.argmax(np.where(sel, S2[:, c], -np.inf)))
                base = np.median(S2[(ds >= 28) & (ds <= 45), c])
                crease[c] = ds[j] + 1.0; strength[c] = S2[j, c] - base
        else:
            crease, strength = locate(S, ds, {2: 6, 3: 5}[k], 32, "drop")
            edge, _ = locate(S, ds, -4, 4, "drop")
        stations = {}
        for t in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
            m = (ts >= t - 0.02) & (ts <= t + 0.02)
            stations[f"{t:.2f}"] = dict(crease_from_outline=round(float(np.nanmedian(crease[m])), 1),
                                        crease_from_metal_edge=round(float(np.nanmedian(crease[m] - edge[m])), 1),
                                        strength=round(float(np.nanmedian(strength[m])), 1))
        core = (ts >= 0.1) & (ts <= 0.9)
        w = crease[core] - edge[core]
        med = float(np.nanmedian(w))
        consistent = float(np.mean(np.abs(w - med) <= 4.0))
        strong = float(np.mean(strength[core] >= 4.0))
        res[SN[k]] = dict(stations=stations, width_median_px=med, width_p10_px=float(np.nanpercentile(w, 10)),
                          width_p90_px=float(np.nanpercentile(w, 90)),
                          frac_cols_within_4px_of_median=consistent, frac_cols_strong_edge=strong,
                          outline_to_crease_median_px=float(np.nanmedian(crease[core])),
                          graded_zone_median_px=float(np.nanmedian(edge[core])))
        X = C[0] + (Rr + crease) * ux; Y = C[1] + (Rr + crease) * uy
        Xe = C[0] + (Rr + edge) * ux; Ye = C[1] + (Rr + edge) * uy
        pts[SN[k]] = (np.c_[X, Y], np.c_[Xe, Ye], ts)
    return res, pts


def fillet_fit(h_ref, hcor, zone=30.0):
    """1-parameter rounded-corner fit: the two fitted side lines joined by a tangent arc of radius r;
    r chosen by grid search to minimise RMS distance of the contour points within `zone` px."""
    out = []
    for k in range(4):
        q = hcor[k]
        u1 = hcor[(k - 1) % 4] - q; u1 /= np.linalg.norm(u1)
        u2 = hcor[(k + 1) % 4] - q; u2 /= np.linalg.norm(u2)
        phi = math.acos(np.clip(u1 @ u2, -1, 1)); b = (u1 + u2) / np.linalg.norm(u1 + u2)
        P = h_ref[np.hypot(*(h_ref - q).T) < zone]
        best = None
        for r in np.arange(0.0, 30.01, 0.1):
            t = r / math.tan(phi / 2); c = q + b * r / math.sin(phi / 2)
            T1 = q + u1 * t; T2 = q + u2 * t
            d = np.empty(len(P))
            for i, p in enumerate(P):
                a1 = (p - q) @ u1; a2 = (p - q) @ u2
                if r > 0 and a1 <= t and a2 <= t:
                    d[i] = abs(np.hypot(*(p - c)) - r)
                else:
                    n1 = np.array([-u1[1], u1[0]]); n2 = np.array([-u2[1], u2[0]])
                    d[i] = min(abs((p - q) @ n1) if a1 >= 0 else 1e9, abs((p - q) @ n2) if a2 >= 0 else 1e9)
                    if d[i] >= 1e9: d[i] = np.hypot(*(p - q))
            rms = float(np.sqrt((d ** 2).mean()))
            if best is None or rms < best[1]:
                best = (float(r), rms)
        out.append(dict(corner=["TL", "TR", "BR", "BL"][k], r_px=best[0], rms_px=best[1], npts=int(len(P)),
                        corner_angle_deg=math.degrees(phi)))
    return out


def draw_overlay(A, S_arr, hcorS, crease_pts, path):
    rgb = np.load(D + "cache/senban_rgb.npy").astype(float)
    img = 0.55 * rgb + 0.45 * 255 * 0.35
    H, W, _ = img.shape

    def dot(x, y, col, r=1):
        xi, yi = int(round(x)), int(round(y))
        img[max(0, yi - r):yi + r + 1, max(0, xi - r):xi + r + 1] = col

    def line(p, q, col, step=0.5, r=0):
        n = int(np.hypot(*(q - p)) / step) + 1
        for t in np.linspace(0, 1, n):
            dot(*(p + t * (q - p)), col, r)

    def arc(fit, P0, P1, col, r=0):
        C, Rr, ts, ux, uy = arc_frame(fit, P0, P1, 2000)
        for x, y in zip(C[0] + Rr * ux, C[1] + Rr * uy):
            dot(x, y, col, r)

    # threshold contour (cyan), hole contour (cyan)
    for x, y in A["c_ref"]: dot(x, y, [0, 255, 255], 0)
    for x, y in A["h_ref"]: dot(x, y, [0, 255, 255], 0)
    # fitted side circles P (yellow) between P corners, S (orange)
    for k in range(4):
        arc(A["fits"][k], A["corners"][k], A["corners"][(k + 1) % 4], [255, 230, 0])
        arc(S_arr["fits"][k], S_arr["corners"][k], S_arr["corners"][(k + 1) % 4], [255, 120, 0])
    # chords + sagitta marker (white / magenta)
    for k in range(4):
        P0, P1 = A["corners"][k], A["corners"][(k + 1) % 4]
        line(P0, P1, [255, 255, 255], step=3)
        f = A["fits"][k]; Cc = np.array([f["cx"], f["cy"]]); mid = 0.5 * (P0 + P1)
        v = mid - Cc; v /= np.linalg.norm(v)
        line(mid, Cc + f["R"] * v, [255, 0, 255], r=1)
    # diagonals (thin grey)
    line(A["corners"][0], A["corners"][2], [200, 200, 200], step=4)
    line(A["corners"][1], A["corners"][3], [200, 200, 200], step=4)
    # hole fitted lines (green) between sharp corners, S hole (orange)
    for k in range(4):
        line(A["hcor"][k], A["hcor"][(k + 1) % 4], [0, 255, 0])
        line(hcorS[k], hcorS[(k + 1) % 4], [255, 120, 0])
    # crease points (blue) and S top metal edge (orange)
    for nm, (cp, ep, ts) in crease_pts.items():
        for (x, y), t in zip(cp, ts):
            if np.isfinite(x) and 0.03 <= t <= 0.97: dot(x, y, [60, 120, 255], 0)
    # corners (red) + contour tips (white) + centres
    for q in A["corners"]: dot(*q, [255, 0, 0], 3)
    for q in A["tips"]: dot(*q, [255, 255, 255], 2)
    dot(*A["cen"], [255, 0, 0], 3); dot(*A["hcor"].mean(0), [0, 255, 0], 3)
    write_png(path, np.clip(img, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    R = run()
    A = R.pop("_arrays")
    # --- shadow-corrected outline (S)
    ptsS, shiftS = shadow_corrected_outer(A)
    outerS, S_arr = outer_from_side_points(ptsS)
    holeS, hcorS = shadow_corrected_hole(A)
    # --- bevel creases
    bev, cpts = bevel_creases(A)
    # --- threshold sensitivity (P method)
    sens = {}
    for t in (90.0, 105.0, 135.0, 150.0):
        Rt = run(tL=t); Rt.pop("_arrays")
        o = Rt["outer"]; h = Rt["hole"]
        sens[str(t)] = dict(S_ref_px=o["S_ref_px"], adjacent_px=o["adjacent_px"],
                            sag_over_chord=[s["sag_over_chord"] for s in o["sides"]],
                            R_over_chord=[s["R_over_chord"] for s in o["sides"]],
                            tip_angle_deg=[c["angle_circle_tangents_deg"] for c in o["corners"]],
                            hole_side_px=h["side_len_px"], hole_over_S=float(np.mean(h["side_len_px"]) / o["S_ref_px"]),
                            hole_rel_deg=[q["rel_deg"] for q in h["orientation"]],
                            hole_offset_plate_px=h["offset_px_plate_frame"])
    fil = fillet_fit(A["h_ref"], A["hcor"])
    out = dict(primary_threshold=R, shadow_corrected=dict(outer=outerS, outer_shift=shiftS, hole=holeS),
               bevel=bev, threshold_sensitivity=sens, hole_fillet_constrained_fit=fil)
    print("FILLET", json.dumps(fil))
    json.dump(out, open(D + "senban_contour_results.json", "w"), indent=1, default=float)
    draw_overlay(A, S_arr, hcorS, cpts, D + "senban_contour_overlay.png")
    print(json.dumps(dict(S=outerS, Sshift=shiftS, holeS=holeS, bevel=bev, sens=sens), indent=1, default=float))
