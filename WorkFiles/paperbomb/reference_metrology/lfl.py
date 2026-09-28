# -*- coding: utf-8 -*-
"""LIKE-FOR-LIKE INSTRUMENT, round 2 of the fidelity pass.

METROLOGY ONLY.  This file MEASURES References/PaperBomb/*.png; it never copies a
pixel of either guide into anything that ships, and nothing under Scripts/ imports it.
It exists because three separate instruments disagreed about V1 - on the paper grain's
correlation length (1.59 mm against 0.19 mm), on whether V1's corners carry black ink,
and on whether V1's flame encloses an eye - and a disagreement between instruments is
settled by running ONE instrument over BOTH sheets.

Everything below therefore:
  * loads V1 and our shipped base colour the same way (stored sRGB, 0..1),
  * resamples BOTH to a common 8.80 px/mm grid (V1's own scale, so the guide is never
    interpolated and our sheet is the one that moves),
  * classifies RED FIRST then black, as REFERENCE_SPEC's binarisation note requires,
  * and reports the same dictionary for each sheet.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread  # noqa: E402

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
V1 = os.path.join(ROOT, "References", "PaperBomb", "paperbomb_guide.png")
V2 = os.path.join(ROOT, "References", "PaperBomb", "paperbomb_guide_v2_real_glyphs.png")
BC = os.path.join(ROOT, "Exports", "PaperBomb", "Textures", "T_PaperBomb_BC.png")

CARD_W_MM, CARD_H_MM = 70.0, 156.0
GRID = 8.80                     # the common grid, px/mm


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def _read(path):
    a, _info = pngread.read_png(path)
    a = a.astype(np.float64) / (65535.0 if a.dtype == np.uint16 else 255.0)
    if a.ndim == 2:
        a = a[..., None]
    if a.shape[2] == 1:
        a = np.repeat(a, 3, axis=2)
    return a[..., :3]


def _tag_rect(a):
    """REFERENCE_SPEC's own tag-edge rule: half-maximum of the warmth transition."""
    warm = a[..., 0] - a[..., 2]
    hi = float(np.percentile(warm, 99.0))
    lo = float(np.percentile(warm, 1.0))
    m = warm > (lo + 0.5 * (hi - lo))
    ys = np.flatnonzero(m.any(axis=1))
    xs = np.flatnonzero(m.any(axis=0))
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def _resample(a, H, W):
    """Area-average resample to (H, W).  Down only; both sheets are bigger."""
    h, w = a.shape[:2]
    yi = np.arange(H + 1) * (h / float(H))
    xi = np.arange(W + 1) * (w / float(W))
    cs = np.cumsum(np.cumsum(np.pad(a, ((1, 0), (1, 0), (0, 0))), 0), 1)

    def at(y, x):
        y = np.clip(y, 0, h)
        x = np.clip(x, 0, w)
        y0 = np.floor(y).astype(int)
        x0 = np.floor(x).astype(int)
        fy = (y - y0)[:, None, None]
        fx = (x - x0)[None, :, None]
        y1 = np.minimum(y0 + 1, h)
        x1 = np.minimum(x0 + 1, w)
        c00 = cs[y0][:, x0]
        c01 = cs[y0][:, x1]
        c10 = cs[y1][:, x0]
        c11 = cs[y1][:, x1]
        return (c00 * (1 - fy) * (1 - fx) + c01 * (1 - fy) * fx
                + c10 * fy * (1 - fx) + c11 * fy * fx)

    c = at(yi, xi)
    s = c[1:, 1:] - c[:-1, 1:] - c[1:, :-1] + c[:-1, :-1]
    area = (np.diff(yi)[:, None, None] * np.diff(xi)[None, :, None])
    return s / np.maximum(area, 1e-9)


def load_sheet(which):
    """(rgb_stored, ppmm) on the common grid, card only."""
    H = int(round(CARD_H_MM * GRID))
    W = int(round(CARD_W_MM * GRID))
    if which == "ours":
        b = _read(BC)
        PPMM = 12.923
        OX = OY = 16            # the island padding, 1.6 mm at 12.923 px/mm
        card = b[OY:OY + int(round(CARD_H_MM * PPMM)),
                 OX:OX + int(round(CARD_W_MM * PPMM))]
    else:
        a = _read(V1 if which == "V1" else V2)
        x0, y0, x1, y1 = _tag_rect(a)
        card = a[y0:y1, x0:x1]
    return _resample(card, H, W), GRID


# ---------------------------------------------------------------------------
# classification - RED FIRST, then black (REFERENCE_SPEC section 2)
# ---------------------------------------------------------------------------

def _luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _hsv(rgb):
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    d = mx - mn
    s = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-9
    idx = m & (mx == r)
    h[idx] = (60.0 * ((g - b) / np.maximum(d, 1e-9)))[idx] % 360.0
    idx = m & (mx == g)
    h[idx] = (60.0 * (2.0 + (b - r) / np.maximum(d, 1e-9)))[idx]
    idx = m & (mx == b)
    h[idx] = (60.0 * (4.0 + (r - g) / np.maximum(d, 1e-9)))[idx]
    return h, s, mx


def classify(rgb):
    """(paper, red, black) masks.  RED FIRST: a deep seal red is darker than any
    sensible black threshold, so black is what is left AFTER red is taken."""
    h, s, v = _hsv(rgb)
    lum = _luma(rgb)
    pap0 = (s < 0.28) & (lum > 0.62)
    paper_v = float(np.median(v[pap0])) if pap0.any() else 0.9
    paper_lum = float(np.median(lum[pap0])) if pap0.any() else 0.8
    warm = (h < 26.0) | (h > 330.0)
    red = warm & (s > 0.42) & (v > 0.10)
    black = (~red) & (lum < 0.45 * paper_lum)
    return {"paper_v": paper_v, "paper_lum": paper_lum,
            "red": red, "black": black, "ink": red | black,
            "h": h, "s": s, "v": v, "lum": lum}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def label_cc(mask):
    """8-connected labelling by two raster passes with union-find."""
    m = np.asarray(mask, bool)
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(H):
        row = m[y]
        if not row.any():
            continue
        prev = lab[y - 1] if y else None
        for x in np.flatnonzero(row):
            ns = []
            if x and lab[y, x - 1]:
                ns.append(int(lab[y, x - 1]))
            if prev is not None:
                for xx in (x - 1, x, x + 1):
                    if 0 <= xx < W and prev[xx]:
                        ns.append(int(prev[xx]))
            if ns:
                a = min(ns)
                lab[y, x] = a
                for b in ns:
                    union(a, b)
            else:
                parent.append(nxt)
                lab[y, x] = nxt
                nxt += 1
    if nxt == 1:
        return lab, 0
    root = np.array([find(i) for i in range(nxt)], np.int32)
    order = {}
    out = np.zeros(nxt, np.int32)
    for i in range(1, nxt):
        r = int(root[i])
        if r not in order:
            order[r] = len(order) + 1
        out[i] = order[r]
    return out[lab], len(order)


def runs(flags):
    f = np.asarray(flags, bool)
    if not f.any():
        return []
    d = np.diff(f.astype(np.int8))
    st = list(np.flatnonzero(d == 1) + 1)
    sp = list(np.flatnonzero(d == -1) + 1)
    if f[0]:
        st.insert(0, 0)
    if f[-1]:
        sp.append(len(f))
    return list(zip(st, sp))


def box(a, r):
    p = np.pad(a.astype(np.float64), r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    return s / (n * n)
