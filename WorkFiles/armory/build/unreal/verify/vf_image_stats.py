"""Independent verifier: image stats for the builder's Unreal captures vs the Blender fix1 renders (display-referred PNG
values). Run: blender -b --factory-startup --python <this> -- <out.json>"""
import hashlib
import json
import sys

import bpy
import numpy as np

CAP = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\captures"
REN = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\renders\fix1"
pairs = {"C1": (CAP + r"\C1_EntryReveal.png", REN + r"\C1_EntryReveal_golden.png"),
         "C10": (CAP + r"\C10_Hero.png", REN + r"\C10_Hero_golden.png"),
         "CW": (CAP + r"\CW_WestAisle.png", REN + r"\CW_WestAisle_golden.png")}


def load(p):
    im = bpy.data.images.load(p)
    im.colorspace_settings.name = "Non-Color"   # raw stored display values
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[::-1, :, :3]
    return a, (w, h), hashlib.md5(open(p, "rb").read()).hexdigest()


def stats(a):
    y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    h, w = y.shape
    grid = [[round(float(y[i * h // 4:(i + 1) * h // 4, j * w // 4:(j + 1) * w // 4].mean()), 3) for j in range(4)] for i in range(4)]
    return {"mean": round(float(y.mean()), 4), "median": round(float(np.median(y)), 4),
            "p10": round(float(np.percentile(y, 10)), 4), "p90": round(float(np.percentile(y, 90)), 4),
            "black_lt_0.02": round(float((y < 0.02).mean()), 4), "clip_all_gt_0.98": round(float((mn > 0.98).mean()), 4),
            "sat_mean": round(float(sat.mean()), 3), "grid4x4_mean": grid}


res = {}
for k, (u, b) in pairs.items():
    ua, us, uh = load(u)
    ba, bs, bh = load(b)
    su, sb = stats(ua), stats(ba)
    gu, gb = np.array(su["grid4x4_mean"]), np.array(sb["grid4x4_mean"])
    res[k] = {"unreal": {"size": us, "md5": uh, **su}, "blender": {"size": bs, "md5": bh, **sb},
              "grid_ratio_ue_over_bl": np.round(gu / np.maximum(gb, 1e-3), 2).tolist(),
              "grid_corr": round(float(np.corrcoef(gu.ravel(), gb.ravel())[0, 1]), 3)}
    # structural similarity proxy: correlation of downsampled luminance (32x18 blocks)
    def ds(a):
        y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        h, w = y.shape
        return y[: h - h % 18, : w - w % 32].reshape(18, h // 18, 32, w // 32).mean((1, 3))
    res[k]["block_corr_32x18"] = round(float(np.corrcoef(ds(ua).ravel(), ds(ba).ravel())[0, 1]), 3)
json.dump(res, open(sys.argv[sys.argv.index("--") + 1], "w"), indent=1)
print("VF_IMG_DONE")
