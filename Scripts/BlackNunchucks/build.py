"""Black nunchucks built from measured front-reference landmarks.
Creates independent handle, cap, attachment and chain geometry with analytic UVs.
"""
from pathlib import Path
import bpy,bmesh,math,sys,json,hashlib,os
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'WorkFiles/BlackNunchucks';REND=ROOT/'Renders/BlackNunchucks'
sys.path.insert(0,str(ROOT/'Scripts/pipeline'));from lock import assert_owner
assert_owner('BlackNunchucks','codex')
sys.path.insert(0,str(ROOT/'Scripts/BlackNunchucks'));from materials import create_materials
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
asset=bpy.data.collections.new('BLACK_NUNCHUCKS');s.collection.children.link(asset)
studio=bpy.data.collections.new('STUDIO_ExcludeFromExport');s.collection.children.link(studio)
grip,steel=create_materials();S=.00030;TAU=math.tau
parts=[];CHARTS={};UV_LOOPS={};BONES={};HANDLES={}

def P(x,y,depth=0):return Vector(((x-627)*S,depth,(1195-y)*S))
def chart(key,w,h):CHARTS[key]=(max(w,.0005),max(h,.0005));return key
def mesh(part,verts,faces,faceuvs,mat,level,bone,component,matrix=None):
    me=bpy.data.meshes.new(part+'_mesh');me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(f'SM_BlackNunchucks_{part}_LOD{level}',me);asset.objects.link(ob)
    ob.data.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    uv=me.uv_layers.new(name='UVMap')
    UV_LOOPS[ob.name]=faceuvs
    for p,uvf in zip(me.polygons,faceuvs):
        for li,(key,u,v) in zip(p.loop_indices,uvf):uv.data[li].uv=(u,v)
    if matrix is not None:ob.matrix_world=matrix
    ob['part_id']=part;ob['lod_level']=level;ob['bone_name']=bone;ob['component']=component
    ob.hide_render=level!=0;ob.hide_set(level!=0)
    parts.append(ob);return ob

def lathe(part,profile,n,mat,level,bone,component,transform):
    verts=[];faces=[];uvs=[];arc=[0.0]
    for i in range(1,len(profile)):arc.append(arc[-1]+math.dist(profile[i],profile[i-1]))
    maxr=max(r for z,r in profile);side=chart(part+'_side',TAU*maxr,arc[-1])
    for z,r in profile:
        for i in range(n):
            a=TAU*i/n;verts.append((r*math.cos(a),r*math.sin(a),z))
    for j in range(len(profile)-1):
        for i in range(n):
            i2=(i+1)%n;faces.append((j*n+i,j*n+i2,(j+1)*n+i2,(j+1)*n+i))
            u0=i/n;u1=(i+1)/n;v0=arc[j]/arc[-1];v1=arc[j+1]/arc[-1]
            uvs.append([(side,u0,v0),(side,u1,v0),(side,u1,v1),(side,u0,v1)])
    for end in (0,len(profile)-1):
        z,r=profile[end];key=chart(part+('_bottom' if end==0 else '_top'),2*r,2*r)
        ci=len(verts);verts.append((0,0,z))
        for i in range(n):
            inds=(ci,end*n+(i+1)%n,end*n+i) if end==0 else (ci,end*n+i,end*n+(i+1)%n)
            faces.append(inds);tu=[]
            for ix in inds:
                x,y,_=verts[ix];tu.append((key,.5+x/(2*r),.5+y/(2*r)))
            uvs.append(tu)
    return mesh(part,verts,faces,uvs,mat,level,bone,component,transform)

def tube(part,points,tangents,radius,segments,mat,level,bone,component,closed=True,transform=None):
    vs=[];fs=[];uvs=[];lengths=[0]
    for j in range(1,len(points)):lengths.append(lengths[-1]+(Vector(points[j])-Vector(points[j-1])).length)
    total=lengths[-1]+((Vector(points[-1])-Vector(points[0])).length if closed else 0)
    key=chart(part+'_tube',max(total,.001),TAU*radius)
    plane=None
    for tv in tangents[1:]:
        cross=Vector(tangents[0]).cross(Vector(tv))
        if cross.length>.0001:plane=cross.normalized();break
    if plane is None:plane=Vector((0,1,0))
    for j,co in enumerate(points):
        t=Vector(tangents[j]).normalized();b=t.cross(plane).normalized();n=t.cross(b).normalized()
        for k in range(segments):
            a=TAU*k/segments;vs.append(Vector(co)+radius*(math.cos(a)*b+math.sin(a)*n))
    count=len(points)
    for j in range(count if closed else count-1):
        j2=(j+1)%count;u0=lengths[j]/total;u1=lengths[j2]/total if j2 else 1
        for k in range(segments):
            k2=(k+1)%segments;fs.append((j*segments+k,j*segments+k2,j2*segments+k2,j2*segments+k))
            uvs.append([(key,u0,k/segments),(key,u0,(k+1)/segments),(key,u1,(k+1)/segments),(key,u1,k/segments)])
    if not closed:
        for end in (0,count-1):
            capkey=chart(part+f'_end{end}',2*radius,2*radius)
            ci=len(vs);vs.append(Vector(points[end]))
            for k in range(segments):
                seq=[k,(k+1)%segments] if end==count-1 else [(k+1)%segments,k]
                fs.append((ci,end*segments+seq[0],end*segments+seq[1]))
                uvs.append([(capkey,.5,.5)]+[(capkey,.5+.5*math.cos(TAU*i/segments),.5+.5*math.sin(TAU*i/segments)) for i in seq])
    return mesh(part,vs,fs,uvs,mat,level,bone,component,transform)

def racetrack(u,half_length,half_width):
    b=half_width;c=half_length-b;arc=math.pi*b;line=2*c;total=2*(arc+line);q=(u%1)*total
    if q<arc:
        a=-math.pi/2+q/b;return Vector((c+b*math.cos(a),b*math.sin(a))),Vector((-math.sin(a),math.cos(a)))
    q-=arc
    if q<line:return Vector((c-q,b)),Vector((-1,0))
    q-=line
    if q<arc:
        a=math.pi/2+q/b;return Vector((-c+b*math.cos(a),b*math.sin(a))),Vector((-math.sin(a),math.cos(a)))
    q-=arc;return Vector((-c+q,-b)),Vector((1,0))

# Pixel-space axes. A shallow depth lean exposes the top-cap ellipses.
for side,base,top in [('L',(258,1181),(464.5,196)),('R',(989,1183),(772.7,196))]:
    a=P(*base,0);b=P(*top,-.014);axis=(b-a).normalized();length=(b-a).length
    xx=(Vector((1,0,0))-axis*axis.x).normalized();yy=axis.cross(xx).normalized()
    rot=Matrix((xx,yy,axis)).transposed().to_4x4();rot.translation=a
    HANDLES[side]=(a,b,length,rot);BONES['handle_'+side]=(a,b)
    for level,n in [(0,112),(1,64),(2,32)]:
        join=length-.0300
        prof=[(.011*(1-math.cos(math.radians(a))),.0097+.011*math.sin(math.radians(a))) for a in (0,15,30,45,60,75,90)]
        prof +=[(.020,.02055)]
        prof += [(z,.02055+(.01690-.02055)*(z-.02)/(join-.02)) for z in [.055,.105,.155,.205,join-.002]]
        prof += [(join-.0007,.01690),(join,.01675)]
        lathe('grip_'+side,prof,n,grip,level,'handle_'+side,'handle',rot)
        cap=[(join-.00020,.01660),(join+.00020,.01688),(join+.00075,.01697),
             (length-.0012,.01697),(length-.00045,.01685),(length,.01635)]
        lathe('cap_'+side,cap,n,steel,level,'handle_'+side,'handle',rot)
        # Fixed cap eye: an anchored U with the lower rails sunk into the cap.
        points=[];tangents=[];rr=.0044;h=.009;tilt=math.radians(53 if side=='L' else -53)
        ex=Vector((math.cos(tilt),math.sin(tilt),0));ez=Vector((0,0,1))
        samples=(14,10,7)[level]
        for j in range(samples):
            t=j/samples;points.append(ex*rr+ez*(length-.0008+t*(h+.0008)));tangents.append(ez)
        for j in range(samples*2+1):
            ang=math.pi*j/(samples*2);points.append(ex*(rr*math.cos(ang))+ez*(length+h+rr*math.sin(ang)));tangents.append(-ex*math.sin(ang)+ez*math.cos(ang))
        for j in range(1,samples+1):
            t=j/samples;points.append(-ex*rr+ez*(length+h-t*(h+.0008)));tangents.append(-ez)
        tube('eye_'+side,points,tangents,.0021,(14,10,8)[level],steel,level,'handle_'+side,'attachment',False,rot)

links=[(477,157,-73,78,52,18),(513,117,-47,88,60,75),(560,85,-22,94,60,0),
       (623,77,0,94,60,-65),(686,85,22,94,60,0),(732,117,47,88,60,-75),(764,157,73,78,52,-18)]
for index,(px,py,deg,long_px,wide_px,roll) in enumerate(links,1):
    phi=math.radians(deg);psi=math.radians(roll);axis=Vector((math.cos(phi),0,-math.sin(phi)))
    across=Vector((math.sin(phi),0,math.cos(phi)))*math.cos(psi)+Vector((0,1,0))*math.sin(psi)
    center=P(px,py,-.0165);wire=8.7*S;a=(long_px*S-2*wire)/2;b=(wide_px*S-2*wire)/2
    BONES[f'chain_{index:02d}']=(center-axis*a,center+axis*a)
    for level,count,sides in [(0,76,14),(1,48,10),(2,32,8)]:
        pts=[];tans=[]
        for j in range(count):
            v,t=racetrack(j/count,a,b);pts.append(center+axis*v.x+across*v.y);tans.append(axis*t.x+across*t.y)
        tube(f'chain_{index:02d}',pts,tans,wire,sides,steel,level,f'chain_{index:02d}','chain')
        if index in (3,4,5):
            v,t=racetrack(.29 if index!=5 else .79,a,b);co=center+axis*v.x+across*v.y;tan=(axis*t.x+across*t.y).normalized()
            nn=axis.cross(across).normalized();bb=tan.cross(nn).normalized();wp=[];wt=[]
            for j in range((24,16,12)[level]):
                ang=TAU*j/(24,16,12)[level];wp.append(co+(wire+.000025)*(nn*math.cos(ang)+bb*math.sin(ang)));wt.append(-nn*math.sin(ang)+bb*math.cos(ang))
            tube(f'weld_{index:02d}',wp,wt,.00012,(6,5,4)[level],steel,level,f'chain_{index:02d}','chain')

# Shelf-pack charts once in physical units. Every LOD uses identical rectangles.
# A shared scale gives consistent texel density; all charts have 16 px gutters.
def try_pack(scale):
    margin=16/2048;items=sorted(CHARTS.items(),key=lambda t:max(t[1]),reverse=True)
    rows=[];result={}
    for key,(w,h) in items:
        # Tall sides stay vertical; short tube strips are oriented horizontally.
        ww=w*scale+2*margin;hh=h*scale+2*margin
        choice=None
        for ri,row in enumerate(rows):
            if hh<=row['height'] and row['x']+ww<=1:
                choice=ri;break
        if choice is None:
            y=sum(row['height'] for row in rows)
            if ww>1 or y+hh>1:return None
            rows.append({'x':0.,'y':y,'height':hh});choice=len(rows)-1
        row=rows[choice];result[key]=(row['x']+margin,row['y']+margin,w*scale,h*scale);row['x']+=ww
    return result
lo,hi=0.1,10
for _ in range(35):
    mid=(lo+hi)/2
    if try_pack(mid) is None:hi=mid
    else:lo=mid
packed=try_pack(lo*.996)
for ob in parts:
    for poly,uvf in zip(ob.data.polygons,UV_LOOPS[ob.name]):
        for li,(key,u,v) in zip(poly.loop_indices,uvf):
            x,y,w,h=packed[key];ob.data.uv_layers[0].data[li].uv=(x+u*w,y+v*h)
    ob.data.uv_layers.new(name='LightmapUV',do_init=True)
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    # Recalculate closed mesh normals without altering the chart loops.
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()

# A simple rigid-part rig makes both handles and all chain links poseable.
rig=bpy.data.objects.new('Nunchucks_Rig',bpy.data.armatures.new('Nunchucks_Rig_Data'));asset.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
root=rig.data.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,0,.02);root.use_deform=True
order=['handle_L']+[f'chain_{i:02d}' for i in range(1,8)]+['handle_R']
parent=root
for name in order:
    bone=rig.data.edit_bones.new(name);bone.head,bone.tail=BONES[name];bone.parent=parent;bone.use_connect=False;bone.use_deform=True;parent=bone
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.hide_render=True;rig.show_in_front=True
for ob in parts:
    group=ob.vertex_groups.new(name=ob['bone_name']);group.add(list(range(len(ob.data.vertices))),1,'REPLACE')
    mod=ob.modifiers.new('Rigid part articulation','ARMATURE');mod.object=rig
    ob['surface_note']='Analytic bevels and circular profiles; baked procedural finish in final asset.'

def place(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    studio.objects.link(obj)
def area(name,loc,energy,size,sy,target):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='RECTANGLE';d.size=size;d.size_y=sy
    o=bpy.data.objects.new(name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Key_Softbox',(-.25,-.43,.40),.75,.13,.46,(0,0,.17))
area('Right_Softbox',(.34,-.18,.33),.42,.10,.42,(0,0,.17))
area('Top_Fill',(-.05,.15,.56),.55,.35,.28,(0,0,.17))
ground=min((o.matrix_world@v.co).z for o in parts if o['lod_level']==0 for v in o.data.vertices)-.00005
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,ground));floor=bpy.context.object;floor.name='StudioFloor';place(floor)
fm=bpy.data.materials.new('M_StudioWhite');fm.diffuse_color=(.92,.92,.92,1);fm.use_nodes=True;fm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.92,.92,.92,1);fm.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.8;floor.data.materials.append(fm)
# White product-shot floor with geometry-derived contact occlusion; the
# camera-only branch contributes no extra illumination to the black material.
fn=fm.node_tree.nodes;fl=fm.node_tree.links;ao=fn.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=.008;ao.samples=32
em=fn.new('ShaderNodeEmission');fl.new(ao.outputs['Color'],em.inputs['Color'])
fpath=fn.new('ShaderNodeLightPath');fmix=fn.new('ShaderNodeMixShader');fl.new(fpath.outputs['Is Camera Ray'],fmix.inputs[0]);fl.new(fn.get('Principled BSDF').outputs[0],fmix.inputs[1]);fl.new(em.outputs[0],fmix.inputs[2]);fl.new(fmix.outputs[0],fn.get('Material Output').inputs[0])
world=bpy.data.worlds.new('Nunchucks_StudioWorld');s.world=world;world.use_nodes=True
wn=world.node_tree.nodes;wl=world.node_tree.links;amb=wn.get('Background');amb.inputs[0].default_value=(1,1,1,1);amb.inputs[1].default_value=.12
white=wn.new('ShaderNodeBackground');white.inputs[0].default_value=(1,1,1,1);white.inputs[1].default_value=1
lp=wn.new('ShaderNodeLightPath');mix=wn.new('ShaderNodeMixShader');wl.new(lp.outputs['Is Camera Ray'],mix.inputs[0]);wl.new(amb.outputs[0],mix.inputs[1]);wl.new(white.outputs[0],mix.inputs[2]);wl.new(mix.outputs[0],wn.get('World Output').inputs[0])
cam=bpy.data.objects.new('Nunchucks_Camera',bpy.data.cameras.new('Nunchucks_Camera'));studio.objects.link(cam);s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU';s.view_settings.view_transform='Standard';s.view_settings.look='None'
s.render.resolution_x=1254;s.render.resolution_y=1254;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
def camera(loc,target,scale):
    cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
camera((0,-2,(1195-627)*S+.105),(0,0,(1195-627)*S),1254*S)
s.render.filepath=str(REND/'Draft_Front.png')
s['reference']=str(ROOT/'References/BlackNunchucks/nunchucks.png');s['scale_assumption']='Approximately 30 cm handles; reference supplies no physical scale.'
s['rig_status']='Rigid individual pieces; no physics simulation or animations authored.'
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA';ar.spaces.active.overlay.show_overlays=False
rig.hide_set(True)
(WORK/'build_report.json').write_text(json.dumps({'reference_sha256':hashlib.sha256((ROOT/'References/BlackNunchucks/nunchucks.png').read_bytes()).hexdigest(),'charts':packed,'texel_density_px_cm':lo*.996*2048/100,'parts':len(parts),'links':7,'scale_m_per_pixel':S,'bones':list(BONES)},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'BlackNunchucks_procedural.blend'))
bpy.ops.render.render(write_still=True)
camera((0,-1,.354),(0,0,.325),.143);s.render.filepath=str(REND/'Draft_Chain.png');s.render.resolution_x=1400;s.render.resolution_y=900;bpy.ops.render.render(write_still=True)
print('NUNCHUCKS_BUILT_AND_RENDERED',flush=True)
