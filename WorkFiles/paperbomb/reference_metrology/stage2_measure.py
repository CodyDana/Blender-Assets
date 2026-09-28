# -*- coding: utf-8 -*-
"""Stage 2 driver: measure one source (V1 | V2 | OURS) and write its JSON."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pngread as P  # noqa: E402
import tagmeas as T  # noqa: E402

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
SCRATCH = os.environ["PB_SCRATCH"]
key = sys.argv[-1]

RECT_W, RECT_H = 840, 1872


def resample(f, x0, y0, x1, y1, w, h):
    """Bilinear resample of the axis-aligned box [x0,x1)x[y0,y1) to w x h."""
    xs = x0 + (np.arange(w) + 0.5) * (x1 - x0) / w - 0.5
    ys = y0 + (np.arange(h) + 0.5) * (y1 - y0) / h - 0.5
    xs = np.clip(xs, 0, f.shape[1] - 1.001)
    ys = np.clip(ys, 0, f.shape[0] - 1.001)
    xi = np.floor(xs).astype(int)
    yi = np.floor(ys).astype(int)
    fx = (xs - xi)[None, :, None]
    fy = (ys - yi)[:, None, None]
    a = f[np.ix_(yi, xi)]
    b = f[np.ix_(yi, xi + 1)]
    c = f[np.ix_(yi + 1, xi)]
    d = f[np.ix_(yi + 1, xi + 1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


t0 = time.time()
support_override = None
aspect = None

if key in ("V1", "V2"):
    geo = json.load(open(HERE + "/debug/stage1_rectify.json", encoding="utf-8"))[key]
    rect = np.load(os.path.join(SCRATCH, "rect_%s.npy" % key)).astype(np.float64)
    src = (ROOT + "/References/PaperBomb/paperbomb_guide.png" if key == "V1"
           else ROOT + "/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png")
    arr, info = P.read_png(src)
    f = P.to_float(arr, info)[..., :3]
    c = geo["corners_px"]
    x0 = int(np.ceil(max(c["TL"][0], c["BL"][0])))
    x1 = int(np.floor(min(c["TR"][0], c["BR"][0])))
    y0 = int(np.ceil(max(c["TL"][1], c["TR"][1])))
    y1 = int(np.floor(min(c["BL"][1], c["BR"][1])))
    native = f[y0:y1, x0:x1]
    native_ppmm = geo["source_px_per_mm"]
    aspect = geo["aspect_h_over_w"]
    name = key

elif key == "OURS":
    arr, info = P.read_png(ROOT + "/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
    f = P.to_float(arr, info)[..., :3]
    PPMM = 12.923
    PAD = 16
    CW, CH = 70.0 * PPMM, 156.0 * PPMM          # 904.61 x 2015.99
    rect = resample(f, PAD, PAD, PAD + CW, PAD + CH, RECT_W, RECT_H)
    native = f[PAD:int(PAD + CH) + 1, PAD:int(PAD + CW) + 1]
    native_ppmm = PPMM
    aspect = 156.0 / 70.0
    name = "OURS_T_PaperBomb_BC_front_island"
    # analytic octagon: corner_clip_mm = 7.6 (props_lib.spec.corner_clip_mm)
    CLIP = 7.6
    u = (np.arange(RECT_W) + 0.5) / RECT_W * 70.0
    v = (np.arange(RECT_H) + 0.5) / RECT_H * 156.0
    U, V = np.meshgrid(u, v)
    support_override = ((U + V > CLIP) & ((70.0 - U) + V > CLIP)
                        & (U + (156.0 - V) > CLIP) & ((70.0 - U) + (156.0 - V) > CLIP))
else:
    raise SystemExit("key must be V1 | V2 | OURS")

# native-resolution support: same rule, scaled
nh, nw = native.shape[:2]
if support_override is not None:
    nu = (np.arange(nw) + 0.5) / nw * 70.0
    nv = (np.arange(nh) + 0.5) / nh * 156.0
    NU, NV = np.meshgrid(nu, nv)
    nsup = ((NU + NV > 7.6) & ((70.0 - NU) + NV > 7.6)
            & (NU + (156.0 - NV) > 7.6) & ((70.0 - NU) + (156.0 - NV) > 7.6))
else:
    nsup = None

print("%s: rect %dx%d  native %dx%d @ %.3f px/mm" % (name, RECT_W, RECT_H, nw, nh, native_ppmm))
m = T.TagMeasure(rect, name, native_ppmm, native, aspect)
out = m.run(native_rgb=native, native_support=nsup, support_override=support_override)
out["_frame"]["source_file"] = (src if key in ("V1", "V2")
                                else ROOT + "/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
out["_frame"]["seconds"] = round(time.time() - t0, 1)
dst = os.path.join(SCRATCH, "meas_%s.json" % key)
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
print("wrote", dst, "in %.1fs" % (time.time() - t0))
print("coverage:", json.dumps(out["coverage"]["total"], indent=1))
