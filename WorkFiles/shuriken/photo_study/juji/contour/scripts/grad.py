import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
rgb = load().astype(np.float64)
bg = np.load(ROOT + "bgfit.npy").astype(np.float64)
m5 = np.load(ROOT + "mask_t5.0.npy")
res = rgb - bg
far = ~dilate(np.load(ROOT + "mask_lo.npy"), 12)
C = np.cov(res[far].T)
ev, V = np.linalg.eigh(C)
Wm = V @ np.diag(1 / np.sqrt(ev)) @ V.T
Z = res @ Wm.T   # whitened residual, bg ~ N(0, I)
def gauss1d(sig):
    r = int(3 * sig + 0.5); x = np.arange(-r, r + 1); k = np.exp(-x**2 / (2 * sig**2)); return k / k.sum()
def gblur(a, sig):
    k = gauss1d(sig); r = len(k) // 2
    p = np.pad(a, ((r, r), (0, 0)) + ((0, 0),) * (a.ndim - 2), mode="edge")
    a1 = sum(k[i] * p[i:i + a.shape[0]] for i in range(len(k)))
    p = np.pad(a1, ((0, 0), (r, r)) + ((0, 0),) * (a.ndim - 2), mode="edge")
    return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(len(k)))
Zs = gblur(Z, 1.5)
gy = np.zeros_like(Zs); gx = np.zeros_like(Zs)
gy[1:-1] = (Zs[2:] - Zs[:-2]) / 2; gx[:, 1:-1] = (Zs[:, 2:] - Zs[:, :-2]) / 2
G = np.sqrt((gx**2 + gy**2).sum(-1))
np.save(ROOT + "Zs.npy", Zs.astype(np.float32)); np.save(ROOT + "G.npy", G.astype(np.float32))
print("G bg pct 50/99/99.9", np.percentile(G[far], [50, 99, 99.9]).round(2), "G near edge pct 50/90", np.percentile(G[m5 & ~erode(m5, 3)], [50, 90]).round(2))
write_png(ROOT + "debug_grad.png", np.clip(G / np.percentile(G, 99.5), 0, 1))
