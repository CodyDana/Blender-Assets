"""Stage 10: rectify the image along a polyline path so a band along it becomes horizontal.
args: name halfwidth K sigma base x1 y1 x2 y2 [x3 y3 ...]   (base st|ln)
Output rows = offset perpendicular to the path (-hw at top -> +hw at bottom, + = to the right of travel
in image coords), columns = arc length. Grid: every 25 px of offset / length, labels every 50."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
from sb_m08_segments import text

a = sys.argv[sys.argv.index('--') + 1:]
name, hw, K, sigma, base = a[0], int(a[1]), int(a[2]), float(a[3]), a[4]
P = np.array([float(v) for v in a[5:]]).reshape(-1, 2)
rgb = L.load_srgb(); Y = L.lum(rgb)
Yb = L.gauss_blur(Y, sigma) if sigma > 0 else Y
if base == 'st':
    img = L.stretch(Yb, 0.02, 0.30)
else:
    mu = L.gauss_blur(Y, 40)
    sd = np.sqrt(L.gauss_blur((Yb - mu) ** 2, 40)) + 0.005
    img = np.clip(0.5 + 0.2 * (Yb - mu) / sd, 0, 1)
    img[Y > 0.6] = 0.9
# densify path, arc length param
seg = np.diff(P, axis=0); sl = np.hypot(*seg.T); cum = np.r_[0, np.cumsum(sl)]
s = np.arange(0, cum[-1], 1.0)
px = np.interp(s, cum, P[:, 0]); py = np.interp(s, cum, P[:, 1])
# smooth tangent
tx = np.gradient(px); ty = np.gradient(py)
k = 15
tx = np.convolve(tx, np.ones(k) / k, mode='same'); ty = np.convolve(ty, np.ones(k) / k, mode='same')
tn = np.hypot(tx, ty); tx /= tn; ty /= tn
nx, ny = -ty, tx       # right-hand normal in image coords (y down): for travel +x, normal = +y (down)
v = np.arange(-hw, hw + 1, 1.0)
X = px[None, :] + v[:, None] * nx[None, :]
Yc = py[None, :] + v[:, None] * ny[None, :]
R = L.bilinear(img, X, Yc)
out = np.repeat(R[..., None], 3, 2).astype(np.float32)
out = L.upscale(out, K).copy()
M = 36
big = np.ones((out.shape[0] + M, out.shape[1] + M, 3), np.float32)
big[M:, M:] = out
for sv in range(0, int(s[-1]) + 1, 25):
    c = M + sv * K
    if c < big.shape[1]:
        clr = np.array((1, 0.2, 0.2) if sv % 100 == 0 else (0.25, 0.55, 1), np.float32)
        big[M:, c] = 0.6 * big[M:, c] + 0.4 * clr
        if sv % 50 == 0:
            text(big, str(sv), c - 6, 4 if (sv // 50) % 2 == 0 else 18, clr * 0.8, 2)
for vv in range(-hw, hw + 1, 25):
    r = M + (vv + hw) * K
    clr = np.array((1, 0.2, 0.2) if vv == 0 else ((1, 0.5, 0.5) if vv % 100 == 0 else (0.25, 0.55, 1)), np.float32)
    big[r, M:] = 0.6 * big[r, M:] + 0.4 * clr
    if vv % 50 == 0:
        text(big, str(vv), 1, r - 5, clr * 0.8, 2)
L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_rect_{name}.png"), big)
np.save(os.path.join(L.D, f"sb_rect_{name}_path.npy"), np.c_[s, px, py, nx, ny])
print("saved", name, "length", s[-1])
