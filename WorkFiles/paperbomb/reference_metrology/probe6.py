# -*- coding: utf-8 -*-
"""Probe 6 - high-res DEBUG zooms so structures can be identified before measuring."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
DBG = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology/debug"

a = L.load_stored(os.path.join(REF, "paperbomb_guide.png"))[..., :3]
# V1 tag box (continuous): x 198.99..826.28, y 58.15..1449.0
X0, Y0, W, H = 199.0, 58.2, 627.3, 1390.8

def crop(fx0, fy0, fx1, fy1, up, name):
    x0 = int(X0 + fx0 * W); x1 = int(X0 + fx1 * W)
    y0 = int(Y0 + fy0 * H); y1 = int(Y0 + fy1 * H)
    c = a[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, up, axis=0), up, axis=1)
    L.save_debug_png(c, os.path.join(DBG, f"DEBUG_NEVER_SHIP_{name}.png"))
    print(name, "src box x", x0, x1, "y", y0, y1, "->", c.shape)

crop(0.00, 0.000, 0.30, 0.110, 3, "V1_zoom_TLcorner")
crop(0.70, 0.000, 1.00, 0.110, 3, "V1_zoom_TRcorner")
crop(0.00, 0.890, 0.30, 1.000, 3, "V1_zoom_BLcorner")
crop(0.70, 0.890, 1.00, 1.000, 3, "V1_zoom_BRcorner")
crop(0.35, 0.000, 0.65, 0.060, 4, "V1_zoom_TOPmid")
crop(0.35, 0.940, 0.65, 1.000, 4, "V1_zoom_BOTmid")
crop(0.38, 0.690, 0.62, 0.990, 3, "V1_zoom_lowercentre")
crop(0.05, 0.560, 0.50, 0.980, 2, "V1_zoom_leftseal")
crop(0.50, 0.720, 1.00, 0.990, 2, "V1_zoom_rightseal")
crop(0.00, 0.120, 0.35, 0.520, 2, "V1_zoom_leftcolumn")

b = L.load_stored(os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))[..., :3]
X0, Y0, W, H = 12.0, 9.0, 280.0, 644.0
a = b
crop(0.00, 0.000, 0.35, 0.130, 6, "V2_zoom_TLcorner")
crop(0.65, 0.860, 1.00, 1.000, 6, "V2_zoom_BRcorner")
crop(0.35, 0.660, 0.68, 1.000, 5, "V2_zoom_lowercentre")
crop(0.00, 0.520, 0.55, 1.000, 4, "V2_zoom_leftseal")
