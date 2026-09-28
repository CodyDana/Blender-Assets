import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
rgb = load().astype(np.float64)
h, w, _ = rgb.shape
bg = np.load(ROOT + "bgfit.npy").astype(np.float64)
m5 = np.load(ROOT + "mask_t5.0.npy"); m35 = np.load(ROOT + "mask_t3.5.npy")
m0 = m5 | (m35 & dilate(m5, 5))
m0 = erode(dilate(m0, 2), 2); m0 = dilate(erode(m0, 2), 2)
res = rgb - bg
far = ~dilate(np.load(ROOT + "mask_lo.npy"), 12)
C = np.cov(res[far].T); ev, V = np.linalg.eigh(C); Wm = V @ np.diag(1 / np.sqrt(ev)) @ V.T
Z = res @ Wm.T
def gauss1d(sig):
    r = int(3 * sig + 0.5); x = np.arange(-r, r + 1); k = np.exp(-x**2 / (2 * sig**2)); return k / k.sum()
def gblur(a, sig):
    k = gauss1d(sig); r = len(k) // 2
    p = np.pad(a, ((r, r), (0, 0), (0, 0)), mode="edge"); a1 = sum(k[i] * p[i:i + a.shape[0]] for i in range(len(k)))
    p = np.pad(a1, ((0, 0), (r, r), (0, 0)), mode="edge"); return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(len(k)))
SIG = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
Zs = gblur(Z, SIG)
P = moore_trace(m0)
Pr = resample_closed(smooth_closed(P, 2.0), 1.0)
T = np.gradient(smooth_closed(Pr, 5.0), axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
N = np.stack([T[:, 1], -T[:, 0]], 1)
test = Pr + 4 * N
inside = m0[np.clip(test[:, 1].round().astype(int), 0, h - 1), np.clip(test[:, 0].round().astype(int), 0, w - 1)]
if inside.mean() > 0.5: N = -N
ts = np.arange(-10, 16.01, 0.25)
X = Pr[:, None, 0] + ts[None, :] * N[:, None, 0]; Y = Pr[:, None, 1] + ts[None, :] * N[:, None, 1]
prof = bilinear(Zs, X.ravel(), Y.ravel()).reshape(len(Pr), len(ts), 3)
# far-outside reference: sample at +16..+20 px (beyond halo mostly) and inside reference at -10..-7
tin = (ts <= -7); tout = (ts >= 13)
zin = prof[:, tin].mean(1); zout = prof[:, tout].mean(1)
u = zin - zout; u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
proj = np.einsum("ntc,nc->nt", prof, u)
dproj = -np.gradient(proj, ts, axis=1)   # positive where projection falls going outward
WIN_IN = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
win_ok = (ts >= -WIN_IN) & (ts <= 12)
sc = np.where(win_ok[None, :], dproj, -np.inf)
k = sc.argmax(1); off = ts[k].astype(float)
for i in range(len(Pr)):
    j = k[i]
    if 0 < j < len(ts) - 1 and np.isfinite(sc[i, j - 1]) and np.isfinite(sc[i, j + 1]):
        a, b, c = sc[i, j - 1], sc[i, j], sc[i, j + 1]; den = a - 2 * b + c
        if den < 0: off[i] += 0.25 * 0.5 * (a - c) / den
border = (Pr[:, 1] < 2.0) | (Pr[:, 0] < 2) | (Pr[:, 0] > w - 3) | (Pr[:, 1] > h - 3)
off[border] = 0.0
n = len(off); win = 12
med = np.array([np.median(np.take(off, range(i - win, i + win + 1), mode="wrap")) for i in range(n)])
bad = np.abs(off - med) > 1.5
off2 = np.where(bad, med, off)
off2 = np.convolve(np.concatenate([off2[-4:], off2, off2[:4]]), np.ones(9) / 9, "same")[4:-4]
off2[border] = 0.0
Q = Pr + off2[:, None] * N
contrast = dproj.max(1)
print(f"sig={SIG} offset median {np.median(off2):.2f} p5/p95 {np.percentile(off2, [5, 95]).round(2)} frac at window limits {(np.abs(off - 12) < 0.3).mean() + (np.abs(off + WIN_IN) < 0.3).mean():.3f} outliers {bad.sum()} / {n}")
np.save(ROOT + "contour_initial.npy", Pr); np.save(ROOT + "contour_refined.npy", Q)
np.save(ROOT + "contour_border_flag.npy", border); np.save(ROOT + "contour_offset.npy", off2)
np.save(ROOT + "contour_normals.npy", N)
mref = poly_fill(Q, h, w); np.save(ROOT + "mask_refined.npy", mref)
write_png(ROOT + "juji_mask.png", mref.astype(np.float32))
print("refined area", int(mref.sum()), "initial area", int(m0.sum()))
