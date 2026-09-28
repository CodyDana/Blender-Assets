# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, lib_metro as L, lib_tag as T
def cls(rgb):
    gb = 0.5*(rgb[...,1]+rgb[...,2]); return rgb[...,0]/np.maximum(gb,0.02) > 1.55
for nm, p, ours in (("V1", r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide.png", False),
                    ("OURS", r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png", True)):
    a = L.load_stored(p)
    m = T.tag_mask_ours(a, 940) if ours else T.tag_mask_ref(a)
    rect, _ = T.rectify(a, T.refine_edges(a, T.fit_quad(m)))
    red = cls(rect)
    print(f"--- {nm}: red column occupancy over y 0.15..0.85 (fraction of rows red), x 0..16mm ---")
    lo, hi = int(0.15*T.CH), int(0.85*T.CH)
    occ = red[lo:hi, :int(16*T.PPMM)].mean(axis=0)
    print("  left  :", " ".join("%d:%.2f" % (int(round(i/T.PPMM*10)), occ[i]) for i in range(0, int(16*T.PPMM), 4)))
    occ2 = red[lo:hi, T.CW-int(16*T.PPMM):][:, ::-1].mean(axis=0)
    print("  right :", " ".join("%d:%.2f" % (int(round(i/T.PPMM*10)), occ2[i]) for i in range(0, int(16*T.PPMM), 4)))
    lo2, hi2 = int(0.15*T.CW), int(0.85*T.CW)
    occ3 = red[:int(16*T.PPMM), lo2:hi2].mean(axis=1)
    print("  top   :", " ".join("%d:%.2f" % (int(round(i/T.PPMM*10)), occ3[i]) for i in range(0, int(16*T.PPMM), 4)))
    occ4 = red[T.CH-int(16*T.PPMM):, lo2:hi2][::-1].mean(axis=1)
    print("  bottom:", " ".join("%d:%.2f" % (int(round(i/T.PPMM*10)), occ4[i]) for i in range(0, int(16*T.PPMM), 4)))
    print("  (key = tenths of a mm from the tag edge : fraction of scanlines that are red)")
