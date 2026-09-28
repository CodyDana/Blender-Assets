"""Verifier: measure the C10 top-pane band and emblem/deck regions (display values)."""
import bpy, numpy as np, json, sys
def load(p):
    im = bpy.data.images.load(p); im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[::-1, :, :3]
u = load(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\captures\C10_Hero.png")
b = load(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\renders\fix1\C10_Hero_golden.png")
res = {}
for nm, a in (("unreal", u), ("blender", b)):
    y = 0.2126*a[..., 0] + 0.7152*a[..., 1] + 0.0722*a[..., 2]
    band = y[125:160, 40:1560]
    rowmeans = [round(float(v), 3) for v in y[120:165, 40:1560].mean(1)]
    res[nm] = {"band_rows125_160_mean": round(float(band.mean()), 3), "band_frac_gt_0.9": round(float((band > 0.9).mean()), 3),
               "rows_120_165_mean": rowmeans,
               "frame_frac_gt_0.9": round(float((y > 0.9).mean()), 4),
               "deck_rows500_570_mean": round(float(y[500:570, 100:1500].mean()), 3),
               "emblem_rgb_mean": [round(float(v), 3) for v in a[845:895, 745:855].reshape(-1, 3).mean(0)]}
json.dump(res, open(sys.argv[-1], "w"), indent=1); print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows_120_165_mean"} for k, v in res.items()}))
print(res["unreal"]["rows_120_165_mean"])
