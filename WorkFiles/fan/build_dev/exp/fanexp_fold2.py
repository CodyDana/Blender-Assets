import sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
fs = F.FoldSolver(FAN)
for s in [1, .8, .6, .4, .2, .1, .05, .02, .01, .005, 0]:
    g = fs.solve(s)
    r = fs._residual(g.x, *fs._targets(s)).reshape(-1, 3)
    print(f"s={s:6.3f}", " ".join(f"{np.linalg.norm(v):.4f}" for v in r), " (A_rib_in A_rib_out B_rib_in B_rib_out mid_in mid_out)")
