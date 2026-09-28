"""Stage 20: outer-edge scallop. Subpixel outer radius r(theta) (50% crossing along each ray), detrended; period, amplitude, and phase vs the leaf light/dark faces."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json")))
res = {}
for i in (1, 2):
    cx, cy = S2[str(i)]["rivet_bright_centroid"]
    a = load(i); L = a @ LUMW.astype(np.float32); H, W = L.shape
    bg = 1.0 if i == 1 else 0.9647
    th = np.arange(0, 180, 0.1); rr = np.arange(250, 420, 0.25)
    T, R = np.meshgrid(np.radians(th), rr)
    X = cx + R*np.cos(T); Y = cy - R*np.sin(T)
    x0 = np.clip(np.floor(X).astype(int), 0, W-2); y0 = np.clip(np.floor(Y).astype(int), 0, H-2); fx = X-x0; fy = Y-y0
    S = L[y0, x0]*(1-fx)*(1-fy) + L[y0, x0+1]*fx*(1-fy) + L[y0+1, x0]*(1-fx)*fy + L[y0+1, x0+1]*fx*fy
    rout = np.full(len(th), np.nan)
    for j in range(len(th)):
        col = S[:, j]; dark = col < bg*0.5 + 0.5*0.12
        nz = np.nonzero(dark)[0]
        if len(nz) == 0 or nz.max() >= len(rr)-2: continue
        k = nz.max(); v0, v1 = col[k], col[k+1]; thr = bg*0.5 + 0.5*0.12
        rout[j] = rr[k] + 0.25*(thr - v0)/(v1 - v0 + 1e-6)
    rng = (18, 158) if i == 1 else (12, 170)
    sel = (th > rng[0]) & (th < rng[1]) & ~np.isnan(rout)
    t = th[sel]; r = rout[sel]
    # detrend by 3rd-order poly in sin/cos
    A = np.c_[np.ones_like(t), np.sin(np.radians(t)), np.cos(np.radians(t)), np.sin(2*np.radians(t)), np.cos(2*np.radians(t))]
    c, *_ = np.linalg.lstsq(A, r, rcond=None); d = r - A @ c
    F = np.abs(np.fft.rfft(d*np.hanning(len(d)), 16*len(d))); fr = np.fft.rfftfreq(16*len(d), 0.1)
    fs = (fr > 1/12) & (fr < 1/1.5); fpk = fr[fs][np.argmax(F[fs])]
    per = 1/fpk
    # amplitude: peak-to-trough via fold into one period
    ph = (t % per)/per; bins = np.linspace(0, 1, 21); idx = np.digitize(ph, bins)-1
    prof = np.array([np.median(d[idx == b]) for b in range(20)])
    np.save(os.path.join(OUT, f"fm_rout_sub{i}.npy"), np.c_[th, rout])
    # peaks list
    pk = [round(float(t[j]), 1) for j in range(5, len(d)-5) if d[j] == d[max(0, j-int(per*4)):j+int(per*4)+1].max()]
    vl = [round(float(t[j]), 1) for j in range(5, len(d)-5) if d[j] == d[max(0, j-int(per*4)):j+int(per*4)+1].min()]
    res[i] = dict(period_deg=round(float(per), 3), folded_profile_px=[round(float(v), 2) for v in prof],
                  p2p_px=round(float(prof.max()-prof.min()), 2), rms_px=round(float(d.std()), 2),
                  outward_peaks_deg=pk, inward_notches_deg=vl, trend_coef=[round(float(v), 3) for v in c])
json.dump(res, open(os.path.join(OUT, "fm_s20_scallop.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
