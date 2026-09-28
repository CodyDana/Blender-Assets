"""Stage 21: wear map in unrolled cone space: pixels brighter than 1.8x the local (theta-column) p30 baseline smoothed at 6 deg."""
import sys, os, numpy as np, json, colorsys
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
lin = srgb_to_lin(load_srgb())
th = np.arange(-95, 95.001, 0.2); rho = np.arange(0.40, 0.975, 0.0025)
T, R = np.meshgrid(np.radians(th), rho)
uv = pr(np.stack([R * np.sin(T), -R * np.cos(T), H * (1 - R)], -1))
C = bilinear(lin, uv[..., 0], uv[..., 1]); L = C @ LW
valid = ~((th >= 18) & (th <= 70))[None, :].repeat(len(rho), 0)   # tails/knot excluded
p30 = np.percentile(L, 30, axis=0)
k = np.ones(31) / 31; base = np.convolve(np.pad(p30, 15, mode='edge'), k, 'valid')
ratio = L / base[None, :]
worn = (ratio > 1.8) & valid
print('worn fraction of visible straw (rho .40-.975, excl knot/tails):', round(float(worn.sum() / valid.sum()), 4))
# broad (smoothed) lightness map: 3 deg x 0.03 rho boxes
sm = box_blur(np.where(valid, L, np.nan_to_num(np.median(L))), 6) / base[None, :]
for (t0, t1, r0, r1) in [(-62, -25, 0.45, 0.97), (-45, -35, 0.55, 0.9), (-18, -5, 0.70, 0.82), (-5, 16, 0.45, 0.97), (72, 95, 0.45, 0.97)]:
    m = (th[None, :] >= t0) & (th[None, :] < t1) & (rho[:, None] >= r0) & (rho[:, None] < r1) & valid
    print(f'region th[{t0},{t1}] rho[{r0},{r1}] worn-frac {worn[m].mean():.3f} mean lin lum {L[m].mean():.4f} p50 {np.median(L[m]):.4f}')
w = C[worn]; m = w.mean(0); s = lin_to_srgb(m)
print('worn fleck mean lin', np.round(m, 4), 'srgb', np.round(s, 3), 'chroma', np.round(m / m.sum(), 3), 'hsv', np.round(colorsys.rgb_to_hsv(*s), 3), 'lum p50/p90', np.round(np.percentile(w @ LW, [50, 90]), 4))
nw = C[(~worn) & valid]; m2 = nw.mean(0); print('unworn straw mean lin', np.round(m2, 4), 'srgb', np.round(lin_to_srgb(m2), 3))
img = np.repeat(stretch(lin_to_srgb(L), 0, 0.45)[..., None], 3, 2)
img[worn] = img[worn] * 0.4 + np.array([1, 0.3, 0]) * 0.6
img[~valid] *= 0.35
save_png(os.path.join(DBG, 'dbg_wear_map_unrolled_orange.png'), upscale(img, 2))
np.save(os.path.join(D, 'bh_wear_mask_unrolled.npy'), worn)
