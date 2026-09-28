# sm_m13: minimal sheath bow (lower-part curve) that holds each blade statically, per tip-rest station
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"]); TOP = s01["top"]
half_px = body_half_table(prof)
s12 = json.load(open(os.path.join(HERE, "sm_s12.json")))
blades = {"rev3": np.array(s12["rev3"]), "sheet": np.array(s12["sheet"])}
nb = blades["rev3"].copy(); nb[:, 2] = np.minimum(nb[:, 2], 0.0230); nb[-1, 1] = min(nb[-1, 1], 0.0230); blades["rev3_backedge_straight"] = nb
out = {}
for WALL, CLR in ((0.003, 0.0015), (0.0025, 0.001)):
    for name, bl in blades.items():
        for y_end in (1250, 1300, 1350, 1380, 1400, 1420, 1440, 1460):
            Lb = bl[-1, 0] + 0.005
            k = Lb / (y_end - TOP)
            zs = bl[:, 0]
            inner = np.array([half_px[int(round(TOP + z / k))] * k for z in zs]) - WALL - CLR
            lo = bl[:, 2] - inner   # d must be >= lo
            hi = bl[:, 1] + inner   # d must be <= hi
            best = None
            for z0f in np.linspace(0.3, 0.9, 25):
                z0 = z0f * Lb
                s = np.clip((zs - z0) / (Lb - z0), 0, None) ** 2
                for d0 in np.linspace(-0.01, 0.015, 101):
                    # need lo <= d0 + A s <= hi  for all  -> A range
                    base_ok = (s == 0)
                    if np.any((d0 < lo[base_ok]) | (d0 > hi[base_ok])):
                        continue
                    m = s > 0
                    Amin = np.max((lo[m] - d0) / s[m]); Amax = np.min((hi[m] - d0) / s[m])
                    if Amin <= Amax:
                        A = max(Amin, 0.0) if Amax >= 0 else Amin
                        # choose the smallest |A| in the feasible interval
                        A = 0.0 if Amin <= 0 <= Amax else (Amin if Amin > 0 else Amax)
                        if best is None or abs(A) < abs(best[0]):
                            best = (A, d0, z0f)
            key = f"{name}_wall{WALL*1000:.1f}_clr{CLR*1000:.1f}_yend{y_end}"
            if best is None:
                out[key] = None
                print(key, "no feasible bow in search space")
                continue
            A, d0, z0f = best
            out[key] = dict(k_mm_px=k * 1000, sheath_len=1466 * k, bow_mm=A * 1000, bow_ref_px=A / k, cavity_offset_mm=d0 * 1000,
                            bow_starts_at_frac_of_blade=z0f, bow_start_ref_row=TOP + z0f * Lb / k, overhang_mm=(1496 - y_end) * k * 1000)
            print("%-34s k %.3f sheath %.3f m | cavity offset %+.1f mm | bow %.1f mm (= %.1f ref px) starting at %.0f%% of blade (ref row %.0f) | overhang %.0f mm" % (
                key, k * 1000, 1466 * k, d0 * 1000, A * 1000, A / k, z0f * 100, TOP + z0f * Lb / k, (1496 - y_end) * k * 1000))
json.dump(out, open(os.path.join(HERE, "sm_s13.json"), "w"), indent=1)
