"""Stage 14: theta-rectified rim face (camera d=2.6 R) -> lashing azimuths, widths; rib azimuths at rho=0.8.
Rim face sampled on the cylinder r=1.0, z from +0.05 (above the cone edge) down to -0.06."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(P, e, d, f, u0, v0, roll)
Lm = lum(load_srgb())
th = np.radians(np.arange(-105, 105.001, 0.1)); zs = np.arange(0.05, -0.065, -0.0025)
T, Z = np.meshgrid(th, zs)
P = np.stack([np.sin(T), -np.cos(T), Z], -1)
uv = pr(P)
strip = bilinear(Lm, uv[..., 0], uv[..., 1])
np.save(os.path.join(D, 'bh_rim_theta_strip.npy'), strip)
img = stretch(strip, 0, 0.45); img = np.repeat(img[..., None], 3, 2)
img = np.concatenate([np.ones((20, img.shape[1], 3)), img], 0)
A = np.degrees(th)
for j, a in enumerate(A):
    q = round(a * 10)
    if q % 50 == 0: img[20 - (18 if q % 150 == 0 else 8):20, j] = (1, 0, 0) if q % 150 == 0 else (0, 0, 0)
save_png(os.path.join(DBG, 'dbg_rim_theta_strip_ticks15deg_red.png'), upscale(img, 2))
# px per degree at the front (for widths)
p0 = pr(np.array([[np.sin(0), -np.cos(0), 0]]))[0]; p1 = pr(np.array([[np.sin(np.radians(1)), -np.cos(np.radians(1)), 0]]))[0]
print('px per deg at front', np.hypot(*(p1 - p0)), 'image scale px per R at front', np.hypot(*(p1 - p0)) * 180 / np.pi)
# face rows: which z rows are rim face? print mean lum per z row at front
print('row z mean', [(round(z, 4), round(float(strip[i, 900:1200].mean()), 3)) for i, z in enumerate(zs)])
