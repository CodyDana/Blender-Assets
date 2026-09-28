"""Stage 24: two-light (key + fill) + ambient Lambert fit to the block-75th-percentile surface luminance, and an
order-2 SH irradiance fit. Also the block residual by region to show what the fit misses."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S

rgb = L.load_srgb().astype(np.float64)
Ylin = L.srgb_to_lin(rgb) @ L.LW.astype(np.float64)
H, W = Ylin.shape
B = 16
rows = []
for by in range(0, H - B, B):
    for bx in range(0, W - B, B):
        cu = (bx + B / 2 - S.CX) / S.R; cv = (S.CY - (by + B / 2)) / S.R
        if cu * cu + cv * cv > 0.92 ** 2:
            continue
        blk = Ylin[by:by + B, bx:bx + B].ravel()
        rows.append((cu, cv, np.sqrt(1 - cu * cu - cv * cv), np.percentile(blk, 75)))
R_ = np.array(rows); n = R_[:, :3]; I = R_[:, 3]
dirs = []
for el in range(-40, 91, 4):
    for az in range(-120, 121, 4):
        e, a = np.radians(el), np.radians(az)
        dirs.append((az, el, np.array([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)])))


def solve(ls):
    M = np.c_[np.ones(len(n))] if not ls else np.c_[np.ones(len(n)), np.stack([np.maximum(0, n @ l) for l in ls], 1)]
    c, *_ = np.linalg.lstsq(M, I, rcond=None)
    return c, np.sum((M @ c - I) ** 2)


l1 = np.array([0.267, 0.946, 0.187]); l2 = np.array([-1.0, 0, 0.3]); l2 /= np.linalg.norm(l2)
for it in range(3):
    best = min(((solve([l1, d[2]])[1], d) for d in dirs), key=lambda t: t[0]); l2 = best[1][2]; d2 = best[1]
    best = min(((solve([d[2], l2])[1], d) for d in dirs), key=lambda t: t[0]); l1 = best[1][2]; d1 = best[1]
c, e = solve([l1, l2])
tot = np.sum((I - I.mean()) ** 2)
print("KEY az=%d el=%d  FILL az=%d el=%d  coeffs amb=%.5f key=%.5f fill=%.5f  R2=%.3f" % (d1[0], d1[1], d2[0], d2[1], c[0], c[1], c[2], 1 - e / tot))
c1, e1 = solve([l1])
print("single-light R2 with that key: %.3f" % (1 - e1 / tot))
# SH order 2 (real, unnormalised basis)
x, y, z = n.T
Bsh = np.c_[np.ones_like(x), y, z, x, x * y, y * z, 3 * z * z - 1, x * z, x * x - y * y]
csh, *_ = np.linalg.lstsq(Bsh, I, rcond=None)
print("SH2 coeffs [1,y,z,x,xy,yz,3z2-1,xz,x2-y2]:", csh.round(5), "R2=%.3f" % (1 - np.sum((Bsh @ csh - I) ** 2) / tot))
peak = n[np.argmax(Bsh @ csh)]
print("SH2 brightest visible normal:", peak.round(3), "darkest:", n[np.argmin(Bsh @ csh)].round(3),
      "ratio max/min %.2f" % ((Bsh @ csh).max() / (Bsh @ csh).min()))
key_at_view = c[0] + c[1] * max(0, l1[2]) + c[2] * max(0, l2[2])
out = dict(key=dict(az_deg=d1[0], el_deg=d1[1], vec=l1.round(4).tolist(), coeff=float(c[1])),
           fill=dict(az_deg=d2[0], el_deg=d2[1], vec=l2.round(4).tolist(), coeff=float(c[2])),
           ambient=float(c[0]), R2=float(1 - e / tot), fill_over_key=float(c[2] / c[1]), ambient_over_key=float(c[0] / c[1]),
           peak_irradiance_model=float(c[0] + c[1] + c[2] * max(0, float(l1 @ l2))),
           sh2=dict(coeffs=csh.tolist(), R2=float(1 - np.sum((Bsh @ csh - I) ** 2) / tot), brightest_normal=peak.tolist(),
                    max_over_min=float((Bsh @ csh).max() / (Bsh @ csh).min())),
           note="az: +right of camera, el: +up, measured in the camera frame; vec = direction TO the light")
L.dump("sb_s24_light2.json", out)
print(json.dumps(out)[:600])
