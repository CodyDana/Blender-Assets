# -*- coding: utf-8 -*-
"""Shared metrology helpers. MEASUREMENT ONLY - emits numbers.
Nothing here writes artwork that a build could consume."""
import numpy as np


def load_stored(path):
    """HxWx4 float32 of STORED (non-colour-managed) 0..1 values, row 0 = top."""
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a


def lum(rgb):
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def sat(rgb):
    return rgb.max(axis=-1) - rgb.min(axis=-1)


# ---------------------------------------------------------------- morphology
def _shift_or(m, dy, dx):
    out = np.zeros_like(m)
    h, w = m.shape
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


# ------------------------------------------- run-based connected components
def label_components(mask):
    """Return (labels int32 HxW, list of dicts per component)."""
    h, w = mask.shape
    parent = [0]
    runs_by_row = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for y in range(h):
        row = mask[y]
        if not row.any():
            runs_by_row.append([])
            continue
        d = np.diff(row.astype(np.int8))
        starts = list(np.nonzero(d == 1)[0] + 1)
        ends = list(np.nonzero(d == -1)[0] + 1)
        if row[0]:
            starts.insert(0, 0)
        if row[-1]:
            ends.append(w)
        runs = []
        prev = runs_by_row[y - 1] if y else []
        pi = 0
        for s, e in zip(starts, ends):
            lbl = 0
            while pi < len(prev) and prev[pi][1] < s:
                pi += 1
            j = pi
            while j < len(prev) and prev[j][0] <= e:
                if lbl == 0:
                    lbl = prev[j][2]
                else:
                    union(lbl, prev[j][2])
                j += 1
            if lbl == 0:
                lbl = len(parent)
                parent.append(lbl)
            runs.append((s, e, lbl))
        runs_by_row.append(runs)

    remap = {}
    labels = np.zeros((h, w), dtype=np.int32)
    comps = {}
    for y, runs in enumerate(runs_by_row):
        for s, e, l in runs:
            r = find(l)
            if r not in remap:
                remap[r] = len(remap) + 1
            ll = remap[r]
            labels[y, s:e] = ll
            c = comps.setdefault(ll, dict(n=0, x0=w, x1=-1, y0=h, y1=-1, sx=0.0, sy=0.0))
            n = e - s
            c['n'] += n
            c['x0'] = min(c['x0'], s)
            c['x1'] = max(c['x1'], e - 1)
            c['y0'] = min(c['y0'], y)
            c['y1'] = max(c['y1'], y)
            c['sx'] += (s + e - 1) * n / 2.0
            c['sy'] += y * n
    out = []
    for ll, c in comps.items():
        out.append(dict(label=ll, n=c['n'], x0=c['x0'], x1=c['x1'], y0=c['y0'], y1=c['y1'],
                        cx=c['sx'] / c['n'], cy=c['sy'] / c['n']))
    out.sort(key=lambda d: -d['n'])
    return labels, out


# ------------------------------------------------------------------ geometry
def fit_line(xs, ys):
    """Least squares x = a*y + b (edges are near-vertical) -> (a, b, rms)."""
    A = np.stack([ys, np.ones_like(ys)], axis=1)
    sol, *_ = np.linalg.lstsq(A, xs, rcond=None)
    a, b = sol
    res = xs - (a * ys + b)
    return float(a), float(b), float(np.sqrt((res ** 2).mean())), res


def homography(src, dst):
    """src, dst: 4x2 arrays. Returns 3x3 H mapping src->dst."""
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    A = np.array(A, dtype=np.float64)
    _, _, Vt = np.linalg.svd(A)
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def warp(img, H_inv, out_w, out_h):
    """Bilinear-sample img (HxWxC) into out_h x out_w using inverse homography
    (dest -> src)."""
    ys, xs = np.mgrid[0:out_h, 0:out_w].astype(np.float64)
    ones = np.ones_like(xs)
    P = np.stack([xs + 0.5, ys + 0.5, ones], axis=0).reshape(3, -1)
    Q = H_inv @ P
    sx = Q[0] / Q[2] - 0.5
    sy = Q[1] / Q[2] - 0.5
    h, w = img.shape[:2]
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0 = np.floor(sx).astype(np.int32); y0 = np.floor(sy).astype(np.int32)
    fx = (sx - x0)[:, None]; fy = (sy - y0)[:, None]
    x1 = x0 + 1; y1 = y0 + 1
    c = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) +
         img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)
    return c.reshape(out_h, out_w, img.shape[2]).astype(np.float32)


def save_debug_png(arr, path, label="DEBUG - NEVER SHIP"):
    """arr: HxWx3/4 float 0..1 (stored values). Writes a NON-SHIPPABLE overlay."""
    import bpy, os
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], axis=2)
    img = bpy.data.images.new("DEBUG_NEVER_SHIP", w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(arr[::-1].astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return path
