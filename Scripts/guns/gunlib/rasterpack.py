"""Shape-aware atlas packer on an occupancy grid (numpy only).

Why not Blender's pack_islands: on the AR-01 sets it reached 36-48 % fill (the gun study gates are 70 / 65 %); its
concave mode barely nests big islands. Here every island is rasterised at the trial scale onto a coarse grid (cells of
`cell_px` texels; conservative coverage: a cell is taken when any triangle reaches within half a cell diagonal of its
centre), its taken cells dilated by the margin; islands go in largest first at the lowest free spot where their own
bounding window is empty (summed-area table: one vectorised window sum per island and rotation). Islands are marked
by their SHAPE, so later small islands fill the concave space of earlier big ones. The scale is the largest that
places every island (bisection). Rotations: 0 and 90 degrees (axis-aligned, never mirrored).

Coordinates: island UVs in any unit; the result maps them to texels / atlas UV (0..1) with one 2x3 affine per island.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np


def _raster(T, h, w):
    """Conservative raster of triangles T (n, 3, 2) in cell units (origin at the island's min corner) -> (h, w)."""
    M = np.zeros((h, w), bool)
    r = 0.7072
    for tri in T:
        lo = np.floor(tri.min(0) - r).astype(int)
        hi = np.ceil(tri.max(0) + r).astype(int)
        x0, y0 = max(lo[0], 0), max(lo[1], 0)
        x1, y1 = min(hi[0], w), min(hi[1], h)
        if x1 <= x0 or y1 <= y0:
            continue
        xs = np.arange(x0, x1) + 0.5
        ys = np.arange(y0, y1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        ok = np.ones(X.shape, bool)
        a = tri
        area = (a[1, 0] - a[0, 0]) * (a[2, 1] - a[0, 1]) - (a[2, 0] - a[0, 0]) * (a[1, 1] - a[0, 1])
        sg = 1.0 if area >= 0 else -1.0
        for k in range(3):
            p, q = a[k], a[(k + 1) % 3]
            e = q - p
            L = math.hypot(e[0], e[1])
            if L < 1e-12:
                continue
            d = sg * ((X - p[0]) * e[1] - (Y - p[1]) * e[0]) / L     # > 0 = outside for CCW
            ok &= d <= r
        M[y0:y1, x0:x1] |= ok
    return M


def _dilate(M, d):
    if d <= 0:
        return M
    h, w = M.shape
    out = np.zeros((h + 2 * d, w + 2 * d), bool)
    for dy in range(-d, d + 1):
        for dx in range(-d, d + 1):
            if dx * dx + dy * dy <= d * d + d:
                out[d + dy:d + dy + h, d + dx:d + dx + w] |= M
    return out


def _rot90(T, H):
    """Rotate island coordinates 90 deg CCW inside its box: (x, y) -> (H - y, x)."""
    return np.stack([H - T[..., 1], T[..., 0]], -1)


def _try(islands, scale, size, cell, d, rotate=True):
    G = size // cell
    occ = np.zeros((G, G), bool)
    S = np.zeros((G + 1, G + 1), np.int32)
    r_free = 0                                  # rows below this are full
    place = {}
    for i in islands["order"]:
        T0 = islands["tris"][i]
        lo = islands["lo"][i]
        Tc = (T0 - lo) * scale / cell                    # cell units, origin at the min corner
        W, H = islands["ext"][i] * scale / cell
        best = None
        for rot in ((0, 1) if rotate else (0,)):
            w, h = (W, H) if rot == 0 else (H, W)
            wi, hi = int(math.ceil(w + 1e-9)), int(math.ceil(h + 1e-9))
            if wi > G or hi > G or r_free + hi > G:
                continue
            Sb = S[r_free:]
            win = Sb[hi:, wi:] - Sb[:-hi, wi:] - Sb[hi:, :-wi] + Sb[:-hi, :-wi]
            ok = win == 0
            rows = np.flatnonzero(ok.any(1))
            if not len(rows):
                continue
            y = int(rows[0]) + r_free
            x = int(np.argmax(ok[rows[0]]))
            sc = (y + hi, x)
            if best is None or sc < best[0]:
                best = (sc, rot, x, y, wi, hi)
        if best is None:
            return None
        _, rot, x, y, wi, hi = best
        T = Tc if rot == 0 else _rot90(Tc, H)
        M = _dilate(_raster(T, hi, wi), d)
        y0, x0 = y - d, x - d
        ys0, xs0 = max(y0, 0), max(x0, 0)
        ys1, xs1 = min(y0 + M.shape[0], G), min(x0 + M.shape[1], G)
        occ[ys0:ys1, xs0:xs1] |= M[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
        S[ys0 + 1:, 1:] = S[ys0:ys0 + 1, 1:] + np.cumsum(np.cumsum(occ[ys0:], 0, dtype=np.int32), 1, dtype=np.int32)
        while r_free < G and occ[r_free].all():
            r_free += 1
        place[i] = (rot, x, y)
    return place


def pack(tris: Sequence[np.ndarray], size: int, gap_px: int, cell_px: int = 4, rotate=True, iters=9,
         scale_hi=None, refine=0) -> Dict:
    """tris: per island (n, 3, 2) coordinates (any unit). Returns {'scale' (texels per unit), 'affine' [2x3 per island,
    unit -> atlas UV 0..1], 'fill' (triangle area / atlas), 'placements'}."""
    tris = [np.asarray(t, float) for t in tris]
    lo = np.array([t.reshape(-1, 2).min(0) for t in tris])
    hi = np.array([t.reshape(-1, 2).max(0) for t in tris])
    ext = np.maximum(hi - lo, 1e-9)
    area = np.array([0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                                  - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1])).sum() for t in tris])
    order = np.lexsort((-area, -np.max(ext, axis=1)))      # longest side first, then area
    isl = {"tris": tris, "lo": lo, "ext": ext, "order": order}
    d = int(math.ceil(gap_px / cell_px))
    s_hi = math.sqrt(size * size / max(area.sum(), 1e-12))
    if scale_hi:
        scale_hi = min(scale_hi, s_hi)
        s_hi = scale_hi
    s_lo = s_hi * 0.3
    best = None
    while best is None:
        best = _try(isl, s_lo, size, cell_px, d, rotate)
        if best is None:
            s_lo *= 0.7
    best_s = s_lo
    if scale_hi:
        # a capped scale (texel density ceiling): take the cap itself when it fits
        r = _try(isl, s_hi, size, cell_px, d, rotate)
        if r is not None:
            best, best_s, iters = r, s_hi, 0
    s_top = s_hi
    for _ in range(iters):
        s = math.sqrt(s_lo * s_hi)
        r = _try(isl, s, size, cell_px, d, rotate)
        if r is None:
            s_hi = s
        else:
            s_lo, best, best_s = s, r, s
    if refine and best_s < s_top * 0.999:
        # greedy packing is not monotonic in the scale (a slightly larger scale often packs where the bisection's probe
        # failed), and the island order matters: walk down from the top scale in 1.5 % steps with two orders (longest
        # side first; largest area first) and keep the first that fits above the bisection's result
        orders = [order, np.lexsort((-np.max(ext, axis=1), -area))]
        s = s_top
        for _ in range(int(refine)):
            if s <= best_s * 1.001:
                break
            hit = None
            for od in orders:
                r = _try(dict(isl, order=od), s, size, cell_px, d, rotate)
                if r is not None:
                    hit = r
                    break
            if hit is not None:
                best, best_s = hit, s
                break
            s *= 0.985
    aff = []
    for i in range(len(tris)):
        rot, x, y = best[i]
        s = best_s
        W, H = ext[i] * s
        ox, oy = x * cell_px, y * cell_px
        if rot == 0:
            A = np.array([[s, 0.0, ox - lo[i, 0] * s], [0.0, s, oy - lo[i, 1] * s]])
        else:
            # (u, v) -> local (x, y) = ((u - lo) s); rotated: (H - y, x)
            A = np.array([[0.0, -s, ox + H + lo[i, 1] * s], [s, 0.0, oy - lo[i, 0] * s]])
        aff.append(A / size)
    return {"scale": best_s, "affine": aff, "fill": float(area.sum() * best_s * best_s / (size * size)),
            "placements": best, "gap_px": d * cell_px, "cell_px": cell_px}
