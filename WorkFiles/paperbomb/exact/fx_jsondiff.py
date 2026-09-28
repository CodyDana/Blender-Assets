import json
a = json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/fx/pre_final/paperbomb_traced.json", encoding="utf-8"))
b = json.load(open("C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_traced.json", encoding="utf-8"))
def walk(x, y, path):
    if type(x) != type(y): print("TYPE", path); return
    if isinstance(x, dict):
        for k in set(x) | set(y): walk(x.get(k), y.get(k), path + "." + str(k))
    elif isinstance(x, list):
        if len(x) != len(y): print("LEN", path, len(x), len(y)); return
        for i, (p, q) in enumerate(zip(x, y)): walk(p, q, path + "[%d]" % i)
    elif x != y:
        s = path
        if "polys_mm" in s and s.count("[") > 3: s = s[:s.index("polys_mm") + 8]
        print("DIFF", s, str(x)[:90], "->", str(y)[:90])
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf): walk(a, b, "")
lines = buf.getvalue().splitlines(); seen = set()
for l in lines:
    key = l.split(" ")[1] if "polys_mm" in l else l
    if key in seen: continue
    seen.add(key); print(l[:260])
