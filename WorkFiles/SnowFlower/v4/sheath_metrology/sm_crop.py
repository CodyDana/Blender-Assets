# sm_crop: args key y0 y1 x0 x1 scale name [grid_step]  -> debug/<name>.png with optional pixel grid ticks
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
argv = sys.argv[sys.argv.index("--") + 1:]
key = argv[0]; y0, y1, x0, x1, sc = map(int, argv[1:6]); name = argv[6]
step = int(argv[7]) if len(argv) > 7 else 0
a = load(key)[y0:y1, x0:x1, :3].copy()
if step:
    for y in range(y0, y1):
        if y % step == 0:
            a[y - y0, :6] = (1, 0, 0); a[y - y0, -6:] = (1, 0, 0)
            if y % (step * 5) == 0:
                a[y - y0, :14] = (1, 0, 0)
    for x in range(x0, x1):
        if x % step == 0:
            a[:4, x - x0] = (0, 0, 1)
            if x % (step * 5) == 0:
                a[:10, x - x0] = (0, 0, 1)
print(save_png(a, name, sc))
