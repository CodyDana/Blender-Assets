"""Experiment 2: candidate MF_TintDetail fixes on the fabric parts (covered texels only)."""
import json, sys, time
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import recolour_common as rc
PARTS = json.loads((P / "WorkFiles/materials/final/exp/parts.json").read_text()) if False else None
PARTS = {
 "Kunai_Wrap": ("Shuriken", "Kunai_Plain/Wrap", "Exports/Shuriken/Textures/Recolour/T_Kunai_Wrap_Detail16.png"),
 "SmokeBomb_Cloth": ("SmokeBomb", "Cloth", "Exports/SmokeBomb/Textures/Recolour/T_SmokeBomb_Detail16.png"),
 "BlackHat_Straw": ("BlackHat", "Straw", "Exports/BlackHat/Textures/Recolour/T_BlackHat_Straw_Detail16.png"),
 "BlackHat_Cloth": ("BlackHat", "Cloth", "Exports/BlackHat/Textures/Recolour/T_BlackHat_Cloth_Detail16.png"),
}
ONLY = sys.argv[1] if len(sys.argv) > 1 else None
CMINS = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0.25, 0.35, 0.45]
PCT = float(sys.argv[3]) if len(sys.argv) > 3 else 99.9
COLS = ["FFFFFF", "F2E8D5", "FF0000", "0000FF", "E7E7E7", "808080", "B01010", "1A1A1A", "000000"]
LUM = rc.LUM
KNEE, LIMIT, CEIL, FOLLOW, FLOOR = 0.85, 0.95, 0.9, 0.5, 0.01
def hexlin(h): return rc.s2l(np.array([int(h[i:i+2], 16) for i in (0, 2, 4)]) / 255.0)
def box(a): h, w = a.shape[:2]; return a.reshape(h//2, 2, w//2, 2, *a.shape[2:]).mean(axis=(1, 3))
def poly(m, c): return m[0] + c * (m[1] + c * (m[2] + c * m[3]))
def consts(n, pct):
    k = rc.fabric_constants(n)
    k["highlight_ratio"] = float(np.percentile(n, pct))
    return k
def model(n, k, colour, cmin=None, floor=None, sig2=None, G=None):
    colour = np.asarray(colour, float)
    if floor is not None:
        colour = colour + max(floor - colour.max(), 0.0)
    cmax = max(colour.max(), 1e-4)
    if cmin is not None:
        cap = CEIL / k["highlight_ratio"] ** cmin
        colour = colour * min(1.0, cap / cmax); cmax = max(colour.max(), 1e-4)
    H = np.log(CEIL / cmax) / np.log(k["highlight_ratio"])
    chi = min(1.0, max(H, 0.0)); clo = 1.0 + (chi - 1.0) * FOLLOW
    nn = np.maximum(n, 1e-6)
    expo = np.where(nn > 1.0, chi, clo)
    if G is not None:
        s = np.power(G, expo) * np.power(nn / G, expo * expo)
    else:
        s = np.power(nn, expo)
        if sig2 is not None:
            s = s * np.exp(expo * (expo - 1.0) * sig2 / 2.0)
    e = poly(k["moments_low"], clo) + poly(k["moments_high"], chi)
    s = s * (k["mean"] / e)
    m = colour.max() * s
    w = LIMIT - KNEE
    mm = KNEE + w * (1 - np.exp(-np.maximum(m - KNEE, 0) / w))
    g = s * (mm / np.maximum(m, KNEE))
    return colour, g, {"H": float(H), "chi": chi, "clo": clo}
def plateau(v):
    c = np.bincount(v.ravel(), minlength=256); return float(c.max() / max(v.size, 1)), int((c > 0).sum())
def logl(q): return np.log(np.maximum(rc.s2l(q / 255.0) @ LUM, 1e-5))
res = {}
for name, (grp, part, png) in PARTS.items():
    if ONLY and ONLY not in name: continue
    t0 = time.time()
    rm = json.loads((P / f"Exports/{grp}/Textures/Recolour/recolour_maps.json").read_text())
    p = rm["parts"][part]["params"]
    d16, _, _ = rc.png_read(P / png)
    vals, cnts = np.unique(d16, return_counts=True); fill = int(vals[np.argmax(cnts)])
    cov = (d16 != fill)
    d = d16 / 65535.0
    # renormalise to covered mean (Colour' = Colour x m, n' = n / m)
    n_old = p["Detail Bias"] + p["Detail Scale"] * d
    mcov = float(n_old[cov].mean())
    n = n_old / mcov
    dcol = np.array(p["Colour"][:3]) * mcov
    k = consts(n[cov], PCT)
    nc = n[cov]
    _, g0, _ = model(nc, k, dcol)
    q0 = rc.q8_srgb(dcol[None] * g0[:, None]).astype(np.int32)
    ll0 = logl(q0); hi = nc > 1
    R = {"mcov": mcov, "k": {kk: k[kk] for kk in ("mean", "highlight_ratio", "moments_low", "moments_high")}, "cols": {}}
    for h in COLS:
        pick = hexlin(h)
        for label, cmin, fl in [("orig", None, None)] + [(f"cmin{c}", c, FLOOR) for c in CMINS]:
            ce, g, info = model(nc, k, pick, cmin, fl)
            lin = ce[None] * g[:, None]
            q = rc.q8_srgb(lin).astype(np.int32)
            dom = int(np.argmax(ce)) if ce.max() > 0 else 1
            pl, used = plateau(q[:, dom]); plh, _ = plateau(q[hi, dom])
            ll = logl(q)
            mean = lin.mean(0)
            r = {"out": "".join(f"{v:02X}" for v in rc.q8_srgb(mean)), "dE": round(float(rc.de2000(mean, pick)), 2),
                 "pl": round(pl, 3), "plh": round(plh, 3), "lv": used,
                 "det": round(float(ll.std() / ll0.std()), 3) if ll.std() > 0 else 0,
                 "deth": round(float(ll[hi].std() / ll0[hi].std()), 3), "detl": round(float(ll[~hi].std() / ll0[~hi].std()), 3),
                 "lim": round(float((ce.max() * g >= 0.94).mean()), 4), **{kk: round(v, 3) for kk, v in info.items()}}
            R["cols"][f"{h}_{label}"] = r
            print(f"{name:16s} {h} {label:8s} out#{r['out']} dE{r['dE']:5.2f} pl {r['pl']:.3f} plh {r['plh']:.3f} lv {used:3d} det {r['det']:.2f} hi {r['deth']:.2f} lo {r['detl']:.2f} lim {r['lim']:.4f} chi {info['chi']:.2f}", flush=True)
    res[name] = R
    print(name, "sec", round(time.time() - t0, 1), flush=True)
(P / f"WorkFiles/materials/final/exp/exp_models_{ONLY or 'all'}_{PCT}.json").write_text(json.dumps(res, indent=1))
