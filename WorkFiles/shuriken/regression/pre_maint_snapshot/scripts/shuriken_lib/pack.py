"""Build orchestration: one form or a whole pack, from scratch, through Scripts/pipeline.

Flow (the same for one form or eight):

    reset scene -> M_Shuriken_Master -> per form, in its own collection:
        LOD0..LODn authored by the generator, material, UVs, UCX hull, sockets,
        LOD group (pipeline.make_lod_group renames LOD0 and its helpers together),
        measurement, symmetry, LOD deviation, qa_check
    -> save the .blend ONCE (scripts are the source of truth; nothing is patched)
    -> per form: FBX + .sockets.json sidecar (one form per FBX: study 4, only the first
       mesh's collision imports from a multi-mesh file)
    -> per form: gallery renders with every other form hidden, rig torn down after
    -> per form JSON report (+ the pack report when run through build_pack.py)

The rig is built after the save, so it never reaches the .blend.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import bpy

from . import LIBRARY_DIR, PROJECT, VERSION
from .geometry import author_lod, author_tip_prism_hull
from .material import MATERIAL_NAME, build_material, tag_object, wear_range
from .measure import (cn_deviation, lod_deviation, measure, surface_snapshot, triangles_of,
                      uv_coverage)
from .render import render_previews
from .spec import LOD_SCREEN_SIZES, MM, RadialStarSpec

import pipeline  # noqa: E402  (Scripts/ is on sys.path via the package __init__)

PACK = "Shuriken"
DEFAULT_BLEND = PROJECT / "Assets" / "Shuriken.blend"
DEFAULT_EXPORT_DIR = PROJECT / "Exports" / "Shuriken"
DEFAULT_RENDER_DIR = PROJECT / "Renders" / "Shuriken"
DEFAULT_REPORT_DIR = PROJECT / "WorkFiles" / "shuriken"
DEFAULT_DIAG = DEFAULT_REPORT_DIR / "diag"
PACK_REPORT_NAME = "pack_report.json"
FORMS_DIR = LIBRARY_DIR.parent


# =========================================================================== data


@dataclass
class Form:
    """A pack form: its spec plus the form-only report text.

    ``annotate(report)`` runs after every generic figure is in the report (measured,
    renders, qa ...) and adds the form's originality notes, history and gaps.
    """

    spec: RadialStarSpec
    module_path: str = ""
    annotate: Optional[Callable[[dict], None]] = None
    report_name: Optional[str] = None

    @property
    def name(self) -> str:
        return self.spec.form

    @property
    def report_filename(self) -> str:
        return self.report_name or f"{self.spec.form}_report.json"


@dataclass
class BuildOptions:
    blend: Path = DEFAULT_BLEND
    export_dir: Path = DEFAULT_EXPORT_DIR
    render_dir: Path = DEFAULT_RENDER_DIR
    diag_dir: Path = DEFAULT_DIAG
    report_dir: Path = DEFAULT_REPORT_DIR
    fbx_paths: Dict[str, Path] = field(default_factory=dict)       # form -> FBX override
    report_paths: Dict[str, Path] = field(default_factory=dict)    # form -> report override
    budget: int = 2500
    hull_verts: int = 24
    island_margin: float = 0.005
    texel_map: int = 2048
    samples: int = 220
    light_scale: float = 1.0
    res: int = 1600
    res_y: int = 0
    no_export: bool = False
    no_render: bool = False

    @property
    def render_height(self) -> int:
        return self.res_y or round(self.res * 9 / 16)

    def fbx_path(self, form: Form) -> Path:
        return Path(self.fbx_paths.get(form.name) or Path(self.export_dir) / f"{form.spec.mesh_name}.fbx")

    def report_path(self, form: Form) -> Path:
        return Path(self.report_paths.get(form.name) or Path(self.report_dir) / form.report_filename)


@dataclass
class FormBuild:
    form: Form
    collection: object
    lod_objects: list
    hull: object
    group: object
    report: dict
    started: float


# =========================================================================== scene


def reset_scene() -> None:
    """Empty the factory-startup scene and set metric units at scale 1.0."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "MILLIMETERS"


def unwrap(obj, island_margin: float = 0.005) -> None:
    """Smart UV Project (study 4 / guidelines 6.4 want a real, non-overlapping unwrap).

    The islands are repacked with the concave, free-rotation packer.  Measured on the
    four-point, the packer is not what limits coverage: sweeping shape_method x
    margin_method x margin over 20 combinations moves UV square coverage only between
    26.0% and 32.0%.  The limit is the island *shapes* Smart UV Project produces from
    this outline (long thin plate, chamfer and wall strips); getting past it means
    hand-laying the shells, which belongs to the pack-atlas pass.  0.005 is kept from
    rev 2, where it was chosen because 0.004 put an overlapping pair on a Decimate-
    folded LOD2; LODs are now authored and unwrapped on their own, but changing the
    margin would change the four-point's shipped LOD0 UVs for no measured gain.
    """
    view_layer = bpy.context.view_layer
    for other in view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=island_margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", shape_method="CONCAVE",
                            margin_method="SCALED", margin=island_margin, scale=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


def collection_name(spec: RadialStarSpec) -> str:
    return spec.mesh_name[len("SM_"):] if spec.mesh_name.startswith("SM_") else spec.mesh_name


# =========================================================================== one form


def _round_stats(stats: dict) -> dict:
    return {k: (round(v, 12) if isinstance(v, float) else v) for k, v in stats.items()}


def build_form(form: Form, material, options: BuildOptions) -> FormBuild:
    """Author, dress and measure one form in its own collection.  Does not save or export."""
    started = time.time()
    spec = form.spec
    spec.validate()
    o = spec.outline()
    coll = bpy.data.collections.new(collection_name(spec))
    bpy.context.scene.collection.children.link(coll)

    report: dict = {
        "asset": spec.mesh_name,
        "form": spec.form,
        "title": spec.title,
        "pack": PACK,
        "revision": spec.revision,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "script": form.module_path,
        "library": str(LIBRARY_DIR),
        "library_version": VERSION,
        "pipeline_version": pipeline.VERSION,
        "blender": bpy.app.version_string,
        "build_to": {
            "points": spec.points,
            "across_mm": spec.tip_circle_mm, "thickness_mm": spec.thickness_mm,
            "mass_g": spec.mass_target_g, "arm_width_mm": spec.arm_width_mm,
            "hub_radius_mm": spec.hub_radius_mm, "hole_mm": spec.hole_diameter_mm,
            "tip_included_deg": spec.tip_included_deg,
            "bevel_offset_mm": spec.bevel_offset_mm, "bevel_runout_mm": spec.bevel_runout_mm,
            "source": f"References/Shuriken/SHURIKEN_STUDY.md section {spec.study_section}",
        },
    }

    # --- LOD0: author, material, UVs, then the helpers that key to it.
    lod_objects, lod_used, lod_stats = [], [], []
    lod0, stats0, used0 = author_lod(o, spec.lods[0], spec.mesh_name, coll)
    lod0.data.materials.append(material)
    tag_object(lod0, o)
    lod0["shuriken_form"] = spec.form
    lod0["shuriken_lod"] = 0
    unwrap(lod0, island_margin=options.island_margin)
    lod_objects.append(lod0)
    lod_used.append(used0)
    lod_stats.append(stats0)
    bpy.context.view_layer.update()
    report["lod0_triangles_pre_group"] = triangles_of(lod0)

    if spec.hull == "tip_prism":
        hull = author_tip_prism_hull(lod0, o, index=0)
        report["hull_method"] = (f"tip_prism: shuriken_lib.geometry.author_tip_prism_hull, the {o.n}-gon prism "
                                 "through the tips at full plate thickness (exactly C_n, encloses LOD0)")
    else:
        hull = pipeline.make_ucx_hull(lod0, index=0, max_verts=options.hull_verts)
        report["hull_method"] = (f"pipeline: pipeline.make_ucx_hull, convex hull of LOD0 collapse-decimated "
                                 f"to <= {options.hull_verts} vertices")
    report["hull"] = {"name": hull.name, "verts": len(hull.data.vertices),
                      "faces": len(hull.data.polygons)}
    grip = (math.radians(spec.grip_angle_deg) if spec.grip_angle_deg is not None
            else math.pi / o.n)                      # the rim notch between arms 0 and 1
    pipeline.make_socket(lod0, "Grip", (o.r_hub * math.cos(grip), o.r_hub * math.sin(grip), 0.0),
                         rotation_euler=(0.0, 0.0, grip))
    pipeline.make_socket(lod0, "Trail", (0.0, 0.0, 0.0), rotation_euler=(0.0, 0.0, 0.0))

    # --- LOD1..n: authored by the same generator at their own segment counts.
    for level, lod in enumerate(spec.lods[1:], start=1):
        obj, stats, used = author_lod(o, lod, f"{spec.mesh_name}_LOD{level}", coll)
        obj.data.materials.append(material)
        tag_object(obj, o)
        obj["shuriken_form"] = spec.form
        obj["shuriken_lod"] = level
        unwrap(obj, island_margin=options.island_margin)
        lod_objects.append(obj)
        lod_used.append(used)
        lod_stats.append(stats)

    group = pipeline.make_lod_group(spec.mesh_name, lod_objects)
    bpy.context.view_layer.update()
    lod0 = lod_objects[0]

    lod0_spec = lod_used[0]
    hole_total = lod0_spec.hole_segments * o.n
    report["density"] = {
        "points": o.n,
        "N_COL": lod0_spec.columns, "N_NOTCH": lod0_spec.notch_segments,
        "N_STRAIGHT": lod0_spec.straight_intervals,
        "N_TAPER_B1": lod0_spec.taper_intervals, "N_TAPER_B2": lod0_spec.tip_intervals,
        "HOLE_SEG_PER_WEDGE": lod0_spec.hole_segments, "hole_segments_total": hole_total,
        "hub_segments_total": lod0_spec.hub_segments * o.n,
        "hub_to_hole_ratio": (lod0_spec.hub_segments // lod0_spec.hole_segments
                              if lod0_spec.has_hole else None),
        "X_TAPER_mm": o.x_taper / MM, "X_RUNOUT_mm": o.x_runout / MM, "X_APEX_mm": o.x_apex / MM,
        "taper_len_mm": o.taper_len / MM,
        "bevel_offset_mm": o.bevel_offset / MM, "bevel_y_inset_mm": o.bevel_y / MM,
        "bevel_segments": lod0_spec.bevel_segments, "bevel_runout_mm": o.bevel_runout / MM,
        "hole_polygon_radius_mm": o.hole_polygon_radius(hole_total) / MM if hole_total else None,
    }
    report["mesh_stats"] = _round_stats(lod_stats[0])
    report["lod_mesh_stats"] = {obj.name: _round_stats(st) for obj, st in zip(lod_objects, lod_stats)}
    report["lod_params"] = {obj.name: asdict(used) for obj, used in zip(lod_objects, lod_used)}
    report["lod_group"] = group.name
    report["objects"] = [obj.name for obj in lod_objects]
    report["sockets"] = [s.name for s in pipeline.socket_children(lod0)]
    report["hull"]["name"] = hull.name   # make_lod_group renamed it alongside the mesh
    report["socket_records"] = [pipeline.socket_record(lod0, s) for s in pipeline.socket_children(lod0)]
    report["wear_mask_radius_mm"] = [round(v / MM, 6) for v in wear_range(o)]
    report["material"] = MATERIAL_NAME

    tri_counts = {obj.name: triangles_of(obj) for obj in lod_objects}
    bands = [used.band for used in lod_used]
    report["triangles"] = tri_counts
    report["lod_triangles"] = [tri_counts[obj.name] for obj in lod_objects]
    report["lod_bands"] = {f"LOD{i}": list(band) for i, band in enumerate(bands)}
    report["lod_bands_ok"] = [band[0] <= tri_counts[obj.name] <= band[1]
                              for obj, band in zip(lod_objects, bands)]
    report["lod_screen_sizes"] = list(LOD_SCREEN_SIZES[:len(lod_objects)])
    report["lod_surfaces"] = {obj.name: surface_snapshot(obj, o.n) for obj in lod_objects}
    deviations = {obj.name: lod_deviation(lod0, obj, split_radius=o.r_hub) for obj in lod_objects[1:]}
    report["lod_surface_deviation_mm"] = {name: d["lod0_vertices_to_lod"] for name, d in deviations.items()}
    report["lod_surface_deviation_two_sided_mm"] = deviations
    if len(lod_objects) > 1:
        lod1 = lod_objects[1]
        s0, s1 = report["lod_surfaces"][lod0.name], report["lod_surfaces"][lod1.name]
        report["lod1_is_distinct"] = {
            "triangle_reduction": round(1.0 - tri_counts[lod1.name] / tri_counts[lod0.name], 4),
            "volume_delta_mm3": round(s1["volume_mm3"] - s0["volume_mm3"], 6),
            "surface_area_delta_mm2": round(s1["surface_area_mm2"] - s0["surface_area_mm2"], 6),
            "max_surface_deviation_mm": deviations[lod1.name]["two_sided"],
            "rev2_metric_lod0_vertices_to_lod1_mm": deviations[lod1.name]["lod0_vertices_to_lod"],
            "note": ("LODs are authored by the radial-star generator at reduced segment counts "
                     "(study 4's table), not decimated, so LOD1 is a genuinely different mesh: "
                     "its hole ring and bevel segments are halved. max_surface_deviation_mm is "
                     "two-sided (vertices, edge midpoints and triangle centroids of each mesh "
                     "against the other's surface); the rev2 metric (LOD0 vertices only) is kept "
                     "for comparison with rev 2's 1e-6 mm."),
        }

    report["measured"] = measure(lod0, spec, lod_used[0])
    report["lod_measured"] = {obj.name: measure(obj, spec, used)
                              for obj, used in zip(lod_objects[1:], lod_used[1:])}
    report["uv"] = uv_coverage(lod0, texture_size=options.texel_map)
    report["lod_uv"] = {obj.name: uv_coverage(obj, texture_size=options.texel_map) for obj in lod_objects[1:]}
    symmetry = {obj.name: cn_deviation(obj, o.n) for obj in lod_objects}
    report[f"c{o.n}_max_deviation_mm"] = symmetry
    report["symmetry"] = {
        "order": o.n, "max_deviation_mm": symmetry,
        "method": (f"max nearest-neighbour distance after a 360/{o.n} deg rotation of the stored "
                   "(float32) vertices. Quarter-turn forms are exact (0.0); any other n is exact in "
                   "topology and float64 authoring, and lands within float32 storage precision "
                   "(a few nm) on the stored mesh")}

    qa = pipeline.qa_check([obj.name for obj in lod_objects], budget_tris=options.budget, require_ucx=True)
    report["qa"] = qa
    report["qa_failures"] = [c for c in qa["checks"] if not c["passed"]]
    report["qa_check_names"] = sorted({c["name"] for c in qa["checks"]})
    report["lod_strategy"] = {
        "method": "parametric: every LOD authored by shuriken_lib.geometry at its own segment counts",
        "table": "study 4: LOD0 full outline, bevels, hole ring; LOD1 halve the hole ring and bevel "
                 "segments; LOD2 drop the bevel and the hole entirely",
        "replaces": "rev 2 pipeline.decimate_lods (Collapse Decimate of LOD0)",
        "naming": "LODn objects are created as <mesh>_LODn, and pipeline.make_lod_group renames LOD0 "
                  "with its UCX_/SOCKET_ children, so the hull stays UCX_<mesh>_LOD0_00",
    }
    return FormBuild(form=form, collection=coll, lod_objects=lod_objects, hull=hull, group=group,
                     report=report, started=started)


def export_form(fb: FormBuild, options: BuildOptions) -> None:
    report = fb.report
    if options.no_export:
        report["export"] = None
        return
    fbx_path = options.fbx_path(fb.form)
    fbx_path.parent.mkdir(parents=True, exist_ok=True)
    export = pipeline.export_fbx(str(fbx_path), [fb.group.name], kind="static")
    report["export"] = export
    report["fbx"] = export["filepath"]
    report["sockets_sidecar"] = export.get("sidecar")


def render_form(fb: FormBuild, others: Sequence, options: BuildOptions) -> None:
    report = fb.report
    if options.no_render:
        report["renders"] = []
        report["render_stats"] = {}
        return
    lod0, lods = fb.lod_objects[0], fb.lod_objects[1:]
    helpers = [fb.hull] + list(pipeline.socket_children(lod0))
    written, stats, rig = render_previews(
        fb.form.name, fb.form.spec.outline(), lod0, lods, helpers, Path(options.render_dir),
        Path(options.diag_dir), options.samples, options.res, options.render_height,
        light_scale=options.light_scale, hide=others)
    report["renders"] = list(written.values())
    report["render_stats"] = stats
    report["render_rig"] = rig


GENERIC_GAPS = [
    "LOD UVs are independent Smart UV unwraps of each authored LOD, not LOD0's UVs carried "
    "down (rev 2's Decimate carried them, distorted at folds). Nothing ships a texture yet - "
    "M_Shuriken_Master is procedural in object space and the FBX carries only Principled "
    "scalars - so nothing is visible today, but a baked or UV-tiled texture would change "
    "layout at each LOD switch. Before the pack-atlas bake, LOD1/LOD2 UVs must be made "
    "consistent with LOD0: either analytic UVs emitted by the generator per face class, or "
    "a per-face-class transfer from LOD0's islands.",
    "No texture bake yet. The wear and grind are procedural and Cycles-only: they carry the "
    "renders, and the FBX exports only the Principled scalars, so nothing about them reaches "
    "the engine. The per-form wear radii travel as object custom properties "
    "(shuriken_wear_from / _to), which the FBX does not export (use_custom_props off).",
    "The imported material slot binds to WorldGridMaterial when the verification import runs "
    "with import_materials=False. The slot NAME (M_Shuriken_Master) survives the FBX, so "
    "slot-based assignment works; whether the pack ships a UE material asset is a listing "
    "decision, not a mesh defect.",
    "LightMapResolution is left at Unreal's default 64 for a ~10 cm prop, and the generated UV1 "
    "has never been exercised because the validation project sets r.AllowStaticLighting=False. "
    "Dropping it to 16 or 32 belongs to the Unreal-side import settings.",
]


def finalize_report(fb: FormBuild, blend: Path) -> dict:
    report = fb.report
    report["blend"] = str(blend)
    measured = report["measured"]
    uv = report.get("uv") or {}
    report["known_gaps"] = list(GENERIC_GAPS) + [
        f"LOD0 UV coverage is {uv.get('uv_square_coverage', 0) * 100:.1f}% of the square. On the "
        "four-point, sweeping the packer over 20 shape x margin combinations moved it only between "
        "26.0% and 32.0%, so the packer is not the limit - Smart UV Project's island shapes are. "
        "Hand-laying the shells belongs to the pack-atlas pass.",
    ]
    if fb.form.annotate is not None:
        fb.form.annotate(report)
    report["mass_check"] = {
        "measured_g": measured["mass_g"], "target_g": measured["mass_target_g"],
        "within_tolerance": measured["mass_within_tolerance"],
    }
    report["seconds"] = round(time.time() - fb.started, 2)
    return report


# =========================================================================== pack


def build_pack(forms: Sequence[Form], options: BuildOptions) -> Dict[str, dict]:
    """Rebuild the .blend from scratch with ``forms``; export and render each.  Returns reports."""
    names = [form.name for form in forms]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate forms: {names}")
    mesh_names = [form.spec.mesh_name for form in forms]
    if len(set(mesh_names)) != len(mesh_names):
        raise ValueError(f"two forms share a mesh name: {mesh_names}")

    reset_scene()
    material = build_material()
    builds = [build_form(form, material, options) for form in forms]

    blend_path = Path(options.blend)
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    for fb in builds:
        export_form(fb, options)
    for fb in builds:
        others = [obj for other in builds if other is not fb for obj in other.collection.all_objects]
        render_form(fb, others, options)
    return {fb.form.name: finalize_report(fb, blend_path) for fb in builds}


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")


def report_passed(report: dict) -> bool:
    return bool(report["qa"]["passed"]) and all(report["lod_bands_ok"])


def summary(report: dict) -> dict:
    return {
        "form": report["form"],
        "measured": report["measured"],
        "density": report["density"],
        "triangles": report["triangles"],
        "lod_bands_ok": report["lod_bands_ok"],
        "lod1_is_distinct": report.get("lod1_is_distinct"),
        "lod_surface_deviation_two_sided_mm": report["lod_surface_deviation_two_sided_mm"],
        "symmetry": report["symmetry"]["max_deviation_mm"],
        "uv": report["uv"],
        "mesh_stats": report["mesh_stats"],
        "hull": report["hull"],
        "sockets": report["sockets"],
        "qa_passed": report["qa"]["passed"],
        "qa_checks": len(report["qa"]["checks"]),
        "qa_failures": [f"{c['name']}[{c['object']}]: {c['detail']}" for c in report["qa_failures"]],
        "export_warnings": (report.get("export") or {}).get("warnings"),
        "renders": report["renders"],
        "render_stats": report["render_stats"],
        "seconds": report["seconds"],
    }


# =========================================================================== discovery + CLI


def load_form_module(path: Path):
    """Import a ``build_<form>.py`` without running it; return its FORM (or None)."""
    module_name = f"shuriken_form_{path.stem}"
    if module_name in sys.modules:
        module = sys.modules[module_name]
    else:
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return getattr(module, "FORM", None)


def discover_forms(directory: Path = FORMS_DIR) -> Dict[str, Form]:
    """Every ``build_*.py`` next to the library that defines ``FORM``, keyed by form name."""
    found: Dict[str, Form] = {}
    for path in sorted(Path(directory).glob("build_*.py")):
        if path.stem == "build_pack":
            continue
        form = load_form_module(path)
        if isinstance(form, Form):
            if form.name in found:
                raise ValueError(f"form {form.name!r} defined twice ({path})")
            found[form.name] = form
    return found


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Flags shared by every build script (rev 2's CLI, minus the per-form paths)."""
    parser.add_argument("--blend", default=str(DEFAULT_BLEND))
    parser.add_argument("--render-dir", default=str(DEFAULT_RENDER_DIR))
    parser.add_argument("--diag-dir", default=str(DEFAULT_DIAG))
    parser.add_argument("--budget", type=int, default=2500)
    parser.add_argument("--hull-verts", type=int, default=24)
    parser.add_argument("--island-margin", type=float, default=0.005)
    parser.add_argument("--texel-map", type=int, default=2048)
    parser.add_argument("--samples", type=int, default=220)
    parser.add_argument("--light-scale", type=float, default=1.0,
                        help="multiply every preview lamp, for re-tuning exposure")
    parser.add_argument("--res", type=int, default=1600,
                        help="render width; gallery images are 16:9 so they survive Fab's "
                             "1920x1080 thumbnail crop (study 7)")
    parser.add_argument("--res-y", type=int, default=0, help="render height (default res*9/16)")
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--no-render", action="store_true")


def options_from_args(args) -> BuildOptions:
    return BuildOptions(
        blend=Path(args.blend), render_dir=Path(args.render_dir), diag_dir=Path(args.diag_dir),
        export_dir=Path(getattr(args, "export_dir", DEFAULT_EXPORT_DIR)),
        report_dir=Path(getattr(args, "report_dir", DEFAULT_REPORT_DIR)),
        budget=args.budget, hull_verts=args.hull_verts, island_margin=args.island_margin,
        texel_map=args.texel_map, samples=args.samples, light_scale=args.light_scale,
        res=args.res, res_y=args.res_y, no_export=args.no_export, no_render=args.no_render)


def blender_argv(argv=None) -> List[str]:
    if argv is not None:
        return list(argv)
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def warn_if_pack_blend(forms: Sequence[Form], options: BuildOptions) -> Optional[str]:
    """A single-form run rebuilds the .blend from scratch: say so if it held more forms."""
    pack_report = Path(options.report_dir) / PACK_REPORT_NAME
    try:
        data = json.loads(pack_report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if Path(data.get("blend", "")).resolve() != Path(options.blend).resolve():
        return None
    lost = sorted(set(data.get("forms", [])) - {form.name for form in forms})
    if not lost:
        return None
    message = (f"WARNING: {options.blend} was last built by build_pack.py with {sorted(data['forms'])}; "
               f"this run rebuilds it from scratch WITHOUT {lost}. Re-run build_pack.py to restore them.")
    print(message)
    return message


def run_single(form: Form, args) -> int:
    """Entry point for a thin ``build_<form>.py``: rev 2's CLI, same outputs."""
    options = options_from_args(args)
    options.fbx_paths[form.name] = Path(args.fbx)
    options.report_paths[form.name] = Path(args.report)
    warning = warn_if_pack_blend([form], options)
    reports = build_pack([form], options)
    report = reports[form.name]
    if warning:
        report.setdefault("notes", []).append(warning)
    write_report(report, options.report_path(form))
    print("=== SHURIKEN REPORT ===")
    print(json.dumps(summary(report), indent=2))
    print("=== END REPORT ===")
    return 0 if report["qa"]["passed"] else 1


__all__ = [
    "BuildOptions", "DEFAULT_BLEND", "DEFAULT_DIAG", "DEFAULT_EXPORT_DIR", "DEFAULT_RENDER_DIR",
    "DEFAULT_REPORT_DIR", "Form", "FormBuild", "GENERIC_GAPS", "PACK", "PACK_REPORT_NAME",
    "add_common_args", "blender_argv", "build_form", "build_pack", "collection_name", "discover_forms",
    "export_form", "finalize_report", "load_form_module", "options_from_args", "render_form",
    "report_passed", "reset_scene", "run_single", "summary", "unwrap", "warn_if_pack_blend",
    "write_report",
]
