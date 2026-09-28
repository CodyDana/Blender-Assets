"""Compute the optimised bind of the fan's leaf (props_lib.fan_fold.optimise_bind) and write the build's cache
WorkFiles/fan/fold_bind_cache.json (keyed by fan_fold.bind_cache_key).  Deterministic; ~12 min.
Run with Blender's Python:  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" WorkFiles/fan/run_fold_optimisation.py"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import fan_fold as F
from props_lib.fan_spec import FAN
t0 = time.time()
key = F.bind_cache_key(FAN)
off, rep = F.optimise_bind(FAN, iters=120, log=lambda m: print(m, round(time.time() - t0), flush=True))
out = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/fold_bind_cache.json")
out.write_text(json.dumps({"key": key, "offsets": np.asarray(off).tolist(), "report": rep}, indent=1))
print("wrote", out, key, rep, flush=True)
