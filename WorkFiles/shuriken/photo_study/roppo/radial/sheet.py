"""Contact sheet of crops. args: <img> <out.png> <cols> <scale> <half> x:y[:label] ...
Each cell = square crop of side 2*half centred at x,y, scaled by nearest-neighbour."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
src, out, cols, s, half = argv[0], argv[1], int(argv[2]), int(argv[3]), int(argv[4])
rgb = imgio.load_rgb(src)
H, W, _ = rgb.shape
cells = []
for spec in argv[5:]:
    x, y = [int(round(float(v))) for v in spec.split(":")[:2]]
    c = np.ones((2 * half, 2 * half, 3), np.float32)
    x0, y0 = x - half, y - half
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(W, x0 + 2 * half), min(H, y0 + 2 * half)
    c[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = rgb[sy0:sy1, sx0:sx1]
    c = np.repeat(np.repeat(c, s, 0), s, 1)
    c[:2, :] = 0; c[:, :2] = 0
    cells.append(c)
rows = (len(cells) + cols - 1) // cols
cs = 2 * half * s
sheet = np.ones((rows * cs, cols * cs, 3), np.float32)
for i, c in enumerate(cells):
    r, q = divmod(i, cols)
    sheet[r * cs:(r + 1) * cs, q * cs:(q + 1) * cs] = c
imgio.save_rgb(out, sheet)
print("sheet", sheet.shape)
