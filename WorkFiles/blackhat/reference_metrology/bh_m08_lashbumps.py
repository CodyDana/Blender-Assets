"""Stage 8: lashing bumps on the silhouette: outline radius about the rim-ellipse centre vs a smooth fit."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
mask = np.load(os.path.join(D, 'bh_mask.npy')); Lm = lum(load_srgb())
cx, cy = 333.0, 330.0
# radial outline, only lower half + sides (image angle from +x, measured clockwise i.e. downward positive)
angs = np.radians(np.arange(-40, 220.01, 0.1))
thr = 0.58
rr = []
for a in angs:
    dx, dy = np.cos(a), np.sin(a)
    rs = np.arange(40, 420, 0.25)
    xs = cx + rs * dx; ys = cy + rs * dy
    ok = (xs >= 0) & (xs < 669) & (ys >= 0) & (ys < 598)
    v = bilinear(Lm, xs, ys); v[~ok] = 1
    idx = np.where(v >= thr)[0]
    # last crossing from dark to light starting inside
    j = idx[0] if len(idx) else len(rs) - 1
    rr.append(rs[j - 1] + (thr - v[j - 1]) / (v[j] - v[j - 1] + 1e-9) * 0.25 if j > 0 else np.nan)
rr = np.array(rr); A = np.degrees(angs)
# smooth: rolling median 6 deg
sm = np.array([np.nanmedian(rr[max(0, i - 30):i + 31]) for i in range(len(rr))])
bump = rr - sm
np.save(os.path.join(D, 'bh_radial_outline.npy'), np.stack([A, rr, sm]))
pk = [i for i in range(5, len(rr) - 5) if bump[i] == np.nanmax(bump[max(0, i - 15):i + 16]) and bump[i] > 0.9]
for i in pk:
    x = cx + rr[i] * np.cos(angs[i]); y = cy + rr[i] * np.sin(angs[i])
    print(f'ang {A[i]:7.1f} bump {bump[i]:5.2f} at ({x:6.1f},{y:6.1f})')
