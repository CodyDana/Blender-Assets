"""glow cores: the brightest 8 % of a box (median of them), saturation, and the clip fraction of the box.
py -3 cores.py <img> x0,y0,x1,y1 ..."""
import sys, colorsys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert("RGB"), float)
for b in sys.argv[2:]:
    x0, y0, x1, y1 = map(int, b.split(","))
    r = a[y0:y1, x0:x1].reshape(-1, 3)
    lum = r @ np.array([0.2126, 0.7152, 0.0722])
    top = r[lum >= np.quantile(lum, 0.92)]
    m = np.median(top, 0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255))
    print(b, "core", tuple(int(x) for x in m), f"h{h*360:.0f} s{s:.2f}", "clip_any", round(float((r.max(1) >= 254).mean()), 4))
