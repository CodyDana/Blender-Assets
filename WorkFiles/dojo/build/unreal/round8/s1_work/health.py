import sys, glob, os, json
import numpy as np
from PIL import Image
rows = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.png"))):
    a = np.asarray(Image.open(f).convert("RGB")).astype(float)
    lu = a[..., 0] * .2126 + a[..., 1] * .7152 + a[..., 2] * .0722
    h, w = lu.shape
    cells = [(a[i*h//4:(i+1)*h//4, j*w//4:(j+1)*w//4].max(2) < 12).mean() * 100 for i in range(4) for j in range(4)]
    rows[os.path.basename(f)[:-4]] = {"under40_pct": round(float((lu < 40).mean() * 100), 1), "mean": round(float(lu.mean()), 1),
        "clip_any_pct": round(float((a >= 254).any(2).mean() * 100), 2), "near_black_pct": round(float((a.max(2) < 12).mean() * 100), 2),
        "worst_cell_near_black_pct": round(max(cells), 1)}
json.dump(rows, open(sys.argv[2], "w"), indent=1)
for k, v in rows.items(): print(f"{k:28s} {v}")
