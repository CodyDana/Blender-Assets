"""Stack ref|ours crops for several boxes into one image.  usage: r2_sheet.py ours.png out.png k box1,box2,..  [ours2.png]
With ours2: ref | ours | ours2 (e.g. reference | round 1 | round 2)."""
import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *
ref = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3].astype(np.float32) * 255
BOX = {"head_v1": (60, 40, 330, 200), "head_v2": (370, 40, 600, 200), "head_v3": (660, 40, 930, 200), "head_v4": (975, 40, 1215, 200),
       "body_v2": (380, 180, 560, 420), "body_v3": (650, 280, 840, 520), "base_v1": (60, 600, 260, 725), "base_v3": (640, 600, 840, 725),
       "lever_v1": (230, 150, 320, 600), "lever_v4": (1110, 90, 1210, 600), "row": (0, 0, 1254, 748),
       "v1": (40, 30, 345, 725), "v2": (345, 30, 615, 725), "v3": (615, 30, 950, 725), "v4": (950, 30, 1240, 725),
       "p1": (6, 756, 318, 1220), "p2": (323, 756, 629, 1220), "p3": (634, 756, 939, 1220), "p4": (946, 756, 1249, 1220)}
imgs = [read_png(sys.argv[1])[..., :3]]
if len(sys.argv) > 5:
    imgs.append(read_png(sys.argv[5])[..., :3])
k = float(sys.argv[3])
rows = []
for n in sys.argv[4].split(","):
    b = BOX[n]
    tiles = [crop(ref, b)] + [crop(i, b) for i in imgs]
    h = min(t.shape[0] for t in tiles)
    parts = []
    for t in tiles:
        parts += [t[:h], np.full((h, 4, 3), 230.0)]
    r = np.concatenate(parts[:-1], 1)
    if k != 1:
        kk = int(k) if k >= 1 else None
        r = up(r, kk) if kk else r[::int(1 / k), ::int(1 / k)]
    rows.append(r)
wmax = max(r.shape[1] for r in rows)
rows = [np.pad(r, ((0, 6), (0, wmax - r.shape[1]), (0, 0)), constant_values=230) for r in rows]
write_png(sys.argv[2], np.concatenate(rows, 0))
