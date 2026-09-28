"""Stage 16: radial profiles (log-lum, blurred 1px) averaged over +-dth degrees of angle, from r0 to r1.
Prints the prominent minima (crevices) and maxima (rims). args: dth r0 r1 prom theta1 theta2 ..."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

a = [float(v) for v in sys.argv[sys.argv.index('--') + 1:]]
dth, r0, r1, prom = a[:4]
thetas = a[4:]
CX, CY, R = 627.378, 628.918, 464.107
rgb = L.load_srgb(); Y = L.lum(rgb)
Yl = np.log(np.clip(L.gauss_blur(Y, 1.0), 0.02, 1))
r = np.arange(r0, r1, 0.5)
for th in thetas:
    ts = np.radians(np.linspace(th - dth, th + dth, 25))
    X = CX + np.cos(ts)[None, :] * r[:, None]
    Yc = CY - np.sin(ts)[None, :] * r[:, None]
    p = L.bilinear(Yl, X, Yc).mean(1)
    p = np.convolve(p, np.ones(3) / 3, mode='same')
    out = []
    for i in range(6, len(r) - 6):
        w = p[max(0, i - 14):i + 15]
        if p[i] == w.min() and w.max() - p[i] > prom:
            out.append(f"m{r[i]:.0f}({w.max() - p[i]:.2f})")
        if p[i] == w.max() and p[i] - w.min() > prom:
            out.append(f"M{r[i]:.0f}")
    print(f"TH {th:5.1f}: " + " ".join(out))
