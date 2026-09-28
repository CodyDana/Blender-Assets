"""Compare two pack dumps (WorkFiles/materials/build/dump_<tag>.json): every non-flashbang instance, master, function,
mesh and texture must be identical; list what changed on the flashbang's own entries.
    py -3 -B fin2_dump_diff.py <before_dump.json> <after_dump.json> <out.json>"""
import json
import sys

a = json.load(open(sys.argv[1], encoding="utf-8"))
b = json.load(open(sys.argv[2], encoding="utf-8"))
out = {"before": sys.argv[1], "after": sys.argv[2], "sections": {}}
ok = True
for sec in ("instances", "masters", "functions", "meshes", "textures"):
    A, B = a.get(sec, {}), b.get(sec, {})
    own = lambda k: "flashbang" in k.lower()  # noqa: E731
    other_changed = [k for k in sorted(set(A) | set(B)) if not own(k) and A.get(k) != B.get(k)]
    own_changed = {}
    for k in sorted(set(A) | set(B)):
        if own(k) and A.get(k) != B.get(k):
            va, vb = A.get(k) or {}, B.get(k) or {}
            if isinstance(va, dict) and isinstance(vb, dict):
                own_changed[k] = sorted(f for f in set(va) | set(vb) if va.get(f) != vb.get(f))
            else:
                own_changed[k] = "added/removed"
    out["sections"][sec] = {"before_count": len(A), "after_count": len(B),
                            "added": sorted(set(B) - set(A)), "removed": sorted(set(A) - set(B)),
                            "other_changed": other_changed, "flashbang_changed_fields": own_changed}
    ok = ok and not other_changed and not (set(A) - set(B))
out["every_other_entry_unchanged"] = ok
json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), indent=1)
print(json.dumps({s: {k: v for k, v in d.items() if k != "flashbang_changed_fields"} for s, d in out["sections"].items()}, indent=1))
print("flashbang changed:", json.dumps({s: d["flashbang_changed_fields"] for s, d in out["sections"].items()})[:3000])
print("every_other_entry_unchanged", ok)
