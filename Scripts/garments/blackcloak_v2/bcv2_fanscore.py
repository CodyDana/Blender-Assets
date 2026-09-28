"""BlackCloak_MH_v2 builder helper: fold-fan proxy on a drape preview (copy of the arc detector of
WorkFiles/BlackCloak_MH_v2/spec/scripts/v2m_jin_score.py, which stays the measurer's tool; v2m_lib is imported read-only).

fan_score(lum, mask, cx, cy, px_per_m) -> {"r0.35m": {...}, "r0.55m": {...}} with the same sectors as v2m_jin_score
('cross' -50..10 deg, 'fan' 15..120 deg; 0 = image right = HIS LEFT, 90 = down)."""
import os
import sys
import numpy as np

_V2M = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/scripts"
if _V2M not in sys.path:
    sys.path.append(_V2M)
import v2m_lib as L  # noqa: E402


def arc_profile(lum, mask, cx, cy, r):
    angs = np.arange(-60.0, 125.0001, 0.1)
    t = np.radians(angs); xs = cx + r * np.cos(t); ys = cy + r * np.sin(t)
    v = L.bilinear(lum, xs, ys, np.nan)
    inside = L.bilinear(mask.astype(float), xs, ys, 0.0) > 0.5
    return angs, v, inside


def crossings(angs, v, inside, step=0.1):
    k = int(6 / step) | 1
    vv = np.where(inside, v, np.nan)
    ok = ~np.isnan(vv)
    if ok.sum() < 20:
        return []
    filled = np.interp(np.arange(len(vv)), np.nonzero(ok)[0], vv[ok])
    hp = filled - L.smooth1d(filled, k)
    sm = L.smooth1d(hp, 5)
    win = int(4 / step)
    loc_std = np.array([np.std(sm[max(0, i - 60):i + 60]) for i in range(len(sm))])
    out = []
    for i in range(win, len(sm) - win):
        if not inside[i]:
            continue
        if sm[i] == sm[i - 3:i + 4].min() and sm[i] < sm[i - 1] and sm[i] <= sm[i + 1]:
            left = sm[i - win:i].max(); right = sm[i + 1:i + 1 + win].max()
            depth = min(left, right) - sm[i]
            if depth >= max(1.2 * loc_std[i], 2.0):
                if out and angs[i] - out[-1] < 1.5:
                    continue
                out.append(float(angs[i]))
    return out


def fan_score(lum, mask, cx, cy, px_per_m):
    k = max(3, int(round(0.012 * px_per_m)) | 1)
    lb = L.blur2d(lum, k)
    res = {}
    for rm in (0.35, 0.55):
        sets = []
        for dr in (-0.02, 0.0, 0.02):
            angs, v, ins = arc_profile(lb, mask, cx, cy, (rm + dr) * px_per_m)
            sets.append((crossings(angs, v, ins), ins))
        mid = sets[1][0]
        cr = [c for c in mid if sum(any(abs(c - o) <= 2.5 for o in sets[j][0]) for j in (0, 2)) >= 1]
        fan = [c for c in cr if 15 <= c <= 120]
        res["r%.2fm" % rm] = {"crossings_deg": [round(c, 1) for c in cr], "cross_-50_10": sum(-50 <= c <= 10 for c in cr),
                              "fan_15_120": len(fan), "fan_spread_deg": (max(fan) - min(fan)) if fan else 0.0}
    return res
