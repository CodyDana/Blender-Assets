import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
rgb = rio.load_rgb(IMG)
H, W, _ = rgb.shape

circles = [  # cx, cy, r, colour
    (630.6819, 527.0314, 134.1657, (1, 0, 0)),      # A crisp half
    (631.7723, 525.2504, 132.2548, (0, 0.4, 1)),    # B lit half
    (629.8743, 531.4104, 138.4211, (0, 1, 0)),      # reconciler v2 3/4-rim gradient
]

# zoom the hole box at 3x
x0, x1, y0, y1 = 460, 800, 360, 700
Z = 3
crop = rgb[y0:y1, x0:x1]
big = np.repeat(np.repeat(crop, Z, axis=0), Z, axis=1).copy()
for cx, cy, r, col in circles:
    for a in np.arange(0, 360, 0.05):
        th = np.radians(a)
        px = (cx + np.cos(th) * r - x0) * Z
        py = (cy + np.sin(th) * r - y0) * Z
        i, j = int(round(py)), int(round(px))
        if 0 <= i < big.shape[0] and 0 <= j < big.shape[1]:
            big[i, j] = col
rio.save_rgb(os.path.join(HERE, "zoom_hole_circles.png"), big)

# 6x zooms of the top rim and the right rim
for tag, (bx0, bx1, by0, by1) in (("top", (590, 680, 370, 420)),
                                  ("right", (740, 790, 500, 560)),
                                  ("left", (470, 520, 500, 560)),
                                  ("bottom", (590, 680, 640, 690))):
    Z2 = 8
    crop = rgb[by0:by1, bx0:bx1]
    big = np.repeat(np.repeat(crop, Z2, axis=0), Z2, axis=1).copy()
    for cx, cy, r, col in circles:
        for a in np.arange(0, 360, 0.02):
            th = np.radians(a)
            px = (cx + np.cos(th) * r - bx0) * Z2
            py = (cy + np.sin(th) * r - by0) * Z2
            i, j = int(round(py)), int(round(px))
            if 0 <= i < big.shape[0] and 0 <= j < big.shape[1]:
                big[i, j] = col
    rio.save_rgb(os.path.join(HERE, "zoom_hole_%s.png" % tag), big)
print("ok")
