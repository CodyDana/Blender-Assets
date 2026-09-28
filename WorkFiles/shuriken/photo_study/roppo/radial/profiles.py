"""Print lum/chroma profiles along lines. args: photo then specs x0:y0:x1:y1 (top-origin)."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
rgb = imgio.load_rgb(argv[0])
for spec in argv[1:]:
    x0, y0, x1, y1 = [float(v) for v in spec.split(":")]
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    print("=== profile", spec)
    for i in range(n):
        t = i / (n - 1)
        x = int(round(x0 + t * (x1 - x0))); y = int(round(y0 + t * (y1 - y0)))
        p = rgb[y, x]
        lum = p.mean(); chroma = p.max() - p.min()
        print(f"{x:5d} {y:5d} lum {lum:.3f} chr {chroma:.3f} rgb {p[0]:.2f} {p[1]:.2f} {p[2]:.2f}")
