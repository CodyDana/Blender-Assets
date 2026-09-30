"""contact sheet: py -3 contact.py <dir> <out> [cams...] (half size, 2 columns)"""
import sys
from pathlib import Path
from PIL import Image
d = Path(sys.argv[1]); cams = sys.argv[3:] or sorted(p.stem for p in d.glob("C*.png"))
ims = [Image.open(d / f"{c}.png").convert("RGB") for c in cams]
w = 960
ims = [i.resize((w, int(i.height * w / i.width))) for i in ims]
rows = [ims[k:k + 2] for k in range(0, len(ims), 2)]
H = sum(max(i.height for i in r) for r in rows)
out = Image.new("RGB", (2 * w, H), (0, 0, 0)); y = 0
for r in rows:
    for k, i in enumerate(r):
        out.paste(i, (k * w, y))
    y += max(i.height for i in r)
out.save(sys.argv[2])
