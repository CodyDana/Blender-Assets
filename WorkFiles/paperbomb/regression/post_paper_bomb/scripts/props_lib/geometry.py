#!/usr/bin/env python
"""props_lib.geometry - turn a ``props_lib.sheet.SheetMesh`` into Blender objects.

Everything bpy-shaped about the card lives here: the mesh datablock and its UV layer,
smooth shading and sharp edges, the sockets, and the collision hull.  The maths is in
``sheet``; this module only talks to Blender.

COLLISION (study 3, "build_to.collision")
-----------------------------------------
``make_card_hull`` does NOT use ``pipeline.helpers.make_ucx_hull``.  That helper hulls
the evaluated mesh and then decimates, which for a 0.15 mm card produces a hull that is
0.15 mm thick - degenerate for Chaos, and the study says so.  This one builds a
CONTAINING octagonal prism instead: eight supporting half-planes in the plan, at 0, 45,
90 ... degrees, each pushed out to the furthest vertex, intersected into an octagon, and
extruded in Z to at least 3 mm.  Two consequences worth stating:

* it is guaranteed to contain LOD0, because a supporting half-plane cannot cut a point
  off.  The Unreal round-trip gate measures that, and it is a gate rather than a hope;
* the card's own 45 deg corner clips are exactly perpendicular to the diagonal
  directions, so the octagon lies ON them and the hull wastes nothing there.

Sixteen vertices, which is the study's ceiling and half of Unreal's 32.

THE HULL'S NAME
---------------
Unreal matches collision against the RENDER MESH NODE NAME.  The node is
``SM_PaperBomb_LOD0`` once ``pipeline.helpers.make_lod_group`` has renamed it, so the
hull must end up ``UCX_SM_PaperBomb_LOD0_00``.  ``make_lod_group`` rewrites helper
children with the mesh, so the hull is created as ``UCX_SM_PaperBomb_00`` on a mesh
called ``SM_PaperBomb`` and follows it.  ``UCX_SM_PaperBomb_00`` left on a node called
``SM_PaperBomb_LOD0`` imports with convex count 0 and NO collision, silently.

SOCKETS
-------
Empties (FBX Nulls), through ``pipeline.helpers.make_socket`` so they carry the pack's
measured 180 deg Y correction.  Each one is SNAPPED to the real deformed surface at its
paper coordinate rather than placed at the study's nominal millimetres, and how far it
moved is measured and reported: the two creases tilt the top panel, so the study's
``Cord`` at Z = 0 would have floated 1.4 mm off the paper.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from .sheet import MM, SheetMesh, Surface

UV_NAME = "UVMap"


# ===========================================================================
# 1.  The mesh
# ===========================================================================

def make_object(name: str, sheet: SheetMesh, material: Optional["bpy.types.Material"] = None,
                collection: Optional["bpy.types.Collection"] = None) -> "bpy.types.Object":
    """Create ``name`` from ``sheet``: geometry, UV0, smooth shading, sharp rim edges."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([Vector(v) for v in sheet.verts], [], [list(f) for f in sheet.faces])
    mesh.update()
    if mesh.validate(verbose=False):
        raise RuntimeError(f"{name}: Blender rejected the topology")

    uv = mesh.uv_layers.new(name=UV_NAME)
    loop = 0
    for fi, face in enumerate(mesh.polygons):
        coords = sheet.loop_uv[fi]
        for k in range(face.loop_total):
            uv.data[face.loop_start + k].uv = coords[k]
        loop += face.loop_total

    for poly in mesh.polygons:
        poly.use_smooth = True
    sharp = {tuple(sorted(e)) for e in sheet.sharp_edges}
    for edge in mesh.edges:
        if tuple(sorted((edge.vertices[0], edge.vertices[1]))) in sharp:
            edge.use_edge_sharp = True

    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    obj.matrix_world = Matrix.Identity(4)
    return obj


# ===========================================================================
# 2.  Collision
# ===========================================================================

OCTAGON_DIRECTIONS = [(math.cos(math.radians(a)), math.sin(math.radians(a)))
                      for a in (0, 45, 90, 135, 180, 225, 270, 315)]


def containing_octagon(points_xy: np.ndarray,
                       directions: Sequence[Tuple[float, float]] = OCTAGON_DIRECTIONS
                       ) -> np.ndarray:
    """The smallest octagon with these eight face normals that contains every point."""
    d = np.asarray(directions, np.float64)
    h = (points_xy @ d.T).max(axis=0)                  # support in each direction
    verts = []
    n = len(d)
    for i in range(n):
        a, b = d[i], d[(i + 1) % n]
        m = np.array([a, b])
        rhs = np.array([h[i], h[(i + 1) % n]])
        det = m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0]
        if abs(det) < 1e-12:
            continue
        verts.append(np.linalg.solve(m, rhs))
    return np.array(verts, np.float64)


def make_card_hull(obj: "bpy.types.Object", min_thickness_m: float = 0.003,
                   index: int = 0) -> "bpy.types.Object":
    """``UCX_<obj.name>_<index:02d>``: a containing octagonal prism, 16 vertices."""
    name = f"UCX_{obj.name}_{index:02d}"
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"{name!r} already exists")
    co = np.array([v.co[:] for v in obj.data.vertices], np.float64)
    ring = containing_octagon(co[:, :2])
    z0, z1 = float(co[:, 2].min()), float(co[:, 2].max())
    if (z1 - z0) < min_thickness_m:
        mid = 0.5 * (z0 + z1)
        z0, z1 = mid - min_thickness_m * 0.5, mid + min_thickness_m * 0.5

    verts = [(float(x), float(y), z0) for x, y in ring] + [(float(x), float(y), z1) for x, y in ring]
    n = len(ring)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if mesh.validate(verbose=False):
        raise RuntimeError(f"{name}: invalid hull topology")
    hull = bpy.data.objects.new(name, mesh)
    for parent in obj.users_collection:
        parent.objects.link(hull)
    hull.parent = obj
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.matrix_basis = Matrix.Identity(4)
    hull.hide_render = True
    hull.display_type = "WIRE"
    hull["ue_collision"] = "UCX"
    return hull


def hull_contains(hull: "bpy.types.Object", obj: "bpy.types.Object") -> float:
    """Worst distance in METRES by which a vertex of ``obj`` sits outside ``hull``."""
    hc = np.array([v.co[:] for v in hull.data.vertices], np.float64)
    planes = []
    for poly in hull.data.polygons:
        nrm = np.array(poly.normal[:], np.float64)
        if np.linalg.norm(nrm) < 1e-12:
            continue
        nrm = nrm / np.linalg.norm(nrm)
        planes.append((nrm, float(np.dot(nrm, hc[poly.vertices[0]]))))
    co = np.array([v.co[:] for v in obj.data.vertices], np.float64)
    worst = -1e9
    for nrm, d in planes:
        worst = max(worst, float((co @ nrm - d).max()))
    return worst


# ===========================================================================
# 3.  Sockets
# ===========================================================================

def snap_socket(surface: Surface, spec, socket) -> Dict[str, object]:
    """Where a socket really sits: on the deformed surface at its paper coordinate."""
    from pipeline.helpers import ue_socket_transform  # noqa: F401  (import check only)

    if socket.snap_paper_uv is None:
        return {"position_mm": list(socket.position_mm), "snapped": False}
    u, v = socket.snap_paper_uv
    p, tu, tv, n = surface.frame(np.array([float(u)]), np.array([float(v)]))
    off = {"front": spec.half_thickness_mm, "back": -spec.half_thickness_mm, "mid": 0.0}[socket.snap_side]
    pos = (p[0] + n[0] * off)
    nominal = np.array(socket.position_mm, np.float64)
    return {
        "position_mm": [round(float(x), 4) for x in pos],
        "study_nominal_mm": [round(float(x), 4) for x in nominal],
        "moved_mm": round(float(np.linalg.norm(pos - nominal)), 4),
        "surface_normal": [round(float(x), 5) for x in n[0]],
        "paper_uv_mm": [float(u), float(v)],
        "snapped": True,
    }


def make_sockets(obj: "bpy.types.Object", surface: Surface, spec) -> List[Dict[str, object]]:
    """Create every socket as an Empty child of ``obj``; return what was measured."""
    from pipeline.helpers import make_socket

    records: List[Dict[str, object]] = []
    for socket in spec.sockets:
        info = snap_socket(surface, spec, socket)
        location = tuple(x * MM for x in info["position_mm"])
        rotation = tuple(math.radians(a) for a in socket.rotation_deg)
        make_socket(obj, socket.name, location, rotation)
        info["name"] = socket.name
        info["rotation_deg"] = list(socket.rotation_deg)
        info["use"] = socket.use
        records.append(info)
    return records


# ===========================================================================
# 4.  Measurement helpers that need bpy
# ===========================================================================

def triangles_of(obj: "bpy.types.Object") -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def bounds_mm(obj: "bpy.types.Object") -> Dict[str, List[float]]:
    co = np.array([v.co[:] for v in obj.data.vertices], np.float64) * 1000.0
    return {"min": [round(float(x), 4) for x in co.min(axis=0)],
            "max": [round(float(x), 4) for x in co.max(axis=0)],
            "size": [round(float(x), 4) for x in np.ptp(co, axis=0)]}


def unreal_bounds_radius_mm(obj: "bpy.types.Object") -> float:
    """Unreal's bounds sphere radius: the box half-extent's length, in millimetres."""
    b = bounds_mm(obj)
    half = [0.5 * s for s in b["size"]]
    return round(math.sqrt(sum(h * h for h in half)), 4)


__all__ = ["UV_NAME", "make_object", "make_card_hull", "make_sockets", "snap_socket",
           "containing_octagon", "hull_contains", "triangles_of", "bounds_mm",
           "unreal_bounds_radius_mm"]
