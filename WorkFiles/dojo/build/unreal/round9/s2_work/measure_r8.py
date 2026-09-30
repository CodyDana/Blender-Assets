"""Round 8: reference 2 vs our CAM_Ref2Match (matched framing), both resampled to 1448 x 1086 (the reference size).
Whole-frame luma (Rec.709 weights on the sRGB values): share under 40, mean, p90. Ground texture: the high-pass luma std
(luma minus a 6 px Gaussian) in a sand box and the plain luma std. Regions (boxes picked per image on the gridded
frames, since the two framings differ): median sRGB, HLS hue / saturation / lightness, R/B.
usage: py -3 measure_r8.py <out.json> <label>=<png> [<label>=<png> ...]
"""
import colorsys
import json
import sys

import numpy as np
from PIL import Image, ImageFilter

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/Dojo/dojo1_reference2.png"
W, H = 1448, 1086
# (x0, y0, x1, y1) in the 1448 x 1086 frame; a list = pooled boxes; "mode": median | top30 | bot50 | top10
BOX = {
    "ref": {
        "tiles_lit": ([(520, 140, 940, 250)], "top30"),
        "tiles_shade": ([(520, 140, 940, 250), (410, 280, 1050, 320)], "bot50"),
        "plaster": ([(120, 250, 275, 300), (1170, 250, 1320, 300)], "median"),
        "sand_near": ([(250, 700, 640, 880), (810, 700, 1200, 880)], "median"),
        "sand_far": ([(270, 500, 660, 590), (790, 500, 1180, 590)], "median"),
        "gravel": ([(230, 395, 380, 440), (1100, 395, 1230, 440), (260, 905, 630, 940)], "median"),
        "horizon_sky_behind_hall": ([(40, 100, 480, 150), (960, 100, 1350, 140)], "median"),
        "top_sky": ([(300, 0, 1448, 50)], "median"),
        "shoji_glow": ([(490, 335, 990, 395)], "top30"),
        "lantern_glow": ([(598, 385, 630, 420), (818, 385, 852, 420)], "top10"),
        "timber": ([(360, 405, 1090, 445)], "median"),
        "sand_tex": [(300, 720, 620, 860), (830, 720, 1150, 860)],
    },
    "ours": {
        "tiles_lit": ([(480, 260, 960, 380)], "top30"),
        "tiles_shade": ([(480, 260, 960, 380), (330, 440, 1120, 480)], "bot50"),
        "plaster": ([(110, 395, 280, 445), (1170, 395, 1330, 445)], "median"),
        "sand_near": ([(100, 760, 600, 1000), (850, 760, 1350, 1000)], "median"),
        "sand_far": ([(100, 615, 620, 690), (800, 615, 1330, 690)], "median"),
        "gravel": ([(20, 545, 320, 590), (1130, 545, 1340, 590)], "median"),
        "horizon_sky_behind_hall": ([(0, 225, 450, 265), (1000, 225, 1440, 265)], "median"),
        "top_sky": ([(300, 0, 1448, 50)], "median"),
        "shoji_glow": ([(500, 488, 950, 540)], "top30"),
        "lantern_glow": ([(592, 552, 630, 600), (822, 552, 860, 600)], "top10"),
        "timber": ([(350, 555, 1100, 585)], "median"),
        "sand_tex": [(880, 780, 1180, 960), (1100, 650, 1400, 760)],
    },
}


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def pooled(a, boxes):
    return np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for x0, y0, x1, y1 in boxes])


def region(a, boxes, mode):
    px = pooled(a, boxes)
    lu = luma(px)
    if mode != "median":
        q = {"top30": 70, "bot50": None, "top10": 90}[mode]
        px = px[lu <= np.percentile(lu, 50)] if mode == "bot50" else px[lu >= np.percentile(lu, q)]
    m = np.median(px, axis=0)
    h, l, s = colorsys.rgb_to_hls(*(m / 255.0))
    return {"rgb": [int(round(v)) for v in m], "hue": round(h * 360, 1), "hls_s": round(s, 3), "L": round(l, 3),
            "r_over_b": round(float(m[0] / max(m[2], 1.0)), 3), "clip_pct": round(float((pooled(a, boxes) >= 254).any(1).mean() * 100), 2)}


def measure(path, key):
    im = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64)
    lu = luma(a)
    blur = np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(6))).astype(np.float64)
    hp = np.asarray(im.convert("L")).astype(np.float64) - blur
    out = {"file": path, "luma_share_under_40_pct": round(float((lu < 40).mean() * 100), 2),
           "luma_mean": round(float(lu.mean()), 1), "luma_p90": round(float(np.percentile(lu, 90)), 1),
           "luma_p10": round(float(np.percentile(lu, 10)), 1), "clip_pct": round(float((a >= 254).any(2).mean() * 100), 2)}
    tb = BOX[key]["sand_tex"]
    out["sand_texture_highpass_std"] = round(float(np.concatenate([hp[y0:y1, x0:x1].ravel() for x0, y0, x1, y1 in tb]).std()), 2)
    out["sand_luma_std"] = round(float(np.concatenate([lu[y0:y1, x0:x1].ravel() for x0, y0, x1, y1 in tb]).std()), 2)
    out["regions"] = {k: region(a, *v) for k, v in BOX[key].items() if k != "sand_tex"}
    return out


def main():
    res = {"ref2": measure(REF, "ref")}
    for arg in sys.argv[2:]:
        lab, p = arg.split("=", 1)
        res[lab] = measure(p, "ours")
    json.dump(res, open(sys.argv[1], "w"), indent=1)
    labs = list(res)
    print("| metric | " + " | ".join(labs) + " |")
    print("|---|" + "---|" * len(labs))
    for k in ("luma_share_under_40_pct", "luma_mean", "luma_p90", "luma_p10", "clip_pct", "sand_texture_highpass_std",
              "sand_luma_std"):
        print(f"| {k} | " + " | ".join(str(res[l][k]) for l in labs) + " |")
    for r in res["ref2"]["regions"]:
        cells = []
        for l in labs:
            g = res[l]["regions"][r]
            cells.append(f"({g['rgb'][0]}, {g['rgb'][1]}, {g['rgb'][2]}) h{g['hue']:.0f} s{g['hls_s']:.2f} R/B {g['r_over_b']:.2f}")
        print(f"| {r} | " + " | ".join(cells) + " |")


main()
