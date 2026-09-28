p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_trace.py"
s = open(p, encoding="utf-8").read()
s = s.replace('PB_TRACE_VERSION = "2.1.0"', 'PB_TRACE_VERSION = "2.2.0"')
s = s.replace("from . import trace as T\n", "from . import trace as T\nfrom . import paperbomb_finefit as FF\n", 1)
s = s.replace('''def trace_all(source: str | None = None,''', '''KNOCKOUT_DERIVED = ("knock-out: a {kind} of paper erased from the traced red, fitted by "
                    "analysis by synthesis (props_lib.paperbomb_finefit {ver}): rendered "
                    "through the source PSF at full-strength density and moved (pattern "
                    "search) until it reproduces the observed red in its window; start "
                    "point from the reference's own paper deficit; replaces {n} traced "
                    "hole(s) the half-level contour had cut there")


def apply_knockouts(L: Layers, group: str, layer: str, curves: list) -> tuple:
    """Fit this group's sub-pixel knock-outs (paperbomb_finefit.KNOCKOUTS).  Returns the
    curves with the replaced traced holes dropped, the erase polygons (source px) and
    the JSON records."""
    specs = [k for k in FF.KNOCKOUTS if k["group"] == group and k["layer"] == layer]
    if not specs or not curves:
        return curves, [], []
    fit = L.fit
    samples = [c.sample(0.05) for c in curves]
    areas = [T.signed_area(q) for q in samples]
    sgn = float(np.sign(areas[int(np.argmax(np.abs(areas)))]))
    drop = set()
    count = {}
    for spec in specs:
        x0, y0, x1, y1 = FF.window_mm(spec)
        n = 0
        for i, (q, a) in enumerate(zip(samples, areas)):
            cx, cy = fit.px_to_mm(*q.mean(0))
            if (np.sign(a) != sgn and abs(a) / fit.ppmm ** 2 < FF.MAX_REPLACED_HOLE_MM2
                    and x0 <= cx <= x1 and y0 <= cy <= y1):
                drop.add(i)
                n += 1
        count[spec["name"]] = n
    kept = [c for i, c in enumerate(curves) if i not in drop]
    base = [c.sample(0.05) for c in kept]
    obs = layer_field(L, layer, behind=True)
    erase, recs = [], []
    for spec in specs:
        r = FF.fit_knockout(spec, base, obs, L.density[layer], fit)
        erase += r["polys_px"]
        mm = []
        for q in r["polys_px"]:
            x, y = fit.px_to_mm(q[:, 0], q[:, 1])
            mm.append(np.round(np.stack([x, y], 1), 5).tolist())
        recs.append({"name": spec["name"], "kind": spec["kind"],
                     "window_mm": [round(v, 3) for v in FF.window_mm(spec)],
                     "params_px": r["params_px"],
                     "loss": {"holes_removed": r["loss_traced_holes_removed"],
                              "init": r["loss_init"], "fit": r["loss_fit"]},
                     "replaced_traced_holes": count[spec["name"]],
                     "derived": KNOCKOUT_DERIVED.format(kind=spec["kind"], ver=FF.FINEFIT_VERSION,
                                                        n=count[spec["name"]]),
                     "polys_mm": mm})
    return kept, erase, recs


def trace_all(source: str | None = None,''')
old = '''        else:
            curves, info = trace_contour(L, layer, region, refine=refine, **kw)
            entry["curves_mm"] = [c.to_json() for c in _curves_px_to_mm(curves, fit)]'''
new = '''        else:
            curves, info = trace_contour(L, layer, region, refine=refine, **kw)
            curves, erase, ko = apply_knockouts(L, g, layer, curves)
            erase_by_layer[layer] += erase
            entry["curves_mm"] = [c.to_json() for c in _curves_px_to_mm(curves, fit)]
            if ko:
                entry["knockouts_mm"] = ko'''
assert old in s
s = s.replace(old, new)
s = s.replace('''    polys_by_layer = {"black": [], "red": []}
    kw = dict(variant or {})''', '''    polys_by_layer = {"black": [], "red": []}
    erase_by_layer = {"black": [], "red": []}
    kw = dict(variant or {})''')
old = '''            for side in ("L", "R", "T", "B"):
                r = trace_rule(L, layer, side, region)'''
new = '''            # THE BLACK RULE RUNS OUT DRY.  The black middle of the top rule thins and
            # greys out past its half-strength end (a 0.1 mm hair of ink reads ~0.35 at
            # the source's grid) and then lifts; a stroke limited to the half-strength
            # component's region stopped where the ink first fell under half, and the
            # grey run beyond was left to the residual (a bristle splay) and to the paper
            # (grey dashes).  The black stroke integrates the whole rule band instead,
            # clear of every other group's black ink, so its width runs down to a hair
            # exactly as the reference thins, and it lifts only where the reference lifts.
            sregion = region
            if layer == "black":
                others = np.zeros_like(region)
                for (g2, l2), m2 in masks.items():
                    if l2 == "black" and g2 != FRAME:
                        others |= m2
                sregion = region | (stroke_zone(L) & ~T.dilate(others, 2))
            for side in ("L", "R", "T", "B"):
                r = trace_rule(L, layer, side, sregion)'''
assert old in s
s = s.replace(old, new)
old = '''        box = T.fill_polys(polys_by_layer[layer], H, W, ss=16).astype(np.float64)
        pred[layer] = {"box": box,'''
new = '''        box = T.fill_polys(polys_by_layer[layer], H, W, ss=16).astype(np.float64)
        if erase_by_layer[layer]:
            box = box * (1.0 - T.fill_polys(erase_by_layer[layer], H, W, ss=16))
        pred[layer] = {"box": box,'''
assert old in s
s = s.replace(old, new)
old = '''    fields = {"pred": pred, "obs": obs, "element_regions": eregs, "masks": masks,
              "polys_by_layer": polys_by_layer}'''
assert old in s
s = s.replace(old, '''    fields = {"pred": pred, "obs": obs, "element_regions": eregs, "masks": masks,
              "polys_by_layer": polys_by_layer, "erase_by_layer": erase_by_layer}''')
old = '''                   "rule_stroke_half_mm": RULE_STROKE_HALF_MM,'''
assert old in s
s = s.replace(old, '''                   "rule_stroke_half_mm": RULE_STROKE_HALF_MM,
                   "black_rule_stroke_region": "rule band minus other groups' black ink",
                   "finefit": FF.FINEFIT_VERSION,''')
s = s.replace('''def rasterise_mm(''', '''def knockout_polys_mm(entry: dict) -> list:
    """The group's fitted knock-outs (card mm): paper ERASED from its traced ink,
    coverage = traced x (1 - erase)."""
    out = []
    for k in entry.get("knockouts_mm", []):
        out += [np.asarray(q, np.float64) for q in k["polys_mm"]]
    return out


def stroke_only_polys_mm(entry: dict) -> list:
    """Only the stroke part of a group (the rules), card mm."""
    polys = []
    for r in entry.get("strokes_mm", []):
        c = np.asarray(r["centre_mm"], np.float64)
        w = np.asarray(r["width_mm"], np.float64)
        ps = stroke_polys(c, w, RULE_GAP_WIDTH_PX / 3.917 * 0.999)
        polys += _orient(ps, r.get("winding", 1.0))
    return polys


def contour_only_polys_mm(entry: dict, step_mm: float = 0.01) -> list:
    """Only the contour part of a group, card mm."""
    polys = []
    for cj in entry.get("curves_mm", []):
        c = T.Curve([np.asarray(q, np.float64) for q in cj["pieces"]], bool(cj["periodic"]))
        polys.append(c.sample(step_mm))
    return polys


def rasterise_mm(''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
