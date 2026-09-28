import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
# seam: dark horizontal line inside centre holes (v2 x 450..488, v3 x 742..780)
for v, (a, b) in dict(v2=(452, 486), v3=(744, 778)).items():
    for row, (cy, h) in dict(A=(326, 37), B=(442, 37), C=(562, 37)).items():
        p = L[cy-h+6:cy+h-6, a:b].mean(1)
        hp = p - gauss_blur(np.tile(p[None], (3, 1)), 3)[1]
        i = int(np.argmin(hp)); print(v, row, "seam y", cy-h+6+i, "depth", round(float(hp[i]), 3), "hole centre", cy)
# inner tube limb inside side holes: horizontal luminance profile
for v, y in (('v2', 442), ('v2', 326), ('v2', 562)):
    p = L[y-4:y+5, 376:416].mean(0)
    print(v, y, "left hole x376..415:", ' '.join(f"{t:.2f}" for t in p))
    p = L[y-4:y+5, 522:560].mean(0)
    print(v, y, "right hole x522..559:", ' '.join(f"{t:.2f}" for t in p))
for v, y in (('v3', 442), ('v3', 326)):
    p = L[y-4:y+5, 655:702].mean(0)
    print(v, y, "left hole x655..701:", ' '.join(f"{t:.2f}" for t in p))
