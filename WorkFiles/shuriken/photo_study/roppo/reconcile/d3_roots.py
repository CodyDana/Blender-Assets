import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
rgb = rio.load_rgb(IMG)
H, W, _ = rgb.shape

spots = [
    ("A_rootmark_right_of_top_arc", 710, 238),
    ("A_rootmark_left_of_top_arc", 546, 246),
    ("B_pt5A_vcut_top_left", 423, 330),
    ("ctrl_root_lower_right", 912, 592),
    ("ctrl_root_left_lower", 424, 716),
    ("B_crescent_upper_right_arc", 850, 345),
]
Z = 7
R = 45
tiles = []
for name, x, y in spots:
    crop = rgb[y - R:y + R, x - R:x + R].copy()
    lo = np.percentile(crop, 2)
    hi = np.percentile(crop, 98)
    st = np.clip((crop - lo) / max(hi - lo, 1e-6), 0, 1)
    both = np.concatenate([np.clip(crop, 0, 1), st], axis=1)
    big = np.repeat(np.repeat(both, Z, axis=0), Z, axis=1)
    tiles.append(big)
    rio.save_rgb(os.path.join(HERE, "root_%s.png" % name), big)
print("saved", len(tiles))
