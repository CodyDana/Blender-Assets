"""verify_engineering: measure the source cages on a COPY of Assets/BlackCloak.blend (never saved)."""
import bpy, bmesh, json, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out = sys.argv[sys.argv.index('--') + 1]
R = {}
col = bpy.data.collections.get('BLACK_CLOAK')
objs = [o for o in col.all_objects if o.type == 'MESH']
R['n'] = len(objs)
dg = bpy.context.evaluated_depsgraph_get()
base = 0; ev = 0; per = {}
bvh = {}
for o in objs:
    me = o.data; me.calc_loop_triangles(); t = len(me.loop_triangles); base += t
    e = o.evaluated_get(dg); em = e.to_mesh(); em.calc_loop_triangles(); et = len(em.loop_triangles); ev += et; e.to_mesh_clear()
    d = {'base_tris': t, 'eval_tris': et, 'verts': len(me.vertices), 'mods': [(m.type, getattr(m, 'levels', None), round(getattr(m, 'thickness', 0) or 0, 4), getattr(m, 'offset', None)) for m in o.modifiers],
         'vgroups': [g.name for g in o.vertex_groups]}
    # normals vs body axis: fraction of faces whose normal points away from the vertical axis (x=y=0)
    outw = sum(1 for p in me.polygons if p.normal.xy.dot((o.matrix_world @ p.center).xy) > 0)
    d['normals_outward_frac'] = round(outw / max(len(me.polygons), 1), 3)
    # UV area per world area (UV units per metre)
    if me.uv_layers:
        uv = me.uv_layers[0].data; ua = sum(abs((uv[lt.loops[1]].uv - uv[lt.loops[0]].uv).cross(uv[lt.loops[2]].uv - uv[lt.loops[0]].uv)) / 2 for lt in me.loop_triangles)
        wa = sum(lt.area for lt in me.loop_triangles)
        d['uv_per_m'] = round(math.sqrt(ua / max(wa, 1e-12)), 3)
    g = o.vertex_groups.get('CLOTH_Pin')
    if g:
        ws = []
        for v in me.vertices:
            w = 0.0
            for gg in v.groups:
                if gg.group == g.index: w = gg.weight
            ws.append(w)
        d['pin_eq1'] = sum(1 for w in ws if w >= 0.999); d['pin_eq0'] = sum(1 for w in ws if w <= 1e-6); d['pin_n'] = len(ws)
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(o.matrix_world); bmesh.ops.triangulate(bm, faces=bm.faces)
    bvh[o.name] = BVHTree.FromBMesh(bm); bm.free()
    per[o.name] = d
R['base_tris'] = base; R['eval_tris'] = ev; R['per'] = per
names = list(bvh); cross = {}; selfc = {}
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        n = len(bvh[names[i]].overlap(bvh[names[j]]))
        if n: cross[names[i] + ' x ' + names[j]] = n
for n_ in names:
    s = len([p for p in bvh[n_].overlap(bvh[n_]) if p[0] < p[1]])
    if s: selfc[n_] = s
R['cage_cross_total'] = sum(cross.values()); R['cage_cross_pairs'] = len(cross); R['cage_top'] = dict(sorted(cross.items(), key=lambda x: -x[1])[:6])
R['cage_self_total'] = sum(selfc.values()); R['cage_self'] = selfc
# material node mapping scale for wool
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'MAPPING':
                R.setdefault('mapping', {})[m.name] = [round(x, 4) for x in nd.inputs['Scale'].default_value]
R['unit'] = [bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length]
json.dump(R, open(out, 'w'), indent=1)
print('VE_SRC_DONE')
