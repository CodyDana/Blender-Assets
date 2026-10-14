"""Gridded zoom of a panel crop for reading seams by eye (scratch QA helper).

    py -3 -B gridzoom.py <crop.png> <x0> <y0> <x1> <y1> <scale> <out.png> [grid_step] [mirror]

Coordinates are panel-crop px; grid lines every grid_step px (default 10), labelled with the panel x / y.
"""
import sys

from PIL import Image, ImageDraw, ImageFont


def main():
    src, x0, y0, x1, y1, sc, out = sys.argv[1:8]
    step = int(sys.argv[8]) if len(sys.argv) > 8 else 10
    mirror = len(sys.argv) > 9 and sys.argv[9] == "mirror"
    x0, y0, x1, y1, sc = int(x0), int(y0), int(x1), int(y1), int(sc)
    im = Image.open(src).convert("RGB")
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    c = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.NEAREST)
    d = ImageDraw.Draw(c)
    try:
        f = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        f = ImageFont.load_default()
    for x in range((x0 // step + 1) * step, x1, step):
        X = (x - x0) * sc
        major = x % (step * 5) == 0
        d.line([(X, 0), (X, c.height)], fill=(255, 0, 0) if major else (0, 160, 255), width=1)
        d.text((X + 2, 2), str(x), fill=(255, 255, 0), font=f)
    for y in range((y0 // step + 1) * step, y1, step):
        Y = (y - y0) * sc
        major = y % (step * 5) == 0
        d.line([(0, Y), (c.width, Y)], fill=(255, 0, 0) if major else (0, 160, 255), width=1)
        d.text((2, Y + 2), str(y), fill=(255, 255, 0), font=f)
    c.save(out)


if __name__ == "__main__":
    main()
