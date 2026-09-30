"""quick region medians: py -3 m.py <img> x0,y0,x1,y1 ..."""
import sys, colorsys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert("RGB"), float)
for b in sys.argv[2:]:
    x0, y0, x1, y1 = map(int, b.split(","))
    r = a[y0:y1, x0:x1].reshape(-1, 3)
    m = np.median(r, 0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255))
    clip = float((r.max(1) >= 254).mean())
    print(b, tuple(int(x) for x in m), f"h{h*360:.0f} s{s:.2f} v{v:.2f} R/B {m[0]/max(m[2],1):.2f} clip {clip:.3f}")
