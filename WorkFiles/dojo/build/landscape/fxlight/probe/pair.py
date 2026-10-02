"""pair.py <dir> <setA> <setB> <cam> [<cam>...] -> <dir>/pair_<setA>_<setB>.jpg (rows: cams; left A, right B)"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
d = Path(sys.argv[1]); a, b = sys.argv[2], sys.argv[3]; cams = sys.argv[4:]
rows = []
for c in cams:
    ims = [Image.open(d / f"{s}__{c}.png").convert("RGB") for s in (a, b)]
    h = 540
    ims = [im.resize((int(im.size[0] * h / im.size[1]), h)) for im in ims]
    row = Image.new("RGB", (ims[0].size[0] + ims[1].size[0] + 8, h + 22), (15, 15, 15))
    row.paste(ims[0], (0, 22)); row.paste(ims[1], (ims[0].size[0] + 8, 22))
    ImageDraw.Draw(row).text((6, 5), f"{c}: {a} | {b}", fill=(240, 240, 240))
    rows.append(row)
W = max(r.size[0] for r in rows)
s = Image.new("RGB", (W, sum(r.size[1] for r in rows)), (15, 15, 15))
y = 0
for r in rows:
    s.paste(r, (0, y)); y += r.size[1]
out = d / f"pair_{a}_{b}_{cams[0]}.jpg"
s.save(out, quality=88)
print(out)
