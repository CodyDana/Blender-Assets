"""r20 look: neutral-light floor swatch sheet: reference 2 floor crops (lit / shade) | r19 | r20 (albedo + studio)."""
import sys, json
from pathlib import Path
from PIL import Image, ImageDraw
import colorstats as C
H = Path(__file__).resolve().parent
tags = sys.argv[1:] or ["old_r19", "new_A"]
ref = Image.open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png").convert("RGB")
crops = [("reference 2: sunlit + shaded boards", ref.crop((300, 560, 700, 810)).resize((400, 250))),
         ("reference 2: shaded boards (sheen)", ref.crop((940, 720, 1240, 900)).resize((400, 250)))]
cols = []
for t in tags:
    a = Image.open(H / "swatch" / f"{t}_albedo.png").convert("RGB").resize((250, 250))
    s = Image.open(H / "swatch" / f"{t}_studio.png").convert("RGB").resize((400, 250))
    st = C.region(str(H / "swatch" / f"{t}_albedo.png"), (16, 16, 496, 496))
    cols.append((t, a, s, st))
W = 20 + 400 + 20 + len(cols) * (250 + 400 + 30)
out = Image.new("RGB", (W, 600), (24, 24, 24))
d = ImageDraw.Draw(out)
y = 30
for lab, im in crops:
    out.paste(im, (20, y)); d.text((22, y - 16), lab, fill=(230, 230, 230)); y += 280
x = 440
for t, a, s, st in cols:
    out.paste(a, (x, 30)); out.paste(s, (x + 255, 30))
    d.text((x, 14), f"{t}: albedo (neutral white, no spec) | studio white key", fill=(230, 230, 230))
    r, g, b = [round(v * 255) for v in st["mean_srgb"]]
    h, sat, v = st["hsv"]
    d.text((x, 290), f"albedo sRGB ({r}, {g}, {b})  HSV {h:.0f} deg / {sat:.2f} / {v:.2f}", fill=(230, 230, 230))
    d.rectangle((x, 310, x + 120, 400), fill=(r, g, b))
    x += 680
out.save(H / "compare" / "floor_swatch_neutral.png")
print("saved")
