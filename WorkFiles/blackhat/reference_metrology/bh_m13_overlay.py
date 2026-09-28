"""Stage 13: overlay of the fitted camera model (d=2.6 R) on the reference: rim circle, cap edge, apex,
primary ribs every 30 deg from theta=7.5, lashings every 15 deg. LOOK check of camera + rib/lashing layout."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *; from bh_draw import *
key = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '2.6'
c = load('bh_s07_joint.json')[key]; d = float(key)
H, e, f, u0, v0, roll, rc = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg']), c['rc']
pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
def circ(r, z, t0=-180, t1=180, n=721):
    t = np.radians(np.linspace(t0, t1, n)); return np.stack([r * np.sin(t), -r * np.cos(t), np.full_like(t, z)], -1)
k = 2; img = upscale(stretch(load_srgb(), 0, 0.5), k).copy()
polyline(img, pr(circ(1.0, 0.0, -100, 100)), (0, 1, 0), k)          # outer rim (front)
polyline(img, pr(circ(1.0, 0.0, 100, 260)), (0, 0.5, 0), k)
polyline(img, pr(circ(rc, H * (1 - rc))), (1, 0, 1), k)               # cap edge
ap = pr([[0, 0, H]])[0]; dot(img, ap[0], ap[1], (1, 1, 0), k, 3)
for t in np.arange(7.5 - 180, 180, 30):
    a = np.radians(t); P = [[rho * np.sin(a), -rho * np.cos(a), H * (1 - rho)] for rho in (0.15, 0.97)]
    uv = pr(P)
    if abs(t) < 100: line(img, uv[0][0], uv[0][1], uv[1][0], uv[1][1], (1, 0, 0), k, 1)
for t in np.arange(-172.5, 180, 15):
    if abs(t) > 105: continue
    a = np.radians(t); uv = pr([[0.985 * np.sin(a), -0.985 * np.cos(a), -0.02]])[0]
    ring(img, uv[0], uv[1], (1, 1, 0), k, 7)
save_png(os.path.join(DBG, f'dbg_camera_model_overlay_d{key}.png'), img)
print('apex', ap)
