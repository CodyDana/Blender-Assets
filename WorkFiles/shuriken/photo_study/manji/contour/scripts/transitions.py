import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
m = np.load(BASE + "/mask_solid.npy").astype(np.int8)
def runs(v):
    d = np.diff(np.concatenate([[0], v, [0]]))
    return list(zip(np.nonzero(d == 1)[0].tolist(), (np.nonzero(d == -1)[0] - 1).tolist()))
for y in [300, 700, 1000, 1150, 1250, 1350, 1500, 1900, 2300]:
    print("row", y, runs(m[y]))
for x in [300, 600, 900, 1250, 1600, 1800, 2100, 2400]:
    print("col", x, runs(m[:, x]))
