"""Stage 24: pleat face contrast (lit/unlit face luminance ratio, linear) vs radius and vs theta, design masked; plus the
angular sawtooth shape (rise width vs drop width) at r = 300-325, fan2."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
P = np.load(os.path.join(OUT, "fm_polar2.npy")); Ls = P @ LUMW.astype(np.float32); Lin = srgb2lin(P) @ LUMW
mx = P.max(2); mn = P.min(2); sat = (mx-mn)/(mx+1e-4)
design = (Ls > 0.30) | ((sat > 0.30) & (mx > 0.12))
th = -20 + 0.1*np.arange(P.shape[1])
res = dict(by_radius={}, by_theta={})
def ratio(r0, r1, t0, t1):
    sel = (th > t0) & (th < t1)
    B = np.where(design[r0:r1][:, sel], np.nan, Lin[r0:r1][:, sel]); prof = np.nanmedian(B, 0)
    ok = ~np.isnan(prof); prof = prof[ok]
    if len(prof) < 50: return None
    hi = np.percentile(prof, 85); lo = np.percentile(prof, 15)
    return round(float(hi/lo), 2), round(float(hi), 4), round(float(lo), 4)
for r0, r1 in ((152, 190), (190, 230), (230, 270), (270, 305), (305, 322)):
    res['by_radius'][f"{r0}-{r1}"] = ratio(r0, r1, 15, 168)
for t0 in range(15, 165, 25):
    res['by_theta'][f"{t0}-{t0+25}"] = ratio(200, 300, t0, t0+25)
# sawtooth: rising vs falling run lengths of the smoothed angular profile at r 300-322
sel = (th > 14) & (th < 168)
B = np.where(design[300:322][:, sel], np.nan, Lin[300:322][:, sel]); prof = np.nanmedian(B, 0)
prof = np.where(np.isnan(prof), np.nanmean(prof), prof); prof = np.convolve(prof, np.ones(5)/5, 'same')
dp = np.sign(np.diff(prof)); runs = []; cur = dp[0]; n = 0
for v in dp:
    if v == cur: n += 1
    else: runs.append((int(cur), n)); cur = v; n = 1
up = [n*0.1 for s, n in runs if s > 0 and n >= 3]; dn = [n*0.1 for s, n in runs if s < 0 and n >= 3]
res['sawtooth_r300_322'] = dict(rise_deg_median=round(float(np.median(up)), 2), fall_deg_median=round(float(np.median(dn)), 2), n_rise=len(up), n_fall=len(dn))
json.dump(res, open(os.path.join(OUT, "fm_s24_pleatcontrast.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
