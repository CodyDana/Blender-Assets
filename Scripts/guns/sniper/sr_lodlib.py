"""SR01 W3 LOD helpers (Blender; shared by sr_game.py and sr_attach.py): a part's LOD copy by collapse decimation
(UV seams and both UV layers kept, weighted normals re-done: sharp 30, weight 100) and qa_check's UV overlap rule
applied the SMG way (the smaller triangle of every overlapping pair collapses to its centre: zero area, ignored by
qa_check)."""
from __future__ import annotations

import numpy as np

from gunlib import bl
from gunlib import uvchart as UC


def duplicate_faces(ob):
    """faces sharing their vertex set with another face (a back-to-back fin the collapse can leave; FBX drops one)."""
    from collections import Counter
    c = Counter(tuple(sorted(p.vertices)) for p in ob.data.polygons)
    return sum(v for v in c.values() if v > 1)


def drop_coincident_pairs(ob):
    """(W4 A2) faces sharing their vertex set with another face after the joined LOD's weld: two touching parts'
    decimated walls meeting face to face. Back-to-back pairs are internal walls (both go, the solids close against each
    other); same-facing copies keep one. The FBX writer otherwise drops one of each pair itself (scope LOD2: 850 built,
    848 exported). Returns the number of faces removed."""
    import bmesh
    from collections import defaultdict
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    groups = defaultdict(list)
    for f in bm.faces:
        groups[tuple(sorted(v.index for v in f.verts))].append(f)
    kill = []
    for fs in groups.values():
        if len(fs) < 2:
            continue
        if len(fs) == 2 and fs[0].normal.dot(fs[1].normal) < 0.0:
            kill += fs
        else:
            kill += fs[1:]
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        bm.to_mesh(ob.data)
        ob.data.update()
    bm.free()
    return len(kill)


def decimate_copy(o, name, coll, ratio, tries=6):
    """a decimated copy; a result with duplicate faces is redone at ratio x 0.97 (up to `tries`)."""
    for k in range(tries):
        c = o.copy()
        c.data = o.data.copy()
        c.name = name
        c.data.name = name
        coll.objects.link(c)
        for cc in list(c.users_collection):
            if cc != coll:
                cc.objects.unlink(c)
        if ratio < 0.999:
            m = c.modifiers.new("dec", "DECIMATE")
            m.decimate_type = "COLLAPSE"
            m.ratio = ratio * (0.97 ** k)
            m.use_collapse_triangulate = True
            bl.apply_modifiers(c)
            bl.clean(c)                 # exact duplicates / zero-area faces the collapse can leave (the FBX drops them)
        if duplicate_faces(c) == 0 or k == tries - 1:
            break
        me = c.data
        import bpy
        bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.meshes.remove(me)
    if duplicate_faces(c):              # (W4) fins left after the last try: the FBX writer drops one of each pair
        drop_coincident_pairs(c)
    bl.weighted_normals(c, sharp_deg=30.0, weight=100, clear_custom=True)
    return c


def loop_tris(o, layer):
    me = o.data
    lay = me.uv_layers[layer]
    uv = np.empty(len(lay.data) * 2)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    L = ls[:, None] + np.arange(3)[None, :]
    return uv, L


def fix_uv_overlaps(objs, layer):
    """qa_check's SAT overlap rule over the given objects' triangles in `layer`: the smaller of every overlapping pair
    collapses to its centre (zero area). Returns the number collapsed."""
    data = []
    for o in objs:
        uv, L = loop_tris(o, layer)
        data.append((o, uv, L))
    T = np.vstack([uv[L] for _o, uv, L in data]) if data else np.zeros((0, 3, 2))
    owner = np.concatenate([np.full(len(L), i) for i, (_o, _u, L) in enumerate(data)]) if data else np.zeros(0, int)
    local = np.concatenate([np.arange(len(L)) for _o, _u, L in data]) if data else np.zeros(0, int)
    n_fixed = 0
    for _ in range(4):
        pairs = UC.overlap_pairs(T.astype(np.float32).astype(np.float64), 1e-5, qa=True)
        if not len(pairs):
            break
        area = 0.5 * np.abs((T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) -
                            (T[:, 2, 0] - T[:, 0, 0]) * (T[:, 1, 1] - T[:, 0, 1]))
        kill = set()
        for i, j in pairs:
            kill.add(int(i) if area[i] <= area[j] else int(j))
        for k in kill:
            T[k] = T[k].mean(0)[None, :]
        n_fixed += len(kill)
    for i, (o, uv, L) in enumerate(data):
        sel = owner == i
        uv[L[local[sel]].ravel()] = T[sel].reshape(-1, 2)
        o.data.uv_layers[layer].data.foreach_set("uv", uv.ravel())
    return n_fixed


def hull_safe(name, pts_m, parent, coll, max_verts=32, dilate_m=0.0002):
    """(W4) gunlib.game.hull_from_points' method (convex hull -> collapse to <= max_verts + re-hull -> dilate -> grow
    to contain -> dissolve coplanar -> grow) with the points deduplicated on a 1 micron grid and the face normals
    recalculated outward after every hull step: W4's cheek-riser points gave gunlib's path inward faces, and its
    grow step (planes from the normals) then scaled the hull to 1e16 m. Used only when gunlib's hull fails the
    sr_game.valid_hull check."""
    import bmesh
    import bpy
    from mathutils import Matrix, Vector
    from gunlib.game import _grow_to_contain
    from pipeline.helpers import apply_modifier
    P = np.unique(np.round(np.asarray(pts_m, float), 6), axis=0)

    def rehull(me):
        bm = bmesh.new()
        bm.from_mesh(me)
        res = bmesh.ops.convex_hull(bm, input=list(bm.verts))
        keep_f = {g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)}
        stale = [f for f in bm.faces if f not in keep_f]
        if stale:
            bmesh.ops.delete(bm, geom=stale, context="FACES_ONLY")
        loose_e = [e for e in bm.edges if not e.link_faces]
        if loose_e:
            bmesh.ops.delete(bm, geom=loose_e, context="EDGES")
        loose_v = [v for v in bm.verts if not v.link_faces]
        if loose_v:
            bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        me.update()
    c0 = P.mean(0)
    bm = bmesh.new()
    for p in P:
        bm.verts.new(p)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    rehull(me)
    h = bpy.data.objects.new(name, me)
    coll.objects.link(h)
    for _ in range(30):
        if len(h.data.vertices) <= max_verts:
            break
        mod = h.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = max(0.1, (max_verts * 1.6) / max(len(h.data.polygons), 1))
        apply_modifier(h, mod)
        rehull(h.data)
    for v in h.data.vertices:
        d = np.array(v.co[:]) - c0
        ln = np.linalg.norm(d)
        if ln > 0:
            v.co = Vector(np.array(v.co[:]) + d / ln * dilate_m)
    rehull(h.data)
    _grow_to_contain(h, P)
    b3 = bmesh.new()
    b3.from_mesh(h.data)
    bmesh.ops.dissolve_limit(b3, angle_limit=0.0005, verts=b3.verts[:], edges=b3.edges[:])
    bmesh.ops.triangulate(b3, faces=b3.faces[:])
    bmesh.ops.recalc_face_normals(b3, faces=b3.faces[:])
    b3.to_mesh(h.data)
    b3.free()
    _grow_to_contain(h, P)
    h.data.materials.clear()
    h.parent = parent
    h.matrix_parent_inverse = Matrix.Identity(4)
    h.hide_render = True
    h.display_type = "WIRE"
    h["ue_collision"] = "UCX"
    return h
