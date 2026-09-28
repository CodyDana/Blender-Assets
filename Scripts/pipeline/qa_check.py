"""Headless QA checklist (FAB_ASSET_STUDY.md section 3.10, items 1-6).

``qa_check`` returns ``{"passed": bool, "checks": [{"name", "object", "passed",
"detail"}, ...]}``, never prints and never edits the scene. Checks per object:

1. transforms applied (matrix_basis has no rotation/scale), unit scale 1.0,
   evaluated triangle count within budget, LOD counts descending
2. no n-gons, no non-manifold edges (>2 faces or wire), no loose vertices, no
   degenerate geometry (zero-length edges, zero-area faces, coincident but
   unmerged vertices); boundary edges are reported but do not fail, because
   decals, hair cards and open-bottom props are legitimate
3. UV0 (layer index 0, not the active layer) present, texel density within
   tolerance of a target, no overlapping UVs; UV0 must stay inside a tile range
   (default -1..2, which allows study 3.3's "+1 in U" mirrored shells) while the
   strict 0-1 containment and non-overlap requirement of Fab 4.3.3.2 is applied
   to the lightmap layer UV1 when it is required
4. images power-of-two, files present, Non-Color on normal/ORM by suffix
5. SM_/SK_/T_/M_/MI_ prefixes; every SM_ has a ``UCX_<render node name>_NN``
   child (the name must repeat the object name exactly, because Unreal matches
   collision against the render node and silently drops a mismatch); SOCKET_
   children must be Empties; no franchise strings
6. skeletal: one root at the origin (for a skeleton imported from Unreal the armature
   object named ``root`` IS the root bone), <= 4 influences (``max_influences``), no
   unweighted vertices, weight sum error < 1e-6, no "." in bone names

Garments on the locked character base add their own gates on top: ``garment_qa.py``.

CLI (prints JSON, exit 1 when not passed)::

    blender -b file.blend --factory-startup --python Scripts/pipeline/qa_check.py -- \
        --objects A,B [--budget 50000] [--texel 10.24] [--tolerance 0.25] [--require-uv1] \
        [--no-ucx] [--no-names] [--overlap sat|operator|both] [--json out.json]
"""
from __future__ import annotations

import argparse
import contextlib
import itertools
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[1])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

from pipeline.helpers import (  # noqa: E402
    COLLISION_PREFIXES, SOCKET_PREFIX, ObjectLike, lod_base_name, lod_index, resolve_objects, selection,
    transform_is_applied,
)

# Terms of four characters or more are matched as plain case-insensitive
# substrings (with optional separators between words), because CamelCase and
# digit suffixes hide them from a word-boundary match: SM_KamishBlade, SM_AWM01,
# T_Gilgamesh2K all have to be caught. "ea" is genuinely ambiguous, so it keeps a
# start boundary and only rejects a following lowercase letter (SM_EA2 and
# SM_EaBlade hit; SM_Sea_Blade and SM_Feather do not).
DENY_SUBSTRINGS = ("kamish", "solo leveling", "gilgamesh", "naruto", "jin mu-won", "jinmuwon",
                   "northern blade", "awm", "accuracy international")
DENY_WORDS = ("ea",)
DENY_LIST = DENY_SUBSTRINGS + DENY_WORDS
DATA_SUFFIXES = ("_n", "_normal", "_nrm", "_normaldx", "_normalgl", "_orm", "_rma", "_mra", "_ao",
                 "_r", "_m", "_roughness", "_metallic", "_mask", "_h", "_height")
MESH_PREFIXES = ("SM_", "SK_")
MATERIAL_PREFIXES = ("M_", "MI_")
IMAGE_PREFIX = "T_"
UV_EPSILON = 1e-5
# Degenerate-geometry thresholds, in scene units (1 unit = 1 m under the house
# metric setup, so: a micron, a square micron, a micron).
ZERO_EDGE_LENGTH = 1e-6
ZERO_FACE_AREA = 1e-12
COINCIDENT_DISTANCE = 1e-6
DEFAULT_TEXTURE_SIZE = 2048
DEFAULT_TILE_RANGE = (-1.0, 2.0)
OVERLAP_METHODS = ("sat", "operator", "both")
MAX_INFLUENCES = 4
WEIGHT_TOLERANCE = 1e-6
# Blender's FBX importer turns an Unreal skeleton's root node into the armature object (see _armature_checks).
UE_ROOT_OBJECT = "root"
# Mesh attributes bpy.ops.uv.select_overlap and its mode changes can rewrite.
_MESH_STATE_ATTRIBUTES = (".hide_vert", ".hide_edge", ".hide_poly", ".select_vert", ".select_edge",
                          ".select_poly", ".uv_select_vert", ".uv_select_edge", ".uv_select_face")


def _deny_pattern() -> "re.Pattern[str]":
    parts = []
    for term in DENY_SUBSTRINGS:
        words = [re.escape(word) for word in re.split(r"[\s\-]+", term) if word]
        parts.append(r"[\s_\-]*".join(words))
    for term in DENY_WORDS:
        parts.append(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![a-z])")
    return re.compile("|".join(parts), re.IGNORECASE)


DENY_RE = _deny_pattern()


def _check(name: str, obj: Optional[str], passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "object": obj, "passed": bool(passed), "detail": detail}


# --------------------------------------------------------------------------- item 1

def evaluated_triangles(obj: "bpy.types.Object", depsgraph: "bpy.types.Depsgraph") -> int:
    """Triangle count of the modifier-applied mesh (``loop_triangles``)."""
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return len(mesh.loop_triangles)
    finally:
        evaluated.to_mesh_clear()


def _check_unit_scale() -> Dict[str, Any]:
    units = bpy.context.scene.unit_settings
    ok = units.system == "METRIC" and abs(units.scale_length - 1.0) < 1e-6
    return _check("unit_scale", None, ok, f"system={units.system}, scale_length={units.scale_length}")


def _check_lod_order(tri_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[int, Tuple[str, int]]] = defaultdict(dict)
    for name, count in tri_counts.items():
        index = lod_index(name)
        if index is not None:
            groups[lod_base_name(name)][index] = (name, count)
    checks = []
    for base, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        indices = sorted(members)
        counts = [members[i][1] for i in indices]
        contiguous = indices == list(range(indices[0], indices[0] + len(indices)))
        descending = all(a > b for a, b in zip(counts, counts[1:]))
        detail = ", ".join(f"LOD{i}={members[i][1]}" for i in indices)
        checks.append(_check("lod_counts_descending", base, descending and contiguous,
                             detail + ("" if contiguous else " (indices not contiguous)")))
    return checks


# --------------------------------------------------------------------------- item 2

def coincident_vertex_pairs(coords: np.ndarray, tolerance: float = COINCIDENT_DISTANCE) -> int:
    """Vertex pairs closer together than ``tolerance``, by lexicographic sweep."""
    if len(coords) < 2:
        return 0
    order = np.lexsort((coords[:, 2], coords[:, 1], coords[:, 0]))
    ordered = coords[order]
    pairs = 0
    for i in range(len(ordered)):
        j = i + 1
        while j < len(ordered) and ordered[j, 0] - ordered[i, 0] <= tolerance:
            if float(np.linalg.norm(ordered[j] - ordered[i])) <= tolerance:
                pairs += 1
            j += 1
    return pairs


def _degenerate_checks(obj: "bpy.types.Object", bm: "bmesh.types.BMesh") -> List[Dict[str, Any]]:
    """Zero-length edges, zero-area faces and coincident-but-unmerged vertices.

    Added after a shipped star passed all 46 of the other checks while carrying 16
    coincident vertex pairs, 16 zero-length edges and 32 zero-area triangles at its
    bevel run-outs. Nothing here could see them: ``no_non_manifold_edges`` passed
    *because* the zero-area faces stitched the splits shut, and ``uv_no_overlap``
    discards degenerate triangles by design. Unreal removed them on import
    (``remove_degenerates`` is on by default), so the engine reported 1632 triangles
    against Blender's 1664 and the render mesh met at coincident, separate vertices.
    Thresholds are absolute, in scene units: at 1 unit = 1 m they are a micron, a
    square micron and a micron, orders of magnitude below any real game asset feature.
    """
    short_edges = [edge for edge in bm.edges if edge.calc_length() <= ZERO_EDGE_LENGTH]
    thin_faces = [face for face in bm.faces if face.calc_area() <= ZERO_FACE_AREA]
    coords = np.array([vert.co[:] for vert in bm.verts], dtype=np.float64) if bm.verts else np.zeros((0, 3))
    coincident = coincident_vertex_pairs(coords)
    smallest_edge = min((edge.calc_length() for edge in bm.edges), default=0.0)
    smallest_face = min((face.calc_area() for face in bm.faces), default=0.0)
    return [
        _check("no_zero_length_edges", obj.name, not short_edges,
               f"{len(short_edges)} edge(s) at or below {ZERO_EDGE_LENGTH:g} of {len(bm.edges)}; "
               f"shortest {smallest_edge:.6g}"),
        _check("no_degenerate_faces", obj.name, not thin_faces,
               f"{len(thin_faces)} face(s) at or below {ZERO_FACE_AREA:g} area of {len(bm.faces)}; "
               f"smallest {smallest_face:.6g}"),
        _check("no_coincident_vertices", obj.name, coincident == 0,
               f"{coincident} vertex pair(s) within {COINCIDENT_DISTANCE:g} of {len(bm.verts)}"),
    ]


def _topology_checks(obj: "bpy.types.Object", bm: "bmesh.types.BMesh") -> List[Dict[str, Any]]:
    """n-gons, real non-manifold edges, loose verts; boundary edges informational."""
    ngons = sum(1 for face in bm.faces if len(face.verts) > 4)
    multi_face = sum(1 for edge in bm.edges if len(edge.link_faces) > 2)
    wire = sum(1 for edge in bm.edges if not edge.link_faces)
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    loose = sum(1 for vert in bm.verts if not vert.link_edges)
    return [
        _check("no_ngons", obj.name, ngons == 0, f"{ngons} n-gon(s) of {len(bm.faces)} faces"),
        _check("no_non_manifold_edges", obj.name, multi_face + wire == 0,
               f"{multi_face} edge(s) with more than 2 faces, {wire} wire edge(s), of {len(bm.edges)}"),
        _check("open_boundary_edges", obj.name, True,
               f"{boundary} boundary edge(s) of {len(bm.edges)} (informational: open meshes are allowed)"),
        _check("no_loose_vertices", obj.name, loose == 0, f"{loose} loose vertex/vertices of {len(bm.verts)}"),
    ] + _degenerate_checks(obj, bm)


# --------------------------------------------------------------------------- item 3

def _uv_triangles(bm: "bmesh.types.BMesh", layer: Any) -> np.ndarray:
    """UV triangles (n, 3, 2) of a BMesh via bmesh triangulation of a copy."""
    work = bm.copy()
    work_layer = work.loops.layers.uv[layer.name]
    bmesh.ops.triangulate(work, faces=list(work.faces))
    tris = np.array([[tuple(loop[work_layer].uv) for loop in face.loops] for face in work.faces],
                    dtype=np.float64).reshape(-1, 3, 2)
    work.free()
    return tris


def uv_overlap_sat(tris: np.ndarray, epsilon: float = UV_EPSILON) -> int:
    """Count overlapping UV triangle pairs with a separating-axis test on a uniform grid.

    Touching edges and shared vertices are not overlaps; degenerate triangles are ignored.
    """
    if len(tris) < 2:
        return 0
    edge_a = tris[:, 1] - tris[:, 0]
    edge_b = tris[:, 2] - tris[:, 0]
    area2 = np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0])
    keep = np.nonzero(area2 > 1e-12)[0]
    if len(keep) < 2:
        return 0
    tris = tris[keep]
    mins = tris.min(axis=1)
    maxs = tris.max(axis=1)
    extent = float(np.median(maxs - mins)) * 2.0
    cell = max(extent, 1e-4)
    buckets: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    lo = np.floor(mins / cell).astype(np.int64)
    hi = np.floor(maxs / cell).astype(np.int64)
    for index in range(len(tris)):
        for cx in range(lo[index, 0], hi[index, 0] + 1):
            for cy in range(lo[index, 1], hi[index, 1] + 1):
                buckets[(cx, cy)].append(index)
    pairs = set()
    for members in buckets.values():
        if len(members) > 1:
            pairs.update(itertools.combinations(members, 2))
    if not pairs:
        return 0
    pair_array = np.array(sorted(pairs), dtype=np.int64)
    first = tris[pair_array[:, 0]]
    second = tris[pair_array[:, 1]]
    bbox_apart = np.any(maxs[pair_array[:, 0]] <= mins[pair_array[:, 1]] + epsilon, axis=1) | \
        np.any(maxs[pair_array[:, 1]] <= mins[pair_array[:, 0]] + epsilon, axis=1)
    separated = bbox_apart.copy()
    for tri in (first, second):
        for k in range(3):
            edge = tri[:, (k + 1) % 3] - tri[:, k]
            axis = np.stack([-edge[:, 1], edge[:, 0]], axis=-1)
            norm = np.linalg.norm(axis, axis=1, keepdims=True)
            axis = axis / np.where(norm == 0, 1.0, norm)
            proj_a = np.einsum("pij,pj->pi", first, axis)
            proj_b = np.einsum("pij,pj->pi", second, axis)
            separated |= (proj_a.max(axis=1) <= proj_b.min(axis=1) + epsilon) | \
                (proj_b.max(axis=1) <= proj_a.min(axis=1) + epsilon)
    return int(np.count_nonzero(~separated))


@contextlib.contextmanager
def _preserve_mesh_state(mesh: "bpy.types.Mesh") -> Iterator[None]:
    """Snapshot and restore the hide/select attributes an operator may rewrite.

    ``bpy.ops.mesh.reveal`` removes ``.hide_poly`` outright, so the attribute is
    re-created when it is missing afterwards and removed again when it was not
    there before. qa_check has to leave the scene exactly as it found it.
    """
    snapshot: Dict[str, Optional[Tuple[str, str, List[Any]]]] = {}
    for name in _MESH_STATE_ATTRIBUTES:
        attribute = mesh.attributes.get(name)
        if attribute is None:
            snapshot[name] = None
        else:
            snapshot[name] = (attribute.domain, attribute.data_type,
                              [item.value for item in attribute.data])
    active_uv = mesh.uv_layers.active_index if len(mesh.uv_layers) else None
    try:
        yield
    finally:
        for name, saved in snapshot.items():
            attribute = mesh.attributes.get(name)
            if saved is None:
                if attribute is not None:
                    with contextlib.suppress(RuntimeError):
                        mesh.attributes.remove(attribute)
                continue
            domain, data_type, values = saved
            if attribute is None:
                try:
                    attribute = mesh.attributes.new(name, data_type, domain)
                except RuntimeError:
                    continue
            attribute.data.foreach_set("value", values)
        if active_uv is not None and len(mesh.uv_layers):
            mesh.uv_layers.active_index = active_uv
        mesh.update()


def _uv_overlap_operator(obj: "bpy.types.Object", uv_index: int = 0) -> int:
    """Faces flagged by ``bpy.ops.uv.select_overlap`` on UV layer ``uv_index``.

    The operator reads the mesh's active UV layer, so the layer is switched to
    ``uv_index`` for the duration. Hide and selection state is restored.
    Blender 5.2 stores UV selection in the ``.uv_select_face`` /
    ``.uv_select_vert`` mesh attributes, which are read back in object mode.
    """
    mesh = obj.data
    with _preserve_mesh_state(mesh):
        if len(mesh.uv_layers) > uv_index:
            mesh.uv_layers.active_index = uv_index
        with selection([obj], obj):
            bpy.ops.object.mode_set(mode="EDIT")
            try:
                bpy.ops.mesh.reveal()
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.select_all(action="DESELECT")
                result = bpy.ops.uv.select_overlap()
            finally:
                bpy.ops.object.mode_set(mode="OBJECT")
        if "FINISHED" not in result:
            raise RuntimeError(f"uv.select_overlap returned {result}")
        face_flags = mesh.attributes.get(".uv_select_face")
        if face_flags is not None and face_flags.domain == "FACE":
            return sum(1 for item in face_flags.data if item.value)
        corner_flags = mesh.attributes.get(".uv_select_vert")
        if corner_flags is not None and corner_flags.domain == "CORNER":
            flagged = set()
            for polygon in mesh.polygons:
                if any(corner_flags.data[index].value for index in polygon.loop_indices):
                    flagged.add(polygon.index)
            return len(flagged)
        raise RuntimeError("UV selection attributes not found after uv.select_overlap")


def _texture_size(obj: "bpy.types.Object") -> int:
    sizes = [max(image.size) for _material, image in _material_images(obj) if image.size[0] > 0]
    return max(sizes) if sizes else DEFAULT_TEXTURE_SIZE


def _layer_coords(bm: "bmesh.types.BMesh", layer: Any) -> np.ndarray:
    return np.array([tuple(loop[layer].uv) for face in bm.faces for loop in face.loops], dtype=np.float64)


def _span(coords: np.ndarray) -> str:
    if not len(coords):
        return "no loops"
    return (f"u {coords[:, 0].min():.4f}..{coords[:, 0].max():.4f}, "
            f"v {coords[:, 1].min():.4f}..{coords[:, 1].max():.4f}")


def _overlap_checks(obj: "bpy.types.Object", bm: "bmesh.types.BMesh", layer: Any, uv_index: int,
                    check_name: str, method: str) -> List[Dict[str, Any]]:
    """Run the requested overlap test(s) on one UV layer and report the method used."""
    checks: List[Dict[str, Any]] = []
    if method in ("sat", "both"):
        overlapping = uv_overlap_sat(_uv_triangles(bm, layer))
        checks.append(_check(check_name, obj.name, overlapping == 0,
                             f"{overlapping} overlapping triangle pair(s) on {layer.name!r} (UV{uv_index}); "
                             f"method: numpy separating-axis test on the evaluated mesh"))
    if method in ("operator", "both"):
        try:
            flagged = _uv_overlap_operator(obj, uv_index)
            detail = (f"{flagged} overlapping face(s) on {layer.name!r} (UV{uv_index}); "
                      f"method: bpy.ops.uv.select_overlap on the base mesh")
            passed = flagged == 0
        except (RuntimeError, ValueError) as exc:
            detail = f"bpy.ops.uv.select_overlap unavailable: {exc}"
            passed = method != "operator"
        checks.append(_check(check_name if method == "operator" else f"{check_name}_operator",
                             obj.name, passed, detail))
    return checks


def _uv_checks(obj: "bpy.types.Object", bm: "bmesh.types.BMesh", texel_density: Optional[float],
               tolerance: float, require_uv1: bool, tile_range: Sequence[float] = DEFAULT_TILE_RANGE,
               overlap_method: str = "sat") -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    layers = bm.loops.layers.uv
    if not len(layers):
        checks.append(_check("uv0_present", obj.name, False, "no UV map"))
        if require_uv1:
            checks.append(_check("uv1_present", obj.name, False, "no UV map"))
        return checks
    # Always grade UV0 by index: on a finished asset the lightmap layer is often left active.
    uv0 = layers[0]
    active_name = layers.active.name if layers.active is not None else "<none>"
    checks.append(_check("uv0_present", obj.name, True,
                         f"{len(layers)} UV map(s); UV0 is {uv0.name!r} (active layer is {active_name!r})"))

    coords = _layer_coords(bm, uv0)
    low, high = float(tile_range[0]), float(tile_range[1])
    within = bool(len(coords) == 0 or (coords.min() >= low - UV_EPSILON and coords.max() <= high + UV_EPSILON))
    checks.append(_check("uv0_tile_range", obj.name, within,
                         f"{_span(coords)} on {uv0.name!r}; allowed {low}..{high} "
                         f"(study 3.3 offsets mirrored shells by +1 in U)"))

    uv_area = 0.0
    mesh_area = 0.0
    for face in bm.faces:
        uvs = [loop[uv0].uv for loop in face.loops]
        shoelace = sum(uvs[i].x * uvs[(i + 1) % len(uvs)].y - uvs[(i + 1) % len(uvs)].x * uvs[i].y
                       for i in range(len(uvs)))
        uv_area += abs(shoelace) * 0.5
        mesh_area += face.calc_area()
    texture_px = _texture_size(obj)
    density = math.sqrt(uv_area / mesh_area) * texture_px / 100.0 if mesh_area > 0 else 0.0
    detail = (f"{density:.3f} px/cm at {texture_px}px on {uv0.name!r} "
              f"(uv area {uv_area:.4f}, mesh area {mesh_area:.4f} m2)")
    if texel_density:
        error = abs(density - texel_density) / texel_density
        checks.append(_check("texel_density", obj.name, error <= tolerance,
                             f"{detail}; target {texel_density} px/cm, error {error:.1%}, tolerance {tolerance:.0%}"))
    else:
        checks.append(_check("texel_density", obj.name, True, detail + "; no target given"))

    checks.extend(_overlap_checks(obj, bm, uv0, 0, "uv_no_overlap", overlap_method))

    if require_uv1:
        has_uv1 = len(layers) >= 2
        checks.append(_check("uv1_present", obj.name, has_uv1,
                             f"{len(layers)} UV map(s); UE lightmap UV needs index 1"))
        if has_uv1:
            uv1 = layers[1]
            coords1 = _layer_coords(bm, uv1)
            inside = bool(len(coords1) == 0 or
                          (coords1.min() >= -UV_EPSILON and coords1.max() <= 1.0 + UV_EPSILON))
            checks.append(_check("uv1_inside_0_1", obj.name, inside,
                                 f"{_span(coords1)} on {uv1.name!r} (Fab 4.3.3.2 lightmap UV)"))
            checks.extend(_overlap_checks(obj, bm, uv1, 1, "uv1_no_overlap", overlap_method))
    return checks


# --------------------------------------------------------------------------- item 4

def _material_images(obj: "bpy.types.Object") -> Iterable[Tuple["bpy.types.Material", "bpy.types.Image"]]:
    seen = set()
    for slot in obj.material_slots:
        material = slot.material
        if material is None or material.node_tree is None:
            continue
        for node in material.node_tree.nodes:
            image = getattr(node, "image", None)
            if image is not None and image.name not in seen:
                seen.add(image.name)
                yield material, image


def _image_file_present(image: "bpy.types.Image") -> Tuple[bool, str]:
    if image.packed_file is not None:
        return True, "packed"
    if image.source in {"FILE", "SEQUENCE", "TILED"}:
        path = bpy.path.abspath(image.filepath, library=image.library)
        return os.path.isfile(path), path
    return False, f"source {image.source} (not on disk)"


def _image_checks(obj: "bpy.types.Object") -> List[Dict[str, Any]]:
    checks = []
    for _material, image in _material_images(obj):
        width, height = image.size
        pot = width > 0 and height > 0 and (width & (width - 1)) == 0 and (height & (height - 1)) == 0
        checks.append(_check("image_power_of_two", image.name, pot, f"{width}x{height}"))
        present, where = _image_file_present(image)
        checks.append(_check("image_file_present", image.name, present, where))
        stem = os.path.splitext(image.name)[0].lower()
        if stem.endswith(DATA_SUFFIXES):
            colorspace = image.colorspace_settings.name
            checks.append(_check("image_colorspace_non_color", image.name, colorspace == "Non-Color",
                                 f"colorspace {colorspace!r} for data suffix"))
    return checks


# --------------------------------------------------------------------------- item 5

def _deny_hits(*values: Optional[str]) -> List[str]:
    hits = []
    for value in values:
        if value:
            for match in DENY_RE.finditer(value):
                hits.append(f"{match.group(0)!r} in {value!r}")
    return hits


def _helper_child_checks(obj: "bpy.types.Object", require_ucx: bool) -> List[Dict[str, Any]]:
    """Collision and socket children must key to this object's exact node name."""
    checks: List[Dict[str, Any]] = []
    hull_pattern = re.compile(rf"^UCX_{re.escape(obj.name)}_\d{{2}}$")
    any_pattern = re.compile(rf"^(?:{'|'.join(COLLISION_PREFIXES)}){re.escape(obj.name)}_\d{{2}}$")
    hulls = [child for child in obj.children if hull_pattern.match(child.name)]
    if require_ucx and obj.name.startswith("SM_") and lod_index(obj.name) in (None, 0):
        checks.append(_check("ucx_present", obj.name, bool(hulls),
                             ", ".join(hull.name for hull in hulls) if hulls
                             else f"no child named UCX_{obj.name}_NN (Unreal keys collision to the "
                                  f"render node name, so UCX_<base>_NN on a {obj.name!r} node is dropped)"))
    for hull in hulls:
        bm = bmesh.new()
        bm.from_mesh(hull.data)
        closed = all(edge.is_manifold for edge in bm.edges) and len(bm.faces) >= 4
        bm.free()
        checks.append(_check("ucx_closed", hull.name, closed,
                             f"{len(hull.data.vertices)} vertices, {len(hull.data.polygons)} faces"))
    for child in obj.children:
        if child.name.startswith(COLLISION_PREFIXES):
            ok = bool(any_pattern.match(child.name))
            checks.append(_check("collision_name_matches_mesh", child.name, ok,
                                 f"parent render node is {obj.name!r}; expected "
                                 f"<UCX|UBX|USP|UCP>_{obj.name}_NN"))
        if child.name.startswith(SOCKET_PREFIX):
            checks.append(_check("socket_is_empty", child.name, child.type == "EMPTY",
                                 f"node type {child.type}; UE 5.8.2 only reads an FBX Null as a socket, "
                                 f"a child mesh is welded into the render mesh"))
            checks.append(_check("socket_name_matches_mesh", child.name,
                                 child.name.startswith(f"{SOCKET_PREFIX}{obj.name}_"),
                                 f"parent render node is {obj.name!r}; expected {SOCKET_PREFIX}{obj.name}_<socket>"))
    return checks


def _name_checks(obj: "bpy.types.Object", require_ucx: bool) -> List[Dict[str, Any]]:
    checks = []
    names = [obj.name, obj.data.name if obj.data else None]
    if obj.type == "MESH":
        ok = obj.name.startswith(MESH_PREFIXES)
        checks.append(_check("name_prefix", obj.name, ok, f"mesh object prefix must be one of {MESH_PREFIXES}"))
        for slot in obj.material_slots:
            material = slot.material
            if material is None:
                checks.append(_check("material_assigned", obj.name, False, "empty material slot"))
                continue
            names.append(material.name)
            checks.append(_check("material_prefix", material.name, material.name.startswith(MATERIAL_PREFIXES),
                                 f"material prefix must be one of {MATERIAL_PREFIXES}"))
        for _material, image in _material_images(obj):
            names.extend([image.name, os.path.basename(image.filepath) if image.filepath else None])
            checks.append(_check("image_prefix", image.name, image.name.startswith(IMAGE_PREFIX),
                                 f"image name must start with {IMAGE_PREFIX!r}"))
        checks.extend(_helper_child_checks(obj, require_ucx))
    elif obj.type == "ARMATURE":
        names.extend(bone.name for bone in obj.data.bones)
    hits = _deny_hits(*names)
    checks.append(_check("no_franchise_strings", obj.name, not hits, "; ".join(hits) if hits else "clean"))
    return checks


# --------------------------------------------------------------------------- item 6

def _armature_checks(armature: "bpy.types.Object") -> List[Dict[str, Any]]:
    checks = []
    bones = armature.data.bones
    roots = [bone for bone in bones if bone.parent is None]
    checks.append(_check("single_root_bone", armature.name, len(roots) == 1,
                         ", ".join(bone.name for bone in roots) or "no bones"))
    if len(roots) == 1 and armature.name == UE_ROOT_OBJECT and roots[0].name != UE_ROOT_OBJECT:
        # A skeleton imported from Unreal (metahuman_base_skel, Manny) keeps its root bone as the armature OBJECT:
        # Blender's importer turns the FBX root node into the object, so the bones start at pelvis. The root is
        # then the object, and it is the object that has to sit at the origin.
        origin = armature.matrix_world.translation
        checks.append(_check("root_bone_at_origin", armature.name, origin.length < 1e-4,
                             f"armature object {armature.name!r} is the root bone (Unreal convention), at "
                             f"({origin.x:.4f}, {origin.y:.4f}, {origin.z:.4f}); top bone {roots[0].name}"))
    elif len(roots) == 1:
        head = armature.matrix_world @ roots[0].head_local
        at_origin = head.length < 1e-4
        checks.append(_check("root_bone_at_origin", armature.name, at_origin,
                             f"{roots[0].name} head at ({head.x:.4f}, {head.y:.4f}, {head.z:.4f})"))
    dotted = [bone.name for bone in bones if "." in bone.name]
    checks.append(_check("bone_names_without_dots", armature.name, not dotted,
                         ", ".join(dotted[:10]) + (" ..." if len(dotted) > 10 else "") if dotted else "clean"))
    return checks


def _skin_checks(obj: "bpy.types.Object", armature: "bpy.types.Object",
                 max_influences: int = MAX_INFLUENCES) -> List[Dict[str, Any]]:
    bone_names = {bone.name for bone in armature.data.bones if bone.use_deform}
    group_is_bone = {group.index: group.name in bone_names for group in obj.vertex_groups}
    worst_influences = 0
    unweighted = 0
    max_error = 0.0
    for vertex in obj.data.vertices:
        weights = [g.weight for g in vertex.groups if group_is_bone.get(g.group) and g.weight > 0.0]
        worst_influences = max(worst_influences, len(weights))
        total = sum(weights)
        if total <= 0.0:
            unweighted += 1
        else:
            max_error = max(max_error, abs(total - 1.0))
    return [
        _check("max_influences", obj.name, worst_influences <= max_influences,
               f"max {worst_influences} (limit {max_influences})"),
        _check("no_unweighted_vertices", obj.name, unweighted == 0, f"{unweighted} unweighted of {len(obj.data.vertices)}"),
        _check("weight_sum_error", obj.name, max_error < WEIGHT_TOLERANCE, f"max |sum-1| = {max_error:.2e} (limit {WEIGHT_TOLERANCE})"),
    ]


# --------------------------------------------------------------------------- driver

def qa_check(objects: Iterable[ObjectLike], budget_tris: Optional[int] = None, texel_density: Optional[float] = None,
             tolerance: float = 0.25, require_uv1: bool = False, require_ucx: bool = True,
             check_names: bool = True, uv0_tile_range: Sequence[float] = DEFAULT_TILE_RANGE,
             overlap_method: str = "sat", max_influences: int = MAX_INFLUENCES) -> Dict[str, Any]:
    """Run study 3.10 items 1-6 on ``objects`` (names or objects) and return the results.

    ``uv0_tile_range`` bounds UV0 without demanding 0-1 containment (study 3.3
    offsets mirrored shells by +1 in U). ``overlap_method`` is ``"sat"`` (the
    default: a read-only numpy test on the evaluated mesh), ``"operator"``
    (``bpy.ops.uv.select_overlap``, which is restored afterwards but only sees
    the base mesh) or ``"both"``. ``max_influences`` is the skin influence limit (4 by default; the garment
    gates pass their type's limit, e.g. 8 for a fitted garment on the MetaHuman body).
    """
    if overlap_method not in OVERLAP_METHODS:
        raise ValueError(f"overlap_method must be one of {OVERLAP_METHODS}, got {overlap_method!r}")
    resolved = resolve_objects(objects)
    if not resolved:
        raise ValueError("No objects to check")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    checks: List[Dict[str, Any]] = [_check_unit_scale()]
    tri_counts: Dict[str, int] = {}
    armatures_seen = set()
    for obj in resolved:
        ok, detail = transform_is_applied(obj)
        checks.append(_check("transforms_applied", obj.name, ok, detail))
        if obj.type == "MESH":
            tris = evaluated_triangles(obj, depsgraph)
            tri_counts[obj.name] = tris
            if budget_tris is not None:
                checks.append(_check("triangle_budget", obj.name, tris <= budget_tris, f"{tris} triangles (budget {budget_tris})"))
            else:
                checks.append(_check("triangle_budget", obj.name, True, f"{tris} triangles (no budget given)"))
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
            finally:
                evaluated.to_mesh_clear()
            try:
                checks.extend(_topology_checks(obj, bm))
                checks.extend(_uv_checks(obj, bm, texel_density, tolerance, require_uv1,
                                         uv0_tile_range, overlap_method))
            finally:
                bm.free()
            checks.extend(_image_checks(obj))
            if check_names:
                checks.extend(_name_checks(obj, require_ucx))
            for modifier in obj.modifiers:
                if modifier.type == "ARMATURE" and modifier.object is not None:
                    if modifier.object.name not in armatures_seen:
                        armatures_seen.add(modifier.object.name)
                        checks.extend(_armature_checks(modifier.object))
                    checks.extend(_skin_checks(obj, modifier.object, max_influences))
        elif obj.type == "ARMATURE":
            if obj.name not in armatures_seen:
                armatures_seen.add(obj.name)
                checks.extend(_armature_checks(obj))
            if check_names:
                checks.extend(_name_checks(obj, require_ucx))
        elif check_names:
            checks.append(_check("no_franchise_strings", obj.name, not _deny_hits(obj.name), "; ".join(_deny_hits(obj.name)) or "clean"))
    checks.extend(_check_lod_order(tri_counts))
    # Shared materials/images are reached from several objects; report each check once.
    unique: List[Dict[str, Any]] = []
    seen = set()
    for check in checks:
        key = (check["name"], check["object"], check["detail"])
        if key not in seen:
            seen.add(key)
            unique.append(check)
    return {"passed": all(check["passed"] for check in unique), "checks": unique,
            "triangles": tri_counts, "objects": [obj.name for obj in resolved]}


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="qa_check.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--objects", required=True, help="comma-separated object names")
    parser.add_argument("--budget", type=int, default=None, help="triangle budget per object")
    parser.add_argument("--texel", type=float, default=None, help="target texel density in px/cm")
    parser.add_argument("--tolerance", type=float, default=0.25)
    parser.add_argument("--require-uv1", action="store_true")
    parser.add_argument("--no-ucx", action="store_true", help="do not require UCX_ children")
    parser.add_argument("--no-names", action="store_true", help="skip naming checks")
    parser.add_argument("--overlap", default="sat", choices=OVERLAP_METHODS, help="UV overlap test to run")
    parser.add_argument("--tile-range", type=float, nargs=2, default=list(DEFAULT_TILE_RANGE),
                        metavar=("LOW", "HIGH"), help="allowed UV0 tile range")
    parser.add_argument("--max-influences", type=int, default=MAX_INFLUENCES, help="skin influence limit")
    parser.add_argument("--json", default=None, help="also write the result to this path")
    return parser.parse_args(argv)


def main() -> int:
    """CLI entry point: print the JSON result; return 1 when the check fails."""
    args = _parse_args()
    names = [name.strip() for name in args.objects.split(",") if name.strip()]
    try:
        result = qa_check(names, budget_tris=args.budget, texel_density=args.texel, tolerance=args.tolerance,
                          require_uv1=args.require_uv1, require_ucx=not args.no_ucx, check_names=not args.no_names,
                          uv0_tile_range=args.tile_range, overlap_method=args.overlap,
                          max_influences=args.max_influences)
    except Exception as exc:  # noqa: BLE001 - the CLI contract is JSON on stdout plus exit 1
        result = {"passed": False, "checks": [], "error": f"{type(exc).__name__}: {exc}"}
    text = json.dumps(result, indent=2)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
