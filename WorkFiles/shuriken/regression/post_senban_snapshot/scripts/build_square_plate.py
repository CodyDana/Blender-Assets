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
unmistakably.  So this form departs from study 3 on photographic evidence: a rounded ground
facet (the pack's quarter-round profile, b = 0.7 mm in plan and in depth) on both faces along
every side, mitred into a ridge at each corner, leaving a 0.5 mm square land at the edge
(ground sharp, but not a knife edge a 1.9 mm plate could not hold or a renderer could not
shade).  The scan shows one face only; both faces are ground (a thrown plate is symmetric).

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
# LOD0: 6 chords per half side = 12 per side.  The study's "two or three segments is plenty" is
# the arc's shape, not the hero close-up: 124 mm arc radius, so a 3-chord side sits 0.67 mm off
# the arc (~9 px in the 1600 px hero) and a 12-chord side 0.042 mm (~0.5 px, the pack's hole-ring
# criterion on the eight-point).  The hole fillet: 2 chords per half corner (4 per corner, 0.019 mm
# off the 1 mm radius).  The rings buy topology, not shape: two hole-parallel offsets spread the
# fillet's 0.39 mm chords, then three blended rings grade out to the 12-chord edge - without them
# the plate is a fan of 0.5 deg slivers (measured: aspect 237), which MikkTSpace tangents and the
# generated lightmap UVs handle badly and the wireframe gallery shows.  No plate triangle under
# 12.9 deg, none over aspect 9.7.  Nothing here is padding for a band floor.
_LOD0 = PlateLodSpec(
    edge_intervals=6, fillet_segments=2, bevel_segments=3, hole_intervals=1, fillet_u=0.34,
    offsets_mm=(1.5, 4.0), rings=((3, 0.2), (4, 0.45), (5, 0.72)), band=(1200, 2500),
    note="LOD0: 12 chords per side (0.042 mm sagitta), 3-segment facet, 4-chord hole fillets, graded plate",
)
# LOD1 (switch at ~0.89 m, ~1 px/mm): study 4 halves the facet segments (3 -> 2) and the hole's
# corner chords (4 -> 2); the side goes to 6 chords (0.17 mm, ~0.2 px).  One offset and one ring.
_LOD1 = PlateLodSpec(
    edge_intervals=3, fillet_segments=1, bevel_segments=2, hole_intervals=1, fillet_u=0.34,
    offsets_mm=(2.5,), rings=(("edge", 0.3),), band=(500, 900),
    note="LOD1: 6 chords per side, 2-segment facet, 2-chord fillets",
)
# LOD2 (switch at ~2.54 m, ~0.38 px/mm): study 4 drops the facet and the fillets; the hole is KEPT
# as a plain square - 12.7 mm is ~5 px there and it is the form's defining feature (the eight-point
# dropped a 9.5 mm round hole at ~3.6 px).  4 chords per side: 2 would sit 1.5 mm off the arc,
# which is invisible (0.6 px) but puts LOD2's wall ~20 px off its UV island (the pack's cross-LOD
# UV gate allows 8); 4 chords (0.38 mm) keep it at ~5 px.  96 triangles; the stars' 120-250 floor
# does not apply to a plate and nothing is padded to reach it.
_LOD2 = PlateLodSpec(
    edge_intervals=2, fillet_segments=0, bevel_segments=0, hole_intervals=1, band=(0, 250),
    note="LOD2: facet and fillets dropped, plain square hole kept, 4 chords per side",
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
    bevel_offset_mm=0.7,
    mass_target_g=66.0,
    mass_tolerance_g=2.0,
    lods=(_LOD0, _LOD1, _LOD2),
    hole_orientation="parallel",
    edge_grind="full_side",
    study_section="2.3",
    revision=1,
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
    # the facet profile is polygonised too: K chords of a quarter circle cut deeper than the round
    k = lod0.bevel_segments
    delta = 0.5 * math.pi / k
    b = SPEC.bevel_offset_mm
    profile_extra = k * b * b * (delta - math.sin(delta)) / 2.0          # mm2 of section per face
    facet_poly = a["facet_volume_mm3"] * (1.0 + profile_extra / a["facet_quarter_round_section_mm2"])
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
            "note": ("both faces, all four sides: the quarter-round depth b - sqrt(2bs - s^2) integrated over "
                     "the concave band (area element (rho + s) ds dbeta) minus the band beyond each corner "
                     "mitre (straight-edge approximation); the mesh profile is K chords of the quarter "
                     "circle, which cut slightly deeper than the round"),
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
            f"full-length ground facet removes {facet_removed:.2f} mm3 ({facet_removed / 1000.0 * 7.85:.2f} g); "
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
    "decision": ("full_side: a rounded ground facet (the pack's quarter-round profile, b = 0.7 mm in plan and "
                 "in depth, 3 segments at LOD0) on BOTH faces along every concave side, mitred into a ridge at "
                 "each corner, leaving a 0.5 mm square land (the corner ends in a 0.5 mm chisel edge)"),
    "why_not_study_3": ("the photographs are conclusive for this form; study 3's rule is a general hira-shuriken "
                        "observation (points sharpened, long edges blunt) and the senban - a tool-derived plate "
                        "whose whole edge is the cutting edge - is the documented exception [42]"),
    "why_a_land": ("a knife edge on a 1.9 mm plate would be a zero-width wall (degenerate normals, UV and "
                   "lightmap slivers) and is not what a thrown plate keeps; a 0.5 mm land reads sharp at every "
                   "gallery distance and keeps the pack's round-over convention"),
    "wear": ("the facet is bare ground steel all round (M_Shuriken_Master's facet mask, noise-modulated), with "
             "the chipped tip wear on the four points over the last 5.8 mm of radius (where the corner is "
             "narrower than ~6 mm, the stars' criterion) - matching F's lighter edge bands"),
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
        "finish": ("blackened oxide, not flat grey: base colour (0.035, 0.034, 0.033) linear, bare steel on the "
                   "full-length ground facet and worn through on the four points"),
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
    report["known_gaps"] += [
        "Sagitta 6 mm is the study's ESTIMATE; image F measures ~5.3 mm on a 76.2 mm side (+-0.7 mm from a "
        "screen measurement). At 5.3 mm the plate would be ~2 g heavier. Kept at 6 mm.",
        "The full-length ground facet departs from study 3's short-facet default on photographic evidence (image F, "
        "chart I, source [42]); the scan shows one face, both faces are ground. The facet is the pack's rounded "
        "profile with a 0.5 mm land, not a knife edge.",
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
        "facets (0.7 mm proud per face at the edge). Conservative for a thrown projectile; a stick-into-wall "
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
