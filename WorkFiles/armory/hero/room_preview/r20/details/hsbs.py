# hsbs.py <out> <scale> <label|img>... : full frames side by side (labels)
import sys
from PIL import Image, ImageDraw
out, k = sys.argv[1], float(sys.argv[2])
ims = []
for a in sys.argv[3:]:
    lab, p = a.split('|')
    im = Image.open(p).convert('RGB'); im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    d = ImageDraw.Draw(im); d.rectangle([0, 0, 8 * len(lab) + 8, 18], fill=(0, 0, 0)); d.text((4, 3), lab, fill=(255, 255, 0))
    ims.append(im)
S = Image.new('RGB', (sum(i.width for i in ims), max(i.height for i in ims)))
x = 0
for i in ims:
    S.paste(i, (x, 0)); x += i.width
S.save(out); print(out, S.size)
