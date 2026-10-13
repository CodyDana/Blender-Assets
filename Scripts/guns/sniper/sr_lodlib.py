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
