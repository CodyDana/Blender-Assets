"""Reconciler IO + numeric helpers (numpy only, runs in Blender's bundled Python)."""
import numpy as np
import bpy


def load_rgb(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, dtype=np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(h, w, ch)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    return arr


def save_rgb(path, arr):
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    h, w, _ = arr.shape
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(arr, 0, 1)
    rgba = rgba[::-1].copy()
    img = bpy.data.images.new("out_tmp", w, h, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def lum(rgb):
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]


def gauss1d(sig, radius=None):
    if radius is None:
        radius = int(np.ceil(3 * sig))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sig) ** 2)
    return k / k.sum()


def blur(img, sig):
    k = gauss1d(sig)
    r = (len(k) - 1) // 2
    p = np.pad(img, ((r, r), (r, r)), mode='edge')
    out = np.zeros_like(p, dtype=np.float64)
    for i, kv in enumerate(k):
        out += kv * np.roll(p, i - r, axis=1)
    out2 = np.zeros_like(out)
    for i, kv in enumerate(k):
        out2 += kv * np.roll(out, i - r, axis=0)
    return out2[r:-r, r:-r]


def sample(img, x, y):
    """Bilinear sample. x, y arrays in pixel coords (x right, y down, pixel centres at ints)."""
    h, w = img.shape
    x = np.clip(np.asarray(x, dtype=np.float64), 0, w - 1.001)
    y = np.clip(np.asarray(y, dtype=np.float64), 0, h - 1.001)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = x - x0
    fy = y - y0
    v = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
         + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
    return v


def peak_refine(v, i):
    """Parabolic sub-sample peak position around index i of 1-D array v."""
    if i <= 0 or i >= len(v) - 1:
        return float(i)
    a, b, c = v[i - 1], v[i], v[i + 1]
    d = a - 2 * b + c
    if abs(d) < 1e-12:
        return float(i)
    return float(i) - 0.5 * (c - a) / d


def fit_circle(x, y):
    """Kasa + Gauss-Newton geometric refine. Returns cx, cy, r, rms."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    A = np.stack([x, y, np.ones_like(x)], 1)
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
    for _ in range(60):
        dx, dy = x - cx, y - cy
        d = np.hypot(dx, dy)
        res = d - r
        J = np.stack([-dx / d, -dy / d, -np.ones_like(d)], 1)
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx += step[0]
        cy += step[1]
        r += step[2]
        if np.max(np.abs(step)) < 1e-9:
            break
    d = np.hypot(x - cx, y - cy)
    rms = float(np.sqrt(np.mean((d - r) ** 2)))
    return float(cx), float(cy), float(r), rms


def fit_radius_fixed_centre(x, y, cx, cy):
    d = np.hypot(np.asarray(x, float) - cx, np.asarray(y, float) - cy)
    r = float(np.mean(d))
    return r, float(np.sqrt(np.mean((d - r) ** 2)))


def fit_ellipse(x, y):
    """Algebraic conic fit (SVD). Returns dict with centre, semi-axes, angle."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    sc = np.sqrt(((x - mx) ** 2 + (y - my) ** 2).mean())
    xs, ys = (x - mx) / sc, (y - my) / sc
    D = np.stack([xs ** 2, xs * ys, ys ** 2, xs, ys, np.ones_like(xs)], 1)
    _, _, Vt = np.linalg.svd(D, full_matrices=False)
    a, b, c, d, e, f = Vt[-1]
    M = np.array([[a, b / 2], [b / 2, c]])
    evals, evecs = np.linalg.eigh(M)
    cen = np.linalg.solve(2 * M, [-d, -e])
    val = a * cen[0] ** 2 + b * cen[0] * cen[1] + c * cen[1] ** 2 + d * cen[0] + e * cen[1] + f
    axes = np.sqrt(np.maximum(-val / evals, 1e-12))
    order = np.argsort(-axes)
    axes = axes[order] * sc
    vec = evecs[:, order[0]]
    return {
        'cx': float(cen[0] * sc + mx), 'cy': float(cen[1] * sc + my),
        'a': float(axes[0]), 'b': float(axes[1]),
        'ratio': float(axes[1] / axes[0]),
        'angle_deg': float(np.degrees(np.arctan2(vec[1], vec[0]))),
    }


def fit_line_tls(x, y):
    """Total least squares line. Returns point p (mean), unit direction u, rms."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    p = np.array([x.mean(), y.mean()])
    A = np.stack([x - p[0], y - p[1]], 1)
    _, _, Vt = np.linalg.svd(A, full_matrices=False)
    u = Vt[0]
    n = np.array([-u[1], u[0]])
    res = A @ n
    return p, u / np.linalg.norm(u), float(np.sqrt(np.mean(res ** 2))), res


def line_intersect(p1, u1, p2, u2):
    A = np.stack([u1, -u2], 1)
    t = np.linalg.solve(A, p2 - p1)
    return p1 + t[0] * u1
