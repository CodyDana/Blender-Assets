import sys, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
t0 = time.time()
off, rep = F.optimise_bind(FAN, iters=120, log=lambda m: print(m, round(time.time()-t0), flush=True))
print(rep, flush=True)
fs = F.FoldSolver(FAN, off)
print("closed tilt", fs.page_tilt_deg(0.0))
for s in [0.9, 0.7, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.0]:
    print(s, fs.cracks(s), flush=True)
