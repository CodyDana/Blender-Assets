import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
rgb = rio.load_rgb(IMG)
L = rio.lum(rgb)
Lb = rio.blur(L, 0.8)
cx, cy = 630.7, 527.0   # method A crisp centre
for a in (35, 215, 0, 90, 125, 305, 270):
    th = np.radians(a)
    rr = np.arange(118, 152, 1.0)
    v = rio.sample(Lb, cx + np.cos(th) * rr, cy + np.sin(th) * rr)
    print("ang %4d" % a, " ".join("%.2f" % x for x in v))
print("r         ", " ".join("%4.0f" % x for x in np.arange(118, 152, 1.0)))
# straight horizontal scanline through the hole centre row, raw values
row = int(round(cy))
print("row", row, "x 480..520:", " ".join("%.2f" % x for x in L[row, 480:520]))
print("row", row, "x 745..785:", " ".join("%.2f" % x for x in L[row, 745:785]))
