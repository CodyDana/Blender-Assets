import os, sys, math
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
name = sys.argv[1]
spec = [s for s in FF.SPIKES if s["name"] == name][0]
tx, ty = fit.mm_to_px(*spec["tip_mm"])
fr = FF.spike_frame(loops, (tx, ty), spec["cut_mm"] * fit.ppmm)
loop = loops[fr["loop"]]
print({k: (np.round(v, 2).tolist() if isinstance(v, np.ndarray) else v) for k, v in fr.items()})
mid = 0.5 * (fr["E1"] + fr["E2"]); th0 = math.atan2(*(fr["tip"] - mid)[::-1]); Lp = float(np.hypot(*(fr["tip"] - mid)))
p0 = [fr["tip"][0], fr["tip"][1], th0, 0.1, 0.35 * Lp, 0.35 * Lp, 0.3 * Lp, 0.3 * Lp]
cut, ink = FF.spike_polys(p0, fr, loop)
print("areas", T.signed_area(cut), T.signed_area(ink), T.signed_area(loop), len(ink))
c = fr["tip"]; F = 24; R = 10
x0, y0 = c[0] - R, c[1] - R
tz = lambda q: (q - np.array([x0, y0])) * F
n = 2 * R * F
base = T.fill_polys([tz(q) for q in loops], n, n, ss=2)
cm = T.fill_polys([tz(cut)], n, n, ss=2); im = T.fill_polys([tz(ink)], n, n, ss=2)
img = np.stack([base, cm, im], -1)
xt_io.write(os.path.join(OUT, "spkdbg_%s.png" % name), img)
win = FF._Window(loops, L.red_behind, L.density["red"], int(c[0]) - 8, int(c[1]) - 8, int(c[0]) + 8, int(c[1]) + 8)
cutm = T.fill_polys([cut - win.off], win.h, win.w, ss=16)
inkm = T.fill_polys([ink - win.off], win.h, win.w, ss=16)
bc = win.base * (1 - cutm)
np.set_printoptions(linewidth=250, precision=2, suppress=True)
print("base"); print(win.base)
print("cut"); print(cutm)
print("ink"); print(inkm)
def lc(cov):
    pred = T.gauss_blur(cov, T.SOURCE_PSF_SIGMA_PX) * win.dens
    d = pred - win.obs
    return float((d[win.inner] ** 2).sum())
print("dens", win.dens.flat[0], "traced", lc(win.base), "init", lc(np.maximum(bc, inkm)), "cutonly", lc(bc))
print("obs"); print(win.obs)
