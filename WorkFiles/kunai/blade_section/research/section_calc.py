"""Section ratios and blade-steel volume for the current kunai section and option C candidates.
Mirrors kunai_spec.h_blade / ridge_blade / z_blade_face (read-only copy of the formulas; grind removal ignored)."""
import math
def h(x):
    if x <= 35: return 8 + 10 * x / 35
    u = (x - 35) / 105; return 18 * (1 - u) * (1 + 0.25 * u)
def ridge(x, b, t, tat=135.0):
    if x <= 35: return b
    return max(t, b + (t - b) * (x - 35) / (tat - 35))
def vol(T0, T1, edge):
    n = 14000; s = 0
    for i in range(n):
        x = (i + 0.5) * 140 / n
        s += h(x) * (edge + ridge(x, T0, T1)) * 140 / n   # area of the section = 2h * (edge + T)/2
    return s
cur = vol(5, 1.6, 1.5)
print("blade plan area mm2", round(sum(2 * h((i + .5) * 0.01) * 0.01 for i in range(14000))))
print("current blade vol mm3", round(cur), "steel g", round(cur * 7.85e-3, 1))
for T0, T1, e in [(6, 1.6, 0), (6.35, 1.6, 0), (7, 1.6, 0), (7, 2.0, 0), (8, 2.0, 0), (7, 1.6, 1.5)]:
    v = vol(T0, T1, e)
    print(f"ridge {T0}->{T1} edge {e}: vol {round(v)} mm3, {v*7.85e-3:.1f} g, delta {(v-cur)*7.85e-3:+.1f} g")
print("stations (fraction of 140 mm blade from shoulder)")
for f in [0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9]:
    x = 140 * f; hh = h(x)
    for name, (b, t, e) in {"current": (5, 1.6, 1.5), "C 7->1.6 full": (7, 1.6, 0), "C 6->1.6 full": (6, 1.6, 0), "C 8->2.0 full": (8, 2.0, 0)}.items():
        T = ridge(x, b, t); rr = (T / 2) / hh; fs = (T / 2 - e / 2) / hh
        print(f"{f:.2f} x={x:6.1f} hw={hh:5.2f} {name:14s} T={T:4.2f} ridge_ratio={rr:.3f} face_slope={fs:.3f} ({math.degrees(math.atan(fs)):.1f} deg)")
