# Quick polar look at the outer contour around the hole centre: tips, hub band.
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = np.load(os.path.join(OUT, "contours.npz"))
outer, hc = c["outer"], c["hole"]
hf = fit_circle(hc)
print("hole fit", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in hf.items()})
C = np.array([hf["cx"], hf["cy"]])
d = outer - C
r = np.hypot(d[:, 0], d[:, 1]); th = np.degrees(np.arctan2(-d[:, 1], d[:, 0]))  # math angle, y up
# smooth r along contour
n = len(r)
k = 7
rs = np.convolve(np.r_[r[-k:], r, r[:k]], np.ones(2 * k + 1) / (2 * k + 1), 'valid')
# local maxima with large window
w = 150
peaks = [i for i in range(n) if rs[i] == max(rs[(i + j) % n] for j in range(-w, w + 1)) and rs[i] > np.percentile(rs, 80)]
print("peaks", [(i, round(float(r[i]), 1), round(float(th[i]), 1), outer[i].tolist()) for i in peaks])
mins = [i for i in range(n) if rs[i] == min(rs[(i + j) % n] for j in range(-w, w + 1))]
print("mins", [(i, round(float(r[i]), 1), round(float(th[i]), 1), outer[i].tolist()) for i in mins])
h, e = np.histogram(r, bins=40, range=(250, 650))
print("r hist", list(zip(e[:-1].astype(int).tolist(), h.tolist())))
