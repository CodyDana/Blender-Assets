"""Stage 1: silhouette mask, per-column top/bottom subpixel outlines, backdrop shadow check."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
im = load_srgb(); H, W = im.shape[:2]
L = lum(im)
bg = 0.9960; obj = float(np.median(L[L < 0.5]))
thr = 0.5 * (bg + obj)
mask = L < thr
print("obj median lum", obj, "thr", thr, "mask px", mask.sum())
np.save(os.path.join(D, 'bh_mask.npy'), mask)
top = np.full(W, np.nan); bot = np.full(W, np.nan)
for x in range(W):
    col = L[:, x]; idx = np.where(col < thr)[0]
    if len(idx) == 0: continue
    y = idx[0]   # first below threshold going down; subpixel between y-1 and y
    if y > 0:
        a, b = col[y - 1], col[y]; top[x] = (y - 1) + (a - thr) / (a - b)
    y = idx[-1]
    if y < H - 1:
        a, b = col[y], col[y + 1]; bot[x] = y + (thr - a) / (b - a)
np.save(os.path.join(D, 'bh_top.npy'), top); np.save(os.path.join(D, 'bh_bot.npy'), bot)
xs = np.where(~np.isnan(top))[0]
print("x extent", xs.min(), xs.max())
ys = np.where(mask.any(1))[0]; print("y extent", ys.min(), ys.max())
for x in list(range(0, W, 20)) + [xs.min(), xs.max()]:
    print(x, round(float(top[x]), 2) if not np.isnan(top[x]) else None, round(float(bot[x]), 2) if not np.isnan(bot[x]) else None)
# leftmost / rightmost points
for x in [xs.min(), xs.max()]:
    yy = np.where(mask[:, x])[0]; print("tip col", x, yy.min(), yy.max())
# shadow check: pixels well away from the object (dilate by 6 px) below the rim
from numpy.lib.stride_tricks import sliding_window_view
pad = np.pad(mask, 8)
dil = sliding_window_view(pad, (17, 17)).any(axis=(2, 3))
far = ~dil
vals = L[far]
print("bg far: n", vals.size, "min", vals.min(), "p0.1", np.percentile(vals, 0.1), "p1", np.percentile(vals, 1), "mean", vals.mean())
# band just below rim bottom: rows bot+10..bot+40 in columns 100..500
sh = []
for x in range(60, 520, 10):
    b = int(bot[x]); sh.append(L[b + 10:b + 40, x].mean())
print("below-rim mean lum", np.round(sh, 4).tolist())
# darkest far-bg pixels location
yy, xx = np.where(far & (L < 0.985)); print("far px <0.985:", len(yy), list(zip(xx[:20].tolist(), yy[:20].tolist())))
