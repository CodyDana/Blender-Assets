"""Stage 10: test for foreshortening of ray angles: fit phi = roll + atan2(k sin t, cos t), t = t0 + n*Delta to the
rib-band minima and leaf-band light maxima of fan2 (and fan1). k<1 = vertical compression (tilt about horizontal axis)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
E = json.load(open(os.path.join(OUT, "fm_s07_extrema.json")))
def clean(lst, lo, hi, per):
    v = sorted(set(x for x in lst if lo <= x <= hi))
    # keep chain with spacing near per: greedy from first
    out = [v[0]]
    for x in v[1:]:
        if x - out[-1] > 0.7*per: out.append(x)
    return out
sets = {
 '2_ribmin': clean(E['2']['rib']['min_deg'], 10, 173, 6.6),
 '2_leafmax': clean(E['2']['leaf']['max_deg'], 10.5, 168, 6.5),
 '1_ribmin': clean(E['1']['rib']['min_deg'], 16, 163, 4.87),
 '1_leafmax': clean(E['1']['leaf']['max_deg'], 16, 163, 4.87),
}
res = {}
for name, phis in sets.items():
    phis = np.array(phis); per = np.median(np.diff(phis))
    n = np.round((phis - phis[0])/per).astype(int)
    # drop points whose index rounding is ambiguous
    best = None
    for k in np.arange(0.80, 1.201, 0.005):
        for roll in np.arange(-6, 6.01, 0.25):
            # invert: t = atan2(sin(phi-roll)/k, cos(phi-roll))
            pr = np.radians(phis - roll)
            t = np.degrees(np.arctan2(np.sin(pr)/k, np.cos(pr)))
            A = np.c_[np.ones_like(n), n]; sol, *_ = np.linalg.lstsq(A, t, rcond=None)
            rr = t - A @ sol; rms = float(np.sqrt((rr**2).mean()))
            if best is None or rms < best[0]: best = (rms, k, roll, sol)
    # k = 1 reference
    A = np.c_[np.ones_like(n), n]; sol1, *_ = np.linalg.lstsq(A, phis, rcond=None); rms1 = float(np.sqrt(((phis - A@sol1)**2).mean()))
    # local spacing by thirds
    thirds = [float(np.polyfit(n[s], phis[s], 1)[0]) for s in np.array_split(np.arange(len(n)), 3)]
    res[name] = dict(values=[round(float(x), 1) for x in phis], index=n.tolist(), count=len(phis),
                     linear=dict(t0=round(float(sol1[0]), 2), step=round(float(sol1[1]), 3), rms=round(rms1, 3)),
                     spacing_by_thirds=[round(x, 3) for x in thirds],
                     best_k=dict(k=round(float(best[1]), 3), roll=float(best[2]), t0=round(float(best[3][0]), 2), step=round(float(best[3][1]), 3), rms=round(best[0], 3)))
json.dump(res, open(os.path.join(OUT, "fm_s10_spacingfit.json"), "w"), indent=1)
print("FMRES", json.dumps(res))
