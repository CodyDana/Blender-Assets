"""PlayerBase conform input - step 2: inventory the COPY of the custom human.

Run headless on the copy only:
    blender -b WorkFiles/MetaHuman/player_base/src_Human_copy.blend --factory-startup \
        --python Scripts/MetaHuman/pb_inventory.py -- <out.json>

Read-only: never saves the .blend.
"""
import sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from pipeline import lock
lock.assert_owner("JinMuWon_v2", "claude")

import json
import os

import bpy
import bmesh

COPY_DIR = os.path.normcase(os.path.abspath(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base"))
if os.path.normcase(os.path.dirname(os.path.abspath(bpy.data.filepath))) != COPY_DIR:
    raise SystemExit(f"Refusing to run on {bpy.data.filepath}: only the player_base copy is allowed")

ORIG_DIR = r"C:/Users/Cody/Desktop/Blender_Projects/Assets/JinMuWon_v2"

out_path = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None


def resolve_image_path(img):
    """Relative paths in the copy are relative to the ORIGINAL blend's folder."""
    fp = img.filepath_raw or img.filepath
    if not fp:
        return None
    if fp.startswith("//"):
        return os.path.normpath(os.path.join(ORIG_DIR, fp[2:]))
    return os.path.normpath(fp)


report = {"blend": bpy.data.filepath, "scene": bpy.context.scene.name,
          "unit_system": bpy.context.scene.unit_settings.system,
          "unit_scale": bpy.context.scene.unit_settings.scale_length,
          "objects": {}, "images": {}, "materials": {}}

deps = bpy.context.evaluated_depsgraph_get()
for obj in bpy.data.objects:
    rec = {"type": obj.type, "parent": obj.parent.name if obj.parent else None,
           "parent_type": obj.parent_type if obj.parent else None,
           "hide_viewport": obj.hide_viewport, "hide_render": obj.hide_render,
           "hide_get": obj.hide_get() if obj.name in bpy.context.view_layer.objects else None,
           "collections": [c.name for c in obj.users_collection],
           "location": list(obj.location), "rotation_euler": list(obj.rotation_euler),
           "scale": list(obj.scale),
           "matrix_world_translation": list(obj.matrix_world.translation),
           "modifiers": [{"name": m.name, "type": m.type, "show_viewport": m.show_viewport,
                          "show_render": m.show_render,
                          **({"object": m.object.name if m.object else None} if hasattr(m, "object") else {}),
                          **({"levels": m.levels, "render_levels": m.render_levels} if m.type == "SUBSURF" else {}),
                          } for m in obj.modifiers]}
    if obj.type == "MESH":
        me = obj.data
        rec["mesh"] = {"name": me.name, "verts": len(me.vertices), "edges": len(me.edges),
                       "faces": len(me.polygons),
                       "tris": sum(len(p.vertices) - 2 for p in me.polygons),
                       "uv_layers": [uv.name for uv in me.uv_layers],
                       "active_uv": me.uv_layers.active.name if me.uv_layers.active else None,
                       "materials": [m.name if m else None for m in me.materials],
                       "shape_keys": ([(kb.name, round(kb.value, 4), kb.mute) for kb in me.shape_keys.key_blocks]
                                      if me.shape_keys else []),
                       "vertex_groups": len(obj.vertex_groups),
                       "color_attributes": [a.name for a in me.color_attributes],
                       "attributes": sorted(a.name for a in me.attributes)}
        ev = obj.evaluated_get(deps)
        em = ev.to_mesh()
        rec["evaluated"] = {"verts": len(em.vertices), "faces": len(em.polygons),
                            "tris": sum(len(p.vertices) - 2 for p in em.polygons)}
        ws = [ev.matrix_world @ v.co for v in em.vertices]
        if ws:
            rec["evaluated"]["world_min"] = [min(v[i] for v in ws) for i in range(3)]
            rec["evaluated"]["world_max"] = [max(v[i] for v in ws) for i in range(3)]
        ev.to_mesh_clear()
        # topology of the base mesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        boundary = [e for e in bm.edges if e.is_boundary]
        nonman = [e for e in bm.edges if not e.is_manifold]
        loose_v = [v for v in bm.verts if not v.link_edges]
        # components
        seen = set()
        comps = 0
        for v in bm.verts:
            if v.index in seen:
                continue
            comps += 1
            stack = [v]
            seen.add(v.index)
            while stack:
                cur = stack.pop()
                for e in cur.link_edges:
                    o = e.other_vert(cur)
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
        rec["topology"] = {"components": comps, "boundary_edges": len(boundary),
                           "non_manifold_edges": len(nonman), "loose_verts": len(loose_v)}
        bm.free()
    elif obj.type == "ARMATURE":
        arm = obj.data
        rec["armature"] = {"bones": len(arm.bones), "pose_position": arm.pose_position,
                           "has_action": bool(obj.animation_data and obj.animation_data.action),
                           "action": (obj.animation_data.action.name
                                      if obj.animation_data and obj.animation_data.action else None)}
        # any posed bones?
        posed = []
        for pb in obj.pose.bones:
            if (pb.location.length > 1e-6 or pb.rotation_quaternion.angle > 1e-5 and pb.rotation_mode == "QUATERNION"
                    or (pb.rotation_mode != "QUATERNION" and pb.rotation_euler.to_quaternion().angle > 1e-5)
                    or (pb.scale - pb.scale.__class__((1, 1, 1))).length > 1e-6):
                posed.append(pb.name)
        rec["armature"]["posed_bones"] = posed[:40]
        rec["armature"]["posed_bone_count"] = len(posed)
        rec["armature"]["bone_names"] = [b.name for b in arm.bones]
        heads = {}
        for b in arm.bones:
            heads[b.name] = {"head": list(obj.matrix_world @ b.head_local), "tail": list(obj.matrix_world @ b.tail_local)}
        rec["armature"]["bones_world"] = heads
    report["objects"][obj.name] = rec

for img in bpy.data.images:
    rp = resolve_image_path(img)
    report["images"][img.name] = {"filepath": img.filepath, "resolved": rp,
                                  "exists": bool(rp and os.path.exists(rp)),
                                  "packed": img.packed_file is not None,
                                  "size": list(img.size), "colorspace": img.colorspace_settings.name,
                                  "source": img.source, "users": img.users}

for mat in bpy.data.materials:
    rec = {"users": mat.users, "use_nodes": mat.use_nodes, "nodes": []}
    if mat.node_tree:
        for n in mat.node_tree.nodes:
            nrec = {"name": n.name, "type": n.type, "bl_idname": n.bl_idname}
            if n.type == "TEX_IMAGE" and n.image:
                nrec["image"] = n.image.name
            if n.type == "GROUP" and n.node_tree:
                nrec["group"] = n.node_tree.name
            # what does each output feed
            links = []
            for o in n.outputs:
                for l in o.links:
                    links.append(f"{o.name}->{l.to_node.name}.{l.to_socket.name}")
            nrec["links_out"] = links
            rec["nodes"].append(nrec)
    report["materials"][mat.name] = rec

txt = json.dumps(report, indent=1, default=str)
if out_path:
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("WROTE", out_path)
else:
    print(txt)
