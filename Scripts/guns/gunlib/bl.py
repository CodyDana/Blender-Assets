"""Blender-side helpers for gun parts (import only inside Blender).

boolean / bevel / weighted normals applied in place; n-gon triangulation; manifold report; evaluated triangles to
numpy (mm, frame M); BVH intersection and clearance queries used by the motion sweep (fit.py) and the gates.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from .mesh import Mesh


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def collection(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in par.children]:
        par.children.link(c)
    return c


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def as_object(m, name, coll, offset):
    if isinstance(m, Mesh):
        return m.to_object(name, coll, offset)
    return m


def boolean(ob, cutter, op="DIFFERENCE", solver="EXACT", offset=(0, 0, 0), keep_cutter=False):
    """Apply a boolean with a Mesh (frame M, mm) or an object as the cutter."""
    tmp = as_object(cutter, "_cut", bpy.context.scene.collection, offset)
    mod = ob.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.solver = solver
    mod.object = tmp
    apply_modifiers(ob)
    if not keep_cutter and tmp is not cutter:
        bpy.data.objects.remove(tmp, do_unlink=True)
    return ob


def boolean_many(ob, cutters: Sequence, op="DIFFERENCE", solver="EXACT", offset=(0, 0, 0)):
    """One boolean with a collection operand holding every cutter (EXACT handles overlapping cutters)."""
    if not cutters:
        return ob
    col = bpy.data.collections.new("_cutters")
    bpy.context.scene.collection.children.link(col)
    objs = [as_object(c, "_cut%d" % i, col, offset) for i, c in enumerate(cutters)]
    mod = ob.modifiers.new("boolc", "BOOLEAN")
    mod.operation = op
    mod.solver = solver
    mod.operand_type = "COLLECTION"
    mod.collection = col
    apply_modifiers(ob)
    for o in objs:
        if o.name.startswith("_cut"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
    return ob


def _bbox_m(me):
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    return V.min(0), V.max(0)


def bevel(ob, width_mm, segments=2, angle_deg=30.0, profile=0.5, harden=True, clamp=True, limit="ANGLE",
          miter="ARC"):
    """Bevel modifier, applied. Guard: Blender's bevel occasionally throws a vertex to ~1e32 at a degenerate corner
    (seen on the receiver once the build frame moved by 6 mm: the same geometry, other float coordinates; the arc
    outer miter with overlap clamping was the trigger). If any vertex lands outside the pre-bevel box grown by 2
    widths, the bevel is undone and retried: the angle limit 5 deg lower (form fix round 2 found the trigger: an angle
    limit sitting inside a cluster of near-equal dihedrals selects half of a corner's edges), then a sharp outer miter,
    the width x0.97, no clamping; every retry is printed. Edges within 1 deg of the limit are reported as a warning."""
    keep = ob.data.copy()
    lo, hi = _bbox_m(ob.data)
    tol = 2.0 * width_mm * 0.001 + 1e-5
    if limit == "ANGLE":
        near = _edges_near_angle(ob.data, angle_deg, 1.0)
        if near:
            print("[gunlib.bl] warning: %d edge(s) of %s within 1 deg of the %.1f deg bevel limit" % (near, ob.name, angle_deg))
    tries = [(1.0, miter, clamp, 0.0), (1.0, miter, clamp, -5.0), (1.0, "SHARP", clamp, 0.0), (0.97, "SHARP", clamp, 0.0),
             (1.0, miter, False, 0.0)]
    for k, (f, mt, cl, da) in enumerate(tries):
        if k:
            bad = ob.data
            ob.data = keep.copy()
            bpy.data.meshes.remove(bad)
            print("[gunlib.bl] bevel %.3f mm on %s threw vertices out; retry x%.2f miter %s clamp %s angle %.1f"
                  % (width_mm, ob.name, f, mt, cl, angle_deg + da))
        _bevel_once(ob, width_mm * f, segments, angle_deg + da, profile, harden, cl, limit, mt)
        a, b = _bbox_m(ob.data)
        if np.all(a >= lo - tol) and np.all(b <= hi + tol):
            break
    else:
        raise RuntimeError("bevel %.3f mm on %s keeps throwing vertices out" % (width_mm, ob.name))
    bpy.data.meshes.remove(keep)
    return ob


def _edges_near_angle(me, angle_deg, tol_deg) -> int:
    bm = bmesh.new()
    bm.from_mesh(me)
    n = 0
    for e in bm.edges:
        if len(e.link_faces) == 2 and abs(math.degrees(e.calc_face_angle()) - angle_deg) <= tol_deg:
            n += 1
    bm.free()
    return n


def _bevel_once(ob, width_mm, segments, angle_deg, profile, harden, clamp, limit, miter):
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width = width_mm * 0.001
    mod.segments = segments
    mod.limit_method = limit
    mod.angle_limit = math.radians(angle_deg)
    mod.profile = profile
    mod.use_clamp_overlap = clamp
    mod.harden_normals = harden
    try:
        mod.miter_outer = "MITER_ARC" if miter == "ARC" else "MITER_SHARP"
    except Exception:  # noqa: BLE001
        pass
    apply_modifiers(ob)
    return ob


def weighted_normals(ob, keep_sharp=True, sharp_deg=35.0):
    triangulate_ngons(ob)
    mark_sharp(ob, sharp_deg)
    mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    mod.keep_sharp = keep_sharp
    mod.mode = "FACE_AREA"
    try:
        mod.use_face_influence = True
    except Exception:  # noqa: BLE001
        pass
    apply_modifiers(ob)
    return ob


def triangulate_ngons(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    ng = [f for f in bm.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(bm, faces=ng, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return len(ng)


def clean(ob, dist_m=1e-7):
    """Merge exact duplicates left by booleans, dissolve degenerate faces, recalc normals."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist_m)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist_m)
    loose = [v for v in bm.verts if not v.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def manifold_report(ob) -> Dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.edges.ensure_lookup_table()
    multi = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    bound = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    wire = sum(1 for e in bm.edges if not e.link_faces)
    ngon = sum(1 for f in bm.faces if len(f.verts) > 4)
    zero_f = sum(1 for f in bm.faces if f.calc_area() <= 1e-12)
    zero_e = sum(1 for e in bm.edges if e.calc_length() <= 1e-6)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    shells = _shell_count(bm)
    bm.free()
    return {"multi_face_edges": multi, "boundary_edges": bound, "wire_edges": wire, "ngons": ngon,
            "zero_area_faces": zero_f, "zero_length_edges": zero_e, "triangles": tris, "shells": shells}


def _shell_count(bm) -> int:
    seen = set()
    n = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        n += 1
        stack = [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
    return n


def mark_sharp(ob, deg=35.0):
    ob.data.set_sharp_from_angle(angle=math.radians(deg))


def finish(ob, smooth_deg=35.0):
    """Final clean at qa_check's own tolerances (1 micron): merge near-coincident vertices left by bevel clamping
    and booleans, dissolve zero-area faces, then triangulate n-gons."""
    clean(ob, dist_m=2e-6)
    triangulate_ngons(ob)
    clean(ob, dist_m=2e-6)
    return ob


def tris_np(ob, offset_mm=(0, 0, 0)) -> Tuple[np.ndarray, np.ndarray]:
    """Evaluated triangles: vertices in mm (frame M = B + offset), triangle index array."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    V = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0 + np.asarray(offset_mm, float)
    T = np.zeros(len(me.loop_triangles) * 3, int)
    me.loop_triangles.foreach_get("vertices", T)
    ev.to_mesh_clear()
    return V, T.reshape(-1, 3)


def bvh_of(ob, matrix: Optional[Matrix] = None) -> BVHTree:
    V, T = tris_np(ob)
    V = V * 0.001
    if matrix is not None:
        M = np.array(matrix)
        V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)


def bvh_from_np(V_m, T) -> BVHTree:
    return BVHTree.FromPolygons([tuple(v) for v in V_m], [tuple(int(i) for i in t) for t in T], all_triangles=True,
                                epsilon=0.0)


def min_distance(V_query_m: np.ndarray, tree: BVHTree, cap_m=0.01) -> float:
    """Minimum distance (m) from query points to a BVH surface (points farther than cap are ignored)."""
    best = cap_m
    for p in V_query_m:
        hit = tree.find_nearest(Vector(p), best)
        if hit[0] is not None and hit[3] < best:
            best = hit[3]
    return best


def surface_samples(V, T, step_mm=0.5) -> np.ndarray:
    """Points on every triangle (vertices + edge midpoints + interior grid at ~step)."""
    out = [V]
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    L = np.maximum(np.linalg.norm(B - A, axis=1), np.maximum(np.linalg.norm(C - B, axis=1), np.linalg.norm(A - C, axis=1)))
    for k in np.unique(np.clip(np.ceil(L / step_mm), 1, 40).astype(int)):
        sel = np.ceil(L / step_mm).clip(1, 40).astype(int) == k
        if k <= 1:
            out.append((A[sel] + B[sel] + C[sel]) / 3)
            continue
        ij = [(i, j) for i in range(k + 1) for j in range(k + 1 - i)]
        for i, j in ij:
            u, v = i / k, j / k
            out.append(A[sel] + u * (B[sel] - A[sel]) + v * (C[sel] - A[sel]))
    return np.vstack(out)


def export_npz(objs, path, offset_mm=(0, 0, 0), labels=None):
    """Triangles of every object (mm, frame M) with a per-triangle part label -> .npz (V, T, lab, names)."""
    Vs, Ts, Ls, names = [], [], [], []
    n = 0
    for k, ob in enumerate(objs):
        V, T = tris_np(ob, offset_mm)
        Vs.append(V)
        Ts.append(T + n)
        Ls.append(np.full(len(T), k, np.int32))
        names.append(ob.name if labels is None else labels[k])
        n += len(V)
    np.savez_compressed(path, V=np.vstack(Vs), T=np.vstack(Ts), lab=np.concatenate(Ls), names=np.array(names))


def set_bevel_weights(ob, pred, offset_mm=(0, 0, 0)) -> int:
    """Edge bevel weights from a predicate pred(mid_mm, dir, n1, n2, dihedral_deg) -> weight (0 = no bevel), all in
    frame M. Returns the number of weighted edges."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lay = bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")
    off = np.asarray(offset_mm, float)
    n = 0
    for e in bm.edges:
        w = 0.0
        if len(e.link_faces) == 2:
            a, b = e.verts[0].co, e.verts[1].co
            mid = np.array((a + b) / 2) * 1000.0 + off
            d = np.array(b - a)
            ln = np.linalg.norm(d)
            if ln > 0:
                d = d / ln
                n1 = np.array(e.link_faces[0].normal)
                n2 = np.array(e.link_faces[1].normal)
                dih = float(np.degrees(np.arccos(np.clip(n1 @ n2, -1, 1))))
                w = float(pred(mid, d, n1, n2, dih))
        e[lay] = w
        n += w > 0
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return n


def bevel_weighted(ob, width_mm, segments, pred, offset_mm=(0, 0, 0), profile=0.5, harden=True):
    n = set_bevel_weights(ob, pred, offset_mm)
    if n:
        bevel(ob, width_mm, segments, limit="WEIGHT", profile=profile, harden=harden)
    return n


def surface_normals_from(ob, sources, tol_mm=0.05, max_angle_deg=20.0, smooth_deg=35.0) -> int:
    """Custom split normals from smooth SOURCE surfaces (form fix round 2, the grip's shading blotches).

    Booleans and bevels re-triangulate a lofted surface into long thin triangles; weighted normals then average them
    unevenly and the curved surface shows blotches. Every face of `ob` that lies on a source surface (centroid within
    tol_mm, normal within max_angle_deg of the source's interpolated normal) takes, per corner, the source's smooth
    normal interpolated (barycentric, over the source's loop triangles with sharp edges at smooth_deg) at the corner's
    vertex. Every other corner (bevels, cut faces, the panel walls) keeps its current normal. `ob` and the sources share
    one local frame. Returns the number of faces that took source normals."""
    me = ob.data
    me.calc_loop_triangles()
    cur = np.array([tuple(c.vector) for c in me.corner_normals], float)
    trees = []
    for src in sources:
        sm = src.data
        sm.polygons.foreach_set("use_smooth", [True] * len(sm.polygons))
        sm.set_sharp_from_angle(angle=math.radians(smooth_deg))
        sm.update()
        sm.calc_loop_triangles()
        SV = np.array([tuple(v.co) for v in sm.vertices], float)
        SN = np.array([tuple(c.vector) for c in sm.corner_normals], float)
        tri_v = np.array([tuple(t.vertices) for t in sm.loop_triangles], int)
        tri_l = np.array([tuple(t.loops) for t in sm.loop_triangles], int)
        tree = BVHTree.FromPolygons([tuple(v) for v in SV], [tuple(t) for t in tri_v], all_triangles=True)
        trees.append((tree, SV, SN, tri_v, tri_l))

    def interp(p):
        best = None
        for tree, SV, SN, tri_v, tri_l in trees:
            loc, nrm, idx, dist = tree.find_nearest(Vector(p))
            if loc is not None and (best is None or dist < best[0]):
                a, b, c = SV[tri_v[idx]]
                v0, v1, v2 = b - a, c - a, np.array(loc) - a
                d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
                d20, d21 = v2 @ v0, v2 @ v1
                den = d00 * d11 - d01 * d01
                if abs(den) < 1e-30:
                    w = np.array([1 / 3, 1 / 3, 1 / 3])
                else:
                    wv = (d11 * d20 - d01 * d21) / den
                    ww = (d00 * d21 - d01 * d20) / den
                    w = np.clip(np.array([1 - wv - ww, wv, ww]), 0, 1)
                n = (SN[tri_l[idx]] * w[:, None]).sum(0)
                n /= max(np.linalg.norm(n), 1e-12)
                best = (dist, n)
        return best

    V = np.array([tuple(v.co) for v in me.vertices], float)
    tol = tol_mm * 0.001
    cosmax = math.cos(math.radians(max_angle_deg))
    out = cur.copy()
    n_on = 0
    for poly in me.polygons:
        c = np.array(poly.center)
        r = interp(c)
        if r is None or r[0] > tol or float(np.array(poly.normal) @ r[1]) < cosmax:
            continue
        n_on += 1
        for li in poly.loop_indices:
            q = interp(V[me.loops[li].vertex_index])
            if q is not None:
                out[li] = q[1]
    me.normals_split_custom_set([tuple(n) for n in out])
    me.update()
    return n_on
