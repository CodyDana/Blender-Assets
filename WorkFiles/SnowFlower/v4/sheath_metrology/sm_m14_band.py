# sm_m14: feasible band for the sheath centreline offset d(z) and a minimal-motion (taut) path through it
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
s01 = json.load(open(os.path.join(HERE, "sm_s01.json")))
prof = np.array(s01["profile"]); TOP = s01["top"]
half_px = body_half_table(prof)
s12 = json.load(open(os.path.join(HERE, "sm_s12.json")))
blades = {"rev3": np.array(s12["rev3"]), "sheet": np.array(s12["sheet"])}
out = {}
for WALL, CLR in ((0.003, 0.0015), (0.0025, 0.001)):
    for name, bl in blades.items():
        for y_end in (1150, 1200, 1250, 1300, 1350, 1400, 1440):
            Lb = bl[-1, 0] + 0.005; k = Lb / (y_end - TOP)
            zs = bl[:, 0]
            inner = np.array([half_px[int(round(TOP + z / k))] * k for z in zs]) - WALL - CLR
            lo = bl[:, 2] - inner; hi = bl[:, 1] + inner
            feasible = bool(np.all(hi >= lo))
            # best constant offset for the straight upper part, then taut path downwards
            d0_lo = lo[: len(zs) // 3].max(); d0_hi = hi[: len(zs) // 3].min()
            d = np.clip(0.0, d0_lo, d0_hi); path = []
            for i in range(len(zs)):
                d = min(max(d, lo[i]), hi[i]); path.append(d)
            path = np.array(path)
            d_start = path[0]
            dev = path - d_start
            i0 = int(np.argmax(np.abs(dev) > 0.0005)) if np.any(np.abs(dev) > 0.0005) else len(zs) - 1
            key = f"{name}_w{WALL*1000:.1f}_c{CLR*1000:.1f}_y{y_end}"
            out[key] = dict(feasible=feasible, k=k, sheath_len=1466 * k, d_start_mm=d_start * 1000, bow_mm=float(dev.max() * 1000),
                            bow_ref_px=float(dev.max() / k), bow_start_z=float(zs[i0]), bow_start_ref_row=float(TOP + zs[i0] / k),
                            worst_band_mm=float((hi - lo).min() * 1000), overhang_mm=(1496 - y_end) * k * 1000)
            o = out[key]
            print("%-24s feasible %-5s k %.3f L %.3f | offset %+.1f mm | bow %5.1f mm = %4.1f ref px, from z %.2f (ref row %4.0f) | min band %.1f mm | overhang %3.0f mm" % (
                key, feasible, k * 1000, 1466 * k, o["d_start_mm"], o["bow_mm"], o["bow_ref_px"], o["bow_start_z"], o["bow_start_ref_row"], o["worst_band_mm"], o["overhang_mm"]))
json.dump(out, open(os.path.join(HERE, "sm_s14.json"), "w"), indent=1)
