"""Apply the collision-clear chain solution to all source LODs without changing UVs/topology.

Run with Blender --background --python this_file.py. The only .blend written is
WorkFiles/BlackNunchucks/BlackNunchucks_resolved.blend. Optimization parameters and
the full geometric verification report are kept beside that file.
"""
import bpy, json, hashlib, struct, sys, math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Scripts/pipeline'))
from lock import assert_owner
assert_owner('BlackNunchucks','codex')
WORK=ROOT/'WorkFiles/BlackNunchucks'
SOURCE=WORK/'BlackNunchucks_procedural.blend'
DESTINATION=WORK/'BlackNunchucks_resolved.blend'
S=.00030
solution=json.loads((WORK/'chain_solution.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))

def invariant(ob):
    h=hashlib.sha256()
    for p in ob.data.polygons:
        h.update(struct.pack('<I',len(p.vertices)))
        h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
    for uv in ob.data.uv_layers:
        h.update(uv.name.encode())
        for loop in uv.data:h.update(struct.pack('<2f',*loop.uv))
    return (len(ob.data.vertices),len(ob.data.edges),len(ob.data.polygons),h.hexdigest())

def vector(info,key):return Vector(info[key])

def move_center(world,info):
    center=vector(info,'center')*S;shift=vector(info,'shift')*S
    q=world-center
    return center+shift+vector(info,'axis')*q.dot(vector(info,'axis'))+vector(info,'new_across')*(q.dot(vector(info,'across'))*info['width_scale'])+vector(info,'new_normal')*q.dot(vector(info,'normal'))

def rotate_offset(v,info):
    return vector(info,'axis')*v.dot(vector(info,'axis'))+vector(info,'new_across')*v.dot(vector(info,'across'))+vector(info,'new_normal')*v.dot(vector(info,'normal'))

changed=[]
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    part=ob.get('part_id','')
    target='chain_'+part.split('_',1)[1] if part.startswith('weld_') else part
    if target not in solution['parts']:continue
    before=invariant(ob);info=solution['parts'][target];mw=ob.matrix_world.copy();inv=mw.inverted()
    if part.startswith('weld_'):
        for v in ob.data.vertices:v.co=inv@move_center(mw@v.co,info)
    else:
        level=ob['lod_level'];sectors=(14,10,8)[level]
        count=(len(ob.data.vertices)-(2 if part.startswith('eye_') else 0))//sectors
        radius_scale=info['wire_radius_px']/(7. if part.startswith('eye_') else 8.7)
        for ring in range(count):
            indices=range(ring*sectors,(ring+1)*sectors)
            worlds=[mw@ob.data.vertices[i].co for i in indices]
            center=sum(worlds,Vector())/sectors;newcenter=move_center(center,info)
            for i,world in zip(indices,worlds):
                ob.data.vertices[i].co=inv@(newcenter+rotate_offset(world-center,info)*radius_scale)
        for i in range(count*sectors,len(ob.data.vertices)):
            v=ob.data.vertices[i];v.co=inv@move_center(mw@v.co,info)
    ob.data.update()
    after=invariant(ob)
    assert before==after,(ob.name,'topology or UV changed')
    ob['chain_clearance_revision']='Optimized centerline pose; all source topology and UVs preserved.'
    changed.append({'object':ob.name,'invariant':before})

# A weld follows its link centerline, but its radial cross-section must not
# inherit the link-hole width stretch. Rebuild the same torus vertices/UVs.
for weld in [o for o in bpy.data.objects if o.type=='MESH' and o.get('part_id','').startswith('weld_')]:
    before=invariant(weld); level=weld['lod_level']; target='chain_'+weld['part_id'].split('_')[1]
    chain=next(o for o in bpy.data.objects if o.get('part_id')==target and o.get('lod_level')==level)
    sections=(14,10,8)[level]; mw=chain.matrix_world
    centers=[sum((mw@chain.data.vertices[j+k].co for k in range(sections)),Vector())/sections for j in range(0,len(chain.data.vertices),sections)]
    wm=weld.matrix_world; inv=wm.inverted()
    wanted=sum((wm@v.co for v in weld.data.vertices),Vector())/len(weld.data.vertices)
    choices=[]
    for a,b in zip(centers,centers[1:]+centers[:1]):
        line=b-a; t=max(0.,min(1.,(wanted-a).dot(line)/line.length_squared)); co=a+t*line
        choices.append(((wanted-co).length,co,line.normalized()))
    _,co,tan=min(choices,key=lambda x:x[0])
    n=vector(solution['parts'][target],'new_normal'); n=(n-tan*n.dot(tan)).normalized(); across=tan.cross(n).normalized()
    major=(24,16,12)[level]; minor=(6,5,4)[level]
    radius=solution['parts'][target]['wire_radius_px']*S+.000025
    for j in range(major):
        theta=math.tau*j/major; radial=n*math.cos(theta)+across*math.sin(theta)
        for k in range(minor):
            phi=math.tau*k/minor
            weld.data.vertices[j*minor+k].co=inv@(co+radial*(radius+.00012*math.cos(phi))-tan*(.00012*math.sin(phi)))
    weld.data.update(); assert before==invariant(weld)

rig=bpy.data.objects.get('Nunchucks_Rig')
if rig:
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for part,info in solution['parts'].items():
        if not part.startswith('chain_'):continue
        bone=rig.data.edit_bones[part]
        bone.head=move_center(bone.head,info);bone.tail=move_center(bone.tail,info)
        bone.align_roll(vector(info,'new_normal'))
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    rig.select_set(False)

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(DESTINATION))
(WORK/'chain_resolution_report.json').write_text(json.dumps({'source':str(SOURCE),'saved':str(DESTINATION),'all_topology_and_uv_invariants_preserved':True,'changed_parts':changed,'solution':solution},indent=2))
print('RESOLVED_CHAIN_SAVED',str(DESTINATION),flush=True)
