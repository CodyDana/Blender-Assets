import os, sys, math
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T, paperbomb_trace as PT, paperbomb_finefit as FF
import xt_io
OUT = os.path.dirname(os.path.abspath(__file__))
L = PT.load_layers(); fit = L.fit
data = PT.load_traced()
g = [g for g in data["groups"] if g["group"] == "seal_big"][0]
base = []
for q in PT.contour_only_polys_mm(g, 0.01):
    x, y = fit.mm_to_px(q[:, 0], q[:, 1]); base.append(np.stack([x, y], 1))
old = {k["name"]: k for k in g["knockouts_mm"]}
res = {}
KIND = sys.argv[1] if len(sys.argv) > 1 else "star"; SOFT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
TAG = "%s_%s" % (KIND, SOFT)
for spec in FF.KNOCKOUTS[:1]:
    spec = dict(spec, kind=KIND, soft_px=SOFT)
    r = FF.fit_knockout(spec, [b.copy() for b in base], L.red_behind, L.density["red"], fit)
    print(spec["name"], spec["kind"], "loss", r["loss_traced_holes_removed"], r["loss_init"], r["loss_fit"], "old", old[spec["name"]]["loss"])
    print("  params", r["params_px"])
    res[spec["name"]] = r
for name, (x0, x1, y0, y1, F) in {"TL": (42, 62, 496, 518, 20)}.items():
    nx, ny = (x1 - x0) * F, (y1 - y0) * F
    px, py = np.meshgrid(x0 + (np.arange(nx) + 0.5) / F, y0 + (np.arange(ny) + 0.5) / F)
    ref = L.src.rgb[py.astype(int), px.astype(int)]
    tz = lambda q: (q - np.array([x0, y0])) * F
    bm = T.fill_polys([tz(q) for q in base], ny, nx, ss=2)
    oldp = []
    for k in old.values():
        for q in k["polys_mm"]:
            q = np.asarray(q); x, y = fit.mm_to_px(q[:, 0], q[:, 1]); oldp.append(tz(np.stack([x, y], 1)))
    newp = [tz(q) for r in res.values() for q in r["polys_px"]]
    o = bm * (1 - T.fill_polys(oldp, ny, nx, ss=2)); en = T.fill_polys(newp, ny, nx, ss=2)
    if SOFT > 0: en = T.gauss_blur(np.asarray(en, np.float64), SOFT * F)
    n = bm * (1 - en)
    # photographed: box-average to the source grid then nearest back up
    def photo(c):
        s = c.reshape(y1 - y0, F, x1 - x0, F).mean((1, 3))
        s = T.gauss_blur(s, T.SOURCE_PSF_SIGMA_PX)
        return np.repeat(np.repeat(s, F, 0), F, 1)
    g3 = lambda a: np.repeat((1 - a)[..., None], 3, -1)
    sep = np.ones((ny, 6, 3)) * 0.5
    xt_io.write(os.path.join(OUT, "glint_%s_%s.png" % (name, TAG)), np.concatenate([ref, sep, g3(o), sep, g3(n), sep, g3(photo(n))], 1))
