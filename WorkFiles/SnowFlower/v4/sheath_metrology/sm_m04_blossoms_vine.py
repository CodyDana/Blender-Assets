# sm_m04: blossoms (bright blobs) and the vine path/stem width
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
a = load("sheath"); L = lum(a)
fg = np.load(os.path.join(HERE, "sm_sheath_fg.npy"))
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"]); top, bot = s01["top"], s01["bottom"]; Lpx = bot - top
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}

def label(mask):
    H, W = mask.shape
    lab = -np.ones(mask.shape, int)
    ys, xs = np.nonzero(mask)
    idx = {}
    parent = list(range(len(ys)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, (y, x) in enumerate(zip(ys, xs)):
        idx[(y, x)] = i
    for i, (y, x) in enumerate(zip(ys, xs)):
        for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
            j = idx.get((y + dy, x + dx))
            if j is not None:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
    comps = {}
    for i, (y, x) in enumerate(zip(ys, xs)):
        comps.setdefault(find(i), []).append((y, x))
    return list(comps.values())

bright = fg & (L > 0.80)
comps = label(bright)
blobs = []
for c in comps:
    c = np.array(c)
    if len(c) < 25:
        continue
    y0, x0 = c.min(0); y1, x1 = c.max(0)
    cy, cx = c.mean(0)
    blobs.append(dict(n=len(c), cy=float(cy), cx=float(cx), y0=int(y0), y1=int(y1), x0=int(x0), x1=int(x1),
                      h=int(y1 - y0 + 1), w=int(x1 - x0 + 1), t=float((cy - top) / Lpx)))
blobs.sort(key=lambda b: b["cy"])
print("bright blobs (L>0.80, >=25px):", len(blobs))
for b in blobs:
    l, r = edge[int(round(b["cy"]))]
    u = (b["cx"] - (l + r) / 2) / ((r - l) / 2)
    b["u"] = float(u)
    print("  y %6.1f x %6.1f t %.3f u %+.2f  n %4d  box %3dx%3d  [%d-%d, %d-%d]" % (b["cy"], b["cx"], b["t"], u, b["n"], b["w"], b["h"], b["y0"], b["y1"], b["x0"], b["x1"]))
# vine: metal pixels (L>0.45) inside |u|<0.85, per row runs
vine = []
for y in range(335, 1270):
    l, r = edge[y]; c = (l + r) / 2; hw = (r - l) / 2
    xa, xb = int(np.ceil(c - 0.85 * hw)), int(np.floor(c + 0.85 * hw))
    m = L[y, xa:xb + 1] > 0.45
    rs = [(s + xa, e + xa) for s, e in runs(m) if e - s + 1 >= 2]
    vine.append((y, [(s, e, round(float((((s + e) / 2) - c) / hw), 3)) for s, e in rs]))
json.dump(dict(blobs=blobs, vine=vine), open(os.path.join(HERE, "sm_s04.json"), "w"))
for y, rs in vine[::8]:
    print(y, [(s, e, e - s + 1, u) for s, e, u in rs])
# debug overlay
dbg = a[..., :3].copy() * 0.6
dbg[bright] = (1, 0.2, 0.8)
for b in blobs:
    dbg[b["y0"]:b["y1"] + 1, b["x0"]] = (0, 1, 0); dbg[b["y0"]:b["y1"] + 1, b["x1"]] = (0, 1, 0)
    dbg[b["y0"], b["x0"]:b["x1"] + 1] = (0, 1, 0); dbg[b["y1"], b["x0"]:b["x1"] + 1] = (0, 1, 0)
save_png(dbg[0:1510, 400:620], "DEBUG_NEVER_SHIP_sheath_blossoms.png", 1)
