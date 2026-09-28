"""Reconcile measurer A, measurer B and this stage's validated re-measurement into one photo result per station.

Central value = median over the log-residual runs of measure_photo.py's sensitivity grid (PSF 0.3/0.6 px, probe depth cut
0/0.1, perspective ortho/300/200/135 mm FF) - the configuration validated on our renders (0.98-1.08x at the photo's
probe scale).  Range = p10-p90 of that grid.  ridge_ratio = face_slope + e / h with e = 0.75 mm (our un-ground edge
half-thickness; the photo's edge is not resolvable) and h = our half-width at the mapped station; the sharp-edge value
equals face_slope."""
import json
import math
from pathlib import Path

import numpy as np

from run_validate import FV, x_of_fvis, analytic, h_blade

HERE = Path(__file__).parent
BS = HERE.parent
R = json.loads((HERE / "photo_v3_results.json").read_text())
A = json.loads((BS / "photo_A" / "photo_A_measurement.json").read_text()) if (BS / "photo_A" / "photo_A_measurement.json").exists() else None
runs = R["runs"]
logk = [k for k in runs if k.endswith("log1")]
A_ST = {0.1: 0.306, 0.3: 0.33, 0.45: 0.355, 0.6: 0.365, 0.75: 0.36, 0.9: 0.345}
B_ST = {0.1: 0.29, 0.245: 0.178, 0.4: 0.178, 0.6: 0.178, 0.8: 0.178, 0.93: 0.178}


def interp(d, f):
    ks = sorted(d)
    return float(np.interp(f, ks, [d[k] for k in ks]))


stations = []
for i, f in enumerate(FV):
    v = np.array([runs[k]["rows"][i]["r"] for k in logk])
    base = runs[R["base"]]["rows"][i]
    x = x_of_fvis(f)
    h = h_blade(x)
    fs = float(np.median(v))
    ours = analytic(x)
    a, b = interp(A_ST, f), interp(B_ST, f)
    stations.append({
        "frac_from_shoulder": f, "section": "rear" if f < 0.262 else "front", "ours_x_mm": round(x, 1),
        "face_slope": round(fs, 3), "face_slope_p10_p90": [round(float(np.percentile(v, 10)), 3),
                                                             round(float(np.percentile(v, 90)), 3)],
        "face_angle_deg": round(math.degrees(math.atan(fs)), 1),
        "ridge_ratio": round(fs + 0.75 / h, 3), "ridge_ratio_sharp_edge": round(fs, 3),
        "measurer_A": a, "measurer_B": b, "A_vs_B_disagreement_pct": round(100 * abs(a - b) / min(a, b), 0),
        "ridge_offset_q": round(base["q"], 4), "roll_from_q_deg": round(base["roll"], 1),
        "facet_L_srgb_top_bottom": [round(base["L_top_srgb"], 1), round(base["L_bot_srgb"], 1)],
        "ours_face_slope": round(ours["face_slope"], 4), "ours_ridge_ratio": round(ours["ridge_ratio"], 4),
        "photo_over_ours_face_slope": round(fs / ours["face_slope"], 2)})
front = [s for s in stations if s["section"] == "front"]
rear = [s for s in stations if s["section"] == "rear"]
allfront = np.concatenate([[runs[k]["rows"][i]["r"] for k in logk] for i, f in enumerate(FV) if f >= 0.3])
summary = {
    "front_face_slope": round(float(np.median([s["face_slope"] for s in front])), 3),
    "front_range": [round(float(np.percentile(allfront, 10)), 3), round(float(np.percentile(allfront, 90)), 3)],
    "rear_face_slope": round(float(np.median([s["face_slope"] for s in rear])), 3),
    "front_face_angle_deg": round(math.degrees(math.atan(float(np.median([s["face_slope"] for s in front])))), 1),
    "photo_over_ours_front": round(float(np.median([s["photo_over_ours_face_slope"] for s in front])), 2),
    "front_ridge_ratio_with_our_1p5mm_edge": [min(s["ridge_ratio"] for s in front), max(s["ridge_ratio"] for s in front)],
    "shape": ("front facets planar: face_slope ~constant (0.18-0.23) from the widest point to the bark, i.e. the ridge "
              "falls in proportion to the half-width toward the tip; rear steeper (0.24-0.33 toward the shoulder), "
              "consistent with a ridge held at constant height from the shoulder to the widest crease (the same "
              "structure as our spec, 2x deeper)"),
}
out = {"summary": summary, "stations": stations,
       "mapping": ("fraction f of the VISIBLE blade (shoulder -> bark entry, measured along the axis; photo 154.4 px) "
                   "-> photo px s = f * 154.4; our x piecewise on the landmarks: shoulder->widest crease (photo 0-40.4 "
                   "px) = our 0-35 mm, widest->extrapolated tip (40.4-180.9 px) = our 35-140 mm.  The visible blade is "
                   "0.85 of shoulder->tip (both measurers), so f = 1 is our x = 120.2 mm."),
       "reconciliation": {
           "A": ("0.33-0.365 front (kernel-smoothed ring matcap sigma 0.12).  Rejected as biased: the same kernel "
                 "method on our photo-pose render reads 2.1x the known ratio (validate/final_check.json), because "
                 "blurring the probe in normal space flattens the matcap so a steeper facet is needed to reproduce the "
                 "facets' contrast.  A / 2.1 = 0.16-0.17."),
           "B": ("0.178 front, 0.29 rear (1-D up-tilt probe curve, albedo 1.1).  Agrees with the validated value within "
                 "its IQR; kept.  B's rear 0.29 is confirmed (0.24-0.33)."),
           "this_stage": ("parametric matcap forward-fitted to the ring through the pixel footprint + PSF (0.3 px), "
                          "albedo-free contrast inversion with roll from the measured ridge offset; validated 0.98-1.08x "
                          "on our renders at the photo's probe scale (0.87-1.33x per station)."),
           "residual": ("front: this stage 0.18-0.23 per station vs B 0.178 (<= 25 %); A disagrees by ~70 % until its "
                        "demonstrated bias is removed.  Remaining uncertainty is the probe fit (photo ring fit rms 0.69 "
                        "in log vs 0.25-0.35 on renders: the forged ring is pitted and only ~11 px thick) and the lens "
                        "(perspective grid).  The ring-coplanar pose (roll 23-25 deg, which would make the photo blade "
                        "as flat as ours) predicts a top/bottom facet contrast of 1.2-2.8x against the observed "
                        "11-16x (linear): rejected (photo_q_sensitivity.json).")},
       "ridge_ratio_note": "ridge_ratio uses e = 0.75 mm (our 1.5 mm un-ground edge) at our half-width; sharp = face_slope"}
(HERE / "photo_reconciled.json").write_text(json.dumps(out, indent=1))
print(json.dumps(summary, indent=1))
for s in stations:
    print(s)
