# Assemble final ratios/angles (method B) into results.json.
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FN = pickle.load(open(os.path.join(OUT, "final.pkl"), "rb")); RAW, COR = FN["RAW"], FN["COR"]
LF = pickle.load(open(os.path.join(OUT, "litfit.pkl"), "rb"))
BN = pickle.load(open(os.path.join(OUT, "bevel_notch.pkl"), "rb"))
SH = pickle.load(open(os.path.join(OUT, "shadow.pkl"), "rb"))
seg = json.load(open(os.path.join(OUT, "seg_info.json")))
S = COR["span"]
hubL = LF["hub_lit_0.1"]; holeL = LF["hole_lit_0.0"]
CH = np.array([hubL["cx"], hubL["cy"]]); RH = hubL["r"]


def st(v):
    v = np.asarray(v, float)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0, min=float(v.min()), max=float(v.max()), n=int(len(v)), values=[round(float(x), 4) for x in v])


pts = COR["pts"]
res = {}
res["span_px"] = S
res["span_pairs_obs_px_cor"] = COR["span_obs"]; res["span_pairs_obs_px_raw"] = RAW["span_obs"]
res["span_pairs_apex_px_cor"] = COR["span_apex"]
res["clipped_points"] = [i for i, p in enumerate(pts) if p["clipped"]]
axes = np.array([p["axis_deg"] for p in pts])
sp = np.diff(np.r_[axes, axes[0] - 360] * -1)  # descending axes order
sp = (-(np.r_[axes[1:], axes[0] - 360] - axes))
res["axis_deg"] = st(axes); res["axis_spacing_deg"] = st(sp)
res["axis_offset_ratio"] = st([p["axis_offset"] / S for p in pts])
# tips relative to lit hub centre
tipr = []
for p in pts:
    t = COR["CH"] + p["obs_tip_rho_est"] * p["axis"]
    tipr.append(np.linalg.norm(t - CH))
res["tip_radius_from_hub_centre_ratio"] = st(np.array(tipr) / S)
res["tip_angle_deg_cor"] = st([p["angle"] for p in pts]); res["tip_angle_deg_raw"] = st([p["angle"] for p in RAW["pts"]])
res["taper_inner40_deg"] = st([p["taper_inner40"] for p in RAW["pts"]]); res["taper_outer40_deg"] = st([p["taper_outer40"] for p in RAW["pts"]])
res["taper_mid_deg"] = st([p["taper_mid"] for p in RAW["pts"]])
res["edge_line_rms_px_raw"] = st([p[s]["rms"] for p in RAW["pts"] for s in "AB"])
res["edge_sagitta_px_raw"] = st([p[s]["sagitta_px"] for p in RAW["pts"] for s in "AB"])
res["edge_sagitta_ratio_raw"] = st([p[s]["sagitta_px"] / S for p in RAW["pts"] for s in "AB"])
res["edge_fit_len_px"] = st([p[s]["full_len"] for p in RAW["pts"] for s in "AB"])
res["width_linear_rms_px_raw"] = st([p["width_linear_rms"] for p in RAW["pts"]])
res["hub_radius_ratio_litfit"] = RH / S; res["hub_diam_ratio_litfit"] = 2 * RH / S
res["hub_litfit"] = hubL
res["hub_diam_ratio_cor_allarcs"] = 2 * COR["hub"]["r"] / S; res["hub_diam_ratio_raw"] = 2 * RAW["hub"]["r"] / RAW["span"]
res["hub_arc_r_about_centre_ratio_cor"] = st([g["r_mean"] / S for g in COR["gaps"]])
res["hole_diam_ratio_litfit"] = 2 * holeL["r"] / S; res["hole_litfit"] = holeL
res["hole_diam_ratio_cor_all"] = 2 * COR["hole"]["r"] / S; res["hole_diam_ratio_raw"] = 2 * RAW["hole"]["r"] / RAW["span"]
res["hole_ellipse_ratio_cor"] = COR["hole_ellipse_ratio"]; res["hole_ellipse_ratio_raw"] = RAW["hole_ellipse_ratio"]
res["hole_over_hub_diam"] = holeL["r"] / RH
res["hole_hub_centre_offset_ratio"] = float(np.hypot(holeL["cx"] - hubL["cx"], holeL["cy"] - hubL["cy"]) / S)
tc = COR["tip_circle"]
res["tipcircle_hub_centre_offset_ratio"] = float(np.hypot(tc["cx"] - hubL["cx"], tc["cy"] - hubL["cy"]) / S)
# base width at the lit hub circle using corrected edge lines
bw, bang, root_ang, reentrant, lengths = [], [], [], [], []
roots_by_pt = []
for p in pts:
    rts = []
    for s in "AB":
        cen, dv = p[s]["cen"], p[s]["dir"]
        b = np.dot(cen - CH, dv); cc = np.dot(cen - CH, cen - CH) - RH * RH
        tr = -b + np.sqrt(b * b - cc)
        rt = cen + tr * dv; rts.append(rt)
        ur = (rt - CH) / np.linalg.norm(rt - CH)
        alpha = np.degrees(np.arccos(np.clip(np.dot(dv, ur), -1, 1)))
        root_ang.append(alpha); reentrant.append(90 + alpha)
    roots_by_pt.append(rts)
    bw.append(np.linalg.norm(rts[0] - rts[1]))
    a0 = np.arctan2(-(rts[0] - CH)[1], (rts[0] - CH)[0]); a1 = np.arctan2(-(rts[1] - CH)[1], (rts[1] - CH)[0])
    bang.append(abs(np.degrees(np.angle(np.exp(1j * (a0 - a1))))))
    lengths.append((p["obs_tip_rho_est"] - RH))
res["base_width_ratio"] = st(np.array(bw) / S); res["base_angle_at_hub_centre_deg"] = st(bang)
res["base_width_ratio_raw"] = st([p["base_width"] / RAW["span"] for p in RAW["pts"]])
res["edge_to_radial_angle_at_root_deg"] = st(root_ang); res["reentrant_corner_angle_deg"] = st(reentrant)
res["point_length_hub_to_tip_ratio"] = st(np.array(lengths) / S)
# exposed arc between adjacent points: angle from pt i root B to pt i+1 root A
ex = []
for i in range(6):
    rb = roots_by_pt[i][1]; ra = roots_by_pt[(i + 1) % 6][0]
    a0 = np.arctan2(-(rb - CH)[1], (rb - CH)[0]); a1 = np.arctan2(-(ra - CH)[1], (ra - CH)[0])
    ex.append(abs(np.degrees(np.angle(np.exp(1j * (a0 - a1))))))
res["exposed_hub_arc_deg"] = st(ex)
# gap opening angle between adjacent point edges (B of i, A of i+1)
gap = []
for i in range(6):
    d1 = pts[i]["B"]["dir"]; d2 = pts[(i + 1) % 6]["A"]["dir"]
    gap.append(np.degrees(np.arccos(np.clip(np.dot(d1, d2), -1, 1))))
res["adjacent_edge_opening_angle_deg"] = st(gap)
# tips
res["tip_gap_apex_to_obs_px_cor"] = st([p["tip_gap"] for p in pts if not p["clipped"]])
res["tip_nose_radius_from_gap_ratio_cor"] = st([p["tip_radius_from_gap"] / S for p in pts if not p["clipped"]])
blur_gap = 8.0
res["tip_nose_radius_blur_corrected_ratio"] = st([max(0.0, (p["tip_gap"] - blur_gap)) / (1 / np.sin(np.radians(p["angle"] / 2)) - 1) / S for p in pts if not p["clipped"]])
res["apex_span_over_obs_span"] = float(np.mean(list(COR["span_apex"].values())) / S)
# bevel bands (exclude root 0-0.1 and tip 0.9-1 groups; exclude implausible >16 px or peaks deep inside)
bands_lit, bands_sh, bands_all = [], [], []
for e in BN["edges"]:
    for r in e["rows"][1:5]:
        if r is None: continue
        if r["s_width"] > 16 or r["s_out"] < -12 and e["lit"]: continue
        (bands_lit if e["lit"] else bands_sh).append(r["s_width"]); bands_all.append(r["s_width"])
res["bevel_band_width_ratio_lit"] = st(np.array(bands_lit) / S); res["bevel_band_width_ratio_shadow"] = st(np.array(bands_sh) / S)
res["bevel_band_width_ratio_all"] = st(np.array(bands_all) / S)
res["bevel_band_px_median"] = float(np.median(bands_all))
res["bevel_present_edges"] = sum(1 for e in BN["edges"] if all(r is not None and r["s_peak"] > r["s_face"] + 0.1 for r in e["rows"][:5]))
# junction notches
jn = BN["junctions"]
res["junction_min_dev_px"] = {f"pt{j['point']}{j['side']}": round(j["min_dev"], 2) for j in jn}
res["junction_max_dev_px"] = {f"pt{j['point']}{j['side']}": round(j["max_dev"], 2) for j in jn}
res["shadow_model"] = dict(direction_image_deg=SH["shadow_dir_deg"], length_px=SH["Ls"], length_ratio=SH["Ls"] / S, rms_px=SH["rms"])
res["segmentation"] = seg
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=float)
for k, v in res.items():
    if isinstance(v, dict) and "mean" in v:
        print(f"{k}: mean {v['mean']:.4f} sd {v['sd']:.4f} [{v['min']:.4f}, {v['max']:.4f}] n{v['n']}")
    elif isinstance(v, float):
        print(f"{k}: {v:.4f}")
    else:
        print(k, v if not isinstance(v, dict) or len(str(v)) < 300 else str(v)[:300])
