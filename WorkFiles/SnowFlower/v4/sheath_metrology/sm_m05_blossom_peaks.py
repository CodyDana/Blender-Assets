# sm_m05: blossom/bud detection by bright-area density peaks, with size estimate; overlay for visual check
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a)
fg = np.load(os.path.join(HERE, "sm_sheath_fg.npy"))
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"]); top, bot = s01["top"], s01["bottom"]; Lpx = bot - top
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}
B = (fg & (L > 0.70)).astype(np.float32)
def boxmean(m, r):
    c = np.cumsum(np.cumsum(np.pad(m, ((r + 1, r), (r + 1, r))), 0), 1)
    k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
D = boxmean(B, 5)
peaks = []
H, W = D.shape
cand = np.argwhere(D > 0.30)
vals = D[cand[:, 0], cand[:, 1]]
order = np.argsort(-vals)
taken = np.zeros_like(D, bool)
for i in order:
    y, x = cand[i]
    if taken[max(0, y - 9):y + 10, max(0, x - 9):x + 10].any():
        continue
    taken[y, x] = True
    # size: radius at which ring-mean of B drops below 0.25
    rad = 0
    for r in range(3, 40):
        yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
        ring = (np.abs(np.hypot(yy, xx) - r) < 0.7)
        ys = np.clip(y + yy, 0, H - 1); xs = np.clip(x + xx, 0, W - 1)
        sub = B[ys, xs][ring]
        if sub.mean() < 0.25:
            rad = r; break
    l, rr = edge.get(int(y), (np.nan, np.nan))
    u = (x - (l + rr) / 2) / ((rr - l) / 2)
    peaks.append(dict(y=int(y), x=int(x), d=float(D[y, x]), r=int(rad), t=float((y - top) / Lpx), u=float(u)))
peaks.sort(key=lambda p: p["y"])
for p in peaks:
    print("y %4d x %4d t %.3f u %+.2f dens %.2f radius %2d" % (p["y"], p["x"], p["t"], p["u"], p["d"], p["r"]))
json.dump(peaks, open(os.path.join(HERE, "sm_s05.json"), "w"))
dbg = a[..., :3].copy()
for p in peaks:
    r = max(p["r"], 3)
    t = np.linspace(0, 2 * np.pi, 80)
    col = (1, 0, 0) if r >= 12 else ((0, 0.8, 0) if r >= 7 else (0, 0.4, 1))
    ys = np.clip((p["y"] + r * np.sin(t)).astype(int), 0, H - 1); xs = np.clip((p["x"] + r * np.cos(t)).astype(int), 0, W - 1)
    dbg[ys, xs] = col
save_png(dbg[0:760, 420:600], "DEBUG_NEVER_SHIP_sheath_blossoms_top.png", 2)
save_png(dbg[750:1510, 420:600], "DEBUG_NEVER_SHIP_sheath_blossoms_bottom.png", 2)
