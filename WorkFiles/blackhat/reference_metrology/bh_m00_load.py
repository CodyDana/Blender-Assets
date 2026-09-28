"""Stage 0: load the black-hat reference, dump stored sRGB pixels (top-down) to .npy, basic stats."""
import bpy, numpy as np, json, os, hashlib
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/reference_metrology"
img = bpy.data.images.load(REF)
img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1].copy()
np.save(os.path.join(OUT, "bh_ref_srgb.npy"), px[..., :3])
info = dict(size=[w, h], channels=img.channels, sha256=hashlib.sha256(open(REF, 'rb').read()).hexdigest())
rgb = px[..., :3]
if img.channels == 4:
    info['alpha_min'] = float(px[..., 3].min())
for name, sl in dict(tl=(slice(0, 40), slice(0, 40)), tr=(slice(0, 40), slice(-40, None)),
                     bl=(slice(-40, None), slice(0, 40)), br=(slice(-40, None), slice(-40, None))).items():
    c = rgb[sl].reshape(-1, 3)
    info['bg_' + name] = dict(mean=c.mean(0).round(5).tolist(), min=c.min(0).round(5).tolist())
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
info['lum_hist20'] = np.histogram(lum, bins=20, range=(0, 1))[0].tolist()
print("BHINFO", json.dumps(info))
