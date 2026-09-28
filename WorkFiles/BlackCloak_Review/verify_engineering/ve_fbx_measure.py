"""verify_engineering: independent measurement of exported FBX files (read-only import into factory scene, never saved)."""
import bpy, bmesh, json, sys, math, re
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]
src, out, do_isect = argv[0], argv[1], argv[2] == '1'
bones_json = r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default/rig/bones.json'
mh = list(json.load(open(bones_json)).values())[0]['bones']
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
R = {'file': src}
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
R['objects'] = {o.name: o.type for o in bpy.context.scene.objects}
if arms:
    a = arms[0]
    names = [b.name for b in a.data.bones]
    R['armature'] = {'object_name': a.name, 'bones': len(names), 'dotted': sum('.' in n for n in names),
                     'shared_with_mh': sorted(set(names) & set(mh)), 'same_order_as_mh': names == mh,
                     'root_bones': [b.name for b in a.data.bones if b.parent is None]}
tot = 0; per = {}; infl_hist = {}; bone_use = {}; wsum_err = 0.0; unweighted = 0
edge_all = []; minang = []
for o in meshes:
    me = o.data; me.calc_loop_triangles()
    mw = o.matrix_world
    t = len(me.loop_triangles); tot += t
    d = {'tris': t, 'verts': len(me.vertices), 'uv_layers': [u.name for u in me.uv_layers],
         'color_attrs': [c.name for c in me.color_attributes], 'materials': [m.name if m else None for m in me.materials]}
    # per material tri count
    mt = {}
    for lt in me.loop_triangles:
        mn = me.materials[lt.material_index].name if me.materials and me.materials[lt.material_index] else 'None'
        mt[mn] = mt.get(mn, 0) + 1
    d['tris_by_material'] = mt
    # uv ranges
    for u in me.uv_layers:
        xs = [l.uv.x for l in u.data]; ys = [l.uv.y for l in u.data]
        d['uv_' + u.name] = [round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3)]
    # texel: uv0 area / world area
    if me.uv_layers:
        uv = me.uv_layers[0].data
        ua = 0; wa = 0
        for lt in me.loop_triangles:
            a_, b_, c_ = [uv[i].uv for i in lt.loops]
            ua += abs((b_ - a_).cross(c_ - a_)) / 2
            wa += lt.area
        # world area in m^2 (apply scale)
        s = mw.to_scale(); sc = s.x * s.y
        d['uv0_units_per_m'] = round(math.sqrt(ua / max(wa * sc, 1e-12)), 3)
    # weights
    gi = {g.index: g.name for g in o.vertex_groups}
    for v in me.vertices:
        ws = [(gi[g.group], g.weight) for g in v.groups if g.weight > 1e-6 and g.group in gi]
        n = len(ws); infl_hist[n] = infl_hist.get(n, 0) + 1
        if n == 0: unweighted += 1
        else: wsum_err = max(wsum_err, abs(sum(w for _, w in ws) - 1))
        for b, w in ws: bone_use[b] = bone_use.get(b, 0) + 1
    # normals outward fraction relative to object centroid (xy plane)
    cen = sum((v.co for v in me.vertices), Vector()) / max(len(me.vertices), 1)
    outw = 0
    for p in me.polygons:
        dv = (p.center - Vector((0, 0, p.center.z)));  # radial from vertical axis at origin
        if p.normal.xy.dot(dv.xy) > 0: outw += 1
    d['normals_radially_outward_frac'] = round(outw / max(len(me.polygons), 1), 3)
    bm = bmesh.new(); bm.from_mesh(me)
    d['boundary_edges'] = sum(1 for e in bm.edges if e.is_boundary)
    d['nonmanifold'] = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    d['ngons_in_file'] = sum(1 for f in me.polygons if len(f.vertices) > 4)
    bm.free()
    per[o.name] = d
R['meshes'] = per; R['n_meshes'] = len(meshes); R['total_tris'] = tot
R['influences_hist'] = infl_hist; R['bone_use_vertices'] = bone_use; R['unweighted'] = unweighted; R['max_weight_sum_err'] = round(wsum_err, 5)
# bounds in world (Blender import converts cm->m)
allco = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
mn = [min(c[i] for c in allco) for i in range(3)]; mx = [max(c[i] for c in allco) for i in range(3)]
R['bounds_m_min'] = [round(x, 4) for x in mn]; R['bounds_m_max'] = [round(x, 4) for x in mx]
R['size_cm'] = [round((mx[i] - mn[i]) * 100, 2) for i in range(3)]
# intersections
if do_isect:
    bvh = {}; tris = {}
    for o in meshes:
        bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); bmesh.ops.triangulate(bm, faces=bm.faces)
        bvh[o.name] = BVHTree.FromBMesh(bm); bm.free()
    cross = 0; pairs = {}
    names = list(bvh)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            n = len(bvh[names[i]].overlap(bvh[names[j]]))
            if n: pairs[names[i] + ' x ' + names[j]] = n; cross += n
    selfn = {}
    for n_, b in bvh.items():
        ov = b.overlap(b)
        # overlap(self) returns pairs incl adjacent faces sharing verts? BVHTree.overlap excludes shared-vertex pairs for self
        s = len([p for p in ov if p[0] < p[1]])
        if s: selfn[n_] = s
    R['intersections'] = {'cross_total': cross, 'cross_pairs_count': len(pairs), 'top_pairs': dict(sorted(pairs.items(), key=lambda x: -x[1])[:8]),
                          'self_total': sum(selfn.values()), 'self_by_mesh': selfn}
json.dump(R, open(out, 'w'), indent=1)
print('VE_DONE', out)
