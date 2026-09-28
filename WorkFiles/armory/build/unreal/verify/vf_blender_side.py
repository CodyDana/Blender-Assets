"""Independent verifier, Blender side (read-only, nothing saved). Written by the verifier, not the builder.

Computes from Assets/Armory/ArmoryKit.blend:
  - world AABB (metres) of every mesh object in the Assembly collection, from the EVALUATED mesh (modifiers applied)
    and also from the raw mesh data, so a modifier-induced difference would show;
  - per Kit piece: material slot names, UCX children count.
Run: blender -b --factory-startup Assets/Armory/ArmoryKit.blend --python <this> -- <out.json>
"""
import json
import sys

import bpy
from mathutils import Vector

out_path = sys.argv[sys.argv.index("--") + 1]
dg = bpy.context.evaluated_depsgraph_get()


def aabb(o, evaluated):
    if evaluated:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        pts = [oe.matrix_world @ v.co for v in me.vertices]
        oe.to_mesh_clear()
    else:
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


coll = bpy.data.collections.get("Assembly")
res = {"blend": bpy.data.filepath, "collections": [c.name for c in bpy.data.collections]}
inst = {}
types = {}
for o in coll.all_objects:
    types[o.type] = types.get(o.type, 0) + 1
    if o.type != "MESH":
        continue
    emin, emax = aabb(o, True)
    rmin, rmax = aabb(o, False)
    rz = o.matrix_world.to_euler("XYZ")
    inst[o.name] = {"data": o.data.name, "min": list(emin), "max": list(emax), "raw_min": list(rmin), "raw_max": list(rmax),
                    "loc": list(o.matrix_world.translation), "rot_deg": [round(a * 57.29577951308232, 4) for a in rz],
                    "scale": list(o.matrix_world.to_scale()), "modifiers": [m.type for m in o.modifiers]}
res["assembly_object_types"] = types
res["instances"] = inst
kit = bpy.data.collections.get("Kit")
pieces = {}
if kit:
    for o in kit.all_objects:
        if o.type != "MESH" or o.name.startswith("UCX_"):
            continue
        pieces[o.name] = {"slots": [s.material.name if s.material else None for s in o.material_slots],
                          "ucx": sorted(c.name for c in o.children if c.name.startswith("UCX_"))}
res["pieces"] = pieces
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
print("VF_BLENDER_DONE instances", len(inst), "pieces", len(pieces), "types", types)
