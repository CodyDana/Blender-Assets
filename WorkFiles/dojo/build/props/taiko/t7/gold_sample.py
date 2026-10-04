"""t6 (judge t5 item 3): sample the rendered mid-gold on the upper skirt (ours: 3x3 px at the projected points of the
skirt's mid-gold zone, design x 0.462, facing the camera +-35 deg, gold_sample_px_front.json from render_t6 "front")
and the photo's upper-skirt gold (rows 262-318, cols 180-840: pixels classed gold by hue 25-50 deg, HSV s 0.18-0.6,
v > 0.5; the median). System Python + numpy + Pillow. Usage: py gold_sample.py [render.png]"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
ren = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "drum_front_standing_photo.png"


def hsv(rgb):
    h, s, v = colorsys.rgb_to_hsv(*[c / 255 for c in rgb])
    hl, ll, sl = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
    return round(h * 360, 1), round(s, 3), round(sl, 3)


ref = np.asarray(Image.open(ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp").convert("RGB")).astype(float)
crop = ref[262:318, 180:840].reshape(-1, 3)
hs = np.array([colorsys.rgb_to_hsv(*(p / 255)) for p in crop])
m = (hs[:, 0] * 360 > 25) & (hs[:, 0] * 360 < 50) & (hs[:, 1] > 0.18) & (hs[:, 1] < 0.6) & (hs[:, 2] > 0.5)
ref_med = np.median(crop[m], 0)
ref_p = [np.percentile(crop[m], q, 0).round().tolist() for q in (25, 75)]
im = np.asarray(Image.open(ren).convert("RGB")).astype(float)
pts = json.loads((HERE / "gold_sample_px_front.json").read_text())
smp = []
for x, y in pts:
    xi, yi = int(round(x)), int(round(y))
    smp.append(im[yi - 1:yi + 2, xi - 1:xi + 2].reshape(-1, 3).mean(0))
smp = np.array(smp)
ours_med = np.median(smp, 0)
# the same classifier as the photo's over our upper-skirt band (the sample rows -15 .. +25 px, cols 200-830)
ys = [p[1] for p in pts]
band = im[int(min(ys)) - 15:int(max(ys)) + 25, 200:830].reshape(-1, 3)
hb = np.array([colorsys.rgb_to_hsv(*(q / 255)) for q in band])
mb = (hb[:, 0] * 360 > 25) & (hb[:, 0] * 360 < 50) & (hb[:, 1] > 0.18) & (hb[:, 1] < 0.6) & (hb[:, 2] > 0.5)
ours_cls = np.median(band[mb], 0) if mb.any() else np.zeros(3)
out = {"render": ren.name, "photo_gold_px": int(m.sum()), "photo_median_rgb": ref_med.round().tolist(),
       "photo_iqr_rgb": ref_p, "photo_median_hue_hsv_s_hls_s": hsv(ref_med),
       "ours_median_rgb": ours_med.round().tolist(), "ours_min_max_rgb": [smp.min(0).round().tolist(), smp.max(0).round().tolist()],
       "ours_median_hue_hsv_s_hls_s": hsv(ours_med),
       "ours_minus_photo_rgb": (ours_med - ref_med).round().tolist(), "target_rgb_judge": [186, 158, 115],
       "ours_minus_judge_target_rgb": (ours_med - np.array([186, 158, 115])).round().tolist(),
       "ours_band_classified_median_rgb": ours_cls.round().tolist(), "ours_band_classified_px": int(mb.sum()),
       "ours_band_classified_minus_photo_classified_rgb": (ours_cls - ref_med).round().tolist(),
       "per_point_rgb": smp.round().tolist()}
print(json.dumps(out))
(HERE / ("gold_sample_%s.json" % ren.stem)).write_text(json.dumps(out, indent=1), encoding="utf-8")
