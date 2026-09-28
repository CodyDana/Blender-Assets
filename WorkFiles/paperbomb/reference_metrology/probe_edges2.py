# -*- coding: utf-8 -*-
"""Probe 2: V1 chamfer profile (to recover V2's crop) and our own card masks."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P
import pbtag as T

V1 = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide.png"
V2 = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"

a = P.load_stored(V1)[..., :3]
m = T.paper_mask_white_bg(a)
rows = np.flatnonzero(m.any(axis=1))
y0, y1 = rows[0], rows[-1]
wid = m.sum(axis=1)
full = float(np.median(wid[y0 + 300:y1 - 300]))
print(f"V1 tag rows {y0}..{y1}  full width {full}")
print("V1 width profile top (row, width, width/full):")
for y in range(y0, y0 + 90, 6):
    print(f"   {y-y0:4d} {int(wid[y]):4d} {wid[y]/full:.4f}")
print("V1 width profile bottom (rows from bottom):")
for y in range(y1, y1 - 90, -6):
    print(f"   {y1-y:4d} {int(wid[y]):4d} {wid[y]/full:.4f}")

b = P.load_stored(V2)[..., :3]
m2 = T.paper_mask_white_bg(b)
rows2 = np.flatnonzero(m2.any(axis=1))
y0b, y1b = rows2[0], rows2[-1]
wid2 = m2.sum(axis=1)
full2 = float(np.median(wid2[y0b + 130:y1b - 130]))
print(f"\nV2 tag rows {y0b}..{y1b}  full width {full2}")
print("V2 width profile top:")
for y in range(y0b, y0b + 42, 3):
    print(f"   {y-y0b:4d} {int(wid2[y]):4d} {wid2[y]/full2:.4f}")
print("V2 width profile bottom (last rows):")
for y in range(y1b, y1b - 42, -3):
    print(f"   {y1b-y:4d} {int(wid2[y]):4d} {wid2[y]/full2:.4f}")

print("\n--- our own card silhouette masks ---")
for p in (r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_card.png",
          r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_fringe.png"):
    c = P.load_stored(p)
    print(os.path.basename(p), c.shape, "min", float(c[..., 0].min()), "max", float(c[..., 0].max()))
    g = c[..., 0]
    mm = g > 0.5
    rr = np.flatnonzero(mm.any(axis=1)); cc = np.flatnonzero(mm.any(axis=0))
    print("   >0.5 bbox x", cc[0], cc[-1], "y", rr[0], rr[-1],
          "-> w", cc[-1] - cc[0] + 1, "h", rr[-1] - rr[0] + 1)
    wd = mm.sum(axis=1)
    print("   width profile top:", [int(wd[rr[0] + i]) for i in range(0, 40, 4)])
    print("   width profile bot:", [int(wd[rr[-1] - i]) for i in range(0, 40, 4)])
    ht = mm.sum(axis=0)
    print("   height at cols:", [int(ht[cc[0] + i]) for i in range(0, 40, 4)])

# our art bc: where is the card edge really?
d = P.load_stored(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png")[..., :3]
L = P.luma_stored(d)
print("\nfront_bc luma row means near top:", [round(float(L[y].mean()), 4) for y in range(0, 40, 3)])
print("front_bc luma col means near left:", [round(float(L[:, x].mean()), 4) for x in range(0, 40, 3)])
print("front_bc luma col means near right:", [round(float(L[:, 945 - x].mean()), 4) for x in range(0, 40, 3)])
