import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *
ref = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3].astype(np.float32)
print(ref.shape, ref.dtype, ref.max())
if ref.max() <= 1.01: ref = ref * 255
boxes = {"v1": (60, 40, 330, 200), "v2": (370, 40, 600, 200), "v3": (660, 40, 930, 200), "v4": (975, 40, 1215, 200)}
for k, b in boxes.items():
    write_png(f"look/ref_head_{k}.png", up(crop(ref, b), 4))
