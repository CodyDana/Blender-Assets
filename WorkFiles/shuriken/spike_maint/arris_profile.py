"""Luminance profile across the hero's camera-facing top arris (the round = mask blue in the bar's middle).

    "<blender python>" arris_profile.py <beauty.png> <mask.png> [x0 x1 step]
For each column: the rows from 4 above the first round pixel of the upper-most round run that borders the
side face below, to 4 below the round run, as stored-sRGB luma.  Prints a table and a mean profile.
"""
import sys

import numpy as np
import OpenImageIO as oiio

W = np.array([0.2126, 0.7152, 0.0722])
beauty, mask_path = sys.argv[1:3]
x0, x1, step = (int(v) for v in sys.argv[3:6]) if len(sys.argv) > 5 else (450, 1050, 50)
px = np.asarray(oiio.ImageBuf(beauty).get_pixels(oiio.FLOAT))
m = np.asarray(oiio.ImageBuf(mask_path).get_pixels(oiio.FLOAT))
lum = px[..., :3].astype(np.float64) @ W
sel = m[..., 3] > 0.5
blue = sel & (m[..., 2] > 0.5)
red = sel & (m[..., 0] > 0.5) & (m[..., 2] <= 0.5)
profiles = []
for x in range(x0, x1 + 1, step):
    col_blue = np.nonzero(blue[:, x])[0]
    col_red = np.nonzero(red[:, x])[0]
    if not len(col_blue) or not len(col_red):
        continue
    # the round run directly above the first side-face (red) row
    first_red = col_red.min()
    above = col_blue[col_blue < first_red]
    if not len(above):
        continue
    top = above.max()
    run_top = top
    while run_top - 1 in set(above):
        run_top -= 1
    rows = list(range(run_top - 5, top + 7))
    prof = [round(float(lum[r, x]), 3) for r in rows]
    tags = "".join("B" if blue[r, x] else ("R" if red[r, x] else ("." if sel[r, x] else " ")) for r in rows)
    profiles.append(prof)
    print(f"x={x:5d} rows {rows[0]}-{rows[-1]} {tags}  " + " ".join(f"{v:.2f}" for v in prof))
n = min(len(p) for p in profiles)
mean = np.mean([p[:n] for p in profiles], axis=0)
print("mean  " + " ".join(f"{v:.2f}" for v in mean))
