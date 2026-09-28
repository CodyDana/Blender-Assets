"""Read-only inventory of a COPY of Assets/BlackCloak.blend. Never saves. Writes JSON to argv path."""
import bpy, bmesh, json, sys, math
from mathutils import Matrix

out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene
res = {"file": bpy.data.filepath, "scene": sc.name,
       "unit_system": sc.unit_settings.system, "scale_length": sc.unit_settings.scale_length,
       "length_unit": sc.unit_settings.length_unit,
       "custom_props": {k: str(v)[:400] for k, v in sc.items()},
       "collections": {}, "objects": {}, "materials": {}, "images": {}}

def coll_tree(c, depth=0):
    res["collections"][c.name] = {"objects": [o.name for o in c.objects],
                                  "children": [ch.name for ch in c.children],
                                  "exclude_render": c.hide_render}
    for ch in c.children:
        coll_tree(ch, depth + 1)
coll_tree(sc.collection)
# view-layer exclusion
def lc_walk(lc, acc):
    acc[lc.name] = {"exclude": lc.exclude, "hide_viewport": lc.hide_viewport}
    for ch in lc.children:
        lc_walk(ch, acc)
acc = {}
lc_walk(bpy.context.view_layer.layer_collection, acc)
res["layer_collections"] = acc

dg = bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    d = {"type": o.type, "data": o.data.name if o.data else None,
         "collections": [c.name for c in o.users_collection],
         "parent": o.parent.name if o.parent else None,
         "location": list(o.location), "rotation_euler": list(o.rotation_euler), "scale": list(o.scale),
         "matrix_basis_identity_rot_scale": None,
         "hide_render": o.hide_render, "hide_viewport": o.hide_viewport,
         "custom_props": {k: str(v)[:200] for k, v in o.items()},
         "modifiers": []}
    mb = o.matrix_basis.to_3x3()
    d["matrix_basis_identity_rot_scale"] = all(abs(mb[i][j] - (1 if i == j else 0)) < 1e-6 for i in range(3) for j in range(3))
    for m in o.modifiers:
        md = {"name": m.name, "type": m.type, "show_viewport": m.show_viewport, "show_render": m.show_render}
        for attr in ("levels", "render_levels", "thickness", "offset", "use_even_offset", "use_rim", "ratio",
                     "vertex_group", "subdivision_type", "use_flip_normals", "use_quality_normals", "width", "segments",
                     "strength", "factor", "iterations", "object"):
            if hasattr(m, attr):
                v = getattr(m, attr)
                md[attr] = v.name if hasattr(v, "name") else (v if isinstance(v, (int, float, str, bool)) or v is None else str(v))
        d["modifiers"].append(md)
    if o.type == "MESH":
        me = o.data
        me.calc_loop_triangles()
        d["base"] = {"verts": len(me.vertices), "faces": len(me.polygons), "tris": len(me.loop_triangles),
                     "ngons": sum(1 for p in me.polygons if len(p.vertices) > 4)}
        d["materials"] = [m.name if m else None for m in me.materials]
        d["uv_layers"] = [u.name for u in me.uv_layers]
        d["color_attributes"] = [(c.name, c.domain, c.data_type) for c in me.color_attributes]
        d["attributes"] = [a.name for a in me.attributes if not a.name.startswith(".")]
        vg = {}
        for g in o.vertex_groups:
            vg[g.name] = 0
        if o.vertex_groups:
            counts = {g.index: [0, 0.0, 1.0] for g in o.vertex_groups}
            for v in me.vertices:
                for ge in v.groups:
                    c = counts.get(ge.group)
                    if c is not None:
                        c[0] += 1; c[1] = max(c[1], ge.weight); c[2] = min(c[2], ge.weight)
            for g in o.vertex_groups:
                c = counts[g.index]
                vg[g.name] = {"assigned": c[0], "max": round(c[1], 4), "min": round(c[2], 4) if c[0] else None}
        d["vertex_groups"] = vg
        d["shape_keys"] = [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []
        # topology on base mesh
        bm = bmesh.new(); bm.from_mesh(me)
        d["base_topology"] = {
            "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
            "nonmanifold_3plus": sum(1 for e in bm.edges if len(e.link_faces) > 2),
            "wire_edges": sum(1 for e in bm.edges if e.is_wire),
            "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
            "zero_area_faces": sum(1 for f in bm.faces if f.calc_area() < 1e-12),
            "zero_len_edges": sum(1 for e in bm.edges if e.calc_length() < 1e-6),
            "islands": None,
        }
        bm.free()
        ev = o.evaluated_get(dg)
        em = ev.to_mesh()
        em.calc_loop_triangles()
        mw = o.matrix_world
        xs = [mw @ v.co for v in em.vertices]
        d["evaluated"] = {"verts": len(em.vertices), "tris": len(em.loop_triangles), "faces": len(em.polygons)}
        if xs:
            d["world_bounds_m"] = [[min(p[i] for p in xs) for i in range(3)], [max(p[i] for p in xs) for i in range(3)]]
        bm = bmesh.new(); bm.from_mesh(em)
        d["evaluated_topology"] = {
            "boundary_edges": sum(1 for e in bm.edges if e.is_boundary),
            "nonmanifold_3plus": sum(1 for e in bm.edges if len(e.link_faces) > 2),
            "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
            "zero_area_faces": sum(1 for f in bm.faces if f.calc_area() < 1e-12),
        }
        bm.free()
        ev.to_mesh_clear()
    elif o.type == "ARMATURE":
        d["bones"] = len(o.data.bones)
    res["objects"][o.name] = d

for m in bpy.data.materials:
    md = {"users": m.users, "nodes": []}
    if m.node_tree:
        for n in m.node_tree.nodes:
            nd = {"type": n.type, "name": n.name}
            if n.type == "TEX_IMAGE" and n.image:
                nd["image"] = n.image.name
            md["nodes"].append(nd)
    res["materials"][m.name] = md
for im in bpy.data.images:
    res["images"][im.name] = {"size": list(im.size), "packed": im.packed_file is not None,
                              "filepath": im.filepath, "colorspace": im.colorspace_settings.name,
                              "source": im.source}
mesh_objs = [o for o in res["objects"].values() if o["type"] == "MESH"]
res["totals"] = {"base_tris": sum(o["base"]["tris"] for o in mesh_objs),
                 "evaluated_tris": sum(o["evaluated"]["tris"] for o in mesh_objs)}
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, default=str)
print("INVENTORY_DONE", res["totals"])
