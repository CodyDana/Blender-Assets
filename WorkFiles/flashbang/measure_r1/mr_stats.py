import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *
p = sys.argv[sys.argv.index("--") + 1]
O = load_png(p)[..., :3] * 255; R = ref()
def pct(im, m):
    lum = im[m] @ np.array([0.2126, 0.7152, 0.0722]); o = np.argsort(lum)
    return [[int(x) for x in im[m][o[int(len(o) * q)]]] for q in (0.1, 0.5, 0.9)]
print("MRT bg ref", np.median(R[5:25, 5:300].reshape(-1, 3), 0), "ours", np.median(O[5:25, 5:300].reshape(-1, 3), 0))
print("MRT bg topright ref", np.median(R[5:25, 1000:1240].reshape(-1, 3), 0), "ours", np.median(O[5:25, 1000:1240].reshape(-1, 3), 0))
print("MRT floor ref", np.median(R[735:745, 5:1240].reshape(-1, 3), 0), "ours", np.median(O[735:745, 5:1240].reshape(-1, 3), 0))
for v, (x0, y0, x1, y1) in VIEW_BOX.items():
    sl = (slice(y0, y1), slice(x0, x1))
    rs = ref_sil(v)[sl]
    rp = paint_mask(R[sl]) & rs; op = paint_mask(O[sl])
    # cap band: dark steel p50 in rows 0.1-0.4 D above bottom around centre
    print("MRT", v, "paint ref", pct(R[sl], rp), "ours", pct(O[sl], op), "frac ref %.3f ours %.3f" % (rp.mean(), op.mean()))
