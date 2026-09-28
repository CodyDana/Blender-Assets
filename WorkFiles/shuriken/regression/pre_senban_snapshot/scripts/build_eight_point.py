#!/usr/bin/env python
"""Build SM_Shuriken_EightPoint - the happo-gata eight-point hira-shuriken.

Source of truth for the asset (house rule: the script, not the .blend).  This file is
only the form's SPEC and its report text; the C_n generator, M_Shuriken_Master, UVs,
UCX hull, sockets, LOD group, FBX, gallery renders, the JSON report and qa_check live in
Scripts/shuriken/shuriken_lib and are shared by every form in the pack.  Running it on
its own rebuilds Assets/Shuriken.blend FROM SCRATCH with this one form; the canonical
builder for the pack is build_pack.py (``--forms four_point,eight_point``).

Authority: References/Shuriken/SHURIKEN_STUDY.md section 2.2 (build-to numbers),
section 3 (construction and finish), section 4 (modelling plan, LOD table, physics
mass), section 5 (originality); ASSET_GUIDELINES.md sections 6.1 - 6.5 (pipeline).

Build-to (study 2.2; the mass reference is Royal Armouries XXVIM.21, 102.0 mm, 2.5 mm,
57.5 g):
    across 100 mm (tip radius 50 mm), thickness 2.5 mm, mass about 60 g at 7.85 g/cm3,
    arm width 10 mm, hub radius 22 mm, centre hole 9.5 mm (the minimum opening: the hole
    polygon is circumscribed), tip included angle 35 deg.  C8, 45 deg pitch: each arm
    takes 2 asin(5/22) = 26.27 deg of its sector at the hub, leaving 18.73 deg of clear
    hub (study: 26 / 19).  Large round hub, short arms: it reads as a sun.

Bevel (study 2.2 "Bevel the last 16 mm"; study 3 "a short ground facet near each point,
long edges square"): the taper is 15.858 mm long, so the facet covers exactly the taper
and begins on the shoulder.  0.75 mm is the four-point's proportion (0.9 of 3.0 mm =
30% of the thickness per side), leaving a 1.0 mm flat rim band and a 1.0 mm chisel edge
at the point.  The same 1.2 mm run-out and 3 rounded segments as the four-point.

Area: the study's cross-check (3055 mm2, 60.0 g) is checked, not trusted.  The report's
``area_check`` computes the exact analytic area term by term (shuriken_lib.analytic_area),
verifies the formula with an independent shoelace integration of the outline and with an
un-bevelled mesh at LOD0's counts, and reconciles it with the measured finished mesh.

Revision 2 (maintenance pass, after the geometry / Unreal / visual review):
    graded ring hub instead of the 3:1 pinwheel fan (LodSpec.hub_rings), 24-gon hole,
    LOD0 taper in 4 intervals (no triangle under 5 deg), LOD1 8-gon hole on a graded hub,
    LOD1/LOD2 UV0 from LOD0's islands, baked T_Shuriken_EightPoint_BC/_ORM/_N and a
    gallery rendered from those maps, pack LOD screen sizes 1.0 / 0.10 / 0.035, measured
    tip angle and bevel stations, SHA-256-bound engine check (UnrealCheck6).

Originality (study 5): plain single points, NOT the three-tipped trident points of
XXVIM.21; a centre hole, NOT XXVIM.21's small rim hole beside an engraved dragon; no
stamp; no franchise name anywhere.  Finish: blackened with bare steel worn through at
the points, which is the one thing taken from XXVIM.21 (study 2.2: loss of the black
coating on the points).

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_eight_point.py -- [options]      (this form only)
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import LOD1_BAND, LOD2_BAND, LodSpec, RadialStarSpec, analytic_area, numeric_outline_area  # noqa: E402

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_EightPoint.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "eight_point_report.json"

STUDY_CROSS_CHECK_MM2 = 3055.0      # study 2.2, unverified arithmetic
STUDY_CROSS_CHECK_G = 60.0

# --------------------------------------------------------------------------- spec

# Revision 2 (maintenance pass).  The hub is graded rings instead of the 16-gon hole fanned
# 3:1 onto the 48-segment rim, which the wireframe showed as a chiral pinwheel of 17 mm
# slivers (median aspect 14.4, max 19.6, 32 of 48 hub faces over 8).  Radii were searched
# for the lowest worst-face aspect (scratch search, hub faces only): LOD0 hole -> 24-segment
# ring at r = 12.5 mm -> 32-segment ring on the arm-corner angles at r = 19.0 mm -> rim.
_LOD0 = LodSpec(
    columns=2,             # quads across the 10 mm arm; the centre column line runs on as a hub spoke
    notch_segments=2,      # per half notch -> 4 chords over the 18.73 deg notch arc (0.018 mm sagitta)
    hole_segments=3,       # per wedge -> 24-gon (was 16: its corners showed at ~1.3 px in the hero;
                           # the 24-gon's 0.041 mm is ~0.5 px)
    bevel_segments=3,      # rounded ground facet, as the four-point
    straight_intervals=2,  # 12.1 mm parallel run in ~6 mm steps (near-square quads)
    taper_intervals=4,     # run-out ring to bevel apex: 4 keeps the facet strips at ~3.0 x 0.39 mm
                           # (min triangle angle ~7 deg, as the four-point; 2 gave 3.4 deg slivers)
    tip_intervals=2,       # bevel apex to the point (curved roof)
    hub_rings=(("hole", 0.448), ("arm", 0.826)),   # r = 12.50 mm and 19.01 mm
    note="study 4 LOD0: full outline, bevels, 24-gon hole ring graded to the hub rim",
)
# LOD1: study 4 halves the hole ring (24 -> 8: one segment per wedge keeps it an octagon,
# 0.39 mm off the 24-gon) and the bevel segments (3 -> 2, rounded up so it stays a curve).
# It also drops what carries no silhouette at LOD1's size: one plate column, one chord
# per half notch (0.07 mm sagitta, 0.08 px at the 0.10 switch), one straight and one taper
# interval, and the 2.49 mm roof past the bevel apex in one interval.  Hub: the verifier's
# octagon -> 8-segment ring (r = 13 mm) -> 24-segment rim.
_LOD1 = LodSpec(
    columns=1, notch_segments=1, hole_segments=1, bevel_segments=2, straight_intervals=1,
    taper_intervals=1, tip_intervals=1, band=LOD1_BAND, hub_rings=(("hole", 0.466),),
    note="study 4 LOD1: hole ring and bevel segments halved; graded hub (8-gon -> 8 ring -> 24 rim)",
)
# LOD2: study 4 drops the bevel and the hole; the hub is a symmetric fan from the axis.
_LOD2 = LodSpec(
    columns=1, notch_segments=1, hole_segments=0, bevel_segments=0, straight_intervals=1,
    taper_intervals=1, tip_intervals=0, band=LOD2_BAND,
    note="study 4 LOD2: bevel and hole dropped",
)

SPEC = RadialStarSpec(
    form="eight_point",
    mesh_name="SM_Shuriken_EightPoint",
    title="Happo-gata eight-point hira-shuriken",
    points=8,
    tip_circle_mm=100.0,
    thickness_mm=2.5,
    arm_width_mm=10.0,
    hub_radius_mm=22.0,
    hole_diameter_mm=9.5,
    tip_included_deg=35.0,
    bevel_offset_mm=0.75,
    bevel_runout_mm=1.2,
    mass_target_g=60.0,
    mass_tolerance_g=2.0,
    lods=(_LOD0, _LOD1, _LOD2),
    study_section="2.2",
    revision=2,
    physics_mass_kg=0.06,           # study 4, Physics
    # pipeline.make_ucx_hull collapse-decimates this form's convex hull to 24 vertices and lands
    # ~1.1 mm off C8, past the tips and inside the plate faces (hull_check re-measures it on every
    # build as pipeline_hull_for_comparison); the 16-vertex tip prism is exactly C8 and encloses LOD0.
    hull="tip_prism",
)


# --------------------------------------------------------------------------- report text


def _grams(area_mm2: float) -> float:
    return area_mm2 * SPEC.thickness_mm / 1000.0 * SPEC.density_g_cm3


def area_check(report: dict) -> dict:
    """Study 2.2's cross-check against the exact analytic area and the finished mesh."""
    from shuriken_lib import unbevelled_plate_area_mm2

    params = dict(report["lod_params"][report["objects"][0]])
    params["band"] = tuple(params["band"])
    lod0 = LodSpec(**params)
    a = analytic_area(SPEC, lod0)
    numeric = numeric_outline_area(SPEC)
    plain = unbevelled_plate_area_mm2(SPEC, lod0)
    measured = report["measured"]["plate_area_mm2"]
    bevel_removed = plain["plate_area_mm2"] - measured
    four = analytic_area(replace(SPEC, points=4, tip_circle_mm=97.0, thickness_mm=3.0, arm_width_mm=11.0,
                                 hub_radius_mm=11.0, hole_diameter_mm=8.0, tip_included_deg=40.0))
    exact = a["exact"]
    study_err = STUDY_CROSS_CHECK_MM2 - exact
    r4 = lambda v: round(v, 4)  # noqa: E731
    return {
        "method": ("Exact plan area of the un-bevelled outline = hub disc - round hole + 8 x (parallel "
                   "run outside the hub circle + taper triangle). Parallel run = w * x_taper - cap, "
                   "cap = integral over |y| <= w/2 of sqrt(r^2 - y^2) = (w/2) sqrt(r^2 - w^2/4) + "
                   "r^2 asin(w / 2r). Taper triangle = (w/2) * L, L = (w/2) / tan(tip/2). "
                   "shuriken_lib.spec.analytic_area; mass = area x 2.5 mm x 7.85 g/cm3."),
        "inputs": {"tip_radius_mm": 0.5 * SPEC.tip_circle_mm, "arm_width_mm": SPEC.arm_width_mm,
                   "hub_radius_mm": SPEC.hub_radius_mm, "hole_mm": SPEC.hole_diameter_mm,
                   "tip_included_deg": SPEC.tip_included_deg, "thickness_mm": SPEC.thickness_mm,
                   "density_g_cm3": SPEC.density_g_cm3},
        "terms_mm2": {
            "hub_disc pi 22^2": r4(a["hub_disc"]),
            "hole_disc pi 4.75^2": r4(a["hole_disc"]),
            "hub_minus_hole": r4(a["hub_minus_hole"]),
            "per_arm_rectangle w x_taper (10 x 34.1420)": r4(a["arm_rectangle_to_shoulder"]),
            "per_arm_circular_cap_inside_hub": r4(a["arm_circular_cap_inside_hub"]),
            "per_arm_parallel_run_outside_hub": r4(a["arm_parallel_run_outside_hub"]),
            "per_arm_taper_triangle 5 x 15.8580": r4(a["arm_taper_triangle"]),
            "per_arm_total": r4(a["arm_total"]),
            "eight_arms": r4(a["arms_total"]),
            "total": r4(exact),
        },
        "analytic_exact_mm2": r4(exact),
        "analytic_exact_g": r4(_grams(exact)),
        "numeric_shoelace_mm2": r4(numeric),
        "numeric_minus_analytic_mm2": float(f"{numeric - exact:.3e}"),
        "study_2_2_mm2": STUDY_CROSS_CHECK_MM2,
        "study_2_2_g": STUDY_CROSS_CHECK_G,
        "study_minus_exact_mm2": r4(study_err),
        "study_minus_exact_pct": round(100.0 * study_err / exact, 3),
        "study_slip": {
            "arms_counted_from_hub_radius_mm2": r4(a["arms_from_hub_radius_mm2"]),
            "root_sliver_per_arm_mm2": r4(a["root_sliver_per_arm"]),
            "explanation": (f"3055 is {a['arms_from_hub_radius_mm2']:.2f} mm2 rounded: the area you get when "
                            "each arm's parallel run is counted as a plain rectangle from the line x = r_hub "
                            "(10 x (34.142 - 22)) instead of from the hub arc. The arm root actually starts on "
                            f"the arc at x = sqrt(22^2 - 5^2) = 21.424 mm, so 8 circular slivers of "
                            f"{a['root_sliver_per_arm']:.4f} mm2 ({8 * a['root_sliver_per_arm']:.2f} mm2 in all) "
                            "belong to the star and were dropped."),
            "same_slip_in_study_2_1": (f"The same formula on the four-point numbers gives {four['exact']:.2f} mm2 "
                                       f"exact (the study's corrected 1668) and {four['arms_from_hub_radius_mm2']:.2f} "
                                       "mm2 when the arms are counted from the hub radius (the study's original "
                                       "1647, 1.3% low)."),
        },
        "reconciliation_mm2": {
            "1 exact outline": r4(exact),
            f"2 notch arcs as {a['polygon_notch_chords']} chords": r4(-a["polygon_notch_chord_loss"]),
            f"3 hole as the circumscribed {a['polygon_hole_segments']}-gon": r4(-a["polygon_hole_excess"]),
            "4 = analytic polygonised outline": r4(a["polygonised"]),
            "5 un-bevelled mesh at LOD0's counts, measured": plain["plate_area_mm2"],
            "6 ground bevel removes (5 - 7)": r4(-bevel_removed),
            "7 = finished LOD0, measured (volume / 2.5 mm)": measured,
            "check 4 vs 5 (formula vs generator)": float(f"{plain['plate_area_mm2'] - a['polygonised']:.3e}"),
        },
        "measured_mesh_mm2": measured,
        "measured_mesh_g": report["measured"]["mass_g"],
        "unbevelled_mesh": plain,
        "which_is_right": (
            f"The exact analytic area, {exact:.2f} mm2 ({_grams(exact):.2f} g at 2.5 mm), is the correct area "
            f"of the outline study 2.2 specifies: an independent shoelace integration of the outline agrees to "
            f"{abs(numeric - exact):.1e} mm2, and the generator's own un-bevelled mesh at LOD0's counts matches "
            f"the polygonised figure to {abs(plain['plate_area_mm2'] - a['polygonised']):.1e} mm2. The study's "
            f"3055 mm2 / 60.0 g is {-study_err:.2f} mm2 ({-100.0 * study_err / exact:.2f}%) low - the same "
            "arm-root slip as 2.1's first figure. The measured mesh "
            f"({measured:.2f} mm2, {report['measured']['mass_g']:.2f} g) is right for the shipped asset and is "
            f"lower than the exact outline because the ground bevel removes {bevel_removed:.2f} mm2-equivalent "
            f"and polygonisation {a['polygon_notch_chord_loss'] + a['polygon_hole_excess']:.2f} mm2. That the "
            "measured mesh lands near the study's number is a coincidence of two unrelated deficits, not a "
            "confirmation of the study's arithmetic."),
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
        "c8_max_deviation_mm": cn_deviation(obj, SPEC.points),
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
    # The probe runs after the .blend was saved and exported, and removes what it made.
    probe = bpy.data.objects.new("PROBE_EightPointHull", lod0.data.copy())
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
    """Eight-point-only report text: area check, originality, physics, engine pointer, gaps."""
    measured = report["measured"]
    check = area_check(report)
    report["area_check"] = check
    report["build_to"].update({
        "study_cross_check_mm2": STUDY_CROSS_CHECK_MM2, "study_cross_check_g": STUDY_CROSS_CHECK_G,
        "analytic_exact_mm2": check["analytic_exact_mm2"], "analytic_exact_g": check["analytic_exact_g"],
        "study_cross_check_note": (
            "SHURIKEN_STUDY.md 2.2's cross-check (50 mm tip, 10 mm arm, 22 mm hub, 35 deg = 3055 mm2, "
            f"60.0 g) is {abs(check['study_minus_exact_pct']):.2f}% low: the exact analytic area of that outline is "
            f"{check['analytic_exact_mm2']:.2f} mm2 ({check['analytic_exact_g']:.2f} g). See area_check. The "
            "measured plate area is lower again because the 0.75 mm ground facets remove material over the "
            "taper; the measured mass is the correctness check against the ~60 g target."),
    })
    hull = hull_check(report)
    report["hull_check"] = hull
    franchise = [c for c in report["qa"]["checks"] if c["name"] == "no_franchise_strings"]
    report["originality"] = {
        "basis": "historical happo-gata hira-shuriken, public domain (study 5)",
        "points": (f"8 plain single points, {SPEC.tip_included_deg:g} deg included - deliberately NOT the "
                   "three-tipped trident points of Royal Armouries XXVIM.21, which is a mass reference only"),
        "hole_mm": measured["hole_mm"],
        "hole": ("round centre hole, 9.5 mm minimum opening (study 2.2: the sourced retail typical) - not "
                 "XXVIM.21's small hole near the rim beside an engraved dragon's head; no engraving"),
        "arm_width_mm": measured["arm_width_mm"],
        "tip_taper": (f"{SPEC.tip_included_deg:g} deg included, ground over the last "
                      f"{measured['bevel_run_mm']:.1f} mm, ending in a {measured['tip_edge_height_mm']:.2f} mm "
                      "chisel edge"),
        "finish": ("blackened oxide, not flat grey: base colour (0.035, 0.034, 0.033) linear with bare steel "
                   "worn through on the points and the ground bevels - the coating loss on the points is the "
                   "wear XXVIM.21 records (study 2.2)"),
        "stamp": "none (study 5; any future mark must be an invented glyph)",
        "franchise_strings": (f"none in any object, mesh, material, texture or file name; qa_check "
                              f"no_franchise_strings passed on {sum(c['passed'] for c in franchise)} of "
                              f"{len(franchise)} objects"),
    }
    lod1_name = f"{SPEC.mesh_name}_LOD1"
    lod1 = report.get("lod1_is_distinct", {})
    dev1 = report["lod_surface_deviation_two_sided_mm"].get(lod1_name, {})
    topo = report.get("topology_quality", {})
    lod0_name = report["objects"][0]
    report["lod_choice"] = {
        "lod0": ("2 columns, 2 notch, 3 hole segments per wedge (24-gon hole), hub graded hole 24 -> ring 24 at "
                 "12.5 mm -> ring 32 on the arm-corner angles at 19.0 mm -> rim 48; 3 bevel segments, 2 straight, "
                 "4 taper, 2 tip intervals"),
        "lod1": ("1 column, 1 notch, 1 hole segment per wedge (8-gon), hub graded 8 -> ring 8 at 13 mm -> rim 24; "
                 "2 bevel segments, 1 straight, 1 taper, 1 tip interval (hand-spelled: study 4 halves the hole "
                 "ring and bevel segments; the rest is what carries no silhouette at LOD1's size)"),
        "lod2": "1 column, 1 notch, no bevel, no hole (study 4); hub fanned symmetrically from the axis",
        "topology_quality": {name: {k: q[k] for k in ("hub_aspect_median", "hub_aspect_max", "hub_mirror_misses",
                                                       "min_triangle_angle_deg", "triangles_under_5deg")}
                             for name, q in topo.items()},
        "previous_rev1": ("16-gon hole bridged 3:1 onto the 48-segment rim: hub aspect median 14.4, max 19.6, 32 of "
                          "48 hub faces over 8, every hub face chiral; taper in 2 intervals: 384 triangles under "
                          "5 deg (min 3.42 deg); LODs 1504 / 736 / 192"),
    }
    report["rev3_changes"] = [
        "Not a change list: SM_Shuriken_EightPoint was born on shuriken_lib 3.1 (library rev 3), so it never had "
        "the four-point's rev-2 Decimate LODs. Its own history is in maintenance_changes.",
    ]
    q0 = topo.get(lod0_name, {})
    report["maintenance_changes"] = [
        f"Revision 2. Hub topology: graded rings (LodSpec.hub_rings) instead of the 3:1 pinwheel fan - LOD0 hub "
        f"aspect median {q0.get('hub_aspect_median')}, max {q0.get('hub_aspect_max')}, "
        f"{q0.get('hub_mirror_misses')} mirror misses (rev 1: 14.4 / 19.6 / every face chiral).",
        f"24-gon hole on LOD0 (was 16: corners visible in the hero), measured "
        f"{measured['hole_across_flats_mm']} mm across the flats; LOD0 taper in 4 intervals, min triangle angle "
        f"{q0.get('min_triangle_angle_deg')} deg, {q0.get('triangles_under_5deg')} under 5 deg (rev 1: 3.42 deg, 384).",
        f"LODs {report['lod_triangles']} (rev 1: 1504 / 736 / 192), all in the study 4 bands. LOD1 differs from "
        f"LOD0 by {lod1.get('max_surface_deviation_mm')} mm two-sided: {dev1.get('two_sided_hub_and_hole')} mm in "
        f"the hub (8-gon), {dev1.get('two_sided_arms')} mm on the arms.",
        "LOD1/LOD2 UV0 now come from LOD0's islands (shuriken_lib.uv): one texture set serves every LOD "
        "(cross_lod_uv, uv_consistency).",
        "Textures: T_Shuriken_EightPoint_BC / _ORM / _N baked from M_Shuriken_Master (textures); the gallery "
        "beauty shots render from those maps only (render_gates.beauty_source).",
        f"LOD screen sizes {report.get('lod_screen_sizes')} (study 4's 1.0 / 0.5 / 0.25 switched to LOD2 at "
        "0.36 m); see lod_switching.",
        "measured.tip_included_deg is now fitted to the taper edges of all 8 arms (was copied from the spec); "
        "the bevel is reported in arm-local stations (bevel_start_arm_x_mm, bevel_full_size_arm_x_mm).",
        "engine_check is bound to the SHA-256 of the exported FBX and sidecar (UnrealCheck6).",
    ]
    report["fixes_applied"] = [
        "Inherited by construction, not re-fixed: every rev-2 four-point lesson is in the library - the plate "
        "and ground bevel are authored (no bmesh.ops.bevel clamping), every vertex goes through the 1 nm "
        "orbit-keyed factory and the hygiene gate refuses zero-length edges, zero-area faces and coincident "
        f"vertices before an object exists (measured here: {measured['zero_length_edges']} / "
        f"{measured['zero_area_faces']} / {measured['coincident_vertices']}).",
        f"Centre hole: circumscribed {measured['hole_segments']}-gon, {measured['hole_across_flats_mm']:.3f} mm "
        "across the flats (the true minimum opening), as the four-point.",
        f"Bevel: {SPEC.bevel_offset_mm} mm requested, {measured['bevel_offset_measured_mm']} mm measured on the "
        "finished mesh.",
        f"LOD screen sizes {report.get('lod_screen_sizes')} travel in the .sockets.json sidecar "
        "(pipeline.export_fbx lod_screen_sizes) and are applied by ue_import_sockets after import.",
        "Sockets are Empties through the sidecar (FBX sockets land at scale 100); the hull keys to the LOD0 "
        "node name (UCX_SM_Shuriken_EightPoint_LOD0_00).",
    ]
    report["known_gaps"] += [
        "Tip angle (35 deg) and arm width (10 mm) are study 2.2 modelling defaults chosen to reproduce the "
        "~60 g mass (study 2: no source publishes a tip angle); reference image A (Happo.JPG) was never "
        "downloaded, so the outline has not been checked against a photograph. Built to the study's numbers it "
        "reads as much a sprocket as a sun (44 mm hub, parallel-sided spokes); a 'sun' variant would taper the "
        "arms from the hub circle or raise the hub to 26-28 mm and re-fit the mass - a study decision.",
        "XXVIM.21, the best-measured eight-point, is only a mass reference: its trident points and rim hole "
        "are deliberately not reproduced. The shipped outline is the study's plain-point happo-gata.",
        "LOD2 has no hole by design (study 4), so its two-sided deviation is dominated by the filled 9.5 mm "
        "hole; at the pack's 0.035 switch (~2.5 m) the hole is ~3.6 px. Quote the arm-region figure for "
        "silhouette loss. LOD2's hub is a fan from the axis (symmetric, aspect ~12 on the notch triangles).",
        "The ground facet is a 0.75 mm convex round-over ending in a 1.0 mm square edge, the four-point's "
        "convention, not a flat grind to a thin edge: a pack-wide art call, left as is.",
    ]
    if (not isinstance(hull.get("c8_max_deviation_mm"), (int, float)) or hull["c8_max_deviation_mm"] > 1e-4
            or hull.get("lod0_max_outside_mm", 1.0) > 1e-6):
        report["known_gaps"].append(
            f"The UCX hull is not exactly C8 or does not enclose LOD0: {hull}.")
    probe = hull.get("pipeline_hull_for_comparison")
    probe_text = (f" (the pipeline hull, probed on this build: {probe['verts']} verts, {probe['c8_max_deviation_mm']} "
                  f"mm off C8, LOD0 up to {probe['lod0_max_outside_mm']} mm outside it)"
                  if isinstance(probe, dict) else "")
    report["known_gaps"].append(
        "The UCX hull is the 16-vertex tip prism (hull='tip_prism'), not the pipeline's decimated hull"
        f"{probe_text}. The prism is a flat 2.5 mm slab through the 8 tips: like any convex hull it spans "
        "the gaps between the points, and it stays full thickness over the ground facets, where the steel "
        "thins to the 1.0 mm chisel edge at each point (up to 0.75 mm proud per face at the tip). That is "
        "the conservative side for a thrown projectile; a stick-into-wall mechanic should trace from a tip "
        "(study 4), not rely on this hull.")


def _form():
    from shuriken_lib import Form  # needs bpy; SPEC above does not
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate, report_name="eight_point_report.json")


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


# --------------------------------------------------------------------------- CLI


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_eight_point.py", description=__doc__,
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
