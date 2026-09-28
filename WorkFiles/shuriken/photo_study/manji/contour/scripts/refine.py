# Sub-pixel edge relocation along contour normals using fine-scale edge magnitude (DoG sigma 1.2 px),
# with a scanner cast-shadow model setting the search window. Produces the refined mask.
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy")
H, W = px.shape[:2]
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
m = np.load(BASE + "/mask_solid.npy")
c = np.load(BASE + "/coarse_contour.npy")
N = len(c)
area2 = np.sum(c[:, 0] * np.roll(c[:, 1], -1) - np.roll(c[:, 0], -1) * c[:, 1])
print("contour pts", N, "signed area*2", area2)
def circ_smooth(a, sig):
    r = int(3 * sig); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2); k /= k.sum()
    ap = np.concatenate([a[-r:], a, a[:r]])
    return np.stack([np.convolve(ap[:, j], k, mode="valid") for j in range(a.shape[1])], 1)
cs = circ_smooth(c, 8.0)
tg = np.roll(cs, -3, 0) - np.roll(cs, 3, 0)
tg /= np.maximum(np.hypot(tg[:, 0], tg[:, 1]), 1e-9)[:, None]
nrm = np.stack([tg[:, 1], -tg[:, 0]], 1)
# orient outward: test a sample of points
test = cs + 6 * nrm
inside = m[np.clip(np.round(test[:, 1]).astype(int), 0, H - 1), np.clip(np.round(test[:, 0]).astype(int), 0, W - 1)]
if inside.mean() > 0.5: nrm = -nrm
print("outward check frac inside after flip", float(m[np.clip(np.round((cs + 6 * nrm)[:, 1]).astype(int), 0, H - 1), np.clip(np.round((cs + 6 * nrm)[:, 0]).astype(int), 0, W - 1)].mean()))
S_VEC = np.array([24.0, -40.0])   # cast-shadow vector fitted from averaged profiles (px): shadows fall up and to the right
ts = np.arange(-66, 8.01, 0.5)
sig = 1.2; dt = 0.5; r = int(4 * sig / dt); kk = np.arange(-r, r + 1) * dt
gk = -kk * np.exp(-0.5 * (kk / sig) ** 2); gk /= np.sum(np.abs(gk) * np.abs(kk))
pred = np.maximum(0, nrm @ S_VEC)
tang = np.stack([-nrm[:, 1], nrm[:, 0]], 1)
# sample all profiles once (tangentially averaged over 5 px)
G = np.zeros((N, len(ts)), np.float32)
TB = np.zeros((N, len(ts)), np.float32)
WB = np.zeros((N, len(ts)), np.float32)
Warm = (px[:, :, 0] - px[:, :, 2]).astype(np.float32)   # R-B warmth: the bevel band on the top hook back edge is golden
Tex = np.load(BASE + "/texture.npy")
B = 500
for s0 in range(0, N, B):
    sl = slice(s0, min(N, s0 + B))
    base = cs[sl]; nn = nrm[sl]; tt = tang[sl]
    prof = np.zeros((len(base), len(ts))); tprof = np.zeros((len(base), len(ts))); wprof = np.zeros((len(base), len(ts)))
    for dtan in (-3, -2, -1, 0, 1, 2, 3):
        X = base[:, 0:1] + dtan * tt[:, 0:1] + ts[None, :] * nn[:, 0:1]
        Y = base[:, 1:2] + dtan * tt[:, 1:2] + ts[None, :] * nn[:, 1:2]
        prof += bilinear(L, X, Y); tprof += bilinear(Tex, X, Y); wprof += bilinear(Warm, X, Y)
    prof /= 7; TB[sl] = tprof / 7; WB[sl] = wprof / 7
    for j in range(len(base)):
        G[s0 + j] = np.abs(np.convolve(prof[j], gk[::-1], mode="same") / dt)
def cmed(a, k):
    hk = k // 2; ap = np.concatenate([a[-hk:], a, a[:hk]])
    return np.array([np.median(ap[i:i + k]) for i in range(len(a))])
# Optimal continuous edge path through the band-unwrapped edge-magnitude image (Viterbi / dynamic programming):
# maximise sum G[i, k_i] - LAM * |k_i - k_{i-1}| with |k_i - k_{i-1}| <= MAXJ bins, over offsets t in [-62, +6] px.
LAM = 0.004; MAXJ = 3
valid = (ts >= -62) & (ts <= 6)
# inner-side texture weight: a real metal edge has in-focus textured metal just inside it; shadow ramps do not.
# texture-onset term: textured inside minus outside (catches blurred edges where the luminance step is weak).
Tin = np.zeros_like(TB); Tout = np.zeros_like(TB)
for d in range(2, 11):          # 1..5 px at 0.5 px spacing
    Tin[:, d:] += TB[:, :-d]; Tout[:, :-d] += TB[:, d:]
Tin /= 9; Tout /= 9
Wt = np.clip((Tin - 0.005) / 0.005, 0.15, 1.0)
TS = np.clip(Tin - Tout, 0, None)
GAMMA = 0.0   # texture-onset term disabled: the step edge itself inflates T just outside sharp edges
np.save(BASE + "/refine_Tin.npy", Tin.astype(np.float32))
Gv = np.where(valid[None, :], G * Wt + GAMMA * TS, -1.0).astype(np.float64)
# start at a point on a long non-shadow (down-facing) edge where the coarse boundary is reliable
start = int(np.argmax((nrm[:, 1] > 0.95) * Gv[:, np.argmin(np.abs(ts))]))
order = np.r_[start:N, 0:start]
K = len(ts)
score = Gv[order[0]].copy()
back = np.zeros((N, K), np.int16)
shifts = range(-MAXJ, MAXJ + 1)
for step in range(1, N):
    best = np.full(K, -1e18); arg = np.zeros(K, np.int16)
    for s in shifts:
        prev = np.full(K, -1e18)
        if s >= 0: prev[s:] = score[:K - s] if s > 0 else score
        else: prev[:K + s] = score[-s:]
        cand = prev - LAM * abs(s)
        better = cand > best
        best = np.where(better, cand, best); arg = np.where(better, np.arange(K) - s, arg)
    score = best + Gv[order[step]]
    back[step] = arg
path = np.zeros(N, int); path[-1] = int(np.argmax(score))
for step in range(N - 1, 0, -1):
    path[step - 1] = back[step][path[step]]
offs = np.zeros(N); offs[order] = ts[path]
strength = np.zeros(N); strength[order] = G[order, path]
offs_med = cmed(offs, 5)
o1 = offs; o1s = offs_med
print("DP start index", start, "at", cs[start].round(1))
# --- zone override: the top hook back edge (x 480..1400, y < 260, up-facing) is defocused and carries a golden bevel
# band; the luminance path locks onto the band's inner line and the texture onset is contaminated by umbra noise.
# There the silhouette is taken as the warmth onset: outermost t where R-B (7 px tangential mean) rises through THR_W
# going inward and stays >= 0.9*THR_W for 2 px further in. Where no such onset exists the luminance path is kept.
THR_W = 0.105
zone = (cs[:, 0] > 480) & (cs[:, 0] < 1400) & (cs[:, 1] < 260) & (nrm[:, 1] < -0.5)
zi = np.nonzero(zone)[0]
ov = np.full(N, np.nan)
k1 = np.exp(-0.5 * (np.arange(-4, 5) * 0.5 / 1.0) ** 2); k1 /= k1.sum()
for j in zi:
    wb = np.convolve(WB[j], k1, mode="same")
    ok = (ts >= -50) & (ts <= 4)
    for k in range(len(ts) - 2, 10, -1):
        if not (ok[k] and ok[k + 1]): continue
        if wb[k] >= THR_W and wb[k + 1] < THR_W and wb[k - 4:k + 1].min() >= 0.9 * THR_W:
            ov[j] = ts[k] + (wb[k] - THR_W) / (wb[k] - wb[k + 1]) * 0.5
            break
good = ~np.isnan(ov[zi])
zz = zi[good]; vals = ov[zz]
vm = np.array([np.median(vals[max(0, i - 7):i + 8]) for i in range(len(vals))])
d = vm - offs_med[zz]
print("top-hook back-edge zone points", len(zi), "warmth onset found", int(good.sum()),
      "| override-DP median %.1f p10 %.1f p90 %.1f" % tuple(np.percentile(d, [50, 10, 90])))
# only accept overrides that lie outward of the luminance path (the path is on the band's inner line) and within 30 px
acc = (d > -2) & (d < 30)
zz = zz[acc]; offs_med[zz] = vm[acc]
print("  accepted", int(acc.sum()))
# bridge short gaps (<= 40 contour points) between accepted overrides by linear interpolation along the contour
if len(zz) > 1:
    gaps = 0
    for a_, b_ in zip(zz[:-1], zz[1:]):
        if 1 < b_ - a_ <= 40:
            ii = np.arange(a_ + 1, b_)
            offs_med[ii] = np.interp(ii, [a_, b_], [offs_med[a_], offs_med[b_]]); gaps += 1
    print("  bridged gaps", gaps)
np.save(BASE + "/tophook_override_idx.npy", zz)
refined = cs + offs_med[:, None] * nrm
np.save(BASE + "/refined_contour_raw.npy", refined)
np.save(BASE + "/refine_offsets.npy", np.stack([o1, o1s, offs, offs_med, strength, pred], 1))
print("offset stats: mean", offs_med.mean().round(2), "pct", np.percentile(offs_med, [1, 10, 50, 90, 99]).round(1))
print("edge strength pct", np.percentile(strength, [1, 5, 50]).round(3))
fm = fill_polygon(refined, H, W)
rm = fm & m
lab, n = label_runs(rm)
sz = np.bincount(lab.ravel()); sz[0] = 0
rm = lab == int(np.argmax(sz))
# fill enclosed background specks (hole state is decided separately from the coarse analysis)
lab2, n2 = label_runs(~rm)
border = np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])); border = border[border > 0]
filled = ~np.isin(lab2, border)
print("refined area", int(rm.sum()), "after fill", int(filled.sum()), "coarse area", int(m.sum()))
np.save(BASE + "/mask_refined.npy", filled)
write_png(BASE + "/manji_mask.png", filled.astype(np.float32))
