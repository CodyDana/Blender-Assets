# -*- coding: utf-8 -*-
"""Stage A: find the tag, measure its rotation/keystone, segment ink, dump
component inventory as TEXT so the operator can assign elements.  No pixels
derived from the reference are ever written to disk."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
V1 = os.path.join(REF, "paperbomb_guide.png")
V2 = os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png")
BC = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
FRONT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png"


def survey(path, name):
    a = P.load_stored(path)
    h, w, ch = a.shape
    rgb = a[..., :3]
    L = P.luma_stored(rgb)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    print(f"\n===== {name} {w}x{h} ch={ch} =====")
    print("luma stored percentiles:", [round(float(np.percentile(L, p)), 4)
                                       for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)])
    print("sat  percentiles:", [round(float(np.percentile(sat, p)), 4)
                                for p in (50, 75, 90, 95, 99, 100)])
    if ch == 4:
        al = a[..., 3]
        print("alpha min/median/max:", round(float(al.min()), 4),
              round(float(np.median(al)), 4), round(float(al.max()), 4),
              "frac<0.5:", round(float((al < 0.5).mean()), 5))
    # corner samples (candidate background)
    for (yy, xx, tag) in ((2, 2, 'TL'), (2, w - 3, 'TR'), (h - 3, 2, 'BL'), (h - 3, w - 3, 'BR')):
        print(f"  corner {tag} stored rgb =", [round(float(v), 4) for v in rgb[yy, xx]])
    # mid sample
    print("  centre stored rgb =", [round(float(v), 4) for v in rgb[h // 2, w // 2]])
    # histogram of luma in 16 bins
    hist, _ = np.histogram(L, bins=16, range=(0, 1))
    print("  luma hist/1e3:", [round(v / 1000.0, 1) for v in hist])
    # red-ness
    redness = rgb[..., 0] - np.maximum(rgb[..., 1], rgb[..., 2])
    print("  redness percentiles:", [round(float(np.percentile(redness, p)), 4)
                                     for p in (50, 90, 95, 99, 99.9, 100)])
    return a


for p, n in ((V1, 'V1 guide'), (V2, 'V2 real glyphs'), (BC, 'OURS shipped BC atlas'),
             (FRONT, 'OURS front bc card')):
    st = os.stat(p)
    print(f"[file] {p} size={st.st_size} mtime={st.st_mtime:.1f}")
    survey(p, n)
