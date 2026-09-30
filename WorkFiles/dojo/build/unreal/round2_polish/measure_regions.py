"""Round-2 colour measurement: mean colour of named regions (tile / plaster / sand / sky / path) in the showcase
captures and in the Blender renders of the same views, plus the neutral probe cards of the colour probe.

Numbers per region: mean sRGB (0-255), HSV saturation and hue of the mean colour, mean per-pixel saturation.
Regions are pixel boxes (x0, y0, x1, y1) picked on each image for the same surface; overlay PNGs show them.
Run: py -3 measure_regions.py <captures dir> <out json> [--overlay]
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build")
# Blender renders (the colour target): the same surfaces, their own framing
BLENDER = {
    "beauty_gate_from_courtyard": (B / "renders/kit1_f2/beauty_gate_from_courtyard.png", {
        "tile": (470, 305, 1130, 372), "plaster": (10, 585, 180, 660), "sky": (500, 40, 1100, 180),
        "timber_post": (205, 420, 225, 700)}),
    "ground_C_Establish": (B / "ground/renders/f1/C_Establish.png", {
        "sand_lit": (850, 640, 1300, 860), "path": (668, 700, 770, 860), "sky": (300, 30, 1150, 150),
        "gravel": (820, 900, 1300, 990)}),
    "beauty_ref2_through_open_gate": (B / "renders/kit1_f2/beauty_ref2_through_open_gate.png", {}),
}
# Unreal captures (cameras of layout_showcase.json)
UE = {
    "CAM_GateFromCourtyard": {"tile": (640, 365, 1260, 432), "plaster": (30, 690, 200, 780), "sky": (700, 30, 1200, 180),
                              "sand_lit": (1300, 930, 1900, 1070), "timber_post": (262, 500, 290, 820)},
    "CAM_Establishing": {"sand_lit": (950, 860, 1290, 1000), "path": (560, 880, 900, 1030)},
}


def stats(img, box):
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("RGB"), dtype=np.float64)[y0:y1, x0:x1].reshape(-1, 3)
    m = a.mean(0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255.0))
    mx, mn = a.max(1), a.min(1)
    ps = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0.0)
    return {"box": list(box), "mean_rgb": [round(float(c), 1) for c in m], "sat_of_mean": round(s, 3),
            "hue_deg": round(h * 360.0, 1), "value": round(v, 3), "mean_pixel_sat": round(float(ps.mean()), 3)}


def overlay(img, regions, out):
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    for k, b in regions.items():
        d.rectangle(b, outline=(0, 255, 255), width=3)
        d.text((b[0] + 4, b[1] + 4), k, fill=(0, 255, 255))
    im.save(out)


def main():
    cap_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    ov = "--overlay" in sys.argv
    res = {"blender": {}, "unreal": {}}
    for name, (p, regs) in BLENDER.items():
        if not p.exists() or not regs:
            continue
        im = Image.open(p)
        res["blender"][name] = {k: stats(im, b) for k, b in regs.items()}
        if ov:
            overlay(im, regs, out.parent / f"regions_{name}.png")
    for cam, regs in UE.items():
        p = cap_dir / f"{cam}.png"
        if not p.exists() or not regs:
            continue
        im = Image.open(p)
        res["unreal"][cam] = {k: stats(im, b) for k, b in regs.items()}
        if ov:
            overlay(im, regs, out.parent / f"regions_{cam}_{cap_dir.name}.png")
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for side in ("blender", "unreal"):
        for img, rr in res[side].items():
            for k, s in rr.items():
                print(f"{side:8s} {img:32s} {k:12s} rgb {s['mean_rgb']} sat {s['sat_of_mean']} hue {s['hue_deg']}")


main()
