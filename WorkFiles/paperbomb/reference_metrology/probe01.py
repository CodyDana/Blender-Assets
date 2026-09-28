# -*- coding: utf-8 -*-
"""Probe 1: file facts + coarse layout + Blender-pixels cross-check."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
FILES = {
    "V1": ROOT + "/References/PaperBomb/paperbomb_guide.png",
    "V2": ROOT + "/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png",
    "OURS_BC": ROOT + "/Exports/PaperBomb/Textures/T_PaperBomb_BC.png",
    "OURS_ORM": ROOT + "/Exports/PaperBomb/Textures/T_PaperBomb_ORM.png",
    "OURS_N": ROOT + "/Exports/PaperBomb/Textures/T_PaperBomb_N.png",
    "OURS_M": ROOT + "/Exports/PaperBomb/Textures/T_PaperBomb_M.png",
}

out = {}
for key, path in FILES.items():
    if not os.path.exists(path):
        out[key] = {"missing": True}
        continue
    t0 = time.time()
    arr, info = P.read_png(path)
    dt = time.time() - t0
    info2 = {k: v for k, v in info.items() if k != "path"}
    info2["decode_seconds"] = round(dt, 2)
    info2["bytes"] = os.path.getsize(path)
    f = P.to_float(arr, info)
    info2["stored_mean_per_channel"] = [round(float(f[..., c].mean()), 5)
                                        for c in range(f.shape[2])]
    info2["stored_min"] = [int(arr[..., c].min()) for c in range(arr.shape[2])]
    info2["stored_max"] = [int(arr[..., c].max()) for c in range(arr.shape[2])]
    # corner + centre samples (stored 0-255 scale for readability)
    H, W = arr.shape[:2]
    scale = 255.0 / info["max_value"]
    def s(y, x):
        return [round(float(arr[y, x, c] * scale), 1) for c in range(min(3, arr.shape[2]))]
    info2["sample_topleft"] = s(2, 2)
    info2["sample_topright"] = s(2, W - 3)
    info2["sample_botleft"] = s(H - 3, 2)
    info2["sample_botright"] = s(H - 3, W - 3)
    info2["sample_centre"] = s(H // 2, W // 2)
    out[key] = info2
    print("== %s %dx%d ch=%d bd=%d ct=%d %.1fs" % (
        key, W, H, arr.shape[2], info["bit_depth"], info["colour_type"], dt))

# --- cross-check Blender's pixels against our stored decode, on V2 (small) ---
try:
    import bpy
    img = bpy.data.images.load(FILES["V2"])
    print("blender colorspace default:", img.colorspace_settings.name)
    W, H = img.size
    buf = np.empty(W * H * img.channels, dtype=np.float32)
    img.pixels.foreach_get(buf)
    buf = buf.reshape(H, W, img.channels)[::-1]  # blender is bottom-up
    arr2, info_2 = P.read_png(FILES["V2"])
    f2 = P.to_float(arr2, info_2)
    ys = [10, H // 3, H // 2, H - 11]
    xs = [10, W // 3, W // 2, W - 11]
    rows = []
    for y in ys:
        for x in xs:
            rows.append({
                "yx": [y, x],
                "stored": [round(float(v), 4) for v in f2[y, x, :3]],
                "blender_pixels": [round(float(v), 4) for v in buf[y, x, :3]],
                "srgb_to_linear(stored)": [round(float(v), 4)
                                           for v in P.srgb_to_linear(f2[y, x, :3])],
            })
    out["_blender_pixels_crosscheck"] = {
        "default_colorspace": img.colorspace_settings.name,
        "samples": rows,
    }
    for r in rows[:4]:
        print(r)
except Exception as exc:  # pragma: no cover
    out["_blender_pixels_crosscheck"] = {"error": repr(exc)}
    print("crosscheck failed:", exc)

dst = HERE + "/debug/probe01.json"
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
print("wrote", dst)
