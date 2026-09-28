p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_spec.py"
s = open(p, encoding="utf-8").read()
old = '''    rear_flap_past_axis_deg: float = 1.2'''
assert old in s
s = s.replace(old, '''    #: the rear guard's OUTER silhouette is a straight line in fan2 (image line through (60, 508.1) and
    #: (330, 547.8) px, WorkFiles/fan/measure/fan_edge_lines.py), mapped onto the rear guard's plane through RS 1's
    #: camera: (x along the guard mm, lateral mm) - it is wider toward the pivot than the front guard (MEASURED;
    #: RS 5 designed the rear guard as the front one mirrored).  Its visible width stays RS 5's.
    rear_guard_outer_mm: Tuple[Tuple[float, float], ...] = ((37.5, 5.58), (191.2, 3.22))
    rear_flap_past_axis_deg: float = 0.95        # the leaf's corner ends on that silhouette (RS 2: 173.8 deg)''')
open(p, "w", encoding="utf-8").write(s)

p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
old = '''    else:
        W = np.array([spec.guard_width_mm(v) for v in xs])
        yo, yi = -0.5 * W, 0.5 * W                    # rear guard: symmetric (its leaf line is its axis)'''
assert old in s
s = s.replace(old, '''    else:
        yo, yi = rear_guard_edges(spec, xs)           # (inner = -y, outer = +y)''')
old = '''        w_at = lambda x: -0.5 * spec.guard_width_mm(x)'''
assert old in s
s = s.replace(old, '''        w_at = lambda x: float(rear_guard_edges(spec, np.array([x]))[0][0])''')
old = '''def guard_outline(spec: FanSpec, which: str, plan: LodPlan) -> np.ndarray:'''
s = s.replace(old, '''def rear_guard_edges(spec: FanSpec, x: np.ndarray):
    """(y_inner, y_outer) of the rear guard in its own frame (+y = outward, away from the leaf): the outer
    silhouette is fan2's straight line (FanSpec.rear_guard_outer_mm), the inner edge RS 5's visible width in."""
    (x0, y0), (x1, y1) = spec.rear_guard_outer_mm
    yo = y0 + (y1 - y0) * (np.asarray(x, np.float64) - x0) / (x1 - x0)
    W = np.array([spec.guard_width_mm(v) for v in np.atleast_1d(x)])
    return yo - W, yo


def guard_outline(spec: FanSpec, which: str, plan: LodPlan) -> np.ndarray:''')
old = '''def rib24_widening(spec: FanSpec):
    """rib 24 toward the rear guard (symmetric about its axis: inner edge at half its width)."""
    n = spec.n_sticks - 1
    sep = spec.stick_axis_deg(n, 1.0) - spec.stick_axis_deg(n - 1, 1.0)
    return _widening(spec, lambda xg: 0.5 * spec.guard_width_mm(xg), sep)'''
assert old in s
s = s.replace(old, '''def rib24_widening(spec: FanSpec):
    """rib 24 toward the rear guard (its inner edge: rear_guard_edges)."""
    n = spec.n_sticks - 1
    sep = spec.stick_axis_deg(n, 1.0) - spec.stick_axis_deg(n - 1, 1.0)
    return _widening(spec, lambda xg: -float(rear_guard_edges(spec, np.array([xg]))[0][0]), sep)''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
