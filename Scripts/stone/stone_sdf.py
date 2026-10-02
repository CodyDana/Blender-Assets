"""SDF rock chain for Blender 5.2 (STONE_BUILDING_STUDY.md 4.9.2, 4.17 `stone_sdf.py`): geometry-node volume grids
built from Python, plus the numpy mesh helpers every rock stage uses. bpy + numpy.

The node chain (Mesh to SDF Grid -> SDF Offset / Boolean -> Grid to Mesh at threshold 0) follows the probes in
WorkFiles/studies/stone/c_probes/ and the first rock that used it (Scripts/vegetation/rock_sdf.py, the pines chat's,
read but not edited; the generic parts are lifted here so the stone library does not depend on another chat's file).

    g = SDFGraph(voxel=0.005, band=12)
    hull = g.intersect([g.mesh(V1, F1), g.mesh(V2, F2)])
    rock = g.opening(hull, 0.15)
    rock = g.difference(rock, [g.mesh(Vc, Fc) for Vc, Fc in batches])
    V, F, info = g.to_mesh(rock)          # threshold 0 (study P15), keeps the largest shell

SDF Offset: a positive Distance grows the solid (probe). Opening = offset(-r) then (+r): rounds convex arrises to r.
Closing = (+r) then (-r): fillets concave joins. Band width must cover the largest offset: band >= r/voxel + 3.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np

import bpy
import bmesh
from mathutils import Vector, geometry


# ----------------------------------------------------------------------------------------------- small maths
def unit(v):
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def rotz(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]], float)


def jitter(n, deg, rng):
    """Tilt a unit normal by up to ``deg`` degrees in a random direction."""
    n = unit(n)
    t = unit(np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]))
    b = np.cross(n, t)
    phi = rng.uniform(0, 2 * math.pi)
    th = math.radians(rng.uniform(0, deg))
    return unit(n * math.cos(th) + (t * math.cos(phi) + b * math.sin(phi)) * math.sin(th))


def smoothstep(x, e0, e1):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF) * 2.0 - 1.0


def vnoise3(P, seed=0):
    """Value noise in [-1, 1] on a unit lattice, smooth (trilinear with smoothstep weights). P: (n, 3)."""
    P = np.asarray(P, float)
    i = np.floor(P).astype(np.int64)
    f = P - i
    w = f * f * (3 - 2 * f)
    out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
                wx = w[:, 0] if dx else 1 - w[:, 0]
                wy = w[:, 1] if dy else 1 - w[:, 1]
                wz = w[:, 2] if dz else 1 - w[:, 2]
                out += h * wx * wy * wz
    return out


def fbm(P, octaves: Sequence[Tuple[float, float]], seed=0):
    """Sum of value-noise octaves: [(amplitude, frequency per metre), ...]."""
    P = np.asarray(P, float)
    out = np.zeros(len(P))
    for k, (a, fr) in enumerate(octaves):
        out += a * vnoise3(P * fr + 17.31 * k, seed + 101 * k)
    return out


def ridged(P, freq, seed=0):
    """Ridged noise in [0, 1] (1 on the ridge lines): crack-like and vein-like patterns."""
    return 1.0 - np.abs(vnoise3(np.asarray(P, float) * freq, seed))


# ----------------------------------------------------------------------------------------------- convex solids
def polytope_vertices(planes):
    """planes: [(n, d)] with n.p <= d inside. Vertices of the convex polytope."""
    pl = [Vector((float(n[0]), float(n[1]), float(n[2]), -float(d))) for n, d in planes]
    verts, _ = geometry.points_in_planes(pl)
    return np.array([v[:] for v in verts], float)


def hull_mesh(P):
    """Closed triangulated convex hull -> (V, F)."""
    bm = bmesh.new()
    for p in np.unique(np.round(np.asarray(P, float), 6), axis=0):
        bm.verts.new(tuple(map(float, p)))
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    for g in res.get("geom_interior", []) + res.get("geom_unused", []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid:
            bm.verts.remove(g)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts])
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V, F


def plane_sdf(P, planes):
    """Approximate signed distance to a convex polytope (max of the plane distances; exact inside)."""
    n = np.array([p[0] for p in planes])
    d = np.array([p[1] for p in planes])
    return (np.asarray(P, float) @ n.T - d).max(1)


def prism_mesh(poly2d, axes, lo, hi):
    """A polygon (k, 2) in the plane of ``axes`` (two of 0, 1, 2) extruded from ``lo`` to ``hi`` along the third
    axis -> closed triangulated (V, F). Concave polygons are fine (bmesh polyfill caps)."""
    a0, a1 = axes
    a2 = 3 - a0 - a1
    poly = np.asarray(poly2d, float)
    # drop consecutive duplicates, force counter-clockwise
    keep = np.ones(len(poly), bool)
    keep[1:] = np.linalg.norm(np.diff(poly, axis=0), axis=1) > 1e-6
    poly = poly[keep]
    area = 0.5 * float(np.dot(poly[:, 0], np.roll(poly[:, 1], -1)) - np.dot(poly[:, 1], np.roll(poly[:, 0], -1)))
    if area < 0:
        poly = poly[::-1]
    bm = bmesh.new()
    rings = []
    for z in (lo, hi):
        ring = []
        for x, y in poly:
            p = [0.0, 0.0, 0.0]
            p[a0], p[a1], p[a2] = float(x), float(y), float(z)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts])
    F = np.array([[v.index for v in f.verts] for f in bm.faces], dtype=np.int64)
    bm.free()
    return V, F


def merge_meshes(parts):
    Vs, Fs, off = [], [], 0
    for V, F in parts:
        Vs.append(V)
        Fs.append(F + off)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def batch_disjoint(parts, pad=0.002):
    """Group closed convex solids into batches whose members do not touch (AABB test), so each batch can be one mesh
    object for Mesh to SDF Grid (overlapping closed shells in one mesh break the inside test)."""
    boxes = [(V.min(0) - pad, V.max(0) + pad) for V, _ in parts]
    batches: List[List[int]] = []
    for i, (lo, hi) in enumerate(boxes):
        placed = False
        for b in batches:
            if all(np.any(hi < boxes[j][0]) or np.any(boxes[j][1] < lo) for j in b):
                b.append(i)
                placed = True
                break
        if not placed:
            batches.append([i])
    return [merge_meshes([parts[i] for i in b]) for b in batches]


# ----------------------------------------------------------------------------------------------- the GN graph
class SDFGraph:
    """Build a geometry-node SDF graph from Python. Every method returns an output socket (a grid)."""

    def __init__(self, voxel: float, band: int = 10, name: str = "__ST_SDF"):
        self.voxel = float(voxel)
        self.band = int(band)
        self.coll = bpy.data.collections.new(name + "_src")
        bpy.context.scene.collection.children.link(self.coll)
        self.ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
        self.ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        self.N, self.L = self.ng.nodes, self.ng.links
        self.out = self.N.new("NodeGroupOutput")
        self.objs = []
        self.n_ops = 0

    def mesh(self, V, F, name="__src"):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(map(int, f)) for f in F])
        me.update()
        ob = bpy.data.objects.new(name, me)
        self.coll.objects.link(ob)
        self.objs.append(ob)
        oi = self.N.new("GeometryNodeObjectInfo")
        oi.transform_space = "ORIGINAL"
        oi.inputs["Object"].default_value = ob
        m = self.N.new("GeometryNodeMeshToSDFGrid")
        m.inputs["Voxel Size"].default_value = self.voxel
        m.inputs["Band Width"].default_value = self.band
        self.L.new(oi.outputs["Geometry"], m.inputs["Mesh"])
        return m.outputs[0]

    def offset(self, g, d):
        n = self.N.new("GeometryNodeSDFGridOffset")
        n.inputs["Distance"].default_value = float(d)
        self.L.new(g, n.inputs["Grid"])
        self.n_ops += 1
        return n.outputs[0]

    def _bool(self, op, a, bs):
        n = self.N.new("GeometryNodeSDFGridBoolean")
        n.operation = op
        # probe (5.2): UNION / INTERSECT expose only the multi-input (identifier "Grid 2"); DIFFERENCE subtracts
        # every "Grid 2" link from "Grid 1"
        if op == "DIFFERENCE":
            self.L.new(a, n.inputs[0])
        else:
            self.L.new(a, n.inputs[1])
        for b in bs:
            self.L.new(b, n.inputs[1])
        self.n_ops += 1
        return n.outputs[0]

    def union(self, gs):
        gs = list(gs)
        return gs[0] if len(gs) == 1 else self._bool("UNION", gs[0], gs[1:])

    def intersect(self, gs):
        gs = list(gs)
        return gs[0] if len(gs) == 1 else self._bool("INTERSECT", gs[0], gs[1:])

    def difference(self, a, bs):
        bs = list(bs)
        return a if not bs else self._bool("DIFFERENCE", a, bs)

    def opening(self, g, r):
        return g if r <= 0 else self.offset(self.offset(g, -r), r)

    def closing(self, g, r):
        return g if r <= 0 else self.offset(self.offset(g, r), -r)

    def to_mesh(self, g, keep_largest=True):
        t0 = time.time()
        gm = self.N.new("GeometryNodeGridToMesh")
        gm.inputs["Threshold"].default_value = 0.0          # study P15: the node default 0.1 is a density default
        gm.inputs["Adaptivity"].default_value = 0.0
        self.L.new(g, gm.inputs["Grid"])
        self.L.new(gm.outputs[0], self.out.inputs[0])
        host_me = bpy.data.meshes.new("__sdf_host")
        host = bpy.data.objects.new("__sdf_host", host_me)
        self.coll.objects.link(host)
        md = host.modifiers.new("sdf", "NODES")
        md.node_group = self.ng
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        ev = host.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        n = len(me.vertices)
        V = np.empty(n * 3)
        me.vertices.foreach_get("co", V)
        V = V.reshape(-1, 3)
        # polygons -> triangles (Grid to Mesh gives quads)
        loop_tot = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get("loop_total", loop_tot)
        lv = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", lv)
        bpy.data.meshes.remove(me)
        if np.all(loop_tot == 4):
            Q = lv.reshape(-1, 4)
            F = np.vstack([Q[:, [0, 1, 2]], Q[:, [0, 2, 3]]])
        else:
            F = []
            st = 0
            for t in loop_tot:
                poly = lv[st:st + t]
                for k in range(1, t - 1):
                    F.append((poly[0], poly[k], poly[k + 1]))
                st += t
            F = np.array(F, np.int64)
        info = {"voxel": self.voxel, "band": self.band, "ops": self.n_ops, "sources": len(self.objs),
                "tris_raw": int(len(F)), "eval_s": round(time.time() - t0, 2)}
        if keep_largest and len(F):
            V, F, nshell = largest_component(V, F)
            info["shells_dropped"] = nshell - 1
        info["tris"] = int(len(F))
        self.cleanup(host)
        return V, F, info

    def cleanup(self, host=None):
        for ob in self.objs + ([host] if host is not None else []):
            d = ob.data
            bpy.data.objects.remove(ob)
            if d is not None and d.users == 0:
                bpy.data.meshes.remove(d)
        self.objs = []
        if self.coll.name in bpy.data.collections:
            bpy.data.collections.remove(self.coll)
        if self.ng.name in bpy.data.node_groups:
            bpy.data.node_groups.remove(self.ng)


def largest_component(V, F):
    """Keep the largest connected shell (internal void shells from block unions are separate components)."""
    n = len(V)
    parent = np.arange(n)

    def find_all(p):
        while True:
            q = p[p]
            if np.array_equal(q, p):
                return p
            p = q
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]]])
    # iterative label propagation (min label over edges) until stable
    lab = np.arange(n)
    for _ in range(4000):
        a = np.minimum(lab[E[:, 0]], lab[E[:, 1]])
        new = lab.copy()
        np.minimum.at(new, E[:, 0], a)
        np.minimum.at(new, E[:, 1], a)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    ids, cnt = np.unique(lab, return_counts=True)
    big = ids[np.argmax(cnt)]
    keepv = lab == big
    remap = -np.ones(n, np.int64)
    remap[keepv] = np.arange(int(keepv.sum()))
    keepf = keepv[F[:, 0]]
    return V[keepv], remap[F[keepf]], len(ids)


# ----------------------------------------------------------------------------------------------- mesh analysis
def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def face_normals_areas(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    a = 0.5 * np.linalg.norm(fn, axis=1)
    return fn / np.maximum(2 * a[:, None], 1e-12), a


def edges_of(F):
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E.sort(1)
    return np.unique(E, axis=0)


def smooth_field(x, E, n_iter=2):
    x = np.asarray(x, float).copy()
    deg = np.bincount(E.ravel(), minlength=len(x)).astype(float)
    dd = np.maximum(deg, 1)
    for _ in range(n_iter):
        acc = np.zeros_like(x)
        np.add.at(acc, E[:, 0], x[E[:, 1]])
        np.add.at(acc, E[:, 1], x[E[:, 0]])
        x = 0.5 * x + 0.5 * acc / (dd[:, None] if x.ndim > 1 else dd)
    return x


def mean_curvature(V, F, E=None, N=None, n_smooth=3):
    """Signed mean curvature (1/m) by the umbrella operator: + convex (arris), - concave (cleft)."""
    if E is None:
        E = edges_of(F)
    if N is None:
        N = vertex_normals(V, F)
    deg = np.bincount(E.ravel(), minlength=len(V)).astype(float)
    acc = np.zeros_like(V)
    np.add.at(acc, E[:, 0], V[E[:, 1]])
    np.add.at(acc, E[:, 1], V[E[:, 0]])
    lap = acc / np.maximum(deg, 1)[:, None] - V
    el = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    e2 = np.zeros(len(V))
    np.add.at(e2, E[:, 0], el ** 2)
    np.add.at(e2, E[:, 1], el ** 2)
    e2 = e2 / np.maximum(deg, 1)
    H = -2.0 * (lap * N).sum(1) / np.maximum(e2, 1e-12)
    return smooth_field(H, E, n_smooth)


def point_segment_dist(P, A, B):
    AB = B - A
    t = np.clip(((P - A) @ AB) / max(float(AB @ AB), 1e-12), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1), t


def bvh_of(V, F):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons([tuple(map(float, v)) for v in V], [tuple(map(int, f)) for f in F])


def kd_nearest(src, dst):
    """Index of the nearest ``src`` point for every ``dst`` point (mathutils KDTree)."""
    from mathutils.kdtree import KDTree
    kd = KDTree(len(src))
    for i, p in enumerate(src):
        kd.insert(Vector(p), i)
    kd.balance()
    out = np.empty(len(dst), np.int64)
    dist = np.empty(len(dst))
    for j, p in enumerate(dst):
        _, i, d = kd.find(p)
        out[j] = i
        dist[j] = d
    return out, dist
