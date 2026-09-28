"""pd_sheet.py -- labelled contact sheets from pd_diagnose captures (plain Python + Pillow, runs outside Unreal).

usage: py pd_sheet.py <out.png> <cols> <crop x0,y0,x1,y1 | full> <scale> <img1> [<img2> ...]
Image arguments may be 'label=path'; otherwise the file stem is the label.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main(argv):
    out, cols, crop, scale = argv[0], int(argv[1]), argv[2], float(argv[3])
    items = []
    for a in argv[4:]:
        if "=" in a and not Path(a).exists():
            label, p = a.split("=", 1)
        else:
            label, p = Path(a).stem, a
        items.append((label, p))
    box = None if crop == "full" else tuple(int(v) for v in crop.split(","))
    tiles = []
    for label, p in items:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:  # noqa: BLE001
            im = Image.new("RGB", (400, 400), (60, 0, 0))
            label += " (missing)"
        if box:
            im = im.crop(box)
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
        tiles.append((label, im))
    w = max(t.width for _, t in tiles)
    h = max(t.height for _, t in tiles)
    lab = 22
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + lab)), (25, 25, 25))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    for i, (label, t) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + lab)
        sheet.paste(t, (x, y + lab))
        draw.text((x + 4, y + 2), label, fill=(255, 255, 160), font=font)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1:])
