import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rc_common import load_rgb, lum

L = lum(load_rgb())
H, W = L.shape
print("\n=== PLATE LEFT EDGE: row profiles (x increasing rightward) ===")
for y in (200, 350, 480, 620, 780):
    row = L[y, :]
    xs = np.where(row[:400] < 0.55)[0]
    x0 = xs[0]
    print(f"\n y={y}  first L<0.55 at x={x0}")
    lo, hi = x0 - 16, x0 + 32
    print("   x :", " ".join(f"{xx:5d}" for xx in range(lo, hi)))
    print("   L :", " ".join(f"{row[xx]:5.3f}" for xx in range(lo, hi)))

print("\n=== PLATE RIGHT EDGE: row profiles ===")
for y in (200, 350, 480, 620, 780):
    row = L[y, :]
    xs = np.where(row[500:] < 0.55)[0]
    x0 = 500 + xs[-1]
    print(f"\n y={y}  last L<0.55 at x={x0}")
    lo, hi = x0 - 32, x0 + 24
    print("   x :", " ".join(f"{xx:5d}" for xx in range(lo, hi)))
    print("   L :", " ".join(f"{row[xx]:5.3f}" for xx in range(lo, hi)))
