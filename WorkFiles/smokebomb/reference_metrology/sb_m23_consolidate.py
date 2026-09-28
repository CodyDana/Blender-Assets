"""Stage 23: consolidate band geometry: per-edge control points (lat/lon, image, disc coords), per-band width
profiles measured on the sphere, weft peaks, per-region shading-normalised albedo. Writes sb_s23_bands.json."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S

tr = json.load(open(os.path.join(L.D, "sb_trace.json")))['edges']
fits = L.load("sb_s18_fits.json")
lc = L.load("sb_s20_light_colour.json")


def dense(pts, step=2.0):
    P = np.asarray(pts, float)
    seg = np.diff(P, axis=0); sl = np.hypot(*seg.T); cum = np.r_[0, np.cumsum(sl)]
    s = np.arange(0, cum[-1] + 1e-6, step)
    return np.c_[np.interp(s, cum, P[:, 0]), np.interp(s, cum, P[:, 1])]


out = {'edges': {}, 'bands': {}}
for k, e in tr.items():
    p = dense(e['pts'])
    idx = np.linspace(0, len(p) - 1, 7).round().astype(int)
    q = p[idx]
    n = S.to_sphere(q)
    lat, lon = S.latlon(n)
    out['edges'][k] = dict(control_img=q.round(0).tolist(),
                           control_disc_uv=np.c_[(q[:, 0] - S.CX) / S.R, (S.CY - q[:, 1]) / S.R].round(3).tolist(),
                           control_latlon=np.c_[lat, lon].round(1).tolist(),
                           end_angle_deg=[round(float(np.degrees(np.arctan2(S.CY - q[i, 1], q[i, 0] - S.CX)) % 360), 1) for i in (0, -1)],
                           end_r_frac=[round(float(np.hypot(q[i, 0] - S.CX, S.CY - q[i, 1]) / S.R), 3) for i in (0, -1)])

# band width profiles: for points on edge e1 (restricted to an x-range), angular distance to nearest point of e2
BW = {"W": ("WUP", "WLO", 700, 1040), "W_twist": ("WTW", "WLO", 540, 612), "A_visible": ("WLO", "ALO", 540, 1030),
      "A_visible_left": ("WTW", "ALO", 363, 540), "B": ("BLO", "BUP", 705, 1075), "C": ("CUP", "CLO", 190, 365),
      "X_visible": ("BLO", "WUP", 705, 1075), "L3_visible": ("L3L", "ALO", 0, 2000), "L4": ("LIN", "L3L", 0, 300),
      "U1": ("UA", "UC", 0, 2000), "U2": ("UC", "UD", 0, 2000), "U3": ("UD", "UE", 0, 2000), "U4": ("UE", "UF", 0, 2000),
      "D_a": ("D14", "D57", 0, 2000), "D_b": ("D57", "D9", 0, 2000), "R_in": ("LIN", "LC", 300, 600), "R2": ("LC", "LA", 250, 600)}
for b, (e1, e2, xa, xb) in BW.items():
    p1 = dense(tr[e1]['pts'], 3.0); p1 = p1[(p1[:, 0] >= xa) & (p1[:, 0] <= xb)]
    p2 = dense(tr[e2]['pts'], 1.0)
    n1, n2 = S.to_sphere(p1), S.to_sphere(p2)
    ang = np.degrees(np.arccos(np.clip(n1 @ n2.T, -1, 1)))
    j = ang.argmin(1)
    dmin = ang[np.arange(len(p1)), j]
    pix = np.hypot(*(p1 - p2[j]).T)
    # drop points whose nearest partner is an endpoint (no true perpendicular partner)
    ok = (j > 2) & (j < len(p2) - 3)
    if ok.sum() < 3:
        ok = np.ones(len(p1), bool)
    dm, px = dmin[ok], pix[ok]
    out['bands'][b] = dict(edges=[e1, e2], n=int(ok.sum()),
                           width_arc_deg=dict(median=round(float(np.median(dm)), 2), p10=round(float(np.percentile(dm, 10)), 2),
                                              p90=round(float(np.percentile(dm, 90)), 2)),
                           width_frac_D=dict(median=round(float(np.radians(np.median(dm)) / 2), 4),
                                             p10=round(float(np.radians(np.percentile(dm, 10)) / 2), 4),
                                             p90=round(float(np.radians(np.percentile(dm, 90)) / 2), 4)),
                           width_image_px=dict(median=round(float(np.median(px)), 1), p10=round(float(np.percentile(px, 10)), 1),
                                               p90=round(float(np.percentile(px, 90)), 1)))
    print(f"BW {b:15s} arc {np.median(dm):6.2f} deg ({np.percentile(dm, 10):.1f}-{np.percentile(dm, 90):.1f}) = "
          f"{np.radians(np.median(dm)) / 2:.3f} D ; image {np.median(px):.0f}px ({np.percentile(px, 10):.0f}-{np.percentile(px, 90):.0f})")

# shading-normalised albedo per region: I = a + b max(0, n.l) ; albedo_rel = lum / (a + b max(0,n.l)) * (a + b)
la = lc['lighting']['lambert_ambient']
l = np.array(la['l']); a_, b_ = la['a'], la['b']
REGC = {"A": (560, 700), "B": (900, 470), "C": (330, 800), "W": (915, 712), "X": (980, 620), "L3": (290, 580),
        "U": (700, 390), "rim_UL": (330, 330), "D_bottom": (520, 970), "E_bottom_right": (805, 965), "whorl_top": (700, 230)}
alb = {}
for k, (x, y) in REGC.items():
    n = S.to_sphere([[x, y]])[0]
    sh = a_ + b_ * max(0.0, float(n @ l))
    lum = lc['colour']['regions'][k]['lum_lin']
    alb[k] = dict(n=n.round(3).tolist(), shading=round(sh, 5), lum_lin=lum,
                  albedo_white1=round(lum / (a_ + b_) * (a_ + b_) / sh, 4))
    print("ALB", k, alb[k])
vals = np.array([v['albedo_white1'] for v in alb.values()])
out['albedo'] = dict(regions=alb, median=float(np.median(vals)), min=float(vals.min()), max=float(vals.max()),
                     cv=float(vals.std() / vals.mean()), convention="albedo = region mean linear luminance / modelled key+ambient irradiance, with the irradiance scaled so a perfect white surface facing the key reads 1.0 (the backdrop reads 0.996)")
print("ALBEDO median %.4f min %.4f max %.4f cv %.3f" % (out['albedo']['median'], vals.min(), vals.max(), out['albedo']['cv']))

# weft: strongest spectral peak with the wave vector ALONG the band (rows across the band)
rgb = L.load_srgb(); Y = L.lum(rgb).astype(np.float64)
Yl = np.log(np.clip(Y, 0.01, 1))
BANDDIR = {"A1": ((620, 745), 152), "A2": ((520, 690), 146), "B1": ((900, 470), 5), "C1": ((330, 810), 22), "C2": ((440, 800), 17),
           "U1": ((720, 385), 56), "X1": ((985, 620), 162)}
N = 64
h = np.outer(np.hanning(N), np.hanning(N))
fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.fftfreq(N)[None, :]
fr = np.hypot(fx, fy)
wvang = np.degrees(np.arctan2(-fy, fx)) % 180
weft = {}
for k, ((cx, cy), bd) in BANDDIR.items():
    p = Yl[cy - 32:cy + 32, cx - 32:cx + 32]; p = p - p.mean()
    F = np.abs(np.fft.fft2(p * h)) ** 2
    F[(fr < 3 / N) | (fr > 0.45)] = 0
    tot = F.sum()
    dd = np.abs(((wvang - bd) + 90) % 180 - 90)     # wave vector parallel to band dir -> rows across the band
    Fw = np.where(dd < 20, F, 0); Fp = np.where(np.abs(((wvang - bd - 90) + 90) % 180 - 90) < 20, F, 0)
    iw = np.unravel_index(np.argmax(Fw), F.shape); ip = np.unravel_index(np.argmax(Fp), F.shape)
    weft[k] = dict(band_dir_deg=bd, weft_period_px=round(float(1 / fr[iw]), 2), weft_wedge_power=round(float(Fw.sum() / tot), 3),
                   warp_period_px=round(float(1 / fr[ip]), 2), warp_wedge_power=round(float(Fp.sum() / tot), 3))
    print("WEAVE", k, weft[k])
out['weave_dirs'] = weft
L.dump("sb_s23_bands.json", out)
