"""Measure the user's reference tack band (taiko_tacks_ref_user.webp): tack centres by distance-transform peaks of the
dark mask, then per-row pitch, diameter, row spacing and offset near the front (least foreshortened)."""
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

im = np.asarray(Image.open(r"C:/Users/Cody/Desktop/Blender_Projects/References/Dojo/taiko_tacks_ref_user.webp").convert("L")).astype(float)
out = {}
for name, (y0, y1) in {"top": (170, 265), "bottom": (820, 920)}.items():
    sub = im[y0:y1, 120:900]
    mask = sub < 70
    mask = ndi.binary_opening(mask, iterations=1)
    dt = ndi.distance_transform_edt(mask)
    mx = ndi.maximum_filter(dt, size=11)
    peaks = np.argwhere((dt == mx) & (dt > 6))
    # merge close peaks
    pts = []
    for (y, x) in peaks:
        if all((y - py) ** 2 + (x - px) ** 2 > 36 for py, px, _ in pts):
            pts.append((y, x, dt[y, x]))
    pts = [(y + y0, x + 120, r) for y, x, r in pts]
    out[name] = sorted(pts, key=lambda p: p[1])
    print(name, len(pts))
    for p in out[name]:
        print("  y %.1f x %.1f r %.1f" % p)
json.dump({k: [[float(a) for a in p] for p in v] for k, v in out.items()}, open("ref_peaks.json", "w"), indent=0)
