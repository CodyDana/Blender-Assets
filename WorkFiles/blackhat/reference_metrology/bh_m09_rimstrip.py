"""Stage 9: rectify the rim band along the outline (angle about the rim-ellipse centre, depth inward), find lashings."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
Lm = lum(load_srgb())
A, rr, sm = np.load(os.path.join(D, 'bh_radial_outline.npy'))
cx, cy = 333.0, 330.0
# smooth the outline more strongly (tails excluded by median of wide window)
sm2 = np.array([np.nanmedian(sm[max(0, i - 60):i + 61]) for i in range(len(sm))])
depths = np.arange(-2, 40, 0.5)
a = np.radians(A)
# local outward normal from the smoothed outline
X = cx + sm2 * np.cos(a); Y = cy + sm2 * np.sin(a)
tx = np.gradient(X); ty = np.gradient(Y); n = np.hypot(tx, ty); tx /= n; ty /= n
nx, ny = ty, -tx   # rotate tangent; pick sign so it points outward
sgn = np.sign((X - cx) * nx + (Y - cy) * ny); nx *= sgn; ny *= sgn
XX = X[None, :] - depths[:, None] * nx[None, :]; YY = Y[None, :] - depths[:, None] * ny[None, :]
strip = bilinear(Lm, XX, YY)
np.save(os.path.join(D, 'bh_rimstrip.npy'), strip); np.save(os.path.join(D, 'bh_rimstrip_xy.npy'), np.stack([XX, YY]))
img = stretch(strip, 0, 0.45)
save_png(os.path.join(DBG, 'dbg_rimstrip_raw.png'), upscale(img, 1))
# tangential gradient energy averaged over depth 4..22 (rim face)
sel = (depths >= 3) & (depths <= 24)
g = np.abs(np.gradient(strip, axis=1))[sel].mean(0)
np.save(os.path.join(D, 'bh_rim_genergy.npy'), np.stack([A, g, X, Y]))
def movavg(v, w): return np.convolve(v, np.ones(w) / w, 'same')
gs = movavg(g, 15); base = np.array([np.median(gs[max(0, i - 80):i + 81]) for i in range(len(gs))])
score = gs / base
pk = [i for i in range(10, len(g) - 10) if score[i] == score[max(0, i - 25):i + 26].max() and score[i] > 1.35]
for i in pk:
    print(f'lash? ang {A[i]:7.1f} score {score[i]:4.2f} at ({X[i]:6.1f},{Y[i]:6.1f})')
