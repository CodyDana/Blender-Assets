"""Stage 15: leaf inner edge radius per theta band from the radial gradient (edge is a sharp arc in the polar image)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
res = {}
for i in (1, 2):
    P = np.load(os.path.join(OUT, f"fm_polar{i}.npy")); L = P @ LUMW.astype(np.float32)
    mx = P.max(2); mn = P.min(2); sat = (mx-mn)/(mx+1e-4)
    design = (L > (0.35 if i == 2 else 0.30)) | ((sat > 0.35) & (mx > 0.15))
    G = np.full_like(L, np.nan); G[1:-1] = (L[2:] - L[:-2])/2
    G[design] = np.nan
    th = -20 + 0.1*np.arange(L.shape[1])
    out = {}
    for t0 in range(10, 175, 10):
        sel = (th >= t0) & (th < t0+10)
        g = np.nanmedian(G[:, sel], 1)
        g_abs = np.nanmean(np.abs(G[:, sel]), 1)
        win = slice(90, 260)
        if np.all(np.isnan(g[win])): continue
        r_signed_min = 90 + int(np.nanargmin(g[win])); r_signed_max = 90 + int(np.nanargmax(g[win]))
        r_abs = 90 + int(np.nanargmax(g_abs[win]))
        out[f"{t0}-{t0+10}"] = dict(r_neg=r_signed_min, g_neg=round(float(np.nanmin(g[win])), 4), r_pos=r_signed_max,
                                    g_pos=round(float(np.nanmax(g[win])), 4), r_absmax=r_abs)
    res[i] = out
json.dump(res, open(os.path.join(OUT, "fm_s15_leafedge.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
