#!/usr/bin/env python
"""props_lib.smokebomb_geometry - smokebomb_mesh pieces -> one Blender mesh per LOD.

The only module that talks to bpy about geometry.  It assembles every piece of every strip
into one mesh through a 1 nm POSITION-KEYED VERTEX FACTORY (the pack rule): a vertex is
identified by its position quantised to a nanometre, so the only vertices two pieces can
share are the deliberate ones (the two sides of a cut across a strip, which carry the
same chart coordinates and therefore the same position), and qa_check's coincident-
vertex gate can never trip on an accident.

Frames: pieces are in the reference CAMERA frame in millimetres; Blender gets metres in
its own frame (X = Xc, Y = -Zc, Z = Yc - see smokebomb_strips).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import smokebomb_strips as SS

MM = 0.001
UV_NAME = "UVMap"
KEY_NM = 1e-9


@dataclass
class Assembled:
    verts: np.ndarray                 # (V, 3) metres, Blender frame
    tris: np.ndarray                  # (T, 3)
    loop_uv: np.ndarray               # (T, 3, 2) atlas UV per corner
    tri_strip: np.ndarray             # (T,) strip index
    tri_wall: np.ndarray              # (T,) bool
    tri_island: np.ndarray            # (T,) island index
    sharp: List[Tuple[int, int]]
    vert_strip: np.ndarray            # (V,) strip index of the vertex's first piece
    vert_chart: np.ndarray            # (V, 2) chart (s, w) mm
    report: Dict[str, object] = field(default_factory=dict)


class VertexFactory:
    """Vertices keyed by position at 1 nm: the same position is the same vertex."""

    def __init__(self):
        self.index: Dict[Tuple[int, int, int], int] = {}
        self.co: List[Tuple[float, float, float]] = []
        self.merged = 0

    def get(self, p) -> int:
        key = (int(round(p[0] / KEY_NM)), int(round(p[1] / KEY_NM)), int(round(p[2] / KEY_NM)))
        i = self.index.get(key)
        if i is None:
            i = len(self.co)
            self.index[key] = i
            self.co.append((key[0] * KEY_NM, key[1] * KEY_NM, key[2] * KEY_NM))
        else:
            self.merged += 1
        return i


def assemble(pieces, island_uv) -> Assembled:
    """``island_uv(piece_index, chart_uv (n, 2)) -> atlas uv (n, 2)`` places each piece."""
    fac = VertexFactory()
    tris, luv, tstrip, twall, tisl = [], [], [], [], []
    sharp = []
    vstrip: Dict[int, int] = {}
    vchart: Dict[int, Tuple[float, float]] = {}
    for pi, pc in enumerate(pieces):
        X = SS.cam_to_blender(pc.verts_cam * (pc.radius_mm[:, None] * MM))
        ids = np.array([fac.get(x) for x in X], np.int64)
        for q, vid in enumerate(ids.tolist()):
            if vid not in vstrip:
                vstrip[vid] = pc.strip
                vchart[vid] = (float(pc.uv_mm[q, 0]), float(pc.uv_mm[q, 1]))
        uv = island_uv(pi, pc.uv_mm)
        T = pc.tris
        is_wall = pc.wall[T].any(axis=1)
        tris.append(ids[T])
        luv.append(uv[T])
        tstrip.append(np.full(len(T), pc.strip))
        twall.append(is_wall)
        tisl.append(np.full(len(T), pi))
        for a, b in pc.sharp:
            sharp.append((int(ids[a]), int(ids[b])))
    V = np.array(fac.co, np.float64)
    T = np.concatenate(tris)
    # drop triangles that collapsed through the 1 nm weld (none expected)
    ok = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])
    out = Assembled(V, T[ok], np.concatenate(luv)[ok], np.concatenate(tstrip)[ok],
                    np.concatenate(twall)[ok], np.concatenate(tisl)[ok], sharp,
                    np.array([vstrip.get(i, -1) for i in range(len(V))]),
                    np.array([vchart.get(i, (0.0, 0.0)) for i in range(len(V))]))
    out.report = {"vertices": int(len(V)), "triangles": int(ok.sum()),
                  "collapsed_dropped": int((~ok).sum()), "welded_by_position": int(fac.merged)}
    return out


def make_object(name: str, A: Assembled, collection=None):
    import bpy
    from mathutils import Matrix
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in A.verts], [], [tuple(t) for t in A.tris.tolist()])
    mesh.update()
    if mesh.validate(verbose=False):
        raise RuntimeError(f"{name}: Blender rejected the topology")
    uv = mesh.uv_layers.new(name=UV_NAME)
    # from_pydata keeps face order, and every face is a triangle
    flat = A.loop_uv.reshape(-1, 2)
    uv.data.foreach_set("uv", flat.astype(np.float32).ravel())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    sharp = {(min(a, b), max(a, b)) for a, b in A.sharp}
    flags = np.zeros(len(mesh.edges), bool)
    ev = np.empty(len(mesh.edges) * 2, np.int64)
    mesh.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    for i, (a, b) in enumerate(ev.tolist()):
        if (min(a, b), max(a, b)) in sharp:
            flags[i] = True
    attr = mesh.attributes.get("sharp_edge") or mesh.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    attr.data.foreach_set("value", flags)
    # per-face data the texture bake and the measurement read
    fa = mesh.attributes.new("sb_strip", "INT", "FACE")
    fa.data.foreach_set("value", A.tri_strip.astype(np.int32))
    fw = mesh.attributes.new("sb_wall", "BOOLEAN", "FACE")
    fw.data.foreach_set("value", A.tri_wall.astype(bool))
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    return obj


__all__ = ["Assembled", "VertexFactory", "assemble", "make_object", "UV_NAME", "MM"]


def _fit_in_box(corners: np.ndarray, box) -> np.ndarray:
    """Pull a chart triangle toward its centroid until it fits the island box (so it
    never reads a neighbouring island); its shape is kept, so it never collapses."""
    s0, s1, w0, w1 = box
    e = 1e-4
    c = corners.mean(axis=0)
    c = np.array([min(max(c[0], s0 + e), s1 - e), min(max(c[1], w0 + e), w1 - e)])
    f = 1.0
    for p in corners:
        d = p - c
        for lo, hi, dv, cv in ((s0 + e, s1 - e, d[0], c[0]), (w0 + e, w1 - e, d[1], c[1])):
            if dv > 1e-12:
                f = min(f, (hi - cv) / dv)
            elif dv < -1e-12:
                f = min(f, (lo - cv) / dv)
    f = max(f, 1e-3)
    return c + (corners - c) * f


def assemble_by_triangle(X_m: np.ndarray, T: np.ndarray, tri_strip: np.ndarray,
                         corner_chart: np.ndarray, atlas, lookup, method: str) -> Assembled:
    """A coarser LOD: every triangle is mapped through the LOD0 island (same strip) that
    holds its centroid, pulled inside that island's box if it pokes out: every LOD reads
    the same texels for the same point of tape, and no triangle reaches a neighbour."""
    fac = VertexFactory()
    ids = np.array([fac.get(x) for x in X_m], np.int64)
    TT = ids[T]
    luv = np.zeros((len(T), 3, 2))
    pulled = 0
    unmirrored = 0
    for ti in range(len(T)):
        cc = corner_chart[ti]
        c = cc.mean(axis=0)
        key, box = lookup(atlas, int(tri_strip[ti]), float(c[0]), float(c[1]))
        fitted = _fit_in_box(cc, box)
        if not np.allclose(fitted, cc):
            pulled += 1
        # the chart is right-handed about the outward normal, so an outward triangle is
        # counter-clockwise in it; a resampled triangle that straddles a fold of its
        # strip's chart can come out clockwise (a MIRRORED UV) - swap two of its corners'
        # chart points, which un-mirrors it at the cost of a scrambled 7 mm texel patch
        ar = ((fitted[1, 0] - fitted[0, 0]) * (fitted[2, 1] - fitted[0, 1])
              - (fitted[2, 0] - fitted[0, 0]) * (fitted[1, 1] - fitted[0, 1]))
        if ar < 0:
            fitted = fitted[[0, 2, 1]]
            unmirrored += 1
        luv[ti] = atlas.uv(key, fitted)
    ok = (TT[:, 0] != TT[:, 1]) & (TT[:, 1] != TT[:, 2]) & (TT[:, 0] != TT[:, 2])
    V = np.array(fac.co, np.float64)
    out = Assembled(V, TT[ok], luv[ok], tri_strip[ok].copy(), np.zeros(int(ok.sum()), bool),
                    np.zeros(int(ok.sum()), np.int64), [], np.full(len(V), -1), np.zeros((len(V), 2)))
    out.report = {"vertices": int(len(V)), "triangles": int(ok.sum()), "collapsed_dropped": int((~ok).sum()),
                  "welded_by_position": int(fac.merged), "method": method,
                  "triangles_pulled_into_their_island": pulled,
                  "triangles_unmirrored": unmirrored}
    return out


def assemble_pieces_by_lookup(pieces, atlas, lookup) -> Assembled:
    Xs, Ts, S, C = [], [], [], []
    n = 0
    for p in pieces:
        X = SS.cam_to_blender(p.verts_cam * (p.radius_mm[:, None] * MM))
        Xs.append(X)
        Ts.append(p.tris + n)
        S.append(np.full(len(p.tris), p.strip))
        C.append(p.uv_mm[p.tris])
        n += len(X)
    return assemble_by_triangle(np.concatenate(Xs), np.concatenate(Ts), np.concatenate(S),
                                np.concatenate(C), atlas, lookup, "strip pieces, no walls")


def assemble_resampled(R, atlas, lookup) -> Assembled:
    X = SS.cam_to_blender(R.verts_cam * (R.radius_mm[:, None] * MM))
    return assemble_by_triangle(X, R.tris, R.tri_strip, R.loop_chart, atlas, lookup,
                                "geodesic resample")


# =========================================================================== collision
def pentakis_hull(r_max_m: float):
    """A pentakis dodecahedron whose 60 faces are all TANGENT to the sphere r_max (the dual
    of the truncated icosahedron): 32 vertices, circumscribed, 1.064 x the sphere's volume
    (study 8).  Built from its 60 face planes; each vertex is placed on its own direction
    at r / max(n . v), which is exact for a vertex of the plane intersection."""
    t = (1.0 + 5 ** 0.5) / 2.0
    # truncated icosahedron vertices: even permutations of (0, +-1, +-3t), (+-1, +-(2+t), +-2t),
    # (+-t, +-2, +-(2t+1))  -> the 60 face normals
    base = [(0.0, 1.0, 3 * t), (1.0, 2 + t, 2 * t), (t, 2.0, 2 * t + 1)]
    normals = set()
    for a, b, c in base:
        for sa in (1, -1):
            for sb in (1, -1):
                for sc in (1, -1):
                    v = (a * sa, b * sb, c * sc)
                    for perm in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
                        normals.add(tuple(round(v[i], 9) for i in perm))
    N = SS.normalize(np.array(sorted(normals)))
    assert len(N) == 60, len(N)
    # the vertices: every triple of face planes, solved, kept where no plane is violated
    import itertools
    pts = []
    for i, j, k in itertools.combinations(range(60), 3):
        A = N[[i, j, k]]
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        x = np.linalg.solve(A, np.full(3, r_max_m))
        if (N @ x <= r_max_m * (1 + 1e-9)).all():
            pts.append(x)
    V = []
    for x in pts:
        if not any(np.linalg.norm(x - y) < 1e-9 * r_max_m + 1e-12 for y in V):
            V.append(x)
    V = np.array(V)
    if len(V) != 32:
        raise RuntimeError(f"pentakis hull has {len(V)} vertices, not 32")
    # faces: every plane holds exactly three vertices
    faces = []
    for n in N:
        on = np.nonzero(np.abs(V @ n - r_max_m) < 1e-6 * r_max_m)[0]
        if len(on) != 3:
            raise RuntimeError(f"pentakis face has {len(on)} vertices")
        a, b, c = on
        if np.dot(np.cross(V[b] - V[a], V[c] - V[a]), n) < 0:
            b, c = c, b
        faces.append((int(a), int(b), int(c)))
    return V, faces


def make_hull(obj, r_max_m: float, index: int = 0):
    import bpy
    from mathutils import Matrix
    name = f"UCX_{obj.name}_{index:02d}"
    V, F = pentakis_hull(r_max_m)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in V], [], F)
    mesh.update()
    if mesh.validate(verbose=False):
        raise RuntimeError(f"{name}: invalid hull")
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


def hull_worst_outside_m(hull, obj) -> float:
    hc = np.array([v.co[:] for v in hull.data.vertices])
    co = np.array([v.co[:] for v in obj.data.vertices])
    worst = -1e9
    for poly in hull.data.polygons:
        n = np.array(poly.normal[:])
        n /= np.linalg.norm(n)
        d = float(n @ hc[poly.vertices[0]])
        worst = max(worst, float((co @ n - d).max()))
    return worst


def hull_volume_m3(hull) -> float:
    co = np.array([v.co[:] for v in hull.data.vertices])
    vol = 0.0
    for poly in hull.data.polygons:
        a, b, c = (co[i] for i in poly.vertices)
        vol += float(np.dot(a, np.cross(b, c))) / 6.0
    return abs(vol)


__all__ += ["assemble_by_triangle", "assemble_pieces_by_lookup", "assemble_resampled", "pentakis_hull", "make_hull",
            "hull_worst_outside_m", "hull_volume_m3"]


# =========================================================================== Unreal's degenerate rule
#: MEASURED on UE 5.8.2 (WorkFiles/smokebomb/UnrealCheck, round trip of build r1): the static
#: mesh build drops every triangle whose |e1 x e2|^2 < 1e-8 cm^4, i.e. AREA < 0.005 mm2 -
#: slivers the chart triangulation leaves at a few tight corners (5 on LOD0, 2 on LOD1, each
#: under 16 um high).  Unreal's triangle count must equal ours, so they go here, with a margin.
MIN_TRIANGLE_AREA_MM2 = 0.008


def drop_slivers(A: Assembled, min_area_mm2: float = MIN_TRIANGLE_AREA_MM2) -> Assembled:
    P = A.verts[A.tris] * 1000.0
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    keep = area >= min_area_mm2
    T = A.tris[keep]
    used = np.unique(T)
    remap = -np.ones(len(A.verts), np.int64)
    remap[used] = np.arange(len(used))
    sharp = [(int(remap[a]), int(remap[b])) for a, b in A.sharp if remap[a] >= 0 and remap[b] >= 0]
    out = Assembled(A.verts[used], remap[T], A.loop_uv[keep], A.tri_strip[keep], A.tri_wall[keep],
                    A.tri_island[keep], sharp, A.vert_strip[used], A.vert_chart[used])
    out.report = dict(A.report)
    out.report["triangles"] = int(keep.sum())
    out.report["vertices"] = int(len(used))
    out.report["slivers_dropped_below_mm2"] = [min_area_mm2, int((~keep).sum())]
    return out


__all__ += ["MIN_TRIANGLE_AREA_MM2", "drop_slivers"]
