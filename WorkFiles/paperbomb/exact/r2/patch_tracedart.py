p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_tracedart.py"
s = open(p, encoding="utf-8").read()
s = s.replace('TRACEDART_VERSION = "1.0.0"', 'TRACEDART_VERSION = "1.1.0"')

# constants
s = s.replace('''#: the fibre band added above the reference's Nyquist: stored-luma standard deviation
FIBRE_STD = 0.0045''', '''#: the fibre band added above the reference's Nyquist: stored-luma standard deviation
FIBRE_STD = 0.0045
#: POOLED INK.  Where the black is a pool on the red (the knob where the top-left
#: flourish's hook meets the rule), the reference shows a soft dark-maroon-to-black
#: wash - black at 0.3 - 0.8 over full red - not a black shape.  The frame's black
#: CONTOUR part is laid as that wash: the reference's own black field, sharpened back
#: through the source's point spread (Van Cittert), within this reach (mm) of the
#: traced pool
WASH_REACH_MM = 0.55
WASH_DECONV_ITERS = 4''')

# dataclass fields
s = s.replace('''    polys_mm: dict                 # layer -> [ (N, 2) card-mm polygons ]''', '''    polys_mm: dict                 # layer -> [ (N, 2) card-mm polygons ]
    erase_mm: dict                 # layer -> knock-out polygons erased from that layer
    wash_mm: list                  # black polygons laid as a pooled wash, not a shape
    stroke_black_mm: list          # the black rule strokes (laid solid, never bristled)
    wash_field: np.ndarray         # black wash coverage at the source grid (sharpened)
    wash_weight: np.ndarray        # where the wash replaces the shape (0..1, source grid)''')

old = '''    polys_mm = {"black": [], "red": []}
    gpolys = {}
    for g in traced["groups"]:
        ps = PT.group_polys_mm(g, step_mm=0.01)
        gpolys[(g["group"], g["layer"])] = ps
        polys_mm[g["layer"]] += ps
'''
new = '''    polys_mm = {"black": [], "red": []}
    erase_mm = {"black": [], "red": []}
    gpolys = {}
    wash_mm, stroke_black_mm = [], []
    for g in traced["groups"]:
        ps = PT.group_polys_mm(g, step_mm=0.01)
        gpolys[(g["group"], g["layer"])] = ps
        polys_mm[g["layer"]] += ps
        erase_mm[g["layer"]] += PT.knockout_polys_mm(g)
        if g["group"] == PT.FRAME and g["layer"] == "black":
            wash_mm += PT.contour_only_polys_mm(g, step_mm=0.01)
            stroke_black_mm += PT.stroke_only_polys_mm(g)
'''
assert old in s
s = s.replace(old, new)

old = '''        box = T.fill_polys([_to_px(fit, p) for p in polys_mm[layer]], H, W, ss=16).astype(np.float64)
        p = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX)'''
new = '''        box = T.fill_polys([_to_px(fit, p) for p in polys_mm[layer]], H, W, ss=16).astype(np.float64)
        if erase_mm[layer]:
            box = box * (1.0 - T.fill_polys([_to_px(fit, p) for p in erase_mm[layer]], H, W, ss=16))
        p = T.gauss_blur(box, T.SOURCE_PSF_SIGMA_PX)'''
assert old in s
s = s.replace(old, new)

old = '''    stats["paper_px_kept"] = int(paper_px.sum())'''
new = '''    # POOLED WASH: the observed black near the traced pool, sharpened back through the
    # source's footprint (pixel box ~ Gaussian 0.29 px, with the PSF's 0.4 px) so that
    # photographing it again gives back what the reference shows, not a softer pool
    wash_weight = np.zeros((H, W))
    wash_field = np.zeros((H, W))
    if wash_mm:
        wbox = T.fill_polys([_to_px(fit, p) for p in wash_mm], H, W, ss=16) > 0.02
        reach = T.dilate(wbox, int(round(WASH_REACH_MM * ppmm_s)))
        wash_weight = np.clip(T.gauss_blur(reach.astype(np.float64), 0.7) * 1.6 - 0.3, 0.0, 1.0)
        obs_k = np.where(T.dilate(reach, 2), ak, 0.0)
        sig = math.hypot(T.SOURCE_PSF_SIGMA_PX, 0.29)
        est = obs_k.copy()
        for _ in range(WASH_DECONV_ITERS):
            est = np.clip(est + (obs_k - T.gauss_blur(est, sig)), 0.0, 1.0)
        wash_field = est
    stats["wash_px"] = int((wash_weight > 0.5).sum())
    stats["erase_polys"] = {k: len(v) for k, v in erase_mm.items()}
    stats["paper_px_kept"] = int(paper_px.sum())'''
assert old in s
s = s.replace(old, new)

old = '''    m = RefModel(L=L, unm=unm, traced=traced, traced_sha256=tsha, polys_mm=polys_mm,'''
new = '''    m = RefModel(L=L, unm=unm, traced=traced, traced_sha256=tsha, polys_mm=polys_mm,
                 erase_mm=erase_mm, wash_mm=wash_mm, stroke_black_mm=stroke_black_mm,
                 wash_field=wash_field, wash_weight=wash_weight,'''
assert old in s
s = s.replace(old, new)

# build_front_traced: extra channels
old = '''             model.orient[..., 0], model.orient[..., 1]]'''
new = '''             model.orient[..., 0], model.orient[..., 1],
             model.wash_field, model.wash_weight]'''
assert old in s
s = s.replace(old, new)
old = '''    oc2, os2 = full[10], full[11]
    del full, base, coef'''
new = '''    oc2, os2 = full[10], full[11]
    wash_f = np.clip(full[12], 0, 1)
    wash_w = np.clip(full[13], 0, 1)
    del full, base, coef'''
assert old in s
s = s.replace(old, new)

old = '''    S = {layer: PT.rasterise_mm(model.polys_mm[layer], px, cfg.pad_mm, H, W, ss=4)
         .astype(np.float32) for layer in ("black", "red")}'''
new = '''    wash_ids = {id(q) for q in model.wash_mm}
    S = {}
    for layer in ("black", "red"):
        polys = model.polys_mm[layer]
        if layer == "black" and model.wash_mm:
            # the pool is laid as a wash below, not as a shape
            polys = [q for q in polys if not any(q.shape == w.shape and np.array_equal(q, w)
                                                  for w in model.wash_mm)]
        cov = PT.rasterise_mm(polys, px, cfg.pad_mm, H, W, ss=4).astype(np.float32)
        if model.erase_mm[layer]:
            cov = cov * (1.0 - PT.rasterise_mm(model.erase_mm[layer], px, cfg.pad_mm, H, W,
                                               ss=4).astype(np.float32))
        S[layer] = cov
    # the black rule strokes are laid at their sampled tone, never split into bristles:
    # their width already carries the dry run-out (it thins to a hair where the
    # reference greys), so a bristle split there frayed the end into a splay
    stroke_k = PT.rasterise_mm(model.stroke_black_mm, px, cfg.pad_mm, H, W, ss=4) \\
        .astype(np.float32) if model.stroke_black_mm else np.zeros((H, W), np.float32)'''
assert old in s
s = s.replace(old, new)

old = '''    def layer_alpha(Sx, tone, res, fld):
        # a crisp inner mark is laid at the solid tone, so its mean is the sampled tone
        inner = np.where(tone >= TONE_SOLID, tone,
                         crisp(np.clip(tone / TONE_SOLID, 0, 1), fld) * TONE_SOLID)'''
new = '''    def layer_alpha(Sx, tone, res, fld, solid=None):
        # a crisp inner mark is laid at the solid tone, so its mean is the sampled tone
        inner = np.where(tone >= TONE_SOLID, tone,
                         crisp(np.clip(tone / TONE_SOLID, 0, 1), fld) * TONE_SOLID)
        if solid is not None:
            inner = np.where(solid > 0.0, tone, inner)'''
assert old in s
s = s.replace(old, new)
old = '''    ak = layer_alpha(S["black"], tone_k, res_k, field_k)'''
new = '''    # the black residual inside the wash's reach belongs to the wash
    res_k = res_k * (1.0 - wash_w)
    res_k = np.where(stroke_k > 0.0, 0.0, res_k)
    ak = layer_alpha(S["black"], tone_k, res_k, field_k, solid=stroke_k)
    ak = np.maximum(ak, (wash_w * wash_f).astype(np.float32))'''
assert old in s
s = s.replace(old, new)
s = s.replace('''        "ornaments": {"source": "traced groups 'frame', 'chain'"},''', '''        "ornaments": {"source": "traced groups 'frame', 'chain'"},
        "knockouts": [{"group": g["group"], "name": k["name"], "kind": k["kind"],
                       "loss": k["loss"]} for g in model.traced["groups"]
                      for k in g.get("knockouts_mm", [])],
        "wash": {"reach_mm": WASH_REACH_MM, "deconv_iters": WASH_DECONV_ITERS,
                 "px_source": model.stats.get("wash_px")},''')
# derivation text
s = s.replace('''        "seal_big": d % "'seal_big'" + " (the white tall curling flame is its knocked-out holes)",
        "small_seal": d % "'small_seal' + 'frame'" + " (box and 火道 traced)",''', '''        "seal_big": d % "'seal_big'" + " (the white tall curling flame is its knocked-out holes; "
                    "the two corner sparkles are sub-pixel knock-outs fitted by analysis by "
                    "synthesis, paperbomb_finefit)",
        "small_seal": d % "'small_seal' + 'frame'" + " (box and 火道 traced; the slots between "
                      "the bars of 道's 目 are sub-pixel knock-outs fitted by analysis by "
                      "synthesis, paperbomb_finefit)",''')
s = s.replace('''        "corners": d % "'frame' (contour part)",''', '''        "corners": d % "'frame' (contour part)" + "; the black pool on the top-left knob is "
                   "the reference's own black field laid as a wash (sharpened back through "
                   "the source PSF), not a shape",''')
s = s.replace('''        "rules": "traced: paperbomb_traced.json group 'frame' strokes (centreline + width, "
                 "gaps only where the reference lifts)",''', '''        "rules": "traced: paperbomb_traced.json group 'frame' strokes (centreline + width, "
                 "gaps only where the reference lifts; the black middle run integrated over "
                 "the whole rule band so it thins to a hair where the reference greys, laid "
                 "solid without bristles)",''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
