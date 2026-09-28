"""Shared image helpers for the BlackCloak_MH_v2 spec/measure tools (Blender Python: numpy available, no PIL).
load(path) -> float32 HxWxC array, row 0 = TOP, sRGB 0..1 as stored in the file; save(arr, path)."""
import bpy, numpy as np, os

def load(path):
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = "Non-Color"  # raw file values, no transform
    w, h = im.size; c = im.channels
    a = np.empty(w * h * c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1].copy()
    bpy.data.images.remove(im)
    return a

def save(arr, path):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.stack([arr] * 3, -1)
    h, w, c = arr.shape
    if c == 3: arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], -1)
    im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(np.clip(arr[::-1], 0, 1).ravel())
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)

def crop(arr, x0, y0, x1, y1, scale=1):
    c = arr[y0:y1, x0:x1]
    if scale != 1:
        c = np.repeat(np.repeat(c, scale, 0), scale, 1)
    return c

def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]

def srgb_to_lin(v):
    v = np.asarray(v, np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)

def draw_grid(arr, step, color=(1, 0, 0), every_label=None):
    a = arr.copy()
    a[::step, :, :3] = color; a[:, ::step, :3] = color
    return a
