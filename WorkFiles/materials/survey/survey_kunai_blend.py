import bpy, json, sys
out = {}
for o in bpy.data.objects:
    if "Kunai" in o.name:
        out[o.name] = {"type": o.type, "materials": [s.material.name if s.material else None for s in o.material_slots],
                       "props": {k: (float(o[k]) if isinstance(o[k], (int, float)) else str(o[k])) for k in o.keys() if not k.startswith("_")},
                       "uv_layers": [u.name for u in o.data.uv_layers] if o.type == "MESH" else None}
mats = {}
for m in bpy.data.materials:
    if m.node_tree and ("Kunai" in m.name or "Shuriken" in m.name or "Preview" in m.name):
        mats[m.name] = {"nodes": len(m.node_tree.nodes), "has_Dye": "Dye" in m.node_tree.nodes, "users": m.users}
out["_materials"] = mats
out["_images"] = sorted(i.name for i in bpy.data.images)[:40]
print("KUNAI_SURVEY " + json.dumps(out))
