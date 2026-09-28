import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
import json
W = ROOT + "WorkFiles/flashbang/measure_r2/"
R = np.load(W + "m2_ref_rgb.npy"); O = load(W + "m2_row.png")[..., :3]
def paint(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    return (np.abs(r - g) <= 12) & ((g - b) >= 7) & (g >= 30)
def boxmean(m, r):
    c = np.cumsum(np.cumsum(np.pad(m.astype(float), ((r + 1, r), (r + 1, r))), 0), 1)
    return (c[2*r+1:, 2*r+1:] - c[:-2*r-1, 2*r+1:] - c[2*r+1:, :-2*r-1] + c[:-2*r-1, :-2*r-1]) / (2*r+1)**2
res = {}
for nm, im, cols in (("ref", R, {"v2": 467, "v3": 746}), ("ours", O, {"v2": 467, "v3": 746})):
    pm = boxmean(paint(im), 2) > 0.5
    for v, cx in cols.items():
        # find hole column near the axis: x with most non-paint within body band
        band = slice(280, 610)
        xs = np.arange(cx - 40, cx + 41)
        npf = [(~pm[band, x]).mean() for x in xs]; xc = int(xs[int(np.argmax(npf))])
        col = ~pm[:, xc - 2:xc + 3].any(1) if False else (~pm[:, xc - 2:xc + 3]).all(1)
        col[:260] = False; col[630:] = False
        runs = []; y = 0
        while y < len(col):
            if col[y]:
                s = y
                while y < len(col) and col[y]: y += 1
                if y - s > 20: runs.append((s, y - 1))
            y += 1
        holes = []
        for (a, b) in runs:
            yc = (a + b) // 2
            row = ~pm[yc - 2:yc + 3].all(0) if False else (~pm[yc - 2:yc + 3]).all(0)
            l = xc; r = xc
            while l > 0 and row[l - 1]: l -= 1
            while r < 1253 and row[r + 1]: r += 1
            holes.append({"y": [a, b], "h": b - a + 1, "w": r - l + 1, "x": [l, r]})
        res[f"{nm}_{v}"] = {"xc": xc, "holes": holes}
        print("M2H", nm, v, xc, holes)
json.dump(res, open(W + "m2_holes.json", "w"), indent=1)
