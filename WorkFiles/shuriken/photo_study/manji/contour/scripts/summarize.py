import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *

M = json.load(open(BASE + "/measurements_raw.json"))
B = json.load(open(BASE + "/bevel_raw.json"))
ARMS = ["top", "right", "bottom", "left"]
SPAN = M["span"]["span_ref_px"]
rows = []


def stat(name, vals, unit="ratio_to_span", scale=None, note=""):
    v = np.array([x for x in vals if x is not None], float)
    if scale == "span":
        v = v / SPAN
    print(f"{name:46s} mean {v.mean():9.4f}  sd {v.std(ddof=1) if len(v)>1 else 0:8.4f}  min {v.min():9.4f}  max {v.max():9.4f}  n={len(v)}  [{unit}] {note}")
    rows.append(dict(name=name, value=float(v.mean()), unit=unit, spread=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                     vmin=float(v.min()), vmax=float(v.max()), n=len(v), note=note))


print("SPAN ref (mean opposite tip-to-tip) px:", round(SPAN, 1),
      "| top-bottom", round(M["span"]["tip_top_to_tip_bottom_px"], 1),
      "| right-left", round(M["span"]["tip_right_to_tip_left_px"], 1),
      "| max Feret", round(M["span"]["feret_max_px"], 1))
print("back-to-back through centre:", {k: round(v, 1) for k, v in M["span"]["back_to_back_through_centre_px"].items()},
      "| extent in arm frame", [round(v, 1) for v in M["span"]["extent_along_arm_frame_px"]])
A = M["arms"]
stat("arm_width_at_root", [A[a]["width_root"] for a in ARMS], scale="span")
stat("arm_width_mid", [A[a]["width_mid"] for a in ARMS], scale="span")
stat("arm_width_at_hook_inner_corner", [A[a]["width_at_inner_corner"] for a in ARMS], scale="span")
stat("arm_taper_included_angle", [A[a]["taper_deg"] for a in ARMS], unit="deg")
stat("hook_root_width_perp_innercorner_to_backedge", [A[a]["hook_root_width_circle"] for a in ARMS], scale="span")
stat("hook_overhang_beyond_arm_inner_edge", [A[a]["tip_reach_beyond_inner_edge"] for a in ARMS], scale="span")
stat("hook_span_outer_edge_to_tip", [A[a]["tip_reach_from_outer_edge"] for a in ARMS], scale="span")
stat("hook_back_edge_contour_length", [A[a]["back_edge_contour_len"] for a in ARMS], scale="span")
stat("hook_inner_edge_contour_length", [A[a]["inner_edge_contour_len"] for a in ARMS], scale="span")
stat("tip_radius_from_centre", [A[a]["tip_radius"] for a in ARMS], scale="span")
stat("tip_angular_offset_from_arm_axis", [A[a]["tip_angle_from_axis_deg"] for a in ARMS], unit="deg")
stat("tip_lateral_offset_from_arm_axis", [A[a]["tip_lateral"] for a in ARMS], scale="span")
stat("radius_to_hook_inner_corner", [A[a]["r_inner_corner"] for a in ARMS], scale="span")
stat("radius_to_outer_elbow_corner", [A[a]["r_outer_elbow"] for a in ARMS], scale="span")
stat("radius_to_back_edge_on_axis", [A[a]["r_back_edge_on_axis_circle"] for a in ARMS], scale="span")
stat("tip_axial_component_along_arm", [A[a]["tip_radius"] * math.cos(math.radians(A[a]["tip_angle_from_axis_deg"])) for a in ARMS], scale="span")
stat("hook_back_edge_arc_radius", [A[a]["back_circle_R"] for a in ARMS], scale="span")
stat("hook_back_edge_sagitta_over_fitted_chord", [A[a]["back_sagitta_over_fit"] for a in ARMS], scale="span")
stat("hook_back_edge_line_fit_rms", [A[a]["back_line_rms"] for a in ARMS], unit="px")
stat("hook_back_edge_circle_fit_rms", [A[a]["back_circle_rms"] for a in ARMS], unit="px")
stat("hook_inner_edge_line_fit_rms", [A[a]["inner_line_rms"] for a in ARMS], unit="px")
stat("hook_inner_edge_max_dev_from_line", [A[a]["inner_line_maxdev"] for a in ARMS], unit="px")
stat("arm_edge_line_fit_rms", [A[a]["outer_line_rms"] for a in ARMS] + [A[a]["inner_arm_line_rms"] for a in ARMS], unit="px")
stat("hook_inner_edge_angle_to_arm_axis", [A[a]["hook_inner_edge_vs_axis_deg"] for a in ARMS], unit="deg")
stat("hook_back_edge_chordline_angle_to_arm_axis", [A[a]["hook_back_edge_vs_axis_deg"] for a in ARMS], unit="deg")
stat("tip_included_angle_local_tangents", [A[a]["tip_angle_local_deg"] for a in ARMS], unit="deg")
stat("tip_included_angle_chord_lines", [A[a]["tip_angle_between_fitted_lines_deg"] for a in ARMS], unit="deg")
stat("tip_setback_from_flank_intersection", [A[a]["tip_setback_from_flank_intersection_px"] for a in ARMS], unit="px")
stat("tip_equiv_round_radius", [A[a]["tip_setback_from_flank_intersection_px"] * math.sin(math.radians(A[a]["tip_angle_local_deg"]) / 2) / (1 - math.sin(math.radians(A[a]["tip_angle_local_deg"]) / 2)) for a in ARMS], unit="px")
Cn = M["corners"]
stat("outer_elbow_corner_angle", [Cn[f"{a}_outer_elbow"]["angle_deg"] for a in ARMS], unit="deg")
stat("outer_elbow_fillet_equiv_radius", [Cn[f"{a}_outer_elbow"]["fillet_r_equiv_px"] for a in ARMS], unit="px")
stat("hook_inner_corner_angle", [Cn[f"{a}_inner_corner"]["angle_deg"] for a in ARMS], unit="deg")
stat("hook_inner_corner_fillet_equiv_radius", [Cn[f"{a}_inner_corner"]["fillet_r_equiv_px"] for a in ARMS], unit="px")
cen = [k for k in Cn if k.startswith("centre_")]
stat("centre_corner_angle", [Cn[k]["angle_deg"] for k in cen], unit="deg")
stat("centre_corner_fillet_equiv_radius", [Cn[k]["fillet_r_equiv_px"] for k in cen], unit="px")
print("centre corner fillets individually:", {k: round(Cn[k]["fillet_r_equiv_px"], 1) for k in cen})
print("elbow fillets individually:", {a: round(Cn[f'{a}_outer_elbow']['fillet_r_equiv_px'], 1) for a in ARMS})
print("inner corner fillets individually:", {a: round(Cn[f'{a}_inner_corner']['fillet_r_equiv_px'], 1) for a in ARMS})
bw = lambda k: B[k]["band_decay_width_px"]
stat("bevel_band_width_hook_back_edges", [bw(f"{a}_hook_back")["per_sample_median"] for a in ARMS], unit="px")
stat("bevel_band_width_hook_inner_edges", [bw(f"{a}_hook_inner")["per_sample_median"] for a in ARMS], unit="px")
stat("bevel_band_width_arm_edges", [bw(f"{a}_arm_outer")["per_sample_median"] for a in ARMS] + [bw(f"{a}_arm_inner")["per_sample_median"] for a in ARMS], unit="px")
print("per-edge band medians (px):", {k: round(bw(k)["per_sample_median"], 1) for k in B})
print("per-edge band per-sample sd (px):", {k: round(bw(k)["per_sample_sd"], 1) for k in B})
print("per-edge band peak excess L / warm:", {k: (round(bw(k)["peak_excess_L"], 3), round(bw(k)["peak_excess_warm"], 3)) for k in B})
print()
print("axis angles adjacent:", {k: round(v, 3) for k, v in M["axis_angles_adjacent_deg"].items()})
print("opposite-arm bend from straight:", {k: round(v, 3) for k, v in M["axis_opposite_deviation_from_straight_deg"].items()})
print("handedness signs:", M["handedness_sign"])
print("centre:", [round(v, 1) for v in M["centre"]["axes_intersection"]], "centroid", [round(v, 1) for v in M["centre"]["mask_centroid"]],
      "tip centroid", [round(v, 1) for v in M["centre"]["tip_centroid"]])
print("centre disc r", round(M["centre"]["centre_disc_radius_px"], 1), "Lmax", round(M["centre"]["centre_disc_L_max"], 3),
      "bg-like px", M["centre"]["centre_disc_bglike_px"])
print("contour", M["contour"])
json.dump(rows, open(BASE + "/summary_rows.json", "w"), indent=1)
