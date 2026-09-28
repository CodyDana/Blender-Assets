"""verify_engineering: clearance of cloak FBXs against a COPY of the locked MH fitting body (never saved)."""
import bpy, bmesh, json, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out = sys.argv[sys.argv.index('--') + 1]
FILES = {'orig_SK_LOD0': r'C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/BlackCloak_Skeletal.fbx',
         'mh_ingame': r'C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Saved/Claude/Blender/SKM_BlackCloak_MH.fbx',
         'mh_pipeline': r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/garment_pipeline/BlackCloak/export/SK_BlackCloak_MH.fbx'}
R = {}
col = bpy.data.collections.get('FITBODY_MH_PlayerDefault')
body = [o for o in col.all_objects if o.type == 'MESH']
R['body_objects'] = [(o.name, len(o.data.vertices)) for o in body]
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new(); regions = []
for o in body:
    e = o.evaluated_get(dg); me = e.to_mesh()
    gi = {g.index: g.name for g in o.vertex_groups}
    tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(o.matrix_world)
    vreg = []
    for v in me.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        vreg.append(gi.get(best.group, '') if best else '')
    bmesh.ops.triangulate(tmp, faces=tmp.faces)
    for f in tmp.faces: regions.append(vreg[f.verts[0].index])
    tmpme = bpy.data.meshes.new('tmp'); tmp.to_mesh(tmpme); tmp.free(); bm.from_mesh(tmpme)
    e.to_mesh_clear()
bm.faces.ensure_lookup_table()
tree = BVHTree.FromBMesh(bm)
def region(name):
    n = name.lower()
    if any(k in n for k in ('upperarm', 'lowerarm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky', 'elbow', 'wrist')): return 'arm'
    if any(k in n for k in ('neck',)): return 'neck'
    if any(k in n for k in ('head', 'face', 'jaw')): return 'head'
    return 'torso_legs'
verts_by_file = {}
for key, path in FILES.items():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    res = {'inside_gt_1mm': 0, 'inside_gt_1cm': 0, 'deepest_cm': 0.0, 'by_region': {}, 'outside_0_1cm': 0, 'non_arm_inside_gt_1mm': 0, 'min_gap_non_arm_cm': 99}
    allv = []
    for o in new:
        for v in o.data.vertices:
            p = o.matrix_world @ v.co; allv.append(p)
            loc, nrm, idx, dist = tree.find_nearest(p)
            if loc is None: continue
            inside = (p - loc).dot(nrm) < 0
            reg = region(regions[idx])
            if inside and dist > 0.001:
                res['inside_gt_1mm'] += 1; res['by_region'][reg] = res['by_region'].get(reg, 0) + 1
                if reg != 'arm': res['non_arm_inside_gt_1mm'] += 1
                if dist > 0.01: res['inside_gt_1cm'] += 1
                res['deepest_cm'] = max(res['deepest_cm'], round(dist * 100, 2))
            elif not inside:
                if dist < 0.01: res['outside_0_1cm'] += 1
                if reg != 'arm': res['min_gap_non_arm_cm'] = min(res['min_gap_non_arm_cm'], round(dist * 100, 3))
    res['verts'] = len(allv)
    verts_by_file[key] = allv
    R[key] = res
    for o in new: bpy.data.objects.remove(o)
# ingame vs pipeline per-index deltas
a, b = verts_by_file['mh_ingame'], verts_by_file['mh_pipeline']
if len(a) == len(b):
    d = sorted((a[i] - b[i]).length for i in range(len(a)))
    R['ingame_vs_pipeline'] = {'n': len(d), 'max_mm': round(d[-1] * 1000, 2), 'n_over_0.01mm': sum(1 for x in d if x > 1e-5), 'n_over_1mm': sum(1 for x in d if x > 1e-3)}
json.dump(R, open(out, 'w'), indent=1)
print('VE_CLR_DONE')
