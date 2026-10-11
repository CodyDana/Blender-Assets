"""Lightmap chart packer for the SMG01 UV1 (numpy only): gunlib.rasterpack's occupancy-grid method with the two
changes a lightmap padding gate needs (UD4: conservative raster at the lightmap resolution, 2 px padding):

- each chart's conservative raster is NOT clipped to its bounding window (a triangle on the window's edge reaches up to
  half a texel diagonal past it; rasterpack clips there, which is right for its texture atlases' gutters but leaves a
  lightmap chart one texel wider than its footprint);
- the padding ring is a square (Chebyshev) dilation, so two charts end at least `gap` empty texels apart in every
  direction, diagonals included.

Same interface as gunlib.rasterpack.pack (cell = 1 texel): returns {'scale', 'affine' (unit -> 0..1), 'fill'}.
"""
from __future__ import annotations

import math
from typing import Dict, Sequence

import numpy as np

R_CONS = 0.7072


def _raster(T, h, w, off):
    """Conservative raster of triangles T (cell units, origin at the island's min corner) into an (h + 2 off) x
    (w + 2 off) window whose origin is off cells before the min corner."""
    H, W = h + 2 * off, w + 2 * off
    M = np.zeros((H, W), bool)
    for tri in T + off:
        lo = np.floor(tri.min(0) - R_CONS).astype(int)
        hi = np.ceil(tri.max(0) + R_CONS).astype(int)
        x0, y0, x1, y1 = max(lo[0], 0), max(lo[1], 0), min(hi[0], W), min(hi[1], H)
        if x1 <= x0 or y1 <= y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        a = tri
        ar = (a[1, 0] - a[0, 0]) * (a[2, 1] - a[0, 1]) - (a[2, 0] - a[0, 0]) * (a[1, 1] - a[0, 1])
        sg = 1.0 if ar >= 0 else -1.0
        ok = np.ones(X.shape, bool)
        for k in range(3):
            p, q = a[k], a[(k + 1) % 3]
            e = q - p
            L = math.hypot(e[0], e[1])
            if L < 1e-12:
                continue
            ok &= sg * ((X - p[0]) * e[1] - (Y - p[1]) * e[0]) / L <= R_CONS
        M[y0:y1, x0:x1] |= ok
    return M


def _square_dilate(M, d):
    h, w = M.shape
    out = np.zeros((h + 2 * d, w + 2 * d), bool)
    for dy in range(-d, d + 1):
        for dx in range(-d, d + 1):
            out[d + dy:d + dy + h, d + dx:d + dx + w] |= M
    return out


def _rot90(T, H):
    return np.stack([H - T[..., 1], T[..., 0]], -1)


def _try(isl, scale, G, gap, rotate=True):
    occ = np.zeros((G, G), bool)         # raw texels of placed charts dilated by the ring
    place = {}
    off = 1
    for i in isl["order"]:
        Tc = (isl["tris"][i] - isl["lo"][i]) * scale
        W, H = isl["ext"][i] * scale
        best = None
        for rot in ((0, 1) if rotate else (0,)):
            T = Tc if rot == 0 else _rot90(Tc, H)
            w, h = (W, H) if rot == 0 else (H, W)
            wi, hi = int(math.ceil(w + 1e-9)), int(math.ceil(h + 1e-9))
            M = _raster(T, hi, wi, off)                       # (hi + 2, wi + 2), origin at (-1, -1)
            mh, mw = M.shape
            if mh > G or mw > G:
                continue
            # placements (y, x) of the raster window's origin with no raw texel on an occupied (ringed) texel
            ys, xs = np.nonzero(M)
            free = np.ones((G - mh + 1, G - mw + 1), bool)
            for y, x in zip(ys, xs):
                free &= ~occ[y:y + G - mh + 1, x:x + G - mw + 1]
                if not free.any():
                    break
            cand = np.argwhere(free)
            if not len(cand):
                continue
            y, x = cand[np.lexsort((cand[:, 1], cand[:, 0] + mh))[0]]
            sc = (int(y) + mh, int(x))
            if best is None or sc < best[0]:
                best = (sc, rot, int(x), int(y), M)
        if best is None:
            return None
        _, rot, x, y, M = best
        D = _square_dilate(M, gap)
        y0, x0 = y - gap, x - gap
        ys0, xs0 = max(y0, 0), max(x0, 0)
        ys1, xs1 = min(y0 + D.shape[0], G), min(x0 + D.shape[1], G)
        occ[ys0:ys1, xs0:xs1] |= D[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
        place[i] = (rot, x + off, y + off)                  # the island's min corner in texels
    return place


def pack(tris: Sequence[np.ndarray], size: int, gap: int, iters=14) -> Dict:
    tris = [np.asarray(t, float) for t in tris]
    lo = np.array([t.reshape(-1, 2).min(0) for t in tris])
    hi = np.array([t.reshape(-1, 2).max(0) for t in tris])
    ext = np.maximum(hi - lo, 1e-9)
    area = np.array([0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                                  - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1])).sum() for t in tris])
    order = np.lexsort((-area, -np.max(ext, axis=1)))
    isl = {"tris": tris, "lo": lo, "ext": ext, "order": order}
    s_hi = math.sqrt(size * size / max(area.sum(), 1e-12))
    s_lo = s_hi * 0.2
    best = None
    for _ in range(12):
        best = _try(isl, s_lo, size, gap)
        if best is not None:
            break
        s_lo *= 0.7
    if best is None:
        raise RuntimeError("lightmap charts do not fit at any tried scale")
    best_s = s_lo
    for _ in range(iters):
        s = math.sqrt(s_lo * s_hi)
        r = _try(isl, s, size, gap)
        if r is None:
            s_hi = s
        else:
            s_lo, best, best_s = s, r, s
    aff = []
    for i in range(len(tris)):
        rot, x, y = best[i]
        s = best_s
        H = ext[i, 1] * s
        if rot == 0:
            A = np.array([[s, 0.0, x - lo[i, 0] * s], [0.0, s, y - lo[i, 1] * s]])
        else:
            A = np.array([[0.0, -s, x + H + lo[i, 1] * s], [s, 0.0, y - lo[i, 0] * s]])
        aff.append(A / size)
    return {"scale": best_s, "affine": aff, "fill": float(area.sum() * best_s * best_s / (size * size))}
