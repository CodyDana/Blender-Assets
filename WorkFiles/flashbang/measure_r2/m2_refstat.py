import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
R = load(REFP)[..., :3]
print("M2 shape", R.shape)
for y in (10, 100, 300, 500, 700, 730, 745):
    print("M2 row", y, [tuple(int(v) for v in R[y, x]) for x in (5, 30, 290, 330, 600, 630, 960, 1245)])
