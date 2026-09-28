"""reference | ours crops at identical pixel boxes, upscaled. usage: r2_pair.py ours_row.png tag [k]"""
import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *
ref = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3].astype(np.float32) * 255
ours = read_png(sys.argv[1])[..., :3]
tag = sys.argv[2]
k = int(sys.argv[3]) if len(sys.argv) > 3 else 3
boxes = {"head_v1": (60, 40, 330, 200), "head_v2": (370, 40, 600, 200), "head_v3": (660, 40, 930, 200), "head_v4": (975, 40, 1215, 200),
         "body_v2": (380, 180, 560, 420), "body_v3": (650, 280, 840, 520), "base_v1": (60, 600, 260, 725), "base_v3": (640, 600, 840, 725),
         "lever_v1": (230, 150, 320, 600), "lever_v4": (1110, 90, 1210, 600)}
sel = sys.argv[4].split(",") if len(sys.argv) > 4 else list(boxes)
for n in sel:
    b = boxes[n]
    a, o = crop(ref, b), crop(ours, b)
    gap = np.full((a.shape[0], 3, 3), 230.0)
    write_png(f"look/{tag}_{n}.png", up(np.concatenate([a, gap, o], 1), k))
