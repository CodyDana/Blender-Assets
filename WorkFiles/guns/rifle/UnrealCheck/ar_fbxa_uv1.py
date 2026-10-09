import re, sys, json
import numpy as np
from pathlib import Path


def arr(txt, key):
    m = re.search(key + r":\s*\*\d+\s*\{\s*a:\s*([^}]*)\}", txt)
    return np.array([float(x) for x in m.group(1).replace("\n", "").split(",") if x.strip()]) if m else None


def overlap(tris, R):
    grid = np.zeros((R, R), np.uint16)
    for a, b, c in tris:
        mn = np.clip(np.floor(np.minimum(np.minimum(a, b), c) * R).astype(int), 0, R - 1)
        mx = np.clip(np.ceil(np.maximum(np.maximum(a, b), c) * R).astype(int), 0, R)
        if mx[0] <= mn[0] or mx[1] <= mn[1]:
            continue
        xs = (np.arange(mn[0], mx[0]) + 0.5) / R; ys = (np.arange(mn[1], mx[1]) + 0.5) / R
        X, Y = np.meshgrid(xs, ys)
        w0 = (b[0] - X) * (c[1] - Y) - (c[0] - X) * (b[1] - Y); w1 = (c[0] - X) * (a[1] - Y) - (a[0] - X) * (c[1] - Y); w2 = (a[0] - X) * (b[1] - Y) - (b[0] - X) * (a[1] - Y)
        ins = ((w0 > 0) & (w1 > 0) & (w2 > 0)) | ((w0 < 0) & (w1 < 0) & (w2 < 0))
        grid[mn[1]:mx[1], mn[0]:mx[0]] += ins.astype(np.uint16)
    return int((grid > 1).sum())


for p in sys.argv[1:]:
    t = Path(p).read_text(errors="ignore")
    geo = t[t.index("Geometry:"):]
    blocks = [m.start() for m in re.finditer(r"LayerElementUV:", geo)]
    if len(blocks) < 2:
        print(Path(p).stem, "no UV1"); continue
    b1 = geo[blocks[1]:]
    UV = arr(b1, "UV").reshape(-1, 2)
    UVI = arr(b1, "UVIndex").astype(np.int64)
    tris = UV[UVI].reshape(-1, 3, 2)
    print(Path(p).stem, "tris", len(tris), "ov64", overlap(tris, 64), "ov1024", overlap(tris, 1024))
