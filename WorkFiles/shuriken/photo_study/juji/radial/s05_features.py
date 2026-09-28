"""Feature images to understand edges: chromaticity, gradient magnitude, locally-normalised contrast."""
import sys, os
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape


def gblur(img, s):
    r = int(3 * s + 0.5)
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / s) ** 2)
    k /= k.sum()
    p = np.pad(img, [(r, r), (0, 0)] + [(0, 0)] * (img.ndim - 2), mode='edge')
    out = np.zeros_like(img, dtype=np.float32)
    for i, kv in enumerate(k):
        out += kv * p[i:i + img.shape[0]]
    p = np.pad(out, [(0, 0), (r, r)] + [(0, 0)] * (img.ndim - 2), mode='edge')
    out2 = np.zeros_like(img, dtype=np.float32)
    for i, kv in enumerate(k):
        out2 += kv * p[:, i:i + img.shape[1]]
    return out2


s = a.sum(2) + 1e-3
cr = a[:, :, 0] / s
cb = a[:, :, 2] / s
warm = cr - cb
lum = a.mean(2)
print("warm bg median", np.median(warm[:20]), "p99", np.percentile(warm[:20], 99))
jlib.save_png(os.path.join(jlib.OUT, "dbg_warmchroma.png"), np.clip((warm - 0.02) * 6, 0, 1))
ab = gblur(a, 1.5)
gy = np.zeros(ab.shape[:2], np.float32)
gx = np.zeros(ab.shape[:2], np.float32)
gy[1:-1] = np.linalg.norm(ab[2:] - ab[:-2], axis=2) / 2
gx[:, 1:-1] = np.linalg.norm(ab[:, 2:] - ab[:, :-2], axis=2) / 2
g = np.sqrt(gx ** 2 + gy ** 2)
print("grad pct 50/90/99", np.percentile(g, [50, 90, 99]))
jlib.save_png(os.path.join(jlib.OUT, "dbg_grad.png"), np.clip(g * 25, 0, 1))
# local contrast: lum minus large-scale blur
lb = gblur(lum, 20)
jlib.save_png(os.path.join(jlib.OUT, "dbg_localcontrast.png"), np.clip((lum - lb) * 4 + 0.5, 0, 1))
np.savez_compressed(os.path.join(jlib.OUT, "feat.npz"), warm=warm, grad=g)
