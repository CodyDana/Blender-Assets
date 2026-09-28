"""Editable, meter-scale black traveling cloak from Cody's supplied reference."""
from pathlib import Path
import bpy,bmesh,math,sys,json,random,hashlib
import numpy as np
from mathutils import Vector,Quaternion
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'WorkFiles/BlackCloak'
TEX=ROOT/'Textures/BlackCloak';RENDERS=ROOT/'Renders/BlackCloak'
sys.path.insert(0,str(ROOT/'Scripts/pipeline'))
from lock import assert_owner
assert_owner('BlackCloak','codex')
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
asset=bpy.data.collections.new('BLACK_CLOAK');s.collection.children.link(asset)
studio=bpy.data.collections.new('STUDIO_ExcludeFromExport');s.collection.children.link(studio)
cloth=[];hardware=[];patterns={}
TAU=math.tau
def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def lerp(a,b,t):return a+(b-a)*t

def image_save(name,array,noncolor=False):
    path=TEX/(name+'.png')
    if False and path.exists():
        im=bpy.data.images.load(str(path),check_existing=True)
    else:
        im=bpy.data.images.new(name,width=array.shape[1],height=array.shape[0],alpha=False)
        im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
        pixels=np.ones((*array.shape[:2],4),dtype=np.float32)
        if array.ndim==2:pixels[:,:,:3]=array[:,:,None]
        else:pixels[:,:,:3]=array
        im.pixels.foreach_set(pixels.ravel());im.file_format='PNG';im.filepath_raw=str(path);im.save()
        bpy.data.images.remove(im)
        im=bpy.data.images.load(str(path),check_existing=False)
    im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB';im.pack();return im

def textile():
    n=2048;y,x=np.mgrid[0:n,0:n].astype(np.float32);rng=np.random.default_rng(92723)
    field=np.zeros((n,n),np.float32)
    for k in range(38):
        fx=int(rng.integers(1,46));fy=int(rng.integers(1,46));phase=float(rng.uniform(0,TAU))
        field+=np.cos(TAU*(fx*x+fy*y)/n+phase).astype(np.float32)/(math.sqrt(fx*fx+fy*fy)+1)
    field/=max(.1,float(np.std(field)))
    warp=(.5+.5*np.cos(TAU*x/8))**2;weft=(.5+.5*np.cos(TAU*y/8))**2
    alternation=np.tanh(4*np.cos(TAU*x/16)*np.cos(TAU*y/16))
    height=(warp*(.50+.25*alternation)+weft*(.50-.25*alternation))*.000030+field*.000003
    fuzz=rng.normal(0,1,(n,n)).astype(np.float32)
    # Byte-backed generated images write these as sRGB code values. This range
    # decodes to approximately 0.01 linear reflectance, with visible yarn mottling.
    shade=np.clip(.113+field*.013+(warp+weft-1)*.014+fuzz*.0028,.065,.180)
    rgb=np.stack([shade*.96,shade,shade*.98],axis=2)
    base=image_save('T_BlackCloak_BaseColor',rgb)
    rough=image_save('T_BlackCloak_Roughness',np.clip(.87+field*.012+(warp+weft-1)*.026,.76,.96),True)
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*.128/n)
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*.128/n)
    normal=np.stack([-dx,-dy,np.ones_like(dx)],axis=2);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    normal=image_save('T_BlackCloak_Normal_OpenGL',normal*.5+.5,True)
    dx_pixels=np.empty(n*n*4,dtype=np.float32);normal.pixels.foreach_get(dx_pixels);dx_pixels=dx_pixels.reshape(n,n,4)[:,:,:3];dx_pixels[:,:,1]=1-dx_pixels[:,:,1]
    image_save('T_BlackCloak_Normal_DirectX',dx_pixels,True)
    mat=bpy.data.materials.new('M_BlackCloak_WovenWool');mat.use_nodes=True;mat.diffuse_color=(.013,.014,.0135,1)
    nt=mat.node_tree;p=nt.nodes.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.065
    p.inputs['Sheen Weight'].default_value=.035;p.inputs['Sheen Roughness'].default_value=.8
    tc=nt.nodes.new('ShaderNodeTexCoord');scale=nt.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1/.128
    nt.links.new(tc.outputs['UV'],scale.inputs[0])
    for im,socket in [(base,'Base Color'),(rough,'Roughness'),(normal,'Normal')]:
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;tex.extension='REPEAT';tex.name='Export_'+socket.replace(' ','')
        nt.links.new(scale.outputs[0],tex.inputs['Vector'])
        if socket=='Normal':
            nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.72;nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],p.inputs['Normal'])
        else:nt.links.new(tex.outputs['Color'],p.inputs[socket])
    mat['uv_units']='Meters; repeat tile every 0.128 m';return mat

fabric=textile()
def simple_material(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
metal=simple_material('M_BlackCloak_BlackenedSteel',(.040,.041,.038),.42,.85)
leather=simple_material('M_BlackCloak_CharcoalLeather',(.014,.011,.008),.66)

def mesh(name,verts,faces,uvs,mat=fabric):
    me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);asset.objects.link(ob);me.materials.append(mat)
    if uvs:
        uv=me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            for li in p.loop_indices:uv.data[li].uv=uvs[me.loops[li].vertex_index]
    for p in me.polygons:p.use_smooth=True
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob['asset']='BlackCloak';return ob

def grid(name,fn,nu,nv):
    verts=[];uv=[];faces=[]
    for j in range(nv+1):
        for i in range(nu+1):
            u=i/nu;v=j/nv;p,st=fn(u,v);verts.append(p);uv.append(st)
            if i and j:
                a=(j-1)*(nu+1)+i-1;b=j*(nu+1)+i-1;faces.append((a,a+1,b+1,b))
    ob=mesh(name,verts,faces,uv);cloth.append(ob)
    pin=ob.vertex_groups.new(name='CLOTH_Pin')
    for j in range(nv+1):pin.add(list(range(j*(nu+1),(j+1)*(nu+1))),max(0,1-(j/nv)/.17),'REPLACE')
    ob['cloth_pin_group']='CLOTH_Pin';ob['cloth_max_distance_m']=1.2
    ob['pattern_grid']=[nu,nv];patterns[name]={'columns':nu+1,'rows':nv+1,'vertices':len(verts),'quad_faces':len(faces)}
    sub=ob.modifiers.new('Tailored smooth folds','SUBSURF');sub.levels=1;sub.render_levels=1
    solid=ob.modifiers.new('Cloth thickness 1.6 mm','SOLIDIFY');solid.thickness=.0016;solid.offset=-.15;solid.use_even_offset=True
    return ob

def lower_panel(u,v):
    a=lerp(.10,TAU-.10,u);front=math.cos(a)
    shoulder=ease(v/.14)
    z=lerp(1.60,1.425,shoulder) if v<.14 else lerp(1.425,.050,(v-.14)/.86)
    t=max(0,(v-.14)/.86)
    rx=lerp(.111,.287,shoulder) if v<.14 else lerp(.287,.472,t**.85)
    ry=lerp(.099,.173,shoulder) if v<.14 else lerp(.173,.308,t**.82)
    a+=.026*math.sin(3*math.pi*v+1.7*math.sin(a))*math.sin(math.pi*v)
    amp=lerp(.0018,.038,ease(v/.50))*(.85+.20*math.sin(3*a+.5))
    wave=math.sin(12*a+.68*math.sin(3*a)+.6*v)+.31*math.sin(23*a-1.8*v)+.15*math.sin(31*a+2*v)
    fold=amp*wave
    hem=(.018*math.sin(7*a+.3)+.012*math.sin(17*a))*v**12
    z+=hem+.005*math.sin(17*a+v*9)*math.sin(math.pi*v)*ease(v/.2)
    x=(rx+fold)*math.sin(a);y=.016-(ry+fold*.75)*math.cos(a)
    # The slit fans gently away from the center toward the hem.
    edge=math.exp(-min(u,1-u)*70)
    x+=math.copysign(.020*v*v*edge,x)
    return (x,y,z),(u*2.50,v*1.62)
grid('Cloak_LongDrape',lower_panel,184,88)

def mantle_function(layer):
    def fn(u,v):
        # Open, overlapped fabric edges meet at the left shoulder clasp.
        a=lerp(-.90,TAU-.79,u);right=(math.sin(a)+1)/2;front=max(0,math.cos(a))
        if layer==0:
            bottom=1.465-.140*right-.015*front;rx=.286+.022*right;ry=.185
        elif layer==1:
            bottom=1.436-.242*right-.015*front;rx=.308+.040*right;ry=.213
        else:
            bottom=1.395-.565*right**1.38+.018*front;rx=.333+.094*right;ry=.251+.016*right
        # Short left leading edge produces the long diagonal on the right.
        zv=lerp(1.593+(2-layer)*.003,bottom,v**.87)
        depth=max(0,(1.60-zv))
        # Every layer follows the same shoulder surface, with the shorter
        # mantles placed outside it. This avoids the previous intersecting shells.
        xr=float(np.interp(depth,[0,.13,.25,.45,.80],[.108,.272,.315,.370,.437]))
        yr=float(np.interp(depth,[0,.13,.25,.45,.80],[.096,.173,.209,.254,.294]))
        layer_offset=(.024,.014,.004)[layer]*ease(v/.12)
        xr+=layer_offset;yr+=layer_offset
        wave=math.sin(a*7.0+depth*2.0)+.36*math.sin(13*a-depth)
        f=(.002+.015*min(1,depth/.35))*wave*ease(v/.16)
        # A gathered cascade runs from the clasp, not evenly spaced corrugations.
        gather=math.exp(-min(u,1-u)*8)*.010*math.sin(26*a+v*6)*v
        x=(xr+f+gather)*math.sin(a)
        y=.003-(yr+f*.7)*math.cos(a)
        zv+=.010*math.sin(a*3+.4*layer)*math.sin(math.pi*v)+.004*math.sin(a*19)*v**16
        return (x,y,zv),(u*1.60,v*(.34+.16*layer))
    return fn
# Undermost long diagonal sweep, then successively shorter capelets.
for layer in (2,1,0):grid(['Cloak_UpperMantle','Cloak_MiddleMantle','Cloak_DiagonalShawl'][layer],mantle_function(layer),144,32 if layer<2 else 48)

# Independently hanging front panels break the regular cone into overlapping
# lengths, including the reference's long diagonal right-front edge.
def crossing_panel(u,v):
    topx=lerp(-.210,-.130,u);bottomx=lerp(-.090,.423,u)
    x=lerp(topx,bottomx,v)+.048*math.sin(math.pi*v)*u
    z=lerp(1.53-.025*u,.045+.22*(1-u)**1.4,v)
    z+=.012*math.sin(u*19+.5)*v**12
    fold=(.006+.028*v)*math.sin(u*math.pi*7+.55*v)+.006*v*math.sin(u*43-2*v)
    y=-.202-.106*v-.015*math.sin(math.pi*v)+fold
    # Right edge turns outward and toward the side as it descends.
    y+=.105*u**3*v
    return (x,y,z),(u*.61,v*1.65)
grid('Cloak_OverlappingFrontPanel',crossing_panel,72,94)
def hanging_panel(u,v):
    x=lerp(lerp(-.225,-.16,u),lerp(-.472,-.232,u),v)
    z=lerp(1.534-.008*u,.030+.050*u+.014*math.sin(u*17),v)
    fold=(.004+.025*v)*math.sin(u*math.pi*5+.35*v)
    y=-.211-.100*v+fold+.035*math.sin(math.pi*v)
    return (x,y,z),(u*.34,v*1.65)
grid('Cloak_GatheredSideFall',hanging_panel,50,92)

def cowl(u,v):
    a=TAU*u+math.pi
    phase=TAU*(4.35*v+.78*math.sin(a)-.20*math.cos(a)+.09*math.sin(3*a))
    ridge=.002*math.cos(phase)*math.sin(math.pi*v)**.45
    rx=lerp(.135,.111,v)+ridge;ry=lerp(.119,.095,v)+ridge
    z=lerp(1.547,1.735,v)+.009*math.sin(a-.3)+.005*math.sin(3*a)*v
    return (rx*math.sin(a),-.013-ry*math.cos(a),z),(u*.79,v*.23)
collar=grid('Cloak_WrappedCowl',cowl,144,64);collar['cloth_max_distance_m']=.025
bm=bmesh.new();bm.from_mesh(collar.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.to_mesh(collar.data);bm.free()
for band in range(5):
    def scarf(u,v,k=band):
        a=TAU*u+math.pi
        centerz=1.568+k*.034+.018*math.sin(a-.45)-.007*math.cos(2*a)+.002*math.sin(3*a+k)
        z=centerz+(v-.48)*.049
        rx=.145-k*.006+.007*math.sin(math.pi*v);ry=.127-k*.0055+.007*math.sin(math.pi*v)
        rx+=.002*math.sin(3*a+k)*math.sin(math.pi*v)
        return (rx*math.sin(a),-.013-ry*math.cos(a),z),(u*.83,v*.054)
    wrap=grid('Cloak_ScarfWrap_%02d'%(band+1),scarf,144,14)
    wrap['cloth_max_distance_m']=.025
    bm=bmesh.new();bm.from_mesh(wrap.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.to_mesh(wrap.data);bm.free()

def tube(name,points,radius,mat=fabric,sides=6):
    vs=[];fs=[];uv=[]
    closed=(Vector(points[0])-Vector(points[-1])).length<1e-6
    if closed:points=points[:-1]
    for i,co in enumerate(points):
        p=Vector(co);t=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        n=t.cross(Vector((0,1,0))).normalized()
        if n.length<.1:n=t.cross(Vector((1,0,0))).normalized()
        b=t.cross(n).normalized()
        for k in range(sides):
            r=radius(i/(len(points)-1)) if callable(radius) else radius
            vs.append(p+r*(math.cos(TAU*k/sides)*n+math.sin(TAU*k/sides)*b));uv.append((k/sides*.008,i/max(1,len(points)-1)*.20))
            if i:fs.append(((i-1)*sides+k,(i-1)*sides+(k+1)%sides,i*sides+(k+1)%sides,i*sides+k))
    if closed:
        fs.extend([((len(points)-1)*sides+k,(len(points)-1)*sides+(k+1)%sides,(k+1)%sides,k) for k in range(sides)])
    else:fs.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+k for k in range(sides))])
    return mesh(name,vs,fs,uv,mat)

# Rolled hems stay narrow enough to read as fabric, rather than piping.
for layer in (0,1,2):
    fn=mantle_function(layer);points=[fn(i/240,1)[0] for i in range(241)]
    o=tube('Cloak_MantleHem_'+str(layer+1),points,.00072);cloth.append(o)
points=[cowl(i/220,1)[0] for i in range(221)]
cloth.append(tube('Cloak_CowlLip',points,.0010))

# Ring lies on the wearer right shoulder (viewer left), like the reference.
clasp=Vector((-.208,-.236,1.526));pts=[]
for i in range(81):
    a=TAU*i/80;pts.append(clasp+Vector((.026*math.cos(a),-.003*math.cos(a),.026*math.sin(a))))
hardware.append(tube('Clasp_BlackenedRing',pts,.0033,metal,10))
hardware.append(tube('Clasp_Pin',[clasp+Vector((-.018,-.004,-.012)),clasp+Vector((.001,-.007,.002)),clasp+Vector((.020,-.004,.017))],.0017,metal,8))
for side in (-1,1):
    c=clasp+Vector((side*.020,.004,side*.022));verts=[];uv=[]
    for j in range(9):
        t=j/8
        for i in range(3):
            verts.append(c+Vector(((i-1)*.007+side*(t-.5)*.022,.005*math.sin(math.pi*t),side*(t-.5)*.030)))
            uv.append((i*.007,t*.035))
    faces=[(j*3+i,j*3+i+1,(j+1)*3+i+1,(j+1)*3+i) for j in range(8) for i in range(2)]
    o=mesh('Clasp_LeatherTab_'+str(side),verts,faces,uv,leather);hardware.append(o)
    m=o.modifiers.new('Leather edge thickness','SOLIDIFY');m.thickness=.0018

# Keep asset files independently editable; the original character is read-only.
for ob in cloth:ob['component']='fabric'
for ob in hardware:ob['component']='clasp'
s['asset_description']='Black woven traveling cloak: high wrapped cowl, three asymmetrical mantle layers, ring clasp and full-length split drape.'
s['reference']=str(ROOT/'References/BlackCloak/blackcloak.png')
s['units']='Meters; fitted around the JinMuWon_v2 neutral shoulder/neck dimensions.'
s['cloth_status']='Sculpted rest drape. Pin groups prepared; runtime collision and Chaos cloth require game-specific setup.'

def studio_obj(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    studio.objects.link(obj)
def light(name,loc,energy,size,color,target=(0,0,1.0)):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-2.5,-3.2,3.6),450,2.8,(1,.94,.88))
light('Fill',(2.2,-1.4,2.2),230,2.2,(.88,.94,1))
light('Rim',(.5,2.1,2.8),540,2.0,(1,.98,.93))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));floor=bpy.context.object;floor.name='StudioFloor';studio_obj(floor)
floor.data.materials.append(simple_material('Studio_WarmGray',(.22,.21,.20),.87))
world=bpy.data.worlds.new('StudioWorld');s.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.25,.25,1);world.node_tree.nodes['Background'].inputs[1].default_value=.40
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));studio.objects.link(cam);s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type!='CPU'
s.cycles.device='GPU';s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100
def render(name,loc,target,scale,w=1000,h=1350):
    cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(RENDERS/(name+'.png'));bpy.ops.render.render(write_still=True)

cam.data.type='ORTHO';cam.data.ortho_scale=1.95;cam.location=(.20,-4,2.00);cam.rotation_euler=(Vector((0,0,.88))-cam.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=1000;s.render.resolution_y=1350;s.render.resolution_percentage=100
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');cloth[0].select_set(True);bpy.context.view_layer.objects.active=cloth[0]
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BlackCloak_candidate.blend'))
(OUT/'build_report.json').write_text(json.dumps({'patterns':patterns,'meshes':[o.name for o in cloth+hardware],'reference_sha256':hashlib.sha256((ROOT/'References/BlackCloak/blackcloak.png').read_bytes()).hexdigest()},indent=2))
render('Draft_Front',(.12,-4,1.9),(0,0,.89),1.93)
render('Draft_ThreeQuarter',(2.6,-4,2.0),(0,0,.89),1.96)
render('Draft_Back',(-.2,4,1.95),(0,0,.9),1.94)
render('Draft_Collar',(.50,-3,2.03),(0,-.03,1.58),.54,1100,1000)
print('BLACK_CLOAK_CANDIDATE_COMPLETE',flush=True)
