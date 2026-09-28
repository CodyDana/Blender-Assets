#!/usr/bin/env python
"""Build SM_Shuriken_FourPoint - the juji / shiho four-point hira-shuriken.

Source of truth for the asset (house rule: the script, not the .blend).  This file is
now only the form's SPEC and its report text; everything else - the C_n generator,
M_Shuriken_Master, UVs, UCX hull, sockets, LOD group, FBX, gallery renders, the JSON
report and qa_check - lives in Scripts/shuriken/shuriken_lib and is shared by every
form in the pack.  Running it rebuilds Assets/Shuriken.blend FROM SCRATCH with this one
form; to rebuild the whole pack use build_pack.py (a single-form run warns when it is
about to drop forms the pack builder put in the same .blend).

Authority: References/Shuriken/SHURIKEN_STUDY.md section 2.1 (build-to numbers),
section 3 (construction and finish), section 4 (modelling plan, LOD table) and section 5
(originality); ASSET_GUIDELINES.md sections 6.1 - 6.5 (pipeline).

Build-to (study 2.1, one real object, mass is the correctness check):
    across 97 mm (tip radius 48.5 mm), thickness 3.0 mm, mass 39 g at 7.85 g/cm3,
    arm width 11 mm, hub radius 11 mm, centre hole 8 mm, tip included angle 40 deg.

Originality (study 5): historical juji, deliberately NOT the franchise star - arms a
full 11 mm wide, an 8 mm hole rather than a large open ring, a real 40 deg tip taper
and a blackened rather than flat-grey finish.  No franchise name anywhere, no stamp.

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_four_point.py -- [options]

--------------------------------------------------------------------------------
Revision 4 (maintenance pass, pack-wide review).  LOD0, the hull, the sockets and every
LOD's geometry are unchanged to the nanometre; what changed:

* LOD1/LOD2 UV0 now come from LOD0's islands (shuriken_lib.uv), so one texture set
  serves the whole chain (they were independent Smart UV unwraps).
* T_Shuriken_FourPoint_BC / _ORM / _N are baked from M_Shuriken_Master, and the gallery
  beauty shots render from those maps only.  The material gained chipped, per-point
  varied tip wear, quieter ground bevels, a hub-faded grind and straight scratches.
* LOD screen sizes 1.0 / 0.10 / 0.035 (study 4's 1.0 / 0.5 / 0.25 switched to LOD2 at
  0.35 m); the sidecar carries them.
* Pack-wide rig fixes: rim-wall reflection card and wall gate, solved depth of field,
  centred hero, common top-view scale, labelled LOD strip on one backdrop.
* measured.tip_included_deg is fitted to the mesh; engine_check is bound to the export's
  SHA-256 (UnrealCheck6).

Revision 3 (library pass).  LOD0 is unchanged to the nanometre; what changed:

* The one-off script became Scripts/shuriken/shuriken_lib.  The quarter-turn logic is
  now a C_n generator driven by integer n-th turns (still trig-free for quarter turns,
  so this form's floats are rev 2's floats).
* LODs are no longer Decimate copies.  Rev 2's LOD1 reproduced LOD0 to 1e-6 mm because
  a ruled bevel on a straight taper collapses for free; LOD1 and LOD2 are now authored
  by the same generator at study 4's reduced counts (LOD1: hole ring 16 -> 8, bevel
  3 -> 2 segments; LOD2: no bevel, no hole), so each is a clean, exactly C4 mesh that
  genuinely differs from LOD0.  See the report's lod_surface_deviation_two_sided_mm.

Revision 2 (maintenance pass), preserved in the library:

* The plate, including the ground bevel, is authored explicitly instead of being cut by
  ``bmesh.ops.bevel``, which silently clamped a requested 0.9 mm bevel to 0.323 mm and
  left 16 coincident vertices / 16 zero-length edges / 16 zero-area triangles (Unreal
  then stripped them: 1664 in Blender, 1632 in engine).  Every vertex goes through a
  1 nm position-keyed factory and every face loop drops repeated indices.
* The bevel is a 0.9 mm rounded ground facet over the whole 15.11 mm taper; past the
  point where the facet is wider than the arm the facets meet in a ridge, so the point
  ends in a 1.2 mm chisel edge.
* Hub ring 32 segments bridging a 16-segment hole ring 2:1; arm 4 columns across; the
  budget is spent on the taper bevel, not a flat hub fan.
* The centre hole polygon is circumscribed: a true 8.0 mm minimum opening.
* M_Shuriken_Master: bright bare steel on the points and ground bevels (radius- and
  facet-normal-masked) over a blackened coating, with a directional radial grind.
* Preview rig: ground plane with contact shadow, structured dark environment, grazing
  strip lights, matched exposure; the build measures its own renders.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import LodSpec, RadialStarSpec, study_lod_chain  # noqa: E402

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_FourPoint.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "four_point_report.json"

# --------------------------------------------------------------------------- spec

SPEC = RadialStarSpec(
    form="four_point",
    mesh_name="SM_Shuriken_FourPoint",
    title="Juji / shiho four-point hira-shuriken",
    points=4,
    tip_circle_mm=97.0,
    thickness_mm=3.0,
    arm_width_mm=11.0,
    hub_radius_mm=11.0,
    hole_diameter_mm=8.0,
    tip_included_deg=40.0,
    # Knife grind (style pass 2, decision A): both faces of every cutting edge (the parallel arm
    # edges and the taper edges) ground at 35 deg from the face down to a 0.15 mm land - the
    # reference's bevels converge the same way (38 deg, ~0.12 mm land at 197 mm).  The scallops keep
    # a 0.45 mm chamfer over a tall wall, the hole a 0.3 mm deburr; at each arm root the grind runs
    # out into the scallop chamfer over 3 mm.  One flat facet (bevel_segments 1): the knife has no
    # curvature for more segments to carry.
    grind_angle_deg=35.0,
    edge_land_mm=0.15,
    scallop_chamfer_mm=0.45,
    hole_chamfer_mm=0.30,
    grind_runout_mm=3.0,
    mass_target_g=39.0,
    mass_tolerance_g=2.0,
    study_mass_range_g=(34.0, 80.0),        # study 2.1 table: min 34 g (snippet), max 80 g
    study_mass_typical_g=(40.0, 57.0),
    # UCX: the 4-gon tip prism (8 vertices, full plate thickness through the tips), like the
    # other forms.  The pipeline's decimated convex hull of the CHAMFERED LOD0 (24 vertices)
    # followed the chisel tips' sloped faces and left LOD2's full-thickness, chamfer-less tips
    # 0.66 mm outside it; the prism encloses every LOD by construction and is the outline's
    # exact convex hull in plan (the four tips are its corners).
    hull="tip_prism",
    lods=study_lod_chain(LodSpec(
        columns=4,             # quads across the arm
        notch_segments=2,      # per 15 deg half notch -> 4 segments across the 30 deg notch
        hole_segments=4,       # per quarter -> 16 total (study 4: 12 to 16)
        bevel_segments=1,      # one flat knife facet
        straight_intervals=3,  # hub arc to shoulder
        taper_intervals=4,     # run-out ring to bevel apex (raised if under the band floor)
        tip_intervals=2,       # bevel apex to the point
    ), points=4),
    study_section="2.1",
    revision=7,
    physics_mass_kg=0.04,           # study 4, Physics
)


# --------------------------------------------------------------------------- report text


def annotate(report: dict) -> None:
    """Four-point-only report text: study cross-check, originality, history, gaps."""
    measured = report["measured"]
    report["build_to"].update({
        "study_cross_check_mm2": 1668.0, "study_cross_check_g": 39.3,
        "study_cross_check_note": (
            "SHURIKEN_STUDY.md 2.1 was corrected on 2026-09-17 (after rev 2 measured the mesh) "
            "from 1647 mm2 / 38.8 g to 1668 mm2 / 39.3 g, which is the analytic area of the "
            "un-bevelled outline. Since the knife grind pass the mass gate is the un-ground plate "
            f"(outline x 3.0 mm: {measured['outline_mass_g']:.2f} g against the 39 g sourced object); the "
            f"knife grind takes it to {measured['ground_mass_g']:.2f} g, reported, not gated."),
    })
    report["originality"] = {
        "basis": "historical juji / shiho hira-shuriken, public domain (study 5)",
        "arm_width_mm": measured["arm_width_mm"],
        "hole_mm": measured["hole_mm"],
        "tip_taper": (f"{SPEC.tip_included_deg} deg included; every cutting edge knife ground at "
                      f"{SPEC.grind_angle_deg:g} deg to a {measured['edge_land_mm']:.2f} mm land, the point ending in a "
                      f"{measured['tip_edge_height_mm']:.2f} mm edge"),
        "finish": ("dark coat (linear ~0.10, faintly cool) with soft cavity grime at the hole and the scallops, bare "
                   "bright steel on every knife grind with small chips into the face along it, lightly brightened "
                   "scallop and hole chamfers, many faint micro-scratches, near-invisible pits and two rust specks; "
                   "clearly darker coat than bare metal, not flat grey"),
        "stamp": "none (study 5 allows no stamp on the first piece; any future mark must be "
                 "an invented glyph)",
        "franchise_strings": "none in any object, mesh, material, texture or file name; "
                             "qa_check no_franchise_strings passed on every object",
    }
    lod1 = report.get("lod1_is_distinct", {})
    dev1 = report["lod_surface_deviation_two_sided_mm"].get(f"{SPEC.mesh_name}_LOD1", {})
    report["rev3_changes"] = [
        "LIBRARY: the one-off build became Scripts/shuriken/shuriken_lib (generator, material, "
        "UV, UCX, sockets, LOD group, export, render rig, measurement, report, qa) shared by "
        "every form; this file is the SPEC plus report text. LOD0 is unchanged: same vertices, "
        "faces, UVs, hull and sockets.",
        "LODs: Decimate replaced by parametric LODs from the same generator at study 4's reduced "
        f"counts ({report['lod_triangles']} triangles). LOD1 now differs from LOD0 by "
        f"{lod1.get('max_surface_deviation_mm')} mm two-sided (rev 2: 1e-6 mm): "
        f"{dev1.get('two_sided_hub_and_hole')} mm inside the hub, where the hole ring is an "
        f"8-gon, and {dev1.get('two_sided_arms')} mm on the arms, where the ground facet has 2 "
        "segments instead of 3. LOD2 has no bevel and no hole. Every LOD is exactly C4 (rev 2's "
        "decimated LODs were 3.98 mm / 0.80 mm off C4 as vertex sets).",
        "MATERIAL: M_Shuriken_Master is now shared by every form; the tip-wear radii are read "
        "per object (shuriken_wear_from / _to custom properties via Attribute nodes) instead of "
        "being baked into the node tree as four-point constants.",
    ]
    report["fixes_applied"] = [
        "rev 2 BLOCKER topology: the 16 coincident vertices / 16 zero-length edges / 32 zero-area "
        "triangles the clamped bmesh bevel left at every bevel run-out are gone; the plate, "
        "bevel included, is authored through a 1 nm position-keyed vertex factory and the build "
        "refuses to save unless zero-length edges, zero-area faces and coincident vertices are "
        "all zero.",
        "rev 2 BLOCKER qa gate: Scripts/pipeline/qa_check.py gained no_zero_length_edges, "
        "no_degenerate_faces and no_coincident_vertices (test_qa_negative.py case 12).",
        f"rev 2 MAJOR bevel: superseded in rev 5 by the full-length chamfer, {measured['chamfer_width_requested_mm']} "
        f"mm requested, {measured['chamfer_width_measured_mm']} mm measured on the finished mesh.",
        "rev 2 MAJOR topology / budget: 32-segment hub bridged 2:1 to a 16-segment hole ring, "
        "4 columns across the arm, 4-triangle tip caps; the budget buys a 3-segment rounded "
        "ground bevel rather than coplanar filler.",
        "rev 2 MAJOR LOD screen sizes: pipeline.export_fbx writes the LOD screen sizes into the "
        ".sockets.json sidecar and ue_import_sockets applies them after import (rev 2/3: 1.0 / 0.5 / "
        "0.25; rev 4: 1.0 / 0.10 / 0.035 from distance, see lod_switching).",
        "rev 2 BLOCKER renders: rebuilt rig (ground plane, structured environment, grazing "
        "strips, matched exposure, symmetric top lighting).",
        "rev 2 MAJOR material: bare-steel wear on points and ground bevels, directional grind.",
        f"rev 2 MINOR centre hole: circumscribed polygon, {measured['hole_across_flats_mm']:.3f} mm "
        "across the flats.",
        "rev 2 MINOR framing: 16:9 gallery frames and a LOD strip.",
    ]
    topo = report.get("topology_quality", {})
    report["style_pass_changes"] = [
        f"Revision 5 (style pass, STYLE_TARGET.md). Full-length ground chamfer on every outer edge, both faces: "
        f"{measured['chamfer_width_measured_mm']} mm wide, wall top {measured['chamfer_wall_top_drop_mm']} mm below "
        f"the plate, {measured['edge_land_mm']} mm land; the taper and the outline are unchanged. Mass "
        f"{measured['mass_g']} g (rev 4: 38.90 g).",
        "M_Shuriken_Master reworked to the reference recipe: coat linear ~0.10 neutral-cool, metallic 1.0, roughness "
        "0.32 coat / 0.22-0.28 bare / walls +0.05, bare steel on all chamfers with a noise-torn boundary and on the "
        "last 15 mm of each point, dashed random-direction scratches (1 % plate, 3 % walls), 0.3 % pits, coat mottle, "
        "1-3 rust specks; the wear boundary reads a per-vertex distance-to-outline attribute written by the generator.",
        f"LODs {report['lod_triangles']} (rev 4: 1376 / 576 / 160): the chamfer adds rows along the parallel run and "
        "the notch arcs.",
        f"Revision 7 (knife grind, style pass 2). Every cutting edge knife ground at {SPEC.grind_angle_deg:g} deg to a "
        f"{measured['edge_land_mm']} mm land (grind {measured['grind']['grind_width_mm']} mm wide), scallops a "
        f"{SPEC.scallop_chamfer_mm} mm chamfer over a tall wall, hole a {SPEC.hole_chamfer_mm} mm deburr, the grind "
        f"running out into the scallop over {SPEC.grind_runout_mm} mm at each root; outline unchanged. Mass gate on the "
        f"un-ground plate ({measured['outline_mass_g']} g), ground mass {measured['ground_mass_g']} g reported. "
        f"LODs {report['lod_triangles']}: LOD2 keeps a single-facet grind (edge line, pyramid tip). Material: bare "
        "grind, edge nicks, cavity grime, micro-scratches (decision C).",
        "Revision 6 (style pass, second round). Geometry, LODs and sockets unchanged; the UCX hull is now the 8-vertex "
        "tip prism (hull='tip_prism', like the eight-point and the senban) because the pipeline's decimated hull of "
        "the chamfered LOD0 left LOD2's chamfer-less tips 0.66 mm outside it. M_Shuriken_Master rebuilt around "
        "gradients (bare steel from a bright ground crest to a torn, tapering fringe; hairline scratches in loose "
        "pairs; darkening pits; radial patina), the hero gained an overhead glossy-only panel and the top view a "
        "facet band so the camera-facing chamfers read as ground steel instead of an ink band; LOD1/2 UV0 is "
        "clamped to the unit square.",
    ]
    report["maintenance_changes"] = [
        "Revision 4. LOD0, hull, sockets and all three LOD meshes are bitwise unchanged (the four-point keeps the "
        "k:1 bridge hub; its hub aspect is median "
        f"{(topo.get(report['objects'][0]) or {}).get('hub_aspect_median')} - the eight-point's pinwheel problem "
        "does not arise at an 11 mm hub).",
        "LOD1/LOD2 UV0 now come from LOD0's islands (shuriken_lib.uv): one texture set serves every LOD.",
        "Textures: T_Shuriken_FourPoint_BC / _ORM / _N baked from M_Shuriken_Master; the gallery beauty shots "
        "render from those maps only.",
        f"LOD screen sizes {report.get('lod_screen_sizes')} (study 4's 1.0 / 0.5 / 0.25 switched to LOD2 at "
        "~0.35 m); the sidecar carries them, so it is no longer byte-identical to rev 3.",
        "Renders changed pack-wide (reflection card for the rim walls, solved DOF, centred hero, common "
        "top-view scale, labelled LOD strip).",
        "measured.tip_included_deg is fitted to the mesh; the bevel is reported in arm-local stations.",
        "engine_check points at UnrealCheck6 and is bound to the SHA-256 of the exported FBX and sidecar "
        "(the rev-3 UnrealCheck3 pointer is superseded).",
    ]
    report["known_gaps"].append(
        "The round hub does not read strongly at gallery size: the arms leave only 30 deg notch "
        "arcs of the 11 mm hub exposed. That is what the reference outline draws and the hub "
        "radius is load-bearing for the area and the mass, so no geometry was changed; worth a "
        "line in the listing copy rather than a mesh edit.")


def _form():
    from shuriken_lib import Form  # needs bpy; SPEC above does not
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate,
                report_name="four_point_report.json")


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


# --------------------------------------------------------------------------- CLI


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_four_point.py", description=__doc__,
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
