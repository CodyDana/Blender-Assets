"""Stage 7: oriented line detector. Directional 2nd derivative across each of NO orientations on
log-luminance blurred at sigma, averaged along the orientation over +-HL px. Valleys (shadow lines at a
strip edge) and ridges (lit rolled rims) are kept separately. Saves response + orientation arrays and views."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
sigma = float(args[0]) if args else 2.0
HL = int(args[1]) if len(args) > 1 else 18
NO = int(args[2]) if len(args) > 2 else 36
rgb = L.load_srgb()
Y = L.lum(rgb)
ball = Y < 0.6
Yl = np.log(np.clip(Y, 0.02, 1)).astype(np.float32)
Yl[~ball] = np.log(0.12)          # neutral outside so the rim does not dominate
G = L.gauss_blur(Yl, sigma)
gy, gx = np.gradient(G)
gyy, gyx = np.gradient(gy)
gxy, gxx = np.gradient(gx)
H, W = Y.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bestV = np.zeros_like(Y); bestR = np.zeros_like(Y)
angV = np.zeros_like(Y); angR = np.zeros_like(Y)
for k in range(NO):
    th = np.pi * k / NO                  # line direction, image coords CCW from +x with y up
    ux, uy = np.cos(th), -np.sin(th)
    nx, ny = -uy, ux
    d2 = nx * nx * gxx + 2 * nx * ny * gxy + ny * ny * gyy   # across-line curvature
    acc = np.zeros_like(Y)
    for t in range(-HL, HL + 1, 2):
        acc += L.bilinear(d2, xx + t * ux, yy + t * uy)
    acc /= len(range(-HL, HL + 1, 2))
    v = np.maximum(acc, 0); r = np.maximum(-acc, 0)
    m = v > bestV; bestV[m] = v[m]; angV[m] = np.degrees(th)
    m = r > bestR; bestR[m] = r[m]; angR[m] = np.degrees(th)
bestV[~ball] = 0; bestR[~ball] = 0
np.save(os.path.join(L.D, f"sb_s7_lines_s{sigma}_L{HL}.npy"), np.stack([bestV, angV, bestR, angR]).astype(np.float32))
sv = np.percentile(bestV[ball], 99.5); sr = np.percentile(bestR[ball], 99.5)
print("p99.5 valley", sv, "ridge", sr)
vis = np.ones((H, W, 3), np.float32)
a = np.clip(bestV / sv, 0, 1); b = np.clip(bestR / sr, 0, 1)
vis[..., 0] = 1 - a                # valleys dark red->black? valleys shown black, ridges shown blue
vis[..., 1] = 1 - np.maximum(a, b)
vis[..., 2] = 1 - a
c = vis[150:1110, 150:1110].copy()
for v in range(200, 1110, 50):
    clr = (1, 0.3, 0.3) if v % 100 == 0 else (0.6, 0.8, 1.0)
    c[:, v - 150] = 0.5 * c[:, v - 150] + 0.5 * np.array(clr)
    c[v - 150, :] = 0.5 * c[v - 150, :] + 0.5 * np.array(clr)
L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_s7_lines_s{sigma}_L{HL}.png"), c)
print("done")
