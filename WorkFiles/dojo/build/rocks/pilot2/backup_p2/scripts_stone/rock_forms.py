"""Rock form generators for the SDF chain (STONE_BUILDING_STUDY.md 3.9, 4.9.2-4.9.3): traced visual hulls, joint-set
block cells, fresh-fracture flake cutters, crack wedges and corner chips. Everything returns closed convex (or
prism) meshes as numpy (V, F) for `stone_sdf.SDFGraph.mesh`. bpy (bmesh / mathutils) + numpy.

Method notes
- Visual hull (the 2D outline authority, CLAUDE.md "tracing works as the 2D outline authority"): the traced front
  outline extruded along depth, the side outline along length and the plan outline along height, intersected as SDFs.
  Their crossing creases are exactly the arrises a jointed block has; the opening then rounds them.
- Flakes (the pilot's answer to the pine rock's "speckle, no flake relief"): granite spalls in shallow planar scars.
  Each flake is a polytope cutter: the half-space beyond a plane set ``depth`` under the surface, bounded by an
  irregular 5-7-gon footprint whose walls lean outward (a scarp of about 55-70 deg, not a vertical saw cut). Scars
  overlap in random order, so the surface becomes overlapping planar facets with crisp little step edges. The
  scars cut deepest at their centre and run out where the surface curves away from the plane.
- Cliff blocks: 2-3 joint families (vertical A and B, sub-horizontal sheeting C) partition the bounding box into
  cells; each cell is intersected with the (locally eroded) hull and rounded on its own, then all are unioned. The
  joints between neighbouring blocks read as V-grooves, recessed blocks as ledges and steps.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np

from stone_sdf import (unit, jitter, polytope_vertices, hull_mesh, prism_mesh, vertex_normals, face_normals_areas)


# ----------------------------------------------------------------------------------------------- outlines
def mask_polygon(mask, px_per_m_x, px_per_m_y, dp_px=0.6, sigma_px=1.5):
    """Outline polygon of a cropped silhouette mask (row 0 = top) in metres: x from the centre of the bbox, y up from
    the bottom row. The pixel contour is resampled at 0.5 px and smoothed along its length (gaussian, ``sigma_px``,
    inside the +-2 px trace error) so pixel steps do not become ridges when the outline is extruded. Separate x / y
    scales let a reduced sheet view be fitted to measured dimensions."""
    import rock_ref as rr
    P = rr.outline(mask) + 0.5
    seg = np.hypot(*np.diff(np.vstack([P, P[:1]]), axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    t = np.arange(0, L, 0.5)
    Pc = np.vstack([P, P[:1]])
    R = np.stack([np.interp(t, s, Pc[:, 0]), np.interp(t, s, Pc[:, 1])], 1)
    if sigma_px > 0:
        k = int(4 * sigma_px / 0.5)
        w = np.exp(-0.5 * ((np.arange(-k, k + 1) * 0.5) / sigma_px) ** 2)
        w /= w.sum()
        R = np.stack([np.convolve(np.concatenate([R[-k:, i], R[:, i], R[:k, i]]), w, "valid") for i in (0, 1)], 1)
    j = int(np.argmax(np.hypot(*(R - R[0]).T)))
    i1 = rr._dp(R[:j + 1], dp_px)
    i2 = rr._dp(np.vstack([R[j:], R[:1]]), dp_px) + j
    idx = np.unique(np.concatenate([i1, i2[:-1]]) % len(R))
    Q = R[idx]
    H, W = mask.shape
    x = (Q[:, 0] - W / 2.0) / px_per_m_x
    y = (H - Q[:, 1]) / px_per_m_y
    return np.stack([x, y], 1)


def fit_polygon(poly, size_x, size_y, flip_x=False):
    """Scale a polygon (any units) so its bbox is size_x by size_y, x centred on 0, y from 0 (bottom)."""
    P = np.asarray(poly, float).copy()
    lo, hi = P.min(0), P.max(0)
    P = (P - lo) / np.maximum(hi - lo, 1e-9)
    P[:, 0] = (P[:, 0] - 0.5) * size_x
    P[:, 1] = P[:, 1] * size_y
    if flip_x:
        P[:, 0] = -P[:, 0]
    return P


def extend_base(poly, z_cut, z_bury):
    """The buried skirt (study 3.10): each run of the outline below ``z_cut`` is replaced by vertical walls from
    where the outline crosses ``z_cut`` down to ``z_bury``, so a rock set on grade has no pedestal and a sunk rock
    keeps its section. Polygon order is kept (works on concave outlines)."""
    P = np.asarray(poly, float)
    n = len(P)
    below = P[:, 1] <= z_cut
    if not below.any() or below.all():
        return P.copy()
    start = int(np.nonzero(~below)[0][0])          # rotate so the ring starts above the cut
    P = np.roll(P, -start, 0)
    below = np.roll(below, -start)
    out = []
    i = 0
    while i < n:
        if not below[i]:
            out.append(P[i])
            i += 1
            continue
        a, b = P[i - 1], P[i]
        ta = (z_cut - a[1]) / (b[1] - a[1])
        xa = a[0] + ta * (b[0] - a[0])
        j = i
        while j < n and below[j]:
            j += 1
        c, d = P[j - 1], P[j % n]
        tc = (z_cut - c[1]) / (d[1] - c[1])
        xc = c[0] + tc * (d[0] - c[0])
        out += [np.array([xa, z_cut]), np.array([xa, z_bury]), np.array([xc, z_bury]), np.array([xc, z_cut])]
        i = j
    return np.array(out)


def visual_hull_meshes(front_xz, side_yz, top_xy, pad=0.5, zlo=-1.0, zhi=6.0):
    """Three prisms whose SDF intersection is the visual hull: front (x, z) along y, side (y, z) along x, plan
    (x, y) along z."""
    out = []
    span = pad + max(np.abs(np.asarray(front_xz)[:, 0]).max(), np.abs(np.asarray(side_yz)[:, 0]).max(), 1.0) * 2
    out.append(prism_mesh(front_xz, (0, 2), -span, span))
    out.append(prism_mesh(side_yz, (1, 2), -span, span))
    if top_xy is not None:
        out.append(prism_mesh(top_xy, (0, 1), zlo, zhi))
    return out


def halfspace_box(n, d, lo, hi):
    """The solid {n.x >= d} clipped to the box lo..hi (a joint-plane cut or a fresh fracture)."""
    n = unit(n)
    planes = [(-n, -d)]
    for k in range(3):
        e = np.zeros(3)
        e[k] = 1.0
        planes += [(e, float(hi[k])), (-e, float(-lo[k]))]
    V = polytope_vertices(planes)
    if len(V) < 4:
        return None
    return hull_mesh(V)


def support(V, n):
    return float((np.asarray(V) @ unit(n)).max())


def joint_cut(V, n, depth, margin=0.3):
    """Cut a broad joint face: remove the cap of the solid ``V`` (its points) beyond the plane ``depth`` under its
    support in direction ``n``."""
    n = unit(n)
    d = support(V, n) - depth
    lo = V.min(0) - margin
    hi = V.max(0) + margin
    return halfspace_box(n, d, lo, hi)


# ----------------------------------------------------------------------------------------------- flakes
def sample_surface(V, F, n, rng, zmin=0.05, nz_min=-0.45, weights=None):
    """Area-weighted random points on a mesh with their face normals (above ``zmin``, not facing down)."""
    fn, a = face_normals_areas(V, F)
    c = V[F].mean(1)
    ok = (c[:, 2] > zmin) & (fn[:, 2] > nz_min)
    w = a * ok
    if weights is not None:
        w = w * weights
    w = w / w.sum()
    idx = rng.choice(len(F), n, p=w)
    r1 = np.sqrt(rng.uniform(size=n))
    r2 = rng.uniform(size=n)
    A, B, C = V[F[idx, 0]], V[F[idx, 1]], V[F[idx, 2]]
    P = (1 - r1)[:, None] * A + (r1 * (1 - r2))[:, None] * B + (r1 * r2)[:, None] * C
    return P, fn[idx], idx


def flake_cutter(p, n, R, depth, rng, lean=0.45, sides=(5, 8), cap=0.12, elong=(1.0, 1.6)):
    """One spall scar: the solid beyond the plane ``depth`` under ``p`` (normal ``n``) inside an irregular polygon
    footprint of radius ~``R`` with outward-leaning walls (``lean`` = tan of the wall's lean from the normal)."""
    n = unit(n)
    t = unit(np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]))
    b = np.cross(n, t)
    rot = rng.uniform(0, 2 * math.pi)
    k = int(rng.integers(sides[0], sides[1] + 1))
    el = rng.uniform(*elong)
    planes = [(-n, -(float(n @ p) - depth)), (n, float(n @ p) + cap)]
    angs = np.sort(rng.uniform(0, 2 * math.pi, k)) if k > 3 else np.linspace(0, 2 * math.pi, k, endpoint=False)
    angs = np.linspace(0, 2 * math.pi, k, endpoint=False) + rng.uniform(-0.35, 0.35, k) * (2 * math.pi / k)
    for a in angs:
        u = math.cos(a + rot) * t * el + math.sin(a + rot) * b / el
        u = unit(u)
        w = unit(u + lean * n)                      # the wall leans outward: a scarp, not a saw cut
        r = R * rng.uniform(0.75, 1.2)
        q = p + u * r
        planes.append((w, float(w @ q)))
    Vp = polytope_vertices(planes)
    if len(Vp) < 4:
        return None
    return hull_mesh(Vp)


def flakes(V, F, rng, count, R=(0.06, 0.2), depth=(0.008, 0.03), zmin=0.05, nz_min=-0.45, jitter_deg=10.0,
           lean=0.45, weights=None):
    P, N, _ = sample_surface(V, F, count, rng, zmin=zmin, nz_min=nz_min, weights=weights)
    out = []
    Rs = np.exp(rng.uniform(math.log(R[0]), math.log(R[1]), count))     # log-uniform: many small, few large
    for p, n, r in zip(P, N, Rs):
        nn = jitter(n, jitter_deg, rng)
        d = rng.uniform(*depth) * (0.6 + 0.4 * r / R[1])
        c = flake_cutter(p, nn, r, d, rng, lean=lean)
        if c is not None:
            out.append(c)
    return out


# ----------------------------------------------------------------------------------------------- cracks + chips
def crack_wedge(path, m, depth, mouth_w, tip_w=0.002, out=0.05):
    """A crack along a surface polyline ``path`` as convex wedges, one per segment; the crack plane contains the
    segment and the inward direction -``m``; ``mouth_w`` / ``depth`` scalars or per point (taper at the ends)."""
    path = np.asarray(path, float)
    m = unit(m)
    W = np.broadcast_to(np.asarray(mouth_w, float), (len(path),))
    Dp = np.broadcast_to(np.asarray(depth, float), (len(path),))
    parts = []
    for k in range(len(path) - 1):
        A, B = path[k], path[k + 1]
        t = unit(B - A)
        mm = unit(m - t * float(t @ m))
        nn = unit(np.cross(t, mm))
        pts = []
        for P, wk, dk in ((A, W[k], Dp[k]), (B, W[k + 1], Dp[k + 1])):
            wo = wk * 0.5 * (1.0 + out / max(dk, 1e-3))
            pts += [P + mm * out + nn * wo, P + mm * out - nn * wo,
                    P - mm * dk + nn * tip_w * 0.5, P - mm * dk - nn * tip_w * 0.5]
        parts.append(hull_mesh(np.array(pts)))
    return parts


def project_path(bvh, pts2d, face, wander, rng, step=0.03):
    """Key points on a face (``front``: (x, z) seen from -y; ``back``: from +y; ``left``/``right``: (y, z) from -x /
    +x; ``top``: (x, y) from +z) densified to ``step`` with a small lateral wander and ray-cast onto the surface.
    Returns (points, outward direction)."""
    key = np.asarray(pts2d, float)
    seg = np.linalg.norm(np.diff(key, axis=0), axis=1)
    s_ = np.concatenate([[0], np.cumsum(seg)])
    n = max(4, int(s_[-1] / step) + 1)
    ss = np.linspace(0, s_[-1], n)
    p2 = np.stack([np.interp(ss, s_, key[:, 0]), np.interp(ss, s_, key[:, 1])], 1)
    tang = np.gradient(p2, axis=0)
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    wv = np.cumsum(rng.normal(0, wander, n))
    wv -= np.linspace(wv[0], wv[-1], n)
    p2 = p2 + nrm * wv[:, None]
    from mathutils import Vector
    cfg = {"front": ((0, 2), 1, -1.0), "back": ((0, 2), 1, 1.0), "left": ((1, 2), 0, -1.0),
           "right": ((1, 2), 0, 1.0), "top": ((0, 1), 2, 1.0)}
    (a0, a1), a2, sgn = cfg[face]
    out = []
    for u, v in p2:
        o = [0.0, 0.0, 0.0]
        o[a0], o[a1], o[a2] = float(u), float(v), sgn * 10.0
        d = [0.0, 0.0, 0.0]
        d[a2] = -sgn
        hit = bvh.ray_cast(Vector(o), Vector(d), 30.0)
        if hit[0] is not None:
            out.append(np.array(hit[0][:]))
    m = np.zeros(3)
    m[a2] = sgn
    return np.array(out), m


def corner_chip(V_block, rng, depth_share=(0.06, 0.16), up_bias=0.15, margin=0.06):
    """A fresh-fracture chip off one upper corner of a block (points ``V_block``): a half-space cutter boxed to the
    corner region."""
    cen = V_block.mean(0)
    zlo, zhi = V_block[:, 2].min(), V_block[:, 2].max()
    up = V_block[V_block[:, 2] > zlo + 0.3 * (zhi - zlo)]
    if not len(up):
        return None
    p = up[rng.integers(len(up))]
    n = jitter(unit(p - cen + np.array([0, 0, up_bias])), 18.0, rng)
    s = V_block @ n
    d = float(s.max() - rng.uniform(*depth_share) * (s.max() - s.min()))
    beyond = V_block[s > d - 0.03]
    return halfspace_box(n, d, beyond.min(0) - margin, beyond.max(0) + margin)


# ----------------------------------------------------------------------------------------------- cliff blocks
def _plane_through(n, p):
    n = unit(n)
    return (n, float(n @ np.asarray(p, float)))


def cliff_cells(spec, rng):
    """Columnar joint-set cells for a cliff chunk (study 3.9: 2-3 joint families; the sheet's chunks are columns
    split by vertical joints, each column with its own bed joints, so bed joints never run across the whole face).

    spec: bbox (lo, hi); x_splits / y_splits (the vertical joint families, global, each plane tilted by up to
    ``jit`` deg); beds: list of (z_lo, z_hi) ranges, one bed joint drawn per range per column (dipping by up to
    ``dip_deg``), skipped when it would leave a block under ``min_block`` m tall.
    Returns (cells, joints): cells [{"planes", "ix", "iy", "level", "top", "nx", "ny", "V", "zb"}], joints
    {"x": [plane], "y": [plane], "beds": {ix: [plane]}}."""
    lo = np.asarray(spec["bbox"][0], float)
    hi = np.asarray(spec["bbox"][1], float)
    box = []
    for k in range(3):
        e = np.zeros(3)
        e[k] = 1.0
        box += [(e, float(hi[k])), (-e, float(-lo[k]))]
    jit = spec.get("jit", 6.0)
    xs, ys = list(spec["x_splits"]), list(spec.get("y_splits", []))
    xpl = [_plane_through(jitter(np.array([1.0, 0.0, 0.0]), jit, rng) * np.array([1.0, 1.0, 0.35]), (x, 0.0, 0.0))
           for x in xs]
    ypl = [_plane_through(jitter(np.array([0.0, 1.0, 0.0]), jit, rng) * np.array([1.0, 1.0, 0.35]), (0.0, y, 0.0))
           for y in ys]
    dip = spec.get("dip_deg", 4.0)
    mb = spec.get("min_block", 0.45)
    top_z = float(spec["top_z"])
    beds = {}
    for ix in range(len(xs) + 1):
        zb, last = [], 0.0
        for zlo, zhi in spec["beds"]:
            z = rng.uniform(zlo, zhi)
            if z - last < mb or top_z - z < mb:
                continue
            zb.append(z)
            last = z
        beds[ix] = [_plane_through(jitter(np.array([0.0, 0.0, 1.0]), dip, rng), (0.0, 0.0, z)) for z in zb]
    cells = []
    for ix in range(len(xs) + 1):
        pls = beds[ix]
        for lev in range(len(pls) + 1):
            for iy in range(len(ys) + 1):
                pl = list(box)
                if lev > 0:
                    n, d = pls[lev - 1]
                    pl.append((-n, -d))
                if lev < len(pls):
                    n, d = pls[lev]
                    pl.append((n, d))
                if ix > 0:
                    n, d = xpl[ix - 1]
                    pl.append((-n, -d))
                if ix < len(xs):
                    n, d = xpl[ix]
                    pl.append((n, d))
                if iy > 0:
                    n, d = ypl[iy - 1]
                    pl.append((-n, -d))
                if iy < len(ys):
                    n, d = ypl[iy]
                    pl.append((n, d))
                Vc = polytope_vertices(pl)
                if len(Vc) >= 4:
                    cells.append({"planes": pl, "ix": ix, "iy": iy, "level": lev, "top": lev == len(pls),
                                  "nx": len(xs), "ny": len(ys), "V": Vc,
                                  "zb": float(pls[lev - 1][1]) if lev > 0 else float(lo[2])})
    return cells, {"x": xpl, "y": ypl, "beds": beds}


def cell_of(P, cells, tol=0.0):
    """Index of the cell containing each point (-1 if none)."""
    out = -np.ones(len(P), np.int64)
    for k, c in enumerate(cells):
        inside = (plane_sdf_np(P, c["planes"]) <= tol) & (out < 0)
        out[inside] = k
    return out


def plane_sdf_np(P, planes):
    n = np.array([p[0] for p in planes])
    d = np.array([p[1] for p in planes])
    return (np.asarray(P, float) @ n.T - d).max(1)
