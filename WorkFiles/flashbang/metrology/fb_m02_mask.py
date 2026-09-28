import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref).astype(np.float32)
top = L[:745].copy()
def lstd(a, r):
    m = box_blur(a, r); m2 = box_blur(a*a, r); return np.sqrt(np.clip(m2 - m*m, 0, None))
s = lstd(top, 2)
# chroma: background is neutral grey; paint is green
rgb = ref[:745]
chroma = rgb.max(2) - rgb.min(2)
bgc = (s < 0.012) & (chroma < 0.03)
w = bgc.astype(np.float32)
num = gauss_blur(top*w, 25); den = gauss_blur(w, 25)
bg = num / np.maximum(den, 1e-4)
for it in range(2):
    bgc = bgc & (np.abs(top-bg) < 0.03)
    w = bgc.astype(np.float32); num = gauss_blur(top*w, 25); den = gauss_blur(w, 25); bg = num/np.maximum(den,1e-4)
d = np.abs(top - bg)
fg = (d > 0.035) | (s > 0.018) | (chroma > 0.045)
np.save(DBG + "/fb_fg_raw.npy", fg)
np.save(DBG + "/fb_bg.npy", bg)
vis = np.stack([fg*1.0, top, top], 2)
save_png(DBG + "/mask_raw.png", vis)
print("done", fg.mean())
