import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
# column profile of luminance for rows 60..720 (top row). Print mean L per 10-px column band, rows 100..700
for y0 in (50, 150, 300, 450, 600, 700, 730, 745, 750, 755):
    row = L[y0]
    print(y0, ' '.join(f"{v:.2f}" for v in row[::20]))
