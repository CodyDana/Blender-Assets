"""Shared library for the shuriken pack (Blender 5.2 -> Unreal 5.8 -> Fab).

Generators (the radial star; the square plate; the bar; the outline plate), one material (M_Shuriken_Master), one
UV / UCX / socket / LOD-group / export path through Scripts/pipeline, one gallery render
rig, one measurement + JSON report and one qa_check gate - shared by every form.  A form
is a small spec plus a thin ``build_<form>.py``; it plugs into the pack through the
generic generator hook (``hooks.FormGeometry``, ``Form.geometry``), which radial stars
get by default (``hooks.RadialGeometry``).  ``build_pack.py`` rebuilds
Assets/Shuriken.blend from scratch with any set of forms.

Modules:
    spec      pure data: RadialStarSpec, LodSpec, study_lod_chain, Outline, rotate,
              analytic_area / numeric_outline_area (study cross-checks), screen sizes
    geometry  the C_n generator (orbit-keyed 1 nm vertex factory, authored knife grind + scallop / hole chamfers,
              distance-to-outline attributes for the material)
    hooks     FormGeometry (the generic Form hook build_form / render / bake / export use) and
              RadialGeometry (the radial-star path, unchanged from 3.2)
    plate_spec  pure data: SquarePlateSpec, PlateLodSpec, PlateOutline, plate_analytic_area
    plate     the square-plate (senban) generator, measurement and SquarePlateGeometry
    bar_spec  pure data: BarSpec, BarLodSpec, BarOutline, bar_analytic (the throwing spike, study 2.5)
    bar       the bar generator (C4 about +X, rounded arrises, point and tail facets, tip flat), its own
              LOD0 unwrap, measurement and BarGeometry
    outline_spec  pure data: HookedCrossSpec, OutlineLodSpec, HookedOutline (the analytic C4 contour of straight
              edges, one convex back arc, concave fillets and sharp convex corners; columns, ridge, run-outs, area)
    outline_plate the outline-plate generator (edge band per column pair, constrained-Delaunay plate with
              structured Steiner points, selective knife grind + small chamfer, no hole), the handedness gate
              and its negative control, the C4 prism hull, measurement and OutlinePlateGeometry
    material  M_Shuriken_Master (the STYLE_TARGET recipe; per-form numbers via object custom
              properties, wear boundary from the generator's distance attributes)
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

VERSION = "3.9.0"   # 3.9.0 (the hooked cross, SM_Shuriken_HookedCross - the pack's first OUTLINE PLATE; the five frozen
                    # forms' geometry, hulls, sockets, UVs, normals and maps unchanged): outline_spec + outline_plate
                    # (OutlinePlateGeometry through the non-radial Form hook); handedness gate in the build + its
                    # negative control; M_Shuriken_Master cavity mode (shuriken_cavity_mode / shuriken_cavity: the
                    # cavity grime and dish read the concave-corner distance; a Mix with the mode as factor, exact
                    # no-op on every other form); render: grind_target_xy / grind_azimuth_deg for the LOD close-up
                    # and an opt-in presented-face camera record (render.camera_side), both absent = the old paths;
                    # pack: a form's own gates (report["form_gates"]) join the gates block and report_passed
                    # 3.8.1 (spike maintenance, after its visual / geometry / Unreal reviews; the plate forms' geometry,
                    # UVs, hulls, sockets and maps unchanged): hero lamps scaled with a bar's fitted camera distance
                    # (render HERO_RIG_REFERENCE_M), backdrop points + pack_consistency backdrop gate, a bar's side-face
                    # dark-dot gate and wall anchor, the LOD strip's end-on section insets; M_Shuriken_Master bar mode:
                    # pits at BAR_PIT_SCALE, no worn band / nicks on the shoulder, a satin-bright arris round; bar:
                    # analytic custom normals on the round, a deterministic 2048 x 512 UV layout (gaps, border,
                    # every LOD on its island's exact map), bake of non-square maps + unused-texel fill; uv: per-loop
                    # island-map deviation; hooks: texture_size, fill_unused_texels, lod_deviation_headline,
                    # bounds_radius, surface_snapshot, noun / outline_wording (all default to the old paths)
                    # 3.8.0 (the spike, SM_Shuriken_Spike - the pack's first BAR): bar_spec + bar (BarGeometry through
                    # the non-radial Form hook); two OPTIONAL hook methods with the old paths as defaults
                    # (custom_unwrap, symmetry_deviation) and FormGeometry.consistency_class; M_Shuriken_Master
                    # bar mode (input switches keyed on shuriken_wear_axis: FACE attribute classes, analytic
                    # grind line, wear along +X, scratches in each face's plane; exact no-ops on the plate forms);
                    # render: hero_yaw_deg / lod_strip_axis / grind_target_back_m read from the outline, the top
                    # frame check per axis, mask BLUE = ground surfaces, coat_luminance, pack_consistency like
                    # with like (a bar's coat against PACK_COAT_ANCHOR)
                    # 3.7.1 (six-point review, reporting only - no geometry, UV, material, bake or export change):
                    # pack_consistency centred on a FIXED anchor (render.PACK_ANCHOR, the forms frozen at restyle
                    # pass 2) with per-form headroom, the all-forms figures kept as information and an
                    # anchor-drift check; cross_lod_uv names its metrics and splits the surface figure into
                    # plate / non-plate triangles
                    # 3.7 (style pass 2 maintenance, after the same-rig review): knife facets flat-shaded across
                    # their creases (KNIFE_CREASE_DEG) + knife_shading gate on stored corner normals; folded
                    # run-out quads authored as explicit mirrored triangles; four-point LOD2 run-out station;
                    # render: <form>_lodgrind.png oblique LOD close-ups; M_Shuriken_Master second round
                    # (polished 0.7 mm band + satin grind, normal-map roll-off instead of the painted soot
                    # ring, whole-face smears, dirt-filled clustered scratches, sub-pixel rust)
                    # 3.6 (style pass 2, knife grind): every cutting edge knife ground to a per-form grind angle
                    # and edge land (ChamferProfile.knife), scallop chamfer + wall, hole deburr, root run-out,
                    # LOD2 single-facet grind (edge line, run-out vertex, pyramid tip); mass gate on the
                    # un-ground plate, ground mass reported + physics override; wall UV islands per arm side;
                    # M_Shuriken_Master rebuilt (bare grind, nicks, cavity grime, micro-scratches); GPU bake
                    # 3.1 (eight-point): analytic_area, numeric_outline_area, unbevelled_plate_area_mm2,
                    # opt-in RadialStarSpec.hull="tip_prism" (author_tip_prism_hull)
                    # 3.2 (maintenance): LodSpec.hub_rings (graded, mirror-symmetric hub), LOD1..n UV0
                    # from LOD0's islands (uv), texture bake + baked-only gallery (bake), pack LOD
                    # screen sizes from distance, rim-wall reflection card + wall gate, solved DOF,
                    # hero centring, common top-view scale, labelled LOD strip, measured tip angle
                    # and bevel stations, topology quality, SHA-256-bound engine check
                    # 3.3 (senban): generic Form hook (hooks.FormGeometry, Form.geometry; the radial
                    # path moved verbatim into RadialGeometry), square-plate generator (plate,
                    # plate_spec), scaled_lod_screen_sizes
                    # 3.4 (style pass, STYLE_TARGET.md): full-length ground chamfer on every outer
                    # edge of both generators (spec.ChamferProfile, per-form chamfer_width_mm),
                    # generator-written distance attributes (geometry.EDGE_ATTR / HOLE_ATTR),
                    # M_Shuriken_Master rebuilt to the reference recipe (coat 0.10, bare chamfers,
                    # torn boundary, dashed scratches, pits, mottle, rust), gallery plate band re-measured
                    # 3.5 (style pass, second round): M_Shuriken_Master around gradients (crest-to-fringe
                    # bare steel, hairline scratch pairs, darkening pits, radial patina); hero overhead
                    # glossy-only panel + top facet band, facet mask/gate, mean + p50 plate and pack gates
                    # centred on the reference through the pack rig; LOD1..n UV0 clamped to the unit
                    # square (+ gate); outline arm-width measurement; ORM/N PNG colour chunks stripped;
                    # four-point hull = tip prism; ue_import_textures.py (Unreal texture flags)
LIBRARY_DIR = Path(__file__).resolve().parent
PROJECT = LIBRARY_DIR.parents[2]
_SCRIPTS = str(PROJECT / "Scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from .spec import (  # noqa: E402
    CHAMFER_DEPTH_FRACTION, CHAMFER_ROUND_FRACTION, CHAMFER_WIDTH_FRACTION, LOD0_BAND, LOD1_BAND, LOD2_BAND,
    LOD_SCREEN_SIZES, MM, SNAP, STUDY_LOD_SCREEN_SIZES, ChamferProfile, LodSpec, Outline, RadialStarSpec,
    analytic_area, chamfer_profile, lod_triangles, numeric_outline_area, rotate, scaled_lod_screen_sizes,
    screen_size_distance_m, study_lod_chain, wedge_triangles,
)
from .plate_spec import (  # noqa: E402
    PlateLodSpec, PlateOutline, SquarePlateSpec, plate_analytic_area, plate_triangles, plate_wedge_triangles,
)
from .bar_spec import (  # noqa: E402
    BAR_LOD_BANDS, BarLodSpec, BarOutline, BarSpec, bar_analytic, bar_triangles, tail_end_for_mass,
)
from .outline_spec import HookedCrossSpec, HookedOutline, OutlineLodSpec, outline_mass_g  # noqa: E402

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
    from .bar import BarGeometry, author_bar_lod, build_bar_bmesh, measure_bar, unground_bar  # noqa: E402
    from .outline_plate import (  # noqa: E402
        OutlinePlateGeometry, author_outline_lod, build_outline_bmesh, handedness_gate, handedness_negative_control,
        measure_outline,
    )
