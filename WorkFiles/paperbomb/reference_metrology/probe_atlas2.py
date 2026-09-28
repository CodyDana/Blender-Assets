# -*- coding: utf-8 -*-
"""Locate the atlas UV islands from paper grain energy, and re-register."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P
import pbtag as PT

ART = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png"
ATL = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"

b = P.load_stored(ATL)[..., :3]
Lb = P.luma_stored(b).astype(np.float64)
g = np.abs(np.diff(Lb, axis=1, prepend=Lb[:, :1])) + np.abs(np.diff(Lb, axis=0, prepend=Lb[:1, :]))
e = PT.box_blur(g, 3)
colE = e.mean(axis=0)
rowE = e.mean(axis=1)
print("col energy (every 16 px, x=0..1100):")
print(" ".join(f"{x}:{colE[x]*1000:.1f}" for x in range(0, 1104, 16)))
print("\nrow energy (every 32 px):")
print(" ".join(f"{y}:{rowE[y]*1000:.1f}" for y in range(0, 2048, 32)))
thr = float(np.percentile(colE, 20)) * 1.6
print("\nthreshold", thr * 1000)
on = colE > thr
runs = []
i = 0
while i < len(on):
    if on[i]:
        j = i
        while j + 1 < len(on) and on[j + 1]:
            j += 1
        if j - i > 40:
            runs.append((i, j))
        i = j + 1
    else:
        i += 1
print("col runs:", runs)
onr = rowE > float(np.percentile(rowE, 20)) * 1.6
rr = []
i = 0
while i < len(onr):
    if onr[i]:
        j = i
        while j + 1 < len(onr) and onr[j + 1]:
            j += 1
        if j - i > 40:
            rr.append((i, j))
        i = j + 1
    else:
        i += 1
print("row runs:", rr)

# fine edges: first/last column whose energy exceeds the threshold inside island 1
print("\nfine scan left edge:", [f"{x}:{colE[x]*1000:.2f}" for x in range(20, 45)])
print("fine scan right edge:", [f"{x}:{colE[x]*1000:.2f}" for x in range(880, 905)])
print("fine scan top edge:", [f"{y}:{rowE[y]*1000:.2f}" for y in range(0, 25)])
print("fine scan bottom edge:", [f"{y}:{rowE[y]*1000:.2f}" for y in range(2020, 2048)])
