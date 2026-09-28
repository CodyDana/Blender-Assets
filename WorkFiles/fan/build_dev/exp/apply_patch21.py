p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert old in s, old[:90]
    s = s.replace(old, new, 1)
# ---- rib slip: back to the previous leaf line
rep('''    if plan.rib_box:
        hw_top = 0.5 * spec.rib_width_mm(r_end)
        r_s = spec.r_in + spec.rib_slip_past_leaf_mm
        return np.array([[-butt + 0.3 * hw0, -hw0], [r_s - 0.3, -hw_top - em(r_end - 2.0)], [r_s - 0.3, -0.3],
                         [r_end - 0.5, -0.3], [r_end - 0.5, hw_top + ep(r_end - 2.0)], [-butt + 0.3 * hw0, hw0]])''',
'''    o = spec.leaf_line_offset_deg(i) * D2R
    a = spec.leaf_pitch_deg * D2R

    def polar(r, t):
        return np.array([r * math.cos(t), r * math.sin(t)])
    if plan.rib_box:
        hw_top = 0.5 * spec.rib_width_mm(r_end)
        r_s = spec.r_in + spec.rib_slip_past_leaf_mm
        return np.array([[-butt + 0.3 * hw0, -hw0], [r_end - 0.5, -hw_top - em(r_end - 2.0)],
                         polar(r_end - 0.4, o - a + 0.3 / r_end), polar(r_s, o - a + 0.3 / r_end),
                         polar(r_s, o - 0.3 / r_end), polar(r_end - 0.5, o - 0.3 / r_end),
                         [r_end - 0.5, hw_top + ep(r_end - 2.0)], [-butt + 0.3 * hw0, hw0]])''')
rep('''    if r_slip is not None:
        pts[-1] = np.array([r_slip - 1.0, yl])
        a0 = math.asin(max(-0.99, yl / r_slip))
        ys = -0.3
        top = [np.array([r_slip * math.cos(t), r_slip * math.sin(t)])
               for t in np.linspace(a0, math.asin(ys / r_slip), 2)]
        k_sh0 = len(pts)
        pts += top
        pts.append(np.array([math.sqrt(r_end ** 2 - ys ** 2), ys]))
        a1 = math.asin(min(0.99, yr / r_end))
        top2 = [np.array([r_end * math.cos(t), r_end * math.sin(t)])
                for t in np.linspace(math.asin(ys / r_end), a1, max(2, plan.top_seg + 1))][1:]
        pts += top2
        k_sh1 = len(pts) - 1''', '''    if r_slip is not None:
        # the SLIP: behind the leaf, from 0.3 mm short of this rib's leaf line back to 0.3 mm short of the
        # previous one, out to r_slip.  The closed pages all lie on the +y side of the leaf lines, so it never
        # meets them; open, it hides the daylight under the pleats' raised inner corners.  Below the leaf edge its
        # wide part lies behind the neighbouring rib (stacked in front)
        e1 = 0.3 / r_end
        pts[-1] = np.array([r_end - 0.3, yl])
        pts.append(polar(r_end - 0.2, o - a + e1))
        k_sh0 = None
        pts.append(polar(r_slip, o - a + e1))
        pts.append(polar(r_slip, o - e1))
        pts.append(polar(r_end, o - e1))
        a1 = math.asin(min(0.99, yr / r_end))
        top2 = [polar(r_end, t) for t in np.linspace(o - e1, a1, max(2, plan.top_seg + 1))][1:]
        pts += top2
        k_sh1 = len(pts) - 1''')
rep('''    if plan.shoulder_seg > 0:
        poly = fillet(poly, {k_sh0: (spec.rib_shoulder_r_mm, plan.shoulder_seg),
                             k_sh1: (spec.rib_shoulder_r_mm, plan.shoulder_seg)})
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return poly


def _to_fan(''', '''    if plan.shoulder_seg > 0:
        corners = {k_sh1: (spec.rib_shoulder_r_mm, plan.shoulder_seg)}
        if k_sh0 is not None:
            corners[k_sh0] = (spec.rib_shoulder_r_mm, plan.shoulder_seg)
        poly = fillet(poly, corners)
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    return poly


def _to_fan(''')
# ---- rear guard tab
rep('''    else:
        W = np.array([spec.guard_width_mm(v) for v in xs])
        yo, yi = -0.5 * W, 0.5 * W                    # rear guard: symmetric (its leaf line is its axis)''', '''    else:
        W = np.array([spec.guard_width_mm(v) for v in xs])
        yo, yi = -0.5 * W, 0.5 * W                    # rear guard: symmetric (its leaf line is its axis)''')
rep('''    poly = [np.array([x, y]) for x, y in zip(xs, yo)] + tip + [np.array([x, y]) for x, y in zip(xs[::-1], yi[::-1])]''',
    '''    outer = [np.array([x, y]) for x, y in zip(xs, yo)]
    if which == "rear" and plan.lod <= 2:
        # the rear guard's slip tab (see rib_outline): behind the leaf, back to 0.3 mm short of rib 24's leaf line
        r_end = spec.r_in - spec.rib_end_gap_mm
        r_slip = spec.r_in + spec.rib_slip_past_leaf_mm
        a = spec.leaf_pitch_deg * D2R
        e1 = 0.3 / r_end
        w_at = lambda x: -0.5 * spec.guard_width_mm(x)
        keep = [p for p in outer if p[0] < r_end - 0.4 or p[0] > r_slip + 0.4]
        before = [p for p in keep if p[0] < r_end - 0.4]
        after = [p for p in keep if p[0] > r_slip + 0.4]
        tab = [np.array([r_end - 0.2, w_at(r_end - 0.2)]),
               np.array([(r_end - 0.2) * math.cos(-a + e1), (r_end - 0.2) * math.sin(-a + e1)]),
               np.array([r_slip * math.cos(-a + e1), r_slip * math.sin(-a + e1)]),
               np.array([r_slip, w_at(r_slip)])]
        outer = before + tab + after
    poly = outer + tip + [np.array([x, y]) for x, y in zip(xs[::-1], yi[::-1])]''')
rep('''    k_tip0, k_tip1 = len(xs), len(xs) + 1''', '''    k_tip0, k_tip1 = len(outer), len(outer) + 1''')
open(p, "w", encoding="utf-8").write(s)
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_spec.py"
s = open(p, encoding="utf-8").read()
s = s.replace("    hinge_margin_mm: float = 0.2\n", "    hinge_margin_mm: float = 0.03   # the guard's inner edge stops this far short of the leaf line\n")
open(p, "w", encoding="utf-8").write(s)
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/build_fan.py"
s = open(p, encoding="utf-8").read()
s = s.replace("rounded=(K <= 1) & (S > 0) & (S < spec.n_sticks - 1)),", "rounded=(K <= 1) & (S > 0) & (S < spec.n_sticks - 1), edge_band_mm=2.5, edge_drop_mm=0.12),")
open(p, "w", encoding="utf-8").write(s)
print("ok")
