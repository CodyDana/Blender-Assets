"""r1 quick loop: build the traced front at ss (arg1, default 1), score it, write previews."""
import os, sys, json, time
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import paperbomb_art as A
from props_lib import paperbomb_tracedart as TA
from props_lib import paperbomb_fidelity as FD
from props_lib import trace as T
import xt_io
ss = int(sys.argv[1]) if len(sys.argv) > 1 else 1
tag = sys.argv[2] if len(sys.argv) > 2 else "q"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
t0 = time.time()
cfg = A.ArtConfig(ppmm=12.923, seed=20260919, supersample=ss, pad_mm=1.6)
m = TA.reference_model()
print("model", round(time.time() - t0, 1), json.dumps(m.stats))
t1 = time.time()
front = A.build_front(cfg)
print("front", front.width, front.height, round(time.time() - t1, 1))
np.save(os.path.join(OUT, "r1_%s_bc.npy" % tag), front.base_colour)
np.save(os.path.join(OUT, "r1_%s_card.npy" % tag), front.card_mask)
xt_io.write(os.path.join(OUT, "r1_%s_bc.png" % tag), T.linear_to_srgb(front.base_colour))
t2 = time.time()
fid = FD.score(front.base_colour, front.card_mask, 12.923, 1.6, model=m)
print("score", round(time.time() - t2, 1))
for k, v in fid["elements"].items():
    print("  %-10s IoU %.4f edge %.4f mm p95 %s  dE med %s mean %s" % (k, v["iou"], v["edge_mean_mm"] or -1, v.get("edge_p95_mm"), v.get("de_median"), v.get("de_mean")))
print("  paper", json.dumps(fid.get("paper")))
print("  card dE mean", fid["card_de_mean"], "p90", fid["card_de_p90"])
g = FD.gates(fid)
print("  gates failing:", [k for k, v in g.items() if not v["passed"]])
json.dump(FD.public(fid), open(os.path.join(OUT, "r1_%s_fid.json" % tag), "w"), indent=1)
json.dump(front.report.get("text"), open(os.path.join(OUT, "r1_%s_text.json" % tag), "w"), indent=1)
src = m.L.src.rgb
xt_io.write(os.path.join(OUT, "r1_%s_photo_vs_ref.png" % tag),
            np.concatenate([src, np.ones((src.shape[0], 4, 3)), fid["_photo"],
                            np.ones((src.shape[0], 4, 3)),
                            np.repeat(np.clip(fid["_de"] / 20.0, 0, 1)[..., None], 3, -1)], 1), scale=2)
