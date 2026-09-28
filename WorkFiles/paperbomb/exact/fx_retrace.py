# final pass: re-trace the reference into props_lib/paperbomb_traced.json (finefit 1.4.0)
# and list which groups changed against the pre-final JSON
import sys, json, time
from pathlib import Path
PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(PROJECT / "Scripts")); sys.path.insert(0, str(PROJECT / "Scripts" / "props"))
from props_lib import paperbomb_trace as PT
old = json.load(open(PROJECT / "WorkFiles/paperbomb/exact/fx/pre_final/paperbomb_traced.json", encoding="utf-8"))
t0 = time.time()
data, _, _ = PT.trace_all(log=lambda *a: None)
sha = PT.save_traced(data)
print("saved", sha, "%.0fs" % (time.time() - t0))
og = {(g["group"], g["layer"]): g for g in old["groups"]}
for g in data["groups"]:
    k = (g["group"], g["layer"])
    same = json.dumps(og.get(k), sort_keys=True) == json.dumps(g, sort_keys=True)
    if not same:
        diffkeys = [kk for kk in set(g) | set(og.get(k, {})) if json.dumps(g.get(kk), sort_keys=True) != json.dumps(og.get(k, {}).get(kk), sort_keys=True)]
        print("CHANGED", k, sorted(diffkeys))
for kk in set(data) - {"groups"}:
    if json.dumps(data[kk], sort_keys=True) != json.dumps(old.get(kk), sort_keys=True):
        print("top-level changed:", kk)
sc = {(g["group"], g["layer"]): g.get("score") for g in data["groups"]}
print(json.dumps({"%s/%s" % k: v for k, v in sc.items() if k[0] == "seal_big"}, indent=0)[:1500])
