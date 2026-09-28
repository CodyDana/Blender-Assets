import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
pm = np.load(DBG + "/fb_paint.npy")
VIEWS = dict(v1=(60, 255), v2=(372, 562), v3=(650, 842), v4=(1005, 1202))
# vertical profile of paint fraction along body (to find hole rows)
for v, (x0, x1) in VIEWS.items():
    col = pm[:, x0:x1].mean(1)
    print(v, "paintfrac y180..650 step3:", ' '.join(f"{int(col[y]*9.99)}" for y in range(180, 650, 3)))
for v, (x0, x1) in VIEWS.items():
    for y in range(300, 600, 10):
        row = pm[y-1:y+2, x0:x1].mean(0) > 0.5
        # runs of not-paint
        runs = []; inrun = False
        for i, p in enumerate(row):
            if not p and not inrun: s = i; inrun = True
            if p and inrun: runs.append((s+x0, i-1+x0)); inrun = False
        if inrun: runs.append((s+x0, len(row)-1+x0))
        runs = [r for r in runs if r[1]-r[0] >= 6]
        print(v, y, runs)
