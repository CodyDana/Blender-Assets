import bpy, numpy as np, json, os, hashlib
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/Flashbang/flashbang_reference.png"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology"
img = bpy.data.images.load(REF)
img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1].copy()
np.save(os.path.join(OUT, "fb_ref_srgb.npy"), px[..., :3])
info = dict(size=[w, h], channels=img.channels, sha256=hashlib.sha256(open(REF, 'rb').read()).hexdigest())
rgb = px[..., :3]
for name, sl in dict(tl=(slice(0, 40), slice(0, 40)), tr=(slice(0, 40), slice(-40, None)), mid=(slice(600,700), slice(0,40))).items():
    c = rgb[sl]; info['bg_' + name] = c.reshape(-1, 3).mean(0).round(4).tolist()
print("FBINFO", json.dumps(info))
