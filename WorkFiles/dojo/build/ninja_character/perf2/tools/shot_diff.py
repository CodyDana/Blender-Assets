"""perf2: visual cost of a lever = HighResShot (1920x1080) with the lever against the base shot of the same view, next
to the live-noise floor (base against a second base shot of the same view: clouds, wind, cloth, grooms move).
Metrics on 8-bit sRGB: mean |diff| over the frame, % of pixels changed by > 8 / > 24 levels (max channel), and the same
inside the pawn box (the pawn is placed in front of the camera; box = the changed region of base vs pawn-hidden if
given, else none). Also writes a side-by-side + amplified diff JPG per pair.
usage: shot_diff.py <shots_dir> <pairs.json: [[label, base_png, lever_png], ...]> <out.json>"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

D = Path(sys.argv[1])
PAIRS = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
OUT = Path(sys.argv[3])


def load(n):
    return np.asarray(Image.open(D / n).convert("RGB")).astype(np.int16)


# pawn region per view (full-res px, read off the pawn_hidden pairs): the lever's visual cost ON the character
ROI = {"PES": (800, 500, 1110, 1080), "WA": (790, 400, 1140, 1080), "RR": (810, 560, 1100, 880), "PAWN": (800, 450, 1130, 1080)}
res = []
for label, a, b in PAIRS:
    if not (D / a).exists() or not (D / b).exists():
        res.append({"label": label, "missing": [x for x in (a, b) if not (D / x).exists()]})
        continue
    A, B = load(a), load(b)
    d = np.abs(A - B).max(axis=2)
    r = {"label": label, "base": a, "lever": b, "mean_abs": round(float(np.abs(A - B).mean()), 3),
         "pct_gt8": round(100.0 * float((d > 8).mean()), 3), "pct_gt24": round(100.0 * float((d > 24).mean()), 3),
         "mean_luma_base": round(float(A.mean()), 2), "mean_luma_lever": round(float(B.mean()), 2)}
    view = label.split("_")[1] if label.startswith("NOISE_") else label.split("_")[0]
    if view in ROI:
        x0, y0, x1, y1 = ROI[view]
        dr = d[y0:y1, x0:x1]
        r["roi_view"] = view
        r["roi_mean_abs"] = round(float(np.abs(A[y0:y1, x0:x1] - B[y0:y1, x0:x1]).mean()), 3)
        r["roi_pct_gt24"] = round(100.0 * float((dr > 24).mean()), 3)
    ys, xs = np.nonzero(d > 24)
    if len(xs):
        r["changed_box_gt24"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    res.append(r)
    amp = np.clip(d * 4, 0, 255).astype(np.uint8)
    full = Image.new("RGB", (2880, 540))
    full.paste(Image.fromarray(A.astype(np.uint8)).resize((960, 540)), (0, 0))
    full.paste(Image.fromarray(B.astype(np.uint8)).resize((960, 540)), (960, 0))
    full.paste(Image.fromarray(amp).convert("RGB").resize((960, 540)), (1920, 0))
    full.save(OUT.parent / f"pair_{label}.jpg", quality=88)
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
for r in res:
    print(r)
