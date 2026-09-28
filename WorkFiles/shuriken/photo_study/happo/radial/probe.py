"""Print colour profiles along short line segments. args: x0 y0 x1 y1 [...]"""
import sys, os
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
rgb = np.load(os.path.join(OUT, "rgb.npy"))
argv = sys.argv[sys.argv.index("--") + 1:]
vals = list(map(float, argv))
for i in range(0, len(vals), 4):
    x0, y0, x1, y1 = vals[i:i + 4]
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    print("profile (%g,%g)->(%g,%g)" % (x0, y0, x1, y1))
    for t in np.linspace(0, 1, n):
        x = int(round(x0 + t * (x1 - x0))); y = int(round(y0 + t * (y1 - y0)))
        r, g, b = rgb[y, x]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        print("  %4d %4d  rgb %.3f %.3f %.3f  lum %.3f  (r-b) %+.3f" % (x, y, r, g, b, lum, r - b))
