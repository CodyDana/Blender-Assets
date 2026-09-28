"""Derive the version-2 recolour constants of every recolourable part from its Recolour maps (final pass, 2026-09-26).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/unreal/materials/maps/derive_constants.py -- [--only SmokeBomb]

Reads (never writes) each item's Recolour/recolour_maps.json and the maps it lists, and writes a NEW file next to it:
Exports/<Group>/Textures/Recolour/recolour_constants.json. np_spec.py merges it OVER recolour_maps.json (a constant here
wins over the generator's), so the map generators stay untouched and their recorded gates stay valid.

Fabric parts (the map generators' numbers were over EVERY texel, including the 21-35 % constant background fill
outside the UV islands, which no mesh shows; that made 'Colour' differ from the visible mean and shifted the
highlight ratio and moments):
    m            = mean of n over COVERED texels (d16 != the fill value)
    Colour'      = Colour * m;  Bias' = Bias / m;  Scale' = Scale / m      (Colour' * n' = Colour * n: the default
                                                                            look is unchanged to float rounding)
    Detail Mean, Highlight Ratio (p99.9), Moments: over covered texels
    Lightest Colour = min(0.6, AlbedoCeiling / HighlightRatio^0.2)          (the brightest mean that still keeps a
                                                                            highlight exponent >= 0.2)
    Detail Mip Compensation: the power law runs on the MIP-FILTERED detail, so a recoloured part reads lighter at
        distance (Jensen). For C_hi on a grid, R_k(C) = mean(graph on mip k) / mean(box^k of the mip-0 graph) is
        measured on the Unreal mip chain (2x2 box, 16-bit), and log R_k = A_k (1 - C_hi)^P is fitted (A_0 = 0).
        The master multiplies by exp(-A(lod) (1 - C_hi)^P); A(lod) is piecewise linear, stored as increments.
Paper bomb:
    Paper Colour Limit = AlbedoCeiling / p99.9 of the paper weight (PaperDetail.rgb decoded x Paper Weight Scale),
        so a full-intensity paper colour keeps its grain (the default, max 0.900, is below it: unchanged)
    Red Ink Pool Default Saturation = saturation of the default red ink (the pool-gain chroma fades with it)
Gates (all must pass, else exit 1): the v2 twin at the default colour equals the v1 contract to float rounding at mip
0 and at every mip; every guard is inactive at the default; the mip fit's corrected map means are within 2 %.
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402

VERSION = "2.0.0"
FABRIC = {
    "Shuriken": {"Kunai_Plain/Wrap": "Exports/Shuriken/Textures/Recolour/T_Kunai_Wrap_Detail16.png"},
    "SmokeBomb": {"Cloth": "Exports/SmokeBomb/Textures/Recolour/T_SmokeBomb_Detail16.png"},
    "BlackHat": {"Straw": "Exports/BlackHat/Textures/Recolour/T_BlackHat_Straw_Detail16.png",
                 "Cloth": "Exports/BlackHat/Textures/Recolour/T_BlackHat_Cloth_Detail16.png"},
}
PAPER = {"PaperBomb": {"Tag": {"pd": "Exports/PaperBomb/Textures/Recolour/T_PaperBomb_PaperDetail.png",
                               "iw": "Exports/PaperBomb/Textures/Recolour/T_PaperBomb_InkWeights.png"}}}
LIGHTEST_MAX, LIGHTEST_MIN_EXPONENT = 0.6, 0.2
CHI_GRID = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
P_GRID = tuple(round(0.2 + 0.05 * i, 2) for i in range(27))
MIPS = 8
CHECK_HEX = ("FFFFFF", "F2E8D5", "FF0000", "808080", "B01010", "3050A0")


def log(msg):
    print(f"[constants] {msg}", flush=True)


def box(a):
    h, w = a.shape[:2]
    return a.reshape(h // 2, 2, w // 2, 2, *a.shape[2:]).mean(axis=(1, 3))


def hexlin(h):
    return tw.s2l(np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0)


def fabric_part(group, part, png, gen):
    t0 = time.time()
    d16, bits, _ = rc.png_read(rc.PROJECT / png)
    if bits != 16 or d16.shape[0] != d16.shape[1]:
        raise RuntimeError(f"{png}: expected a square 16-bit map")
    vals, cnts = np.unique(d16, return_counts=True)
    fill = int(vals[np.argmax(cnts)])
    cov = d16 != fill
    d = d16 / 65535.0
    g = gen["params"]
    n_old = g["Detail Bias"] + g["Detail Scale"] * d
    m = float(n_old[cov].mean())
    bias, scale = g["Detail Bias"] / m, g["Detail Scale"] / m
    colour = np.asarray(g["Colour"][:3], np.float64) * m
    n = bias + scale * d
    k = rc.fabric_constants(n[cov])
    ratio = k["highlight_ratio"]
    lightest = round(min(LIGHTEST_MAX, g["Albedo Ceiling"] / ratio ** LIGHTEST_MIN_EXPONENT), 3)
    p = {"Colour": [float(x) for x in colour] + [1.0], "Detail Bias": float(bias), "Detail Scale": float(scale),
         "Detail Mean": k["mean"], "Detail Highlight Ratio": ratio, "Detail Moments Low": k["moments_low"],
         "Detail Moments High": k["moments_high"], "Dark Detail Follow": g["Dark Detail Follow"],
         "Albedo Ceiling": g["Albedo Ceiling"], "Lightest Colour": lightest, "Detail Map Size": float(d.shape[0]),
         "Detail Mip Compensation 1-4": [0.0] * 4, "Detail Mip Compensation 5-8": [0.0] * 4,
         "Detail Mip Compensation Power": 1.0}
    # ---- mip compensation fit (no roll-off; strength 1)
    follow = p["Dark Detail Follow"]
    R = np.zeros((MIPS, len(CHI_GRID)))
    covk = [cov.astype(np.float64)]
    dks = [d]
    for _ in range(MIPS):
        covk.append(box(covk[-1]))
        dks.append(np.rint(box(dks[-1]) * 65535.0) / 65535.0)
    for j, chi in enumerate(CHI_GRID):
        clo = 1.0 + (chi - 1.0) * follow
        e = tw.cubic(p["Detail Moments Low"], clo) + tw.cubic(p["Detail Moments High"], chi)

        def s_of(dd):
            nn = np.maximum(bias + scale * dd, 1e-6)
            return np.power(nn, np.where(nn > 1.0, chi, clo)) * (p["Detail Mean"] / e)
        truth = s_of(d)
        for kk in range(1, MIPS + 1):
            truth = box(truth)
            msk = covk[kk] >= 0.5
            R[kk - 1, j] = float(s_of(dks[kk])[msk].mean() / truth[msk].mean())
    y = np.log(R)
    best = None
    for pw in P_GRID:
        x = (1.0 - np.asarray(CHI_GRID)) ** pw
        a = (y * x).sum(axis=1) / (x * x).sum()
        sse = float(((y - a[:, None] * x) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, pw, a)
    sse, pw, a = best
    inc = np.diff(np.concatenate([[0.0], a]))
    p["Detail Mip Compensation 1-4"] = [float(x) for x in inc[:4]]
    p["Detail Mip Compensation 5-8"] = [float(x) for x in inc[4:8]]
    p["Detail Mip Compensation Power"] = float(pw)
    resid = y - a[:, None] * ((1.0 - np.asarray(CHI_GRID)) ** pw)
    fit = {"power": pw, "A_by_mip": [round(float(x), 6) for x in a], "sse": sse,
           "max_abs_log_residual": float(np.abs(resid).max()),
           "uncorrected_ratio": {f"mip{kk + 1}": {str(c): round(float(R[kk, j]), 4) for j, c in enumerate(CHI_GRID)}
                                 for kk in range(MIPS)}}
    # ---- gates
    gates = {}
    # default: v2 twin at the default colour vs the v1 contract (Colour_old x n_old), every covered texel, mip 0
    g2, ce, info = tw.fabric_scalar(p, d, colour)
    v2 = ce[None, None, :] * g2[..., None]
    v1 = np.asarray(g["Colour"][:3])[None, None, :] * n_old[..., None]
    rel = float(np.abs(v2 - v1).max() / max(float(v1.max()), 1e-9))
    lv = int(np.abs(rc.q8_srgb(v2).astype(np.int32) - rc.q8_srgb(np.clip(v1, 0, 1)).astype(np.int32)).max())
    gates["default_equals_v1_contract"] = {"max_rel_diff": rel, "max_level_diff": lv, "info": info,
                                           "pass": bool(rel < 1e-9 and lv == 0)}
    guards = {"colour_above_floor": float(colour.max()) > tw.COLOUR_FLOOR, "colour_below_lightest": float(colour.max()) < lightest,
              "H_ge_1": info["H"] >= 1.0, "K_is_1": info["K"] == 1.0,
              "max_default_albedo_below_knee": float(v2.max()) <= tw.KNEE}
    gates["default_guards_inactive"] = {**guards, "pass": all(guards.values())}
    # default at every mip equals the v1 contract on the mip (K = 1, C = 1: linear, so exact)
    worst = 0.0
    dk = d
    for kk in range(1, MIPS + 1):
        dk = dks[kk]
        a2, _ = tw.fabric_albedo(p, dk, colour, lod=kk)
        a1 = np.asarray(g["Colour"][:3]) * (g["Detail Bias"] + g["Detail Scale"] * dk)[..., None]
        worst = max(worst, float(np.abs(a2 - a1).max()))
    gates["default_every_mip_equals_v1"] = {"max_abs": worst, "pass": bool(worst < 1e-9)}
    # corrected mean drift for real picks through the whole twin (roll-off included)
    drift = {}
    ok = True
    for hx in CHECK_HEX:
        col = hexlin(hx)
        gt, ce_, _ = tw.fabric_scalar(p, d, col, lod=0.0)
        truth = gt
        row = {}
        for kk in range(1, MIPS + 1):
            truth = box(truth)
            if kk not in (1, 2, 4, 6, 8):
                continue
            msk = covk[kk] >= 0.5
            gk, _, _ = tw.fabric_scalar(p, dks[kk], col, lod=float(kk))
            gu, _, _ = tw.fabric_scalar(p, dks[kk], col, lod=float(kk), mip_comp=False)
            r_c = float(gk[msk].mean() / truth[msk].mean())
            r_u = float(gu[msk].mean() / truth[msk].mean())
            row[f"mip{kk}"] = {"corrected": round(r_c, 4), "uncorrected": round(r_u, 4)}
            ok &= abs(r_c - 1.0) <= 0.02
        drift[hx] = row
    gates["mip_mean_drift_within_2pct"] = {"colours": drift, "pass": bool(ok)}
    passed = all(v["pass"] for v in gates.values())
    log(f"{group}/{part}: m_cov {m:.5f} ratio {ratio:.3f} lightest {lightest} P {pw} A {fit['A_by_mip']} "
        f"-> {'PASS' if passed else 'FAIL'} ({time.time() - t0:.0f} s)")
    return {"instance": gen["instance"], "master": "M_Fabric_Master", "detail_map": png,
            "detail_map_sha256": rc.sha256(rc.PROJECT / png), "params": p,
            "derivation": {"background_fill_d16": fill, "background_fraction": float(1 - cov.mean()),
                           "covered_mean_of_v1_n": m, "v1_params": g, "mip_fit": fit,
                           "lightest_rule": f"min({LIGHTEST_MAX}, Albedo Ceiling / Highlight Ratio^{LIGHTEST_MIN_EXPONENT})",
                           "p99_n": float(np.percentile(n[cov], 99)), "p50_n": float(np.percentile(n[cov], 50))},
            "gates": gates, "pass": passed}


def paper_part(group, part, files, gen):
    g = dict(gen["params"])
    pd8, _, _ = rc.png_read(rc.PROJECT / files["pd"])
    iw8, _, _ = rc.png_read(rc.PROJECT / files["iw"])
    w = tw.s2l(pd8[..., :3] / 255.0) * g["Paper Weight Scale"]
    wmax = w.max(axis=-1)
    p999 = float(np.percentile(wmax, 99.9))
    limit = round(g["Albedo Ceiling"] / p999, 5)
    red = np.asarray(g["Red Ink Colour"][:3], np.float64)
    sat = float((red.max() - red.min()) / red.max())
    p = dict(g)
    p["Paper Colour Limit"] = limit
    p["Red Ink Pool Default Saturation"] = sat
    maps = {"pd_rgb": tw.s2l(pd8[..., :3] / 255.0), "pd_a": pd8[..., 3:4] / 255.0, "iw": iw8 / 255.0,
            "ao": np.ones(pd8.shape[:2] + (1,))}
    v2, _, der = tw.paper_albedo(p, maps, ao_in_colour=0.0)
    # v1 (the build's first graph): no floor / limit / chroma fade
    paper = np.asarray(g["Paper Colour"][:3]); black = np.asarray(g["Black Ink Colour"][:3])
    bd = (black + (paper - black) * g["Black Ink Dry Paper Mix"]) * np.asarray(g["Black Ink Dry Gain"][:3])
    rd = tw.s2l(np.clip(g["Red Ink Dry Value Scale"] * tw.l2s(red), 0, 1))
    y = float(red @ tw.LUM)
    rp = (y + (red - y) * g["Red Ink Pool Saturation"]) * np.asarray(g["Red Ink Pool Gain"][:3])
    iw = maps["iw"]
    v1 = np.minimum(paper * maps["pd_rgb"] * g["Paper Weight Scale"] + black * iw[..., 0:1] + bd * iw[..., 1:2]
                    + red * iw[..., 2:3] + rd * iw[..., 3:4] + rp * maps["pd_a"], g["Albedo Ceiling"])
    diff = float(np.abs(v2 - v1).max())
    gates = {"default_equals_v1": {"max_abs": diff, "pass": bool(diff < 1e-9)},
             "paper_default_below_limit": {"max3": float(paper.max()), "limit": limit, "pass": bool(paper.max() < limit)}}
    passed = all(v["pass"] for v in gates.values())
    log(f"{group}/{part}: paper limit {limit} (p99.9 weight {p999:.5f}), red saturation {sat:.5f}, default diff {diff:.2e} "
        f"-> {'PASS' if passed else 'FAIL'}")
    return {"instance": gen["instance"], "master": "M_PaperInk_Master", "params": p,
            "derivation": {"paper_weight_p999_maxchannel": p999, "paper_weight_max": float(wmax.max()),
                           "derived_default": der},
            "gates": gates, "pass": passed}


def main(argv):
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    overall = True
    for group in list(FABRIC) + list(PAPER):
        if only and only != group:
            continue
        maps_json = rc.PROJECT / f"Exports/{group}/Textures/Recolour/recolour_maps.json"
        gen = json.loads(maps_json.read_text(encoding="utf-8"))
        doc = {"schema": "ninjapack.recolour_constants/1", "item": group, "generated": datetime.date.today().isoformat(),
               "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                             "twin": rc.rel(tw.__file__), "twin_sha256": rc.sha256(tw.__file__),
                             "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": blender},
               "source": {"recolour_maps": rc.rel(maps_json), "sha256": rc.sha256(maps_json)},
               "merge_rule": "np_spec.py: params here override recolour_maps.json params of the same instance",
               "parts": {}}
        for part, png in FABRIC.get(group, {}).items():
            doc["parts"][part] = fabric_part(group, part, png, gen["parts"][part])
        for part, files in PAPER.get(group, {}).items():
            doc["parts"][part] = paper_part(group, part, files, gen["parts"][part])
        doc["pass"] = all(v["pass"] for v in doc["parts"].values())
        overall &= doc["pass"]
        out = rc.PROJECT / f"Exports/{group}/Textures/Recolour/recolour_constants.json"
        rc.write_json(out, doc)
        rc.write_json(rc.WORK / "final" / "constants" / f"recolour_constants_{group}.json", doc)
        log(f"wrote {rc.rel(out)} pass={doc['pass']}")
    log(f"DONE overall={'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    code = main(argv)
    sys.stdout.flush()
    import os
    os._exit(code)
