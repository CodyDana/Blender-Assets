"""Stage 13: along-path averaged cross profiles. For a path (polyline) and s-windows, average the
(blurred, log) luminance along s within each window at each offset v, then print the prominent minima
(crevices) and maxima (lit rims) with their image position.
args: hw win step x1 y1 x2 y2 ..."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

a = sys.argv[sys.argv.index('--') + 1:]
hw, win, step = int(a[0]), int(a[1]), int(a[2])
P = np.array([float(v) for v in a[3:]]).reshape(-1, 2)
rgb = L.load_srgb(); Y = L.lum(rgb)
Yl = np.log(np.clip(L.gauss_blur(Y, 1.0), 0.02, 1))
ball = Y < 0.6
seg = np.diff(P, axis=0); sl = np.hypot(*seg.T); cum = np.r_[0, np.cumsum(sl)]
s = np.arange(0, cum[-1], 1.0)
px = np.interp(s, cum, P[:, 0]); py = np.interp(s, cum, P[:, 1])
tx = np.gradient(px); ty = np.gradient(py)
k = 31
tx = np.convolve(tx, np.ones(k) / k, mode='same'); ty = np.convolve(ty, np.ones(k) / k, mode='same')
tn = np.hypot(tx, ty); tx /= tn; ty /= tn
nx, ny = -ty, tx
v = np.arange(-hw, hw + 0.5, 0.5)
X = px[None, :] + v[:, None] * nx[None, :]
Yc = py[None, :] + v[:, None] * ny[None, :]
R = L.bilinear(Yl, X, Yc)
Bm = L.bilinear(ball.astype(np.float32), X, Yc) > 0.99
for s0 in range(0, int(s[-1]) - win + 1, step):
    sel = slice(s0, s0 + win)
    Rm = np.where(Bm[:, sel], R[:, sel], np.nan)
    prof = np.nanmean(Rm, 1)
    valid = np.isfinite(prof)
    sc = s0 + win // 2
    print(f"WINDOW s={s0}-{s0 + win} centre=({px[sc]:.0f},{py[sc]:.0f}) n=({nx[sc]:.2f},{ny[sc]:.2f})")
    pm = np.convolve(np.nan_to_num(prof, nan=np.nanmean(prof)), np.ones(3) / 3, mode='same')
    ext = []
    for i in range(6, len(v) - 6):
        if not valid[i]:
            continue
        w = pm[max(0, i - 16):i + 17]
        if pm[i] == w.min() and (w.max() - pm[i]) > 0.06:
            ext.append(('MIN', v[i], pm[i], w.max() - pm[i]))
        if pm[i] == w.max() and (pm[i] - w.min()) > 0.06:
            ext.append(('max', v[i], pm[i], pm[i] - w.min()))
    for e in ext:
        x = px[sc] + e[1] * nx[sc]; y = py[sc] + e[1] * ny[sc]
        print(f"   {e[0]} v={e[1]:6.1f} img=({x:.0f},{y:.0f}) prom={e[3]:.3f}")
