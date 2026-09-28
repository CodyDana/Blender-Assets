import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *
R = ref(); rp = paint_mask(R)
d = np.load(ROOT + "WorkFiles/flashbang/measure_r1/mr_sweep.npz")
out = {}
for v, (x0, y0, x1, y1) in VIEW_BOX.items():
    rs = ref_sil(v)[::2, ::2]; rpv = rp[::2, ::2] & rs
    sl = (slice(y0 // 2, y1 // 2), slice(x0 // 2, x1 // 2))
    rows = []
    for k in d.files:
        a = d[k].astype(np.float32)
        osil = a[..., 3] > 128
        op = paint_mask(a[..., :3]) & osil
        si = (rs[sl] & osil[sl]).sum() / max((rs[sl] | osil[sl]).sum(), 1)
        pi = (rpv[sl] & op[sl]).sum() / max((rpv[sl] | op[sl]).sum(), 1)
        rows.append((float(k), float(si), float(pi)))
    rows.sort(key=lambda r: -(r[2] + 0.5 * r[1]))
    out[v] = rows[:6]
    print("MRS", v, [(int(a), round(b, 3), round(c, 3)) for a, b, c in rows[:8]])
json.dump(out, open(ROOT + "WorkFiles/flashbang/measure_r1/mr_yaw_scores.json", "w"))
