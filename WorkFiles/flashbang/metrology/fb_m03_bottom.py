import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
for name, xs in dict(v1=(100,157,220), v2=(420,470,520), v3=(700,745,800), v4=(1050,1100,1150)).items():
    for x in xs:
        col = L[680:735, x-3:x+4].mean(1)
        print(name, x, ' '.join(f"{v:.3f}" for v in col))
