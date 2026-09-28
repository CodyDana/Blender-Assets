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
import json
import sys
import time
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
    # Study 3: "Model the bevel as a short ground facet near each point and leave the long
    # edges square"; study 2.1: "Bevel only the last 15 mm of each arm".  The taper is
    # 15.111 mm long, so the facet covers exactly the taper and begins on the shoulder.
    # 0.9 + 0.9 of the 3.0 mm rim leaves a 1.2 mm flat between; 3 rounded segments are
    # what catches the highlight.
    bevel_offset_mm=0.9,
    bevel_runout_mm=1.2,
    mass_target_g=39.0,
    mass_tolerance_g=2.0,
    lods=study_lod_chain(LodSpec(
        columns=4,             # quads across the arm
        notch_segments=2,      # per 15 deg half notch -> 4 segments across the 30 deg notch
        hole_segments=4,       # per quarter -> 16 total (study 4: 12 to 16)
        bevel_segments=3,
        straight_intervals=3,  # hub arc to shoulder
        taper_intervals=4,     # run-out ring to bevel apex (raised if under the band floor)
        tip_intervals=2,       # bevel apex to the point
    ), points=4),
    study_section="2.1",
    revision=3,
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
            "un-bevelled outline. The measured plate area is lower because the 0.9 mm ground "
            "facets remove material over the taper; the measured mass is the correctness "
            "check against the 39 g sourced object."),
    })
    report["originality"] = {
        "basis": "historical juji / shiho hira-shuriken, public domain (study 5)",
        "arm_width_mm": measured["arm_width_mm"],
        "hole_mm": measured["hole_mm"],
        "tip_taper": f"{SPEC.tip_included_deg} deg included, ground over the last "
                     f"{measured['bevel_run_mm']:.1f} mm, ending in a "
                     f"{measured['tip_edge_height_mm']:.2f} mm chisel edge",
        "finish": ("blackened oxide, not flat grey: base colour (0.035, 0.034, 0.033) linear with "
                   "bare steel worn through on the points and the ground bevels"),
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
        f"rev 2 MAJOR bevel: {SPEC.bevel_offset_mm} mm requested, "
        f"{measured['bevel_offset_measured_mm']} mm measured on the finished mesh.",
        "rev 2 MAJOR topology / budget: 32-segment hub bridged 2:1 to a 16-segment hole ring, "
        "4 columns across the arm, 4-triangle tip caps; the budget buys a 3-segment rounded "
        "ground bevel rather than coplanar filler.",
        "rev 2 MAJOR LOD screen sizes: pipeline.export_fbx writes 1.0 / 0.5 / 0.25 into the "
        ".sockets.json sidecar and ue_import_sockets applies them after import.",
        "rev 2 BLOCKER renders: rebuilt rig (ground plane, structured environment, grazing "
        "strips, matched exposure, symmetric top lighting).",
        "rev 2 MAJOR material: bare-steel wear on points and ground bevels, directional grind.",
        f"rev 2 MINOR centre hole: circumscribed polygon, {measured['hole_across_flats_mm']:.3f} mm "
        "across the flats.",
        "rev 2 MINOR framing: 16:9 gallery frames and a LOD strip.",
    ]
    check_dir = PROJECT / "WorkFiles" / "shuriken" / "UnrealCheck3"
    report["engine_check"] = {
        "note": ("Pointer, not a claim about the file you are holding: re-run both passes after any "
                 "change to the mesh or the sidecar; pass 2 in a fresh process is the gate "
                 "(ASSET_GUIDELINES 6.5). Rev 3 runs in its own shuriken-only project "
                 "(UnrealShuriken/ShurikenValidation.uproject); the pass scripts read the Blender LOD "
                 "counts from this report. last_pass2 below is read from disk at build time and "
                 "matches_this_build compares it with this build's counts."),
        "project": str(PROJECT / "WorkFiles" / "shuriken" / "UnrealShuriken" / "ShurikenValidation.uproject"),
        "scripts": [str(check_dir / "pass1_import.py"), str(check_dir / "pass2_reload.py")],
        "evidence": [str(check_dir / "pass1.json"), str(check_dir / "pass2.json"),
                     str(check_dir / "pass1.log"), str(check_dir / "pass2.log")],
        "gates": ["engine LOD triangle counts equal the Blender counts exactly",
                  "LOD screen sizes read back as 1.0 / 0.5 / 0.25 in a fresh process",
                  "exactly one convex hull, both sockets at relative scale 1, bounds 9.7 x 9.7 "
                  "x 0.3 cm, zero Warning or Error lines in either commandlet log"],
    }
    try:
        pass2_path = check_dir / "pass2.json"
        pass2 = json.loads(pass2_path.read_text(encoding="utf-8"))
        report["engine_check"]["last_pass2"] = {
            "file_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(pass2_path.stat().st_mtime)),
            "engine": pass2.get("engine"),
            "lod_triangles": pass2.get("lod_triangles"),
            "triangle_delta": pass2.get("triangle_delta"),
            "lod_screen_sizes": pass2.get("lod_screen_sizes"),
            "convex_hulls": pass2.get("convex_hulls"),
            "size_cm": pass2.get("size_cm"),
            "sockets": [(s["name"], s["scale"]) for s in pass2.get("sockets", [])],
        }
        report["engine_check"]["matches_this_build"] = pass2.get("lod_triangles") == report["lod_triangles"]
    except (OSError, ValueError, KeyError) as exc:
        report["engine_check"]["last_pass2"] = f"not available: {type(exc).__name__}: {exc}"
        report["engine_check"]["matches_this_build"] = False
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
