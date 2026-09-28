import bpy, mathutils, json, sys
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blender/"
out = {"fitbody": {}, "fbx": {}}
for o in bpy.data.objects:
    e = {"type": o.type, "parent": o.parent.name if o.parent else None, "loc": list(o.location), "rot": list(o.rotation_euler),
         "scale": list(o.scale), "collections": [c.name for c in o.users_collection], "hide_render": o.hide_render}
    if o.type == "MESH":
        e["verts"] = len(o.data.vertices); e["polys"] = len(o.data.polygons)
        e["mods"] = [(m.type, getattr(m, "object", None).name if getattr(m, "object", None) else None) for m in o.modifiers]
        e["mats"] = [m.name if m else None for m in o.data.materials]
        e["vgroups"] = len(o.vertex_groups)
        bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        e["bbox"] = [[min(v[i] for v in bb) for i in range(3)], [max(v[i] for v in bb) for i in range(3)]]
    if o.type == "ARMATURE":
        e["bones"] = len(o.data.bones)
        e["pose_position"] = o.data.pose_position
        e["sample_bones"] = {b: [list(o.matrix_world @ o.data.bones[b].head_local)] for b in
                             ("pelvis", "spine_05", "neck_01", "head", "upperarm_l", "upperarm_r", "lowerarm_l", "hand_l", "clavicle_l") if b in o.data.bones}
        e["posed_nonrest"] = [pb.name for pb in o.pose.bones if pb.matrix_basis != mathutils.Matrix.Identity(4)][:20]
    out["fitbody"][o.name] = e
out["scene_unit_scale"] = bpy.context.scene.unit_settings.scale_length
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=D + "copies/SKM_BlackCloak_MH.fbx", automatic_bone_orientation=False)
for o in set(bpy.data.objects) - before:
    e = {"type": o.type, "parent": o.parent.name if o.parent else None, "loc": list(o.location), "rot": list(o.rotation_euler), "scale": list(o.scale)}
    if o.type == "MESH":
        me = o.data
        e["verts"] = len(me.vertices); e["tris"] = sum(len(p.vertices) - 2 for p in me.polygons)
        e["mats"] = [m.name if m else None for m in me.materials]
        e["uv"] = [u.name for u in me.uv_layers]; e["colors"] = [c.name for c in me.color_attributes]
        e["vgroups"] = [g.name for g in o.vertex_groups]
        e["mods"] = [(m.type, getattr(m, "object", None).name if getattr(m, "object", None) else None) for m in o.modifiers]
        bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        e["bbox"] = [[min(v[i] for v in bb) for i in range(3)], [max(v[i] for v in bb) for i in range(3)]]
        per = {}
        for p in me.polygons:
            per[p.material_index] = per.get(p.material_index, 0) + len(p.vertices) - 2
        e["tris_per_slot"] = per
        for m in me.materials:
            if m and m.use_nodes:
                e.setdefault("mat_nodes", {})[m.name] = [(n.type, getattr(getattr(n, "image", None), "name", None)) for n in m.node_tree.nodes]
    if o.type == "ARMATURE":
        e["bones"] = len(o.data.bones)
        e["sample_bones"] = {b: [list(o.matrix_world @ o.data.bones[b].head_local)] for b in
                             ("pelvis", "spine_05", "neck_01", "head", "upperarm_l", "upperarm_r", "lowerarm_l", "hand_l", "clavicle_l") if b in o.data.bones}
    out["fbx"][o.name] = e
json.dump(out, open(D + "logs/inspect_inputs.json", "w"), indent=1, default=str)
print("DONE")
