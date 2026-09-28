import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, imglib as L
OUT = os.path.dirname(os.path.abspath(__file__))
lum = np.load(os.path.join(OUT, "lum.npy"))
def boxmean(a, r):
    k = 2 * r + 1
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), 0)
    a1 = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a1, ((0, 0), (r + 1, r)), mode="edge"), 1)
    return (c[:, k:] - c[:, :-k]) / k
m = boxmean(lum, 2)
v = np.maximum(boxmean(lum * lum, 2) - m * m, 0) ** 0.5
np.save(os.path.join(OUT, "std5.npy"), v.astype(np.float32))
print("std percentiles", np.percentile(v, [1, 10, 50, 90, 99]))
L.save_png(os.path.join(OUT, "texture_std.png"), np.clip(v / 0.05, 0, 1))
# sample values in known regions
for name, (x, y) in dict(face=(700, 600), face2=(400, 700), bevel_T4=(1150, 820), umbra_N1=(584, 334),
                         shadow_N1=(584, 300), lid=(1100, 1100), lid2=(100, 100), darkband_T8=(200, 444),
                         facet_T4=(1150, 790), bevel_T7=(246, 888)).items():
    print("%-12s (%4d,%4d) lum %.2f std %.4f" % (name, x, y, lum[y, x], v[y, x]))
