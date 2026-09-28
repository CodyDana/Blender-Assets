"""Assemble WorkFiles/SnowFlowerHeels/heels_spec.json from the traces, the silhouettes and metro_measure output.
usage: python metro_write_spec.py <sil.json>"""
import sys, os, json, hashlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metro_traces as mt

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/SnowFlowerHeels"
REFPNG = ROOT + "/References/SnowFlowerHeels/snowflowerheels_reference.png"
sil = json.load(open(sys.argv[1]))
meas = json.load(open(OUT + "/heels_spec_measure.json"))
T = mt.T

def along(view, p):
    fr = np.array(T[view + ".toplift_front_corner"]["pts"][0]); toe = np.array(T[view + ".toe_tip"]["pts"][0]); ax = toe - fr; L = np.hypot(*ax)
    q = np.asarray(p, float) - fr
    return [round(float(q @ ax / L**2), 4), round(float((ax[0]*q[1] - ax[1]*q[0]) / L**2), 4)]

GROUND = {"A": 917.3, "B": 792.3}
key = {  # name: (view, xy)
 "A": {"toe_tip": (869, 1172), "toplift_front_corner": (107.4, 917.3), "heel_breast_arch_apex": (160, 628), "seat_back_silhouette_y600": (67, 600),
       "counter_rearmost": (10, 371), "collar_top_far_panel": (171, 26), "crest_spike_tip": (118, 8), "buckle_blossom": (201, 221), "strap_stud": (308, 244),
       "strap_fold": (470, 248), "insole_emblem_top": (163, 405), "insole_emblem_bottom": (248, 535), "insole_blossom_1": (345, 737), "insole_blossom_2": (300, 812),
       "opening_front_edge_low": (118, 560), "piping_start": (205, 745), "far_side_throat_corner": (402, 727), "piping_end_at_toe_plate": (612, 878),
       "toe_apex_spike_tip": (625, 818), "toe_blossom": (672, 913), "toe_keystone": (683, 963), "toe_cap_rear": (690, 1000), "vamp_blossom": (475, 955),
       "vine_frame_corner": (268, 1006), "counter_blossom": (72, 575)},
 "B": {"toe_tip": (1234, 1027), "toplift_front_corner": (633.6, 792.3), "heel_breast_arch_apex": (677, 530), "crest_spike_tip": (686, 37), "collar_top_far_panel_visible": (701, 64),
       "buckle_blossom": (750, 230), "strap_stud": (835, 249), "strap_fold": (1013, 263), "insole_emblem_top": (720, 427), "insole_emblem_bottom": (792, 523),
       "insole_blossom": (857, 730), "toe_apex_spike_tip": (1062, 743), "toe_blossom": (1095, 832), "vamp_frame_notch": (950, 820), "vamp_bud": (938, 893)},
}
lm = {}
for v, d in key.items():
    L = meas["image_proportions"][v]["len_toplift_front_to_toe_px"]
    lm[v] = {k: {"xy": list(p), "along_across_over_len": along(v, p), "height_above_ground_px": round(GROUND[v] - p[1], 1),
                 "height_over_len": round((GROUND[v] - p[1]) / L, 4)} for k, p in d.items()}
hA = GROUND["A"] - 628; hB = GROUND["B"] - 530
vert = {"note": "vertical image extents above the top-lift ground corner; ratios to the heel-breast arch height are the most camera-independent proportions",
        "A": {k: round((GROUND["A"] - p[1]) / hA, 3) for k, p in key["A"].items() if k in ("buckle_blossom", "strap_fold", "collar_top_far_panel", "crest_spike_tip", "insole_emblem_top", "toe_apex_spike_tip", "seat_back_silhouette_y600")},
        "B": {k: round((GROUND["B"] - p[1]) / hB, 3) for k, p in key["B"].items() if k in ("buckle_blossom", "strap_fold", "collar_top_far_panel_visible", "crest_spike_tip", "insole_emblem_top", "toe_apex_spike_tip")},
        "toplift_height_px": {"A": 23.5, "B": 27.0}, "heel_breast_arch_apex_height_px": {"A": hA, "B": hB}}

spec = {
 "meta": {"asset": "Snow Flower heels (SKM_SnowFlowerHeels)", "role": "reference metrology", "date": "2026-09-27",
          "reference": {"path": "References/SnowFlowerHeels/snowflowerheels_reference.png", "size": [1254, 1254],
                        "sha256": hashlib.sha256(open(REFPNG, "rb").read()).hexdigest(), "ignore": "snowflowerheels_reference_OLD_superseded.png"},
          "coords": "reference pixels, origin top-left, x right, y down; 'along/across' = coordinates in the frame toplift_front_corner -> toe_tip (along 0..1, across + = below the axis line), divided by that length",
          "scripts": ["Scripts/SnowFlowerHeels/metro_png.py", "metro_common.py", "metro_crop.py", "metro_traces.py", "metro_overlay.py", "metro_measure.py", "metro_write_spec.py"],
          "view_A": "front/left shoe in the image (larger, sharper, most ornament) = DESIGN AUTHORITY",
          "view_B": "rear/right shoe in the image, ~0.85x scale, yawed ~4.5 deg more toward camera; use for geometry cross-check only where it agrees"},
 "left_right": {
     "visible_side": "both views show the SAME side: the wearer's RIGHT side (toe toward camera-right, heel away-left, camera above at ~22 deg)",
     "pair_or_twice": "not a mirrored pair: both shoes show the open side, buckle and ornament on their right side, so the image is two views of one right-side design",
     "recommended_assignment": "treat the reference as the RIGHT shoe seen from its OUTER (lateral) side: ankle-strap buckles sit on the outside of the ankle and product shots show the outer side. Build the right shoe as shown; the LEFT shoe is its exact mirror across the sagittal plane (open side, buckle, counter ornament and vamp vine all on the outer side).",
     "alternative": "the image cannot rule out a LEFT shoe seen from its inner side (half-d'Orsay open on the arch side); nothing in the reference shows the other side of either shoe. Decision for the user/Study if they want the opening on the inner side instead.",
     "mirror_rules": ["every silver element, the vine directions, the buckle, the strap run and the open side mirror", "blossoms are 5-fold radial: mirror only flips petal twist (keep one blossom mesh and mirror the instance)",
                      "the insole emblem is symmetric about its long axis and lies on the insole midline: unchanged by the mirror", "the printed insole branch is asymmetric: mirror it with the insole"]},
 "camera": meas["camera"],
 "silhouettes": {v: {"outline_xy": sil[v]["outline_xy"], "bbox_xyxy": sil[v]["bbox_xyxy"], "area_px": sil[v]["area_px"],
                     "method": "background flood fill over low-gradient bright pixels + contact-shadow removal under the sole, 3-px closing; RDP 0.75 px", "accuracy": "1 px on the sides, 2-3 px along the sole where the contact shadow touches"} for v in "AB"},
 "traces": T,
 "landmarks": lm,
 "vertical_proportions": vert,
 "image_proportions": meas["image_proportions"],
 "element_sizes_A": meas["element_sizes_A"],
 "estimates_3d_units_of_toplift_to_toe": meas["estimates_3d_units_of_toplift_to_toe"],
 "materials_sampled": meas["materials"],
 "leather_grain": meas["leather_grain"],
 "registration": meas["registration"],
 "files": {k: "WorkFiles/SnowFlowerHeels/ref/" + k for k in sorted(os.listdir(OUT + "/ref"))},
 "overlap_order_back_to_front": [
     "0 insole + insole print; far-side lining",
     "1 sole edge, stiletto body, top-lift",
     "2 upper leather: counter (incl. crackle medallion), vamp (tone-on-tone floral emboss), far quarter",
     "3 silver line work on the leather: front branch band (also over the stiletto back), C-band, sickle lames, topline piping, vine frame and vine runs",
     "4 small silver details: crest spike (end of the front band), leaf spur, heel thorn, heel diamond, vine thorns, frame corner",
     "5 glossy toe cap (inside the frame, flush or slightly proud); counter + vamp blossoms and buds",
     "6 toe plate (apex spike, rear arm, keystone, far + near rails); strap far run (in front of the far lining)",
     "7 strap near run (in front of the far run at the fold); toe blossom (over spike base / arm / keystone)",
     "8 buckle hex frame, side diamonds, strap stud",
     "9 buckle blossom (topmost); the strap root on the visible side passes UNDER the crest-spike/front-band junction"],
 "not_shown": [
     "outside of the far (closed) side = wearer's left / inner side if right shoe: only lining + top edge visible -> plain black leather, same collar line and binding, no ornament, no opening",
     "outsole / sole underside / waist underside / top-lift face -> plain black sole with the same thin edge",
     "far-side strap attachment, strap free tail and holes -> decorative buckle, strap enters it as shown, no tail",
     "heel back straight-on and the stiletto far face -> silver band on the back as seen, far face plain black",
     "toe box interior and forefoot insole -> printed branch ends under the vamp",
     "whether the C-band / lames wrap onto the far side -> stop them at the back centre line",
     "vamp vine on the inner vamp -> do not add one",
     "physical heel height and shoe length -> estimated only (estimates_3d_units_of_toplift_to_toe)"],
 "view_drift_A_vs_B": {
     "vamp_inside_vine_frame": "A: big blossom d68 + 7 buds; B: plain embossed leather, 1 bud, V-notch thorn on the upper arc -> follow A",
     "counter_ornament": "A: crest spike + 2 sickle lames + C-band + medallion + counter blossom; B: crest spike + stacked hooked (claw-like) lames -> A layout, B for the hook profile",
     "same_in_both": "heel, strap, buckle, stud, toe plate, toe cap, piping, insole emblem"},
 "open_points": [
     "tall back: counter + crest rise ~70-110 mm above her ankle joint, strap ~30-60 mm above it -> conflicts with 'nothing above the ankle except the strap' skinning; needs calf influence or a design change (user call)",
     "opening side: recommended outer (right shoe as shown, left mirrored); inner is possible",
     "heel height: image ~82 mm (73-91) at her size; pose chat's 90 mm is inside the range; confirm with a silhouette-IoU fit in the reference camera"],
 "example_scale_on_her": {"foot_mm": 242.4, "assumed_shoe_len_mm": 275, "assumed_L_toplift_to_toe_mm": 257, "viewA_px_per_mm_faceon": 3.8,
                          "heel_seat_height_mm": [73, 82, 91], "toplift_mm": {"height": 6.3, "footprint": [8, 8]}, "strap_height_above_ground_mm": [185, 215], "collar_top_above_ground_mm": [245, 270]},
}
json.dump(spec, open(OUT + "/heels_spec.json", "w"), indent=1)
print("wrote", OUT + "/heels_spec.json", os.path.getsize(OUT + "/heels_spec.json"))
for v in lm:
    for k, d in lm[v].items(): print(v, "%-28s" % k, d["along_across_over_len"], d["height_above_ground_px"], d["height_over_len"])
print(json.dumps(vert, indent=1))
