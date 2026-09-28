# -*- coding: utf-8 -*-
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fid_common as C
a = C.load_v2()
H, W = a.shape[:2]
print("V2", W, H, C.sha256(C.V2))
out = os.path.join(C.HERE, "view"); os.makedirs(out, exist_ok=True)
# column regions in card fractions (x0,x1,y0,y1) from rg_s6 CDEF
R = dict(TL=(.04, .30, .03, .37), TR=(.66, .96, .03, .38), BR=(.68, .96, .60, .84),
         BC=(.36, .64, .68, .93), CEN=(.05, .95, .30, .66), SEAL=(.76, .96, .82, .95), BIGSEAL=(.05, .33, .74, .94))
for k, (x0, x1, y0, y1) in R.items():
    X0 = int(C.XL + x0 * C.WPX); X1 = int(C.XL + x1 * C.WPX)
    Y0 = int(C.YT + y0 * C.HPX); Y1 = int(C.YT + y1 * C.HPX)
    crop = a[Y0:Y1, X0:X1]
    C.save_png(crop, os.path.join(out, "v2_%s_x%d_y%d.png" % (k, X0, Y0)), scale=8 if k not in ("CEN",) else 4)
    print(k, X0, X1, Y0, Y1)
