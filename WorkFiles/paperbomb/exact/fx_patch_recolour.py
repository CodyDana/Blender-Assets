# final pass: re-point make_paperbomb_recolour_maps.py at the traced art (props_lib.paperbomb_tracedart.composite_traced)
import io
p = "C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/maps/make_paperbomb_recolour_maps.py"
s = io.open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)


rep('''cleanly (the pooled vermilion fails a luminance tint at dE76 p99 17.4).  This generator re-runs the art exactly as the
build does - ``bake.draw_art(spec, plan, seed=20260919, supersample=2)`` - with ``paperbomb_art._composite`` wrapped
IN MEMORY (nothing on disk changes) to capture the 2x ink layers the composite consumed, and proves the re-run is the
shipped art (``bake.transfer`` of it re-quantises to the shipped T_PaperBomb_BC byte for byte).

Per texel, at 2x, with K = 1 - 0.13 clip(grime 0.5 + edge_band 0.6) max(a_r (1 - d_r), a_b (1 - d_b)) (``_composite``):

    W_bw = a_b d_b K                      black ink, wet            -> Black Ink Colour
    W_bd = a_b (1 - d_b) K                black ink, dry            -> BlackDry = lerp(Black, Paper, t) * g
    W_rw = (1 - a_b) a_r d_r (1 - p_r) K  red ink, wet              -> Red Ink Colour
    W_rd = (1 - a_b) a_r (1 - d_r)(1 - p_r) K    red ink, dry       -> RedDry = sRGBdecode(0.82 sRGBencode(Red))
    W_rp = (1 - a_b) a_r p_r K            red ink, pooled           -> RedPool = lerp(Y(Red), Red, s) * g_p
''', '''cleanly (the pooled vermilion fails a luminance tint at dE76 p99 17.4).  This generator re-runs the art exactly as the
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
''')
rep('''SNAPSHOT = rc.PROJECT / "WorkFiles" / "paperbomb" / "paused_2026-09-21" / "Scripts_props"
ART_MODULES = ("props_lib/paperbomb_art.py", "props_lib/bake.py", "props_lib/atlas.py", "props_lib/spec.py",
               "props_lib/paper_material.py", "build_paper_bomb.py")''',
    '''#: every file the face depends on: hashed before and after the run (G-P4: unchanged while it ran)
ART_MODULES = ("props_lib/paperbomb_art.py", "props_lib/paperbomb_tracedart.py", "props_lib/paperbomb_trace.py",
               "props_lib/paperbomb_finefit.py", "props_lib/paperbomb_traced.json", "props_lib/trace.py",
               "props_lib/bake.py", "props_lib/atlas.py", "props_lib/spec.py", "props_lib/paper_material.py",
               "build_paper_bomb.py")''')
rep('''    from props_lib import paperbomb_art as art
    from props_lib.spec import PAPER_BOMB''', '''    from props_lib import paperbomb_art as art
    from props_lib import paperbomb_tracedart as TA
    from props_lib.spec import PAPER_BOMB''')
rep('''    # --- G-P4: the art modules are the paused snapshot's
    gp4 = {m: {"live": rc.sha256(rc.PROJECT / "Scripts" / "props" / m), "snapshot": rc.sha256(SNAPSHOT / m)}
           for m in ART_MODULES}
    gp4_pass = all(v["live"] == v["snapshot"] for v in gp4.values())''',
    '''    # --- G-P4: the art modules, hashed now and again at the end (unchanged while this ran)
    gp4 = {m: {"before": rc.sha256(rc.PROJECT / "Scripts" / "props" / m)} for m in ART_MODULES}''')
rep('''    captured = []
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
        raise RuntimeError(f"_composite ran {len(captured)} times; expected once (the front)")''',
    '''    captured = []
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
        raise RuntimeError(f"composite_traced ran {len(captured)} times; expected once (the front)")''')
rep('''    # --- the 2x weights, and their own recomposition check against the composite the art produced
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
    del recomp2, dirt, thin''',
    '''    # --- the capture is complete: the composite re-run from the captured layers is the captured colour, exactly
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
    del k2, r2, rgb2, red_loc, g_r, ink2, hh, h, resid2''')
rep('''    black, red = np.array(pal.black_wet, np.float64), np.array(pal.red_wet, np.float64)
    t_mix''', '''    t_mix''')
rep('''    gp2 = {}
    for name, got, want in (("BlackDry", der["BlackDry"], pal.black_dry), ("RedDry", der["RedDry"], pal.red_dry),
                            ("RedPool", der["RedPool"], pal.red_pool)):
        dl = np.abs(rc.l2s(got) - rc.l2s(np.asarray(want))) * 255.0
        gp2[name] = {"derived": rc.rnd(got, 7), "palette": list(want), "max_stored_level_diff": round(float(dl.max()), 4)}
    gp2["pass"] = all(v["max_stored_level_diff"] <= 0.25 for v in gp2.values() if isinstance(v, dict))''',
    '''    # G-P2: the traced face has no dry / pooled layer (their weights are zero, checked on the stored map below); the
    # master's MF_InkDerive colours are still derived from the three buyer colours so its graph is unchanged, and
    # they must be real colours
    gp2 = {}
    for name in ("BlackDry", "RedDry", "RedPool"):
        got = der[name]
        gp2[name] = {"derived": rc.rnd(got, 7), "inside_0_1": bool((got >= 0).all() and (got <= 1).all())}''')
rep('''    # --- write the two maps''', '''    wq8 = rc.q8_linear(wa)
    gp2["dry_and_pool_weights_zero"] = bool(int(wq8[..., 1].max()) == 0 and int(wq8[..., 3].max()) == 0
                                            and int(wq8[..., 4].max()) == 0)
    gp2["pass"] = bool(gp2["dry_and_pool_weights_zero"] and all(v["inside_0_1"] for v in gp2.values()
                                                                   if isinstance(v, dict)))
    # --- write the two maps''')
rep('''    gates = {"G-P0_rerun_equals_shipped_BC": gp0,
             "decomposition_2x_max_abs_linear": decomposition_2x_max_abs,''',
    '''    gp4_after = {m: rc.sha256(rc.PROJECT / "Scripts" / "props" / m) for m in ART_MODULES}
    for m in ART_MODULES:
        gp4[m]["after"] = gp4_after[m]
    gp4_pass = all(v["before"] == v["after"] for v in gp4.values())
    gates = {"G-P0_rerun_equals_shipped_BC": gp0,
             "decomposition_2x_max_abs_linear": decomposition_2x_max_abs,
             "weights_2x": weights_2x,''')
rep('''"G-P2_derived_vs_palette": gp2,''', '''"G-P2_dry_pool_zero_and_derived_valid": gp2,''')
rep('''"G-P4_art_modules_equal_snapshot": {"pass": gp4_pass, "modules": gp4},''',
    '''"G-P4_art_modules_unchanged_during_run": {"pass": gp4_pass, "modules": gp4},''')
rep('''    ok = bool(gp0["pass"] and gp1["pass"] and gp2["pass"] and gp3_pass and gp4_pass and readback["pass"]
              and stress_pass and decomposition_2x_max_abs < 1e-5)''',
    '''    ok = bool(gp0["pass"] and gp1["pass"] and gp2["pass"] and gp3_pass and gp4_pass and readback["pass"]
              and stress_pass and weights_2x["pass"] and decomposition_2x_max_abs == 0.0)''')
rep('''              "Black Ink Colour": list(pal.black_wet) + [1.0], "Red Ink Colour": list(pal.red_wet) + [1.0],''',
    '''              "Black Ink Colour": rc.rnd(list(black) + [1.0], 9), "Red Ink Colour": rc.rnd(list(red) + [1.0], 9),''')
rep('''        "status": "PAUSED item: built against the CURRENT maps; rerun this generator after the exact-match pass "
                  "(G-P0 fails loudly if the art no longer matches the shipped BC)",''',
    '''        "status": "exact-match pass 2026-09-26: the traced face (paperbomb_tracedart); rerun this generator whenever "
                  "the art changes (G-P0 fails loudly if the art no longer matches the shipped BC)",''')
rep('''                              "capture": "paperbomb_art._composite wrapped in memory (restored after draw_art)"}},''',
    '''                              "capture": "paperbomb_tracedart.composite_traced wrapped in memory (restored after "
                                         "draw_art)"}},''')
rep('''                           "palette": {"black_wet": list(pal.black_wet), "black_dry": list(pal.black_dry),
                                       "red_wet": list(pal.red_wet), "red_dry": list(pal.red_dry),
                                       "red_pool": list(pal.red_pool), "paper": list(pal.paper)}},''',
    '''                           "defaults_from": {"Black Ink Colour": "sRGBdecode of the traced art's black "
                                                                         "(trace.BLACK_STORED)",
                                             "Red Ink Colour": "median linear colour of the traced art's red cores",
                                             "dry_pool_rule_anchors": {"black_dry": list(pal.black_dry),
                                                                       "red_pool": list(pal.red_pool)}}},''')
rep('''                      "Black ink's only tonal variation is wet vs dry (a 2:1 albedo ratio in a near-black); with the "
                      "MF_InkDerive rule BlackDry = lerp(BlackInk, Paper, 0.006) * gain ~ BlackInk, a LIGHT black-ink "
                      "colour reads flat inside solid strokes (stress std_ratio_logL 0.002-0.29); the brush texture "
                      "survives at stroke edges and dry-brush coverage, which the paper weight carries"],''',
    '''                      "The traced face has no dry or pooled ink layer: W_bd, W_rd and W_rp are zero and the dry / "
                      "pool colours of MF_InkDerive are unused; the ink's mottle and dry-brush bristles are its "
                      "coverage, so a LIGHT ink colour keeps them only as coverage and the paper weight carries the "
                      "rest (see recolour_stress std_ratio_logL)"],''')
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
