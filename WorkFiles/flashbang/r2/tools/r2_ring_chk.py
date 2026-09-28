import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2_ring_fit import *
px, pz = S.pin_c
top = (px, S.pin_eye_y(), pz)
rp = ring_pts(top, 0.0, 30.0)
for v in VIEW_X_PX:
    m = bodym[v] | mask(rp, v)
    ex = extents(m, v, [3.0, 3.2, 3.4, 3.6])
    print(v, [(round(a, 1), round(b, 1)) for a, b in ex])
    print("  ref", [(round(a, 1), round(b, 1)) for a, b in extents(REFM[v], v, [3.0, 3.2, 3.4, 3.6])])
