"""Round 3 look pass: sRGB region medians on the DojoLab captures (plain Python, read-only).

Run: py -3 WorkFiles/dojo/build/unreal/round3/measure_r3.py [capture_dir] [tag]
Regions are fixed pixel boxes per camera (x0, y0, x1, y1), picked on the r3 captures and drawn on
<capture_dir>/regions/<cam>.png so every box can be checked by eye. Per region: median sRGB, HSV hue / sat, R/B,
the fraction of pixels with every channel >= 250 (blown) and any channel >= 254 (clipped), near-black fraction.
Whole image: near-black and blown fractions (verifier r2 method).
Also the rake spacing: the dominant period of the sand luminance along image rows is left to measure_rake_r3.py (ground).
Out: <capture_dir>/regions_<tag>.json
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
CAP = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "r3"
TAG = sys.argv[2] if len(sys.argv) > 2 else "r3"
REGIONS = json.loads((HERE / "regions_r3.json").read_text(encoding="utf-8"))


def stats(a, box, hp=None):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(px, axis=0)
    h, s, v = colorsys.rgb_to_hsv(*(med / 255.0))
    return {"box": box, "median_srgb": [int(round(c)) for c in med], "hue_deg": round(h * 360, 1), "sat": round(s, 3),
            "val": round(v, 3), "r_over_b": round(float(med[0] / max(med[2], 1)), 3),
            "blown_frac": round(float(np.mean(np.all(px >= 250, axis=1))), 4),
            "clip_any_frac": round(float(np.mean(px.max(axis=1) >= 254)), 4),
            "near_black_frac": round(float(np.mean(px.max(axis=1) < 12)), 4),
            # speckle: std of (luma - its 6 px Gaussian local mean) / mean luma (the texture-grain contrast on screen)
            "speckle": round(float(hp[y0:y1, x0:x1].std() / max(a[y0:y1, x0:x1].mean(), 1)), 4) if hp is not None else None}


def main():
    out = {"capture_dir": str(CAP), "cams": {}, "images": {}}
    (CAP / "regions").mkdir(exist_ok=True)
    for cam, boxes in REGIONS.items():
        p = CAP / f"{cam}.png"
        if not p.exists():
            continue
        img = Image.open(p).convert("RGB")
        a = np.asarray(img).astype(np.float64)
        lum = img.convert("L")
        hp = np.asarray(lum).astype(np.float64) - np.asarray(lum.filter(ImageFilter.GaussianBlur(6))).astype(np.float64)
        out["cams"][cam] = {k: stats(a, v, hp) for k, v in boxes.items()}
        d = ImageDraw.Draw(img)
        for k, (x0, y0, x1, y1) in boxes.items():
            d.rectangle((x0, y0, x1, y1), outline=(0, 255, 255), width=3)
            d.text((x0 + 4, y0 + 4), k, fill=(0, 255, 255))
        img.save(CAP / "regions" / f"{cam}.png")
    for p in sorted(CAP.glob("C*_*.png")):
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
        mx = a.max(axis=2)
        out["images"][p.stem] = {"near_black_frac": round(float(np.mean(mx < 12)), 4),
                                 "blown_frac": round(float(np.mean(a.min(axis=2) >= 250)), 4),
                                 "any_255_frac": round(float(np.mean(mx >= 255)), 4)}
    (CAP / f"regions_{TAG}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for cam, rs in out["cams"].items():
        for k, r in rs.items():
            print(f"{cam:22s} {k:24s} {str(r['median_srgb']):16s} hue {r['hue_deg']:5.1f} sat {r['sat']:.2f} "
                  f"R/B {r['r_over_b']:.2f} blown {r['blown_frac']:.3f} clip {r['clip_any_frac']:.3f} "
                  f"black {r['near_black_frac']:.3f} speckle {r['speckle']}")
    for k, v in out["images"].items():
        if v["near_black_frac"] > 0.02 or v["blown_frac"] > 0.005:
            print("IMAGE", k, v)


main()
