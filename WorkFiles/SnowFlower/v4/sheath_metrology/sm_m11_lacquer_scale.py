# sm_m11: lacquer vein orientation excluding facet lines, and correlation lengths on metal-free patches
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a)
prof = np.array(json.load(open(os.path.join(HERE, "sm_s01.json")))["profile"])
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}
metal = L > 0.36
m = metal.copy()
for _ in range(4):
    g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; m = g
lac = np.zeros(L.shape, bool); U = np.full(L.shape, np.nan)
for y in range(340, 1250):
    l, r = edge[y]; c = (l + r) / 2; hw = (r - l) / 2
    xs = np.arange(l, r + 1); u = (xs - c) / hw
    U[y, l:r + 1] = u
    ok = (np.abs(u) < 0.82) & (np.abs(np.abs(u) - 0.51) > 0.09)
    lac[y, l:r + 1] = ok
lac &= ~m
k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
Ls = L.astype(float)
for ax in (0, 1):
    Ls = np.apply_along_axis(lambda s: np.convolve(s, k, mode="same"), ax, Ls)
gy, gx = np.gradient(Ls)
sel = lac
ang = (np.degrees(np.arctan2(gy[sel], gx[sel])) + 90) % 180
mag = np.hypot(gx[sel], gy[sel])
strong = mag > np.percentile(mag, 80)
h, e = np.histogram(ang[strong], bins=12, range=(0, 180), weights=mag[strong])
h = h / h.sum()
print("vein dir hist (facets excluded), 0=across, 90=along")
for i in range(12):
    print("  %3d-%3d %.3f %s" % (e[i], e[i + 1], h[i], "#" * int(h[i] * 200)))
# correlation lengths: 32x20 patches, metal fraction < 5%
along, across = [], []
for y0 in range(345, 1215, 8):
    for x0 in range(455, 560, 4):
        pm = lac[y0:y0 + 32, x0:x0 + 20]
        if pm.mean() < 0.95:
            continue
        p = L[y0:y0 + 32, x0:x0 + 20].astype(float); p = p - p.mean()
        if p.std() < 1e-3:
            continue
        def ac_len(p, axis):
            n = p.shape[axis]; ac = []
            for lag in range(0, n - 4):
                a1 = p[:n - lag] if axis == 0 else p[:, :n - lag]
                a2 = p[lag:] if axis == 0 else p[:, lag:]
                ac.append((a1 * a2).mean())
            ac = np.array(ac) / ac[0]
            b = np.where(ac < 1 / np.e)[0]
            return int(b[0]) if len(b) else n
        along.append(ac_len(p, 0)); across.append(ac_len(p, 1))
print("patches", len(along), "corr len along median", np.median(along), "IQR", np.percentile(along, [25, 75]),
      "across median", np.median(across), "IQR", np.percentile(across, [25, 75]))
out = dict(vein_dir_hist=h.tolist(), bins=e.tolist(), n_patches=len(along), corr_along_med=float(np.median(along)),
           corr_along_iqr=np.percentile(along, [25, 75]).tolist(), corr_across_med=float(np.median(across)),
           corr_across_iqr=np.percentile(across, [25, 75]).tolist())
json.dump(out, open(os.path.join(HERE, "sm_s11.json"), "w"), indent=1)
