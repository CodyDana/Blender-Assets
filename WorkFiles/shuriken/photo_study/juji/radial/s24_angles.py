"""Arm bearings from the centre, inter-arm angles, opposite-arm collinearity, and a few final aggregates."""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

names = ["right", "top", "left", "bottom"]
g1 = json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))
c = np.array(g1["centre_candidates_px"]["sym90"])
summ = json.load(open(os.path.join(jlib.OUT, "summary.json")))
jp = json.load(open(os.path.join(jlib.OUT, "junction_panels.json")))
met = json.load(open(os.path.join(jlib.OUT, "metrics_outer.json")))
span = summ["span_used_px"]
out = {"span_px": span}

bear = {}
for nm in names:
    t = summ["tips"][nm]
    if not t["clipped"]:
        p = np.array(t["tip_xy"])
    else:
        z = np.load(os.path.join(jlib.OUT, "final_edges_outer_%s.npz" % nm))
        R = summ["tips"][nm]["R_tip_px_estimated"]
        u = z["u"]; origin = z["origin"]
        tmid = float(np.median(0.5 * (z["tL"] + z["tR"])[-40:]))
        p = origin + R * u + tmid * z["n"]
    bear[nm] = math.degrees(math.atan2(-(p[1] - c[1]), p[0] - c[0])) % 360
out["arm_bearing_deg_from_centre"] = {k: round(v, 2) for k, v in bear.items()}
order = ["right", "top", "left", "bottom"]
inter = {}
for i in range(4):
    a1, a2 = bear[order[i]], bear[order[(i + 1) % 4]]
    inter["%s->%s" % (order[i], order[(i + 1) % 4])] = round((a2 - a1) % 360, 2)
out["inter_arm_angles_deg"] = inter
vals = list(inter.values())
out["inter_arm_angle_stats"] = {"mean": round(float(np.mean(vals)), 2), "sd": round(float(np.std(vals)), 2),
                                "min": min(vals), "max": max(vals)}
out["opposite_arm_collinearity_deg"] = {"right_left": round(abs(((bear["left"] - bear["right"]) % 360) - 180), 2),
                                        "top_bottom": round(abs(((bear["bottom"] - bear["top"]) % 360) - 180), 2)}
R = {nm: (summ["tips"][nm]["R_tip_px"] if not summ["tips"][nm]["clipped"] else summ["tips"][nm]["R_tip_px_estimated"]) for nm in names}
out["R_tip_px"] = R
out["R_tip_stats"] = {"mean": round(float(np.mean(list(R.values()))), 1), "sd": round(float(np.std(list(R.values()))), 1),
                      "min": round(min(R.values()), 1), "max": round(max(R.values()), 1),
                      "range_pct_of_mean": round(100 * (max(R.values()) - min(R.values())) / float(np.mean(list(R.values()))), 2)}
# notches
nr = [n["r_notch_px"] for n in jp["notches"]]
fr = [n["fillet_radius_px"] for n in jp["notches"]]
out["notch_r_px"] = {"values": nr, "mean": round(float(np.mean(nr)), 1), "sd": round(float(np.std(nr)), 1),
                     "mean_over_span": round(float(np.mean(nr)) / span, 4)}
out["fillet_radius_px"] = {"values": fr, "mean": round(float(np.mean(fr)), 1), "sd": round(float(np.std(fr)), 1),
                           "mean_over_span": round(float(np.mean(fr)) / span, 4),
                           "all_concave": all(n["fillet_centre_outside_piece"] for n in jp["notches"])}
# panel / bevel aggregates (arms with a full panel run)
pa = {nm: jp["arms"][nm] for nm in names if jp["arms"][nm].get("panel_length_px", 0) > 100}
out["panel"] = {
    "arms_with_full_panel": list(pa.keys()),
    "length_px": {nm: pa[nm]["panel_length_px"] for nm in pa},
    "length_over_span": {nm: round(pa[nm]["panel_length_px"] / span, 4) for nm in pa},
    "start_over_R": {nm: round(pa[nm]["panel_s_start_px"] / R[nm], 3) for nm in pa},
    "end_over_R": {nm: round(pa[nm]["panel_s_end_px"] / R[nm], 3) for nm in pa},
    "max_width_px": {nm: pa[nm]["panel_max_width_px"] for nm in pa},
    "max_width_over_span": {nm: round(pa[nm]["panel_max_width_px"] / span, 4) for nm in pa},
    "max_width_over_blade_max_width": {nm: round(pa[nm]["panel_max_width_px"] / summ["width_profile"]["outer"][nm]["max_width_px"], 3) for nm in pa},
    "centre_offset_from_axis_px": {nm: pa[nm]["panel_centre_offset_at_max_px(+ = arm's left)"] for nm in pa},
}
bb = []
for nm in pa:
    bb += [pa[nm]["bevel_band_left_median_px"], pa[nm]["bevel_band_right_median_px"]]
out["bevel_band_px"] = {"values": bb, "mean": round(float(np.mean(bb)), 1), "sd": round(float(np.std(bb)), 1),
                        "mean_over_span": round(float(np.mean(bb)) / span, 4),
                        "min_over_span": round(min(bb) / span, 4), "max_over_span": round(max(bb) / span, 4)}
# diamond
out["diamond"] = {"vertex_r_px": jp["diamond_vertex_r_px"], "mean_vertex_r_over_span": round(jp["diamond_mean_vertex_r_px"] / span, 4),
                  "side_mid_r_over_span": round(jp["diamond_mean_side_mid_r_px"] / span, 4),
                  "side_over_vertex_ratio": jp["diamond_side_mid_over_vertex"],
                  "extent_horizontal_over_span": round(jp["diamond_extent_horizontal_px"] / span, 4),
                  "extent_vertical_over_span": round(jp["diamond_extent_vertical_px"] / span, 4),
                  "area_px": jp["diamond_px_area"],
                  "area_over_span2": round(jp["diamond_px_area"] / span ** 2, 5)}
json.dump(out, open(os.path.join(jlib.OUT, "angles_final.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
