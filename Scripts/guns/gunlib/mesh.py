"""Mesh primitives in millimetres (numpy), converted to Blender objects in metres.

Every primitive returns a closed solid (prism of a 2D outline, loft of rings, revolve of a profile, box, cylinder,
ellipsoid). Faces may be n-gons (booleans and bevels handle them); ``bl.finish`` triangulates n-gons at the end
because qa_check fails them. Normals are recalculated outward in Blender (all solids are closed).

Coordinates are the gun's measurement frame M (mm). ``to_object(offset=...)`` subtracts the build-frame origin
(the Grip point) so Blender objects live in frame B.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

import numpy as np


class Mesh:
    def __init__(self):
        self.V: List[np.ndarray] = []
        self.F: List[tuple] = []
        self._n = 0

    def add_verts(self, P) -> np.ndarray:
        P = np.asarray(P, float).reshape(-1, 3)
        idx = np.arange(self._n, self._n + len(P))
        self.V.append(P)
        self._n += len(P)
        return idx

    def face(self, idx):
        idx = tuple(int(i) for i in idx)
        if len(set(idx)) >= 3:
            self.F.append(idx)

    def extend(self, other: "Mesh") -> "Mesh":
        off = self._n
        for P in other.V:
            self.V.append(P)
        self._n += other._n
        for f in other.F:
            self.F.append(tuple(i + off for i in f))
        return self

    def verts(self) -> np.ndarray:
        return np.vstack(self.V) if self.V else np.zeros((0, 3))

    def transformed(self, M4) -> "Mesh":
        out = Mesh()
        P = self.verts()
        Q = (np.c_[P, np.ones(len(P))] @ np.asarray(M4, float).T)[:, :3]
        out.add_verts(Q)
        out.F = list(self.F)
        return out

    def translated(self, d) -> "Mesh":
        M = np.eye(4)
        M[:3, 3] = d
        return self.transformed(M)

    def tri_count(self) -> int:
        return sum(len(f) - 2 for f in self.F)

    # ------------------------------------------------------------------ Blender
    def to_object(self, name, collection=None, offset=(0.0, 0.0, 0.0), smooth_deg: Optional[float] = 30.0):
        import bpy
        import bmesh
        P = (self.verts() - np.asarray(offset, float)) * 0.001
        me = bpy.data.meshes.new(name)
        me.from_pydata(P.tolist(), [], [list(f) for f in self.F])
        me.update()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-9)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(me)
        bm.free()
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        if smooth_deg is not None:
            me.set_sharp_from_angle(angle=math.radians(smooth_deg))
        me.update()
        ob = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob


# ====================================================================== primitives
def _plane_pts(P2, d, plane):
    P2 = np.asarray(P2, float)
    a, b = P2[:, 0], P2[:, 1]
    dd = np.full(len(P2), float(d))
    if plane == "XZ":
        return np.c_[a, dd, b]
    if plane == "XY":
        return np.c_[a, b, dd]
    if plane == "YZ":
        return np.c_[dd, a, b]
    raise ValueError(plane)


def prism(P2, d0, d1, plane="XZ") -> Mesh:
    """Extrude a closed 2D outline (a, b) between depths d0..d1 along the plane's normal axis."""
    from .geo2d import ccw, dedupe
    P2 = ccw(dedupe(P2))
    m = Mesh()
    i0 = m.add_verts(_plane_pts(P2, d0, plane))
    i1 = m.add_verts(_plane_pts(P2, d1, plane))
    n = len(P2)
    m.face(i0[::-1])
    m.face(i1)
    for k in range(n):
        k2 = (k + 1) % n
        m.face((i0[k], i0[k2], i1[k2], i1[k]))
    return m


def loft(rings: Sequence[np.ndarray], cap0=True, cap1=True, closed_loop=False) -> Mesh:
    """Quads between consecutive closed rings (same vertex count); n-gon caps at both ends."""
    m = Mesh()
    idx = [m.add_verts(r) for r in rings]
    n = len(rings[0])
    R = len(rings) if not closed_loop else len(rings) + 1
    for r in range(R - 1):
        a, b = idx[r % len(idx)], idx[(r + 1) % len(idx)]
        for k in range(n):
            k2 = (k + 1) % n
            m.face((a[k], a[k2], b[k2], b[k]))
    if not closed_loop:
        if cap0:
            m.face(idx[0][::-1])
        if cap1:
            m.face(idx[-1])
    return m


def _frame(axis):
    w = np.asarray(axis, float)
    w = w / np.linalg.norm(w)
    t = np.array([0.0, 0.0, 1.0]) if abs(w[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(t, w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    return u, v, w


def revolve(profile, origin, axis, nseg=32, phase_deg=0.0, ref=None) -> Mesh:
    """Revolve a profile [(t, r), ...] (t along the axis from origin, r radius) around the axis. Points with r == 0
    become poles. The profile runs from one end to the other; the solid is closed by poles or n-gon caps."""
    o = np.asarray(origin, float)
    u, v, w = _frame(axis)
    if ref is not None:
        u = np.asarray(ref, float) - (np.asarray(ref, float) @ w) * w
        u /= np.linalg.norm(u)
        v = np.cross(w, u)
    th = np.radians(phase_deg) + np.linspace(0, 2 * math.pi, nseg, endpoint=False)
    ring_dirs = np.outer(np.cos(th), u) + np.outer(np.sin(th), v)
    m = Mesh()
    rows = []
    for t, r in profile:
        if r <= 1e-9:
            rows.append(("pole", m.add_verts([o + w * t])[0]))
        else:
            rows.append(("ring", m.add_verts(o + w * t + r * ring_dirs)))
    for (ka, a), (kb, b) in zip(rows[:-1], rows[1:]):
        if ka == "ring" and kb == "ring":
            for k in range(nseg):
                k2 = (k + 1) % nseg
                m.face((a[k], a[k2], b[k2], b[k]))
        elif ka == "pole" and kb == "ring":
            for k in range(nseg):
                m.face((a, b[(k + 1) % nseg], b[k]))
        elif ka == "ring" and kb == "pole":
            for k in range(nseg):
                m.face((a[k], a[(k + 1) % nseg], b))
    if rows[0][0] == "ring":
        m.face(rows[0][1][::-1])
    if rows[-1][0] == "ring":
        m.face(rows[-1][1])
    return m


def cylinder(p0, p1, r, nseg=32, phase_deg=0.0, ref=None) -> Mesh:
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    return revolve([(0.0, r), (L, r)], p0, p1 - p0, nseg, phase_deg, ref)


def box(x0, x1, y0, y1, z0, z1) -> Mesh:
    return prism([[x0, z0], [x1, z0], [x1, z1], [x0, z1]], y0, y1, "XZ")


def ellipsoid(c, rx, ry, rz, nu=32, nv=16) -> Mesh:
    c = np.asarray(c, float)
    prof = []
    for j in range(nv + 1):
        ph = math.pi * j / nv
        prof.append((-math.cos(ph), math.sin(ph)))
    m = revolve([(t, r) for t, r in prof], (0, 0, 0), (0, 0, 1), nu)
    P = m.verts() * np.array([rx, ry, rz]) + c
    out = Mesh()
    out.add_verts(P)
    out.F = m.F
    return out


def dome(c, normal, r, h, nseg=24, nrings=4) -> Mesh:
    """Domed rivet head: spherical cap of base radius r and height h on a base disc, base centre c, axis normal."""
    R = (r * r + h * h) / (2 * h)
    prof = [(0.0, r)]
    for j in range(1, nrings + 1):
        z = h * j / nrings
        rr = math.sqrt(max(R * R - (R - h + z) ** 2, 0.0))
        prof.append((z, rr if j < nrings else 0.0))
    return revolve([(0.0, 0.0)] + prof, c, normal, nseg)


def sweep_profile(path, section2d, ups=None, closed_path=False) -> Mesh:
    """Sweep a closed 2D section (local (s, t): s along the path normal 'side', t along 'up') along a 3D polyline."""
    path = np.asarray(path, float)
    n = len(path)
    rings = []
    for i in range(n):
        tng = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
        tng /= np.linalg.norm(tng)
        up = np.array([0, 0, 1.0]) if ups is None else np.asarray(ups[i], float)
        side = np.cross(tng, up)
        side /= np.linalg.norm(side)
        up2 = np.cross(side, tng)
        S = np.asarray(section2d, float)
        rings.append(path[i] + np.outer(S[:, 0], side) + np.outer(S[:, 1], up2))
    return loft(rings, closed_loop=closed_path)


def tube(p0, p1, r_in, r_out, nseg=32) -> Mesh:
    """Closed annular tube (ring) between p0 and p1."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    u, v, w = _frame(p1 - p0)
    th = np.linspace(0, 2 * math.pi, nseg, endpoint=False)
    D = np.outer(np.cos(th), u) + np.outer(np.sin(th), v)
    m = Mesh()
    a_o = m.add_verts(p0 + r_out * D)
    b_o = m.add_verts(p1 + r_out * D)
    a_i = m.add_verts(p0 + r_in * D)
    b_i = m.add_verts(p1 + r_in * D)
    for k in range(nseg):
        k2 = (k + 1) % nseg
        m.face((a_o[k], a_o[k2], b_o[k2], b_o[k]))
        m.face((b_i[k], b_i[k2], a_i[k2], a_i[k]))
        m.face((a_i[k], a_i[k2], a_o[k2], a_o[k]))
        m.face((b_o[k], b_o[k2], b_i[k2], b_i[k]))
    return m


def capsule(p0, p1, r, nseg=24, nend=6) -> Mesh:
    """Cylinder with hemispherical ends between the centres p0 and p1."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    prof = []
    for j in range(nend + 1):
        a = math.pi / 2 * j / nend
        prof.append((r - r * math.cos(a) - r, r * math.sin(a)))
    prof = [(t, rr) for t, rr in prof]
    prof2 = [(L + r * math.sin(math.pi / 2 * j / nend), r * math.cos(math.pi / 2 * j / nend)) for j in range(nend + 1)]
    pr = [(-r, 0.0)] + [(t, rr) for t, rr in prof[1:]] + prof2[:-1] + [(L + r, 0.0)]
    return revolve(pr, p0, p1 - p0, nseg)
