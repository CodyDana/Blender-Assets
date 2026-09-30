import sys, numpy as np
from PIL import Image
def peaks(p, box):
    L = np.asarray(Image.open(p).convert('L')).astype(float)
    x0,y0,x1,y1 = box
    a = L[y0:y1, x0:x1]
    from numpy.fft import fft2, fftshift, fftfreq
    k = 9
    ker = np.ones((k,k))/k/k
    # high-pass: subtract box blur
    kk=np.ones(15)/15
    b=np.apply_along_axis(lambda r: np.convolve(np.pad(r,7,mode='edge'),kk,'valid'),1,a)
    b=np.apply_along_axis(lambda r: np.convolve(np.pad(r,7,mode='edge'),kk,'valid'),0,b)
    a=a-b
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    F = np.abs(fftshift(fft2(a*w, s=(256,512))))**2
    fy = fftshift(fftfreq(256)); fx = fftshift(fftfreq(512))
    FY, FX = np.meshgrid(fy, fx, indexing='ij')
    fr = np.hypot(FX, FY)
    F[(fr < 1/25) | (fr > 1/2.2)] = 0
    F[FY < 0] = 0
    out = []
    for _ in range(6):
        i = np.unravel_index(np.argmax(F), F.shape)
        v = F[i]; fxv, fyv = FX[i], FY[i]
        out.append((round(float(v/1e3)), 'px_x', round(1/fxv,2) if abs(fxv)>1e-6 else 'inf', 'px_y', round(1/fyv,2) if abs(fyv)>1e-6 else 'inf'))
        F[max(0,i[0]-4):i[0]+5, max(0,i[1]-8):i[1]+9] = 0
    return out
for p in sys.argv[1:]:
    print(p.split('/')[-1])
    for b in [(600,990,860,1060),(600,950,860,990)]:
        print(' ', b, peaks(p, b))
