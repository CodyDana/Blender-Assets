# sm_m02: tone histograms (lacquer vs metal), facet lines across the body
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a); S = sat(a)
fg = np.load(os.path.join(HERE, "sm_sheath_fg.npy"))
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"])
out = {}
# --- global tone histogram of the body window (rows 340-1250), inner 80% of width
def inner(y, frac=0.9):
    r = prof[prof[:, 0] == y][0]
    l, rr = r[1], r[2]; c = (l + rr) / 2; hw = (rr - l) / 2 * frac
    return int(np.ceil(c - hw)), int(np.floor(c + hw))
vals = []
for y in range(340, 1250):
    l, r = inner(y)
    vals.append(L[y, l:r + 1])
v = np.concatenate(vals)
qs = [1, 5, 10, 25, 50, 75, 90, 95, 99]
out["body_lum_percentiles"] = {q: float(np.percentile(v, q)) for q in qs}
h, e = np.histogram(v, bins=40, range=(0, 1))
print("body lum percentiles", out["body_lum_percentiles"])
for i in range(40):
    print("%.3f-%.3f %7d %s" % (e[i], e[i + 1], h[i], "#" * int(60 * h[i] / h.max())))
# RGB of darkest/median lacquer and colour cast
body_rgb = np.concatenate([a[y, inner(y)[0]:inner(y)[1] + 1, :3] for y in range(340, 1250)])
bl = lum(body_rgb)
for lo, hi, nm in [(0, 0.15, "lacquer_dark"), (0.15, 0.3, "lacquer_mid"), (0.3, 0.45, "lacquer_vein_or_sheen"), (0.5, 0.75, "metal_mid"), (0.8, 1.01, "metal_bright")]:
    m = (bl >= lo) & (bl < hi)
    if m.sum():
        c = body_rgb[m].mean(0)
        out["rgb_" + nm] = dict(frac=float(m.mean()), mean_rgb=c.tolist(), sat=float(sat(body_rgb[m]).mean()))
        print(nm, "frac %.3f" % m.mean(), "rgb", np.round(c, 3), "sat %.3f" % sat(body_rgb[m]).mean())
# --- column median profile in bands, in coordinates relative to silhouette (u in [-1,1])
nb = 24
bands = {}
for y0 in range(340, 1250, 60):
    rows = range(y0, y0 + 60)
    acc = []
    for y in rows:
        r = prof[prof[:, 0] == y][0]
        l, rr = int(r[1]), int(r[2])
        seg = L[y, l:rr + 1]
        # resample to 97 samples across the width
        xs = np.linspace(0, len(seg) - 1, 97)
        acc.append(np.interp(xs, np.arange(len(seg)), seg))
    acc = np.array(acc)
    med = np.median(acc, 0)
    bands[y0] = med
# average median profile over all bands
allmed = np.median(np.array(list(bands.values())), 0)
out["median_profile_across_width_97"] = allmed.tolist()
print("median profile across width (u from -1..1):")
for i in range(0, 97, 2):
    u = -1 + 2 * i / 96
    print("u %+.3f  %.3f %s" % (u, allmed[i], "#" * int(allmed[i] * 120)))
# facet-line detection per row: gradient of row-median (7 rows) in absolute px
lines = []
for y in range(340, 1250, 10):
    blk = L[y - 3:y + 4]
    med = np.median(blk, 0)
    r = prof[prof[:, 0] == y][0]; l, rr = int(r[1]), int(r[2])
    seg = med[l:rr + 1]
    g = np.abs(np.diff(seg))
    # darkest thin lines: local minima well below neighbours
    cand = []
    for i in range(3, len(seg) - 3):
        if seg[i] <= seg[i - 1] and seg[i] <= seg[i + 1]:
            depth = min(seg[i - 3:i].max(), seg[i + 1:i + 4].max()) - seg[i]
            if depth > 0.03:
                cand.append((l + i, round(float(depth), 3)))
    lines.append((y, l, rr, cand))
json.dump(dict(out=out, lines=lines), open(os.path.join(HERE, "sm_s02.json"), "w"), indent=0, default=float)
for y, l, rr, cand in lines[::3]:
    print(y, l, rr, [(c[0] - l, c[1]) for c in cand])
