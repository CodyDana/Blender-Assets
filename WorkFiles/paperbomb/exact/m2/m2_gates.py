import json
d=json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/r2_detB_report.json",encoding="utf8"))
g=d.get("gates",{}); print("gates",sum(bool(v) for v in g.values()),"/",len(g))
print([k for k,v in g.items() if not v])
print([k for k in g if any(s in k for s in ("mip","colour","color","socket","ucx","lod","determin","provenance","ink_floor","gallery","baked"))])
for k in ("retired_gates","RETIRED_GATES","provenance"):
    if k in d: print(k, json.dumps(d[k],ensure_ascii=False)[:1500])
print([k for k in d.keys()])
