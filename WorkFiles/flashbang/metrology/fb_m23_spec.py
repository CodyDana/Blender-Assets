"""Consolidate the flashbang reference metrology into WorkFiles/flashbang/flashbang_spec.json.
Run: blender -b --factory-startup --python fb_m23_spec.py
"""
import sys, json, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
W = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang"
E = json.load(open(DBG + "/fb_edges.json"))
OUTL = json.load(open(DBG + "/fb_outlines_auto.json"))
LEV = json.load(open(DBG + "/fb_lever_rows.json"))
COL = json.load(open(DBG + "/fb_colour.json"))
REG = json.load(open(W + "/ref/fb_registration.json"))
HAZ = json.load(open(DBG + "/fb_holeaz.json"))

Dpx = 175.31                    # body diameter at axis depth (mean of v2 174.91 / v3 175.71)
F, YH = 2600.0, 460.0           # camera estimate (focal px, horizon row) for the top row
Z = F / Dpx                     # camera distance to axis in D
YB = 716.8                      # v2 bottom contact (front centre)


def corr(y, r):
    """move an image row measured on a front surface at radius r (D) to the axis-depth scale"""
    return YH + (y - YH) * (Z - r) / Z


ybc = corr(YB, 0.468)


def H(y, r):
    return dict(y_ref_v2=y, H_raw_D=round((YB - y) / Dpx, 4), H_persp_corr_D=round((ybc - corr(y, r)) / Dpx, 4))


L = {
    'bottom_contact_front': H(716.8, 0.468),
    'foot_chamfer_top__cap_side_bottom': H(703.5, 0.548),
    'cap_side_top__top_chamfer_bottom_bright_edge': H(643.0, 0.548),
    'cap_top_chamfer_top__paint_end': H(632.0, 0.50),
    'hole_row_C_bottom': H(599.6, 0.50),
    'hole_row_C_centre': H(561.6, 0.50),
    'hole_row_C_top': H(523.5, 0.50),
    'ring_line_BC': H(501.5, 0.50),
    'hole_row_B_bottom': H(479.2, 0.50),
    'hole_row_B_centre': H(441.5, 0.50),
    'hole_row_B_top': H(403.7, 0.50),
    'ring_line_AB': H(383.5, 0.50),
    'hole_row_A_bottom': H(363.1, 0.50),
    'hole_row_A_centre': H(325.9, 0.50),
    'hole_row_A_top': H(288.6, 0.50),
    'sleeve_bottom_step': H(258.0, 0.533),
    'sleeve_top_full_diameter__top_chamfer_bottom': H(198.5, 0.533),
    'sleeve_top_chamfer_top': H(185.3, 0.47),
    'collar_disc_bottom': H(181.5, 0.387),
    'collar_disc_top__plinth_bottom': H(156.5, 0.387),
    'plinth_top__housing_box_bottom': H(149.0, 0.29),
    'lever_joggle_v4': H(140.0, 0.62),
    'pin_boss_centre_median': H(83.7, 0.35),
    'ring_top_v2_v4': H(77.0, 0.40),
    'housing_box_top_v2': H(59.0, 0.23),
    'top_cover_plate_top_v3': H(48.0, 0.23),
    'overall_top_hinge_knuckle_or_lever_bend': H(45.0, 0.10),
}

bw = {v: round(float(np.mean([E[v][k]['width'] for k in ('body_web_A_B', 'body_web_B_C', 'body_low')])), 2) for v in ['v1', 'v2', 'v3', 'v4']}
bc = {v: round(float(np.mean([E[v][k]['centre'] for k in ('body_web_A_B', 'body_web_B_C', 'body_low')])), 2) for v in ['v1', 'v2', 'v3', 'v4']}

spec = {
    'meta': dict(
        reference="C:/Users/Cody/Desktop/Blender_Projects/References/Flashbang/flashbang_reference.png",
        sha256="64d1f5606df30f70f9f5c6801d990ef10a08cde42a3deee1115e3fd68fa9994a", size_px=[1254, 1254],
        date="2026-09-27", role="reference metrology",
        coords="reference pixels, x right, y down, origin top-left of the 1254x1254 file",
        unit="D = body (perforated tube) outer diameter; H = height above the bottom contact line",
        scripts="WorkFiles/flashbang/metrology/fb_m*.py (Blender 5.2 headless + NumPy); debug images in metrology/debug"),
    'layout': dict(
        top_row_views_box_x0y0x1y1={'v1_front_ring_toward_viewer': [40, 30, 345, 725], 'v2_threequarter_a': [345, 30, 615, 725],
                                    'v3_threequarter_b': [615, 30, 950, 725], 'v4_lever_side': [950, 30, 1240, 725]},
        bottom_panels_box_x0y0x1y1=REG['panels_ref_px_box_x0y0x1y1'],
        background_srgb8_p50=COL['background_top_row']['p50_srgb8'],
        background_note="dark neutral grey studio sweep, slightly lighter toward the top-right, soft contact shadow under each object; bottom panels have a 1-2 px light frame"),
    'unit': dict(
        D_px_axis_depth=Dpx, per_view_body_width_px=bw, per_view_body_centre_x=bc,
        note=("v1/v4 read 2.0%/3.5% wider than v2/v3 with no matching height change: off-axis perspective widening of a cylinder, "
              "not a size change. 175.31 px (v2/v3) is the true D at the object depth.")),
    'camera_estimate_top_row': dict(
        focal_px=F, focal_px_range=[1750, 3500], focal_mm_fullframe_36mm=round(F / 1254 * 36, 1), focal_mm_range=[50, 100],
        horizon_row_y=YH, horizon_range=[430, 510], distance_to_axis_D=round(Z, 2),
        elevation=("camera roughly level with the lower ring line (H ~1.2 D): circles above it are seen from below (the sleeve step bows UP "
                   "4-5 px at the centre), the base-cap bottom is seen from above (bows DOWN 4-5 px)"),
        object_centres_x=[bc['v1'], bc['v2'], bc['v3'], bc['v4']], contact_row_y=[720.5, 716.8, 717.0, 717.0],
        evidence=("(a) width growth of the off-centre views, (b) sag of the ring lines / sleeve step / cap bottom, (c) the ring read face-on "
                  "in v1 is 3% taller than edge-on in v2-v4. All weak. Heights are given raw (orthographic reading) and perspective-corrected with this camera; they differ by up to 3.5% at mid-body (row A 2.23 vs 2.16 D). Use the corrected set and confirm by overlaying a render from this camera on the registered crops.")),
    'heights_from_bottom': L,
    'diameters_D': dict(
        body=dict(D=1.0, px=Dpx, note="constant from the sleeve step to the cap: v2 174.95/174.76/175.03 px at three heights, v3 175.72/175.42/176.00"),
        sleeve_top_band=dict(D=round(186.92 / Dpx, 4), px_v2=186.74, px_v3=187.10,
                             note="solid band above hole row A, proud of the body by 0.033 D radially; small chamfers top and bottom"),
        sleeve_top_chamfer_top_edge=dict(D=0.94, note="approx; chamfer ~0.063 D radial x 0.075 D tall, paint worn to bare steel on it"),
        base_cap_side=dict(D=round(191.9 / Dpx, 4), px_v2=189.88, px_v3=193.89, sides=12,
                           note=("reads as a 12-flat polygon: faint vertical facet lines ~30 deg apart in v2 (x 420, 470, 507, 548) and "
                                 "polygonal kinks on the top chamfer edge; flats with soft corners")),
        foot_bottom_edge=dict(D=0.94, note="lower chamfer from the cap side in to the foot (v2); rough +-0.03"),
        collar_disc=dict(D=round(135.46 / Dpx, 4), px_v2=135.46, height_D=round(25 / Dpx, 4), note="round steel disc, chamfered top edge"),
        neck_under_collar=dict(D=0.74, height_D=0.02, note="thin dark gap between the collar disc and the sleeve chamfer"),
        plinth_disc_under_housing=dict(D=round(103 / Dpx, 3), height_D=round(7.5 / Dpx, 3), note="round (p1 shows stacked round discs)"),
        inner_brass_tube=dict(D=0.76, range=[0.74, 0.78], note="its limb is visible inside the side holes: v2 r=64.5 px, v3 r=67.9 px"),
        outer_wall_thickness=dict(D=0.04, range=[0.03, 0.05], note="cut face of each hole visible (lit, 5-9 px) on the side holes")),
    'holes': dict(
        rows=3, rows_aligned=True, row_to_row_angular_offset_deg=0,
        row_centres_H_raw_D=[L['hole_row_A_centre']['H_raw_D'], L['hole_row_B_centre']['H_raw_D'], L['hole_row_C_centre']['H_raw_D']],
        row_pitch_px=[115.6, 120.1], row_pitch_D=[round(115.6 / Dpx, 3), round(120.1 / Dpx, 3)],
        outline_measured_v2_front=dict(
            width_chord_px=64.8, height_px=75.4, width_arc_D=0.349, height_D=0.41, w_over_h=0.86,
            note=("paint-edge outline (includes the thin bare-steel rim). Holes are slightly TALL ovals, not circles: w/h 0.85-0.88 in v2, "
                  "v3 and the p4 close-up")),
        angular_width_deg=40, angular_width_note="41-42 deg raw, 40 deg after the front-surface perspective correction",
        per_view_hole_azimuths=dict(data=HAZ, format="[x_left, x_right, az_left_deg, az_right_deg] per visible hole, 0 = toward camera, + = right; -90/90 = clipped at the limb"),
        per_view_web_widths_deg=dict(v1=[57], v2=[19, 20], v3=[22, 25], v4=[46]),
        count_per_row=("NOT self-consistent across views. v2 and v3 show a 60-63 deg pitch (narrow ~20 deg webs); v1 and v4 each show "
                       "one ~50 deg web (hole pitch 87-97 deg). Hole centres per view (deg): v1 -61, 36.5 | v2 -61, 1.4, 63 | "
                       "v3 -52, 11, 77 | v4 -67, 20, 87."),
        candidate_patterns=[
            dict(name="5 holes, two wide webs", centres_deg=[0, 60, 120, 180, 270], webs_deg=[20, 20, 20, 50, 50],
                 fits="every view's local spacing (v2/v3 60-deg pairs, v1 97-deg gap, v4 87 then 67)", recommended=True),
            dict(name="6 holes even", centres_deg=[0, 60, 120, 180, 240, 300], webs_deg=[20] * 6,
                 fits="v2, v3 and p2 only; v1 and v4 would show an extra front hole where the reference shows paint"),
            dict(name="5 holes even", centres_deg=[0, 72, 144, 216, 288], webs_deg=[32] * 5,
                 fits="the average spacing only; off by 10-25 deg in every view")],
        rim="every hole edge has a thin bare-steel rim (paint chipped); the cut wall is visible on the side holes",
        inner_seam=dict(count=3, where="one circumferential seam line on the inner brass tube at each hole-row centre height (0-3 px above the centre)",
                        width_D=0.006)),
    'ring_lines': dict(
        count=2, positions=["midway between rows A/B", "midway between rows B/C"],
        type="thin engraved groove with a light upper lip: 2-3 px dark line (0.012-0.017 D); paint worn along it",
        H_raw_D=[L['ring_line_AB']['H_raw_D'], L['ring_line_BC']['H_raw_D']],
        plus="the sleeve-bottom step (H ~2.62 D) reads as a third, stronger line"),
    'fuze_head': dict(
        housing_box=dict(plan="square", side_D=0.48, side_range_D=[0.46, 0.52], height_D=round(90 / Dpx, 3),
                         note="v2 face 82 px (0.46 D after perspective); v3 shows two faces 57+70 px -> side 90 px (0.52 D) at ~39 deg yaw"),
        top_cover_plate=dict(thickness_D=0.1, overhang_arm_D=[0.07, 0.25],
                             note=("plate over the box top; on the side away from the pin it extends as an arm ending in a small curl with "
                                   "a cross pin (v1 x75-118, v3 x679-692, v4 x1013-1035); overhang length differs per view")),
        hinge_knuckle=dict(diameter_D=round(24 / Dpx, 3), length_D=round(58 / Dpx, 3), axis="horizontal, parallel to the lever face",
                           where="top edge of the lever-side face; the lever top curls round it (v2: x 442-500, y 45-69)"),
        pin_boss=dict(diameter_D=0.095, length_D=0.17, axis="horizontal, 90 deg from the lever normal (see pin_vs_lever)",
                      where="upper corner of the housing beside the knuckle, centre at H ~3.61 D raw"),
        small_round_boss_on_face=dict(diameter_D=0.057,
                                      where="upper corner of a housing face near the top plate (v1 x185 y63, v3 x802 y68); v3 also shows a spiral/slotted screw head of similar size at x760 y67"),
        pin_vs_lever=("in v1, v2 and v4 the pin axis is 90 deg from the lever normal (v2: lever at the back, pin points right; v4: lever "
                      "front-right, pin front-left; v1: lever right, pin toward the viewer). v3 does not agree.")),
    'pull_ring': dict(
        outer_diameter_D=1.05, outer_range_D=[1.0, 1.09],
        px=dict(v1_face_on_w_h=[171.3, 191.7], v2_h=186, v3_h=183, v4_h=176),
        wire=dict(p1_closeup="single round wire, ~0.04 D", v1="reads as TWO parallel strands (split-ring style), each ~0.022 D, pair ~0.06 D"),
        hangs_from="the pin eye at H ~3.6 D; ring top ~H 3.65 D, bottom ~H 2.6-2.7 D (about the sleeve-bottom step)",
        orientation_per_view=dict(v1="plane ~26 deg from face-on", v2="nearly edge-on (~74 deg), right side", v3="~66 deg, right side",
                                  v4="~72 deg, left side")),
    'lever': dict(
        length_total_D=[2.9, 3.1], top="curls over the hinge knuckle at the housing top (H ~3.83 raw)",
        upper_segment=dict(H_raw_D=[3.29, 3.83], width_D_top=0.41, width_D_bottom=0.29,
                           note="v4: hugs the housing face, tapers from 72 px to 50 px (left edge slanted, right edge vertical)"),
        joggle=dict(H_raw_D=3.29, note="v4 y 138-143: the lower segment steps outward (rounded top corner) to clear the collar and sleeve"),
        lower_segment=dict(width_D=0.26, face_px_v4=41, edge_or_flange_px=[8, 15], thickness_or_flange_D=[0.05, 0.09],
                           standoff_from_body_surface_D=0.11,
                           note=("flat face; the visible side band (8 px in v4, 15 px in v1, 10 px in v3) is either a thick plate (~0.05 D) "
                                 "or a shallow side flange; not resolvable")),
        tip=dict(H_raw_D_per_view=dict(v1=round((720.5 - 584) / Dpx, 3), v3=round((717 - 544) / Dpx, 3), v4=round((717 - 557) / Dpx, 3)),
                 recommended_H_D=0.91,
                 shape=("squared end with rounded corners r~0.05 D; in v1 the last ~0.1 D bends inward toward the body (the bent tip); "
                        "v3 shows only a rounded corner")),
        per_view_rows_ref_px=dict(
            v1_y_ge_295=[r for r in LEV['v1_rows_y_xl_xr'] if r[0] >= 295],
            v3_y_ge_265=[r for r in LEV['v3_rows_y_xl_xr'] if r[0] >= 265],
            format="[y, x_left, x_right]",
            note="auto from the silhouette; above those rows the ring overlaps; the v3 left edge is the body limb (lever partly behind the body)"),
        v4_outline_ref_px=[[1105, 45], [1166, 44], [1173.7, 50], [1173.7, 137], [1178, 139], [1181.3, 143], [1181.3, 550], [1175, 557],
                           [1147, 557], [1140.3, 550], [1132, 548], [1132, 145], [1128.7, 140], [1123, 140], [1099, 60]]),
    'base_cap': dict(
        side_D=round(191.9 / Dpx, 4), height_total_D=round((YB - 632) / Dpx, 3),
        top_chamfer_H_D=[round((YB - 643) / Dpx, 3), round((YB - 632) / Dpx, 3)],
        side_H_D=[round((YB - 703.5) / Dpx, 3), round((YB - 643) / Dpx, 3)], foot_H_D=[0, round((YB - 703.5) / Dpx, 3)], facets=12,
        end_face=dict(
            structure="flat outer annulus -> raised rim lip at the outer edge -> narrow recessed groove -> central disc (about flush with the rim)",
            rim_lip_radial_D=0.045, groove_radial_D=0.03, central_disc_D=0.8, notch_count=5, notch_pitch_deg=72, notch_width_D=0.05,
            notch_positions_p3_ref_px=dict(a=[870, 960], b=[778, 995], c=[731, 1124], e=[803, 1157], f=[918, 1075]),
            notch_angles_unprojected_deg=[-10, -72, -156, 147, 70],
            note=("notches are rectangular cuts through the rim lip, each with a matching step on the disc edge; the side views v1 and v3 "
                  "instead show one wide recess in the foot (58-68 deg of arc) - inconsistent with the close-up"))),
    'colours': COL,
    'outlines': dict(
        silhouettes_ref_px={v: OUTL[v] for v in OUTL},
        note=("Moore trace of the cleaned silhouette, Douglas-Peucker 0.8 px; ring interiors are not part of the outer outline; below y 690 "
              "clipped to the cap width to drop the floor shadow")),
    'registration': REG,
}
json.dump(spec, open(W + "/flashbang_spec.json", "w"), indent=1)
for k, v in L.items():
    print("LM", k, v)
print("Zc", Z, "ybc", ybc)
