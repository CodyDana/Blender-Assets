#!/usr/bin/env python
"""props_lib.atlas - front / back / rim island packing for a printed sheet.

The whole point of this module is that the UV is not solved, it is CHOSEN, and chosen so
that the artwork's own raster and the atlas are the same pixel grid.  That makes the
transfer from art to texture a 1:1 blit at an integer offset rather than a resample, and
it makes the LODs' UVs agree exactly instead of to within a projection tolerance.

THE GRID
--------
One number decides everything: ``ppmm``, the study's 12.923 px/mm, which is the hard
ceiling for a 156 mm side on a 2048 map once 16 px of padding is taken off each end
(156 x 12.923 = 2016, + 2 x 16 = 2048).  The art module is then asked for a raster with
``pad_mm = 16 / ppmm``, so its padding is EXACTLY 16 px and its card origin lands exactly
on the island's card origin.

    front island   card (0,0) at atlas px (16, 16)            u 0.0078 .. 0.4495
    back island    card (0,0) at atlas px (953, 16)           u 0.4653 .. 0.9070
    rim            three vertical strips in the last 174 px   u 0.9268 .. 0.9668

The study wrote the back island at u 0.458 and the rim from 0.905.  Placing the back
raster immediately after the front raster instead (col 937, not 922) is the same island
one pixel further right: at 0.458 the two rasters' PADDING would have overlapped by 15 px,
so the front's bake margin and the back's would have written over each other.  The islands
themselves are exactly the study's size and density.

THE RIM
-------
The rim develops to about 434 x 0.15 mm.  At true density that is a strip 1.94 px wide,
which is a fragile island - mip 1 already merges it with whatever is beside it.  It does
not matter, and that is the point: the edge of a torn card IS paper colour, so when the
mips blur the rim into its padding they blur it into more paper.  The strips are laid at
true density, 40 px apart so nothing bleeds between them, and the rim's content is a slow
vertical gradient of edge-paper colour, which makes every LOD's slightly different
strip-boundary arc length invisible.

A rim quad must not straddle a strip boundary or its UV jumps across the gap, so the
strip is chosen ONCE per quad from its start arc length (``rim_strip_index``) and both its
ends are mapped inside that strip.  The last quad of a strip overshoots a little into the
16 px of padding below it, which is what that padding is for.

ORIENTATION
-----------
Every array in this module has ROW 0 = the TOP of the tag, which is how
``paperbomb_art`` draws and how a PNG stores its first row.  UV V is measured down from
1.0, so ``v = 1 - (row + 0.5) / size``.  Blender's ``image.pixels`` is bottom-up and is
flipped on the way in and out; that happens in ``props_lib.bake``, never here.

THE BACK IS MIRRORED ON THE WAY IN
----------------------------------
``paperbomb_art.build_back`` authors the back in the frame you see when you TURN THE CARD
OVER, so its show-through ghost is already mirrored in u.  The mesh's back faces carry the
same monotone u -> U mapping as the front (a mirrored UV island would flip the tangent
handedness for no gain), so the back raster is mirrored once here, on the way into the
atlas.  The result is the physically right one: the back at paper ``(u, v)`` shows the
front's ink at the same ``(u, v)``, because that is the paper the light went through.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Sequence, Tuple

import numpy as np

ATLAS = 2048
PAD_PX = 16
#: gap between rim strips, px - far more than the 16 px bake margin needs
RIM_STRIP_PITCH = 40
RIM_STRIPS = 3


@dataclass(frozen=True)
class AtlasPlan:
    """Where everything sits, in atlas pixels and in UV."""

    size: int
    ppmm: float
    pad_px: int
    card_w_mm: float
    card_h_mm: float
    thickness_mm: float

    @property
    def pad_mm(self) -> float:
        """The padding to ask the art module for, so its raster is OUR pixel grid."""
        return self.pad_px / self.ppmm

    @property
    def raster(self) -> Tuple[int, int]:
        """(width, height) of one art raster, padding included."""
        w = int(round((self.card_w_mm + 2 * self.pad_mm) * self.ppmm))
        h = int(round((self.card_h_mm + 2 * self.pad_mm) * self.ppmm))
        return w, h

    @property
    def front_origin(self) -> Tuple[int, int]:
        """Atlas pixel of card (0, 0) on the front island: (col, row)."""
        return (self.pad_px, self.pad_px)

    @property
    def back_origin(self) -> Tuple[int, int]:
        return (self.raster[0] + self.pad_px, self.pad_px)

    @property
    def rim_x0(self) -> int:
        return 2 * self.raster[0]

    @property
    def card_px(self) -> Tuple[float, float]:
        return (self.card_w_mm * self.ppmm, self.card_h_mm * self.ppmm)

    # ---- UV --------------------------------------------------------------

    def uv_front(self, u_mm: float, v_mm: float) -> Tuple[float, float]:
        ox, oy = self.front_origin
        return ((ox + u_mm * self.ppmm) / self.size,
                1.0 - (oy + v_mm * self.ppmm) / self.size)

    def uv_back(self, u_mm: float, v_mm: float) -> Tuple[float, float]:
        ox, oy = self.back_origin
        return ((ox + u_mm * self.ppmm) / self.size,
                1.0 - (oy + v_mm * self.ppmm) / self.size)

    def rim_strip_index(self, s_mm: float, perimeter_mm: float) -> int:
        f = 0.0 if perimeter_mm <= 0 else s_mm / perimeter_mm
        return int(min(RIM_STRIPS - 1, max(0, math.floor(f * RIM_STRIPS))))

    def rim_strip_x(self, strip: int) -> float:
        """Centre column of a rim strip."""
        return self.rim_x0 + 24.0 + strip * RIM_STRIP_PITCH

    def uv_rim(self, s_mm: float, t: float, s0_mm: float, s1_mm: float,
               strip: int) -> Tuple[float, float]:
        """One rim UV.  ``t`` is 0 at the back face and 1 at the front.

        ``s0_mm`` and ``s1_mm`` are the arc lengths of the strip's OWN first and last
        ring vertex, not a third of the perimeter: a strip boundary has to land on a
        real vertex or the last quad of each strip runs off the bottom of the map
        (measured: LOD2's 20 mm quads overshot to V = -0.13).  Each LOD therefore lays
        its own third of the rim across the full island height, at a slightly different
        px/mm - which is invisible, because the rim's content is a slow vertical
        gradient of edge-paper colour with no registration to anything.
        """
        half = self.thickness_mm * self.ppmm * 0.5
        cx = self.rim_strip_x(strip)
        x = cx + (t - 0.5) * 2.0 * half
        span = max(s1_mm - s0_mm, 1e-9)
        g = min(max((s_mm - s0_mm) / span, 0.0), 1.0)
        rows = self.card_h_mm * self.ppmm              # 2016 px, the island's own height
        y = self.pad_px + g * rows
        return (x / self.size, 1.0 - y / self.size)

    # ---- description -----------------------------------------------------

    def describe(self) -> Dict[str, object]:
        rw, rh = self.raster
        cw, ch = self.card_px
        fx, fy = self.front_origin
        bx, _by = self.back_origin
        return {
            "size": self.size,
            "ppmm": self.ppmm,
            "texel_density_px_per_cm": round(self.ppmm * 10.0, 3),
            "pad_px": self.pad_px,
            "pad_mm": round(self.pad_mm, 6),
            "art_raster_px": [rw, rh],
            "card_px": [round(cw, 2), round(ch, 2)],
            "front_island_u": [round(fx / self.size, 6), round((fx + cw) / self.size, 6)],
            "front_island_v": [round(1.0 - (fy + ch) / self.size, 6),
                               round(1.0 - fy / self.size, 6)],
            "back_island_u": [round(bx / self.size, 6), round((bx + cw) / self.size, 6)],
            "rim_region_px": [self.rim_x0, self.size],
            "rim_strips": RIM_STRIPS,
            "rim_strip_width_px": round(self.thickness_mm * self.ppmm, 3),
            "rim_strip_centres_px": [self.rim_strip_x(k) for k in range(RIM_STRIPS)],
            "packing_efficiency": round(2 * cw * ch / (self.size * self.size), 4),
            "back_island_note": ("the study's 0.458 would have overlapped the front raster's "
                                 "padding by 15 px; the island is the same size and density"),
        }


def plan_for(spec) -> AtlasPlan:
    return AtlasPlan(size=spec.texture_size, ppmm=spec.ppmm, pad_px=PAD_PX,
                     card_w_mm=spec.width_mm, card_h_mm=spec.height_mm,
                     thickness_mm=spec.thickness_mm)


# ===========================================================================
# Compositing
# ===========================================================================

def _blit(dst: np.ndarray, src: np.ndarray, col: int, row: int = 0) -> None:
    h, w = src.shape[:2]
    dst[row:row + h, col:col + w] = src


def compose(plan: AtlasPlan, front: np.ndarray, back: np.ndarray,
            rim_fill, mirror_back: bool = True) -> np.ndarray:
    """One atlas channel-set from the two art rasters and a rim filler.

    ``front`` and ``back`` are ``(H, W)`` or ``(H, W, C)`` arrays at the plan's raster
    size, row 0 at the top.  ``rim_fill`` is a value, or a callable ``(rows, cols) ->
    array``, used for the whole rim region so the strips and their padding agree.
    """
    rw, rh = plan.raster
    if front.shape[0] != rh or front.shape[1] != rw:
        raise ValueError(f"front raster is {front.shape[:2]}, the plan wants {(rh, rw)}")
    if back.shape[:2] != front.shape[:2]:
        raise ValueError("front and back rasters differ in size")
    chan = front.shape[2] if front.ndim == 3 else 1
    shape = (plan.size, plan.size) + ((chan,) if front.ndim == 3 else ())
    out = np.zeros(shape, np.float32)

    _blit(out, front.astype(np.float32), 0)
    b = back.astype(np.float32)
    if mirror_back:
        b = np.ascontiguousarray(b[:, ::-1])
    _blit(out, b, rw)

    x0 = plan.rim_x0
    cols = plan.size - x0
    if callable(rim_fill):
        patch = rim_fill(plan.size, cols)
    else:
        patch = np.zeros((plan.size, cols) + ((chan,) if front.ndim == 3 else ()), np.float32)
        patch[...] = rim_fill
    out[:, x0:] = patch
    # the rasters are 937 px wide and the islands 905, so rows above and below the card
    # already carry the art module's own edge-extended padding: nothing else to fill.
    return out


def tangent_normal(height_mm: np.ndarray, ppmm: float) -> np.ndarray:
    """Height in mm (row 0 at the top) -> a DirectX tangent-space normal, 0..1 RGB.

    UV U runs with paper ``u``, UV V runs against paper ``v`` (row 0 is V = 1).  So

        n = normalize(-dh/du, -dh/dv, 1)

    is the DIRECTX encoding: green low where the surface tips toward the top of the image.
    Blender's own normal-map node wants OpenGL, so the gallery material flips G back;
    Unreal wants what is written here and imports it with Flip Green OFF.
    """
    h = np.asarray(height_mm, np.float64)
    # central differences in millimetres
    du = np.gradient(h, axis=1) * ppmm
    dv = np.gradient(h, axis=0) * ppmm
    nx = -du
    ny = -dv
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([nx * inv, ny * inv, nz * inv], axis=-1)
    return np.clip(rgb * 0.5 + 0.5, 0.0, 1.0).astype(np.float32)


def rim_gradient(paper_edge_rgb, paper_rgb, size: int, cols: int, seed: int = 20260919):
    """The rim's content: worn edge paper, slowly varying, with a little fibre in it."""
    rng = np.random.default_rng([int(seed), 0x81DE])
    t = np.linspace(0.0, 1.0, size)[:, None]
    ctrl = rng.uniform(0.0, 1.0, 9)
    tt = t[:, 0] * (len(ctrl) - 1)
    j = np.clip(np.floor(tt).astype(int), 0, len(ctrl) - 2)
    f = tt - j
    f = f * f * (3.0 - 2.0 * f)
    mix = (ctrl[j] * (1 - f) + ctrl[j + 1] * f)[:, None]
    edge = np.asarray(paper_edge_rgb, np.float32)[None, None, :]
    body = np.asarray(paper_rgb, np.float32)[None, None, :]
    col = edge * (1.0 - mix[..., None] * 0.55) + body * (mix[..., None] * 0.55)
    return np.repeat(col, cols, axis=1).astype(np.float32)


__all__ = ["ATLAS", "PAD_PX", "RIM_STRIPS", "AtlasPlan", "plan_for", "compose",
           "tangent_normal", "rim_gradient"]


if __name__ == "__main__":                                   # pragma: no cover
    import json
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from props_lib.spec import PAPER_BOMB
    print(json.dumps(plan_for(PAPER_BOMB).describe(), indent=2))
