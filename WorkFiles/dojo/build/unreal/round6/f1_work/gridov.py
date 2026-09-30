import sys
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]
sc = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
im = Image.open(src).convert('RGB'); d = ImageDraw.Draw(im)
for x in range(0, im.width, 100):
    d.line([(x, 0), (x, im.height)], fill=(0, 255, 255) if x % 500 else (255, 0, 0), width=1); d.text((x + 2, 2), str(x), fill=(255, 255, 0))
for y in range(0, im.height, 100):
    d.line([(0, y), (im.width, y)], fill=(0, 255, 255) if y % 500 else (255, 0, 0), width=1); d.text((2, y + 2), str(y), fill=(255, 255, 0))
im.resize((int(im.width * sc), int(im.height * sc))).save(out)
