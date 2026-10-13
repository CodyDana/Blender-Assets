"""SR01 debug aid (W3 Part 0, UD3): build the named parts (no save), triangulate them as the UV step does (loop
triangles), and list every triangle with a raw corner under 0.4 deg (the W2 zero-tangent corners were 0.08-0.36 deg
raw) with its frame-M position, plus gunlib.ud's zero-tangent risk. Usage:
blender -b --factory-startup --python sr_sliver_probe.py -- --only chassis,barrel"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
from sr_common import GRIP  # noqa: E402
from gunlib import bl, ud  # noqa: E402
import sniper_parts as SP  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
only = argv[argv.index("--only") + 1].split(",")
coll = bl.collection(SP.PARTS_COLL)
out = {}
for n in only:
    ob, rep = SP.PARTS[n]().build(coll)
    V, T = bl.tris_np(ob)
    P = V[T]
    ang = []
    for k in range(3):
        a = P[:, (k + 1) % 3] - P[:, k]
        b = P[:, (k + 2) % 3] - P[:, k]
        ang.append(np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), (a * b).sum(1))))
    ang = np.min(np.array(ang), axis=0)
    bad = np.nonzero(ang < 0.4)[0]
    u = ud.check_object(ob)
    out[n] = {"tris": int(len(T)), "zero_tangent_risk": u.get("zero_tangent_risk"), "pass_ud1": u["pass_ud1"],
              "pass_ud2": u["pass_ud2"], "min_area": u.get("min_area_mm2"), "shells": rep.get("shells"), "stations": rep.get("stations"), "pre": rep.get("ud_pre_repair"),
              "slivers": [[np.round(P[i].mean(0) + GRIP, 2).tolist(), round(float(ang[i]), 3)] for i in bad]}
    print("SLIVER", n, json.dumps(out[n]))
