"""Round 5 f1: fit the painted-sky -> captured-output response (per channel) on DojoLab captures of the dome.

For sky-only boxes of some showcase cameras, every capture pixel is traced back to its dome texel (the sky_dome
material's own mapping; the same pinhole as the SceneCapture: horizontal FOV, look-at frame), giving pairs
(painted linear value, captured sRGB). Per channel: quantile bins -> monotone median curve. The inverse (desired output
sRGB -> painted linear) is written for make_sky_sunset.py --calib. Painted values above 1.0 are allowed in the table;
make_sky_sunset divides by 'scale' and the dome Intensity must be multiplied by it (reported).

py -3 fit_sky_calib.py <capture_dir> <painted_png> <out_json> [old_calib_json]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
L = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text())
CAMS = {c["name"]: c for c in L["cameras"]}
BOXES = {   # sky-only boxes (x0, y0, x1, y1) on the full-size stills
    "CU_R5_FarBackground": [(0, 0, 1920, 120)],
    "CAM_GateFromCourtyard": [(150, 0, 1750, 190)],
    "CU_R5_Skyline": [(0, 0, 1920, 330)],
    "CAM_EstablishingRef2": [(0, 0, 1448, 90)],
    "CAM_Establishing": [(0, 130, 200, 240), (1250, 130, 1448, 220)],
}


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def dirs(c, w, h):
    loc, at = np.array(c["loc"]), np.array(c["look_at"])
    f = at - loc
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    fx = (w / 2) / math.tan(math.radians(c["hfov_deg"]) / 2)
    xs, ys = np.meshgrid(np.arange(w) - w / 2 + 0.5, np.arange(h) - h / 2 + 0.5)
    d = f[None, None] * fx + r[None, None] * xs[..., None] - u[None, None] * ys[..., None]
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def bilinear(img, x, y):
    H, W = img.shape[:2]
    x0 = np.floor(x).astype(int)
    y0 = np.clip(np.floor(y).astype(int), 0, H - 1)
    fx, fy = (x - x0)[..., None], np.clip(y - y0, 0, 1)[..., None]
    x0 %= W
    x1 = (x0 + 1) % W
    y1 = np.clip(y0 + 1, 0, H - 1)
    return (img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy


def main():
    cap_dir, png, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    sky = srgb_to_lin(np.asarray(Image.open(png).convert("RGB"), np.float32)).astype(np.float32)
    H, W = sky.shape[:2]
    P, Cc = [], []
    for cam, boxes in BOXES.items():
        f = cap_dir / f"{cam}.png"
        if not f.exists():
            continue
        im = Image.open(f).convert("RGB").filter(ImageFilter.MedianFilter(5))
        a = np.asarray(im, np.float32)
        w, h = CAMS[cam]["out_wh"]
        d = dirs(CAMS[cam], w, h)
        dx, dy, dz = d[..., 0], -d[..., 1], d[..., 2]
        uu = (np.arctan2(dy, dx) / (2 * math.pi) + 0.5) * W - 0.5
        vv = (1 - np.arcsin(np.clip(dz, 0, 1)) / (math.pi / 2)) * H - 0.5
        for (x0, y0, x1, y1) in boxes:
            sl = (slice(y0, y1, 2), slice(x0, x1, 2))
            P.append(bilinear(sky, uu[sl], vv[sl]).reshape(-1, 3))
            Cc.append(a[sl].reshape(-1, 3))
    P, Cc = np.concatenate(P), np.concatenate(Cc)
    res = {"n": int(len(P)), "paint_lin": [], "out": [], "fwd": []}
    Pp, Cp = P.reshape(-1), Cc.reshape(-1)          # pooled over R, G, B: one tonemapper curve (the per-channel ranges
    for i in range(3):                              # of a sky are too narrow to fit alone)
        o = np.argsort(Pp)
        p, c = Pp[o], Cp[o]
        nb = 48
        edges = np.linspace(0, len(p), nb + 1).astype(int)
        pb = np.array([np.median(p[a:b]) for a, b in zip(edges[:-1], edges[1:]) if b > a])
        cb = np.array([np.median(c[a:b]) for a, b in zip(edges[:-1], edges[1:]) if b > a])
        cb = np.maximum.accumulate(cb)
        # extend: through the origin at the bottom; at the top a power law through the last bins (the tonemapper
        # shoulder), up to painted 4.0
        k = max(1, len(pb) // 6)
        lp, lc = np.log(np.maximum(pb[-k:], 1e-4)), np.log(np.maximum(cb[-k:], 1e-3))
        slope = max(0.05, float(np.polyfit(lp, lc, 1)[0]))
        top_p = np.array([pb[-1] * s for s in (1.25, 1.6, 2.0, 2.6, 3.4, 4.5)])
        top_c = np.minimum(cb[-1] * (top_p / pb[-1]) ** slope, 255.0)
        pb2 = np.concatenate([[0.0], pb, top_p])
        cb2 = np.concatenate([[0.0], cb, top_c])
        cb2 = np.maximum.accumulate(cb2 + np.arange(len(cb2)) * 1e-3)
        res["paint_lin"].append([round(float(v), 6) for v in pb2])
        res["out"].append([round(float(v), 3) for v in cb2])
        res["fwd"].append({"slope_top": round(slope, 3), "p_range": [round(float(pb[0]), 4), round(float(pb[-1]), 4)],
                           "c_range": [round(float(cb[0]), 1), round(float(cb[-1]), 1)]})
    out.write_text(json.dumps(res, indent=1))
    print("CALIB", json.dumps(res["fwd"]), res["n"])


main()
