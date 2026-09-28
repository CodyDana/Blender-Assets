"""T_PaperBomb_PaperDetail + T_PaperBomb_InkWeights: an exact linear LAYER DECOMPOSITION of the paper bomb's base colour,
so a buyer can recolour the paper, the black ink and the red ink separately (MATERIAL_PLAN.md 5.3, D5), plus
Exports/PaperBomb/Textures/Recolour/recolour_maps.json.

The shipped T_PaperBomb_M.B is max(red, black): one channel for two inks and no paper detail, so it cannot recolour
cleanly (the pooled vermilion fails a luminance tint at dE76 p99 17.4).  This generator re-runs the art exactly as the
build does - ``bake.draw_art(spec, plan, seed=20260919, supersample=2)`` - with ``paperbomb_art._composite`` wrapped
IN MEMORY (nothing on disk changes) to capture the 2x ink layers the composite consumed, and proves the re-run is the
shipped art (``bake.transfer`` of it re-quantises to the shipped T_PaperBomb_BC byte for byte).

Per texel, at 2x, with K = 1 - 0.13 clip(grime 0.5 + edge_band 0.6) max(a_r (1 - d_r), a_b (1 - d_b)) (``_composite``):

    W_bw = a_b d_b K                      black ink, wet            -> Black Ink Colour
    W_bd = a_b (1 - d_b) K                black ink, dry            -> BlackDry = lerp(Black, Paper, t) * g
    W_rw = (1 - a_b) a_r d_r (1 - p_r) K  red ink, wet              -> Red Ink Colour
    W_rd = (1 - a_b) a_r (1 - d_r)(1 - p_r) K    red ink, dry       -> RedDry = sRGBdecode(0.82 sRGBencode(Red))
    W_rp = (1 - a_b) a_r p_r K            red ink, pooled           -> RedPool = lerp(Y(Red), Red, s) * g_p

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
SNAPSHOT = rc.PROJECT / "WorkFiles" / "paperbomb" / "paused_2026-09-21" / "Scripts_props"
ART_MODULES = ("props_lib/paperbomb_art.py", "props_lib/bake.py", "props_lib/atlas.py", "props_lib/spec.py",
               "props_lib/paper_material.py", "build_paper_bomb.py")
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
    from props_lib.spec import PAPER_BOMB

    t_start = time.time()
    # --- G-P4: the art modules are the paused snapshot's
    gp4 = {m: {"live": rc.sha256(rc.PROJECT / "Scripts" / "props" / m), "snapshot": rc.sha256(SNAPSHOT / m)}
           for m in ART_MODULES}
    gp4_pass = all(v["live"] == v["snapshot"] for v in gp4.values())
    shipped_sha = {s: rc.sha256(TEX / f"T_PaperBomb_{s}.png") for s in ("BC", "ORM", "N", "M")}

    spec = PAPER_BOMB
    plan = A.plan_for(spec)
    captured = []
    original = art._composite

    def capture(paper, red, black, cfg=None):
        rgb, rough = original(paper, red, black, cfg)
        captured.append({"a_r": red.a.copy(), "d_r": red.d.copy(), "p_r": red.p.copy(), "a_b": black.a.copy(),
                         "d_b": black.d.copy(), "grime": paper["grime"].copy(), "edge": paper["edge_band"].copy(),
                         "paper_rgb": paper["rgb"].copy(), "rgb": rgb.copy()})
        return rgb, rough

    art._composite = capture                         # IN MEMORY only; restored below
    try:
        t0 = time.time()
        cfg, front, back, provenance = PB.draw_art(spec, plan, seed=SEED, supersample=SUPERSAMPLE)
        log(f"art drawn in {time.time() - t0:.0f} s, raster {front.width} x {front.height}")
    finally:
        art._composite = original
    if len(captured) != 1:
        raise RuntimeError(f"_composite ran {len(captured)} times; expected once (the front)")
    cap = captured[0]
    pal = art.palette_for(cfg)

    # --- G-P0: the re-run IS the shipped art (the transfer re-quantises to the shipped BC byte for byte)
    channels = PB.transfer(plan, front, back, spec, cfg)
    regen = np.clip(np.rint(PB.linear_to_srgb(channels["base"]) * 255.0), 0, 255).astype(np.int16)
    shipped = rc.load_levels8(TEX / "T_PaperBomb_BC.png")[..., :3]
    gp0 = rc.level_diff_stats(regen, shipped)
    gp0["pass"] = bool(gp0["max"] == 0)
    log(f"G-P0 re-run vs shipped BC: max {gp0['max']} (texels>0 {gp0['texels_diff_gt0']})")

    # --- the 2x weights, and their own recomposition check against the composite the art produced
    a_r, d_r, p_r, a_b, d_b = (cap[k].astype(np.float64) for k in ("a_r", "d_r", "p_r", "a_b", "d_b"))
    dirt = np.clip(cap["grime"] * 0.5 + cap["edge"] * 0.6, 0.0, 1.0)
    thin = np.maximum(a_r * (1.0 - d_r), a_b * (1.0 - d_b))
    kk = 1.0 - 0.13 * dirt * thin
    w2 = np.stack([a_b * d_b * kk, a_b * (1 - d_b) * kk, (1 - a_b) * a_r * d_r * (1 - p_r) * kk,
                   (1 - a_b) * a_r * (1 - d_r) * (1 - p_r) * kk, (1 - a_b) * a_r * p_r * kk], axis=-1)
    wpg = (1 - a_r) * (1 - a_b) * kk
    pal_cols = np.array([pal.black_wet, pal.black_dry, pal.red_wet, pal.red_dry, pal.red_pool], np.float64)
    recomp2 = np.clip(wpg[..., None] * cap["paper_rgb"] + w2 @ pal_cols, pal.floor_linear, pal.ceiling_linear)
    decomposition_2x_max_abs = float(np.abs(recomp2 - cap["rgb"]).max())
    del recomp2, dirt, thin
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
    black, red = np.array(pal.black_wet, np.float64), np.array(pal.red_wet, np.float64)
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
    gp2 = {}
    for name, got, want in (("BlackDry", der["BlackDry"], pal.black_dry), ("RedDry", der["RedDry"], pal.red_dry),
                            ("RedPool", der["RedPool"], pal.red_pool)):
        dl = np.abs(rc.l2s(got) - rc.l2s(np.asarray(want))) * 255.0
        gp2[name] = {"derived": rc.rnd(got, 7), "palette": list(want), "max_stored_level_diff": round(float(dl.max()), 4)}
    gp2["pass"] = all(v["max_stored_level_diff"] <= 0.25 for v in gp2.values() if isinstance(v, dict))

    # --- quantise the inks (as stored), then the paper weight as the per-channel residual
    wq = rc.q8_linear(wa) / 255.0                                 # (S, S, 5): InkWeights RGBA + PaperDetail A
    residual = bc_lin - wq @ ink_cols
    wp = residual / paper_colour[None, None, :]
    negative = wp < 0
    clip_report = {"texel_channels_negative": int(negative.sum()),
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

    # --- write the two maps
    paper_map = np.concatenate([pd_rgb, rc.q8_linear(wa[..., 4:5])], axis=-1).astype(np.int32)
    ink_map = rc.q8_linear(wa[..., :4]).astype(np.int32)
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

    gates = {"G-P0_rerun_equals_shipped_BC": gp0,
             "decomposition_2x_max_abs_linear": decomposition_2x_max_abs,
             "G-P1_recompose_default_vs_shipped_BC": gp1,
             "encoding_choice": {"PaperDetail_rgb_srgb": enc["srgb"], "PaperDetail_rgb_linear_rejected": enc["linear"]},
             "paper_weight_clip": clip_report,
             "default_every_mip_vs_BC_mips": {"max_level_diff": mip_max, "per_mip": mips},
             "G-P2_derived_vs_palette": gp2,
             "G-P3_derived_inside_0_1": {"pass": gp3_pass, "cases": gp3},
             "G-P4_art_modules_equal_snapshot": {"pass": gp4_pass, "modules": gp4},
             "readback": readback,
             "recolour_stress": {"pass": stress_pass, "layers": stress,
                                 "regions": {"Paper": "paper term > half the texel's albedo",
                                             "Black Ink": "W_bw + W_bd >= 0.5", "Red Ink": "W_rw + W_rd + W_rp >= 0.5"}}}
    ok = bool(gp0["pass"] and gp1["pass"] and gp2["pass"] and gp3_pass and gp4_pass and readback["pass"]
              and stress_pass and decomposition_2x_max_abs < 1e-5)
    shipped_after = {s: rc.sha256(TEX / f"T_PaperBomb_{s}.png") for s in ("BC", "ORM", "N", "M")}
    params = {"Paper Colour": rc.rnd(list(paper_colour) + [1.0], 9),
              "Black Ink Colour": list(pal.black_wet) + [1.0], "Red Ink Colour": list(pal.red_wet) + [1.0],
              "Paper Weight Scale": scale, **consts, "Albedo Ceiling": pal.ceiling_linear}
    doc = {
        "schema": "ninjapack.recolour_maps/1", "item": "PaperBomb",
        "status": "PAUSED item: built against the CURRENT maps; rerun this generator after the exact-match pass "
                  "(G-P0 fails loudly if the art no longer matches the shipped BC)",
        "generated": datetime.date.today().isoformat(),
        "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__), "common": rc.rel(rc.__file__),
                      "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": bpy.app.version_string,
                      "art": {"seed": SEED, "supersample": SUPERSAMPLE, "ink_floor": cfg.ink_floor,
                              "raster": [rw, rh], "ppmm": plan.ppmm, "atlas": plan.size,
                              "capture": "paperbomb_art._composite wrapped in memory (restored after draw_art)"}},
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
                           "palette": {"black_wet": list(pal.black_wet), "black_dry": list(pal.black_dry),
                                       "red_wet": list(pal.red_wet), "red_dry": list(pal.red_dry),
                                       "red_pool": list(pal.red_pool), "paper": list(pal.paper)}},
            "paper_colour_texels": int(paper_only.sum()),
            "notes": ["Paper Colour is the mean linear colour of the front's ink-free card texels (the shipped BC)",
                      "Pooled red stays dark for any Red Ink Colour (the pool gain ~0.08-0.10): that is how pooled "
                      "vermilion reads; document it for buyers",
                      "AO is NOT in these maps: the master multiplies ORM.R into the base colour, as the gallery did",
                      "Black ink's only tonal variation is wet vs dry (a 2:1 albedo ratio in a near-black); with the "
                      "MF_InkDerive rule BlackDry = lerp(BlackInk, Paper, 0.006) * gain ~ BlackInk, a LIGHT black-ink "
                      "colour reads flat inside solid strokes (stress std_ratio_logL 0.002-0.29); the brush texture "
                      "survives at stroke edges and dry-brush coverage, which the paper weight carries"],
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
