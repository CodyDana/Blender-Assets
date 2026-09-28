"""Probe: fine-scale texture energy to separate the in-focus metal face from smooth scanner shadows."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C


def box(a, r):
    k = 2 * r + 1
    P = np.pad(a, r, mode='edge').astype(np.float64)
    S = np.zeros((P.shape[0] + 1, P.shape[1] + 1))
    S[1:, 1:] = P.cumsum(0).cumsum(1)
    return ((S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]) / (k * k)).astype(np.float32)


rgb, info = C.load_rgb(C.IMG)
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
g = box(box(box(lum, 2), 2), 2)
hp = np.abs(lum - g)
E = box(hp, 4)
np.save(os.path.join(C.OUT, "texture_E.npy"), E.astype(np.float16))
for name, (x0, y0, x1, y1) in dict(bg=(100, 1800, 400, 2400), metal=(1150, 1150, 1450, 1450),
                                  shadow_core=(1600, 1166, 2000, 1172), ramp_right=(1455, 600, 1500, 800),
                                  hook_shadow=(600, 80, 800, 110)).items():
    v = E[y0:y1, x0:x1]
    print("E %-12s mean %.4f p5 %.4f p50 %.4f p95 %.4f" % (name, v.mean(), *np.percentile(v, [5, 50, 95])))
C.save_png(np.clip(E / 0.04, 0, 1)[::2, ::2], os.path.join(C.OUT, "texture_E_half.png"))
