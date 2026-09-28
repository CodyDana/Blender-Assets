"""Physical tips, tip angles referenced to the tip, aggregated blade metrics and ratios to the span."""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
ab = jlib.gblur(a, 0.7)
names = ["right", "top", "left", "bottom"]
g1 = json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))
c = np.array(g1["centre_candidates_px"]["sym90"])
met = {v: json.load(open(os.path.join(jlib.OUT, "metrics_%s.json" % v))) for v in ("outer", "inner")}
res = {"centre_px": c.tolist()}


def line_fit(xs, ys):
    A = np.stack([xs, np.ones_like(xs)], 1)
    (b, a0), *_ = np.linalg.lstsq(A, ys, rcond=None)
    return a0, b, float(np.sqrt(((ys - (a0 + b * xs)) ** 2).mean()))


# ---------- physical tips ----------
tips = {}
for nm in names:
    z = np.load(os.path.join(jlib.OUT, "final_edges_outer_%s.npz" % nm))
    S, tL, tR, origin, u, n = z["S"], z["tL"], z["tR"], z["origin"], z["u"], z["n"]
    t_mid = float(np.median(0.5 * (tL + tR)[-40:]))
    s_axis = np.arange(560, 760, 0.5)
    P = origin[None, :] + s_axis[:, None] * u[None, :] + t_mid * n[None, :]
    inimg = (P[:, 0] >= 1) & (P[:, 0] <= W - 2) & (P[:, 1] >= 1) & (P[:, 1] <= H - 2)
    acc = np.zeros((len(s_axis), 3))
    for dt in (-1.5, -0.75, 0, 0.75, 1.5):
        Pp = origin[None, :] + s_axis[:, None] * u[None, :] + (t_mid + dt) * n[None, :]
        acc += jlib.bilinear(ab, np.clip(Pp[:, 0], 0, W - 1.01), np.clip(Pp[:, 1], 0, H - 1.01))
    col = acc / 5
    Rws = met["outer"]["arms"][nm]["R_last_station_px"]
    good = np.nonzero(inimg)[0]
    s_last = s_axis[good.max()]
    info = {"axis_last_in_image_s_px": float(s_last)}
    if s_last > Rws + 11:
        sel_bg = inimg & (s_axis > min(s_last, Rws + 45) - 9) & (s_axis <= min(s_last, Rws + 45))
        B = np.median(col[sel_bg], 0)
        O = np.median(col[(s_axis > Rws - 50) & (s_axis < Rws - 25)], 0)
        v = O - B
        f = (col - B) @ v / (v @ v)
        s_cross = np.nan
        for j in range(good.max() - 1, 0, -1):
            if f[j] >= 0.5:
                s_cross = s_axis[j] + (0.5 - f[j]) / (f[j + 1] - f[j]) * (s_axis[j + 1] - s_axis[j])
                break
        xy = origin + s_cross * u + t_mid * n
        info.update(clipped=False, tip_s_px=round(float(s_cross), 1), tip_xy=xy.round(1).tolist(),
                    R_tip_px=round(float(np.hypot(*(xy - c))), 1))
    else:
        info.update(clipped=True)
    tips[nm] = info
# top arm: estimate from the mean (apex - tip) offset of the others
off = [met["outer"]["arms"][nm]["R_apex_px"] - tips[nm]["R_tip_px"] for nm in names if not tips[nm]["clipped"]]
if tips["top"]["clipped"]:
    est = met["outer"]["arms"]["top"]["R_apex_px"] - float(np.mean(off))
    tips["top"].update(R_tip_px_estimated=round(est, 1), estimate_note="virtual apex minus the mean apex-to-tip"
                       " rounding offset of the three complete tips (%.1f +- %.1f px)" % (np.mean(off), np.std(off)),
                       R_tip_px_lower_bound=round(float(met["outer"]["arms"]["top"]["R_last_station_px"]), 1))
res["tips"] = tips
res["apex_to_physical_tip_offset_px"] = {"values": [round(o, 1) for o in off], "mean": round(float(np.mean(off)), 1)}

R_tip = {nm: (tips[nm]["R_tip_px"] if not tips[nm]["clipped"] else tips[nm]["R_tip_px_estimated"]) for nm in names}
span_h = float(np.hypot(*(np.array(tips["right"]["tip_xy"]) - np.array(tips["left"]["tip_xy"]))))
span_v_est = R_tip["top"] + R_tip["bottom"]
res["span_px"] = {"horizontal_tip_to_tip_measured": round(span_h, 1),
                  "vertical_tip_to_tip_top_estimated": round(span_v_est, 1),
                  "vertical_lower_bound_bottom_tip_to_image_top_row": round(float(tips["bottom"]["tip_xy"][1]) + 0.0, 1),
                  "mean_2R": round(float(np.mean(list(R_tip.values())) * 2), 1)}
span = span_h
res["span_used_px"] = round(span, 1)

# ---------- tip angles referenced to the physical tip ----------
tipang = {}
for nm in names:
    z = np.load(os.path.join(jlib.OUT, "final_edges_outer_%s.npz" % nm))
    S, tL, tR = z["S"], z["tL"], z["tR"]
    Rt = tips[nm]["tip_s_px"] if not tips[nm]["clipped"] else float(S[-1]) + (R_tip["top"] - met["outer"]["arms"]["top"]["R_last_station_px"])
    d = {}
    for frac in (0.03, 0.05, 0.075, 0.10, 0.15):
        L = frac * span
        sel = (S >= Rt - L) & (S <= Rt - 6)
        if sel.sum() < 6:
            continue
        aL, bL, rL = line_fit(S[sel], tL[sel])
        aR, bR, rR = line_fit(S[sel], tR[sel])
        d["%.1f%%span" % (frac * 100)] = {"window_from_tip_px": [round(6, 1), round(L, 1)],
                                          "included_deg": round(math.degrees(math.atan(-bL)) + math.degrees(math.atan(bR)), 2),
                                          "rms_px": [round(rL, 2), round(rR, 2)], "n": int(sel.sum())}
    tipang[nm] = d
res["tip_included_angle"] = tipang
for key in ("3.0%span", "5.0%span", "7.5%span", "10.0%span", "15.0%span"):
    vals = [tipang[nm][key]["included_deg"] for nm in names if key in tipang[nm]]
    if vals:
        res.setdefault("tip_angle_summary", {})[key] = {"mean": round(float(np.mean(vals)), 1),
                                                        "sd": round(float(np.std(vals)), 1),
                                                        "min": round(min(vals), 1), "max": round(max(vals), 1),
                                                        "per_arm": {nm: round(tipang[nm][key]["included_deg"], 1) for nm in names if key in tipang[nm]}}

# ---------- width profile metrics, both variants ----------
prof = {}
for v in ("outer", "inner"):
    pv = {}
    for nm in names:
        z = np.load(os.path.join(jlib.OUT, "final_edges_%s_%s.npz" % (v, nm)))
        S, tL, tR = z["S"], z["tL"], z["tR"]
        w = tL - tR
        Rt = R_tip[nm]
        sel_n = (S >= 110) & (S <= 380)
        i_n = np.nonzero(sel_n)[0][np.argmin(w[sel_n])]
        sel_m = (S >= S[i_n]) & (S <= Rt - 40)
        i_m = np.nonzero(sel_m)[0][np.argmax(w[sel_m])]
        # steepest widening between neck and max (the ogee inflection)
        seg = np.nonzero((S > S[i_n]) & (S < S[i_m]))[0]
        dw = np.gradient(np.convolve(w, np.ones(11) / 11, 'same'))
        i_i = seg[np.argmax(dw[seg])] if len(seg) else i_n
        # width at fractions of the tip radius
        wf = {}
        for fr in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            j = int(np.argmin(np.abs(S - fr * Rt)))
            wf["%.1f" % fr] = round(float(w[j]), 1)
        pv[nm] = {"R_tip_px": round(Rt, 1), "R_tip_over_span": round(Rt / span, 4),
                  "neck_width_px": round(float(w[i_n]), 1), "neck_station_px": float(S[i_n]),
                  "neck_width_over_span": round(float(w[i_n]) / span, 4),
                  "neck_station_over_R": round(float(S[i_n]) / Rt, 3),
                  "max_width_px": round(float(w[i_m]), 1), "max_station_px": float(S[i_m]),
                  "max_width_over_span": round(float(w[i_m]) / span, 4),
                  "max_station_over_R": round(float(S[i_m]) / Rt, 3),
                  "max_over_neck": round(float(w[i_m] / w[i_n]), 3),
                  "inflection_station_px": float(S[i_i]), "inflection_over_R": round(float(S[i_i]) / Rt, 3),
                  "width_at_fraction_of_R": wf}
    for key in ("neck_width_px", "max_width_px", "neck_station_over_R", "max_station_over_R", "max_over_neck",
                "neck_width_over_span", "max_width_over_span", "R_tip_over_span", "inflection_over_R"):
        vals = [pv[nm][key] for nm in names]
        pv.setdefault("summary", {})[key] = {"mean": round(float(np.mean(vals)), 4), "sd": round(float(np.std(vals)), 4),
                                             "min": min(vals), "max": max(vals)}
    prof[v] = pv
res["width_profile"] = prof

# ---------- curvature summary (from metrics_outer) ----------
cv = {}
for nm in names:
    d = met["outer"]["arms"][nm]["curvature"]
    cv[nm] = {side: {"blade_arc_radius_over_span": round(d[side]["blade_arc_radius_px"] / span, 3),
                     "blade_arc_rms_px": d[side]["blade_arc_rms_px"], "blade_line_rms_px": d[side]["blade_line_rms_px"],
                     "blade_sagitta_over_chord": round(d[side]["blade_sagitta_px"] / d[side]["blade_chord_px"], 4),
                     "neck_arc_radius_over_span": round(d[side]["neck_arc_radius_px"] / span, 3),
                     "neck_edge_concave": d[side]["neck_edge_concave"]} for side in ("left", "right")}
res["edge_curvature"] = cv
vals = [cv[nm][s]["blade_arc_radius_over_span"] for nm in names for s in ("left", "right")]
res["blade_arc_radius_over_span_summary"] = {"mean": round(float(np.mean(vals)), 3), "sd": round(float(np.std(vals)), 3),
                                             "min": min(vals), "max": max(vals)}

# ---------- patina colours ----------
def med_hex(ys, xs):
    v = np.median(a[ys, xs].reshape(-1, 3), 0)
    return "#%02x%02x%02x" % tuple(int(round(x * 255)) for x in v), [round(float(x), 3) for x in v]


panel = np.load(os.path.join(jlib.OUT, "panel_mask.npy"))
m = np.load(os.path.join(jlib.OUT, "mask_ref.npy")).astype(bool)
inner = jlib.erode(m, 6)
bevel = inner & ~jlib.dilate(panel, 4)
ys, xs = np.nonzero(bevel)
res["colour"] = {"ground_bevel_median": med_hex(ys, xs),
                 "ground_bevel_p10_p90_lum": [round(float(np.percentile(a[bevel].reshape(-1, 3).mean(1), q)), 3) for q in (10, 90)],
                 "dark_panel_median": med_hex(*np.nonzero(panel)),
                 }
sel = np.zeros_like(m); sel[660:680, 860:940] = True
res["colour"]["lit_lower_bevel_right_arm"] = med_hex(*np.nonzero(sel))
sel = np.zeros_like(m); sel[620:640, 860:940] = True
res["colour"]["shaded_upper_bevel_right_arm"] = med_hex(*np.nonzero(sel))
sel = np.zeros_like(m); sel[800:900, 660:690] = True
res["colour"]["lit_bevel_bottom_arm_west"] = med_hex(*np.nonzero(sel))
sel = np.zeros_like(m); sel[1000:1100, 690:730] = True
res["colour"]["dark_panel_bottom_arm"] = med_hex(*np.nonzero(sel))

json.dump(res, open(os.path.join(jlib.OUT, "summary.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("tip_included_angle",)}, indent=1))
