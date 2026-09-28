# final pass: refit the big seal's top-left sparkle with a larger window / less softness and
# score every variant in ONE common window against the reference's observed red.
import sys, time, copy
from pathlib import Path
PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(PROJECT / "Scripts")); sys.path.insert(0, str(PROJECT / "Scripts" / "props"))
import numpy as np
from props_lib import paperbomb_trace as PT, paperbomb_finefit as FF, trace as T

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
name = argv[0] if argv else "seal_spark_TL"
variants = [v.split(":") for v in (argv[1].split(",") if len(argv) > 1 else ["2.4:0.45", "3.0:0.45", "3.0:0.25", "3.0:0.0"])]
L = PT.load_layers(); fit = L.fit
data = PT.load_traced(verify_source=False)
entry = next(g for g in data["groups"] if g["group"] == "seal_big" and g["layer"] == "red")
base_mm = PT.group_polys_mm(entry)
base_px = []
for q in base_mm:
    x, y = fit.mm_to_px(q[:, 0], q[:, 1]); base_px.append(np.stack([x, y], 1))
# the other knockouts in this group stay erased (their polygons) - only 'name' is refitted
others = [k for k in entry["knockouts_mm"] if k["name"] != name]
obs = PT.layer_field(L, "red", behind=True)
spec0 = next(k for k in FF.KNOCKOUTS if k["name"] == name)
cx, cy = fit.mm_to_px(*spec0["centre_mm"]); R = 3.4 * fit.ppmm
common = FF._Window(base_px, obs, L.density["red"], int(cx - R), int(cy - R), int(cx + R), int(cy + R))
def other_erase():
    out = []
    for k in others:
        for q in k["polys_mm"]:
            q = np.asarray(q); x, y = fit.mm_to_px(q[:, 0], q[:, 1]); out.append(np.stack([x, y], 1))
    return out
common_base = common.base.copy()
res = []
for half, soft in variants:
    spec = dict(spec0); spec["half_mm"] = float(half); spec["soft_px"] = float(soft)
    t0 = time.time()
    r = FF.fit_knockout(spec, base_px, obs, L.density["red"], fit)
    common.soft = float(soft)
    lc = common.loss(r["polys_px"])
    pred = common.render(r["polys_px"]); d = (pred - common.obs)[common.inner]
    # the long vertical ray: observed vs predicted paper deficit along the column through the centre
    res.append((half, soft, r["loss_fit"], lc, float((d ** 2).sum()), r["params_px"][:3], time.time() - t0))
    print("half %s soft %s: own-window loss %.4f  COMMON loss %.4f  sse %.4f  rays %s  %.0fs" % (
        half, soft, r["loss_fit"], lc, float((d ** 2).sum()),
        [(round(np.degrees(r["params_px"][7 + 4 * k])), round(r["params_px"][8 + 4 * k], 1)) for k in range(4)],
        time.time() - t0), flush=True)
common.soft = 0.0
print("no sparkle at all: COMMON loss %.4f" % common.loss([]))
