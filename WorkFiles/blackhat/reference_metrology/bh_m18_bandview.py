"""Debug: unrolled cone (theta -100..100, rho 0.25..0.60) x2 with rho ticks every 0.05 (cyan) and theta ticks 10 deg (red)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
S = np.load(os.path.join(D, 'bh_cone_theta_rho.npy')); th = np.arange(-100, 100.001, 0.1); rho = np.arange(0.10, 1.001, 0.0025)
r = (rho >= 0.25) & (rho <= 0.60)
img = np.repeat(stretch(S[r], 0, 0.4)[..., None], 3, 2)
for i, v in enumerate(rho[r]):
    q = round(v * 400)
    if q % 20 == 0: img[i, :15] = (0, 0.8, 1); img[i, -15:] = (0, 0.8, 1)
img = np.concatenate([np.ones((12, img.shape[1], 3)), img], 0)
for j, a in enumerate(th):
    q = round(a * 10)
    if q % 100 == 0: img[:12, j] = (1, 0, 0)
img = upscale(img, 2)
save_png(os.path.join(DBG, 'dbg_band_unrolled_rho025_060.png'), img[:, :2000])
save_png(os.path.join(DBG, 'dbg_band_unrolled_rho025_060_right.png'), img[:, 2000:])
