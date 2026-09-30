"""Planting rock for a rock-grown tree: a visual hull of the traced front and side outlines, chunky granite
facets, a crack for the trunk and root guides projected onto the surface (numpy only).

Study 4.2 / 8.7: the rock is part of the asset (a third mesh with its own hulls), sharing the tree's origin at the
rock's ground-contact centre, sunk 0.1-0.2 m below grade. Outlines are traced from the sheet (the 2D outline
authority); only the depth-wise shape between the two traced views is inferred.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


def icosphere(level: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    V = [np.array(v, dtype=np.float64) / np.linalg.norm(v) for v in V]
    for _ in range(level):
        cache: Dict[Tuple[int, int], int] = {}
        nf = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = V[a] + V[b]
                V.append(m / np.linalg.norm(m))
                cache[key] = len(V) - 1
            return cache[key]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = nf
    return np.array(V), np.array(F, dtype=np.int64)


def point_in_poly(px: np.ndarray, py: np.ndarray, poly: np.ndarray) -> np.ndarray:
    inside = np.zeros(px.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > py) != (y2 > py))
        xint = (x2 - x1) * (py - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1
        inside ^= cond & (px < xint)
    return inside


def visual_hull(front: np.ndarray, side: np.ndarray, level: int = 5, rounding: float = 0.35) -> Tuple[np.ndarray, np.ndarray]:
    """front: (n,2) polygon in (x, z); side: (m,2) polygon in (y, z). Star-shaped hull from a centre inside both.

    ``rounding`` < 1 pulls the corners in (the product of two extrusions is boxy; a boulder is rounder)."""
    D, F = icosphere(level)
    zc = 0.45 * (front[:, 1].min() + front[:, 1].max())
    c = np.array([0.5 * (front[:, 0].min() + front[:, 0].max()), 0.5 * (side[:, 0].min() + side[:, 0].max()), zc])
    tmax = 4.0 * max(np.ptp(front[:, 0]), np.ptp(side[:, 0]), np.ptp(front[:, 1]))
    lo = np.zeros(len(D))
    hi = np.full(len(D), tmax)
    for _ in range(40):
        t = 0.5 * (lo + hi)
        P = c + D * t[:, None]
        ok = point_in_poly(P[:, 0], P[:, 2], front) & point_in_poly(P[:, 1], P[:, 2], side)
        lo = np.where(ok, t, lo)
        hi = np.where(ok, hi, t)
    t = lo
    # soften the box corners of the two-view intersection: blend toward an ellipsoid of the same extents
    ext = np.array([np.ptp(front[:, 0]) / 2, np.ptp(side[:, 0]) / 2, np.ptp(front[:, 1]) / 2])
    ell = 1.0 / np.sqrt(((D / ext) ** 2).sum(1))
    t = np.minimum(t, rounding * t + (1 - rounding) * ell)
    P = c + D * t[:, None]
    # round it in plan: depth shrinks toward the left/right edge of the FRONT outline at each height, so the front
    # silhouette stays exactly as traced while the boulder stops reading as two crossed extrusions
    zs = np.linspace(front[:, 1].min(), front[:, 1].max(), 64)
    hw = []
    for z in zs:
        xs = np.linspace(front[:, 0].min() - 0.01, front[:, 0].max() + 0.01, 400)
        ins = point_in_poly(xs, np.full_like(xs, z), front)
        hw.append((xs[ins].min(), xs[ins].max()) if ins.any() else (c[0], c[0]))
    hw = np.array(hw)
    lo_x = np.interp(P[:, 2], zs, hw[:, 0])
    hi_x = np.interp(P[:, 2], zs, hw[:, 1])
    mid = 0.5 * (lo_x + hi_x)
    half = np.maximum(0.5 * (hi_x - lo_x), 1e-3)
    xn = np.clip(np.abs(P[:, 0] - mid) / half, 0, 1)
    f = np.sqrt(np.clip(1.0 - xn ** 2, 0.0, 1.0)) ** 0.5 * 0.75 + 0.25
    P[:, 1] = c[1] + (P[:, 1] - c[1]) * f
    return P, F


def facet(V: np.ndarray, rng: np.random.Generator, n_facets: int = 60, strength: float = 0.75,
          centre: np.ndarray = None) -> np.ndarray:
    """Chunky granite facets: each vertex moves toward the plane of its nearest facet seed (crisp ridges where
    cells meet)."""
    seeds = V[rng.choice(len(V), n_facets, replace=False)]
    c = V.mean(0) if centre is None else centre
    normals = seeds - c
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    normals += rng.normal(0, 0.25, normals.shape)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    d2 = ((V[:, None, :] - seeds[None, :, :]) ** 2).sum(-1)
    near = d2.argmin(1)
    n = normals[near]
    s = seeds[near]
    dist = ((V - s) * n).sum(1)
    out = V - (strength * dist)[:, None] * n
    return out


def crack(V: np.ndarray, point: np.ndarray, normal: np.ndarray, width: float, depth: float, top_z: float,
          reach: float) -> np.ndarray:
    """A V-groove along the plane through ``point`` with ``normal``, deepest at the top, fading ``reach`` below."""
    normal = normal / np.linalg.norm(normal)
    d = (V - point) @ normal
    w = np.clip(1.0 - np.abs(d) / width, 0.0, 1.0) ** 1.5
    fade = np.clip((V[:, 2] - (top_z - reach)) / reach, 0.0, 1.0)
    c = V.mean(0)
    inward = c - V
    inward[:, 2] *= 0.3
    inward /= np.maximum(np.linalg.norm(inward, axis=1, keepdims=True), 1e-9)
    return V + inward * (depth * w * fade)[:, None]


def faceted_mass_points(P: np.ndarray, rng: np.random.Generator, n_chips: int = 16,
                        depth: Tuple[float, float] = (0.03, 0.12), up_bias: float = 0.35,
                        avoid: Optional[List[np.ndarray]] = None) -> np.ndarray:
    """Chip a point cloud with random planes (f1 boulder). Every point beyond a plane is projected onto it, so the
    convex hull of the result has big, crisp planar facets (judge r0: 'faceted, angular', not a smooth drum).
    ``depth`` is the cut depth as a share of the cloud's extent along the plane normal."""
    P = np.asarray(P, float).copy()
    c = P.mean(0)
    for _ in range(n_chips):
        for _try in range(20):
            n = rng.normal(0, 1, 3)
            n[2] = abs(n[2]) * up_bias + n[2] * (1 - up_bias)
            n /= np.linalg.norm(n)
            # never chip the faces that meet another mass (they must stay fused) or the buried bottom
            if n[2] > -0.5 and not any(float(n @ a) > 0.35 for a in (avoid or [])):
                break
        proj = (P - c) @ n
        hmax, hmin = proj.max(), proj.min()
        cut = hmax - rng.uniform(*depth) * (hmax - hmin)
        over = proj > cut
        P[over] -= ((proj[over] - cut)[:, None]) * n[None, :]
    return P


def split_masses(P: np.ndarray, planes: List[Tuple[np.ndarray, np.ndarray]], overlap: float = 0.06) -> List[np.ndarray]:
    """Split a point cloud into masses by a list of (point, normal) planes applied in sequence: plane k splits the
    LARGEST current mass in two. Each side keeps the points up to ``overlap`` m past the plane, so the convex masses
    interpenetrate (no see-through slit) and meet in a concave crease."""
    masses = [(np.asarray(P, float), [])]
    for (q, n) in planes:
        n = np.asarray(n, float) / np.linalg.norm(n)
        k = int(np.argmax([len(m[0]) for m in masses]))
        M, av = masses.pop(k)
        d = (M - np.asarray(q, float)) @ n
        a, b = M[d < overlap], M[d > -overlap]
        if len(a) >= 12:
            masses.append((a, av + [n]))        # mass a lies on the -n side: its fused face points along +n
        if len(b) >= 12:
            masses.append((b, av + [-n]))
    return masses


def flatten_bottom(V: np.ndarray, z_floor: float) -> np.ndarray:
    V = V.copy()
    V[:, 2] = np.maximum(V[:, 2], z_floor)
    return V


def vertex_normals(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def project_front(V: np.ndarray, N: np.ndarray, x: float, z: float, side: str = "front", tol: float = 0.06) -> Tuple[np.ndarray, np.ndarray]:
    """Surface point seen at (x, z) from the front (min y) or back (max y): the extreme vertex in a small window."""
    m = (np.abs(V[:, 0] - x) < tol) & (np.abs(V[:, 2] - z) < tol)
    grow = tol
    while m.sum() < 3 and grow < 0.5:
        grow *= 1.6
        m = (np.abs(V[:, 0] - x) < grow) & (np.abs(V[:, 2] - z) < grow)
    idx = np.nonzero(m)[0]
    if len(idx) == 0:
        j = int(np.argmin((V[:, 0] - x) ** 2 + (V[:, 2] - z) ** 2))
        return V[j], N[j]
    j = idx[np.argmin(V[idx, 1])] if side == "front" else idx[np.argmax(V[idx, 1])]
    return V[j], N[j]


def root_on_rock(V: np.ndarray, N: np.ndarray, guide_xz: List[Tuple[float, float]], radius: float,
                 side: str = "front", lift: float = 0.55) -> np.ndarray:
    """3D polyline hugging the rock: each guide (x, z) projected to the surface, lifted by ``lift`` x radius."""
    out = []
    for i, (x, z) in enumerate(guide_xz):
        p, n = project_front(V, N, x, z, side)
        r = radius * (1.0 - 0.8 * i / max(1, len(guide_xz) - 1))
        out.append(p + n * r * lift)
    return np.array(out)
