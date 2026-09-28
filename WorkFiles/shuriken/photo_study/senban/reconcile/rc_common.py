"""Shared loaders for the senban reconciliation pass."""
import numpy as np
import bpy

PHOTO = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Senban.jpg"
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/"


def load_rgb():
    """Return (H, W, 3) float array of stored sRGB values, row 0 = TOP of image."""
    img = bpy.data.images.load(PHOTO, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(h, w, 4)[:, :, :3]
    a = a[::-1].copy()            # row 0 -> top
    bpy.data.images.remove(img)
    return a


def lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def bilinear(arr, x, y):
    """Sample a 2-D array at float (x=col, y=row). Clamps at the border."""
    h, w = arr.shape
    x = np.clip(np.asarray(x, dtype=np.float64), 0, w - 1.001)
    y = np.clip(np.asarray(y, dtype=np.float64), 0, h - 1.001)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = x - x0
    fy = y - y0
    x1 = x0 + 1
    y1 = y0 + 1
    return (arr[y0, x0] * (1 - fx) * (1 - fy) + arr[y0, x1] * fx * (1 - fy) +
            arr[y1, x0] * (1 - fx) * fy + arr[y1, x1] * fx * fy)


def fit_circle(pts, w=None):
    """Kasa algebraic circle fit, then 8 Gauss-Newton refinements. pts (N,2)."""
    x = pts[:, 0].astype(np.float64)
    y = pts[:, 1].astype(np.float64)
    if w is None:
        w = np.ones_like(x)
    A = np.stack([x, y, np.ones_like(x)], axis=1)
    b = x * x + y * y
    W = np.sqrt(w)[:, None]
    sol, *_ = np.linalg.lstsq(A * W, b * W[:, 0], rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    R = np.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-9))
    for _ in range(8):
        dx, dy = x - cx, y - cy
        d = np.sqrt(dx * dx + dy * dy)
        d = np.where(d < 1e-9, 1e-9, d)
        r = d - R
        J = np.stack([-dx / d, -dy / d, -np.ones_like(d)], axis=1)
        try:
            step, *_ = np.linalg.lstsq(J * W, -r * W[:, 0], rcond=None)
        except np.linalg.LinAlgError:
            break
        cx += step[0]; cy += step[1]; R += step[2]
        if np.max(np.abs(step)) < 1e-9:
            break
    dx, dy = x - cx, y - cy
    resid = np.sqrt(dx * dx + dy * dy) - R
    return cx, cy, R, float(np.sqrt(np.mean(resid ** 2))), resid


def fit_line_tls(pts):
    """Total-least-squares line. Returns (point_on_line, unit_dir, rms)."""
    p = pts.astype(np.float64)
    c = p.mean(axis=0)
    u, s, vt = np.linalg.svd(p - c)
    d = vt[0]
    n = np.array([-d[1], d[0]])
    resid = (p - c) @ n
    return c, d, float(np.sqrt(np.mean(resid ** 2)))


def line_intersect(c1, d1, c2, d2):
    A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]], dtype=np.float64)
    b = np.array([c2[0] - c1[0], c2[1] - c1[1]], dtype=np.float64)
    t = np.linalg.solve(A, b)
    return c1 + t[0] * d1


def save_png(path, rgb_top_origin):
    """rgb_top_origin: (H,W,3) float 0..1, row 0 = top."""
    h, w = rgb_top_origin.shape[:2]
    img = bpy.data.images.new("out", width=w, height=h, alpha=False)
    flat = np.empty((h, w, 4), dtype=np.float32)
    flat[:, :, :3] = rgb_top_origin[::-1]
    flat[:, :, 3] = 1.0
    img.pixels.foreach_set(flat.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
