"""SHOWCASE_SHEET_R2.png: the combined DojoLab import round 2 (2026-09-28) captures on one sheet, plus measured medians.

Run: py -3 WorkFiles/dojo/build/unreal/showcase_r2/make_sheet_r2.py
In:  WorkFiles/dojo/build/unreal/showcase/captures/CAM_*.png (dj_sc_capture.py), References/Dojo/dojo1_reference2.png
Out: WorkFiles/dojo/build/unreal/showcase/captures/SHOWCASE_SHEET_R2.png (+ a copy beside this script),
     WorkFiles/dojo/build/unreal/showcase_r2/capture_regions_r2.json (sRGB medians of fixed regions)
"""
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "showcase" / "captures"
HERE = Path(__file__).resolve().parent
REF2 = ROOT / "References" / "Dojo" / "dojo1_reference2.png"
TILES = [
    ("REF", "dojo1_reference2 (AI-generated modelling reference, look only)"),
    ("CAM_Establishing", "Establishing: in the gateway toward the hall (ref 2 aspect)"),
    ("CAM_EstablishingRef2", "Ref 2 elevated framing (3.1 m, past the gate eave)"),
    ("CAM_PlayerEyeSand", "Player eye on the raked sand toward the hall"),
    ("CAM_HallVeranda", "Hall kit close: granite step band, central stair, veranda"),
    ("CAM_HallRoofClimb", "Routes 4-5: eave landing deck, lower roof, roof AC (+5.10)"),
    ("CAM_GateFromCourtyard", "Gate from the courtyard (short lanterns inside the gate)"),
    ("CAM_GateFromStreet", "Gate from the street"),
    ("CAM_Drum", "Taiko under the (grey-box) pavilion"),
    ("CAM_EastYard", "East yard: well, residence lamp, hall east side"),
    ("CAM_VendingShed", "Vending machine (true 0.80 m depth) / shed corner"),
    ("CAM_WallTop", "West wall top"),
    ("CAM_WallCorner", "SE wall corner from outside"),
    ("CAM_Overview", "Overview from above the gate"),
]
# fixed measurement boxes (x0, y0, x1, y1) in each capture's own pixels
REGIONS = {
    "CAM_EstablishingRef2": {"upper_roof_tiles": (560, 215, 880, 260), "front_lattice_glow": (600, 450, 660, 520),
                             "sand_left": (100, 650, 450, 750), "path": (640, 800, 760, 900), "sky": (300, 40, 1100, 140)},
    "CAM_PlayerEyeSand": {"upper_roof_tiles": (700, 215, 1200, 280), "front_lattice_glow": (1000, 545, 1070, 640),
                          "step_band": (500, 690, 800, 720), "sand": (100, 800, 600, 1000), "sky": (300, 40, 1500, 140)},
    "CAM_HallVeranda": {"deck": (1300, 700, 1600, 760), "step_band_riser": (1000, 780, 1300, 840),
                        "post": (1120, 300, 1160, 600)},
    "CAM_GateFromCourtyard": {"gate_tiles": (700, 380, 1200, 430), "wall_plaster": (80, 690, 450, 780)},
}


def fit(img, w, h):
    s = min(w / img.width, h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def main():
    tw, th, pad, lab = 640, 360, 14, 34
    cols = 4
    rows = (len(TILES) + 1 + cols - 1) // cols
    W = cols * tw + (cols + 1) * pad
    head = 70
    H = head + rows * (th + lab + pad) + pad
    sheet = Image.new("RGB", (W, H), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    f_big = ImageFont.truetype("arialbd.ttf", 30)
    f = ImageFont.truetype("arial.ttf", 17)
    d.text((pad, 18), "DojoLab L_Dojo - combined import round 2 (2026-09-28): hall kit + kit 1 r2f + ground + all props, "
                      "shared material library, UE 5.8 offscreen captures (Lumen, 96 frames)", font=f_big,
           fill=(235, 235, 235))
    for k, (name, text) in enumerate(TILES):
        r, c = divmod(k, cols)
        x = pad + c * (tw + pad)
        y = head + r * (th + lab + pad)
        path = REF2 if name == "REF" else CAP / f"{name}.png"
        img = Image.open(path).convert("RGB")
        t = fit(img, tw, th)
        sheet.paste(t, (x + (tw - t.width) // 2, y + (th - t.height) // 2))
        d.text((x + 2, y + th + 6), (name if name != "REF" else "REFERENCE") + " - " + text, font=f, fill=(220, 220, 220))
    out = CAP / "SHOWCASE_SHEET_R2.png"
    sheet.save(out, optimize=True)
    shutil.copy2(out, HERE / "SHOWCASE_SHEET_R2.png")
    meas = {}
    for cam, boxes in REGIONS.items():
        a = np.asarray(Image.open(CAP / f"{cam}.png").convert("RGB")).astype(float)
        meas[cam] = {}
        for rn, (x0, y0, x1, y1) in boxes.items():
            px = a[y0:y1, x0:x1].reshape(-1, 3)
            med = np.median(px, axis=0)
            mx, mn = med.max(), med.min()
            meas[cam][rn] = {"box": [x0, y0, x1, y1], "median_srgb": [int(round(v)) for v in med],
                             "saturation": round(float((mx - mn) / mx) if mx > 0 else 0.0, 3),
                             "clipped_frac": round(float((px.max(axis=1) >= 254).mean()), 4)}
    (HERE / "capture_regions_r2.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    print("SHEET", out, sheet.size)
    print(json.dumps(meas, indent=0))


main()
