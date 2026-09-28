"""Recolour STRESS TEST of the ninja pack's recolourable parts, on an independent float64 replica of the Unreal graphs.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/materials/recolour_tests/rst_twin_stress.py -- [--only <part>]

The replica is written from Scripts/unreal/materials/np_functions.py + np_masters.py (MF_TintDetail, MF_AlbedoRollOff,
MF_InkDerive, M_Fabric_Master, M_PaperInk_Master), NOT imported from the build's own twin (recolour_common.tint_detail),
so it is an independent check. Only file IO and colour-space helpers come from recolour_common. Parameter values are the
ones Unreal READ BACK from the built instances (WorkFiles/materials/build/dump_r3.json).

Test colours are what a buyer would type in Unreal's colour picker (sRGB hex; the picker stores the decoded linear
value). For every part x colour it measures, on the 8-bit sRGB base colour the GBuffer stores:
    colour match      mean albedo vs the picked colour (dE00), per-region for the paper bomb
    posterisation     plateau = share of texels on the single most common level (whole part and highlights only),
                      distinct levels, largest gap between used levels (p1..p99)
    detail            std of log-luminance vs the default (whole, highlights n>1, darks n<=1), Spearman vs default
    clipping          share of texels in the roll-off (max > 0.85) / near its limit (>= 0.94); paper: at 0.962
    mips              the maps' mip chain as Unreal builds it (2x2 box: G16 linear, sRGB decoded before averaging),
                      the graph evaluated ON the mip (what the GPU shows at distance) vs the correctly box-filtered
                      mip-0 result (what the surface really averages to): mean-colour drift and per-texel dE00
Writes WorkFiles/materials/recolour_tests/: swatch_<part>.png, rst_twin_results.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = PROJECT / "WorkFiles" / "materials" / "recolour_tests"
sys.path.insert(0, str(PROJECT / "Scripts" / "unreal" / "materials" / "maps"))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import recolour_common as rc  # noqa: E402  (IO + sRGB + CIEDE2000 only)
from rst_font import draw_text  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
DUMP = json.loads((PROJECT / "WorkFiles/materials/build/dump_r3.json").read_text(encoding="utf-8"))["instances"]
LUM = np.array([0.2126, 0.7152, 0.0722])
KNEE, LIMIT = 0.85, 0.95          # np_masters.build_fabric: MF_AlbedoRollOff Knee / Limit constants

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

# (key, label, sRGB hex).  The six the brief asks for, then three comparison picks.
COLOURS = [
    ("pure_white", "PURE WHITE", "FFFFFF"),
    ("pale_cream", "PALE CREAM", "F2E8D5"),
    ("sat_red", "SATURATED RED", "FF0000"),
    ("sat_blue", "SATURATED BLUE", "0000FF"),
    ("mid_grey", "MID GREY", "808080"),
    ("black", "BLACK", "000000"),
    ("offwhite_E7", "OFF-WHITE (0.8 LIN)", "E7E7E7"),
    ("deep_red", "DEEP RED", "B01010"),
    ("near_black", "NEAR BLACK", "1A1A1A"),
]
FIX_CMIN = 0.3        # proposed fix preview: floor the highlight exponent (never shipped)


def hex_lin(h):
    return rc.s2l(np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0)


def lin_hex(c):
    return "".join(f"{int(v):02X}" for v in rc.q8_srgb(np.asarray(c)[:3]))


def box(a, f=2):
    h, w = a.shape[:2]
    return a.reshape(h // f, f, w // f, f, *a.shape[2:]).mean(axis=(1, 3))


def rank(x):
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r


def de(a, b):
    return rc.de2000(np.asarray(a, np.float64), np.asarray(b, np.float64))


# ============================================================================ replica: fabric
def poly(m, c):
    return m[0] + c * (m[1] + c * (m[2] + c * m[3]))


def fabric_scalar(d, p, colour, cmin=None):
    """M_Fabric_Master BaseColor (Use Baked Colour Map off, Use Lettering with a blank mask = identity) as
    colour x g(texel): MF_TintDetail then MF_AlbedoRollOff (both scale all three channels by one factor)."""
    colour = np.asarray(colour, np.float64)
    n = np.maximum(p["Detail Bias"] + p["Detail Scale"] * d, 1e-6)
    cmax = max(float(colour.max()), 1e-4)
    strength, follow = p["Detail Strength"], p["Dark Detail Follow"]
    headroom = np.log2(p["Albedo Ceiling"] / cmax) / np.log2(p["Detail Highlight Ratio"])
    c_hi = min(strength, max(headroom, 0.0))
    if cmin is not None:
        c_hi = max(c_hi, cmin)
    c_lo = strength + (c_hi - strength) * follow
    expo = np.where(n > 1.0, c_hi, c_lo)                   # If(n, 1): A>B -> C_hi, A==B / A<B -> C_lo
    e = poly(p["Detail Moments Low"][:4], c_lo) + poly(p["Detail Moments High"][:4], c_hi)
    s = np.power(n, expo) * (p["Detail Mean"] / e)
    m = float(colour.max()) * s                            # max3 of the albedo
    w = max(LIMIT - KNEE, 1e-4)
    mm = KNEE + w * (1.0 - np.exp(-np.maximum(m - KNEE, 0.0) / w))
    g = s * (mm / np.maximum(m, KNEE))
    return g, n, {"H": float(headroom), "C_hi": float(c_hi), "C_lo": float(c_lo), "E": float(e)}


# ============================================================================ replica: paper
def ink_derive(p, paper, black, red):
    black_dry = (black + (paper - black) * p["Black Ink Dry Paper Mix"]) * np.asarray(p["Black Ink Dry Gain"][:3])
    red_dry = rc.s2l(np.clip(p["Red Ink Dry Value Scale"] * rc.l2s(np.clip(red, 0, 1)), 0, 1))
    y = float(red @ LUM)
    red_pool = (y + (red - y) * p["Red Ink Pool Saturation"]) * np.asarray(p["Red Ink Pool Gain"][:3])
    return black_dry, red_dry, red_pool


def paper_base(maps, p, paper, black, red, ao_in_colour):
    black_dry, red_dry, red_pool = ink_derive(p, paper, black, red)
    iw = maps["iw"]
    tot = (paper * maps["pd_rgb"] * p["Paper Weight Scale"] + black * iw[..., 0:1] + black_dry * iw[..., 1:2]
           + red * iw[..., 2:3] + red_dry * iw[..., 3:4] + red_pool * maps["pd_a"])
    unclipped = tot
    tot = np.minimum(tot, p["Albedo Ceiling"])
    if ao_in_colour:
        tot = tot * (1.0 + (maps["ao"] - 1.0) * ao_in_colour)
    return tot, unclipped, {"BlackDry": black_dry, "RedDry": red_dry, "RedPool": red_pool}


def paper_mips(pd8, iw8, ao8, k):
    """Unreal mip k of the paper maps: PaperDetail RGB sRGB (decoded, averaged, re-encoded to 8 bit), A linear;
    InkWeights linear 8 bit; ORM R linear 8 bit (block compression ignored)."""
    pd_rgb = rc.s2l(pd8[..., :3] / 255.0)
    pd_a = pd8[..., 3:4] / 255.0
    iw = iw8 / 255.0
    ao = ao8 / 255.0
    for _ in range(k):
        pd_rgb, pd_a, iw, ao = box(pd_rgb), box(pd_a), box(iw), box(ao)
        pd_rgb = rc.s2l(np.rint(rc.l2s(pd_rgb) * 255) / 255)
        pd_a, iw, ao = np.rint(pd_a * 255) / 255, np.rint(iw * 255) / 255, np.rint(ao * 255) / 255
    return {"pd_rgb": pd_rgb, "pd_a": pd_a, "iw": iw, "ao": ao}


# ============================================================================ metrics
def q8(lin):
    return rc.q8_srgb(lin).astype(np.int32)


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
    lin = rc.s2l(q / 255.0)
    return np.log(np.maximum(lin @ LUM, 1e-5))


def fabric_metrics(colour, g, n, q, base, cov):
    """q: (N, 3) stored levels of this colour; base: dict of the default's arrays (already coverage-filtered);
    cov: the texels a mesh actually uses (the map's constant background fill is excluded)."""
    g, n, q = g[cov], n[cov], q[cov]
    dom = int(np.argmax(colour)) if np.max(colour) > 0 else 1
    lvl = q[:, dom]
    hi = n > 1.0
    pl, used = plateau(lvl)
    pl_hi, used_hi = plateau(lvl[hi])
    gap, span = gaps(lvl)
    ll = logl(q)
    sub = slice(None, None, 7)
    out_mean = np.asarray(colour) * float(g.mean())
    m = float(np.max(colour)) * g
    r = {"mean_albedo": rc.rnd(out_mean, 5), "picked": rc.rnd(colour, 5),
         "dE00_mean_vs_picked": round(float(de(out_mean, colour)), 3),
         "plateau_frac": round(pl, 4), "plateau_frac_highlights": round(pl_hi, 4),
         "levels_used": used, "levels_used_highlights": used_hi, "max_gap_levels": gap, "p1_p99_span": span,
         "rolloff_frac": round(float((m > KNEE).mean()), 4), "near_limit_frac": round(float((m >= 0.94).mean()), 4),
         "logL_std_ratio": round(float(ll.std() / base["ll"].std()), 4) if ll.std() > 0 else 0.0,
         "logL_std_ratio_highlights": round(float(ll[hi].std() / base["ll"][hi].std()), 4),
         "logL_std_ratio_darks": round(float(ll[~hi].std() / base["ll"][~hi].std()), 4),
         "spearman_vs_default": (round(float(np.corrcoef(rank(ll[sub]), rank(base["ll"][sub]))[0, 1]), 4)
                                 if ll.std() > 0 else None)}
    return r


# ============================================================================ sheet drawing
BG = (24, 24, 26)
FG = (235, 235, 235)
WARN = (255, 120, 90)
OKC = (140, 220, 140)


def to_rgb8(lin):
    return q8(lin)


def paste(canvas, img, x, y, target=None):
    """img: (h, w, 3) int levels; nearest-upscale to ``target`` px (integer factor)."""
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
    """rows: [dict(label_lines, panels=[(img, target_px)], hist=img)]."""
    ov, crop, mip = 512, 480, 256
    widths = [360, ov, crop, mip, mip, 256]
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
    """top-left of the size x size window with the highest mean score."""
    h, w = score.shape
    best, at = -1e9, (0, 0)
    ii = np.cumsum(np.cumsum(np.pad(score, ((1, 0), (1, 0))), 0), 1)
    for yy in range(0, h - size, stride):
        for xx in range(0, w - size, stride):
            s = ii[yy + size, xx + size] - ii[yy, xx + size] - ii[yy + size, xx] + ii[yy, xx]
            if s > best:
                best, at = s, (yy, xx)
    return at


# ============================================================================ fabric part
def run_fabric(part, results):
    inst, det_png, bc_png = FABRIC[part]
    dump = DUMP[inst]
    p = {**dump["scalar"], **dump["vector"]}
    default_colour = np.asarray(p["Colour"][:3], np.float64)
    t0 = time.time()
    d16, _, _ = rc.png_read(PROJECT / det_png)
    d = d16.astype(np.float64) / 65535.0
    S = d.shape[0]
    # Unreal's G16 mip chain (2x2 box on the linear values, each level stored 16-bit)
    mips = [d]
    for _ in range(6):
        mips.append(np.rint(box(mips[-1]) * 65535.0) / 65535.0)
    bc = rc.load_levels8(PROJECT / bc_png)[..., :3].astype(np.int32)

    g0, n, info0 = fabric_scalar(d, p, default_colour)
    q_def = q8(default_colour[None, :] * g0.reshape(-1, 1))
    vals, cnts = np.unique(d16, return_counts=True)
    fill = int(vals[np.argmax(cnts)])
    cov2 = d16 != fill                      # the constant background fill outside the UV islands is not on the mesh
    cov = cov2.ravel()
    base = {"ll": logl(q_def[cov])}
    nflat = n.ravel()
    covk = [cov2.astype(np.float64)]
    for _ in range(6):
        covk.append(box(covk[-1]))
    res = {"instance": inst, "params_from": "dump_r3.json (Unreal read-back)", "size": S,
           "default_vs_shipped_BC_levels": int(np.abs(q_def.reshape(S, S, 3) - bc).max()),
           "default_vs_shipped_BC_p999": float(np.percentile(np.abs(q_def.reshape(S, S, 3) - bc).max(-1), 99.9)),
           "background_fill": {"d16": fill, "n": round(float(p["Detail Bias"] + p["Detail Scale"] * fill / 65535.0), 4),
                               "fraction": round(float(1 - cov.mean()), 4), "note": "excluded from every statistic"},
           "colours": {}}
    # crop: the most varied window (std of n)
    cs = 160
    var = np.kron(box(n * n, 8) - box(n, 8) ** 2, np.ones((8, 8)))
    cy, cx = pick_crop(var, cs, stride=max(32, S // 64))
    res["crop"] = {"row": cy, "col": cx, "size": cs}
    rows = []
    tests = [("default", "DEFAULT (SHIPPED)", None, None)] + [(k, lab, hx, None) for k, lab, hx in COLOURS]
    tests += [("fix_pure_white", "PURE WHITE - PROPOSED FIX", "FFFFFF", FIX_CMIN),
              ("fix_sat_red", "SAT RED - PROPOSED FIX", "FF0000", FIX_CMIN)]
    for key, label, hx, cmin in tests:
        colour = default_colour if hx is None else hex_lin(hx)
        g, _, info = fabric_scalar(d, p, colour, cmin)
        lin = colour[None, :] * g.reshape(-1, 1)
        q = q8(lin)
        r = fabric_metrics(colour, g.ravel(), nflat, q, base, cov)
        r.update({k: round(v, 5) for k, v in info.items()})
        r["hex"] = hx or lin_hex(default_colour)
        r["proposed_fix_not_shipped"] = cmin is not None
        # mips: graph on the mip vs the box-filtered mip-0 result
        mip_rep = {}
        lin_img = colour[None, None, :] * g[..., None]
        truth = lin_img
        for k in range(1, 7):
            truth = box(truth)
            gk, _, _ = fabric_scalar(mips[k], p, colour, cmin)
            gpu = colour[None, None, :] * gk[..., None]
            if k in (2, 4, 6):
                full = covk[k] >= 0.5                         # mip texels mostly made of used texels
                if not full.any():
                    full = covk[k] >= 0.0
                a, b = gpu[full], truth[full]
                step = max(1, len(a) // 60000)
                dd = de(a[::step], b[::step])
                ga, tb = a.mean(0), b.mean(0)
                mip_rep[f"mip{k}"] = {"mean_colour_gpu": rc.rnd(ga, 5), "mean_colour_true": rc.rnd(tb, 5),
                                      "texels": int(full.sum()),
                                      "dE00_mean_colour": round(float(de(ga, tb)), 3),
                                      "luminance_ratio_gpu_over_true": round(float((ga @ LUM) / max(tb @ LUM, 1e-9)), 4),
                                      "dE00_texel_mean": round(float(dd.mean()), 3), "dE00_texel_p95": round(float(np.percentile(dd, 95)), 3)}
            if k == 4:
                gpu4, true4 = gpu, truth
        r["mips"] = mip_rep
        res["colours"][key] = r
        # sheet row
        img = lin_img
        f = max(1, S // 512)
        ovw = to_rgb8(box(img, f) if f > 1 else img)
        crop = q.reshape(S, S, 3)[cy:cy + cs, cx:cx + cs]
        lines = [label, f"#{r['hex']}  LIN {colour[0]:.3f} {colour[1]:.3f} {colour[2]:.3f}",
                 f"MEAN OUT #{lin_hex(r['mean_albedo'])}  DE00 {r['dE00_mean_vs_picked']:.2f}",
                 f"H {r['H']:.2f}  C_HI {r['C_hi']:.3f}  C_LO {r['C_lo']:.3f}",
                 (f"PLATEAU {100 * r['plateau_frac']:.1f}%  HI {100 * r['plateau_frac_highlights']:.1f}%",
                  WARN if r["plateau_frac_highlights"] > 0.2 else FG),
                 f"LEVELS {r['levels_used']}  GAP {r['max_gap_levels']}",
                 (f"DETAIL LOGL {100 * r['logL_std_ratio']:.0f}%  HI {100 * r['logL_std_ratio_highlights']:.0f}%",
                  WARN if r["logL_std_ratio_highlights"] < 0.25 else FG),
                 f"DARKS {100 * r['logL_std_ratio_darks']:.0f}%  SPEARMAN {r['spearman_vs_default']}",
                 (f"ROLLOFF {100 * r['rolloff_frac']:.1f}%  AT LIMIT {100 * r['near_limit_frac']:.1f}%",
                  WARN if r["near_limit_frac"] > 0.01 else FG),
                 (f"MIP4 DRIFT DE00 {mip_rep['mip4']['dE00_mean_colour']:.2f}  L X{mip_rep['mip4']['luminance_ratio_gpu_over_true']:.3f}",
                  WARN if mip_rep["mip4"]["dE00_mean_colour"] > 1.0 else FG),
                 f"MIP6 DRIFT DE00 {mip_rep['mip6']['dE00_mean_colour']:.2f}"]
        if cmin is not None:
            lines.append(("NOT SHIPPED: C_HI FLOOR 0.3", (255, 210, 90)))
        rows.append({"label_lines": lines,
                     "panels": [(ovw, 512), (crop, 480), (to_rgb8(gpu4), 256), (to_rgb8(true4), 256)],
                     "hist": histogram(q[:, int(np.argmax(colour)) if colour.max() > 0 else 1], colour),
                     "hist_lines": ["HISTOGRAM OF DOMINANT CHANNEL", "(8-BIT SRGB LEVELS, LOG COUNT)"]})
        print(f"[rst] {part} {key}: plateau {r['plateau_frac']:.3f}/{r['plateau_frac_highlights']:.3f} "
              f"hi-detail {r['logL_std_ratio_highlights']:.3f} dE {r['dE00_mean_vs_picked']:.2f} "
              f"mip4 {mip_rep['mip4']['dE00_mean_colour']:.2f}", flush=True)
    make_sheet(HERE / f"swatch_{part}.png", f"RECOLOUR STRESS: {part.upper()} ({inst.upper()})",
               "FLOAT64 REPLICA OF M_FABRIC_MASTER ON THE SHIPPED MAPS, PARAMETERS READ BACK FROM UNREAL. 8-BIT SRGB BASE COLOUR.",
               rows, ["WHOLE MAP (BOX-FILTERED TO 512)", f"1:1 TEXELS, 160X160 CROP AT ({cy},{cx}) X3",
                      "MIP 4 AS THE GPU SHADES IT", "MIP 4 TRUE (BOX OF MIP 0)"])
    res["seconds"] = round(time.time() - t0, 1)
    results[part] = res


# ============================================================================ paper parts
def run_paper(results):
    dump = DUMP[PAPER["inst"]]
    p = {**dump["scalar"], **dump["vector"]}
    pd8, _, _ = rc.png_read(PROJECT / PAPER["pd"])
    iw8, _, _ = rc.png_read(PROJECT / PAPER["iw"])
    ao8 = rc.load_levels8(PROJECT / PAPER["orm"])[..., 0:1].astype(np.float64)
    bc = rc.load_levels8(PROJECT / PAPER["bc"])[..., :3].astype(np.int32)
    maps0 = paper_mips(pd8, iw8, ao8, 0)
    maps4 = paper_mips(pd8, iw8, ao8, 4)
    maps2 = paper_mips(pd8, iw8, ao8, 2)
    S = pd8.shape[0]
    iw = maps0["iw"]
    regions = {
        "paper": (iw.sum(-1) < 0.004) & (maps0["pd_a"][..., 0] < 0.004),
        "black_wet_core": iw[..., 0] >= 0.95, "black_dry": iw[..., 1] >= 0.5,
        "red_wet_core": iw[..., 2] >= 0.95, "red_dry": iw[..., 3] >= 0.5, "red_pool": maps0["pd_a"][..., 0] >= 0.5,
        "ink_edges": ((iw > 0.1) & (iw < 0.9)).any(-1) | ((maps0["pd_a"][..., 0] > 0.1) & (maps0["pd_a"][..., 0] < 0.9))}
    default = {k: np.asarray(p[k][:3], np.float64) for k in ("Paper Colour", "Black Ink Colour", "Red Ink Colour")}
    ao_def = float(p["Baked AO In Colour"])
    d_off, _, _ = paper_base(maps0, p, default["Paper Colour"], default["Black Ink Colour"], default["Red Ink Colour"], 0.0)
    d_on, _, _ = paper_base(maps0, p, default["Paper Colour"], default["Black Ink Colour"], default["Red Ink Colour"], ao_def)
    qd_off = q8(d_off)
    base_ll = {rk: logl(qd_off[m].reshape(-1, 3)) for rk, m in regions.items()}
    out = {"instance": PAPER["inst"], "params_from": "dump_r3.json (Unreal read-back)",
           "region_texels": {k: int(v.sum()) for k, v in regions.items()},
           "default_AOoff_vs_shipped_BC_levels": int(np.abs(qd_off - bc).max()),
           "default_AOoff_vs_BC_p999": float(np.percentile(np.abs(qd_off - bc).max(-1), 99.9)),
           "parts": {}}
    main_region = {"Paper Colour": "paper", "Black Ink Colour": "black_wet_core", "Red Ink Colour": "red_wet_core"}
    for part, pname in PAPER_PARTS.items():
        if ONLY and ONLY not in part:
            continue
        reg = main_region[pname]
        # crop: paper -> a window with little ink but texture; inks -> a window whose ink weight is ~40 %
        if pname == "Paper Colour":
            score = (regions["paper"].astype(np.float64) * 0.6 + regions["ink_edges"] * 0.4)
        elif pname == "Black Ink Colour":
            score = -np.abs((iw[..., 0] + iw[..., 1]) - 0.45)
        else:
            score = -np.abs((iw[..., 2] + iw[..., 3] + maps0["pd_a"][..., 0]) - 0.45)
        cs = 160
        cy, cx = pick_crop(score, cs, stride=32)
        res = {"parameter": pname, "judged_region": reg, "crop": {"row": cy, "col": cx, "size": cs}, "colours": {}}
        rows = []
        for key, label, hx in [("default", "DEFAULT (SHIPPED)", None)] + COLOURS:
            cols = dict(default)
            if hx is not None:
                cols[pname] = hex_lin(hx)
            picked = cols[pname]
            lin_off, unclipped, der = paper_base(maps0, p, cols["Paper Colour"], cols["Black Ink Colour"], cols["Red Ink Colour"], 0.0)
            lin_on, _, _ = paper_base(maps0, p, cols["Paper Colour"], cols["Black Ink Colour"], cols["Red Ink Colour"], ao_def)
            q_off = q8(lin_off)
            q_on = q8(lin_on)
            m = regions[reg]
            reg_mean = lin_off[m].mean(0)
            dom = int(np.argmax(picked)) if picked.max() > 0 else 1
            lvl = q_off[m][:, dom]
            pl, used = plateau(lvl)
            gap, span = gaps(lvl)
            ll = logl(q_off[m].reshape(-1, 3))
            e_m = regions["ink_edges"]
            egap, _ = gaps(q_off[e_m][:, dom])
            clip_any = (unclipped >= p["Albedo Ceiling"]).any(-1)
            r = {"hex": hx or lin_hex(picked), "picked": rc.rnd(picked, 5),
                 "region_mean": rc.rnd(reg_mean, 5), "dE00_region_mean_vs_picked": round(float(de(reg_mean, picked)), 3),
                 "region_plateau_frac": round(pl, 4), "region_levels_used": used, "region_max_gap": gap,
                 "ink_edge_max_gap": egap,
                 "region_logL_std_ratio": round(float(ll.std() / base_ll[reg].std()), 4) if ll.std() > 0 else 0.0,
                 "clip_frac_all": round(float(clip_any.mean()), 5),
                 "clip_frac_region": round(float(clip_any[m].mean()), 5),
                 "derived": {k: rc.rnd(v, 5) for k, v in der.items()},
                 "derived_hex": {k: lin_hex(np.clip(v, 0, 1)) for k, v in der.items()}}
            # derived-colour casts: the chroma the derived ink colours carry when the picked ink is neutral
            lab = rc._lab(np.clip(np.stack([picked, der["RedPool"], der["BlackDry"], der["RedDry"]]), 0, 1))
            r["chroma_Cab"] = {"picked": round(float(np.hypot(*lab[0, 1:])), 2),
                               "RedPool": round(float(np.hypot(*lab[1, 1:])), 2),
                               "BlackDry": round(float(np.hypot(*lab[2, 1:])), 2),
                               "RedDry": round(float(np.hypot(*lab[3, 1:])), 2)}
            r["hue_ab_deg"] = {"picked": round(float(np.degrees(np.arctan2(lab[0, 2], lab[0, 1]))), 1),
                               "RedPool": round(float(np.degrees(np.arctan2(lab[1, 2], lab[1, 1]))), 1)}
            # other regions' mean colours (to see what the pick does to pools / dry strokes)
            r["region_means"] = {rk: lin_hex(lin_off[rm].mean(0)) for rk, rm in regions.items() if rm.any()}
            # mips (AO on, as shipped)
            mip_rep = {}
            for k, mk in ((2, maps2), (4, maps4)):
                gpu, _, _ = paper_base(mk, p, cols["Paper Colour"], cols["Black Ink Colour"], cols["Red Ink Colour"], ao_def)
                truth = lin_on
                for _ in range(k):
                    truth = box(truth)
                dd = de(gpu.reshape(-1, 3)[::3], truth.reshape(-1, 3)[::3])
                mip_rep[f"mip{k}"] = {"dE00_mean_colour": round(float(de(gpu.reshape(-1, 3).mean(0), truth.reshape(-1, 3).mean(0))), 3),
                                      "dE00_texel_mean": round(float(dd.mean()), 3),
                                      "dE00_texel_p99": round(float(np.percentile(dd, 99)), 3)}
                if k == 4:
                    gpu4, true4 = gpu, truth
            r["mips"] = mip_rep
            res["colours"][key] = r
            lines = [label, f"{pname.upper()} #{r['hex']}",
                     f"LIN {picked[0]:.3f} {picked[1]:.3f} {picked[2]:.3f}",
                     (f"{reg.upper()} MEAN #{lin_hex(reg_mean)} DE00 {r['dE00_region_mean_vs_picked']:.2f}",
                      WARN if r["dE00_region_mean_vs_picked"] > 3 else FG),
                     (f"PLATEAU {100 * pl:.1f}%  LEVELS {used}  GAP {gap}", WARN if pl > 0.2 else FG),
                     f"EDGE GAP {egap}  DETAIL {100 * r['region_logL_std_ratio']:.0f}%",
                     (f"CLIP 0.962: ALL {100 * r['clip_frac_all']:.1f}% REGION {100 * r['clip_frac_region']:.1f}%",
                      WARN if r["clip_frac_region"] > 0.05 else FG),
                     f"POOL #{r['derived_hex']['RedPool']} C {r['chroma_Cab']['RedPool']:.1f}",
                     f"DRY BLACK #{r['derived_hex']['BlackDry']}  DRY RED #{r['derived_hex']['RedDry']}",
                     f"MIP4 DRIFT DE00 {mip_rep['mip4']['dE00_mean_colour']:.2f} TEXEL {mip_rep['mip4']['dE00_texel_mean']:.2f}"]
            rows.append({"label_lines": lines,
                         "panels": [(to_rgb8(box(lin_on, 4)), 512), (q_on[cy:cy + cs, cx:cx + cs], 480),
                                    (to_rgb8(gpu4), 256), (to_rgb8(true4), 256)],
                         "hist": histogram(q_off[m][:, dom], picked if picked.max() > 0 else np.array([0.5, 0.5, 0.5])),
                         "hist_lines": [f"HISTOGRAM, {reg.upper()} TEXELS", "DOMINANT CHANNEL, LOG COUNT"]})
            print(f"[rst] {part} {key}: dE {r['dE00_region_mean_vs_picked']:.2f} plateau {pl:.3f} clip {r['clip_frac_region']:.3f} "
                  f"pool {r['derived_hex']['RedPool']} C{r['chroma_Cab']['RedPool']}", flush=True)
        make_sheet(HERE / f"swatch_{part}.png", f"RECOLOUR STRESS: {part.upper()} ({pname.upper()})",
                   "FLOAT64 REPLICA OF M_PAPERINK_MASTER (AO IN COLOUR ON, AS SHIPPED). OTHER COLOURS AT DEFAULT. METRICS AO-OFF.",
                   rows, ["WHOLE MAP (BOX-FILTERED TO 512)", f"1:1 TEXELS, 160X160 CROP AT ({cy},{cx}) X3",
                          "MIP 4 AS THE GPU SHADES IT", "MIP 4 TRUE (BOX OF MIP 0)"])
        out["parts"][part] = res
    results["PaperBomb"] = out


def main():
    t0 = time.time()
    results = {"method": __doc__.strip(), "colours": {k: {"label": lab, "hex": hx, "linear": rc.rnd(hex_lin(hx), 5)}
                                                        for k, lab, hx in COLOURS},
               "proposed_fix_preview": f"C_hi = max(C_hi, {FIX_CMIN}) in MF_TintDetail (not shipped)"}
    for part in FABRIC:
        if ONLY and ONLY not in part:
            continue
        run_fabric(part, results)
    if not ONLY or "Paper" in ONLY:
        run_paper(results)
    results["seconds"] = round(time.time() - t0, 1)
    name = "rst_twin_results.json" if not ONLY else f"rst_twin_results_{ONLY}.json"
    rc.write_json(HERE / name, results)
    print("RST_DONE", results["seconds"], flush=True)


main()
