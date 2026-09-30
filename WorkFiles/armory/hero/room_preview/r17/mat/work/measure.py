import sys, numpy as np
from PIL import Image
def prof(path, rows, x0, x1):
    im = np.asarray(Image.open(path).convert('L')).astype(float)
    out=[]
    for y in rows:
        band = im[y-3:y+4, x0:x1].mean(0)
        band = band - np.convolve(band, np.ones(15)/15, 'same')
        band = band[10:-10]*np.hanning(len(band)-20)
        F = np.abs(np.fft.rfft(band, 8192))
        f = np.fft.rfftfreq(8192)
        m = (f>1/20)&(f<1/2.2)
        i = np.argmax(F*m)
        out.append((y, round(1/f[i],2)))
    return out
def vprof(path, cols, y0, y1):
    im = np.asarray(Image.open(path).convert('L')).astype(float)
    out=[]
    for x in cols:
        band = im[y0:y1, x-10:x+11].mean(1)
        band = band - np.convolve(band, np.ones(11)/11, 'same')
        band = band[6:-6]*np.hanning(len(band)-12)
        F = np.abs(np.fft.rfft(band, 8192)); f=np.fft.rfftfreq(8192)
        m=(f>1/20)&(f<1/2.2); i=np.argmax(F*m)
        out.append((x, round(1/f[i],2)))
    return out
def edges(path, rows):
    im = np.asarray(Image.open(path).convert('RGB')).astype(float)
    return [(y, [round(v) for v in im[y, 300:1150:25].mean(-1)]) for y in rows]
p=sys.argv[1]
print('H period', prof(p, [955, 975, 1000, 1025, 1050, 1070], 480, 980))
print('V period', vprof(p, [560, 720, 880], 950, 1065))
