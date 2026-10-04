# judge r7: independent geometry checks on the FINAL exported FBX bytes (drum, stand, stick)
import bpy, bmesh, json, math, sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import numpy as np
R = 'C:/Users/Cody/Desktop/Blender_Projects/'
E = R + 'Exports/DojoKit/Props/taiko/'
OUT = R + 'WorkFiles/dojo/build/props/taiko/judge_r7/geo_check.json'
res = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = {}
for p in ('Drum', 'Stand', 'Stick'):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=E + 'SM_DKP_Taiko_%s.fbx' % p)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        objs[o.name] = o
res['objects'] = {}
for n, o in sorted(objs.items()):
    if o.type == 'MESH':
        me = o.data
        tris = sum(len(pl.vertices) - 2 for pl in me.polygons)
        res['objects'][n] = dict(tris=tris, dims_m=[round(v, 4) for v in o.dimensions], mats=[m.name if m else None for m in me.materials],
                                 scale=[round(v, 4) for v in o.matrix_world.to_scale()])
    else:
        res['objects'][n] = dict(type=o.type)
def world_mesh(o):
    me = o.data; M = o.matrix_world
    V = [M @ v.co for v in me.vertices]
    F = [list(p.vertices) for p in me.polygons]
    return V, F, me
drum = next(o for n, o in objs.items() if n.endswith('Drum_LOD0') or n == 'SM_DKP_Taiko_Drum_LOD0')
V, F, me = world_mesh(drum)
# loose parts
parent = list(range(len(V)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
for e in me.edges:
    a, b = find(e.vertices[0]), find(e.vertices[1])
    if a != b: parent[a] = b
comp = [find(i) for i in range(len(V))]
parts = {}
for i, c in enumerate(comp): parts.setdefault(c, []).append(i)
Vn = np.array([tuple(v) for v in V])
info = []
for c, idx in parts.items():
    P = Vn[idx]; mn, mx = P.min(0), P.max(0)
    info.append(dict(c=c, n=len(idx), ext=(mx - mn), ctr=(mn + mx) / 2, maxext=float((mx - mn).max())))
info.sort(key=lambda d: -d['maxext'])
res['drum_parts'] = len(info)
res['drum_parts_top15'] = [dict(n=d['n'], ext_mm=[round(float(x) * 1000, 1) for x in d['ext']], ctr_m=[round(float(x), 4) for x in d['ctr']]) for d in info[:15]]
# tacks: parts with max extent 40-50 mm
tacks = [d for d in info if 0.040 < d['maxext'] < 0.050 and d['n'] < 120]
res['tack_count'] = len(tacks)
face_part = [comp[f[0]] for f in F]
def bvh_of(fids):
    sub = [F[i] for i in fids]
    return BVHTree.FromPolygons(V, sub), fids
tackset = set(d['c'] for d in tacks)
tf = [i for i, c in enumerate(face_part) if c in tackset]
tb, _ = bvh_of(tf)
pairs = tb.overlap(tb)
cross = [(a, b) for a, b in pairs if face_part[tf[a]] != face_part[tf[b]]]
res['tack_tack_intersecting_pairs'] = len(cross)
# tack min gap between centres of different rows: approximate via vertex-to-other-part distances for a sample
tack_ctrs = np.array([d['ctr'] for d in tacks])
# ring hardware: parts near the +Y handle (y > 0.6)
hw = [d for d in info if d['ctr'][1] > 0.55 and d['maxext'] < 0.5 and d not in tacks]
res['handle_+Y_parts'] = [dict(n=d['n'], ext_mm=[round(float(x) * 1000, 1) for x in d['ext']], ctr_m=[round(float(x), 4) for x in d['ctr']]) for d in hw]
# the barrel = largest part
barrel = info[0]
# per-part bvh overlap among handle parts + barrel
def part_faces(c): return [i for i, p in enumerate(face_part) if p == c]
hwb = {}
for d in hw + [barrel]:
    hwb[d['c']] = bvh_of(part_faces(d['c']))[0]
ov = {}
keys = list(hwb)
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        k = len(hwb[keys[i]].overlap(hwb[keys[j]]))
        if k: ov['%d-%d' % (i, j)] = k
res['handle_overlaps_(index into handle list, last = barrel)'] = ov
# ring orientation: the part with a hole (torus): largest ext in handle parts with n moderate and roughly ring-shaped
for k, d in enumerate(hw):
    P = Vn[parts[d['c']]]
    cen = P.mean(0); Q = P - cen
    w, vecs = np.linalg.eigh(Q.T @ Q / len(Q))
    nrm = vecs[:, 0]
    rad = np.linalg.norm(Q - np.outer(Q @ nrm, nrm), axis=1)
    d['pca'] = dict(normal=[round(float(x), 3) for x in nrm], sv=[round(float(math.sqrt(max(x, 0))) * 1000, 1) for x in w],
                    r_min_mm=round(float(rad.min()) * 1000, 1), r_max_mm=round(float(rad.max()) * 1000, 1), centre_m=[round(float(x), 4) for x in cen])
res['handle_pca'] = [d['pca'] for d in hw]
# barrel outward normal at handle
res['note'] = 'barrel outward normal at the +Y handle ~ +Y for a drum on X axis'
# ----- drum in stand
stand = next(o for n, o in objs.items() if n.endswith('Stand_LOD0'))
SV, SF, sme = world_mesh(stand)
lay = json.load(open(R + 'WorkFiles/dojo/build/props/taiko/layout_taiko.json'))
dz = [i for i in lay['instances'] if i['piece'] == 'SM_DKP_Taiko_Drum'][0]['loc'][2] - [i for i in lay['instances'] if i['piece'] == 'SM_DKP_Taiko_Stand'][0]['loc'][2]
res['drum_z_in_stand'] = dz
VD = [v + Vector((0, 0, dz)) for v in V]
dbvh = BVHTree.FromPolygons(VD, F)
felt_mi = [i for i, m in enumerate(sme.materials) if m and 'Hide' in m.name]
felt_f = [list(p.vertices) for p in sme.polygons if p.material_index in felt_mi]
wood_f = [list(p.vertices) for p in sme.polygons if p.material_index not in felt_mi]
fb = BVHTree.FromPolygons(SV, felt_f); wb = BVHTree.FromPolygons(SV, wood_f)
res['drum_vs_felt_pairs'] = len(dbvh.overlap(fb)); res['drum_vs_wood_pairs'] = len(dbvh.overlap(wb))
# felt top vertices: felt verts within 15 mm of the drum; signed distance (+ = outside drum)
fv = set(i for f in felt_f for i in f)
sd = []
for i in fv:
    loc, n, fi, d = dbvh.find_nearest(SV[i], 0.02)
    if loc is None: continue
    s = 1 if (SV[i] - loc).dot(n) >= 0 else -1
    sd.append(s * d)
sd = np.array(sd) * 1000
res['felt_verts_within_20mm_signed_mm'] = dict(n=len(sd), min=round(float(sd.min()), 3), p5=round(float(np.percentile(sd, 5)), 3), median=round(float(np.median(sd)), 3)) if len(sd) else None
# felt contact: of felt verts with |d|<3mm
close = sd[np.abs(sd) < 3]
res['felt_contact_verts_mm'] = dict(n=int(len(close)), min=round(float(close.min()), 3) if len(close) else None, max=round(float(close.max()), 3) if len(close) else None)
# nearest drum vertex to wood
best = 9
for v in VD:
    loc, n, fi, d = wb.find_nearest(v, 0.01)
    if loc is not None and d < best: best = d
res['nearest_drum_vertex_to_wood_mm'] = round(best * 1000, 2)
wv = set(i for f in wood_f for i in f); bw = 9
for i in wv:
    loc, n, fi, d = dbvh.find_nearest(SV[i], 0.01)
    if loc is not None and d < bw: bw = d
res['nearest_wood_vertex_to_drum_mm'] = round(bw * 1000, 2)
json.dump(res, open(OUT, 'w'), indent=1, default=float)
print('DONE')
