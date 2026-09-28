# sm_m16b: same trade-off using the design-sheet blade outline (its stronger taper), back-edge sweep capped at s
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"]); TOP = s01["top"]
half_px = body_half_table(prof)
s12 = json.load(open(os.path.join(HERE, "sm_s12.json")))
rev3 = np.array(s12["sheet"])  # sheet-faithful widths
def solve(bl, y_end, WALL, CLR):
    Lb = bl[-1, 0] + 0.005; k = Lb / (y_end - TOP); zs = bl[:, 0]
    inner = np.array([half_px[int(round(TOP + z / k))] * k for z in zs]) - WALL - CLR
    lo = bl[:, 2] - inner; hi = bl[:, 1] + inner
    best = None
    for z0f in np.linspace(0.3, 0.9, 31):
        z0 = z0f * Lb; s = np.clip((zs - z0) / (Lb - z0), 0, None) ** 2
        for d0 in np.linspace(-0.01, 0.012, 111):
            b = s == 0
            if np.any((d0 < lo[b]) | (d0 > hi[b])): continue
            m = s > 0
            Amin = np.max((lo[m] - d0) / s[m]); Amax = np.min((hi[m] - d0) / s[m])
            if Amin > Amax: continue
            A = 0.0 if Amin <= 0 <= Amax else (Amin if Amin > 0 else Amax)
            # margin with this A: distance to band edges
            d = d0 + A * s
            marg = np.minimum(d - lo, hi - d).min()
            cand = (abs(A), -marg, A, d0, z0f, marg)
            if best is None or cand < best: best = cand
    return k, best
out = {}
WALL, CLR = 0.0025, 0.001
for sweep_mm in (0, 2, 4, 6, 8, 12, 19.8):
    bl = rev3.copy()
    cap = 0.0251 + sweep_mm / 1000.0
    bl[:, 2] = np.minimum(bl[:, 2], cap); bl[:, 1] = np.minimum(bl[:, 1], bl[:, 2])
    for y_end in (1380, 1400, 1420):
        k, b = solve(bl, y_end, WALL, CLR)
        key = f"sweep{sweep_mm}_y{y_end}"
        if b is None:
            print(key, "infeasible"); out[key] = None; continue
        _, _, A, d0, z0f, marg = b
        out[key] = dict(sweep_mm=sweep_mm, y_end=y_end, sheath_len=1466 * k, k_mm_px=k * 1000, bow_mm=A * 1000, bow_ref_px=A / k,
                        cavity_offset_mm=d0 * 1000, bow_start_frac=z0f, bow_start_row=TOP + z0f * (bl[-1, 0] + 0.005) / k, margin_mm=marg * 1000)
        print("tip sweep %4.1f mm | tip rests row %d | sheath %.3f m | bow %5.1f mm = %4.1f ref px from row %4.0f | cavity offset %+.1f mm | margin %.1f mm" % (
            sweep_mm, y_end, 1466 * k, A * 1000, A / k, out[key]["bow_start_row"], d0 * 1000, marg * 1000))
json.dump(out, open(os.path.join(HERE, "sm_s16b.json"), "w"), indent=1)
