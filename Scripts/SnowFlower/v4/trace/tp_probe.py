import numpy as np
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
a = np.load(OUT + "/ref_full.npy")[..., :3]
lum = a @ np.array([0.2126, 0.7152, 0.0722]); br = a[..., 2] - a[..., 0]
np.set_printoptions(linewidth=250)
print("LUM rows 96..136 step4, cols 524..572 step3")
for r in range(96, 137, 4): print(r, " ".join(f"{lum[r,c]:.2f}" for c in range(524, 573, 3)))
print("B-R")
for r in range(96, 137, 4): print(r, " ".join(f"{br[r,c]*100:+4.0f}" for c in range(524, 573, 3)))
print("LEFT mirror B-R")
for r in range(96, 137, 4): print(r, " ".join(f"{br[r,c]*100:+4.0f}" for c in range(487, 438, -3)))
