import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SnowFlower/SnowFlower_sheath_reference.png"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
os.makedirs(OUT, exist_ok=True)
a = tp_img.load(REF)
print("shape", a.shape, a[..., :3].min(), a[..., :3].max())
c = a[20:190, 420:592]          # rows 20..189, cols 420..591
big = tp_img.resize(c, 6, kind='nearest')
# grid ticks every 10 px
for r in range(0, c.shape[0], 10):
    big[r*6, :, :3] = [1, 0, 0] if (r + 20) % 50 == 0 else [1, .6, .6]
for q in range(0, c.shape[1], 10):
    big[:, q*6, :3] = [0, 0, 1] if (q + 420) % 50 == 0 else [.6, .6, 1]
tp_img.save(OUT + "/ref_throat_x6_grid.png", big)
tp_img.save(OUT + "/ref_throat_x6.png", tp_img.resize(c, 6, kind='linear'))
np.save(OUT + "/ref_full.npy", a)
