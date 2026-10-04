"""t8 (judge r7 item 2): the ring hardware's finish in the judge's aligned photo-camera frame (t8/judge_style/photo.png
and ours_aligned.png from pairs.py): the plate's luminance on three bare lobe patches, the washer's right petals (tone
spread p10-p90, median hue / HSV saturation), and the same patches in the photo; the photo also scaled to our
exposure (head white: photo 186, ours 235, the judge's factor). System Python + numpy + Pillow."""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

T = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/t8/judge_style")
K = 235.0 / 186.0
PATCHES = {"plate_right_lobe": (586, 598, 612, 616), "plate_top_lobe": (514, 526, 540, 548),
           "plate_bottom_lobe": (514, 680, 540, 690), "washer_right_petals": (556, 585, 576, 635)}


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


res = {"patches_u0_v0_u1_v1": PATCHES, "photo_exposure_factor": round(K, 4)}
for nm, f in (("photo", "photo.png"), ("ours", "ours_aligned.png")):
    a = np.asarray(Image.open(T / f).convert("RGB")).astype(float)
    out = {}
    for k, (u0, v0, u1, v1) in PATCHES.items():
        c = a[v0:v1, u0:u1].reshape(-1, 3)
        L = lum(c)
        d = {"lum_p10_p50_p90": [round(float(np.percentile(L, q)), 1) for q in (10, 50, 90)]}
        if nm == "photo":
            d["lum_p10_p50_p90_at_our_exposure"] = [round(K * x, 1) for x in d["lum_p10_p50_p90"]]
        if k.startswith("washer"):
            hs = np.array([colorsys.rgb_to_hsv(*(p / 255.0)) for p in c])
            bright = L > np.percentile(L, 20)
            d["hue_deg_median"] = round(float(np.median(hs[bright, 0]) * 360), 1)
            d["sat_hsv_median"] = round(float(np.median(hs[bright, 1])), 3)
            d["rgb_median"] = [int(x) for x in np.median(c, 0)]
        out[k] = d
    res[nm] = out
(T / "finish_metrics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
