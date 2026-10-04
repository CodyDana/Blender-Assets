"""t3: the judge's tack darkness test on closeup_tack_band.png (t1 studio light) with the rendered tack mask
closeup_tack_band_mask.png: share of the tack pixels darker than 45/255 apart from the highlights, and the brightness of
the rim ring (the outer 3 px of each tack). Luminance = mean of the sRGB channels over a white background.
System Python + numpy + Pillow. Usage: py tack_stats.py [beauty.png] [mask.png]"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
beauty = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "closeup_tack_band.png"
maskp = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "closeup_tack_band_mask.png"
im = Image.open(beauty).convert("RGBA")
bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
rgb = np.asarray(Image.alpha_composite(bg, im).convert("RGB")).astype(np.float64)
lum = rgb.mean(2)
mk = Image.open(maskp).convert("L")
m = np.asarray(mk) > 128
# rim ring: the visible ring just inside each tack's silhouette, 2-5 px in (the outer 2 px are the anti-aliased
# blend with the hide and are left out)
e2 = np.asarray(mk.filter(ImageFilter.MinFilter(5))) > 128
e5 = np.asarray(mk.filter(ImageFilter.MinFilter(11))) > 128
rim = e2 & ~e5
m = e2                               # the tack area without its anti-aliased outer 2 px
# the highlights: where the lights' glossy reflection adds more than 12 levels (closeup_tack_band_nohl*.png: the same
# render with the lights hidden from glossy rays); without that render, lum > 120
nohl = beauty.with_name(beauty.stem.replace("closeup_tack_band", "closeup_tack_band_nohl") + ".png")
if beauty.stem.endswith("_photo"):
    nohl = beauty.with_name("closeup_tack_band_nohl_photo.png")
if nohl.exists():
    im2 = Image.alpha_composite(bg, Image.open(nohl).convert("RGBA")).convert("RGB")
    hl = (lum - np.asarray(im2).astype(np.float64).mean(2)) > 12
else:
    hl = lum > 120
t = lum[m & ~hl]
res = {"beauty": beauty.name, "tack_px": int(m.sum()), "highlight_px_share": round(float((m & hl).sum() / m.sum()), 4),
       "share_below_45_excl_highlights": round(float((t < 45).mean()), 4),
       "tack_lum_p1_p25_p50_p90": [round(float(np.percentile(t, q)), 1) for q in (1, 25, 50, 90)],
       "rim_ring_px": int(rim.sum()),
       "rim_lum_p50_p90_p99": [round(float(np.percentile(lum[rim & ~hl], q)), 1) for q in (50, 90, 99)],
       "rim_share_over_60": round(float((lum[rim & ~hl] > 60).mean()), 4),
       "pass_90pct_below_45": bool((t < 45).mean() >= 0.90),
       "pass_rim_le_60_p90": bool(np.percentile(lum[rim & ~hl], 90) <= 60)}
print(json.dumps(res))
out = HERE / ("tack_stats_" + beauty.stem + ".json")
out.write_text(json.dumps(res, indent=1), encoding="utf-8")
