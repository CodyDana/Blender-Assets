import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb()
cols = dict(v1=(130, 150), v2=(506, 518), v3=(708, 720), v4=(1062, 1080), v2c=(462, 474), v3c=(755, 767))
for v, (a, b) in cols.items():
    p = ref[:, a:b+1].mean(1)
    g = (p[2:] - p[:-2]).sum(1) / 2   # signed (sum of channels), + = getting brighter downward
    ys = np.arange(1, len(p)-1)
    ag = np.abs(g)
    pk = [(int(ys[i]), round(float(g[i]), 3)) for i in range(1, len(g)-1)
          if ag[i] >= ag[i-1] and ag[i] >= ag[i+1] and ag[i] > 0.10 and 170 < ys[i] < 725]
    print(v, pk)
