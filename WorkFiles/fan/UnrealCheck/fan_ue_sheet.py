"""Blender (headless) half of the Unreal fold proof: composite pass 2's offscreen captures over a grey ground (the
HDR capture's alpha is the coverage mask), measure each shot's opening FROM THE PIXELS (the angular span of the fan
between 13 and 18.5 cm from the rivet), and write the sheet.

    blender -b --factory-startup --python fan_ue_sheet.py -- <pass2.json> <out_png> <out_json>
"""
import json
import math
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
P2 = json.loads(open(args[0], encoding="utf-8").read())
OUT_PNG, OUT_JSON = args[1], args[2]

FONT = {  # 5x7
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    " ": ["00000"] * 7,
    "d": ["00001", "00001", "01101", "10011", "10001", "10011", "01101"],
    "e": ["00000", "00000", "01110", "10001", "11111", "10000", "01110"],
    "g": ["00000", "01111", "10001", "10001", "01111", "00001", "01110"],
    "s": ["00000", "00000", "01111", "10000", "01110", "00001", "11110"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "m": ["00000", "00000", "11010", "10101", "10101", "10101", "10101"],
    "a": ["00000", "00000", "01110", "00001", "01111", "10001", "01111"],
    "x": ["00000", "00000", "10001", "01010", "00100", "01010", "10001"],
    "p": ["00000", "00000", "11110", "10001", "11110", "10000", "10000"],
    "n": ["00000", "00000", "10110", "11001", "10001", "10001", "10001"],
}


def text(img, s, x, y, scale=3, colour=(0.9, 0.9, 0.88)):
    for ch in s:
        g = FONT.get(ch, FONT[" "])
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == "1":
                    y0 = y + r * scale
                    x0 = x + c * scale
                    img[y0:y0 + scale, x0:x0 + scale, :3] = colour
        x += 6 * scale


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]      # top row first
    bpy.data.images.remove(im)
    return a


shots = P2["renders"]["shots"]
cam = P2["renders"]["camera"]
px = cam["px"]
cm_per_px = cam["ortho_width_cm"] / px
cx, cy = cam["loc_cm"][0], cam["loc_cm"][1]
# pivot (component origin) in pixels: image right = +X, image up = -Y (Unreal) = +Y (Blender)
piv_x = px / 2 + (0.0 - cx) / cm_per_px
piv_y = px / 2 + (0.0 - cy) / cm_per_px
yy, xx = np.mgrid[0:px, 0:px]
rx = (xx + 0.5 - piv_x) * cm_per_px
ry = -(yy + 0.5 - piv_y) * cm_per_px
rad = np.hypot(rx, ry)
ang = np.degrees(np.arctan2(ry, rx))
ring = (rad > 13.0) & (rad < 18.5)

tiles, meas = [], []
for s in shots:
    rgb = load(s["file"])                                     # PNG: display-referred values
    alpha = load(s["file"][:-4] + "_hdr.png")[..., 3]
    mask = alpha < 0.5
    ground = np.array([0.42, 0.42, 0.41], np.float32)
    out = np.empty((px, px, 4), np.float32)
    out[..., :3] = np.where(mask[..., None], rgb[..., :3], ground)
    out[..., 3] = 1.0
    sel = mask & ring
    a = ang[sel]
    a = np.where(a < -90.0, a + 360.0, a)                    # the fan spans about -2 .. 170 deg
    span = float(a.max() - a.min()) if a.size else 0.0
    rec = {"file": s["file"], "coverage_px": int(mask.sum()), "ring_span_deg": round(span, 2),
           "ring_min_deg": round(float(a.min()), 2) if a.size else None, "ring_max_deg": round(float(a.max()), 2) if a.size else None}
    if "expected_opening_deg" in s:
        rec["expected_opening_deg"] = s["expected_opening_deg"]
        rec["engine_opening_deg"] = round(s["opening_deg"], 4)
        label = f"{s['deg']:.1f} deg"
    else:
        rec["engine_opening_deg"] = round(s["opening_deg"], 4)
        label = f"OC {s['time_s']:.2f}s"
    text(out, label, 14, 14, 3)
    text(out, f"UE {s['opening_deg']:.2f}", 14, 44, 2)
    tiles.append(out)
    meas.append(rec)

# the pixel spans must follow the opening: monotone over the fold angles, span - opening within the ribs' width
fold = [m for m in meas if "expected_opening_deg" in m]
extra = [m["ring_span_deg"] - m["expected_opening_deg"] for m in fold]
mono = all(b["ring_span_deg"] > a["ring_span_deg"] for a, b in zip(fold, fold[1:]))
ok = mono and all(0.0 <= e <= 8.0 for e in extra)

cols = 5
rows = math.ceil(len(tiles) / cols)
gap = 8
sheet = np.full((rows * px + (rows + 1) * gap, cols * px + (cols + 1) * gap, 4), 0.12, np.float32)
sheet[..., 3] = 1.0
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    y0, x0 = gap + r * (px + gap), gap + c * (px + gap)
    sheet[y0:y0 + px, x0:x0 + px] = t
h, w = sheet.shape[:2]
img = bpy.data.images.new("ue_sheet", w, h, alpha=True)
img.pixels[:] = sheet[::-1].ravel()
img.filepath_raw = OUT_PNG
img.file_format = "PNG"
img.save()
json.dump({"shots": meas, "span_minus_opening_deg": extra, "monotone": mono, "pixel_gate": ok,
           "sheet": OUT_PNG, "note": "span measured between 13 and 18.5 cm from the rivet; it includes the guards' "
                                     "own width, so it exceeds the axis-to-axis opening by a few degrees"},
          open(OUT_JSON, "w", encoding="utf-8"), indent=1)
print("UE_SHEET", ok, OUT_PNG)
