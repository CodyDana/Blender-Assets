"""Locate the isolated dark dots on a bar's hero side face and write an enlarged contact sheet of them.

    "<blender python>" dot_locate.py <beauty.png> <mask.png> <out.png> [threshold]
"""
import sys

import numpy as np
import OpenImageIO as oiio
from numpy.lib.stride_tricks import sliding_window_view

W = np.array([0.2126, 0.7152, 0.0722])
beauty, mask_path, out_path = sys.argv[1:4]
thr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.70


def load(p):
    return np.asarray(oiio.ImageBuf(p).get_pixels(oiio.FLOAT))


def erode(m, k):
    out = m.copy()
    for _ in range(k):
        s = out.copy()
        for ax in (0, 1):
            s &= np.roll(out, 1, ax)
            s &= np.roll(out, -1, ax)
        out = s
    return out


px = load(beauty)
m = load(mask_path)
lum = px[..., :3].astype(np.float64) @ W
sel = m[..., 3] > 0.85
side = sel & (m[..., 0] > 0.5) & (m[..., 2] <= 0.5)
core = erode(side, 4)
r = 3
a = np.where(side, lum, np.nan)
pad = np.pad(a, r, constant_values=np.nan)
ys, xs = np.nonzero(core)
v = sliding_window_view(pad, (7, 7))
med = np.nanmedian(v[ys, xs].reshape(len(ys), -1), axis=1)
dark = lum[ys, xs] < med * thr
dy, dx = ys[dark], xs[dark]
print("dark px", len(dy))
# cluster crudely: unique 6 px cells
cells = sorted({(int(y) // 6 * 6, int(x) // 6 * 6) for y, x in zip(dy, dx)})
print("cells", len(cells), cells[:40])
tiles = []
for (y, x) in cells[:24]:
    y0, x0 = max(y - 10, 0), max(x - 10, 0)
    t = px[y0:y0 + 26, x0:x0 + 26, :3]
    if t.shape[:2] != (26, 26):
        continue
    tiles.append(np.repeat(np.repeat(t, 8, 0), 8, 1))
rows = [np.concatenate(tiles[i:i + 6], axis=1) for i in range(0, len(tiles) - len(tiles) % 6, 6)]
sheet = np.concatenate(rows, axis=0) if rows else np.zeros((8, 8, 3))
buf = oiio.ImageBuf(oiio.ImageSpec(sheet.shape[1], sheet.shape[0], 3, oiio.FLOAT))
buf.set_pixels(oiio.ROI(), sheet.astype(np.float32))
buf.write(out_path)
print("sheet", sheet.shape)
