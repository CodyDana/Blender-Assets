# -*- coding: utf-8 -*-
"""Probe: is V2 clipped?  Does the atlas card mask work?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P
import pbtag as T

V2 = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"
V1 = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide.png"

a = P.load_stored(V2)[..., :3]
L = P.luma_stored(a)
h, w = L.shape
print("V2", w, "x", h)
for y in [0, 1, 2, 5, 8, 9, 10, 640, 645, 648, 650, 651, 652]:
    row = L[y]
    print(f"  row {y:4d}: min={row.min():.3f} mean={row.mean():.3f} "
          f"first6={[round(float(v),3) for v in row[:6]]} last6={[round(float(v),3) for v in row[-6:]]}")
for x in [0, 3, 6, 9, 12, 13, 14, 285, 288, 290, 291, 293, 296, 299]:
    col = L[:, x]
    print(f"  col {x:4d}: min={col.min():.3f} mean={col.mean():.3f}")
m = T.paper_mask_white_bg(a)
rows = np.flatnonzero(m.any(axis=1)); cols = np.flatnonzero(m.any(axis=0))
print("  V2 paper mask bbox x", cols[0], cols[-1], " y", rows[0], rows[-1],
      " -> wxh", cols[-1]-cols[0]+1, "x", rows[-1]-rows[0]+1)
print("  V2 mask row counts near bottom:", [int(m[y].sum()) for y in range(635, 653)])
print("  V2 mask col counts near right:", [int(m[:, x].sum()) for x in range(285, 300)])

b = P.load_stored(V1)[..., :3]
m1 = T.paper_mask_white_bg(b)
rows = np.flatnonzero(m1.any(axis=1)); cols = np.flatnonzero(m1.any(axis=0))
print("V1 paper mask bbox x", cols[0], cols[-1], " y", rows[0], rows[-1],
      " -> wxh", cols[-1]-cols[0]+1, "x", rows[-1]-rows[0]+1,
      " aspect", (cols[-1]-cols[0]+1)/(rows[-1]-rows[0]+1))

# atlas
BC = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
c = P.load_stored(BC)[..., :3]
mA = T.paper_mask_atlas(c, 'left')
rows = np.flatnonzero(mA.any(axis=1)); cols = np.flatnonzero(mA.any(axis=0))
print("ATLAS left island bbox x", cols[0], cols[-1], " y", rows[0], rows[-1],
      "-> wxh", cols[-1]-cols[0]+1, "x", rows[-1]-rows[0]+1,
      "aspect", (cols[-1]-cols[0]+1)/(rows[-1]-rows[0]+1))
print("  atlas mask fill frac", float(mA.mean()))
