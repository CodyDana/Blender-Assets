"""VERIFY r6: plan pictures of the in-engine floods (ue_alley_suite*.json): per plan cell, dark red = reached at a
ground bottom (<= +0.62), orange = reached higher only, light grey = free but never reached, black = never free /
never tested; the rear target boxes drawn in cyan. North up. Out: verify_r6/flood_plan_<mode>.png"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r6")
src = sys.argv[1] if len(sys.argv) > 1 else "ue_alley_suite.json"
d = json.loads((VD / src).read_text(encoding="utf-8"))
COL = {"2": (150, 20, 20), "1": (240, 150, 40), "0": (200, 200, 200), "9": (20, 20, 20)}
S = 4
for key in [k for k in d if k.startswith("A_flood")]:
    f = d[key]
    rows = f["plan_rows_y_up"]
    ny, nx = len(rows), len(rows[0])
    im = Image.new("RGB", (nx * S, ny * S))
    px = im.load()
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            for a in range(S):
                for b in range(S):
                    px[i * S + a, (ny - 1 - j) * S + b] = COL[c]
    dr = ImageDraw.Draw(im)
    x0, y0, dx = f["plan_x0"], f["plan_y0"], f["plan_dx"]
    for name, (bx0, bx1, by0, by1, _z) in d["targets"].items():
        dr.rectangle([(bx0 - x0) / dx * S, (ny - 1 - (by1 - y0) / dx) * S, (bx1 - x0) / dx * S, (ny - 1 - (by0 - y0) / dx) * S], outline=(0, 220, 255), width=2)
    out = VD / f"flood_plan_{key}.png"
    im.save(out)
    print(out, im.size)
