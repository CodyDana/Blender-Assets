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
E5 = box(np.abs(lum - box(lum, 1)), 2)
l3 = box(lum, 1)
for reg, (x0, y0, x1, y1) in dict(bevel_left_hook=(106, 1700, 114, 1800), bevel_tip=(125, 2050, 140, 2080), corner_block=(1432, 60, 1450, 75),
                                  face=(1150, 1150, 1450, 1450), ramp_right=(1455, 600, 1500, 800), bhook_band=(1900, 2340, 1950, 2350),
                                  rust_strip_top_hook=(920, 114, 1000, 120)).items():
    v = E5[y0:y1, x0:x1]; L = l3[y0:y1, x0:x1]
    print("P %-20s E5 p5 %.4f p50 %.4f p95 %.4f | lum p5 %.3f p50 %.3f p95 %.3f" % (reg, *np.percentile(v, [5, 50, 95]), *np.percentile(L, [5, 50, 95])))
