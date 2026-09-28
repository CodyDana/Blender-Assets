# sm_m00: load both references into npy (float32 RGBA, row 0 = TOP of image) + hashes
import bpy, numpy as np, hashlib, json, os, sys
OUT = os.path.dirname(os.path.abspath(__file__))
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SnowFlower"
res = {}
for key, fn in [("sheath", "SnowFlower_sheath_reference.png"), ("sword", "SnowFlower_user_reference.png")]:
    p = os.path.join(REF, fn)
    img = bpy.data.images.load(p)
    img.colorspace_settings.name = "Non-Color"  # stored values, no transform
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1]  # flip so row 0 is top
    np.save(os.path.join(OUT, f"sm_{key}.npy"), a)
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
    res[key] = dict(file=fn, w=w, h=h, sha256=sha, channels=img.channels,
                    alpha_min=float(a[..., 3].min()), corner=a[:5, :5, :3].mean(axis=(0, 1)).tolist())
json.dump(res, open(os.path.join(OUT, "sm_s00.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
