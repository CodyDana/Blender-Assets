"""Debug: polar unwrap (r 120..400) with phi ticks every 1 deg (short) / 5 deg (long, red) / 10 deg (yellow)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
pol = np.load(os.path.join(D, 'bh_polar.npy'))
rs = np.arange(0, 420, 0.5); phis = np.linspace(-66, 66, 1321)
a, b = sys.argv[sys.argv.index('--') + 1:][:2]; a = float(a); b = float(b)
cols = (phis >= a) & (phis <= b); rows = (rs >= 120) & (rs < 400)
g = stretch(pol[np.ix_(rows, cols)], 0, 0.45)
img = np.repeat(g[..., None], 3, 2)
img = np.concatenate([np.ones((40, img.shape[1], 3)), img], 0)
ph = phis[cols]
for j, p in enumerate(ph):
    q = round(p * 10)
    if q % 10 == 0:
        L = 12; col = (0, 0, 0)
        if q % 50 == 0: L = 25; col = (1, 0, 0)
        if q % 100 == 0: L = 40; col = (0.9, 0.7, 0)
        img[40 - L:40, j] = col
img = upscale(img, 2)
save_png(os.path.join(DBG, f'dbg_polar_ticks_{int(a)}_{int(b)}.png'), img)
