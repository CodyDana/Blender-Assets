import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb()
x0, y0, x1, y1 = 640, 920, 940, 1180
c = ref[y0:y1, x0:x1]
L = lum(c); hp = L - gauss_blur(L, 5)
e = np.clip(0.5 + hp*3, 0, 1)
e3 = np.stack([e]*3, 2)
# ruler grid every 20 px
for gx in range(0, x1-x0, 20): e3[:, gx] = [1, 0, 0] if (gx+x0) % 100 == 0 else [0.3, 0.6, 1]
for gy in range(0, y1-y0, 20): e3[gy, :] = [1, 0, 0] if (gy+y0) % 100 == 0 else [0.3, 0.6, 1]
save_png(DBG + "/p3_endface_hp.png", upscale(e3, 3))
print("ok")
