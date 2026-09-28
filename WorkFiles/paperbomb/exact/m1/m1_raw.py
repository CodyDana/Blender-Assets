import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m1")
from m1_lib import *
A = json.load(open(OUT+"m1_align.json")); r = load(REF); fr = load(FRONT); H, W = r.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
w = bilinear(fr, A["front"][0]*(xx+0.5)+A["front"][2]-0.5, A["front"][1]*(yy+0.5)+A["front"][3]-0.5)
Lr = lab(r); Lw = lab(w)
m = (xx > 40) & (xx < 260) & (yy > 40) & (yy < 620) & (Lr[..., 0] > 85) & (np.abs(Lr[..., 1]) < 8)
pr = np.median(Lr[m], 0); pw = np.median(Lw[m], 0)
print("paper ref", pr.round(2), "render raw", pw.round(2), "dE", float(de2000(pr, pw)))

kr = np.median(Lr[(Lr[..., 0] < 20)], 0); kw = np.median(Lw[(Lr[..., 0] < 20)], 0)
print("black ref", kr.round(2), "render raw", kw.round(2), "dE", float(de2000(kr, kw)))
rr = np.median(Lr[(Lr[..., 1] > 50)], 0); rw = np.median(Lw[(Lr[..., 1] > 50)], 0)
print("red ref", rr.round(2), "render raw", rw.round(2), "dE", float(de2000(rr, rw)))
