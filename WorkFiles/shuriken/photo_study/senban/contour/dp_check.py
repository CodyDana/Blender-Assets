# Cross-check: fit the side circles to the Douglas-Peucker (1.5 px) vertices only, instead of the dense contour.
import sys, math, numpy as np
D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/"
sys.path.insert(0, D)
from measure import run, arclen
from geom import douglas_peucker, fit_circle, fit_line
R = run(); A = R["_arrays"]
c = A["c_ref"]; corners = A["corners"]
for k, si in enumerate(A["sides"]):
    p = c[si]; s = arclen(p); s /= s[-1]
    core = p[(s >= 0.08) & (s <= 0.92)]
    v, _ = douglas_peucker(core, 1.5)
    cx, cy, Rr, rms, _ = fit_circle(v)
    A0, B0 = corners[k], corners[(k + 1) % 4]; chord = np.hypot(*(B0 - A0)); u = (B0 - A0) / chord; nin = np.array([-u[1], u[0]])
    sag = Rr - abs((np.array([cx, cy]) - A0) @ nin)
    print(["top", "right", "bottom", "left"][k], "DP vertices", len(v), "R", round(Rr, 1), "sag", round(sag, 2), "sag/chord", round(sag / chord, 4), "rms", round(rms, 2))
h = A["h_ref"]; hv, _ = douglas_peucker(np.r_[h, h[:1]], 1.5); print("hole DP vertices", len(hv) - 1)
