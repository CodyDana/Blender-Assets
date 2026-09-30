"""r18 mat (second pass): the field's weave pitch across (px and m) and the along-rib spectrum, per row band, for any
C1 1448x1086 image (reference 2 or a render). usage: py -3 pitch.py img [img...]"""
import sys
import numpy as np
from PIL import Image
dz = 3.435
def Y(row):
    v = -11.34 - (row - 543) / 1086 * 27
    return -4.18 + 40 * dz / (-v)
def pxm(row):
    return 40 / (Y(row) + 4.18) / 36 * 1448
def vpxm(row):   # rows per metre along Y at this row
    return 1.0 / abs(Y(row + 0.5) - Y(row - 0.5))
for p in sys.argv[1:]:
    a = np.asarray(Image.open(p).convert("RGB")).astype(float)
    L = a @ [0.299, 0.587, 0.114]
    print(p)
    for (y0, y1) in ((955, 985), (985, 1015), (1015, 1045), (1045, 1068)):
        for (x0, x1) in ((470, 640), (640, 810), (810, 980)):
            P = np.zeros(x1 - x0)
            for y in range(y0, y1):
                r = L[y, x0:x1] - L[y, x0:x1].mean()
                r = r * np.hanning(len(r))
                P += np.abs(np.fft.rfft(r, n=len(r))) ** 2 if False else 0
            # horizontal spectrum
            blk = L[y0:y1, x0:x1]
            blk = blk - blk.mean(1, keepdims=True)
            w = np.hanning(x1 - x0)
            n = 2048
            S = (np.abs(np.fft.rfft(blk * w, n=n, axis=1)) ** 2).mean(0)
            f = np.fft.rfftfreq(n)
            m = (f > 1 / 14) & (f < 1 / 4)
            ph = 1 / f[m][np.argmax(S[m])]
            # vertical spectrum (columns)
            cb = L[y0 - 10:y1 + 10, x0:x1]
            cb = cb - cb.mean(0, keepdims=True)
            wv = np.hanning(cb.shape[0])[:, None]
            Sv = (np.abs(np.fft.rfft(cb * wv, n=n, axis=0)) ** 2).mean(1)
            mv = (f > 1 / 25) & (f < 1 / 3.5)
            pv = 1 / f[mv][np.argmax(Sv[mv])]
            conc = Sv[mv].max() / Sv[mv].mean()
            blkc = L[y0:y1, x0:x1]
            yc = (y0 + y1) / 2
            rgb = a[y0:y1, x0:x1].reshape(-1, 3).mean(0)
            print(f"  y{y0}-{y1} x{x0}-{x1}: across {ph:.2f}px = {100*ph/pxm(yc):.2f}cm | along peak {pv:.2f}px "
                  f"= {100*pv/vpxm(yc):.2f}cm peak/mean {conc:.1f} | std/mean {blkc.std()/blkc.mean():.3f} "
                  f"mean L {blkc.mean():.0f} rgb {rgb.round(0)} R/B {rgb[0]/rgb[2]:.2f}")
