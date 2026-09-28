import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep")
from ms_lib import *
ref = np.load(D+"ref_rgb.npy"); lum = ref.mean(2); sat = ref.max(2)-ref.min(2); rfg = (lum < 0.9) | (sat > 0.08)
MM = 1256.3/1205
for view, x0, ax in [("front", 215, 287)]:
    om = np.load(D+"ours_mask_%s.npy" % view); rm = rfg[:, x0:x0+om.shape[1]]
    a = ax - x0
    def run(m):
        c = np.where(m)[0]
        if not len(c): return None
        segs = np.split(c, np.where(np.diff(c) > 3)[0]+1)
        s = min(segs, key=lambda s: 0 if s[0] <= a <= s[-1] else min(abs(s[0]-a), abs(s[-1]-a)))
        return (round((s[0]-a)*MM,1), round((s[-1]+1-a)*MM,1))
    for r in list(range(10, 60, 4)) + list(range(240, 345, 6)) + list(range(1100, 1222, 10)):
        print(r, "ref", run(rm[r]), "ours", run(om[r]))
# tone: blade channel luminance (front view rows 400-650, central cols), guard, grip
S = np.load(D+"ours_sheet_front.npy")
for nm, (r0, r1, c0, c1) in {"blade_upper": (400, 650, 270, 310), "blade_lower": (750, 1050, 268, 305), "grip": (80, 230, 272, 300), "guard": (275, 315, 240, 330)}.items():
    rr = ref[r0:r1, c0:c1]; oo = S[r0:r1, c0-215:c1-215]
    print("TONE", nm, "ref mean", rr.mean((0,1)).round(3), "std", rr.mean(2).std().round(3), "| ours mean", oo.mean((0,1)).round(3), "std", oo.mean(2).std().round(3))
