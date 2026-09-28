"""Stage 7: per-rib angles from angular profiles (minima of the rib band = gaps between ribs; leaf-band edges = folds)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
def extrema(d, th, sep, lo, hi, kind):
    s = d if kind == 'min' else -d
    idx = []
    for j in range(2, len(d)-2):
        if not (lo <= th[j] <= hi): continue
        a0 = max(0, j-int(sep*10/2)); a1 = j+int(sep*10/2)+1
        if s[j] == np.min(s[a0:a1]): idx.append(j)
    return idx
res = {}
per = {1: 4.87, 2: 6.62}
rng = {1: (10, 170), 2: (2, 178)}
for i in (1, 2):
    th = -20 + 0.1*np.arange(2200)
    out = {}
    for b in ('rib', 'leaf'):
        prof = np.load(os.path.join(OUT, f"fm_prof{i}_{b}.npy"))
        p = np.where(np.isnan(prof), np.nanmean(prof), prof)
        # light smoothing
        k = np.array([1, 2, 3, 2, 1], float); k /= k.sum()
        ps = np.convolve(p, k, 'same')
        tr = np.convolve(ps, np.ones(int(per[i]*10))/int(per[i]*10), 'same')
        d = ps - tr
        mins = extrema(d, th, per[i]*0.7, *rng[i], 'min'); maxs = extrema(d, th, per[i]*0.7, *rng[i], 'max')
        out[b] = dict(min_deg=[round(float(th[j]), 1) for j in mins], max_deg=[round(float(th[j]), 1) for j in maxs],
                      min_amp=[round(float(d[j]), 4) for j in mins], max_amp=[round(float(d[j]), 4) for j in maxs],
                      raw_level_median=round(float(np.nanmedian(prof[(th > 20) & (th < 160)])), 4))
    res[i] = out
json.dump(res, open(os.path.join(OUT, "fm_s07_extrema.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
