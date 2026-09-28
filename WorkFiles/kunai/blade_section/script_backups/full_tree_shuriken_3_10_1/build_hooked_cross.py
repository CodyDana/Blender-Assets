#!/usr/bin/env python
"""Build SM_Shuriken_HookedCross - the hooked cross, the photo-matched swept-blade outline (user's choice B).

Source of truth for the asset (house rule: the script, not the .blend).  This file is the form's SPEC and its
report text; the outline-plate generator, its measurement, the handedness gate and the FormGeometry hook live in
Scripts/shuriken/shuriken_lib/outline_plate.py (+ outline_spec.py), and everything else - M_Shuriken_Master, UVs,
UCX hull, sockets, LOD group, FBX, bake, gallery, JSON report, qa_check - is the pack's shared path
(shuriken_lib.pack).  It plugs in through ``Form(geometry=OutlinePlateGeometry(SPEC))``.

Authority: References/Shuriken/SHURIKEN_STUDY.md section 2.6 (the form, the back-face note, the handedness gate),
sections 3-5; WorkFiles/shuriken/photo_study/PHOTO_MEASUREMENT.md section 2.5 (the outline recipe the user chose);
the verification outline WorkFiles/shuriken/photo_study/synthesis/photo_matched_outlines_mm.json (1460 points, mm)
is used ONLY to verify (Hausdorff distance and IoU in the report), never to build.  Names: HookedCross only
(study 5); nothing in any object, material, texture or file name carries the historical name.

Build-to (100 mm tip to tip; photo proportions at the study's ESTIMATE size and plate):
    arm half-width 5.62 mm - 0.0397 u (2.275 deg per edge, 4.55 deg included), u along the arm;
    hook inner corner on the leading edge at u = 34.41 mm; the inner edge runs from it straight to the tip at
    r = 50 mm, 35.0 deg COUNTER-clockwise of the arm axis (74.99 deg to the arm; the recipe's 75.05 is the photo
    measurement, the corner and the tip fix the line); the arm end and the hook back are ONE convex arc of R 98 mm
    crossing the arm axis at 41.46 mm (from the elbow on the trailing edge to the tip); concave corners (the four
    junctions round the centre square, the four hook corners) filleted 0.56 mm; the elbows and the tips sharp;
    no centre hole; plate 2.5 mm (study ESTIMATE); outline 1890.05 mm2 -> 37.09 g at 7.85 g/cm3.

Handedness (study 2.6).  The presented face is +Z and reads as the left-facing hooked cross: in the Blender top
view the arm along +X hooks toward +Y, the arm along +Y toward -X.  Nothing in the path mirrors (no Mirror
modifier, no negative scale, the generator's only reflection is z -> -z); ``handedness_gate`` checks every LOD on
every build and the build FAILS on the wrong handedness; ``handedness_negative_control`` proves the gate catches the
mirrored outline.  Every gallery image looks down on +Z.  The back face of any flat plate of this outline reads as
the mirrored form - physics, not a defect, and the user's release-time decision (study 2.6, 5).

Revision 2 (library 3.9.1, maintenance after the geometry / Unreal / visual reviews): the texture sheets' -Z plate island
is mirrored in U before the packer, so both plate islands of T_Shuriken_HookedCross_BC / _ORM / _N read as the
presented face (form gate texture_sheets_read_plus_z + its negative control); LOD0's blade run-outs are eased over 4
intervals and the polished band narrows to a line through them (no bright cap, no plunge highlight); LOD2's sharp
concave corners are hard edges and its taller walls map inside LOD0's wall islands; the LOD close-up's lamps follow its
turned camera; usage_warnings in the report (never mirror or negative-scale the mesh).

HEADLESS ONLY:
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate,six_point,spike,hooked_cross
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib.outline_spec import HookedCrossSpec, OutlineLodSpec  # noqa: E402
from shuriken_lib.spec import MM, scaled_lod_screen_sizes  # noqa: E402

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_HookedCross.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "hooked_cross_report.json"
PHOTO_OUTLINE = PROJECT / "WorkFiles" / "shuriken" / "photo_study" / "synthesis" / "photo_matched_outlines_mm.json"
PHOTO_AREA_MM2 = 1890.03

# --------------------------------------------------------------------------- LODs
# LOD0: 8 arm stations (3.5 mm), the back arc in 2 + 4 + 4 + 3 chords (max chord sagitta ~0.02 mm on R 98), the
# blade matched on both edges (4 intervals) so the hook plate is a strip, 3 ridge intervals, 2 chords per half
# junction fillet, 3 on the hook-corner fillet.  3.9.1 (visual review): each 3 mm blade run-out is 4 intervals on a
# smoothstep (runout_ease), so the grind leaves the knife facet and meets the chamfer tangentially - a smooth twisted
# plunge instead of one flat facet tilted ~13 deg along the edge (+192 triangles)
_LOD0 = OutlineLodSpec(arm_intervals=8, end_intervals=2, arm_end_intervals=2, runout_intervals=4, runout_ease=True,
                       hook_intervals=4, roof_intervals=3, junction_fillet_segments=2, hook_fillet_segments=3,
                       end_axis_points=2, seam_points=2, band=(0, 2500),
                       note="LOD0: full silhouette, knife grind with its land on the hook blades (eased 4-interval "
                            "run-outs), 0.45 mm chamfers and 0.56 mm fillets elsewhere")
# LOD1 (~0.89 m, ~1 px/mm): stations and blade columns halved; the grind keeps its land, the chamfers stay, the
# fillets are one chord each.
_LOD1 = OutlineLodSpec(arm_intervals=4, end_intervals=1, arm_end_intervals=1, runout_intervals=1, hook_intervals=2,
                       roof_intervals=1, junction_fillet_segments=1, hook_fillet_segments=1, end_axis_points=1,
                       seam_points=1, band=(0, 900),
                       note="LOD1: columns halved, knife grind + land and chamfers kept, one-chord fillets")
# LOD2 (~2.54 m, ~0.38 px/mm): a single-facet knife grind whose facets meet in an edge line (land 0), square
# non-cutting edges (a 0.45 mm chamfer is 0.17 px there), sharp concave corners (0.56 mm fillets: 0.2 px).
_LOD2 = OutlineLodSpec(arm_intervals=1, end_intervals=1, arm_end_intervals=1, runout_intervals=1, hook_intervals=1,
                       roof_intervals=1, junction_fillet_segments=0, hook_fillet_segments=0, chamfer=False,
                       knife_land=False, end_axis_points=1, hook_points=False, seam_points=1, band=(0, 250),
                       note="LOD2: single-facet grind to an edge line, square non-cutting edges, sharp concave corners")

SPEC = HookedCrossSpec(
    form="hooked_cross",
    mesh_name="SM_Shuriken_HookedCross",
    title="Hooked cross hira-shuriken (photo-matched swept-blade outline)",
    thickness_mm=2.5,
    arm_half_width_mm=5.62,
    taper_per_edge_deg=2.275,
    hook_corner_u_mm=34.41,
    tip_radius_mm=50.0,
    tip_offset_deg=35.0,
    back_arc_radius_mm=98.0,
    back_arc_axis_mm=41.46,
    fillet_mm=0.56,
    mass_target_g=37.09,                  # the photo outline at 2.5 mm (PHOTO_MEASUREMENT 2.5); no sourced mass exists
    mass_tolerance_g=2.0,
    lods=(_LOD0, _LOD1, _LOD2),
    grind_angle_deg=35.0,
    edge_land_mm=0.15,
    chamfer_mm=0.45,
    runout_mm=3.0,
    study_section="2.6",
    revision=2,
    physics_mass_kg=0.06,                 # study 4's table (placeholder outline); the override follows the ground mass
    lod_screen_sizes=scaled_lod_screen_sizes(50.0),
    # grind extent: the whole blade (None = the chamfer resumes where the blade meets the arm: the shoulder on the back
    # arc, the hook-corner fillet on the inner edge); chosen against the photo-length alternative (20 mm from the tip)
    # on WorkFiles/shuriken/hooked_cross/grind_extent_compare.png
    back_grind_end_mm=None,
    inner_grind_end_mm=None,
    # the hero turns the plate 40 deg about Z (camera, lamps and floor unchanged; the top view is never turned):
    # at 0 deg a hook blade and its floor shadow sit on two of the pack's backdrop points (r50, q78) and the camera-
    # facing arm walls pull the hero mean to -0.052 of the anchor; 40 deg clears both (scratch sweep 0/20/40/60/75)
    hero_yaw_deg=40.0,
)


# --------------------------------------------------------------------------- verification against the photo outline


def _poly_area(p):
    x, y = p[:, 0], p[:, 1]
    import numpy as np
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _hausdorff(a, b):
    """Symmetric Hausdorff distance between two closed polylines (every vertex to the other's segments)."""
    import numpy as np
    from shuriken_lib.geometry import segment_distance
    da = segment_distance(a, b, np.roll(b, -1, axis=0), chunk=128)
    db = segment_distance(b, a, np.roll(a, -1, axis=0), chunk=128)
    return float(max(da.max(), db.max())), float(da.max()), float(db.max())


def _row_intervals(poly, y):
    import numpy as np
    x0, y0 = poly[:, 0], poly[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    cross = ((y0 <= y) & (y1 > y)) | ((y1 <= y) & (y0 > y))
    xs = np.sort(x0[cross] + (y - y0[cross]) * (x1[cross] - x0[cross]) / (y1[cross] - y0[cross]))
    return list(zip(xs[0::2], xs[1::2]))


def _iou(a, b, step=0.005):
    """Intersection over union of two simple polygons (mm), exact per scan row, rows every ``step`` mm."""
    import numpy as np
    lo = min(a[:, 1].min(), b[:, 1].min())
    hi = max(a[:, 1].max(), b[:, 1].max())
    inter = union = 0.0
    for y in np.arange(lo + 0.5 * step, hi, step):
        ia, ib = _row_intervals(a, y), _row_intervals(b, y)
        la = sum(q - p for p, q in ia)
        lb = sum(q - p for p, q in ib)
        li = 0.0
        for p, q in ia:
            for r, s in ib:
                li += max(0.0, min(q, s) - max(p, r))
        inter += li
        union += la + lb - li
    return inter / union if union > 0 else None


def photo_check(report: dict) -> dict:
    """The analytic outline and LOD0's polygonised outline against the photo outline JSON (verification only)."""
    import numpy as np
    import bpy
    data = json.loads(PHOTO_OUTLINE.read_text(encoding="utf-8"))["manji"]
    ref = np.array(data["outer"], dtype=np.float64)
    o = SPEC.outline()
    exact = np.array(o.dense_contour(0.02 * MM), dtype=np.float64) / MM
    runs = o.columns(SPEC.lods[0])
    pts = []
    for run in runs:
        for c in run.columns:
            p = (c.x / MM, c.y / MM)
            if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-9:
                pts.append(p)
    wedge = np.array(pts[:-1])
    lod0_poly = np.concatenate([wedge @ np.array([[math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)],
                                                 [-math.sin(k * math.pi / 2), math.cos(k * math.pi / 2)]])
                                for k in range(4)])
    # every polygon corner must be a vertex of the finished LOD0 (the polygon IS the mesh's outline)
    obj = bpy.data.objects.get(report["objects"][0])
    co = np.array([v.co[:2] for v in obj.data.vertices], dtype=np.float64) / MM
    miss = max(float(np.min(np.hypot(co[:, 0] - x, co[:, 1] - y))) for x, y in lod0_poly)
    h_exact = _hausdorff(exact, ref)
    h_lod0 = _hausdorff(lod0_poly, ref)
    return {
        "reference": str(PHOTO_OUTLINE), "reference_points": int(len(ref)),
        "reference_area_mm2": round(_poly_area(ref), 4), "stated_area_mm2": PHOTO_AREA_MM2,
        "analytic_outline": {"area_mm2": round(_poly_area(exact), 4),
                             "area_vs_1890_03_mm2": round(_poly_area(exact) - PHOTO_AREA_MM2, 4),
                             "hausdorff_mm": round(h_exact[0], 5), "max_analytic_to_ref_mm": round(h_exact[1], 5),
                             "max_ref_to_analytic_mm": round(h_exact[2], 5), "iou": round(_iou(exact, ref), 6)},
        "lod0_outline_polygon": {"corners": int(len(lod0_poly)), "area_mm2": round(_poly_area(lod0_poly), 4),
                                 "hausdorff_mm": round(h_lod0[0], 5), "iou": round(_iou(lod0_poly, ref), 6),
                                 "corners_on_mesh_max_miss_mm": round(miss, 7)},
        "reading": ("the reference is the reconciled photo outline densified every 0.5 mm; its elbows carry the "
                    "reconciler's 0.18 mm round where the recipe (and this build) keeps them sharp, so the Hausdorff "
                    "distance is dominated by the elbows and the 0.5 mm chords of the 0.56 mm fillets"),
    }


# --------------------------------------------------------------------------- report text


def annotate(report: dict) -> None:
    import bpy
    from shuriken_lib.outline_plate import handedness_gate, handedness_negative_control, texture_handedness

    o = SPEC.outline()
    lods = [bpy.data.objects.get(name) for name in report["objects"]]
    gates = {obj.name: handedness_gate(obj, o) for obj in lods}
    control = handedness_negative_control(lods[0], o)
    texture = texture_handedness(lods, o)
    report["handedness"] = {
        "rule": ("study 2.6: in the Blender top view (+Z toward the viewer, X right, Y up) the hook on the arm along +Y "
                 "lies at negative X and the hook on the arm along +X at positive Y; presented face +Z"),
        "gate": gates,
        "passed": all(g["passed"] for g in gates.values()),
        "negative_control": control,
        "no_mirror_in_the_path": ("outline_plate authors each wedge by exact quarter turns (spec.rotate); its only "
                                  "reflection is z -> -z for the bottom face; no Mirror modifier, no negative scale, "
                                  "every object's matrix is the identity (qa_check transforms_applied)"),
        "back_face": ("the -Z face of this (or any) flat plate reads as the mirrored form - physics, accepted; whether "
                      "to ship the form is the user's release-time decision (study 2.6, 5)"),
    }
    ok = bool(report["handedness"]["passed"] and control.get("caught"))
    report["form_gates"] = {"handedness": ok, "handedness_negative_control_caught": bool(control.get("caught"))}
    if not ok:
        report["known_gaps"].append("HANDEDNESS GATE FAILED: " + json.dumps(
            {name: g["checks"] for name, g in gates.items()}))
    # 3.9.1 (visual review, major): the texture sheets.  Smart UV mapped the underside's island as seen from below, so
    # T_Shuriken_HookedCross_BC / _ORM / _N carried the mirrored form as a flat picture; the -Z islands are now mirrored
    # in U before the packer (OutlinePlateGeometry.uv_mirror_underside) and this gate reads every plate island
    report["texture_handedness"] = texture
    report["form_gates"]["texture_sheets_read_plus_z"] = bool(texture["passed"])
    report["form_gates"]["texture_negative_control_caught"] = bool(texture["negative_control"]["caught"])
    if not texture["passed"]:
        report["known_gaps"].append("TEXTURE HANDEDNESS GATE FAILED: " + json.dumps(texture["lod0_islands"]))
    report["photo_check"] = photo_check(report)
    report["gallery_presented_face"] = gallery_check(report)
    report["form_gates"]["gallery_shows_plus_z"] = bool(report["gallery_presented_face"]["passed"])
    report["physics_note"] = (f"Mass in KG override {report['physics']['mass_kg_override']} kg (the knife-ground LOD0; "
                              "study 4's 0.06 kg was derived from the placeholder outline).")
    _decisions(report)


GRIND_DECISION = {
    "question": ("which edges of the hook blade are knife ground, and how far (the user: both edges that converge at the "
                 "tip, the grind fading out cleanly where the blade meets the arm; the photo shows a ground facet on the "
                 "hook back near the tip, 0.7 mm wide and ~17 mm long, PHOTO_MEASUREMENT section 6)"),
    "decision": ("A, the whole blade: the back arc knife ground from the tip to 3 mm above the SHOULDER (where the arm's "
                 "leading-edge line meets the arc, i.e. where the hook leaves the arm) and running out into the 0.45 mm "
                 "chamfer exactly at the shoulder; the inner edge knife ground from the tip to 3 mm before the hook-corner "
                 "fillet and running out into the chamfer exactly at the fillet's tangent point (a wheel cannot grind into "
                 "a concave corner: the stars' root run-out)"),
    "rejected": ("B, the photo length: the grind 17-20 mm from the tip + 3 mm run-out. Rendered side by side through the "
                 "rig's hero lights (WorkFiles/shuriken/hooked_cross/grind_extent_compare.png), B leaves a blunt 2-5 mm "
                 "stretch of blade at the hook root that reads as a manufacturing flaw, not a grind; A reads as one ground "
                 "blade whose facet fades where the arm begins, like every star's grind at its root"),
    "photo_consistency": ("the photo's facet sits on the hook back near the tip, inside A's ground length; one face of "
                          "one piece is visible, so the far face and the inner edge are unknown - both faces are ground "
                          "(a thrown plate is symmetric), as on every pack form"),
    "not_ground": ("the arm edges, the arm end on the back arc (elbow to shoulder), the junction and hook-corner fillets: "
                   "0.45 mm chamfer at 35 deg over a 1.87 mm wall (the stars' scallop treatment)"),
    "run_out_look": ("3.9.1 (visual review: each band kept its full width and stopped in a bright square cap, the run-out "
                     "read as plate grey, and in the hero each run-out showed a bright triangular plunge facet like a "
                     "chip).  The extent (A) is unchanged.  Geometry: each 3 mm run-out on LOD0 is 4 intervals on a "
                     "smoothstep (OutlineLodSpec.runout_ease), one smooth class, so the grind leaves the knife facet and "
                     "meets the chamfer tangentially instead of as one flat facet tilted ~13 deg along the edge.  "
                     "Material (M_Shuriken_Master run-out taper mode): the 0.7 mm polished band narrows over the last "
                     "1.5 mm of the full knife to a 0.12 mm line, which runs on along the run-out's edge, narrowing "
                     "with the grind, into the chamfer line; the land highlight fades over the same 1.5 mm.  The cap "
                     "was polish on the tilted run-out facet (it mirrors the lamps), so no wide polish lands there now.  "
                     "Before / after: WorkFiles/shuriken/hooked_cross_maint/runout_compare.png"),
}

HERO_DECISION = ("The hero turns the plate 40 deg about Z (hero_yaw_deg; the camera, lamps and floor are the pack's, and the "
                 "top view is never turned). Swept at 0 / 20 / 40 / 60 / 75 deg on scratch builds: at 0 deg a hook blade "
                 "and its floor shadow cover two of the pack's backdrop points (r50, q78) and the camera-facing arm walls "
                 "pull the hero mean to -0.052 of the anchor (tolerance 0.05); 40 deg clears every backdrop point and "
                 "puts the arms on the diagonals like the stars' heroes; 60 deg passes too but crowds the right edge.")

MATERIAL_DECISION = ("M_Shuriken_Master cavity mode (library 3.9): on this form nearly the whole outline is a non-cutting edge, "
                     "and the stars' cavity terms (grime boost, 0.2 mm x 2.6 mm dish) keyed to the non-cutting-edge "
                     "distance pillowed every 8-11 mm arm (hero coat mean 0.518 vs the stars' 0.547-0.553). The object now "
                     "reads its cavity terms from the distance to its CONCAVE corners (shuriken_cavity: the four junction "
                     "fillets round the centre square and the four hook corners - what the stars' notch arcs are), while the "
                     "non-cutting-edge distance still classifies the small chamfers. The switch is one Mix with the object's "
                     "shuriken_cavity_mode as factor: a CPU bake of all five frozen forms with the 3.8.1 and 3.9 materials is "
                     "bit-identical (WorkFiles/shuriken/hooked_cross/material_noop_check.json).")


def _decisions(report: dict) -> None:
    m = report["measured"]
    derived = report["build_to"]["derived"]
    report["grind_decision"] = dict(GRIND_DECISION)
    report["hero_decision"] = HERO_DECISION
    report["material_decision"] = MATERIAL_DECISION
    report["recipe_vs_build"] = {
        "tip_to_tip_mm": {"recipe": 100.0, "measured": m["tip_to_tip_mm"]},
        "arm_half_width": {"recipe": "5.62 - 0.0397 u mm (4.53 deg included in the recipe text; 2.275 deg per edge in "
                                     "the reconciler that drew the verification outline)",
                           "measured_widths_mm": m["arm_widths_mm"]},
        "hook_corner_u_mm": {"recipe": 34.41, "built": derived["hook_corner_mm"][0]},
        "inner_edge_deg": {"recipe": 75.05, "measured": m["inner_edge_deg_to_arm"],
                           "note": ("the corner (u 34.41 on the tapered leading edge) and the tip (r 50, 35.0 deg) fix the "
                                    "line: 74.99 deg; 75.05 is the photo measurement the reconciler reported (0.06 deg = "
                                    "0.026 mm over the 25.3 mm edge)")},
        "tip": {"recipe": "r 50 mm, 35.0 deg ccw of the arm", "measured_radius_mm": m["tip_radius_mm"],
                "measured_deg": m["tip_angle_deg_ccw_of_arm"]},
        "back_arc": {"recipe": "R 98 mm crossing the arm axis at 41.46 mm", "measured": m["back_arc_fit"]},
        "fillets_mm": {"recipe": 0.56, "measured": m["fillets"]},
        "convex_corners_and_tips": "sharp (the tip ends in the 0.15 mm vertical land edge; sharp in plan)",
        "hole": "none",
        "area_mm2": {"recipe_json": PHOTO_AREA_MM2, "analytic": m["analytic_area_mm2"],
                     "lod0_polygon_unground": m["outline_plate_area_mm2"]},
    }
    report["originality"] = {
        "basis": ("a generic hooked-cross hira-shuriken, the photo-matched outline of a public-domain scan "
                  "(References/Shuriken/images, provenance.json) at the study's estimate size; study 2.6 provenance: a "
                  "1960s television prop form of a generic Buddhist symbol, owned by nobody"),
        "names": ("HookedCross only: SM_Shuriken_HookedCross, T_Shuriken_HookedCross_*, hooked_cross; no historical "
                  "name, maker, retailer or franchise string in any object, material, texture or file (study 5; qa_check "
                  "no_franchise_strings)"),
        "storefront": ("study 5: list as 'Hooked Cross Star', provenance in the body text, be ready to drop the form if "
                       "moderation objects; the back face reads as the mirrored form - a release-time decision for the "
                       "user, not made here"),
    }
    topo = report.get("topology_quality", {})
    report["lod_choice"] = {
        "lod0": _LOD0.note, "lod1": _LOD1.note, "lod2": _LOD2.note,
        "triangles": report["lod_triangles"],
        "bands": ("ceilings only (2500 / 900 / 250): study 4's floors are for stars and nothing is padded; the counts are "
                  "what a flat polygon plate with these columns needs (the pack's stars run 1232-1536 / 576-672 / 228-240)"),
        "screen_sizes": (f"{report.get('lod_screen_sizes')}: the tips sit at r = 50 mm, the pack's reference radius, so the "
                         "pack's 1.0 / 0.10 / 0.035 are already scaled - switches at ~0.89 m and ~2.54 m"),
        "lod2": ("square non-cutting edges (a 0.45 mm chamfer is 0.17 px at 2.54 m) and sharp concave corners (0.56 mm "
                 "fillets: 0.2 px); the blade keeps a single-facet knife grind to an edge line (land 0), like every star's "
                 "LOD2"),
        "topology_quality": {name: {k: q.get(k) for k in ("plate_aspect_median", "plate_aspect_max",
                                                           "plate_min_triangle_angle_deg", "min_triangle_angle_deg",
                                                           "plate_triangles_under_15deg", "strip_triangles_under_5deg")}
                             for name, q in topo.items()},
    }
    report["known_gaps"] += [
        "No sourced size, thickness or mass exists for this form: 100 mm and 2.5 mm are the study's ESTIMATEs; the outline "
        "mass gate (37.09 g +-2) is self-consistency with the photo outline at that plate, not a sourced mass.",
        "The back (-Z) face reads as the mirrored form - true of any flat plate of this outline (study 2.6). Every gallery "
        "image shows +Z; whether the pack ships the form is the user's release-time decision (study 5).",
        f"Physics: the Mass in KG override is the ground mass {report['physics']['mass_kg_override']} kg, not study 4's "
        "0.06 kg (derived from the placeholder outline, 60 % more area).",
        "The inner edge is 74.99 deg to the arm (fixed by the recipe's corner and tip), the recipe text says 75.05 (the "
        "photo measurement); 0.026 mm over the edge.",
        "The verification outline's elbows carry the reconciler's 0.18 mm round and its fillets are 0.5 mm chords; the "
        f"build keeps the elbows sharp as the recipe says: Hausdorff {report['photo_check']['analytic_outline']['hausdorff_mm']} "
        f"mm, IoU {report['photo_check']['analytic_outline']['iou']} (analytic outline vs the JSON).",
        f"UV0 covers {100.0 * report['uv']['uv_square_coverage']:.1f} % of the square (Smart UV + one planar island per "
        "wall piece, the -Z island mirrored in U before the packer); the stars reach 26-32 %.",
        "The mesh is chiral and nothing in the asset can stop a user from mirroring it: Unreal builds a reversed index "
        "buffer on every LOD (build_reversed_index_buffer, UE's default), so a StaticMeshComponent placed with an odd "
        "negative scale renders a correctly lit mirror image with no warning. The Fab description and the game "
        "documentation must say: never mirror or negative-scale SM_Shuriken_HookedCross (see usage_warnings); in the "
        "game, an editor data-validation rule or a construction-script check should flag a negative-determinant "
        "component transform on anything that uses it.",
        "The underside's texture island is mirrored in U (so the texture sheets read as the presented face): its UV "
        "triangles have the opposite winding to their faces, i.e. a mirrored UV shell. That is ordinary for a tangent-"
        "space normal map (MikkTSpace in Blender's bake and in Unreal carries the bitangent sign), but a tool that flags "
        f"'flipped UVs' will list the {((report.get('uv_wall_islands') or {}).get('mirror_underside') or {}).get('mirrored_faces')} "
        "-Z-facing LOD0 faces; it is deliberate (texture_handedness).",
    ]
    report["usage_warnings"] = {
        "never_mirror": ("Never mirror SM_Shuriken_HookedCross or place it with a negative (odd-signed) scale: the mirror "
                         "image is the form the pack must never show (study 2.6), and Unreal renders it without a warning "
                         "because every LOD builds a reversed index buffer. Rotate it; never scale it by -1."),
        "presented_face": ("The +Z face is the presented face (left-facing); the -Z face reads as the mirrored form by "
                           "physics - keep thumbnails, marketing shots and in-game close-ups on the +Z side."),
        "for_the_fab_description": "Repeat both lines in the listing's technical notes if the form ships.",
        "game_side_check": ("Suggested for the user's game: an Editor Utility / Data Validation rule that fails when a "
                            "StaticMeshComponent using SM_Shuriken_HookedCross has a world transform with a negative "
                            "determinant (the reviewer's Unreal pass: UnrealCheck11_HookedCrossVerify/u6_renderdata.json)."),
    }
    report["uv_notes"] = {"island_map_deviation_px_at_2048": (report.get("uv_consistency") or {}).get(
        "island_map_deviation_px_at_2048"), "note": ("3.9.1: LOD2's square non-cutting walls are taller than LOD0's (2.5 vs "
                                                     "1.87 mm); their corners are clamped onto LOD0's wall islands "
                                                     "(uv.transfer_uvs clamp_walls), so the island-map deviation is that "
                                                     "compression (information) and no LOD2 UV reaches past LOD0's "
                                                     "border margin; the gated figures are cross_lod_uv (top plate 0.5 "
                                                     "px, surface 8 px)"),
                          "texture_sheets": ("3.9.1: the -Z plate island is mirrored in U before the packer, so both "
                                             "plate islands of T_Shuriken_HookedCross_BC / _ORM / _N read as the "
                                             "presented +Z face (texture_handedness)")}


def gallery_check(report: dict) -> dict:
    """Every gallery shot shows the +Z face: the rig's camera record, and the rendered masks read as the left-facing
    form in image space (with a left-right flip of each mask as the negative control, which must fail)."""
    from pathlib import Path as _P
    from shuriken_lib.outline_plate import handedness_from_mask, handedness_of_strip
    rig = report.get("render_rig") or {}
    face = rig.get("presented_face_check")
    if not face:
        return {"passed": False, "detail": "no renders (or no presented-face record)"}
    o = SPEC.outline()
    masks = face.get("masks", {})
    out = {"camera_record": {k: v.get("sees") if v else None for k, v in face["shots"].items()},
           "cameras_all_plus_z": all(v and v.get("sees") == "+Z" for v in face["shots"].values()), "image": {}}
    top_px = rig.get("top_px_per_mm")
    lod_px = rig.get("lod_strip_px_per_mm")
    for name, path in masks.items():
        if not _P(path).exists():
            out["image"][name] = {"passed": False, "detail": f"missing {path}"}
            continue
        if name.endswith("_lods"):
            res = handedness_of_strip(path, lod_px, o, len(report["objects"]))
            neg = handedness_of_strip(path, lod_px, o, len(report["objects"]), flip=True)
        elif name.endswith(("_top", "_wire")):
            from shuriken_lib.render import load_pixels
            h, w = load_pixels(path).shape[:2]
            res = handedness_from_mask(path, top_px, o, centre_px=(0.5 * w, 0.5 * h))
            neg = handedness_from_mask(path, top_px, o, centre_px=(0.5 * w, 0.5 * h), flip=True)
        else:
            continue                      # the perspective hero: the camera record is the proof (see note)
        out["image"][name] = {"passed": res["passed"], "negative_control_flipped_image_failed": not neg["passed"],
                              "arms": res.get("arms") or [p.get("arms") for p in res.get("panels", [])]}
    out["passed"] = bool(out["cameras_all_plus_z"] and out["image"] and all(
        v.get("passed") and v.get("negative_control_flipped_image_failed") for v in out["image"].values()))
    out["note"] = ("top / wire / LOD strip: straight-down ortho views, read from their own masks in image space (x right = "
                   "+X, up = +Y only when the camera looks down on +Z); hero and LOD close-up: perspective cameras, each "
                   "above the plate with its view pointing down (render.camera_side), so every ray meets the +Z face "
                   "first - a plate viewed from its +Z side keeps its handedness under any such projection")
    return out


def _form():
    from shuriken_lib import Form
    from shuriken_lib.outline_plate import OutlinePlateGeometry
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate, report_name="hooked_cross_report.json",
                geometry=OutlinePlateGeometry(SPEC))


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_hooked_cross.py", description=__doc__,
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
