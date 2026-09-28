"""Stage 22: two-light + ambient Lambert fit on the straw azimuth profile (p30) and rim-tube azimuth profile."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
J = load('bh_s20_colour_light.json'); H = load('bh_s07_joint.json')['2.6']['H']
c = load('bh_s07_joint.json')['2.6']; d = 2.6
e, f, u0, v0, roll = np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
lin = srgb_to_lin(load_srgb()); L = lin @ LW
prof = J['straw_theta_profile']
t = np.radians([p[0] for p in prof]); I = np.array([p[1] for p in prof])
N1 = np.stack([H * np.sin(t), -H * np.cos(t), np.ones_like(t)], -1) / np.sqrt(1 + H * H)
# rim tube: outer face normal ~ horizontal outward tilted 20 deg down-ish -> use outward horizontal (sin, -cos, 0) rotated up 20
rim = []
for td in range(-80, 81, 5):
    if 20 <= td <= 50: continue
    tr = np.radians(td); zs = np.linspace(0.008, 0.035, 8)
    uv = pr(np.stack([np.full(8, np.sin(tr)), np.full(8, -np.cos(tr)), zs], -1))
    v = bilinear(L, uv[:, 0], uv[:, 1]); rim.append((td, float(np.percentile(v, 50))))
print('rim tube lin lum vs theta', [(a, round(b, 4)) for a, b in rim])
t2 = np.radians([a for a, b in rim]); I2 = np.array([b for a, b in rim])
N2 = np.stack([np.sin(t2) * 0.94, -np.cos(t2) * 0.94, np.full_like(t2, 0.34)], -1)
def ldir(az, el):
    a, b = np.radians(az), np.radians(el); return np.array([np.sin(a) * np.cos(b), -np.cos(a) * np.cos(b), np.sin(b)])
dirs = [(az, el) for az in range(-180, 180, 15) for el in range(0, 76, 15)]
Ls = np.array([ldir(*q) for q in dirs])
S1 = np.maximum(0, N1 @ Ls.T); S2 = np.maximum(0, N2 @ Ls.T)
best = None
for i in range(len(dirs)):
    for j in range(i + 1, len(dirs)):
        A1 = np.stack([np.ones(len(t)), S1[:, i], S1[:, j], np.zeros(len(t))], -1)
        A2 = np.stack([np.ones(len(t2)), S2[:, i], S2[:, j], np.ones(len(t2))], -1)   # rim gets its own albedo offset term
        A = np.vstack([A1, A2]); y = np.concatenate([I, I2])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        if coef[1] < 0 or coef[2] < 0 or coef[0] < 0: continue
        r = y - A @ coef; sse = r @ r
        if best is None or sse < best[0]: best = (sse, dirs[i], dirs[j], coef)
sse, d1, d2, coef = best
y = np.concatenate([I, I2]); r2 = 1 - sse / ((y - y.mean()) ** 2).sum()
print('two-light fit: L1', d1, 'L2', d2, 'amb', round(coef[0], 4), 'k1', round(coef[1], 4), 'k2', round(coef[2], 4), 'rim offset', round(coef[3], 4), 'R2', round(float(r2), 3))
dump('bh_s22_light2.json', dict(L1=d1, L2=d2, amb=coef[0], k1=coef[1], k2=coef[2], R2=float(r2), rim_profile=rim))
