"""Build orchestration: one form or a whole pack, from scratch, through Scripts/pipeline.

Flow (the same for one form or eight):

    reset scene -> M_Shuriken_Master -> per form, in its own collection:
        LOD0..LODn authored by the generator, material, LOD0 Smart UV unwrap and LOD1..n
        UV0 transferred from LOD0's islands (one texture layout for the whole chain),
        UCX hull, sockets, LOD group (pipeline.make_lod_group renames LOD0 and its
        helpers together), measurement, symmetry, LOD deviation, topology, qa_check
    -> save the .blend ONCE (scripts are the source of truth; nothing is patched)
    -> per form: FBX + .sockets.json sidecar (one form per FBX: study 4, only the first
       mesh's collision imports from a multi-mesh file), with the pack's LOD screen sizes;
       SHA-256 of both recorded, so the Unreal evidence can be tied to these exact bytes
    -> per form: T_Shuriken_<Form>_BC / _ORM / _N baked from M_Shuriken_Master on LOD0's UV0
    -> per form: gallery renders from the BAKED maps only, every other form hidden, rig
       torn down after; wall / plate / UV gates
    -> per form JSON report (+ the pack report when run through build_pack.py)

The rig and the bake images are made after the save, so they never reach the .blend.
Unreal verification runs after the build, on the exported bytes, and
WorkFiles/shuriken/UnrealCheck6/attach_engine_check.py writes its result into each
report's ``engine_check`` (``pending`` until then).
"""
from __future__ import annotations

import argparse
import hashlib
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
from .bake import TEXTURE_SIZE, bake_form, preview_material
from .hooks import FormGeometry, RadialGeometry, geometry_of
from .material import MATERIAL_NAME, build_material
from .measure import (cn_deviation, evaluated_bm, lod_deviation, surface_snapshot, triangles_of, uv_coverage,
                      vertices_of)
from .render import plate_gate, render_previews, wall_gate
from .spec import MM, STUDY_LOD_SCREEN_SIZES, RadialStarSpec, screen_size_distance_m
from .uv import cross_lod_uv, transfer_uvs, uv_overlap_pairs

import pipeline  # noqa: E402  (Scripts/ is on sys.path via the package __init__)

PACK = "Shuriken"
DEFAULT_BLEND = PROJECT / "Assets" / "Shuriken.blend"
DEFAULT_EXPORT_DIR = PROJECT / "Exports" / "Shuriken"
DEFAULT_TEXTURE_DIR = DEFAULT_EXPORT_DIR / "Textures"
DEFAULT_RENDER_DIR = PROJECT / "Renders" / "Shuriken"
DEFAULT_REPORT_DIR = PROJECT / "WorkFiles" / "shuriken"
DEFAULT_DIAG = DEFAULT_REPORT_DIR / "diag"
PACK_REPORT_NAME = "pack_report.json"
FORMS_DIR = LIBRARY_DIR.parent
ENGINE_CHECK_DIR = DEFAULT_REPORT_DIR / "UnrealCheck6"
UNREAL_PROJECT = DEFAULT_REPORT_DIR / "UnrealShuriken" / "ShurikenValidation.uproject"
# Cross-LOD UV gate (shuriken_lib.uv): top plates must agree to half a texel at 2048,
# the whole surface within 8 px (half the 16 px bake padding), and no UV0 overlap.
UV_PLATE_MAX_PX = 0.5
UV_SURFACE_MAX_PX = 8.0


# =========================================================================== data


@dataclass
class Form:
    """A pack form: its spec, its generator hook and the form-only report text.

    ``annotate(report)`` runs after every generic figure is in the report (measured,
    renders, qa ...) and adds the form's originality notes, history and gaps.
    """

    spec: RadialStarSpec
    module_path: str = ""
    annotate: Optional[Callable[[dict], None]] = None
    report_name: Optional[str] = None
    # The generator hook (shuriken_lib.hooks.FormGeometry).  None = the radial-star path
    # (RadialGeometry of ``spec``); a non-radial form passes its own, e.g. the senban's
    # plate.SquarePlateGeometry.  ``spec`` then only needs form, mesh_name, title, revision,
    # lods, lod_screen_sizes, density_g_cm3 and physics_mass_kg.
    geometry: Optional[object] = None

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
    texture_dir: Path = DEFAULT_TEXTURE_DIR
    render_dir: Path = DEFAULT_RENDER_DIR
    diag_dir: Path = DEFAULT_DIAG
    report_dir: Path = DEFAULT_REPORT_DIR
    fbx_paths: Dict[str, Path] = field(default_factory=dict)       # form -> FBX override
    report_paths: Dict[str, Path] = field(default_factory=dict)    # form -> report override
    budget: int = 2500
    hull_verts: int = 24
    island_margin: float = 0.005
    texel_map: int = 2048
    texture_size: int = TEXTURE_SIZE
    samples: int = 220
    light_scale: float = 1.0
    res: int = 1600
    res_y: int = 0
    no_export: bool = False
    no_render: bool = False
    no_bake: bool = False

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
    material: object = None
    geometry: object = None


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

    LOD0 only: LOD1..n take their UV0 from LOD0's islands (shuriken_lib.uv), so one
    texture set serves the whole chain.  The islands are repacked with the concave,
    free-rotation packer.  Measured on the four-point, the packer is not what limits
    coverage: sweeping shape_method x margin_method x margin over 20 combinations moves
    UV square coverage only between 26.0% and 32.0%.  The limit is the island *shapes*
    Smart UV Project produces from this outline (long thin plate, chamfer and wall
    strips); getting past it means hand-laying the shells, which belongs to the
    pack-atlas pass.  0.005 is kept from rev 2 so the four-point's shipped LOD0 UVs do
    not change.
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


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mesh_volume_mm3(obj) -> float:
    bm = evaluated_bm(obj)
    try:
        return bm.calc_volume(signed=True) / MM ** 3
    finally:
        bm.free()


# =========================================================================== one form


def _round_stats(stats: dict) -> dict:
    return {k: (round(v, 12) if isinstance(v, float) else v) for k, v in stats.items()}


def lod_switching(spec: RadialStarSpec, lod0) -> dict:
    """Screen sizes as camera distances, so the thresholds can be judged in metres."""
    co = vertices_of(lod0)
    radius = float(max(math.sqrt(x * x + y * y + z * z) for x, y, z in co))
    sizes = list(spec.lod_screen_sizes[:len(spec.lods)])
    return {
        "screen_sizes": sizes,
        "study_4_table": list(STUDY_LOD_SCREEN_SIZES),
        "bounds_radius_mm": round(radius / MM, 4),
        "reference_view": "16:9, 90 deg horizontal FOV (Unreal ComputeBoundsScreenSize: S = 1.778 R / d)",
        "switch_distance_m": [None] + [round(screen_size_distance_m(s, radius), 4) for s in sizes[1:]],
        "study_table_switch_distance_m": [None] + [round(screen_size_distance_m(s, radius), 4)
                                                   for s in STUDY_LOD_SCREEN_SIZES[1:len(sizes)]],
        "star_height_px_at_switch_1080p": [None] + [round(s * 1080, 1) for s in sizes[1:]],
        "why": ("Study 4's 1.0 / 0.5 / 0.25 put LOD2 - no hole, no bevel - on screen from ~0.36 m, i.e. a "
                "star held in first person or lying on a table. The pack sets the thresholds from distance "
                "(LOD1 ~0.9 m, LOD2 ~2.5 m for a 5 cm radius) so each switch happens where the LOD's surface "
                "deviation is under a pixel or two. They travel in the .sockets.json sidecar "
                "(pipeline.export_fbx lod_screen_sizes) and ue_import_sockets applies them."),
    }


def build_form(form: Form, material, options: BuildOptions) -> FormBuild:
    """Author, dress and measure one form in its own collection.  Does not save or export.

    Everything form-specific goes through the form's generator hook (shuriken_lib.hooks):
    a radial star without one runs ``RadialGeometry``, which is 3.2's code path unchanged
    (same calls in the same order), so the stars rebuild bit-for-bit.
    """
    started = time.time()
    spec = form.spec
    geo = geometry_of(form)
    geo.validate()
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
        "build_to": geo.build_to(),
    }
    if geo.kind != "radial_star":
        report["geometry"] = geo.kind

    # --- LOD0: author, material, UVs, then the helpers that key to it.
    lod_objects, lod_used, lod_stats = [], [], []
    lod0, stats0, used0 = geo.author(0, spec.mesh_name, coll)
    lod0.data.materials.append(material)
    geo.tag(lod0)
    lod0["shuriken_form"] = spec.form
    lod0["shuriken_lod"] = 0
    margin = geo.island_margin(options.island_margin)
    unwrap(lod0, island_margin=margin)
    if margin != options.island_margin:
        report["uv_island_margin"] = {"used": margin, "pack_default": options.island_margin,
                                      "why": getattr(geo, "island_margin_reason", "")}
    lod_objects.append(lod0)
    lod_used.append(used0)
    lod_stats.append(stats0)
    bpy.context.view_layer.update()
    report["lod0_triangles_pre_group"] = triangles_of(lod0)

    hull, report["hull_method"] = geo.make_hull(lod0, options)
    report["hull"] = {"name": hull.name, "verts": len(hull.data.vertices),
                      "faces": len(hull.data.polygons)}
    geo.make_sockets(lod0)

    # --- LOD1..n: authored by the same generator at their own segment counts; UV0 from LOD0.
    report["uv_transfer"] = {}
    for level in range(1, len(spec.lods)):
        obj, stats, used = geo.author(level, f"{spec.mesh_name}_LOD{level}", coll)
        obj.data.materials.append(material)
        geo.tag(obj)
        obj["shuriken_form"] = spec.form
        obj["shuriken_lod"] = level
        report["uv_transfer"][obj.name] = transfer_uvs(lod0, obj)
        lod_objects.append(obj)
        lod_used.append(used)
        lod_stats.append(stats)

    group = pipeline.make_lod_group(spec.mesh_name, lod_objects)
    bpy.context.view_layer.update()
    lod0 = lod_objects[0]
    # make_lod_group renamed LOD0; key the transfer records by the final names
    report["uv_transfer"] = {obj.name: report["uv_transfer"][key]
                             for obj, key in zip(lod_objects[1:], list(report["uv_transfer"]))}

    report["density"] = geo.density(lod_used)
    report["mesh_stats"] = _round_stats(lod_stats[0])
    report["lod_mesh_stats"] = {obj.name: _round_stats(st) for obj, st in zip(lod_objects, lod_stats)}
    report["lod_params"] = {obj.name: asdict(used) for obj, used in zip(lod_objects, lod_used)}
    report["lod_group"] = group.name
    report["objects"] = [obj.name for obj in lod_objects]
    report["sockets"] = [s.name for s in pipeline.socket_children(lod0)]
    report["hull"]["name"] = hull.name   # make_lod_group renamed it alongside the mesh
    report["socket_records"] = [pipeline.socket_record(lod0, s) for s in pipeline.socket_children(lod0)]
    report["wear_mask_radius_mm"] = [round(v / MM, 6) for v in geo.wear_range()]
    report["material"] = MATERIAL_NAME
    report["material_nodes"] = len(material.node_tree.nodes)

    tri_counts = {obj.name: triangles_of(obj) for obj in lod_objects}
    bands = [used.band for used in lod_used]
    report["triangles"] = tri_counts
    report["lod_triangles"] = [tri_counts[obj.name] for obj in lod_objects]
    report["lod_bands"] = {f"LOD{i}": list(band) for i, band in enumerate(bands)}
    report["lod_bands_ok"] = [band[0] <= tri_counts[obj.name] <= band[1]
                              for obj, band in zip(lod_objects, bands)]
    report["lod_screen_sizes"] = list(spec.lod_screen_sizes[:len(lod_objects)])
    report["lod_switching"] = lod_switching(spec, lod0)
    extra = geo.lod_switching_extra(report)
    if extra:
        report["lod_switching"].update(extra)
    n = geo.order
    report["lod_surfaces"] = {obj.name: surface_snapshot(obj, n) for obj in lod_objects}
    deviations = {obj.name: lod_deviation(lod0, obj, split_radius=geo.split_radius()) for obj in lod_objects[1:]}
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
            "note": geo.lod_note(),
        }

    report["measured"] = geo.measure(lod0, lod_used[0])
    report["lod_measured"] = {obj.name: geo.measure(obj, used)
                              for obj, used in zip(lod_objects[1:], lod_used[1:])}
    report["topology_quality"] = {obj.name: geo.topology_quality(obj) for obj in lod_objects}
    report["uv"] = uv_coverage(lod0, texture_size=options.texel_map)
    report["lod_uv"] = {obj.name: uv_coverage(obj, texture_size=options.texel_map) for obj in lod_objects[1:]}
    report["cross_lod_uv"] = {obj.name: cross_lod_uv(lod0, obj, texture_size=options.texel_map)
                              for obj in lod_objects[1:]}
    overlaps = {obj.name: uv_overlap_pairs(obj) for obj in lod_objects}
    report["uv_consistency"] = {
        "method": "LOD1..n UV0 from LOD0's island maps (shuriken_lib.uv); one texture set for every LOD",
        "overlap_pairs": overlaps,
        "gate": {"top_plate_max_px": UV_PLATE_MAX_PX, "surface_max_px": UV_SURFACE_MAX_PX, "overlap_pairs": 0},
        "passed": bool(all(v == 0 for v in overlaps.values()) and all(
            c["top_plate"]["max_px"] <= UV_PLATE_MAX_PX and c["surface"]["max_px"] <= UV_SURFACE_MAX_PX
            for c in report["cross_lod_uv"].values())),
    }
    symmetry = {obj.name: cn_deviation(obj, n) for obj in lod_objects}
    report[f"c{n}_max_deviation_mm"] = symmetry
    report["symmetry"] = {"order": n, "max_deviation_mm": symmetry, "method": geo.symmetry_method()}
    extra = geo.symmetry_extra(lod_objects)
    if extra:
        report["symmetry"].update(extra)

    measured = report["measured"]
    hull_volume = mesh_volume_mm3(hull)
    report["physics"] = {
        "mass_kg_override": spec.physics_mass_kg,
        "source": "SHURIKEN_STUDY.md 4, Physics: set an explicit Mass in KG override",
        "measured_mass_kg": round(measured["mass_g"] / 1000.0, 5),
        "hull_volume_mm3": round(hull_volume, 3),
        "hull_volume_at_steel_density_kg": round(hull_volume * 1e-3 * spec.density_g_cm3 / 1000.0, 5),
        "applies": ("Not carried by the FBX or the sidecar, and not applied by the import scripts: set it on the "
                    "StaticMeshComponent's Body Instance (Physics > Mass (kg) override) in the Blueprint that "
                    "throws the star, and say so in the Fab description."),
        "note": ("hull_volume_at_steel_density_kg is the UCX hull volume times 7.85 g/cm3, shown only to say how "
                 "far a hull-volume mass at steel density would overstate the star. It is NOT Unreal's own "
                 "figure: without an override Unreal derives mass from the collision volume and the physical "
                 "material's density (default 1 g/cm3) with RaiseMassToPower 0.75, which was not measured here "
                 "(StaticMeshComponent.get_mass needs Simulate Physics; UnrealCheck5/mass_diag.json)."),
    }

    qa = pipeline.qa_check([obj.name for obj in lod_objects], budget_tris=options.budget, require_ucx=True)
    report["qa"] = qa
    report["qa_failures"] = [c for c in qa["checks"] if not c["passed"]]
    report["qa_check_names"] = sorted({c["name"] for c in qa["checks"]})
    report["lod_strategy"] = dict(geo.lod_strategy())
    report["lod_strategy"]["screen_sizes"] = report["lod_screen_sizes"]
    return FormBuild(form=form, collection=coll, lod_objects=lod_objects, hull=hull, group=group,
                     report=report, started=started, material=material, geometry=geo)


def export_form(fb: FormBuild, options: BuildOptions) -> None:
    report = fb.report
    if options.no_export:
        report["export"] = None
        return
    fbx_path = options.fbx_path(fb.form)
    fbx_path.parent.mkdir(parents=True, exist_ok=True)
    export = pipeline.export_fbx(str(fbx_path), [fb.group.name], kind="static",
                                 lod_screen_sizes=list(fb.form.spec.lod_screen_sizes[:len(fb.lod_objects)]))
    report["export"] = export
    report["fbx"] = export["filepath"]
    report["sockets_sidecar"] = export.get("sidecar")
    report["export_sha256"] = {"fbx": sha256(export["filepath"]),
                               "sidecar": sha256(export["sidecar"]) if export.get("sidecar") else None,
                               "note": ("FBX bytes change on every export (header timestamp, object UIDs); "
                                        "the Unreal evidence is tied to these exact bytes by this hash")}


def bake_textures(fb: FormBuild, options: BuildOptions) -> None:
    report = fb.report
    if options.no_bake:
        report["textures"] = None
        return
    started = time.time()
    report["textures"] = bake_form(fb.lod_objects[0], fb.material, Path(options.texture_dir),
                                   size=options.texture_size)
    report["textures"]["seconds"] = round(time.time() - started, 2)
    report["textures"]["shared_by_lods"] = [obj.name for obj in fb.lod_objects]


def render_form(fb: FormBuild, others: Sequence, options: BuildOptions) -> None:
    report = fb.report
    if options.no_render:
        report["renders"] = []
        report["render_stats"] = {}
        report["render_gates"] = None
        return
    lod0, lods = fb.lod_objects[0], fb.lod_objects[1:]
    helpers = [fb.hull] + list(pipeline.socket_children(lod0))
    beauty = None
    textures = report.get("textures")
    if textures:
        beauty = preview_material(f"M_Preview_Baked_{fb.form.spec.mesh_name}", textures["maps"],
                                  uv_map=textures["uv_map"])
    sizes = report["lod_screen_sizes"]

    def fmt(value: float) -> str:
        return f"{value:.2f}" if round(value, 2) == value else f"{value:.3f}"

    labels = []
    for i, obj in enumerate(fb.lod_objects):
        tris = f"{report['triangles'][obj.name]:,} tris"
        if i == 0:
            band = f"screen size > {fmt(sizes[1])}" if len(sizes) > 1 else "all distances"
        elif i + 1 < len(sizes):
            band = f"screen size {fmt(sizes[i + 1])} - {fmt(sizes[i])}"
        else:
            band = f"screen size < {fmt(sizes[i])}"
        labels.append(f"LOD{i}   {tris}\n{band}")
    written, stats, rig = render_previews(
        fb.form.name, fb.geometry.render_outline(), lod0, lods, helpers, Path(options.render_dir),
        Path(options.diag_dir), options.samples, options.res, options.render_height,
        light_scale=options.light_scale, hide=others, beauty_material=beauty, lod_labels=labels)
    if beauty is not None:
        for node in beauty.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                bpy.data.images.remove(node.image)
        bpy.data.materials.remove(beauty)
    report["renders"] = list(written.values())
    report["render_stats"] = stats
    report["render_rig"] = rig
    persp, top = stats.get(f"{fb.form.name}_persp", {}), stats.get(f"{fb.form.name}_top", {})
    report["render_gates"] = {
        "beauty_source": ("baked textures only (T_Shuriken_*_BC/_ORM/_N via a preview material)" if beauty
                          else "procedural M_Shuriken_Master: INTERNAL REVIEW ONLY, not a listing image"),
        "hero_walls": wall_gate(persp),
        "hero_plate": plate_gate(persp),
        "top_plate": plate_gate(top),
    }
    report["render_gates"]["passed"] = bool(beauty is not None and all(
        g["passed"] for k, g in report["render_gates"].items() if isinstance(g, dict)))


GENERIC_GAPS = [
    "The baked maps are 2048 px per form on a Smart UV layout at ~32 % coverage; the pack atlas (study 4: one "
    "2K atlas, or 1K per star) needs hand-laid shells first. The Unreal side has no M_Shuriken_Master / "
    "MI_Shuriken_Blackened asset yet: the validation import runs with import_materials=False, so the slot binds "
    "to WorldGridMaterial until the pack's material is built and the three maps are assigned.",
    "The FBX carries only UV0. UV1 (lightmap) exists only because the import generates it (Generate Lightmap "
    "UVs ON, src 0 -> dst 1, LightMapCoordinateIndex 1, measured in UnrealCheck5/6): the Fab description and "
    "import notes must say so, or a buyer importing with other settings gets no lightmap channel. "
    "LightMapResolution is left at Unreal's default 64.",
    "Wear, grind and scratches are procedural in M_Shuriken_Master and reach the engine only through the baked "
    "maps; the per-form wear radii, point count and hub radius travel as object custom properties "
    "(shuriken_wear_from / _to, shuriken_points, shuriken_hub_r), which the FBX does not export "
    "(use_custom_props off) - they matter only to the bake.",
]


def engine_check(form: Form, report: dict) -> dict:
    """Build-time pointer; the verified result is attached after the Unreal passes run."""
    sha = report.get("export_sha256") or {}
    return {
        "status": "pending",
        "matches_this_build": False,
        "note": ("Written 'pending' by the build. The Unreal 5.8 passes run on the exported bytes afterwards "
                 "(UnrealCheck6: pass 1 import + sidecar, pass 2 fresh-process gates, pass 3 export of the saved "
                 "asset + Blender round trip), and attach_engine_check.py writes the result here only when the "
                 "SHA-256 of the FBX and sidecar Unreal imported equal fbx_sha256 / sidecar_sha256 below."),
        "project": str(UNREAL_PROJECT),
        "scripts": [str(ENGINE_CHECK_DIR / name) for name in ("uc6_common.py", "pass1_import.py", "pass2_reload.py",
                                                            "pass3_export_diag.py", "roundtrip_compare.py",
                                                            "run_pass.ps1", "attach_engine_check.py")],
        "run_with": f"SHURIKEN_FORM={form.name}",
        "fbx_sha256": sha.get("fbx"),
        "sidecar_sha256": sha.get("sidecar"),
        "gates": ["engine LOD triangle counts equal the Blender counts exactly",
                  f"LOD screen sizes read back as {report.get('lod_screen_sizes')} in a fresh process",
                  "exactly one convex hull, both sockets at relative scale 1, bounds equal the measured size",
                  "LightMapCoordinateIndex 1 with a generated UV1 on every LOD",
                  "Unreal's own FBX export of the saved asset: hull and positions equal the shipped FBX",
                  "zero Warning or Error lines in the commandlet logs"],
    }


def finalize_report(fb: FormBuild, blend: Path) -> dict:
    report = fb.report
    report["blend"] = str(blend)
    measured = report["measured"]
    uv = report.get("uv") or {}
    report["engine_check"] = engine_check(fb.form, report)
    report["known_gaps"] = list(GENERIC_GAPS) + [
        f"LOD0 UV coverage is {uv.get('uv_square_coverage', 0) * 100:.1f}% of the square. On the "
        "four-point, sweeping the packer over 20 shape x margin combinations moved it only between "
        "26.0% and 32.0%, so the packer is not the limit - Smart UV Project's island shapes are. "
        "Hand-laying the shells belongs to the pack-atlas pass.",
        f"Physics: the study-4 Mass in KG override ({fb.form.spec.physics_mass_kg} kg) is recorded here only; "
        "it has to be set on the component in the Blueprint (see physics.applies).",
    ]
    if fb.form.annotate is not None:
        fb.form.annotate(report)
    if not report["engine_check"].get("matches_this_build"):
        report["known_gaps"].append(
            "ENGINE CHECK PENDING: Unreal 5.8 verification of THIS export is not attached yet "
            "(engine_check.status). Run WorkFiles/shuriken/UnrealCheck6 passes 1-3 and attach_engine_check.py.")
    report["mass_check"] = {
        "measured_g": measured["mass_g"], "target_g": measured["mass_target_g"],
        "within_tolerance": measured["mass_within_tolerance"],
    }
    report["gates"] = {
        "qa_check": bool(report["qa"]["passed"]),
        "lod_bands": all(report["lod_bands_ok"]),
        "uv_consistency": bool(report["uv_consistency"]["passed"]),
        "textures_baked": bool(report.get("textures")),
        "render_gates": (report.get("render_gates") or {}).get("passed"),
    }
    report["seconds"] = round(time.time() - fb.started, 2)
    return report


# =========================================================================== pack


def build_pack(forms: Sequence[Form], options: BuildOptions) -> Dict[str, dict]:
    """Rebuild the .blend from scratch with ``forms``; export, bake and render each.  Returns reports."""
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
        bake_textures(fb, options)
    for fb in builds:
        others = [obj for other in builds if other is not fb for obj in other.collection.all_objects]
        render_form(fb, others, options)
    return {fb.form.name: finalize_report(fb, blend_path) for fb in builds}


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")


def report_passed(report: dict, require_renders: bool = True) -> bool:
    gates = report.get("gates") or {}
    passed = bool(report["qa"]["passed"]) and all(report["lod_bands_ok"]) and bool(gates.get("uv_consistency"))
    if report.get("renders") and require_renders:
        passed = passed and bool(gates.get("render_gates"))
    return passed


def summary(report: dict) -> dict:
    return {
        "form": report["form"],
        "measured": report["measured"],
        "density": report["density"],
        "triangles": report["triangles"],
        "lod_bands_ok": report["lod_bands_ok"],
        "lod_screen_sizes": report.get("lod_screen_sizes"),
        "lod1_is_distinct": report.get("lod1_is_distinct"),
        "lod_surface_deviation_two_sided_mm": report["lod_surface_deviation_two_sided_mm"],
        "topology_quality": report.get("topology_quality"),
        "symmetry": report["symmetry"]["max_deviation_mm"],
        "uv": report["uv"],
        "uv_consistency": report.get("uv_consistency"),
        "cross_lod_uv": report.get("cross_lod_uv"),
        "mesh_stats": report["mesh_stats"],
        "hull": report["hull"],
        "sockets": report["sockets"],
        "qa_passed": report["qa"]["passed"],
        "qa_checks": len(report["qa"]["checks"]),
        "qa_failures": [f"{c['name']}[{c['object']}]: {c['detail']}" for c in report["qa_failures"]],
        "export_warnings": (report.get("export") or {}).get("warnings"),
        "export_sha256": report.get("export_sha256"),
        "textures": {k: v for k, v in (report.get("textures") or {}).items() if k in ("maps", "stats", "seconds")},
        "renders": report["renders"],
        "render_gates": report.get("render_gates"),
        "render_rig": report.get("render_rig"),
        "render_stats": report["render_stats"],
        "gates": report.get("gates"),
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
    parser.add_argument("--texture-dir", default=str(DEFAULT_TEXTURE_DIR),
                        help="where T_Shuriken_<Form>_BC/_ORM/_N.png are written")
    parser.add_argument("--texture-size", type=int, default=TEXTURE_SIZE)
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
    parser.add_argument("--no-bake", action="store_true",
                        help="skip the texture bake; renders then use the procedural material "
                             "and are marked internal review only")


def options_from_args(args) -> BuildOptions:
    return BuildOptions(
        blend=Path(args.blend), render_dir=Path(args.render_dir), diag_dir=Path(args.diag_dir),
        export_dir=Path(getattr(args, "export_dir", DEFAULT_EXPORT_DIR)),
        texture_dir=Path(args.texture_dir), texture_size=args.texture_size,
        report_dir=Path(getattr(args, "report_dir", DEFAULT_REPORT_DIR)),
        budget=args.budget, hull_verts=args.hull_verts, island_margin=args.island_margin,
        texel_map=args.texel_map, samples=args.samples, light_scale=args.light_scale,
        res=args.res, res_y=args.res_y, no_export=args.no_export, no_render=args.no_render,
        no_bake=args.no_bake)


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
    return 0 if report_passed(report) else 1


__all__ = [
    "BuildOptions", "DEFAULT_BLEND", "FormGeometry", "RadialGeometry", "geometry_of", "DEFAULT_DIAG", "DEFAULT_EXPORT_DIR", "DEFAULT_RENDER_DIR",
    "DEFAULT_REPORT_DIR", "DEFAULT_TEXTURE_DIR", "ENGINE_CHECK_DIR", "Form", "FormBuild", "GENERIC_GAPS", "PACK",
    "PACK_REPORT_NAME", "UNREAL_PROJECT", "add_common_args", "bake_textures", "blender_argv", "build_form",
    "build_pack", "collection_name", "discover_forms", "engine_check", "export_form", "finalize_report",
    "load_form_module", "lod_switching", "options_from_args", "render_form", "report_passed", "reset_scene",
    "run_single", "sha256", "summary", "unwrap", "warn_if_pack_blend", "write_report",
]
