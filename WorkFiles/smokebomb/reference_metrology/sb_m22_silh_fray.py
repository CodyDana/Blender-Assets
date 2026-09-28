"""Stage 22: silhouette detail (bump/step list, sector radii, wisps) + fray statistics along traced edges
+ step signature (rim/crevice widths & depths) across the traced edges."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L
import sb_sphere as S

out = {}
rad = np.load(os.path.join(L.D, "sb_s1_radial.npy"))    # th, r25, r50, r75, r90, r97 about the COARSE centre
ru = np.load(os.path.join(L.D, "sb_s1_ru.npy"))         # tu, ru, rlow, hp about the fitted circle centre
tu, rr_, rlow, hp = ru.T
deg = np.degrees(tu) % 360
order = np.argsort(deg)
deg, rr_, rlow, hp = deg[order], rr_[order], rlow[order], hp[order]
# sector means (30 deg)
sect = []
for s0 in range(0, 360, 30):
    m = (deg >= s0) & (deg < s0 + 30)
    sect.append(dict(from_deg=s0, to_deg=s0 + 30, mean_r_px=round(float(rr_[m].mean()), 2),
                     dev_pct_R=round(float((rr_[m].mean() - S.R) / S.R * 100), 2), max_r=round(float(rr_[m].max()), 1),
                     min_r=round(float(rr_[m].min()), 1)))
out['sectors'] = sect
for s in sect:
    print("SECT", s)
# steps: jumps in r over 0.5 deg > 2.5 px
steps = []
dr = rr_[np.r_[5:len(rr_), 0:5]] - rr_
i = 0
while i < len(dr):
    if abs(dr[i]) > 2.5:
        j = i
        while j + 1 < len(dr) and abs(dr[j + 1]) > 2.5 and np.sign(dr[j + 1]) == np.sign(dr[i]):
            j += 1
        k = i + np.argmax(np.abs(dr[i:j + 1]))
        steps.append(dict(deg=round(float(deg[k]), 1), jump_px=round(float(dr[k]), 1)))
        i = j + 1
    else:
        i += 1
out['steps'] = steps
print("STEPS", len(steps), steps)
# bumps: local maxima of hp exceeding +4 px, minima below -4
bumps = []
for i in range(len(hp)):
    w = hp[max(0, i - 20):i + 21]
    if hp[i] == w.max() and hp[i] > 4:
        bumps.append(dict(deg=round(float(deg[i]), 1), hp_px=round(float(hp[i]), 1), kind='bulge'))
    if hp[i] == w.min() and hp[i] < -4:
        bumps.append(dict(deg=round(float(deg[i]), 1), hp_px=round(float(hp[i]), 1), kind='dent'))
out['bumps'] = bumps
print("BUMPS", len(bumps))
for b in bumps:
    print("  ", b)
# wisps (faint protrusion beyond the 50% edge): r97 - r50
th = np.degrees(rad[:, 0]); w97 = rad[:, 5] - rad[:, 2]
wisp = []
for i in range(len(th)):
    wv = w97[max(0, i - 10):i + 11]
    if w97[i] == wv.max() and w97[i] > 3.0:
        wisp.append(dict(deg=round(float(th[i]), 1), reach_px=round(float(w97[i]), 1)))
out['wisps_gt3px'] = wisp
print("WISPS>3px", len(wisp), sorted([w_['reach_px'] for w_ in wisp])[-8:])

# ---------------- fray along edges ----------------
rgb = L.load_srgb(); Y = L.lum(rgb)
Yl = np.log(np.clip(L.gauss_blur(Y, 0.7), 0.02, 1)).astype(np.float64)
gy, gx = np.gradient(Yl)
tr = json.load(open(os.path.join(L.D, "sb_trace.json")))['edges']
FR = {"WLO": (700, 1030), "WUP": (760, 1040), "BLO": (720, 1070), "BUP": (620, 1040), "ALO": (450, 960), "CLO": (280, 620),
      "CUP": (195, 360), "L3L": (0, 2000), "UA": (0, 2000)}
fray = {}
for k, (xa, xb) in FR.items():
    P = np.asarray(tr[k]['pts'], float)
    seg = np.diff(P, axis=0); sl = np.hypot(*seg.T); cum = np.r_[0, np.cumsum(sl)]
    s = np.arange(0, cum[-1], 1.0)
    px = np.interp(s, cum, P[:, 0]); py = np.interp(s, cum, P[:, 1])
    m = (px >= xa) & (px <= xb)
    px, py = px[m], py[m]
    tx = np.gradient(px); ty = np.gradient(py)
    kk = 21
    tx = np.convolve(tx, np.ones(kk) / kk, mode='same'); ty = np.convolve(ty, np.ones(kk) / kk, mode='same')
    tn = np.hypot(tx, ty); tx /= tn; ty /= tn
    nx, ny = -ty, tx
    off = np.arange(-12, 12.01, 0.25)
    X = px[:, None] + off[None, :] * nx[:, None]
    Yc = py[:, None] + off[None, :] * ny[:, None]
    prof = L.bilinear(Yl, X, Yc)
    # edge = location of the steepest bright->dark transition (either sign), take the dominant sign
    d = np.gradient(prof, axis=1)
    sgn = np.sign(np.median(d[:, np.argmax(np.abs(d).mean(0))]))
    loc = off[np.argmax(sgn * d, axis=1)]
    # continuity: reject jumps, detrend with 41-px moving median
    trend = np.array([np.median(loc[max(0, i - 20):i + 21]) for i in range(len(loc))])
    res = loc - trend
    ok = np.abs(res) < 6
    r_ = res[ok]
    zc = np.sum(np.diff(np.sign(r_ - r_.mean())) != 0) / max(1, len(r_))
    # mean profile (aligned) for rim/crevice signature
    al = np.array([np.interp(off, off - trend[i], prof[i]) for i in range(len(prof))])
    mp = al.mean(0)
    imin = np.argmin(mp); imax = np.argmax(mp)
    fray[k] = dict(n=int(len(r_)), rms_px=round(float(r_.std()), 2), p95_abs_px=round(float(np.percentile(np.abs(r_), 95)), 2),
                   max_abs_px=round(float(np.abs(r_).max()), 2), zero_cross_per_px=round(float(zc), 3),
                   mean_wavelength_px=round(float(2 / zc), 1) if zc > 0 else None,
                   crevice_offset_px=round(float(off[imin]), 2), rim_offset_px=round(float(off[imax]), 2),
                   crevice_depth_log=round(float(np.median(mp) - mp[imin]), 3), rim_height_log=round(float(mp[imax] - np.median(mp)), 3),
                   profile_log=[round(float(v), 3) for v in mp[::4]])
    print("FRAY", k, {kk_: vv for kk_, vv in fray[k].items() if kk_ != 'profile_log'})
out['fray'] = fray
out['fray_profile_offsets_px'] = [float(v) for v in off[::4]]
L.dump("sb_s22_silh_fray.json", out)
