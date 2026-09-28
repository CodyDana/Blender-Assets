"""Edge refinement v4: per-normal half-level crossing of a shading-invariant chromaticity feature.
F = (r_chroma - b_chroma) residual vs fitted background, in LINEAR RGB chromaticity (piece is redder/less blue,
the scanner-lid shadow keeps the background's chromaticity). Usage: refine4.py [level_frac] [tag]"""
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/contour/scripts")
from common import *
from geom import *
LEVEL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
TAG = sys.argv[2] if len(sys.argv) > 2 else ""
rgb = load()
h, w, _ = rgb.shape
res = np.load(ROOT + "chroma_res.npy").astype(np.float64)
F = (res[..., 0] - res[..., 1]) / np.sqrt(2)
def gauss1d(sig):
    r = int(3 * sig + 0.5); x = np.arange(-r, r + 1); k = np.exp(-x**2 / (2 * sig**2)); return k / k.sum()
def gblur2(a, sig):
    k = gauss1d(sig); r = len(k) // 2
    p = np.pad(a, ((r, r), (0, 0)), mode="edge"); a1 = sum(k[i] * p[i:i + a.shape[0]] for i in range(len(k)))
    p = np.pad(a1, ((0, 0), (r, r)), mode="edge"); return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(len(k)))
Fs = gblur2(F, 1.5)
np.save(ROOT + "Fs.npy", Fs.astype(np.float32))
m5 = np.load(ROOT + "mask_t5.0.npy"); m35 = np.load(ROOT + "mask_t3.5.npy")
m0 = m5 | (m35 & dilate(m5, 5))
m0 = erode(dilate(m0, 2), 2); m0 = dilate(erode(m0, 2), 2)
P = moore_trace(m0)
Pr = resample_closed(smooth_closed(P, 2.0), 1.0)
T = np.gradient(smooth_closed(Pr, 5.0), axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
N = np.stack([T[:, 1], -T[:, 0]], 1)
test = Pr + 4 * N
inside = m0[np.clip(test[:, 1].round().astype(int), 0, h - 1), np.clip(test[:, 0].round().astype(int), 0, w - 1)]
if inside.mean() > 0.5: N = -N
ts = np.arange(-30, 16.01, 0.25)
X = Pr[:, None, 0] + ts[None, :] * N[:, None, 0]; Y = Pr[:, None, 1] + ts[None, :] * N[:, None, 1]
prof = bilinear(Fs, X.ravel(), Y.ravel()).reshape(len(Pr), len(ts))
inm = m0[np.clip(Y.round().astype(int), 0, h - 1), np.clip(X.round().astype(int), 0, w - 1)]
jin = (ts <= -3); jout = (ts >= 6)
off = np.full(len(Pr), np.nan); lev_in = np.zeros(len(Pr)); lev_out = np.zeros(len(Pr))
for i in range(len(Pr)):
    pin = prof[i, jin & inm[i]]
    if len(pin) < 4: continue
    a = np.percentile(pin, 85); b = np.median(prof[i, jout])
    lev_in[i] = a; lev_out[i] = b
    if a - b < 5e-3: continue
    lev = b + LEVEL * (a - b)
    strong = np.nonzero((prof[i] >= b + 0.8 * (a - b)) & (ts <= 0) & inm[i])[0]
    if len(strong) == 0: continue
    j = strong.max()
    while j < len(ts) - 1 and prof[i, j + 1] >= lev: j += 1
    if j >= len(ts) - 1: continue
    f0, f1 = prof[i, j], prof[i, j + 1]
    off[i] = ts[j] + 0.25 * (f0 - lev) / max(f0 - f1, 1e-9)
border = (Pr[:, 1] < 2.0) | (Pr[:, 0] < 2) | (Pr[:, 0] > w - 3) | (Pr[:, 1] > h - 3)
valid = ~np.isnan(off) & ~border
print(f"level={LEVEL}: valid {valid.mean():.3f}; raw offset pct 5/50/95 {np.nanpercentile(off[valid], [5, 50, 95]).round(2)}; contrast median {np.median((lev_in - lev_out)[valid]):.4f}")
off_f = np.where(valid, off, np.nan)
n = len(off); win = int(sys.argv[3]) if len(sys.argv) > 3 else 20
med = np.array([np.nanmedian(np.take(off_f, range(i - win, i + win + 1), mode="wrap")) if not border[i] else 0.0 for i in range(n)])
med = np.where(np.isnan(med), 0.0, med)
bad = ~valid | (np.abs(np.nan_to_num(off_f, nan=1e9) - med) > 2.0)
off2 = np.where(bad, med, off_f)
off2 = smooth_closed(off2[:, None], 3.0)[:, 0]
off2[border] = 0.0
Q = Pr + off2[:, None] * N
T0 = T.copy()
for _it in range(50):
    d = np.roll(Q, -1, 0) - Q
    fw = (d * T0).sum(1)
    keep = fw > 0.05
    if keep.all(): break
    Q = Q[keep]; T0 = T0[keep]; border = border[keep]; off2 = off2[keep]
print("  after de-loop", len(Q), "pts")
print(f"  final offset pct 5/50/95 {np.percentile(off2[~border], [5, 50, 95]).round(2)}")
np.save(ROOT + "contour_initial.npy", Pr); np.save(ROOT + "contour_normals.npy", N); np.save(ROOT + f"contour_tangent{TAG}.npy", T0)
np.save(ROOT + f"contour_refined{TAG}.npy", Q); np.save(ROOT + "contour_border_flag.npy", border)
np.save(ROOT + f"contour_offset{TAG}.npy", off2)
if not TAG:
    mref = poly_fill(Q, h, w); np.save(ROOT + "mask_refined.npy", mref)
    write_png(ROOT + "juji_mask.png", mref.astype(np.float32))
    print("  refined area", int(mref.sum()), "initial area", int(m0.sum()))
