"""Stage 14: radial luminance profiles (design masked, median over theta bands) and radial texture energy, to locate the leaf inner edge."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
res = {}
for i in (1, 2):
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy")); L = P @ LUMW.astype(np.float32)
    mx = P.max(2); mn = P.min(2); sat = (mx-mn)/(mx+1e-4)
    design = (L > (0.35 if i == 2 else 0.30)) | ((sat > 0.35) & (mx > 0.15))
    Lm = np.where(design, np.nan, L)
    # angular high-pass energy: |L - moving mean over 1 deg| per row, which is high in the pierced rib zone
    out = {}
    bands = [(20, 50), (50, 80), (80, 100), (100, 130), (130, 160)] if i == 2 else [(25, 50), (50, 80), (80, 100), (100, 130), (130, 150)]
    for t0, t1 in bands:
        j0, j1 = int((t0+20)*10), int((t1+20)*10)
        B = Lm[:, j0:j1]
        med = np.nanmedian(B, 1)
        # radial derivative of the median
        hp = np.nanmean(np.abs(np.diff(B, axis=1)), 1)
        out[f"{t0}-{t1}"] = dict(med=[round(float(v), 3) if not np.isnan(v) else None for v in med[0:420:4]],
                                 hp=[round(float(v), 3) if not np.isnan(v) else None for v in hp[0:420:4]])
    res[i] = out
json.dump(res, open(os.path.join(OUT, "fm_s14_radprof.json"), "w"))
for i in (1, 2):
    for k, v in res[i].items():
        print(f"M{i} {k:8s}", " ".join('--' if x is None else f"{int(x*100):2d}" for x in v['med']))
        print(f"H{i} {k:8s}", " ".join('--' if x is None else f"{int(x*1000):2d}" for x in v['hp']))
