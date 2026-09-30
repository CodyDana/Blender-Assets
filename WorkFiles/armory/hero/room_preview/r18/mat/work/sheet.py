"""sheet.py OUT BOX SCALE label=img ...: stacked crops (reference first)."""
import sys
from PIL import Image, ImageDraw
out, box, sc = sys.argv[1], tuple(int(v) for v in sys.argv[2].split(',')), int(sys.argv[3])
tiles = []
for a in sys.argv[4:]:
    lab, p = a.split('=', 1)
    c = Image.open(p).convert('RGB').crop(box)
    c = c.resize((c.width * sc, c.height * sc), Image.LANCZOS)
    d = ImageDraw.Draw(c); d.rectangle((0, 0, 8 + 7 * len(lab), 16), fill=(0, 0, 0)); d.text((4, 2), lab, fill=(255, 255, 255))
    tiles.append(c)
s = Image.new('RGB', (tiles[0].width, sum(t.height for t in tiles)))
y = 0
for t in tiles:
    s.paste(t, (0, y)); y += t.height
s.save(out)
