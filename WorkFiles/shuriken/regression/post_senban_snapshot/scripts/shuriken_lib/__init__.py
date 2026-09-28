"""Shared library for the shuriken pack (Blender 5.2 -> Unreal 5.8 -> Fab).

Generators (the radial star; the square plate), one material (M_Shuriken_Master), one
UV / UCX / socket / LOD-group / export path through Scripts/pipeline, one gallery render
rig, one measurement + JSON report and one qa_check gate - shared by every form.  A form
is a small spec plus a thin ``build_<form>.py``; it plugs into the pack through the
generic generator hook (``hooks.FormGeometry``, ``Form.geometry``), which radial stars
get by default (``hooks.RadialGeometry``).  ``build_pack.py`` rebuilds
Assets/Shuriken.blend from scratch with any set of forms.

Modules:
    spec      pure data: RadialStarSpec, LodSpec, study_lod_chain, Outline, rotate,
              analytic_area / numeric_outline_area (study cross-checks), screen sizes
    geometry  the C_n generator (orbit-keyed 1 nm vertex factory, authored bevel)
    hooks     FormGeometry (the generic Form hook build_form / render / bake / export use) and
              RadialGeometry (the radial-star path, unchanged from 3.2)
    plate_spec  pure data: SquarePlateSpec, PlateLodSpec, PlateOutline, plate_analytic_area
    plate     the square-plate (senban) generator, measurement and SquarePlateGeometry
    material  M_Shuriken_Master (per-form wear radii via object custom properties)
    measure   measurement, LOD deviation, C_n symmetry, UV coverage, topology quality
    uv        LOD1..n UV0 from LOD0's islands; cross-LOD UV agreement
    bake      T_Shuriken_<Form>_BC / _ORM / _N from M_Shuriken_Master; baked preview material
    render    hero / top / wire / LOD-strip rig, camera fit, image statistics, render gates
    pack      orchestration, reports, form discovery, shared CLI

HEADLESS ONLY: every entry point runs under ``blender -b --factory-startup --python``.
"""
from __future__ import annotations

import sys
from pathlib import Path

VERSION = "3.3.0"   # 3.1 (eight-point): analytic_area, numeric_outline_area, unbevelled_plate_area_mm2,
                    # opt-in RadialStarSpec.hull="tip_prism" (author_tip_prism_hull)
                    # 3.2 (maintenance): LodSpec.hub_rings (graded, mirror-symmetric hub), LOD1..n UV0
                    # from LOD0's islands (uv), texture bake + baked-only gallery (bake), pack LOD
                    # screen sizes from distance, rim-wall reflection card + wall gate, solved DOF,
                    # hero centring, common top-view scale, labelled LOD strip, measured tip angle
                    # and bevel stations, topology quality, SHA-256-bound engine check
                    # 3.3 (senban): generic Form hook (hooks.FormGeometry, Form.geometry; the radial
                    # path moved verbatim into RadialGeometry), square-plate generator (plate,
                    # plate_spec), scaled_lod_screen_sizes
LIBRARY_DIR = Path(__file__).resolve().parent
PROJECT = LIBRARY_DIR.parents[2]
_SCRIPTS = str(PROJECT / "Scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from .spec import (  # noqa: E402
    LOD0_BAND, LOD1_BAND, LOD2_BAND, LOD_SCREEN_SIZES, MM, SNAP, STUDY_LOD_SCREEN_SIZES, LodSpec, Outline,
    RadialStarSpec, analytic_area, lod_triangles, numeric_outline_area, rotate, scaled_lod_screen_sizes,
    screen_size_distance_m, study_lod_chain, wedge_triangles,
)
from .plate_spec import (  # noqa: E402
    PlateLodSpec, PlateOutline, SquarePlateSpec, plate_analytic_area, plate_triangles, plate_wedge_triangles,
)

try:
    import bpy  # noqa: F401
except ImportError:  # pure-Python use: specs only
    bpy = None  # type: ignore[assignment]

if bpy is not None:
    from .geometry import author_lod, author_tip_prism_hull, build_star_bmesh  # noqa: E402
    from .material import MATERIAL_NAME, build_material, tag_object  # noqa: E402
    from .measure import (  # noqa: E402
        cn_deviation, lod_deviation, measure, surface_deviation, topology_quality, unbevelled_plate_area_mm2,
    )
    from .uv import cross_lod_uv, transfer_uvs, uv_overlap_pairs  # noqa: E402
    from .bake import bake_form, preview_material, texture_paths  # noqa: E402
    from .pack import (  # noqa: E402
        BuildOptions, Form, add_common_args, blender_argv, build_pack, discover_forms, options_from_args,
        report_passed, run_single, summary, write_report,
    )
    from .render import render_previews  # noqa: E402
    from .hooks import FormGeometry, RadialGeometry, geometry_of  # noqa: E402
    from .plate import (  # noqa: E402
        SquarePlateGeometry, author_plate_lod, build_plate_bmesh, measure_plate, unbevelled_plate,
    )
