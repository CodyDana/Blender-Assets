"""r20 final2 (combined, judge fixes; copied from r20/final/compare.py): side-by-sides reference 2 | night_r19 (live) |
r20 final2 for C1 (1448 x 1086 and 1600 x 900; night and golden), night_r19 | r20 final2 for CX / CW / C10 / C3 / C4 / C5,
the neutral-light floor swatch sheet (r19 | r20 final | r20 final2), and whole-frame mean display luminance. py -3 compare.py"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory")
REF = ROOT / "reference" / "armory3_reference2.png"
R19 = ROOT / "build" / "renders" / "night_r19"
LOOK = ROOT / "hero" / "room_preview" / "r20" / "look"
FINAL = ROOT / "hero" / "room_preview" / "r20" / "final"
OUT = HERE / "compare"
OUT.mkdir(exist_ok=True)
CAMS = ("C1_EntryReveal", "CX_FromPlatform", "CW_WestAisle", "C10_Hero", "C3_Case3", "C4_ShurikenTray", "C5_CloakCase")


def lum(p, box=None):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    if box:
        a = a[box[1]:box[3], box[0]:box[2]]
    return round(float((a @ np.array([0.2126, 0.7152, 0.0722])).mean()), 3)


def side(paths, labels, out):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h), Image.LANCZOS) for i in ims]
    im = Image.new("RGB", (sum(i.width for i in ims) + 16 * (len(ims) - 1), h + 26), (20, 20, 20))
    d = ImageDraw.Draw(im)
    x = 0
    for i, lab, p in zip(ims, labels, paths):
        d.text((x + 6, 6), f"{lab}  (mean L {lum(p)})", fill=(230, 230, 230))
        im.paste(i, (x, 26))
        x += i.width + 16
    im.save(out)
    print("wrote", out.name, im.size)


for P in ("night", "golden"):
    side([REF, R19 / "ref_aspect" / "C1_EntryReveal_night.png", HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r19 (live, night)", f"r20 final2 ({P})"], OUT / f"C1_ref_vs_night_r19_vs_r20final2_{P}.png")
    side([REF, R19 / "C1_EntryReveal_night.png", HERE / f"C1_EntryReveal_{P}.png"],
         ["reference 2", "night_r19 (live, night)", f"r20 final2 ({P})"],
         OUT / f"C1_ref_vs_night_r19_vs_r20final2_{P}_1600x900.png")
for cam in CAMS[1:]:
    side([R19 / f"{cam}_night.png", HERE / f"{cam}_night.png"], ["night_r19 (live, night)", "r20 final2 (night)"],
         OUT / f"{cam}_night_r19_vs_r20final2.png")

# neutral-light floor swatch: reference 2 floor crops | r19 floor (look/swatch/old_r19, M_AK_Plank as live: old BC x 1.8)
# | r20 final floor (the combined build's M_AK_Plank as built, no overrides)
ref = Image.open(REF).convert("RGB")
crops = [("reference 2: sunlit + shaded boards", ref.crop((300, 560, 700, 810)).resize((400, 250))),
         ("reference 2: shaded boards (sheen)", ref.crop((940, 720, 1240, 900)).resize((400, 250)))]
cols = [("r19 floor (live)", LOOK / "swatch" / "old_r19_albedo.png", LOOK / "swatch" / "old_r19_studio.png"),
        ("r20 final floor (#42291D)", FINAL / "swatch" / "r20final_albedo.png", FINAL / "swatch" / "r20final_studio.png"),
        ("r20 final2 floor (#3E2D25)", HERE / "swatch" / "r20final2_albedo.png", HERE / "swatch" / "r20final2_studio.png")]


def lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


W = 20 + 400 + 20 + len(cols) * (250 + 400 + 30)
sheet = Image.new("RGB", (W, 600), (24, 24, 24))
d = ImageDraw.Draw(sheet)
y = 30
for lab, im in crops:
    sheet.paste(im, (20, y)); d.text((22, y - 16), lab, fill=(230, 230, 230)); y += 280
x = 440
swatch_stats = {}
for lab, ap, sp in cols:
    a = np.asarray(Image.open(ap).convert("RGB")).astype(float)[16:496, 16:496] / 255
    m = srgb(lin(a).reshape(-1, 3).mean(0))
    r, g, b = [int(round(float(v) * 255)) for v in m]
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(*[float(t) for t in m])
    swatch_stats[lab] = {"albedo_srgb255": [r, g, b], "hsv": [round(h * 360, 1), round(s, 3), round(v, 3)]}
    sheet.paste(Image.open(ap).convert("RGB").resize((250, 250)), (x, 30))
    sheet.paste(Image.open(sp).convert("RGB").resize((400, 250)), (x + 255, 30))
    d.text((x, 14), f"{lab}: albedo (neutral white, no spec) | studio white key", fill=(230, 230, 230))
    d.text((x, 290), f"albedo sRGB ({r}, {g}, {b})  HSV {h * 360:.0f} deg / {s:.2f} / {v:.2f}", fill=(230, 230, 230))
    d.rectangle((x, 310, x + 120, 400), fill=(r, g, b))
    x += 680
sheet.save(OUT / "floor_swatch_neutral_r19_vs_r20final_vs_r20final2.png")
print("wrote floor_swatch_neutral_r19_vs_r20final2.png")

stats = {"reference2": lum(REF), "night_r19/ref_aspect/C1": lum(R19 / "ref_aspect" / "C1_EntryReveal_night.png")}
for cam in CAMS:
    stats[f"night_r19/{cam}"] = lum(R19 / f"{cam}_night.png")
for P in ("night", "golden"):
    stats[f"r20final2/ref_aspect/C1_{P}"] = lum(HERE / "ref_aspect" / f"C1_EntryReveal_{P}.png")
    for cam in CAMS:
        stats[f"r20final2/{cam}_{P}"] = lum(HERE / f"{cam}_{P}.png")
# exterior through the entrance in CX (the door opening box used by r20 look)
stats["CX door opening night_r19 / r20final2"] = [lum(R19 / "CX_FromPlatform_night.png", (700, 290, 900, 460)),
                                                 lum(HERE / "CX_FromPlatform_night.png", (700, 290, 900, 460))]
stats["floor_swatch"] = swatch_stats
(OUT / "luminance.json").write_text(json.dumps(stats, indent=1))
print(json.dumps(stats, indent=1))

# r20 final2: floor colour in the C1 ref-aspect frame (open floor boxes, same framing), r20 final against r20 final2,
# night and golden: mean sRGB of the box (linear mean) + HSV, and the 90th-percentile per-pixel saturation
import colorsys
FLOOR_BOXES = {"floor_right_of_case1_sun_stripes": (930, 640, 1100, 780), "floor_in_front_of_case1": (560, 830, 1000, 895)}


def floor_stats(p, box):
    a = np.asarray(Image.open(p).convert("RGB")).astype(float)[box[1]:box[3], box[0]:box[2]] / 255
    m = srgb(lin(a).reshape(-1, 3).mean(0))
    h, s, v = colorsys.rgb_to_hsv(*[float(t) for t in m])
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return {"srgb255": [int(round(float(t) * 255)) for t in m], "hsv": [round(h * 360, 1), round(s, 3), round(v, 3)],
            "sat_p90": round(float(np.percentile(sat, 90)), 3)}


fl = {}
for P in ("night", "golden"):
    for tag, d in (("r20final", FINAL), ("r20final2", HERE)):
        for bn, box in FLOOR_BOXES.items():
            fl[f"{tag}/{P}/{bn}"] = floor_stats(d / "ref_aspect" / f"C1_EntryReveal_{P}.png", box)
for bn, box in FLOOR_BOXES.items():
    fl[f"reference2/{bn}"] = floor_stats(REF, box)
stats["C1_floor_boxes"] = fl
(OUT / "luminance.json").write_text(json.dumps(stats, indent=1))
print(json.dumps(fl, indent=1))
