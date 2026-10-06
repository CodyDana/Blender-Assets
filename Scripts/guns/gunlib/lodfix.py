"""UV repair for decimated LODs (import inside Blender).

A collapse decimate interpolates UV0, so the reduced LOD keeps sampling the LOD0 maps; near island borders a collapse
can fold a triangle over in UV (its UV winding flips) and it then overlaps a neighbour (qa_check uv_no_overlap).
relax_uv_foldovers moves each corner of a flipped triangle, with every loop welded to it (same vertex, same UV), to the
centroid of its UV one-ring (the classic fold-over fix: a star-shaped ring contains its centroid), pass after pass,
until no triangle is flipped. Islands and seams are kept: only welded loops move together.
"""
from __future__ import annotations

from typing import Dict

import bmesh
import numpy as np


def _signed(a, b, c):
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def relax_uv_foldovers(ob, layer="UV0", passes=30, key_digits=7) -> Dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv[layer]
    # dominant winding (no mirrored islands on guns)
    s = [_signed(*[l[uvl].uv for l in f.loops]) for f in bm.faces if len(f.loops) == 3]
    sign = 1.0 if sum(1 for x in s if x > 0) >= sum(1 for x in s if x < 0) else -1.0

    def flipped():
        return [f for f in bm.faces if len(f.loops) == 3 and _signed(*[l[uvl].uv for l in f.loops]) * sign <= 0.0]

    before = len(flipped())
    for _ in range(passes):
        bad = flipped()
        if not bad:
            break
        for f in bad:
            for l in f.loops:
                v = l.vert
                key = (round(l[uvl].uv.x, key_digits), round(l[uvl].uv.y, key_digits))
                group = [m for m in v.link_loops if (round(m[uvl].uv.x, key_digits), round(m[uvl].uv.y, key_digits)) == key]
                ring = []
                for m in group:
                    ring.append(m.link_loop_next[uvl].uv.copy())
                    ring.append(m.link_loop_prev[uvl].uv.copy())
                if not ring:
                    continue
                c = np.mean([(p.x, p.y) for p in ring], axis=0)
                for m in group:
                    m[uvl].uv = (float(c[0]), float(c[1]))
    after = len(flipped())
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return {"flipped_before": before, "flipped_after": after}


def overlap_pairs(tris: np.ndarray, epsilon: float = 1e-5):
    """Overlapping UV triangle pairs (indices), qa_check.uv_overlap_sat's test (touching / degenerate excluded)."""
    import itertools
    from collections import defaultdict
    edge_a = tris[:, 1] - tris[:, 0]
    edge_b = tris[:, 2] - tris[:, 0]
    area2 = np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0])
    keep = np.nonzero(area2 > 1e-12)[0]
    t = tris[keep]
    mins, maxs = t.min(axis=1), t.max(axis=1)
    cell = max(float(np.median(maxs - mins)) * 2.0, 1e-4)
    buckets = defaultdict(list)
    lo = np.floor(mins / cell).astype(np.int64)
    hi = np.floor(maxs / cell).astype(np.int64)
    for i in range(len(t)):
        for cx in range(lo[i, 0], hi[i, 0] + 1):
            for cy in range(lo[i, 1], hi[i, 1] + 1):
                buckets[(cx, cy)].append(i)
    pairs = set()
    for m in buckets.values():
        if len(m) > 1:
            pairs.update(itertools.combinations(m, 2))
    if not pairs:
        return []
    P = np.array(sorted(pairs), np.int64)
    A, B = t[P[:, 0]], t[P[:, 1]]
    sep = np.any(maxs[P[:, 0]] <= mins[P[:, 1]] + epsilon, axis=1) | np.any(maxs[P[:, 1]] <= mins[P[:, 0]] + epsilon, axis=1)
    for tri in (A, B):
        for k in range(3):
            e = tri[:, (k + 1) % 3] - tri[:, k]
            ax = np.stack([-e[:, 1], e[:, 0]], axis=-1)
            n = np.linalg.norm(ax, axis=1, keepdims=True)
            ax = ax / np.where(n == 0, 1.0, n)
            pa = np.einsum("pij,pj->pi", A, ax)
            pb = np.einsum("pij,pj->pi", B, ax)
            sep |= (pa.max(1) <= pb.min(1) + epsilon) | (pb.max(1) <= pa.min(1) + epsilon)
    return [(int(keep[a]), int(keep[b])) for a, b in P[~sep]]


def fix_uv_overlaps(ob, layer="UV0", rounds=40, step=0.3, key_digits=7) -> Dict[str, int]:
    """Separate the few overlapping UV triangles a decimate leaves at island borders: each round, every corner of an
    overlapping pair that lies inside (or within 2e-5 of) the other triangle moves, with its welded loops, `step` of
    the way toward its own triangle's centroid. Triangulated meshes only."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    quads = [f for f in bm.faces if len(f.loops) > 3]
    if quads:
        bmesh.ops.triangulate(bm, faces=quads)
    bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv[layer]
    faces = [f for f in bm.faces]

    def tris():
        return np.array([[tuple(l[uvl].uv) for l in f.loops] for f in faces], float)

    def inside(p, tri, m=2e-5):
        a, b, c = tri
        d1, d2, d3 = _signed(p, a, b), _signed(p, b, c), _signed(p, c, a)
        s = _signed(a, b, c)
        return (d1 > -m and d2 > -m and d3 > -m) if s > 0 else (d1 < m and d2 < m and d3 < m)

    before = len(overlap_pairs(tris()))
    for _ in range(rounds):
        T = tris()
        pairs = overlap_pairs(T)
        if not pairs:
            break
        for i, j in pairs:
            for a, b in ((i, j), (j, i)):
                fa = faces[a]
                cen = T[a].mean(0)
                for k, l in enumerate(fa.loops):
                    if inside(T[a][k], T[b]):
                        v = l.vert
                        key = (round(l[uvl].uv.x, key_digits), round(l[uvl].uv.y, key_digits))
                        new = T[a][k] + (cen - T[a][k]) * step
                        for m in v.link_loops:
                            if (round(m[uvl].uv.x, key_digits), round(m[uvl].uv.y, key_digits)) == key:
                                m[uvl].uv = (float(new[0]), float(new[1]))
    after = len(overlap_pairs(tris()))
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return {"overlaps_before": before, "overlaps_after": after}
