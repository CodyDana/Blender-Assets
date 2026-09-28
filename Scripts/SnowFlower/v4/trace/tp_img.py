"""trace pilot - image I/O via bpy (Blender's Python has numpy; no PIL)."""
import bpy, numpy as np, os

def load(path):
    """-> float32 array (H, W, 4), row 0 = TOP, stored values (no colour management)."""
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1].copy()

def save(path, arr):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2:
        arr = np.dstack([arr, arr, arr, np.ones_like(arr)])
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.ones(arr.shape[:2], np.float32)])
    h, w = arr.shape[:2]
    img = bpy.data.images.new("tp_save", w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.clip(arr[::-1], 0, 1).ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)

def resize(arr, fy, fx=None, kind='nearest'):
    fx = fy if fx is None else fx
    h, w = arr.shape[:2]
    H, W = int(round(h * fy)), int(round(w * fx))
    if kind == 'nearest':
        yi = np.minimum((np.arange(H) + 0.5) / fy, h - 1).astype(int)
        xi = np.minimum((np.arange(W) + 0.5) / fx, w - 1).astype(int)
        return arr[yi][:, xi]
    ys = np.clip((np.arange(H) + 0.5) / fy - 0.5, 0, h - 1)
    xs = np.clip((np.arange(W) + 0.5) / fx - 0.5, 0, w - 1)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, h - 1); x1 = np.minimum(x0 + 1, w - 1)
    wy = (ys - y0)[:, None, None] if arr.ndim == 3 else (ys - y0)[:, None]
    wx = (xs - x0)[None, :, None] if arr.ndim == 3 else (xs - x0)[None, :]
    a = arr[y0][:, x0] * (1 - wx) + arr[y0][:, x1] * wx
    b = arr[y1][:, x0] * (1 - wx) + arr[y1][:, x1] * wx
    return a * (1 - wy) + b * wy
