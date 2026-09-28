"""Print colour profiles along short line segments. usage: -- x0 y0 x1 y1 [x0 y0 x1 y1 ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

a = [float(v) for v in sys.argv[sys.argv.index('--') + 1:]]
rgb, info = C.load_rgb(C.IMG)
# light 5x5 box blur to suppress texture
k = 2
S = np.zeros((rgb.shape[0] + 2 * k + 1, rgb.shape[1] + 2 * k + 1, 3), np.float64)
P = np.pad(rgb, ((k, k), (k, k), (0, 0)), mode='edge')
S[1:, 1:] = P.cumsum(0).cumsum(1)
n = 2 * k + 1
blur = ((S[n:, n:] - S[:-n, n:] - S[n:, :-n] + S[:-n, :-n]) / n / n).astype(np.float32)
for i in range(0, len(a), 4):
    x0, y0, x1, y1 = a[i:i + 4]
    L = int(np.hypot(x1 - x0, y1 - y0))
    t = np.linspace(0, 1, L + 1)
    xs = x0 + (x1 - x0) * t; ys = y0 + (y1 - y0) * t
    v = C.bilinear(blur, xs, ys)
    print("PROFILE", x0, y0, "->", x1, y1)
    for j in range(0, L + 1, 2):
        r, g, b = v[j]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        print("%4d (%7.1f,%7.1f) rgb %.3f %.3f %.3f lum %.3f  r-b %.3f  g-b %.3f" % (j, xs[j], ys[j], r, g, b, lum, r - b, g - b))
