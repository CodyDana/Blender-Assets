"""Compare two pack dumps (WorkFiles/materials/build/dump_<tag>.json): added / removed / changed per section."""
import json, sys
from pathlib import Path
B = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/build")
a_tag, b_tag, out = sys.argv[1], sys.argv[2], sys.argv[3]
A = json.loads((B / f"dump_{a_tag}.json").read_text()); Bd = json.loads((B / f"dump_{b_tag}.json").read_text())
res = {}
for sec in ("functions", "instances", "masters", "meshes", "textures"):
    a, b = A[sec], Bd[sec]
    res[sec] = {"before": len(a), "after": len(b), "added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
                "changed": sorted(k for k in set(a) & set(b) if json.dumps(a[k], sort_keys=True) != json.dumps(b[k], sort_keys=True))}
la = json.loads((B / f"dump_layout_{a_tag}.json").read_text()); lb = json.loads((B / f"dump_layout_{b_tag}.json").read_text())
res["node_layout_identical"] = la == lb
Path(out).write_text(json.dumps(res, indent=1))
print(json.dumps({k: (v if not isinstance(v, dict) else {kk: (vv if not isinstance(vv, list) else len(vv)) for kk, vv in v.items()}) for k, v in res.items()}))
print("CHANGED", {k: v["changed"] for k, v in res.items() if isinstance(v, dict) and v["changed"]})
print("ADDED", {k: v["added"] for k, v in res.items() if isinstance(v, dict) and v["added"]})
