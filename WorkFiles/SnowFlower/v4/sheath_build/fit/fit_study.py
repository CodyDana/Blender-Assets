"""Feasibility of holding the FINAL v4 blade in the EXACT reference sheath outline (k = 0.687 mm/px):
straight sheath, the sword seated with a small tilt about Y (Holster socket rotation) and a lateral offset.
static = sheathed pose only; swept = the cavity is the blade swept along its own axis (clean straight draw).
Pure numpy on the analytic v4 blade (sfv4_spec, equals LOD0 within 0.2 mm)."""
import json, sys
import numpy as np
sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import sfv4_spec as S
K = 0.687
BODY = [(169, 97), (250, 97), (286, 97), (322, 96), (340, 96), (400, 95), (500, 92), (600, 90), (700, 88), (800, 85), (900, 83),
        (1000, 79), (1100, 77), (1200, 74), (1250, 72), (1292, 71.5)]
def outer_px(row):
    if row < 169: return 97.0          # throat: the body continues under the fitting (fitting is wider)
    if row <= 1292: return float(np.interp(row, *zip(*BODY)))
    if row <= 1387: return 72 + 12 * min(1.0, (row - 1292) / 52.0)
    return float(np.interp(row, [1387, 1388, 1420, 1440, 1460, 1480, 1496], [84, 68, 60, 50, 38, 21, 3]))
Z_MOUTH = 128.9
zs = np.arange(S.Z_PENDANT_TIP, S.Z_TIP + 0.01, 1.0)
sp, ed = S.spine_x(zs), S.edge_x(zs)
def margins(c0, th_deg, wall, clr, swept):
    th = np.radians(th_deg)
    # sword point (x, z) -> sheath frame: rotate about the mouth point by -th, offset -c0 (sheath axis at x=c0 in sword frame at the mouth)
    def to_s(x, z):
        dx, dz = x, z - Z_MOUTH
        return dx * np.cos(th) - dz * np.sin(th) - c0, dx * np.sin(th) + dz * np.cos(th)
    xs1, zs1 = to_s(sp, zs); xe1, ze1 = to_s(ed, zs)
    if swept:
        # the blade moved back along its own axis by d: points p - d*a; in the sheath frame the axis is (sin th, cos th) in (x,z)
        # for each station z_s, lateral extent = extremes over all blade points below that slid up to z_s
        a = np.array([np.sin(th), np.cos(th)])
        zq = np.arange(0, zs1.max() + 0.01, 2.0)
        hi = np.full(zq.shape, -1e9); lo = np.full(zq.shape, 1e9)
        for X, Z in ((xs1, zs1), (xe1, ze1)):
            for x, z in zip(X, Z):
                m = zq <= z
                xq = x - (z - zq[m]) / a[1] * a[0]
                hi[m] = np.maximum(hi[m], xq); lo[m] = np.minimum(lo[m], xq)
        ok = hi > -1e8
        zq, hi, lo = zq[ok], hi[ok], lo[ok]
    else:
        zq = zs1; hi = np.maximum(xs1, xe1); lo = np.minimum(xs1, xe1)
    rows = 31 + zq / K
    hw = np.array([outer_px(r) * K / 2 for r in rows]) - wall - clr
    m = np.minimum(hw - hi, hw + lo)
    i = int(np.argmin(m))
    return float(m[i]), float(zq[i] + Z_MOUTH)
out = {}
for swept in (False, True):
    for wall, clr in ((2.5, 1.0), (2.0, 0.75), (1.5, 0.75)):
        best = None
        for th in np.arange(0.0, 1.21, 0.05):
            for c0 in np.arange(-6, 6.01, 0.25):
                m, zl = margins(c0, th, wall, clr, swept)
                if best is None or m > best[0]: best = (m, c0, th, zl)
        best0 = max((margins(c0, 0.0, wall, clr, swept) + (c0,) for c0 in np.arange(-6, 6.01, 0.25)), key=lambda t: t[0])
        key = f"{'swept' if swept else 'static'}_wall{wall}_clr{clr}"
        out[key] = {"best_margin_mm": round(best[0], 2), "c0_mm": best[1], "tilt_deg": round(best[2], 2), "limit_z": round(best[3], 1),
                    "no_tilt_margin_mm": round(best0[0], 2), "no_tilt_c0": best0[2]}
        print(key, out[key], flush=True)
json.dump(out, open(r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sheath_build/fit/fit_study.json', 'w'), indent=1)
