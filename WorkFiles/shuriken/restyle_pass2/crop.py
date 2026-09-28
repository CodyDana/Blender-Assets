"""Crop regions of images side by side (OpenImageIO): <python> crop.py out.png x0 y0 w h scale img1 [img2 ...]"""
import sys
from OpenImageIO import ImageBuf, ImageBufAlgo, ImageSpec, ROI
import OpenImageIO as oiio
out, x0, y0, w, h, scale = sys.argv[1], *map(int, sys.argv[2:6]), float(sys.argv[6])
paths = sys.argv[7:]
W, H = int(w * scale), int(h * scale)
sheet = ImageBuf(ImageSpec(W * len(paths) + 4 * (len(paths) - 1), H, 3, oiio.FLOAT))
for k, p in enumerate(paths):
    src = ImageBufAlgo.channels(ImageBuf(p), (0, 1, 2))
    cut = ImageBufAlgo.cut(src, ROI(x0, x0 + w, y0, y0 + h))
    dst = ImageBuf(ImageSpec(W, H, 3, oiio.FLOAT))
    ImageBufAlgo.resize(dst, cut, filtername="box" if scale < 1 else "triangle")
    ImageBufAlgo.paste(sheet, k * (W + 4), 0, 0, 0, dst)
sheet.write(out, "uint8")
print("wrote", out)
