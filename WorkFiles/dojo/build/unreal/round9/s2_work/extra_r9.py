"""Round 9 extra measures (beside round8 measure_r8.py), on the NATIVE-resolution captures (no resampling, so no new
colours are invented):
- sand lit/shade: the sand boxes of CAM_Ref2Match (measure_r8's 'ours' sand_near + sand_far boxes scaled to the native
  frame), luma split into two clusters (1-D k-means); ratio = median(lit cluster) / median(shade cluster); also the
  lit share of the sand and a penumbra width proxy (share of sand pixels between the two cluster medians' 25-75 % band).
- sky band: rows 0..280 of CAM_Ref2Match (1920 x 1440, above the far ridges) and rows 235..330 of CAM_Establishing
  (between the gate beams and the hall roof): unique RGB colours and zero-gradient share (the mean share of horizontal
  and vertical neighbour pairs with all three channels equal). Ref 2: (40, 0, 1400, 100) of the 1448 x 1086 image.
usage: py -3 extra_r9.py <capture dir> [<capture dir> ...]  -> prints one JSON line per dir
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/Dojo/dojo1_reference2.png"
SAND_1448 = [(100, 760, 600, 1000), (850, 760, 1350, 1000), (100, 615, 620, 690), (800, 615, 1330, 690)]
SAND_REF = [(250, 700, 640, 880), (810, 700, 1200, 880), (270, 500, 660, 590), (790, 500, 1180, 590)]


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def sky(a, box):
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1].astype(np.int32)
    u = len(np.unique(r.reshape(-1, 3), axis=0))
    dx = (np.abs(np.diff(r, axis=1)).sum(2) == 0).mean()
    dy = (np.abs(np.diff(r, axis=0)).sum(2) == 0).mean()
    return {"unique_colours": int(u), "zero_gradient_pct": round(float((dx + dy) / 2 * 100), 2), "px": int(r.shape[0] * r.shape[1])}


def lit_shade(a, boxes=SAND_1448):
    h, w = a.shape[:2]
    sx, sy = w / 1448.0, h / 1086.0
    lu = np.concatenate([luma(a[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)].astype(float)).ravel()
                         for x0, y0, x1, y1 in boxes])
    c0, c1 = np.percentile(lu, 20), np.percentile(lu, 80)
    for _ in range(30):
        m = lu > (c0 + c1) / 2
        n0, n1 = np.median(lu[~m]), np.median(lu[m])
        if abs(n0 - c0) < 1e-3 and abs(n1 - c1) < 1e-3:
            break
        c0, c1 = n0, n1
    lo, hi = c0 + 0.25 * (c1 - c0), c0 + 0.75 * (c1 - c0)
    return {"lit_over_shade": round(float(c1 / max(c0, 1.0)), 3), "lit_median": round(float(c1), 1),
            "shade_median": round(float(c0), 1), "lit_share_pct": round(float(m.mean() * 100), 1),
            "penumbra_band_pct": round(float(((lu > lo) & (lu < hi)).mean() * 100), 1),
            "p85_over_p15": round(float(np.percentile(lu, 85) / max(np.percentile(lu, 15), 1.0)), 3)}


def one(d):
    d = Path(d)
    out = {"dir": str(d)}
    p = d / "CAM_Ref2Match.png"
    if p.exists():
        a = np.asarray(Image.open(p).convert("RGB"))
        out["sand"] = lit_shade(a)
        out["sky_ref2match"] = sky(a, (0, 0, a.shape[1], int(280 * a.shape[0] / 1440)))
    p = d / "CAM_Establishing.png"
    if p.exists():
        a = np.asarray(Image.open(p).convert("RGB"))
        out["sky_establishing"] = sky(a, (0, int(235 * a.shape[0] / 1440), a.shape[1], int(330 * a.shape[0] / 1440)))
    return out


if __name__ == "__main__":
    ref = np.asarray(Image.open(REF).convert("RGB"))
    print(json.dumps({"ref2": {"sky": sky(ref, (40, 0, 1400, 100)), "sand": lit_shade(ref, SAND_REF)}}))
    for d in sys.argv[1:]:
        print(json.dumps(one(d)))
