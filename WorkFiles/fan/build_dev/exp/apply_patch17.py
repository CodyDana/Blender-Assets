p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
a = s.index("def rib_outline(")
b = s.index("def _to_fan(")
new = '''def rib_outline(spec: FanSpec, i: int, plan: LodPlan, widen_minus: Optional[callable] = None,
                widen_plus: Optional[callable] = None) -> np.ndarray:
    """Inner rib i (1..24) in its own frame; widen_minus / widen_plus (x) -> extra half-width on the -y / +y side
    (rib 1 and rib 24 reach under their guards so no daylight shows between a guard and its neighbour)."""
    butt = spec.butt_mm
    r_end = spec.r_in - spec.rib_end_gap_mm
    hw0 = 0.5 * spec.rib_width_mm(0.0)
    em = widen_minus or (lambda x: 0.0)
    ep = widen_plus or (lambda x: 0.0)
    if plan.rib_box:
        hw_top = 0.5 * spec.rib_width_mm(r_end)
        return np.array([[-butt + 0.3 * hw0, -hw0], [r_end - 0.5, -hw_top - em(r_end - 2.0)],
                         [r_end - 0.5, hw_top + ep(r_end - 2.0)], [-butt + 0.3 * hw0, hw0]])
    cx = -butt + hw0
    xs = [cx, 0.0, r_end - 1.0]
    if widen_minus is not None or widen_plus is not None:
        xs = [cx, 0.0] + list(np.linspace(35.0, r_end - 1.0, 5))
    minus = [np.array([x, -(0.5 * spec.rib_width_mm(x) + em(x))]) for x in xs]
    plus = [np.array([x, 0.5 * spec.rib_width_mm(x) + ep(x)]) for x in xs]
    # top: an arc r = r_end between the two sides (the shoulders are filleted below)
    yl, yr = minus[-1][1], plus[-1][1]
    a0, a1 = math.asin(max(-0.99, yl / r_end)), math.asin(min(0.99, yr / r_end))
    top = [np.array([r_end * math.cos(t), r_end * math.sin(t)]) for t in np.linspace(a0, a1, plan.top_seg + 2)]
    pts = list(minus)
    k_sh0 = len(pts)
    pts += top
    k_sh1 = len(pts) - 1
    pts += plus[::-1]
    # butt semicircle (from +y back round to -y)
    for t in np.linspace(0.5 * math.pi, 1.5 * math.pi, plan.butt_seg + 2)[1:-1]:
        pts.append(np.array([cx + hw0 * math.cos(t), hw0 * math.sin(t)]))
    poly = np.array(pts)
    # the two side points at x = cx coincide with the semicircle's ends: drop exact duplicates
    keep = [0] + [k for k in range(1, len(poly)) if np.linalg.norm(poly[k] - poly[k - 1]) > 1e-6]
    poly = poly[keep]
    if np.linalg.norm(poly[0] - poly[-1]) < 1e-6:
        poly = poly[:-1]
    if plan.shoulder_seg > 0:
        poly = fillet(poly, {k_sh0: (spec.rib_shoulder_r_mm, plan.shoulder_seg),
                             k_sh1: (spec.rib_shoulder_r_mm, plan.shoulder_seg)})
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return poly


'''
s = s[:a] + new + s[b:]
# rear widening
a = s.index("def rib1_widening(spec: FanSpec):")
b = s.index("# =========================================================================== stick solids")
new2 = '''def _widening(spec: FanSpec, inner_edge: callable, sep_deg: float):
    """Extra half-width a rib needs toward a guard sep_deg away so that it reaches 0.3 mm under the guard's
    inner edge (``inner_edge(x_guard)`` = that edge's distance from the guard's axis) in the bare zone."""
    a1 = sep_deg * D2R
    xx = np.linspace(20.0, spec.r_in, 60)
    ex = []
    for x in xx:
        xg = x * math.cos(a1)
        need = (x * math.sin(a1) - (inner_edge(xg) - 0.3)) / math.cos(a1)
        ex.append(max(0.0, need - 0.5 * spec.rib_width_mm(x)))
    ex = np.array(ex)
    return lambda x: float(np.interp(x, xx, ex))


def rib1_widening(spec: FanSpec):
    """rib 1 toward the front guard (its inner edge: front_guard_edges)."""
    xs = np.linspace(0.0, spec.r_in, 80)
    _, yi = front_guard_edges(spec, xs)
    return _widening(spec, lambda xg: float(np.interp(xg, xs, yi)), spec.stick_axis_deg(1, 1.0))


def rib24_widening(spec: FanSpec):
    """rib 24 toward the rear guard (symmetric about its axis: inner edge at half its width)."""
    n = spec.n_sticks - 1
    sep = spec.stick_axis_deg(n, 1.0) - spec.stick_axis_deg(n - 1, 1.0)
    return _widening(spec, lambda xg: 0.5 * spec.guard_width_mm(xg), sep)


'''
s = s[:a] + new2 + s[b:]
old = '''    widen = rib1_widening(spec)'''
assert old in s
s = s.replace(old, '''    widen = rib1_widening(spec)
    widen24 = rib24_widening(spec)''')
old = '''            outlines[i] = rib_outline(spec, i, plan, widen if i == 1 else None)'''
assert old in s
s = s.replace(old, '''            outlines[i] = rib_outline(spec, i, plan, widen if i == 1 else None,
                                      widen24 if i == spec.n_sticks - 2 else None)''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_spec.py"
s = open(p, encoding="utf-8").read()
old = '''    rib_end_gap_mm: float = 0.40       # the bare rib stops this far inside the leaf's inner edge
    rib_shoulder_r_mm: float = 1.6    # rounded shoulders (RS 4, 0.415 - 0.431 L)'''
assert old in s
s = s.replace(old, '''    #: the bare rib stops this far inside the leaf's inner edge: a closing pleat's inner corner comes in to
    #: r_in x cos(gamma) (gamma <= face angle, 3.4 deg) = r_in - 0.15 mm; 0.18 keeps clear and shows no daylight
    rib_end_gap_mm: float = 0.18
    rib_shoulder_r_mm: float = 0.6    # rounded shoulders (RS 4); small, so no daylight shows between shoulders''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_refview.py"
s = open(p, encoding="utf-8").read()
a = s.index("REF_LIGHTS = [")
b = s.index("REF_WORLD = 0.35")
s = s[:a] + '''REF_LIGHTS = [
    # fitted on RS 7 / RS 9's tones (leaf p10/p50/p90, bare ribs, lobe; WorkFiles/fan/build_dev/exp/tune_light.py):
    # a big soft key above the camera, a faint front fill, a near-black studio (the camera side reflects dark)
    ("Key", (0.0, -0.4, 1.0), 3.0, 3.2, (1.0, 1.0, 1.0)),
    ("Fill", (0.0, -1.0, 0.2), 3.0, 0.12, (1.0, 1.0, 1.0)),
]
''' + s[b:]
s = s.replace("REF_WORLD = 0.35", "REF_WORLD = 0.03")
open(p, "w", encoding="utf-8").write(s)
print("ok")
