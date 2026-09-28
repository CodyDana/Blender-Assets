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
    -> per form: T_Shuriken_<Form>_BC / _ORM / _N baked from M_Shuriken_Master on LOD0's UV0 (3.9.1: with
       --frozen-maps, a frozen form's fresh bake is checked against its snapshot maps and their bytes ship)
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
import numpy as np

from . import LIBRARY_DIR, PROJECT, VERSION
from .bake import TEXTURE_SIZE, bake_form, preview_material
from .hooks import FormGeometry, RadialGeometry, geometry_of
from .material import MATERIAL_NAME, build_material
from .measure import (cn_deviation, evaluated_bm, lod_deviation, surface_snapshot, triangles_of, uv_coverage,
                      vertices_of)
from .geometry import KNIFE_SHADING_GATE_DEG
from .render import bar_wall_gate, coat_gate, facet_gate, plate_gate, render_previews, wall_gate
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
UV_SQUARE_EPS = 1e-6      # float32 slack on the [0, 1] unit-square gate


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
    # 3.9.1: a regression snapshot's textures/ directory; a form whose three maps are in it is FROZEN: its fresh bake
    # is compared with them and, within the GPU bake's run-to-run noise (FROZEN_MAP_NOISE), the snapshot's bytes ship
    frozen_maps: Optional[Path] = None

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
    hulls: list = field(default_factory=list)     # 3.10: every UCX hull (a form may have several part hulls)


# =========================================================================== scene


def reset_scene() -> None:
    """Empty the factory-startup scene and set metric units at scale 1.0."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "MILLIMETERS"


def _project_hole_wall(obj, points: int, radius: float) -> int:
    """Overwrite the hole wall's UV0 with one planar projection per wedge (object units).

    Every face with a horizontal normal whose centroid lies inside ``radius`` belongs to the
    hole wall; it is grouped by the wedge its centroid falls in and projected along that
    wedge's arm direction (u along the wedge's tangent, v = z), the same kind of planar map
    Smart UV Project makes, so each wedge's hole faces form one affine island that the
    LOD1..n transfer (uv.lod0_island_maps) fits exactly.  Returns the number of faces done.
    """
    mesh = obj.data
    npoly = len(mesh.polygons)
    normals = np.empty(npoly * 3, dtype=np.float32)
    mesh.polygons.foreach_get("normal", normals)
    centres = np.empty(npoly * 3, dtype=np.float32)
    mesh.polygons.foreach_get("center", centres)
    normals, centres = normals.reshape(-1, 3), centres.reshape(-1, 3)
    hole = (np.abs(normals[:, 2]) < 0.01) & (np.hypot(centres[:, 0], centres[:, 1]) < radius)
    if not hole.any():
        return 0
    uv_layer = mesh.uv_layers[0].data
    sector = 2.0 * math.pi / points
    done = 0
    for f in np.nonzero(hole)[0]:
        poly = mesh.polygons[int(f)]
        wedge = int(round(math.atan2(centres[f, 1], centres[f, 0]) / sector)) % points
        angle = wedge * sector
        tx, ty = -math.sin(angle), math.cos(angle)          # the wedge's tangent direction
        for loop_index in poly.loop_indices:
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv_layer[loop_index].uv = (co.x * tx + co.y * ty, co.z)
        done += 1
    mesh.update()
    return done


def _project_walls(obj, classify) -> dict:
    """Overwrite chosen wall faces' UV0 with one planar projection per group, at the unwrap's scale.

    ``classify(centre, normal)`` returns ``(group key, (tx, ty))`` for a face to re-project (u =
    position . tangent, v = z) or None.  Knife grind pass: Smart UV Project split the thin wall
    strips (the notch walls, the arm edges' lands and the root run-out walls) into islands
    differently on every arm, so a coarser LOD's wall face (one chord per half notch, LOD2's
    root-to-shoulder run-out wall) straddled two LOD0 islands and its transferred UVs landed up to
    220 px away.  One planar island per notch and per arm-edge side (and per wedge of the hole
    wall, as before) makes every LODn wall face map through the island of the plane it lies in.
    The UVs are scaled to the smart-projected faces' own texel density (the hole wall used to be
    written in metres, ~16x under-sized).  The packer runs afterwards.  Returns counts per kind.
    """
    mesh = obj.data
    npoly = len(mesh.polygons)
    normals = np.empty(npoly * 3, dtype=np.float32)
    mesh.polygons.foreach_get("normal", normals)
    centres = np.empty(npoly * 3, dtype=np.float32)
    mesh.polygons.foreach_get("center", centres)
    normals, centres = normals.reshape(-1, 3), centres.reshape(-1, 3)
    picks = {}
    for f in range(npoly):
        group = classify(centres[f], normals[f])
        if group is not None:
            picks[f] = group
    if not picks:
        return {}
    uv_layer = mesh.uv_layers[0].data
    world, uv_area = 0.0, 0.0
    for poly in mesh.polygons:
        if poly.index in picks:
            continue
        uvs = [uv_layer[i].uv for i in poly.loop_indices]
        twice = sum(a.x * b.y - b.x * a.y for a, b in zip(uvs, uvs[1:] + uvs[:1]))
        uv_area += 0.5 * abs(twice)
        world += poly.area
    scale = math.sqrt(uv_area / world) if world > 0.0 and uv_area > 0.0 else 1.0
    counts: dict = {}
    for f, (key, (tx, ty)) in picks.items():
        poly = mesh.polygons[f]
        for loop_index in poly.loop_indices:
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv_layer[loop_index].uv = (scale * (co.x * tx + co.y * ty), scale * co.z)
        kind = key[0] if isinstance(key, tuple) else str(key)
        counts[kind] = counts.get(kind, 0) + 1
    mesh.update()
    counts["uv_per_m"] = round(scale, 4)
    return counts


def _plug_hole(obj, radius: float) -> int:
    """Close the round hole with one n-gon per face (top and bottom) and return how many were added.

    The plugs exist only while the islands are unwrapped and packed: they make the plate
    islands solid in UV space, so the concave packer cannot nest small islands inside the
    hole - where a hole-less LOD2's hub fan (its centre corner maps into the hole) would
    overlap them and the transfer would have to clamp the fan.  ``_unplug_hole`` removes
    them again (faces only; the hole ring's vertices and edges belong to the hole wall).
    """
    import bmesh

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    top, bottom = [], []
    for face in bm.faces:
        centre = face.calc_center_median()
        if abs(face.normal.z) < 0.01 and math.hypot(centre.x, centre.y) < radius:
            for v in face.verts:
                (top if v.co.z > 0.0 else bottom).append(v)
    added = 0
    for ring in (top, bottom):
        verts = sorted(set(ring), key=lambda v: math.atan2(v.co.y, v.co.x))
        if len(verts) >= 3:
            bm.faces.new(verts)
            added += 1
    if added:
        bm.to_mesh(mesh)
        mesh.update()
    bm.free()
    return added


def _unplug_hole(obj, count: int) -> None:
    """Remove the last ``count`` faces (the plugs appended by ``_plug_hole``), faces only."""
    import bmesh

    if not count:
        return
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    plugs = [bm.faces[i] for i in range(len(bm.faces) - count, len(bm.faces))]
    bmesh.ops.delete(bm, geom=plugs, context="FACES_ONLY")
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()


def uv_islands(obj, uv_match: float = 1e-7):
    """UV0 islands of ``obj``: (island index per polygon, number of islands).  Two polygons share an island when
    they share an edge whose two corners carry the same UVs on both sides (``uv.lod0_island_maps``' rule)."""
    mesh = obj.data
    npoly, nloop = len(mesh.polygons), len(mesh.loops)
    loop_vert = np.empty(nloop, dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vert)
    start = np.empty(npoly, dtype=np.int64)
    total = np.empty(npoly, dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", start)
    mesh.polygons.foreach_get("loop_total", total)
    uv = np.empty(nloop * 2, dtype=np.float32)
    mesh.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    parent = list(range(npoly))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    edges: Dict[tuple, list] = {}
    for f in range(npoly):
        s, t = int(start[f]), int(total[f])
        for k in range(t):
            la, lb = s + k, s + (k + 1) % t
            va, vb = int(loop_vert[la]), int(loop_vert[lb])
            edges.setdefault((min(va, vb), max(va, vb)), []).append((f, {va: uv[la], vb: uv[lb]}))
    for key, owners in edges.items():
        if len(owners) != 2:
            continue
        (f1, d1), (f2, d2) = owners
        if all(np.abs(d1[v] - d2[v]).max() <= uv_match for v in key):
            parent[find(f1)] = find(f2)
    roots = sorted({find(f) for f in range(npoly)})
    index = {r: i for i, r in enumerate(roots)}
    return np.array([index[find(f)] for f in range(npoly)], dtype=np.int64), len(roots)


def _mirror_underside_islands(obj) -> dict:
    """3.9.1 (the hooked cross, visual review): mirror in U every UV0 island that faces -Z, in place, before the packer.

    Smart UV Project maps each island as seen along its own normal, so the bottom plate's island is the plate seen
    from BELOW - on a chiral outline the baked texture sheets then carry the mirrored form as a flat picture, visible
    to anyone who opens the PNGs, a Content Browser thumbnail or a texture preview, without turning the model over.
    Mirrored in U, every -Z island reads as seen from +Z (the presented face).  The packer that runs afterwards
    rotates, scales and translates islands but never mirrors them, and ``uv.lod0_island_maps`` fits an affine map
    whatever its determinant, so the LOD transfer is unchanged.  A mirrored island is ordinary for a tangent-space
    normal map: MikkTSpace (Blender's bake, Unreal's import) carries the bitangent sign per vertex.
    An island faces -Z when its area-weighted mean normal has z < -0.5 (the plate, the facets and the chamfers of
    the underside; the walls are vertical and stay as they are)."""
    mesh = obj.data
    island_of, count = uv_islands(obj)
    npoly = len(mesh.polygons)
    normals = np.empty(npoly * 3, dtype=np.float32)
    mesh.polygons.foreach_get("normal", normals)
    areas = np.empty(npoly, dtype=np.float32)
    mesh.polygons.foreach_get("area", areas)
    start = np.empty(npoly, dtype=np.int64)
    total = np.empty(npoly, dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", start)
    mesh.polygons.foreach_get("loop_total", total)
    nz = normals.reshape(-1, 3)[:, 2].astype(np.float64)
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    mesh.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    mirrored, faces = [], 0
    for island in range(count):
        members = np.nonzero(island_of == island)[0]
        weight = float(areas[members].sum())
        if weight <= 0.0 or float((nz[members] * areas[members]).sum()) / weight >= -0.5:
            continue
        loops = np.concatenate([np.arange(start[f], start[f] + total[f]) for f in members])
        centre = 0.5 * (float(uv[loops, 0].min()) + float(uv[loops, 0].max()))
        uv[loops, 0] = 2.0 * centre - uv[loops, 0]
        mirrored.append(int(island))
        faces += int(len(members))
    if mirrored:
        mesh.uv_layers[0].data.foreach_set("uv", uv.ravel())
        mesh.update()
    return {"islands_before_pack": int(count), "mirrored_underside_islands": len(mirrored),
            "mirrored_faces": faces,
            "rule": "UV0 islands facing -Z (area-weighted mean normal z < -0.5) mirrored in U before the packer, so "
                    "every plate island of the texture sheets reads as seen from the presented +Z face"}


def uv_tile_check(obj, tiles: dict) -> dict:
    """3.10: every face's UV0 inside the unit tile of its material slot (``tiles``: slot -> (u_min, u_max)), v in 0..1."""
    mesh = obj.data
    npoly = len(mesh.polygons)
    mat_index = np.empty(npoly, dtype=np.int64)
    mesh.polygons.foreach_get("material_index", mat_index)
    start = np.empty(npoly, dtype=np.int64)
    total = np.empty(npoly, dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", start)
    mesh.polygons.foreach_get("loop_total", total)
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    mesh.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    out = {"slots": {}, "rule": "every face's UV0 inside its material slot's unit tile (u tile, v 0..1)"}
    ok = True
    for slot, (lo, hi) in tiles.items():
        faces = np.nonzero(mat_index == int(slot))[0]
        if not len(faces):
            out["slots"][str(slot)] = {"faces": 0}
            continue
        loops = np.concatenate([np.arange(start[f], start[f] + total[f]) for f in faces])
        us, vs = uv[loops, 0], uv[loops, 1]
        inside = bool(us.min() >= lo - UV_SQUARE_EPS and us.max() <= hi + UV_SQUARE_EPS
                      and vs.min() >= -UV_SQUARE_EPS and vs.max() <= 1.0 + UV_SQUARE_EPS)
        out["slots"][str(slot)] = {"faces": int(len(faces)), "tile_u": [lo, hi],
                                   "u_range": [round(float(us.min()), 6), round(float(us.max()), 6)],
                                   "v_range": [round(float(vs.min()), 6), round(float(vs.max()), 6)], "inside": inside}
        ok = ok and inside
    unassigned = int(np.count_nonzero(~np.isin(mat_index, [int(k) for k in tiles])))
    out["faces_in_no_listed_slot"] = unassigned
    out["passed"] = bool(ok and unassigned == 0)
    return out


def unwrap(obj, island_margin: float = 0.005, hole_projection=None, wall_projection=None,
           mirror_underside: bool = False) -> dict:
    """Smart UV Project (study 4 / guidelines 6.4 want a real, non-overlapping unwrap).

    LOD0 only: LOD1..n take their UV0 from LOD0's islands (shuriken_lib.uv), so one
    texture set serves the whole chain.  The islands are repacked with the concave,
    free-rotation packer.  Measured on the four-point, the packer is not what limits
    coverage: sweeping shape_method x margin_method x margin over 20 combinations moves
    UV square coverage only between 26.0% and 32.0%.  The limit is the island *shapes*
    Smart UV Project produces from this outline (long thin plate, chamfer and wall
    strips); getting past it means hand-laying the shells, which belongs to the
    pack-atlas pass.

    Style pass, for forms with a round hole (``hole_projection`` = ``(n, radius)`` from the
    form's hook): the hole is plugged with a temporary n-gon per face while the islands are
    projected and packed, so the plate islands are solid and the concave packer cannot nest
    islands inside the hole (a hole-less LOD2's hub fan maps its centre corner there and
    would overlap them); and the hole wall is re-projected as one planar island per wedge
    (``_project_hole_wall``), so no coarser LOD's hole face straddles two islands.  The
    plugs are removed before anything reads the mesh.

    Knife grind pass: ``wall_projection`` (the hook's classifier, see ``_project_walls``) puts
    every notch wall and every arm-edge wall side on one planar island, so LOD1..n's coarser wall
    faces transfer through the island of their own plane; it replaces the hole-only projection.

    3.9.1: ``mirror_underside`` (the hook's ``uv_mirror_underside``; False on every earlier form, whose path is
    unchanged) mirrors the -Z islands in U before the packer (``_mirror_underside_islands``) and records it under
    ``mirror_underside`` in the returned dict.
    """
    walls: dict = {}
    view_layer = bpy.context.view_layer
    for other in view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    view_layer.objects.active = obj
    plugs = _plug_hole(obj, hole_projection[1]) if hole_projection is not None else 0
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=island_margin,
                                 area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        if wall_projection is not None:
            walls = _project_walls(obj, wall_projection)
        elif hole_projection is not None:
            _project_hole_wall(obj, *hole_projection)
        if mirror_underside:
            walls["mirror_underside"] = _mirror_underside_islands(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", shape_method="CONCAVE",
                                margin_method="SCALED", margin=island_margin, scale=True)
        bpy.ops.object.mode_set(mode="OBJECT")
    finally:
        _unplug_hole(obj, plugs)
    obj.select_set(False)
    return walls


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


def lod_switching(spec: RadialStarSpec, lod0, radius: Optional[float] = None) -> dict:
    """Screen sizes as camera distances, so the thresholds can be judged in metres.

    ``radius`` (m, 3.8.1): the form's own bounds radius (the spike: Unreal's bounds sphere about the bounding-box
    centre, which its screen sizes are built from); None = the largest vertex distance from the origin, which is
    the same figure for every form whose origin is its bounding-box centre."""
    co = vertices_of(lod0)
    from_origin = float(max(math.sqrt(x * x + y * y + z * z) for x, y, z in co))
    extra = {}
    if radius is None:
        radius = from_origin
    else:
        extra = {"bounds_radius_definition": "the form's bounds_radius hook (Unreal's bounds sphere, bbox centre)",
                 "bounds_radius_from_origin_mm": round(from_origin / MM, 4)}
    sizes = list(spec.lod_screen_sizes[:len(spec.lods)])
    return {**extra,
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
    custom_uv = geo.custom_unwrap(lod0, margin)          # 3.8: a form's own LOD0 UV0 (the spike); None = Smart UV
    if custom_uv is None:
        report["uv_wall_islands"] = unwrap(lod0, island_margin=margin, hole_projection=geo.hole_projection(),
                                           wall_projection=geo.wall_projection(),
                                           mirror_underside=bool(getattr(geo, "uv_mirror_underside", False)))
    else:
        report["uv_layout"] = custom_uv
    if margin != options.island_margin:
        report["uv_island_margin"] = {"used": margin, "pack_default": options.island_margin,
                                      "why": getattr(geo, "island_margin_reason", "")}
    lod_objects.append(lod0)
    lod_used.append(used0)
    lod_stats.append(stats0)
    bpy.context.view_layer.update()
    report["lod0_triangles_pre_group"] = triangles_of(lod0)

    hull, report["hull_method"] = geo.make_hull(lod0, options)
    # 3.10 (the kunai): a form may return several part hulls (UCX_<mesh>_LOD0_00, _01, ...); a single hull is the old path
    hulls = list(hull) if isinstance(hull, (list, tuple)) else [hull]
    hull = hulls[0]
    report["hull"] = {"name": hull.name, "verts": len(hull.data.vertices),
                      "faces": len(hull.data.polygons)}
    if len(hulls) > 1:
        report["hull"]["count"] = len(hulls)
    geo.make_sockets(lod0)

    # --- LOD1..n: authored by the same generator at their own segment counts; UV0 from LOD0.
    report["uv_transfer"] = {}
    for level in range(1, len(spec.lods)):
        obj, stats, used = geo.author(level, f"{spec.mesh_name}_LOD{level}", coll)
        obj.data.materials.append(material)
        geo.tag(obj)
        obj["shuriken_form"] = spec.form
        obj["shuriken_lod"] = level
        own = geo.lod_uv(lod0, obj) if hasattr(geo, "lod_uv") else None    # 3.10: a form's own LOD1..n UV0
        report["uv_transfer"][obj.name] = own if own is not None else (
            transfer_uvs(lod0, obj, clamp_walls=True) if getattr(geo, "uv_clamp_walls", False)
            else transfer_uvs(lod0, obj))
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
    if len(hulls) > 1:
        report["hull"]["all"] = [{"name": h.name, "verts": len(h.data.vertices), "faces": len(h.data.polygons)}
                                 for h in hulls]
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
    report["lod_switching"] = lod_switching(spec, lod0, geo.bounds_radius(lod0))
    extra = geo.lod_switching_extra(report)
    if extra:
        report["lod_switching"].update(extra)
    n = geo.order
    report["lod_surfaces"] = {obj.name: (geo.surface_snapshot(obj) or surface_snapshot(obj, n)) for obj in lod_objects}
    deviations = {obj.name: lod_deviation(lod0, obj, split_radius=geo.split_radius()) for obj in lod_objects[1:]}
    headline = geo.lod_deviation_headline()
    report["lod_surface_deviation_mm"] = {name: d[headline] for name, d in deviations.items()}
    if headline != "lod0_vertices_to_lod":
        report["lod_surface_deviation_metric"] = headline
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
    texel_map = geo.texture_size(options.texel_map)      # 3.8.1: an int, or a form's (width, height)
    report["uv"] = uv_coverage(lod0, texture_size=texel_map)
    report["lod_uv"] = {obj.name: uv_coverage(obj, texture_size=texel_map) for obj in lod_objects[1:]}
    own_xlod = getattr(geo, "cross_lod_uv", None)       # 3.10: a form of interpenetrating shells compares per shell
    report["cross_lod_uv"] = {obj.name: ((own_xlod(lod0, obj, options.texel_map) if own_xlod is not None else None)
                                         or cross_lod_uv(lod0, obj, texture_size=options.texel_map))
                              for obj in lod_objects[1:]}
    overlaps = {obj.name: uv_overlap_pairs(obj) for obj in lod_objects}
    # Every LOD's UV0 inside the unit square (a corner past it would wrap under Unreal's
    # default texture addressing); uv.transfer_uvs clamps LOD1..n, LOD0 is the packer's.
    ranges = {lod0.name: report["uv"]}
    ranges.update(report["lod_uv"])
    in_square = {name: bool(r and r["u_range"][0] >= -UV_SQUARE_EPS and r["v_range"][0] >= -UV_SQUARE_EPS
                            and r["u_range"][1] <= 1.0 + UV_SQUARE_EPS and r["v_range"][1] <= 1.0 + UV_SQUARE_EPS)
                 for name, r in ranges.items()}
    tiles = getattr(geo, "uv_tiles", None)
    if tiles:
        # 3.10 (the kunai's two material slots): every slot's UV0 islands inside their OWN unit tile (the wrap slot's in
        # u 1..2, read by Wrap addressing from the same texels), so no UV0 triangle overlaps another across the slots
        per_slot = {obj.name: uv_tile_check(obj, tiles) for obj in lod_objects}
        in_square = {name: bool(r["passed"]) for name, r in per_slot.items()}
        report["uv_tiles"] = per_slot
    report["uv_consistency"] = {
        "method": "LOD1..n UV0 from LOD0's island maps (shuriken_lib.uv); one texture set for every LOD",
        "island_map_deviation_px_at_2048": {name: (t.get("island_map_deviation") or {}).get("max_px_at_2048")
                                            for name, t in report["uv_transfer"].items()},
        "island_map_deviation_note": ("information: per-loop distance of every LODn UV from the affine map of its "
                                      "LOD0 island (uv.transfer_uvs island_map_deviation)"),
        "overlap_pairs": overlaps,
        "in_unit_square": in_square,
        "gate": {"top_plate_max_px": UV_PLATE_MAX_PX, "surface_max_px": UV_SURFACE_MAX_PX, "overlap_pairs": 0,
                 "in_unit_square": True},
        "passed": bool(all(v == 0 for v in overlaps.values()) and all(in_square.values()) and all(
            c["top_plate"]["max_px"] <= UV_PLATE_MAX_PX and c["surface"]["max_px"] <= UV_SURFACE_MAX_PX
            for c in report["cross_lod_uv"].values())),
    }
    symmetry = {obj.name: geo.symmetry_deviation(obj) for obj in lod_objects}   # default: cn_deviation(obj, n)
    report[f"c{n}_max_deviation_mm"] = symmetry
    report["symmetry"] = {"order": n, "max_deviation_mm": symmetry, "method": geo.symmetry_method()}
    extra = geo.symmetry_extra(lod_objects)
    if extra:
        report["symmetry"].update(extra)

    measured = report["measured"]
    hull_volume = sum(mesh_volume_mm3(h) for h in hulls)
    ground_g = measured.get("ground_mass_g", measured["mass_g"])
    report["physics"] = {
        # decision B: the override comes from the GROUND (finished) mass, rounded to the gram
        "mass_kg_override": round(ground_g / 1000.0, 3),
        "mass_kg_override_exact": round(ground_g / 1000.0, 5),
        "source": (("the finished (knife-ground) LOD0 mesh volume x 7.85 g/cm3" if geo.noun == "star" else
                    f"the finished {geo.noun} (LOD0 mesh volume) x 7.85 g/cm3")
                   + " - SHURIKEN_STUDY.md 4, Physics: set an explicit Mass in KG override"),
        "study_4_table_kg": spec.physics_mass_kg,
        "outline_mass_kg": round(measured.get("outline_mass_g", measured["mass_g"]) / 1000.0, 5),
        "measured_mass_kg": round(ground_g / 1000.0, 5),
        "hull_volume_mm3": round(hull_volume, 3),
        "hull_volume_at_steel_density_kg": round(hull_volume * 1e-3 * spec.density_g_cm3 / 1000.0, 5),
        "applies": ("Not carried by the FBX or the sidecar, and not applied by the import scripts: set it on the "
                    "StaticMeshComponent's Body Instance (Physics > Mass (kg) override) in the Blueprint that "
                    f"throws the {geo.noun}, and say so in the Fab description."),
        "note": ("hull_volume_at_steel_density_kg is the UCX hull volume times 7.85 g/cm3, shown only to say how "
                 f"far a hull-volume mass at steel density would overstate the {geo.noun}. It is NOT Unreal's own "
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
                     report=report, started=started, material=material, geometry=geo, hulls=hulls)


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
    geo = fb.geometry
    if geo is not None and hasattr(geo, "bake"):
        # 3.10 (the kunai): a form with a second material slot bakes both slots' maps itself (kunai_wrap.bake_kunai)
        report["textures"] = geo.bake(fb.lod_objects[0], fb.material, Path(options.texture_dir), options)
    else:
        report["textures"] = bake_form(fb.lod_objects[0], fb.material, Path(options.texture_dir),
                                       size=geo.texture_size(options.texture_size) if geo is not None
                                       else options.texture_size,
                                       fill_unused=bool(getattr(geo, "fill_unused_texels", False)))
    report["textures"]["seconds"] = round(time.time() - started, 2)
    report["textures"]["shared_by_lods"] = [obj.name for obj in fb.lod_objects]
    if options.frozen_maps:
        frozen = freeze_maps(report["textures"], Path(options.frozen_maps))
        if frozen is not None:
            # 3.10: a form's other maps frozen by its own bake (the kunai's wrap: textures["wrap"]["frozen_maps"]) must
            # pass too
            extra = [(report["textures"].get("wrap") or {}).get(k) for k in ("frozen_maps", "frozen_natural_bc")]
            extra = [e for e in extra if e is not None]
            if extra:
                frozen["other_slots"] = extra
                frozen["passed"] = bool(frozen["passed"] and all(e.get("passed") for e in extra))
            report["textures"]["frozen_maps"] = frozen


# 3.9.1: what a frozen form's fresh GPU bake may differ from its snapshot by (8-bit steps; pixels with any channel off).
# Measured between builds of unchanged forms: <= 1/255 on <= 26 px per 2048 map (hooked_cross/texdiff_*.json).
FROZEN_MAP_NOISE = {"max_abs_8bit": 2, "max_pixels_differing": 2000}


def _png_bytes(path: Path) -> np.ndarray:
    """An 8-bit PNG's stored values (0-255, int16) as (h, w, 4); ``Image.pixels`` of a byte image is not colour managed."""
    image = bpy.data.images.load(str(Path(path).resolve()), check_existing=False)   # absolute: not the .blend's dir
    try:
        width, height = image.size
        pixels = np.empty(width * height * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
    finally:
        bpy.data.images.remove(image)
    return np.rint(pixels.reshape(height, width, 4) * 255.0).astype(np.int16)


def freeze_maps(textures: dict, frozen_dir: Path) -> Optional[dict]:
    """A frozen form's maps (3.9.1, the geometry review of the hooked-cross build): the GPU bake is not bit-reproducible,
    so a rebuild changed every frozen form's maps by 1/255 on a few dozen pixels.  When ``frozen_dir`` (a regression
    snapshot's textures/) holds this form's three maps, each fresh bake is compared with its snapshot map; within
    FROZEN_MAP_NOISE the SNAPSHOT's bytes are written over the fresh file (so the shipped maps stay bit-identical and the
    gallery renders from them), beyond it nothing is replaced and ``passed`` is False (a real change: the build fails).
    Returns None when the snapshot has no maps for the form (a new or changed form: its fresh bake ships)."""
    import shutil

    maps = {suffix: Path(path) for suffix, path in textures["maps"].items()}
    snap = {suffix: Path(frozen_dir) / path.name for suffix, path in maps.items()}
    if not all(path.exists() for path in snap.values()):
        return None
    out = {"snapshot": str(frozen_dir), "noise_allowed": dict(FROZEN_MAP_NOISE), "maps": {}}
    ok = True
    for suffix, path in maps.items():
        fresh, frozen = _png_bytes(path), _png_bytes(snap[suffix])
        if fresh.shape != frozen.shape:
            out["maps"][suffix] = {"shape": [list(fresh.shape), list(frozen.shape)], "within_bake_noise": False}
            ok = False
            continue
        diff = np.abs(fresh - frozen)
        differing = int(np.count_nonzero(diff.max(axis=-1)))
        worst = int(diff.max())
        within = worst <= FROZEN_MAP_NOISE["max_abs_8bit"] and differing <= FROZEN_MAP_NOISE["max_pixels_differing"]
        out["maps"][suffix] = {"max_abs_8bit": worst, "pixels_differing": differing, "within_bake_noise": within,
                               "fresh_bake_sha256": sha256(path), "snapshot_sha256": sha256(snap[suffix])}
        ok = ok and within
    if ok:
        for suffix, path in maps.items():
            shutil.copyfile(snap[suffix], path)
            textures["sha256"][suffix] = sha256(path)
    out["passed"] = ok
    out["shipped"] = ("the snapshot's bytes (the fresh bake differs only by bake noise)" if ok else
                      "the fresh bake: it differs from the frozen maps beyond bake noise (gate FAILED)")
    return out


def render_form(fb: FormBuild, others: Sequence, options: BuildOptions) -> None:
    report = fb.report
    if options.no_render:
        report["renders"] = []
        report["render_stats"] = {}
        report["render_gates"] = None
        return
    lod0, lods = fb.lod_objects[0], fb.lod_objects[1:]
    helpers = list(fb.hulls or [fb.hull]) + list(pipeline.socket_children(lod0))
    beauty = None
    extra = None
    textures = report.get("textures")
    if textures:
        beauty = preview_material(f"M_Preview_Baked_{fb.form.spec.mesh_name}", textures["maps"],
                                  uv_map=textures["uv_map"])
        if hasattr(fb.geometry, "preview_materials"):
            extra = fb.geometry.preview_materials(textures)       # 3.10: the other slots' baked preview materials
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
        light_scale=options.light_scale, hide=others, beauty_material=beauty, lod_labels=labels,
        **({"beauty_extra": extra} if extra else {}))
    for mat in [beauty] + list((extra or {}).values()):
        if mat is None:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                bpy.data.images.remove(node.image)
        bpy.data.materials.remove(mat)
    report["renders"] = list(written.values())
    report["render_stats"] = stats
    report["render_rig"] = rig
    persp, top = stats.get(f"{fb.form.name}_persp", {}), stats.get(f"{fb.form.name}_top", {})
    cls = getattr(fb.geometry, "consistency_class", "plate")      # 3.8: a bar's plate gates read its coat pixels
    report["render_gates"] = {
        "beauty_source": (("baked textures only (T_Shuriken_*_BC/_ORM/_N via a preview material)" if not extra else
                           "baked textures only: every material slot through its own baked-map preview material")
                          if beauty else "procedural M_Shuriken_Master: INTERNAL REVIEW ONLY, not a listing image"),
        "hero_walls": wall_gate(persp),
        "hero_facets_near": facet_gate(persp, "near"),
        "hero_plate": plate_gate(persp, cls),
        "hero_coat_dark": coat_gate(persp),       # 3.10.1: flat coat steel must not read as a hole (the kunai's neck)
        "top_facets": facet_gate(top, "all"),
        "top_plate": plate_gate(top, cls),
        "top_coat_dark": coat_gate(top),
    }
    if cls == "bar":
        report["render_gates"]["hero_bar_walls"] = bar_wall_gate(persp)     # 3.8.1: no pepper on the side faces
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
    "Wear (a polished band along the edge land and satin steel over the rest of the grind, edge nicks, lightly "
    "brightened scallops), whole-face smears, micro-scratches, dirt specks, pits and the two sub-pixel rust specks are "
    "procedural in M_Shuriken_Master, and the roll-off toward the hole and the notch arcs is a normal-map dish; all of "
    "it reaches the engine only through the baked maps; the per-form "
    "numbers travel as object custom properties (shuriken_wear_from / _to, shuriken_points, shuriken_hub_r, "
    "shuriken_tip_r, shuriken_chamfer, shuriken_scallop_w, shuriken_hole_w, shuriken_centre_r, shuriken_land, "
    "shuriken_half_t, shuriken_wall_top, shuriken_rust1/2_*), which the FBX does not export (use_custom_props off), and the material reads four float "
    "point attributes the generator writes (shuriken_edge / _hole / _scallop: distance to the outline, the hole and "
    "the notch arcs; shuriken_grind: signed distance from the grind's plate line), which the FBX exporter does not "
    "carry either (only colour attributes export) - they matter only to the bake.",
    "Knife grind (style pass 2): the cutting edges are ground to a 0.15 mm land, so the finished (ground) mass is "
    "well under the un-ground outline's; the study mass gate is evaluated on the un-ground plate (outline x "
    "thickness) and the ground mass is reported against the study min-max range (measured.mass_gate, "
    "measured.ground_mass_vs_study_range); the physics override is the ground mass. The gallery bands "
    "(render.PLATE_BAND / PLATE_MEAN_BAND) stay centred on the reference rendered through THIS rig "
    "(WorkFiles/shuriken/style_reference/ref_on_rig.py).",
    "Unreal texture import: the ORM map must be imported with sRGB OFF and Compression Settings = Masks (Unreal "
    "cannot detect a mask map; a plain import decodes roughness 0.32 as 0.08 and the steel renders as a mirror); "
    "BC is sRGB / Default and the _N suffix is auto-detected (sRGB off, Normalmap, Flip Green OFF - the map is "
    "DirectX on disk). Scripts/shuriken/ue_import_textures.py imports, sets and verifies these flags; the "
    "report's textures.unreal_import block and the Fab import notes must repeat them.",
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
        f"Physics: the Mass in KG override ({(report.get('physics') or {}).get('mass_kg_override')} kg, the knife-ground "
        f"LOD0 mass; study 4 table {fb.form.spec.physics_mass_kg} kg) is recorded here only; "
        "it has to be set on the component in the Blueprint (see physics.applies).",
    ]
    if fb.form.annotate is not None:
        fb.form.annotate(report)
    if not report["engine_check"].get("matches_this_build"):
        report["known_gaps"].append(
            "ENGINE CHECK PENDING: Unreal 5.8 verification of THIS export is not attached yet "
            "(engine_check.status). Run WorkFiles/shuriken/UnrealCheck6 passes 1-3 and attach_engine_check.py.")
    report["mass_check"] = {
        "evaluated_on": getattr(fb.geometry, "outline_wording", "outline (un-ground plate)"),
        "outline_g": measured.get("outline_mass_g"), "target_g": measured["mass_target_g"],
        "within_tolerance": measured["mass_within_tolerance"],
        "ground_g": measured.get("ground_mass_g", measured["mass_g"]),
        "ground_vs_study_range": measured.get("ground_mass_vs_study_range"),
        "measured_g": measured["mass_g"],
    }
    # Knife-facet shading (geometry review, style pass 2): the flat knife facets must be shaded flat -
    # the largest corner-normal vs face-normal angle on any knife facet of any LOD within the gate.
    # The senban's facets follow a curved side and are smooth within it on purpose (reported only).
    stats_by_lod = report.get("lod_mesh_stats") or {}
    flat = {name: st.get("knife_shading_max_dev_deg") for name, st in stats_by_lod.items()
            if st.get("knife_shading_max_dev_deg") is not None}
    curved = {name: st.get("curved_facet_shading_max_dev_deg") for name, st in stats_by_lod.items()
              if st.get("curved_facet_shading_max_dev_deg") is not None}
    report["knife_shading"] = {
        "gate_deg": KNIFE_SHADING_GATE_DEG,
        "flat_knife_facets_max_corner_normal_dev_deg": flat,
        "curved_side_facets_max_corner_normal_dev_deg": curved,
        "warp_mm": {name: st.get("knife_face_max_warp_mm", st.get("curved_facet_max_warp_mm"))
                    for name, st in stats_by_lod.items()},
        "passed": bool(all(v <= KNIFE_SHADING_GATE_DEG for v in flat.values())),
        "note": ("max angle between a stored corner normal and its own face normal over the knife facets "
                 "(flat facets shaded flat: creases above geometry.KNIFE_CREASE_DEG inside a knife class are "
                 "hard edges). Curved-side facets (senban) are smooth within their side by design and bounded "
                 "by half a chord's turn; they are reported, not gated."),
    }
    report["gates"] = {
        "knife_shading": report["knife_shading"]["passed"],
        "outline_mass": bool(measured["mass_within_tolerance"]),
        "qa_check": bool(report["qa"]["passed"]),
        "lod_bands": all(report["lod_bands_ok"]),
        "uv_consistency": bool(report["uv_consistency"]["passed"]),
        "textures_baked": bool(report.get("textures")),
        "render_gates": (report.get("render_gates") or {}).get("passed"),
    }
    # 3.9.1: a frozen form's maps (build_pack --frozen-maps): the fresh bake within bake noise of the snapshot's
    frozen = (report.get("textures") or {}).get("frozen_maps")
    if frozen is not None:
        report["gates"]["frozen_maps"] = bool(frozen.get("passed"))
    # 3.9: a form's own gates (the hooked cross: handedness), written by its annotate() as report["form_gates"];
    # absent on every earlier form, whose gates block is unchanged
    report["gates"].update(report.get("form_gates") or {})
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
    passed = (bool(report["qa"]["passed"]) and all(report["lod_bands_ok"]) and bool(gates.get("uv_consistency"))
              and bool(gates.get("outline_mass", True)) and bool(gates.get("knife_shading", True))
              and bool(gates.get("frozen_maps", True))
              and all(bool(v) for v in (report.get("form_gates") or {}).values()))
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
    parser.add_argument("--frozen-maps", default=None,
                        help="3.9.1: a regression snapshot's textures/ dir; a form whose three maps are there is "
                             "frozen: its fresh bake must match them within bake noise and their bytes ship")


def options_from_args(args) -> BuildOptions:
    return BuildOptions(
        blend=Path(args.blend), render_dir=Path(args.render_dir), diag_dir=Path(args.diag_dir),
        export_dir=Path(getattr(args, "export_dir", DEFAULT_EXPORT_DIR)),
        texture_dir=Path(args.texture_dir), texture_size=args.texture_size,
        report_dir=Path(getattr(args, "report_dir", DEFAULT_REPORT_DIR)),
        budget=args.budget, hull_verts=args.hull_verts, island_margin=args.island_margin,
        texel_map=args.texel_map, samples=args.samples, light_scale=args.light_scale,
        res=args.res, res_y=args.res_y, no_export=args.no_export, no_render=args.no_render,
        no_bake=args.no_bake,
        frozen_maps=Path(args.frozen_maps).resolve() if getattr(args, "frozen_maps", None) else None)


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
    "build_pack", "collection_name", "discover_forms", "engine_check", "export_form", "finalize_report", "freeze_maps",
    "uv_islands", "FROZEN_MAP_NOISE", "uv_tile_check",
    "load_form_module", "lod_switching", "options_from_args", "render_form", "report_passed", "reset_scene",
    "run_single", "sha256", "summary", "unwrap", "warn_if_pack_blend", "write_report",
]
