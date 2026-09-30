"""Round 4 combined import: do the four new kits (outbuildings, corridors, shed, pavilion) clash with anything else in
the composed showcase? Render meshes (LOD0) in world space, every round-4 instance against every instance of ANOTHER
kit whose world box overlaps its own (+2 cm): intersecting triangle pairs (BVHTree.overlap) and the z range of the
round-4 faces involved. A contact whose faces all sit below +0.08 m is a grade contact (footings, paving and plinths
bedded into the ground kit's gravel / sand), reported apart from real clashes.
Run: blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python <this>
Out: WorkFiles/dojo/build/unreal/round4/checks/clearance_r4.json
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
L = json.loads((WORK / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
R4 = ("outbuildings", "corridors", "shed", "pavilion")
GRADE_Z = 0.08
ASM = {o.name: o for o in bpy.data.collections["Assembly"].objects}
insts = []
for n, i in enumerate(L["instances"]):
    o = ASM.get(f"{i['piece']}__{n:04d}")
    if o is None or i["collision_class"] == "boundary":
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[k] for p in bb) for k in range(3)])
    hi = Vector([max(p[k] for p in bb) for k in range(3)])
    insts.append((n, i, o, lo, hi))
cache = {}


def bvh(o):
    if o.name not in cache:
        mw = o.matrix_world
        vs = [mw @ v.co for v in o.data.vertices]
        cache[o.name] = (BVHTree.FromPolygons(vs, [list(p.vertices) for p in o.data.polygons], epsilon=0.0), vs)
    return cache[o.name]


clashes, grade = [], []
for n, i, o, lo, hi in insts:
    if i["kit"] not in R4:
        continue
    for m, j, p, lo2, hi2 in insts:
        if j["kit"] == i["kit"] or (j["kit"] in R4 and m < n):
            continue
        if any(hi[k] < lo2[k] - 0.02 or hi2[k] < lo[k] - 0.02 for k in range(3)):
            continue
        b1, v1 = bvh(o)
        b2, _ = bvh(p)
        pairs = b1.overlap(b2)
        if not pairs:
            continue
        zs = [max(v1[k].z for k in o.data.polygons[a].vertices) for a, _b in pairs[:5000]]
        zmin = [min(v1[k].z for k in o.data.polygons[a].vertices) for a, _b in pairs[:5000]]
        xy = [[round(v1[o.data.polygons[a].vertices[0]][c], 2) for c in range(3)] for a, _b in pairs[:3]]
        row = {"a": o.name, "a_kit": i["kit"], "b": p.name, "b_kit": j["kit"], "pairs": len(pairs),
               "z_range_of_a_faces": [round(min(zmin), 3), round(max(zs), 3)], "sample": xy}
        (grade if max(zs) < GRADE_Z else clashes).append(row)
res = {"grade_z_m": GRADE_Z, "n_round4_instances": sum(1 for x in insts if x[1]["kit"] in R4),
       "clashes": clashes, "grade_contacts": grade, "n_clashes": len(clashes), "n_grade_contacts": len(grade)}
out = WORK / "unreal" / "round4" / "checks" / "clearance_r4.json"
out.write_text(json.dumps(res, indent=1), encoding="utf-8")
for c in clashes:
    print("CLASH", c["a"], "x", c["b"], c["pairs"], c["z_range_of_a_faces"], c["sample"][:1])
print("CLEARANCE_R4 clashes", len(clashes), "grade", len(grade))
