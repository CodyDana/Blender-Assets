"""Montage of magnified crops centred on given points.
usage: -- outname half scale ncols [mask.npy|none] x y x y ...
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[sys.argv.index("--") + 1:]
name, half, s, ncols, maskf = a[0], int(a[1]), int(a[2]), int(a[3]), a[4]
pts = list(map(float, a[5:]))
pts = [(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)]
rgb = np.load(os.path.join(OUT, "rgb.npy"))
H, W = rgb.shape[:2]
pad = np.pad(rgb, ((half, half), (half, half), (0, 0)), constant_values=1.0)
if maskf != "none":
    m = np.load(os.path.join(OUT, maskf))
    e = m & ~L.erode(m, 1)
    rgb2 = rgb.copy()
    rgb2[e] = rgb2[e] * 0.2 + np.array([1, 0, 0]) * 0.8
    pad = np.pad(rgb2, ((half, half), (half, half), (0, 0)), constant_values=1.0)
tiles = []
for (x, y) in pts:
    xi, yi = int(round(x)), int(round(y))
    c = pad[yi:yi + 2 * half, xi:xi + 2 * half].copy()
    c = np.repeat(np.repeat(c, s, 0), s, 1)
    c[:, :2] = [0, 0.6, 0]; c[:2, :] = [0, 0.6, 0]
    # centre cross
    cc = half * s
    c[cc - 1:cc + 1, cc - 6:cc + 6] = [0, 0.8, 1]
    c[cc - 6:cc + 6, cc - 1:cc + 1] = [0, 0.8, 1]
    tiles.append(c)
while len(tiles) % ncols:
    tiles.append(np.ones_like(tiles[0]))
rows = [np.concatenate(tiles[i:i + ncols], 1) for i in range(0, len(tiles), ncols)]
os.makedirs(os.path.join(OUT, "crops"), exist_ok=True)
L.save_png(os.path.join(OUT, "crops", name + ".png"), np.concatenate(rows, 0))
