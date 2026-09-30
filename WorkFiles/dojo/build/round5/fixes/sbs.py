"""Side-by-side sheets: py -3 sbs.py <out.png> <img1> [<img2> ...] (labels = parent folder / file stem)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

out, ims = sys.argv[1], sys.argv[2:]
H = 540
tiles = []
for p in ims:
    im = Image.open(p).convert("RGB")
    w = int(im.width * H / im.height)
    im = im.resize((w, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    lab = f"{Path(p).parent.name}/{Path(p).stem}"
    d.rectangle((0, 0, 8 * len(lab) + 10, 18), fill=(0, 0, 0))
    d.text((5, 3), lab, fill=(255, 255, 255))
    tiles.append(im)
W = sum(t.width for t in tiles) + 6 * (len(tiles) - 1)
sheet = Image.new("RGB", (W, H), (30, 30, 30))
x = 0
for t in tiles:
    sheet.paste(t, (x, 0))
    x += t.width + 6
sheet.save(out)
print(out, sheet.size)
