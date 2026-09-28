import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
sil = np.load(DBG + "/fb_sil.npy")
VIEWS = dict(v1=(40, 345, 157), v2=(345, 615, 468), v3=(615, 950, 745), v4=(950, 1240, 1103))
res = {}
for v, (x0, x1, xc) in VIEWS.items():
    rows = {}
    for y in range(30, 721):
        r = sil[y, x0:x1]
        if not r.any(): continue
        xs = np.nonzero(r)[0] + x0
        # run containing xc
        if sil[y, xc]:
            a = xc
            while a > x0 and sil[y, a-1]: a -= 1
            b = xc
            while b < x1-1 and sil[y, b+1]: b += 1
            run = (int(a), int(b))
        else: run = None
        rows[y] = dict(env=(int(xs.min()), int(xs.max())), run=run)
    res[v] = rows
    print(v, "top y", min(rows), "bottom", max(rows))
    for y in range(30, 721, 6):
        if y in rows: print(v, y, rows[y]['env'], rows[y]['run'])
json.dump({v: {str(k): d for k, d in r.items()} for v, r in res.items()}, open(DBG + "/fb_extents.json", "w"))
