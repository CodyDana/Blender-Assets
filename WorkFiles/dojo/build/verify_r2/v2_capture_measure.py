"""VERIFY r2: capture colour measurement (plain Python, read-only). Regions picked by the verifier on each image.
Out: verify_r2/capture_measure.json"""
import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build")
CAP = B / "unreal" / "showcase" / "captures"
R2 = B / "unreal" / "showcase_r2"
OUT = B / "verify_r2" / "capture_measure.json"


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64)


def region(a, box):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(px, axis=0)
    h, s, v = colorsys.rgb_to_hsv(*(med / 255.0))
    return {"box": box, "median_srgb": [int(round(c)) for c in med], "hue_deg": round(h * 360, 1), "sat": round(s, 3),
            "val": round(v, 3), "r_over_b": round(float(med[0] / max(med[2], 1)), 3),
            "clipped_frac": round(float(np.mean(np.all(px >= 250, axis=1))), 4)}


PAIRS = {
    # (UE capture, Blender render, {name: (ue_box, blender_box)})
    "ref2_elevated": (CAP / "CAM_EstablishingRef2.png", B / "hall/renders/r2/context_ref2_elevated.png", {
        "upper_roof_tiles": ((470, 215, 960, 285), (470, 280, 980, 365)),
        "lower_roof_tiles": ((330, 378, 1100, 420), (330, 445, 1100, 490)),
        "sand": ((100, 640, 450, 760), (100, 680, 500, 860)),
        "path": ((640, 800, 760, 900), (680, 700, 760, 820)),
        "sky": ((300, 40, 1100, 140), (300, 40, 1100, 140)),
    }),
    "gate_from_courtyard": (CAP / "CAM_GateFromCourtyard.png", B / "renders/kit1_r2f/beauty_gate_from_courtyard.png", {
        "gate_tiles": ((650, 370, 1300, 430), (500, 318, 1100, 372)),
        "wall_tiles_left": ((20, 625, 460, 655), (20, 530, 390, 560)),
        "wall_plaster_left": ((20, 690, 470, 780), (20, 585, 385, 660)),
        "wall_plaster_right_sunlit": ((1450, 690, 1780, 780), (1200, 590, 1440, 660)),
        "footing": ((20, 800, 460, 850), (20, 675, 390, 725)),
        "gate_post_left": ((495, 600, 540, 790), (415, 480, 455, 680)),
        "sky": ((200, 40, 1700, 160), (200, 40, 1400, 160)),
    }),
}


def cmp(ue, bl):
    return {"d_sat": round(ue["sat"] - bl["sat"], 3), "d_r_over_b": round(ue["r_over_b"] - bl["r_over_b"], 3),
            "val_ratio": round(ue["val"] / max(bl["val"], 1e-6), 3), "d_hue_deg": round(ue["hue_deg"] - bl["hue_deg"], 1)}


res = {"pairs": {}, "images": {}}
for key, (ue_p, bl_p, regs) in PAIRS.items():
    ua, ba = load(ue_p), load(bl_p)
    res["pairs"][key] = {}
    for name, (ub, bb) in regs.items():
        u, b = region(ua, ub), region(ba, bb)
        res["pairs"][key][name] = {"ue": u, "blender": b, "delta": cmp(u, b)}

# whole-image health: black, blown, missing (flat) content
imgs = sorted(CAP.glob("CAM_*.png")) + sorted((R2 / "captures_emissive_x025").glob("CAM_*.png")) + \
    [R2 / "SHOWCASE_SHEET_R2.png", CAP / "SHOWCASE_SHEET_R2.png"]
for p in imgs:
    a = load(p)
    mx = a.max(axis=2)
    lum = a @ np.array([0.2126, 0.7152, 0.0722])
    h, w = mx.shape
    # largest near-black blob proxy: fraction of 32x32 tiles that are > 90 % near-black
    t = 32
    tiles = mx[: h // t * t, : w // t * t].reshape(h // t, t, w // t, t).swapaxes(1, 2).reshape(-1, t * t)
    black_tiles = float(np.mean(np.mean(tiles < 12, axis=1) > 0.9))
    blown = a.min(axis=2) >= 250
    ttiles = blown[: h // t * t, : w // t * t].reshape(h // t, t, w // t, t).swapaxes(1, 2).reshape(-1, t * t)
    res["images"][str(p.relative_to(B))] = {
        "size": [w, h], "mean_lum": round(float(lum.mean()), 1),
        "near_black_frac": round(float(np.mean(mx < 12)), 4), "black_tile_frac": round(black_tiles, 4),
        "blown_frac": round(float(np.mean(blown)), 4),
        "blown_tile_frac": round(float(np.mean(np.mean(ttiles, axis=1) > 0.5)), 4),
        "any_channel_255_frac": round(float(np.mean(a.max(axis=2) >= 255)), 4),
        "mean_r_minus_b": round(float((a[..., 0] - a[..., 2]).mean()), 1)}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in res["pairs"].items():
    for n, r in v.items():
        print(k, n, "UE", r["ue"]["median_srgb"], r["ue"]["sat"], r["ue"]["r_over_b"], "| BL", r["blender"]["median_srgb"],
              r["blender"]["sat"], r["blender"]["r_over_b"], "|", r["delta"])
for k, v in res["images"].items():
    print(k, v)
