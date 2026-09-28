"""Backdrop luminance at fixed frame points of every hero (Blender's python: numpy + OpenImageIO).

    "<blender>/5.2/python/bin/python.exe" backdrop_probe.py [renders_dir] [diag_dir]
"""
import json
import sys

import numpy as np
import OpenImageIO as oiio

R = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/Cody/Desktop/Blender_Projects/Renders/Shuriken/"
D = sys.argv[2] if len(sys.argv) > 2 else r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/diag/"
FORMS = sys.argv[3].split(",") if len(sys.argv) > 3 else ["four_point", "eight_point", "square_plate", "six_point", "spike"]
W = np.array([0.2126, 0.7152, 0.0722])
POINTS = {"tl": (0.0125, 0.0222), "tr": (0.9875, 0.0222), "bl": (0.0125, 0.9778), "br": (0.9875, 0.9778),
          "r28": (0.9875, 0.28), "r50": (0.9875, 0.50), "r78": (0.9875, 0.78),
          "q11": (0.90, 0.11), "q50": (0.90, 0.50), "q78": (0.90, 0.78), "t03": (0.80, 0.03), "t97": (0.80, 0.97)}


def load(p):
    return np.asarray(oiio.ImageBuf(p).get_pixels(oiio.FLOAT))


def dilate(m, k):
    out = m.copy()
    for _ in range(k):
        s = out.copy()
        for ax in (0, 1):
            s |= np.roll(out, 1, ax)
            s |= np.roll(out, -1, ax)
        out = s
    return out


res = {}
for f in FORMS:
    px = load(R + f"{f}_persp.png")
    m = load(D + f"{f}_persp_mask.png")
    lum = px[..., :3].astype(np.float64) @ W
    obj = dilate(m[..., 3] > 0.02, 3)
    h, w = lum.shape
    out = {}
    for k, (fx, fy) in POINTS.items():
        cx, cy = int(round(fx * (w - 1))), int(round(fy * (h - 1)))
        y0, y1, x0, x1 = max(cy - 5, 0), min(cy + 6, h), max(cx - 5, 0), min(cx + 6, w)
        patch, valid = lum[y0:y1, x0:x1], ~obj[y0:y1, x0:x1]
        out[k] = round(float(np.median(patch[valid])), 4) if valid.mean() >= 0.5 else None
    res[f] = out
print("point  " + " ".join(f"{f[:10]:>11}" for f in res))
for k in POINTS:
    print(f"{k:6} " + " ".join(f"{str(res[f][k]):>11}" for f in res))
print(json.dumps(res))
