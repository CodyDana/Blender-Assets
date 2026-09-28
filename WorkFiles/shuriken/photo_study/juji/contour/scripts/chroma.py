import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load().astype(np.float64)
bg = np.load(ROOT + "bgfit.npy").astype(np.float64)
res = rgb - bg
far = ~dilate(np.load(ROOT + "mask_lo.npy"), 12)
C = np.cov(res[far].T); ev, V = np.linalg.eigh(C)
print("eigvals sd", np.sqrt(ev).round(4)); print("eigvecs (cols)", V.round(3))
Zc = (res @ V[:, :2]) / np.sqrt(ev[:2])   # chroma-like minor components, whitened
Zl = (res @ V[:, 2]) / np.sqrt(ev[2])
def box(a, r):
    k = 2 * r + 1; p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1); c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
Mc = np.sqrt((Zc ** 2).sum(-1))
Mcs = box(Mc, 2)
print("Mcs bg pct 50/99/99.9/max", np.percentile(Mcs[far], [50, 99, 99.9, 100]).round(2))
t = float(np.expm1(otsu(np.log1p(Mcs)))); print("otsu Mcs", round(t, 3))
np.save(ROOT + "Mcs.npy", Mcs.astype(np.float32)); np.save(ROOT + "Zc.npy", Zc.astype(np.float32))
write_png(ROOT + "debug_chroma.png", np.clip(Mcs / 12, 0, 1))
