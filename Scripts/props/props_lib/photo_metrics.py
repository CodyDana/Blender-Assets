"""What a PHOTOGRAPH of the card shows, at the reference's own resolution.

ROUND 7.  The independent auditor's headline finding was that every rule gate measured
the DRAWING and not the photograph: the gates read the authored raster at 12.42 px/mm,
where a hairline of thin ink still registers, and passed a border that the shipped render
showed 27.8 % bare on its top side with a 9.5 mm hole.  The reference of record is a
274 x 636 pixel image of the card (3.914 px/mm), so its own figures - 12.7 % bare, a
6.64 mm worst break - are figures AT THAT RESOLUTION, and a raster four times finer can
never be compared with them directly.

So this module measures any image of the card - our base-colour map, our gallery render,
or the reference itself - the same way:

1. area-resample the card's box onto the reference's own 274 x 636 grid;
2. classify ink with thresholds RELATIVE to that image's own paper level (red where the
   redness exceeds 0.449 of the paper luma, black where the luma is under half of it) -
   the reference's absolute thresholds, 0.4045 and 0.450, are exactly those fractions of
   its 0.900 paper, and a rendered sheet under studio light sits at 0.77 rather than 0.90;
3. measure the rules, the ring and the ink exactly as the auditor's instrument did.

The numbers in :data:`REFERENCE` are the reference image put through THIS code
(``WorkFiles/paperbomb/claudeR3/photo_reference.json``), not typed in from anywhere
else, and they reproduce the auditor's own figures for the same quantities.  Nothing
here is ever an input to the drawing: it reads what was drawn, or what was rendered.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np

REF_W_PX, REF_H_PX = 274, 636
CARD_W_MM = 70.0
PPMM_REF = REF_W_PX / CARD_W_MM                  # 3.914 px/mm
RED_OF_PAPER = 0.4492                             # 0.4045 / 0.9004 on the reference
BLACK_OF_PAPER = 0.50


def luma(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def redness(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] - 0.5 * (rgb[..., 1] + rgb[..., 2])


def area_resample(a: np.ndarray, tw: int = REF_W_PX, th: int = REF_H_PX) -> np.ndarray:
    """Box-average resample - what a lower-resolution photograph of the same sheet sees."""
    h, w = a.shape[:2]
    ys = np.arange(th + 1) * h / th
    xs = np.arange(tw + 1) * w / tw
    a3 = a[..., None] if a.ndim == 2 else a
    cs = np.cumsum(np.cumsum(np.pad(a3.astype(np.float64), ((1, 0), (1, 0), (0, 0))), 0), 1)

    def at(Y, X):
        Yi = np.clip(np.round(Y).astype(int), 0, h)
        Xi = np.clip(np.round(X).astype(int), 0, w)
        return cs[Yi[:, None], Xi[None, :], :]

    S = at(ys[1:], xs[1:]) - at(ys[:-1], xs[1:]) - at(ys[1:], xs[:-1]) + at(ys[:-1], xs[:-1])
    cnt = ((np.round(ys[1:]) - np.round(ys[:-1]))[:, None]
           * (np.round(xs[1:]) - np.round(xs[:-1]))[None, :])
    out = S / np.maximum(cnt, 1)[..., None]
    return out[..., 0] if a.ndim == 2 else out


def octagon_mask(h: int = REF_H_PX, w: int = REF_W_PX, clip_mm: float = 8.05,
                 card_h_mm: float = 162.29) -> np.ndarray:
    """The card's own outline on a grid that exactly spans its box."""
    yy = (np.arange(h)[:, None] + 0.5) / h * card_h_mm
    xx = (np.arange(w)[None, :] + 0.5) / w * CARD_W_MM
    c = clip_mm
    out = ((xx + yy >= c) & ((CARD_W_MM - xx) + yy >= c)
           & (xx + (card_h_mm - yy) >= c) & ((CARD_W_MM - xx) + (card_h_mm - yy) >= c))
    return out


def _label(mask: np.ndarray) -> Tuple[np.ndarray, int]:
    from .art_metrics import label_cc
    return label_cc(mask)


def classify(srgb: np.ndarray, mask: np.ndarray) -> Dict[str, np.ndarray]:
    lum = luma(srgb)
    red = redness(srgb)
    vals = lum[mask]
    hist, e = np.histogram(vals, bins=256, range=(0.0, 1.0))
    ctr = 0.5 * (e[1:] + e[:-1])
    paper = float(ctr[int(np.argmax(np.where(ctr > 0.55, hist, 0)))])
    is_red = (red > RED_OF_PAPER * paper) & mask
    is_black = (lum < BLACK_OF_PAPER * paper) & ~is_red & mask
    return {"red": is_red, "black": is_black, "ink": is_red | is_black,
            "lum": lum, "paper": paper}


def _runs_bool(v: np.ndarray):
    out = []
    cur = 0
    for z in v:
        if z:
            cur += 1
        elif cur:
            out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out


def rule_frame(D: Dict[str, np.ndarray], ppmm: float = PPMM_REF) -> Dict[str, object]:
    """The four rules: where each one is, and how much of it a photograph sees as bare.

    Ported from the independent auditor's instrument without change of definition:
    each rule is the peak of ink per column (row) in the outer band of its side, and a
    station along it is BARE when no ink at all falls within +-1.6 mm of that peak -
    red, or the rule's own pooled near-black.  Only the stretch between the two cross
    rules is counted, so the corner ornaments are not scored as rule.
    """
    ink = D["ink"]
    h, w = ink.shape
    colsum = ink.sum(0).astype(float)
    rowsum = ink.sum(1).astype(float)

    def peak(profile, lo, hi):
        return lo + int(np.argmax(profile[lo:hi]))

    xl = peak(colsum, int(0.01 * w), int(0.14 * w))
    xr = peak(colsum, int(0.86 * w), int(0.99 * w))
    yt = peak(rowsum, int(0.01 * h), int(0.10 * h))
    yb = peak(rowsum, int(0.90 * h), int(0.99 * h))
    band = max(2, int(round(1.6 * ppmm)))
    sides = {}
    for key, axis, pos in (("L", "v", xl), ("R", "v", xr), ("T", "h", yt), ("B", "h", yb)):
        if axis == "v":
            sl = ink[yt:yb + 1, max(0, pos - band):pos + band + 1]
            widths = sl.sum(1).astype(float) / ppmm
        else:
            sl = ink[max(0, pos - band):pos + band + 1, xl:xr + 1]
            widths = sl.sum(0).astype(float) / ppmm
        zero = widths <= 1e-9
        runs = [r / ppmm for r in _runs_bool(zero)]
        nz = widths[widths > 0]
        sides[key] = {
            "zero_frac": round(float(zero.mean()), 4),
            "breaks": len(runs),
            "longest_break_mm": round(float(max(runs)) if runs else 0.0, 3),
            "breaks_mm": [round(r, 2) for r in sorted(runs, reverse=True)[:8]],
            "width_median_mm": round(float(np.median(nz)) if nz.size else 0.0, 3),
        }
    return {"insets_mm": [round(xl / ppmm, 2), round((w - 1 - xr) / ppmm, 2),
                          round(yt / ppmm, 2), round((h - 1 - yb) / ppmm, 2)],
            "sides": sides,
            "zero_frac_max": max(s["zero_frac"] for s in sides.values()),
            "longest_break_mm": max(s["longest_break_mm"] for s in sides.values())}


def ring_photo(D: Dict[str, np.ndarray], ppmm: float = PPMM_REF) -> Dict[str, object]:
    """The ring as ALL red ink in the central band, swept from its own bbox centre.

    The auditor's ring instrument, unchanged in definition: the hero's black strokes cut
    the annulus into arcs, so no single component is the ring.  Adds the one number the
    auditor showed was the most obvious difference at thumbnail size: how many texels of
    hero ink touch ring ink.
    """
    red = D["red"]
    h, w = red.shape
    band = np.zeros_like(red)
    band[int(0.20 * h):int(0.70 * h), int(0.075 * w):int(0.925 * w)] = True
    R = red & band
    ys, xs = np.nonzero(R)
    if ys.size == 0:
        return {"present": False}
    cx, cy = 0.5 * (xs.min() + xs.max()), 0.5 * (ys.min() + ys.max())
    NA = 720
    cov = np.zeros(NA, bool)
    inner = np.full(NA, np.nan)
    outer = np.full(NA, np.nan)
    rmax = 0.75 * max(w, h)
    ts = np.arange(1.0, rmax, 0.2)
    for i in range(NA):
        a = 2 * math.pi * i / NA
        X = np.round(cx + math.cos(a) * ts).astype(int)
        Y = np.round(cy + math.sin(a) * ts).astype(int)
        ok = (X >= 0) & (Y >= 0) & (X < w) & (Y < h)
        v = R[Y[ok], X[ok]]
        if v.any():
            idx = np.nonzero(v)[0]
            t2 = ts[ok]
            cov[i] = True
            inner[i] = t2[idx[0]]
            outer[i] = t2[idx[-1]]
    ok = ~np.isnan(inner)
    swept = (outer - inner)[ok] / ppmm
    best = cur = 0
    for v in np.concatenate([cov, cov]):
        cur = 0 if v else cur + 1
        best = max(best, cur)
    env = np.zeros_like(R)
    for i in range(NA):
        if np.isnan(inner[i]):
            continue
        a = 2 * math.pi * i / NA
        tt = np.arange(inner[i], outer[i] + 0.01, 0.2)
        X = np.round(cx + math.cos(a) * tt).astype(int)
        Y = np.round(cy + math.sin(a) * tt).astype(int)
        g = (X >= 0) & (Y >= 0) & (X < w) & (Y < h)
        env[Y[g], X[g]] = True
    holes = env & ~R & ~D["black"]
    hl, hn = _label(holes)
    el = []
    nh = 0
    if hn:
        areas = np.bincount(hl.ravel())
        for i in range(1, hn + 1):
            if areas[i] < 2:
                continue
            nh += 1
            yy, xx = np.nonzero(hl == i)
            if yy.size < 3:
                continue
            P = np.stack([xx - xx.mean(), yy - yy.mean()])
            ev = np.sqrt(np.maximum(np.linalg.eigvalsh(P @ P.T / yy.size), 1e-9))
            el.append(ev[1] / max(ev[0], 1e-6))
    # the hero: the largest black island in the middle band
    b = D["black"]
    keep = np.zeros_like(b)
    keep[int(0.28 * h):int(0.72 * h), :] = True
    lab, n = _label(b & keep)
    touch = 0
    hero_mm2 = 0.0
    if n:
        ar = np.bincount(lab.ravel())[1:]
        hm = lab == (int(np.argmax(ar)) + 1)
        hero_mm2 = float(hm.sum()) / ppmm ** 2
        grown = hm.copy()
        grown[1:, :] |= hm[:-1, :]; grown[:-1, :] |= hm[1:, :]
        grown[:, 1:] |= hm[:, :-1]; grown[:, :-1] |= hm[:, 1:]
        touch = int((grown & R).sum())
    return {
        "centre_mm": [round(cx / ppmm, 2), round(cy / ppmm, 2)],
        "red_ink_mm2": round(float(R.sum()) / ppmm ** 2, 1),
        "swept_median_mm": round(float(np.median(swept)), 3),
        "swept_p05_mm": round(float(np.percentile(swept, 5)), 3),
        "swept_p95_mm": round(float(np.percentile(swept, 95)), 3),
        "swept_cv": round(float(swept.std() / max(swept.mean(), 1e-9)), 3),
        "coverage": round(float(cov.mean()), 4),
        "longest_gap_deg": round(best * 360.0 / NA, 2),
        "holes": nh,
        "paper_through": round(float(holes.sum()) / max(float(env.sum()), 1.0), 4),
        "hole_elongation": round(float(np.median(el)) if el else 0.0, 3),
        "hero_mm2": round(hero_mm2, 1),
        "hero_touch_px": touch,
    }


def measure(srgb_card: np.ndarray, card_h_mm: float = 162.29,
            mask: Optional[np.ndarray] = None, resample: bool = True) -> Dict[str, object]:
    """Everything above, on one image whose array spans exactly the card's box."""
    img = area_resample(srgb_card) if resample else srgb_card
    if mask is None:
        mask = octagon_mask(img.shape[0], img.shape[1], card_h_mm=card_h_mm)
    D = classify(img, mask)
    area = float(mask.sum())
    return {
        "grid_px": [int(img.shape[1]), int(img.shape[0])],
        "paper_luma": round(D["paper"], 4),
        "ink": {"red": round(float(D["red"].sum()) / area, 5),
                "black": round(float(D["black"].sum()) / area, 5),
                "total": round(float(D["ink"].sum()) / area, 5)},
        "rules": rule_frame(D),
        "ring": ring_photo(D),
    }


#: The reference of record through :func:`measure`, run on its own 274 x 636 card box
#: (``resample=False``: it is already on its own grid).  Recorded by
#: ``WorkFiles/paperbomb/claudeR3/photo_reference.json``; see the module docstring.
REFERENCE: Dict[str, object] = {
    "grid_px": [
        274,
        636
    ],
    "paper_luma": 0.9004,
    "ink": {
        "red": 0.11634,
        "black": 0.18493,
        "total": 0.30127
    },
    "rules": {
        "insets_mm": [
            3.58,
            3.83,
            6.64,
            7.15
        ],
        "sides": {
            "L": {
                "zero_frac": 0.0893,
                "breaks": 11,
                "longest_break_mm": 3.832,
                "breaks_mm": [
                    3.83,
                    1.79,
                    1.53,
                    1.28,
                    1.28,
                    1.28,
                    0.51,
                    0.51
                ],
                "width_median_mm": 0.766
            },
            "R": {
                "zero_frac": 0.0997,
                "breaks": 13,
                "longest_break_mm": 4.088,
                "breaks_mm": [
                    4.09,
                    1.79,
                    1.53,
                    1.28,
                    1.28,
                    1.02,
                    0.77,
                    0.77
                ],
                "width_median_mm": 0.511
            },
            "T": {
                "zero_frac": 0.1265,
                "breaks": 3,
                "longest_break_mm": 6.642,
                "breaks_mm": [
                    6.64,
                    0.77,
                    0.51
                ],
                "width_median_mm": 0.511
            },
            "B": {
                "zero_frac": 0.151,
                "breaks": 7,
                "longest_break_mm": 2.555,
                "breaks_mm": [
                    2.55,
                    2.55,
                    1.79,
                    1.02,
                    0.77,
                    0.51,
                    0.26
                ],
                "width_median_mm": 0.766
            }
        },
        "zero_frac_max": 0.151,
        "longest_break_mm": 6.642
    },
    "ring": {
        "centre_mm": [
            35.0,
            79.07
        ],
        "red_ink_mm2": 642.0,
        "swept_median_mm": 5.161,
        "swept_p05_mm": 2.453,
        "swept_p95_mm": 7.511,
        "swept_cv": 0.314,
        "coverage": 0.9597,
        "longest_gap_deg": 6.5,
        "holes": 56,
        "paper_through": 0.273,
        "hole_elongation": 2.228,
        "hero_mm2": 806.4,
        "hero_touch_px": 22
    }
}

#: Tolerances.  Two-sided wherever the reference sits in the middle of a range: a rule
#: with LESS bare paper than the reference is as wrong as one with more.
TOL = {
    "zero_frac": 0.050,          # per side, absolute
    "longest_break_mm": 1.00,    # per side, over the reference's own worst
    "breaks": (6, 4),            # per side, fewer / more than the reference
    "ink_total_rel": 0.08, "ink_red_rel": 0.12, "ink_black_rel": 0.10,
    "ring_swept_median_mm": 0.50, "ring_swept_p05_mm": 0.90, "ring_cv_over": 0.10,
    "ring_paper_through": 0.06, "ring_elongation_over": 0.45, "ring_red_rel": 0.12,
    "ring_coverage_min": 0.93, "hero_touch_px_max": 60,
    # the gallery render is lit and slightly curled; its rules get a little more room
    "render_zero_frac": 0.070, "render_longest_break_mm": 1.60,
}


def gates(m: Dict[str, object], ref: Optional[Dict[str, object]] = None,
          render: bool = False) -> Dict[str, bool]:
    """Pass / fail for one measured image against the reference through the same code."""
    ref = ref or REFERENCE
    g: Dict[str, bool] = {}
    if not ref:
        return {"p00_reference_recorded": False}
    rs, qs = (m.get("rules") or {}).get("sides") or {}, ref["rules"]["sides"]
    zf = TOL["render_zero_frac"] if render else TOL["zero_frac"]
    lb = TOL["render_longest_break_mm"] if render else TOL["longest_break_mm"]
    ok_zero = ok_long = ok_n = True
    for k in "LRTB":
        s, q = rs.get(k) or {}, qs[k]
        ok_zero &= abs(float(s.get("zero_frac", 9.0)) - float(q["zero_frac"])) <= zf
        ok_long &= float(s.get("longest_break_mm", 99.0)) <= float(q["longest_break_mm"]) + lb
        lo, hi = TOL["breaks"]
        ok_n &= (int(q["breaks"]) - lo) <= int(s.get("breaks", -99)) <= (int(q["breaks"]) + hi)
    pre = "r" if render else "p"
    g[pre + "01_rule_bare_fraction_per_side"] = bool(ok_zero)
    g[pre + "02_rule_longest_break_per_side"] = bool(ok_long)
    if render:
        return g
    g["p03_rule_break_count_per_side"] = bool(ok_n)
    mi, ri = m["ink"], ref["ink"]
    g["p04_ink_as_photographed"] = bool(
        abs(mi["total"] / ri["total"] - 1.0) <= TOL["ink_total_rel"]
        and abs(mi["red"] / ri["red"] - 1.0) <= TOL["ink_red_rel"]
        and abs(mi["black"] / ri["black"] - 1.0) <= TOL["ink_black_rel"])
    mr, rr = m["ring"], ref["ring"]
    g["p05_ring_band_as_photographed"] = bool(
        abs(mr["swept_median_mm"] - rr["swept_median_mm"]) <= TOL["ring_swept_median_mm"]
        and mr["swept_p05_mm"] >= rr["swept_p05_mm"] - TOL["ring_swept_p05_mm"]
        and mr["swept_cv"] <= rr["swept_cv"] + TOL["ring_cv_over"]
        and abs(mr["red_ink_mm2"] / rr["red_ink_mm2"] - 1.0) <= TOL["ring_red_rel"])
    g["p06_ring_kasure_as_photographed"] = bool(
        abs(mr["paper_through"] - rr["paper_through"]) <= TOL["ring_paper_through"]
        and mr["hole_elongation"] <= rr["hole_elongation"] + TOL["ring_elongation_over"]
        and mr["coverage"] >= TOL["ring_coverage_min"])
    g["p07_hero_inside_the_ring_not_over_it"] = bool(
        mr["hero_touch_px"] <= TOL["hero_touch_px_max"])
    return g


def measure_bc_front(base_colour_linear: np.ndarray, ppmm: float, pad_mm: float,
                     card_h_mm: float) -> Dict[str, object]:
    """Our drawn front's base colour (LINEAR, with its island padding) as a photograph."""
    lin = np.clip(np.asarray(base_colour_linear, np.float64), 0.0, 1.0)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    x0 = int(round(pad_mm * ppmm))
    y0 = int(round(pad_mm * ppmm))
    x1 = x0 + int(round(CARD_W_MM * ppmm))
    y1 = y0 + int(round(card_h_mm * ppmm))
    return measure(srgb[y0:y1, x0:x1], card_h_mm=card_h_mm)


def measure_render(render_srgb: np.ndarray, card_mask: np.ndarray,
                   card_h_mm: float) -> Dict[str, object]:
    """The flat front RENDER, cropped to the card's own silhouette box."""
    ys, xs = np.nonzero(card_mask)
    crop = render_srgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    small_mask = area_resample(card_mask[ys.min():ys.max() + 1,
                                         xs.min():xs.max() + 1].astype(np.float64)) > 0.5
    img = area_resample(crop)
    D = classify(img, small_mask)
    return {"grid_px": [int(img.shape[1]), int(img.shape[0])],
            "paper_luma": round(D["paper"], 4),
            "crop_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "rules": rule_frame(D)}


__all__ = ["measure", "measure_bc_front", "measure_render", "gates", "REFERENCE", "TOL",
           "area_resample", "octagon_mask", "classify", "rule_frame", "ring_photo"]
