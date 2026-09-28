import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
hp = L - gauss_blur(L, 6)
def enh(x0, y0, x1, y1, k, out):
    c = hp[y0:y1, x0:x1]
    c = np.clip(0.5 + c*4, 0, 1)
    # column mean of high-pass inside cap band (vertical line detector)
    save_png(out, upscale(c, k))
enh(360, 620, 580, 725, 4, DBG + "/cap_v2_hp.png")
enh(640, 620, 850, 725, 4, DBG + "/cap_v3_hp.png")
enh(45, 620, 265, 725, 4, DBG + "/cap_v1_hp.png")
# column profile of vertical-edge energy in cap side band y 650..695
gx = np.abs(np.diff(gauss_blur(L, 1.0), axis=1))
for v, (a, b) in dict(v1=(55, 258), v2=(368, 565), v3=(645, 847), v4=(1000, 1206)).items():
    prof = gx[652:696, a:b].mean(0)
    thr = np.percentile(prof, 85)
    pk = [a+i for i in range(2, len(prof)-2) if prof[i] == prof[i-2:i+3].max() and prof[i] > thr]
    print(v, "cap vertical-line peaks x:", pk)
