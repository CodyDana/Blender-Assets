import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio
ov = rio.load_rgb(os.path.join(os.path.dirname(HERE), "roppo_overlay_reconciled.png"))
for name,(x0,x1,y0,y1) in (("right_point",(840,1250,430,620)),("top_left_root",(330,560,240,430))):
    c = ov[y0:y1, x0:x1]
    Z = 3
    big = np.repeat(np.repeat(c, Z, axis=0), Z, axis=1)
    rio.save_rgb(os.path.join(HERE, "check_%s.png" % name), big)
print("ok")
