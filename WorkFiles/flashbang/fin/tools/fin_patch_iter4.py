"""Finalise patch, iteration 4: paint light patches smaller, ring lines read as bright-edged engraved lines, the
sleeve chamfer keeps more paint."""
from pathlib import Path

P = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_paint.py")
s = P.read_text(encoding="utf-8")
rep = [
    ("    paint_light: float = 0.85          # lighter worn / dusty patches (the reference's p90 101-116)",
     "    paint_light: float = 0.45          # lighter worn scuffs 1-4 mm (the reference's p90 101-116)"),
    ("    n_light = fbm(p, 6.0, 3, sd + 22)             # FINALISE: lighter worn / dusty paint patches",
     "    n_light = fbm(p, 2.8, 3, sd + 22)             # FINALISE: lighter worn paint scuffs"),
    ("        zone += 0.40 * np.exp(-((z - zl) / 0.30) ** 2) * on_body",
     "        zone += 0.75 * np.exp(-((z - zl) / 0.35) ** 2) * on_body          # chips run along the engraved line"),
    ("    zone += 0.22 * smoothstep(spec.sleeve_z1 - 0.3, spec.sleeve_z1 + 0.8, z) * on_sleeve",
     "    zone += 0.10 * smoothstep(spec.sleeve_z1 - 0.3, spec.sleeve_z1 + 0.8, z) * on_sleeve"),
    ("    lumf *= 1.0 + look.paint_light * smoothstep(0.56, 0.80, n_light) * (1.0 - blot)",
     "    lumf *= 1.0 + look.paint_light * smoothstep(0.58, 0.78, n_light) * (1.0 - blot)"),
    ('''        alb[sel] *= (1.0 - 0.3 * g[sel] + 0.22 * lip[sel] * (~chip[sel]))[:, None]''',
     '''        alb[sel] *= (1.0 - 0.15 * g[sel] + 0.30 * lip[sel] * (~chip[sel]))[:, None]'''),
]
for a, b in rep:
    assert a in s, a[:80]
    s = s.replace(a, b)
P.write_text(s, encoding="utf-8")
print("iter4 patched")
