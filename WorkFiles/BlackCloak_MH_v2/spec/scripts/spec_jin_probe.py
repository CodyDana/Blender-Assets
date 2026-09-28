import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from spec_imgutil import *
O = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"
a = load(os.path.join(O, "spec_jin_full.png"))
pts = {"bg": (2200, 1800), "bg2": (100, 200), "skin_cheek": (1050, 620), "skin_fore": (1120, 420), "cloak_fill": (1500, 2200), "cloak_fill2": (900, 2800), "collar": (1100, 900), "collar_inside": (900, 720), "clasp": (563, 1320), "hair": (800, 300), "inkline": (0,0)}
for k, (x, y) in pts.items():
    p = a[y-3:y+4, x-3:x+4, :3].reshape(-1, 3).mean(0)
    print(k, (x, y), (p * 255).round(1))
# column profile at face centre x=1124: print luma + rgb every 10 px from y=400..900
for y in range(600, 860, 8):
    p = a[y, 1115:1135, :3].mean(0) * 255
    print("col", y, p.round(0))
