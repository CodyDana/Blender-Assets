"""Compare two pack dumps (np_dump, written by run_build.sh 'verify'): added / removed / changed per section, and the
node layout of the functions and masters.  The AR-01 gate: every entry that is not an AR-01 entry is unchanged.

    py -3 -B WorkFiles/guns/rifle/materials/dump_compare_ar01.py <dump_before.json> <dump_after.json> <out.json>
(the layout files are the dumps' dump_layout_<tag>.json siblings)
"""
import json
import sys
from pathlib import Path

a_path, b_path, out = (Path(x) for x in sys.argv[1:4])
A = json.loads(a_path.read_text(encoding="utf-8"))
B = json.loads(b_path.read_text(encoding="utf-8"))
res = {"before": str(a_path), "after": str(b_path)}
for sec in ("functions", "masters", "instances", "meshes", "textures"):
    a, b = A[sec], B[sec]
    res[sec] = {"before": len(a), "after": len(b), "added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
                "changed": sorted(k for k in set(a) & set(b)
                                  if json.dumps(a[k], sort_keys=True) != json.dumps(b[k], sort_keys=True))}
la = json.loads(a_path.with_name(a_path.name.replace("dump_", "dump_layout_")).read_text(encoding="utf-8"))
lb = json.loads(b_path.with_name(b_path.name.replace("dump_", "dump_layout_")).read_text(encoding="utf-8"))
res["node_layout_identical"] = la == lb
added = [k for s in ("functions", "masters", "instances", "meshes", "textures") for k in res[s]["added"]]
res["added_all_ar01"] = all("AR01" in k for k in added)
res["nothing_removed_or_changed"] = not any(res[s]["removed"] or res[s]["changed"]
                                            for s in ("functions", "masters", "instances", "meshes", "textures"))
res["pass"] = bool(res["added_all_ar01"] and res["nothing_removed_or_changed"] and res["node_layout_identical"])
Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({s: {k: (len(v) if isinstance(v, list) else v) for k, v in res[s].items()}
                  for s in ("functions", "masters", "instances", "meshes", "textures")}))
print("CHANGED", {s: res[s]["changed"] for s in ("functions", "masters", "instances", "meshes", "textures") if res[s]["changed"]})
print("PASS", res["pass"], "layout", res["node_layout_identical"])
