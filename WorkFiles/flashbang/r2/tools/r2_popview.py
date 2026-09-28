import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *
d = sys.argv[1]; k = sys.argv[2]; turn = sys.argv[3]; a_n = sys.argv[4]; b_n = sys.argv[5]
A = read_png(f"{d}/lodpop_d{k}_turn{turn}_{a_n}.png"); B = read_png(f"{d}/lodpop_d{k}_turn{turn}_{b_n}.png")
al = np.maximum(A[..., 3], B[..., 3]) > 127
ys, xs = np.nonzero(al)
y0, y1, x0, x1 = ys.min() - 4, ys.max() + 4, xs.min() - 4, xs.max() + 4
g = 0.18 * 255
ca = A[..., :3] * (A[..., 3:] / 255) + (1 - A[..., 3:] / 255) * g
cb = B[..., :3] * (B[..., 3:] / 255) + (1 - B[..., 3:] / 255) * g
diff = (np.abs(ca - cb).max(2) > 20) & al
dimg = np.stack([diff * 255] * 3, -1).astype(np.float32)
sc = int(sys.argv[6]) if len(sys.argv) > 6 else 3
out = np.concatenate([ca[y0:y1, x0:x1], cb[y0:y1, x0:x1], dimg[y0:y1, x0:x1]], 1)
write_png(sys.argv[7] if len(sys.argv) > 7 else "look/pop.png", up(out, sc))
print(diff.sum(), al.sum())
