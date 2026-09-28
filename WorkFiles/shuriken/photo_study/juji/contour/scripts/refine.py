import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
rgb = load()
h, w, _ = rgb.shape
m0 = np.load(ROOT + "mask_t5.0.npy")
m0 = erode(dilate(m0, 2), 2); m0 = dilate(erode(m0, 2), 2)
Zs = np.load(ROOT + "Zs.npy").astype(np.float64)
P = moore_trace(m0)
print("traced", len(P), "pts; signed area", signed_area(P), "mask area", m0.sum())
Pr = resample_closed(smooth_closed(P, 2.0), 1.0)
T = np.gradient(smooth_closed(Pr, 4.0), axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
N = np.stack([T[:, 1], -T[:, 0]], 1)
test = Pr + 4 * N
inside = m0[np.clip(test[:, 1].round().astype(int), 0, h - 1), np.clip(test[:, 0].round().astype(int), 0, w - 1)]
if inside.mean() > 0.5:
    N = -N
print("normal orientation: frac(+4N inside) =", round(float(inside.mean()), 3))
ts = np.arange(-8, 14.01, 0.5)  # positive = outward
X = Pr[:, None, 0] + ts[None, :] * N[:, None, 0]
Y = Pr[:, None, 1] + ts[None, :] * N[:, None, 1]
prof = bilinear(Zs, X.ravel(), Y.ravel()).reshape(len(Pr), len(ts), 3)
mag = np.linalg.norm(prof, axis=-1)
dZ = np.gradient(prof, ts, axis=1)
dmag = np.gradient(mag, ts, axis=1)
score = np.linalg.norm(dZ, axis=-1) * (dmag < 0)
border = (Pr[:, 1] < 2.0) | (Pr[:, 0] < 2) | (Pr[:, 0] > w - 3) | (Pr[:, 1] > h - 3)
k = score.argmax(1)
off = ts[k].astype(float)
for i in range(len(Pr)):
    j = k[i]
    if 0 < j < len(ts) - 1:
        a, b, c = score[i, j - 1], score[i, j], score[i, j + 1]
        den = a - 2 * b + c
        if den < 0:
            off[i] += 0.5 * 0.5 * (a - c) / den
off[border] = 0.0
n = len(off); win = 7
med = np.array([np.median(np.take(off, range(i - win, i + win + 1), mode="wrap")) for i in range(n)])
bad = np.abs(off - med) > 2.0
off2 = np.where(bad, med, off)
off2 = np.convolve(np.concatenate([off2[-3:], off2, off2[:3]]), np.ones(7) / 7, "same")[3:-3]
off2[border] = 0.0
Q = Pr + off2[:, None] * N
print("offset (px, + = outward): median", np.median(off2).round(2), "p5/p95", np.percentile(off2, [5, 95]).round(2), "outliers replaced", int(bad.sum()), "border pts", int(border.sum()))
np.save(ROOT + "contour_initial.npy", Pr)
np.save(ROOT + "contour_refined.npy", Q); np.save(ROOT + "contour_border_flag.npy", border)
np.save(ROOT + "contour_offset.npy", off2)
mref = poly_fill(Q, h, w)
np.save(ROOT + "mask_refined.npy", mref)
write_png(ROOT + "juji_mask.png", mref.astype(np.float32))
print("refined area", int(mref.sum()))
