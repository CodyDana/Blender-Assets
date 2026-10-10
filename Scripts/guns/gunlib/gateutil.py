"""Shared helpers for the gate drivers (gunlib 0.2.0, promoted from the AR-01 rifle_* scripts).

Plain-Python helpers (numpy only): gate records, sha256, rotation angles, plane sections of triangle meshes, band
clipping. Blender-only helpers (mathutils BVH trees, ray parity, object arrays) import mathutils / bpy lazily, so this
module also imports in plain Python.

Every function here is a verbatim move of the rifle scripts' local copies (rifle_magfit_check, rifle_mag_fit,
rifle_g5_lods, rifle_rig_verify), so the promoted drivers reproduce the AR-01's committed gate values to the bit.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Optional

import numpy as np


# ====================================================================== records
def gate(name, value, threshold, ok, note=None) -> Dict[str, Any]:
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def angle_deg(Ra, Rb) -> float:
    """Angle of Ra^T Rb, robust near 0 (atan2 of the skew and symmetric parts; acos loses ~0.01 deg there)."""
    R = Ra.T @ Rb
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return math.degrees(math.atan2(0.5 * np.linalg.norm(v), 0.5 * (np.trace(R) - 1.0)))


def quat_xyzw_matrix(q) -> np.ndarray:
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# ====================================================================== plane sections (numpy)
def section_segs(V, T, axis, c) -> np.ndarray:
    """Segments (n x 2 x 3) where the plane coord[axis] = c cuts the triangles."""
    s = V[:, axis] - c
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    P, m_ = [], []
    for e0, e1 in ((A, B), (B, C), (C, A)):
        s0, s1 = s[e0], s[e1]
        m = (s0 * s1) < 0
        t = np.where(m, s0 / np.where(m, s0 - s1, 1.0), 0.0)
        P.append(V[e0] + (V[e1] - V[e0]) * t[:, None])
        m_.append(m)
    cnt = m_[0].astype(int) + m_[1] + m_[2]
    out = []
    for i in np.nonzero(cnt == 2)[0]:
        q = [P[k][i] for k in range(3) if m_[k][i]]
        out.append(q)
    return np.array(out) if out else np.zeros((0, 2, 3))


def band_pts(segs, axis, lo, hi) -> np.ndarray:
    """Endpoints of the section segments clipped to lo <= |coord[axis]| <= hi (a plane section measured on its
    segments, not only on the mesh's vertices: long faces cross a band with no vertex in it)."""
    out = []
    for a, b in segs:
        a, b = np.asarray(a), np.asarray(b)
        for sgn in (1.0, -1.0):
            ya, yb = sgn * a[axis], sgn * b[axis]
            t0, t1, d = 0.0, 1.0, yb - ya
            for bound, above in ((lo, True), (hi, False)):
                if abs(d) < 1e-12:
                    if (ya < bound) if above else (ya > bound):
                        t0, t1 = 1.0, 0.0
                    continue
                t = (bound - ya) / d
                if (d > 0) == above:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
            if t0 <= t1:
                out += [a + (b - a) * t0, a + (b - a) * t1]
    return np.array(out) if out else np.zeros((0, 3))


def in_box(P, box) -> np.ndarray:
    """Rows of P inside box {'X': (lo, hi), 'Y': ..., 'Z': ...} (inclusive)."""
    lo = np.array([box["X"][0], box["Y"][0], box["Z"][0]])
    hi = np.array([box["X"][1], box["Y"][1], box["Z"][1]])
    return np.all((P >= lo) & (P <= hi), axis=1)


def box_lohi(box, offset=(0.0, 0.0, 0.0)):
    o = np.asarray(offset, float)
    return (np.array([box["X"][0], box["Y"][0], box["Z"][0]]) - o,
            np.array([box["X"][1], box["Y"][1], box["Z"][1]]) - o)


# ====================================================================== Blender-side (mathutils, lazy)
def tree(V, T):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in T], all_triangles=True,
                                epsilon=0.0)


def _dirs():
    from mathutils import Vector
    return [Vector((0.31, 0.53, 0.79)).normalized(), Vector((-0.62, 0.21, -0.75)).normalized(),
            Vector((0.12, -0.91, 0.40)).normalized()]


def parity(t, p, d, cap=2000.0) -> bool:
    from mathutils import Vector
    n, o = 0, Vector(p)
    for _ in range(64):
        h = t.ray_cast(o, d, cap)
        if h[0] is None:
            break
        n += 1
        o = h[0] + d * 1e-4
    return n % 2 == 1


def depth_inside(points, t, lo, hi, cap=30.0) -> float:
    """Deepest point inside the closed mesh of tree t (inside by ray parity, 2 of 3 rays odd; the nearest-face normal
    test calls points beyond an edge 'inside'), depth = distance to its nearest surface (mm). Points outside the box
    lo..hi are skipped."""
    from mathutils import Vector
    dirs = _dirs()
    best = 0.0
    P = np.asarray(points, float).reshape(-1, 3)
    for p in P[np.all((P >= lo) & (P <= hi), axis=1)]:      # the box test, vectorised (same points, same order)
        h = t.find_nearest(Vector(p), cap)
        if h[0] is None or h[3] <= best:
            continue
        if sum(parity(t, p, d) for d in dirs) >= 2:
            best = h[3]
    return best


def nearest(points, t, cap=20.0) -> float:
    """Smallest distance from the points to the tree's surface (capped)."""
    from mathutils import Vector
    b = cap
    for p in points:
        h = t.find_nearest(Vector(p), b)
        if h[0] is not None and h[3] < b:
            b = h[3]
    return float(b)


def nearest_arg(points, t, cap=10.0):
    from mathutils import Vector
    b, arg = cap, None
    for i, p in enumerate(points):
        h = t.find_nearest(Vector(p), b)
        if h[0] is not None and h[3] < b:
            b, arg = h[3], i
    return b, arg


def mesh_np(o, offset=(0.0, 0.0, 0.0), materials: bool = False):
    """Object vertices in mm (world, + offset: pass the Grip point for frame M) and loop triangles; optionally the
    material name per triangle."""
    me = o.data
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(o.matrix_world)
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0
    if any(offset):
        V = V + np.asarray(offset, float)
    me.calc_loop_triangles()
    T = np.empty(len(me.loop_triangles) * 3, int)
    me.loop_triangles.foreach_get("vertices", T)
    T = T.reshape(-1, 3)
    if not materials:
        return V, T
    mi = np.empty(len(me.loop_triangles), int)
    me.loop_triangles.foreach_get("material_index", mi)
    names = [s.material.name if s.material else "" for s in o.material_slots]
    return V, T, np.array([names[i] if i < len(names) else "" for i in mi])


def clear_scene(data_blocks: bool = False) -> None:
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    if data_blocks:
        for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
            for d in list(coll):
                coll.remove(d)


def argv_after_dashes():
    import sys
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(argv, name, default=None, cast=None) -> Optional[Any]:
    if name in argv:
        v = argv[argv.index(name) + 1]
        return cast(v) if cast else v
    return default
