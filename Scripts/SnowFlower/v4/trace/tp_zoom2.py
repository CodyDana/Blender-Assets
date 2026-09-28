import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
a = np.load(OUT + "/ref_full.npy")
argv = sys.argv[sys.argv.index("--") + 1:]
r0, r1, c0, c1, s = map(int, argv[:5]); name = argv[5]
c = a[r0:r1, c0:c1].copy()
big = tp_img.resize(c, s, kind='linear')
pad = 24
H, W = big.shape[:2]
can = np.ones((H + pad, W + pad, 4), np.float32)
can[pad:, pad:] = big
for r in range(r0, r1 + 1):
    y = pad + (r - r0) * s
    if y >= can.shape[0]: break
    L = 24 if r % 10 == 0 else (14 if r % 5 == 0 else 5)
    can[y, :L, :3] = [1, 0, 0] if r % 10 == 0 else [0, 0, 0]
    can[y, pad:, :3] = can[y, pad:, :3] * 0.85 + 0.15 * np.array([1, 0, 0]) if r % 10 == 0 else can[y, pad:, :3]
for q in range(c0, c1 + 1):
    x = pad + (q - c0) * s
    if x >= can.shape[1]: break
    L = 24 if q % 10 == 0 else (14 if q % 5 == 0 else 5)
    can[:L, x, :3] = [0, 0, 1] if q % 10 == 0 else [0, 0, 0]
    can[pad:, x, :3] = can[pad:, x, :3] * 0.85 + 0.15 * np.array([0, 0, 1]) if q % 10 == 0 else can[pad:, x, :3]
tp_img.save(OUT + f"/z2_{name}.png", can)
print("saved", name, r0, c0, s)
