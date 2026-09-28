import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *
ref = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3].astype(np.float32) * 255
ours = read_png(sys.argv[1])[..., :3]
VIEW_CX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
VIEW_BOTTOM = {"v1": 720.5, "v2": 716.8, "v3": 717.0, "v4": 717.0}
D = 175.31
for v in ("v2", "v3"):
    for H in (2.75, 1.2, 0.3):          # sleeve band, ring-line web, cap
        y = int(VIEW_BOTTOM[v] - H * D)
        xs = np.linspace(-0.5, 0.5, 11)
        out = []
        for im in (ref, ours):
            row = im[y - 3:y + 4].mean(0) @ np.array([0.2126, 0.7152, 0.0722])
            out.append([int(row[int(VIEW_CX[v] + x * D)]) for x in xs])
        print(v, H, "ref ", out[0]); print(v, H, "ours", out[1])
