"""T_PaperBomb_PaperDetail + T_PaperBomb_InkWeights: an exact linear LAYER DECOMPOSITION of the paper bomb's base colour,
so a buyer can recolour the paper, the black ink and the red ink separately (MATERIAL_PLAN.md 5.3, D5), plus
Exports/PaperBomb/Textures/Recolour/recolour_maps.json.

The shipped T_PaperBomb_M.B is max(red, black): one channel for two inks and no paper detail, so it cannot recolour
cleanly (the pooled vermilion fails a luminance tint at dE76 p99 17.4).  This generator re-runs the art exactly as the
build does - ``bake.draw_art(spec, plan, seed=20260919, supersample=2)`` - with the face's one compositing function,
``paperbomb_tracedart.composite_traced``, wrapped IN MEMORY (nothing on disk changes) to capture the 2x layers it
consumed, and proves the re-run is the shipped art (``bake.transfer`` of it re-quantises to the shipped T_PaperBomb_BC
byte for byte).

THE TRACED FACE (2026-09-26 exact-match pass).  The front is traced from the owner's reference and composited in the
reference's stored space, red behind black (``composite_traced``):

    stored = Paper_s (1 - k - r) + RedLocal_s r + Black_s k,    r = a_r (1 - k),    BC = clip(sRGBdecode(stored))

There is no wet / dry / pooled split any more (a dry passage is crisp bristle marks of the one ink; the pool is black
over red), so W_bd = W_rd = W_rp = 0 and only two ink weights carry anything.  Per texel, at 2x:

    Black Ink Colour = sRGBdecode(Black_s)                  (the traced art's own black: g_b = 1)
    Red Ink Colour   = median linear colour of the red cores (r >= 0.99, k < 0.01) of the traced art
    g_r  = clip(min_c RedLocal_c / Red_c, 0, 1)             (a locally darker red is never over-claimed)
    h    = min(1, min_c BC_c / (k Black_c + r g_r Red_c))   (black over red, or a thin mix, never over-claims either)
    W_bw = k h        W_rw = r g_r h        W_bd = W_rd = W_rp = 0

so the ink terms never exceed the texel's own colour and the paper residual below is non-negative at 2x by
construction (whatever the stored-space mix leaves - the local red's variation, the mix's curvature - is paper weight).

box-filtered 2:1 exactly as ``_downsample`` does (``paperbomb_art._down``), edge-extended like ``bake._fit_raster`` and
composed into the atlas by ``atlas.compose`` (the back island and the rim carry no ink: their show-through ghost and
edge gradient belong to the paper).  The inks are quantised FIRST (8-bit linear, as stored); then the paper weight is
the per-channel RESIDUAL against the shipped BC:

    W_P,c = (sRGBdecode(BC8)_c - sum_k W_k,stored Colour_k,c) / PaperColour_c

so paper grain, foxing, the edge band, the dirt, the clip, the ghost and the rim are all paper, and the recomposition
at the default colours reproduces the shipped BC to the paper weight's own storage precision.

Encodings (measured, see the report's ``encoding_choice``):
    T_PaperBomb_PaperDetail  RGBA8.  RGB = W_P / PaperWeightScale, sRGB-ENCODED (import sRGB ON: the GPU decodes it and
                             Unreal builds its mips in linear light); A = W_rp, LINEAR (alpha is never sRGB-decoded).
                             Linear 8-bit RGB would put the paper weight's quantum (0.0035 linear of paper colour) under
                             the ink cores, where it is 7 stored levels.
    T_PaperBomb_InkWeights   RGBA8 LINEAR (import sRGB OFF): R W_bw, G W_bd, B W_rw, A W_rd.
Both must import UNCOMPRESSED (BGRA8): block compression of weight maps breaks the default equality.

READ-ONLY on every shipped file and module; writes only NEW files under Exports/PaperBomb/Textures/Recolour/ (the props
importer's non-recursive glob never scans it) and a gate report under WorkFiles/materials/maps/.  Never saves a .blend.
Re-pointing after the paper bomb's exact-match pass: rerun this script, then build_pack_materials.py.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/unreal/materials/maps/make_paperbomb_recolour_maps.py
"""
from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import recolour_common as rc  # noqa: E402

sys.path.insert(0, str(rc.PROJECT / "Scripts"))
sys.path.insert(0, str(rc.PROJECT / "Scripts" / "props"))

VERSION = "1.0.0"
SEED = 20260919
SUPERSAMPLE = 2
#: every file the face depends on: hashed before and after the run (G-P4: unchanged while it ran)
ART_MODULES = ("props_lib/paperbomb_art.py", "props_lib/paperbomb_tracedart.py", "props_lib/paperbomb_trace.py",
               "props_lib/paperbomb_finefit.py", "props_lib/paperbomb_traced.json", "props_lib/trace.py",
               "props_lib/bake.py", "props_lib/atlas.py", "props_lib/spec.py", "props_lib/paper_material.py",
               "build_paper_bomb.py")
TEX = rc.EXPORTS / "PaperBomb" / "Textures"
OUT_DIR = TEX / "Recolour"
OUT_PAPER = OUT_DIR / "T_PaperBomb_PaperDetail.png"
OUT_INK = OUT_DIR / "T_PaperBomb_InkWeights.png"
RED_DRY_VALUE_SCALE = 0.82          # Palette.red_dry: "red_wet scaled by 0.82 in STORED space"
RED_POOL_SATURATION = 0.30
INK_NAMES = ("W_bw", "W_bd", "W_rw", "W_rd", "W_rp")


def log(msg):
    print(f"[paperbomb_recolour] {msg}", flush=True)


def lum(c):
    return float(np.dot(np.asarray(c, np.float64), rc.LUM))


def derive(paper, black, red, k: dict) -> dict:
    """MF_InkDerive (material_spec.json material_functions): dry / pool colours from the three buyer colours."""
    paper, black, red = (np.asarray(v, np.float64) for v in (paper, black, red))
    black_dry = (black + (paper - black) * k["Black Ink Dry Paper Mix"]) * np.asarray(k["Black Ink Dry Gain"])
    red_dry = rc.s2l(k["Red Ink Dry Value Scale"] * rc.l2s(red))
    y = lum(red)
    red_pool = (y + (red - y) * k["Red Ink Pool Saturation"]) * np.asarray(k["Red Ink Pool Gain"])
    return {"BlackDry": black_dry, "RedDry": red_dry, "RedPool": red_pool}


def fit(a: np.ndarray, want_w: int, want_h: int) -> np.ndarray:
    """bake._fit_raster's far-edge extension, for a raster the art object does not own."""
    a = a[:want_h, :want_w]
    if a.shape[0] < want_h:
        a = np.concatenate([a, np.repeat(a[-1:], want_h - a.shape[0], axis=0)], axis=0)
    if a.shape[1] < want_w:
        a = np.concatenate([a, np.repeat(a[:, -1:], want_w - a.shape[1], axis=1)], axis=1)
    return np.ascontiguousarray(a)


def main() -> int:
    import bpy
    from props_lib import atlas as A
    from props_lib import bake as PB
    from props_lib import paperbomb_art as art
    from props_lib import paperbomb_tracedart as TA
    from props_lib.spec import PAPER_BOMB

    t_start = time.time()
    # --- G-P4: the art modules, hashed now and again at the end (unchanged while this ran)
    gp4 = {m: {"before": rc.sha256(rc.PROJECT / "Scripts" / "props" / m)} for m in ART_MODULES}
    shipped_sha = {s: rc.sha256(TEX / f"T_PaperBomb_{s}.png") for s in ("BC", "ORM", "N", "M")}

    spec = PAPER_BOMB
    plan = A.plan_for(spec)
    captured = []
    original = TA.composite_traced

    def capture(paper_st, red_rgb, blk_rgb, arb, ak, cfg_):
        rgb, ar = original(paper_st, red_rgb, blk_rgb, arb, ak, cfg_)
        captured.append({"paper_st": paper_st.copy(), "red_rgb": red_rgb.copy(), "blk_rgb": np.array(blk_rgb).copy(),
                         "arb": arb.copy(), "ak": ak.copy(), "rgb": rgb.copy(), "ar": ar.copy(), "cfg": cfg_})
        return rgb, ar

    TA.composite_traced = capture                    # IN MEMORY only; restored below
    try:
        t0 = time.time()
        cfg, front, back, provenance = PB.draw_art(spec, plan, seed=SEED, supersample=SUPERSAMPLE)
        log(f"art drawn in {time.time() - t0:.0f} s, raster {front.width} x {front.height}")
    finally:
        TA.composite_traced = original
    if len(captured) != 1:
        raise RuntimeError(f"composite_traced ran {len(captured)} times; expected once (the front)")
    cap = captured[0]
    pal = art.palette_for(cfg)

    # --- G-P0: the re-run IS the shipped art (the transfer re-quantises to the shipped BC byte for byte)
    channels = PB.transfer(plan, front, back, spec, cfg)
    regen = np.clip(np.rint(PB.linear_to_srgb(channels["base"]) * 255.0), 0, 255).astype(np.int16)
    shipped = rc.load_levels8(TEX / "T_PaperBomb_BC.png")[..., :3]
    gp0 = rc.level_diff_stats(regen, shipped)
    gp0["pass"] = bool(gp0["max"] == 0)
    log(f"G-P0 re-run vs shipped BC: max {gp0['max']} (texels>0 {gp0['texels_diff_gt0']})")

    # --- the capture is complete: the composite re-run from the captured layers is the captured colour, exactly
    re_rgb, _ = original(cap["paper_st"], cap["red_rgb"], cap["blk_rgb"], cap["arb"], cap["ak"], cap["cfg"])
    decomposition_2x_max_abs = float(np.abs(re_rgb.astype(np.float64) - cap["rgb"]).max())
    del re_rgb
    # --- the 2x ink weights (see the module docstring)
    k2 = cap["ak"].astype(np.float64)
    r2 = cap["ar"].astype(np.float64)
    rgb2 = cap["rgb"].astype(np.float64)
    red_loc = rc.s2l(np.clip(cap["red_rgb"].astype(np.float64), 0.0, 1.0))
    black = rc.s2l(np.clip(cap["blk_rgb"].reshape(3).astype(np.float64), 0.0, 1.0))
    red_core = (r2 >= 0.99) & (k2 < 0.01)
    red = np.median(red_loc[red_core], axis=0)
    g_r = np.clip((red_loc / red[None, None, :]).min(axis=-1), 0.0, 1.0)
    ink2 = k2[..., None] * black[None, None, :] + (r2 * g_r)[..., None] * red[None, None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        hh = np.where(ink2 > 0, rgb2 / np.maximum(ink2, 1e-30), np.inf).min(axis=-1)
    h = np.minimum(1.0, hh)
    zero2 = np.zeros_like(k2)
    w2 = np.stack([k2 * h, zero2, r2 * g_r * h, zero2, zero2], axis=-1)
    ink_cols2 = np.stack([black, black, red, red, red])            # dry / pool weights are zero
    resid2 = rgb2 - w2 @ ink_cols2
    weights_2x = {"red_ink_colour_linear": rc.rnd(red, 7), "red_core_texels_2x": int(red_core.sum()),
                  "black_ink_colour_linear": rc.rnd(black, 7),
                  "texels_g_r_below_1_in_red": int(((g_r < 1.0) & (r2 > 0.5)).sum()),
                  "texels_h_below_1": int((h < 1.0).sum()),
                  "texels_h_below_0.9": int((h < 0.9).sum()),
                  "residual_min_linear_2x": float(resid2.min()),
                  "pass": bool(resid2.min() >= -1e-6)}
    log(f"2x weights: red ink {weights_2x['red_ink_colour_linear']}, black {weights_2x['black_ink_colour_linear']}; "
        f"h<1 on {weights_2x['texels_h_below_1']} texels; residual min {weights_2x['residual_min_linear_2x']:.2e}")
    del k2, r2, rgb2, red_loc, g_r, ink2, hh, h, resid2
    # 2:1 box (paperbomb_art._down), then the far-edge fit, then the atlas
    rw, rh = plan.raster
    w1 = fit(art._down(w2.astype(np.float32), SUPERSAMPLE).astype(np.float64), rw, rh)
    card1 = fit(np.asarray(front.card_mask, np.float64), rw, rh)
    zeros = np.zeros_like(w1)
    wa = A.compose(plan, w1.astype(np.float32), zeros.astype(np.float32), 0.0).astype(np.float64)
    card_a = A.compose(plan, card1.astype(np.float32), np.zeros_like(card1, np.float32), 0.0)
    del w2, zeros

    # --- default colours and the derivation constants (recomputed from the palette the art used)
    bc_lin = rc.s2l(shipped / 255.0)
    front_region = np.zeros((plan.size, plan.size), bool)
    front_region[:rh, :rw] = True
    paper_only = front_region & (card_a > 0.999) & (wa.sum(axis=-1) < 1e-7)
    paper_colour = bc_lin[paper_only].mean(axis=0)
    t_mix = (lum(pal.black_dry) - lum(black)) / (lum(paper_colour) - lum(black))
    lerp_b = black + (paper_colour - black) * t_mix
    y_red = lum(red)
    consts = {
        "Black Ink Dry Paper Mix": float(t_mix),
        "Black Ink Dry Gain": [float(v) for v in np.asarray(pal.black_dry) / lerp_b],
        "Red Ink Dry Value Scale": RED_DRY_VALUE_SCALE,
        "Red Ink Pool Saturation": RED_POOL_SATURATION,
        "Red Ink Pool Gain": [float(v) for v in np.asarray(pal.red_pool) / (y_red + (red - y_red) * RED_POOL_SATURATION)],
    }
    der = derive(paper_colour, black, red, consts)
    ink_cols = np.stack([black, der["BlackDry"], red, der["RedDry"], der["RedPool"]])
    # G-P2: the traced face has no dry / pooled layer (their weights are zero, checked on the stored map below); the
    # master's MF_InkDerive colours are still derived from the three buyer colours so its graph is unchanged, and
    # they must be real colours
    gp2 = {}
    for name in ("BlackDry", "RedDry", "RedPool"):
        got = der[name]
        gp2[name] = {"derived": rc.rnd(got, 7), "inside_0_1": bool((got >= 0).all() and (got <= 1).all())}

    # --- quantise the inks (as stored), then the paper weight as the per-channel residual.
    # ROUND, EXCEPT WHERE ROUNDING UP OVER-CLAIMS: one stored level of red weight is 0.0023 linear in R, several
    # stored BC levels in a near-black texel (black over the red's edge), so a red weight rounded up from under half a
    # level made the ink alone brighter than the texel and the clipped paper residual could not take it back (G-P1
    # missed by up to 4 levels there).  Where the rounded inks exceed the texel's BC by more than 1e-6 in any channel,
    # the red weight is floored, then the black weight
    ink_levels = rc.q8_linear(wa)                                     # (S, S, 5): InkWeights RGBA + PaperDetail A
    floored = {}
    for ch in (2, 0):
        over = ((bc_lin - (ink_levels / 255.0) @ ink_cols) < -1e-6).any(axis=-1)
        fl = np.floor(np.clip(wa[..., ch], 0.0, 1.0) * 255.0).astype(np.int16)
        change = over & (fl < ink_levels[..., ch])
        ink_levels[..., ch] = np.where(change, fl, ink_levels[..., ch])
        floored[INK_NAMES[ch]] = int(change.sum())
    wq = ink_levels / 255.0
    residual = bc_lin - wq @ ink_cols
    wp = residual / paper_colour[None, None, :]
    negative = wp < 0
    clip_report = {"texel_channels_negative": int(negative.sum()),
                   "ink_levels_floored_not_rounded": floored,
                   "most_negative_linear": float(residual.min()),
                   "note": "clipped to 0; rounding of an ink weight above a texel's own BC (bounded by half a stored "
                           "level of that ink)"}
    wp = np.maximum(wp, 0.0)
    scale = float(wp.max() * 1.001)

    def recompose(pd_rgb_levels, pd_encoding, wq5):
        if pd_encoding == "srgb":
            wpd = rc.s2l(pd_rgb_levels / 255.0) * scale
        else:
            wpd = pd_rgb_levels / 255.0 * scale
        return np.minimum(paper_colour * wpd + wq5 @ ink_cols, pal.ceiling_linear)

    enc = {}
    for name, levels in (("srgb", rc.q8_srgb(wp / scale)), ("linear", rc.q8_linear(wp / scale))):
        out = recompose(levels, name, wq)
        s = rc.level_diff_stats(rc.q8_srgb(out), shipped)
        de = rc.de2000(out.reshape(-1, 3), bc_lin.reshape(-1, 3))
        enc[name] = {**s, "dE00_mean": round(float(de.mean()), 4), "dE00_p99": round(float(np.percentile(de, 99)), 4),
                     "dE00_max": round(float(de.max()), 4)}
    pd_rgb = rc.q8_srgb(wp / scale)
    out0 = recompose(pd_rgb, "srgb", wq)
    gp1 = {**enc["srgb"], "encoding": "PaperDetail RGB sRGB-encoded (chosen)",
           "pass": bool(enc["srgb"]["max"] <= 1 and enc["srgb"]["dE00_mean"] <= 0.3)}

    wq8 = ink_levels
    gp2["dry_and_pool_weights_zero"] = bool(int(wq8[..., 1].max()) == 0 and int(wq8[..., 3].max()) == 0
                                            and int(wq8[..., 4].max()) == 0)
    gp2["pass"] = bool(gp2["dry_and_pool_weights_zero"] and all(v["inside_0_1"] for v in gp2.values()
                                                                   if isinstance(v, dict)))
    # --- write the two maps
    paper_map = np.concatenate([pd_rgb, ink_levels[..., 4:5]], axis=-1).astype(np.int32)
    ink_map = ink_levels[..., :4].astype(np.int32)
    rc.png_write(OUT_PAPER, paper_map, 8)
    rc.png_write(OUT_INK, ink_map, 8)
    readback = {}
    for path, arr in ((OUT_PAPER, paper_map), (OUT_INK, ink_map)):
        back_own, bits, ctype = rc.png_read(path)
        back_bpy = rc.load_levels8(path)
        readback[path.name] = {"own_decoder_equal": bool(np.array_equal(back_own, arr)),
                               "blender_decoder_equal": bool(np.array_equal(back_bpy, arr)), "bits": bits,
                               "colour_type": ctype, "png_chunks": rc.png_chunks(path)}
    readback["pass"] = all(v["own_decoder_equal"] and v["blender_decoder_equal"] and v["colour_type"] == 6
                           for k, v in readback.items() if isinstance(v, dict))

    # --- every mip, as Unreal builds them (SimpleAverage in linear light; each level stored in its own format)
    pd_lin_rgb = rc.s2l(paper_map[..., :3] / 255.0)
    pd_a = paper_map[..., 3] / 255.0
    ink_lin = ink_map / 255.0
    mips = []
    for f in rc.mip_factors(plan.size, plan.size):
        bcm = rc.q8_srgb(rc.block_mean(bc_lin, f))
        pdm = rc.q8_srgb(rc.block_mean(pd_lin_rgb, f))
        w5 = np.concatenate([rc.q8_linear(rc.block_mean(ink_lin, f)),
                             rc.q8_linear(rc.block_mean(pd_a, f))[..., None]], axis=-1) / 255.0
        om = recompose(pdm, "srgb", w5)
        mips.append({"mip": len(mips), "size": list(bcm.shape[:2]), **rc.level_diff_stats(rc.q8_srgb(om), bcm)})
    mip_max = max(m["max"] for m in mips)

    # --- light / saturated recolours, one layer at a time (the others at their defaults)
    region = {"Paper": (wp.mean(axis=-1) * paper_colour.mean()) > 0.5 * bc_lin.mean(axis=-1),
              "Black Ink": wa[..., 0] + wa[..., 1] >= 0.5, "Red Ink": wa[..., 2] + wa[..., 3] + wa[..., 4] >= 0.5}
    wp_stored = rc.s2l(pd_rgb / 255.0) * scale
    stress = {}
    gp3 = {}
    for layer in ("Paper", "Black Ink", "Red Ink"):
        stress[layer] = {}
        for cname, col in {**rc.STRESS, **rc.REPORT_ONLY}.items():
            p_c, b_c, r_c = paper_colour, black, red
            if layer == "Paper":
                p_c = np.array(col)
            elif layer == "Black Ink":
                b_c = np.array(col)
            else:
                r_c = np.array(col)
            dd = derive(p_c, b_c, r_c, consts)
            cols = np.stack([b_c, dd["BlackDry"], r_c, dd["RedDry"], dd["RedPool"]])
            inside = all(bool((v >= 0).all() and (v <= 1).all()) for v in dd.values())
            gp3[f"{layer}/{cname}"] = inside
            o = np.minimum(np.asarray(p_c)[None, None, :] * wp_stored + wq @ cols, pal.ceiling_linear)
            m = region[layer]
            s8 = rc.q8_srgb(o[m])
            dom = int(np.argmax(col))
            b = rc.banding(s8, dom)
            ly = np.log(np.maximum(o[m] @ rc.LUM, 1e-7))
            ly0 = np.log(np.maximum(out0[m] @ rc.LUM, 1e-7))
            stress[layer][cname] = {
                **b, "region_texels": int(m.sum()),
                "clip_frac": round(float((o[m] >= 0.949).any(axis=-1).mean()), 6),
                "mean_colour_in_region": rc.rnd(o[m].mean(axis=0), 5),
                "std_ratio_logL": round(float(ly.std() / max(ly0.std(), 1e-9)), 4),
                "derived": {k2: rc.rnd(v, 5) for k2, v in dd.items()}, "derived_inside_0_1": inside}
            stress[layer][cname]["pass"] = bool(b["pass"] and inside)
    stress_pass = all(v["pass"] for layer in stress.values() for c, v in layer.items() if c in rc.STRESS)
    gp3_pass = all(v for k2, v in gp3.items() if k2.split("/")[1] in rc.STRESS)

    gp4_after = {m: rc.sha256(rc.PROJECT / "Scripts" / "props" / m) for m in ART_MODULES}
    for m in ART_MODULES:
        gp4[m]["after"] = gp4_after[m]
    gp4_pass = all(v["before"] == v["after"] for v in gp4.values())
    gates = {"G-P0_rerun_equals_shipped_BC": gp0,
             "decomposition_2x_max_abs_linear": decomposition_2x_max_abs,
             "weights_2x": weights_2x,
             "G-P1_recompose_default_vs_shipped_BC": gp1,
             "encoding_choice": {"PaperDetail_rgb_srgb": enc["srgb"], "PaperDetail_rgb_linear_rejected": enc["linear"]},
             "paper_weight_clip": clip_report,
             "default_every_mip_vs_BC_mips": {"max_level_diff": mip_max, "per_mip": mips},
             "G-P2_dry_pool_zero_and_derived_valid": gp2,
             "G-P3_derived_inside_0_1": {"pass": gp3_pass, "cases": gp3},
             "G-P4_art_modules_unchanged_during_run": {"pass": gp4_pass, "modules": gp4},
             "readback": readback,
             "recolour_stress": {"pass": stress_pass, "layers": stress,
                                 "regions": {"Paper": "paper term > half the texel's albedo",
                                             "Black Ink": "W_bw + W_bd >= 0.5", "Red Ink": "W_rw + W_rd + W_rp >= 0.5"}}}
    ok = bool(gp0["pass"] and gp1["pass"] and gp2["pass"] and gp3_pass and gp4_pass and readback["pass"]
              and stress_pass and weights_2x["pass"] and decomposition_2x_max_abs == 0.0)
    shipped_after = {s: rc.sha256(TEX / f"T_PaperBomb_{s}.png") for s in ("BC", "ORM", "N", "M")}
    params = {"Paper Colour": rc.rnd(list(paper_colour) + [1.0], 9),
              "Black Ink Colour": rc.rnd(list(black) + [1.0], 9), "Red Ink Colour": rc.rnd(list(red) + [1.0], 9),
              "Paper Weight Scale": scale, **consts, "Albedo Ceiling": pal.ceiling_linear}
    doc = {
        "schema": "ninjapack.recolour_maps/1", "item": "PaperBomb",
        "status": "exact-match pass 2026-09-26: the traced face (paperbomb_tracedart); rerun this generator whenever "
                  "the art changes (G-P0 fails loudly if the art no longer matches the shipped BC)",
        "generated": datetime.date.today().isoformat(),
        "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__), "common": rc.rel(rc.__file__),
                      "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": bpy.app.version_string,
                      "art": {"seed": SEED, "supersample": SUPERSAMPLE, "ink_floor": cfg.ink_floor,
                              "raster": [rw, rh], "ppmm": plan.ppmm, "atlas": plan.size,
                              "capture": "paperbomb_tracedart.composite_traced wrapped in memory (restored after "
                                         "draw_art)"}},
        "source_maps_sha256": shipped_sha, "source_maps_unchanged_after": shipped_after == shipped_sha,
        "maps": {
            "T_PaperBomb_PaperDetail": {
                "file": rc.rel(OUT_PAPER), "sha256": rc.sha256(OUT_PAPER), "size": [plan.size, plan.size],
                "format": "PNG RGBA 8-bit (colour type 6), no colour chunks, row 0 = top",
                "channels": {"R": "paper weight, red channel / Paper Weight Scale", "G": "... green", "B": "... blue",
                             "A": "W_rp: pooled red ink weight (LINEAR)"},
                "encoding": "RGB sRGB-ENCODED linear weights (sample with sRGB ON: the sampled value is the linear "
                            "weight / scale); A linear",
                "unreal_import": {"srgb": True, "compression": "TC_EDITOR_ICON (UserInterface2D: uncompressed BGRA8, "
                                                               "honours sRGB)", "expected_pc_format": "B8G8R8A8 (sRGB)",
                                  "sampler": "SAMPLERTYPE_COLOR", "mips": "TMGS_FROM_TEXTURE_GROUP",
                                  "address": "Wrap",
                                  "why_uncompressed": "G-P1 holds at 1 stored level with UNCOMPRESSED weights; block "
                                                      "compression (BC7) was not measured here and adds its block "
                                                      "error on top of that budget - the Unreal V2 capture decides"}},
            "T_PaperBomb_InkWeights": {
                "file": rc.rel(OUT_INK), "sha256": rc.sha256(OUT_INK), "size": [plan.size, plan.size],
                "format": "PNG RGBA 8-bit (colour type 6), no colour chunks, row 0 = top",
                "channels": {"R": "W_bw black ink wet", "G": "W_bd black ink dry", "B": "W_rw red ink wet",
                             "A": "W_rd red ink dry"},
                "encoding": "LINEAR weights 0..1",
                "unreal_import": {"srgb": False, "compression": "TC_VECTOR_DISPLACEMENTMAP (uncompressed BGRA8, "
                                                                "linear)", "expected_pc_format": "B8G8R8A8",
                                  "sampler": "SAMPLERTYPE_LINEAR_COLOR", "mips": "TMGS_FROM_TEXTURE_GROUP",
                                  "address": "Wrap"}}},
        "parts": {"Tag": {
            "slot_material": "M_PaperBomb", "instance": "MI_PaperBomb_Tag", "master": "M_PaperInk_Master",
            "recolourable_parts": ["Paper", "Black Ink", "Red Ink"],
            "params": params,
            "graph": ("BaseColor = min(PaperColour * PaperDetail.rgb * PaperWeightScale + BlackInk * Ink.r + BlackDry * "
                      "Ink.g + RedInk * Ink.b + RedDry * Ink.a + RedPool * PaperDetail.a, AlbedoCeiling) x lerp(1, "
                      "ORM.R, Baked AO In Colour); PaperDetail sampled sRGB (decoded), InkWeights linear"),
            "derivation": {"BlackDry": "lerp(BlackInk, PaperColour, Black Ink Dry Paper Mix) * Black Ink Dry Gain",
                           "RedDry": "sRGBdecode(Red Ink Dry Value Scale * sRGBencode(RedInk)), per channel",
                           "RedPool": "lerp(Y(RedInk), RedInk, Red Ink Pool Saturation) * Red Ink Pool Gain, "
                                      "Y = Rec.709 luminance (0.2126, 0.7152, 0.0722)",
                           "derived_at_defaults": {k2: rc.rnd(v, 7) for k2, v in der.items()},
                           "defaults_from": {"Black Ink Colour": "sRGBdecode of the traced art's black "
                                                                         "(trace.BLACK_STORED)",
                                             "Red Ink Colour": "median linear colour of the traced art's red cores",
                                             "dry_pool_rule_anchors": {"black_dry": list(pal.black_dry),
                                                                       "red_pool": list(pal.red_pool)}}},
            "paper_colour_texels": int(paper_only.sum()),
            "notes": ["Paper Colour is the mean linear colour of the front's ink-free card texels (the shipped BC)",
                      "Pooled red stays dark for any Red Ink Colour (the pool gain ~0.08-0.10): that is how pooled "
                      "vermilion reads; document it for buyers",
                      "AO is NOT in these maps: the master multiplies ORM.R into the base colour, as the gallery did",
                      "The traced face has no dry or pooled ink layer: W_bd, W_rd and W_rp are zero and the dry / "
                      "pool colours of MF_InkDerive are unused; the ink's mottle and dry-brush bristles are its "
                      "coverage, so a LIGHT ink colour keeps them only as coverage and the paper weight carries the "
                      "rest (see recolour_stress std_ratio_logL)"],
            "gates": gates, "pass": ok}},
        "pass": ok,
    }
    rc.write_json(OUT_DIR / "recolour_maps.json", doc)
    rc.write_json(rc.WORK / "maps" / "gates_paperbomb.json", doc)
    log(f"G-P0 {gp0['max']}; G-P1 max {gp1['max']} (>1: {gp1['texels_diff_gt1']}) dE00 mean {gp1['dE00_mean']}; linear-"
        f"RGB alternative max {enc['linear']['max']}; mips max {mip_max}; neg residual texel-channels "
        f"{clip_report['texel_channels_negative']}; G-P2 {gp2['pass']}; G-P3 {gp3_pass}; G-P4 {gp4_pass}; stress "
        f"{stress_pass}; {time.time() - t_start:.0f} s -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        import os
        os._exit(code)
