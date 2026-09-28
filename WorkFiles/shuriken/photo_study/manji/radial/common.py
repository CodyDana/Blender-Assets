"""Shared helpers for the manji photo measurement (Blender 5.2 bundled Python, numpy only).

Coordinate conventions used everywhere in this folder:
  * arrays are TOP-origin: row 0 is the top of the photo as a viewer sees it.
  * pixel (row=y, col=x). "math" frame: X = x, Y = -y (up is positive), angles CCW from +X.
"""
import os
import numpy as np
import bpy

OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/radial"
IMG = r"C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Manjiken.JPG"


def load_rgb(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    ch = im.channels
    a = np.empty(w * h * ch, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, ch)[::-1, :, :3].copy()  # flip to top-origin
    info = dict(w=w, h=h, channels=ch, colorspace=im.colorspace_settings.name,
                is_float=im.is_float)
    bpy.data.images.remove(im)
    return a, info


def save_png(arr, path):
    """arr: top-origin HxW or HxWx3 float in 0..1 (written as raw byte values)."""
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, -1)
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    im = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    im.pixels.foreach_set(rgba[::-1].ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def box_count(m, r):
    """Number of True pixels in the (2r+1)^2 window around each pixel (zero padded)."""
    m = m.astype(np.int32)
    k = 2 * r + 1
    P = np.pad(m, r)
    S = np.zeros((P.shape[0] + 1, P.shape[1] + 1), np.int64)
    S[1:, 1:] = P.cumsum(0).cumsum(1)
    return S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]


def dilate(m, r):
    return box_count(m, r) > 0 if r > 0 else m.copy()


def erode(m, r):
    return box_count(m, r) == (2 * r + 1) ** 2 if r > 0 else m.copy()


def open_(m, r):
    return dilate(erode(m, r), r)


def close_(m, r):
    return erode(dilate(m, r), r)


def label_runs(mask, conn8=True):
    """Run-length union-find labelling. Returns (runs, comp_of_run, areas_by_comp, touches_border)."""
    h, w = mask.shape
    pad = np.zeros((h, w + 2), np.int8)
    pad[:, 1:-1] = mask.astype(np.int8)
    d = np.diff(pad, axis=1)
    ys, xs = np.nonzero(d == 1)
    ye, xe = np.nonzero(d == -1)
    assert np.array_equal(ys, ye)
    n = len(ys)
    parent = list(range(n))

    def find(a):
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:
            parent[a], a = root, parent[a]
        return root

    rs = np.searchsorted(ys, np.arange(h + 1))
    xs_l = xs.tolist(); xe_l = xe.tolist()
    for y in range(1, h):
        i, i1 = rs[y - 1], rs[y]
        j, j1 = rs[y], rs[y + 1]
        while i < i1 and j < j1:
            if conn8:
                ok = xs_l[j] <= xe_l[i] and xs_l[i] <= xe_l[j]
            else:
                ok = xs_l[j] < xe_l[i] and xs_l[i] < xe_l[j]
            if ok:
                a, b = find(i), find(j)
                if a != b:
                    parent[max(a, b)] = min(a, b)
            if xe_l[i] < xe_l[j]:
                i += 1
            else:
                j += 1
    roots = np.array([find(k) for k in range(n)], np.int64)
    lengths = xe - xs
    areas = np.bincount(roots, weights=lengths, minlength=n)
    border = np.zeros(n, bool)
    edge_run = (ys == 0) | (ys == h - 1) | (xs == 0) | (xe == w)
    border[np.unique(roots[edge_run])] = True
    return (ys, xs, xe), roots, areas, border


def paint(shape, runs, sel):
    ys, xs, xe = runs
    m = np.zeros(shape, bool)
    for y, a, b in zip(ys[sel].tolist(), xs[sel].tolist(), xe[sel].tolist()):
        m[y, a:b] = True
    return m


def otsu(values, bins=1024):
    v = values.ravel()
    lo, hi = float(v.min()), float(v.max())
    hist, edges = np.histogram(v, bins=bins, range=(lo, hi))
    p = hist.astype(np.float64) / hist.sum()
    c = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * c)
    mt = m0[-1]
    w1 = 1 - w0
    with np.errstate(divide='ignore', invalid='ignore'):
        sb = (mt * w0 - m0) ** 2 / (w0 * w1)
    sb[~np.isfinite(sb)] = 0
    return float(c[np.argmax(sb)])


def bilinear(img, x, y):
    """Sample top-origin image (HxW or HxWxC) at float pixel coords x (col), y (row)."""
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
    fx = x - x0; fy = y - y0
    if img.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    a = img[y0, x0]; b = img[y0, x0 + 1]; c = img[y0 + 1, x0]; d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def trace_contour(mask):
    """Moore-neighbour trace (Jacob stop) of the outer boundary of the single component.
    Returns Nx2 int array of (x, y), top-origin, clockwise on screen."""
    h, w = mask.shape
    m = np.zeros((h + 2, w + 2), bool)
    m[1:-1, 1:-1] = mask
    ys, xs = np.nonzero(m)
    k = np.lexsort((xs, ys))[0]
    sy, sx = int(ys[k]), int(xs[k])
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    idx = {v: i for i, v in enumerate(nb)}
    cy, cx = sy, sx
    back = 0
    pts = [(sx, sy)]
    second = None
    limit = 20 * (h + w) * 4
    while len(pts) < limit:
        found = False
        for i in range(8):
            d = (back + 1 + i) % 8
            ny, nx = cy + nb[d][0], cx + nb[d][1]
            if m[ny, nx]:
                found = True
                break
        if not found:
            break
        pd = nb[(d - 1) % 8]
        by, bx = cy + pd[0], cx + pd[1]
        back = idx[(by - ny, bx - nx)]
        if (cy, cx) == (sy, sx) and second is not None and (ny, nx) == second:
            break
        if second is None:
            second = (ny, nx)
        cy, cx = ny, nx
        pts.append((cx, cy))
    if len(pts) > 1 and pts[-1] == (sx, sy):
        pts.pop()
    return np.array(pts, np.int64) - 1
