"""Shared library for the shuriken pack (Blender 5.2 -> Unreal 5.8 -> Fab).

One radial-star generator, one material (M_Shuriken_Master), one UV / UCX / socket /
LOD-group / export path through Scripts/pipeline, one gallery render rig, one
measurement + JSON report and one qa_check gate - shared by every form.  A form is a
small ``RadialStarSpec`` plus a thin ``build_<form>.py``; ``build_pack.py`` rebuilds
Assets/Shuriken.blend from scratch with any set of forms.

Modules:
    spec      pure data: RadialStarSpec, LodSpec, study_lod_chain, Outline, rotate,
              analytic_area / numeric_outline_area (study cross-checks)
    geometry  the C_n generator (orbit-keyed 1 nm vertex factory, authored bevel)
    material  M_Shuriken_Master (per-form wear radii via object custom properties)
    measure   measurement, LOD deviation, C_n symmetry, UV coverage
    render    hero / top / wire / LOD-strip rig, camera fit, image statistics
    pack      orchestration, reports, form discovery, shared CLI

HEADLESS ONLY: every entry point runs under ``blender -b --factory-startup --python``.
"""
from __future__ import annotations

import sys
from pathlib import Path

VERSION = "3.1.0"   # 3.1 (eight-point): analytic_area, numeric_outline_area, unbevelled_plate_area_mm2,
                    # opt-in RadialStarSpec.hull="tip_prism" (author_tip_prism_hull)
LIBRARY_DIR = Path(__file__).resolve().parent
PROJECT = LIBRARY_DIR.parents[2]
_SCRIPTS = str(PROJECT / "Scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from .spec import (  # noqa: E402
    LOD0_BAND, LOD1_BAND, LOD2_BAND, LOD_SCREEN_SIZES, MM, SNAP, LodSpec, Outline, RadialStarSpec, analytic_area,
    lod_triangles, numeric_outline_area, rotate, study_lod_chain, wedge_triangles,
)

try:
    import bpy  # noqa: F401
except ImportError:  # pure-Python use: specs only
    bpy = None  # type: ignore[assignment]

if bpy is not None:
    from .geometry import author_lod, author_tip_prism_hull, build_star_bmesh  # noqa: E402
    from .material import MATERIAL_NAME, build_material, tag_object  # noqa: E402
    from .measure import (  # noqa: E402
        cn_deviation, lod_deviation, measure, surface_deviation, unbevelled_plate_area_mm2,
    )
    from .pack import (  # noqa: E402
        BuildOptions, Form, add_common_args, blender_argv, build_pack, discover_forms, options_from_args,
        report_passed, run_single, summary, write_report,
    )
    from .render import render_previews  # noqa: E402
