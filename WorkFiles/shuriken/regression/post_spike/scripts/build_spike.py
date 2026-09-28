#!/usr/bin/env python
"""Build SM_Shuriken_Spike - the bo-shuriken throwing spike, Katori / Meifu Shinkage pattern (modern line).

Source of truth for the asset (house rule: the script, not the .blend).  This file is only the
form's SPEC and its report text; the bar generator (shuriken_lib.bar, plugged in through the
non-radial Form hook as ``Form(geometry=BarGeometry(SPEC))``), M_Shuriken_Master (bar mode), the
UVs, UCX hull, sockets, LOD group, FBX, bake, gallery renders, JSON report and qa_check live in
Scripts/shuriken/shuriken_lib and are shared by every form.  Running it alone rebuilds
Assets/Shuriken.blend FROM SCRATCH with this one form; the canonical builder is build_pack.py
(``--forms four_point,eight_point,square_plate,six_point,spike``).

Authority: References/Shuriken/SHURIKEN_STUDY.md section 2.5 (build-to numbers), 3 (bar stock,
blackened iron), 4 (C4 about the long axis, pivot at the centre of mass by volume, the amended LOD
table scaled by bounding radius, physics 0.037 kg, the throwing methods and the recorded grip),
5 (originality); the pack style (STYLE_TARGET.md top section, shuriken_lib/material.py docstring).

Build-to (study 2.5; a living school publishes its own spec, two retailers agree):
    a straight SQUARE bar, square in section through the point, lying on a flat face; long axis X,
    +X toward the point; C4 about the long axis; no hole.
    length 150 mm (SOURCED), section 6 mm square (SOURCED - never the reseller's impossible 8 mm:
    an 8 mm bar 160 mm long is ~80 g before tapering), point 25 mm (SOURCED), tail tapering over
    its last 20 mm to 3 mm (ESTIMATE), mass 37 g (SOURCED).

Mass (the brief's hand check, checked, not trusted): 150 x 6 x 6 = 5400 mm3; the point removes
25 x 36 - 36 x 25 / 3 = 600; the tail removes 20 x 36 - 20/3 (36 + 9 + 18) = 300; the un-ground
bar is 4500 mm3 = 35.325 g at 7.85 g/cm3, -1.675 g from the sourced 37 g, inside +-2 g.  CHOICE:
the tail ESTIMATE is kept at 20 mm -> 3 mm.  Closing the gap by moving only the tail would need a
5.25 mm butt (shuriken_lib.bar_spec.tail_end_for_mass): a 1.1 deg taper per face instead of 4.3,
which no longer reads as the study's "shorter taper at the other" end, for a figure the gate
already accepts.  The finished
bar (0.3 mm arris round, 0.15 mm tip flat) is reported beside it and drives the physics override.

Style on a bar (the pack's restyled look, the same material read): the point is the cutting part,
so its four facets are ground bare steel ending in a 0.15 mm tip flat (tip radius 0.075 mm, the
stars' figure), finished like a star's grind: polished along the four ridges (its cutting edges)
and over the last 10 mm to the tip, satin toward the grind line.  (Polished over the full 25 mm
the facets rendered as the white arrowhead the pass-2 review rejected on the stars; scratch
render WorkFiles/shuriken/spike/iteration/.)  The four long arrises carry a 0.3 mm round (study: "bevel the four long
arrises about 0.3 mm"; Blender's Offset sense) with a polished highlight and a worn polished band
along it that widens toward the point; the four faces carry the satin coat (linear ~0.10,
metallic 1.0, roughness 0.34), smears, dirt-filled clustered micro-scratches and nicks along the
arris edges; wear grows along the long axis toward the point (M_Shuriken_Master bar mode).

Thrown point first with little spin (jiki-daho, the documented direct throw, study 4 [3][23]);
the recorded grip lays the dart along the palm, three fingers on it, the thumb on the butt [70].

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate,six_point,spike
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_spike.py -- [options]      (this form only)
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
    BAR_LOD_BANDS, BarLodSpec, BarSpec, bar_analytic, scaled_lod_screen_sizes, tail_end_for_mass,
)

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_Spike.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "spike_report.json"

HAND_CHECK = {"volume_mm3": 4500.0, "mass_g": 35.3, "text": "5400 - 600 (point pyramid) - 300 (tail frustum) = 4500 mm3"}
# Unreal's bounds sphere radius (the largest vertex distance from the bounding-box centre): the butt corners,
# sqrt(75^2 + 2 x 1.5^2) = 75.030 mm.  The pack's 1.0 / 0.10 / 0.035 are set for a 50 mm star; scaled by this
# radius the spike switches at the pack's ~0.89 m and ~2.54 m too.
UE_BOUNDS_RADIUS_MM = math.sqrt(75.0 ** 2 + 2.0 * 1.5 ** 2)

# --------------------------------------------------------------------------- spec

# LODs: a bar is straight, so nothing along it is subdivided (the faces and the round's chords are single
# planar strips from the tail base to the point base); what changes is the arris round.  Ceilings only
# (bar_spec.BAR_LOD_BANDS), nothing padded.
_LOD0 = BarLodSpec(arris_segments=4, band=BAR_LOD_BANDS[0],
                   note="LOD0: the four long arrises rounded (0.3 mm, 4 chords, smooth-shaded) running out into the "
                        "point and tail facets; point facets, 0.15 mm tip flat, tail taper, butt")
_LOD1 = BarLodSpec(arris_segments=2, band=BAR_LOD_BANDS[1],
                   note="LOD1: the arris round halved to 2 chords; everything else as LOD0")
_LOD2 = BarLodSpec(arris_segments=0, band=BAR_LOD_BANDS[2],
                   note="LOD2: square arrises (the round is ~0.1 px at the ~2.5 m switch); point, tip flat, tail, butt kept")

SPEC = BarSpec(
    form="spike",
    mesh_name="SM_Shuriken_Spike",
    title="Bo-shuriken throwing spike (Katori / Meifu Shinkage pattern)",
    length_mm=150.0,                # SOURCED [8][12][13]
    section_mm=6.0,                 # SOURCED [8][13]
    point_mm=25.0,                  # SOURCED [8]
    tail_taper_mm=20.0,             # ESTIMATE (study 2.5)
    tail_end_mm=3.0,                # ESTIMATE (study 2.5) - kept, see the module docstring
    mass_target_g=37.0,             # SOURCED [12][13]
    tip_flat_mm=0.15,               # tip radius 0.075 mm, the stars' (knife grind: 0.15 mm land)
    arris_mm=0.30,                  # study 2.5: "bevel the four long arrises about 0.3 mm"
    lods=(_LOD0, _LOD1, _LOD2),
    study_mass_range_g=(35.0, 42.0),        # study 2.5 table
    study_mass_typical_g=(37.0, 38.0),
    study_section="2.5",
    revision=1,
    physics_mass_kg=0.037,          # study 4, Physics (the report's override is the finished mass)
    lod_screen_sizes=scaled_lod_screen_sizes(UE_BOUNDS_RADIUS_MM),
    grip_from_butt_mm=40.0,         # ESTIMATE: the middle of three fingers laid along the bar, thumb on the butt
    axial_wear_mm=50.0,             # the coat's wear ramps up over the front third toward the point
    hero_yaw_deg=40.0,              # gallery: the bar lies across the hero frame, the point toward the viewer
    hull="bar_prism",
)


# --------------------------------------------------------------------------- report text


def mass_check(report: dict) -> dict:
    """The brief's hand check against the exact analytic figures and the measured meshes."""
    a = bar_analytic(SPEC)
    m = report["measured"]
    butt_for_37 = tail_end_for_mass(SPEC)
    r4 = lambda v: round(v, 4)  # noqa: E731
    return {
        "hand_check": HAND_CHECK,
        "analytic_mm3": {"prism 150 x 6 x 6": r4(a["prism_150x6x6"]), "point removes (900 - 300)": r4(a["point_removes"]),
                         "tail removes (720 - 420)": r4(a["tail_removes"]), "un-ground outline": r4(a["outline_volume"])},
        "analytic_outline_g": r4(a["outline_mass_g"]),
        "measured_unground_mesh_mm3": m["outline_volume_mm3"],
        "measured_unground_g": m["outline_mass_g"],
        "formula_vs_mesh_mm3": float(f"{m['outline_volume_mm3'] - a['outline_volume']:.3e}"),
        "target_g": SPEC.mass_target_g,
        "outline_minus_target_g": r4(m["outline_mass_g"] - SPEC.mass_target_g),
        "gate": "PASS" if m["mass_within_tolerance"] else "FAIL",
        "choice": ("KEPT the study's ESTIMATE tail (20 mm to 3 mm). The un-ground bar is 35.325 g, 1.675 g under the "
                   "sourced 37 g and inside the +-2 g gate. Moving only the tail estimate to close the gap would need "
                   f"a {butt_for_37:.2f} mm butt over the same 20 mm (a {math.degrees(math.atan((3.0 - 0.5 * butt_for_37) / 20.0)):.2f} "
                   "deg taper per face): the tail would stop reading as the study's shorter second taper for a figure "
                   "the gate already accepts. Real bars run 35-42 g (study 2.5), and a 6 mm section is nominal."),
        "tail_end_for_37g_mm": r4(butt_for_37),
        "finished_mesh_mm3": m["volume_mm3"],
        "finished_g": m["ground_mass_g"],
        "finished_note": ("the finished bar = the outline minus the 0.3 mm arris round (4 x 0.3^2 (1 - pi/4) = "
                          f"{a['arris_round_section_loss_mm2']:.4f} mm2 of section for the true arc, the 4-chord round a "
                          "little more) plus the tip flat's sliver (the facets end on a 0.15 mm square at 150 mm instead "
                          f"of a point: +{a['tip_flat_adds']:.3f} mm3); it drives the physics override"),
        "centre_of_mass": {
            "outline_from_butt_mm_analytic": r4(a["outline_com_from_butt_mm"]),
            "outline_from_middle_mm_analytic": r4(a["outline_com_from_middle_mm"]),
            "finished_from_butt_mm_mesh": m["centre_of_mass_from_butt_mm"],
            "finished_from_middle_mm_mesh": m["centre_of_mass_from_middle_mm"],
            "origin_residual_mm": m["centre_of_mass_mm"],
            "note": (f"the origin is the finished LOD0's centre of mass by volume; it sits "
                     f"{abs(m['centre_of_mass_from_middle_mm']):.2f} mm toward the butt of the geometric middle "
                     f"(the un-ground outline's: {abs(a['outline_com_from_middle_mm']):.2f} mm) because the 25 mm point "
                     "removes 600 mm3 and the 20 mm tail only 300; the tip flat moves it 0.11 mm back toward the point"),
        },
    }


GALLERY = {
    "lead_image": "Renders/Shuriken/spike_persp.png",
    "order": ["spike_persp.png", "spike_top.png", "spike_lodgrind.png", "spike_wire.png", "spike_lods.png"],
    "reason": ("lead with the hero (the bar turned 40 deg about Z for the shot only, so it lies across the frame with "
               "the polished point toward the viewer); the top view keeps the pack's common scale and shows the bar "
               "along +X, point right"),
}


def annotate(report: dict) -> None:
    """Spike-only report text: mass check, centre of mass, sockets, throwing, originality, LODs, gaps."""
    measured = report["measured"]
    check = mass_check(report)
    report["mass_check_spike"] = check
    report["build_to"].update({
        "hand_check_mm3": HAND_CHECK["volume_mm3"], "hand_check_g": HAND_CHECK["mass_g"],
        "analytic_outline_mm3": check["analytic_mm3"]["un-ground outline"],
        "analytic_outline_g": check["analytic_outline_g"],
        "unreal_bounds_radius_mm": round(UE_BOUNDS_RADIUS_MM, 4),
    })
    report["sockets_design"] = {
        "Grip": (f"on the long axis {SPEC.grip_from_butt_mm:g} mm from the butt (ESTIMATE), +X toward the point: the "
                 "recorded grip lays the dart along the palm, held by three fingers with the thumb securing the butt, "
                 "sliding out through the fingers on release (study 4 [70]); 40 mm is the middle of three fingers laid "
                 "along the bar from the butt"),
        "Trail": "at the butt, on the long axis, +X toward the point: a ribbon or spark emitter trails from the tail",
        "same_names_as_every_form": True,
    }
    report["throwing"] = {
        "method": "jiki-daho (direct throw): point first, little or no spin",
        "source": "SHURIKEN_STUDY.md 4, Throwing ([3][23]); the half-turn hanten-daho is the alternative for a bar",
        "for_the_blueprint": ("ProjectileMovementComponent along +X with the point leading; no RotatingMovement about Z "
                              "(that is the flat stars' kaiten-daho). The centre of mass sits "
                              f"{abs(measured['centre_of_mass_from_middle_mm']):.2f} mm toward the butt of the middle, "
                              "at the origin, so a half-turn throw pivots about the origin"),
    }
    franchise = [c for c in report["qa"]["checks"] if c["name"] == "no_franchise_strings"]
    report["originality"] = {
        "basis": "historical bo-shuriken (Katori / Meifu Shinkage pattern), public domain (study 5); study 2.5 numbers",
        "shape": ("a plain straight square bar, 25 mm four-facet point, 20 mm tail taper, no flight, no cord hole, no "
                  "engraving; generic, no franchise design"),
        "stamp": "none (study 5; any future mark must be an invented glyph)",
        "franchise_strings": (f"none in any object, mesh, material, texture or file name; qa_check no_franchise_strings "
                              f"passed on {sum(c['passed'] for c in franchise)} of {len(franchise)} objects"),
    }
    report["lod_choice"] = {
        "lod0": _LOD0.note, "lod1": _LOD1.note, "lod2": _LOD2.note,
        "bands": [list(lod.band) for lod in SPEC.lods],
        "why_so_few": ("study 2.5: 'at 1:25 the silhouette is nearly all straight line, so the triangles belong at the "
                       "point' - the faces and the rounds are single planar strips; the vertices sit at the point, "
                       "the tip flat and the two run-outs. Nothing is padded to reach a star's band."),
        "screen_sizes": (f"{report.get('lod_screen_sizes')} = the pack's 1.0 / 0.10 / 0.035 scaled by Unreal's bounds "
                         f"radius {UE_BOUNDS_RADIUS_MM:.3f} / 50 mm, so the switches stay at ~0.89 m and ~2.54 m"),
    }
    report["gallery"] = GALLERY
    report["style_on_a_bar"] = {
        "material": "M_Shuriken_Master, bar mode (shuriken_wear_axis = 1): the pack recipe, only its inputs switched",
        "coat": "the four faces, the tail facets and the butt: satin coat linear ~0.10, metallic 1.0, roughness 0.34, "
                "smears, dirt-filled clustered micro-scratches laid in each face's own plane, near-invisible pits, "
                "two sub-pixel rust specks (top face toward the point, bottom face toward the butt)",
        "arrises": ("0.3 mm round (4 chords at LOD0, smooth-shaded), polished; a worn polished band on the faces along it "
                    "that widens from 0.08 mm at the butt to 0.30 mm toward the point, nicks chipped into the faces "
                    "along it, more of them toward the point (the polished highlight)"),
        "point": ("ground bare steel, the stars' two-finish grind: polished along the four ridges (the point's cutting "
                  "edges, the pack's 0.7 mm band) and over the last 10 mm to the 0.15 mm tip flat, satin toward the "
                  "grind line. The brief asked for 'its four facets polished'; polished over the full 25 mm they "
                  "rendered as a white arrowhead (WorkFiles/shuriken/spike/iteration/polished_*), the look the pass-2 "
                  "review rejected on the stars' tips, so the point carries the same grind polish as a star's point"),
        "wear": "along the long axis toward the point (nick density, the arris band, the tip polish), not by radius",
        "gallery": ("hero: the object is turned 40 deg about Z for the shot only (camera, lights and floor unchanged), so "
                    "the bar lies across the frame; top view unturned at the pack's common scale; LOD strip stacked"),
        "gate_adaptations": [
            "hero_plate / top_plate: a bar reads its COAT pixels (up-facing coat faces, what a star's plate is); the "
            "whole object is reported beside it (render_gates.*.whole_object)",
            "pack_consistency: the spike's coat pixels against PACK_COAT_ANCHOR (the anchor forms' own plate pixels); "
            "its whole-object figures are information (pack_consistency.bar_whole_object)",
        ],
    }
    report["known_gaps"] += [
        "Tail taper (20 mm to 3 mm) is the study's ESTIMATE, kept (see mass_check_spike.choice); the 0.3 mm arris round "
        "and the grip distance are modelling estimates. No flight or cord hole (antique spikes sometimes carry one).",
        "The spike's LOD bands are its own (ceilings 150 / 100 / 48, no floor): study 4's 1,200-2,500 table is for stars.",
        "Pack consistency compares the spike like with like: its coat pixels (up-facing faces) against the anchor forms' "
        "plate pixels; its whole-object gallery statistics are reported, not gated (half of a bar's silhouette is side "
        "face and polished point).",
    ]


def _form():
    from shuriken_lib import BarGeometry, Form  # needs bpy; SPEC above does not
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate, report_name="spike_report.json",
                geometry=BarGeometry(SPEC))


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


# --------------------------------------------------------------------------- CLI


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_spike.py", description=__doc__,
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
