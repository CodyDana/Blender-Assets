"""Compare two pack dumps (np_dump, written by run_build.sh 'verify'): added / removed / changed per section, and the
node layout of the functions and masters.  The SMG01 W6 gate: every entry that is not an AR-01 or SMG-01 entry is
unchanged (the reference is katana_1003, the last pack build in the main checkout; the AR-01 build ar01_1009b added only
AR01 entries to it, and its dump lived in a temporary mirror that no longer exists).

    py -3 -B WorkFiles/guns/smg/materials/dump_compare_smg01.py <dump_before.json> <dump_after.json> <out.json>
(the layout files are the dumps' dump_layout_<tag>.json siblings)
"""
import json
import sys
from pathlib import Path

ALLOWED = ("AR01", "SMG01")
a_path, b_path, out = (Path(x) for x in sys.argv[1:4])
A = json.loads(a_path.read_text(encoding="utf-8"))
B = json.loads(b_path.read_text(encoding="utf-8"))
SECS = ("functions", "masters", "instances", "meshes", "textures")
res = {"before": a_path.name, "after": b_path.name, "allowed_additions": ALLOWED}
for sec in SECS:
    a, b = A[sec], B[sec]
    res[sec] = {"before": len(a), "after": len(b), "added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
                "changed": sorted(k for k in set(a) & set(b)
                                  if json.dumps(a[k], sort_keys=True) != json.dumps(b[k], sort_keys=True))}
la = json.loads(a_path.with_name(a_path.name.replace("dump_", "dump_layout_")).read_text(encoding="utf-8"))
lb = json.loads(b_path.with_name(b_path.name.replace("dump_", "dump_layout_")).read_text(encoding="utf-8"))
res["node_layout_identical"] = la == lb
added = [k for s in SECS for k in res[s]["added"]]
res["added_smg01"] = [k for k in added if "SMG01" in k]
res["added_all_allowed"] = all(any(t in k for t in ALLOWED) for k in added)
res["nothing_removed_or_changed"] = not any(res[s]["removed"] or res[s]["changed"] for s in SECS)
res["pass"] = bool(res["added_all_allowed"] and res["nothing_removed_or_changed"] and res["node_layout_identical"])
Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({s: {k: (len(v) if isinstance(v, list) else v) for k, v in res[s].items()} for s in SECS}))
print("CHANGED", {s: res[s]["changed"] for s in SECS if res[s]["changed"]})
print("PASS", res["pass"], "layout", res["node_layout_identical"], "smg01 added", len(res["added_smg01"]))
