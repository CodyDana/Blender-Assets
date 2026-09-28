"""r3 diag: resid/tone fields of the reference model round the corner prongs, TL knob, TL sparkle."""
import os, sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact")
import numpy as np
from props_lib import trace as T, paperbomb_tracedart as TA
import xt_io
OUT = os.path.dirname(os.path.abspath(__file__))
m = TA.reference_model()
np.set_printoptions(linewidth=260, precision=2, suppress=True)
C = {"cBL": (20, 60, 592, 636), "cBR": (244, 284, 592, 636), "cTL": (20, 60, 24, 62)}
for n, (x0, x1, y0, y1) in C.items():
    sl = (slice(y0, y1), slice(x0, x1))
    F = 10
    def up(a):
        return np.repeat(np.repeat(a, F, 0), F, 1)
    obs = m.L.red_behind[sl]; psf = m.psf["red"][sl]; res = m.resid["red"][sl]; tone = m.tone["red"][sl]
    kb = m.L.black[sl]; wf = m.wash_field[sl] * m.wash_weight[sl]; kres = m.resid["black"][sl]; kpsf = m.psf["black"][sl]
    panels = [obs, psf, np.clip(res * 3, 0, 1), np.clip((1 - tone) * 5, 0, 1), kb, kpsf, wf, np.clip(kres * 3, 0, 1)]
    row = []
    for p in panels:
        row += [up(p), np.ones((up(p).shape[0], 4))]
    xt_io.write(os.path.join(OUT, "diag_%s.png" % n), np.concatenate(row[:-1], 1))
    print(n, "resid red sum", round(float(res.sum()), 2), "px>0.05", int((res > 0.05).sum()),
          "tone<0.86 in shape", int(((tone < 0.86) & (psf > 0.5)).sum()), "black resid", round(float(kres.sum()), 2))
