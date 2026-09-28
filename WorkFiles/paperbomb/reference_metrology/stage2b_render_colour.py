# -*- coding: utf-8 -*-
"""Secondary check: what do our ink and paper colours READ AS in the shipped
render? The basecolour map is an albedo; the reference PNG is a finished picture.
Comparing only BC to the reference would be unfair to whichever way the lighting
goes, so measure the render too. No rectification: colour statistics only.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402
import tagmeas as T  # noqa: E402

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
SCRATCH = os.environ["PB_SCRATCH"]

src = ROOT + "/Renders/PaperBomb/paperbomb_front.png"
arr, info = P.read_png(src)
f = P.to_float(arr, info)[..., :3]
h, s, v = P.rgb_to_hsv(f)
warm = f[..., 0] - f[..., 2]

# the backdrop is a flat neutral grey; the card is warm
card = (warm > 0.06) | ((v < 0.55) & (s > 0.10))
# keep the largest blob only
import metro as M  # noqa: E402
lab, n = M.label_cc(M.closing(card, 6))
cs = M.cc_stats(lab, n)
cs.sort(key=lambda d: -d["area_px"])
card = lab == cs[0]["label"]
ys, xs = np.nonzero(card)
H, W = f.shape[:2]

paper = card & (v > 0.55) & (s < 0.50) & (h > 20) & (h < 65)
black = card & (v < 0.45) & (s < 0.55)
red = card & (((h < 28) | (h > 335))) & (s > 0.40) & (v > 0.15)

out = {
    "source_file": src,
    "what_this_is": "colour statistics of the shipped render, for comparison with "
                    "the reference PNG on equal terms (both are finished pictures). "
                    "No rectification and no geometry: values only.",
    "card_pixels": int(card.sum()),
    "card_bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
    "image_px": [W, H],
    "paper": T.colour_report(f[paper]),
    "black_ink": T.colour_report(f[black]),
    "red_ink": T.colour_report(f[red]),
    "area_fracs_of_card": {
        "paper": round(float(paper.sum()) / card.sum(), 5),
        "black": round(float(black.sum()) / card.sum(), 5),
        "red": round(float(red.sum()) / card.sum(), 5),
    },
}
# darkest black actually reached
if black.sum():
    lin = P.srgb_to_linear(f[black])
    lum = 0.2126 * lin[:, 0] + 0.7152 * lin[:, 1] + 0.0722 * lin[:, 2]
    out["black_ink"]["darkest"] = {
        "min_linear_luma": round(float(lum.min()), 7),
        "p1_linear_luma": round(float(np.percentile(lum, 1)), 7),
        "median_linear_luma": round(float(np.median(lum)), 7),
        "p1_stored_srgb_8bit": int(round(float(np.percentile(np.max(f[black], axis=1), 1)) * 255)),
    }
dst = os.path.join(SCRATCH, "meas_OURS_RENDER.json")
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
print("wrote", dst)
print("paper", out["paper"]["stored_srgb_hex"], out["paper"]["hsv_stored"])
print("black", out["black_ink"]["stored_srgb_hex"], out["black_ink"].get("darkest"))
print("red  ", out["red_ink"]["stored_srgb_hex"], out["red_ink"]["hsv_stored"])
