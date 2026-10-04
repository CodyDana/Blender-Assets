"""Writes WorkFiles/katana/katana_spec.json: every dimension of the basic katana + saya.

Plain Python (no numpy). Run: py -3 -B WorkFiles/katana/study/make_spec.py
All lengths in millimetres. The design sheet (make_design_sheet.py) reads the JSON this writes,
so the sheet and the spec cannot drift apart. Change a number HERE, rerun both.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "katana_spec.json"))

# ---------------------------------------------------------------- primary design numbers
NAGASA = 705.0          # straight chord, mune-machi -> tip
SORI = 17.0             # max distance chord -> mune
MOTOHABA = 31.0         # width at the machi
SAKIHABA = 22.0         # width at the yokote
MOTOKASANE = 7.0        # thickness at the machi (at the shinogi)
SAKIKASANE = 5.0        # thickness at the yokote
KISSAKI_LEN = 38.0      # along the mune arc, yokote -> tip (chu-kissaki, ~1.7 x sakihaba)
Z_MACHI = 58.0          # machi plane (= blade-side seppa face) above the Grip socket
MUNE_X_AT_MACHI = 15.5  # blade centred on the tsuka axis at the machi

R = NAGASA ** 2 / (8.0 * SORI) + SORI / 2.0           # mune arc radius
PHI_TIP = 2.0 * math.asin(NAGASA / (2.0 * R))         # arc angle machi -> tip
S_TIP = R * PHI_TIP                                   # mune arc length machi -> tip
TIP_X = MUNE_X_AT_MACHI + R * (1.0 - math.cos(PHI_TIP))
TIP_Z = Z_MACHI + R * math.sin(PHI_TIP)
S_YOKOTE = S_TIP - KISSAKI_LEN
CENTRE = (MUNE_X_AT_MACHI + R, Z_MACHI)               # arc centre (x, z), on the mune (+X) side

def centre_line(s_arc):
    a = s_arc / R
    if s_arc <= S_TIP - KISSAKI_LEN:
        w = MOTOHABA + (SAKIHABA - MOTOHABA) * s_arc / (S_TIP - KISSAKI_LEN)
    else:
        q = (s_arc - (S_TIP - KISSAKI_LEN)) / KISSAKI_LEN
        w = SAKIHABA * max(0.0, 1 - q ** 1.8) ** 0.7
    rho = R + w / 2.0
    return CENTRE[0] - rho * math.cos(a), CENTRE[1] + rho * math.sin(a)


MID_X, MID_Z = centre_line(S_TIP / 2.0)
TE_X, TE_Z = centre_line(S_TIP - 15.0)

# tsuka / ito
Z_FUCHI_TOP = 50.0
Z_FUCHI_BOT = 37.0
Z_KASHIRA_TOP = -204.0
Z_KASHIRA_END = -215.0
ITO_LEN = Z_FUCHI_BOT - Z_KASHIRA_TOP                 # 241
N_CROSS = 9
PITCH = ITO_LEN / N_CROSS                             # 26.78
omote_cross = [round(Z_FUCHI_BOT - PITCH * (0.25 + k), 2) for k in range(N_CROSS)]
ura_cross = [round(Z_FUCHI_BOT - PITCH * (0.75 + k), 2) for k in range(N_CROSS)]

# saya / seat
SEAT_GAP = 0.3
S_MOUTH = SEAT_GAP                                    # mune-arc station of the koiguchi face
CAVITY_TIP_CLEAR = 10.0
KOJIRI_FLOOR = 6.0
S_CAV_END = S_TIP + CAVITY_TIP_CLEAR
S_SAYA_END = S_CAV_END + KOJIRI_FLOOR
KURIKATA_FROM_MOUTH = 80.0
Z_BELT = Z_MACHI + SEAT_GAP + KURIKATA_FROM_MOUTH     # saya pivot, sword frame


def r(v, n=3):
    return round(v, n)


spec = {
    "meta": {
        "name": "Basic katana + saya (the user's own design)",
        "version": "1.0",
        "date": "2026-10-03",
        "units": "millimetres (Blender builds in metres: divide by 1000; Unreal cm: divide by 10)",
        "authority": "This file + KATANA_DESIGN_SHEET.png are the reference. The builds read numbers from here.",
        "ip": "Generic historical form (shinogi-zukuri uchigatana in plain koshirae). No named blade, smith, school, brand, film or game design is copied. Menuki form is an abstract lozenge of our own.",
    },
    "frame_sword": {
        "origin": "Grip socket: primary (right) hand centre on the tsuka axis, 37 mm below the fuchi's lower edge",
        "+Z": "along the tsuka toward the blade (the blade curves away from +Z toward +X)",
        "+X": "mune (spine) side; the tip sweeps toward +X; the cutting edge faces -X",
        "-Y": "omote (the side seen with the handle left and the edge up); omote menuki, kurikata side of the saya",
        "tsuka_axis": "the Z axis is the tsuka's long axis and the blade's tangent at the machi",
    },
    "blade": {
        "type": "shinogi-zukuri, iori-mune, chu-kissaki, torii-zori (centred curve), no hi (no groove)",
        "nagasa_chord": NAGASA,
        "sori": SORI,
        "sori_shape": "the mune is a CIRCULAR ARC tangent to the tsuka axis at the mune-machi; the draw from the saya is a rotation about its centre",
        "mune_arc_radius": r(R, 2),
        "mune_arc_centre_xz": [r(CENTRE[0], 2), r(CENTRE[1], 2)],
        "arc_angle_deg": r(math.degrees(PHI_TIP), 4),
        "mune_arc_length_machi_to_tip": r(S_TIP, 2),
        "mune_machi_xz": [MUNE_X_AT_MACHI, Z_MACHI],
        "ha_machi_xz": [MUNE_X_AT_MACHI - MOTOHABA, Z_MACHI],
        "tip_xz": [r(TIP_X, 2), r(TIP_Z, 2)],
        "tip_tangent_deg_from_Z": r(math.degrees(PHI_TIP), 3),
        "motohaba": MOTOHABA,
        "sakihaba_at_yokote": SAKIHABA,
        "width_rule": "linear in mune arc length from the machi (31.0) to the yokote (22.0); measured along the section normal (radial from the arc centre)",
        "motokasane": MOTOKASANE,
        "sakikasane_at_yokote": SAKIKASANE,
        "thickness_rule": "linear in arc length machi -> yokote; inside the kissaki linear to tip_thickness",
        "tip_thickness": 0.8,
        "edge_thickness": {"machi": 0.5, "tip": 0.4, "note": "game minimum; reads as sharp at any distance"},
        "shinogi_ji_ratio": 0.27,
        "shinogi_ji_note": "the shinogi ridge sits 0.27 x local width from the mune peak: 8.37 mm at the machi, 5.94 mm at the yokote",
        "mune_shoulder_thickness_ratio": 0.74,
        "iori_mune_roof_height": {"machi": 1.4, "yokote": 0.9, "tip": 0.0},
        "hira_niku": {"machi": 0.35, "yokote": 0.25, "peak_at": "half way from the shinogi to the edge (niku * 4f(1-f))", "note": "convex bulge of each hira-ji face above the straight shinogi-to-edge line"},
        "kissaki": {
            "size": "chu-kissaki",
            "length_on_mune_arc": KISSAKI_LEN,
            "yokote_station_on_mune_arc": r(S_YOKOTE, 2),
            "yokote": "straight crisp crease across the blade, perpendicular to the mune at the yokote station",
            "fukura": "fukura-tsuku (moderately full): width w(q) = 22.0 x (1 - q^1.8)^0.7, q = arc fraction yokote -> tip",
            "ko_shinogi": "continues the shinogi line from the mitsukado to the tip at 0.27 x local width from the mune, crisp",
            "point": "the tip lies on the mune arc",
        },
        "machi_nakago": "ha-machi and mune-machi notches and the nakago are inside the habaki / tsuka and are NOT modelled; the blade mesh starts at the machi plane (z 58) under the habaki",
        "section_points": "per station, in (u = distance from the mune PEAK (the arc) toward the edge along the radial normal, y = thickness): mune peak (0, 0); mune shoulders (roof, +-0.37k); shinogi (0.27w, +-k/2); hira-ji f = 0.25/0.5/0.75 from shinogi to edge: (lerp(0.27w, w, f), +-(lerp(k/2, e/2, f) + niku*4f(1-f))); edge (w, +-e/2). Width w is measured from the mune peak.",
    },
    "hamon": {
        "style": "ko-notare (gentle low wave) with a soft nioi line; ko-maru boshi; plain, nothing dramatic",
        "distance_from_edge": {"machi": 6.5, "yokote": 5.0, "rule": "linear in arc length, measured across the hira-ji from the edge"},
        "undulation": {"amplitude": 1.0, "wavelengths": [118.0, 87.0, 131.0, 96.0, 109.0, 92.0, 124.0], "note": "sum of these half-cosine waves laid end to end from the machi; deterministic; the ura uses the same curve shifted 15 mm toward the tip"},
        "nioi_band": 1.0,
        "starts": "at the machi (hidden under the habaki); visible from the habaki top",
        "boshi": {"type": "ko-maru", "offset_inside_fukura": 4.0, "turn_radius": 4.0, "kaeri_along_mune": 5.0},
        "look": "hardened zone (edge -> hamon) frosted pale grey-white, higher roughness; ji polished dark blue-grey; boundary soft over the nioi band",
    },
    "habaki": {
        "z": [Z_MACHI, Z_MACHI + 28.0],
        "length": 28.0,
        "section_base": {"x": [-17.0, 17.5], "y_half": 6.0},
        "section_top": {"x": [-16.4, 16.8], "y_half": 4.9},
        "shape": "single-piece plain habaki: rounded-rectangle section (superellipse n 4), straight taper, flat top face perpendicular to the blade, crisp 0.4 mm bevels, no file marks or crest",
        "finish": "satin brass",
    },
    "seppa": {
        "count": 2,
        "outline": {"depth_x": 40.5, "width_y": 28.0, "superellipse_n": 2.6, "centre_x": 0.0},
        "thickness": 1.5,
        "z_blade_side": [Z_MACHI - 1.5, Z_MACHI],
        "z_tsuka_side": [Z_FUCHI_TOP, Z_FUCHI_TOP + 1.5],
        "edge_round": 0.3,
        "finish": "polished brass, plain",
    },
    "tsuba": {
        "form": "maru-gata (round), plain plate, no openings (no hitsu-ana), no relief",
        "diameter": 76.0,
        "plate_thickness": 5.0,
        "z_plate": [Z_FUCHI_TOP + 1.5, Z_FUCHI_TOP + 6.5],
        "mimi": {"type": "maru-mimi (rounded rim)", "width": 3.0, "thickness": 5.6, "z": [Z_FUCHI_TOP + 1.2, Z_FUCHI_TOP + 6.8]},
        "seppa_dai": "plain, flush with the plate, not outlined",
        "finish": "blackened iron, satin; faint hand-forged surface in the normal map only (<= 0.05 mm), no pattern",
    },
    "fuchi": {
        "z": [Z_FUCHI_BOT, Z_FUCHI_TOP],
        "height": 13.0,
        "outline_top": {"depth_x": 38.5, "width_y": 27.0},
        "outline_bottom": {"depth_x": 37.6, "width_y": 26.4},
        "superellipse_n": 2.6,
        "centre_x": 0.0,
        "wall": 0.8,
        "top_plate": 1.0,
        "edges": "top edge bevel 0.5, lower (ito) edge rounded 0.6",
        "finish": "blackened iron, plain, matches the tsuba",
    },
    "tsuka": {
        "length_fuchi_top_to_kashira_end": Z_FUCHI_TOP - Z_KASHIRA_END,
        "shape": "haichi: the mune side straight, the ha side tapering slightly toward the kashira; oval section (superellipse n 2.8); the tsuka axis is straight",
        "wrapped_silhouette": {
            "mune_x": 18.2,
            "ha_x": {"at_fuchi": -18.3, "at_kashira": -16.0},
            "width_y": {"at_fuchi": 25.6, "at_kashira": 23.6},
            "z_range": [Z_FUCHI_BOT, Z_KASHIRA_TOP],
        },
        "same_core_inset": 1.6,
        "core": "ho wood under one full white same panel wrapping all round (not visible except through the diamonds)",
    },
    "same": {
        "colour": "ivory white",
        "nodules": "dense rounded nodules 0.6 - 1.2 mm, in the normal map + subtle AO; no large 'emperor' nodule",
        "visible": "only through the ito diamonds",
    },
    "ito": {
        "material": "black flat cotton/silk cord",
        "style": "hineri-maki (twisted at every crossing), top cord alternating at successive crossings",
        "cord_width_visible": 8.0,
        "cord_width_at_edge_fold": 16.0,
        "width_rule": "width = lerp(8.0, 16.0, |l|^1.5), l = lateral position across the face (0 at the crossing, 1 at the edge): the flat ito spreads as it folds over the hishigami and closes the diamond's side points",
        "thickness": 1.4,
        "ito_length_on_tsuka": ITO_LEN,
        "wrap_pitch": r(PITCH, 3),
        "crossings_per_face": N_CROSS,
        "full_diamonds_per_face": N_CROSS - 1,
        "omote_crossing_z": omote_cross,
        "ura_crossing_z": ura_cross,
        "path_model": "two opposite wraps. Helix angle phi = -90deg +- 360deg * (z_fuchi_bot - 0.25 pitch - z) / pitch (from +X toward +Y; -90deg = omote centre, 0 = mune edge). The lateral position across the face l = 1 - |wrap(phi)| / 90deg is a triangle wave of z, so in the side view each cord runs in a STRAIGHT diagonal from a crossing to the edge; the face (omote/ura) is sign(sin phi). The cords cross only at the face centres; omote and ura crossings are offset by half a pitch; each edge (ha, mune) is crossed by one cord every half pitch",
        "crossing": "the upper cord twists (hineri) at each face crossing: it is turned over on itself so it stands up as a sharp fold ridge ~1.0 mm above the lower cord along the crossing's long axis; the over/under alternates at successive crossings of a face",
        "edges": "over the ha and mune edges each cord is lifted ~0.8 mm by its hishigami and spread to 16 mm, so the edge silhouette is scalloped (one bump per half pitch, >= 1 mm) and no same shows on the edges",
        "hishigami": "folded paper triangles under the cord at every edge pass: base 14 mm along the edge, 9.5 mm into the face, lifting the cord 0.8 mm; they close the diamonds' side corners to points",
        "fuchi_end": "cords start under the fuchi's lower edge, no knot",
        "kashira_end": "the two cords pass through the kashira's eyelets and over the end as one flat double band (2 x 8 mm) from omote to ura; ends hidden under the last crossings; NOTHING hangs",
        "diamond_opening": "see design_sheet_measured.diamond_* (computed from the path model by the sheet script)",
    },
    "menuki": {
        "form": "our own plain form: a domed lozenge with a low lengthwise centre ridge, rounded ends",
        "size": {"length": 30.0, "width": 10.0, "height": 3.2, "ridge": 0.4},
        "omote": {"face": "-Y", "z_centre": r((omote_cross[2] + omote_cross[3]) / 2.0, 2), "where": "third full diamond from the fuchi"},
        "ura": {"face": "+Y", "z_centre": r((ura_cross[5] + ura_cross[6]) / 2.0, 2), "where": "third full diamond from the kashira"},
        "seating": "on the same, under the ito; the cords pass over both ends and rise over them",
        "finish": "antique brass",
    },
    "mekugi": {
        "diameter": 6.0,
        "axis": "Y, through the tsuka",
        "x": 0.0,
        "z": r((omote_cross[0] + omote_cross[1]) / 2.0, 2),
        "visible": "omote: centred in the first full diamond; ura: under the first ura crossing",
        "head": "slightly domed, 0.3 above the same",
        "finish": "bamboo",
    },
    "kashira": {
        "z": [Z_KASHIRA_END, Z_KASHIRA_TOP],
        "height": 11.0,
        "base_outline": {"depth_x": 35.0, "width_y": 24.6, "superellipse_n": 2.6},
        "centre_x": 1.1,
        "profile": "straight sides for 7 mm, then a low dome closing over the last 4 mm (end crown nearly flat, 3.5 mm rise)",
        "eyelets": {"diameter_outer": 4.5, "diameter_inner": 2.8, "faces": "omote and ura", "z": -208.0, "finish": "brass"},
        "finish": "blackened iron, plain",
    },
    "saya": {
        "construction": "ho wood, black roiro (gloss) lacquer, buffalo-horn koiguchi, kurikata and kojiri; no kaeshizuno; no sageo",
        "frame": "pivot = BeltMount, on the mouth's tangent axis at the kurikata station; axes = the seated sword's axes; saya frame = sword frame - (0, 0, %.1f)" % Z_BELT,
        "curve": "concentric with the blade's mune arc (same centre); every station is given as a mune-arc length s from the machi of the seated sword",
        "mune_outer_radius": r(R - 4.5, 2),
        "mune_outer_rule": "mune clearance 0.5 + mune wall 4.0 -> the saya's mune line sits 4.5 mm outside the blade's mune",
        "depth_x": {"mouth": 40.0, "kojiri_end": 35.0, "rule": "linear in s"},
        "width_y": {"mouth": 27.5, "kojiri_end": 23.0, "rule": "linear in s"},
        "section": "superellipse n 2.4 in the (radial, Y) plane, centred radially at mune_outer + depth/2",
        "s_mouth": S_MOUTH,
        "s_end": r(S_SAYA_END, 2),
        "length_on_blade_mune_arc": r(S_SAYA_END - S_MOUTH, 2),
        "koiguchi": {"s": [S_MOUTH, S_MOUTH + 20.0], "material": "black horn", "flush": True, "seam_groove": [0.3, 0.2], "mouth_face": "flat, perpendicular to the arc, 0.4 mm round on the outer edge"},
        "kojiri": {"s": [r(S_SAYA_END - 28.0, 2), r(S_SAYA_END, 2)], "material": "black horn", "end": "flat, 4 mm round-over all round", "seam_groove": [0.3, 0.2]},
        "kurikata": {
            "s_centre": r(S_MOUTH + KURIKATA_FROM_MOUTH, 2),
            "from_mouth": KURIKATA_FROM_MOUTH,
            "face": "omote (-Y)",
            "radial_offset_toward_ha": 3.0,
            "size": {"along": 30.0, "radial_x": 11.0, "proud_of_face": 9.0},
            "profile": "rounded 'chestnut' knob: semicircular ends seen face-on, domed top",
            "hole": {"slot": [14.0, 4.5], "axis": "radial (X): through the knob, parallel to the face"},
            "shitodome": {"outer": [18.0, 8.0], "flange_proud": 0.6, "faces": "both X faces of the knob", "finish": "brass"},
            "material": "black horn",
        },
        "cavity": {
            "rule": "the seated blade (all LODs) + clearance: edge side 1.0, sides 1.0, mune 0.5; ends at s %.2f (10 mm past the tip)" % S_CAV_END,
            "habaki_pocket": "the habaki + 0.1 all round, from the mouth to 0.5 below the habaki top, swept along the draw arc",
            "min_wall": 3.0,
        },
        "sageo": "OMITTED: no cord on the mesh (a static cord freezes in one pose). The kurikata and its open shitodome stay, so a cord can be added later as a separate rigged or simulated piece",
        "finish": "black roiro lacquer, gloss",
    },
    "sheathed": {
        "seat": "the blade-side seppa face sits %.1f mm from the koiguchi face; the habaki is fully inside the koiguchi (0 mm visible); the whole blade is inside; the tip stops 10 mm short of the cavity end" % SEAT_GAP,
        "holster_in_saya_frame": [0.0, 0.0, r(-Z_BELT, 2)],
        "mouth_in_saya_frame": [0.0, 0.0, r(-(Z_BELT - Z_MACHI - SEAT_GAP), 2)],
        "draw": "rotation in the X-Z plane about the arc centre (saya frame x %.2f, z %.2f), the blade leaving toward -Z; the arc swept to the tip is %.2f deg" % (CENTRE[0], Z_MACHI - Z_BELT, math.degrees(PHI_TIP)),
        "gates": [
            "0 intersecting triangles, every sword LOD x saya LOD pair",
            "seat gap seppa -> koiguchi 0.3 +- 0.2 mm; 0 mm of habaki visible",
            "every blade vertex enclosed by the cavity; blade clearance >= 0.4 mm",
            "clean draw along the arc in <= 0.25 deg steps, 0 intersections at every step",
            "wall >= 3.0 mm everywhere (>= 2.3 at the koiguchi around the habaki pocket: the design minimum there is 2.35 at the pocket corners)",
        ],
    },
    "sockets": {
        "katana_mm": {
            "Grip": [0.0, 0.0, 0.0],
            "OffHand": [0.0, 0.0, -170.0],
            "BladeBase": [0.0, 0.0, Z_MACHI],
            "BladeTip": [r(TIP_X, 2), 0.0, r(TIP_Z, 2)],
        },
        "saya_mm": {
            "BeltMount": [0.0, 0.0, 0.0],
            "Mouth": [0.0, 0.0, r(-(KURIKATA_FROM_MOUTH), 2)],
            "Holster": [0.0, 0.0, r(-Z_BELT, 2)],
        },
        "katana_mm_extra": {
            "BladeMid": [r(MID_X, 2), 0.0, r(MID_Z, 2)],
            "TrailStart": [0.0, 0.0, Z_MACHI + 50.0],
            "TrailEnd": [r(TE_X, 2), 0.0, r(TE_Z, 2)],
            "note": "BladeMid = blade centre line at half the mune arc; TrailEnd = centre line 15 mm (arc) short of the tip; CenterOfMass is computed by the builder from part volumes",
        },
        "saya_mm_extra": {"DrawPivot": [r(CENTRE[0], 2), 0.0, r(Z_MACHI - Z_BELT, 2)], "note": "the arc centre in the saya frame; a clean draw rotates the katana about this point (about Y) by up to %.2f deg" % (math.degrees(PHI_TIP) + 1.0)},
        "rotations": "zero, except BladeTip: pitch = the blade tangent at the tip, %.3f deg from +Z toward +X. The Holster takes the sword's Grip with zero relative rotation" % math.degrees(PHI_TIP),
        "precedence": "positions here follow this design; KATANA_BUILD_PLAN.md section 6 lists the same sockets with nominal numbers that these replace",
    },
    "overall": {
        "kashira_end_z": Z_KASHIRA_END,
        "length_along_Z": r(TIP_Z - Z_KASHIRA_END, 2),
        "length_chord_kashira_to_tip": r(math.hypot(TIP_X, TIP_Z - Z_KASHIRA_END), 2),
    },
    "materials": {
        "note": "sRGB hex for base colour; roughness / metallic as authored. Metals 1.0, everything else 0.0 (house rule: no partial metallic)",
        "blade_ji": {"hex": "#6E757B", "rough": 0.14, "metal": 1.0},
        "blade_shinogi_ji_and_mune": {"hex": "#5C6268", "rough": 0.09, "metal": 1.0, "note": "burnished, darker mirror"},
        "blade_hamon": {"hex": "#C9CDD0", "rough": 0.34, "metal": 1.0, "note": "frosted"},
        "habaki": {"hex": "#B08D57", "rough": 0.30, "metal": 1.0},
        "seppa": {"hex": "#B8955E", "rough": 0.24, "metal": 1.0},
        "iron_fittings": {"hex": "#393633", "rough": 0.55, "metal": 1.0, "parts": "tsuba, fuchi, kashira"},
        "menuki": {"hex": "#9A7A45", "rough": 0.42, "metal": 1.0},
        "eyelets_and_shitodome": {"hex": "#B8955E", "rough": 0.30, "metal": 1.0},
        "ito": {"hex": "#19191B", "rough": 0.72, "metal": 0.0},
        "same": {"hex": "#E8E2D2", "rough": 0.55, "metal": 0.0},
        "mekugi": {"hex": "#A88A5A", "rough": 0.60, "metal": 0.0},
        "saya_lacquer": {"hex": "#0C0C0D", "rough": 0.12, "metal": 0.0},
        "horn": {"hex": "#16120F", "rough": 0.28, "metal": 0.0},
    },
    "slots_and_pack": {
        "precedence": "ADVISORY. KATANA_BUILD_PLAN.md (the game/tech plan) governs slots, texture sizes, budgets, LOD screen sizes and collision where it differs; this spec governs every dimension, form, pattern and colour",
        "SM_Katana": ["M_Katana_Blade (steel atlas: blade)", "M_Katana_Fittings (habaki, seppa, tsuba, fuchi, kashira, menuki, eyelets)", "M_Katana_Grip (ito, same, mekugi; ito recolourable)"],
        "SM_Katana_Saya": ["M_Katana_Saya_Lacquer (recolourable lacquer)", "M_Katana_Saya_Horn (koiguchi, kurikata, kojiri; shitodome brass via ORM metallic)"],
        "pack_masters": "Blade + Fittings -> M_Steel_Master; Grip -> M_Fabric_Master (ito colour); Lacquer -> M_Fabric_Master; Horn -> M_Fabric_Master with Metal From ORM (as the Snow Flower sheath). Finaliser decides.",
        "textures": "2048 per atlas (small held item rule); BC sRGB, ORM linear, N DirectX; full mips",
        "texel_targets": "blade >= 20 px/cm, grip >= 40 px/cm, saya >= 20 px/cm",
    },
    "budgets": {
        "precedence": "ADVISORY; KATANA_BUILD_PLAN.md section 3 governs",
        "SM_Katana_LOD0_max": 36000,
        "SM_Katana_LOD1_ratio": 0.45,
        "SM_Katana_LOD2_ratio": 0.15,
        "SM_Katana_Saya_LOD0_max": 8000,
        "SM_Katana_Saya_LOD1_ratio": 0.5,
        "SM_Katana_Saya_LOD2_ratio": 0.25,
        "lod_screen_sizes": [1.0, 0.5, 0.25],
        "lod_rule": "authored LODs; LOD1 keeps the ito as real geometry (fewer segments); LOD2 may bake the ito to a normal map on the core",
    },
    "collision": {
        "precedence": "ADVISORY; KATANA_BUILD_PLAN.md section 7 governs",
        "SM_Katana": "5 hulls UCX_SM_Katana_LOD0_00..04: blade base / mid / kissaki third (along the arc), tsuba, tsuka (fuchi..kashira)",
        "SM_Katana_Saya": "3 hulls UCX_SM_Katana_Saya_LOD0_00..02 along the arc (top one includes the kurikata), the top hull cut at the mouth plane",
    },
    "judging": [
        "blind test against KATANA_DESIGN_SHEET.png views: a judge must not pick the build on design",
        "key dimensions within +-0.5 mm (nagasa, sori, motohaba, sakihaba, kasane, kissaki, habaki, tsuba, tsuka, saya depth/width) on the exported bytes",
        "ito is real geometry: 9 crossings per face, 8 full diamonds, omote/ura offset half a pitch, hineri twist with alternating over/under, menuki at the specified diamonds",
        "hamon is plain ko-notare with a ko-maru boshi; nothing the spec does not call for",
    ],
}

MEAS = os.path.join(HERE, "sheet_measures.json")
if os.path.exists(MEAS):
    with open(MEAS, encoding="utf-8") as f:
        spec["design_sheet_measured"] = json.load(f)
    spec["ito"]["diamond_opening"] = "%.1f mm along the axis x %.1f mm across (measured on the sheet model, omote face, the 4th diamond)" % (
        spec["design_sheet_measured"]["diamond_along_mm"], spec["design_sheet_measured"]["diamond_across_mm"])

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)
print("wrote", OUT)
print("R", R, "phi deg", math.degrees(PHI_TIP), "S_TIP", S_TIP, "tip", TIP_X, TIP_Z)
print("pitch", PITCH, "omote", omote_cross, "ura", ura_cross)
print("menuki", spec["menuki"]["omote"]["z_centre"], spec["menuki"]["ura"]["z_centre"], "mekugi", spec["mekugi"]["z"])
print("saya", S_SAYA_END, "belt", Z_BELT, spec["overall"])
