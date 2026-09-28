# -*- coding: utf-8 -*-
"""REAL-GLYPH PRIMARY METROLOGY - shared loading / geometry.

METROLOGY ONLY.  Reads References/PaperBomb/*.png and emits NUMBERS.
Nothing here writes artwork a build could consume; nothing under Scripts/
imports it.  Debug rasters go only to reference_metrology/debug/ and are
labelled DEBUG - NEVER SHIP.

AUTHORITY: paperbomb_guide_v2_real_glyphs.png (300 x 653, real kanji) is the
reference of record.  paperbomb_guide.png (1024 x 1536) is consulted ONLY for
sub-pixel character and never to override a position, size, weight, colour or
shape.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread  # noqa: E402

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
RG = os.path.join(ROOT, "References", "PaperBomb",
                  "paperbomb_guide_v2_real_glyphs.png")   # PRIMARY
HR = os.path.join(ROOT, "References", "PaperBomb", "paperbomb_guide.png")  # texture only
DEBUG = os.path.join(HERE, "debug")

CARD_W_MM = 70.0          # product decision: width is fixed


def read_stored(path):
    a, info = pngread.read_png(path)
    a = a.astype(np.float64) / (65535.0 if a.dtype == np.uint16 else 255.0)
    if a.ndim == 2:
        a = a[..., None]
    if a.shape[2] == 1:
        a = np.repeat(a, 3, axis=2)
    return a[..., :3], info


def luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def warmth(rgb):
    return rgb[..., 0] - rgb[..., 2]


def hsv(rgb):
    mx = rgb.max(axis=-1); mn = rgb.min(axis=-1); d = mx - mn
    s = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    nz = d > 1e-9
    idx = nz & (mx == r); h[idx] = ((g - b)[idx] / d[idx]) % 6
    idx = nz & (mx == g); h[idx] = ((b - r)[idx] / d[idx]) + 2
    idx = nz & (mx == b); h[idx] = ((r - g)[idx] / d[idx]) + 4
    return h * 60.0, s, mx


# ------------------------------------------------------------------ morphology
def _shift_or(m, dy, dx):
    out = np.zeros_like(m); h, w = m.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def dilate(m, r=1):
    for _ in range(r):
        acc = m.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                acc |= _shift_or(m, dy, dx)
        m = acc
    return m


def erode(m, r=1):
    return ~dilate(~m, r)


def close_(m, r=1):
    return erode(dilate(m, r), r)


def open_(m, r=1):
    return dilate(erode(m, r), r)


def label(mask):
    """Connected components, 8-connected. Returns (labels, comps sorted by area)."""
    h, w = mask.shape
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb: parent[rb] = ra
            else:       parent[ra] = rb

    rows = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            rows.append([]); continue
        d = np.diff(row.astype(np.int8))
        st = list(np.flatnonzero(d == 1) + 1)
        en = list(np.flatnonzero(d == -1) + 1)
        if row[0]: st.insert(0, 0)
        if row[-1]: en.append(w)
        runs = []; prev = rows[y - 1] if y else []; pi = 0
        for s, e in zip(st, en):
            lbl = 0
            while pi < len(prev) and prev[pi][1] < s:
                pi += 1
            j = pi
            while j < len(prev) and prev[j][0] <= e:
                if lbl == 0: lbl = prev[j][2]
                else:        union(lbl, prev[j][2])
                j += 1
            if lbl == 0:
                lbl = len(parent); parent.append(lbl)
            runs.append((s, e, lbl))
        rows.append(runs)
    remap = {}; labels = np.zeros((h, w), np.int32); comps = {}
    for y, runs in enumerate(rows):
        for s, e, l in runs:
            r = find(l)
            if r not in remap: remap[r] = len(remap) + 1
            ll = remap[r]; labels[y, s:e] = ll
            c = comps.setdefault(ll, dict(n=0, x0=w, x1=-1, y0=h, y1=-1, sx=0.0, sy=0.0))
            n = e - s
            c['n'] += n
            c['x0'] = min(c['x0'], s); c['x1'] = max(c['x1'], e - 1)
            c['y0'] = min(c['y0'], y); c['y1'] = max(c['y1'], y)
            c['sx'] += (s + e - 1) * n / 2.0; c['sy'] += y * n
    out = []
    for ll, c in comps.items():
        out.append(dict(label=ll, n=c['n'], x0=c['x0'], x1=c['x1'], y0=c['y0'], y1=c['y1'],
                        cx=c['sx'] / c['n'], cy=c['sy'] / c['n']))
    out.sort(key=lambda d: -d['n'])
    return labels, out


def fill_holes(m):
    inv = ~m
    lab, comps = label(inv)
    bg = None
    for c in comps:
        if c['x0'] == 0 and c['y0'] == 0:
            bg = c['label']; break
    if bg is None:
        bg = comps[0]['label']
    return ~(lab == bg)


# ------------------------------------------------------------------- fitting
def fit_line_pts(p, q):
    """Least squares q = a*p + b -> (a, b, residuals)."""
    A = np.stack([p, np.ones_like(p)], 1)
    sol, *_ = np.linalg.lstsq(A, q, rcond=None)
    res = q - A @ sol
    return float(sol[0]), float(sol[1]), res


def robust_fit(p, q, iters=3, k=2.5):
    a, b, res = fit_line_pts(p, q)
    keep = np.ones(len(p), bool)
    for _ in range(iters):
        s = np.std(res[keep]) if keep.sum() > 3 else 0.0
        if s < 1e-9:
            break
        keep = np.abs(res) < k * s
        if keep.sum() < 4:
            break
        a, b, _ = fit_line_pts(p[keep], q[keep])
        res = q - (a * p + b)
    return a, b, res, keep


def save_debug(arr, name, scale=1):
    """arr HxWx3 float 0..1 stored. Writes debug/DEBUG_NEVER_SHIP_<name>.png"""
    import bpy
    a = np.clip(arr, 0, 1)
    if scale > 1:
        a = np.repeat(np.repeat(a, scale, 0), scale, 1)
    h, w = a.shape[:2]
    a = np.concatenate([a, np.ones((h, w, 1))], 2)
    img = bpy.data.images.new("DEBUG_NEVER_SHIP", w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(a[::-1].astype(np.float32).ravel())
    p = os.path.join(DEBUG, "DEBUG_NEVER_SHIP_RG_%s.png" % name)
    img.filepath_raw = p
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return p
