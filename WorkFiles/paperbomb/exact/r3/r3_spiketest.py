"""Fit the claw spikes on the stored traced frame red; write a zoom of the result."""
import os, sys, math, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT, paperbomb_finefit as FF
import xt_io
OUT = os.path.dirname(os.path.abspath(__file__))
if not hasattr(FF, "fit_spike"):
    exec(open(os.path.join(OUT, "spike_chunk.py"), encoding="utf-8").read(), FF.__dict__)
L = PT.load_layers(); fit = L.fit
data = PT.load_traced()
g = [g for g in data["groups"] if g["group"] == "frame" and g["layer"] == "red"][0]
loops = []
for p in PT.contour_only_polys_mm(g, 0.01):
    x, y = fit.mm_to_px(p[:, 0], p[:, 1]); loops.append(np.stack([x, y], 1))
PX = {"claw_BL_long": (46.1, 626.6), "claw_BL_short": (42.3, 619.9), "claw_BR_spike": (257.2, 627.0),
      "claw_BR_hook": (267.3, 616.2), "claw_BR_prong": (260.1, 613.8)}
for k, v in PX.items():
    print(k, "tip mm", [round(float(a), 3) for a in fit.px_to_mm(*v)])
res = []
only = sys.argv[1].split(",") if len(sys.argv) > 1 else None
for spec in FF.SPIKES:
    if only and spec["name"] not in only:
        continue
    r = FF.fit_spike(spec, loops, L.red_behind, L.density["red"], fit)
    print(spec["name"], "traced", r["loss_traced"], "init", r["loss_init"], "fit", r["loss_fit"], r["params_px"])
    res.append(r)
# zoom: reference | old traced fill | new fill
for name, (x0, x1, y0, y1, F) in {"cBL": (20, 60, 592, 636, 12), "cBR": (244, 284, 592, 636, 12)}.items():
    nx, ny = (x1 - x0) * F, (y1 - y0) * F
    px, py = np.meshgrid(x0 + (np.arange(nx) + 0.5) / F, y0 + (np.arange(ny) + 0.5) / F)
    ref = L.src.rgb[py.astype(int), px.astype(int)]
    tz = lambda q: (q - np.array([x0, y0])) * F
    old = T.fill_polys([tz(q) for q in loops], ny, nx, ss=2)
    cut = [tz(r["cut_px"]) for r in res]; ink = [tz(r["ink_px"]) for r in res]
    new = old * (1 - (T.fill_polys(cut, ny, nx, ss=2) if cut else 0))
    if ink:
        new = np.maximum(new, T.fill_polys(ink, ny, nx, ss=2))
    ov = ref.copy()
    b = new > 0.5; e = b ^ T.erode(b, 1); ov[e] = (0, 0.9, 1)
    sep = np.ones((ny, 6, 3)) * 0.5
    g3 = lambda a: np.repeat((1 - a)[..., None], 3, -1)
    xt_io.write(os.path.join(OUT, "spk_%s.png" % name), np.concatenate([ref, sep, g3(old), sep, g3(new), sep, ov], 1))
