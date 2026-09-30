"""Round 4 ridges: prove the collision did not move. Loads the UCX_* hull objects of two .blend files (the round-3
start backup and the rebuilt blend), matched by name, and compares their world-space vertex sets (sorted, rounded to
0.1 mm). Also compares the render meshes' bounding boxes (the visual envelope) for the named pieces.
Run: blender -b --factory-startup --python compare_hulls.py -- <old.blend> <new.blend> <prefix[,prefix]> <out.json>
"""
import json
import sys

import bpy

old_p, new_p, prefixes, out_p = sys.argv[sys.argv.index("--") + 1:][:4]
PRE = tuple(prefixes.split(","))


def grab(path):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(PRE) or n.startswith(tuple("UCX_" + p for p in PRE))]
    hulls, boxes = {}, {}
    for o in dst.objects:
        if o is None or o.type != "MESH":
            continue
        M = o.matrix_world
        pts = sorted(tuple(round(c, 4) for c in (M @ v.co)) for v in o.data.vertices)
        base = o.name.split(".")[0]
        if base.startswith("UCX_"):
            hulls[base] = pts
        else:
            xs = [M @ v.co for v in o.data.vertices]
            boxes[base] = [[round(min(p[i] for p in xs), 4) for i in range(3)],
                           [round(max(p[i] for p in xs), 4) for i in range(3)], len(o.data.polygons)]
        bpy.data.objects.remove(o, do_unlink=True)
    return hulls, boxes


ho, bo = grab(old_p)
hn, bn = grab(new_p)
res = {"hulls_old": len(ho), "hulls_new": len(hn), "missing": sorted(set(ho) - set(hn)),
       "added": sorted(set(hn) - set(ho)), "moved": [], "max_vertex_delta_m": 0.0, "bbox": {}}
for k in sorted(set(ho) & set(hn)):
    a, b = ho[k], hn[k]
    if len(a) != len(b):
        res["moved"].append([k, "vertex count %d -> %d" % (len(a), len(b))])
        continue
    d = max(max(abs(p[i] - q[i]) for i in range(3)) for p, q in zip(a, b)) if a else 0.0
    res["max_vertex_delta_m"] = max(res["max_vertex_delta_m"], d)
    if d > 0.0005:
        res["moved"].append([k, round(d, 4)])
for k in sorted(set(bo) & set(bn)):
    res["bbox"][k] = {"old": bo[k][:2], "new": bn[k][:2], "faces": [bo[k][2], bn[k][2]]}
res["passed"] = not res["missing"] and not res["added"] and not res["moved"]
open(out_p, "w", encoding="utf-8").write(json.dumps(res, indent=1))
print("HULLS", "passed", res["passed"], "old", len(ho), "new", len(hn), "moved", res["moved"][:10],
      "max_delta", res["max_vertex_delta_m"])
