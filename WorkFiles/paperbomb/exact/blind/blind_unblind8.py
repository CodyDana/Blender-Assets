# post-reveal (unblinded) 8x views: reference LEFT, ours (front render, native density) RIGHT
import bpy, numpy as np
exec(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/blind/blind_build.py", encoding="utf-8-sig").read().split("key = {}")[0].split("# light anti-alias")[0])
g = np.array([1.168451629171994, 1.1793596431678997, 1.2031434706849922], np.float32)
def up(a, f):
    h, w = a.shape[:2]; yy2, xx2 = np.mgrid[0:int(h*f), 0:int(w*f)].astype(np.float32)
    return bil(a, (xx2+0.5)/f-0.5, (yy2+0.5)/f-0.5)
def pair(A, B):
    return np.concatenate([A, np.full((A.shape[0], 8, 3), 0.2, np.float32), B], 1)
C = {"seal_sparkles": (36, 112, 488, 530), "seal_sparkle_br": (80, 116, 560, 602), "corner_TL8": (14, 60, 18, 64),
     "corner_BL8": (14, 60, 588, 634), "emblem8": (98, 202, 82, 180)}
for n, (x0, x1, y0, y1) in C.items():
    f = 8.0 if n != "emblem8" else 5.0
    hh, ww = int((y1-y0)*f), int((x1-x0)*f)
    yq, xq = np.mgrid[0:hh, 0:ww].astype(np.float32)
    rx = x0+(xq+0.5)/f; ry = y0+(yq+0.5)/f
    O = np.clip(bil(fr, AFF[0]*rx+AFF[2]-0.5, AFF[1]*ry+AFF[3]-0.5)*g, 0, 1)
    R = bil(ref, rx-0.5, ry-0.5)
    save(pair(R, O), OUT + "unblind_%s.png" % n)
print("OK")
