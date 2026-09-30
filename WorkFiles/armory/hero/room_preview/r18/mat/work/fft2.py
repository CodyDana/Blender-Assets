"""r18 mat: 2D FFT peaks of the mat field patches (reference 2 vs renders at C1 1448x1086)."""
import sys, numpy as np
from PIL import Image
def peaks(path, box, k=6):
    L = np.asarray(Image.open(path).convert('L')).astype(float)
    x0, y0, x1, y1 = box
    a = L[y0:y1, x0:x1]
    from numpy.fft import fft2, fftshift, fftfreq
    # remove low-freq trend
    kk = np.ones(15) / 15
    sm = np.apply_along_axis(lambda r: np.convolve(r, kk, 'same'), 1, a)
    sm = np.apply_along_axis(lambda c: np.convolve(c, kk, 'same'), 0, sm)
    a = (a - sm)[8:-8, 8:-8]
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    N = 512
    F = np.abs(fftshift(fft2(a * w, (N, N))))
    fy = fftshift(fftfreq(N)); fx = fftshift(fftfreq(N))
    FY, FX = np.meshgrid(fy, fx, indexing='ij')
    r = np.hypot(FX, FY)
    F[(r < 1/25) | (r > 1/2.5)] = 0
    F[FY < 0] = 0
    out = []
    for _ in range(k):
        i = np.unravel_index(np.argmax(F), F.shape)
        out.append((round(float(FX[i]), 4), round(float(FY[i]), 4), round(float(F[i])), 'px/cyc x %.2f y %.2f' % (1/abs(FX[i]) if FX[i] else 0, 1/abs(FY[i]) if FY[i] else 0)))
        F[max(0,i[0]-6):i[0]+7, max(0,i[1]-6):i[1]+7] = 0
    return out
for p in sys.argv[1:]:
    print(p.split('/')[-1])
    for box in ((560, 985, 760, 1045), (760, 985, 960, 1045), (600, 950, 900, 985)):
        print('  ', box, peaks(p, box))
