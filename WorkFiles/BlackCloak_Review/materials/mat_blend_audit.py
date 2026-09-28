"""List materials, images, slots and UV layers in a COPY of Assets/BlackCloak.blend. Never saves."""
import bpy, json, hashlib
import numpy as np
from pathlib import Path
OUT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/materials")
R = {"file": bpy.data.filepath, "images": [], "materials": {}, "objects": []}
for im in bpy.data.images:
    d = {"name": im.name, "filepath": im.filepath, "packed": im.packed_file is not None, "size": list(im.size),
         "colorspace": im.colorspace_settings.name, "users": im.users}
    if im.packed_file is not None:
        d["packed_sha256"] = hashlib.sha256(bytes(im.packed_file.data)).hexdigest()
    R["images"].append(d)
for m in bpy.data.materials:
    md = {"users": m.users, "nodes": []}
    if m.use_nodes and m.node_tree:
        for n in m.node_tree.nodes:
            nd = {"type": n.type, "name": n.name}
            if n.type == "BSDF_PRINCIPLED":
                for k in ("Base Color", "Metallic", "Roughness", "Specular IOR Level", "Sheen Weight", "Coat Weight"):
                    s = n.inputs.get(k)
                    if s is not None and not s.is_linked:
                        v = s.default_value
                        nd[k] = list(v) if hasattr(v, "__len__") else v
                    elif s is not None:
                        nd[k] = "linked"
            if n.type == "TEX_IMAGE" and n.image:
                nd["image"] = n.image.name; nd["cs"] = n.image.colorspace_settings.name
            if n.type in ("TEX_NOISE", "TEX_VORONOI", "TEX_WAVE", "TEX_MUSGRAVE"):
                nd["procedural"] = True
            md["nodes"].append(nd)
    R["materials"][m.name] = md
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    me = o.data
    counts = {}
    mi = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("material_index", mi)
    lt = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("loop_total", lt)
    for i, slot in enumerate(o.material_slots):
        counts[slot.material.name if slot.material else "None"] = int((lt[mi == i] - 2).sum())
    R["objects"].append({"name": o.name, "collections": [c.name for c in o.users_collection],
                         "slots": [s.material.name if s.material else None for s in o.material_slots],
                         "tris_by_slot_base_mesh": counts, "uv_layers": [u.name for u in me.uv_layers],
                         "color_attributes": [c.name for c in me.color_attributes],
                         "vertex_groups": len(o.vertex_groups), "modifiers": [md.type for md in o.modifiers]})
(OUT / "mat_blend_audit.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
print("BLEND_AUDIT_DONE")
