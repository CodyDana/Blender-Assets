import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
bands = dict(v2c=(460, 476), v2web=(508, 520), v3c=(735, 755), v1c=(120, 140), v4c=(1060, 1080))
prof = {k: L[:, a:b].mean(1) for k, (a, b) in bands.items()}
print("y " + " ".join(f"{k:>6}" for k in prof))
for y in range(35, 725):
    print(y, " ".join(f"{prof[k][y]:6.3f}" for k in prof), "  d:", " ".join(f"{prof[k][y+1]-prof[k][y-1]:+.2f}" for k in prof))
