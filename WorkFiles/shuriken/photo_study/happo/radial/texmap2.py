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
res = lum - boxmean(lum, 2)
tex = boxmean(np.abs(res), 2)
np.save(os.path.join(OUT, "tex.npy"), tex.astype(np.float32))
print("tex percentiles", np.percentile(tex, [1, 10, 50, 75, 90, 99]))
L.save_png(os.path.join(OUT, "texture_hp.png"), np.clip(tex / 0.03, 0, 1))
for name, (x, y) in dict(face=(700, 600), face2=(400, 700), face3=(900, 700), bevel_T4=(1150, 820),
                         umbra_N1=(584, 334), shadow_N1=(584, 300), shadow_N1b=(584, 315), lid=(1100, 1100),
                         lid2=(100, 100), darkband_T8=(200, 444), darkband_T8b=(300, 443),
                         facet_T4=(1150, 790), bevel_T7=(246, 888), bevel_T1=(337, 156),
                         umbra_N8=(360, 444), face_nearT8=(200, 460)).items():
    print("%-13s (%4d,%4d) lum %.2f tex %.4f" % (name, x, y, lum[y, x], tex[y, x]))
