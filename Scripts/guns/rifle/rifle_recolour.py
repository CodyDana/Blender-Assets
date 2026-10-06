"""AR-01 furniture recolour maps + a pre-check through the pack's own derive step (plain Python, read-only use of the
pack code; no edit under Scripts/unreal/materials, so no PackMaterials lock):

    py -3 -B Scripts/guns/rifle/rifle_recolour.py

The katana convention (Scripts/Katana/katana_recolour.py): the item build writes Recolour/T_AR01_Furniture_Detail16.png
(16-bit linear grey, 1024, d = normalised lum(BC) over the wood texels, 3 px edge extension, one fill constant
elsewhere) and Recolour/recolour_maps.json (v1 fields: Colour = the wood's mean linear albedo, Detail Bias / Scale so
Colour x (Bias + Scale x d) reproduces the baked luminance). Stage 9 (PackMaterials lock, run_build.sh) derives
recolour_constants.json with maps/derive_constants_ar01.py.

How the per-part wood tone survives the pack (M_Fabric_Master: BaseColor = Colour x n, n a SCALAR from the detail):
  value   - each part's tone luminance is in lum(BC), hence in d: a recolour keeps the parts' relative values;
  hue     - the tone's chroma (unit luminance) is NOT representable by a scalar detail: a recolour gives all four parts
            the buyer's hue (they move together, the pack's recolour rule); the sheet's four hues are the baked BC.
  default - so the recolour path at the default Colour differs from the shipped BC by the per-part chroma offset
            (measured here, per part, in sRGB levels): the pack's "default capture = shipped BC (p99.9 <= 2 levels)"
            gate holds only with Use Original Baked Colours ON for the default instance (the recolour is the buyer's
            opt-in), which this report states for stage 9.
Pre-check (derive_constants.fabric_part on the map, the pack's own gates): default equals the v1 contract, every guard
inactive at the default (Colour above the master's black floor 0.01, below Lightest Colour, H >= 1, max albedo under
the 0.85 knee), every mip equals v1, the mip-compensated mean drift <= 2 % for the stress colours. Plus the 10-colour
stress of plan stage 9 (incl. FFFFFF FF0000 0000FF F2E8D5 000000): albedo finite, under the 0.95 limit, grain kept.
Writes Exports/Guns/AR01/Textures/Recolour/{T_AR01_Furniture_Detail16.png, recolour_maps.json} and
WorkFiles/guns/rifle/gates/recolour_precheck.json.
"""
from __future__ import annotations

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

TEX = ROOT / "Exports" / "Guns" / "AR01" / "Textures"
REC = TEX / "Recolour"
BAKE = ROOT / "WorkFiles" / "guns" / "rifle" / "scratch" / "bake"
DET = 1024
STRESS = ("FFFFFF", "FF0000", "0000FF", "F2E8D5", "000000", "808080", "1A1A1A", "3050A0", "2E5E2E", "6B3C27")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).resolve().relative_to(ROOT.resolve()).as_posix()


def detail(lum, cover):
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
    return q, cov1, a_lo, a_hi


def main():
    REC.mkdir(parents=True, exist_ok=True)
    bcp = TEX / "T_AR01_Furniture_BC.png"
    bc8 = np.asarray(Image.open(bcp).convert("RGB"), np.float64) / 255.0
    bc = tw.s2l(bc8)
    meta = json.loads((BAKE / "bake_meta.json").read_text())
    names = {v: k for k, v in meta["parts"].items()}
    pid = np.load(BAKE / "Furniture_ids.npy")[..., 0].astype(np.int32)[::-1]     # PNG rows (paint writes [::-1])
    cover = pid > 0
    lum = bc @ rc.LUM
    colour = bc[cover].mean(axis=0)
    q, cov1, a_lo, a_hi = detail(lum, cover)
    p16 = REC / "T_AR01_Furniture_Detail16.png"
    rc.png_write(p16, q, 16)
    back, bits, _ = rc.png_read(p16)
    ok_rt = bool(np.array_equal(back, q)) and bits == 16
    lum_c = float(colour @ rc.LUM)
    bias, scale = a_lo / lum_c, (a_hi - a_lo) / lum_c
    vals, cnts = np.unique(q, return_counts=True)
    fillv = int(vals[np.argmax(cnts)])
    covq = q != fillv
    kc = rc.fabric_constants(bias + scale * (q[covq] / 65535.0))
    gen = {"instance": "MI_AR01_Furniture", "master": "M_Fabric_Master",
           "params": {"Colour": [*[round(float(x), 6) for x in colour], 1.0], "Detail Bias": round(bias, 6),
                      "Detail Scale": round(scale, 6), "Detail Mean": kc["mean"],
                      "Detail Highlight Ratio": kc["highlight_ratio"], "Detail Moments Low": kc["moments_low"],
                      "Detail Moments High": kc["moments_high"], "Dark Detail Follow": rc.DARK_FOLLOW,
                      "Albedo Ceiling": rc.ALBEDO_CEILING, "Specular Strength": 0.5},
           "switches": {"Metal From ORM": False, "Cloth Sheen": False, "Use Lettering": False,
                        "Use Original Baked Colours": "ON for the shipped default (see default_path_vs_bc)"}}
    maps = {"schema": "ninjapack.recolour_maps/1", "item": "AR01", "generated": datetime.date.today().isoformat(),
            "generator": {"script": rel(__file__), "script_sha256": sha256(__file__),
                          "common_sha256": sha256(MAPS / "recolour_common.py")},
            "maps": {"T_AR01_Furniture_Detail16": {"file": rel(p16), "sha256": sha256(p16), "size": [DET, DET],
                                                   "encoding": "LINEAR: value / 65535 = d", "source": rel(bcp),
                                                   "source_sha256": sha256(bcp), "png_roundtrip_exact": ok_rt}},
            "parts": {"AR01/Furniture": gen},
            "wood_tone": "per-part tone ratios (rifle_wood_tone.py): value in the detail, hue in the BC only"}
    (REC / "recolour_maps.json").write_text(json.dumps(maps, indent=1))
    # ---- the pack's own derive step on this map (read-only)
    der = dc.fabric_part("AR01", "AR01/Furniture", rel(p16), gen)
    p = der["params"]
    # ---- default recolour path vs the shipped BC, per part (2048 BC vs the 1024 detail, upsampled 2x)
    d16 = np.repeat(np.repeat(back / 65535.0, 2, 0), 2, 1)
    g, ce, _ = tw.fabric_scalar(p, d16, np.asarray(p["Colour"][:3]))
    alb = ce[None, None, :] * g[..., None]
    lev = np.abs(rc.q8_srgb(alb).astype(np.int32) - np.rint(bc8 * 255).astype(np.int32))
    per_part = {}
    for k in np.unique(pid[cover]):
        m = pid == k
        lv = lev[m].max(axis=1)
        rel_val = float((bc[m] @ rc.LUM).mean() / (bc[cover] @ rc.LUM).mean())
        rel_val_rec = float((alb[m] @ rc.LUM).mean() / (alb[cover] @ rc.LUM).mean())
        per_part[names[int(k)]] = {"levels_p50": float(np.percentile(lv, 50)),
                                   "levels_p999": float(np.percentile(lv, 99.9)),
                                   "value_ratio_bc": round(rel_val, 4),
                                   "value_ratio_recolour_default": round(rel_val_rec, 4)}
    allv = lev[cover].max(axis=1)
    # ---- stress colours through the full v2 twin
    stress = {}
    ok_stress = True
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
    out = {"generated": datetime.date.today().isoformat(), "detail_map": rel(p16), "png_roundtrip_exact": ok_rt,
           "derive_constants_fabric_part": {"gates": der["gates"], "pass": der["pass"],
                                            "params": {k: p[k] for k in ("Colour", "Lightest Colour", "Detail Mean",
                                                                         "Detail Highlight Ratio")}},
           "black_floor": {"colour_max": round(cmax, 5), "floor": tw.COLOUR_FLOOR, "pass": cmax > tw.COLOUR_FLOOR},
           "knee": {"max_default_albedo": round(amax, 4), "knee": tw.KNEE, "pass": amax <= tw.KNEE},
           "stress_10_colours": {"colours": stress, "pass": ok_stress},
           "default_path_vs_bc": {"levels_p999_all": float(np.percentile(allv, 99.9)), "per_part": per_part,
                                  "note": "the recolour path at the default Colour carries one hue: each part's own "
                                          "hue offset shows here; value ratios are kept (value_ratio_*). Stage 9: "
                                          "Use Original Baked Colours ON for the default instance so the pack's "
                                          "default-capture gate (p99.9 <= 2 levels) compares the BC itself; a buyer "
                                          "recolour moves all four parts together."},
           "pass": bool(ok_rt and der["pass"] and ok_stress and cmax > tw.COLOUR_FLOOR and amax <= tw.KNEE)}
    (ROOT / "WorkFiles" / "guns" / "rifle" / "gates" / "recolour_precheck.json").write_text(json.dumps(out, indent=1))
    print("[AR01-recolour]", "PASS" if out["pass"] else "FAIL", json.dumps(out["default_path_vs_bc"]["per_part"]),
          json.dumps({k: v["pass"] for k, v in der["gates"].items()}))


if __name__ == "__main__":
    main()
