# sm_m03: facet lines from metal-masked lacquer, in silhouette-relative u (-1 left edge .. +1 right edge)
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a)
prof = np.array(json.load(open(os.path.join(HERE, "sm_s01.json")))["profile"])
metal = L > 0.42
m = metal.copy()
for _ in range(3):
    g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; m = g
N = 193
res = {}
for (ya, yb) in [(340, 700), (700, 1000), (1000, 1250), (340, 1250)]:
    acc = []
    for y in range(ya, yb):
        r = prof[prof[:, 0] == y][0]; l, rr = int(r[1]), int(r[2])
        seg = L[y, l:rr + 1].astype(float).copy(); mk = m[y, l:rr + 1]
        seg[mk] = np.nan
        xs = np.linspace(0, len(seg) - 1, N)
        # nearest sample to keep NaN
        acc.append(seg[np.round(xs).astype(int)])
    acc = np.array(acc)
    med = np.nanmedian(acc, 0)
    cnt = np.isfinite(acc).sum(0)
    res[f"{ya}-{yb}"] = med.tolist()
    print(f"rows {ya}-{yb}")
    for i in range(0, N, 3):
        u = -1 + 2 * i / (N - 1)
        print("  u %+.3f %.3f n%4d %s" % (u, med[i], cnt[i], "#" * int(np.nan_to_num(med[i]) * 150)))
json.dump(res, open(os.path.join(HERE, "sm_s03.json"), "w"))
