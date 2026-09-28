"""Experiment 1: per-part detail statistics over COVERED texels and per-mip log variance."""
import json, sys
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import recolour_common as rc
PARTS = {
 "Kunai_Wrap": ("Shuriken", "Kunai_Plain/Wrap", "Exports/Shuriken/Textures/Recolour/T_Kunai_Wrap_Detail16.png"),
 "SmokeBomb_Cloth": ("SmokeBomb", "Cloth", "Exports/SmokeBomb/Textures/Recolour/T_SmokeBomb_Detail16.png"),
 "BlackHat_Straw": ("BlackHat", "Straw", "Exports/BlackHat/Textures/Recolour/T_BlackHat_Straw_Detail16.png"),
 "BlackHat_Cloth": ("BlackHat", "Cloth", "Exports/BlackHat/Textures/Recolour/T_BlackHat_Cloth_Detail16.png"),
}
def box(a): h, w = a.shape; return a.reshape(h//2, 2, w//2, 2).mean(axis=(1, 3))
out = {}
for name, (grp, part, png) in PARTS.items():
    rm = json.loads((P / f"Exports/{grp}/Textures/Recolour/recolour_maps.json").read_text())
    p = rm["parts"][part]["params"]
    d16, _, _ = rc.png_read(P / png)
    vals, cnts = np.unique(d16, return_counts=True)
    fill = int(vals[np.argmax(cnts)])
    cov = d16 != fill
    d = d16 / 65535.0
    n = p["Detail Bias"] + p["Detail Scale"] * d
    nc = n[cov]
    r = {"size": d.shape[0], "fill_d16": fill, "fill_frac": float(1 - cov.mean()), "fill_n": float(p["Detail Bias"] + p["Detail Scale"] * fill / 65535),
         "mean_all": float(n.mean()), "mean_cov": float(nc.mean()),
         "p50": float(np.percentile(nc, 50)), "p90": float(np.percentile(nc, 90)), "p99": float(np.percentile(nc, 99)), "p999": float(np.percentile(nc, 99.9)),
         "p999_all": float(np.percentile(n, 99.9)), "max": float(nc.max()), "min": float(nc.min()), "frac_gt1": float((nc > 1).mean())}
    ln = np.log(np.maximum(n, 1e-6))
    r["logvar_total_cov"] = float(ln[cov].var())
    # per-mip within-footprint log variance and mean-n variance, covered-mostly texels
    L, L2, C = ln.copy(), ln * ln, cov.astype(float)
    dk = d.copy()
    sig = []
    for k in range(1, 9):
        L, L2, C = box(L), box(L2), box(C)
        m = C >= 0.99
        v = np.maximum(L2 - L * L, 0)
        sig.append({"k": k, "sigma2_mean": float(v[m].mean()) if m.any() else None, "sigma2_p50": float(np.median(v[m])) if m.any() else None, "texels": int(m.sum())})
    r["sigma2_by_mip"] = sig
    out[name] = r
    print(name, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != "sigma2_by_mip"}))
    print("   sigma2:", [(s["k"], round(s["sigma2_mean"], 4) if s["sigma2_mean"] else None) for s in sig])
(P / "WorkFiles/materials/final/exp/exp_stats.json").write_text(json.dumps(out, indent=1))
