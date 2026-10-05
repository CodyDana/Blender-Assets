"""Blender side of the gun UV stage (import inside Blender): mesh <-> uvchart.PartMesh, per-face openness (which faces
can ever be seen: GUN_BUILDING_STUDY 5.8 class E), island packing with Blender's own packer, LOD face -> LOD0 island
assignment, and UV layer writes.

Packing: every set (texture atlas) is packed once with bpy.ops.uv.pack_islands (exact concave shapes, 90-degree
rotations, one uniform scale): each island goes in at (its UVs in mm) x (its texel class factor), so the classes keep
their density ratios and the packer fills the atlas. An island's LOD1-3 faces ride in the same pack (merge_overlap:
they overlap the island's LOD0 faces), so the packed footprint covers every LOD's projection and no LOD face can land
in a neighbour island. Each island's transform (2x3 affine: scale, quarter turn, offset) is fitted from its LOD0 loops.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from . import uvchart as UC


def part_mesh(ob, name=None) -> UC.PartMesh:
    """Object mesh (frame B, metres; object transform applied) -> PartMesh in mm, with Blender's polygon normals."""
    me = ob.data
    nv = len(me.vertices)
    V = np.empty(nv * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    V = (np.c_[V, np.ones(nv)] @ M.T)[:, :3] * 1000.0
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    ps = np.empty(len(me.polygons), np.int64)
    pt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ps)
    me.polygons.foreach_get("loop_total", pt)
    return UC.PartMesh(name or ob.name, V, lv, ps, pt)


def write_uv(ob, layer, uv, first=False):
    me = ob.data
    lay = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    lay.data.foreach_set("uv", np.asarray(uv, np.float32).ravel())
    if first and me.uv_layers[0].name != layer:
        # Blender cannot reorder layers: rebuild them with `layer` first
        keep = [(l.name, np.array([d.uv[:] for d in l.data], np.float32)) for l in me.uv_layers]
        for l in list(me.uv_layers):
            me.uv_layers.remove(l)
        for nm, data in sorted(keep, key=lambda t: t[0] != layer):
            l2 = me.uv_layers.new(name=nm)
            l2.data.foreach_set("uv", data.ravel())
    me.uv_layers.active = me.uv_layers[layer]
    return lay


# ====================================================================== openness
def _fib_dirs(n):
    """Cosine-weighted hemisphere directions about +Z (Fibonacci spiral)."""
    i = np.arange(n) + 0.5
    r = np.sqrt(i / n)
    phi = i * math.pi * (3.0 - math.sqrt(5.0))
    return np.c_[r * np.cos(phi), r * np.sin(phi), np.sqrt(np.maximum(1 - r * r, 0.0))]


def _frame_from(n):
    t = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(n, t)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u), n


def openness(faces_c_mm, faces_n, tree: BVHTree, n_dirs=64, quick=8, dist_m=3.0, lift_mm=0.02):
    """Fraction of hemisphere rays that escape (no hit within dist) per face; early exit at the first escape when
    only visibility matters (returns 1/n_dirs for 'some ray escapes'). Rays start lift_mm above the face (inside a
    butt joint's 0.01-0.05 mm gap, so a contact face is hidden)."""
    D = _fib_dirs(n_dirs)
    order = np.r_[np.argsort(-D[:, 2])[:quick:max(1, quick // quick)], np.arange(n_dirs)]
    seen = []
    for k in order:
        if k not in seen:
            seen.append(int(k))
    out = np.zeros(len(faces_c_mm))
    for i, (c, n) in enumerate(zip(faces_c_mm, faces_n)):
        nn = np.linalg.norm(n)
        if nn < 1e-9:
            continue
        n = n / nn
        u, v, w = _frame_from(n)
        o = Vector(((c + n * lift_mm) * 0.001).tolist())
        for k in seen:
            d = D[k]
            dv = Vector((u * d[0] + v * d[1] + w * d[2]).tolist())
            hit = tree.ray_cast(o, dv, dist_m)
            if hit[0] is None:
                out[i] = 1.0
                break
    return out


def bvh_of_meshes(pms: Sequence[UC.PartMesh], mats=None) -> BVHTree:
    """One BVH (metres) over several PartMeshes; mats: optional 4x4 per mesh (mm space) for moved configurations."""
    Vs, Ps, off = [], [], 0
    for k, pm in enumerate(pms):
        V = pm.V
        if mats is not None and mats[k] is not None:
            M = np.asarray(mats[k], float)
            V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
        Vs.append(V * 0.001)
        for f in range(pm.nf):
            s, t = pm.ps[f], pm.pt[f]
            Ps.append(tuple(int(x) + off for x in pm.loop_v[s:s + t]))
        off += len(V)
    V = np.vstack(Vs)
    return BVHTree.FromPolygons([tuple(v) for v in V], Ps, epsilon=0.0)


# ====================================================================== LOD assignment
class FaceIndex:
    """Nearest LOD0 face lookup over one or more LOD0 PartMeshes (BVH on polygons + KD on face centres)."""

    def __init__(self, pms: Sequence[UC.PartMesh]):
        self.pms = list(pms)
        Vs, Ps, own, off = [], [], [], 0
        for k, pm in enumerate(self.pms):
            Vs.append(pm.V * 0.001)
            for f in range(pm.nf):
                s, t = pm.ps[f], pm.pt[f]
                Ps.append(tuple(int(x) + off for x in pm.loop_v[s:s + t]))
                own.append((k, f))
            off += len(pm.V)
        self.own = np.array(own, np.int64)
        V = np.vstack(Vs)
        self.tree = BVHTree.FromPolygons([tuple(v) for v in V], Ps, epsilon=0.0)
        C = np.vstack([pm.fc for pm in self.pms]) * 0.001
        self.N = np.vstack([pm.fn for pm in self.pms])
        self.kd = KDTree(len(C))
        for i, c in enumerate(C):
            self.kd.insert(Vector(c.tolist()), i)
        self.kd.balance()

    def best(self, c_mm, n, k=24, min_dot=0.35):
        """(mesh index, face index, distance mm) of the LOD0 face that best matches a LOD face (centre, normal): the
        nearest surface face if its normal agrees, else the nearest of the k nearest centres with normal . n >=
        min_dot (falling back to the best-aligned one)."""
        p = Vector((np.asarray(c_mm) * 0.001).tolist())
        loc, nrm, idx, d = self.tree.find_nearest(p)
        if idx is not None and float(self.N[idx] @ n) >= min_dot:
            mk, f = self.own[idx]
            return int(mk), int(f), d * 1000.0
        best, score = None, -1e9
        for co, i, dd in self.kd.find_n(p, k):
            s = float(self.N[i] @ n) - dd * 1000.0 * 0.05
            if s > score:
                best, score = (i, dd), s
        i, dd = best
        mk, f = self.own[i]
        return int(mk), int(f), dd * 1000.0


# ====================================================================== packing
def pack_islands(groups: List[dict], size: int, gap_px: float, name="_UVPACK"):
    """groups: [{'id', 'polys': [(uv (k,2) scaled), ...] for LOD0 faces sharing vertices by 'verts' keys,
    'lod_polys': [uv (k,2), ...]}]. Each group's LOD0 polygons are given as one connected patch: 'loop_keys' (vertex
    key per loop, equal keys = shared vertex) + 'loop_uv' + 'poly_sizes'; LOD faces are separate polygons.
    Returns {id: 2x3 affine from the scaled-mm input to the packed 0..1 UVs}, the packed UV arrays and a report."""
    verts, faces, uvs, owner, is_lod = [], [], [], [], []
    # pre-layout: groups on rows, scaled into 0..1 so the packer's "closest UDIM" is tile 0
    boxes = []
    for g in groups:
        allp = np.vstack([g["loop_uv"]] + [p for p in g["lod_polys"]]) if g["lod_polys"] else g["loop_uv"]
        lo, hi = allp.min(0), allp.max(0)
        boxes.append((lo, hi))
    widths = np.array([b[1][0] - b[0][0] for b in boxes])
    heights = np.array([b[1][1] - b[0][1] for b in boxes])
    row_w = max(float(np.sqrt((widths + 2) @ (heights + 2))) * 1.2, float(widths.max()) + 2)
    x = y = rowh = 0.0
    offs = []
    for w, h in zip(widths, heights):
        if x + w > row_w:
            x, y, rowh = 0.0, y + rowh + 2.0, 0.0
        offs.append((x, y))
        x += w + 2.0
        rowh = max(rowh, h)
    total = max(row_w, y + rowh) + 2.0
    for gi, (g, (lo, hi), o) in enumerate(zip(groups, boxes, offs)):
        sh = np.array(o) - lo
        keymap = {}
        k0 = 0
        for sz in g["poly_sizes"]:
            idx = []
            for j in range(k0, k0 + sz):
                key = g["loop_keys"][j]
                if key not in keymap:
                    keymap[key] = len(verts)
                    verts.append((0.0, 0.0, 0.0))
                idx.append(keymap[key])
            faces.append(idx)
            uvs.append((g["loop_uv"][k0:k0 + sz] + sh) / total)
            owner.append(gi)
            is_lod.append(False)
            k0 += sz
        for p in g["lod_polys"]:
            idx = list(range(len(verts), len(verts) + len(p)))
            verts += [(0.0, 0.0, 0.0)] * len(p)
            faces.append(idx)
            uvs.append((p + sh) / total)
            owner.append(gi)
            is_lod.append(True)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    lay = me.uv_layers.new(name="UV0")
    U = np.vstack(uvs)
    lay.data.foreach_set("uv", U.astype(np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    res = bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="CARDINAL", scale=True,
                                  merge_overlap=True, margin_method="FRACTION", margin=gap_px / size,
                                  shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    P = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UV0"].data.foreach_get("uv", P)
    P = P.reshape(-1, 2).astype(float)
    starts = np.cumsum([0] + [len(f) for f in faces])
    aff = {}
    rep = {"result": list(res), "lod_faces_off_affine": 0, "max_lod_dev_px": 0.0}
    for gi, g in enumerate(groups):
        sel = [k for k in range(len(faces)) if owner[k] == gi]
        src = np.vstack([uvs[k] for k in sel if not is_lod[k]]) * total - (np.array(offs[gi]) - boxes[gi][0])
        dst = np.vstack([P[starts[k]:starts[k + 1]] for k in sel if not is_lod[k]])
        A = UC.fit_affine(src, dst)
        aff[g["id"]] = A
        for k in sel:
            if is_lod[k]:
                s2 = uvs[k] * total - (np.array(offs[gi]) - boxes[gi][0])
                dev = float(np.abs(UC.apply_affine(A, s2) - P[starts[k]:starts[k + 1]]).max()) * size
                rep["max_lod_dev_px"] = max(rep["max_lod_dev_px"], dev)
                if dev > 0.5:
                    rep["lod_faces_off_affine"] += 1
    rep["uv_min"] = P.min(0).tolist()
    rep["uv_max"] = P.max(0).tolist()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return aff, rep


def triangulate_keep_normals(ob):
    """Triangulate quads (and any n-gon) in place, manifold-safe, keeping the corner custom normals: per quad Blender's
    own split (v0-v2: the loop triangles every earlier gate measured) unless that diagonal already exists as an edge
    or leaves a zero-area triangle (BEAUTY / the modifier's fixed splits put a duplicate edge on the AR-01 dust cover
    and the gas-tube cap: a 3-face edge and a 1e-13 m^2 sliver). The export is triangles anyway, so the UVs, the bake's tangent frame and Unreal's MikkTSpace see the same
    triangles."""
    me = ob.data
    if all(p.loop_total == 3 for p in me.polygons):
        return 0
    # custom normals are stored relative to each corner's own normal space, which a face split changes: keep the
    # actual corner normals per (original face, vertex) and set them again after the split
    keep = {}
    cn = me.corner_normals
    for p in me.polygons:
        for li in p.loop_indices:
            keep[(p.index, me.loops[li].vertex_index)] = tuple(cn[li].vector)
    bm = bmesh.new()
    bm.from_mesh(me)
    orig = bm.faces.layers.int.new("_orig_face")
    for f in bm.faces:
        f[orig] = f.index
    quads = [f for f in bm.faces if len(f.verts) == 4]
    pairs = []
    for f in quads:
        v = list(f.verts)
        best = None
        for a, b in ((0, 2), (1, 3)):
            dup = bm.edges.get((v[a], v[b])) is not None
            o1, o2 = [x for x in range(4) if x not in (a, b)]
            ar = []
            for o in (o1, o2):
                p0, p1, p2 = v[a].co, v[b].co, v[o].co
                ar.append(((p1 - p0).cross(p2 - p0)).length * 0.5)
            # keep Blender's own quad split (v0-v2, what every earlier gate measured through loop triangles) unless
            # it duplicates an edge or leaves a zero-area triangle
            score = (0 if dup else 1, 1 if min(ar) > 1e-12 else 0, 1 if a == 0 else 0, min(ar))
            if best is None or score > best[0]:
                best = (score, v[a], v[b], f)
        pairs.append(best)
    for score, va, vb, f in pairs:
        if f.is_valid:
            bmesh.ops.connect_verts(bm, verts=[va, vb], check_degenerate=False)
    ng = [f for f in bm.faces if len(f.verts) > 3]
    if ng:
        bmesh.ops.triangulate(bm, faces=ng, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.faces.ensure_lookup_table()
    per_loop = []
    for f in bm.faces:
        o = f[orig]
        for lp in f.loops:
            per_loop.append(keep.get((o, lp.vert.index)))
    bm.faces.layers.int.remove(orig)
    bm.to_mesh(me)
    bm.free()
    # loops come out face by face in bm.faces order, the same order to_mesh writes them
    if all(v is not None for v in per_loop) and len(per_loop) == len(me.loops):
        me.normals_split_custom_set(per_loop)
    me.update()
    a = me.attributes.get("_orig_face")
    if a is not None:
        me.attributes.remove(a)
    return len(me.polygons)


class IslandSnap:
    """Closest-point UV lookup restricted to one LOD0 island (its triangles in 3D, mm, with their packed UVs)."""

    def __init__(self, pm: UC.PartMesh, faces, uv01):
        self.pm = pm
        self.faces = np.asarray(faces)
        tri_l = np.array([np.arange(pm.ps[f], pm.ps[f] + 3) for f in self.faces])       # triangles only
        self.tri_l = tri_l
        P = pm.V[pm.loop_v[tri_l]]                                                        # (n, 3, 3)
        self.P = P
        self.UV = uv01[tri_l]
        verts = P.reshape(-1, 3) * 0.001
        polys = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tri_l))]
        self.tree = BVHTree.FromPolygons([tuple(v) for v in verts], polys, epsilon=0.0)

    def _bary_uv(self, idx, loc):
        a, b, c = self.P[idx]
        q = np.array(loc) * 1000.0
        v0, v1, v2 = b - a, c - a, q - a
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-18:
            w = np.array([1 / 3, 1 / 3, 1 / 3])
        else:
            wv = (d11 * d20 - d01 * d21) / den
            ww = (d00 * d21 - d01 * d20) / den
            w = np.array([1 - wv - ww, wv, ww])
        return w @ self.UV[idx]

    def uv_near(self, p_mm, uv_ref, tol_mm=0.6):
        """UV of the closest island point; among the island points within (closest + tol) the one whose UV is
        nearest uv_ref wins (an island that wraps a cylinder carries two UVs along its seam: the face's own side)."""
        p = Vector((np.asarray(p_mm) * 0.001).tolist())
        loc, nrm, idx, d = self.tree.find_nearest(p)
        best = self._bary_uv(idx, loc)
        if uv_ref is None:
            return best, d * 1000.0
        bd = float(np.abs(best - uv_ref).sum())
        for loc2, n2, i2, d2 in self.tree.find_nearest_range(p, d + tol_mm * 0.001):
            u2 = self._bary_uv(i2, loc2)
            dd = float(np.abs(u2 - uv_ref).sum())
            if dd < bd:
                best, bd = u2, dd
        return best, d * 1000.0

    def uv_at(self, p_mm):
        loc, nrm, idx, d = self.tree.find_nearest(Vector((np.asarray(p_mm) * 0.001).tolist()))
        a, b, c = self.P[idx]
        q = np.array(loc) * 1000.0
        v0, v1, v2 = b - a, c - a, q - a
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-18:
            w = np.array([1 / 3, 1 / 3, 1 / 3])
        else:
            wv = (d11 * d20 - d01 * d21) / den
            ww = (d00 * d21 - d01 * d20) / den
            w = np.array([1 - wv - ww, wv, ww])
        return w @ self.UV[idx], d * 1000.0


def footprint_tree(pm: UC.PartMesh, faces, luv):
    """2D BVH (z = 0) of an island's chart-space triangles (mm): a point is on the island when its distance is ~0."""
    faces = np.asarray(faces)
    tri_l = np.array([np.arange(pm.ps[f], pm.ps[f] + 3) for f in faces])
    U = luv[tri_l].reshape(-1, 2)
    verts = [(float(u), float(v), 0.0) for u, v in U]
    polys = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tri_l))]
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0)


def inside(tree, uv_mm, tol=1e-4):
    loc, nrm, idx, d = tree.find_nearest(Vector((float(uv_mm[0]), float(uv_mm[1]), 0.0)))
    return idx is not None and d <= tol
