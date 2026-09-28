#!/usr/bin/env python
"""props_lib.paperbomb_trace - every element of the paper bomb, traced from the user's reference.

The paper bomb is the USER'S OWN design and they asked for it to be traced ("it's my own
design, so trace it directly from that image; it's the only source").  This module is the
element layer on top of ``props_lib.trace``, which reads the source, fits the card, unmixes
the ink and owns the contour / spline / rasteriser primitives.  It:

    1. rectifies the reference onto the card (``trace.fit_card``; its four corners agree
       with the rg_s1 instrument in WorkFiles/paperbomb/reference_metrology to 0.005 px)
    2. separates the ink into a BLACK and a RED layer, red classified first
       (``trace.ink_layers``: a deep seal red is darker than a naive black threshold and
       would otherwise come out as grey black)
    3. vectorises every element into resolution-independent shapes in CARD MILLIMETRES:

         contour   filled shapes (emblem, glyphs, ring, seals, ornaments, leaves).
                   Ink field (normalised to full strength) -> cubic B-spline interpolation
                   x8 -> sub-pixel marching squares at the half level -> corner-split
                   clamped cubic B-spline least-squares fit (knot 1.5 source px, smooth
                   0.1; corners found on a first stiff fit so the one-pixel staircase of
                   an aliased edge is neither copied nor mistaken for a tip) ->
                   analysis-by-synthesis refinement: the curves move along their normals
                   until, rendered through the source's own point spread (pixel box +
                   Gaussian 0.4 px), they reproduce the observed ink.  That is what
                   lengthens the tapered tips a half-level contour always cuts short.
                   (Knot 0.5 re-rendered the source marginally better but copied the
                   staircase as visible scallops at 8x; see exact/pbt/pbt_bench_*.json.)
         stroke    the long straight runs of the four frame rules.  A rule is often
                   NARROWER than one source pixel, so its half-level contour breaks where it
                   thins and the rule came out dashed.  A stroke is traced as a centreline
                   plus a width profile: every 0.25 px along the rule the ink across it is
                   INTEGRATED (blur preserves the integral, so the width is unbiased by the
                   point spread) and divided by the ink's full-strength density.  The rule
                   thins exactly where the reference thins and lifts only where it lifts.

    4. scores every element against the source on the source's own grid (IoU, soft IoU,
       symmetric contour edge distance, edge-band MAE) and writes the whole set, with its
       provenance, to ``paperbomb_traced.json`` next to this module.

TRACE GROUPS AND SCORE ELEMENTS.  Ink is traced per connected group, so nothing is ever cut
where two elements touch: the frame rules, the four corner flourishes and the small seal's
box are one connected piece of red in the reference, traced as the group ``frame`` (its
thin rule runs as strokes, the rest as contours).  Scores are reported per ELEMENT the user
names - emblem, centre, ring, seals, chain, each corner, the rules, each column - over
pixel regions, so the frame is scored as its corners, its rules and its seal box.

Provenance: the JSON records the one source (path + SHA-256), the card fit and, per element,
how it was derived.  ``load_traced()`` refuses a file whose recorded source hash does not
match the reference on disk.

Deterministic numpy only: the same source bytes give the same JSON byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from . import trace as T
from . import paperbomb_finefit as FF

PB_TRACE_VERSION = "2.3.0"
HERE = os.path.dirname(os.path.abspath(__file__))
TRACED_JSON = os.path.join(HERE, "paperbomb_traced.json")

CARD_W_MM = T.CARD_W_MM
CARD_H_MM = T.CARD_H_MM

#: contour tracer parameters (chosen by measurement: WorkFiles/paperbomb/exact/pbt/)
UPSAMPLE = 8
KERNEL = "bspline"
ISO = 0.5
KNOT_PX = 1.5
CORNER_DEG = 80.0
CORNER_ARM_PX = 1.5
CORNER2_ARM_PX = 0.8
CORNER2_DEG = 40.0
SMOOTH = 0.1
REFINE_ITERS = 12
MIN_LOOP_AREA_PX2 = 0.35          # below this a loop is paper mottle, not a mark


# ===========================================================================
# 1.  Groups (what is traced together) and elements (what is scored)
# ===========================================================================

#: rule centrelines (card mm) and the half-width of the band the rules live in
RULES_MM = {"L": 3.83, "R": 65.87, "T": 6.56, "B": 154.81}
RULE_HALF_BAND_MM = 1.5
#: how far either side of a rule's centreline its stroke integrates (covers the side marks)
RULE_STROKE_HALF_MM = 1.05

#: (group, layer) -> box in card mm (x0, y0, x1, y1).  A connected component of ink goes to
#: the first group whose box CONTAINS it; then anything touching the rule band goes to the
#: frame; then anything whose centroid is in a box goes to that group.
GROUPS: tuple = (
    ("emblem",     "black", (21.5, 18.5, 48.5, 43.6)),
    ("chain",      "black", (32.5, 151.5, 37.5, 157.8)),
    ("chain",      "red",   (32.8, 109.8, 37.3, 160.5)),
    ("small_seal", "red",   (55.6, 136.2, 63.3, 151.3)),
    ("col_TL",     "black", (4.5, 8.8, 22.0, 56.0)),
    ("col_TR",     "black", (48.8, 8.8, 66.2, 55.5)),
    ("col_BR",     "black", (49.5, 102.0, 66.2, 132.5)),
    ("col_BC",     "black", (27.0, 113.5, 43.0, 149.0)),
    ("seal_big",   "red",   (5.0, 121.8, 24.6, 150.6)),
    ("centre",     "black", (6.5, 52.0, 67.0, 107.0)),
    ("ring",       "red",   (5.0, 43.5, 65.0, 111.0)),
)
FRAME = "frame"

CORNER_BOXES = {
    "corner_TL": (0.0, 0.0, 12.8, 15.6),
    "corner_TR": (57.2, 0.0, 70.0, 15.6),
    "corner_BL": (0.0, 146.7, 12.8, CARD_H_MM),
    "corner_BR": (57.2, 146.7, 70.0, CARD_H_MM),
}
SMALL_SEAL_BOX = (55.6, 136.2, 63.3, 151.3)


@dataclass(frozen=True)
class Element:
    name: str
    groups: tuple              # trace groups whose ink this element is scored on
    box_mm: tuple | None       # pixel box that splits a shared group (None: whole group)
    label: str


ELEMENTS: tuple = (
    Element("emblem", ("emblem",), None,
            "top-centre flame emblem: two tall tongues, spiral heart with its tail, two hooks"),
    Element("centre", ("centre",), None, "centre character"),
    Element("ring", ("ring",), None, "dry-brush ring"),
    Element("seal_big", ("seal_big",), None,
            "large lower-left seal: frame, panel, the white flame device knocked out"),
    Element("small_seal", ("small_seal", FRAME), SMALL_SEAL_BOX,
            "small bottom-right seal: its box and the two red characters"),
    Element("chain", ("chain",), None, "centreline chain: red leaves and the black diamond"),
    Element("corner_TL", (FRAME,), CORNER_BOXES["corner_TL"], "top-left corner flourish"),
    Element("corner_TR", (FRAME,), CORNER_BOXES["corner_TR"], "top-right corner flourish"),
    Element("corner_BL", (FRAME,), CORNER_BOXES["corner_BL"], "bottom-left corner flourish"),
    Element("corner_BR", (FRAME,), CORNER_BOXES["corner_BR"], "bottom-right corner flourish"),
    Element("rules", (FRAME,), "rules", "the four frame rules, their side marks, the black "
            "middle run of the top rule"),
    Element("col_TL", ("col_TL",), None, "upper-left column (waits for the font result)"),
    Element("col_TR", ("col_TR",), None, "upper-right column (waits for the font result)"),
    Element("col_BR", ("col_BR",), None, "lower-right column (waits for the font result)"),
    Element("col_BC", ("col_BC",), None, "lower-centre column (waits for the font result)"),
)


# ===========================================================================
# 2.  Source, layers, groups
# ===========================================================================

@dataclass
class Layers:
    src: T.Source
    fit: T.CardFit
    black: np.ndarray            # black coverage 0..1 at source px
    red: np.ndarray              # red coverage as observed
    red_behind: np.ndarray       # red coverage with the black lifted off it
    density: dict                # layer -> full-strength density field
    xm: np.ndarray               # card mm of each source pixel centre
    ym: np.ndarray
    inside: np.ndarray           # pixel centre on the card


def load_layers(source: str | None = None) -> Layers:
    src = T.read_source(source)
    fit = T.fit_card(src)
    ak, behind, unm = T.ink_layers(src, fit)
    H, W = ak.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    xm, ym = fit.px_to_mm(xx, yy)
    inside = (xm > 0.0) & (xm < CARD_W_MM) & (ym > 0.0) & (ym < CARD_H_MM)
    dens = {}
    for name, a in (("black", ak), ("red", behind)):
        core = T.erode(a > 0.5, 1)
        dens[name] = np.clip(T.norm_conv(a, core.astype(np.float64), 1.5, 0.97), 0.6, 1.0)
    return Layers(src=src, fit=fit, black=ak, red=unm.alpha_r, red_behind=behind,
                  density=dens, xm=xm, ym=ym, inside=inside)


def layer_field(L: Layers, layer: str, behind: bool = True) -> np.ndarray:
    if layer == "black":
        return L.black
    return L.red_behind if behind else L.red


def _in_box(xm, ym, box):
    x0, y0, x1, y1 = box
    return (xm >= x0) & (xm < x1) & (ym >= y0) & (ym < y1)


def rule_band(L: Layers, half: float = RULE_HALF_BAND_MM) -> np.ndarray:
    x, y = L.xm, L.ym
    ok_y = (y > RULES_MM["T"] - half) & (y < RULES_MM["B"] + half)
    ok_x = (x > RULES_MM["L"] - half) & (x < RULES_MM["R"] + half)
    return L.inside & (((np.abs(x - RULES_MM["L"]) < half) & ok_y)
                       | ((np.abs(x - RULES_MM["R"]) < half) & ok_y)
                       | ((np.abs(y - RULES_MM["T"]) < half) & ok_x)
                       | ((np.abs(y - RULES_MM["B"]) < half) & ok_x))


def rule_s_range(side: str, extend: float = 0.0) -> tuple:
    """The run of a rule traced as a STROKE: between the two corner boxes it ends in
    (and, on the right rule, not through the small seal's box - it never reaches it)."""
    if side in ("L", "R"):
        top = CORNER_BOXES["corner_TL"][3]; bot = CORNER_BOXES["corner_BL"][1]
        return top - extend, bot + extend
    left = CORNER_BOXES["corner_TL"][2]; right = CORNER_BOXES["corner_TR"][0]
    return left - extend, right + extend


def side_stroke_zone(L: Layers, side: str, extend: float = 0.0) -> np.ndarray:
    """The stroke zone of ONE rule."""
    x, y = L.xm, L.ym
    h = RULE_STROKE_HALF_MM
    a0, a1 = rule_s_range(side, extend)
    if side in ("L", "R"):
        z = (np.abs(x - RULES_MM[side]) < h) & (y >= a0) & (y < a1)
    else:
        z = (np.abs(y - RULES_MM[side]) < h) & (x >= a0) & (x < a1)
    return z & L.inside


def stroke_zone(L: Layers, extend: float = 0.0) -> np.ndarray:
    """Pixels the rule STROKES own (the contour part of the frame is zeroed here)."""
    x, y = L.xm, L.ym
    h = RULE_STROKE_HALF_MM
    z = np.zeros_like(L.inside)
    for side in ("L", "R", "T", "B"):
        a0, a1 = rule_s_range(side, extend)
        if side in ("L", "R"):
            z |= (np.abs(x - RULES_MM[side]) < h) & (y >= a0) & (y < a1)
        else:
            z |= (np.abs(y - RULES_MM[side]) < h) & (x >= a0) & (x < a1)
    return z & L.inside


def group_masks(L: Layers) -> dict:
    """(group, layer) -> bool mask of the ink (> 0.5, 8-connected components) it owns."""
    out = {}
    band = rule_band(L)
    for layer in ("black", "red"):
        a = layer_field(L, layer, behind=False)
        lab, n = T.label((a > 0.5) & L.inside)
        H, W = a.shape
        idx = lab.ravel()
        cnt = np.bincount(idx, minlength=n + 1).astype(np.float64)
        cx = np.bincount(idx, weights=L.xm.ravel(), minlength=n + 1) / np.maximum(cnt, 1)
        cy = np.bincount(idx, weights=L.ym.ravel(), minlength=n + 1) / np.maximum(cnt, 1)
        big = 1e9
        x0 = np.full(n + 1, big); y0 = np.full(n + 1, big)
        x1 = np.full(n + 1, -big); y1 = np.full(n + 1, -big)
        np.minimum.at(x0, idx, L.xm.ravel()); np.minimum.at(y0, idx, L.ym.ravel())
        np.maximum.at(x1, idx, L.xm.ravel()); np.maximum.at(y1, idx, L.ym.ravel())
        touches = np.bincount(idx, weights=band.ravel().astype(np.float64), minlength=n + 1) > 0
        owner = np.full(n + 1, "", dtype=object)
        owner[0] = "-"
        groups = [(g, box) for g, lay, box in GROUPS if lay == layer]
        for g, (bx0, by0, bx1, by1) in groups:            # 1. wholly inside a box
            take = (owner == "") & (x0 >= bx0) & (x1 < bx1) & (y0 >= by0) & (y1 < by1)
            owner[take] = g
        owner[(owner == "") & touches] = FRAME             # 2. touches the rule band
        for g, box in groups:                               # 3. centroid in a box
            take = (owner == "") & _in_box(cx, cy, box)
            owner[take] = g
        owner[owner == ""] = "unassigned"
        names = [g for g, _ in groups] + [FRAME, "unassigned"]
        for g in names:
            ids = np.flatnonzero(owner == g)
            m = np.isin(lab, ids) if len(ids) else np.zeros((H, W), bool)
            if m.any():
                out[(g, layer)] = m
    return out


def group_regions(L: Layers, masks: dict) -> dict:
    """Owned ink grown by 3 px, minus every other group's ink grown by 1 px."""
    out = {}
    for (g, layer), m in masks.items():
        others = np.zeros_like(m)
        for (g2, l2), m2 in masks.items():
            if l2 == layer and g2 != g:
                others |= m2
        out[(g, layer)] = T.dilate(m, 3) & L.inside & ~T.dilate(others, 1)
    return out


def element_regions(L: Layers, masks: dict, regions: dict) -> dict:
    """(element, layer) -> scoring region (bool)."""
    out = {}
    corners = np.zeros_like(L.inside)
    for b in CORNER_BOXES.values():
        corners |= _in_box(L.xm, L.ym, b)
    seal_box = _in_box(L.xm, L.ym, SMALL_SEAL_BOX)
    for e in ELEMENTS:
        for layer in ("black", "red"):
            reg = np.zeros_like(L.inside)
            for g in e.groups:
                if (g, layer) in regions:
                    reg |= regions[(g, layer)]
            if e.box_mm == "rules":
                reg &= ~corners & ~seal_box
            elif e.box_mm is not None:
                reg &= _in_box(L.xm, L.ym, e.box_mm)
            core = np.zeros_like(reg)
            for g in e.groups:
                if (g, layer) in masks:
                    core |= masks[(g, layer)]
            if (core & reg).any():
                out[(e.name, layer)] = reg
    return out


# ===========================================================================
# 3.  The contour tracer
# ===========================================================================

def _window(mask: np.ndarray, pad: int, shape) -> tuple:
    ys, xs = np.nonzero(mask)
    H, W = shape
    return (max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
            min(W, int(xs.max()) + 1 + pad), min(H, int(ys.max()) + 1 + pad))


def trace_contour(L: Layers, layer: str, region: np.ndarray, refine: bool = True,
                  factor: int = UPSAMPLE, kind: str = KERNEL, knot: float = KNOT_PX,
                  iters: int = REFINE_ITERS, spline: bool = True, field=None,
                  smooth: float = None, corner_arm: float = None, corner_deg: float = None,
                  two_pass: bool = True):
    """Trace the ink of one group.  Returns (curves in SOURCE px, info)."""
    if field is None:
        field = layer_field(L, layer, behind=True)
    dens = L.density[layer]
    f = np.where(region, field / dens, 0.0)            # this group's ink at full strength
    win = _window(region, 3, f.shape)
    t0 = time.time()
    x0, y0, x1, y1 = win
    if factor == 1 and kind == "linear":
        loops = [l + np.array([x0 + 0.5, y0 + 0.5])
                 for l in T.marching_squares(f[y0:y1, x0:x1], ISO)]
    else:
        fine, gx0, gy0, st = T.upsample_window(f, x0, y0, x1, y1, factor, kind)
        loops = [np.stack([gx0 + l[:, 0] * st, gy0 + l[:, 1] * st], 1)
                 for l in T.marching_squares(fine, ISO)]
    loops = [l for l in loops if abs(T.signed_area(l)) >= MIN_LOOP_AREA_PX2]
    curves, stats = [], []
    sm_ = SMOOTH if smooth is None else smooth
    for l in loops:
        if spline:
            c, s = T.fit_loop(l, knot, corner_deg=CORNER_DEG if corner_deg is None else corner_deg,
                              corner_arm_px=CORNER_ARM_PX if corner_arm is None else corner_arm,
                              smooth=sm_)
            if two_pass:
                # TWO PASSES.  The half-level contour of an aliased edge carries a one-pixel
                # staircase, so corners searched on it at a short arm are staircase steps
                # and at a long arm the real tips (a barb, a notch) are missed.  The first,
                # stiff fit has no staircase; the corners are searched on IT at a short arm,
                # and the contour is fitted again with exactly those corners.
                q1 = c.sample(0.05)
                cs = T.find_corners(q1, 0.05, CORNER2_ARM_PX, CORNER2_DEG)
                c, s = T.fit_loop(l, knot, smooth=sm_, corner_pts=[q1[i] for i in cs])
        else:
            c, s = T.Curve([l], True), {"corners": 0, "rms_px": 0.0, "joint_kink_deg": 0.0}
        curves.append(c)
        stats.append(s)
    hist = []
    if refine and spline and curves:
        obs = np.where(region, field, 0.0)
        curves, hist = T.refine_curves(curves, obs, dens, region, knot,
                                       SMOOTH if smooth is None else smooth, iters=iters)
    info = {"loops": len(curves),
            "holes": int(sum(1 for l in loops if T.signed_area(l) < 0)),
            "corners": int(sum(s["corners"] for s in stats)),
            "fit_rms_px": round(float(np.mean([s["rms_px"] for s in stats])) if stats else 0.0, 4),
            "joint_kink_deg_max": round(max([s.get("joint_kink_deg", 0.0) for s in stats] or [0.0]), 3),
            "refine_residual": [round(h, 4) for h in hist],
            "secs": round(time.time() - t0, 2)}
    return curves, info


# ===========================================================================
# 4.  The stroke tracer (the long runs of the rules)
# ===========================================================================

#: a sample narrower than this is a real gap in the rule: the ink across it integrates to
#: less than 1/20 of a source pixel (0.013 mm), which reads as bare paper
RULE_GAP_WIDTH_PX = 0.05


def trace_rule(L: Layers, layer: str, side: str, region: np.ndarray, step_px: float = 0.25,
               extend_mm: float = 0.3):
    """One rule's stroke run as (centreline, width) samples in SOURCE px.

    Samples run along the rule every ``step_px``; at each, this layer's frame ink across
    the rule is integrated over +-RULE_STROKE_HALF_MM (bilinear, 0.1 px steps) and divided
    by the full-strength density: that integral IS the stroke's width, unbiased by the
    blur.  The centre is the ink-weighted centroid, smoothed along the rule.  The run
    reaches ``extend_mm`` into the corner boxes so it overlaps the contour part there.
    """
    fit = L.fit
    field = np.where(region, layer_field(L, layer, behind=False), 0.0)
    dens = L.density[layer]
    a0m, a1m = rule_s_range(side, extend_mm)
    if side in ("L", "R"):
        a0 = np.array(fit.mm_to_px(RULES_MM[side], a0m)); a1 = np.array(fit.mm_to_px(RULES_MM[side], a1m))
    else:
        a0 = np.array(fit.mm_to_px(a0m, RULES_MM[side])); a1 = np.array(fit.mm_to_px(a1m, RULES_MM[side]))
    d = a1 - a0
    Lpx = float(np.hypot(*d))
    t_hat = d / Lpx
    n_hat = np.array([-t_hat[1], t_hat[0]])
    half_px = RULE_STROKE_HALF_MM * fit.ppmm
    s = np.arange(0.0, Lpx + 1e-9, step_px)
    u = np.arange(-half_px, half_px + 1e-9, 0.1)
    P = a0[None, None, :] + s[:, None, None] * t_hat + u[None, :, None] * n_hat
    flat = P.reshape(-1, 2)
    v = T._bilinear(field, flat).reshape(len(s), len(u))
    # THE PAPER'S FLOOR.  The unmixing clips coverage at zero, so the bare paper either
    # side of a rule reads a small POSITIVE coverage (mean 0.009 red on near-bare paper);
    # integrated over the +-1.05 mm window that adds ~0.07 px of width to every sample and
    # the rules came out ~0.05 mm heavier than the reference measures them.  The floor is
    # the lower of the two outer quarters' means, a running median along the rule over
    # ~4 mm (so a side mark, which fills the outer bins over 1 - 2 mm, cannot raise it),
    # capped at 0.06, and subtracted before integrating.
    outer = np.abs(u) > 0.70 * half_px
    left = (u < 0) & outer; right = (u > 0) & outer
    fl = np.minimum(v[:, left].mean(1), v[:, right].mean(1))
    k_ = max(1, int(round(4.0 * fit.ppmm / step_px)) // 2)
    pad_ = np.pad(fl, k_, mode="edge")
    fl = np.array([np.median(pad_[i:i + 2 * k_ + 1]) for i in range(len(fl))])
    fl = np.clip(fl, 0.0, 0.06)
    v = np.clip(v - fl[:, None], 0.0, None)
    dv = T._bilinear(dens, flat).reshape(len(s), len(u))
    mass = v.sum(1) * 0.1
    dmean = np.where(v.sum(1) > 1e-9, (v * dv).sum(1) / np.maximum(v.sum(1), 1e-12), 0.97)
    width = mass / np.maximum(dmean, 0.6)
    off = np.where(mass > 1e-6, (v * u[None, :]).sum(1) * 0.1 / np.maximum(mass, 1e-12), 0.0)
    wt = np.clip(width, 0, None)
    k = np.exp(-0.5 * (np.arange(-24, 25) * step_px / 2.0) ** 2)
    num = np.convolve(off * wt, k, mode="same"); den = np.convolve(wt, k, mode="same")
    off_s = np.where(den > 1e-6, num / np.maximum(den, 1e-12), 0.0)
    centre = a0[None, :] + s[:, None] * t_hat + off_s[:, None] * n_hat
    return {"side": side, "layer": layer, "centre_px": centre, "width_px": width,
            "n_hat": n_hat, "step_px": step_px}


def _runs(on: np.ndarray) -> list:
    out = []
    i = 0
    N = len(on)
    while i < N:
        if not on[i]:
            i += 1
            continue
        j = i
        while j < N and on[j]:
            j += 1
        out.append((i, j))
        i = j
    return out


def stroke_polys(centre: np.ndarray, width: np.ndarray, gap_width) -> list:
    """Closed polygons of a stroke: centreline +- width/2, one per run above the gap
    width, wound like an outer contour (positive area in y-down pixel/mm coordinates)."""
    d = np.gradient(centre, axis=0)
    d /= np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    polys = []
    for i, j in _runs(width > gap_width):
        if j - i < 2:
            continue
        cc = centre[i:j]; ww = width[i:j, None]; nn = n[i:j]
        p = np.vstack([cc + 0.5 * ww * nn, (cc - 0.5 * ww * nn)[::-1]])
        polys.append(p)
    return polys


def _orient(polys, sign):
    return [p if np.sign(T.signed_area(p)) == sign or T.signed_area(p) == 0 else p[::-1]
            for p in polys]


# ===========================================================================
# 5.  Rendering and scoring at the source's grid
# ===========================================================================

def render_polys_source(polys, H, W, window=None, sigma=0.0):
    cov = T.fill_polys(polys, H, W, ss=16, window=window).astype(np.float64)
    return T.gauss_blur(cov, sigma) if sigma > 0 else cov


def _contour_pts(field, iso=0.5, step=0.1):
    pts = []
    for l in T.marching_squares(field, iso):
        if len(l) < 3:
            continue
        pts.append(T.resample_closed(l + 0.5, step))
    return np.vstack(pts) if pts else np.zeros((0, 2))


def _nn(a, b, cell: float = 2.0):
    """Distance from each point of ``a`` to the nearest point of ``b`` (exact).

    Bucketed: ``b`` is binned into ``cell``-px cells; a point of ``a`` searches its own
    cell and the eight around it, which is exact whenever the answer is under ``cell``.
    Points with nothing within that reach fall back to a brute-force pass."""
    if len(a) == 0 or len(b) == 0:
        return np.full(len(a), np.nan)
    kb = np.floor(b / cell).astype(np.int64)
    ka = np.floor(a / cell).astype(np.int64)
    ox = min(int(kb[:, 0].min()), int(ka[:, 0].min())) - 1
    oy = min(int(kb[:, 1].min()), int(ka[:, 1].min())) - 1
    nx = max(int(kb[:, 0].max()), int(ka[:, 0].max())) - ox + 2
    idb = (kb[:, 1] - oy) * nx + (kb[:, 0] - ox)
    order = np.argsort(idb, kind="stable")
    bs = b[order]; ids = idb[order]
    ida = (ka[:, 1] - oy) * nx + (ka[:, 0] - ox)
    out = np.full(len(a), np.inf)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            q = ida + dy * nx + dx
            lo = np.searchsorted(ids, q, "left"); hi = np.searchsorted(ids, q, "right")
            cnt = hi - lo
            m = cnt > 0
            if not m.any():
                continue
            c = cnt[m]
            ai = np.repeat(np.flatnonzero(m), c)
            bi = np.repeat(lo[m], c) + (np.arange(int(c.sum())) - np.repeat(np.cumsum(c) - c, c))
            d = np.hypot(a[ai, 0] - bs[bi, 0], a[ai, 1] - bs[bi, 1])
            np.minimum.at(out, ai, d)
    far = ~(out < cell)
    for i in np.flatnonzero(far):
        out[i] = float(np.hypot(a[i, 0] - b[:, 0], a[i, 1] - b[:, 1]).min())
    return out


def score_fields(pred: np.ndarray, obs: np.ndarray, region: np.ndarray, ppmm: float) -> dict:
    """pred, obs: coverage fields at source px (full strength = 1); region: bool.

    IoU     of the half-level regions, inside ``region``
    soft    sum(min) / sum(max) of the fields
    edge    symmetric nearest-contour distance between the half-level contours (linear
            marching squares on both fields), counting only contour points more than
            1.5 px inside ``region`` so a region's own border never scores as a match
    band    mean |pred - obs| where either is between 0.05 and 0.95 (the edge pixels)
    """
    ys, xs = np.nonzero(region)
    if len(ys) == 0:
        return {"iou": None}
    x0, x1 = max(0, xs.min() - 2), xs.max() + 3
    y0, y1 = max(0, ys.min() - 2), ys.max() + 3
    p = np.where(region, pred, 0.0)[y0:y1, x0:x1]
    o = np.where(region, obs, 0.0)[y0:y1, x0:x1]
    rg = region[y0:y1, x0:x1]
    pb = p > 0.5; ob = o > 0.5
    union = (pb | ob).sum()
    iou = float((pb & ob).sum() / union) if union else 1.0
    soft = float(np.minimum(p, o).sum() / max(1e-9, np.maximum(p, o).sum()))
    band = rg & (((p > 0.05) & (p < 0.95)) | ((o > 0.05) & (o < 0.95)))
    band_mae = float(np.abs(p - o)[band].mean()) if band.any() else 0.0
    cp = _contour_pts(p); co = _contour_pts(o)
    deep = T.erode(rg, 2)

    def keep(pts):
        if len(pts) == 0:
            return pts
        i = np.clip(np.floor(pts[:, 1]).astype(int), 0, rg.shape[0] - 1)
        j = np.clip(np.floor(pts[:, 0]).astype(int), 0, rg.shape[1] - 1)
        return pts[deep[i, j]]

    cp = keep(cp); co = keep(co)
    d = np.concatenate([_nn(co, cp), _nn(cp, co)])
    d = d[np.isfinite(d)]
    res = {"iou": round(iou, 4), "soft_iou": round(soft, 4), "band_mae": round(band_mae, 4),
           "ink_px_obs": int(ob.sum()), "ink_px_pred": int(pb.sum())}
    if len(d):
        res.update({"edge_mean_px": round(float(d.mean()), 4),
                    "edge_p95_px": round(float(np.percentile(d, 95)), 4),
                    "edge_max_px": round(float(d.max()), 4),
                    "edge_mean_mm": round(float(d.mean()) / ppmm, 4),
                    "edge_p95_mm": round(float(np.percentile(d, 95)) / ppmm, 4)})
    return res


# ===========================================================================
# 6.  Tracing everything
# ===========================================================================

def _curves_px_to_mm(curves, fit):
    def f(p):
        x, y = fit.px_to_mm(p[:, 0], p[:, 1])
        return np.stack([x, y], 1)
    return [c.mapped(f) for c in curves]


def _colour_sample(L: Layers, core: np.ndarray) -> dict:
    """Median stored sRGB of the element's full-strength ink (colour is sampled, too)."""
    inner = T.erode(core, 1)
    if inner.sum() < 4:
        inner = core
    if not inner.any():
        return {}
    rgb = L.src.rgb[inner]
    med = np.median(rgb, 0)
    p10 = np.percentile(rgb, 10, axis=0); p90 = np.percentile(rgb, 90, axis=0)
    return {"median_srgb": [round(float(v), 4) for v in med],
            "p10_srgb": [round(float(v), 4) for v in p10],
            "p90_srgb": [round(float(v), 4) for v in p90],
            "hex": "#%02X%02X%02X" % tuple(int(round(v * 255)) for v in med),
            "px": int(inner.sum())}


CONTOUR_DERIVED = ("contour: {kernel} x{up} interpolation of the unmixed {layer} ink "
                   "(normalised to full strength), half-level sub-pixel marching squares, "
                   "clamped cubic B-spline least-squares fit (knot {knot} source px, smooth "
                   "{smooth}; two passes: corners found on a first stiff fit, arm {arm2} px, "
                   "turn above {corner} deg), {refine}")
STROKE_DERIVED = ("stroke: centreline + width profile; every 0.25 source px the {layer} ink "
                  "across the rule (+-{half} mm) is integrated and divided by the "
                  "full-strength density, so the width is unbiased by blur; a gap only "
                  "where that integral is under {gap} source px")


def _stroke_record(r, fit):
    cx, cy = fit.px_to_mm(r["centre_px"][:, 0], r["centre_px"][:, 1])
    wmm = r["width_px"] / fit.ppmm
    on = r["width_px"] > RULE_GAP_WIDTH_PX
    runs = _runs(on)
    gaps = [round((b0 - a1) * r["step_px"] / fit.ppmm, 3) for (a0, a1), (b0, b1) in zip(runs, runs[1:])]
    return {"side": r["side"], "layer": r["layer"], "step_mm": round(r["step_px"] / fit.ppmm, 6),
            "centre_mm": np.round(np.stack([cx, cy], 1), 4).tolist(),
            "width_mm": np.round(wmm, 4).tolist(),
            "runs": len(runs), "gaps_mm": gaps,
            "min_width_on_mm": round(float(wmm[on].min()), 4) if on.any() else None,
            "median_width_mm": round(float(np.median(wmm[on])), 4) if on.any() else None}


KNOCKOUT_DERIVED = ("knock-out: a {kind} of paper erased from the traced red, fitted by "
                    "analysis by synthesis (props_lib.paperbomb_finefit {ver}): rendered "
                    "through the source PSF at full-strength density and moved (pattern "
                    "search) until it reproduces the observed red in its window; start "
                    "point from the reference's own paper deficit; replaces {n} traced "
                    "hole(s) the half-level contour had cut there")


def apply_knockouts(L: Layers, group: str, layer: str, curves: list) -> tuple:
    """Fit this group's sub-pixel knock-outs (paperbomb_finefit.KNOCKOUTS).  Returns the
    curves with the replaced traced holes dropped, the erase polygons (source px) and
    the JSON records."""
    specs = [k for k in FF.KNOCKOUTS if k["group"] == group and k["layer"] == layer]
    if not specs or not curves:
        return curves, [], []
    fit = L.fit
    samples = [c.sample(0.05) for c in curves]
    areas = [T.signed_area(q) for q in samples]
    sgn = float(np.sign(areas[int(np.argmax(np.abs(areas)))]))
    drop = set()
    count = {}
    for spec in specs:
        x0, y0, x1, y1 = FF.window_mm(spec)
        n = 0
        for i, (q, a) in enumerate(zip(samples, areas)):
            cx, cy = fit.px_to_mm(*q.mean(0))
            if (np.sign(a) != sgn and abs(a) / fit.ppmm ** 2 < FF.MAX_REPLACED_HOLE_MM2
                    and x0 <= cx <= x1 and y0 <= cy <= y1):
                drop.add(i)
                n += 1
        count[spec["name"]] = n
    kept = [c for i, c in enumerate(curves) if i not in drop]
    base = [c.sample(0.05) for c in kept]
    obs = layer_field(L, layer, behind=True)
    erase, recs = [], []
    for spec in specs:
        r = FF.fit_knockout(spec, base, obs, L.density[layer], fit)
        erase.append((float(r.get("soft_px", 0.0)), r["polys_px"]))
        mm = []
        for q in r["polys_px"]:
            x, y = fit.px_to_mm(q[:, 0], q[:, 1])
            mm.append(np.round(np.stack([x, y], 1), 5).tolist())
        recs.append({"name": spec["name"], "kind": spec["kind"],
                     "window_mm": [round(v, 3) for v in FF.window_mm(spec)],
                     "params_px": r["params_px"],
                     "loss": {"holes_removed": r["loss_traced_holes_removed"],
                              "init": r["loss_init"], "fit": r["loss_fit"]},
                     "replaced_traced_holes": count[spec["name"]],
                     "window_px": r["window_px"], "density": r["density"],
                     "soft_px": r.get("soft_px", 0.0),
                     "derived": KNOCKOUT_DERIVED.format(kind=spec["kind"], ver=FF.FINEFIT_VERSION,
                                                        n=count[spec["name"]]),
                     "polys_mm": mm})
    return kept, erase, recs


SPIKE_DERIVED = ("spike: the traced prong's end past a cut {cut} mm back along its axis "
                 "is erased and re-drawn as a tapered point (two cubic edges leaving the "
                 "cut along the traced contour's tangents, meeting in a sharp tip), fitted "
                 "by analysis by synthesis (props_lib.paperbomb_finefit {ver}): rendered "
                 "through the source PSF at full-strength density and moved (pattern "
                 "search) until it reproduces the observed red round the prong")


def apply_spikes(L: Layers, group: str, layer: str, curves: list) -> tuple:
    """Fit this group's prong-end spikes (paperbomb_finefit.SPIKES).  Returns the erase
    polygons, the ink polygons (source px) and the JSON records."""
    specs = [k for k in FF.SPIKES if k["group"] == group and k["layer"] == layer]
    if not specs or not curves:
        return [], [], []
    fit = L.fit
    loops = [c.sample(0.05) for c in curves]
    obs = layer_field(L, layer, behind=True)
    erase, ink, recs = [], [], []

    def mm(q):
        x, y = fit.px_to_mm(q[:, 0], q[:, 1])
        return np.round(np.stack([x, y], 1), 5).tolist()
    for spec in specs:
        r = FF.fit_spike(spec, loops, obs, L.density[layer], fit)
        erase.append(r["cut_px"]); ink.append(r["ink_px"])
        recs.append({"name": spec["name"], "kind": "spike", "tip_mm": list(spec["tip_mm"]),
                     "cut_mm": spec["cut_mm"], "params_px": r["params_px"],
                     "loss": {"traced": r["loss_traced"], "init": r["loss_init"], "fit": r["loss_fit"]},
                     "window_px": r["window_px"], "density": r["density"],
                     "derived": SPIKE_DERIVED.format(cut=spec["cut_mm"], ver=FF.FINEFIT_VERSION),
                     "erase_mm": mm(r["cut_px"]), "ink_mm": mm(r["ink_px"])})
    return erase, ink, recs


def trace_all(source: str | None = None, only: Sequence[str] | None = None,
              refine: bool = True, log=print, variant: dict | None = None) -> tuple:
    """Trace every group, score every element.  Returns (json dict, fields, layers).

    ``variant`` overrides the contour tracer for benchmarking (keys of ``trace_contour``:
    factor, kind, knot, iters, spline)."""
    L = load_layers(source)
    fit = L.fit
    H, W = L.black.shape
    masks = group_masks(L)
    regions = group_regions(L, masks)
    szone = stroke_zone(L)
    groups_out = []
    polys_by_layer = {"black": [], "red": []}
    erase_by_layer = {"black": [], "red": []}
    soft_by_layer = {"black": [], "red": []}
    ink_by_layer = {"black": [], "red": []}
    kw = dict(variant or {})
    for (g, layer) in sorted(masks, key=lambda k: (k[1], k[0])):
        if g == "unassigned":
            continue
        if only and g not in only:
            continue
        region = regions[(g, layer)]
        entry = {"group": g, "layer": layer}
        if g == FRAME:
            # thin rule runs as strokes, everything else of the frame as contours
            cregion = region & ~szone
            curves, info = trace_contour(L, layer, cregion, refine=refine, **kw) \
                if cregion.any() and masks[(g, layer)][cregion].any() else ([], {"loops": 0})
            sgn = 1.0
            if curves:
                areas = [T.signed_area(c.sample(0.1)) for c in curves]
                sgn = float(np.sign(areas[int(np.argmax(np.abs(areas)))]))
            strokes = []
            spolys = []
            # THE BLACK RULE RUNS OUT DRY.  The black middle of the top rule thins and
            # greys out past its half-strength end (a 0.1 mm hair of ink reads ~0.35 at
            # the source's grid) and then lifts; a stroke limited to the half-strength
            # component's region stopped where the ink first fell under half, and the
            # grey run beyond was left to the residual (a bristle splay) and to the paper
            # (grey dashes).  The black stroke integrates the whole rule band instead,
            # clear of every other group's black ink, so its width runs down to a hair
            # exactly as the reference thins, and it lifts only where the reference lifts.
            # Only a rule that HAS a black run (a half-strength black component on it) is
            # extended; the other rules' faint dark edge unmixes as a trace of black and
            # must stay red.
            others = np.zeros_like(region)
            for (g2, l2), m2 in masks.items():
                if l2 == layer and g2 != FRAME:
                    others |= m2
            for side in ("L", "R", "T", "B"):
                sregion = region
                if layer == "black":
                    zs = side_stroke_zone(L, side)
                    if (masks[(g, layer)] & zs).any():
                        sregion = region | (zs & ~T.dilate(others, 2))
                r = trace_rule(L, layer, side, sregion)
                if not (r["width_px"] > RULE_GAP_WIDTH_PX).any():
                    continue
                strokes.append(_stroke_record(r, fit))
                spolys += stroke_polys(r["centre_px"], r["width_px"], RULE_GAP_WIDTH_PX)
            spolys = _orient(spolys, sgn)
            for rec in strokes:
                rec["winding"] = sgn
            entry["curves_mm"] = [c.to_json() for c in _curves_px_to_mm(curves, fit)]
            entry["strokes_mm"] = strokes
            s_erase, s_ink, s_recs = apply_spikes(L, g, layer, curves)
            if s_recs:
                entry["spikes_mm"] = s_recs
                erase_by_layer[layer] += s_erase
                ink_by_layer[layer] += s_ink
            entry["trace"] = info
            entry["derived"] = [
                CONTOUR_DERIVED.format(kernel=KERNEL, up=UPSAMPLE, layer=layer, knot=KNOT_PX,
                                       corner=int(CORNER2_DEG), smooth=SMOOTH, arm2=CORNER2_ARM_PX,
                                       refine=("analysis-by-synthesis refinement, %d iterations, "
                                               "source PSF box + Gaussian %.1f px"
                                               % (REFINE_ITERS, T.SOURCE_PSF_SIGMA_PX))
                                       if refine else "no refinement")
                + " - corner flourishes, the small seal's box, rule stubs inside the corner boxes",
                STROKE_DERIVED.format(layer=layer, half=RULE_STROKE_HALF_MM,
                                      gap=RULE_GAP_WIDTH_PX)
                + " - the four rules between the corner boxes"]
            polys = [c.sample(0.05) for c in curves] + spolys
        else:
            curves, info = trace_contour(L, layer, region, refine=refine, **kw)
            curves, erase, ko = apply_knockouts(L, g, layer, curves)
            for soft, ps in erase:
                if soft > 0.0:
                    soft_by_layer[layer].append((soft, ps))
                else:
                    erase_by_layer[layer] += ps
            entry["curves_mm"] = [c.to_json() for c in _curves_px_to_mm(curves, fit)]
            if ko:
                entry["knockouts_mm"] = ko
            entry["trace"] = info
            entry["derived"] = [CONTOUR_DERIVED.format(
                kernel=kw.get("kind", KERNEL), up=kw.get("factor", UPSAMPLE), layer=layer,
                knot=kw.get("knot", KNOT_PX), corner=int(CORNER2_DEG), smooth=SMOOTH, arm2=CORNER2_ARM_PX,
                refine=("analysis-by-synthesis refinement, %d iterations, source PSF box + "
                        "Gaussian %.1f px" % (kw.get("iters", REFINE_ITERS), T.SOURCE_PSF_SIGMA_PX))
                if refine else "no refinement")]
            polys = [c.sample(0.05) for c in curves]
        entry["colour"] = _colour_sample(L, masks[(g, layer)])
        polys_by_layer[layer] += polys
        secs = entry["trace"].pop("secs", "")          # timing stays out of the JSON
        log("  traced %-10s %-5s loops %3s  strokes %s  (%s s)"
            % (g, layer, entry["trace"].get("loops"), len(entry.get("strokes_mm", [])), secs))
        groups_out.append(entry)

    # ---- scoring, per element, on the source's grid ------------------------------------
    pred = {}
    obs = {}
    for layer in ("black", "red"):
        box = compose_coverage(lambda ps: T.fill_polys(ps, H, W, ss=16),
                               polys_by_layer[layer], erase_by_layer[layer],
                               soft_by_layer[layer], ink_by_layer[layer])
        # in a knock-out window the ink is scored at the full strength its fit used (one
        # pigment at one load; the density field falls towards its floor among bars one
        # pixel wide, see paperbomb_finefit._Window)
        dens_s = L.density[layer].copy()
        for g_ in groups_out:
            if g_["layer"] != layer:
                continue
            for k in g_.get("knockouts_mm", []):
                x0, y0, x1, y1 = k["window_px"]
                dens_s[y0:y1, x0:x1] = k["density"]
        pred[layer] = {"box": box,
                       "psf": T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX) * dens_s}
        obs[layer] = layer_field(L, layer, behind=True)
    occluded = L.black > 0.85                          # red under solid black: unobservable
    eregs = element_regions(L, masks, regions)
    scores = []
    for e in ELEMENTS:
        if only and not (set(e.groups) & set(only)):
            continue
        rec = {"element": e.name, "label": e.label, "groups": list(e.groups), "layers": {}}
        for layer in ("black", "red"):
            if (e.name, layer) not in eregs:
                continue
            reg = eregs[(e.name, layer)]
            if layer == "red":
                reg = reg & ~occluded
            rec["layers"][layer] = score_fields(pred[layer]["psf"], obs[layer], reg, fit.ppmm)
        # both layers pooled: the element as a whole
        if len(rec["layers"]) == 2:
            ious = [(v.get("ink_px_obs", 0) + v.get("ink_px_pred", 0), v["iou"])
                    for v in rec["layers"].values() if v.get("iou") is not None]
            wsum = sum(w for w, _ in ious)
            rec["iou"] = round(sum(w * i for w, i in ious) / max(wsum, 1), 4)
            rec["edge_mean_px"] = round(float(np.mean([v["edge_mean_px"] for v in rec["layers"].values()
                                                       if "edge_mean_px" in v])), 4)
        else:
            v = next(iter(rec["layers"].values()))
            rec["iou"] = v.get("iou"); rec["edge_mean_px"] = v.get("edge_mean_px")
        scores.append(rec)
        log("  score  %-10s IoU %s  edge mean %s px  %s"
            % (e.name, rec["iou"], rec["edge_mean_px"],
               "  ".join("%s:p95 %s" % (k, v.get("edge_p95_px")) for k, v in rec["layers"].items())))
    unassigned = {layer: int(masks[("unassigned", layer)].sum())
                  for layer in ("black", "red") if ("unassigned", layer) in masks}
    out = {
        "format": "paperbomb_traced",
        "version": PB_TRACE_VERSION,
        "trace_lib": "props_lib.trace " + T.TRACE_VERSION,
        "provenance": provenance_record(L),
        "card_mm": [CARD_W_MM, CARD_H_MM],
        "units": "card millimetres, x from the left edge, y down from the top edge",
        "params": {"upsample": UPSAMPLE, "kernel": KERNEL, "iso": ISO, "knot_px": KNOT_PX,
                   "corner_deg": CORNER_DEG, "corner_arm_px": CORNER_ARM_PX,
                   "corner2_deg": CORNER2_DEG, "corner2_arm_px": CORNER2_ARM_PX, "smooth": SMOOTH, "refine_iters": REFINE_ITERS,
                   "max_piece_px": T.MAX_PIECE_PX, "psf_sigma_px": T.SOURCE_PSF_SIGMA_PX,
                   "min_loop_area_px2": MIN_LOOP_AREA_PX2,
                   "rule_gap_width_px": RULE_GAP_WIDTH_PX,
                   "rule_stroke_half_mm": RULE_STROKE_HALF_MM,
                   "black_rule_stroke_region": "rule band minus other groups' black ink",
                   "finefit": FF.FINEFIT_VERSION,
                   "variant": kw or None, "refine": refine},
        "unassigned_ink_px": unassigned,
        "groups": groups_out,
        "scores": scores,
    }
    fields = {"pred": pred, "obs": obs, "element_regions": eregs, "masks": masks,
              "polys_by_layer": polys_by_layer, "erase_by_layer": erase_by_layer,
              "soft_by_layer": soft_by_layer, "ink_by_layer": ink_by_layer}
    return out, fields, L


def provenance_record(L: Layers | None = None, source: str | None = None) -> dict:
    """The one source: path, SHA-256, size, card fit.  Goes in the JSON and the report."""
    if L is None:
        src = T.read_source(source)
        fit = T.fit_card(src)
    else:
        src, fit = L.src, L.fit
    rec = src.record()
    return {
        "method": "traced from the user's own design (the user asked for it to be traced)",
        "source": rec["path"],
        "source_sha256": rec["sha256"],
        "source_bytes": rec["bytes"],
        "source_px": [rec["width"], rec["height"]],
        "only_source": True,
        "card_fit": fit.record(),
    }


# ===========================================================================
# 7.  Storage
# ===========================================================================

def save_traced(data: dict, path: str = TRACED_JSON) -> str:
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt)
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


class TracedSourceMismatch(RuntimeError):
    """The traced shapes were not traced from the reference on disk."""


def load_traced(path: str = TRACED_JSON, verify_source: bool = True) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if verify_source:
        src = os.path.join(T.PROJECT_ROOT, data["provenance"]["source"])
        with open(src, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        if h != data["provenance"]["source_sha256"]:
            raise TracedSourceMismatch("%s was traced from sha256 %s but the reference on "
                                       "disk is %s" % (path, data["provenance"]["source_sha256"], h))
    return data


def group_polys_mm(entry: dict, step_mm: float = 0.01) -> list:
    """Closed polygons of one traced group in card mm, for any rasteriser (nonzero
    winding, |winding| clipped to 1: overlapping strokes and contours union)."""
    polys = []
    for cj in entry.get("curves_mm", []):
        c = T.Curve([np.asarray(p, np.float64) for p in cj["pieces"]], bool(cj["periodic"]))
        polys.append(c.sample(step_mm))
    for r in entry.get("strokes_mm", []):
        c = np.asarray(r["centre_mm"], np.float64)
        w = np.asarray(r["width_mm"], np.float64)
        ps = stroke_polys(c, w, RULE_GAP_WIDTH_PX / 3.917 * 0.999)
        polys += _orient(ps, r.get("winding", 1.0))
    return polys


def knockout_polys_mm(entry: dict) -> list:
    """The group's crisp erases (card mm): its fitted knock-outs laid crisp and its
    spikes' cuts - paper ERASED from its traced ink, coverage = traced x (1 - erase)."""
    out = []
    for k in entry.get("knockouts_mm", []):
        if float(k.get("soft_px", 0.0)) > 0.0:
            continue
        out += [np.asarray(q, np.float64) for q in k["polys_mm"]]
    for k in entry.get("spikes_mm", []):
        out.append(np.asarray(k["erase_mm"], np.float64))
    return out


def soft_knockouts_mm(entry: dict) -> list:
    """The group's knock-outs laid SOFT: [(soft_px (source px), [card-mm polygons])]."""
    return [(float(k["soft_px"]), [np.asarray(q, np.float64) for q in k["polys_mm"]])
            for k in entry.get("knockouts_mm", []) if float(k.get("soft_px", 0.0)) > 0.0]


def ink_polys_mm(entry: dict) -> list:
    """The group's re-drawn spike outlines (card mm): ink laid OVER the erased traced
    ink, coverage = max(traced x (1 - erase), ink)."""
    return [np.asarray(k["ink_mm"], np.float64) for k in entry.get("spikes_mm", [])]


def compose_coverage(fill, polys, erase, soft, ink, blur_scale: float = 1.0):
    """One layer's coverage: traced polygons x (1 - crisp erase) x (1 - soft erase), then
    the spike ink over it.  ``fill`` rasterises a polygon list on the target grid;
    ``soft`` is [(soft_px, polys)] with soft_px in source px, ``blur_scale`` the target
    grid's px per source px."""
    box = np.asarray(fill(polys), np.float64)
    if erase:
        box = box * (1.0 - np.asarray(fill(erase), np.float64))
    for sp, ps in soft:
        e = T.gauss_blur(np.asarray(fill(ps), np.float64), sp * blur_scale)
        box = box * (1.0 - np.clip(e, 0.0, 1.0))
    if ink:
        box = np.maximum(box, np.asarray(fill(ink), np.float64))
    return box


def stroke_only_polys_mm(entry: dict) -> list:
    """Only the stroke part of a group (the rules), card mm."""
    polys = []
    for r in entry.get("strokes_mm", []):
        c = np.asarray(r["centre_mm"], np.float64)
        w = np.asarray(r["width_mm"], np.float64)
        ps = stroke_polys(c, w, RULE_GAP_WIDTH_PX / 3.917 * 0.999)
        polys += _orient(ps, r.get("winding", 1.0))
    return polys


def contour_only_polys_mm(entry: dict, step_mm: float = 0.01) -> list:
    """Only the contour part of a group, card mm."""
    polys = []
    for cj in entry.get("curves_mm", []):
        c = T.Curve([np.asarray(q, np.float64) for q in cj["pieces"]], bool(cj["periodic"]))
        polys.append(c.sample(step_mm))
    return polys


def rasterise_mm(polys_mm: Sequence[np.ndarray], ppmm: float, pad_mm: float, H: int, W: int,
                 ss: int = 8) -> np.ndarray:
    """Exact-area coverage of card-mm polygons on a grid of ``ppmm`` with ``pad_mm`` of
    margin (pixel (i, j) covers card mm [j/ppmm - pad, ...))."""
    polys = [(np.asarray(p) + pad_mm) * ppmm for p in polys_mm]
    return T.fill_polys(polys, H, W, ss=ss)


# ===========================================================================
# 8.  The build's check: one source, reproducible, overlap within tolerance
# ===========================================================================

#: per-element tolerance on the traced shapes' overlap with the reference, at the
#: reference's own grid (IoU of the half-level regions, mean contour distance in px).
#: The emblem - the user's priority - is held tighter.  Rules are thin (0.1-0.9 mm, i.e.
#: 0.4-3.5 source px), where one pixel of IoU is a larger fraction.
OVERLAP_TOLERANCE = {"default": {"iou": 0.975, "edge_mean_px": 0.08},
                     "emblem": {"iou": 0.995, "edge_mean_px": 0.05, "edge_p95_px": 0.10},
                     "rules": {"iou": 0.965, "edge_mean_px": 0.08}}


def overlap_gates(data: dict) -> dict:
    out = {}
    for rec in data.get("scores", []):
        tol = OVERLAP_TOLERANCE.get(rec["element"], OVERLAP_TOLERANCE["default"])
        ok = rec.get("iou") is not None and rec["iou"] >= tol["iou"] \
            and (rec.get("edge_mean_px") or 0.0) <= tol["edge_mean_px"]
        if "edge_p95_px" in tol:
            ok = ok and all((v.get("edge_p95_px") or 0.0) <= tol["edge_p95_px"]
                            for v in rec["layers"].values())
        out[rec["element"]] = {"passed": bool(ok), "iou": rec.get("iou"),
                               "edge_mean_px": rec.get("edge_mean_px"), "tolerance": tol}
    return out


def verify_traced(path: str = TRACED_JSON, retrace: bool = True, log=None) -> dict:
    """What the build puts in its report: the stored shapes were traced from the reference
    on disk, a fresh trace reproduces them byte for byte, and every element's overlap is
    within ``OVERLAP_TOLERANCE``."""
    res = {"path": os.path.relpath(path, T.PROJECT_ROOT).replace("\\", "/")}
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        res["sha256"] = hashlib.sha256(raw).hexdigest()
        data = load_traced(path, verify_source=True)
        res["source_verified"] = True
        res["source"] = data["provenance"]["source"]
        res["source_sha256"] = data["provenance"]["source_sha256"]
    except Exception as exc:                                  # pragma: no cover
        res.update({"source_verified": False, "error": "%s: %s" % (type(exc).__name__, exc)})
        return res
    if retrace:
        t0 = time.time()
        fresh, _, _ = trace_all(log=log or (lambda *a: None))
        txt = json.dumps(fresh, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        res["retrace_sha256"] = hashlib.sha256(txt.encode("utf-8")).hexdigest()
        res["reproduces"] = res["retrace_sha256"] == res["sha256"]
        res["retrace_secs"] = round(time.time() - t0, 1)
    res["overlap"] = overlap_gates(data)
    res["overlap_passed"] = all(v["passed"] for v in res["overlap"].values())
    return res
