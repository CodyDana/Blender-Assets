"""Stage 19: tails below the rim outline - per-row dark runs (x ranges), tip points, widths."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
Lm = lum(load_srgb()); mask = Lm < 0.58
bot = np.load(os.path.join(D, 'bh_bot.npy'))
# rim bottom outline without tails: interpolate the smooth rim ellipse from the fit outline near x 520..664
A, rr, sm = np.load(os.path.join(D, 'bh_radial_outline.npy'))
runs = {}
for y in range(360, 540, 4):
    xs = np.where(mask[y, 500:670])[0] + 500
    if not len(xs): continue
    segs = []; s = xs[0]; p = xs[0]
    for x in xs[1:]:
        if x != p + 1: segs.append((s, p)); s = x
        p = x
    segs.append((s, p)); runs[y] = segs
    print(y, segs)
ys, xs = np.where(mask); sel = xs > 500
iy = np.argmax(ys * sel); print('lowest dark pixel', xs[iy], ys[iy])
# lowest point per tail: split by x < 615 or >= 615 below y 470
for nm, (a, b) in dict(tailA=(540, 612), tailB=(612, 670)).items():
    m = mask[:, a:b]; yy, xx = np.where(m); i = np.argmax(yy); print(nm, 'tip', xx[i] + a, yy[i])
