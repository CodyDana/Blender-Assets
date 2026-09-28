"""Build Snow Flower from the user's reference, with editable physical relief.
All output paths are isolated from the Jin Mu-Won character project.
"""
from pathlib import Path
from collections import defaultdict
import bpy, bmesh, math, random, json, hashlib
from mathutils import Vector, Quaternion

ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
ASSET=ROOT/'Assets/SnowFlower';WORK=ROOT/'WorkFiles/SnowFlower';RENDER=ROOT/'Renders/SnowFlower'
for p in (ASSET,WORK,RENDER):p.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
rng=random.Random(918206)
parts={};materials={};collections={}

def collection(name):
    if name not in collections:
        c=bpy.data.collections.new(name);scene.collection.children.link(c);collections[name]=c
    return collections[name]

def mat(name,color,metal,rough,noise_scale=180,bump=.000015):
    m=bpy.data.materials.new('M_SnowFlower_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=noise_scale;noise.inputs['Detail'].default_value=3
    l.new(tex.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[1].position=.8
    ramp.color_ramp.elements[0].color=(*(v*.91 for v in color),1);ramp.color_ramp.elements[1].color=(*(min(1,v*1.07) for v in color),1)
    l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    r=n.new('ShaderNodeMapRange');r.inputs['From Min'].default_value=0;r.inputs['From Max'].default_value=1
    r.inputs['To Min'].default_value=max(.05,rough-.025);r.inputs['To Max'].default_value=min(.98,rough+.035)
    l.new(noise.outputs['Fac'],r.inputs['Value']);l.new(r.outputs['Result'],bs.inputs['Roughness'])
    micro=n.new('ShaderNodeTexNoise');micro.inputs['Scale'].default_value=noise_scale*9;micro.inputs['Detail'].default_value=2
    l.new(tex.outputs['Object'],micro.inputs['Vector'])
    b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.16;b.inputs['Distance'].default_value=bump
    l.new(micro.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],bs.inputs['Normal'])
    if name=='Leather':
        micro.inputs['Scale'].default_value=2400;b.inputs['Strength'].default_value=.55;b.inputs['Distance'].default_value=.00012
        bs.inputs['Specular IOR Level'].default_value=.12
    if name=='Silk':bs.inputs['Specular IOR Level'].default_value=.16
    if name in ('BladeEdge','Silver','Inlay'):
        anisotropy=bs.inputs.get('Anisotropic IOR Level') or bs.inputs.get('Anisotropic')
        if anisotropy:anisotropy.default_value=.32
    materials[name]=m;return m

mat('BlackenedSteel',(.040,.046,.050),1,.38,300,.000014)
mat('BladeEdge',(.40,.43,.45),1,.32,500,.000008)
mat('Silver',(.44,.45,.44),1,.31,650,.000009)
mat('Inlay',(.40,.415,.42),1,.34,700,.000009)
mat('Leather',(.008,.009,.010),0,.58,180,.00009)
mat('Silk',(.011,.013,.017),0,.39,240,.000018)
mat('Recess',(.012,.017,.023),.85,.40,110,.000012)

exec((ROOT/'Scripts/SnowFlower/metal_finish_revision.py').read_text(encoding='utf-8'),globals())

def buffer(name,material,group):
    key=(name,material,group)
    if key not in parts:parts[key]={'v':[],'f':[]}
    return parts[key]

def add(name,material,group,vs,fs):
    p=buffer(name,material,group);offset=len(p['v']);p['v'].extend([tuple(v) for v in vs]);p['f'].extend([tuple(i+offset for i in f) for f in fs])

def tube(name,points,radius,material='Silver',group='03_FloralRelief',sides=6,closed=False):
    points=[Vector(p) for p in points];vs=[];fs=[];previous=None
    for i,p in enumerate(points):
        tangent=(points[(i+1)%len(points)]-points[i-1] if closed else points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
        axis=tangent.cross(Vector((0,1,0)))
        if axis.length<.001:axis=tangent.cross(Vector((1,0,0)))
        axis.normalize()
        if previous is not None and axis.dot(previous)<0:axis=-axis
        previous=axis.copy();axis2=tangent.cross(axis).normalized()
        rr=radius(i/max(1,len(points)-1)) if callable(radius) else radius
        for k in range(sides):
            a=math.tau*k/sides;vs.append(p+rr*(axis*math.cos(a)+axis2*math.sin(a)))
    for i in range(len(points) if closed else len(points)-1):
        j=(i+1)%len(points)
        for k in range(sides):fs.append((i*sides+k,j*sides+k,j*sides+(k+1)%sides,i*sides+(k+1)%sides))
    if not closed:fs.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+k for k in range(sides))])
    add(name,material,group,vs,fs)

def ellipsoid(name,center,a,b,c,material,group,segments=12,rings=6):
    center=Vector(center);a,b,c=Vector(a),Vector(b),Vector(c);vs=[center+c];fs=[]
    for j in range(1,rings):
        phi=math.pi*j/rings
        for i in range(segments):
            theta=math.tau*i/segments;vs.append(center+math.sin(phi)*(a*math.cos(theta)+b*math.sin(theta))+c*math.cos(phi))
    bottom=len(vs);vs.append(center-c)
    for i in range(segments):fs.append((0,1+i,1+(i+1)%segments))
    for j in range(rings-2):
        for i in range(segments):a0=1+j*segments+i;b0=1+j*segments+(i+1)%segments;fs.append((a0,a0+segments,b0+segments,b0))
    for i in range(segments):fs.append((bottom,1+(rings-2)*segments+(i+1)%segments,1+(rings-2)*segments+i))
    add(name,material,group,vs,fs)

def bezier(points,steps=24):
    a,b,c,d=map(Vector,points)
    return [(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for t in [i/steps for i in range(steps+1)]]

def flower(name,center,radius,normal=(0,-1,0),phase=0,group='03_FloralRelief',large=False):
    C=Vector(center);N=Vector(normal).normalized();U=Vector((1,0,0))
    if abs(N.dot(U))>.9:U=Vector((0,1,0))
    U=(U-N*U.dot(N)).normalized();V=N.cross(U).normalized()
    for k in range(5):
        angle=phase+math.tau*k/5;R=U*math.cos(angle)+V*math.sin(angle);T=N.cross(R)
        pc=C+R*(radius*.50)+N*(radius*.025)
        ellipsoid(name+'_Petals',pc,R*(radius*.51),T*(radius*.32),N*(radius*.105),'Inlay',group,16 if large else 8,8 if large else 4)
        loop=[]
        for j in range(28 if large else 14):
            th=math.tau*j/(28 if large else 14)
            loop.append(pc+R*(radius*.495*math.cos(th))+T*(radius*.309*math.sin(th))+N*(radius*.027))
        tube(name+'_PetalRims',loop,radius*(.024 if large else .024),'Silver',group,6 if large else 4,True)
        vein=[C+R*radius*t+N*radius*(.115-.05*t) for t in (.12,.30,.55,.76)]
        tube(name+'_Veins',vein,radius*.009,'Recess',group,4)
    ellipsoid(name+'_Center',C+N*radius*.11,U*radius*.15,V*radius*.15,N*radius*.09,'Recess',group,10,5)
    for i in range(7):
        a=math.tau*i/7;p=C+(U*math.cos(a)+V*math.sin(a))*radius*.17+N*radius*.18
        ellipsoid(name+'_Stamens',p,U*radius*.053,V*radius*.053,N*radius*.05,'Silver',group,8 if large else 6,4)

exec((ROOT/'Scripts/SnowFlower/floral_revision.py').read_text(encoding='utf-8'),globals())

def blade_shape(z):
    t=max(0,min(1,(z-.146)/.939));s=max(0,(t-.69)/.31)
    center=.0005*t+.030*s*s
    width=.046*(1-.075*t)*(1-.999*s**2.65)
    half=.0030*(1-.67*t)
    return center,max(.00008,width),half

cross=[(-.5,.045),(-.36,.82),(-.13,1.0),(.20,.92),(.39,.69),(.5,.045)]
zs=[.142,.146,.158,.19,.27,.38,.50,.62,.73,.80,.86,.92,.975,1.02,1.051,1.071,1.081,1.085]
vs=[];fs=[];mats=[]
for z in zs:
    center,width,half=blade_shape(z)
    for x,d in cross:vs.append((center+x*width,-d*half,z))
    for x,d in reversed(cross[1:-1]):vs.append((center+x*width,d*half,z))
N=10
for j in range(len(zs)-1):
    for k in range(N):
        fs.append((j*N+k,(j+1)*N+k,(j+1)*N+(k+1)%N,j*N+(k+1)%N));mats.append('BladeEdge' if k in (0,4,5,9) else 'BlackenedSteel')
fs += [tuple(reversed(range(N))),tuple((len(zs)-1)*N+i for i in range(N))];mats+=['BladeEdge','BladeEdge']
# Keep facet borders shared in one mesh. Assign the polished bevels per face.
mesh=bpy.data.meshes.new('SnowFlower_BladeMesh');mesh.from_pydata(vs,[],fs);mesh.update()
obj=bpy.data.objects.new('SF_Blade',mesh);collection('01_Blade').objects.link(obj)
for m in ('BlackenedSteel','BladeEdge'):mesh.materials.append(materials[m])
for p,m in zip(mesh.polygons,mats):p.material_index=0 if m=='BlackenedSteel' else 1;p.use_smooth=False
obj['sf_part']='Blade';obj['sf_export']=True

def surface(x,z,side):
    center,width,half=blade_shape(z);u=(x-center)/width
    depth=cross[0][1]
    for (a,da),(b,db) in zip(cross,cross[1:]):
        if a<=u<=b:depth=da+(db-da)*(u-a)/(b-a);break
    return side*(depth*half+.00012)

exec((ROOT/'Scripts/SnowFlower/blade_revision.py').read_text(encoding='utf-8'),globals())

def extrude(name,outline,depth,material,group,cy=0):
    vs=[(x,cy-depth/2,z) for x,z in outline]+[(x,cy+depth/2,z) for x,z in outline];n=len(outline)
    fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n));add(name,material,group,vs,fs)

exec((ROOT/'Scripts/SnowFlower/guard_revision.py').read_text(encoding='utf-8'),globals())

def collar(name,z,rx,ry,height,material,group='04_Grip',segments=48):
    v=[];f=[]
    rows=[(z-height/2,rx*.95,ry*.95),(z-height*.33,rx,ry),(z+height*.33,rx,ry),(z+height/2,rx*.95,ry*.95)]
    for zz,xx,yy in rows:
        for i in range(segments):a=math.tau*i/segments;v.append((math.cos(a)*xx,math.sin(a)*yy,zz))
    for j in range(3):
        for i in range(segments):f.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
    f += [tuple(reversed(range(segments))),tuple(3*segments+i for i in range(segments))];add(name,material,group,v,f)

exec((ROOT/'Scripts/SnowFlower/hilt_revision.py').read_text(encoding='utf-8'),globals())

exec((ROOT/'Scripts/SnowFlower/tassel_revision.py').read_text(encoding='utf-8'),globals())

# Consolidated named components keep the scene usable while retaining editability.
for (name,material,group),p in parts.items():
    me=bpy.data.meshes.new(name+'Mesh');me.from_pydata(p['v'],[],p['f']);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);collection(group).objects.link(ob);me.materials.append(materials[material])
    for poly in me.polygons:poly.use_smooth=True
    ob['sf_export']=True;ob['sf_part']=group;ob['sf_material']=material
    if group=='06_Tassel':ob['sf_secondary_motion_candidate']=True
    if name in ('SF_Guard_Wings',):
        bevel=ob.modifiers.new('Small forged edge bevel','BEVEL');bevel.width=.00032;bevel.segments=3
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=bevel.name)
        for poly in ob.data.polygons:poly.use_smooth=False

# Recalculate blade winding after its asymmetric cross section is complete.
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
exec((ROOT/'Scripts/SnowFlower/uv_helpers.py').read_text(encoding='utf-8'),globals())

asset_objects=[o for o in scene.objects if o.type=='MESH']
for ob in asset_objects:
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
    repair_collapsed_uv(ob.data)

root=bpy.data.objects.new('SnowFlower_GripOrigin',None);collection('00_Attachment').objects.link(root);root.empty_display_size=.028
for ob in asset_objects:ob.parent=root
for name,location in [('Socket_MainHand',(0,0,0)),('Socket_OffHand',(0,0,-.07)),('Socket_BladeTip',(.0305,0,1.085)),('Socket_TasselRoot',(-.018,0,-.148))]:
    e=bpy.data.objects.new(name,None);collection('00_Attachment').objects.link(e);e.location=location;e.empty_display_type='ARROWS';e.empty_display_size=.018;e.parent=root

scene['asset']='Snow Flower — reference revision 3'
scene['revision']=3;scene['reference']='References/SnowFlower/SnowFlower_user_reference.png'
scene['working_overall_length_m']=1.25;scene['attachment_origin']='Center of grip; blade extends along local +Z'
scene.world=bpy.data.worlds.new('SnowFlower_StudioWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.48,.52,.58,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.22
wn=scene.world.node_tree.nodes;wl=scene.world.node_tree.links
wlight=wn.new('ShaderNodeLightPath');wmix=wn.new('ShaderNodeMixShader');wback=wn.new('ShaderNodeBackground')
wback.inputs['Color'].default_value=(1,1,1,1);wback.inputs['Strength'].default_value=4
wl.new(wlight.outputs['Is Camera Ray'],wmix.inputs[0]);wl.new(wn.get('Background').outputs[0],wmix.inputs[1]);wl.new(wback.outputs[0],wmix.inputs[2]);wl.new(wmix.outputs[0],wn.get('World Output').inputs[0])
studio=collection('STUDIO_ExcludeFromExport')
for name,location,power,size,color in [
    ('Key',(-1.1,-1.3,.7),40,1.1,(1,.97,.93)),('Strip',(1,-.7,.5),50,.7,(.83,.91,1)),
    ('Rim',(.5,.8,.55),65,1.1,(1,1,1)),('Top',(-.1,-.4,1.7),25,.5,(1,.97,.92)),('PommelFill',(.10,-.25,-.48),7,.40,(1,.98,.94))]:
    light=bpy.data.lights.new(name,'AREA');ob=bpy.data.objects.new(name,light);studio.objects.link(ob);ob.location=location
    light.energy=power;light.shape='RECTANGLE';light.size=size;light.size_y=size*.65;light.color=color
    ob.rotation_euler=(Vector((0,0,.40))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('SnowFlower_ReviewCamera',bpy.data.cameras.new('SnowFlower_ReviewCamera'));studio.objects.link(cam);scene.camera=cam;cam.data.clip_start=.001
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type!='CPU'
    scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-.30
try:scene.view_settings.look='AgX - Medium High Contrast'
except Exception:pass
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False

def render(name,loc,target,scale,w,h,flip=True):
    cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.location=loc
    rotation=(Vector(target)-cam.location).to_track_quat('-Z','Y')
    if flip:rotation=rotation@Quaternion((0,0,1),math.pi)
    cam.rotation_euler=rotation.to_euler();scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
    scene.render.filepath=str(RENDER/(name+'.png'));bpy.ops.render.render(write_still=True)

cam.data.type='ORTHO';cam.data.ortho_scale=1.43;cam.location=(0,-3,.458)
cam.rotation_euler=((Vector((0,0,.458))-cam.location).to_track_quat('-Z','Y')@Quaternion((0,0,1),math.pi)).to_euler()
scene.render.resolution_x=1000;scene.render.resolution_y=1600;scene.render.filepath=str(RENDER/'SnowFlower_Front.png')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'SnowFlower_Master.blend'))
report={'source_reference_sha256':hashlib.sha256((ROOT/'References/SnowFlower/SnowFlower_user_reference.png').read_bytes()).hexdigest(),
        'objects':{},'working_dimensions_m':{'overall':1.25,'blade':.939,'guard_span':.126,'grip':.260},
        'origin':'Grip center; blade +Z; front -Y','scope':'Sword and tassel; no scabbard; independent from character.'}
for ob in asset_objects:
    ob.data.calc_loop_triangles();report['objects'][ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles),'materials':[m.name for m in ob.data.materials]}
report['triangles']=sum(x['triangles'] for x in report['objects'].values())
(WORK/'build_report.json').write_text(json.dumps(report,indent=2))
render('SnowFlower_Front',(0,-3,.458),(0,0,.458),1.39,900,1600)
render('SnowFlower_Back',(0,3,.458),(0,0,.458),1.39,900,1600)
render('SnowFlower_Oblique',(.65,-3,.66),(0,0,.458),1.39,1000,1600)
render('SnowFlower_Guard',(.065,-.60,.090),(0,0,.128),.166,1300,1100)
render('SnowFlower_BladeDetail',(.06,-.45,.50),(0,0,.44),.27,1100,1400)
render('SnowFlower_Pommel',(.057,-.065,-.235),(0,0,-.152),.080,1200,1100,False)
render('SnowFlower_Side',(3,0,.458),(0,0,.458),1.39,650,1600)
print('SNOW_FLOWER_BUILD_COMPLETE',report['triangles'],flush=True)
