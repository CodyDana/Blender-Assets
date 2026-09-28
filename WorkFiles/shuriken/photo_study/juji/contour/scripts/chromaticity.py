"""Shading-invariant segmentation feature: linear-RGB chromaticity distance from a fitted background model."""
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import bilinear
rgb = load().astype(np.float64)
h, w, _ = rgb.shape
lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
ssum = lin.sum(-1) + 1e-4
ch = np.stack([lin[..., 0] / ssum, lin[..., 2] / ssum], -1)   # r and b chromaticity
Llin = lin @ np.array([0.2126, 0.7152, 0.0722])
yy, xx = np.mgrid[0:h, 0:w]; Y = yy / h - 0.5; X = xx / w - 0.5
def design(Xf, Yf, deg=3):
    return np.stack([(Xf ** i) * (Yf ** j) for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
far = ~dilate(np.load(ROOT + "mask_lo.npy"), 20)
A = design(X[far], Y[far]); Af = design(X.ravel(), Y.ravel())
bgc = np.zeros_like(ch)
for c in range(2):
    coef, *_ = np.linalg.lstsq(A, ch[..., c][far], rcond=None); bgc[..., c] = (Af @ coef).reshape(h, w)
res = ch - bgc
C = np.cov(res[far].T); Ci = np.linalg.inv(C)
print("bg chromaticity resid sd", np.sqrt(np.diag(C)).round(5))
def box(a, r):
    k = 2 * r + 1; p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1); c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
Mq = np.sqrt(np.einsum("hwi,ij,hwj->hw", res, Ci, res))
Mqs = box(Mq, 2)
print("Mqs bg pct 50/99/99.9/max", np.percentile(Mqs[far], [50, 99, 99.9, 100]).round(2))
m5 = np.load(ROOT + "mask_t5.0.npy"); core = erode(m5, 10)
print("Mqs piece core pct 1/5/25/50", np.percentile(Mqs[core], [1, 5, 25, 50]).round(2))
np.save(ROOT + "Mq.npy", Mq.astype(np.float32)); np.save(ROOT + "Mqs.npy", Mqs.astype(np.float32))
np.save(ROOT + "chroma_res.npy", res.astype(np.float32))
write_png(ROOT + "debug_chromaticity.png", np.clip(Mqs / 15, 0, 1))
# signed direction: piece is redder (r up, b down)?
print("piece core mean resid (r,b)", res[core].mean(0).round(4), " bg sd", np.sqrt(np.diag(C)).round(4))
Pr = np.load(ROOT + "contour_initial.npy"); N = np.load(ROOT + "contour_normals.npy")
ts = np.arange(-24, 16.01, 1.0)
print("t:", " ".join(f"{t:4.0f}" for t in ts))
for tx, ty in [(640, 450), (300, 755), (1100, 540), (805, 1100), (1100, 725), (581, 150), (779, 152), (1314, 583), (760, 300)]:
    i = np.argmin(np.hypot(Pr[:, 0] - tx, Pr[:, 1] - ty)); p, n = Pr[i], N[i]
    Xp = p[0] + ts * n[0]; Yp = p[1] + ts * n[1]
    print(f"pt {p.round(0)}\n  Mq:", " ".join(f"{a:4.1f}" for a in bilinear(Mqs, Xp, Yp)))
    print("  L :", " ".join(f"{a:4.2f}" for a in bilinear(Llin, Xp, Yp)))
