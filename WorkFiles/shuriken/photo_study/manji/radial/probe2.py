import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
def box(a, r):
    k = 2 * r + 1
    P = np.pad(a, r, mode='edge').astype(np.float64)
    S = np.zeros((P.shape[0] + 1, P.shape[1] + 1)); S[1:, 1:] = P.cumsum(0).cumsum(1)
    return ((S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]) / (k * k)).astype(np.float32)
rgb, info = C.load_rgb(C.IMG)
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
for name, hp in (("r1", np.abs(lum - box(lum, 1))), ("r2", np.abs(lum - box(lum, 2)))):
    for rr in (1, 2, 3):
        E = box(hp, rr)
        out = []
        for reg, (x0, y0, x1, y1) in dict(bg=(1700, 300, 2100, 700), face=(1150, 1150, 1450, 1450),
                                          core=(1600, 1162, 2000, 1170), ramp_up=(1600, 1130, 2000, 1150),
                                          ramp_right=(1452, 600, 1500, 800), hook_face=(650, 125, 750, 140),
                                          hook_shadow=(650, 95, 750, 112), rarm_face_nearedge=(1600, 1186, 2000, 1195)).items():
            v = E[y0:y1, x0:x1]
            out.append("%s p5 %.4f p50 %.4f p95 %.4f" % (reg, *np.percentile(v, [5, 50, 95])))
        print(name, "box", rr, " | ".join(out))
