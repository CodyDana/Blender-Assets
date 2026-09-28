import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
def darkline(x, ya, yb, hw=3):
    p = L[ya:yb, x-hw:x+hw+1].mean(1)
    p = p - gauss_blur(np.tile(p[None], (3, 1)), 4)[1]
    i = int(np.argmin(p)); return ya + i, round(float(p[i]), 3)
for v, xs in dict(v2=[386, 395, 405, 424, 440, 455, 468, 480, 495, 512, 530, 545, 552], v3=[664, 680, 700, 716, 740, 760, 780, 800, 812, 825]).items():
    for lab, (ya, yb) in dict(AB=(372, 396), BC=(490, 515), sleeve=(250, 275), top=(185, 205), captop=(625, 652), capbot=(690, 712)).items():
        print(v, lab, [(x, *darkline(x, ya, yb)) for x in xs])
