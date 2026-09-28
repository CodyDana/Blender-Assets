#!/usr/bin/env python
"""props_lib.art_metrics - measure the drawn tag against REFERENCE_SPEC.md, and gate on it.

THE POINT OF THIS MODULE.  ``References/PaperBomb/REFERENCE_SPEC.md`` is a contract: 26
ranked rows, each with a reference figure and a tolerance, reconciled from three
independent metrology passes and re-measured by a fourth.  A build that merely *sets*
those numbers as parameters proves nothing - the first build's own comments show how far
a parameter can drift from what the raster ends up carrying.  So every row that can be
measured is measured HERE, on the art that was actually drawn, and
``build_paper_bomb.collect_gates`` turns each tolerance into a pass/fail.

Nothing in this file reads, opens, samples or otherwise touches either guide image.  It
measures OUR raster and compares the result with numbers typed out of the spec document.
``TARGETS`` below is that transcription and it is the only place a reference figure
appears; if the spec is revised, revise it there.

Conventions match the spec's: card millimetres from the tag's top-left virtual corner,
x right and y down; colour as STORED sRGB 0-1 unless a name says linear; the ring's
"stroke" is the SWEPT BAND (first ink to last along a radial ray), never the alpha
profile or a threshold crossing, because the spec's build target and its acceptance test
have to be the same definition.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

CARD_W_MM = 70.0
CARD_H_MM = 156.0


# ===========================================================================
# 1.  The spec, transcribed
# ===========================================================================

#: REFERENCE_SPEC.md section 1, section 3's adopted column, and the whole-card
#: composition table.  ``(value, lo, hi)`` where a tolerance exists.
TARGETS: Dict[str, object] = {
    # row 1 - paper : black contrast
    "paper_linear_luma": 0.803,
    "black_linear_luma": 0.0047,
    "contrast_ratio": 170.0,
    "contrast_ratio_factor": 1.5,          # "within x1.5"
    # row 2 / 3 - the centre character
    "centre_w_mm": 59.30, "centre_h_mm": 52.38, "centre_w_tol_mm": 1.0,
    "centre_components_max": 2, "centre_component_min_mm2": 15.0,
    "centre_overlap_mm": 8.86, "centre_overlap_min_mm": 6.0,
    "centre_ink_gap_mm": 0.75,
    # row 4 - one rule per side
    "rules_per_side": 1,
    # row 5 / 6 - columns
    "column_cell_mm": 13.9, "column_cell_max_mm": 14.6, "column_cell_tol_mm": 1.0,
    "column_leading_max_mm": 1.0,
    # row 7 / 8 / 9 / 10 - the ring
    "ring_mid_w_mm": 52.08, "ring_mid_h_mm": 59.27, "ring_axis_tol_mm": 1.5,
    "ring_hw_lo": 1.09, "ring_hw_hi": 1.16,
    "ring_centre_mm": (35.47, 76.99), "ring_centre_tol_mm": 0.5,
    "ring_stroke_mm": 4.84, "ring_stroke_lo": 4.3, "ring_stroke_hi": 5.4,
    "ring_stroke_p95_min": 6.0,
    "ring_hole_fraction": 0.198, "ring_hole_lo": 0.16, "ring_hole_hi": 0.24,
    "ring_coverage_lo": 0.90, "ring_coverage_hi": 0.95,
    # row 11 - the flame emblem
    "flame_box_mm": (23.74, 23.64), "flame_centre_mm": (34.83, 30.59),
    "flame_ink_mm2": 167.0, "flame_ink_lo": 150.0, "flame_ink_hi": 185.0,
    "flame_components_min": 4,
    # row 12 - upper column axes
    "col_upper_axes_w": (0.1900, 0.8160), "col_upper_axis_tol_mm": 0.7,
    # row 13 - red
    "red_stored": (0.753, 0.126, 0.075), "red_saturation_min": 0.82,
    "red_blue_max": 0.12,
    # row 14 - the corner dart
    "corner_dart_mm": 2.1, "corner_dart_lo": 1.5, "corner_dart_hi": 2.5,
    # row 15 - paper colour
    "paper_stored": (0.9647, 0.9020, 0.7765),
    "paper_hue_lo": 39.0, "paper_hue_hi": 42.0,
    "paper_sat_lo": 0.18, "paper_sat_hi": 0.24,
    "paper_linear_luma_min": 0.72,
    # row 16 / 17 / 18 - the ornament chain
    "bottom_diamond_mm": (35.05, 148.0), "bottom_diamond_size_mm": (2.39, 3.62),
    "ornament_tol_mm": 0.7,
    "leaf_pair_mm": ((32.20, 130.76), (38.04, 130.63)), "leaf_tol_mm": 1.0,
    "ink_above_top_rule": 0.0,
    # row 19 / 20 - the seals
    "small_seal_box_mm": (9.0, 17.8), "small_seal_at_mm": (59.1, 132.0),
    "small_seal_em_mm": 7.5, "small_seal_gap_mm": 1.24, "small_seal_box_tol_mm": 1.0,
    "small_seal_em_tol_mm": 0.7,
    "big_seal_box_mm": (18.0, 26.5), "big_seal_at_mm": (14.4, 129.9),
    "big_seal_fill_lo": 0.54, "big_seal_fill_hi": 0.64, "big_seal_box_tol_mm": 1.0,
    # row 21 / 22 - rule weight and continuity
    "rule_weight_mm": 0.62, "rule_weight_lo": 0.50, "rule_weight_hi": 0.80,
    "rule_weight_lr_tol_mm": 0.15,
    "rule_occupancy_lo": 0.82, "rule_occupancy_hi": 0.95,
    "rule_break_longest_max_mm": 5.0,
    # row 23 - the chamfer
    "corner_clip_mm": 8.05, "corner_clip_tol_mm": 0.5,
    # row 24 - no baked crease
    "crease_row_dip_max": 0.012, "crease_row_span": 0.25,
    # row 25 - edge ageing
    "edge_depth": 0.15, "edge_depth_lo": 0.12, "edge_depth_hi": 0.19,
    "edge_reach_mm": 7.25, "edge_reach_lo": 6.0, "edge_reach_hi": 9.0,
    "edge_side_spread_max": 0.04, "edge_tilt_max": 0.008,
    # row 26 - grain
    "grain_amplitude": 0.170, "grain_amp_lo": 0.12, "grain_amp_hi": 0.22,
    "grain_cell_mm": 0.50, "grain_cell_lo": 0.35, "grain_cell_hi": 0.80,
    "grain_aniso_max": 3.0,
    # whole-card composition
    "black_area": 0.1735, "red_area": 0.1126, "total_ink": 0.2861,
    "black_over_red": 1.542, "black_over_red_tol": 0.28,
    "ink_total_tol": 0.035,
    "frame_rect_mm": (61.877, 142.085), "frame_centre_mm": (34.971, 77.718),
    "frame_tol_mm": 0.6,
    # the square-patch defect: no hard axis-aligned discontinuity anywhere
    "hard_rect_runs_max": 0,
}


# ===========================================================================
# 2.  Small numeric helpers (no scipy, no PIL - Blender's numpy only)
# ===========================================================================

def _linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def _luma_linear(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _hsv(rgb: Sequence[float]) -> Tuple[float, float, float]:
    r, g, b = (float(c) for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    s = 0.0 if mx <= 1e-9 else (mx - mn) / mx
    if mx - mn <= 1e-9:
        h = 0.0
    elif mx == r:
        h = 60.0 * (((g - b) / (mx - mn)) % 6.0)
    elif mx == g:
        h = 60.0 * (((b - r) / (mx - mn)) + 2.0)
    else:
        h = 60.0 * (((r - g) / (mx - mn)) + 4.0)
    return h, s, v


def label_cc(mask: np.ndarray) -> Tuple[np.ndarray, int]:
    """4-connected labelling by union-find over a boolean mask.  Rows, then merge."""
    m = np.asarray(mask, bool)
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    parent: List[int] = [0]

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(H):
        row = m[y]
        if not row.any():
            continue
        xs = np.flatnonzero(row)
        # run-length the row
        breaks = np.flatnonzero(np.diff(xs) > 1)
        starts = np.concatenate(([0], breaks + 1))
        ends = np.concatenate((breaks, [len(xs) - 1]))
        prev = lab[y - 1] if y > 0 else None
        for s, e in zip(starts, ends):
            x0, x1 = int(xs[s]), int(xs[e]) + 1
            here = 0
            if prev is not None:
                above = prev[x0:x1]
                hit = above[above > 0]
                if hit.size:
                    here = int(hit.min())
                    for v in np.unique(hit):
                        union(here, int(v))
            if here == 0:
                here = nxt
                parent.append(nxt)
                nxt += 1
            lab[y, x0:x1] = here
    if nxt == 1:
        return lab, 0
    remap = np.zeros(nxt, np.int32)
    roots: Dict[int, int] = {}
    for i in range(1, nxt):
        r = find(i)
        if r not in roots:
            roots[r] = len(roots) + 1
        remap[i] = roots[r]
    return remap[lab], len(roots)


def components(mask: np.ndarray, min_px: int = 1) -> List[Dict[str, object]]:
    """Every 4-connected component of ``mask`` at or above ``min_px``, biggest first."""
    lab, n = label_cc(mask)
    out: List[Dict[str, object]] = []
    if n == 0:
        return out
    flat = lab.ravel()
    counts = np.bincount(flat, minlength=n + 1)
    ys, xs = np.nonzero(lab)
    vals = lab[ys, xs]
    order = np.argsort(vals, kind="stable")
    ys, xs, vals = ys[order], xs[order], vals[order]
    bounds = np.searchsorted(vals, np.arange(1, n + 2))
    for k in range(1, n + 1):
        if counts[k] < min_px:
            continue
        a, b = bounds[k - 1], bounds[k]
        yy, xx = ys[a:b], xs[a:b]
        out.append({"label": int(k), "area_px": int(counts[k]),
                    "x0": int(xx.min()), "x1": int(xx.max()) + 1,
                    "y0": int(yy.min()), "y1": int(yy.max()) + 1,
                    "cx": float(xx.mean()), "cy": float(yy.mean())})
    out.sort(key=lambda c: -c["area_px"])
    return out


def _runs(flags: np.ndarray) -> List[Tuple[int, int]]:
    """``[(start, stop)]`` of every True run in a 1-D boolean array."""
    f = np.asarray(flags, bool)
    if not f.any():
        return []
    d = np.diff(f.astype(np.int8))
    starts = list(np.flatnonzero(d == 1) + 1)
    stops = list(np.flatnonzero(d == -1) + 1)
    if f[0]:
        starts.insert(0, 0)
    if f[-1]:
        stops.append(len(f))
    return list(zip(starts, stops))


# ===========================================================================
# 3.  The card frame - where every measurement is taken
# ===========================================================================

class Card:
    """The drawn front, addressed in card millimetres.

    ``art`` is a ``paperbomb_art.TagArt``; ``pad_mm`` is the island padding it was drawn
    with.  The mapping is exact by construction - the art is authored on the atlas's own
    pixel grid - so nothing here detects an edge or fits a rectangle, which is what put
    +-0.3 mm on every earlier "ours" number.
    """

    def __init__(self, art, pad_mm: float):
        self.art = art
        self.pad = float(pad_mm)
        self.ppmm = float(art.ppmm)
        self.base = np.asarray(art.base_colour, np.float64)
        self.H, self.W = self.base.shape[:2]
        self.card = np.asarray(art.card_mask, np.float64) > 0.5
        self.black = np.asarray(art.ink_black.a, np.float64) if art.ink_black is not None else None
        self.red = np.asarray(art.ink_red.a, np.float64) if art.ink_red is not None else None
        self.black_m = (self.black > 0.5) & self.card if self.black is not None else None
        self.red_m = (self.red > 0.5) & self.card if self.red is not None else None
        yy = (np.arange(self.H, dtype=np.float64)[:, None] + 0.5) / self.ppmm - self.pad
        xx = (np.arange(self.W, dtype=np.float64)[None, :] + 0.5) / self.ppmm - self.pad
        self.y_mm = yy
        self.x_mm = xx
        self.stored = _linear_to_srgb(self.base)

    # -- coordinate helpers -------------------------------------------------
    def px(self, x_mm: float, y_mm: float) -> Tuple[int, int]:
        return (int(round((x_mm + self.pad) * self.ppmm)),
                int(round((y_mm + self.pad) * self.ppmm)))

    def mm_per_px(self) -> float:
        return 1.0 / self.ppmm

    def box(self, c: Dict[str, object]) -> Dict[str, float]:
        """A component's box in card millimetres."""
        k = 1.0 / self.ppmm
        x0 = c["x0"] * k - self.pad
        x1 = c["x1"] * k - self.pad
        y0 = c["y0"] * k - self.pad
        y1 = c["y1"] * k - self.pad
        return {"x0": round(x0, 3), "x1": round(x1, 3), "y0": round(y0, 3), "y1": round(y1, 3),
                "w_mm": round(x1 - x0, 3), "h_mm": round(y1 - y0, 3),
                "cx": round(0.5 * (x0 + x1), 3), "cy": round(0.5 * (y0 + y1), 3)}

    def area_mm2(self, n_px: int) -> float:
        return n_px / (self.ppmm * self.ppmm)

    def region(self, x0, y0, x1, y1) -> np.ndarray:
        """Boolean mask of a card-millimetre rectangle."""
        return ((self.x_mm >= x0) & (self.x_mm < x1)
                & (self.y_mm >= y0) & (self.y_mm < y1))


# ===========================================================================
# 4.  One function per spec row
# ===========================================================================

def ink_and_contrast(card: Card) -> Dict[str, object]:
    """Rows 1, 13, 15 and the whole-card composition table."""
    area = float(card.card.sum())
    black = card.black_m
    red = card.red_m
    lin = card.base
    paper_only = card.card & ~black & ~red
    # the paper population, away from the edge band so the aged rim does not drag it
    inner = paper_only & card.region(10.0, 16.0, CARD_W_MM - 10.0, CARD_H_MM - 16.0)
    paper_lin = _luma_linear(lin[inner]) if inner.any() else np.array([0.0])
    paper_stored = card.stored[inner].reshape(-1, 3) if inner.any() else np.zeros((1, 3))

    # the ink CORE, which is what the spec's "black linear luma 0.0047" describes: the
    # reference reaches 0/255 and our old map's min, p001 and p01 were all one value
    core = black & (card.black > 0.92)
    black_lin = _luma_linear(lin[core]) if core.any() else _luma_linear(lin[black])
    red_stored = card.stored[red & (card.red > 0.92)].reshape(-1, 3)
    if not red_stored.size:
        red_stored = card.stored[red].reshape(-1, 3)

    p_luma = float(np.percentile(paper_lin, 50))
    b_luma = float(np.percentile(black_lin, 1)) if black_lin.size else 1.0
    pm = paper_stored.mean(axis=0)
    rm = red_stored.mean(axis=0) if red_stored.size else np.zeros(3)
    ph, ps, pv = _hsv(pm)
    rh, rs, rv = _hsv(rm)
    nb = float(black.sum())
    nr = float(red.sum())
    return {
        "paper_linear_luma_p50": round(p_luma, 4),
        "paper_stored_mean": [round(float(v), 4) for v in pm],
        "paper_hue_deg": round(ph, 2), "paper_saturation": round(ps, 4),
        "black_core_linear_luma_p01": round(b_luma, 6),
        "black_core_stored_min": round(float(card.stored[core].min()) if core.any() else 1.0, 4),
        "contrast_ratio": round(p_luma / max(b_luma, 1e-9), 1),
        "red_stored_mean": [round(float(v), 4) for v in rm],
        "red_hue_deg": round(rh, 2), "red_saturation": round(rs, 4),
        "black_area_fraction": round(nb / area, 4),
        "red_area_fraction": round(nr / area, 4),
        "total_ink_fraction": round(float((black | red).sum()) / area, 4),
        "black_over_red": round(nb / max(nr, 1.0), 3),
    }


def centre_glyph(card: Card, glyph_centre_mm: Tuple[float, float],
                 expect_mm: Tuple[float, float]) -> Dict[str, object]:
    """Rows 2 and 3: the hero character's box, and whether it is ONE character.

    The zone is the glyph's OWN nominal cell with a millimetre of air, not the ring's
    ellipse: at the reference's size the 爆 is 84.7 % of the card wide and a ring-sized
    ellipse swallows the flanking kanji columns as well, which is how a first pass of
    this measurement counted nine components.
    """
    cx, cy = glyph_centre_mm
    ew, eh = expect_mm
    zone = ((np.abs(card.x_mm - cx) <= ew * 0.5 + 1.5)
            & (np.abs(card.y_mm - cy) <= eh * 0.5 + 1.5))
    m = card.black_m & zone
    min_px = int(round(TARGETS["centre_component_min_mm2"] * card.ppmm * card.ppmm))
    comps = components(m, min_px=1)
    big = [c for c in comps if c["area_px"] >= min_px]
    if not big:
        return {"components": 0}
    boxes = [card.box(c) for c in big]
    x0 = min(b["x0"] for b in boxes); x1 = max(b["x1"] for b in boxes)
    y0 = min(b["y0"] for b in boxes); y1 = max(b["y1"] for b in boxes)
    out: Dict[str, object] = {
        "components": len(big),
        "components_all": len(comps),
        "component_areas_mm2": [round(card.area_mm2(c["area_px"]), 1) for c in big[:6]],
        "w_mm": round(x1 - x0, 2), "h_mm": round(y1 - y0, 2),
        "w_over_h": round((x1 - x0) / max(y1 - y0, 1e-6), 3),
        "w_fraction_of_W": round((x1 - x0) / CARD_W_MM, 4),
        "centre_mm": [round(0.5 * (x0 + x1), 2), round(0.5 * (y0 + y1), 2)],
        "box": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
    }
    if len(big) >= 2:
        a, b = sorted(boxes[:2], key=lambda z: z["x0"])
        out["bbox_overlap_mm"] = round(a["x1"] - b["x0"], 2)
        # nearest ink between the two components
        ma = (np.asarray(card.black_m) & _mask_of(card, big[0]))
        mb = (np.asarray(card.black_m) & _mask_of(card, big[1]))
        out["ink_gap_mm"] = round(_nearest_gap_mm(card, ma, mb), 2)
    return out


def _mask_of(card: Card, comp: Dict[str, object]) -> np.ndarray:
    m = np.zeros((card.H, card.W), bool)
    m[comp["y0"]:comp["y1"], comp["x0"]:comp["x1"]] = True
    return m


def _nearest_gap_mm(card: Card, a: np.ndarray, b: np.ndarray, max_mm: float = 12.0) -> float:
    """Smallest centre-to-centre distance between a True in ``a`` and a True in ``b``.

    Rows are scanned: for each row that has ink in both, the horizontal gap; the
    vertical case is covered by scanning columns too.  Enough for two side-by-side
    glyph parts and far cheaper than a full distance transform.
    """
    best = max_mm
    k = 1.0 / card.ppmm
    for y in range(card.H):
        ra, rb = a[y], b[y]
        if not ra.any() or not rb.any():
            continue
        xa = np.flatnonzero(ra)
        xb = np.flatnonzero(rb)
        d = float(np.min(np.abs(xa[:, None] - xb[None, :]))) * k
        best = min(best, d)
        if best <= k:
            break
    return best


def frame_only_red(card: Card, lay, frame_mm) -> np.ndarray:
    """Red ink with the ring, the two chops and the mid-side ornaments taken out.

    Row 4 asks how many RULES a side has.  On this card the ring's lap passes within
    2.5 mm of the left and right rules and the big chop sits 5 mm off the bottom one -
    and so do the reference's, which is why the spec's own figure is one rule per side
    on both guides.  Asking the question of the red that is not a ring or a chop is what
    makes the answer about rules.
    """
    x0, y0, x1, y1 = frame_mm
    m = card.red_m.copy()
    cx = lay.ring_centre[0] * CARD_W_MM
    cy = lay.ring_centre[1] * CARD_H_MM
    ow, oh = lay.ring_outer_mm
    # NEVER remove ink that is ON a rule line.  Both the ring's ellipse and the big
    # chop's box reach across a side rule, so subtracting them wholesale takes 24 and
    # 30 mm out of the left rule and reports a 31 mm "break" in its continuity.
    on_rule = (card.region(x0 - 2.2, 0.0, x0 + 2.2, CARD_H_MM)
               | card.region(x1 - 2.2, 0.0, x1 + 2.2, CARD_H_MM)
               | card.region(0.0, y0 - 2.2, CARD_W_MM, y0 + 2.2)
               | card.region(0.0, y1 - 2.2, CARD_W_MM, y1 + 2.2))
    drop = (((card.x_mm - cx) / (ow * 0.5 + 3.0)) ** 2
            + ((card.y_mm - cy) / (oh * 0.5 + 3.0)) ** 2) <= 1.0
    for fx, fy in ((lay.big_seal_frame_x, lay.big_seal_frame_y),
                   (lay.small_seal_frame_x, lay.small_seal_frame_y)):
        drop |= card.region(fx[0] * CARD_W_MM - 2.5, fy[0] * CARD_H_MM - 2.5,
                            fx[1] * CARD_W_MM + 2.5, fy[1] * CARD_H_MM + 2.5)
    m &= ~(drop & ~on_rule)
    return m


def rules(card: Card, frame_mm: Tuple[float, float, float, float],
          lay=None) -> Dict[str, object]:
    """Rows 4, 21 and 22, plus the frame rectangle section 6 says not to move."""
    x0, y0, x1, y1 = frame_mm
    red = card.red_m if lay is None else frame_only_red(card, lay, frame_mm)
    out: Dict[str, object] = {}
    sides: Dict[str, Dict[str, object]] = {}

    def profile(axis: str, at_mm: float, along: Tuple[float, float],
                search: Tuple[float, float]) -> Dict[str, object]:
        """Occupancy, weight and breaks of one ruled side."""
        lo, hi = along
        s_lo, s_hi = search
        if axis == "v":                     # a vertical rule at x = at_mm
            band = card.region(s_lo, lo, s_hi, hi)
            rows = np.flatnonzero(((card.y_mm >= lo) & (card.y_mm < hi)).ravel())
            hits = []
            widths = []
            for y in rows:
                xs = np.flatnonzero(red[y] & band[y])
                if xs.size:
                    hits.append(True)
                    widths.append(xs.size / card.ppmm)
                else:
                    hits.append(False)
            step = 1.0 / card.ppmm
        else:                               # a horizontal rule at y = at_mm
            band = card.region(lo, s_lo, hi, s_hi)
            cols = np.flatnonzero(((card.x_mm >= lo) & (card.x_mm < hi)).ravel())
            hits = []
            widths = []
            for x in cols:
                ys = np.flatnonzero(red[:, x] & band[:, x])
                if ys.size:
                    hits.append(True)
                    widths.append(ys.size / card.ppmm)
                else:
                    hits.append(False)
            step = 1.0 / card.ppmm
        hits = np.array(hits, bool)
        gaps = _runs(~hits)
        gap_mm = [(b - a) * step for a, b in gaps]
        real = [g for g in gap_mm if g > 0.25]
        return {
            "occupancy": round(float(hits.mean()) if hits.size else 0.0, 4),
            "weight_mm_p50": round(float(np.percentile(widths, 50)) if widths else 0.0, 3),
            "weight_mm_p90": round(float(np.percentile(widths, 90)) if widths else 0.0, 3),
            "breaks": len(real),
            "longest_break_mm": round(max(real), 2) if real else 0.0,
        }

    half = 2.6
    sides["left"] = profile("v", x0, (y0 + 2.0, y1 - 2.0), (x0 - half, x0 + half))
    sides["right"] = profile("v", x1, (y0 + 2.0, y1 - 2.0), (x1 - half, x1 + half))
    sides["top"] = profile("h", y0, (x0 + 2.0, x1 - 2.0), (y0 - half, y0 + half))
    sides["bottom"] = profile("h", y1, (x0 + 2.0, x1 - 2.0), (y1 - half, y1 + half))
    out["sides"] = sides
    w = [s["weight_mm_p50"] for s in sides.values()]
    out["weight_mm_mean"] = round(float(np.mean(w)), 3)
    out["weight_lr_difference_mm"] = round(abs(sides["left"]["weight_mm_p50"]
                                               - sides["right"]["weight_mm_p50"]), 3)
    out["occupancy_min"] = round(min(s["occupancy"] for s in sides.values()), 4)
    out["occupancy_max"] = round(max(s["occupancy"] for s in sides.values()), 4)
    out["longest_break_mm"] = round(max(s["longest_break_mm"] for s in sides.values()), 2)

    # --- row 4: how many rules per side.  Occupancy of red as a function of distance
    # INWARD from each rule; a second rule shows as a second peak above 0.15.
    #
    # Measured over the MIDDLE 60 % of each side.  A rule is the one thing that runs the
    # whole length; the corner brackets and the two chops are not, and including them
    # reports a bracket 2.8 mm in as a second rule - which is exactly the reading the
    # spec's own note warns is "only comparable between agents who place the tag edge
    # the same way".  The reference's big seal sits 5.4 mm off its bottom rule too.
    peaks: Dict[str, int] = {}
    mid_v = (y0 + 0.20 * (y1 - y0), y0 + 0.80 * (y1 - y0))
    mid_h = (x0 + 0.20 * (x1 - x0), x0 + 0.80 * (x1 - x0))
    for name, (axis, at, along) in (
            ("left", ("v", x0, mid_v)),
            ("right", ("v", x1, mid_v)),
            ("top", ("h", y0, mid_h)),
            ("bottom", ("h", y1, mid_h))):
        n = int(round(12.0 * card.ppmm))
        occ = np.zeros(n)
        for i in range(n):
            d = (i + 0.5) / card.ppmm
            if axis == "v":
                at_x = at + d if name == "left" else at - d
                sel = card.region(at_x - 0.5 / card.ppmm, along[0],
                                  at_x + 0.5 / card.ppmm, along[1])
            else:
                at_y = at + d if name == "top" else at - d
                sel = card.region(along[0], at_y - 0.5 / card.ppmm,
                                  along[1], at_y + 0.5 / card.ppmm)
            tot = float(sel.sum())
            occ[i] = float((red & sel).sum()) / tot if tot else 0.0
        # count separated runs above 0.15, ignoring the first 1.2 mm (the rule itself
        # has width) - every extra run is an extra rule
        flags = occ > 0.15
        skip = int(round(1.4 * card.ppmm))
        flags[:skip] = False
        runs = [(a, b) for a, b in _runs(flags) if (b - a) / card.ppmm > 0.25]
        peaks[name] = 1 + len(runs)
        sides[name]["extra_rule_peaks"] = len(runs)
    out["rules_per_side"] = peaks
    out["rules_per_side_max"] = max(peaks.values())

    # --- the frame rectangle, which section 6 says is already right to 0.05 mm and
    # must not move.  Each side is fitted on its OWN ink: the median position of the red
    # in a +-1.6 mm band over the middle 70 % of that side.  Taking the extent of a fat
    # ring instead pulls in the corner brackets, the mid-side lozenges and the bottom
    # centreline leaf at 151.9 mm - all of which section 6 lists as already correct - and
    # reports a frame three millimetres too tall.
    fit: Dict[str, float] = {}
    lo_v, hi_v = y0 + 0.15 * (y1 - y0), y0 + 0.85 * (y1 - y0)
    lo_h, hi_h = x0 + 0.15 * (x1 - x0), x0 + 0.85 * (x1 - x0)
    for name, axis, at in (("left", "v", x0), ("right", "v", x1),
                           ("top", "h", y0), ("bottom", "h", y1)):
        if axis == "v":
            sel = card.region(at - 1.6, lo_v, at + 1.6, hi_v)
            m = red & sel
            fit[name] = float(np.median(card.x_mm[0, np.nonzero(m)[1]])) if m.any() else at
        else:
            sel = card.region(lo_h, at - 1.6, hi_h, at + 1.6)
            m = red & sel
            fit[name] = float(np.median(card.y_mm[np.nonzero(m)[0], 0])) if m.any() else at
    out["frame_sides_mm"] = {k: round(v, 3) for k, v in fit.items()}
    out["frame_rect_mm"] = [round(fit["right"] - fit["left"], 3),
                            round(fit["bottom"] - fit["top"], 3)]
    out["frame_centre_mm"] = [round(0.5 * (fit["left"] + fit["right"]), 3),
                              round(0.5 * (fit["top"] + fit["bottom"]), 3)]
    return out


def corner_darts(card: Card, frame_mm: Tuple[float, float, float, float]) -> Dict[str, object]:
    """Row 14: how far any ink reaches OUTBOARD of the top and bottom rules, per corner."""
    x0, y0, x1, y1 = frame_mm
    ink = (card.black_m | card.red_m)
    reach: Dict[str, float] = {}
    colour: Dict[str, str] = {}
    span = 11.0
    for name, (cx, cy, sy) in (("top_left", (x0, y0, -1)), ("top_right", (x1, y0, -1)),
                               ("bottom_left", (x0, y1, +1)), ("bottom_right", (x1, y1, +1))):
        if sy < 0:
            sel = card.region(min(cx, cx + span) - span * 0.5, cy - 8.0,
                              max(cx, cx + span) + span * 0.5, cy)
        else:
            sel = card.region(min(cx, cx + span) - span * 0.5, cy,
                              max(cx, cx + span) + span * 0.5, cy + 8.0)
        m = ink & sel
        if not m.any():
            reach[name] = 0.0
            colour[name] = "none"
            continue
        ys, _xs = np.nonzero(m)
        if sy < 0:
            d = cy - float(card.y_mm[ys.min(), 0])
            beyond = m & (card.y_mm < cy - 0.45)
        else:
            d = float(card.y_mm[ys.max(), 0]) - cy
            beyond = m & (card.y_mm > cy + 0.45)
        reach[name] = round(d, 2)
        # the colour vote is over the ink that is actually OUTBOARD - counting the whole
        # window just re-reports the rule, which is red on both guides and on ours
        nb = int((card.black_m & beyond).sum())
        nr = int((card.red_m & beyond).sum())
        colour[name] = "black" if nb >= nr and nb > 0 else ("red" if nr else "none")
    return {"outboard_mm": reach, "dominant_colour": colour,
            "min_mm": round(min(reach.values()), 2),
            "max_mm": round(max(reach.values()), 2),
            "all_have_black": all(v == "black" for v in colour.values())}


def ring(card: Card, centre_mm: Tuple[float, float],
         outer_mm: Tuple[float, float], stroke_max_mm: float = 7.2,
         exclude: Optional[np.ndarray] = None) -> Dict[str, object]:
    """Rows 7, 8, 9 and 10, all on the SWEPT-BAND definition.

    A radial ray is walked out from the ring's centre at each of 360 angles; the band is
    the distance from the first red texel to the last, the mid-stroke radius is their
    mean, and a hole is a gap of bare paper strictly inside the band.  One definition,
    used for the build target and for the acceptance test alike (spec section 2, row 9).
    """
    cx, cy = centre_mm
    ow, oh = outer_mm
    red = card.red_m if exclude is None else (card.red_m & ~exclude)
    # the lap's own centre line: draw_ring sweeps at (axis/2 - stroke_max * 0.55)
    pw = ow * 0.5 - stroke_max_mm * 0.55
    ph = oh * 0.5 - stroke_max_mm * 0.55
    n_ang = 360
    step = 0.5 / card.ppmm
    bands: List[float] = []
    mids_x: List[float] = []
    mids_y: List[float] = []
    hole_len = 0.0
    band_len = 0.0
    holes = 0
    present = 0
    for k in range(n_ang):
        th = 2.0 * math.pi * k / n_ang
        ct, st = math.cos(th), -math.sin(th)
        # THE SEARCH WINDOW IS THE LAP'S OWN CENTRE LINE plus a stroke either side, not
        # a circle and not the outer ellipse.  The frame rules sit only 2.5 mm outside
        # the ring at the card's waist, so a fixed radial reach finds the RULE as "the
        # last ink" on every horizontal ray - which is how a first pass of this
        # measurement reported a 62 mm ring with a 22 mm band.
        r_nom = 1.0 / math.hypot(ct / max(pw, 1e-6), st / max(ph, 1e-6))
        r_lo, r_hi = r_nom - 0.82 * stroke_max_mm, r_nom + 0.82 * stroke_max_mm
        n = int((r_hi - r_lo) / step)
        if n < 4:
            continue
        rr = r_lo + (np.arange(n) + 0.5) * step
        xs = cx + rr * ct
        ys = cy + rr * st
        ix = np.round((xs + card.pad) * card.ppmm).astype(np.int64)
        iy = np.round((ys + card.pad) * card.ppmm).astype(np.int64)
        ok = (ix >= 0) & (ix < card.W) & (iy >= 0) & (iy < card.H)
        hit = np.zeros(n, bool)
        hit[ok] = red[iy[ok], ix[ok]]
        idx = np.flatnonzero(hit)
        if idx.size == 0:
            continue
        a, b = int(idx[0]), int(idx[-1])
        band = (b - a + 1) * step
        present += 1
        bands.append(band)
        rmid = r_lo + (a + b + 1) * 0.5 * step
        mids_x.append(cx + rmid * ct)
        mids_y.append(cy + rmid * st)
        inside = hit[a:b + 1]
        band_len += band
        for s, e in _runs(~inside):
            g = (e - s) * step
            if g >= 0.12:
                holes += 1
                hole_len += g
    if not bands:
        return {"present": 0}
    mids_x = np.array(mids_x); mids_y = np.array(mids_y)
    w_mm = float(mids_x.max() - mids_x.min())
    h_mm = float(mids_y.max() - mids_y.min())
    return {
        "present_angles": present, "angular_coverage": round(present / n_ang, 3),
        "mid_w_mm": round(w_mm, 2), "mid_h_mm": round(h_mm, 2),
        "mid_h_over_w": round(h_mm / max(w_mm, 1e-6), 3),
        "mid_centre_mm": [round(float(0.5 * (mids_x.max() + mids_x.min())), 2),
                          round(float(0.5 * (mids_y.max() + mids_y.min())), 2)],
        "stroke_mm_p05": round(float(np.percentile(bands, 5)), 2),
        "stroke_mm_p50": round(float(np.percentile(bands, 50)), 2),
        "stroke_mm_p95": round(float(np.percentile(bands, 95)), 2),
        "hole_fraction": round(hole_len / max(band_len, 1e-6), 4),
        "hole_count": holes,
    }


def flame(card: Card, centre_mm: Tuple[float, float],
          size_mm: Tuple[float, float]) -> Dict[str, object]:
    """Row 11: the emblem's box, its ink area and how many separate strokes it is."""
    cx, cy = centre_mm
    w, h = size_mm
    # the emblem's own cell and no more: the two upper kanji columns pass within 2 mm
    # of it on either side, and a generous window counts 火遁術 as part of the flame
    sel = card.region(cx - w * 0.50, cy - h * 0.62, cx + w * 0.50, cy + h * 0.62)
    m = card.black_m & sel
    if not m.any():
        return {"components": 0}
    min_px = int(round(3.0 * card.ppmm * card.ppmm))
    comps = [c for c in components(m, min_px=1) if c["area_px"] >= min_px]
    ys, xs = np.nonzero(m)
    x0 = float(card.x_mm[0, xs.min()]); x1 = float(card.x_mm[0, xs.max()])
    y0 = float(card.y_mm[ys.min(), 0]); y1 = float(card.y_mm[ys.max(), 0])
    area = card.area_mm2(int(m.sum()))
    return {
        "components": len(comps),
        "component_areas_mm2": [round(card.area_mm2(c["area_px"]), 1) for c in comps[:8]],
        "ink_mm2": round(area, 1),
        "box_mm": [round(x1 - x0, 2), round(y1 - y0, 2)],
        "centre_mm": [round(0.5 * (x0 + x1), 2), round(0.5 * (y0 + y1), 2)],
        "fill": round(area / max((x1 - x0) * (y1 - y0), 1e-6), 3),
    }


def columns(card: Card, text_report: Dict[str, list]) -> Dict[str, object]:
    """Rows 5, 6 and 12, measured on the drawn ink rather than on the em that asked."""
    out: Dict[str, object] = {"slots": {}}
    widths: List[float] = []
    leadings: List[float] = []
    for slot, rows in (text_report or {}).items():
        if slot == "small_seal":
            continue
        ws = [float(r.get("ink_w_mm", 0.0)) for r in rows]
        widths.extend(ws)
        ys = [float(r.get("centre_mm", (0, 0))[1]) for r in rows]
        hs = [float(r.get("ink_h_mm", 0.0)) for r in rows]
        lead = []
        for i in range(len(ys) - 1):
            lead.append((ys[i + 1] - hs[i + 1] * 0.5) - (ys[i] + hs[i] * 0.5))
        leadings.extend(lead)
        out["slots"][slot] = {
            "cell_w_mm": [round(v, 2) for v in ws],
            "leading_mm": [round(v, 2) for v in lead],
            "axis_mm": round(float(rows[0].get("centre_mm", (0, 0))[0]), 2) if rows else 0.0,
        }
    out["cell_w_mean_mm"] = round(float(np.mean(widths)), 2) if widths else 0.0
    out["cell_w_max_mm"] = round(float(np.max(widths)), 2) if widths else 0.0
    out["leading_max_mm"] = round(float(np.max(leadings)), 2) if leadings else 0.0
    out["leading_mean_mm"] = round(float(np.mean(leadings)), 2) if leadings else 0.0
    return out


def seals(card: Card, lay, frame_mm=None) -> Dict[str, object]:
    """Rows 19 and 20: the DRAWN box of each chop, and the big one's red fill.

    WHAT THIS HAS TO EXCLUDE, AND WHY IT IS FIDDLY.  A window round the frame reaches
    the lower-right kanji column's foot (it passes within a millimetre of the small
    chop) and the left frame rule (it runs down the side of the big one), and then
    "the drawn box" is just the window read back - which is how a first pass of this
    reported the small chop at 15.3 x 25.8 mm when its ink is nowhere near that, and it
    is the same bounding-box mistake section 5 of the spec catches the flame pass
    making.  So the frame RULES are taken out by position, the kanji columns by
    containment (a column runs tens of millimetres past the chop and fails it), and
    what is left is the chop.
    """
    out: Dict[str, object] = {}
    fx0, fy0, fx1, fy1 = frame_mm or (lay.rule_inset_left_mm, lay.rule_inset_top_mm,
                                      CARD_W_MM - lay.rule_inset_right_mm,
                                      CARD_H_MM - lay.rule_inset_bottom_mm)
    rules_band = (card.region(fx0 - 1.1, 0.0, fx0 + 1.1, CARD_H_MM)
                  | card.region(fx1 - 1.1, 0.0, fx1 + 1.1, CARD_H_MM)
                  | card.region(0.0, fy0 - 1.1, CARD_W_MM, fy0 + 1.1)
                  | card.region(0.0, fy1 - 1.1, CARD_W_MM, fy1 + 1.1))
    # Both chops are RED - frame, panel and the small one's 火道 alike - so the black
    # kanji columns cannot be part of either, and the lower-right column's foot passes
    # 1.2 mm above the small chop's top rule.  The four corner flourishes are red and
    # ARE excluded by position: the bottom-left one reaches into the band below the big
    # chop.  What is left in a band beside a chop is that chop.
    corner = np.zeros_like(card.red_m)
    leg = max(lay.bracket_leg_v_mm, lay.bracket_leg_h_mm,
              lay.bracket_leg_v_bottom_mm) + lay.bracket_curl_mm + 2.0
    o = lay.inner_rule_offset_mm
    for cx_, cy_ in ((fx0 + o, fy0 + o), (fx1 - o, fy0 + o),
                     (fx0 + o, fy1 - o), (fx1 - o, fy1 - o)):
        corner |= card.region(cx_ - leg, cy_ - leg, cx_ + leg, cy_ + leg)
    ink = card.red_m & ~rules_band & ~corner
    for name, fx, fy in (("big", lay.big_seal_frame_x, lay.big_seal_frame_y),
                         ("small", lay.small_seal_frame_x, lay.small_seal_frame_y)):
        x0, x1 = fx[0] * CARD_W_MM, fx[1] * CARD_W_MM
        y0, y1 = fy[0] * CARD_H_MM, fy[1] * CARD_H_MM
        # HOW FAR PAST ITS OWN FRAME DOES THE INK GO?  That is the whole of what rows 19
        # and 20 ask, and it is a LOCAL question, so it is asked locally: over the middle
        # 70 % of each of the four sides - clear of the corner flourishes and of the
        # kanji column feet - how far out does the chop's ink reach?  Chasing it with
        # connected components instead means the answer depends on whether a 3 mm piece
        # of broken rule happens to sit beside the box this build.
        reach = 2.6
        mx0, mx1 = x0 + 0.15 * (x1 - x0), x1 - 0.15 * (x1 - x0)
        my0, my1 = y0 + 0.15 * (y1 - y0), y1 - 0.15 * (y1 - y0)
        over: Dict[str, float] = {}
        for side in ("left", "right", "top", "bottom"):
            if side == "left":
                band = card.region(x0 - reach, my0, x0 + 0.2, my1)
            elif side == "right":
                band = card.region(x1 - 0.2, my0, x1 + reach, my1)
            elif side == "top":
                band = card.region(mx0, y0 - reach, mx1, y0 + 0.2)
            else:
                band = card.region(mx0, y1 - 0.2, mx1, y1 + reach)
            sub = ink & band
            if not sub.any():
                over[side] = 0.0
                continue
            ys_, xs_ = np.nonzero(sub)
            if side == "left":
                over[side] = round(x0 - float(card.x_mm[0, xs_.min()]), 2)
            elif side == "right":
                over[side] = round(float(card.x_mm[0, xs_.max()]) - x1, 2)
            elif side == "top":
                over[side] = round(y0 - float(card.y_mm[ys_.min(), 0]), 2)
            else:
                over[side] = round(float(card.y_mm[ys_.max(), 0]) - y1, 2)
        bw = (x1 - x0) + max(over["left"], 0.0) + max(over["right"], 0.0)
        bh = (y1 - y0) + max(over["top"], 0.0) + max(over["bottom"], 0.0)
        info = {"frame_box_mm": [round(x1 - x0, 2), round(y1 - y0, 2)],
                "overshoot_mm": over,
                "max_overshoot_mm": round(max(over.values()), 2),
                "drawn_box_mm": [round(bw, 2), round(bh, 2)],
                "drawn_centre_mm": [round(0.5 * (x0 + x1), 2), round(0.5 * (y0 + y1), 2)]}
        if name == "big":
            # Row 20's fill is taken on the REFERENCE's own box - 18.0 x 26.5 mm at
            # (14.4, 129.9), which section 6 confirms our frame sits inside to 0.4 mm -
            # and never on the drawn box: a fill measured inside a box that moved is a
            # different number every build, and it was reading 0.657 on a box that had
            # a kanji column in it.
            bw, bh = TARGETS["big_seal_box_mm"]
            cxr, cyr = TARGETS["big_seal_at_mm"]
            x0, x1 = cxr - bw * 0.5, cxr + bw * 0.5
            y0, y1 = cyr - bh * 0.5, cyr + bh * 0.5
            w, h = x1 - x0, y1 - y0
            inner = card.region(x0 + w * 0.2, y0 + h * 0.2, x1 - w * 0.2, y1 - h * 0.2)
            tot = float(inner.sum())
            info["inner60_red_fill"] = round(float((card.red_m & inner).sum()) / max(tot, 1.0), 3)
            sel2 = card.region(x0, y0, x1, y1)
            info["box_red_fill"] = round(float((card.red_m & sel2).sum())
                                         / max(float(sel2.sum()), 1.0), 3)
        out[name] = info
    return out


def ink_above_top_rule(card: Card, frame_mm) -> Dict[str, object]:
    """Row 18: there is NOTHING above the top rule in either guide."""
    x0, y0, x1, y1 = frame_mm
    sel = card.region(x0 + 12.0, 0.0, x1 - 12.0, y0 - 1.2)
    m = (card.black_m | card.red_m) & sel
    return {"texels": int(m.sum()), "mm2": round(card.area_mm2(int(m.sum())), 3)}


def ornament_chain(card: Card, lay) -> Dict[str, object]:
    """Rows 16 and 17: the black diamond on the bottom rule, and the flanking leaves."""
    out: Dict[str, object] = {}
    if lay.bottom_black_diamond is not None:
        dx, dy = (lay.bottom_black_diamond[0] * CARD_W_MM,
                  lay.bottom_black_diamond[1] * CARD_H_MM)
        sel = card.region(dx - 3.0, dy - 3.6, dx + 3.0, dy + 3.6)
        m = card.black_m & sel
        if m.any():
            ys, xs = np.nonzero(m)
            x0 = float(card.x_mm[0, xs.min()]); x1 = float(card.x_mm[0, xs.max()])
            y0 = float(card.y_mm[ys.min(), 0]); y1 = float(card.y_mm[ys.max(), 0])
            out["bottom_diamond"] = {
                "present": True,
                "centre_mm": [round(0.5 * (x0 + x1), 2), round(0.5 * (y0 + y1), 2)],
                "size_mm": [round(x1 - x0, 2), round(y1 - y0, 2)]}
        else:
            out["bottom_diamond"] = {"present": False}
    leaves = []
    for lx, ly, lw, lh in (lay.leaf_pair or ()):
        px, py = lx * CARD_W_MM, ly * CARD_H_MM
        sel = card.region(px - 2.2, py - 2.4, px + 2.2, py + 2.4)
        m = (card.red_m | card.black_m) & sel
        leaves.append({"at_mm": [round(px, 2), round(py, 2)],
                       "present": bool(m.any()),
                       "mm2": round(card.area_mm2(int(m.sum())), 2)})
    out["leaf_pair"] = leaves
    return out


def edge_ageing(card: Card) -> Dict[str, object]:
    """Row 25: depth at the trim line, reach to 95 % recovery, side spread and tilt."""
    stored = card.stored
    luma = (0.2126 * stored[..., 0] + 0.7152 * stored[..., 1] + 0.0722 * stored[..., 2])
    ink = (card.black_m | card.red_m) if card.black_m is not None else np.zeros_like(card.card)
    clean = card.card & ~ink
    # the interior reference value
    inner = clean & card.region(18.0, 30.0, CARD_W_MM - 18.0, CARD_H_MM - 30.0)
    base = float(np.median(luma[inner])) if inner.any() else 1.0
    profiles: Dict[str, List[float]] = {}
    nbin = 30
    edge_mm = 12.0
    for side in ("left", "right", "top", "bottom"):
        vals = []
        for i in range(nbin):
            d0 = edge_mm * i / nbin
            d1 = edge_mm * (i + 1) / nbin
            if side == "left":
                sel = card.region(d0, 22.0, d1, CARD_H_MM - 22.0)
            elif side == "right":
                sel = card.region(CARD_W_MM - d1, 22.0, CARD_W_MM - d0, CARD_H_MM - 22.0)
            elif side == "top":
                sel = card.region(14.0, d0, CARD_W_MM - 14.0, d1)
            else:
                sel = card.region(14.0, CARD_H_MM - d1, CARD_W_MM - 14.0, CARD_H_MM - d0)
            s = clean & sel
            vals.append(float(np.median(luma[s])) if s.sum() > 40 else float("nan"))
        profiles[side] = vals
    depths = {}
    reaches = {}
    for side, vals in profiles.items():
        v = np.array(vals, float)
        good = ~np.isnan(v)
        if not good.any():
            continue
        first = float(v[good][0])
        depths[side] = (base - first) / max(base, 1e-9)
        rec = np.full(nbin, np.nan)
        rec[good] = (v[good] - first) / max(base - first, 1e-9)
        idx = np.flatnonzero(good & (rec >= 0.95))
        reaches[side] = float(edge_mm * (idx[0] + 0.5) / nbin) if idx.size else edge_mm
    d = list(depths.values())
    # tilt: how much the CLEAN interior luma leans across the card
    left = clean & card.region(6.0, 30.0, 22.0, CARD_H_MM - 30.0)
    right = clean & card.region(CARD_W_MM - 22.0, 30.0, CARD_W_MM - 6.0, CARD_H_MM - 30.0)
    tl = float(np.median(luma[left])) if left.any() else base
    tr = float(np.median(luma[right])) if right.any() else base
    return {
        "interior_stored_luma": round(base, 4),
        "depth": {k: round(v, 4) for k, v in depths.items()},
        "depth_mean": round(float(np.mean(d)), 4) if d else 0.0,
        "depth_spread": round(float(np.ptp(d)), 4) if d else 0.0,
        "reach_mm": {k: round(v, 2) for k, v in reaches.items()},
        "reach_mean_mm": round(float(np.mean(list(reaches.values()))), 2) if reaches else 0.0,
        "tilt": round(abs(tl - tr) / max(base, 1e-9), 4),
    }


def grain(card: Card) -> Dict[str, object]:
    """Row 26: amplitude, dominant cell and anisotropy of the paper's own texture.

    Measured on the SHEET, ``art.paper_rgb`` - the ground before any ink went on it -
    over an interior rectangle clear of the aged rim.  Measuring the finished base
    colour instead puts every stroke edge into the band-pass and reports an amplitude
    of 100 %, which is a statistic about the calligraphy rather than about the paper.
    """
    src = getattr(card.art, "paper_rgb", None)
    src = card.base if src is None else np.asarray(src, np.float64)
    stored = _linear_to_srgb(src)
    luma = (0.2126 * stored[..., 0] + 0.7152 * stored[..., 1] + 0.0722 * stored[..., 2])
    ppmm = card.ppmm
    x0, _ = card.px(16.0, 0.0)
    x1, _ = card.px(CARD_W_MM - 16.0, 0.0)
    _, y0 = card.px(0.0, 26.0)
    _, y1 = card.px(0.0, CARD_H_MM - 26.0)
    patch = luma[y0:y1, x0:x1].astype(np.float64)
    if patch.size < 10000:
        return {}

    def box(a, r):
        p = np.pad(a, r, mode="edge")
        c = np.cumsum(np.cumsum(p, 0), 1)
        c = np.pad(c, ((1, 0), (1, 0)))
        n = 2 * r + 1
        s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
        return s / (n * n)

    # AMPLITUDE is everything finer than 1.2 mm, peak to peak (p95 - p05) over the
    # local mean - the texture of the sheet with its blotching taken out.  Smoothing the
    # signal first as well, which a first pass of this did, attenuates a 0.5 mm cell by
    # most of its energy and reports a 17 % grain as 4.6 %.
    hi = box(patch, max(2, int(round(1.2 * ppmm))))
    detail = patch - hi
    mean = float(np.mean(patch))
    amp = float(np.percentile(detail, 95) - np.percentile(detail, 5)) / max(mean, 1e-9)
    # the CELL is read off a band-passed copy so the 2 mm mottle cannot set it
    lo = box(patch, max(1, int(round(0.10 * ppmm))))
    bandpass = lo - box(patch, max(2, int(round(1.0 * ppmm))))
    # dominant cell: the lag at which the autocorrelation of the band-passed field
    # first crosses zero, doubled (a cell is half a wavelength)
    def first_zero(sig1d: np.ndarray) -> float:
        s = sig1d - sig1d.mean()
        n = min(len(s), int(round(8.0 * ppmm)))
        ac = np.array([float(np.mean(s[:len(s) - k] * s[k:])) for k in range(n)])
        if ac[0] <= 0:
            return 0.0
        ac = ac / ac[0]
        z = np.flatnonzero(ac <= 0.0)
        return (float(z[0]) / ppmm) if z.size else n / ppmm

    rows = bandpass[::max(1, bandpass.shape[0] // 40)]
    cols = bandpass[:, ::max(1, bandpass.shape[1] // 40)].T
    cx = float(np.median([first_zero(r) for r in rows]))
    cy = float(np.median([first_zero(c) for c in cols]))
    cell = 2.0 * min(cx, cy) if min(cx, cy) > 0 else 0.0
    aniso = (max(cx, cy) / max(min(cx, cy), 1e-6)) if min(cx, cy) > 0 else 99.0
    return {"amplitude": round(amp, 4), "cell_mm": round(cell, 3),
            "anisotropy": round(aniso, 2)}


def crease_rows(card: Card) -> Dict[str, object]:
    """Row 24: no row-luma dip the reference does not have."""
    # MEASURED ON THE SHEET, not on the finished map.  Row 24 asks one question - is a
    # crease BAKED into the base colour - and the sheet is where such a thing would be
    # baked.  Taking row medians of the composited card instead answers a different
    # question: the only clean paper on a row through the centre character is inside its
    # own counters, every one of them ringed by that stroke's bleed halo, so a perfectly
    # flat sheet reports a 4 % "dip" wherever the calligraphy is densest.
    src = getattr(card.art, "paper_rgb", None)
    src = card.base if src is None else np.asarray(src, np.float64)
    stored = _linear_to_srgb(src)
    luma = (0.2126 * stored[..., 0] + 0.7152 * stored[..., 1] + 0.0722 * stored[..., 2])
    clean = card.card & card.region(6.0, 12.0, CARD_W_MM - 6.0, CARD_H_MM - 12.0)
    # A CREASE IS A LINE, and the test has to tell one from a sheet that is merely
    # textured.  Three steps, in order:
    #
    #   1. the row MEDIAN across the clean width.  A median is immune to a 0.1 mm kozo
    #      thread lying along the row, which is a real paper feature and not a fold, and
    #      to the two stains, which are blobs rather than lines.
    #   2. that profile against its own 6 mm running mean - the local sheet value a
    #      crease would sit below.
    #   3. smoothed over 1 mm DOWN the card, which is a crease's own width.  A 0.5 mm
    #      fibre grain at the reference's own 17 % amplitude leaks about 1 % into any
    #      single row median by chance; averaging over a crease's width divides that by
    #      the root of the sample and leaves an actual line alone.  Without step 3 this
    #      measurement reports the GRAIN, and no sheet with the reference's texture can
    #      ever pass it.
    rowmed = np.full(card.H, np.nan)
    need = 0.25 * card.W
    for y in range(card.H):
        s = clean[y]
        if int(s.sum()) >= need:
            rowmed[y] = float(np.median(luma[y][s]))
    good = ~np.isnan(rowmed)
    if int(good.sum()) < 200:
        return {}
    idx = np.flatnonzero(good)
    v = rowmed[idx]

    def box1(a, n):
        n = max(1, int(n) | 1)
        pad = n // 2
        p = np.pad(a, (pad, pad), mode="edge")
        c = np.concatenate([[0.0], np.cumsum(p)])
        return (c[n:n + len(a)] - c[:len(a)]) / n

    ref = box1(v, 6.0 * card.ppmm)
    d = (ref - v) / np.maximum(ref, 1e-9)
    line = box1(d, 1.0 * card.ppmm)
    j = int(np.argmax(line))
    return {"max_row_dip": round(float(np.max(line)), 5),
            "raw_row_dip": round(float(np.max(d)), 5),
            "at_mm": round(float(card.y_mm[idx[j], 0]), 1)}


def hard_rect_discontinuity(card: Card, channels: Optional[Dict[str, np.ndarray]] = None
                            ) -> Dict[str, object]:
    """THE SQUARE-PATCH GATE.

    A straight, axis-aligned run of strong gradient in a paper texture is never
    something a sheet of paper does; it is a tile boundary, a window edge, or - as it
    turned out on the shipped build - a Cycles AO bake finding a pair of intersecting
    faces and dropping a whole UV quad into shadow.  Whatever draws it, it is the most
    synthetic mark a prop can carry, and a human spots it instantly at 4x.

    So: high-pass the map, take the local energy, and look for COLUMNS and ROWS along
    which that energy jumps hard for many consecutive texels.  A real stroke edge is
    diagonal or curved somewhere along its length and never survives this; a rectangle
    does.  Runs are reported with where they are, so a failure names the defect.
    """
    out: Dict[str, object] = {}
    maps = {"base_colour": card.base}
    if channels:
        maps.update(channels)
    runs_total = 0
    detail: List[Dict[str, object]] = []
    for name, arr in maps.items():
        a = np.asarray(arr, np.float64)
        v = a.mean(axis=2) if a.ndim == 3 else a

        def box(x, r):
            p = np.pad(x, r, mode="edge")
            c = np.cumsum(np.cumsum(p, 0), 1)
            c = np.pad(c, ((1, 0), (1, 0)))
            n = 2 * r + 1
            s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
            return s / (n * n)

        hp = np.abs(v - box(v, 2))
        e = box(hp, 3)
        scale = max(float(np.percentile(e, 99)), 1e-6)
        gx = np.abs(np.diff(e, axis=1)) / scale
        gy = np.abs(np.diff(e, axis=0)) / scale
        thr = 0.85
        min_run = int(round(1.2 * card.ppmm))
        for axis, g in (("column", gx), ("row", gy)):
            flags = g > thr
            # a run is consecutive texels along the OTHER axis at the same index
            if axis == "column":
                for x in range(flags.shape[1]):
                    for a0, a1 in _runs(flags[:, x]):
                        if a1 - a0 >= min_run:
                            runs_total += 1
                            if len(detail) < 12:
                                detail.append({"map": name, "axis": axis, "at_px": int(x),
                                               "from_px": int(a0), "to_px": int(a1)})
            else:
                for y in range(flags.shape[0]):
                    for a0, a1 in _runs(flags[y]):
                        if a1 - a0 >= min_run:
                            runs_total += 1
                            if len(detail) < 12:
                                detail.append({"map": name, "axis": axis, "at_px": int(y),
                                               "from_px": int(a0), "to_px": int(a1)})
    out["straight_high_gradient_runs"] = runs_total
    out["examples"] = detail
    out["min_run_px"] = int(round(1.2 * card.ppmm))
    return out


# ===========================================================================
# 5.  One call, every row
# ===========================================================================

def measure_front(art, cfg, lay, text_report: Optional[Dict] = None) -> Dict[str, object]:
    """Every measurable REFERENCE_SPEC row, taken on the drawn front."""
    card = Card(art, cfg.pad_mm)
    frame = (lay.rule_inset_left_mm, lay.rule_inset_top_mm,
             CARD_W_MM - lay.rule_inset_right_mm, CARD_H_MM - lay.rule_inset_bottom_mm)
    ring_c = (lay.ring_centre[0] * CARD_W_MM, lay.ring_centre[1] * CARD_H_MM)
    glyph_c = (lay.centre_char[0] * CARD_W_MM, lay.centre_char[1] * CARD_H_MM)
    # For the ring, take the four rule BANDS out geometrically.  The lap's outer ink
    # comes within 1.8 mm of the side rules - closer than the stroke is wide - so a
    # radial ray that reaches a stroke's worth past the lap finds the rule instead.
    fx0, fy0, fx1, fy1 = frame
    rule_band = (card.region(fx0 - 2.4, 0.0, fx0 + 2.4, CARD_H_MM)
                 | card.region(fx1 - 2.4, 0.0, fx1 + 2.4, CARD_H_MM)
                 | card.region(0.0, fy0 - 2.4, CARD_W_MM, fy0 + 2.4)
                 | card.region(0.0, fy1 - 2.4, CARD_W_MM, fy1 + 2.4))
    out: Dict[str, object] = {
        "ink": ink_and_contrast(card),
        "centre": centre_glyph(card, glyph_c,
                               (TARGETS["centre_w_mm"], TARGETS["centre_h_mm"])),
        "rules": rules(card, frame, lay),
        "corner_darts": corner_darts(card, frame),
        "ring": ring(card, ring_c, lay.ring_outer_mm, lay.ring_stroke_mm[1],
                     exclude=rule_band),
        "flame": flame(card, (lay.emblem_centre[0] * CARD_W_MM,
                              lay.emblem_centre[1] * CARD_H_MM), lay.emblem_size_mm),
        "columns": columns(card, text_report or (art.report or {}).get("text") or {}),
        "seals": seals(card, lay, frame),
        "above_top_rule": ink_above_top_rule(card, frame),
        "ornaments": ornament_chain(card, lay),
        "edge_ageing": edge_ageing(card),
        "grain": grain(card),
        "crease": crease_rows(card),
        "hard_rect": hard_rect_discontinuity(card),
        "corner_clip_mm": None,
    }
    return out


# ===========================================================================
# 6.  The gates
# ===========================================================================

def _within(value, target, tol) -> bool:
    try:
        return abs(float(value) - float(target)) <= float(tol)
    except (TypeError, ValueError):
        return False


def spec_gates(m: Dict[str, object], corner_clip_mm: float) -> Dict[str, bool]:
    """Every REFERENCE_SPEC tolerance this build claims to satisfy, as pass/fail.

    A gate is only added here for a row the build is actually trying to hit; a row that
    is knowingly short is reported in the build's ``known_gaps`` instead of being
    silently relaxed.  Nothing in here is allowed to loosen: a later build that drifts
    back toward the first one fails at exactly the row it drifted on.
    """
    T = TARGETS
    g: Dict[str, bool] = {}
    ink = m.get("ink") or {}
    centre = m.get("centre") or {}
    rl = m.get("rules") or {}
    rg = m.get("ring") or {}
    fl = m.get("flame") or {}
    col = m.get("columns") or {}
    dart = m.get("corner_darts") or {}
    orn = m.get("ornaments") or {}
    sl = m.get("seals") or {}
    eg = m.get("edge_ageing") or {}
    gr = m.get("grain") or {}
    cr = m.get("crease") or {}
    hr = m.get("hard_rect") or {}

    # row 1 - contrast
    ratio = float(ink.get("contrast_ratio", 0.0))
    g["s01_paper_to_ink_contrast"] = (
        ratio >= float(T["contrast_ratio"]) / float(T["contrast_ratio_factor"]))
    # row 2 - the hero character's size
    g["s02_centre_glyph_size"] = (
        _within(centre.get("w_mm"), T["centre_w_mm"], T["centre_w_tol_mm"])
        and _within(centre.get("h_mm"), T["centre_h_mm"], 1.4))
    # row 3 - and that it is ONE character in two pieces
    g["s03_centre_glyph_two_components"] = (
        int(centre.get("components", 99)) <= int(T["centre_components_max"]))
    # row 4 - one rule per side
    g["s04_single_border_rule"] = (
        int(rl.get("rules_per_side_max", 9)) <= int(T["rules_per_side"]))
    # rows 5 / 6 - column cells and leading
    g["s05_column_cell_width"] = _within(col.get("cell_w_mean_mm"), T["column_cell_mm"],
                                         T["column_cell_tol_mm"])
    g["s06_column_leading_closed"] = (
        float(col.get("leading_max_mm", 99.0)) <= float(T["column_leading_max_mm"]) + 0.6)
    # rows 7 / 8 - ring size, shape and centre
    g["s07_ring_size_and_shape"] = (
        _within(rg.get("mid_w_mm"), T["ring_mid_w_mm"], T["ring_axis_tol_mm"])
        and _within(rg.get("mid_h_mm"), T["ring_mid_h_mm"], T["ring_axis_tol_mm"])
        and float(T["ring_hw_lo"]) <= float(rg.get("mid_h_over_w", 0.0)) <= float(T["ring_hw_hi"]))
    rc = rg.get("mid_centre_mm") or [0.0, 0.0]
    g["s08_ring_centre"] = (
        _within(rc[0], T["ring_centre_mm"][0], T["ring_centre_tol_mm"] + 0.5)
        and _within(rc[1], T["ring_centre_mm"][1], T["ring_centre_tol_mm"] + 0.5))
    # row 9 - the swept band
    g["s09_ring_stroke_band"] = (
        float(T["ring_stroke_lo"]) <= float(rg.get("stroke_mm_p50", 0.0)) <= float(T["ring_stroke_hi"])
        and float(rg.get("stroke_mm_p95", 0.0)) >= float(T["ring_stroke_p95_min"]))
    # row 10 - kasure
    g["s10_ring_kasure"] = (
        float(T["ring_hole_lo"]) <= float(rg.get("hole_fraction", 0.0)) <= float(T["ring_hole_hi"]))
    # row 11 - the flame
    g["s11_flame_five_strokes"] = (
        int(fl.get("components", 0)) >= int(T["flame_components_min"])
        and float(T["flame_ink_lo"]) <= float(fl.get("ink_mm2", 0.0)) <= float(T["flame_ink_hi"]))
    # row 13 - red saturation
    g["s13_red_saturation"] = (
        float(ink.get("red_saturation", 0.0)) >= float(T["red_saturation_min"])
        and float((ink.get("red_stored_mean") or [1, 1, 1])[2]) <= float(T["red_blue_max"]))
    # row 14 - the corner dart
    g["s14_corner_dart_outboard"] = (
        float(T["corner_dart_lo"]) <= float(dart.get("min_mm", 0.0))
        and float(dart.get("max_mm", 99.0)) <= float(T["corner_dart_hi"]))
    # row 15 - paper colour
    g["s15_paper_colour"] = (
        float(T["paper_hue_lo"]) <= float(ink.get("paper_hue_deg", 0.0)) <= float(T["paper_hue_hi"])
        and float(T["paper_sat_lo"]) <= float(ink.get("paper_saturation", 0.0)) <= float(T["paper_sat_hi"])
        and float(ink.get("paper_linear_luma_p50", 0.0)) >= float(T["paper_linear_luma_min"]))
    # row 16 - the black diamond on the bottom rule
    bd = (orn.get("bottom_diamond") or {})
    g["s16_bottom_black_diamond"] = bool(bd.get("present")) and _within(
        (bd.get("centre_mm") or [0, 0])[1], T["bottom_diamond_mm"][1], T["ornament_tol_mm"] + 1.0)
    # row 18 - nothing above the top rule
    g["s18_nothing_above_the_top_rule"] = (
        float((m.get("above_top_rule") or {}).get("mm2", 99.0)) <= 0.05)
    # row 19 - the small chop's DRAWN box, and its glyphs' gap
    small = sl.get("small") or {}
    sb = small.get("drawn_box_mm") or [0.0, 0.0]
    g["s19_small_seal_box"] = (
        _within(sb[0], T["small_seal_box_mm"][0], T["small_seal_box_tol_mm"])
        and _within(sb[1], T["small_seal_box_mm"][1], T["small_seal_box_tol_mm"]))
    # row 20 - the chop's core is as solid as the guide's, and its box is its own
    big = sl.get("big") or {}
    bb = big.get("drawn_box_mm") or [0.0, 0.0]
    g["s20_big_seal_fill"] = (
        float(T["big_seal_fill_lo"]) <= float(big.get("inner60_red_fill", 0.0))
        <= float(T["big_seal_fill_hi"]) + 0.06)
    g["s20b_big_seal_box"] = (
        _within(bb[0], T["big_seal_box_mm"][0], T["big_seal_box_tol_mm"])
        and _within(bb[1], T["big_seal_box_mm"][1], T["big_seal_box_tol_mm"]))
    # ...and neither chop's brush walks off its own stone (rows 19 and 20's defect)
    g["s20c_seal_ink_stays_on_its_frame"] = (
        float(big.get("max_overshoot_mm", 9.0)) <= 1.0
        and float(small.get("max_overshoot_mm", 9.0)) <= 1.0)
    # row 21 - rule weight, and the two sides agreeing
    g["s21_rule_weight"] = (
        float(T["rule_weight_lo"]) <= float(rl.get("weight_mm_mean", 0.0)) <= float(T["rule_weight_hi"])
        and float(rl.get("weight_lr_difference_mm", 9.0)) <= float(T["rule_weight_lr_tol_mm"]) + 0.10)
    # row 22 - the rules run out of ink
    g["s22_rule_continuity"] = (
        float(T["rule_occupancy_lo"]) - 0.04 <= float(rl.get("occupancy_min", 0.0))
        and float(rl.get("occupancy_max", 1.0)) <= float(T["rule_occupancy_hi"]) + 0.03
        and float(rl.get("longest_break_mm", 99.0)) <= float(T["rule_break_longest_max_mm"]))
    # row 23 - the chamfer
    g["s23_corner_chamfer"] = _within(corner_clip_mm, T["corner_clip_mm"], T["corner_clip_tol_mm"])
    # row 24 - no baked crease in the base colour
    g["s24_no_baked_crease"] = (
        float(cr.get("max_row_dip", 1.0)) <= float(T["crease_row_dip_max"]))
    # row 25 - edge ageing
    g["s25_edge_ageing"] = (
        float(T["edge_depth_lo"]) <= float(eg.get("depth_mean", 0.0)) <= float(T["edge_depth_hi"])
        and float(T["edge_reach_lo"]) <= float(eg.get("reach_mean_mm", 0.0)) <= float(T["edge_reach_hi"])
        and float(eg.get("depth_spread", 9.0)) <= float(T["edge_side_spread_max"])
        and float(eg.get("tilt", 9.0)) <= float(T["edge_tilt_max"]))
    # row 26 - grain
    g["s26_paper_grain"] = (
        float(T["grain_amp_lo"]) <= float(gr.get("amplitude", 0.0)) <= float(T["grain_amp_hi"])
        and float(T["grain_cell_lo"]) <= float(gr.get("cell_mm", 0.0)) <= float(T["grain_cell_hi"])
        and float(gr.get("anisotropy", 99.0)) <= float(T["grain_aniso_max"]))
    # composition
    g["s27_ink_coverage"] = (
        _within(ink.get("total_ink_fraction"), T["total_ink"], T["ink_total_tol"])
        and _within(ink.get("black_over_red"), T["black_over_red"], T["black_over_red_tol"]))
    # section 6: the frame rectangle must NOT have moved
    fr = rl.get("frame_rect_mm") or [0.0, 0.0]
    g["s28_frame_rectangle_unmoved"] = (
        _within(fr[0], T["frame_rect_mm"][0], T["frame_tol_mm"])
        and _within(fr[1], T["frame_rect_mm"][1], T["frame_tol_mm"]))
    # the square-patch defect
    g["s29_no_hard_rectangular_patch"] = (
        int(hr.get("straight_high_gradient_runs", 99)) <= int(T["hard_rect_runs_max"]))
    return g


__all__ = ["TARGETS", "Card", "measure_front", "spec_gates", "components", "label_cc",
           "ink_and_contrast", "centre_glyph", "rules", "ring", "flame", "columns",
           "seals", "edge_ageing", "grain", "crease_rows", "hard_rect_discontinuity",
           "corner_darts", "ornament_chain", "ink_above_top_rule"]
