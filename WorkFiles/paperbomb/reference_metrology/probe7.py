# -*- coding: utf-8 -*-
"""Probe 7 - settle the V1/V2 aspect disagreement: edge sanity + landmark ratios."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L
import lib_tag as T

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"

for nm, f in (("V1", "paperbomb_guide.png"), ("V2", "paperbomb_guide_v2_real_glyphs.png")):
    a = L.load_stored(os.path.join(REF, f))
    lu = L.lum(a[..., :3])
    h, w = lu.shape
    m = T.tag_mask_ref(a)
    ys, xs = np.nonzero(m)
    print(f"\n### {nm} {w}x{h}  mask bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]")
    wid = m.sum(axis=1)
    print(" mask row widths, first 6 / last 6 rows of the tag:",
          wid[ys.min():ys.min()+6].tolist(), "...", wid[ys.max()-5:ys.max()+1].tolist())
    hei = m.sum(axis=0)
    print(" mask col heights, first 6 / last 6 cols of the tag:",
          hei[xs.min():xs.min()+6].tolist(), "...", hei[xs.max()-5:xs.max()+1].tolist())
    cx = w // 2
    print(f" lum down column x={cx} around the bottom edge:",
          np.round(lu[ys.max()-4:min(h, ys.max()+8), cx], 3).tolist())
    print(f" lum down column x={cx} around the top edge:",
          np.round(lu[max(0, ys.min()-6):ys.min()+5, cx], 3).tolist())
    cy = (ys.min() + ys.max()) // 2
    print(f" lum across row y={cy} around the left edge:",
          np.round(lu[cy, max(0, xs.min()-6):xs.min()+5], 3).tolist())
    print(f" lum across row y={cy} around the right edge:",
          np.round(lu[cy, xs.max()-4:min(w, xs.max()+8)], 3).tolist())
