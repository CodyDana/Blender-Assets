"""Stage 6: angular luminance profiles (design masked) in the leaf band and the bare-rib band; period by autocorrelation."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
bands = {1: dict(leaf=(240, 380), rib=(40, 190)), 2: dict(leaf=(175, 315), rib=(45, 140))}
res = {}
for i in (1, 2):
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy"))
    L = P @ LUMW.astype(np.float32)
    mx = P.max(2); mn = P.min(2); sat = (mx-mn)/(mx+1e-4)
    design = (L > (0.30 if i == 2 else 0.25)) | ((sat > 0.35) & (mx > 0.15))
    th = -20 + 0.1*np.arange(L.shape[1])
    out = {}
    for bname, (r0, r1) in bands[i].items():
        Lb = np.where(design[r0:r1], np.nan, L[r0:r1])
        prof = np.nanmedian(Lb, 0)
        frac_design = float(design[r0:r1].mean())
        np.save(os.path.join(OUT, f"fm_prof{i}_{bname}.npy"), prof)
        # detrend with 8-deg moving mean
        ok = ~np.isnan(prof)
        p = np.where(ok, prof, np.nanmean(prof))
        k = 80; ker = np.ones(k)/k
        trend = np.convolve(p, ker, 'same')
        d = p - trend
        # restrict to interior angles
        sel = (th > (22 if i == 1 else 16)) & (th < (156 if i == 1 else 168))
        dd = d[sel] - d[sel].mean()
        ac = np.correlate(dd, dd, 'full')[len(dd)-1:]; ac /= ac[0]
        lags = np.arange(len(ac))*0.1
        # first peak after lag 2 deg
        w = (lags > 2) & (lags < 15)
        jpk = np.argmax(np.where(w, ac, -9))
        # refine parabolic
        y0, y1, y2 = ac[jpk-1], ac[jpk], ac[jpk+1]; off = 0.5*(y0-y2)/(y0-2*y1+y2)
        per = (jpk+off)*0.1
        # multiple-period refinement: peak near n*per for n = 1..8
        pk = []
        for n in range(1, 9):
            c = int(round(n*per*10)); a0 = max(1, c-8); a1 = c+9
            if a1 >= len(ac)-1: break
            jj = a0 + np.argmax(ac[a0:a1]); y0, y1, y2 = ac[jj-1], ac[jj], ac[jj+1]; o = 0.5*(y0-y2)/(y0-2*y1+y2)
            pk.append(((jj+o)*0.1, round(float(ac[jj]), 3)))
        per_ls = float(np.polyfit(np.arange(1, len(pk)+1), [q[0] for q in pk], 1)[0]) if len(pk) > 2 else per
        # spectrum
        F = np.abs(np.fft.rfft(dd*np.hanning(len(dd)), 8*len(dd))); fr = np.fft.rfftfreq(8*len(dd), 0.1)
        fsel = (fr > 1/15) & (fr < 1/2)
        fpk = fr[fsel][np.argmax(F[fsel])]
        out[bname] = dict(design_frac=round(frac_design, 3), period_ac1=round(per, 3), period_multi=round(per_ls, 3),
                          ac_peaks=[[round(a, 2), b] for a, b in pk], period_fft=round(1/fpk, 3))
        np.save(os.path.join(OUT, f"fm_dprof{i}_{bname}.npy"), d)
    res[i] = out
json.dump(res, open(os.path.join(OUT, "fm_s06_angprof.json"), "w"), indent=1)
print("FMRES", json.dumps(res))
