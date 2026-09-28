import os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(OUT, "measure2.py")).read()
src = src[:src.index("compass = [")]
exec(compile(src, "m2head", "exec"))
ej = json.load(open(os.path.join(OUT, "edges_v2.json")))
print("%-14s %6s %6s %6s | %6s %6s %6s | %6s %6s %6s | %s" % (
    "edge", "bev_md", "bev_t2", "bev_t8", "rmsD", "sagD", "dirD", "rmsC", "sagC", "dirC", "deficit@3px"))
for e in ej["edges"]:
    n = np.array(e["n"])
    rows = [r for r in e["rows"] if 0.15 <= r["t"] <= 0.85]
    bev = np.array([r["s_clean"] - r["s_dark"] for r in rows])
    t = np.array([r["t"] for r in rows])
    pd_ = np.array([np.array(r["P"]) + r["s_dark"] * n for r in rows])
    pc = np.array([np.array(r["P"]) + r["s_clean"] * n for r in rows])
    fD = robust_line(pd_); fC = robust_line(pc)
    print("%-14s %6.1f %6.1f %6.1f | %6.2f %+6.2f %6.1f | %6.2f %+6.2f %6.1f | %s %s" % (
        e["name"], np.nanmedian(bev), np.nanmedian(bev[t < 0.35]), np.nanmedian(bev[t > 0.65]),
        fD["rms"], fD["sagitta"], math.degrees(math.atan2(-fD["d"][1], fD["d"][0])),
        fC["rms"], fC["sagitta"], math.degrees(math.atan2(-fC["d"][1], fC["d"][0])),
        "%+.3f" % e["lid_deficit_profile"][3], "SHADOWclass" if e["shadowed"] else "cleanclass"))
