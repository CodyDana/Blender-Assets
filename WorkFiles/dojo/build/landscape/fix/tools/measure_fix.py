"""LANDSCAPE FIX ROUND extras on a caps folder (after measure_landscape.py / measure_fxlight.py):
- foam share in the rapids boxes by the world stage's absolute rule AND a sunset-fair relative rule (foam = luma over the
  boxes' turquoise-water median + 35 and saturation < 0.30), reference vs ours
- the share of 'bare tan earth' (hue 20-50 deg, saturation > 0.30, luma > 70) in the forest-slope boxes
usage: py -3 -B measure_fix.py <caps dir>      out: <caps>/json/fix_measure.json"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
WH = (1024, 1536)
FOAM = [(600, 960, 780, 1080), (640, 1080, 860, 1180)]
SLOPES = [(60, 540, 250, 650), (640, 600, 900, 700)]


def load(p):
    return np.asarray(Image.open(p).convert("RGB").resize(WH, Image.LANCZOS)).astype(float)


def lum(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def px(a, boxes):
    return np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for x0, y0, x1, y1 in boxes])


def foam(a):
    p = px(a, FOAM)
    mx, mn = p.max(1), p.min(1)
    sat = (mx - mn) / np.maximum(mx, 1)
    L = p @ np.array([0.2126, 0.7152, 0.0722])
    turq = (p[:, 2] > p[:, 0] + 8) & (p[:, 1] > p[:, 0] + 8)
    base = float(np.median(L[turq])) if turq.sum() > 50 else float(np.percentile(L, 20))
    rel = (L > base + 35) & (sat < 0.30)
    absr = (L > 140) & (sat < 0.28)
    water = rel | turq
    return {"abs_rule_pct_of_water": round(float(absr.sum() / max((absr | turq).sum(), 1) * 100), 1),
            "rel_rule_pct_of_water": round(float(rel.sum() / max(water.sum(), 1) * 100), 1),
            "water_median_luma": round(base, 1)}


def tan_share(a):
    p = px(a, SLOPES) / 255.0
    out = 0
    for r, g, b in p[::7]:
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        if 20 <= h * 360 <= 50 and s > 0.30 and (0.2126 * r + 0.7152 * g + 0.0722 * b) * 255 > 70:
            out += 1
    return round(out / len(p[::7]) * 100, 1)


def peak_width(a, summit, win):
    L = lum(a)
    x0, x1 = win
    sky = np.median(a[summit[1] - 30:summit[1] - 10, x0:x1].reshape(-1, 3), 0)
    res = {}
    for dy in (40, 80, 120):
        row = a[summit[1] + dy, x0:x1]
        d = np.abs(row - sky).sum(1)
        m = np.where(d > 40)[0]
        res[str(dy)] = int(m.max() - m.min()) if len(m) else 0
    return res


def main():
    caps = Path(sys.argv[1])
    ref = load(ROOT / "References/Dojo/dojo_landscape_ref.png")
    ours = load(caps / "CAM_LandscapeRef.png")
    out = {"foam": {"reference": foam(ref), "ours": foam(ours)},
           "forest_slopes_tan_earth_pct": {"reference": tan_share(ref), "ours": tan_share(ours)}
}
    (caps / "json").mkdir(exist_ok=True)
    (caps / "json" / "fix_measure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out))


main()
