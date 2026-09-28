"""Stage 4: texture orientation field (structure tensor on the weave band-pass).
Warp threads run along a strip, so the dominant fine orientation inside a strip = the strip's direction.
Saves orientation (deg, image frame, CCW from +x, 0..180) + coherence arrays and a hue map with grid."""
import sys, os, colorsys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

rgb = L.load_srgb()
Y = L.lum(rgb).astype(np.float32)
ball = Y < 0.6
# band-pass: remove shading
Yl = np.log(np.clip(Y, 0.01, 1))
hp = Yl - L.gauss_blur(Yl, 6)
fine = L.gauss_blur(hp, 0.8)
gy, gx = np.gradient(fine)
res = {}
for s in (6, 12):
    Jxx = L.gauss_blur(gx * gx, s); Jyy = L.gauss_blur(gy * gy, s); Jxy = L.gauss_blur(gx * gy, s)
    # gradient dominant direction angle (image coords, y down)
    ang_g = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)
    lam1 = 0.5 * (Jxx + Jyy) + np.sqrt(0.25 * (Jxx - Jyy) ** 2 + Jxy ** 2)
    lam2 = 0.5 * (Jxx + Jyy) - np.sqrt(0.25 * (Jxx - Jyy) ** 2 + Jxy ** 2)
    coh = (lam1 - lam2) / (lam1 + lam2 + 1e-9)
    # thread direction is perpendicular to dominant gradient; convert to CCW-from-+x with y up
    thr = ang_g + np.pi / 2
    deg = (-np.degrees(thr)) % 180.0
    res[s] = (deg.astype(np.float32), coh.astype(np.float32))
    np.save(os.path.join(L.D, f"sb_s4_orient_s{s}.npy"), np.stack([deg, coh]).astype(np.float32))
    # hue map
    hue = deg / 180.0
    val = np.clip(coh / 0.5, 0, 1)
    h6 = hue * 6
    i = np.floor(h6).astype(int) % 6
    f = h6 - np.floor(h6)
    p = np.zeros_like(f); q = 1 - f; t = f
    r = np.choose(i, [1, q, p, p, t, 1]); g = np.choose(i, [t, 1, 1, q, p, p]); b = np.choose(i, [p, p, t, 1, 1, q])
    col = np.stack([r, g, b], -1) * val[..., None]
    shade = L.stretch(L.gauss_blur(Y, 1.0), 0.02, 0.3)
    col = 0.75 * col + 0.25 * shade[..., None]
    col[~ball] = 1.0
    c = col[150:1110, 150:1110].astype(np.float32)
    for v in range(200, 1110, 100):
        c[:, v - 150] = (1, 1, 1) if v % 500 else (0, 0, 0)
        c[v - 150, :] = (1, 1, 1) if v % 500 else (0, 0, 0)
    L.save_png(os.path.join(L.DBG, f"DEBUG_NEVER_SHIP_sb_s4_orient_s{s}.png"), c)
# legend strip: hue vs angle 0..180 at bottom
leg = np.zeros((40, 360, 3), np.float32)
for x in range(360):
    hh = x / 360.0
    leg[:, x] = colorsys.hsv_to_rgb(hh, 1, 1)
L.save_png(os.path.join(L.DBG, "DEBUG_NEVER_SHIP_sb_s4_orient_legend_0to180deg.png"), leg)
print("done")
