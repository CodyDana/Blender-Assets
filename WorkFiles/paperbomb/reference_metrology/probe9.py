# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, lib_metro as L, lib_tag as T
DBG = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology/debug"
a = L.load_stored(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
q = T.refine_edges(a, T.fit_quad(T.tag_mask_ours(a, 940)))
rect, _ = T.rectify(a, q)
L.save_debug_png(rect[int(0.55*T.CH):int(0.85*T.CH), int(0.58*T.CW):], os.path.join(DBG, "DEBUG_NEVER_SHIP_OURS_lowerright.png"))
L.save_debug_png(rect[int(0.28*T.CH):int(0.76*T.CH), :], os.path.join(DBG, "DEBUG_NEVER_SHIP_OURS_centre.png"))
print("ok")
