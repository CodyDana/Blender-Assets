"""Shared helpers for the smoke-bomb reference metrology (Blender Python, NumPy 2)."""
import numpy as np, os, json
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology"
DBG = os.path.join(D, "debug")
LW = np.array([0.2126, 0.7152, 0.0722], np.float32)


def load_srgb():
    return np.load(os.path.join(D, "sb_ref_srgb.npy"))


def srgb_to_lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float64), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def lum(rgb):
    return rgb @ LW


def bilinear(a, x, y):
    """sample 2D array a at float coords x (col), y (row); edge-clamped."""
    h, w = a.shape[:2]
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    if a.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
            + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def box_blur(a, r):
    """separable box blur radius r (window 2r+1) via cumulative sums, edge-replicated."""
    if r <= 0:
        return a.copy()
    k = 2 * r + 1
    p = np.pad(a, [(r + 1, r)] + [(0, 0)] * (a.ndim - 1), mode='edge')
    c = np.cumsum(p, axis=0, dtype=np.float64)
    a1 = (c[k:] - c[:-k]) / k
    p = np.pad(a1, [(0, 0), (r + 1, r)] + [(0, 0)] * (a.ndim - 2), mode='edge')
    c = np.cumsum(p, axis=1, dtype=np.float64)
    return ((c[:, k:] - c[:, :-k]) / k).astype(np.float32)


def gauss_blur(a, sigma):
    """approx gaussian: three box passes."""
    r = max(1, int(round(np.sqrt(12 * sigma * sigma / 3 + 1) - 1) // 2))
    out = a
    for _ in range(3):
        out = box_blur(out, r)
    return out


def save_png(path, rgb):
    """rgb: HxWx3 (or HxW) top-down, stored values 0..1 -> PNG (written as-is, no view transform)."""
    import bpy
    a = np.asarray(rgb, np.float32)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, 2)
    h, w = a.shape[:2]
    rgba = np.concatenate([np.clip(a, 0, 1), np.ones((h, w, 1), np.float32)], 2)[::-1]
    name = os.path.basename(path)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def upscale(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


def stretch(a, lo, hi):
    return np.clip((a - lo) / (hi - lo), 0, 1)


def dump(name, obj):
    with open(os.path.join(D, name), 'w') as f:
        json.dump(obj, f, indent=1)


def load(name):
    with open(os.path.join(D, name)) as f:
        return json.load(f)
