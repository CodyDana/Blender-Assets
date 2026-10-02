"""contact sheet: sheet.py <dir> <out.jpg> cam1 cam2 ... (each scaled to 960 wide, 2 columns)"""
import sys
from PIL import Image, ImageDraw
d, out, cams = sys.argv[1], sys.argv[2], sys.argv[3:]
ims = []
for c in cams:
    im = Image.open(f"{d}/{c}.png").convert("RGB")
    w = 960
    im = im.resize((w, int(im.height * w / im.width)))
    ImageDraw.Draw(im).text((8, 8), c, fill=(255, 255, 0))
    ims.append(im)
rows = [ims[i:i + 2] for i in range(0, len(ims), 2)]
H = sum(max(i.height for i in r) for r in rows)
S = Image.new("RGB", (1930, H), (20, 20, 20))
y = 0
for r in rows:
    for k, im in enumerate(r):
        S.paste(im, (k * 970, y))
    y += max(i.height for i in r)
S.save(out, quality=85)
