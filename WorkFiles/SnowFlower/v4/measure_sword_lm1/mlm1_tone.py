import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_lm1")
from mlm1_lib import *
ref = np.load(D+"mlm1_ref_rgb.npy")
S = np.load(D+"mlm1_sheet_front.npy")
for nm, (r0, r1, c0, c1) in {"blade_upper": (400, 650, 270, 310), "blade_lower": (750, 1050, 268, 305), "grip": (80, 230, 272, 300), "guard": (275, 315, 240, 330), "pommel": (12, 40, 272, 302)}.items():
    rr = ref[r0:r1, c0:c1]; oo = S[r0:r1, c0-215:c1-215]
    print("TONE", nm, "ref mean", rr.mean((0,1)).round(3), "p10/p90", np.percentile(rr.mean(2),[10,90]).round(3), "| ours mean", oo.mean((0,1)).round(3), "p10/p90", np.percentile(oo.mean(2),[10,90]).round(3))
