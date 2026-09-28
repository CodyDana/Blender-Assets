import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2_ring_fit import *
px, pz = S.pin_c
res = []
for z in (155.5, 156.5, 157.5):
    for ey in (-20.0, -21.0, -22.0, -23.0):
        for alpha in range(0, 21, 5):
            for tau in range(0, 21, 5):
                s, per = score((px, ey, z), alpha, tau)
                res.append((round(s, 2), z, ey, alpha, tau, per))
res.sort(key=lambda t: t[0])
for r in res[:12]:
    print(r)
