import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
a = [int(v) for v in sys.argv[sys.argv.index('--') + 1:]]
rgb, info = C.load_rgb(C.IMG)
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
h, w = lum.shape
for i in range(0, len(a), 3):
    x, y0, y1 = a[i:i + 3]
    p = lum[y0:y1, x - 3:x + 4].mean(1)
    print("COL x=%d y %d..%d:" % (x, y0, y1), " ".join("%d:%.2f" % (y0 + j, v) for j, v in enumerate(p)))
