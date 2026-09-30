"""Scratch helper: a capture with a labelled 100 px grid (for picking measurement boxes)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
src, out = Path(sys.argv[1]), Path(sys.argv[2])
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)
for x in range(0, im.width, 100):
    d.line((x, 0, x, im.height), fill=(0, 255, 0) if x % 500 else (255, 0, 255), width=1)
    d.text((x + 2, 2), str(x), fill=(0, 255, 0))
for y in range(0, im.height, 100):
    d.line((0, y, im.width, y), fill=(0, 255, 0) if y % 500 else (255, 0, 255), width=1)
    d.text((2, y + 2), str(y), fill=(0, 255, 0))
im.save(out)
