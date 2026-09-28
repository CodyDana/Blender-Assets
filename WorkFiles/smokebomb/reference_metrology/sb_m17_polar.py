"""Stage 17: polar (fan) profiles around a whorl point P: log-lum averaged over rho in [r1,r2] at each
angle phi (image, CCW from +x, y up). Prints prominent minima (crevices radiating from P) and saves a
polar-unwrapped image (rows = rho, cols = phi) for viewing. args: px py r1 r2 phi0 phi1 prom name"""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import text

a = sys.argv[sys.argv.index('--') + 1:]
px, py, r1, r2, ph0, ph1, prom = [float(v) for v in a[:7]]
name = a[7]
rgb = L.load_srgb(); Y = L.lum(rgb)
Yl = np.log(np.clip(L.gauss_blur(Y, 1.0), 0.02, 1))
ball = (Y < 0.6).astype(np.float32)
ph = np.radians(np.arange(ph0, ph1, 0.25))
rho = np.arange(r1, r2, 1.0)
X = px + rho[:, None] * np.cos(ph)[None, :]
Yc = py - rho[:, None] * np.sin(ph)[None, :]
Rm = L.bilinear(Yl, X, Yc)
Bm = L.bilinear(ball, X, Yc) > 0.99
prof = np.array([Rm[Bm[:, j], j].mean() if Bm[:, j].sum() > 10 else np.nan for j in range(len(ph))])
pm = np.convolve(np.nan_to_num(prof, nan=np.nanmean(prof)), np.ones(5) / 5, mode='same')
deg = np.degrees(ph)
out = []
for i in range(8, len(ph) - 8):
    w = pm[max(0, i - 16):i + 17]
    if pm[i] == w.min() and w.max() - pm[i] > prom:
        out.append(f"m{deg[i]:.1f}({w.max() - pm[i]:.2f})")
print("POLAR", name, " ".join(out))
# unwrapped view, stretched
img = np.clip((L.bilinear(L.stretch(L.gauss_blur(Y, 1.2), 0.02, 0.3), X, Yc)), 0, 1)
img[~Bm] = 1
o = np.repeat(img[..., None], 3, 2).astype(np.float32)
o = L.upscale(o, 2).copy()
M = 30
big = np.ones((o.shape[0] + M, o.shape[1], 3), np.float32); big[M:] = o
for d in range(int(np.ceil(ph0 / 10) * 10), int(ph1), 10):
    c = int((d - ph0) / 0.25) * 2
    if c < big.shape[1]:
        big[M:, c] = 0.5 * big[M:, c] + 0.5 * np.array((1, 0.2, 0.2))
        text(big, str(d % 360), c - 6, 4, np.array((0.8, 0.1, 0.1), np.float32), 2)
L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_polar_{name}.png"), big)
