
# Read-only geometry probe on a COPY of male_cloak_scene.blend. Never saves.
import bpy, json, sys, math
from mathutils import Vector
out = sys.argv[sys.argv.index('--')+1]
dg = bpy.context.evaluated_depsgraph_get()
rep = {'objects': []}
for o in bpy.data.objects:
    d = {'name': o.name, 'type': o.type}
    if o.type == 'MESH':
        d['verts'] = len(o.data.vertices)
        d['vgroups'] = [g.name for g in o.vertex_groups][:12]
        d['n_vgroups'] = len(o.vertex_groups)
        d['materials'] = [m.name if m else None for m in o.data.materials]
    rep['objects'].append(d)

def world_verts(o):
    e = o.evaluated_get(dg); m = e.to_mesh()
    vs = [e.matrix_world @ v.co for v in m.vertices]
    e.to_mesh_clear(); return vs

objs = {o.name: o for o in bpy.data.objects}
cloak = next(o for o in bpy.data.objects if o.type=='MESH' and 'loak' in o.name)
rep['cloak_obj'] = cloak.name
cv = world_verts(cloak)
# head / face mesh
heads = [o for o in bpy.data.objects if o.type=='MESH' and ('ace' in o.name or 'ead' in o.name) and 'air' not in o.name.lower()]
rep['head_objs'] = [h.name for h in heads]
bodies = [o for o in bpy.data.objects if o.type=='MESH' and 'ody' in o.name]
rep['body_objs'] = [b.name for b in bodies]
res = {}
# armature bones
arm = next((o for o in bpy.data.objects if o.type=='ARMATURE'), None)
if arm:
    for bn in ['head','neck_01','neck_02','spine_05','clavicle_l','clavicle_r','upperarm_l','upperarm_r','hand_l','hand_r','foot_l','ball_l','thigh_l','pelvis']:
        b = arm.pose.bones.get(bn)
        if b: res['bone_'+bn] = [round(c,4) for c in (arm.matrix_world @ b.head)]
# face landmarks by extreme vertices of the face mesh
for h in heads:
    hv = world_verts(h)
    zs = [v.z for v in hv]; ys = [v.y for v in hv]
    res[h.name+'_zrange'] = [min(zs), max(zs)]
    # frontmost point (nose tip): min y (forward is -Y per bounds)
    nose = min(hv, key=lambda v: v.y)
    res[h.name+'_nose_tip'] = list(nose)
    # chin: frontmost vertex below nose-10cm band -> use lowest z among verts with y < nose.y+4cm and |x|<2cm
    cand = [v for v in hv if abs(v.x)<0.02 and v.y < nose.y+0.05 and v.z < nose.z-0.04]
    if cand:
        chin = min(cand, key=lambda v: v.y + 0.0*v.z)
        res[h.name+'_front_below_nose_minY'] = list(chin)
        lowfront = [v for v in hv if abs(v.x)<0.015 and v.y < nose.y+0.06]
        res[h.name+'_midline_front_zmin'] = min(v.z for v in lowfront)
    # eye: vertex groups?
    for g in h.vertex_groups:
        if g.name.lower() in ('facial_l_eye','facial_r_eye','facial_l_eyeball','facial_r_eyeball'):
            res['has_eye_group_'+g.name]=True
    # eye estimate: frontmost verts at |x| 0.02..0.05 region between nose.z and nose.z+0.06
    eyeband = [v for v in hv if 0.025<abs(v.x)<0.045 and nose.z+0.01 < v.z < nose.z+0.07]
    if eyeband:
        # eye socket: the deepest (max y) point in this band's front surface roughly: use z of min-y dip
        res[h.name+'_eyeband_n'] = len(eyeband)
# cowl: cloak verts near the neck axis above z 1.45
hb = res.get('bone_head'); nb = res.get('bone_neck_01')
cx, cy = (hb[0], hb[1]) if hb else (0,0)
top = max(cv, key=lambda v: v.z)
res['cloak_top'] = list(top)
# cowl front height: cloak verts in front of the face (y < cy-0.06, |x-cx|<0.04)
front = [v for v in cv if abs(v.x-cx)<0.04 and v.y < cy-0.05 and v.z>1.4]
if front: res['cowl_front_centre_zmax'] = max(v.z for v in front)
back = [v for v in cv if abs(v.x-cx)<0.04 and v.y > cy+0.05 and v.z>1.4]
if back: res['cowl_back_centre_zmax'] = max(v.z for v in back)
# cowl radius profile vs z
prof = {}
for z0 in [1.50,1.55,1.60,1.65,1.70,1.75]:
    ring = [v for v in cv if abs(v.z-z0)<0.01 and math.hypot(v.x-cx, v.y-cy)<0.30]
    if ring:
        r = sorted(math.hypot(v.x-cx, v.y-cy) for v in ring)
        prof['%.2f'%z0] = {'n':len(r),'r_min_cm':r[0]*100,'r_p50_cm':r[len(r)//2]*100,'r_max_cm':r[-1]*100}
res['cowl_radius_by_z'] = prof
# body dims
if bodies:
    bv = world_verts(bodies[0])
    res['body_zmax'] = max(v.z for v in bv); res['body_zmin']=min(v.z for v in bv)
    sh = [v for v in bv if 1.35<v.z<1.50]
    res['body_width_z135_150_cm'] = (max(v.x for v in sh)-min(v.x for v in sh))*100
allz = []
for h in heads: allz += [v.z for v in world_verts(h)]
res['head_zmax'] = max(allz) if allz else None
# cloak width at shoulder height and hem
for z0 in [1.45,1.40,1.30,1.00,0.50,0.10]:
    band = [v for v in cv if abs(v.z-z0)<0.02]
    if band: res['cloak_width_x_cm_z%.2f'%z0] = (max(v.x for v in band)-min(v.x for v in band))*100
res['cloak_zmin'] = min(v.z for v in cv); res['cloak_zmax']=max(v.z for v in cv)
rep['measures'] = res
json.dump(rep, open(out,'w'), indent=1, default=lambda o: list(o))
print('WROTE', out)
