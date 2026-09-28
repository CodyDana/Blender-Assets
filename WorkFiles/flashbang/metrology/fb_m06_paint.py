import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); H = 745
rgb = ref[:H]
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
# paint: green dominant
greenness = g - 0.5*(r + b)
paint = greenness > 0.02
pm = gauss_blur(paint.astype(np.float32), 1.5) > 0.5
np.save(DBG + "/fb_paint.npy", pm)
vis = rgb*0.5; vis[pm] = [0.2, 0.9, 0.2]
save_png(DBG + "/paint.png", vis)
print("ok")
