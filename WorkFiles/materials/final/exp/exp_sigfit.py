"""Experiment 4: fitted effective log-variance per mip (map mean exact) - is it colour independent?"""
import json, sys
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import recolour_common as rc
_argv = sys.argv; sys.argv = sys.argv[:1]
exec(compile((P / "WorkFiles/materials/final/exp/exp_mips.py").read_text().split("out = {}")[0].replace("_argv = sys.argv; sys.argv = sys.argv[:1]\n", "").replace("sys.argv = _argv\n", ""), "m", "exec"))
sys.argv = _argv
ONLY = sys.argv[1]; CAP = float(sys.argv[2])
COLS = ["FFFFFF", "F2E8D5", "B01010", "808080", "3050A0", "E7E7E7", "404040"]
for name, (grp, part, png) in PARTS.items():
    if ONLY not in name: continue
    rm = json.loads((P / f"Exports/{grp}/Textures/Recolour/recolour_maps.json").read_text())
    p = rm["parts"][part]["params"]
    d16, _, _ = rc.png_read(P / png)
    vals, cnts = np.unique(d16, return_counts=True); fill = int(vals[np.argmax(cnts)])
    cov = d16 != fill; d = d16 / 65535.0
    n_old = p["Detail Bias"] + p["Detail Scale"] * d; mcov = float(n_old[cov].mean())
    bias, scale = p["Detail Bias"] / mcov, p["Detail Scale"] / mcov
    n = bias + scale * d
    k = consts(n[cov], 99.9)
    truths = {}
    for h in COLS:
        ce, g, chi = fab(n, k, hexlin(h), CAP); truths[h] = (g, chi)
    dk, ck = d, cov.astype(float)
    table = []
    for kk in range(1, 9):
        dk = np.rint(box(dk) * 65535) / 65535; ck = box(ck)
        m = ck >= 0.5
        nk = bias + scale * dk
        row = {}
        for h in COLS:
            g, chi = truths[h]; g = box(g); truths[h] = (g, chi)
            t = g[m].mean()
            ce, gp, _ = fab(nk[m], k, hexlin(h), CAP)
            # plain gpu scalar s before rolloff approx: use fab with sig via bisection
            lo, hi = 0.0, 6.0
            for _ in range(50):
                mid = (lo + hi) / 2
                _, gs, _ = fab(nk[m], k, hexlin(h), CAP, "sig", mid)
                if gs.mean() > t: lo = mid
                else: hi = mid
            row[h] = (round(chi, 3), round(float(gp.mean() / t), 4), round((lo + hi) / 2, 4))
        table.append(row)
        print(f"{name} mip{kk}: " + "  ".join(f"{h}[chi {v[0]} plain x{v[1]} sig2eff {v[2]}]" for h, v in row.items()), flush=True)
