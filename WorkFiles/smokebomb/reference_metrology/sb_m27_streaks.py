"""Stage 27: persistent warp streaks ('slub' lines): average log-lum along the strip direction over a long window,
detrend across the strip, count streak peaks and their amplitude and spacing. Also the along-strip correlation length
of the texture (how far a bright thread segment persists)."""
import sys, os
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

rgb = L.load_srgb(); Y = L.lum(rgb)
Yl = np.log(np.clip(L.gauss_blur(Y, 0.6), 0.02, 1)).astype(np.float64)
# (centre, strip dir deg y-up, along half-length, across half-width)
P = {"A": ((640, 740), -29, 110, 70), "B": ((930, 468), 3, 100, 55), "C": ((330, 805), 21, 90, 70), "X": ((990, 615), -18, 60, 40)}
out = {}
for k, ((cx, cy), d, hl, hw) in P.items():
    t = np.radians(d)
    u = np.array([np.cos(t), -np.sin(t)]); n = np.array([np.sin(t), np.cos(t)])
    s = np.arange(-hl, hl + 1, 1.0); v = np.arange(-hw, hw + 1, 0.5)
    X = cx + s[None, :] * u[0] + v[:, None] * n[0]
    Yc = cy + s[None, :] * u[1] + v[:, None] * n[1]
    R = L.bilinear(Yl, X, Yc)
    prof = R.mean(1)
    tr = np.convolve(prof, np.ones(31) / 31, mode='same')
    d_ = (prof - tr)[20:-20]
    pk = [i for i in range(2, len(d_) - 2) if d_[i] == d_[max(0, i - 6):i + 7].max() and d_[i] > 0.04]
    # along-strip autocorrelation of the raw rows (mean over rows)
    Rz = R - R.mean(1, keepdims=True)
    ac = np.array([np.mean(Rz[:, :-l] * Rz[:, l:]) for l in range(1, 40)]) / np.mean(Rz * Rz)
    corr_len = int(np.argmax(ac < 0.3)) + 1 if (ac < 0.3).any() else 40
    # across-strip autocorrelation
    Cz = R - R.mean(0, keepdims=True)
    acx = np.array([np.mean(Cz[:-l, :] * Cz[l:, :]) for l in range(1, 30)]) / np.mean(Cz * Cz)
    corr_x = (int(np.argmax(acx < 0.3)) + 1) * 0.5 if (acx < 0.3).any() else 15
    sp = np.diff(np.array(pk)) * 0.5 if len(pk) > 1 else np.array([np.nan])
    out[k] = dict(streaks=len(pk), across_px=float(len(d_) * 0.5), streaks_per_100px=round(len(pk) / (len(d_) * 0.5) * 100, 1),
                  amp_log_median=round(float(np.median(d_[pk])) if pk else 0, 3), spacing_px_median=round(float(np.nanmedian(sp)), 1),
                  persistent_std_log=round(float(d_.std()), 3), raw_std_log=round(float((R - R.mean()).std()), 3),
                  along_corr_len_px=corr_len, across_corr_len_px=corr_x)
    print(k, out[k])
L.dump("sb_s27_streaks.json", out)
