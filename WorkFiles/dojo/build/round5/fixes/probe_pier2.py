import bpy, json
o = bpy.data.objects["SM_DK_Wall_StepPier"]
vs = [v.co for v in o.data.vertices]
# piece local: x along the pier (0..1 -> world Y 26.4..27.4), z up
res = {}
for lo, hi in ((0.0, 0.6), (0.6, 2.6), (2.6, 3.0), (3.0, 3.6)):
    sel = [v for v in vs if lo <= v.z < hi]
    res[f"z{lo}-{hi}"] = round(max(v.x for v in sel), 4) if sel else None
res["top_z"] = round(max(v.z for v in vs), 4)
print("PROBE", json.dumps(res))
