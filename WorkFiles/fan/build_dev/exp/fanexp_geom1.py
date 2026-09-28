import sys, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib.fan_spec import FAN
from props_lib import fan_fold as F
from props_lib import fan_geom as G
fs = F.FoldSolver(FAN)
atl = None
for lod in range(3):
    mb, info, atl = G.build_lod(FAN, lod, fs.tpl, atl)
    uv = np.concatenate(mb.TUV)
    print(info, "uv range", uv.min(0).round(4), uv.max(0).round(4))
    # uv overlap check per slot (rasterise coarse)
    for slot in range(3):
        sel = [i for i, s in enumerate(mb.TS) if s == slot and mb.TP[i] != "x"]
        # skip back layers for leaf (shared UVs by design)
        if slot == 0:
            sel = [i for i in sel if mb.P[mb.T[i][0]] is not None]
        print("  slot", slot, "tris", len(sel))
