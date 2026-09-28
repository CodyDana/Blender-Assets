"""Stage 0: load both fan references, dump stored sRGB (top-down) to .npy, basic stats."""
import bpy, numpy as np, json, os, hashlib, sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
res = {}
for i, p in REFS.items():
    img = bpy.data.images.load(p)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1].copy()
    np.save(os.path.join(OUT, f"fm_ref{i}_srgb.npy"), px[..., :3])
    rgb = px[..., :3]
    info = dict(size=[w, h], channels=img.channels, sha256=hashlib.sha256(open(p, 'rb').read()).hexdigest())
    if img.channels == 4: info['alpha_min'] = float(px[..., 3].min())
    for name, sl in dict(tl=(slice(0, 30), slice(0, 30)), tr=(slice(0, 30), slice(-30, None)),
                         bl=(slice(-30, None), slice(0, 30)), br=(slice(-30, None), slice(-30, None))).items():
        c = rgb[sl].reshape(-1, 3)
        info['bg_' + name] = dict(mean=c.mean(0).round(4).tolist(), min=c.min(0).round(4).tolist())
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    info['lum_hist10'] = np.histogram(lum, bins=10, range=(0, 1))[0].tolist()
    res[i] = info
json.dump(res, open(os.path.join(OUT, "fm_s00_load.json"), "w"), indent=1)
print("FMINFO", json.dumps(res))
