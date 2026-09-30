import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert("RGB").resize((1448, 1086))
d = ImageDraw.Draw(im)
for x in range(0, 1448, 50):
    d.line([(x, 0), (x, 1086)], fill=(0, 255, 0) if x % 200 == 0 else (0, 90, 0), width=1)
    if x % 100 == 0: d.text((x + 2, 2), str(x), fill=(255, 255, 0))
for y in range(0, 1086, 50):
    d.line([(0, y), (1448, y)], fill=(0, 255, 0) if y % 200 == 0 else (0, 90, 0), width=1)
    if y % 100 == 0: d.text((2, y + 2), str(y), fill=(255, 255, 0))
im.save(sys.argv[2])
