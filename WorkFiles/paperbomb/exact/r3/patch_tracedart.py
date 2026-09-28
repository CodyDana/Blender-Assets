p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_tracedart.py"
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:90])
    s = s.replace(old, new)


rep('TRACEDART_VERSION = "1.1.0"', 'TRACEDART_VERSION = "1.2.0"')
rep('''WASH_REACH_MM = 1.0
WASH_DECONV_ITERS = 4''', '''WASH_REACH_MM = 1.0
WASH_DECONV_ITERS = 4
#: THE POOL SITS ON THE RED.  Round the pool (not the rule's dry run-out) the wash is
#: kept only where the traced red is: the reference's pool is a dark-maroon knob with a
#: tight black rim, and the sharpened black field's reach onto the bare paper beside the
#: knob (the edge pixels' mix of black and paper) laid a grey-black smudge there
POOL_ON_RED = True''')
rep('''    erase_mm: dict                 # layer -> knock-out polygons erased from that layer''',
    '''    erase_mm: dict                 # layer -> crisp polygons erased from that layer
    soft_mm: dict                  # layer -> [(soft_px, polygons)] erased soft
    ink_mm: dict                   # layer -> spike outlines laid over the erased ink
    pool_weight: np.ndarray        # the pool's reach (0..1, source grid)''')
rep('''    erase_mm = {"black": [], "red": []}
    gpolys = {}
    wash_mm, stroke_black_mm, shape_black_mm = [], [], []''',
    '''    erase_mm = {"black": [], "red": []}
    soft_mm = {"black": [], "red": []}
    ink_mm = {"black": [], "red": []}
    gpolys = {}
    wash_mm, stroke_black_mm, shape_black_mm, pool_mm = [], [], [], []''')
rep('''        erase_mm[g["layer"]] += PT.knockout_polys_mm(g)
        if g["group"] == PT.FRAME and g["layer"] == "black":
            # the pool (contour part) and the dry run-out are washes; the body is a shape
            wash_mm += PT.contour_only_polys_mm(g, step_mm=0.01)''',
    '''        erase_mm[g["layer"]] += PT.knockout_polys_mm(g)
        soft_mm[g["layer"]] += PT.soft_knockouts_mm(g)
        ink_mm[g["layer"]] += PT.ink_polys_mm(g)
        if g["group"] == PT.FRAME and g["layer"] == "black":
            # the pool (contour part) and the dry run-out are washes; the body is a shape
            pool_mm += PT.contour_only_polys_mm(g, step_mm=0.01)
            wash_mm += PT.contour_only_polys_mm(g, step_mm=0.01)''')
rep('''        box = T.fill_polys([_to_px(fit, p) for p in polys_mm[layer]], H, W, ss=16).astype(np.float64)
        if erase_mm[layer]:
            box = box * (1.0 - T.fill_polys([_to_px(fit, p) for p in erase_mm[layer]], H, W, ss=16))
        p = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX)''',
    '''        box = PT.compose_coverage(
            lambda ps: T.fill_polys([_to_px(fit, q) for q in ps], H, W, ss=16),
            polys_mm[layer], erase_mm[layer], soft_mm[layer], ink_mm[layer])
        p = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX)''')
rep('''    wash_red = np.zeros((H, W))
    if wash_mm:''', '''    wash_red = np.zeros((H, W))
    pool_weight = np.zeros((H, W))
    if pool_mm and POOL_ON_RED:
        pbox = T.fill_polys([_to_px(fit, p) for p in pool_mm], H, W, ss=16) > 0.02
        preach = T.dilate(pbox, int(round(WASH_REACH_MM * ppmm_s)) + 2)
        pool_weight = np.clip(T.gauss_blur(preach.astype(np.float64), 0.7) * 1.6 - 0.3, 0.0, 1.0)
    if wash_mm:''')
rep('''    stats["erase_polys"] = {k: len(v) for k, v in erase_mm.items()}''',
    '''    stats["erase_polys"] = {k: len(v) for k, v in erase_mm.items()}
    stats["soft_erase_sets"] = {k: len(v) for k, v in soft_mm.items()}
    stats["spike_ink_polys"] = {k: len(v) for k, v in ink_mm.items()}
    stats["pool_px"] = int((pool_weight > 0.5).sum())''')
rep('''                 erase_mm=erase_mm, wash_mm=wash_mm, stroke_black_mm=stroke_black_mm,''',
    '''                 erase_mm=erase_mm, soft_mm=soft_mm, ink_mm=ink_mm, pool_weight=pool_weight,
                 wash_mm=wash_mm, stroke_black_mm=stroke_black_mm,''')
rep('''             model.wash_field, model.wash_weight, model.wash_red]''',
    '''             model.wash_field, model.wash_weight, model.wash_red, model.pool_weight]''')
rep('''    wash_r = np.clip(full[14], 0, 1)''', '''    wash_r = np.clip(full[14], 0, 1)
    pool_w = np.clip(full[15], 0, 1)''')
rep('''        cov = PT.rasterise_mm(polys, px, cfg.pad_mm, H, W, ss=4).astype(np.float32)
        if model.erase_mm[layer]:
            cov = cov * (1.0 - PT.rasterise_mm(model.erase_mm[layer], px, cfg.pad_mm, H, W,
                                               ss=4).astype(np.float32))
        S[layer] = cov''',
    '''        cov = PT.compose_coverage(
            lambda ps: PT.rasterise_mm(ps, px, cfg.pad_mm, H, W, ss=4),
            polys, model.erase_mm[layer], model.soft_mm[layer], model.ink_mm[layer],
            blur_scale=px / fit.ppmm)
        S[layer] = cov.astype(np.float32)''')
rep('''    ak = layer_alpha(S["black"], tone_k, res_k, field_k, solid=stroke_k)
    ak = np.maximum(ak, (wash_w * wash_f).astype(np.float32))
    arb = layer_alpha(S["red"], tone_r, res_r, field_r, solid=kowin if kw_polys else None)
    arb = np.maximum(arb, (wash_w * wash_r).astype(np.float32))''',
    '''    # round the pool the wash lies only on the traced red (see POOL_ON_RED)
    on_red = (1.0 - pool_w * (1.0 - np.clip(S["red"], 0.0, 1.0))).astype(np.float32)
    ak = layer_alpha(S["black"], tone_k, res_k, field_k, solid=stroke_k)
    ak = np.maximum(ak, (wash_w * wash_f * on_red).astype(np.float32))
    arb = layer_alpha(S["red"], tone_r, res_r, field_r, solid=kowin if kw_polys else None)
    arb = np.maximum(arb, (wash_w * wash_r * on_red).astype(np.float32))''')
rep('''        "wash": {"reach_mm": WASH_REACH_MM, "deconv_iters": WASH_DECONV_ITERS,
                 "px_source": model.stats.get("wash_px")},''',
    '''        "wash": {"reach_mm": WASH_REACH_MM, "deconv_iters": WASH_DECONV_ITERS,
                 "px_source": model.stats.get("wash_px"), "pool_on_red": POOL_ON_RED},
        "spikes": [{"group": g["group"], "name": k["name"], "loss": k["loss"]}
                   for g in model.traced["groups"] for k in g.get("spikes_mm", [])],''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
