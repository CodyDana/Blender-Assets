import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); sil = np.load(DBG + "/fb_sil_clean.npy")
g = ref[..., 1] - 0.5*(ref[..., 0] + ref[..., 2]); L = lum(ref)
res = {}
def runs_right(y, xa, xb):
    r = sil[y, xa:xb]; xs = np.nonzero(r)[0]
    if len(xs) == 0: return None
    # first run starting at/after xa
    s = xs[0]; e = s
    while e+1 < len(r) and r[e+1]: e += 1
    return [int(xa+s), int(xa+e)]
# v1: lever right of body limb (247); rows 100..580. Above 290 the ring overlaps - report and flag
v1 = []
for y in range(100, 590):
    rr = runs_right(y, 252, 340)
    if rr: v1.append([y] + rr)
res['v1_rows_y_xl_xr'] = v1
v3 = []
for y in range(90, 560):
    rr = runs_right(y, 836, 900) if y > 140 else runs_right(y, 800, 900)
    if rr: v3.append([y] + rr)
res['v3_rows_y_xl_xr'] = v3
# v4: lever over body: non-green run containing x=1160 between 1118..1190 for y 140..565 ; above 140 use silhouette right edge + visual left edge
v4 = []
for y in range(138, 566):
    p = g[y, 1110:1195]; st = p < 0.012
    i = 1160 - 1110
    if not st[i]: 
        continue
    a = i
    while a > 0 and st[a-1]: a -= 1
    b = i
    while b < len(st)-1 and st[b+1]: b += 1
    v4.append([y, 1110+a, 1110+b])
res['v4_rows_y_xl_xr'] = v4
for k in ('v1_rows_y_xl_xr', 'v3_rows_y_xl_xr', 'v4_rows_y_xl_xr'):
    rows = res[k]
    print(k, "n", len(rows), "first", rows[:3], "last", rows[-3:])
    for r in rows[::25]: print("  ", r)
json.dump(res, open(DBG + "/fb_lever_rows.json", "w"))
