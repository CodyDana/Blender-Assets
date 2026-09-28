"""Finalise patch, iteration 2: UV mirroring fixes, pin head offset, wear tuning."""
from pathlib import Path

G = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_geom.py")
s = G.read_text(encoding="utf-8")
rep = [
    ('''            uvs = [(k * 2 * (r_div + 3.0) + (side > 0) * (r_div + 3.0) + r, z) for r, z in c]''',
     '''            # the two faces look opposite ways: mirror u on one so neither is a mirrored UV triangle
            uvs = [(k * 2 * (r_div + 3.0) + (side > 0) * (r_div + 3.0) + (r if side > 0 else r_div - r), z)
                   for r, z in c]'''),
    ('''            u0 = wk * 6.0
            mb.f([v0, v1, va], [(u0, 0.0), (u0, spec.notch_foot_z), (u0 + 3.3, spec.cap_side_z0)],
                 "cap_notch_walls", "cap", LOOK_STEEL, hint=hint, density=DENSITY["cap_end"])''',
     '''            u0 = wk * 6.0
            ua, ub = (u0, u0 + 3.3) if right else (u0 + 3.3, u0)          # never mirrored
            mb.f([v0, v1, va], [(ua, 0.0), (ua, spec.notch_foot_z), (ub, spec.cap_side_z0)],
                 "cap_foot_walls", "cap", LOOK_STEEL, hint=hint, density=DENSITY["cap_end"])'''),
    ('''    cylinder(mb, (px, 0.0, pz), "y", s.pin_head_r, y_head0, y_head0 - s.pin_head_len, max(8, q.small_segs),
             "pin_head", "pin", LOOK_RING)''',
     '''    cylinder(mb, (px, 0.0, pz), "y", s.pin_head_r, y_head0 - 0.05, y_head0 - s.pin_head_len, max(8, q.small_segs),
             "pin_head", "pin", LOOK_RING)'''),
]
for a, b in rep:
    assert a in s, a[:80]
    s = s.replace(a, b)
G.write_text(s, encoding="utf-8")

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_paint.py")
s = P.read_text(encoding="utf-8")
rep = [
    ("    paint_light: float = 0.55          # lighter worn / dusty patches (the reference's p90 101-116)",
     "    paint_light: float = 0.85          # lighter worn / dusty patches (the reference's p90 101-116)"),
    ("    paint_grime: float = 0.62          # dark grime blotches (p10 40-44)",
     "    paint_grime: float = 0.55          # dark grime blotches (p10 40-44)"),
    ("    paint_rough: float = 0.52", "    paint_rough: float = 0.46"),
    ('''        if lk in (1, 4, 5):
            scr = strokes(p[m], n[m], 2.6, 0.55, (1.5, 7.0), 0.05, sd + 300 + lk)
            wear = np.maximum(wear, 0.8 * scr)
            wear = np.maximum(wear, 0.7 * (n_speck[m] > 0.965))''',
     '''        if lk in (1, 4, 5):
            # fine, short, dense scratch marks (the reference's antiqued steel), then bright bronze specks
            scr = strokes(p[m], n[m], 1.3, 0.6, (0.5, 2.6), 0.03, sd + 300 + lk)
            wear = np.maximum(wear, 0.5 * scr * (0.5 + n_mid[m]))
            wear = np.maximum(wear, 0.6 * (n_speck[m] > 0.955))'''),
    ('''    m = (L == 4)
    if m.any():
        y_, z_ = p[m, 1], p[m, 2]''',
     '''    m = (L == 4) & (np.abs(n[:, 1]) < 0.5)            # the web faces only (the flanges face +-Y)
    if m.any():
        y_, z_ = p[m, 1], p[m, 2]'''),
    ('''        alb[m] = alb[m] * (1 - 0.45 * hat[:, None]) + ecol * 0.45 * hat[:, None]''',
     '''        alb[m] = alb[m] * (1 - 0.35 * hat[:, None]) + ecol * 0.35 * hat[:, None]'''),
    ('''        alb[sel] *= (1.0 - 0.5 * g[sel] + 0.22 * lip[sel] * (~chip[sel]))[:, None]''',
     '''        alb[sel] *= (1.0 - 0.3 * g[sel] + 0.22 * lip[sel] * (~chip[sel]))[:, None]'''),
]
for a, b in rep:
    assert a in s, a[:80]
    s = s.replace(a, b)
P.write_text(s, encoding="utf-8")
print("iter2 patched")
