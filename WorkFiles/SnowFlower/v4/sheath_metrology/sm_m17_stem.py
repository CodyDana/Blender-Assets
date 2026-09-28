# sm_m17: stem width along the hand-read vine path (run of L>thr nearest the path x)
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a)
prof = np.array(json.load(open(os.path.join(HERE, "sm_s01.json")))["profile"])
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}
P = [(167,506),(193,527),(215,521),(250,510),(285,505),(322,508),(340,510),(370,495),(395,485),(430,478),(460,475),(495,486),(530,495),(560,505),(590,515),(625,528),(660,535),(693,525),(720,510),(745,495),(775,485),(800,481),(840,490),(875,510),(900,528),(920,533),(950,525),(980,515),(1010,507),(1040,505),(1077,495),(1110,490),(1140,488),(1170,490),(1200,500),(1230,510),(1245,517),(1262,510)]
P = np.array(P, float)
res = []
for thr in (0.33, 0.42):
    ws = []
    for y in range(170, 1262, 1):
        if 286 <= y <= 322: continue
        x = np.interp(y, P[:, 0], P[:, 1])
        m = L[y] > thr
        rs = [r for r in runs(m[400:620]) ]
        rs = [(s + 400, e + 400) for s, e in rs]
        best = None
        for s, e in rs:
            dist = 0 if s <= x <= e else min(abs(s - x), abs(e - x))
            if dist <= 4 and (best is None or dist < best[0]): best = (dist, s, e)
        if best: ws.append((y, best[2] - best[1] + 1, (best[1] + best[2]) / 2))
    ws = np.array(ws)
    print("thr", thr)
    for ya, yb in ((170, 286), (322, 460), (460, 700), (700, 900), (900, 1100), (1100, 1262)):
        sel = ws[(ws[:, 0] >= ya) & (ws[:, 0] < yb)]
        w = sel[:, 1]; w = w[w < 25]  # drop blossom rows
        l, r = edge[(ya + yb) // 2]
        print("  rows %4d-%4d  n %3d  width p25 %.1f  median %.1f  p75 %.1f   (body width %d)" % (ya, yb, len(w), np.percentile(w, 25), np.median(w), np.percentile(w, 75), r - l + 1))
        res.append(dict(thr=thr, rows=[ya, yb], median=float(np.median(w)), p25=float(np.percentile(w, 25)), p75=float(np.percentile(w, 75)), body=int(r - l + 1)))
json.dump(dict(path=P.tolist(), widths=res), open(os.path.join(HERE, "sm_s17.json"), "w"), indent=1)
# overlay path
dbg = a[..., :3].copy()
for y in range(167, 1262):
    x = int(round(np.interp(y, P[:, 0], P[:, 1]))); dbg[y, x] = (1, 0, 0)
save_png(dbg[150:1280, 440:575], "DEBUG_NEVER_SHIP_sheath_vine_path.png", 1)
