import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np, sb_lib as L, sb_sphere as S
rgb = L.load_srgb(); Y = L.lum(rgb)
H, W = Y.shape
yy, xx = np.mgrid[0:H, 0:W]
r = np.hypot(xx - S.CX, yy - S.CY)
for lo, hi in ((475, 490), (490, 520), (520, 580), (580, 700)):
    m = (r > lo) & (r < hi)
    for nm, mm in (("below", m & (yy > S.CY + 300)), ("above", m & (yy < S.CY - 300)), ("left", m & (xx < S.CX - 300)), ("right", m & (xx > S.CX + 300))):
        v = Y[mm]
        print(f"ring {lo}-{hi} {nm}: mean {v.mean():.4f} min {v.min():.4f} p1 {np.percentile(v,1):.4f}")
v = rgb[(r > 520)]
print("bg rgb mean", v.mean(0).round(4), "std", v.std(0).round(4), "min", v.min(0).round(4), "max", v.max(0).round(4))
