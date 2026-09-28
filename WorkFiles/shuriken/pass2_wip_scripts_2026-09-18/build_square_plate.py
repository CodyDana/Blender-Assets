#!/usr/bin/env python
"""Build SM_Shuriken_SquarePlate - the senban, a square plate standing on a corner.

Source of truth for the asset (house rule: the script, not the .blend).  This file is the
form's SPEC and its report text; the square-plate generator, its measurement and its
FormGeometry hook live in Scripts/shuriken/shuriken_lib/plate.py (+ plate_spec.py), and
everything else - M_Shuriken_Master, UVs, UCX hull, sockets, LOD group, FBX, bake, gallery,
JSON report, qa_check - is the pack's shared path (shuriken_lib.pack).  It is the pack's
first non-radial form: it plugs in through ``Form(geometry=SquarePlateGeometry(SPEC))``.

Authority: References/Shuriken/SHURIKEN_STUDY.md section 2.3 (build-to numbers), section 3
(construction and finish), section 4 (modelling plan, LOD table, physics mass), section 5
(originality); ASSET_GUIDELINES.md sections 6.1 - 6.5 (pipeline).  Generic name only: the
asset is a "square plate", "senban" only as the historical type name, no maker, retailer
or franchise name anywhere (study 5).

Build-to (study 2.3, the [17] pair: 3 in closest tips / 4.25 in farthest = a 76.2 mm square):
    side 76.2 mm, so corner to corner 76.2 x sqrt 2 = 107.763 mm (the study rounds it to 108);
    thickness 1.9 mm (the thinnest plate in the pack: real thickness, never a plane);
    square hole 12.7 mm (sourced), sides PARALLEL to the outer square (image F: the hole's
    corners point at the outer corners), corners filleted r = 1.0 mm (a punched hole is never
    razor-cornered; image F's corners are visibly radiused at ~4-5 % of the hole width);
    concave sides one circular arc each, sagitta 6 mm (ESTIMATE; image F measures ~5.3 mm on a
    76.2 mm side, chart I's variants range from shallow to deep - kept at the study's 6 mm);
    mass ~66 g (DERIVED) at 7.85 g/cm3.

Sharpening (the question the study left open): study 3 says grind only a short facet at each
point and leave the long edges square; source [42] says the senban's sides are ground sharp.
Image F (public-domain flatbed scan) shows a continuous facet band along the FULL length of
all four concave sides - bright on the bottom and side edges, dark on the top edge, as
inclined facets under one scanner lamp would read - and at the bottom-left corner the two
bands meet in a mitre line; chart I's heavier variant shows the same full-length ground bevel
unmistakably.  So this form departs from study 3 on photographic evidence: the pack's ground
chamfer (spec.ChamferProfile, style pass: 0.8 mm wide in plan, 0.4 mm deep, a tiny round-over
at the wall) on both faces along every side, mitred into a ridge at each corner, leaving a
square land at the edge (ground sharp, but not a knife edge a 1.9 mm plate could not hold or
a renderer could not shade).  The scan shows one face only; both faces are ground (a thrown
plate is symmetric).

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_square_plate.py -- [options]      (this form only)
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import PlateLodSpec, SquarePlateSpec, plate_analytic_area, scaled_lod_screen_sizes  # noqa: E402

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_SquarePlate.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "square_plate_report.json"

SIDE_MM = 76.2
STUDY_DIAGONAL_MM = 108.0                 # study 2.3's rounded build-to diagonal
ORCHESTRATOR_HAND_CHECK = {"square_mm2": 5806.4, "segment_mm2": 306.4, "hole_mm2": 161.3,
                           "area_mm2": 4420.0, "mass_g": 65.9}

# --------------------------------------------------------------------------- LODs
# Counts are per HALF side (an eighth of the plate); the generator mirrors and rotates them (D4).
# LOD0: 8 chords per half side = 16 per side (knife grind pass; was 12).  The study's "two or three
# segments is plenty" is the arc's shape, not the hero close-up: 124 mm arc radius, so a 3-chord side
# sits 0.67 mm off the arc (~9 px in the 1600 px hero) and a 16-chord side 0.024 mm.  The hole
# fillet: 2 chords per half corner (4 per corner, 0.019 mm off the 1 mm radius), with a 0.3 mm
# deburr.  The rings buy topology, not shape: two hole-parallel offsets spread the fillet's 0.39 mm
# chords, then four blended rings grade out to the 16-chord plate edge (searched: plate aspect max
# 11.6, no plate triangle under 12.6 deg) - without them the plate is a fan of 0.5 deg slivers
# (measured: aspect 237).  The one-facet knife grind costs fewer triangles than the first style
# pass's 3-segment chamfer; the extra chords are silhouette, not padding.
_LOD0 = PlateLodSpec(
    edge_intervals=8, fillet_segments=2, bevel_segments=1, hole_intervals=1, fillet_u=0.34,
    offsets_mm=(1.5, 4.0), rings=((3, 0.18), (4, 0.4), (5, 0.62), (7, 0.82)), band=(1200, 2500),
    note="LOD0: 16 chords per side (0.024 mm sagitta), one-facet knife grind, 4-chord hole fillets + deburr, graded plate",
)
# LOD1 (switch at ~0.89 m, ~1 px/mm): study 4 halves the hole's corner chords (4 -> 2); the knife
# grind is one facet already; the side goes to 8 chords (0.096 mm, ~0.1 px).  One offset, one ring.
_LOD1 = PlateLodSpec(
    edge_intervals=4, fillet_segments=1, bevel_segments=1, hole_intervals=1, fillet_u=0.34,
    offsets_mm=(2.5,), rings=(("edge", 0.3),), band=(500, 900),
    note="LOD1: 8 chords per side, one-facet knife grind, 2-chord fillets + deburr",
)
# LOD2 (switch at ~2.54 m, ~0.38 px/mm): study 4 drops the fillets (and the deburr); decision D keeps a
# single-facet knife grind whose facets meet in an edge line (no wall); the hole is KEPT as a plain square - 12.7 mm is ~5 px there and it is the form's defining feature (the eight-point
# dropped a 9.5 mm round hole at ~3.6 px).  4 chords per side: 2 would sit 1.5 mm off the arc,
# which is invisible (0.6 px) but puts LOD2's wall ~20 px off its UV island (the pack's cross-LOD
# UV gate allows 8); 4 chords (0.38 mm) keep it at ~5 px.  128 triangles; the stars' 120-250 floor
# does not apply to a plate and nothing is padded to reach it.
_LOD2 = PlateLodSpec(
    edge_intervals=2, fillet_segments=0, bevel_segments=1, hole_intervals=1, band=(0, 250),
    knife_land=False, hole_bevel=False,
    note="LOD2: fillets and deburr dropped, single-facet knife grind to an edge line, plain square hole, 4 chords per side",
)

SPEC = SquarePlateSpec(
    form="square_plate",
    mesh_name="SM_Shuriken_SquarePlate",
    title="Senban square-plate hira-shuriken",
    side_mm=SIDE_MM,
    thickness_mm=1.9,
    sagitta_mm=6.0,
    hole_side_mm=12.7,
    hole_fillet_mm=1.0,
    grind_angle_deg=35.0,                 # knife grind on all four concave sides (decision A)
    edge_land_mm=0.15,
    hole_chamfer_mm=0.30,
    mass_target_g=66.0,
    mass_tolerance_g=2.0,
    study_mass_range_g=(45.0, 82.0),      # study 2.3 table
    study_mass_typical_g=(60.0, 66.0),
    lods=(_LOD0, _LOD1, _LOD2),
    hole_orientation="parallel",
    edge_grind="full_side",
    study_section="2.3",
    revision=3,
    physics_mass_kg=0.06,                 # study 4, Physics
    island_margin=0.012,                  # see plate.SquarePlateGeometry.island_margin_reason
    # the stars' tip-wear ramp starts where the point is ~5.5-6 mm wide (four-point 6.0, eight-point
    # 5.5); the senban's 54.2 deg corner is 5.9 mm wide 5.8 mm from the tip
    corner_wear_mm=5.8,
    # the pack's 1.0 / 0.10 / 0.035 are for a 50 mm tip radius; the senban's corner radius is
    # 53.88 mm, so the thresholds scale by 1.0776 to keep the ~0.89 m / ~2.54 m switch distances
    lod_screen_sizes=scaled_lod_screen_sizes(SIDE_MM / math.sqrt(2.0)),
)


# --------------------------------------------------------------------------- report text


def _grams(area_mm2: float) -> float:
    return area_mm2 * SPEC.thickness_mm / 1000.0 * SPEC.density_g_cm3


def area_check(report: dict) -> dict:
    """The hand check against the exact analytic area, the generator and the finished mesh."""
    from shuriken_lib import unbevelled_plate

    params = dict(report["lod_params"][report["objects"][0]])
    params["band"] = tuple(params["band"])
    params["offsets_mm"] = tuple(params["offsets_mm"])
    params["rings"] = tuple(tuple(r) for r in params["rings"])
    lod0 = PlateLodSpec(**params)
    a = plate_analytic_area(SPEC, lod0)
    plain = unbevelled_plate(SPEC, lod0)
    measured = report["measured"]["plate_area_mm2"]
    measured_volume = report["measured"]["volume_mm3"]
    facet_removed = plain["volume_mm3"] - measured_volume
    # the facet profile is polygonised too: the K-chord round-over cuts a little deeper than the round
    k = lod0.bevel_segments
    facet_poly = a["facet_volume_mm3"] * a["facet_section_polygon_mm2"] / a["facet_section_mm2"]
    exact = a["exact"]
    hand = ORCHESTRATOR_HAND_CHECK["area_mm2"]
    r4 = lambda v: round(v, 4)  # noqa: E731
    return {
        "method": ("Exact plan area of the un-bevelled outline = side^2 - 4 circular segments - the hole. "
                   "Arc: chord c = 76.2, sagitta h = 6 -> radius rho = ((c/2)^2 + h^2) / 2h = 123.9675 mm, "
                   "angle phi = 2 asin(c / 2 rho); segment = rho^2 (phi - sin phi) / 2. Hole: 12.7^2 minus the "
                   "material its four r = 1 mm fillets leave in the corners, (4 - pi) r^2. "
                   "shuriken_lib.plate_spec.plate_analytic_area; mass = area x 1.9 mm x 7.85 g/cm3."),
        "terms_mm2": {
            "square 76.2^2": r4(a["square_side2"]),
            "segment per side": r4(a["segment_per_side"]),
            "four segments": r4(a["segments_total"]),
            "hole 12.7^2 (sharp)": r4(a["hole_sharp_square"]),
            "fillet material left in the hole corners (4 - pi) 1^2": r4(a["hole_fillet_material_left"]),
            "hole, filleted": r4(a["hole"]),
            "total": r4(exact),
        },
        "analytic_exact_mm2": r4(exact),
        "analytic_exact_g": r4(_grams(exact)),
        "hand_check_mm2": hand,
        "hand_check_g": ORCHESTRATOR_HAND_CHECK["mass_g"],
        "hand_check_terms": ORCHESTRATOR_HAND_CHECK,
        "hand_minus_exact_mm2": r4(hand - exact),
        "hand_minus_exact_pct": round(100.0 * (hand - exact) / exact, 3),
        "study_mass_g": SPEC.mass_target_g,
        "reconciliation_mm2": {
            "1 exact outline": r4(exact),
            f"2 edges as {a['polygon_edge_chords']} chords (each lies outside the concave edge)":
                r4(a["polygon_edge_gain"]),
            f"3 fillets as {a['polygon_fillet_chords']} chords (the hole shrinks)": r4(a["polygon_hole_shrink"]),
            "4 = analytic polygonised outline": r4(a["polygonised"]),
            "5 un-bevelled mesh at LOD0's counts, measured": plain["plate_area_mm2"],
            "6 ground facet removes (5 - 7), as area": r4(-facet_removed / SPEC.thickness_mm),
            "7 = finished LOD0, measured (volume / 1.9 mm)": measured,
            "check 4 vs 5 (formula vs generator)": float(f"{plain['plate_area_mm2'] - a['polygonised']:.3e}"),
        },
        "facet_volume_mm3": {
            "analytic_round_profile": r4(a["facet_volume_mm3"]),
            f"analytic_{k}_chord_profile": r4(facet_poly),
            "measured_unbevelled_minus_finished": r4(facet_removed),
            "measured_minus_analytic_chord_profile": float(f"{facet_removed - facet_poly:.3e}"),
            "note": ("both faces, all four sides: the chamfer profile's depth (a flat facet with a round-over at "
                     "the wall, spec.ChamferProfile.drop_at) integrated over the concave band (area element "
                     "(rho + s) ds dbeta) minus the band beyond each corner mitre (straight-edge approximation); "
                     "the mesh profile is K chords, whose round-over cuts slightly deeper than the arc"),
        },
        "measured_mesh_mm2": measured,
        "measured_mesh_g": report["measured"]["mass_g"],
        "unbevelled_mesh": plain,
        "which_is_right": (
            f"The exact analytic area, {exact:.2f} mm2 ({_grams(exact):.2f} g at 1.9 mm), is the area of the outline "
            f"study 2.3 specifies. The hand check ({hand:.0f} mm2, {ORCHESTRATOR_HAND_CHECK['mass_g']} g) agrees to "
            f"{hand - exact:+.2f} mm2 ({100.0 * (hand - exact) / exact:+.3f} %): unlike the four- and eight-point "
            "checks it drops nothing, because a square minus segments has no arm-root slivers to lose; its "
            "segment (306.4) is 0.09 mm2 high and it did not count the fillets. The generator's un-bevelled mesh "
            f"matches the polygonised figure to {abs(plain['plate_area_mm2'] - a['polygonised']):.1e} mm2. The "
            f"finished mesh ({measured:.2f} mm2, {report['measured']['mass_g']:.2f} g) is lower because the "
            f"full-length ground chamfer removes {facet_removed:.2f} mm3 ({facet_removed / 1000.0 * 7.85:.2f} g); "
            "the 66 g target was derived without a facet."),
    }


def _hull_stats(obj, lod0_co):
    import numpy as np

    from shuriken_lib import MM, cn_deviation
    from shuriken_lib.geometry import hull_outside_distance
    from shuriken_lib.measure import evaluated_bm

    bm = evaluated_bm(obj)
    try:
        volume = bm.calc_volume(signed=True)
        co = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    finally:
        bm.free()
    radial = np.hypot(co[:, 0], co[:, 1])
    return {
        "verts": len(co),
        "faces": len(faces),
        "radius_mm": [round(float(radial.min()) / MM, 4), round(float(radial.max()) / MM, 4)],
        "z_mm": [round(float(co[:, 2].min()) / MM, 4), round(float(co[:, 2].max()) / MM, 4)],
        "c4_max_deviation_mm": cn_deviation(obj, 4),
        "lod0_max_outside_mm": round(hull_outside_distance(co, faces, lod0_co) / MM, 6),
        "volume_mm3": round(volume / MM ** 3, 3),
        "hull_volume_mass_g": round(volume / (0.01 ** 3) * SPEC.density_g_cm3, 3),
    }


def hull_check(report: dict) -> dict:
    """The shipped hull, and what pipeline.make_ucx_hull would have produced (probed, then deleted)."""
    import bpy
    import numpy as np

    import pipeline

    lod0 = bpy.data.objects.get(report["objects"][0])
    hull = bpy.data.objects.get(report["hull"]["name"])
    if lod0 is None or hull is None:
        return {"error": f"{report['objects'][0]} or {report['hull']['name']} not found"}
    lod0_co = np.array([v.co[:] for v in lod0.data.vertices], dtype=np.float64)
    out = {"name": hull.name, "method": report.get("hull_method"), **_hull_stats(hull, lod0_co)}
    probe = bpy.data.objects.new("PROBE_SquarePlateHull", lod0.data.copy())
    bpy.context.scene.collection.objects.link(probe)
    bpy.context.view_layer.update()
    made = None
    try:
        made = pipeline.make_ucx_hull(probe, index=0, max_verts=24)
        bpy.context.view_layer.update()
        out["pipeline_hull_for_comparison"] = _hull_stats(made, lod0_co)
    except Exception as exc:                                    # pragma: no cover
        out["pipeline_hull_for_comparison"] = f"probe failed: {type(exc).__name__}: {exc}"
    finally:
        for obj in (made, probe):
            if obj is not None:
                data = obj.data
                bpy.data.objects.remove(obj)
                if data is not None and data.users == 0:
                    bpy.data.meshes.remove(data)
    return out


REFERENCE_OBSERVATIONS = [
    "Image F (commons File:Senban.jpg, public domain, a flatbed scan of one senban; viewed on the file page, "
    "not downloaded): the square hole's sides run PARALLEL to the outer square's sides, so its corners point at "
    "the outer corners. Built that way ('parallel': hole corners on the axes).",
    "Image F: a continuous facet band runs the full length of all four concave sides - light on the bottom and "
    "side edges, dark on the top edge, as inclined facets read under one scanner lamp - and at the bottom-left "
    "corner the two bands meet in a mitre line. Plan width about 0.85 mm on a 76.2 mm side. This is a ground "
    "edge along each side, not a short facet at the points.",
    "Chart I (commons File:Senban_Shuriken_types.jpg, CC BY-SA, viewed only): every variant has the hole "
    "parallel to the outer square; the heavier 3 mm variant shows a wide bright ground bevel along the full "
    "length of every side, mitred at the corners; the 2.5 mm variant a narrower edge band; the blackened ones "
    "are deeply concave. Supports source [42] (sides ground sharp) over the study 3 default for THIS form.",
    "Image F proportions (screen measurement, +-5 px of ~808): sagitta about 7.0 % of the side, i.e. ~5.3 mm "
    "on a 76.2 mm side, against the study's 6 mm ESTIMATE (kept: 6 mm is inside the scatter of the chart's "
    "variants and the 66 g target was derived with it). The hole in F is ~27 % of the side (~21 mm at this "
    "scale) - F's object is not the sourced 12.7 mm-hole listing, so its hole size is not used.",
    "Image F: the hole corners are visibly radiused, about 4 - 5 % of the hole width (~0.8 - 1.0 mm at F's "
    "scale): built r = 1.0 mm. The hole's far wall shows as a dark band, so the scan is slightly off-axis; the "
    "facet bands on the bottom, left and right sides cannot be walls seen from that direction.",
]

SHARPENING_DECISION = {
    "question": ("study 3: a short ground facet at each point, long edges square; source [42]: the senban's "
                 "sides are ground sharp"),
    "seen": ("image F: full-length facet bands on all four concave sides meeting in a mitre at the corner; "
             "chart I: full-length ground bevels on the senban variants"),
    "decision": ("full_side, knife ground (style pass 2): one flat facet at 35 deg from the face on BOTH faces "
                 "along every concave side, run down to a 0.15 mm land and mitred into a ridge at each corner (the "
                 "corner ends in a vertical edge the height of the land)"),
    "why_not_study_3": ("the photographs are conclusive for this form; study 3's rule is a general hira-shuriken "
                        "observation (points sharpened, long edges blunt) and the senban - a tool-derived plate "
                        "whose whole edge is the cutting edge - is the documented exception [42]"),
    "why_a_land": ("a zero-width knife edge on LOD0 would be a degenerate wall (normals, UV and lightmap slivers); "
                   "a 0.15 mm land reads as the thin bright crest line of the reference and stays a clean face. "
                   "LOD2 lets the facets meet in an edge line (no wall)"),
    "wear": ("the knife grind is bare ground steel all round (M_Shuriken_Master) with small 0.2-0.8 mm chips into "
             "the face along it, the points bare over their last 6 mm - matching F's lighter edge bands"),
}


def annotate(report: dict) -> None:
    """Senban-only report text: area check, reference decisions, originality, LOD choice, gaps."""
    measured = report["measured"]
    check = area_check(report)
    report["area_check"] = check
    report["build_to"].update({
        "analytic_exact_mm2": check["analytic_exact_mm2"], "analytic_exact_g": check["analytic_exact_g"],
        "hand_check_mm2": check["hand_check_mm2"], "hand_check_g": check["hand_check_g"],
        "diagonal_note": ("the [17] pair (3 in closest tips, 4.25 in farthest) is a 76.2 mm square: corner to "
                          f"corner 76.2 x sqrt 2 = {SIDE_MM * math.sqrt(2.0):.3f} mm, which study 2.3 rounds to "
                          "108 mm. Built to the exact square; measured "
                          f"{measured['corner_to_corner_mm']:.4f} mm."),
    })
    report["reference_observations"] = list(REFERENCE_OBSERVATIONS)
    report["sharpening_decision"] = dict(SHARPENING_DECISION)
    report["hull_check"] = hull = hull_check(report)
    franchise = [c for c in report["qa"]["checks"] if c["name"] == "no_franchise_strings"]
    report["originality"] = {
        "basis": "historical senban (kugi-nuki derived square plate), public domain (study 2.3, 5)",
        "name": ("generic only: SM_Shuriken_SquarePlate / T_Shuriken_SquarePlate_*; no maker, retailer or "
                 "franchise name in any object, mesh, material, texture, file or report key"),
        "outline": (f"a {SIDE_MM} mm square on a corner with four {SPEC.sagitta_mm:g} mm concave sides (one arc "
                    "each) - the generic type, built to the sourced closest-tip size, not traced from any photo"),
        "hole": (f"{measured['hole_across_flats_mm']:.3f} mm square, sides parallel to the outer square, corners "
                 f"filleted r = {measured['hole_fillet_radius_mm']:.3f} mm"),
        "finish": ("dark coat (linear ~0.10, faintly cool) with soft cavity grime toward the hole, bare bright steel on "
                   "the knife grind all round with small chips into the face along it, a lightly brightened hole "
                   "deburr, many faint micro-scratches, two rust specks; clearly darker coat than bare metal"),
        "stamp": "none (study 5; any future mark must be an invented glyph)",
        "franchise_strings": (f"qa_check no_franchise_strings passed on {sum(c['passed'] for c in franchise)} of "
                              f"{len(franchise)} objects"),
    }
    topo = report.get("topology_quality", {})
    report["lod_choice"] = {
        "lod0": _LOD0.note, "lod1": _LOD1.note, "lod2": _LOD2.note,
        "triangles": report["lod_triangles"],
        "bands": ("study 4's bands are written for stars. LOD0 (1200-2500) and LOD1 (500-900) land inside "
                  "them anyway; LOD2 is 96 triangles, under the stars' 120 floor, and is not padded: its 4 "
                  "chords per side are 0.38 mm off the arc (~0.14 px at the ~2.54 m switch), the plain square "
                  "hole is the only interior feature, and nothing else would change silhouette or shading"),
        "lod0_below_1200": "not applicable: LOD0 is 1440",
        "screen_sizes": (f"{report.get('lod_screen_sizes')} = the pack's 1.0 / 0.10 / 0.035 scaled by "
                         "53.88 / 50 (corner radius / the stars' 50 mm tip radius), so the switches stay at "
                         "~0.89 m and ~2.54 m; see lod_switching"),
        "hole_at_lod2": ("kept, against study 4's 'drop the hole': 12.7 mm is ~5 px at the LOD2 switch (the "
                         "eight-point's 9.5 mm round hole was ~3.6 px) and a filled hole would pop; it costs "
                         "32 of LOD2's 96 triangles"),
        "topology_quality": {name: {k: q.get(k) for k in ("plate_aspect_median", "plate_aspect_max",
                                                           "plate_faces_aspect_over_8", "plate_mirror_misses",
                                                           "plate_min_triangle_angle_deg", "min_triangle_angle_deg",
                                                           "strip_triangles_under_5deg")}
                             for name, q in topo.items()},
        "strips": ("the facet and wall are long strips along a 310 mm perimeter (0.36 mm facet segments, 0.5 mm "
                   "land, 6.45 mm silhouette chords), so their triangles have 3 - 5 deg angles by aspect, not by "
                   "fanning; lifting them past 5 deg would need ~10 chords per half side (+60 % triangles) for "
                   "no change in silhouette or shading. The plate faces - where slivers do matter - have none "
                   "under 12 deg."),
        "without_rings": ("the plate zipped straight from the hole to the edge is 864 triangles with 0.5 deg "
                          "slivers (aspect 237) fanning off the fillet chords"),
    }
    report["physics_note"] = f"Mass in KG override {SPEC.physics_mass_kg} kg (study 4), set in the Blueprint."
    report["style_pass_changes"] = [
        f"Revision 3 (knife grind, style pass 2). All four concave sides knife ground at {SPEC.grind_angle_deg:g} deg to "
        f"a {measured['edge_land_mm']} mm land (grind {measured['facet_plan_width_mm']} mm wide), hole a "
        f"{SPEC.hole_chamfer_mm} mm deburr; outline, hole and sagitta unchanged. Mass gate on the un-ground plate "
        f"({measured['outline_mass_g']} g), ground mass {measured['ground_mass_g']} g reported. LODs "
        f"{report['lod_triangles']} (LOD0 16 chords per side, LOD1 8; LOD2 keeps a single-facet grind to an edge line).",
        f"Revision 2 (style pass, STYLE_TARGET.md). The 0.7 mm quarter-round facet became the pack's ground chamfer: "
        f"{measured['facet_plan_width_mm']} mm wide, wall top {measured['facet_drop_mm']} mm below the plate, "
        f"{measured['edge_land_mm']} mm land; outline, hole and sagitta unchanged. Mass {measured['mass_g']} g "
        "(rev 1: 65.47 g).",
        "M_Shuriken_Master reworked to the reference recipe (see the four-point report / STYLE_TARGET.md).",
        "Second style round: M_Shuriken_Master rebuilt around gradients (crest-to-fringe bare steel, hairline scratch "
        "pairs, darkening pits, radial patina), hero overhead panel + top facet band in the shared rig, facet and "
        "mean gates, LOD1/2 UV0 clamped to the unit square; geometry, LODs, hull and sockets unchanged.",
    ]
    report["known_gaps"] += [
        "Sagitta 6 mm is the study's ESTIMATE; image F measures ~5.3 mm on a 76.2 mm side (+-0.7 mm from a "
        "screen measurement). At 5.3 mm the plate would be ~2 g heavier. Kept at 6 mm.",
        "The full-length grind departs from study 3's short-facet default on photographic evidence (image F, "
        "chart I, source [42]); since style pass 2 it is a knife grind to a "
        f"{measured['edge_land_mm']} mm land; the scan shows one face, both faces are ground.",
        "Image F's own hole is ~27 % of its side; the sourced 12.7 mm hole (study 2.3 [17]) is built. The hole "
        "fillet radius (1.0 mm) is read from F's corner shape, not sourced.",
        "LOD2 keeps the hole (study 4 drops it) and is 96 triangles, under the stars' 120 floor - see lod_choice.",
        "The facet and wall strips have 3 - 5 deg triangles by aspect (see lod_choice.strips); the plate faces "
        "have none under 12 deg.",
    ]
    if (not isinstance(hull.get("c4_max_deviation_mm"), (int, float)) or hull["c4_max_deviation_mm"] > 1e-9
            or hull.get("lod0_max_outside_mm", 1.0) > 1e-6):
        report["known_gaps"].append(f"The UCX hull is not exactly C4 or does not enclose LOD0: {hull}.")
    probe = hull.get("pipeline_hull_for_comparison")
    probe_text = (f" (the pipeline hull, probed on this build: {probe['verts']} verts, {probe['c4_max_deviation_mm']} "
                  f"mm off C4, LOD0 up to {probe['lod0_max_outside_mm']} mm outside it)"
                  if isinstance(probe, dict) else "")
    report["known_gaps"].append(
        "The UCX hull is the 8-vertex square prism through the four corners at full 1.9 mm thickness "
        f"(hull='tip_prism'){probe_text}: the plate's exact convex hull in plan, so like any convex hull it spans "
        "the four concave sides (up to 6 mm of air at each side midpoint) and stays full thickness over the ground "
        f"chamfers ({measured['facet_drop_mm']} mm proud per face at the edge). Conservative for a thrown projectile; a stick-into-wall "
        "mechanic should trace from a corner (study 4).")


def _form():
    from shuriken_lib import Form, SquarePlateGeometry  # needs bpy; SPEC above does not
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate, report_name="square_plate_report.json",
                geometry=SquarePlateGeometry(SPEC))


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


# --------------------------------------------------------------------------- CLI


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_square_plate.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(parser)
    parser.add_argument("--fbx", default=str(DEFAULT_FBX))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    return parser.parse_args(blender_argv(argv))


def main() -> int:
    from shuriken_lib import run_single
    return run_single(FORM, parse_args())


if __name__ == "__main__":
    sys.exit(main())
