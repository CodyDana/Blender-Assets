"""Shared helpers for the senban radial-profile study (run inside Blender's Python)."""
import bpy
import numpy as np
from collections import deque

PHOTO = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Senban.jpg"
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial/"


def load_rgb(path=PHOTO):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1, :, :3].copy()  # top-origin rows
    bpy.data.images.remove(img)
    return px


def save_png(arr, path):
    """arr: HxW (gray) or HxWx3 float 0..1, top-origin rows."""
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(arr, 0, 1)
    rgba = rgba[::-1].ravel()
    name = "tmp_out"
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.pixels.foreach_set(rgba)
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def shift(m, dy, dx, fill=False):
    out = np.full_like(m, fill)
    h, w = m.shape
    ys = slice(max(dy, 0), h + min(dy, 0))
    yd = slice(max(-dy, 0), h + min(-dy, 0))
    xs = slice(max(dx, 0), w + min(dx, 0))
    xd = slice(max(-dx, 0), w + min(-dx, 0))
    out[ys, xs] = m[yd, xd]
    return out


def disk_offsets(r):
    offs = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx <= r * r + 0.5:
                offs.append((dy, dx))
    return offs


def dilate(m, r):
    out = m.copy()
    for dy, dx in disk_offsets(r):
        out |= shift(m, dy, dx, False)
    return out


def erode(m, r):
    out = m.copy()
    for dy, dx in disk_offsets(r):
        out &= shift(m, dy, dx, True)
    return out


def opening(m, r):
    return dilate(erode(m, r), r)


def closing(m, r):
    return erode(dilate(m, r), r)


def label(mask):
    """4-connected component labelling, pure python BFS. Returns labels, sizes."""
    h, w = mask.shape
    flat = mask.ravel()
    lab = np.zeros(h * w, dtype=np.int32)
    sizes = [0]
    cur = 0
    idxs = np.flatnonzero(flat)
    fl = flat.tolist()
    lb = [0] * (h * w)
    for start in idxs.tolist():
        if lb[start]:
            continue
        cur += 1
        lb[start] = cur
        q = deque([start])
        n = 0
        while q:
            p = q.popleft()
            n += 1
            y, x = divmod(p, w)
            if x > 0:
                a = p - 1
                if fl[a] and not lb[a]:
                    lb[a] = cur; q.append(a)
            if x < w - 1:
                a = p + 1
                if fl[a] and not lb[a]:
                    lb[a] = cur; q.append(a)
            if y > 0:
                a = p - w
                if fl[a] and not lb[a]:
                    lb[a] = cur; q.append(a)
            if y < h - 1:
                a = p + w
                if fl[a] and not lb[a]:
                    lb[a] = cur; q.append(a)
        sizes.append(n)
    lab = np.array(lb, dtype=np.int32).reshape(h, w)
    return lab, np.array(sizes)


def fit_circle(x, y):
    """Algebraic (Kasa) circle fit then Gauss-Newton refine. Returns cx, cy, R, rms."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0] / 2, c[1] / 2
    R = np.sqrt(c[2] + cx * cx + cy * cy)
    for _ in range(30):
        dx = x - cx; dy = y - cy
        d = np.sqrt(dx * dx + dy * dy)
        res = d - R
        J = np.column_stack([-dx / d, -dy / d, -np.ones_like(d)])
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx += step[0]; cy += step[1]; R += step[2]
        if np.abs(step).max() < 1e-9:
            break
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    return cx, cy, R, float(np.sqrt(np.mean((d - R) ** 2)))


def fit_line(x, y):
    """Total least squares line. Returns point (mx,my), unit direction (ux,uy), rms."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    M = np.column_stack([x - mx, y - my])
    u, s, vt = np.linalg.svd(M, full_matrices=False)
    d = vt[0]
    n = vt[1]
    rms = float(np.sqrt(np.mean((M @ n) ** 2)))
    return (mx, my), (d[0], d[1]), rms


def line_intersect(p1, d1, p2, d2):
    A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
    b = np.array([p2[0] - p1[0], p2[1] - p1[1]])
    t = np.linalg.solve(A, b)
    return p1[0] + t[0] * d1[0], p1[1] + t[0] * d1[1]
