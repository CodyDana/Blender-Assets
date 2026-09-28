# final pass: photograph the CURRENT shipped BC onto the reference grid with the m3 fit (m3_measure.photo) -> fx/photo_bc.npy
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m3")
from m3_lib import *
A = json.load(open(OUT + "m3_align.json"))
r = load(REF); H, W = r.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bc = load(BC)
s = box_blur(bc, 3)
w = bilinear(s, A["bc"][0]*(xx+0.5)+A["bc"][2]-0.5, A["bc"][1]*(yy+0.5)+A["bc"][3]-0.5)
np.save("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/fx/photo_bc.npy", gauss_blur(w, A["bc_sigma"]).astype(np.float32))
print("ok")
