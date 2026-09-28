"""Geometry helpers that need Blender (BVH, meshes) for the Snow Flower heels builder. Local frame, millimetres."""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import hb_common as C


class Surf:
    """A triangle/quad surface with a BVH: nearest, all ray hits, normals."""

    def __init__(self, verts: np.ndarray, faces: Sequence[Sequence[int]]):
        self.v = np.asarray(verts, dtype=float)
        self.f = [list(map(int, f)) for f in faces]
        self.tree = BVHTree.FromPolygons([tuple(p) for p in self.v], self.f, all_triangles=False)

    def nearest(self, pts: np.ndarray):
        out = np.empty_like(np.asarray(pts, dtype=float))
        nrm = np.empty_like(out)
        for i, p in enumerate(pts):
            loc, n, _idx, _d = self.tree.find_nearest(Vector(p))
            out[i] = loc
            nrm[i] = n
        return out, nrm

    def hits(self, o, d, max_hits=8, maxdist=5000.0):
        o = Vector(o)
        d = Vector(d).normalized()
        res = []
        travelled = 0.0
        for _ in range(max_hits):
            loc, n, idx, dist = self.tree.ray_cast(o, d, maxdist - travelled)
            if loc is None:
                break
            res.append((np.array(loc), np.array(n), idx, travelled + dist))
            o = loc + d * 0.01
            travelled += dist + 0.01
        return res


def grid_sampler(z):
    """Trilinear sampler of the cached last SDF (float) at local mm points."""
    lo = z["lo"].astype(float)
    f = z["f_last"].astype(np.float32)
    shp = np.array(f.shape)

    def sample(p):
        q = np.asarray(p, dtype=float) - lo
        i0 = np.clip(np.floor(q).astype(int), 0, shp - 2)
        t = np.clip(q - i0, 0, 1)
        acc = 0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = (t[..., 0] if dx else 1 - t[..., 0]) * (t[..., 1] if dy else 1 - t[..., 1]) * \
                        (t[..., 2] if dz else 1 - t[..., 2])
                    acc = acc + w * f[i0[..., 0] + dx, i0[..., 1] + dy, i0[..., 2] + dz]
        return acc
    return sample


def zins_sampler(z):
    U, V = z["U"].astype(float), z["V"].astype(float)
    Z = z["zins"].astype(float)

    def sample(u, v):
        u = np.asarray(u, dtype=float)
        v = np.asarray(v, dtype=float)
        qi = np.clip(u - U[0], 0, len(U) - 1.001)
        qj = np.clip(v - V[0], 0, len(V) - 1.001)
        i0 = np.floor(qi).astype(int)
        j0 = np.floor(qj).astype(int)
        ti, tj = qi - i0, qj - j0
        return (Z[i0, j0] * (1 - ti) * (1 - tj) + Z[i0 + 1, j0] * ti * (1 - tj) + Z[i0, j0 + 1] * (1 - ti) * tj
                + Z[i0 + 1, j0 + 1] * ti * tj)
    return sample


def new_object(name: str, verts, faces, collection=None, smooth=True, uv=None, matrix=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], [tuple(map(int, f)) for f in faces])
    if uv is not None:
        layer = me.uv_layers.new(name="UVMap")
        loops = np.array([li for p in me.polygons for li in p.loop_indices])
        vidx = np.array([me.loops[li].vertex_index for li in loops])
        uvs = np.asarray(uv, dtype=float)
        if uvs.shape[0] == len(verts):
            data = uvs[vidx]
        else:
            data = uvs
        layer.data.foreach_set("uv", data.astype(np.float32).ravel())
    me.update()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if matrix is not None:
        ob.matrix_world = matrix
    return ob


def mesh_arrays(ob, world=False):
    me = ob.data
    v = np.array([tuple(x.co) for x in me.vertices])
    if world:
        m = np.array(ob.matrix_world)
        v = v @ m[:3, :3].T + m[:3, 3]
    f = [list(p.vertices) for p in me.polygons]
    return v, f


def grid_faces(nr: int, nc: int, closed_c=False):
    faces = []
    cc = nc if closed_c else nc - 1
    for i in range(nr - 1):
        for j in range(cc):
            j1 = (j + 1) % nc
            faces.append([i * nc + j, i * nc + j1, (i + 1) * nc + j1, (i + 1) * nc + j])
    return faces


def loft(sections: List[np.ndarray], cap_start=False, cap_end=False):
    """Closed-loop sections (each (n,3), same n) -> verts, quad faces (+ fan caps as n-gon-free triangles)."""
    n = len(sections[0])
    verts = np.vstack(sections)
    faces = grid_faces(len(sections), n, closed_c=True)
    if cap_start:
        c = len(verts)
        verts = np.vstack([verts, sections[0].mean(0)[None]])
        faces += [[c, (j + 1) % n, j] for j in range(n)]
    if cap_end:
        c = len(verts)
        base = (len(sections) - 1) * n
        verts = np.vstack([verts, sections[-1].mean(0)[None]])
        faces += [[c, base + j, base + (j + 1) % n] for j in range(n)]
    return verts, faces


def weld(verts, faces, dist=1e-4):
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(p)) for p in verts]
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    bm.verts.ensure_lookup_table()
    v = np.array([tuple(x.co) for x in bm.verts])
    for i, x in enumerate(bm.verts):
        x.index = i
    f = [[x.index for x in fc.verts] for fc in bm.faces]
    bm.free()
    return v, f


def vertex_normals(verts, faces):
    v = np.asarray(verts, dtype=float)
    n = np.zeros_like(v)
    for f in faces:
        p = v[f]
        fn = np.zeros(3)
        for k in range(len(f)):
            fn += np.cross(p[k], p[(k + 1) % len(f)])
        for i in f:
            n[i] += fn
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(ln, 1e-12)


def recalc_faces(verts, faces):
    """Consistent outward winding (bmesh recalc) for closed-ish meshes; returns the new face list."""
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, p))) for p in verts]
    made = []
    for f in faces:
        try:
            made.append(bm.faces.new([vs[i] for i in f]))
        except ValueError:
            made.append(None)
    bm.verts.index_update()
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in made if f is not None])
    out = []
    for f, orig in zip(made, faces):
        out.append([v.index for v in f.verts] if f is not None else list(orig))
    bm.free()
    return out


def orient_by_sdf(verts, faces, sdf, step=0.8):
    """Flip all faces if the majority of face normals point into decreasing SDF (inward)."""
    v = np.asarray(verts, float)
    score = 0
    for f in faces[:: max(1, len(faces) // 400)]:
        p = v[f]
        c = p.mean(0)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        n /= ln
        score += np.sign(sdf(c[None] + n[None] * step)[0] - sdf(c[None] - n[None] * step)[0])
    return faces if score >= 0 else [list(f)[::-1] for f in faces]
