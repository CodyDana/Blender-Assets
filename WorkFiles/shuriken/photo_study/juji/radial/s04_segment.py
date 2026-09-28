"""Segment the Juji piece from the scanner background.

Background model: 2-D polynomial (degree 4) per RGB channel fitted to pixels judged background,
iterated 3 times (initial guess = border colour). Object evidence per pixel:
  dark  = bg_lum - lum         (object darker than local background)
  warm  = (R-B) - bg(R-B)      (object warmer / more saturated than neutral grey background)
  dist  = |rgb - bg_rgb|
Object = dist > T (T chosen from the border-noise distribution) after mild smoothing; brighter-
than-background halo pixels are excluded unless they are also warm.
Outputs arrays in seg.npz for later scripts plus PNG masks.
"""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
yy, xx = np.mgrid[0:H, 0:W]
xn = (xx - W / 2) / (W / 2)
yn = (yy - H / 2) / (H / 2)


def box_blur(img, r):
    """separable box blur via cumulative sums (edge-replicated)."""
    if r <= 0:
        return img.copy()
    k = 2 * r + 1
    p = np.pad(img, [(r, r), (r, r)] + [(0, 0)] * (img.ndim - 2), mode='edge')
    c = np.cumsum(p, axis=0, dtype=np.float64)
    c = np.concatenate([np.zeros_like(c[:1]), c], 0)
    v = (c[k:] - c[:-k]) / k
    c = np.cumsum(v, axis=1)
    c = np.concatenate([np.zeros_like(c[:, :1]), c], 1)
    return ((c[:, k:] - c[:, :-k]) / k).astype(np.float32)


def design(deg, x, y):
    cols = []
    for i in range(deg + 1):
        for j in range(deg + 1 - i):
            cols.append((x ** i) * (y ** j))
    return np.stack(cols, -1)


# initial background guess: border colour
B = 10
border = np.concatenate([a[:B].reshape(-1, 3), a[-B:].reshape(-1, 3), a[:, :B].reshape(-1, 3), a[:, -B:].reshape(-1, 3)])
med = np.median(border, 0)
dist0 = np.linalg.norm(a - med, axis=2)
bgmask = dist0 < 0.10
bgmask &= ~jlib.dilate(dist0 > 0.18, 15)

deg = 4
for it in range(4):
    idx = np.nonzero(bgmask.ravel())[0]
    sel = idx[:: max(1, len(idx) // 60000)]
    A = design(deg, xn.ravel()[sel], yn.ravel()[sel])
    bg = np.empty_like(a)
    Afull = design(deg, xn.ravel(), yn.ravel())
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, a[:, :, c].ravel()[sel], rcond=None)
        bg[:, :, c] = (Afull @ coef).reshape(H, W)
    res = a - bg
    dist = np.linalg.norm(res, axis=2)
    noise = np.percentile(dist[bgmask], [50, 90, 99, 99.9])
    print("iter", it, "bg px", bgmask.sum(), "resid pctl 50/90/99/99.9", noise)
    bgmask = (dist < max(0.05, 2.5 * noise[2])) & ~jlib.dilate(dist > 0.08, 12)

lum = a.mean(2)
bl = bg.mean(2)
dark = bl - lum
warm = (a[:, :, 0] - a[:, :, 2]) - (bg[:, :, 0] - bg[:, :, 2])
# smoothed evidence (JPEG noise): 3x3 box
dists = box_blur(dist, 1)
darks = box_blur(dark, 1)
warms = box_blur(warm, 1)

# noise-based threshold
bgn = dists[bgmask]
print("smoothed bg dist pct 99, 99.9, max", np.percentile(bgn, 99), np.percentile(bgn, 99.9), bgn.max())
T = 0.06
obj = (dists > T) & ((darks > 0.02) | (warms > 0.03))
obj = jlib.opening(obj, 2)
obj = jlib.closing(obj, 3)
obj = jlib.largest_component(obj)
filled, holes = jlib.fill_holes(obj)
print("object px", obj.sum(), "filled", filled.sum(), "enclosed holes px", holes.sum())
hl, nh = jlib.label(holes)
if nh:
    cnt = np.bincount(hl.ravel())[1:]
    print("hole components (px):", sorted(cnt.tolist(), reverse=True)[:10])

np.savez_compressed(os.path.join(jlib.OUT, "seg.npz"), bg=bg.astype(np.float32), dist=dists, dark=darks, warm=warms,
                    obj=obj, filled=filled, holes=holes)
jlib.save_png(os.path.join(jlib.OUT, "dbg_bgmodel.png"), bg)
jlib.save_png(os.path.join(jlib.OUT, "dbg_dist.png"), np.clip(dists * 4, 0, 1))
jlib.save_png(os.path.join(jlib.OUT, "dbg_bgmask.png"), bgmask)
jlib.save_png(os.path.join(jlib.OUT, "mask_v1.png"), filled)
