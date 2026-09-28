import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *
exec(open(ROOT + "WorkFiles/flashbang/measure_r1/mr_pairs.py").read().split("key = []")[0].replace("os.makedirs(OUTD, exist_ok=False)", ""))
res = []
for i, (kind, (x0, y0, x1, y1)) in enumerate(BOXES, 1):
    a = (RM if kind == "mask" else R)[y0:y1, x0:x1]; h, w = a.shape[:2]
    k = min(4.0, 720.0 / h, 900.0 / w); a = resize(a, k)
    P = load_png(OUTD + f"pair_{i:02d}.png")[..., :3] * 255
    wl = a.shape[1]
    L, Rt = P[:, :wl], P[:, wl + 10:]
    dl, dr = np.abs(L - a).mean(), np.abs(Rt - a).mean()
    res.append("right" if dl < dr else "left")  # ours is the side that is NOT the reference
print("MRVER", ",".join(res))
