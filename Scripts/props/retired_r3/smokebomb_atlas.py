#!/usr/bin/env python
"""props_lib.smokebomb_atlas - where every piece of tape lives in the 2048 texture.

numpy only.  An ISLAND is one piece of one strip (``smokebomb_mesh.Piece``) keyed by
(strip, sub-chart, component).  Its UV is its own chart - s along the tape, w across it -
scaled to the atlas' px/mm and translated, never rotated or mirrored:

    px = x0 + (s - s0) * ppmm          (u = px / size)
    py = y0 + (w1 - w) * ppmm          (v = 1 - py / size;  +w is +v)

so u runs along the warp at every texel of every island (the weave never aliases across
a diagonal) and MikkTSpace's tangent is the tape's own direction.  One px/mm for the whole
atlas: every island has the same texel density, and a buyer's decal lands at true scale.

Placement is decided ONCE, on LOD0's islands (padded), and every LOD samples the same
placement, so the three LODs read the same texel for the same point of tape.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

#: study 7: 2048 maps, 16 px padding at 2K (ASSET_GUIDELINES 4)
ATLAS_PX = 2048
PAD_PX = 16
#: chart margin added round every island before packing (mm): room for LOD1 / LOD2
#: boundaries, which sit within their simplification tolerance of LOD0's
ISLAND_MARGIN_MM = 0.6


@dataclass
class Island:
    key: Tuple[int, int, int]
    s0: float
    s1: float
    w0: float
    w1: float
    x0: int = 0
    y0: int = 0

    @property
    def size_mm(self):
        return self.s1 - self.s0, self.w1 - self.w0


@dataclass
class AtlasPlan:
    size: int
    ppmm: float
    pad: int
    islands: Dict[Tuple[int, int, int], Island]
    packing: float = 0.0

    def to_px(self, key, chart_uv: np.ndarray) -> np.ndarray:
        isl = self.islands[key]
        c = np.asarray(chart_uv, np.float64)
        px = isl.x0 + (c[:, 0] - isl.s0) * self.ppmm
        py = isl.y0 + (isl.w1 - c[:, 1]) * self.ppmm
        return np.stack([px, py], axis=1)

    def uv(self, key, chart_uv: np.ndarray) -> np.ndarray:
        p = self.to_px(key, chart_uv)
        return np.stack([p[:, 0] / self.size, 1.0 - p[:, 1] / self.size], axis=1)

    def block(self, key):
        """(x0, y0, w, h) of the island's texel block, padding included."""
        isl = self.islands[key]
        w = int(math.ceil((isl.s1 - isl.s0) * self.ppmm))
        h = int(math.ceil((isl.w1 - isl.w0) * self.ppmm))
        return isl.x0 - self.pad, isl.y0 - self.pad, w + 2 * self.pad, h + 2 * self.pad

    def describe(self) -> dict:
        return {"size_px": self.size, "px_per_mm": round(self.ppmm, 4),
                "px_per_cm": round(self.ppmm * 10.0, 3), "padding_px": self.pad,
                "islands": len(self.islands), "packing_fraction": round(self.packing, 4)}


def piece_key(p) -> Tuple[int, int, int]:
    return (int(p.strip), int(p.sub), int(getattr(p, "comp", 0)))


def _try_pack(sizes: List[Tuple[int, int]], size: int, pad: int):
    """Shelf packing, tallest first.  sizes are (w, h) in px WITHOUT padding."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    pos = [None] * len(sizes)
    x = y = 0
    shelf_h = 0
    for i in order:
        w, h = sizes[i]
        W, H = w + 2 * pad, h + 2 * pad
        if W > size:
            return None
        if x + W > size:
            y += shelf_h
            x = 0
            shelf_h = 0
        if y + H > size:
            return None
        pos[i] = (x + pad, y + pad)
        x += W
        shelf_h = max(shelf_h, H)
    return pos


def plan(pieces, size: int = ATLAS_PX, pad: int = PAD_PX, max_ppmm: float = 16.0) -> AtlasPlan:
    """Pack LOD0's pieces at the largest px/mm that fits."""
    keys = []
    boxes = []
    for p in pieces:
        k = piece_key(p)
        s0, s1, w0, w1 = p.bbox_mm
        m = ISLAND_MARGIN_MM
        keys.append(k)
        boxes.append((s0 - m, s1 + m, w0 - m, w1 + m))
    lo, hi = 4.0, max_ppmm
    best = None
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        sizes = [(int(math.ceil((b[1] - b[0]) * mid)), int(math.ceil((b[3] - b[2]) * mid))) for b in boxes]
        pos = _try_pack(sizes, size, pad)
        if pos is None:
            hi = mid
        else:
            lo = mid
            best = (mid, pos, sizes)
    if best is None:
        raise RuntimeError("the pieces do not fit the atlas at 4 px/mm")
    ppmm, pos, sizes = best
    islands = {}
    used = 0
    for k, b, (x, y), (w, h) in zip(keys, boxes, pos, sizes):
        islands[k] = Island(k, b[0], b[1], b[2], b[3], x, y)
        used += w * h
    return AtlasPlan(size, ppmm, pad, islands, packing=used / float(size * size))


__all__ = ["ATLAS_PX", "PAD_PX", "ISLAND_MARGIN_MM", "Island", "AtlasPlan", "piece_key", "plan"]


def lookup(atlas: AtlasPlan, strip: int, s: float, w: float):
    """The LOD0 island of ``strip`` that holds chart point (s, w), or the nearest one.
    Returns (key, (s0, s1, w0, w1))."""
    best = None
    for key, isl in atlas.islands.items():
        if key[0] != strip:
            continue
        ds = max(isl.s0 - s, 0.0, s - isl.s1)
        dw = max(isl.w0 - w, 0.0, w - isl.w1)
        d = ds * ds + dw * dw
        if best is None or d < best[0]:
            best = (d, key, (isl.s0, isl.s1, isl.w0, isl.w1))
            if d == 0.0:
                break
    if best is None:
        raise KeyError(f"no island for strip {strip}")
    return best[1], best[2]


__all__ += ["lookup"]
