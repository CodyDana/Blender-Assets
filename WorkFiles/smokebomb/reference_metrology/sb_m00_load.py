"""Stage 0: load the smoke-bomb reference, dump stored sRGB pixels (top-down) to .npy, basic stats.
Run: blender -b --factory-startup --python sb_m00_load.py
"""
import bpy, numpy as np, json, os, hashlib
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology"
img = bpy.data.images.load(REF)
img.colorspace_settings.name = 'Non-Color'   # keep stored values (sRGB-encoded 0..1)
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)
px = px[::-1].copy()   # top-down rows, like the file
np.save(os.path.join(OUT, "sb_ref_srgb.npy"), px[..., :3])
info = dict(size=[w, h], channels=img.channels, depth=img.depth, is_float=img.is_float,
            sha256=hashlib.sha256(open(REF, 'rb').read()).hexdigest())
rgb = px[..., :3]
if img.channels == 4:
    a = px[..., 3]
    info['alpha_min'] = float(a.min()); info['alpha_max'] = float(a.max())
# background: corners
for name, sl in dict(tl=(slice(0, 60), slice(0, 60)), tr=(slice(0, 60), slice(-60, None)),
                     bl=(slice(-60, None), slice(0, 60)), br=(slice(-60, None), slice(-60, None))).items():
    c = rgb[sl]
    info['bg_' + name] = dict(mean=c.reshape(-1, 3).mean(0).round(5).tolist(),
                             min=c.reshape(-1, 3).min(0).round(5).tolist(),
                             std=c.reshape(-1, 3).std(0).round(5).tolist())
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
hist, edges = np.histogram(lum, bins=20, range=(0, 1))
info['lum_hist20'] = hist.tolist()
print("SBINFO", json.dumps(info))
