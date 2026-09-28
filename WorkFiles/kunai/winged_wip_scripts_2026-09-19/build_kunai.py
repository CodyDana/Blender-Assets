#!/usr/bin/env python
"""Build SM_Kunai - the three-prong ("winged") kunai the user asked for, blank grip band for their own lettering.

Source of truth for the asset (house rule: the script, not the .blend).  This file is only the form's SPEC and its
report text; the kunai generator (shuriken_lib.kunai + kunai_spec, plugged in through the non-radial Form hook as
``Form(geometry=KunaiGeometry(SPEC))``), M_Shuriken_Master (class mode + the wrap branch), the analytic UVs, the two
UCX hulls, sockets, LOD group, FBX, bake, gallery renders, JSON report and qa_check live in Scripts/shuriken/shuriken_lib
and are shared by every form.  Running it alone rebuilds Assets/Shuriken.blend FROM SCRATCH with this one form; the
canonical builder is build_pack.py (``--forms four_point,eight_point,square_plate,six_point,spike,hooked_cross,kunai``).

Authority: References/Kunai/KUNAI_STUDY.md (section 4, the BUILD-TO table, is authoritative; section 5 the modelling
notes; section 6 franchise avoidance) and the pack style (References/Shuriken/style_reference/STYLE_TARGET.md top
section, shuriken_lib/material.py docstring).

The user's decision (2026-09-18/19): "just build the same look for the kunai as minato namikaze's, i will replace the
lettering on the hilt of the kunai" - the three-pronged look, NO lettering modelled, traced or textured, the grip left
ready for their own.  No franchise word anywhere in an object, material, texture, socket, file or report name
(FRANCHISE_TERMS below are gated on every name this build makes, on top of qa_check's deny list).

HEADLESS ONLY.  Never open this through the live MCP link and never launch a GUI:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_pack.py -- --forms four_point,eight_point,square_plate,six_point,spike,hooked_cross,kunai
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/shuriken/build_kunai.py -- [options]      (this form only)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from shuriken_lib import KunaiLodSpec, KunaiSpec, scaled_lod_screen_sizes  # noqa: E402

PROJECT = HERE.parents[2]
DEFAULT_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Kunai.fbx"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "kunai_report.json"

# Study section 6: the pipeline's deny list catches "naruto" only; the rest is gated here on every name the build makes.
FRANCHISE_TERMS = ("naruto", "minato", "namikaze", "hiraishin", "flying thunder god", "flying raijin", "yondaime",
                   "hokage", "yellow flash", "konoha", "shippuden", "boruto")
# Unreal's bounds sphere about the bounding-box centre: the blade tip and the ring's far end, 140 mm each side.
UE_BOUNDS_RADIUS_MM = 140.0

_LOD0 = KunaiLodSpec(blade_base_intervals=3, blade_leaf_intervals=14, blade_tip_intervals=2, prong_intervals=8,
                     prong_tip_intervals=2, fillet_segments=3, outer_chamfer_intervals=2, rear_intervals=2, land=0.15,
                     chamfer=0.45, plateau_steiner=1, grip_sides=20, collars="bevel", ring_segments=24, ring_section=8,
                     neck_chamfer=0.6, band=(1600, 2800),
                     note="LOD0: the full outline (kite corner, 14 leaf stations), knife grind 35 deg to a 0.15 mm land "
                          "on all six cutting edges with run-outs into the plateau chamfer, 3-segment crotch fillets, a "
                          "20-sided grip with bevelled collars, 24 x 8 ring, chamfered neck")
_LOD1 = KunaiLodSpec(blade_base_intervals=1, blade_leaf_intervals=7, blade_tip_intervals=1, prong_intervals=4,
                     prong_tip_intervals=1, fillet_segments=2, outer_chamfer_intervals=1, rear_intervals=1, land=0.15,
                     chamfer=0.45, plateau_steiner=1, grip_sides=10, collars="step", ring_segments=12, ring_section=6,
                     neck_chamfer=0.0, band=(650, 1100),
                     note="LOD1: half the stations, the grind kept (one facet per station), a 10-sided grip with plain "
                          "collar steps, 12 x 6 ring, square neck")
_LOD2 = KunaiLodSpec(blade_base_intervals=1, blade_leaf_intervals=3, blade_tip_intervals=1, prong_intervals=2,
                     prong_tip_intervals=1, fillet_segments=1, outer_chamfer_intervals=1, rear_intervals=1, land=0.0,
                     chamfer=0.0, plateau_steiner=0, grip_sides=10, collars="none", ring_segments=8, ring_section=4,
                     neck_chamfer=0.0, band=(220, 400),
                     note="LOD2: the silhouette, the prongs and the ring hole kept; cutting edges are the edge line "
                          "(land 0), plateau edges square, no collars (0.6 mm is 0.25 px at the 2.5 m switch)")

SPEC = KunaiSpec(
    form="kunai",
    mesh_name="SM_Kunai",
    title="Three-prong kunai (blank grip band for the user's lettering)",
    lods=(_LOD0, _LOD1, _LOD2),
    mass_target_g=176.9,            # study notes: the mass-gate basis is the un-ground steel, 22,530 mm3 = 176.9 g
    mass_tolerance_g=2.0,
    assembled_target_g=190.0,       # study 4: 187-192 g assembled (DERIVED), reported
    revision=1,
    physics_mass_kg=0.19,           # study 4 / notes: the physics override
    lod_screen_sizes=scaled_lod_screen_sizes(UE_BOUNDS_RADIUS_MM),
    grip_x_mm=-54.0,                # study 5: mid grip
    trail_x_mm=-140.0,              # study 5: the ring's far end
    hero_yaw_deg=40.0,
    texture_px=(4096, 2048),
    steel_px_per_mm=13.5,
    wrap_px_per_mm=10.0,
    letter_px_per_mm=15.0,
    study_mass_range_g=(187.0, 192.0),
    study_mass_typical_g=(190.0, 190.0),
)


def annotate(report: dict) -> None:
    """Kunai-only report text (filled in by the finished build)."""
    report.setdefault("form_gates", {})


def _form():
    from shuriken_lib import Form, KunaiGeometry  # needs bpy; SPEC above does not
    return Form(spec=SPEC, module_path=str(HERE), annotate=annotate, report_name="kunai_report.json",
                geometry=KunaiGeometry(SPEC))


try:
    FORM = _form()
except ImportError:   # imported outside Blender (spec inspection only)
    FORM = None


def parse_args(argv=None):
    from shuriken_lib import add_common_args, blender_argv
    parser = argparse.ArgumentParser(prog="build_kunai.py", description=__doc__,
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
