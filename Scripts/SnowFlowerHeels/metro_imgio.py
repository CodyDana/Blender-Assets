"""Image IO for headless Blender (numpy). Arrays are HxWxC float32 0..1, row 0 = TOP."""
import bpy, numpy as np, os

def load(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'   # keep raw sRGB-encoded values
    w, h = img.size
    a = np.empty(w*h*4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a

def save(arr, path):
    arr = np.asarray(arr, np.float32)
    if arr.ndim == 2: arr = np.stack([arr]*3, -1)
    if arr.shape[2] == 3: arr = np.concatenate([arr, np.ones(arr.shape[:2]+(1,), np.float32)], -1)
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.clip(arr[::-1], 0, 1).ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
