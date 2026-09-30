"""VERIFY r5: near-black (max channel < 12, sRGB) per region: every still split into a 4 x 4 grid (480 x 270 cells at
1920 x 1080); reports every cell over 10 %, and the whole-frame fraction. Blown = min channel >= 250: where (grid
cells) and how much. Out: verify_r5/regions_nb.json"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round5/f1"
VD = B / "WorkFiles/dojo/build/verify_r5"
res = {}
for p in sorted(CAP.glob("C*_*.png")):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    mx, mn = a.max(axis=2), a.min(axis=2)
    h, w = mx.shape
    cells, blown = [], []
    for r in range(4):
        for c in range(4):
            sl = (slice(r * h // 4, (r + 1) * h // 4), slice(c * w // 4, (c + 1) * w // 4))
            f = float((mx[sl] < 12).mean())
            b = float((mn[sl] >= 250).mean())
            if f > 0.10:
                cells.append([r, c, round(f, 3), [int(v) for v in np.median(a[sl].reshape(-1, 3), axis=0)]])
            if b > 0:
                blown.append([r, c, round(b, 5)])
    res[p.stem] = {"frame_nb": round(float((mx < 12).mean()), 4), "cells_over_10pct": cells,
                   "max_cell_nb": round(max(float((mx[r*h//4:(r+1)*h//4, c*w//4:(c+1)*w//4] < 12).mean()) for r in range(4) for c in range(4)), 3),
                   "blown_frac": round(float((mn >= 250).mean()), 6), "blown_cells": blown}
(VD / "regions_nb.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in res.items():
    if v["cells_over_10pct"] or v["frame_nb"] > 0.1 or v["blown_frac"] > 0:
        print(f"{k:24s} frame {v['frame_nb']:.3f} maxcell {v['max_cell_nb']:.3f} cells>10% {[(c[0],c[1],c[2]) for c in v['cells_over_10pct']]} blown {v['blown_frac']} {v['blown_cells']}")
