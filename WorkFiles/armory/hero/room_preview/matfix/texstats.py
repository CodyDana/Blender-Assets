"""matfix: mat-field texture stats in a C1 1448x1086 image: mean sRGB, nub-scale contrast (std of a high-pass),
and the strongest periods (px) across (x) and along (y) from row / column spectra. Usage: texstats.py img [img...]"""
import sys
import numpy as np
from PIL import Image


def blur(a, s=3.0):
    k = np.exp(-0.5 * (np.arange(-3 * int(s), 3 * int(s) + 1) / s) ** 2); k /= k.sum()
    a = np.apply_along_axis(lambda r: np.convolve(r, k, 'same'), 1, a)
    return np.apply_along_axis(lambda c: np.convolve(c, k, 'same'), 0, a)


def stats(path, box=(560, 965, 900, 1060)):
    im = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    x0, y0, x1, y1 = box
    r = im[y0:y1, x0:x1]
    L = r @ np.array([0.2126, 0.7152, 0.0722])
    hp = (L - blur(L))[10:-10, 10:-10]
    Lx = L - L.mean(1, keepdims=True)
    sx = np.abs(np.fft.rfft(Lx, axis=1)).mean(0); fx = np.fft.rfftfreq(L.shape[1])
    Ly = L - L.mean(0, keepdims=True)
    sy = np.abs(np.fft.rfft(Ly, axis=0)).mean(1); fy = np.fft.rfftfreq(L.shape[0])
    def peaks(s, f):
        m = (f > 1 / 12) & (f < 1 / 2.2)
        i = np.argsort(s[m])[::-1][:2]
        return [round(1 / f[m][j], 1) for j in i], round(float(s[m].max() / np.median(s[m])), 1)
    return {"mean_srgb": [round(float(v) * 255) for v in r.reshape(-1, 3).mean(0)], "L": round(float(L.mean()), 3),
            "hp_std": round(float(hp.std()), 4), "rel_hp": round(float(hp.std() / L.mean()), 3),
            "px_x": peaks(sx, fx), "px_y": peaks(sy, fy)}


for p in sys.argv[1:]:
    print(p.split("/")[-1][-60:], stats(p))
