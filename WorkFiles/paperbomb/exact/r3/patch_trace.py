p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_trace.py"
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:80])
    s = s.replace(old, new)


rep('PB_TRACE_VERSION = "2.2.0"', 'PB_TRACE_VERSION = "2.3.0"')

# ---- knock-out records carry their softness
rep('''                     "window_px": r["window_px"], "density": r["density"],''',
    '''                     "window_px": r["window_px"], "density": r["density"],
                     "soft_px": r.get("soft_px", 0.0),''')
rep('''    kept = [c for i, c in enumerate(curves) if i not in drop]
    base = [c.sample(0.05) for c in kept]
    obs = layer_field(L, layer, behind=True)
    erase, recs = [], []
    for spec in specs:
        r = FF.fit_knockout(spec, base, obs, L.density[layer], fit)
        erase += r["polys_px"]''',
    '''    kept = [c for i, c in enumerate(curves) if i not in drop]
    base = [c.sample(0.05) for c in kept]
    obs = layer_field(L, layer, behind=True)
    erase, recs = [], []
    for spec in specs:
        r = FF.fit_knockout(spec, base, obs, L.density[layer], fit)
        erase.append((float(r.get("soft_px", 0.0)), r["polys_px"]))''')

# ---- spikes (the corner claws' prong ends)
rep('''def trace_all(source: str | None = None, only: Sequence[str] | None = None,''',
    '''SPIKE_DERIVED = ("spike: the traced prong's end past a cut {cut} mm back along its axis "
                 "is erased and re-drawn as a tapered point (two cubic edges leaving the "
                 "cut along the traced contour's tangents, meeting in a sharp tip), fitted "
                 "by analysis by synthesis (props_lib.paperbomb_finefit {ver}): rendered "
                 "through the source PSF at full-strength density and moved (pattern "
                 "search) until it reproduces the observed red round the prong")


def apply_spikes(L: Layers, group: str, layer: str, curves: list) -> tuple:
    """Fit this group's prong-end spikes (paperbomb_finefit.SPIKES).  Returns the erase
    polygons, the ink polygons (source px) and the JSON records."""
    specs = [k for k in FF.SPIKES if k["group"] == group and k["layer"] == layer]
    if not specs or not curves:
        return [], [], []
    fit = L.fit
    loops = [c.sample(0.05) for c in curves]
    obs = layer_field(L, layer, behind=True)
    erase, ink, recs = [], [], []

    def mm(q):
        x, y = fit.px_to_mm(q[:, 0], q[:, 1])
        return np.round(np.stack([x, y], 1), 5).tolist()
    for spec in specs:
        r = FF.fit_spike(spec, loops, obs, L.density[layer], fit)
        erase.append(r["cut_px"]); ink.append(r["ink_px"])
        recs.append({"name": spec["name"], "kind": "spike", "tip_mm": list(spec["tip_mm"]),
                     "cut_mm": spec["cut_mm"], "params_px": r["params_px"],
                     "loss": {"traced": r["loss_traced"], "init": r["loss_init"], "fit": r["loss_fit"]},
                     "window_px": r["window_px"], "density": r["density"],
                     "derived": SPIKE_DERIVED.format(cut=spec["cut_mm"], ver=FF.FINEFIT_VERSION),
                     "erase_mm": mm(r["cut_px"]), "ink_mm": mm(r["ink_px"])})
    return erase, ink, recs


def trace_all(source: str | None = None, only: Sequence[str] | None = None,''')
rep('''    erase_by_layer = {"black": [], "red": []}
    kw = dict(variant or {})''',
    '''    erase_by_layer = {"black": [], "red": []}
    soft_by_layer = {"black": [], "red": []}
    ink_by_layer = {"black": [], "red": []}
    kw = dict(variant or {})''')
rep('''            entry["curves_mm"] = [c.to_json() for c in _curves_px_to_mm(curves, fit)]
            entry["strokes_mm"] = strokes''',
    '''            entry["curves_mm"] = [c.to_json() for c in _curves_px_to_mm(curves, fit)]
            entry["strokes_mm"] = strokes
            s_erase, s_ink, s_recs = apply_spikes(L, g, layer, curves)
            if s_recs:
                entry["spikes_mm"] = s_recs
                erase_by_layer[layer] += s_erase
                ink_by_layer[layer] += s_ink''')
rep('''            curves, erase, ko = apply_knockouts(L, g, layer, curves)
            erase_by_layer[layer] += erase''',
    '''            curves, erase, ko = apply_knockouts(L, g, layer, curves)
            for soft, ps in erase:
                if soft > 0.0:
                    soft_by_layer[layer].append((soft, ps))
                else:
                    erase_by_layer[layer] += ps''')
rep('''        box = T.fill_polys(polys_by_layer[layer], H, W, ss=16).astype(np.float64)
        if erase_by_layer[layer]:
            box = box * (1.0 - T.fill_polys(erase_by_layer[layer], H, W, ss=16))''',
    '''        box = compose_coverage(lambda ps: T.fill_polys(ps, H, W, ss=16),
                               polys_by_layer[layer], erase_by_layer[layer],
                               soft_by_layer[layer], ink_by_layer[layer])''')
rep('''              "polys_by_layer": polys_by_layer, "erase_by_layer": erase_by_layer}''',
    '''              "polys_by_layer": polys_by_layer, "erase_by_layer": erase_by_layer,
              "soft_by_layer": soft_by_layer, "ink_by_layer": ink_by_layer}''')

# ---- storage helpers
rep('''def knockout_polys_mm(entry: dict) -> list:
    """The group's fitted knock-outs (card mm): paper ERASED from its traced ink,
    coverage = traced x (1 - erase)."""
    out = []
    for k in entry.get("knockouts_mm", []):
        out += [np.asarray(q, np.float64) for q in k["polys_mm"]]
    return out''',
    '''def knockout_polys_mm(entry: dict) -> list:
    """The group's crisp erases (card mm): its fitted knock-outs laid crisp and its
    spikes' cuts - paper ERASED from its traced ink, coverage = traced x (1 - erase)."""
    out = []
    for k in entry.get("knockouts_mm", []):
        if float(k.get("soft_px", 0.0)) > 0.0:
            continue
        out += [np.asarray(q, np.float64) for q in k["polys_mm"]]
    for k in entry.get("spikes_mm", []):
        out.append(np.asarray(k["erase_mm"], np.float64))
    return out


def soft_knockouts_mm(entry: dict) -> list:
    """The group's knock-outs laid SOFT: [(soft_px (source px), [card-mm polygons])]."""
    return [(float(k["soft_px"]), [np.asarray(q, np.float64) for q in k["polys_mm"]])
            for k in entry.get("knockouts_mm", []) if float(k.get("soft_px", 0.0)) > 0.0]


def ink_polys_mm(entry: dict) -> list:
    """The group's re-drawn spike outlines (card mm): ink laid OVER the erased traced
    ink, coverage = max(traced x (1 - erase), ink)."""
    return [np.asarray(k["ink_mm"], np.float64) for k in entry.get("spikes_mm", [])]


def compose_coverage(fill, polys, erase, soft, ink, blur_scale: float = 1.0):
    """One layer's coverage: traced polygons x (1 - crisp erase) x (1 - soft erase), then
    the spike ink over it.  ``fill`` rasterises a polygon list on the target grid;
    ``soft`` is [(soft_px, polys)] with soft_px in source px, ``blur_scale`` the target
    grid's px per source px."""
    box = np.asarray(fill(polys), np.float64)
    if erase:
        box = box * (1.0 - np.asarray(fill(erase), np.float64))
    for sp, ps in soft:
        e = T.gauss_blur(np.asarray(fill(ps), np.float64), sp * blur_scale)
        box = box * (1.0 - np.clip(e, 0.0, 1.0))
    if ink:
        box = np.maximum(box, np.asarray(fill(ink), np.float64))
    return box''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
