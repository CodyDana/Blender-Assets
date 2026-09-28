# sm_m01: sheath silhouette, per-row extents, axis fit, width profile
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *

a = load("sheath")
L = lum(a); S = sat(a)
H, W = L.shape
print("bg stats: lum corners", L[:20, :20].mean(), L[-20:, -20:].mean(), "min bg region", L[:, :300].min(), L[:, :300].mean())
for thr in (0.97, 0.95, 0.92, 0.90, 0.85):
    nw = L > thr
    bg = flood_bg(nw)
    fg = ~bg
    rows = np.where(fg.any(1))[0]; cols = np.where(fg.any(0))[0]
    print(f"thr {thr}: fg px {fg.sum()} rows {rows.min()}-{rows.max()} cols {cols.min()}-{cols.max()}")
thr = 0.92
bg = flood_bg(L > thr)
fg = ~bg
np.save(os.path.join(HERE, "sm_sheath_fg.npy"), fg)
prof = []
for y in range(H):
    r = runs(fg[y])
    if not r:
        continue
    # keep the widest run (drop specks)
    big = [q for q in r if q[1] - q[0] >= 2]
    if not big:
        continue
    l = big[0][0]; rr = big[-1][1]
    prof.append((y, l, rr, rr - l + 1, (l + rr) / 2, len(big)))
prof = np.array(prof, float)
y0, y1 = int(prof[0, 0]), int(prof[-1, 0])
print("top row", y0, "bottom row", y1, "length px", y1 - y0 + 1)
# print profile every 16 rows
for row in prof[::16]:
    print("y %4d  l %4d r %4d  w %4d  c %6.1f runs %d" % tuple(row))
# axis fit on body rows (exclude fittings rough: use rows 30%-85%)
n = len(prof)
sel = prof[(prof[:, 0] > y0 + 0.30 * (y1 - y0)) & (prof[:, 0] < y0 + 0.80 * (y1 - y0))]
k, b = np.polyfit(sel[:, 0], sel[:, 4], 1)
kl, bl = np.polyfit(sel[:, 0], sel[:, 1], 1)
kr, br = np.polyfit(sel[:, 0], sel[:, 2], 1)
print("centre line x = %.5f*y + %.2f  (tilt %.3f deg)" % (k, b, np.degrees(np.arctan(k))))
print("left edge slope %.5f right edge slope %.5f" % (kl, kr))
res = dict(threshold=thr, top=y0, bottom=y1, length_px=y1 - y0 + 1,
           centre_fit=[k, b], tilt_deg=float(np.degrees(np.arctan(k))),
           left_fit=[kl, bl], right_fit=[kr, br],
           profile=prof.tolist())
json.dump(res, open(os.path.join(HERE, "sm_s01.json"), "w"))
# debug overlay
dbg = a[..., :3].copy()
dbg[fg & (L > 0.8)] = dbg[fg & (L > 0.8)] * 0.5 + np.array([0, 0.5, 0.5])
for (y, l, r, w_, c, nr) in prof.astype(int)[::1]:
    dbg[y, l] = (1, 0, 0); dbg[y, r] = (1, 0, 0)
save_png(dbg, "DEBUG_NEVER_SHIP_sheath_silhouette.png")
