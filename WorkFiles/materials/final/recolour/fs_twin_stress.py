"""FINAL recolour stress test (v2 graphs) on the float64 twin (Scripts/unreal/materials/maps/np_twin.py).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/materials/final/recolour/fs_twin_stress.py -- [--dump <dump json>] [--only <part>]

Same colours and the same metrics as the recolour verifier's rst_twin_stress.py (WorkFiles/materials/recolour_tests/),
so the before / after numbers compare directly. Parameters are the ones Unreal READ BACK from the built buyer-facing
instances (default: WorkFiles/materials/build/dump_f1.json). Metrics on the 8-bit sRGB base colour the GBuffer stores,
over COVERED texels (the constant background fill outside the UV islands is excluded):
    plateau       share of texels on the single most common level of the dominant channel (whole part, highlights)
    levels / gap  distinct levels used; largest gap between used levels inside p1..p99
    detail        std of log-luminance vs the default (whole, highlights n > 1, darks n <= 1); Spearman vs default
    colour        mean albedo vs the pick (dE00) and vs the effective colour after the guards (floor / lightest cap)
    limit         share of texels at the roll-off limit (>= 0.94)
    mips          the graph ON Unreal's mip chain at lod k (with the v2 mip compensation) vs the box-filtered mip-0
                  result: luminance ratio of the means and per-texel dE00
Gates (fabric): plateau(highlights) <= 0.20 and plateau(part) <= 0.15 (not gated when the EFFECTIVE colour is near
black, max channel <= 0.0105: the 8-bit sRGB GBuffer has only ~50-100 levels for the whole part there; the shipped
default wrap itself has a 16.7 % highlight plateau); gap <= 3; whole-part detail >= 0.25; clip (any texel >= 0.949,
the survey's V3 clip gate) <= 0.1 %, the share in the roll-off (>= 0.85) and near its limit (>= 0.94) reported; mip
2 / 4 / 6 luminance ratio within 3 % and mean-colour dE00 <= 1; the default equals the shipped BC.
Paper: paper-region plateau <= 0.20 (not gated for an effective near-black paper: the grain is a few % and the 8-bit
GBuffer has ~10 levels there), paper texels at the art's 0.962 ceiling <= 1 % (the shipped default: 0.03 %), pooled
red of a neutral red-ink pick neutral (C*ab <= 3).
Writes final/recolour/swatch_<part>.png and fs_twin_results.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = PROJECT / "WorkFiles/materials/final/recolour"
sys.path.insert(0, str(PROJECT / "Scripts/unreal/materials/maps"))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402  (IO, CIEDE2000)
from fs_font import draw_text  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
DUMP_PATH = Path(ARGS[ARGS.index("--dump") + 1]) if "--dump" in ARGS else PROJECT / "WorkFiles/materials/build/dump_f1.json"
DUMP = json.loads(DUMP_PATH.read_text(encoding="utf-8"))["instances"]
LUM = tw.LUM

FABRIC = {
    "Kunai_Wrap": ("MI_Kunai_Plain_Wrap", "Exports/Shuriken/Textures/Recolour/T_Kunai_Wrap_Detail16.png",
                   "Exports/Shuriken/Textures/T_Kunai_Wrap_BC.png"),
    "SmokeBomb_Cloth": ("MI_SmokeBomb_Cloth", "Exports/SmokeBomb/Textures/Recolour/T_SmokeBomb_Detail16.png",
                        "Exports/SmokeBomb/Textures/T_SmokeBomb_BC.png"),
    "BlackHat_Straw": ("MI_BlackHat_Straw", "Exports/BlackHat/Textures/Recolour/T_BlackHat_Straw_Detail16.png",
                       "Exports/BlackHat/Textures/T_BlackHat_Straw_BC.png"),
    "BlackHat_Cloth": ("MI_BlackHat_Cloth", "Exports/BlackHat/Textures/Recolour/T_BlackHat_Cloth_Detail16.png",
                       "Exports/BlackHat/Textures/T_BlackHat_Cloth_BC.png"),
}
PAPER = {"inst": "MI_PaperBomb_Tag", "pd": "Exports/PaperBomb/Textures/Recolour/T_PaperBomb_PaperDetail.png",
         "iw": "Exports/PaperBomb/Textures/Recolour/T_PaperBomb_InkWeights.png",
         "orm": "Exports/PaperBomb/Textures/T_PaperBomb_ORM.png", "bc": "Exports/PaperBomb/Textures/T_PaperBomb_BC.png"}
PAPER_PARTS = {"PaperBomb_Paper": "Paper Colour", "PaperBomb_BlackInk": "Black Ink Colour",
               "PaperBomb_RedInk": "Red Ink Colour"}
COLOURS = [("pure_white", "PURE WHITE", "FFFFFF"), ("pale_cream", "PALE CREAM", "F2E8D5"),
           ("sat_red", "SATURATED RED", "FF0000"), ("sat_blue", "SATURATED BLUE", "0000FF"),
           ("mid_grey", "MID GREY", "808080"), ("black", "BLACK", "000000"),
           ("offwhite_E7", "OFF-WHITE (0.8 LIN)", "E7E7E7"), ("deep_red", "DEEP RED", "B01010"),
           ("near_black", "NEAR BLACK", "1A1A1A")]


def params(inst):
    d = DUMP[inst]
    return {**d["scalar"], **d["vector"], **{k: v for k, v in d["static_switch"].items()}}


def hex_lin(h):
    return tw.s2l(np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0)


def lin_hex(c):
    return "".join(f"{int(v):02X}" for v in rc.q8_srgb(np.clip(np.asarray(c)[:3], 0, 1)))


def q8(lin):
    return rc.q8_srgb(lin).astype(np.int32)


def box(a, f=2):
    h, w = a.shape[:2]
    return a.reshape(h // f, f, w // f, f, *a.shape[2:]).mean(axis=(1, 3))


def de(a, b):
    return rc.de2000(np.asarray(a, np.float64), np.asarray(b, np.float64))


def rank(x):
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r


def plateau(levels):
    v = levels.ravel()
    if v.size == 0:
        return 0.0, 0
    cnt = np.bincount(v, minlength=256)
    return float(cnt.max() / v.size), int((cnt > 0).sum())


def gaps(levels):
    v = levels.ravel()
    lo, hi = np.percentile(v, 1), np.percentile(v, 99)
    occ = np.unique(v[(v >= lo) & (v <= hi)])
    return int(np.diff(occ).max()) if len(occ) > 1 else 0, float(hi - lo)


def logl(q):
    return np.log(np.maximum(tw.s2l(q / 255.0) @ LUM, 1e-5))


def chroma(lin):
    lab = rc._lab(np.clip(np.asarray(lin, np.float64), 0, 1))
    return float(np.hypot(lab[..., 1], lab[..., 2]))


# ---------------------------------------------------------------------------------------------- sheet drawing
BG, FG, WARN = (24, 24, 26), (235, 235, 235), (255, 120, 90)


def paste(canvas, img, x, y, target=None):
    if target is not None and img.shape[0] < target:
        f = target // img.shape[0]
        img = np.kron(img, np.ones((f, f, 1), np.int32)) if f > 1 else img
    h, w = img.shape[:2]
    canvas[y:y + h, x:x + w] = img
    return w


def histogram(levels, colour, h=120):
    img = np.zeros((h, 256, 3), np.int32)
    img[:] = (40, 40, 44)
    cnt = np.bincount(levels.ravel(), minlength=256).astype(np.float64)
    if cnt.max() > 0:
        v = np.log1p(cnt) / np.log1p(cnt.max())
        bar = np.clip(np.array(colour) * 255, 90, 255).astype(np.int32)
        for x in range(256):
            t = int(round(v[x] * (h - 1)))
            if t:
                img[h - t:, x] = bar
    return img


def text_block(canvas, x, y, lines, scale=2):
    for ln in lines:
        colr = FG
        if isinstance(ln, tuple):
            ln, colr = ln
        draw_text(canvas, x, y, ln, colr, scale)
        y += 9 * scale
    return y


def make_sheet(path, title, subtitle, rows, panel_titles):
    ov = 512
    widths = [380, ov, 480, 256, 256, 256]
    row_h = ov + 30
    W = sum(widths) + 12 * len(widths) + 20
    H = 90 + row_h * len(rows)
    canvas = np.zeros((H, W, 3), np.int32)
    canvas[:] = BG
    draw_text(canvas, 16, 14, title, FG, 3)
    draw_text(canvas, 16, 50, subtitle, (180, 180, 180), 2)
    xs = [16]
    for wd in widths[:-1]:
        xs.append(xs[-1] + wd + 12)
    for i, t in enumerate(panel_titles):
        draw_text(canvas, xs[i + 1], 72, t, (170, 200, 255), 1)
    y = 90
    for r in rows:
        text_block(canvas, xs[0], y + 4, r["label_lines"])
        for i, (img, tgt) in enumerate(r["panels"]):
            paste(canvas, img, xs[i + 1], y, tgt)
        paste(canvas, r["hist"], xs[5], y)
        text_block(canvas, xs[5], y + 130, r.get("hist_lines", []), 1)
        canvas[y + row_h - 6:y + row_h - 5, :] = (60, 60, 64)
        y += row_h
    rgba = np.concatenate([np.clip(canvas, 0, 255), np.full((H, W, 1), 255, np.int32)], axis=-1)
    rc.png_write(path, rgba, 8)


def pick_crop(score, size, stride=32):
    h, w = score.shape
    best, at = -1e18, (0, 0)
    ii = np.cumsum(np.cumsum(np.pad(score, ((1, 0), (1, 0))), 0), 1)
    for yy in range(0, h - size, stride):
        for xx in range(0, w - size, stride):
            s = ii[yy + size, xx + size] - ii[yy, xx + size] - ii[yy + size, xx] + ii[yy, xx]
            if s > best:
                best, at = s, (yy, xx)
    return at


# ---------------------------------------------------------------------------------------------- fabric
def run_fabric(part, results):
    inst, det_png, bc_png = FABRIC[part]
    p = params(inst)
    t0 = time.time()
    d16, _, _ = rc.png_read(PROJECT / det_png)
    d = d16.astype(np.float64) / 65535.0
    S = d.shape[0]
    mips = [d]
    for _ in range(6):
        mips.append(np.rint(box(mips[-1]) * 65535.0) / 65535.0)
    vals, cnts = np.unique(d16, return_counts=True)
    fill = int(vals[np.argmax(cnts)])
    cov2 = d16 != fill
    cov = cov2.ravel()
    covk = [cov2.astype(np.float64)]
    for _ in range(6):
        covk.append(box(covk[-1]))
    n = np.maximum(p["Detail Bias"] + p["Detail Scale"] * d, 1e-6)
    hi = n.ravel()[cov] > 1.0
    default_colour = np.asarray(p["Colour"][:3])
    g0, ce0, _ = tw.fabric_scalar(p, d, default_colour)
    q_def = q8(ce0 * g0[..., None]).reshape(-1, 3)
    bc = rc.load_levels8(PROJECT / bc_png)[..., :3].astype(np.int32).reshape(-1, 3)
    base_ll = logl(q_def[cov])
    res = {"instance": inst, "params_from": str(DUMP_PATH.name), "size": S,
           "default_vs_shipped_BC_levels": int(np.abs(q_def - bc).max()),
           "default_vs_shipped_BC_levels_covered": int(np.abs(q_def - bc)[cov].max()),
           "background_fill": {"d16": fill, "fraction": round(float(1 - cov.mean()), 4)},
           "lightest_colour": p["Lightest Colour"], "colours": {}}
    var = np.kron(box(n * n, 8) - box(n, 8) ** 2, np.ones((8, 8)))
    cs = 160
    cy, cx = pick_crop(var, cs, stride=max(32, S // 64))
    rows = []
    for key, label, hx in [("default", "DEFAULT (SHIPPED)", None)] + COLOURS:
        colour = default_colour if hx is None else hex_lin(hx)
        g, ce, info = tw.fabric_scalar(p, d, colour)
        lin_img = ce[None, None, :] * g[..., None]
        q = q8(lin_img).reshape(-1, 3)[cov]
        dom = int(np.argmax(ce))
        lvl = q[:, dom]
        pl, used = plateau(lvl)
        pl_hi, _ = plateau(lvl[hi])
        gap, span = gaps(lvl)
        ll = logl(q)
        mean = (ce[None, :] * g.ravel()[cov][:, None]).mean(0)
        m = float(ce.max()) * g.ravel()[cov]
        sub = slice(None, None, 7)
        r = {"hex": hx or lin_hex(default_colour), "picked": rc.rnd(colour, 5), "effective_colour": rc.rnd(ce, 5),
             "effective_hex": lin_hex(ce), "mean_albedo": rc.rnd(mean, 5), "mean_hex": lin_hex(mean),
             "dE00_mean_vs_picked": round(float(de(mean, colour)), 3),
             "dE00_mean_vs_effective": round(float(de(mean, ce * p["Detail Mean"])), 3),
             "plateau_frac": round(pl, 4), "plateau_frac_highlights": round(pl_hi, 4), "levels_used": used,
             "max_gap_levels": gap, "p1_p99_span": span,
             "near_limit_frac": round(float((m >= 0.94).mean()), 5),
             "rolloff_frac": round(float((m >= 0.85).mean()), 5), "clip_frac_0949": round(float((m >= 0.949).mean()), 6),
             "logL_std_ratio": round(float(ll.std() / base_ll.std()), 4) if ll.std() > 0 else 0.0,
             "logL_std_ratio_highlights": round(float(ll[hi].std() / base_ll[hi].std()), 4),
             "logL_std_ratio_darks": round(float(ll[~hi].std() / base_ll[~hi].std()), 4),
             "spearman_vs_default": round(float(np.corrcoef(rank(ll[sub]), rank(base_ll[sub]))[0, 1]), 4)
             if ll.std() > 0 else None,
             **{k: round(v, 5) for k, v in info.items() if isinstance(v, float)}}
        mip_rep = {}
        truth = lin_img
        for k in range(1, 7):
            truth = box(truth)
            if k not in (2, 4, 6):
                continue
            gk, cek, _ = tw.fabric_scalar(p, mips[k], colour, lod=float(k))
            gpu = cek[None, None, :] * gk[..., None]
            full = covk[k] >= 0.5
            a, b = gpu[full], truth[full]
            step = max(1, len(a) // 60000)
            dd = de(a[::step], b[::step])
            ga, tb = a.mean(0), b.mean(0)
            mip_rep[f"mip{k}"] = {"luminance_ratio_gpu_over_true": round(float((ga @ LUM) / max(tb @ LUM, 1e-9)), 4),
                                  "dE00_mean_colour": round(float(de(ga, tb)), 3),
                                  "dE00_texel_mean": round(float(dd.mean()), 3),
                                  "dE00_texel_p95": round(float(np.percentile(dd, 95)), 3)}
            if k == 4:
                gpu4, true4 = gpu, truth
        r["mips"] = mip_rep
        near_black = float(ce.max()) <= 0.0105
        gates = {"plateau_highlights_le_0.20": r["plateau_frac_highlights"] <= 0.20 or near_black,
                 "plateau_part_le_0.15": r["plateau_frac"] <= 0.15 or near_black,
                 "gap_le_3": r["max_gap_levels"] <= 3,
                 "detail_whole_ge_0.25": r["logL_std_ratio"] >= 0.25,
                 "clip_0949_le_0.1pct": r["clip_frac_0949"] <= 0.001,
                 "mips_lum_within_3pct": all(abs(v["luminance_ratio_gpu_over_true"] - 1) <= 0.03 for v in mip_rep.values()),
                 "mips_mean_dE00_le_1": all(v["dE00_mean_colour"] <= 1.0 for v in mip_rep.values())}
        r["gates"] = gates
        r["pass"] = all(gates.values())
        res["colours"][key] = r
        f = max(1, S // 512)
        crop = q8(lin_img)[cy:cy + cs, cx:cx + cs]
        rows.append({"label_lines": [
            label, f"PICK #{r['hex']}  EFFECTIVE #{r['effective_hex']}",
            f"MEAN OUT #{r['mean_hex']}  DE00 VS PICK {r['dE00_mean_vs_picked']:.2f}",
            f"C_HI {r['C_hi']:.3f}  C_LO {r['C_lo']:.3f}",
            (f"PLATEAU {100 * pl:.1f}%  HI {100 * pl_hi:.1f}%", WARN if pl_hi > 0.2 else FG),
            f"LEVELS {used}  GAP {gap}",
            (f"DETAIL {100 * r['logL_std_ratio']:.0f}%  HI {100 * r['logL_std_ratio_highlights']:.0f}%  "
             f"LO {100 * r['logL_std_ratio_darks']:.0f}%", WARN if r["logL_std_ratio"] < 0.25 else FG),
            f"SPEARMAN {r['spearman_vs_default']}  ROLL-OFF {100 * r['rolloff_frac']:.1f}%  CLIP {100 * r['clip_frac_0949']:.2f}%",
            (f"MIP4 L X{mip_rep['mip4']['luminance_ratio_gpu_over_true']:.3f}  DE00 {mip_rep['mip4']['dE00_mean_colour']:.2f}",
             WARN if not gates["mips_lum_within_3pct"] else FG),
            (f"GATES {'PASS' if r['pass'] else 'FAIL: ' + ','.join(k for k, v in gates.items() if not v)[:40]}",
             FG if r["pass"] else WARN)],
            "panels": [(q8(box(lin_img, f)) if f > 1 else q8(lin_img), 512), (crop, 480), (q8(gpu4), 256),
                       (q8(true4), 256)],
            "hist": histogram(lvl, ce), "hist_lines": ["DOMINANT CHANNEL, COVERED TEXELS", "(8-BIT SRGB LEVELS, LOG COUNT)"]})
        print(f"[fs] {part} {key}: eff #{r['effective_hex']} pl {pl:.3f}/{pl_hi:.3f} det {r['logL_std_ratio']:.2f}/"
              f"{r['logL_std_ratio_highlights']:.2f} gap {gap} mip4 L{mip_rep['mip4']['luminance_ratio_gpu_over_true']} "
              f"{'PASS' if r['pass'] else 'FAIL ' + str([k for k, v in gates.items() if not v])}", flush=True)
    res["pass"] = all(v["pass"] for v in res["colours"].values())
    make_sheet(HERE / f"swatch_{part}.png", f"FINAL RECOLOUR STRESS (V2): {part.upper()} ({inst.upper()})",
               "FLOAT64 TWIN OF M_FABRIC_MASTER V2 ON THE SHIPPED MAPS, PARAMETERS READ BACK FROM UNREAL. 8-BIT SRGB BASE COLOUR.",
               rows, ["WHOLE MAP (BOX-FILTERED TO 512)", f"1:1 TEXELS, 160X160 CROP AT ({cy},{cx}) X3",
                      "MIP 4 AS THE GPU SHADES IT (V2)", "MIP 4 TRUE (BOX OF MIP 0)"])
    res["seconds"] = round(time.time() - t0, 1)
    results[part] = res


# ---------------------------------------------------------------------------------------------- paper
def paper_maps(pd8, iw8, ao8, k):
    pd_rgb, pd_a, iw, ao = tw.s2l(pd8[..., :3] / 255.0), pd8[..., 3:4] / 255.0, iw8 / 255.0, ao8 / 255.0
    for _ in range(k):
        pd_rgb, pd_a, iw, ao = box(pd_rgb), box(pd_a), box(iw), box(ao)
        pd_rgb = tw.s2l(np.rint(tw.l2s(pd_rgb) * 255) / 255)
        pd_a, iw, ao = np.rint(pd_a * 255) / 255, np.rint(iw * 255) / 255, np.rint(ao * 255) / 255
    return {"pd_rgb": pd_rgb, "pd_a": pd_a, "iw": iw, "ao": ao}


def run_paper(results):
    p = params(PAPER["inst"])
    pd8, _, _ = rc.png_read(PROJECT / PAPER["pd"])
    iw8, _, _ = rc.png_read(PROJECT / PAPER["iw"])
    ao8 = rc.load_levels8(PROJECT / PAPER["orm"])[..., 0:1].astype(np.float64)
    bc = rc.load_levels8(PROJECT / PAPER["bc"])[..., :3].astype(np.int32)
    maps0, maps4 = paper_maps(pd8, iw8, ao8, 0), paper_maps(pd8, iw8, ao8, 4)
    iw = maps0["iw"]
    regions = {
        "paper": (iw.sum(-1) < 0.004) & (maps0["pd_a"][..., 0] < 0.004),
        "black_wet_core": iw[..., 0] >= 0.95, "black_dry": iw[..., 1] >= 0.5,
        "red_wet_core": iw[..., 2] >= 0.95, "red_dry": iw[..., 3] >= 0.5, "red_pool": maps0["pd_a"][..., 0] >= 0.5}
    default = {k: np.asarray(p[k][:3], np.float64) for k in ("Paper Colour", "Black Ink Colour", "Red Ink Colour")}
    ao_def = float(p["Baked AO In Colour"])
    d_off, _, _ = tw.paper_albedo(p, maps0, ao_in_colour=0.0)
    qd_off = q8(d_off)
    out = {"instance": PAPER["inst"], "region_texels": {k: int(v.sum()) for k, v in regions.items()},
           "default_AOoff_vs_shipped_BC_levels": int(np.abs(qd_off - bc).max()),
           "default_AOoff_vs_BC_p999": float(np.percentile(np.abs(qd_off - bc).max(-1), 99.9)), "parts": {}}
    base_ll = {rk: logl(qd_off[m].reshape(-1, 3)) for rk, m in regions.items()}
    main_region = {"Paper Colour": "paper", "Black Ink Colour": "black_wet_core", "Red Ink Colour": "red_wet_core"}
    for part, pname in PAPER_PARTS.items():
        if ONLY and ONLY not in part:
            continue
        reg = main_region[pname]
        if pname == "Paper Colour":
            score = regions["paper"].astype(np.float64)
        elif pname == "Black Ink Colour":
            score = -np.abs((iw[..., 0] + iw[..., 1]) - 0.45)
        else:
            score = -np.abs((iw[..., 2] + iw[..., 3] + maps0["pd_a"][..., 0]) - 0.45)
        cy, cx = pick_crop(score, 160, stride=32)
        res = {"parameter": pname, "judged_region": reg, "colours": {}}
        rows = []
        for key, label, hx in [("default", "DEFAULT (SHIPPED)", None)] + COLOURS:
            cols = dict(default)
            if hx is not None:
                cols[pname] = hex_lin(hx)
            picked = cols[pname]
            lin_off, unclipped, der = tw.paper_albedo(p, maps0, cols["Paper Colour"], cols["Black Ink Colour"],
                                                      cols["Red Ink Colour"], ao_in_colour=0.0)
            lin_on, _, _ = tw.paper_albedo(p, maps0, cols["Paper Colour"], cols["Black Ink Colour"],
                                           cols["Red Ink Colour"], ao_in_colour=ao_def)
            q_off, q_on = q8(lin_off), q8(lin_on)
            m = regions[reg]
            reg_mean = lin_off[m].mean(0)
            dom = int(np.argmax(picked)) if picked.max() > 0 else 1
            pl, used = plateau(q_off[m][:, dom])
            gap, _ = gaps(q_off[m][:, dom])
            ll = logl(q_off[m].reshape(-1, 3))
            clip = (unclipped >= p["Albedo Ceiling"]).any(-1)
            gpu4, _, _ = tw.paper_albedo(p, maps4, cols["Paper Colour"], cols["Black Ink Colour"], cols["Red Ink Colour"],
                                         ao_in_colour=ao_def)
            true4 = box(lin_on, 16)
            r = {"hex": hx or lin_hex(picked), "picked": rc.rnd(picked, 5), "region_mean_hex": lin_hex(reg_mean),
                 "dE00_region_mean_vs_picked": round(float(de(reg_mean, picked)), 3),
                 "region_plateau_frac": round(pl, 4), "region_levels_used": used, "region_max_gap": gap,
                 "region_logL_std_ratio": round(float(ll.std() / base_ll[reg].std()), 4) if ll.std() > 0 else 0.0,
                 "clip_frac_region": round(float(clip[m].mean()), 5), "clip_frac_all": round(float(clip.mean()), 5),
                 "derived_hex": {k: lin_hex(v) for k, v in der.items()},
                 "red_pool_chroma_Cab": round(chroma(der["RedPool"]), 2), "picked_chroma_Cab": round(chroma(picked), 2),
                 "region_means": {rk: lin_hex(lin_off[rm].mean(0)) for rk, rm in regions.items() if rm.any()},
                 "mip4_dE00_mean_colour": round(float(de(gpu4.reshape(-1, 3).mean(0), true4.reshape(-1, 3).mean(0))), 3)}
            dark_paper = pname == "Paper Colour" and float(np.max(der["PaperColour_e"])) <= 0.0105
            gates = {"region_plateau_le_0.20": pl <= 0.20 or dark_paper or pname != "Paper Colour",
                     "clip_le_1pct_region": r["clip_frac_region"] <= 0.01 or pname != "Paper Colour",
                     "neutral_red_pools_neutral": (not (pname == "Red Ink Colour" and r["picked_chroma_Cab"] < 1))
                     or r["red_pool_chroma_Cab"] <= 3.0}
            r["gates"], r["pass"] = gates, all(gates.values())
            res["colours"][key] = r
            rows.append({"label_lines": [label, f"{pname.upper()} #{r['hex']}",
                                         f"{reg.upper()} MEAN #{r['region_mean_hex']} DE00 {r['dE00_region_mean_vs_picked']:.2f}",
                                         (f"PLATEAU {100 * pl:.1f}%  LEVELS {used}  GAP {gap}", WARN if pl > 0.2 else FG),
                                         f"DETAIL {100 * r['region_logL_std_ratio']:.0f}%",
                                         (f"AT 0.962 CEILING: {100 * r['clip_frac_region']:.2f}%", WARN if r["clip_frac_region"] > 0.01 else FG),
                                         f"POOL #{r['derived_hex']['RedPool']} C {r['red_pool_chroma_Cab']:.1f}",
                                         f"MIP4 DE00 {r['mip4_dE00_mean_colour']:.2f}",
                                         (f"GATES {'PASS' if r['pass'] else 'FAIL'}", FG if r["pass"] else WARN)],
                         "panels": [(q8(box(lin_on, 4)), 512), (q_on[cy:cy + 160, cx:cx + 160], 480), (q8(gpu4), 256),
                                    (q8(true4), 256)],
                         "hist": histogram(q_off[m][:, dom], picked if picked.max() > 0 else np.array([0.5, 0.5, 0.5])),
                         "hist_lines": [f"HISTOGRAM, {reg.upper()} TEXELS", "DOMINANT CHANNEL, LOG COUNT"]})
            print(f"[fs] {part} {key}: plateau {pl:.3f} clip {r['clip_frac_region']:.4f} pool #{r['derived_hex']['RedPool']} "
                  f"C{r['red_pool_chroma_Cab']} {'PASS' if r['pass'] else 'FAIL'}", flush=True)
        res["pass"] = all(v["pass"] for v in res["colours"].values())
        make_sheet(HERE / f"swatch_{part}.png", f"FINAL RECOLOUR STRESS (V2): {part.upper()} ({pname.upper()})",
                   "FLOAT64 TWIN OF M_PAPERINK_MASTER V2 (AO IN COLOUR ON, AS SHIPPED). OTHER COLOURS AT DEFAULT. METRICS AO OFF.",
                   rows, ["WHOLE MAP (BOX-FILTERED TO 512)", f"1:1 TEXELS, 160X160 CROP AT ({cy},{cx}) X3",
                          "MIP 4 AS THE GPU SHADES IT", "MIP 4 TRUE (BOX OF MIP 0)"])
        out["parts"][part] = res
    results["PaperBomb"] = out


def main():
    t0 = time.time()
    results = {"method": __doc__.strip(), "dump": str(DUMP_PATH),
               "colours": {k: {"label": lab, "hex": hx, "linear": rc.rnd(hex_lin(hx), 5)} for k, lab, hx in COLOURS}}
    for part in FABRIC:
        if ONLY and ONLY not in part:
            continue
        run_fabric(part, results)
    if not ONLY or "Paper" in ONLY:
        run_paper(results)
    results["seconds"] = round(time.time() - t0, 1)
    name = "fs_twin_results.json" if not ONLY else f"fs_twin_results_{ONLY}.json"
    rc.write_json(HERE / name, results)
    print("FS_DONE", results["seconds"], flush=True)


main()
