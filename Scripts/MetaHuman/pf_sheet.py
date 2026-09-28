"""pf_sheet.py -- contact sheets from pf_female.py captures (plain Python + Pillow).

usage (module): sheet(out_path, [(label, image_path), ...], cols, crop=(x0, y0, x1, y1) or None, scale=0.5, title="")
usage (cli):    py pf_sheet.py <out.png> <cols> <scale> <crop x0,y0,x1,y1|none> <glob-or-file> [...]
"""
import glob
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def sheet(out, items, cols=4, crop=None, scale=0.5, title=""):
    tiles = []
    for label, p in items:
        if not Path(p).exists():
            im = Image.new("RGB", (400, 400), (60, 0, 0))
        else:
            im = Image.open(p).convert("RGB")
            if crop:
                im = im.crop(crop)
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
        tiles.append((label, im))
    tw = max(t[1].width for t in tiles)
    th = max(t[1].height for t in tiles) + 22
    rows = (len(tiles) + cols - 1) // cols
    top = 30 if title else 0
    S = Image.new("RGB", (cols * tw, rows * th + top), (24, 24, 24))
    d = ImageDraw.Draw(S)
    if title:
        d.text((8, 8), title, fill=(240, 240, 240))
    for i, (label, im) in enumerate(tiles):
        x, y = (i % cols) * tw, top + (i // cols) * th
        S.paste(im, (x, y + 22))
        d.text((x + 6, y + 5), label, fill=(255, 230, 120))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    S.save(out)
    return out


if __name__ == "__main__":
    out, cols, scale, crop = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    crop = None if crop == "none" else tuple(int(v) for v in crop.split(","))
    files = []
    for g in sys.argv[5:]:
        files += sorted(glob.glob(g)) or [g]
    sheet(out, [(Path(f).stem, f) for f in files], cols, crop, scale)
    print(out, len(files))
