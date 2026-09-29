"""r20_mat: mat-field stats in a C1 1448x1086 image: mean sRGB, the strongest periods (px) across (x) and along (y),
nub-scale contrast. Usage: texstats.py img [img...] (box default = the reference field's centre)"""
import sys
import numpy as np
from PIL import Image


def blur(a, s=3.0):
    k = np.exp(-0.5 * (np.arange(-3 * int(s), 3 * int(s) + 1) / s) ** 2); k /= k.sum()
    a = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, a)
    return np.apply_along_axis(lambda c: np.convolve(c, k, 'same'), 0, a)


def stats(path, box):
    im = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    x0, y0, x1, y1 = box
    r = im[y0:y1, x0:x1]
    L = r @ np.array([0.2126, 0.7152, 0.0722])
    hp = (L - blur(L))[8:-8, 8:-8]
    def spec(A, ax):
        A = A - blur(A, 6.0)
        s = np.abs(np.fft.rfft(A * np.hanning(A.shape[ax]).reshape((-1, 1) if ax == 0 else (1, -1)), n=512, axis=ax))
        s = s.mean(1 - ax); f = np.fft.rfftfreq(512)
        m = (f > 1 / 16) & (f < 1 / 2.5)
        i = np.argmax(s[m])
        return round(1 / f[m][i], 2), round(float(s[m].max() / np.median(s[m])), 1)
    return {"mean_srgb": [round(float(v) * 255) for v in r.reshape(-1, 3).mean(0)], "L": round(float(L.mean()), 3),
            "rel_hp": round(float(hp.std() / L.mean()), 3), "px_x": spec(L, 1), "px_y": spec(L, 0)}


box = (560, 975, 900, 1055)
for p in sys.argv[1:]:
    print(p.replace("\\", "/").split("/")[-1][-50:], stats(p, box))
