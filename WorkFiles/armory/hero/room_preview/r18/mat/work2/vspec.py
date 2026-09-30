import sys
import numpy as np
from PIL import Image
for p in sys.argv[1:]:
    a = np.asarray(Image.open(p).convert("RGB")).astype(float) @ [0.299, 0.587, 0.114]
    out = []
    for (y0, y1, x0, x1) in ((960, 1060, 650, 800), (960, 1060, 820, 980)):
        cb = a[y0:y1, x0:x1]
        # detrend: remove a 9-px vertical moving average (the sun stripes / shading)
        k = 9
        pad = np.pad(cb, ((k, k), (0, 0)), mode="edge")
        cs = np.cumsum(pad, 0)
        ma = (cs[2 * k:] - cs[:-2 * k])[: cb.shape[0]] / (2 * k)
        d = cb - ma
        n = 1024
        S = (np.abs(np.fft.rfft(d * np.hanning(d.shape[0])[:, None], n=n, axis=0)) ** 2).mean(1)
        f = np.fft.rfftfreq(n)
        m = (f > 1 / 20) & (f < 1 / 3.2)
        per = 1 / f[m]
        s = S[m]
        top = np.argsort(s)[::-1][:3]
        # horizontal
        dh = cb - cb.mean(1, keepdims=True)
        Sh = (np.abs(np.fft.rfft(dh * np.hanning(dh.shape[1])[None, :], n=n, axis=1)) ** 2).mean(0)
        mh = (f > 1 / 20) & (f < 1 / 3.2)
        out.append(f"x{x0}-{x1}: vert peaks {[round(float(per[i]),1) for i in top]} conc {s.max()/np.median(s):.1f} "
                   f"vert/horiz energy {s.sum()/Sh[mh].sum():.2f} | horiz peak {1/f[mh][np.argmax(Sh[mh])]:.2f} "
                   f"conc {Sh[mh].max()/np.median(Sh[mh]):.1f} | std/mean {cb.std()/cb.mean():.3f}")
    print(p.split('/')[-1], *out, sep="\n  ")
