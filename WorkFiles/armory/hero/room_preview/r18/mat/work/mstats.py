"""r18 mat stats at C1 1448x1086: rib period (2D FFT), rib/row spectral energy, field colour, border band widths.
usage: py -3 mstats.py IMG [IMG ...]"""
import sys, numpy as np
from PIL import Image
from numpy.fft import fft2, fftshift, fftfreq

def spec(L, box):
    x0, y0, x1, y1 = box
    a = L[y0:y1, x0:x1].copy(); a -= a.mean()
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1])); N = 512
    F = np.abs(fftshift(fft2(a * w, (N, N)))); f = fftshift(fftfreq(N))
    FY, FX = np.meshgrid(f, f, indexing='ij')
    tot = F[np.hypot(FX, FY) > 1 / 25].sum()
    col = (np.abs(FX) > 1 / 11) & (np.abs(FX) < 1 / 5.5) & (np.abs(FY) < 1 / 20)
    row = (np.abs(FY) > 1 / 10) & (np.abs(FY) < 1 / 2.5) & (np.abs(FX) < 1 / 20)
    G = F * col; i = np.unravel_index(np.argmax(G), G.shape)
    return 1 / abs(FX[i]), F[col].sum() / tot, F[row].sum() / tot

def run_len(prof, start, step, thr):
    """length of the dark run met walking from start in direction step (skips up to 6 lit px before the run)."""
    i, n, seen = start, 0, False
    for _ in range(60):
        if i < 0 or i >= len(prof): break
        if prof[i] < thr: n += 1; seen = True
        elif seen: break
        i += step
    return n

def stats(p):
    im = np.asarray(Image.open(p).convert('RGB')).astype(float)
    L = im.mean(-1)
    per, cb, rb = zip(*[spec(L, b) for b in ((560, 985, 760, 1045), (760, 985, 960, 1045), (600, 950, 900, 985))])
    f = im[950:1060, 460:990].reshape(-1, 3); fl = f.mean(1)
    sh = f[fl < 140].mean(0) if (fl < 140).any() else np.zeros(3)
    sun = f[fl >= 140].mean(0) if (fl >= 140).any() else np.zeros(3)
    out = {'rib_px': [round(v, 2) for v in per], 'rib_E': round(float(np.mean(cb)), 3), 'row_E': round(float(np.mean(rb)), 3),
           'field_mean': f.mean(0).round(1).tolist(), 'shade_mean': sh.round(1).tolist(), 'sun_mean': sun.round(1).tolist(),
           'sun_frac': round(float((fl >= 140).mean()), 3), 'white_frac': round(float((f.min(1) > 200).mean()), 3),
           'p10_50_90': np.percentile(fl, [10, 50, 90]).round(1).tolist()}
    # side bands: walk outward from 40 px inside the field edge; the field edge found as the outermost column with
    # L > 0.7 * row field median, scanning in from the known band region
    side = []
    for y in (965, 985, 1005, 1025, 1045):
        row = L[y - 1:y + 2].mean(0)
        med = np.median(row[520:930])
        thr = 0.55 * med
        # left: from x=470 walk left to the first dark run
        side.append(('L', y, run_len(row, 470, -1, thr)))
        side.append(('R', y, run_len(row, 975, +1, thr)))
    out['side_dark_px'] = side
    ends = []
    for x in (560, 700, 840, 900):
        col = L[:, x - 2:x + 3].mean(1)
        med = np.median(col[960:1040])
        ends.append(('far', x, run_len(col, 962, -1, 0.55 * med)))
        ends.append(('near', x, run_len(col, 1045, +1, 0.55 * med)))
    out['end_dark_px'] = ends
    return out

for p in sys.argv[1:]:
    s = stats(p)
    print(p.split('/')[-3:])
    for k, v in s.items():
        print('  ', k, v)
