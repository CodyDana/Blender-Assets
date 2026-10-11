"""SMG01 polymer recolour maps + a pre-check through the pack's own derive step (plain Python; read-only use of the
pack code, no edit under Scripts/unreal/materials, so no PackMaterials lock; the AR-01's rifle_recolour.py):

    py -3 -B Scripts/guns/smg/smg_recolour.py [--tex DIR] [--bake DIR] [--gate PATH]

One recolour group SMG01 (spec materials.recolour): M_SMG01_Furniture + M_SMG01_Mag on M_Fabric_Master (Metal From
ORM off), the user colour = the polymer colour. Per member the item build writes Recolour/T_SMG01_<Set>_Detail16.png
(16-bit linear grey, the BC's size up to 2048, d = normalised lum(BC) over the set's texels, 3 px edge extension, one fill constant
elsewhere) and Recolour/recolour_maps.json (Colour = the set's mean linear albedo, Detail Bias / Scale so Colour x
(Bias + Scale x d) reproduces the baked luminance). W6 (PackMaterials lock, run_build.sh) derives the constants with a
maps/derive_constants_smg01.py.

Polymer is ONE hue by construction (black, B - R +2..3; whitening, dust, soot neutral), so the recolour path at the
default Colour should reproduce the shipped BC (pack gate P1: p99.9 <= 2 levels); measured here per set and part.
Pre-check (derive_constants.fabric_part, the pack's own gates) + the plan's 10-colour stress incl. FFFFFF FF0000 0000FF
F2E8D5 000000 and tan / OD / FDE: albedo finite, under the limit, grain kept. Writes the maps and the gate record
(default WorkFiles/guns/smg/gates/recolour_precheck.json).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MAPS = ROOT / "Scripts" / "unreal" / "materials" / "maps"
sys.path.insert(0, str(MAPS))
Image.MAX_IMAGE_PIXELS = None


def _load(name):
    sp = importlib.util.spec_from_file_location(name, str(MAPS / f"{name}.py"))
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


rc = _load("recolour_common")
tw = _load("np_twin")
dc = _load("derive_constants")
assert Path(rc.PROJECT).resolve() == ROOT.resolve(), rc.PROJECT
DET_MAX = 2048        # Detail16 = the BC's size up to 2048 (Furniture 4096 -> 2048: at 1024 the 4 x 4 average lost the
                     # stipple and the whitened edges, default path p99.9 6 levels; Mag 1024 -> 1024)
STRESS = ("FFFFFF", "FF0000", "0000FF", "F2E8D5", "000000", "808080", "1A1A1A", "3050A0", "2E5E2E", "6B3C27",
          "C2B280", "4B5320", "B08D57")          # + tan, OD green, FDE


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).resolve().relative_to(ROOT.resolve()).as_posix()


def detail(lum, cover):
    DET = min(DET_MAX, lum.shape[0])
    a_lo, a_hi = float(np.percentile(lum[cover], 0.05)), float(np.percentile(lum[cover], 99.95))
    d = np.clip((lum - a_lo) / max(a_hi - a_lo, 1e-9), 0.0, 1.0)
    n2 = lum.shape[0] // DET
    cm = cover.reshape(DET, n2, DET, n2).astype(np.float64)
    w = cm.sum(axis=(1, 3))
    dd = np.where(cover, d, 0.0).reshape(DET, n2, DET, n2).sum(axis=(1, 3))
    cov1 = w > 0
    d1 = np.where(cov1, dd / np.maximum(w, 1e-9), 0.0)
    val, ok = d1.copy(), cov1.copy()
    for _ in range(3):
        acc = np.zeros_like(val)
        cnt = np.zeros_like(val)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                acc += np.roll(np.roll(np.where(ok, val, 0.0), dy, 0), dx, 1)
                cnt += np.roll(np.roll(ok.astype(np.float64), dy, 0), dx, 1)
        new = (~ok) & (cnt > 0)
        val = np.where(new, acc / np.maximum(cnt, 1e-9), val)
        ok = ok | new
    q = np.rint(np.clip(val, 0, 1) * 65535.0).astype(np.int64)
    fill = int(np.rint(float(d1[cov1].mean()) * 65535.0))
    q = np.where(ok, q, fill)
    q = np.where(ok & (q == fill), np.minimum(fill + 1, 65535), q)
    return q, cov1, a_lo, a_hi, n2


def member(st, tex, bake):
    rec = tex / "Recolour"
    rec.mkdir(parents=True, exist_ok=True)
    bcp = tex / f"T_SMG01_{st}_BC.png"
    bc8 = np.asarray(Image.open(bcp).convert("RGB"), np.float64) / 255.0
    bc = tw.s2l(bc8)
    meta = json.loads((bake / "bake_meta.json").read_text())
    names = {v: k for k, v in meta["parts"].items()}
    pid = np.load(bake / f"{st}_ids.npy")[..., 0].astype(np.int32)[::-1]
    cover = pid > 0
    lum = bc @ rc.LUM
    colour = bc[cover].mean(axis=0)
    q, cov1, a_lo, a_hi, n2 = detail(lum, cover)
    DET = q.shape[0]
    p16 = rec / f"T_SMG01_{st}_Detail16.png"
    rc.png_write(p16, q, 16)
    back, bits, _ = rc.png_read(p16)
    ok_rt = bool(np.array_equal(back, q)) and bits == 16
    lum_c = float(colour @ rc.LUM)
    bias, scale = a_lo / lum_c, (a_hi - a_lo) / lum_c
    vals, cnts = np.unique(q, return_counts=True)
    fillv = int(vals[np.argmax(cnts)])
    covq = q != fillv
    kc = rc.fabric_constants(bias + scale * (q[covq] / 65535.0))
    inst = f"MI_SMG01_{st}"
    gen = {"instance": inst, "master": "M_Fabric_Master",
           "params": {"Colour": [*[round(float(x), 6) for x in colour], 1.0], "Detail Bias": round(bias, 6),
                      "Detail Scale": round(scale, 6), "Detail Mean": kc["mean"],
                      "Detail Highlight Ratio": kc["highlight_ratio"], "Detail Moments Low": kc["moments_low"],
                      "Detail Moments High": kc["moments_high"], "Dark Detail Follow": rc.DARK_FOLLOW,
                      "Albedo Ceiling": rc.ALBEDO_CEILING, "Specular Strength": 0.5},
           "switches": {"Metal From ORM": False, "Cloth Sheen": False, "Use Lettering": False,
                        "Use Original Baked Colours": "OFF is safe if default_path_vs_bc holds (one polymer hue)"}}
    der = dc.fabric_part("SMG01", f"SMG01/{st}", rel(p16), gen)
    p = der["params"]
    d16 = np.repeat(np.repeat(back / 65535.0, n2, 0), n2, 1)
    g, ce, _ = tw.fabric_scalar(p, d16, np.asarray(p["Colour"][:3]))
    alb = ce[None, None, :] * g[..., None]
    lev = np.abs(rc.q8_srgb(alb).astype(np.int32) - np.rint(bc8 * 255).astype(np.int32))
    per_part = {}
    for k in np.unique(pid[cover]):
        m = pid == k
        lv = lev[m].max(axis=1)
        per_part[names[int(k)]] = {"levels_p50": float(np.percentile(lv, 50)),
                                   "levels_p999": float(np.percentile(lv, 99.9))}
    allv = lev[cover].max(axis=1)
    stress, ok_stress = {}, True
    for hx in STRESS:
        col = dc.hexlin(hx)
        a, info = tw.fabric_albedo(p, d16[cover], col)
        lu = a @ rc.LUM
        row = {"max": round(float(a.max()), 4), "lum_p1_p99": [round(float(np.percentile(lu, 1)), 5),
                                                               round(float(np.percentile(lu, 99)), 5)],
               "grain_kept_p99_over_p1": round(float(np.percentile(lu, 99) / max(np.percentile(lu, 1), 1e-9)), 2),
               "H": round(info["H"], 3), "C_hi": round(info["C_hi"], 3)}
        row["pass"] = bool(np.isfinite(a).all() and a.max() <= tw.LIMIT + 1e-9 and row["grain_kept_p99_over_p1"] > 1.2)
        ok_stress &= row["pass"]
        stress[hx] = row
    cmax = float(max(p["Colour"][:3]))
    amax = float(alb[cover].max())
    mrec = {"file": rel(p16), "sha256": sha256(p16), "size": [DET, DET], "encoding": "LINEAR: value / 65535 = d",
            "source": rel(bcp), "source_sha256": sha256(bcp), "png_roundtrip_exact": ok_rt}
    out = {"detail_map": rel(p16), "png_roundtrip_exact": ok_rt,
           "derive_constants_fabric_part": {"gates": der["gates"], "pass": der["pass"],
                                            "params": {k: p[k] for k in ("Colour", "Lightest Colour", "Detail Mean",
                                                                         "Detail Highlight Ratio")}},
           "black_floor": {"colour_max": round(cmax, 5), "floor": tw.COLOUR_FLOOR, "pass": cmax > tw.COLOUR_FLOOR},
           "knee": {"max_default_albedo": round(amax, 4), "knee": tw.KNEE, "pass": amax <= tw.KNEE},
           "stress_13_colours": {"colours": stress, "pass": ok_stress},
           "default_path_vs_bc": {"levels_p999_all": float(np.percentile(allv, 99.9)), "per_part": per_part,
                                  "p1_bar_levels": 2.0,
                                  "pass": float(np.percentile(allv, 99.9)) <= 2.0},
           "pass": bool(ok_rt and der["pass"] and ok_stress and cmax > tw.COLOUR_FLOOR and amax <= tw.KNEE)}
    return gen, mrec, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default=str(ROOT / "Exports" / "Guns" / "SMG01" / "Textures"))
    ap.add_argument("--bake", default=str(ROOT / "WorkFiles" / "guns" / "smg" / "scratch" / "bake"))
    ap.add_argument("--gate", default=str(ROOT / "WorkFiles" / "guns" / "smg" / "gates" / "recolour_precheck.json"))
    a = ap.parse_args()
    tex, bake = Path(a.tex), Path(a.bake)
    maps = {"schema": "ninjapack.recolour_maps/1", "item": "SMG01", "generated": datetime.date.today().isoformat(),
            "generator": {"script": rel(__file__), "script_sha256": sha256(__file__),
                          "common_sha256": sha256(MAPS / "recolour_common.py")},
            "recolour_group": {"name": "SMG01", "members": ["M_SMG01_Furniture", "M_SMG01_Mag"],
                               "user_colour": "the polymer colour (Colour)"},
            "maps": {}, "parts": {}}
    res = {"generated": datetime.date.today().isoformat(), "members": {}}
    for st in ("Furniture", "Mag"):
        gen, mrec, out = member(st, tex, bake)
        maps["maps"][f"T_SMG01_{st}_Detail16"] = mrec
        maps["parts"][f"SMG01/{st}"] = gen
        res["members"][st] = out
        print("[SMG01-recolour]", st, "PASS" if out["pass"] else "FAIL",
              json.dumps(out["default_path_vs_bc"])[:300], json.dumps({k: v["pass"] for k, v in
                                                                        out["derive_constants_fabric_part"]["gates"].items()}))
    (tex / "Recolour" / "recolour_maps.json").write_text(json.dumps(maps, indent=1))
    res["pass"] = all(v["pass"] for v in res["members"].values())
    Path(a.gate).write_text(json.dumps(res, indent=1))
    print("[SMG01-recolour]", "PASS" if res["pass"] else "FAIL")


if __name__ == "__main__":
    main()
