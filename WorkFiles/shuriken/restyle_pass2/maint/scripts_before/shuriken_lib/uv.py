"""One texture layout for the whole LOD chain: LOD1..n take their UV0 from LOD0's islands.

Why: every LOD used to get its own Smart UV unwrap, so the same surface point sat on a
different texel at each LOD (measured on the eight-point top plate: LOD1 off LOD0 by a
median 0.349 UV, ~715 px at 2048).  Any texture baked on LOD0 would land on the wrong
surface after a LOD switch.

How: LOD0 keeps its Smart UV unwrap (the four-point's shipped UVs stay bit-identical).
Smart UV Project maps every island with one planar projection followed by the packer's
rotation, uniform scale and translation, so each LOD0 island is an exact affine map
(x, y, z, 1) -> (u, v); ``lod0_island_maps`` fits it by least squares and records the
residual (measured < 1e-7 on every island of both forms).  Each LODn face then takes the
LOD0 face that best matches it - nearest in space, with a penalty for a differing
normal - and maps ALL its corners through that face's island map.  Where LODn and LOD0
share a surface (plates, walls, the notch arcs) the UVs are therefore identical to
float precision; where LODn simplifies the surface (fewer bevel segments, the 8-gon
hole, LOD2's missing bevel and hole) its faces are projected by the island of the
surface they replace, so they sample the same texels a few pixels either side.

A LODn face that reaches past the LOD0 island it was matched to (LOD2's chamfer-less
walls are the full plate thickness where LOD0's wall island is only the land) would map
into UV space the packer gave to another island and overlap the LODn face mapped there.
So after the affine pass, every wall or chamfer face in an overlapping pair has each
corner that fell outside its island's UV footprint moved to the UV of the closest point
on that island's surface (``closest_point_barycentric``), a flat plate face only the
corners that fell inside another island, and the overlap test runs again, up to
``max_rounds`` times.  Corners inside their island, and plate corners in empty UV space
(a hole-less LOD2's hub fan puts its centre corner in LOD0's hole), are never touched,
so shared surfaces keep identical UVs.

Measured, not assumed: ``cross_lod_uv`` compares UVs at matching surface points and
``uv_overlap_pairs`` runs qa_check's separating-axis overlap test on the result.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from .spec import MM

UV_MATCH = 1e-7          # UV units: two loops of a shared edge in one island
NORMAL_WEIGHT = 1.0 * MM  # metres of distance one unit of (1 - n.n0) costs when matching faces


def _mesh_arrays(obj):
    """Vertices (float64), polygon loops, per-loop UV0, polygon normals and centroids."""
    mesh = obj.data
    nv, npoly, nloop = len(mesh.vertices), len(mesh.polygons), len(mesh.loops)
    co = np.empty(nv * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    loop_vert = np.empty(nloop, dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vert)
    start = np.empty(npoly, dtype=np.int64)
    total = np.empty(npoly, dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", start)
    mesh.polygons.foreach_get("loop_total", total)
    normals = np.empty(npoly * 3, dtype=np.float32)
    mesh.polygons.foreach_get("normal", normals)
    uv = None
    if mesh.uv_layers:
        uv = np.empty(nloop * 2, dtype=np.float32)
        mesh.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2).astype(np.float64)
    polys = [loop_vert[s:s + t] for s, t in zip(start, total)]
    centroids = np.array([co[p].mean(axis=0) for p in polys])
    return {"co": co, "loop_vert": loop_vert, "start": start, "total": total, "polys": polys,
            "normals": normals.reshape(-1, 3).astype(np.float64), "uv": uv, "centroids": centroids}


def lod0_island_maps(obj) -> dict:
    """UV islands of ``obj``'s UV0 and the exact affine (x, y, z, 1) -> (u, v) map of each."""
    m = _mesh_arrays(obj)
    if m["uv"] is None:
        raise ValueError(f"{obj.name} has no UV map")
    npoly = len(m["polys"])
    parent = list(range(npoly))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    edges: Dict[tuple, list] = {}
    for f, (s, t) in enumerate(zip(m["start"], m["total"])):
        for k in range(t):
            la, lb = s + k, s + (k + 1) % t
            va, vb = m["loop_vert"][la], m["loop_vert"][lb]
            key = (min(va, vb), max(va, vb))
            uva, uvb = m["uv"][la], m["uv"][lb]
            edges.setdefault(key, []).append((f, {va: uva, vb: uvb}))
    for key, owners in edges.items():
        if len(owners) != 2:
            continue
        (f1, d1), (f2, d2) = owners
        if all(np.abs(d1[v] - d2[v]).max() <= UV_MATCH for v in key):
            parent[find(f1)] = find(f2)
    roots = sorted({find(f) for f in range(npoly)})
    island_of = np.array([roots.index(find(f)) for f in range(npoly)], dtype=np.int64)
    maps, residual, sizes = [], [], []
    for island in range(len(roots)):
        faces = np.nonzero(island_of == island)[0]
        loops = np.concatenate([np.arange(m["start"][f], m["start"][f] + m["total"][f]) for f in faces])
        P = np.column_stack([m["co"][m["loop_vert"][loops]], np.ones(len(loops))])
        U = m["uv"][loops]
        M, _res, _rank, _sv = np.linalg.lstsq(P, U, rcond=None)
        maps.append(M)
        residual.append(float(np.abs(P @ M - U).max()))
        sizes.append(int(len(faces)))
    return {"island_of_face": island_of, "maps": maps, "residual_max": max(residual) if residual else 0.0,
            "islands": len(roots), "faces_per_island": sizes, "mesh": m}


def _triangles(m) -> tuple:
    """Fan-triangulated LOD0 polygons (convex by construction) with their polygon index."""
    tris, owner = [], []
    for f, poly in enumerate(m["polys"]):
        for k in range(1, len(poly) - 1):
            tris.append((m["co"][poly[0]], m["co"][poly[k]], m["co"][poly[k + 1]]))
            owner.append(f)
    return np.array(tris, dtype=np.float64), np.array(owner, dtype=np.int64)


def closest_on_triangles(points: np.ndarray, tris: np.ndarray, chunk: int = 64):
    """For each point: distance to every triangle (n_points x n_tris) - chunked generator."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac = b - a, c - a
    normal = np.cross(ab, ac)
    nlen = np.linalg.norm(normal, axis=1)
    nlen[nlen == 0.0] = 1e-30
    d00 = np.einsum("mj,mj->m", ab, ab)
    d01 = np.einsum("mj,mj->m", ab, ac)
    d11 = np.einsum("mj,mj->m", ac, ac)
    denom = d00 * d11 - d01 * d01
    denom[denom == 0.0] = 1e-30

    def seg(point, s0, s1):
        direction = s1 - s0
        length2 = np.einsum("mj,mj->m", direction, direction)
        length2 = np.where(length2 == 0.0, 1e-30, length2)
        t = np.clip(np.einsum("kmj,mj->km", point - s0[None], direction) / length2, 0.0, 1.0)
        closest = s0[None] + t[..., None] * direction[None]
        return np.linalg.norm(point - closest, axis=-1)

    for start in range(0, len(points), chunk):
        point = points[start:start + chunk][:, None, :]
        rel = point - a[None]
        d20 = np.einsum("kmj,mj->km", rel, ab)
        d21 = np.einsum("kmj,mj->km", rel, ac)
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        inside = (v >= 0.0) & (w >= 0.0) & (v + w <= 1.0)
        plane = np.abs(np.einsum("kmj,mj->km", rel, normal)) / nlen
        edges = np.minimum(np.minimum(seg(point, a, b), seg(point, b, c)), seg(point, c, a))
        yield start, np.where(inside, plane, edges)


def closest_point_barycentric(p: np.ndarray, tris: np.ndarray):
    """(triangle index, barycentric (u, v, w), distance) of the point of ``tris`` closest to ``p``.

    Ericson's closest-point-on-triangle regions, vectorised over the triangles.
    """
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac = b - a, c - a
    ap, bp, cp = p[None] - a, p[None] - b, p[None] - c
    d1, d2 = np.einsum("ij,ij->i", ab, ap), np.einsum("ij,ij->i", ac, ap)
    d3, d4 = np.einsum("ij,ij->i", ab, bp), np.einsum("ij,ij->i", ac, bp)
    d5, d6 = np.einsum("ij,ij->i", ab, cp), np.einsum("ij,ij->i", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    n = len(tris)
    bary = np.zeros((n, 3))
    done = np.zeros(n, dtype=bool)

    def put(mask, u, v, w):
        mask = mask & ~done
        bary[mask] = np.column_stack([u, v, w])[mask]
        done[mask] = True

    ones, zeros = np.ones(n), np.zeros(n)
    with np.errstate(divide="ignore", invalid="ignore"):
        put((d1 <= 0) & (d2 <= 0), ones, zeros, zeros)
        put((d3 >= 0) & (d4 <= d3), zeros, ones, zeros)
        put((d6 >= 0) & (d5 <= d6), zeros, zeros, ones)
        t = np.where(d1 - d3 != 0, d1 / (d1 - d3), 0.0)
        put((vc <= 0) & (d1 >= 0) & (d3 <= 0), 1 - t, t, zeros)
        t = np.where(d2 - d6 != 0, d2 / (d2 - d6), 0.0)
        put((vb <= 0) & (d2 >= 0) & (d6 <= 0), 1 - t, zeros, t)
        den = (d4 - d3) + (d5 - d6)
        t = np.where(den != 0, (d4 - d3) / den, 0.0)
        put((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), zeros, 1 - t, t)
        den = va + vb + vc
        v = np.where(den != 0, vb / den, 0.0)
        w = np.where(den != 0, vc / den, 0.0)
        put(np.ones(n, dtype=bool), 1 - v - w, v, w)
    closest = bary[:, :1] * a + bary[:, 1:2] * b + bary[:, 2:3] * c
    dist = np.linalg.norm(closest - p[None], axis=1)
    k = int(np.argmin(dist))
    return k, bary[k], float(dist[k])


def _inside_uv(point: np.ndarray, uv_tris: np.ndarray, tolerance: float) -> bool:
    """True when ``point`` lies in (or within about ``tolerance`` of) one of the UV triangles."""
    a, b, c = uv_tris[:, 0], uv_tris[:, 1], uv_tris[:, 2]
    v0, v1, v2 = b - a, c - a, point[None] - a
    d00 = np.einsum("ij,ij->i", v0, v0)
    d01 = np.einsum("ij,ij->i", v0, v1)
    d11 = np.einsum("ij,ij->i", v1, v1)
    d20 = np.einsum("ij,ij->i", v2, v0)
    d21 = np.einsum("ij,ij->i", v2, v1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-24
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(ok, (d11 * d20 - d01 * d21) / den, -1.0)
        w = np.where(ok, (d00 * d21 - d01 * d20) / den, -1.0)
        scale = np.sqrt(np.maximum(d00, d11))
        tol = tolerance / np.where(scale > 0, scale, 1.0)
    return bool(np.any(ok & (v >= -tol) & (w >= -tol) & (v + w <= 1.0 + tol)))


def _overlapping_faces(target) -> set:
    """Polygon indices of ``target`` in an overlapping UV0 triangle pair (qa_check's SAT test)."""
    import bmesh

    from pipeline.qa_check import uv_overlap_sat
    bm = bmesh.new()
    try:
        bm.from_mesh(target.data)
        layer = bm.loops.layers.uv[0]
        tris, owner = [], []
        for face in bm.faces:
            loops = list(face.loops)
            for k in range(1, len(loops) - 1):
                tris.append([tuple(l[layer].uv) for l in (loops[0], loops[k], loops[k + 1])])
                owner.append(face.index)
    finally:
        bm.free()
    tris = np.array(tris, dtype=np.float64)
    if uv_overlap_sat(tris) == 0:
        return set()
    mins, maxs = tris.min(axis=1), tris.max(axis=1)
    bad = set()
    order = np.argsort(mins[:, 0])
    for pos, i in enumerate(order):
        for j in order[pos + 1:]:
            if mins[j, 0] >= maxs[i, 0]:
                break
            if mins[j, 1] >= maxs[i, 1] or mins[i, 1] >= maxs[j, 1]:
                continue
            if uv_overlap_sat(tris[[i, j]]):
                bad.update((owner[i], owner[j]))
    return bad


def transfer_uvs(lod0, target, normal_weight: float = NORMAL_WEIGHT, max_rounds: int = 4) -> dict:
    """Overwrite ``target``'s UV0 with LOD0's island maps; return what was done."""
    islands = lod0_island_maps(lod0)
    m0 = islands["mesh"]
    tris, owner = _triangles(m0)
    tri_normals = m0["normals"][owner]
    mt = _mesh_arrays(target)
    mesh = target.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    chosen = np.empty(len(mt["polys"]), dtype=np.int64)
    best_distance = np.empty(len(mt["polys"]))
    for start, dist in closest_on_triangles(mt["centroids"], tris):
        normals = mt["normals"][start:start + dist.shape[0]]
        score = dist + normal_weight * (1.0 - normals @ tri_normals.T)
        pick = np.argmin(score, axis=1)
        chosen[start:start + dist.shape[0]] = owner[pick]
        best_distance[start:start + dist.shape[0]] = dist[np.arange(dist.shape[0]), pick]
    uv = np.empty((len(mt["loop_vert"]), 2), dtype=np.float64)
    used = np.zeros(islands["islands"], dtype=bool)
    face_island = np.empty(len(mt["polys"]), dtype=np.int64)
    for f, (s, t) in enumerate(zip(mt["start"], mt["total"])):
        island = islands["island_of_face"][chosen[f]]
        face_island[f] = island
        used[island] = True
        loops = np.arange(s, s + t)
        P = np.column_stack([mt["co"][mt["loop_vert"][loops]], np.ones(t)])
        uv[loops] = P @ islands["maps"][island]
    mesh.uv_layers[0].data.foreach_set("uv", uv.astype(np.float32).ravel())
    mesh.update()

    # --- faces that reach past their island: clamp only the corners outside it.
    tri_island = islands["island_of_face"][owner]
    uv_tris0 = np.array([[m0["uv"][l] for l in (m0["start"][f], m0["start"][f] + k, m0["start"][f] + k + 1)]
                         for f in range(len(m0["polys"])) for k in range(1, m0["total"][f] - 1)])
    clamped_loops, rounds, remaining = set(), 0, set()
    tolerance = 0.25 / 2048.0
    # Which corners of a face in an overlapping pair get clamped: on a wall or chamfer face
    # every corner outside its island (a chamfer-less LOD2 wall is the full plate thickness
    # where LOD0's wall island is only the land, so its UVs compress onto the land); on a
    # flat plate face only a corner that lies inside ANOTHER island's footprint.  A plate
    # corner in empty UV space - a hole-less LOD2's hub fan maps its centre corner into
    # LOD0's hole, the rim corners a texel past the plate island's edge - is harmless and
    # stays where the affine map put it, so the face stays exact wherever LOD0 has a surface
    # (moving it folds the fan over its neighbours).
    for rounds in range(1, max_rounds + 1):
        remaining = _overlapping_faces(target)
        if not remaining:
            rounds -= 1
            break
        changed = False
        for f in sorted(remaining):
            pick = np.nonzero(tri_island == face_island[f])[0]
            others = np.nonzero(tri_island != face_island[f])[0]
            flat = abs(mt["normals"][f][2]) > 0.999
            for loop in range(mt["start"][f], mt["start"][f] + mt["total"][f]):
                if loop in clamped_loops or _inside_uv(uv[loop], uv_tris0[pick], tolerance):
                    continue
                if flat and not _inside_uv(uv[loop], uv_tris0[others], tolerance):
                    continue
                k, bary, _dist = closest_point_barycentric(mt["co"][mt["loop_vert"][loop]], tris[pick])
                uv[loop] = bary @ uv_tris0[pick[k]]
                clamped_loops.add(loop)
                changed = True
        mesh.uv_layers[0].data.foreach_set("uv", uv.astype(np.float32).ravel())
        mesh.update()
        if not changed:
            remaining = _overlapping_faces(target)
            break
    else:
        remaining = _overlapping_faces(target)
    # --- the unit square.  A LODn corner the affine map puts past u = 0 / v = 0 / 1 (a
    # chamfer-less LOD2's plate corner sits W outside LOD0's plate island, whose edge can be
    # within W of the UV border) would sample the opposite edge of the maps under Unreal's
    # default Wrap addressing, so every such corner is clamped to the square.  Sub-texel
    # cosmetics at the LOD2 switch distance (the four-point's were 4.75 px at 2048), but a
    # buyer's texture must never wrap.  The overlap test runs once more afterwards.
    outside_square = int(((uv < 0.0) | (uv > 1.0)).any(axis=1).sum())
    uv_before_clamp = [round(float(uv[:, 0].min()), 5), round(float(uv[:, 1].min()), 5),
                       round(float(uv[:, 0].max()), 5), round(float(uv[:, 1].max()), 5)]
    if outside_square:
        uv = np.clip(uv, 0.0, 1.0)
        mesh.uv_layers[0].data.foreach_set("uv", uv.astype(np.float32).ravel())
        mesh.update()
        remaining = _overlapping_faces(target)
    return {
        "method": "LOD0 island affine maps (Smart UV planar projection + pack transform, fitted by least squares)",
        "lod0_islands": islands["islands"],
        "lod0_island_fit_residual_max_uv": float(f"{islands['residual_max']:.3e}"),
        "lod0_islands_used": int(used.sum()),
        "face_match_distance_mm": {"median": round(float(np.median(best_distance)) / MM, 6),
                                   "max": round(float(best_distance.max()) / MM, 6)},
        "normal_weight_mm": normal_weight / MM,
        "clamped_loops": len(clamped_loops),
        "clamp_rounds": rounds,
        "overlapping_faces_left": len(remaining),
        "unit_square_clamped_loops": outside_square,
        "uv_range_before_unit_square_clamp": uv_before_clamp,
        "uv_range": [round(float(uv[:, 0].min()), 5), round(float(uv[:, 1].min()), 5),
                     round(float(uv[:, 0].max()), 5), round(float(uv[:, 1].max()), 5)],
    }


def uv_overlap_pairs(obj) -> int:
    """qa_check's separating-axis UV0 overlap count on ``obj`` (0 = clean)."""
    import bmesh

    from pipeline.qa_check import _uv_triangles, uv_overlap_sat
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        return int(uv_overlap_sat(_uv_triangles(bm, bm.loops.layers.uv[0])))
    finally:
        bm.free()


def _loop_triangles(m):
    """Fan triangles as (vertex-position triples, loop-index triples)."""
    pos, loops = [], []
    for s, t in zip(m["start"], m["total"]):
        for k in range(1, t - 1):
            li = (s, s + k, s + k + 1)
            loops.append(li)
            pos.append([m["co"][m["loop_vert"][l]] for l in li])
    return np.array(pos, dtype=np.float64), np.array(loops, dtype=np.int64)


def _barycentric_2d(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-30:
        return None
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return 1.0 - v - w, v, w


def cross_lod_uv(lod0, target, texture_size: int = 2048, half_t: Optional[float] = None,
                 near: float = 0.25 * MM) -> dict:
    """UV difference between LOD0 and ``target`` at the same surface point, in UV and px.

    ``top_plate``: centroids and corners of every flat top-plate triangle of ``target``,
    looked up at the same XY on LOD0's flat top plate (points LOD0 has no plate under -
    the filled hole of a hole-less LOD, a missing bevel - are skipped and counted).  This is
    the verifier's metric and the gate.  ``surface``: every triangle centroid of
    ``target`` against LOD0's surface near it (every LOD0 triangle within ``near`` of the
    closest one): the smallest UV distance between the centroid's UV and the UV of the
    closest point on one of those triangles.  Taking the best nearby triangle rather than
    the single closest one keeps UV seams out of the figure - on a seam the closest LOD0
    face can belong to the island across the border, which is a different place in UV for
    the same surface point - so this measures how far a LODn texel lookup lands from
    LOD0's texel for the same point, everywhere on the mesh.
    """
    m0, mt = _mesh_arrays(lod0), _mesh_arrays(target)
    pos0, loops0 = _loop_triangles(m0)
    post, loopst = _loop_triangles(mt)
    uv0, uvt = m0["uv"], mt["uv"]
    zmax = float(m0["co"][:, 2].max()) if half_t is None else half_t

    def flat_top(pos):
        return np.all(np.abs(pos[:, :, 2] - zmax) < 1e-9, axis=1)

    top0 = np.nonzero(flat_top(pos0))[0]
    topt = np.nonzero(flat_top(post))[0]
    a0 = pos0[top0, 0, :2]
    b0 = pos0[top0, 1, :2]
    c0 = pos0[top0, 2, :2]
    diffs, skipped = [], 0
    for tri in topt:
        corners = post[tri, :, :2]
        tuv = uvt[loopst[tri]]
        samples = [(corners.mean(axis=0), tuv.mean(axis=0))] + [(corners[k], tuv[k]) for k in range(3)]
        for p, uv_t in samples:
            # candidate LOD0 top triangles whose bbox holds p
            lo = np.minimum(np.minimum(a0, b0), c0) - 1e-9
            hi = np.maximum(np.maximum(a0, b0), c0) + 1e-9
            cand = np.nonzero(np.all((p >= lo) & (p <= hi), axis=1))[0]
            hit = None
            for k in cand:
                bc = _barycentric_2d(p, a0[k], b0[k], c0[k])
                if bc is not None and min(bc) >= -1e-9:
                    hit = (k, bc)
                    break
            if hit is None:
                skipped += 1
                continue
            k, bc = hit
            uv_0 = bc[0] * uv0[loops0[top0[k], 0]] + bc[1] * uv0[loops0[top0[k], 1]] + bc[2] * uv0[loops0[top0[k], 2]]
            diffs.append(float(np.linalg.norm(uv_0 - uv_t)))
    diffs = np.array(diffs) if diffs else np.zeros(1)
    # whole surface: best agreement among the LOD0 triangles near each centroid
    cent = post.mean(axis=1)
    cent_uv = uvt[loopst].mean(axis=1)
    uv_tris0 = uv0[loops0]
    surf = np.empty(len(cent))
    for start, dist in closest_on_triangles(cent, pos0):
        for row in range(dist.shape[0]):
            cand = np.nonzero(dist[row] <= dist[row].min() + near)[0]
            best = math.inf
            for k in cand:
                _i, bary, _d = closest_point_barycentric(cent[start + row], pos0[k:k + 1])
                best = min(best, float(np.linalg.norm(bary @ uv_tris0[k] - cent_uv[start + row])))
            surf[start + row] = best
    px = float(texture_size)
    return {
        "texture_size": texture_size,
        "top_plate": {"samples": int(diffs.size), "skipped_no_lod0_plate_under": skipped,
                      "median_uv": float(f"{np.median(diffs):.3e}"), "max_uv": float(f"{diffs.max():.3e}"),
                      "max_px": round(float(diffs.max()) * px, 4)},
        "surface": {"samples": int(surf.size), "near_mm": near / MM,
                    "median_px": round(float(np.median(surf)) * px, 4),
                    "p95_px": round(float(np.percentile(surf, 95)) * px, 4),
                    "max_px": round(float(surf.max()) * px, 4)},
    }


__all__ = ["closest_on_triangles", "closest_point_barycentric", "cross_lod_uv", "lod0_island_maps", "transfer_uvs",
           "uv_overlap_pairs"]
