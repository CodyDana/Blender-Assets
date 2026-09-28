"""Stage 26: assemble reference_spec.json (machine twin of References/Fan/REFERENCE_SPEC.md) from the stage outputs fm_s*.json."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json

J = lambda n: json.load(open(os.path.join(OUT, n)))
S00, S04, S06, S10, S11, S13, S20, S21, S22, S23, S24 = (J(f) for f in (
    "fm_s00_load.json", "fm_s04_arcfit.json", "fm_s06_angprof.json", "fm_s10_spacingfit.json", "fm_s11_ends.json",
    "fm_s13_lobe.json", "fm_s20_scallop.json", "fm_s21_tassel.json", "fm_s22_colour.json", "fm_s23_camfit.json",
    "fm_s24_pleatcontrast.json"))
L2, L1 = 343.0, 396.0


def row(value, tol, status, how, unit=""):
    if tol == "":
        tol = ("DESIGNED: free within +-25 % unless it breaks a MEASURED row" if status.startswith("DESIGNED")
               else "qualitative: must read the same in a side-by-side render")
    return dict(value=value, tolerance=tol, status=status, unit=unit, how=how)


BG = float(srgb2lin(0.9647))
SH = 0.8


def albedo(mean_lin, bg=BG):
    lin = np.array(mean_lin) / (bg * SH)
    s = lin2srgb(lin)
    hx = "#" + "".join(f"{int(round(float(v) * 255)):02X}" for v in s)
    return dict(lin_rgb=[round(float(v), 4) for v in lin], lum_lin=round(float(lin @ LUMW), 4),
                srgb=[round(float(v), 3) for v in s], hex=hx, chroma_rgb=[round(float(v), 3) for v in lin / lin.sum()])


c2, c1 = S22["2"], S22["1"]
alb = {k: albedo(c2[k]['mean_lin']) for k in ('leaf', 'ribs_bare', 'right_guard_face')}
alb['tassel'] = albedo(S21['interior_colour']['mean_lin'])
alb1 = {k: albedo(c1[k]['mean_lin'], 1.0) for k in ('leaf', 'ribs_bare', 'right_guard_face')}
cam = S23["3.0"]

spec = {
 "meta": {
  "references": {
   "fan2 (PRIMARY)": dict(path="References/Fan/fan2.png", sha256=S00["2"]["sha256"], size_px=S00["2"]["size"],
                          backdrop="uniform stored 0.9647 (246/255) grey; soft composited elliptical ground shadow under the fan"),
   "fan1 (cross-check)": dict(path="References/Fan/fan1.png", sha256=S00["1"]["sha256"], size_px=S00["1"]["size"],
                              backdrop="pure white 1.0, no shadow")},
  "units": "L = radius from the pivot (rivet axis) to the leaf's outer edge = pivot-to-guard-tip (flush). fan2 L = 343 px at the rivet's depth; fan1 L = 396 px. Image angle phi (deg) is measured about the rivet image, y up, 0 = image right, counter-clockwise.",
  "designed_scale": "L = 190 mm, so the full stick incl. butt = 1.106 L = 210 mm (the common 21 cm silk fan) and the open width 2 L sin(81.6 deg) = 376 mm. DESIGNED.",
  "status_labels": "MEASURED (read off the pixels), INFERRED (geometric or physical consequence of measured rows), DESIGNED (proposal for what neither photo shows)",
  "instrument": "Blender 5.2 headless Python + NumPy 2; scripts fm_m00..fm_m26 in this folder, stage outputs fm_s*.json, helpers fm_lib.py",
  "design_masked": "Painted design (fan2: willow strokes, water swirls, red seal; fan1: sakura, cats, seal) and rib piercing are NOT part of this job. Every statistic excludes design pixels (bright or saturated, dilated 2 px). fan2 design covers %.1f %% of the leaf; fan1 %.1f %%." % (100 * c2['design_coverage_leaf'], 100 * c1['design_coverage_leaf']),
  "debug_dir": "WorkFiles/fan/reference_metrology/debug (DEBUG, NEVER SHIP); labelled layouts DEBUG_NEVER_SHIP_fan2_layout_LABELLED.png and DEBUG_NEVER_SHIP_fan1_layout_LABELLED.png",
  "build_input_policy": "The build must never read, sample, project or trace the reference pixels or the debug images; this spec is numbers and words."
 },
 "camera_fan2": {
  "projection": row("perspective, fan plane tilted top-away", "a plane parallel to the sensor fails: circle about the rivet rms 4.52 px vs 1.00 px", "MEASURED",
                    "the outer leaf edge r(phi) about the rivet falls from 342 px at the ends to 325 px at the top (5 %%) while the rib pitch stays uniform (thirds %s deg): a plane tilted about its horizontal axis through the rivet, top away (fm_m04, fm_m10, fm_m23)" % S10['2_ribmin']['spacing_by_thirds']),
  "distance_to_rivet_L": row(3.0, [1.8, 5.0], "MEASURED (weak)", "ladder fit fm_m23: rms 0.96 (1.8 L), 1.00 (3.0 L), 1.10 (5 L), 1.34 (20 L) px, of which 0.82 px is the pleat scallop; 3.0 L chosen (46 mm lens)"),
  "tilt_alpha_deg": row(cam['alpha_deg'], [9.2, 13.2], "MEASURED", "fan plane rotated about the horizontal axis through the rivet, TOP AWAY from the camera; tied to the distance (9.2 at 1.8 L, 13.2 at 5 L)"),
  "focal": row(dict(f_px=cam['f_px'], f_mm_on_36mm_sensor_800px=cam['f_mm_on_36mm_800px'], hfov_deg=cam['hfov_deg']), "f_px = 344 x distance(L)", "MEASURED",
               "fitted image scale s = %.1f px per L at the rivet depth" % cam['s_px_per_L']),
  "principal_point_px": row([400, 400], "assumed", "INFERRED", "image centre, lens shift 0; sensor upright (optical axis level)"),
  "rivet_image_px": row([398.2, 547.0], 1.5, "MEASURED", "centre of the metal ring (debug/g2_rivet_x12.png); highlight centroid (397.93, 546.07)"),
  "camera_position_rel_rivet_L": row([0.0060, -3.0, 0.4246], "scales with the distance", "INFERRED",
                                     "X right, Y toward the fan (camera on -Y), Z up; camera looks along +Y and is level; the rivet sits 0.4246 L below and 0.0060 L left of the optical axis"),
  "roll_deg": row(1.0, 1.5, "MEASURED", "fan bisector at image angle 91.0 deg (guard axes 9.4 and 172.6): the fan is turned 1.0 deg counter-clockwise as seen"),
  "extent_px": row(dict(left_corner_x=58, right_corner_x=736, leaf_top_y=221, lobe_bottom_y=584, tassel_tip=[199.1, 629.9]), 2, "MEASURED", "silhouette"),
 },
 "camera_fan1": {
  "view": row("front-on", "tilt <= 4 deg", "MEASURED", "a circle about the rivet fits the outer edge with rms %.2f px (%.2f px of it scallop); a free-centre circle lands only 2.2 px away" % (S04['1']['circle_at_rivet']['rms'], S20['1']['rms_px'])),
  "rivet_image_px": row([391.6, 600.3], 1.5, "MEASURED", "silver dome centre (debug/g1_rivet_x12.png)"),
  "L_px": row(396, 3, "MEASURED", "circle about the rivet R = %.1f" % S04['1']['circle_at_rivet']['R']),
  "roll_deg": row(-1.7, 1.5, "MEASURED", "bisector at 88.3 deg (guard axes 16.85 and 159.8)"),
 },
 "opening": {
  "fan2_guard_axis_to_guard_axis_deg": row(163.2, 2.0, "MEASURED", "front guard axis 9.4 (outer edge line 8.88 deg + half width), rear guard axis 172.6 (silhouette 173.95 at 0.93 L less half width); tilt correction < 0.4 deg"),
  "fan2_leaf_corner_to_corner_deg": row(165.5, 1.0, "MEASURED", "silhouette at 0.99 L: 8.25 -> 173.8"),
  "fan1_guard_axis_to_guard_axis_deg": row(142.9, 2.0, "MEASURED", "16.85 -> 159.8 (silhouette 15.6 / 160.6 at 0.9 L, +- guard half width)"),
  "note": "fan1 is opened ~20 deg less than fan2; the reference open pose follows fan2 (163 deg)."
 },
 "sticks": {
  "fan2_total": row(26, "exact (confidence high, ~90 %; otherwise 25 or 27)", "MEASURED",
                    "25 equal gaps between the guard axes, four ways: 25 bare-zone rib boundaries (incl. the front guard's inner edge) at 11.49 + 6.658 n, whose n = 25 prediction (177.9) meets the rear guard's outer silhouette (177.3 at r = 140 px); 25 lit pleat faces; 24 edge-scallop peaks + 1 at the range end; pitch x count = opening"),
  "fan2_breakdown": row("2 guards (outer, thicker) + 24 inner ribs", "exact", "MEASURED", "front guard = image right, lies over the leaf; rear guard = image left, behind the leaf, visible only in the bare zone"),
  "fan2_pitch_deg": row(6.528, 0.1, "MEASURED", "163.2 / 25; single methods: rib boundaries %.3f, leaf lit faces %.3f, scallop %.3f, bare-zone fft %.3f" % (
      S10['2_ribmin']['linear']['step'], S10['2_leafmax']['linear']['step'], S20['2']['period_deg'], S06['2']['rib']['period_fft'])),
  "fan1_total": row(30, "exact (confidence medium-high; otherwise 29 or 31)", "MEASURED", "29 gaps at 4.93 deg (boundaries 21.15 + 4.855 n; scallop 4.845; leaf 4.94) over 142.9 deg; overlay DEBUG_NEVER_SHIP_fan1_layout_LABELLED.png"),
  "fan1_breakdown": row("2 guards + 28 inner ribs", "exact", "MEASURED", ""),
  "stacking_order": row("front guard (image right) on top; each stick to its left lies behind the previous one; the leaf lies over all inner ribs and under the front guard; the rear guard is behind everything", "", "INFERRED",
                        "visible edges of the bare ribs; the front guard overlaps the leaf; the rear guard is hidden in the leaf zone"),
 },
 "inner_rib": {
  "bare_length_from_pivot_L": row(0.431, 0.012, "MEASURED", "leaf inner edge at 148 +- 4 px (debug/dbg_polar2_rgrid_*.png); fan1 0.462 L (183 px, radial gradient fm_m15)"),
  "butt_below_pivot_L": row(0.106, 0.005, "MEASURED", "lobe of stacked rounded butts: radius 35-37.5 px about the rivet over phi 190..345 (fm_m13); fan1 0.08-0.09 L"),
  "total_length_L": row(1.106, 0.01, "INFERRED", "pivot to leaf edge + butt (inner ribs run on behind the leaf; their tips are hidden)"),
  "width_at_leaf_inner_edge_L": row(0.041, 0.005, "MEASURED", "pitch arc at 148 px = 16.9 px, less the 2-3 px dark boundary line; the ribs almost touch there (fan1 0.035 L)"),
  "width_near_pivot_L": row(0.030, 0.006, "DESIGNED", "ribs overlap near the rivet, so this is not measurable; straight edges, linear taper 0.041 -> 0.030"),
  "shoulder": row("rounded shoulders at 0.415-0.431 L, just under the leaf edge", 0.01, "MEASURED", "rounded rib tops at r ~146 px (debug/g2_ribs_top_x6.png) and an un-pierced band at r 142-150 px"),
  "leaf_section": row("hidden: continues behind the leaf as a narrow slip to 0.96 L, width 0.012 L, thickness 0.002 L, rounded tip", "", "DESIGNED", "the back is not visible in either photo"),
  "thickness_bare_L": row(0.0045, "", "DESIGNED", "0.85 mm at L = 190; closed stack at the pivot 24 x 0.0045 + 2 x 0.010 = 0.128 L (24 mm)"),
  "butt_shape": row("rounded (semicircular) end, butt width 0.030 L; the stacked butts form the D-shaped lobe of radius 0.106 L", "", "INFERRED", "the lobe outline is a near-circle about the rivet (35-37.5 px) that falls off only at its ends"),
  "piercing": row("NONE - keep ribs solid", "", "DESIGNED", "fan2's bare ribs carry openwork piercing between 0.13 and 0.37 L and fan1's carry small flower cut-outs; both are surface design for a later stage and are excluded here"),
 },
 "guard": {
  "length_L": row(1.106, 0.01, "MEASURED", "tip flush with the leaf outer edge (+-0.01 L), plus the butt"),
  "width_profile_L": row({"0.17-0.29 L": 0.039, "0.47-0.58 L": 0.034, "0.76 L": 0.041, "0.93 L": 0.047}, 0.006, "MEASURED",
                         "front guard: perpendicular profiles from the outer silhouette to the bright inner-edge highlight (fm_m12); fan1 is similar: 0.028 -> 0.038 -> 0.04-0.055"),
  "grip_section": row("no separate grip shape: the guard runs at about the same width down to the rivet; its outer edge flares ~0.006 L proud of the straight line below 0.45 L", "", "MEASURED", "silhouette edge table fm_s11"),
  "tip": row("cut on the leaf arc, square to the axis, corners softened (fan1: rounded end)", "", "MEASURED", "debug/g2_rightguard_x5.png, debug/g1_rightend_x4.png"),
  "edges": row("rounded / chamfered long edges: a continuous highlight runs along the inner edge", "", "MEASURED", "debug/g2_rightguard_mid_x6.png"),
  "thickness_L": row(0.010, "", "DESIGNED", "about 2 x an inner rib; 1.9 mm at L = 190"),
  "rear_guard": row("identical to the front guard, mirrored; hidden behind the leaf in the leaf zone", "", "DESIGNED", ""),
 },
 "pivot_rivet": {
  "position": row("at the rib convergence; rivet image (398.2, 547.0)", "0.015 L", "MEASURED", "rib boundary lines converge within 5 px of the ring centre (fan1 rms 0.97 px, fan2 3.6 px)"),
  "fan2_head_diameter_L": row(0.035, 0.005, "MEASURED", "metal ring 12 px across with a dark 6 px (0.017 L) centre: a hollow, eyelet-style head"),
  "fan1_head_diameter_L": row(0.022, 0.004, "MEASURED", "solid silver dome 8.5-9 px"),
  "metal_colour": row(dict(bright_pixels_mean_lin=c2['rivet_metal_bright']['mean_lin'], hue_deg=c2['rivet_metal_bright']['hue_deg']), "", "MEASURED", "neutral, faintly warm silver (nickel); polished metal"),
  "back_end": row("matching eyelet head on the back; each head proud of its guard by 0.006 L", "", "DESIGNED", "not visible"),
 },
 "leaf": {
  "inner_radius_L": row(0.431, 0.012, "MEASURED", "fan1 0.462"),
  "outer_radius_L": row(1.0, 0.01, "MEASURED", "flush with the guard tips"),
  "pleats": row(dict(pleats=25, faces=50, rib_folds=24, mid_folds=25, end_faces="glued to the guards"), "exact, follows the stick count", "MEASURED", "one pleat (a lit + an unlit face) per rib gap"),
  "alternation": row("rib folds = valleys seen from the front (sharp dark creases); mid-gap folds = mountains (soft rounded ridges)", "", "INFERRED",
                     "the ribs are invisible on the front of the leaf in both photos, so they lie behind it and every rib fold is a front valley; the sharp lit->unlit creases coincide with the edge notches within 0.5 deg; key light from the top (face contrast is lowest at phi 65-90)"),
  "face_tilt_beta_deg": row(20, [13, 30], "INFERRED", "lit/unlit face luminance ratio %.1f (inner) .. %.1f (outer), up to 3.8 by angle; Lambert with a key 45-60 deg off the fan normal gives beta 18-30; the edge-silhouette ripple gives 10-20" % (
      S24['by_radius']['152-190'][0], S24['by_radius']['305-322'][0])),
  "pleat_depth": row("mountain-to-valley depth d(rho) = 0.0572 rho tan(beta): 0.021 L at the outer edge, 0.009 L at the inner edge (flat wedge faces, depth proportional to radius)", "0.013-0.033 L at the edge", "INFERRED",
                     "face contrast is nearly constant along the radius, so the faces are flat wedges"),
  "unfolded_leaf_angle_deg": row(173.6, [170, 178], "INFERRED", "50 faces x atan(tan(3.264 deg) / cos(20 deg))"),
  "face_shape": row("faces read slightly convex (soft silk); creases sharp at the valleys, softer at the mountains", "", "MEASURED", "gain crops"),
  "edge_scallop": row(dict(per_gap=1, peak_to_trough_L=round(S20['2']['p2p_px'] / L2, 4), notches_at="rib (valley) folds", bumps_at="mid-gap", shape="near-sinusoidal"), "+-0.003 L", "MEASURED",
                      "sub-pixel outer radius, detrended (fm_m20); fan1 %.4f L, sawtooth" % (S20['1']['p2p_px'] / L1)),
  "inner_edge": row("clean circular arc about the pivot, not scalloped, no hem band", "", "MEASURED", ""),
  "material": row("single-layer silk-like fabric with a soft sheen, ribs glued behind", "", "INFERRED", ""),
 },
 "tassel_fan2": {
  "attachment": row("the cord emerges from behind the lobe at its lower-left edge (0.110 L from the rivet, image direction 215 deg); threaded through the hollow rivet from behind", "", "MEASURED / INFERRED", "fm_m21"),
  "cord": row(dict(visible_length_L=0.079, rivet_to_knot_top_L=0.19, diameter_L=0.010), dict(length=0.01, diameter=0.003), "MEASURED", ""),
  "knot": row(dict(length_L=0.047, width_L=0.046, shape="round, bead-like decorative knot"), 0.006, "MEASURED", "width profile s = 28-44 px"),
  "neck_binding": row(dict(length_L=0.017, width_L=0.025), 0.005, "MEASURED", ""),
  "skirt": row(dict(length_L=0.373, width_top_L=0.029, width_at_0p06L_L=0.050, width_mid_L=0.063, width_end_L=0.083, end="ragged thread tips over ~0.015 L"), 0.008, "MEASURED", "fm_s21 width profile"),
  "overall": row(dict(knot_top_to_tip_L=0.437, rivet_to_tip_L=round(S21['far_tip_to_rivet_px'] / L2, 3)), 0.01, "MEASURED", ""),
  "how_it_hangs_in_photo": row("straight, lying out at image direction %.1f deg (20 deg below horizontal, to the left): NOT hanging under gravity (flat-lay / posed product shot)" % S21['axis_dir_deg_yup'], "2 deg", "MEASURED", ""),
  "in_engine": row("hangs under gravity from the pivot; for the fan2 comparison render pose it along -160 deg", "", "DESIGNED", ""),
  "fullness": row("round bundle of fine threads, ~0.07 L thick at mid length (laid flat, width = diameter)", "", "DESIGNED", "strands not resolvable"),
 },
 "colour_albedo": {
  "method": "albedo = observed linear / (backdrop 0.922 lin x mean shading 0.8), as in the black-hat spec: absolute level +-35 %, chroma solid. Design and rib holes masked; tassel mask eroded 2 px.",
  "leaf": row(alb['leaf'], "lum +-35 %, chroma +-0.01", "INFERRED", "observed lum %.4f (lit faces %.4f, unlit %.4f), hue %.0f deg, sat %.2f: a cool blue-grey black" % (
      c2['leaf']['lum_mean'], c2['leaf_light_faces']['lum_mean'], c2['leaf_dark_faces']['lum_mean'], c2['leaf']['hue_deg'], c2['leaf']['hls_sat'])),
  "ribs": row(alb['ribs_bare'], "lum +-35 %", "INFERRED", "bare ribs, holes excluded, observed lum %.4f, hue %.0f" % (c2['ribs_bare']['lum_mean'], c2['ribs_bare']['hue_deg'])),
  "guards": row(alb['right_guard_face'], "lum +-35 %", "INFERRED", "front guard face, observed lum %.4f; the same material as the ribs within error, so ribs and guards are one part" % c2['right_guard_face']['lum_mean']),
  "tassel": row(alb['tassel'], "lum +-50 %", "INFERRED", "interior, observed lum %.4f, chroma %s: the most saturated (bluest) black; it sits at the pack's black floor (0.0097, #191919)" % (
      S21['interior_colour']['lum_mean'], S21['interior_colour']['chroma'])),
  "rivet": row("polished silver metal, near-neutral (hue ~37 deg, sat 0.035)", "", "MEASURED", ""),
  "fan1_cross_check": row(alb1, "", "INFERRED", "fan1 leaf is a navy black (sat 0.30); its ribs are a lighter grey-black (albedo ~0.056) with sheen"),
 },
 "fan1_vs_fan2": [
  "sticks: fan1 30 (28 + 2) vs fan2 26 (24 + 2)",
  "opening: fan1 143 deg vs fan2 163 deg",
  "leaf inner radius: fan1 0.462 L vs fan2 0.431 L",
  "butt lobe: fan1 0.08-0.09 L vs fan2 0.106 L",
  "rivet: fan1 solid silver dome 0.022 L vs fan2 eyelet ring 0.035 L",
  "guard tip: fan1 rounded vs fan2 square-cut with softened corners",
  "rib colour: fan1 lighter grey-black with sheen (~0.056) vs fan2 black (~0.018)",
  "leaf hue: fan1 navy black (sat 0.30) vs fan2 blue-grey black (sat 0.12)",
  "edge scallop: fan1 sawtooth 0.0074 L vs fan2 sinusoid 0.0066 L",
  "camera: fan1 front-on vs fan2 tilted 11.5 deg top-away at ~3 L",
  "tassel: fan1 none vs fan2 cord + knot + skirt",
  "design (masked, not modelled): fan1 sakura/cats on 29 % of the leaf vs fan2 willow/swirls/seal on 12 %; both have pierced ribs"
 ],
 "unseen_designed": {
  "back": "the leaf back shows the 24 inner-rib slips glued along the valley folds up to 0.96 L; the rear guard lies over the leaf's back at the image-left end (mirror of the front); an eyelet rivet head on the back",
  "closed_state": "all 26 sticks share one axis (for the rig: close symmetrically onto the fan bisector); the leaf folds into 50 stacked faces between the guards, its top edge flush with the guard tips; closed width = guard width (0.047 L at the tip); stack thickness 0.128 L at the pivot, ~0.10 L in the leaf zone",
  "thicknesses": "inner rib 0.0045 L bare / 0.002 L in the leaf, guard 0.010 L, silk 0.0006 L",
  "tassel": "hangs under gravity; cord through the hollow rivet; the knot as a round bead-like knot"
 }
}
json.dump(spec, open(os.path.join(OUT, "reference_spec.json"), "w"), indent=1)
print("ALB", json.dumps(alb))
print("ALB1", json.dumps(alb1))
