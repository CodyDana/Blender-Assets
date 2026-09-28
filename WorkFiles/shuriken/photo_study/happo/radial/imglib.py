"""Small numpy-only image helpers for headless Blender (no scipy, no PIL).

Arrays are top-origin: row 0 is the TOP of the image.
"""
import numpy as np
import bpy


def load_rgb(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, ch)[::-1].copy()  # flip to top-origin
    bpy.data.images.remove(img)
    return arr[..., :3], w, h


def save_png(path, rgb):
    """rgb: HxWx3 (or HxW) float 0..1, top-origin."""
    if rgb.ndim == 2:
        rgb = np.repeat(rgb[..., None], 3, axis=2)
    h, w = rgb.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb, 0, 1)
    img = bpy.data.images.new("tmp_out", width=w, height=h, alpha=True)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def shift(a, dy, dx, fill=False):
    out = np.full_like(a, fill)
    h, w = a.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = a[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def disk_offsets(r):
    offs = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + 0.25:
                offs.append((dy, dx))
    return offs


def dilate(m, r):
    out = np.zeros_like(m)
    for dy, dx in disk_offsets(r):
        out |= shift(m, dy, dx, False)
    return out


def erode(m, r):
    out = np.ones_like(m)
    for dy, dx in disk_offsets(r):
        out &= shift(m, dy, dx, True)
    return out


def opening(m, r):
    return dilate(erode(m, r), r)


def closing(m, r):
    return erode(dilate(m, r), r)


def label(mask):
    """8-connected labeling via row runs + union-find. Returns (labels, sizes dict)."""
    h, w = mask.shape
    parent = []

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

    runs = []  # per row list of (x0, x1_exclusive, id)
    for y in range(h):
        row = mask[y].astype(np.int8)
        d = np.diff(np.concatenate(([0], row, [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)
        cur = []
        prev = runs[y - 1] if y > 0 else []
        j = 0
        for s, e in zip(starts, ends):
            rid = len(parent)
            parent.append(rid)
            # 8-connectivity: previous-row run overlaps [s-1, e+1)
            for (ps, pe, pid) in prev:
                if pe > s - 1 and ps < e + 1:
                    union(rid, pid)
            cur.append((int(s), int(e), rid))
        runs.append(cur)
    lab = np.zeros((h, w), dtype=np.int32)
    roots = {}
    sizes = {}
    for y in range(h):
        for (s, e, rid) in runs[y]:
            r = find(rid)
            if r not in roots:
                roots[r] = len(roots) + 1
            L = roots[r]
            lab[y, s:e] = L
            sizes[L] = sizes.get(L, 0) + (e - s)
    return lab, sizes


def bilinear(img, x, y):
    """Sample 2D array at float coords (x=col, y=row). Out of range -> edge clamp."""
    h, w = img.shape
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = x - x0
    fy = y - y0
    a = img[y0, x0]
    b = img[y0, x0 + 1]
    c = img[y0 + 1, x0]
    d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
