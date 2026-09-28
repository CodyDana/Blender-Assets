"""Stage 15: lashing azimuths from the theta-rectified rim face (z 0.004..0.04, camera d=2.6)."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(P, e, d, f, u0, v0, roll)
Lm = lum(load_srgb())
th = np.radians(np.arange(-105, 105.001, 0.05)); zs = np.arange(0.040, 0.0035, -0.0015)
T, Z = np.meshgrid(th, zs)
uv = pr(np.stack([np.sin(T), -np.cos(T), Z], -1))
S = bilinear(Lm, uv[..., 0], uv[..., 1])
save_png(os.path.join(DBG, 'dbg_rimface_theta_-105_105_x4rows.png'), np.repeat(stretch(S, 0, 0.45), 4, 0))
A = np.degrees(th)
g = np.abs(np.diff(S, axis=1)).mean(0); g = np.append(g, g[-1])
gs = np.convolve(g, np.ones(21) / 21, 'same')
base = np.array([np.median(gs[max(0, i - 300):i + 301]) for i in range(len(gs))])
sc = gs / base
pk = [i for i in range(30, len(sc) - 30) if sc[i] == sc[max(0, i - 60):i + 61].max() and sc[i] > 1.4]
res = []
for i in pk:
    # width: extent where sc > 0.5*(peak+1)
    lv = 0.5 * (sc[i] + 1); j0 = i; j1 = i
    while j0 > 0 and sc[j0] > lv: j0 -= 1
    while j1 < len(sc) - 1 and sc[j1] > lv: j1 += 1
    xy = pr(np.array([[np.sin(th[i]), -np.cos(th[i]), 0.02]]))[0]
    res.append(dict(theta=round(float(A[i]), 2), score=round(float(sc[i]), 2), width_deg=round(float(A[j1] - A[j0]), 2), img=[round(float(xy[0]), 1), round(float(xy[1]), 1)]))
    print(res[-1])
dump('bh_s15_lashings.json', res)
