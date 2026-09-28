"""side-by-side: reference crop (4x) | render (same frame)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
W = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
tag = sys.argv[sys.argv.index("--") + 1]
ref = np.load(W + "/ref_full.npy")[20:190, 415:597]
r4 = tp_img.resize(ref, 4, kind='linear')
ours = tp_img.load(W + f"/prev_{tag}_front.png")
out = np.concatenate([r4[..., :3], ours[..., :3]], 1)
tp_img.save(W + f"/sbs_{tag}.png", out)
