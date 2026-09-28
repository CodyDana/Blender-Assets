# sm_m15: straight symmetric sheath exactly as the reference; the blade sits TILTED by a small angle theta
# (about the sheath's thickness axis) and offset d0 inside it.  Lateral offset of the blade frame vs sheath axis:
# d(z) = d0 + z*tan(theta).  Find the (theta, d0) maximising the static margin, per tip-rest row.
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
        for y_end in (1300, 1350, 1380, 1400, 1420, 1440, 1450):
            Lb = bl[-1, 0] + 0.005; k = Lb / (y_end - TOP)
            zs = bl[:, 0]
            inner = np.array([half_px[int(round(TOP + z / k))] * k for z in zs]) - WALL - CLR
            best = None
            for th in np.radians(np.linspace(-1.0, 4.0, 501)):
                for d0 in np.linspace(-0.012, 0.012, 241):
                    d = d0 + zs * np.tan(th)
                    m = (inner - np.maximum(bl[:, 2] - d, d - bl[:, 1])).min()
                    if best is None or m > best[0]:
                        best = (m, np.degrees(th), d0)
            m, th, d0 = best
            key = f"{name}_w{WALL*1000:.1f}_c{CLR*1000:.1f}_y{y_end}"
            pommel_shift = -np.tan(np.radians(th)) * (0.1628 + 0.1713)  # grip end moves the other way
            out[key] = dict(k_mm_px=k * 1000, sheath_len=1466 * k, margin_mm=m * 1000, tilt_deg=th, d0_mm=d0 * 1000,
                            overhang_mm=(1496 - y_end) * k * 1000, pommel_lateral_mm=(d0 + pommel_shift) * 1000)
            print("%-22s k %.3f L %.3f overhang %3.0f mm | best margin %+5.1f mm with tilt %.2f deg, mouth offset %+.1f mm, pommel lateral %+.1f mm" % (
                key, k * 1000, 1466 * k, (1496 - y_end) * k * 1000, m * 1000, th, d0 * 1000, (d0 + pommel_shift) * 1000))
json.dump(out, open(os.path.join(HERE, "sm_s15.json"), "w"), indent=1)
