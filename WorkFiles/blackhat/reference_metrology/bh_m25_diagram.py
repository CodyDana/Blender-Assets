"""Stage 25: DEBUG, NEVER SHIP - labelled layout diagram: fitted camera d=2.6 R; measured primary ribs (red),
designed far-side continuation not visible; rib lashings (yellow rings), bay lashings (orange rings); band ring rho .365 (cyan);
knot (magenta); tail rim crossings (green); cap edge (violet)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *; from bh_draw import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll, rc = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg']), c['rc']
pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
def cp(t, r, dz=0.0): t = np.radians(t); return [r * np.sin(t), -r * np.cos(t), H * (1 - r) + dz]
k = 2; img = upscale(stretch(load_srgb(), 0, 0.5), k).copy() * 0.8 + 0.2
ribs = [-82, -54.5, -23.5, 7.6, 30, 58, 85]
for t in ribs:
    uv = pr([cp(t, 0.12), cp(t, 0.95)]); line(img, *uv[0], *uv[1], (1, 0, 0), k, 1)
for t in [-53.7, -22.1, 7.65, 30.0, 58.35]:
    uv = pr([[np.sin(np.radians(t)), -np.cos(np.radians(t)), 0.02]])[0]; ring(img, *uv, (1, 0.9, 0), k, 8)
for t in [-67.0, -32.5, -9.0, 17.1, 42.75]:
    uv = pr([[np.sin(np.radians(t)), -np.cos(np.radians(t)), 0.02]])[0]; ring(img, *uv, (1, 0.5, 0), k, 8)
band = pr([cp(t, 0.365, 0.005) for t in np.arange(-85, 90, 1)]); polyline(img, band, (0, 0.9, 1), k)
cap = pr([cp(t, rc, 0.008) for t in np.arange(-180, 181, 2)]); polyline(img, cap, (0.6, 0.3, 1), k)
kn = pr([cp(61, 0.43)])[0]; ring(img, *kn, (1, 0, 1), k, 18)
for t in (31, 40):
    uv = pr([[1.02 * np.sin(np.radians(t)), -1.02 * np.cos(np.radians(t)), 0.0]])[0]; dot(img, *uv, (0, 1, 0), k, 5)
dot(img, 592, 533, (0, 1, 0), k, 5); dot(img, 643, 520, (0, 1, 0), k, 5)
# wear-zone boxes (cone space outlines)
for (t0, t1, r0, r1) in [(-62, -25, 0.45, 0.97), (72, 95, 0.45, 0.97)]:
    pts = [cp(t, r0) for t in np.arange(t0, t1 + 1, 1)] + [cp(t1, r) for r in np.arange(r0, r1, 0.01)] + [cp(t, r1) for t in np.arange(t1, t0 - 1, -1)] + [cp(t0, r) for r in np.arange(r1, r0, -0.01)]
    polyline(img, pr(pts), (1, 1, 1), k)
save_png(os.path.join(DBG, 'DEBUG_NEVER_SHIP_bh_layout_LABELLED.png'), img)
