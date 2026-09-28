"""Small helpers for headless Blender image IO + binary morphology (numpy only).

Run inside Blender's bundled Python. Read-only on source images; writes only
where the caller asks.
"""
import numpy as np
import bpy
from collections import deque


def load_rgb(path):
    """Return float32 array (H, W, 3) of stored (sRGB-encoded) values, row 0 = TOP."""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, ch)[::-1, :, :3].copy()  # flip: top-origin rows
    bpy.data.images.remove(img)
    return arr


def save_rgb(path, arr):
    """arr (H, W, 3) or (H, W) floats 0..1, row 0 = TOP. Saves PNG."""
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    h, w, _ = arr.shape
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(arr, 0, 1)
    rgba = rgba[::-1].copy()  # back to bottom-origin
    img = bpy.data.images.new("out_tmp", w, h, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def disk_offsets(r):
    offs = []
    ri = int(np.ceil(r))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if dx * dx + dy * dy <= r * r + 1e-9:
                offs.append((dy, dx))
    return offs


def _shift(m, dy, dx, fill):
    h, w = m.shape
    out = np.full_like(m, fill)
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def dilate(m, r):
    out = np.zeros_like(m)
    for dy, dx in disk_offsets(r):
        out |= _shift(m, dy, dx, False)
    return out


def erode(m, r):
    out = np.ones_like(m)
    for dy, dx in disk_offsets(r):
        out &= _shift(m, dy, dx, True)
    return out


def opening(m, r):
    return dilate(erode(m, r), r)


def closing(m, r):
    return erode(dilate(m, r), r)


def label(m):
    """4-connected labelling. Returns (labels int32, sizes list index=label)."""
    h, w = m.shape
    lab = np.zeros((h, w), dtype=np.int32)
    flat = m.ravel()
    lf = lab.ravel()
    sizes = [0]
    cur = 0
    idxs = np.flatnonzero(flat)
    for start in idxs:
        if lf[start]:
            continue
        cur += 1
        lf[start] = cur
        q = deque([start])
        n = 0
        while q:
            p = q.popleft()
            n += 1
            y, x = divmod(p, w)
            if x > 0:
                pp = p - 1
                if flat[pp] and not lf[pp]:
                    lf[pp] = cur; q.append(pp)
            if x < w - 1:
                pp = p + 1
                if flat[pp] and not lf[pp]:
                    lf[pp] = cur; q.append(pp)
            if y > 0:
                pp = p - w
                if flat[pp] and not lf[pp]:
                    lf[pp] = cur; q.append(pp)
            if y < h - 1:
                pp = p + w
                if flat[pp] and not lf[pp]:
                    lf[pp] = cur; q.append(pp)
        sizes.append(n)
    return lab, sizes
