"""Reference | ours sheets and colour statistics for the ground (system Python with PIL + numpy).

Run: py Scripts/dojo/ground/compare_ground.py <renders_dir>
Writes <dir>/SBS_Establish.png (dojo1_reference2 | C_Establish, same camera fit, same 1448 x 1086 frame),
<dir>/SBS_GroundCrop.png (the same pixel box on both: near path, sand, gravel strip and kerb band, 2x) and
<dir>/compare_stats.json (median sRGB of matched regions: sand lit, sand near, gravel strip, path slabs, sky).
The armory's Scripts/armory/side_by_side.py makes the same kind of sheet inside Blender; this one adds the stats.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from PIL import ImageDraw

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "References" / "Dojo" / "dojo1_reference2.png"
d = Path(sys.argv[1])

if "--sheet" in sys.argv:   # compose TEXTURE_SHEET.png from render_texture_sheet.py's tiles
    mats = [("M_DKG_SandRaked", "Raked sand (own)"), ("M_DKG_SandEdge", "Sand edge strip (own)"),
            ("M_DKG_Granite", "Paving granite (own)"), ("M_DKG_GraniteHewn", "Kerb granite, hewn (own)"),
            ("M_DKG_Gravel", "Surround gravel (CC0 scan, graded)"),
            ("M_DKG_GravelCoarse", "Gate-strip gravel (own pebbles, CC0 fines)"),
            ("M_DKG_Soil", "Soil (own)"), ("M_DKG_EdgeTimber", "Edging timber (own)")]
    t = Image.open(d / "sheet_tiles" / f"{mats[0][0]}_flat.png")
    s_, pad, head = t.width, 24, 40
    sheet = Image.new("RGB", (len(mats) * (s_ + pad) + pad, 2 * (s_ + pad) + head + pad), (128, 128, 128))
    dr = ImageDraw.Draw(sheet)
    for i, (m, label) in enumerate(mats):
        x = pad + i * (s_ + pad)
        dr.text((x, 12), label, fill=(20, 20, 20))
        for j, kind in enumerate(("flat", "eye")):
            y = head + j * (s_ + pad)
            sheet.paste(Image.open(d / "sheet_tiles" / f"{m}_{kind}.png").convert("RGB"), (x, y))
            if kind == "flat":   # tile boundary ticks (every 4 m = a third of the swatch), outside the image
                for k in (1, 2):
                    q = round(k * s_ / 3)
                    dr.line([(x + q, y - 8), (x + q, y - 1)], fill=(200, 30, 30), width=2)
                    dr.line([(x - 8, y + q), (x - 1, y + q)], fill=(200, 30, 30), width=2)
    dr.text((pad, sheet.height - 20), "Top row: 3 x 3 tiles (4 m each, red ticks = tile seams), orthographic. "
            "Bottom row: 1.7 m eye height, 35 mm. Neutral sun 40 deg across the rake lines, grey world.",
            fill=(20, 20, 20))
    sheet.save(d / "TEXTURE_SHEET.png")
    print("sheet", d / "TEXTURE_SHEET.png", sheet.size)
    sys.exit(0)
ref = Image.open(REF).convert("RGB")
ours = Image.open(d / "C_Establish.png").convert("RGB").resize(ref.size, Image.LANCZOS)


def sbs(a, b, out, gap=24):
    h = min(a.height, b.height)
    a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
    b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
    s = Image.new("RGB", (a.width + gap + b.width, h), (255, 255, 255))
    s.paste(a, (0, 0))
    s.paste(b, (a.width + gap, 0))
    s.save(out)


sbs(ref, ours, d / "SBS_Establish.png")
box = (430, 640, 1030, 1000)           # near path + both sand halves + gravel strip + kerb band
ca, cb = ref.crop(box), ours.crop(box)
ca = ca.resize((ca.width * 2, ca.height * 2), Image.LANCZOS)
cb = cb.resize((cb.width * 2, cb.height * 2), Image.LANCZOS)
sbs(ca, cb, d / "SBS_GroundCrop.png")
regions = {"sand_mid_right": (850, 1100, 600, 700), "sand_near_left": (300, 600, 780, 880),
           "sand_far": (350, 650, 500, 560), "gravel_near_strip": (820, 1180, 912, 940),
           "path_slabs_mid": (690, 760, 620, 760), "gravel_far_band": (800, 1000, 462, 480), "sky_top": (300, 1100, 20, 90)}
A, B = np.asarray(ref, float), np.asarray(ours, float)
stats = {}
for k, (x0, x1, y0, y1) in regions.items():
    stats[k] = {"ref": np.median(A[y0:y1, x0:x1].reshape(-1, 3), 0).round().astype(int).tolist(),
                "ours": np.median(B[y0:y1, x0:x1].reshape(-1, 3), 0).round().astype(int).tolist()}
lum = lambda a: 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
stats["frame_luma_p10_p50_p90"] = {"ref": np.percentile(lum(A), [10, 50, 90]).round(1).tolist(),
                                   "ours": np.percentile(lum(B), [10, 50, 90]).round(1).tolist()}
(d / "compare_stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
for k, v in stats.items():
    print(k, v)
