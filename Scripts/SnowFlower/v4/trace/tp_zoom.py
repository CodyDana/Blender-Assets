import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
a = np.load(OUT + "/ref_full.npy")
argv = sys.argv[sys.argv.index("--") + 1:]
r0, r1, c0, c1, s = map(int, argv[:5]); name = argv[5]
c = a[r0:r1, c0:c1].copy()
big = tp_img.resize(c, s, kind='linear')
for r in range(r0, r1):
    if r % 5 == 0:
        y = (r - r0) * s
        big[y, :, :3] = [1, 0, 0] if r % 10 == 0 else [1, 0.7, 0.7]
        if r % 50 == 0: big[y:y+2, :, :3] = [0.6, 0, 0]
for q in range(c0, c1):
    if q % 5 == 0:
        x = (q - c0) * s
        big[:, x, :3] = [0, 0, 1] if q % 10 == 0 else [0.7, 0.7, 1]
        if q % 50 == 0: big[:, x:x+2, :3] = [0, 0, 0.6]
tp_img.save(OUT + f"/zoom_{name}.png", big)
