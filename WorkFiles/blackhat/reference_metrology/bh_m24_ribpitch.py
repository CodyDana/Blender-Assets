"""Stage 24: primary-rib azimuths (rib meets rim) re-derived for every camera distance; even-pitch fit -> implied rib count."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
J = load('bh_s07_joint.json')
def cam(key):
    c = J[key]; d = float(key)
    return c['H'], (lambda P, c=c, d=d: project(np.asarray(P, float), np.radians(c['e_deg']), d, c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])))
H0, p0 = cam('2.6')
ribs26 = np.array([-82, -54.5, -23.5, 7.6, 30, 58, 85.0])
lash26 = np.array([-53.7, -32.5, -22.1, -9.0, 7.65, 17.1, 42.75, 58.35])
def pts(th, H, pr, rho=0.95):
    t = np.radians(th); return pr(np.stack([rho * np.sin(t), -rho * np.cos(t), np.full_like(t, H * (1 - rho))], -1))
img_r = pts(ribs26, H0, p0); img_l = pts(lash26, H0, p0)
tt = np.arange(-120, 120, 0.02)
res = {}
for key in J:
    H, pr = cam(key)
    uvs = pts(tt, H, pr)
    def inv(uv):
        return np.array([tt[np.argmin(np.hypot(uvs[:, 0] - u, uvs[:, 1] - v))] for u, v in uv])
    th_r = inv(img_r); th_l = inv(img_l)
    k = np.arange(-3, 4); A = np.stack([np.ones(7), k], -1)
    coef, *_ = np.linalg.lstsq(A, th_r, rcond=None); rr = th_r - A @ coef
    res[key] = dict(ribs=np.round(th_r, 1).tolist(), pitch=float(coef[1]), phase=float(coef[0]), N=360 / coef[1], rms=float(np.sqrt(np.mean(rr ** 2))), lash=np.round(th_l, 1).tolist(),
                    cap_rms=J[key]['rms_cap'])
    # forced pitch fits
    for N in (12, 13):
        ph = np.mean(th_r - k * 360 / N); r2 = th_r - (ph + k * 360 / N); res[key][f'rms_N{N}'] = float(np.sqrt(np.mean(r2 ** 2))); res[key][f'phase_N{N}'] = float(ph)
    print(key, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in res[key].items()})
dump('bh_s24_ribpitch.json', res)
