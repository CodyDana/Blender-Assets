"""Stage 2: coarse centre, r(theta) and vertex list from a mask (default: Otsu mask).
Angles: theta measured in the IMAGE frame with y DOWN, theta = atan2(-(y-cy), x-cx),
so 0 deg = +x (right), 90 deg = up in the picture (counter-clockwise as viewed).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
maskf = argv[0] if argv else "mask_filled.npy"
m = np.load(os.path.join(OUT, maskf)).astype(np.float32)
H, W = m.shape
ys, xs = np.nonzero(m > 0.5)
cx, cy = xs.mean(), ys.mean()

def r_of_theta(mask, cx, cy, step=0.1, rmax=900):
    th = np.deg2rad(np.arange(0, 360, step))
    rs = np.arange(0, rmax, 0.25)
    out = np.zeros(len(th))
    for i, t in enumerate(th):
        x = cx + rs * np.cos(t)
        y = cy - rs * np.sin(t)
        ok = (x >= 0) & (x <= W - 1.001) & (y >= 0) & (y <= H - 1.001)
        v = np.zeros_like(rs)
        v[ok] = L.bilinear(mask, x[ok], y[ok])
        inside = np.flatnonzero(v >= 0.5)
        out[i] = rs[inside[-1]] if len(inside) else 0
    return np.rad2deg(th), out

th, r = r_of_theta(m, cx, cy)
# periodicity
F = np.abs(np.fft.rfft(r - r.mean()))
k = int(np.argmax(F[1:40]) + 1)
print("centroid", cx, cy, "dominant harmonic", k, "top harmonics", np.argsort(F[1:40])[::-1][:5] + 1)
# extrema: split into k sectors around maxima
n = len(r)
per = n // k
# smooth
rs_ = np.convolve(np.concatenate([r[-20:], r, r[:20]]), np.ones(9) / 9, mode="same")[20:-20]
maxima = []
for i in range(n):
    w = rs_[[(i + j) % n for j in range(-per // 3, per // 3 + 1)]]
    if rs_[i] == w.max() and rs_[i] > np.median(rs_):
        if not maxima or (i - maxima[-1]) % n > per // 3:
            maxima.append(i)
minima = []
for a_, b_ in zip(maxima, maxima[1:] + [maxima[0] + n]):
    idx = [(j) % n for j in range(a_, b_)]
    minima.append(idx[int(np.argmin(rs_[idx]))])
tips = [dict(theta=float(th[i]), r=float(r[i]), x=float(cx + r[i] * np.cos(np.deg2rad(th[i]))),
             y=float(cy - r[i] * np.sin(np.deg2rad(th[i])))) for i in maxima]
notches = [dict(theta=float(th[i]), r=float(r[i]), x=float(cx + r[i] * np.cos(np.deg2rad(th[i]))),
                y=float(cy - r[i] * np.sin(np.deg2rad(th[i])))) for i in minima]
for t in tips:
    print("tip   th %7.2f r %7.2f  (%.1f, %.1f)" % (t["theta"], t["r"], t["x"], t["y"]))
for t in notches:
    print("notch th %7.2f r %7.2f  (%.1f, %.1f)" % (t["theta"], t["r"], t["x"], t["y"]))
json.dump(dict(mask=maskf, centroid=[cx, cy], harmonic=k, tips=tips, notches=notches),
          open(os.path.join(OUT, "coarse_%s.json" % os.path.splitext(maskf)[0]), "w"), indent=1)
np.save(os.path.join(OUT, "rtheta_%s.npy" % os.path.splitext(maskf)[0]), np.stack([th, r]))
