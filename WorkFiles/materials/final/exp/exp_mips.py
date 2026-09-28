"""Experiment 3: mean cap (MaxMean) + mip strategies. Covered texels; mip truth = box of the mip-0 result."""
import json, sys, time
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import recolour_common as rc
_argv = sys.argv; sys.argv = sys.argv[:1]
exec(compile((P / "WorkFiles/materials/final/exp/exp_models.py").read_text().split("res = {}")[0], "m", "exec"))
sys.argv = _argv
ONLY = sys.argv[1] if len(sys.argv) > 1 else None
CAPS = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0.55, 0.63, 0.7]
DO_MIPS = len(sys.argv) > 3 and sys.argv[3] == "mips"
COLS = ["FFFFFF", "F2E8D5", "FF0000", "E7E7E7", "808080", "B01010", "1A1A1A"]
def fab(n, k, colour, cap, mode=None, sig2=0.0, G=None):
    colour = np.asarray(colour, float)
    colour = colour + max(FLOOR - colour.max(), 0.0)
    colour = colour * min(1.0, cap / max(colour.max(), 1e-4))
    cmax = colour.max()
    H = np.log(CEIL / cmax) / np.log(k["highlight_ratio"])
    chi = min(1.0, max(H, 0.0)); clo = 1.0 + (chi - 1.0) * FOLLOW
    nn = np.maximum(n, 1e-6)
    ex = np.where(nn > 1.0, chi, clo)
    if mode == "G":
        s = np.power(G, ex) * np.power(nn / G, ex * ex)
    else:
        s = np.power(nn, ex)
        if mode == "sig":
            s = s * np.exp(ex * (ex - 1.0) * sig2 / 2.0)
    e = poly(k["moments_low"], clo) + poly(k["moments_high"], chi)
    s = s * (k["mean"] / e)
    m = cmax * s; w = LIMIT - KNEE
    mm = KNEE + w * (1 - np.exp(-np.maximum(m - KNEE, 0) / w))
    return colour, s * (mm / np.maximum(m, KNEE)), chi
out = {}
for name, (grp, part, png) in PARTS.items():
    if ONLY and ONLY not in name: continue
    rm = json.loads((P / f"Exports/{grp}/Textures/Recolour/recolour_maps.json").read_text())
    p = rm["parts"][part]["params"]
    d16, _, _ = rc.png_read(P / png)
    vals, cnts = np.unique(d16, return_counts=True); fill = int(vals[np.argmax(cnts)])
    cov = d16 != fill
    d = d16 / 65535.0
    n_old = p["Detail Bias"] + p["Detail Scale"] * d
    mcov = float(n_old[cov].mean())
    bias, scale = p["Detail Bias"] / mcov, p["Detail Scale"] / mcov
    n = bias + scale * d
    dcol = np.array(p["Colour"][:3]) * mcov
    k = consts(n[cov], 99.9)
    nc = n[cov]; hi = nc > 1
    _, g0, _ = fab(nc, k, dcol, 10.0)
    q0 = rc.q8_srgb(dcol[None] * g0[:, None]).astype(np.int32); ll0 = logl(q0)
    R = {}
    for cap in CAPS:
        for h in COLS:
            pick = hexlin(h)
            ce, g, chi = fab(nc, k, pick, cap)
            lin = ce[None] * g[:, None]; q = rc.q8_srgb(lin).astype(np.int32)
            dom = int(np.argmax(ce)); pl, used = plateau(q[:, dom]); plh, _ = plateau(q[hi, dom]); ll = logl(q)
            mean = lin.mean(0)
            r = {"out": "".join(f"{v:02X}" for v in rc.q8_srgb(mean)), "dE": round(float(rc.de2000(mean, pick)), 2), "pl": round(pl, 3), "plh": round(plh, 3), "lv": used,
                 "det": round(float(ll.std() / ll0.std()), 3), "deth": round(float(ll[hi].std() / ll0[hi].std()), 3), "detl": round(float(ll[~hi].std() / ll0[~hi].std()), 3), "chi": round(chi, 3)}
            R[f"cap{cap}_{h}"] = r
            print(f"{name:16s} cap {cap} {h} out#{r['out']} dE{r['dE']:5.2f} pl {r['pl']:.3f} plh {r['plh']:.3f} lv {used:3d} det {r['det']:.2f} hi {r['deth']:.2f} lo {r['detl']:.2f} chi {chi:.3f}", flush=True)
    if DO_MIPS:
        cap = CAPS[0]
        ln = np.log(np.maximum(n, 1e-6))
        # mip chains: n (G16 of d), log n (G16 of normalised log), coverage
        dk, lk, ck, l2k = d, ln, cov.astype(float), ln * ln
        lo_l, hi_l = float(ln.min()), float(ln.max())
        lq = np.rint((ln - lo_l) / (hi_l - lo_l) * 65535) / 65535
        lqk = lq
        truths = {h: None for h in ["FFFFFF", "F2E8D5", "808080", "B01010", "E7E7E7"]}
        full = {}
        for h in truths:
            ce, g, _ = fab(n, k, hexlin(h), cap)
            truths[h] = ce[None, None] * g[..., None]
        sig_tab = []
        for kk in range(1, 7):
            dk = np.rint(box(dk) * 65535) / 65535; lqk = np.rint(box(lqk) * 65535) / 65535
            lk2 = box(lk); l2k = box(l2k); ck = box(ck); lk = lk2
            m = ck >= 0.5
            s2 = float(np.maximum(l2k - lk * lk, 0)[ck >= 0.99].mean())
            sig_tab.append(s2)
            nk = bias + scale * dk
            G = np.exp(lo_l + lqk * (hi_l - lo_l))
            for h in truths:
                truths[h] = box(truths[h])
                if kk not in (2, 4, 6): continue
                t = truths[h][m]
                row = {}
                for mode in ("plain", "sig", "G"):
                    ce, g, _ = fab(nk, k, hexlin(h), cap, None if mode == "plain" else mode, s2, G)
                    gpu = (ce[None, None] * g[..., None])[m]
                    lr = float((gpu.mean(0) @ LUM) / (t.mean(0) @ LUM))
                    step = max(1, len(t) // 50000)
                    dd = rc.de2000(gpu[::step], t[::step])
                    row[mode] = (round(lr, 4), round(float(dd.mean()), 2), round(float(np.percentile(dd, 95)), 2))
                print(f"   {name} mip{kk} {h} sig2 {s2:.3f}  " + "  ".join(f"{mo}: Lx{v[0]} dE {v[1]}/{v[2]}" for mo, v in row.items()), flush=True)
        R["sig_tab"] = sig_tab
    out[name] = R
(P / f"WorkFiles/materials/final/exp/exp_mips_{ONLY or 'all'}.json").write_text(json.dumps(out, indent=1))
