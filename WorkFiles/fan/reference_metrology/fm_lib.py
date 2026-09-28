"""Shared helpers for fan reference metrology (fm_*). Run inside Blender 5.2 headless."""
import bpy, numpy as np, os
ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + r"/WorkFiles/fan/reference_metrology"
DBG = OUT + "/debug"
REFS = {1: ROOT + r"/References/Fan/fan1.png", 2: ROOT + r"/References/Fan/fan2.png"}

def load(i):
    p = os.path.join(OUT, f"fm_ref{i}_srgb.npy")
    return np.load(p)

def srgb2lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def lin2srgb(c):
    c = np.clip(np.asarray(c, np.float64), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

LUMW = np.array([0.2126, 0.7152, 0.0722])

def save_png(arr, name, scale=1):
    """arr: HxWx3 float sRGB top-down. Saved via Blender image (non-color so stored as is)."""
    a = np.clip(np.asarray(arr, np.float32), 0, 1)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, 2)
    if scale != 1:
        a = np.repeat(np.repeat(a, scale, 0), scale, 1)
    h, w = a.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    rgba = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)[::-1]
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(DBG, name if name.endswith('.png') else name + '.png')
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)

def draw_line(a, p0, p1, col, w=1):
    h, W = a.shape[:2]
    n = int(max(abs(p1[0]-p0[0]), abs(p1[1]-p0[1])) * 2) + 2
    for t in np.linspace(0, 1, n):
        x = p0[0] + (p1[0]-p0[0]) * t; y = p0[1] + (p1[1]-p0[1]) * t
        xi, yi = int(round(x)), int(round(y))
        if not (0 <= xi < a.shape[1] and 0 <= yi < a.shape[0]): continue
        a[max(0, yi-w//2):min(h, yi+w//2+1), max(0, xi-w//2):min(W, xi+w//2+1)] = col

def draw_circle(a, c, r, col, w=1):
    n = int(2*np.pi*r*2)+8
    for t in np.linspace(0, 2*np.pi, n):
        x = c[0]+r*np.cos(t); y = c[1]+r*np.sin(t)
        xi, yi = int(round(x)), int(round(y))
        if not (0 <= xi < a.shape[1] and 0 <= yi < a.shape[0]): continue
        h, W = a.shape[:2]
        a[max(0, yi-w//2):min(h, yi+w//2+1), max(0, xi-w//2):min(W, xi+w//2+1)] = col
