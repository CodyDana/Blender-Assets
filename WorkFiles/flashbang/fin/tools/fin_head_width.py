"""Head silhouette width at H = 3.3 / 3.4 / 3.5 D (and the lever / ring limb extents) per view: ours (the build's alpha
row, WorkFiles/flashbang/build/flashbang_row_alpha.png) vs the Study's traced outlines (flashbang_spec.json).
Also the paint p10/p50/p90 are in the build report.  Writes WorkFiles/flashbang/fin/head_width.json.
    blender -b --factory-startup --python fin_head_width.py
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/props"))
from props_lib import flashbang_gallery as GAL  # noqa: E402

im = bpy.data.images.load(str(P / "WorkFiles/flashbang/build/flashbang_row_alpha.png"))
w, h = im.size
a = np.empty(w * h * 4, np.float32)
im.pixels.foreach_get(a)
alpha = a.reshape(h, w, 4)[::-1, :, 3]
spec = json.loads((P / "WorkFiles/flashbang/flashbang_spec.json").read_text())
yy, xx = np.mgrid[0:h, 0:w]


def poly_mask(poly):
    poly = np.asarray(poly, float)
    m = np.zeros((h, w), bool)
    x0, y0 = poly.min(0).astype(int)
    x1, y1 = poly.max(0).astype(int) + 1
    sy, sx = yy[y0:y1, x0:x1] + 0.5, xx[y0:y1, x0:x1] + 0.5
    ins = np.zeros(sx.shape, bool)
    for i in range(len(poly)):
        xa, ya = poly[i]
        xb, yb = poly[(i + 1) % len(poly)]
        ins ^= ((ya > sy) != (yb > sy)) & (sx < (xb - xa) * (sy - ya) / (yb - ya + 1e-12) + xa)
    m[y0:y1, x0:x1] = ins
    return m


out = {}
for v, (bx0, by0, bx1, by1) in GAL.VIEW_BOX.items():
    ref = poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"])
    ours = alpha > 0.5
    rec = {}
    for H in (3.3, 3.4, 3.5):
        y = int(round(GAL.VIEW_BOTTOM[v] - H * GAL.D_PX))
        r = {}
        for tag, m in (("ref", ref), ("ours", ours)):
            row = np.nonzero(m[y, bx0:bx1])[0]
            r[tag] = round(float((row.max() - row.min() + 1) / GAL.D_PX), 3) if len(row) else None
        rec[f"H{H}"] = r
    iou = float((ref & (alpha > 0.5))[by0:by1, bx0:bx1].sum() / max((ref | (alpha > 0.5))[by0:by1, bx0:bx1].sum(), 1))
    rec["silhouette_iou_alpha"] = round(iou, 4)
    out[v] = rec
(P / "WorkFiles/flashbang/fin/head_width.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out))
