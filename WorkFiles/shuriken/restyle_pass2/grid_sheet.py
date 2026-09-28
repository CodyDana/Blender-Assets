"""Labelled image grid (OpenImageIO, bundled with Blender 5.2): comparison sheets, headless.

    blender -b --factory-startup --python grid_sheet.py -- --out sheet.png --cols 2 --cell-w 960 \
        [--title "text"] "LABEL::path.png" "LABEL::path.png" ...

Every image is resized to --cell-w wide (aspect kept; the pack's frames are all 16:9), laid out
row by row, and labelled top-left on a dark box (Arial).  An optional title band runs across the top.
"""
import sys

import OpenImageIO as oiio
from OpenImageIO import ImageBuf, ImageBufAlgo, ImageSpec, ROI

FONT = "C:/Windows/Fonts/arial.ttf"
argv = sys.argv[sys.argv.index("--") + 1:]


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


out = arg("--out")
cols = int(arg("--cols", "2"))
cell_w = int(arg("--cell-w", "960"))
title = arg("--title")
gap = 6
skip = {"--out", "--cols", "--cell-w", "--title"}
items, i = [], 0
while i < len(argv):
    if argv[i] in skip:
        i += 2
        continue
    label, path = argv[i].split("::", 1)
    items.append((label, path))
    i += 1

bufs = []
for label, path in items:
    src = ImageBuf(path)
    spec = src.spec()
    h = round(spec.height * cell_w / spec.width)
    dst = ImageBuf(ImageSpec(cell_w, h, 3, oiio.FLOAT))
    ImageBufAlgo.resize(dst, ImageBufAlgo.channels(src, (0, 1, 2)))
    size = max(16, cell_w // 34)
    text_w = int(0.62 * size * len(label)) + 16
    ImageBufAlgo.fill(dst, (0.08, 0.08, 0.09), ROI(6, 6 + text_w, 6, 6 + size + 14))
    ImageBufAlgo.render_text(dst, 14, 6 + size + 4, label, size, FONT, (0.95, 0.95, 0.93))
    bufs.append(dst)

cell_h = max(b.spec().height for b in bufs)
rows = (len(bufs) + cols - 1) // cols
title_h = 56 if title else 0
W = cols * cell_w + (cols + 1) * gap
H = title_h + rows * cell_h + (rows + 1) * gap
sheet = ImageBuf(ImageSpec(W, H, 3, oiio.FLOAT))
ImageBufAlgo.fill(sheet, (0.12, 0.12, 0.13))
if title:
    ImageBufAlgo.render_text(sheet, gap + 8, 40, title, 30, FONT, (0.95, 0.95, 0.93))
for k, buf in enumerate(bufs):
    r, c = divmod(k, cols)
    x = gap + c * (cell_w + gap)
    y = title_h + gap + r * (cell_h + gap)
    ImageBufAlgo.paste(sheet, x, y, 0, 0, buf)
sheet.write(out, "uint8")
print("wrote", out, W, H)
