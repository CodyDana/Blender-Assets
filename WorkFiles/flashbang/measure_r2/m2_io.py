import numpy as np, bpy, os
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
REFP = ROOT + "References/Flashbang/flashbang_reference.png"
def load(path):
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(im)
    return a * 255.0
def save(path, arr):
    arr = np.clip(np.asarray(arr, np.float32), 0, 255)
    if arr.ndim == 2: arr = np.stack([arr]*3, -1)
    h, w = arr.shape[:2]
    if arr.shape[2] == 3: arr = np.concatenate([arr, np.full((h, w, 1), 255.0, np.float32)], -1)
    im = bpy.data.images.new("m2_tmp", w, h, alpha=True)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set((arr[::-1] / 255.0).ravel().astype(np.float32))
    im.filepath_raw = path; im.file_format = "PNG"
    sc = bpy.context.scene
    s = sc.render.image_settings
    im.save(filepath=path)
    bpy.data.images.remove(im)
def resize(a, k):
    h, w = a.shape[:2]; H, W = max(1, int(round(h * k))), max(1, int(round(w * k)))
    if k < 1:  # box prefilter
        n = int(np.floor(1 / k))
        if n > 1:
            hh, ww = (h // n) * n, (w // n) * n
            a = a[:hh, :ww].reshape(hh // n, n, ww // n, n, -1).mean((1, 3)) if a.ndim == 3 else a[:hh, :ww].reshape(hh // n, n, ww // n, n).mean((1, 3))
            return resize(a, k * n) if abs(k * n - 1) > 1e-3 else a
    ys = (np.arange(H) + 0.5) * h / H - 0.5; xs = (np.arange(W) + 0.5) * w / W - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1); x0 = np.clip(np.floor(xs).astype(int), 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1); x1 = np.clip(x0 + 1, 0, w - 1)
    fy = np.clip(ys - y0, 0, 1); fx = np.clip(xs - x0, 0, 1)
    if a.ndim == 3: fy = fy[:, None, None]; fx = fx[None, :, None]
    else: fy = fy[:, None]; fx = fx[None, :]
    return (a[y0][:, x0] * (1 - fy) * (1 - fx) + a[y0][:, x1] * (1 - fy) * fx + a[y1][:, x0] * fy * (1 - fx) + a[y1][:, x1] * fy * fx)
