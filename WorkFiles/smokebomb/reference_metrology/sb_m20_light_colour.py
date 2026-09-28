"""Stage 20: lighting (shading fit on the sphere), colour/albedo per region, weave spectrum per patch."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S

rgb = L.load_srgb().astype(np.float64)
lin = L.srgb_to_lin(rgb)
Ylin = lin @ L.LW.astype(np.float64)
H, W = Ylin.shape
yy, xx = np.mgrid[0:H, 0:W]
u = (xx - S.CX) / S.R; v = (S.CY - yy) / S.R
rr = np.sqrt(u * u + v * v)
out = {}

# ---------------- lighting: block percentiles ----------------
B = 16
rows = []
for by in range(0, H - B, B):
    for bx in range(0, W - B, B):
        cu, cv = u[by + B // 2, bx + B // 2], v[by + B // 2, bx + B // 2]
        if cu * cu + cv * cv > 0.92 ** 2:
            continue
        blk = Ylin[by:by + B, bx:bx + B].ravel()
        rows.append((cu, cv, np.sqrt(max(0, 1 - cu * cu - cv * cv)), np.percentile(blk, 75), np.percentile(blk, 50),
                     np.percentile(blk, 10)))
Rw = np.array(rows)
n = Rw[:, :3]; I75 = Rw[:, 3]; I50 = Rw[:, 4]
A = np.c_[np.ones(len(n)), n]
c, *_ = np.linalg.lstsq(A, I75, rcond=None)
pred = A @ c
r2 = 1 - np.var(I75 - pred) / np.var(I75)
l1 = c[1:] / np.linalg.norm(c[1:])
print("SH1 fit c0=%.5f c=(%.5f,%.5f,%.5f) R2=%.3f dir=%s" % (c[0], c[1], c[2], c[3], r2, l1.round(3)))
# Lambert + ambient grid search
best = None
for el in np.radians(np.arange(-30, 91, 1.0)):
    for az in np.radians(np.arange(-90, 91, 1.0)):
        l = np.array([np.cos(el) * np.sin(az), np.sin(el), np.cos(el) * np.cos(az)])
        f = np.maximum(0, n @ l)
        M = np.c_[np.ones(len(n)), f]
        cc, *_ = np.linalg.lstsq(M, I75, rcond=None)
        e = np.sum((M @ cc - I75) ** 2)
        if best is None or e < best[0]:
            best = (e, np.degrees(az), np.degrees(el), cc, l)
e, az, el, cc, l = best
r2l = 1 - e / np.sum((I75 - I75.mean()) ** 2)
amb_frac = cc[0] / (cc[0] + cc[1])
print("LAMBERT+AMB az=%.0f el=%.0f a=%.5f b=%.5f ambient_frac=%.3f R2=%.3f" % (az, el, cc[0], cc[1], amb_frac, r2l))
# wrap-lighting variant: I = a + b * clamp((n.l + w)/(1+w))
bestw = None
for w_ in np.arange(0, 1.01, 0.1):
    f = np.clip((n @ l + w_) / (1 + w_), 0, None)
    M = np.c_[np.ones(len(n)), f]
    cc2, *_ = np.linalg.lstsq(M, I75, rcond=None)
    e2 = np.sum((M @ cc2 - I75) ** 2)
    if bestw is None or e2 < bestw[0]:
        bestw = (e2, w_, cc2)
print("WRAP best w=%.1f a=%.5f b=%.5f" % (bestw[1], bestw[2][0], bestw[2][1]))
# brightness vs angle from the key and vs radius
cosk = n @ l
bins = np.linspace(-0.2, 1.0, 13)
prof_k = [(round(float(bins[i]), 2), round(float(np.median(I75[(cosk >= bins[i]) & (cosk < bins[i + 1])])), 5))
          for i in range(len(bins) - 1) if ((cosk >= bins[i]) & (cosk < bins[i + 1])).sum() > 5]
print("I75 vs n.l:", prof_k)
rb = np.linspace(0, 0.92, 8)
rad = np.hypot(n[:, 0], n[:, 1])
prof_r = [(round(float(rb[i]), 2), round(float(np.median(I75[(rad >= rb[i]) & (rad < rb[i + 1])])), 5)) for i in range(len(rb) - 1)]
print("I75 vs r:", prof_r)
# quadrant medians
quad = {}
for nm, m in dict(upper_left=(n[:, 0] < -0.3) & (n[:, 1] > 0.3), upper_right=(n[:, 0] > 0.3) & (n[:, 1] > 0.3),
                  lower_left=(n[:, 0] < -0.3) & (n[:, 1] < -0.3), lower_right=(n[:, 0] > 0.3) & (n[:, 1] < -0.3),
                  centre=rad < 0.3).items():
    quad[nm] = round(float(np.median(I75[m])), 5)
print("quadrant I75 (linear lum):", quad)
out['lighting'] = dict(block=B, sh1=dict(c0=float(c[0]), c=c[1:].tolist(), R2=float(r2), dir=l1.tolist()),
                       lambert_ambient=dict(az_deg=float(az), el_deg=float(el), a=float(cc[0]), b=float(cc[1]),
                                            ambient_frac=float(amb_frac), R2=float(r2l), l=l.tolist()),
                       wrap=dict(w=float(bestw[1]), a=float(bestw[2][0]), b=float(bestw[2][1])),
                       I75_vs_ndotl=prof_k, I75_vs_r=prof_r, quadrants=quad)

# ---------------- colour per region ----------------
REG = {"A": [(560, 700), (700, 780), (430, 640), (820, 830)], "B": [(900, 470), (800, 480), (980, 470)],
       "C": [(300, 800), (420, 800), (240, 790)], "W": [(950, 726), (880, 697)], "X": [(950, 610), (1010, 630)],
       "L3": [(290, 580)], "U": [(700, 390), (620, 420), (800, 360)], "rim_UL": [(330, 330), (380, 300), (260, 400)],
       "D_bottom": [(560, 960), (480, 980)], "E_bottom_right": [(850, 970), (760, 960)], "whorl_top": [(640, 230), (760, 230)]}
col = {}
allpix = []
for k, pts in REG.items():
    px = []
    for (cx, cy) in pts:
        r_ = 14 if k in ("W", "L3") else 22
        m = (xx - cx) ** 2 + (yy - cy) ** 2 < r_ * r_
        px.append(lin[m])
    px = np.concatenate(px)
    Yp = px @ L.LW.astype(np.float64)
    lo, hi = np.percentile(Yp, [20, 95])
    sel = (Yp >= lo) & (Yp <= hi)
    mlin = px[sel].mean(0)
    allpix.append(px[sel])
    s = L.lin_to_srgb(mlin)
    mx, mn = s.max(), s.min()
    hue = 0.0
    if mx > mn:
        rr_, gg, bb = s
        if mx == rr_:
            hue = (60 * ((gg - bb) / (mx - mn))) % 360
        elif mx == gg:
            hue = 60 * ((bb - rr_) / (mx - mn)) + 120
        else:
            hue = 60 * ((rr_ - gg) / (mx - mn)) + 240
    sat = (mx - mn) / mx if mx > 0 else 0
    chrom = mlin / mlin.sum()
    col[k] = dict(mean_lin=mlin.round(5).tolist(), mean_srgb=s.round(4).tolist(), lum_lin=round(float(mlin @ L.LW), 5),
                  hue_deg=round(float(hue), 1), sat_hsv=round(float(sat), 3), chroma_rgb=chrom.round(4).tolist(),
                  n=int(sel.sum()))
    print("COLOUR", k, col[k])
allp = np.concatenate(allpix)
mall = allp.mean(0)
out['colour'] = dict(regions=col, all_mean_lin=mall.tolist(), all_mean_srgb=L.lin_to_srgb(mall).tolist())
print("ALL mean lin", mall.round(5), "srgb", L.lin_to_srgb(mall).round(4))

# ---------------- surface luminance distribution (whole disc, r<0.9) ----------------
disc = rr < 0.9
Yd = Ylin[disc]
out['disc_lum_lin_percentiles'] = {str(p): float(np.percentile(Yd, p)) for p in (1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9)}
Sd = (rgb @ L.LW.astype(np.float64))[disc]
out['disc_lum_srgb_percentiles'] = {str(p): float(np.percentile(Sd, p)) for p in (1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9)}
print("disc lin pct", out['disc_lum_lin_percentiles'])
print("disc srgb pct", out['disc_lum_srgb_percentiles'])
# highlight speckles (sheen/fibre): pixels > 3x local median
med = L.gauss_blur(Ylin.astype(np.float32), 6)
spk = disc & (Ylin > 3 * med)
out['speckle_fraction'] = float(spk.sum() / disc.sum())
sp_rgb = lin[spk].mean(0)
out['speckle_mean_lin'] = sp_rgb.tolist(); out['speckle_mean_srgb'] = L.lin_to_srgb(sp_rgb).tolist()
out['speckle_chroma'] = (sp_rgb / sp_rgb.sum()).tolist()
print("speckles frac", out['speckle_fraction'], "rgb", L.lin_to_srgb(sp_rgb).round(3), "chroma", (sp_rgb / sp_rgb.sum()).round(3))
# speckle density vs radius
for r0, r1 in ((0, 0.3), (0.3, 0.6), (0.6, 0.8), (0.8, 0.9)):
    m = (rr >= r0) & (rr < r1)
    print("speckle density r %.1f-%.1f: %.4f" % (r0, r1, (spk & m).sum() / m.sum()))
L.dump("sb_s20_light_colour.json", out)
