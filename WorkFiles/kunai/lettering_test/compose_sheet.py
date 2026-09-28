"""Compose lettering_test_sheet.png from the four renders of lettering_test_render.py (plain Python + Pillow):
a 2 x 2 grid of half-size shots, TEST mask on top, the SHIPPED blank mask below, +Z view left, 3/4 view right.

    py -3 WorkFiles/kunai/lettering_test/compose_sheet.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1600, 900
CELLS = [("lettering_test_top.png", "TEST mask, from +Z, tip to the right", (0, 0)),
         ("lettering_test_34.png", "TEST mask, 3/4 view", (800, 0)),
         ("lettering_blank_top.png", "SHIPPED blank mask, from +Z", (0, 450)),
         ("lettering_blank_34.png", "SHIPPED blank mask, 3/4 view", (800, 450))]

sheet = Image.new("RGB", (W, H), (20, 20, 20))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
except OSError:
    font = ImageFont.load_default()
for name, label, (x, y) in CELLS:
    im = Image.open(HERE / name).convert("RGBA").resize((800, 450), Image.LANCZOS)
    base = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sheet.paste(Image.alpha_composite(base, im).convert("RGB"), (x, y))
    l, t, r, b = draw.textbbox((x + 8, y + 6), label, font=font)
    draw.rectangle((x, y, r + 72, b + 10), fill=(20, 20, 20))
    draw.text((x + 8, y + 6), label, font=font, fill=(235, 235, 235))
out = HERE / "lettering_test_sheet.png"
sheet.save(out)
print("LETTERING_SHEET", out, sheet.size)
