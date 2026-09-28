"""Stage 16: cone skin rectified to (theta, rho) with the d=2.6 camera; rib azimuths; debug image."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(P, e, d, f, u0, v0, roll)
Lm = lum(load_srgb())
th = np.radians(np.arange(-100, 100.001, 0.1)); rho = np.arange(0.10, 1.001, 0.0025)
T, Rh = np.meshgrid(th, rho)
uv = pr(np.stack([Rh * np.sin(T), -Rh * np.cos(T), H * (1 - Rh)], -1))
S = bilinear(Lm, uv[..., 0], uv[..., 1])
np.save(os.path.join(D, 'bh_cone_theta_rho.npy'), S)
img = np.repeat(stretch(S, 0, 0.45)[..., None], 3, 2)
img = np.concatenate([np.ones((16, img.shape[1], 3)), img], 0)
A = np.degrees(th)
for j, a in enumerate(A):
    q = round(a * 10)
    if q % 50 == 0: img[16 - (14 if q % 300 == 0 else 6):16, j] = (1, 0, 0) if q % 300 == 0 else (0, 0, 0)
for i, r in enumerate(rho):
    q = round(r * 400)
    if q % 40 == 0: img[16 + i, :8] = (0, 0.8, 1)
save_png(os.path.join(DBG, 'dbg_cone_unrolled_theta_rho_d2.6.png'), img)
# rib detection: rows rho 0.62..0.9 (below band, above rim)
sel = (rho >= 0.62) & (rho <= 0.90)
prof = S[sel].mean(0)
hp = prof - np.convolve(prof, np.ones(41) / 41, 'same')
for nm, s in (('bright', hp), ('dark', -hp)):
    pk = [i for i in range(25, len(s) - 25) if s[i] == s[max(0, i - 15):i + 16].max() and s[i] > 0.008]
    print(nm, [(round(float(A[i]), 1), round(float(s[i]), 3)) for i in pk])
