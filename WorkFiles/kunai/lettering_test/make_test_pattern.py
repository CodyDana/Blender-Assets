"""A NEUTRAL placement / orientation test pattern for T_Kunai_Lettering (NOT shipped; the shipped mask is blank).

1536 x 256, 8-bit greyscale, white = ink.  A frame 6 px in from the edge, a 128 px grid, "RING END" at the left (U = 0),
"TIP" and an arrow at the right (U = 1), "+Y" and an arrow at the top edge (the band's +Y side), "ABC 123" in the middle,
corner tags TL / TR / BL / BR.  Drawn upright as any image editor shows it (row 0 at the top).

    py -3 make_test_pattern.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1536, 256
HERE = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/arialbd.ttf"

img = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(img)
for x in range(0, W, 128):
    d.line([(x, 0), (x, H)], fill=70, width=2)
for y in range(0, H, 128):
    d.line([(0, y), (W, y)], fill=70, width=2)
d.rectangle([6, 6, W - 7, H - 7], outline=255, width=8)
big = ImageFont.truetype(FONT, 120)
mid = ImageFont.truetype(FONT, 56)
small = ImageFont.truetype(FONT, 34)
d.text((W / 2, H / 2 + 6), "ABC 123", font=big, fill=255, anchor="mm")
d.text((40, H / 2), "RING END", font=mid, fill=255, anchor="lm")
d.text((W - 360, H / 2), "TIP", font=mid, fill=255, anchor="rm")
d.polygon([(W - 200, H / 2 - 40), (W - 110, H / 2), (W - 200, H / 2 + 40)], fill=255)
d.line([(W - 335, H / 2), (W - 200, H / 2)], fill=255, width=16)
d.polygon([(W / 2 + 380, 22), (W / 2 + 350, 62), (W / 2 + 410, 62)], fill=255)
d.text((W / 2 + 430, 42), "+Y", font=small, fill=255, anchor="lm")
for tag, xy, anchor in (("TL", (20, 18), "lt"), ("TR", (W - 20, 18), "rt"), ("BL", (20, H - 18), "lb"),
                        ("BR", (W - 20, H - 18), "rb")):
    d.text(xy, tag, font=small, fill=255, anchor=anchor)
out = HERE / "T_Kunai_Lettering_TEST.png"
img.save(out)
print("TEST_PATTERN", out, img.size, img.mode)
