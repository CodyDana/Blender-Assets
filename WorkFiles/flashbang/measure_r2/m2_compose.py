"""Compose OUR eight-view sheet in the reference layout (only our pixels: row render + our four close-ups)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
W = ROOT + "WorkFiles/flashbang/measure_r2/"
P = {"p1": (6, 756, 318, 1220), "p2": (323, 756, 629, 1220), "p3": (634, 756, 939, 1220), "p4": (946, 756, 1249, 1220)}
row = load(W + "m2_row.png")[..., :3]
S = np.zeros((1254, 1254, 3), np.float32)
S[:] = np.array([38.0, 38.0, 37.0])        # flat gap colour (ours, not copied from the reference)
S[:750] = row[:750]
for k, (x0, y0, x1, y1) in P.items():
    o = load(W + f"m2_{k}.png")[..., :3]
    o = resize(o, (y1 - y0) / o.shape[0])
    S[y0:y1, x0:x1] = o[:, :x1 - x0]
    S[y0 - 1, x0 - 1:x1 + 1] = S[y1, x0 - 1:x1 + 1] = 70.0
    S[y0 - 1:y1 + 1, x0 - 1] = S[y0 - 1:y1 + 1, x1] = 70.0
np.save(W + "m2_ours_sheet.npy", S)
save(W + "m2_ours_eight_views.png", S)
R = np.load(W + "m2_ref_rgb.npy")
gap = np.full((1254, 12, 3), 128.0)
save(W + "m2_side_by_side.png", np.concatenate([R, gap, S], 1))
print("M2C done")
