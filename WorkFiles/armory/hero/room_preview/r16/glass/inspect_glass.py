"""glass-bug: read-only inspection of the live blend's case glass (never saves)."""
import bpy, bmesh
from mathutils import Vector
sc = bpy.context.scene
print("SCENE", sc.name, "engine", sc.render.engine)
c = sc.cycles
for k in ("max_bounces", "diffuse_bounces", "glossy_bounces", "transmission_bounces", "transparent_max_bounces", "volume_bounces"):
    print("  cycles", k, getattr(c, k))
for o in bpy.data.objects:
    if "Tall_Glass" in o.name or ("Glass" in o.name and o.type == "MESH" and "Case" in o.name and o.name.endswith(("_Glass",))):
        pass
names = sorted({(o.data.name if o.type == 'MESH' else '') for o in bpy.data.objects if 'Case_Tall' in (o.data.name if o.type=='MESH' else '')})
print("TALL meshes", names)
for o in bpy.data.objects:
    if o.type == 'MESH' and 'Case_Tall_Glass' in o.data.name:
        mw = o.matrix_world
        print("OBJ", o.name, "data", o.data.name, "loc", tuple(round(v, 3) for v in mw.translation), "rotz",
              round(o.matrix_world.to_euler().z, 3), "scale", tuple(round(v, 3) for v in o.matrix_world.to_scale()),
              "slots", [s.material.name if s.material else None for s in o.material_slots],
              "link", [s.link for s in o.material_slots], "vis_cam", o.visible_camera, "vis_tr", o.visible_transmission,
              "hide_render", o.hide_render, "parent", o.parent.name if o.parent else None,
              "mods", [m.type for m in o.modifiers])
me = next(m for m in bpy.data.meshes if m.name.startswith('SM_AK_Case_Tall_Glass'))
print("MESH", me.name, len(me.vertices), "v", len(me.polygons), "f", "users", me.users, "mats", [m.name if m else None for m in me.materials])
# glass faces: normals, area, duplicates
bm = bmesh.new(); bm.from_mesh(me)
glass_idx = [i for i, m in enumerate(me.materials) if m and 'Glass' in m.name]
gf = [f for f in bm.faces if f.material_index in glass_idx]
print("glass faces", len(gf))
cen = {}
for f in gf:
    c_ = f.calc_center_median(); n = f.normal
    key = tuple(round(v, 4) for v in c_)
    cen.setdefault(key, []).append(tuple(round(v, 3) for v in n))
    print("  GF c", tuple(round(v, 4) for v in c_), "n", tuple(round(v, 3) for v in n), "area", round(f.calc_area(), 4),
          "mat", me.materials[f.material_index].name)
print("dup centres", {k: v for k, v in cen.items() if len(v) > 1})
# glass material nodes
for m in bpy.data.materials:
    if 'Glass' in m.name:
        nodes = [(n.type, n.name) for n in m.node_tree.nodes] if m.use_nodes else None
        print("MAT", m.name, "users", m.users, "blend", getattr(m, 'surface_render_method', None), "backface", m.use_backface_culling, "nodes", len(nodes or []))
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'MATH': print("    math", n.operation, [i.default_value for i in n.inputs[:2]])
                if n.type == 'BSDF_TRANSPARENT': print("    transp", tuple(n.inputs['Color'].default_value))
# any other mesh intersecting case 6's glass bbox
for o in bpy.data.objects:
    if o.type == 'MESH' and 'Case_Tall_Glass' in o.data.name:
        ws = [o.matrix_world @ Vector(b) for b in o.bound_box]
        lo = Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws)))
        hi = Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))
        hits = []
        for p in bpy.data.objects:
            if p is o or p.type != 'MESH': continue
            ps = [p.matrix_world @ Vector(b) for b in p.bound_box]
            plo = Vector((min(v.x for v in ps), min(v.y for v in ps), min(v.z for v in ps)))
            phi = Vector((max(v.x for v in ps), max(v.y for v in ps), max(v.z for v in ps)))
            if all(plo[i] < hi[i] and phi[i] > lo[i] for i in range(3)):
                hits.append((p.name, p.data.name, tuple(round(v, 2) for v in plo), tuple(round(v, 2) for v in phi), p.visible_camera))
        print("OVERLAP", o.name, tuple(round(v,2) for v in lo), tuple(round(v,2) for v in hi))
        for h in hits: print("    ", h)
