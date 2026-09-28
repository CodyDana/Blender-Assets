import os, sys, json, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import paperbomb_art as A, paperbomb_tracedart as TA, paperbomb_fidelity as FD, trace as T
from props_lib import atlas as AT
from props_lib.spec import PAPER_BOMB
import xt_io
plan = AT.plan_for(PAPER_BOMB)
m = TA.reference_model()
for rim in [float(v) for v in sys.argv[1].split(",")]:
    TA.POOL_RIM_MM = rim
    cfg = A.ArtConfig(ppmm=plan.ppmm, seed=20260919, supersample=2, pad_mm=plan.pad_mm)
    front = A.build_front(cfg)
    fid = FD.score(front.base_colour, front.card_mask, plan.ppmm, plan.pad_mm, model=m)
    e = fid["elements"]["corner_TL"]
    print(rim, "IoU", e["iou"], "edge mm", e["edge_mean_mm"], "black", {k: e["layers"]["black"][k] for k in ("iou", "ink_px_pred", "edge_mean_px", "de_median")})
    np.save("rim_%s_bc.npy" % rim, front.base_colour)
