"""Blade metrics per arm from the refined edges (s19), for two silhouette variants:
  primary 'outer' : E50 half-contrast edges; on the up-facing (image -y) sides of the horizontal arms the
                    near-black band is counted as metal (Eincl).
  alt     'inner' : watershed reference edges (inner end of soft ramps); band excluded (Eexcl) where found.
Writes metrics_<variant>.json, an overlay of the primary edges and fit lines, and prints tables.
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
names = ["right", "top", "left", "bottom"]
UP_SIDE = {"right": "L", "left": "R"}
g1 = json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))
c = np.array(g1["centre_candidates_px"]["sym90"])


def medfilt(x, k=9):
    x = np.asarray(x, float)
    y = x.copy()
    h = k // 2
    for i in range(len(x)):
        w = x[max(0, i - h):i + h + 1]
        w = w[np.isfinite(w)]
        y[i] = np.median(w) if len(w) else np.nan
    return y


def fill(x):
    x = np.asarray(x, float).copy()
    ok = np.isfinite(x)
    if ok.sum() >= 2:
        x[~ok] = np.interp(np.nonzero(~ok)[0], np.nonzero(ok)[0], x[ok])
    return x


def circle_fit(xs, ys):
    A = np.stack([xs, ys, np.ones_like(xs)], 1)
    b = -(xs ** 2 + ys ** 2)
    (D, E, F), *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = -D / 2, -E / 2
    r = math.sqrt(max(cx * cx + cy * cy - F, 0))
    res = np.hypot(xs - cx, ys - cy) - r
    return cx, cy, r, float(np.sqrt((res ** 2).mean()))


def line_fit(xs, ys):
    A = np.stack([xs, np.ones_like(xs)], 1)
    (b, a0), *_ = np.linalg.lstsq(A, ys, rcond=None)
    res = ys - (a0 + b * xs)
    return a0, b, float(np.sqrt((res ** 2).mean()))


variant = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "outer"
metrics = {"variant": variant, "centre_px": c.tolist(), "arms": {}}
edges_img = {}
for nme in names:
    z = np.load(os.path.join(jlib.OUT, "edges_%s.npz" % nme))
    S = z["S"]; u = z["u"]; n = z["n"]; origin = z["origin"]
    if variant == "outer":
        tL = z["E50L"].copy(); tR = z["E50R"].copy()
        if UP_SIDE.get(nme) == "L":
            tL = np.where(np.isfinite(z["EinclL"]), z["EinclL"], tL)
        if UP_SIDE.get(nme) == "R":
            tR = np.where(np.isfinite(z["EinclR"]), z["EinclR"], tR)
    else:
        tL = z["refL"].copy(); tR = z["refR"].copy()
        if UP_SIDE.get(nme) == "L":
            tL = np.where(np.isfinite(z["EexclL"]), z["EexclL"], tL)
        if UP_SIDE.get(nme) == "R":
            tR = np.where(np.isfinite(z["EexclR"]), z["EexclR"], tR)
    # only stations where the reference run exists
    valid = np.isfinite(z["refL"]) & np.isfinite(z["refR"])
    tL[~valid] = np.nan; tR[~valid] = np.nan
    tL = fill(medfilt(tL, 9)); tR = fill(medfilt(tR, 9))
    last = np.nonzero(valid)[0].max()
    S2, tL, tR = S[:last + 1], tL[:last + 1], tR[:last + 1]
    w = tL - tR
    mid = 0.5 * (tL + tR)
    # --- tip apex from line fits to the last 10 % of each edge ---
    Rr = S2[-1]
    tipfits = {}
    for frac in (0.05, 0.10, 0.15, 0.20):
        Lw = frac * 660.0
        sel = (S2 >= Rr - Lw) & (S2 <= Rr - 4)
        if sel.sum() < 5:
            continue
        aL, bL, rmsL = line_fit(S2[sel], tL[sel])
        aR, bR, rmsR = line_fit(S2[sel], tR[sel])
        # apex: tL = tR
        s_ap = (aR - aL) / (bL - bR) if bL != bR else np.nan
        ang = math.degrees(math.atan(-bL)) + math.degrees(math.atan(bR))
        # half-angles relative to the arm axis (asymmetry check)
        tipfits["%d%%" % int(frac * 100)] = {"window_px": [round(Rr - Lw, 1), round(Rr - 4, 1)],
                                             "included_deg": round(ang, 2),
                                             "half_left_deg": round(math.degrees(math.atan(-bL)), 2),
                                             "half_right_deg": round(math.degrees(math.atan(bR)), 2),
                                             "apex_s_px": round(float(s_ap), 1), "apex_t_px": round(float(aL + bL * s_ap), 1),
                                             "rms_px": [round(rmsL, 2), round(rmsR, 2)]}
    s_apex = tipfits["10%"]["apex_s_px"]
    t_apex = tipfits["10%"]["apex_t_px"]
    apex_xy = origin + s_apex * u + t_apex * n
    R_apex = float(np.hypot(*(apex_xy - c)))
    # --- neck & blade max ---
    sel_neck = (S2 >= 100) & (S2 <= 380)
    i_neck = np.nonzero(sel_neck)[0][np.argmin(w[sel_neck])]
    s_neck = S2[i_neck]; w_neck = w[i_neck]
    sel_max = (S2 >= s_neck) & (S2 <= Rr - 20)
    i_max = np.nonzero(sel_max)[0][np.argmax(w[sel_max])]
    s_max = S2[i_max]; w_max = w[i_max]
    # junction: width where the fillets open out (w = 1.5 * neck) nearest the centre side
    sel_j = (S2 < s_neck)
    jj = np.nonzero(sel_j & (w >= 1.5 * w_neck))[0]
    s_junction = float(S2[jj.max()]) if len(jj) else np.nan
    # --- edge curvature: blade edge from max width to tip ---
    curv = {}
    for side, tt in (("left", tL), ("right", tR)):
        sel = (S2 >= s_max) & (S2 <= Rr - 6)
        xs, ys = S2[sel], tt[sel]
        cx, cy, rc, rms_c = circle_fit(xs, ys)
        a0, b0, rms_l = line_fit(xs, ys)
        # sagitta: max deviation from the chord joining the ends
        p0 = np.array([xs[0], ys[0]]); p1 = np.array([xs[-1], ys[-1]])
        dvec = (p1 - p0) / np.linalg.norm(p1 - p0)
        dev = (xs - p0[0]) * dvec[1] - (ys - p0[1]) * dvec[0]
        chord = float(np.linalg.norm(p1 - p0))
        # neck side: from junction to max width
        sel2 = (S2 >= s_neck - 50) & (S2 <= s_neck + 50)
        cx2, cy2, rc2, rms_c2 = circle_fit(S2[sel2], tt[sel2])
        # inflection between neck and max: sign change of 2nd derivative of smoothed edge
        sm = np.convolve(fill(tt), np.ones(15) / 15, mode='same')
        d2 = np.gradient(np.gradient(sm))
        seg = np.nonzero((S2 > s_neck) & (S2 < s_max))[0]
        sgn = np.sign(d2[seg]) * (1 if side == "left" else -1)
        infl = [float(S2[seg[k]]) for k in range(1, len(seg)) if sgn[k] != sgn[k - 1]]
        curv[side] = {"blade_arc_radius_px": round(rc, 1), "blade_arc_rms_px": round(rms_c, 2),
                      "blade_line_rms_px": round(rms_l, 2), "blade_chord_px": round(chord, 1),
                      "blade_sagitta_px": round(float(np.max(np.abs(dev))), 1),
                      "neck_arc_radius_px": round(rc2, 1), "neck_arc_rms_px": round(rms_c2, 2),
                      "neck_edge_concave": bool((cy2 > tt[i_neck]) if side == "left" else (cy2 < tt[i_neck])),
                      "inflections_s_px": infl[:4]}
    metrics["arms"][nme] = {
        "R_last_station_px": float(Rr), "apex_xy": apex_xy.round(1).tolist(), "R_apex_px": round(R_apex, 1),
        "neck_width_px": round(float(w_neck), 1), "neck_station_px": float(s_neck),
        "max_width_px": round(float(w_max), 1), "max_station_px": float(s_max),
        "junction_station_px": s_junction,
        "tip": tipfits, "curvature": curv,
        "width_at": {str(s): round(float(w[np.argmin(np.abs(S2 - s))]), 1) for s in range(60, int(Rr), 20)},
        "midline_offset_at_max_px": round(float(mid[i_max]), 1),
    }
    edges_img[nme] = (origin, u, n, S2, tL, tR, tipfits)
    np.savez(os.path.join(jlib.OUT, "final_edges_%s_%s.npz" % (variant, nme)), S=S2, tL=tL, tR=tR, origin=origin, u=u, n=n)

# ---- spans ----
ap = {k: np.array(v["apex_xy"]) for k, v in metrics["arms"].items()}
span_h = float(np.linalg.norm(ap["right"] - ap["left"]))
span_v = float(np.linalg.norm(ap["top"] - ap["bottom"]))
metrics["span_horizontal_px"] = round(span_h, 1)
metrics["span_vertical_px_extrapolated_top"] = round(span_v, 1)
# vertical lower bound: bottom apex to the image top row along the vertical axis
metrics["top_apex_y_px"] = round(float(ap["top"][1]), 1)
# intersection of tip-to-tip lines
p1, p2, p3, p4 = ap["left"], ap["right"], ap["bottom"], ap["top"]
d1, d2 = p2 - p1, p4 - p3
A = np.array([d1, -d2]).T
tt_ = np.linalg.solve(A, p3 - p1)
X = p1 + tt_[0] * d1
metrics["tipline_intersection_px"] = X.round(2).tolist()
ang_h = math.degrees(math.atan2(-(d1[1]), d1[0])); ang_v = math.degrees(math.atan2(-(d2[1]), d2[0]))
metrics["tipline_angles_deg"] = [round(ang_h, 2), round(ang_v, 2), round(ang_v - ang_h, 2)]
json.dump(metrics, open(os.path.join(jlib.OUT, "metrics_%s.json" % variant), "w"), indent=1)

span = span_h
print("variant", variant, "span_h %.1f  span_v(extrap) %.1f  top apex y %.1f" % (span_h, span_v, ap["top"][1]))
print("tip-line intersection", X, "angles", metrics["tipline_angles_deg"])
print("%-7s %8s %8s %8s %8s %8s %8s %8s | tip10 tip5 tip15 tip20" % ("arm", "R_apex", "neck_w", "neck_s", "max_w", "max_s", "junc_s", "R/span"))
for nme in names:
    m_ = metrics["arms"][nme]
    print("%-7s %8.1f %8.1f %8.0f %8.1f %8.0f %8.0f %8.3f | %s" % (
        nme, m_["R_apex_px"], m_["neck_width_px"], m_["neck_station_px"], m_["max_width_px"], m_["max_station_px"],
        m_["junction_station_px"], m_["R_apex_px"] / span,
        " ".join("%5.1f" % m_["tip"][k]["included_deg"] for k in ("10%", "5%", "15%", "20%") if k in m_["tip"])))
for nme in names:
    print(nme, "curv", json.dumps(metrics["arms"][nme]["curvature"]))
    print(nme, "tip halves 10%", metrics["arms"][nme]["tip"]["10%"])

# overlay
if variant == "outer":
    ov = a.copy() * 0.85
    for nme, (origin, u, n, S2, tL, tR, tipfits) in edges_img.items():
        for tt, col in ((tL, [1, 0.2, 0.2]), (tR, [0.2, 0.6, 1])):
            P = origin[None, :] + S2[:, None] * u[None, :] + tt[:, None] * n[None, :]
            for x, y in P:
                if 0 <= int(y) < H and 0 <= int(x) < W:
                    ov[int(y), int(x)] = col
        # 10% tip fit lines
        f = tipfits["10%"]
        for side in ("L", "R"):
            pass
        ap_ = metrics["arms"][nme]["apex_xy"]
        x, y = int(ap_[0]), int(ap_[1])
        ov[max(0, y - 3):max(0, y + 4), max(0, x - 3):x + 4] = [1, 1, 0]
    ov[int(c[1]) - 3:int(c[1]) + 4, int(c[0]) - 3:int(c[0]) + 4] = [1, 1, 0]
    jlib.save_png(os.path.join(jlib.OUT, "dbg_final_edges_outer.png"), ov)
