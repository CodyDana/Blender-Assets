"""Debug: rim strip pieces, depth x3, angle ticks each 1 deg (red 5, yellow 10)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
strip = np.load(os.path.join(D, 'bh_rimstrip.npy')); A = np.load(os.path.join(D, 'bh_rim_genergy.npy'))[0]
a0, a1 = map(float, sys.argv[sys.argv.index('--') + 1:][:2])
c = (A >= a0) & (A <= a1)
g = stretch(strip[:, c], 0, 0.45); g = np.repeat(g, 3, 0)
img = np.repeat(g[..., None], 3, 2); img = np.concatenate([np.ones((30, img.shape[1], 3)), img], 0)
for j, a in enumerate(A[c]):
    q = round(a * 10)
    if q % 10 == 0:
        L, col = 8, (0, 0, 0)
        if q % 50 == 0: L, col = 18, (1, 0, 0)
        if q % 100 == 0: L, col = 30, (0.9, 0.7, 0)
        img[30 - L:30, j] = col
save_png(os.path.join(DBG, f'dbg_rimstrip_{int(a0)}_{int(a1)}.png'), upscale(img, 2))
