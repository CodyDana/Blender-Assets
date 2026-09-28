import json
d=json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/r2_detB_report.json",encoding="utf8"))
print(json.dumps(d["textures"],ensure_ascii=False)[:1800])
a=d["art"]; print(list(a.keys()))
p=a.get("provenance") or {}
print(json.dumps({k:(v if not isinstance(v,(dict,list)) else str(v)[:300]) for k,v in p.items()},ensure_ascii=False)[:2500])
