#!/usr/bin/env python
"""Build SM_Shuriken_SixPoint - the roppo-gata six-point hira-shuriken (modern line).

Source of truth for the asset (house rule: the script, not the .blend).  This file is
only the form's SPEC and its report text; the C_n generator, M_Shuriken_Master, UVs,
UCX hull, sockets, LOD group, FBX, gallery renders, the JSON report and qa_check live in
Scripts/shuriken/shuriken_lib and are shared by every form in the pack.  Running it on
its own rebuilds Assets/Shuriken.blend FROM SCRATCH with this one form; the canonical
builder for the pack is build_pack.py
(``--forms four_point,eight_point,square_plate,six_point``).

Authority: References/Shuriken/SHURIKEN_STUDY.md section 2.4 (build-to numbers),
section 3 (construction and finish), section 4 (modelling plan, amended LOD table,
physics mass), section 5 (originality); the pack style (STYLE_TARGET.md top section,
shuriken_lib/material.py docstring); ASSET_GUIDELINES.md sections 6.1 - 6.5 (pipeline).

Build-to (study 2.4; the mass reference is a sourced one-piece steel retail six-point,
9.8 cm, 2 mm, 40 g [32]):
    across 98 mm (tip radius 49 mm), thickness 2.0 mm, mass about 40 g at 7.85 g/cm3,
    arm width 11 mm, hub radius 18 mm, centre hole 8 mm (the minimum opening: the hole
    polygon is circumscribed), tip included angle 38 deg.  C6, 60 deg pitch, +X down arm 0:
    each arm takes 2 asin(5.5/18) = 35.58 deg of its sector at the hub, leaving 24.42 deg
    of clear round hub.  No concavity.  With +X down one tip the plan box is 98 mm along X
    by 2 x 49 sin 60 = 84.87 mm along Y (study 2.4 draws it tip-up: 98 tall, 85 wide).

MODERN LINE, not the photograph: References/Shuriken/images/Roppo.JPG shows a traditional
piece (triangular points straight off a large hole).  The pack's modern line builds the
study's numbers above (decision 2026-09-18: "just stay with the modern line for now").

Edges (knife grind, the pack style): every cutting edge - the parallel arm edges and the
taper edges - knife ground on both faces at 35 deg from the face down to a 0.15 mm land.
On a 2.0 mm plate the grind is (1.0 - 0.075) / tan 35 = 1.321 mm wide in plan (1.43 mm
would be the land-free figure 1.0 / tan 35).  The scallops keep a 0.45 mm chamfer over a
tall wall, the hole a 0.3 mm deburr, and the grind runs out into the scallop over 3 mm at
each root.  The 40 +-2 g mass gate is evaluated on the un-ground plate; the ground mass is
reported against the study's 40-79 g range and drives the physics override.

Area: the study's cross-check (2486 mm2, 39.0 g) and the orchestrator's hand check
(~2505 mm2, 39.3 g) are both checked, not trusted.  ``area_check`` computes the exact
analytic area term by term (shuriken_lib.analytic_area), verifies the formula with an
independent shoelace integration of the outline and with an un-bevelled mesh at LOD0's
counts, and reconciles it with the measured finished mesh.

Originality (study 5): plain single points on parallel-sided arms off a round hub, a small
8 mm centre hole (not a large open ring), no stamp, no franchise name anywhere.

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate,six_point
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_six_point.py -- [options]      (this form only)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import (  # noqa: E402
    LOD1_BAND, LOD2_BAND, LodSpec, RadialStarSpec, analytic_area, numeric_outline_area, scaled_lod_screen_sizes,
)

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_SixPoint.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "six_point_report.json"

STUDY_CROSS_CHECK_MM2 = 2486.0      # study 2.4, unverified arithmetic
STUDY_CROSS_CHECK_G = 39.0
ORCHESTRATOR_HAND_CHECK = {"area_mm2": 2505.0, "mass_g": 39.3}   # the build brief's hand check, also checked
TIP_RADIUS_MM = 49.0

# --------------------------------------------------------------------------- spec

# LOD0.  Hub: an 18 mm hub round an 8 mm hole is the eight-point's problem (hub / hole ~4.5), so
# the hole ring is graded out to the plate rim through intermediate rings instead of a k:1 fan.
# Ring radii were searched (scratch search over 4,230 layouts, hub faces only) for the lowest
# worst-face aspect, then the lowest median: hole 24 -> ring 24 on the hole angles at t = 0.20 ->
# two rings on the arm-corner angles at t = 0.35 and 0.75 -> rim 36.  Worst hub face 4.58 (the
# eight-point ships 4.15), median 1.80 (eight-point 3.24), no mirror misses, 1320 triangles.
_LOD0 = LodSpec(
    columns=2,             # quads across the 11 mm arm (8.36 mm of flat plate between the grinds)
    notch_segments=2,      # per half notch -> 4 chords over the 24.42 deg notch arc (0.026 mm sagitta)
    hole_segments=4,       # per wedge -> 24-gon hole (0.034 mm sagitta; the eight-point's 16-gon lesson)
    bevel_segments=1,      # one flat knife facet
    straight_intervals=1,  # the flat parallel run (run-out station to shoulder) in one interval
    taper_intervals=3,     # shoulder to the grind apex
    tip_intervals=1,       # apex to the point: the ridge is straight, one interval is exact
    hub_rings=(("hole", 0.20), ("arm", 0.35), ("arm", 0.75)),   # r = 6.98, 8.96, 14.25 mm
    note="study 4 LOD0: full outline, knife grind, 24-gon hole ring graded to the hub plate rim",
)
# LOD1.  Study 4 halves the hole ring: 24 -> 12 (2 per wedge).  study_lod_chain's ceil(h/2) would
# give the same 12 from this LOD0, but it is spelled out because a C6 LOD0 with a 12-gon hole
# halves to a HEXAGON (the caveat from the C6 smoke test); the 12-gon sits 0.14 mm off the round
# hole, ~0.15 px at the ~0.89 m switch, so LOD1 still reads round.  One column and one chord per
# half notch (0.10 mm sagitta, 0.1 px there); hub: 12-gon -> one ring on the hole angles at
# t = 0.54 -> rim 18 (searched: worst face 3.82, median 1.77).
_LOD1 = LodSpec(
    columns=1, notch_segments=1, hole_segments=2, bevel_segments=1, straight_intervals=1,
    taper_intervals=1, tip_intervals=1, band=LOD1_BAND, hub_rings=(("hole", 0.54),),
    note="study 4 LOD1: hole ring halved to a 12-gon (hand-set: not a hexagon); graded hub 12 -> 12 -> 18",
)
# LOD2.  Study 4 drops the hole; decision D keeps a single-facet knife grind whose facets meet in an
# edge line (land 0), square scallops, pyramid tip.  At one column the run-out station costs 8
# triangles per wedge and still fits (228 of 250), so LOD2 keeps it like the four-point: the plate
# edge runs parallel from x_run and the whole parallel run is one constant facet (the eight-point
# could not afford it at C8).  Hub fanned from the axis.
_LOD2 = LodSpec(
    columns=1, notch_segments=1, hole_segments=0, bevel_segments=1, straight_intervals=1,
    taper_intervals=1, tip_intervals=0, band=LOD2_BAND,
    scallop=False, hole_bevel=False, runout_station=True, knife_land=False, pyramid_tip=True,
    note="study 4 LOD2: hole dropped; single-facet knife grind to an edge line, square scallops, pyramid tip; "
         "run-out station kept (the parallel run is one constant facet)",
)

SPEC = RadialStarSpec(
    form="six_point",
    mesh_name="SM_Shuriken_SixPoint",
    title="Roppo-gata six-point hira-shuriken",
    points=6,
    tip_circle_mm=2.0 * TIP_RADIUS_MM,
    thickness_mm=2.0,
    arm_width_mm=11.0,
    hub_radius_mm=18.0,
    hole_diameter_mm=8.0,
    tip_included_deg=38.0,
    grind_angle_deg=35.0,           # knife grind, the pack style (decision A)
    edge_land_mm=0.15,
    scallop_chamfer_mm=0.45,
    hole_chamfer_mm=0.30,
    grind_runout_mm=3.0,
    mass_target_g=40.0,             # sourced retail 9.8 cm / 2 mm / 40 g [32]
    mass_tolerance_g=2.0,
    study_mass_range_g=(40.0, 79.0),        # study 2.4 table
    study_mass_typical_g=(40.0, 54.0),
    lods=(_LOD0, _LOD1, _LOD2),
    study_section="2.4",
    revision=1,
    physics_mass_kg=0.04,           # study 4, Physics (the report's override is the ground mass)
    # UCX: the 12-vertex hexagonal tip prism, like the other stars: exactly C6, encloses every LOD by
    # construction and is the outline's exact convex hull in plan (the six tips are its corners).
    hull="tip_prism",
    # the pack's 1.0 / 0.10 / 0.035 are set for a 50 mm tip radius; at 49 mm they scale by 0.98 so the
    # switches stay at ~0.89 m and ~2.54 m (study 4, amended)
    lod_screen_sizes=scaled_lod_screen_sizes(TIP_RADIUS_MM),
)


# --------------------------------------------------------------------------- report text


def _grams(area_mm2: float) -> float:
    return area_mm2 * SPEC.thickness_mm / 1000.0 * SPEC.density_g_cm3


def area_check(report: dict) -> dict:
    """Study 2.4's cross-check and the brief's hand check against the exact analytic area and the mesh."""
    from shuriken_lib import unbevelled_plate_area_mm2

    params = dict(report["lod_params"][report["objects"][0]])
    params["band"] = tuple(params["band"])
    params["hub_rings"] = tuple(tuple(r) for r in params.get("hub_rings") or ())
    lod0 = LodSpec(**params)
    a = analytic_area(SPEC, lod0)
    numeric = numeric_outline_area(SPEC)
    plain = unbevelled_plate_area_mm2(SPEC, lod0)
    measured = report["measured"]["plate_area_mm2"]
    bevel_removed = plain["plate_area_mm2"] - measured
    exact = a["exact"]
    study_err = STUDY_CROSS_CHECK_MM2 - exact
    hand_err = ORCHESTRATOR_HAND_CHECK["area_mm2"] - exact
    r4 = lambda v: round(v, 4)  # noqa: E731
    return {
        "method": ("Exact plan area of the un-ground outline = hub disc - round hole + 6 x (parallel run outside "
                   "the hub circle + taper triangle). Parallel run = w * x_taper - cap, cap = integral over "
                   "|y| <= w/2 of sqrt(r^2 - y^2) = (w/2) sqrt(r^2 - w^2/4) + r^2 asin(w / 2r). Taper triangle = "
                   "(w/2) * L, L = (w/2) / tan(tip/2). shuriken_lib.spec.analytic_area; mass = area x 2.0 mm x "
                   "7.85 g/cm3."),
        "inputs": {"tip_radius_mm": TIP_RADIUS_MM, "arm_width_mm": SPEC.arm_width_mm,
                   "hub_radius_mm": SPEC.hub_radius_mm, "hole_mm": SPEC.hole_diameter_mm,
                   "tip_included_deg": SPEC.tip_included_deg, "thickness_mm": SPEC.thickness_mm,
                   "density_g_cm3": SPEC.density_g_cm3},
        "terms_mm2": {
            "hub_disc pi 18^2": r4(a["hub_disc"]),
            "hole_disc pi 4^2": r4(a["hole_disc"]),
            "hub_minus_hole": r4(a["hub_minus_hole"]),
            f"per_arm_rectangle w x_taper (11 x {a['x_taper_mm']:.4f})": r4(a["arm_rectangle_to_shoulder"]),
            "per_arm_circular_cap_inside_hub": r4(a["arm_circular_cap_inside_hub"]),
            "per_arm_parallel_run_outside_hub": r4(a["arm_parallel_run_outside_hub"]),
            f"per_arm_taper_triangle 5.5 x {a['taper_len_mm']:.4f}": r4(a["arm_taper_triangle"]),
            "per_arm_total": r4(a["arm_total"]),
            "six_arms": r4(a["arms_total"]),
            "total": r4(exact),
        },
        "analytic_exact_mm2": r4(exact),
        "analytic_exact_g": r4(_grams(exact)),
        "numeric_shoelace_mm2": r4(numeric),
        "numeric_minus_analytic_mm2": float(f"{numeric - exact:.3e}"),
        "study_2_4_mm2": STUDY_CROSS_CHECK_MM2,
        "study_2_4_g": STUDY_CROSS_CHECK_G,
        "study_minus_exact_mm2": r4(study_err),
        "study_minus_exact_pct": round(100.0 * study_err / exact, 3),
        "hand_check_mm2": ORCHESTRATOR_HAND_CHECK["area_mm2"],
        "hand_check_g": ORCHESTRATOR_HAND_CHECK["mass_g"],
        "hand_check_minus_exact_mm2": r4(hand_err),
        "study_slip": {
            "arms_counted_from_hub_radius_mm2": r4(a["arms_from_hub_radius_mm2"]),
            "arms_counted_from_hub_radius_g": r4(_grams(a["arms_from_hub_radius_mm2"])),
            "root_sliver_per_arm_mm2": r4(a["root_sliver_per_arm"]),
            "explanation": (f"2486 is {a['arms_from_hub_radius_mm2']:.2f} mm2 rounded: the area you get when each arm's "
                            f"parallel run is counted as a plain rectangle from the line x = r_hub (11 x "
                            f"({a['x_taper_mm']:.3f} - 18)) instead of from the hub arc. The arm root actually starts on "
                            f"the arc at x = sqrt(18^2 - 5.5^2) = 17.139 mm, so 6 circular slivers of "
                            f"{a['root_sliver_per_arm']:.4f} mm2 ({6 * a['root_sliver_per_arm']:.2f} mm2 in all) belong "
                            "to the star and were dropped - the same slip as study 2.1's first 1647 and 2.2's 3055."),
        },
        "reconciliation_mm2": {
            "1 exact outline": r4(exact),
            f"2 notch arcs as {a['polygon_notch_chords']} chords": r4(-a["polygon_notch_chord_loss"]),
            f"3 hole as the circumscribed {a['polygon_hole_segments']}-gon": r4(-a["polygon_hole_excess"]),
            "4 = analytic polygonised outline": r4(a["polygonised"]),
            "5 un-ground mesh at LOD0's counts, measured": plain["plate_area_mm2"],
            "6 knife grind removes (5 - 7)": r4(-bevel_removed),
            "7 = finished LOD0, measured (volume / 2.0 mm)": measured,
            "check 4 vs 5 (formula vs generator)": float(f"{plain['plate_area_mm2'] - a['polygonised']:.3e}"),
        },
        "measured_mesh_mm2": measured,
        "measured_mesh_g": report["measured"]["mass_g"],
        "unbevelled_mesh": plain,
        "which_is_right": (
            f"The exact analytic area, {exact:.2f} mm2 ({_grams(exact):.2f} g at 2.0 mm), is the correct area of the "
            f"outline study 2.4 specifies: an independent shoelace integration agrees to {abs(numeric - exact):.1e} mm2 "
            f"and the generator's own un-ground mesh at LOD0's counts matches the polygonised figure to "
            f"{abs(plain['plate_area_mm2'] - a['polygonised']):.1e} mm2. The brief's hand check (~2505 mm2, 39.3 g) is "
            f"right ({hand_err:+.2f} mm2, rounding). The study's 2486 mm2 / 39.0 g is {-study_err:.2f} mm2 "
            f"({-100.0 * study_err / exact:.2f}%) low: it is the arm-root slip of 2.1 and 2.2 again. The un-ground "
            f"plate the mass gate reads is {report['measured']['outline_mass_g']:.2f} g (the polygonised outline), "
            f"against the sourced 40 g; the knife grind removes {bevel_removed:.2f} mm2-equivalent, so the finished "
            f"star is {measured:.2f} mm2 / {report['measured']['mass_g']:.2f} g."),
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
        "extent_mm": [round(float(np.ptp(co[:, i])) / MM, 4) for i in range(3)],
        "z_mm": [round(float(co[:, 2].min()) / MM, 4), round(float(co[:, 2].max()) / MM, 4)],
        "c6_max_deviation_mm": cn_deviation(obj, SPEC.points),
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
    lods = [bpy.data.objects.get(name) for name in report["objects"]]
    out["every_lod_max_outside_mm"] = {}
    from shuriken_lib import MM
    from shuriken_lib.geometry import hull_outside_distance
    from shuriken_lib.measure import evaluated_bm
    bm = evaluated_bm(hull)
    try:
        hco = np.array([v.co[:] for v in bm.verts], dtype=np.float64)
        hfaces = [tuple(v.index for v in f.verts) for f in bm.faces]
    finally:
        bm.free()
    for obj in lods:
        if obj is not None:
            co = np.array([v.co[:] for v in obj.data.vertices], dtype=np.float64)
            out["every_lod_max_outside_mm"][obj.name] = round(hull_outside_distance(hco, hfaces, co) / MM, 6)
    # The probe runs after the .blend was saved and exported, and removes what it made.
    probe = bpy.data.objects.new("PROBE_SixPointHull", lod0.data.copy())
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


def annotate(report: dict) -> None:
    """Six-point-only report text: area check, hull, originality, LOD choice, gaps."""
    measured = report["measured"]
    check = area_check(report)
    report["area_check"] = check
    report["build_to"].update({
        "study_cross_check_mm2": STUDY_CROSS_CHECK_MM2, "study_cross_check_g": STUDY_CROSS_CHECK_G,
        "hand_check_mm2": ORCHESTRATOR_HAND_CHECK["area_mm2"], "hand_check_g": ORCHESTRATOR_HAND_CHECK["mass_g"],
        "analytic_exact_mm2": check["analytic_exact_mm2"], "analytic_exact_g": check["analytic_exact_g"],
        "plan_box_mm": [2.0 * TIP_RADIUS_MM, round(2.0 * TIP_RADIUS_MM * math.sin(math.radians(60.0)), 4)],
        "orientation": "+X down arm 0 (study 4 pivot rule): 98 mm along X, 84.87 mm along Y",
        "study_cross_check_note": (
            "SHURIKEN_STUDY.md 2.4's cross-check (49 mm tip, 11 mm arm, 18 mm hub, 38 deg = 2486 mm2, 39.0 g) is "
            f"{abs(check['study_minus_exact_pct']):.2f}% low: the exact analytic area of that outline is "
            f"{check['analytic_exact_mm2']:.2f} mm2 ({check['analytic_exact_g']:.2f} g), which the brief's hand check "
            f"(~2505 mm2, 39.3 g) matches. See area_check. The mass gate is the un-ground plate (outline x 2.0 mm, "
            f"{measured['outline_mass_g']:.2f} g against the sourced 40 g); the knife grind takes the finished star to "
            f"{measured['ground_mass_g']:.2f} g, reported, not gated."),
    })
    hull = hull_check(report)
    report["hull_check"] = hull
    franchise = [c for c in report["qa"]["checks"] if c["name"] == "no_franchise_strings"]
    report["originality"] = {
        "basis": "historical roppo-gata hira-shuriken, public domain (study 5); modern-line proportions (study 2.4)",
        "points": (f"6 plain single points, {SPEC.tip_included_deg:g} deg included, on parallel-sided 11 mm arms off a "
                   "round 18 mm hub - the study's modern line, deliberately NOT the photographed traditional piece "
                   "(References/Shuriken/images/Roppo.JPG: triangular points straight off a large hole)"),
        "hole_mm": measured["hole_mm"],
        "hole": ("round centre hole, 8 mm minimum opening (study 2.4, ESTIMATE in the 6-10 mm retail range) - not a "
                 "large open ring (study 5's franchise trait); no engraving"),
        "arm_width_mm": measured["arm_width_mm"],
        "tip_taper": (f"{SPEC.tip_included_deg:g} deg included; every cutting edge knife ground at "
                      f"{SPEC.grind_angle_deg:g} deg to a {measured['edge_land_mm']:.2f} mm land, the point ending in a "
                      f"{measured['tip_edge_height_mm']:.2f} mm edge"),
        "finish": ("the pack finish (M_Shuriken_Master): satin coat (linear ~0.10, metallic 1.0, roughness 0.34), a "
                   "0.7 mm polished band along the edge land over a satin grimy grind, polished last 2.5 mm of each "
                   "point, narrow nicks along the grind line, soft smears, the dished halo round the hole in the normal "
                   "map, fine mostly-dark clustered micro-scratches, near-invisible pits, two sub-pixel rust specks"),
        "stamp": "none (study 5; any future mark must be an invented glyph)",
        "franchise_strings": (f"none in any object, mesh, material, texture or file name; qa_check "
                              f"no_franchise_strings passed on {sum(c['passed'] for c in franchise)} of "
                              f"{len(franchise)} objects"),
    }
    topo = report.get("topology_quality", {})
    report["lod_choice"] = {
        "lod0": ("2 columns, 2 notch, 4 hole segments per wedge (24-gon hole), hub graded hole 24 -> ring 24 at "
                 "t 0.20 -> arm rings 24 at t 0.35 and 0.75 -> plate rim 36; one flat knife facet, 1 straight, "
                 "3 taper, 1 tip interval"),
        "lod1": ("1 column, 1 notch, 2 hole segments per wedge (12-gon, hand-set so it never halves to a hexagon), "
                 "hub graded 12 -> ring 12 at t 0.54 -> rim 18; one knife facet, 1 straight, 1 taper, 1 tip interval"),
        "lod2": ("1 column, 1 notch, no hole (study 4); a single-facet knife grind to an edge line on every cutting "
                 "edge, square scallops, the run-out station kept (one constant facet on the parallel run), the "
                 "shoulder capped straight onto the point; hub fanned from the axis"),
        "hub_search": ("LOD0 / LOD1 hub rings chosen by a scratch search (4,230 / 2,739 layouts) for the lowest "
                       "worst hub-face aspect, then the lowest median"),
        "topology_quality": {name: {k: q.get(k) for k in ("hub_aspect_median", "hub_aspect_max", "hub_mirror_misses",
                                                          "min_triangle_angle_deg", "triangles_under_5deg")}
                             for name, q in topo.items()},
        "screen_sizes": (f"{report.get('lod_screen_sizes')} = the pack's 1.0 / 0.10 / 0.035 scaled by 49 / 50 mm, so "
                         "the switches stay at ~0.89 m and ~2.54 m; see lod_switching"),
    }
    report["known_gaps"] += [
        "Tip angle (38 deg), arm width (11 mm) and hub radius (18 mm) are study 2.4 modelling defaults chosen to "
        "reproduce the sourced ~40 g (study 2: no source publishes a tip angle); the 8 mm hole is an ESTIMATE. The "
        "downloaded photo (Roppo.JPG) is a traditional piece and was deliberately not followed (modern line).",
        f"The knife grind takes {measured['grind_removes_g']:.2f} g off the un-ground plate: the finished star is "
        f"{measured['ground_mass_g']:.2f} g against the study's {SPEC.study_mass_range_g[0]:g}-"
        f"{SPEC.study_mass_range_g[1]:g} g range (below its 40 g floor, as the four-point's finished 32.6 g is below "
        "its 34 g floor: the sourced masses are of pieces with square edges); the gate is on the outline and the "
        "physics override uses the finished mass.",
        "LOD2 has no hole by design (study 4); at the ~2.54 m switch the filled 8 mm hole is ~3 px. Quote the "
        "arm-region deviation for silhouette loss. LOD2's hub is a fan from the axis.",
    ]
    if (not isinstance(hull.get("c6_max_deviation_mm"), (int, float)) or hull["c6_max_deviation_mm"] > 1e-4
            or hull.get("lod0_max_outside_mm", 1.0) > 1e-6):
        report["known_gaps"].append(f"The UCX hull is not exactly C6 or does not enclose LOD0: {hull}.")
    probe = hull.get("pipeline_hull_for_comparison")
    probe_text = (f" (the pipeline hull, probed on this build: {probe['verts']} verts, {probe['c6_max_deviation_mm']} "
                  f"mm off C6, LOD0 up to {probe['lod0_max_outside_mm']} mm outside it)"
                  if isinstance(probe, dict) else "")
    report["known_gaps"].append(
        "The UCX hull is the 12-vertex hexagonal tip prism (hull='tip_prism'), not the pipeline's decimated hull"
        f"{probe_text}. It is a flat 2.0 mm slab through the 6 tips, 98 x 84.87 mm in plan: like any convex hull it "
        "spans the gaps between the points, and it stays full thickness over the knife grind. That is the "
        "conservative side for a thrown projectile; a stick-into-wall mechanic should trace from a tip (study 4).")


def _form():
    from shuriken_lib import Form  # needs bpy; SPEC above does not
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate, report_name="six_point_report.json")


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


# --------------------------------------------------------------------------- CLI


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_six_point.py", description=__doc__,
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
