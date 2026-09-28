"""Print raw luminance profiles across the contested edges so the shadow
model can be arbitrated by eye, independent of either agent's edge rule."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rc_common import load_rgb, lum

rgb = load_rgb()
L = lum(rgb)
H, W = L.shape
print("image", W, "x", H)
np.set_printoptions(precision=3, suppress=True, linewidth=220)

# ---- plate top edge: vertical columns through the top side --------------
print("\n=== PLATE TOP EDGE: column profiles (y increasing downward) ===")
for x in (180, 300, 420, 505, 620, 740, 840):
    # find approximate top edge: first row from y=0 where L < 0.55
    col = L[:, x]
    y0 = int(np.argmax(col[:400] < 0.55))
    print(f"\n x={x}  first L<0.55 at y={y0}")
    lo, hi = y0 - 14, y0 + 34
    print("   y :", " ".join(f"{yy:5d}" for yy in range(lo, hi)))
    print("   L :", " ".join(f"{col[yy]:5.3f}" for yy in range(lo, hi)))

# ---- plate bottom edge (crisp, lit) -------------------------------------
print("\n=== PLATE BOTTOM EDGE: column profiles ===")
for x in (300, 505, 700):
    col = L[:, x]
    ys = np.where(col[500:] < 0.55)[0]
    y0 = 500 + ys[-1]
    print(f"\n x={x}  last L<0.55 at y={y0}")
    lo, hi = y0 - 34, y0 + 14
    print("   y :", " ".join(f"{yy:5d}" for yy in range(lo, hi)))
    print("   L :", " ".join(f"{col[yy]:5.3f}" for yy in range(lo, hi)))

# ---- hole: vertical profile through hole centre -------------------------
print("\n=== HOLE: vertical profiles (through the hole) ===")
for x in (430, 470, 505, 545, 585):
    col = L[:, x]
    print(f"\n x={x}")
    print("   top edge region")
    lo, hi = 340, 385
    print("   y :", " ".join(f"{yy:5d}" for yy in range(lo, hi)))
    print("   L :", " ".join(f"{col[yy]:5.3f}" for yy in range(lo, hi)))
    print("   bottom edge region")
    lo, hi = 552, 612
    print("   y :", " ".join(f"{yy:5d}" for yy in range(lo, hi)))
    print("   L :", " ".join(f"{col[yy]:5.3f}" for yy in range(lo, hi)))

print("\n=== HOLE: horizontal profiles ===")
for y in (400, 440, 480, 520, 555):
    row = L[y, :]
    print(f"\n y={y}")
    print("   left edge region")
    lo, hi = 368, 418
    print("   x :", " ".join(f"{xx:5d}" for xx in range(lo, hi)))
    print("   L :", " ".join(f"{row[xx]:5.3f}" for xx in range(lo, hi)))
    print("   right edge region")
    lo, hi = 592, 642
    print("   x :", " ".join(f"{xx:5d}" for xx in range(lo, hi)))
    print("   L :", " ".join(f"{row[xx]:5.3f}" for xx in range(lo, hi)))
