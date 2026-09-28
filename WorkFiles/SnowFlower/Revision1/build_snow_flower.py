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
    ramp.color_ramp.elements[0].color=(*(v*.68 for v in color),1);ramp.color_ramp.elements[1].color=(*(min(1,v*1.22) for v in color),1)
    l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    r=n.new('ShaderNodeMapRange');r.inputs['From Min'].default_value=0;r.inputs['From Max'].default_value=1
    r.inputs['To Min'].default_value=max(.05,rough-.055);r.inputs['To Max'].default_value=min(.98,rough+.08)
    l.new(noise.outputs['Fac'],r.inputs['Value']);l.new(r.outputs['Result'],bs.inputs['Roughness'])
    micro=n.new('ShaderNodeTexNoise');micro.inputs['Scale'].default_value=noise_scale*9;micro.inputs['Detail'].default_value=2
    l.new(tex.outputs['Object'],micro.inputs['Vector'])
    b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.16;b.inputs['Distance'].default_value=bump
    l.new(micro.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],bs.inputs['Normal'])
    if name=='Leather':
        micro.inputs['Scale'].default_value=1750;b.inputs['Strength'].default_value=.42;b.inputs['Distance'].default_value=.00016
        bs.inputs['Specular IOR Level'].default_value=.12
    if name=='Silk':bs.inputs['Specular IOR Level'].default_value=.16
    if name in ('BladeEdge','Silver','Inlay'):
        anisotropy=bs.inputs.get('Anisotropic IOR Level') or bs.inputs.get('Anisotropic')
        if anisotropy:anisotropy.default_value=.32
    materials[name]=m;return m

mat('BlackenedSteel',(.043,.054,.063),1,.32,90,.000019)
mat('BladeEdge',(.47,.51,.54),1,.23,250,.000008)
mat('Silver',(.47,.47,.45),1,.255,160,.000012)
mat('Inlay',(.39,.415,.43),1,.31,360,.000009)
mat('Leather',(.008,.009,.010),0,.58,180,.00009)
mat('Silk',(.011,.013,.017),0,.39,240,.000018)
mat('Recess',(.012,.017,.023),.85,.40,110,.000012)

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

# Fine irregular raised silver branches, carefully kept within the dark face.
for side in (-1,1):
    phase=0 if side==-1 else .9;name='SF_BladeRelief_Front' if side==-1 else 'SF_BladeRelief_Back'
    def stem(t):
        z=.179+.854*t;c,w,h=blade_shape(z);x=c+w*(.16*math.sin(t*17+phase)+.07*math.sin(t*39+.3))
        return Vector((x,surface(x,z,side),z))
    tube(name+'_Stem',[stem(i/145) for i in range(146)],lambda t:(.00068*(1-.74*t)+.00012)*(1+.18*math.sin(t*53)),'Silver','03_FloralRelief',7)
    # A finer wandering branch intermittently separates from the main trunk.
    secondary=[]
    for i in range(100):
        t=i/99*.89;p=stem(t);p.x+=.0018*math.sin(t*29+phase);p.y=surface(p.x,p.z,side)+side*.00015;secondary.append(p)
    tube(name+'_SecondaryStem',secondary,lambda t:.00030*(1-.65*t),'Inlay','03_FloralRelief',5)
    positions=[.04,.09,.145,.19,.235,.29,.35,.405,.48,.57,.69,.80,.89]
    for index,t in enumerate(positions):
        base=stem(t);direction=1 if index%2 else -1;span=.005+rng.random()*.004
        target=base+Vector((direction*span,0,.012+rng.random()*.013));c,w,h=blade_shape(target.z)
        target.x=max(c-w*.24,min(c+w*.24,target.x));target.y=surface(target.x,target.z,side)
        path=bezier([base,base+Vector((direction*.003,0,.005)),target-Vector((direction*.002,0,.004)),target],12)
        for p in path:p.y=surface(p.x,p.z,side)
        tube(name+'_Twigs',path,lambda u:.00044*(1-.64*u),'Silver','03_FloralRelief',5)
        r=.0033+rng.random()*.0020
        if t>.80:r*=.7
        flower(name,target+Vector((0,side*.00016,0)),r,(0,side,0),rng.random()*math.tau)
        if index in (1,2,4,6,9):
            p=path[len(path)//2];p=p+Vector((-direction*.0032,side*.00018,.0045));p.y=surface(p.x,p.z,side)+side*.00012
            flower(name,p,r*.63,(0,side,0),rng.random()*math.tau)
        bud=base+Vector((-direction*.0025,side*.0002,.010));bud.y=surface(bud.x,bud.z,side)+side*.0002
        ellipsoid(name+'_Buds',bud,(.00072,0,0),(0,.0004,0),(0,0,.0010),'Silver','03_FloralRelief',8,4)

def extrude(name,outline,depth,material,group,cy=0):
    vs=[(x,cy-depth/2,z) for x,z in outline]+[(x,cy+depth/2,z) for x,z in outline];n=len(outline)
    fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n));add(name,material,group,vs,fs)

wing=[(.010,.124),(.022,.100),(.046,.081),(.064,.099),(.066,.115),(.054,.142),(.033,.148),(.017,.141)]
for side in (-1,1):
    outline=[(side*x,.122+(z-.122)*.72) for x,z in wing]
    coarse=[Vector(p) for p in outline];outline=[]
    for i in range(len(coarse)):
        a,b,c,d=[coarse[j%len(coarse)] for j in (i-1,i,i+1,i+2)]
        for f in (0,.25,.50,.75):outline.append(tuple(.5*((2*b)+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)))
    # Open forged wings: an annular frame with visible filigree, not a solid shield.
    center2=Vector((side*.040,.122));inner=[tuple(center2+(Vector(p)-center2)*.75) for p in outline]
    v=[(x,y,z) for y in (-.0065,.0065) for points in (outline,inner) for x,z in points];f=[];n=len(outline)
    for i in range(n):
        j=(i+1)%n
        f.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    add('SF_Guard_Wings','Recess','02_Guard',v,f)
    for front in (-1,1):
        loop=[(x,front*.0078,z) for x,z in outline];tube('SF_Guard_WingBorders',loop,.00115,'Silver','02_Guard',8,True)
        inner_loop=[(x,front*.0072,z) for x,z in inner]
        tube('SF_Guard_WingInner',inner_loop,.00055,'Silver','02_Guard',6,True)

def guard_leaf(angle,length,width,side,layer=0):
    center=Vector((0,side*(.010+layer*.003),.126));D=Vector((math.sin(angle),0,math.cos(angle)));T=Vector((math.cos(angle),0,-math.sin(angle)));N=Vector((0,side,0))
    start=center+D*.006;segments=16;sides=10;v=[start];f=[]
    for j in range(1,segments):
        t=j/segments;w=width*math.sin(math.pi*t)**.95;lift=.004*math.sin(math.pi*t)+.0015*t
        for k in range(sides):
            a=math.tau*k/sides;v.append(start+D*length*t+T*w*math.cos(a)+N*(lift+.0012*math.sin(a)))
    end=len(v);v.append(start+D*length+N*.0015)
    for k in range(sides):f.append((0,1+(k+1)%sides,1+k))
    for j in range(segments-2):
        for k in range(sides):a=1+j*sides+k;b=1+j*sides+(k+1)%sides;f.append((a,b,b+sides,a+sides))
    for k in range(sides):f.append((end,1+(segments-2)*sides+k,1+(segments-2)*sides+(k+1)%sides))
    add('SF_Guard_Petals','BlackenedSteel','02_Guard',v,f)
    edge=[]
    for sign,ts in [(1,[i/segments for i in range(segments+1)]),(-1,[i/segments for i in range(segments-1,0,-1)])]:
        for t in ts:edge.append(start+D*length*t+T*sign*width*math.sin(math.pi*t)**.95+N*(.004*math.sin(math.pi*t)+.0015*t+.0006))
    tube('SF_Guard_PetalBorders',edge,.00070,'Silver','02_Guard',6,True)
    tube('SF_Guard_PetalVeins',[start+D*length*t+N*(.004*math.sin(math.pi*t)+.0015*t+.0013) for t in [i/18 for i in range(2,18)]],lambda t:.00042*(1-.7*t),'Silver','02_Guard',5)

for side in (-1,1):
    for angle,length,width,layer in [(0,.052,.012,0),(-.87,.050,.018,0),(.87,.050,.018,0),(-1.67,.047,.013,0),(1.67,.047,.013,0),(-2.40,.036,.010,1),(2.40,.036,.010,1)]:guard_leaf(angle,length,width,side,layer)
    flower('SF_GuardFlower',(0,side*.023,.126),.019,(0,side,0),.35,group='02_Guard',large=True)
    for sign in (-1,1):
        path=bezier([(sign*.008,side*.010,.119),(sign*.038,side*.011,.090),(sign*.045,side*.010,.127),(sign*.020,side*.010,.152)],32)
        tube('SF_Guard_Filigree',path,.00058,'Silver','02_Guard',6)
        for i in (8,19,27):
            p=path[i];ellipsoid('SF_Guard_FiligreeBeads',p,(.0011,0,0),(0,.0006,0),(0,0,.0011),'Silver','02_Guard',8,4)

def collar(name,z,rx,ry,height,material,group='04_Grip',segments=48):
    v=[];f=[]
    rows=[(z-height/2,rx*.95,ry*.95),(z-height*.33,rx,ry),(z+height*.33,rx,ry),(z+height/2,rx*.95,ry*.95)]
    for zz,xx,yy in rows:
        for i in range(segments):a=math.tau*i/segments;v.append((math.cos(a)*xx,math.sin(a)*yy,zz))
    for j in range(3):
        for i in range(segments):f.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
    f += [tuple(reversed(range(segments))),tuple(3*segments+i for i in range(segments))];add(name,material,group,v,f)

collar('SF_Grip_Core',-.014,.0155,.012,.260,'Leather')
collar('SF_Grip_LowerFerrule',.105,.018,.0145,.012,'Recess')
collar('SF_Grip_LowerSilver',.106,.0186,.0151,.0033,'Silver')
collar('SF_Grip_PommelCollar',-.147,.019,.0157,.014,'Recess')
collar('SF_Grip_PommelBand',-.150,.0197,.0164,.003,'Silver')
# Two helical flattened leather strips, rather than stacked cylindrical rings.
for direction in (-1,1):
    v=[];f=[];steps=420
    for i in range(steps+1):
        t=i/steps;z=-.138+.236*t;a=direction*math.tau*(10.5*t)+.35;offset=.00065+(.00034 if direction==1 else 0)
        for zz,dr in [(-.0044,-.00025),(-.0044,.0004),(.0044,.0004),(.0044,-.00025)]:
            v.append(((.0155+offset+dr)*math.cos(a),(.012+offset+dr)*math.sin(a),z+zz))
        if i:
            for k in range(4):f.append(((i-1)*4+k,i*4+k,i*4+(k+1)%4,(i-1)*4+(k+1)%4))
    f += [(3,2,1,0),tuple(steps*4+k for k in range(4))];add('SF_Grip_CrossWrap','Leather','04_Grip',v,f)

for side in (-1,1):
    for index,(z,x,r) in enumerate([(.076,.004,.0048),(-.015,-.005,.0040),(-.108,.004,.0044)]):
        y=side*(.0137*math.sqrt(max(.1,1-(x/.016)**2))+.0006)
        flower('SF_Grip_Blossoms',(x,y,z),r,(0,side,0),index*.9,'04_Grip')
        path=bezier([(x,side*.0142,z+.014),(x-.006,side*.0145,z+.008),(x+.008,side*.0145,z-.009),(x-.001,side*.0145,z-.017)],18)
        tube('SF_Grip_SilverVines',path,.00034,'Silver','04_Grip',5)

# Circular pommel face, slightly tilted details visible in the three-quarter view.
collar('SF_Pommel_Housing',-.155,.020,.019,.018,'Recess','05_Pommel')
for z in (-.1645,-.148):
    tube('SF_Pommel_Rim',[(.0199*math.cos(math.tau*i/64),.0189*math.sin(math.tau*i/64),z) for i in range(64)],.00085,'Silver','05_Pommel',8,True)
flower('SF_Pommel_Flower',(0,0,-.1652),.0145,(0,0,-1),.2,'05_Pommel',True)
for side in (-1,1):
    ellipsoid('SF_Pommel_FacePlate',(0,side*.016,-.147),(.0185,0,0),(0,side*.0028,0),(0,0,.0185),'Recess','05_Pommel',32,12)
    tube('SF_Pommel_FaceRim',[(.0182*math.cos(math.tau*i/48),side*.018,-.147+.0182*math.sin(math.tau*i/48)) for i in range(48)],.00065,'Silver','05_Pommel',8,True)
    flower('SF_Pommel_FaceBlossom',(0,side*.0195,-.147),.0138,(0,side,0),.2,'05_Pommel',True)
for k in range(5):
    a=math.tau*k/5
    points=[]
    for j in range(25):
        t=j/24;theta=a+(.12+.90*t);r=.0145+.0020*math.sin(t*math.pi)
        points.append((math.cos(theta)*r,math.sin(theta)*r,-.1655))
    tube('SF_Pommel_Filigree',points,.00035,'Silver','05_Pommel',5)

# Side-attached cord and five-petal charm. All tassel pieces are independent.
cord=bezier([(-.018,0,-.148),(-.029,0,-.147),(-.039,.001,-.060),(-.052,.002,-.026)],56)
tube('SF_Tassel_Cord',cord,.0018,'Silk','06_Tassel',10)
for offset in (0,.005,.010):
    p=Vector((-.025-offset*.55,0,-.132+offset));ellipsoid('SF_Tassel_AttachmentKnots',p,(.0038,0,0),(0,.0035,0),(0,0,.0034),'Silk','06_Tassel',14,7)
for side in (-1,1):flower('SF_Tassel_FlowerCharm',(-.054,side*.0018,-.013),.0115,(0,side,0),.2,'06_Tassel',True)
tube('SF_Tassel_LowerCord',[(-.054,0,-.002),(-.058,0,.011),(-.061,0,.022)],.0017,'Silk','06_Tassel',10)
ellipsoid('SF_Tassel_Bead',(-.061,0,.021),(.006,0,0),(0,.0055,0),(0,0,.009),'Recess','06_Tassel',24,12)
for z in (.026,.030,.034):tube('SF_Tassel_SilverCap',[( -.064+.0063*math.cos(math.tau*i/32),.0063*math.sin(math.tau*i/32),z) for i in range(32)],.00045,'Silver','06_Tassel',6,True)
for i in range(126):
    a=i*2.399963;r=.0056*math.sqrt((i+.5)/126);dx=r*math.cos(a);dy=r*math.sin(a);phase=rng.random()*math.tau
    length=.117+rng.uniform(-.005,.006);points=[]
    for j in range(17):
        t=j/16;x=-.064-.026*t+dx*(1+.8*t)+.00065*math.sin(phase+t*7)*t
        y=dy*(1+.9*t)+.00035*math.cos(phase+t*9)*t;z=.035+length*t;points.append((x,y,z))
    tube('SF_Tassel_Strands',points,lambda t:.00034*(1-.20*t),'Silk','06_Tassel',5)

# Consolidated named components keep the scene usable while retaining editability.
for (name,material,group),p in parts.items():
    me=bpy.data.meshes.new(name+'Mesh');me.from_pydata(p['v'],[],p['f']);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);collection(group).objects.link(ob);me.materials.append(materials[material])
    for poly in me.polygons:poly.use_smooth=True
    ob['sf_export']=True;ob['sf_part']=group;ob['sf_material']=material
    if group=='06_Tassel':ob['sf_secondary_motion_candidate']=True
    if name in ('SF_Guard_Wings',):
        bevel=ob.modifiers.new('Small forged edge bevel','BEVEL');bevel.width=.001;bevel.segments=3
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=bevel.name)
        for poly in ob.data.polygons:poly.use_smooth=False

# Recalculate blade winding after its asymmetric cross section is complete.
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
asset_objects=[o for o in scene.objects if o.type=='MESH']
for ob in asset_objects:
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')

root=bpy.data.objects.new('SnowFlower_GripOrigin',None);collection('00_Attachment').objects.link(root);root.empty_display_size=.028
for ob in asset_objects:ob.parent=root
for name,location in [('Socket_MainHand',(0,0,0)),('Socket_OffHand',(0,0,-.07)),('Socket_BladeTip',(.0305,0,1.085)),('Socket_TasselRoot',(-.018,0,-.148))]:
    e=bpy.data.objects.new(name,None);collection('00_Attachment').objects.link(e);e.location=location;e.empty_display_type='ARROWS';e.empty_display_size=.018;e.parent=root

scene['asset']='Snow Flower — user reference interpretation';scene['reference']='References/SnowFlower/SnowFlower_user_reference.png'
scene['working_overall_length_m']=1.25;scene['attachment_origin']='Center of grip; blade extends along local +Z'
scene.world=bpy.data.worlds.new('SnowFlower_StudioWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.48,.52,.58,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.22
studio=collection('STUDIO_ExcludeFromExport')
for name,location,power,size,color in [
    ('Key',(-1.1,-1.3,.7),40,1.1,(1,.97,.93)),('Strip',(1,-.7,.5),50,.7,(.83,.91,1)),
    ('Rim',(.5,.8,.55),65,1.1,(1,1,1)),('Top',(-.1,-.4,1.7),25,.5,(1,.97,.92))]:
    light=bpy.data.lights.new(name,'AREA');ob=bpy.data.objects.new(name,light);studio.objects.link(ob);ob.location=location
    light.energy=power;light.shape='RECTANGLE';light.size=size;light.size_y=size*.65;light.color=color
    ob.rotation_euler=(Vector((0,0,.40))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('SnowFlower_ReviewCamera',bpy.data.cameras.new('SnowFlower_ReviewCamera'));studio.objects.link(cam);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type!='CPU'
    scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-.4
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
        'objects':{},'working_dimensions_m':{'overall':1.25,'blade':.939,'guard_span':.134,'grip':.260},
        'origin':'Grip center; blade +Z; front -Y','scope':'Sword and tassel; no scabbard; independent from character.'}
for ob in asset_objects:
    ob.data.calc_loop_triangles();report['objects'][ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles),'materials':[m.name for m in ob.data.materials]}
report['triangles']=sum(x['triangles'] for x in report['objects'].values())
(WORK/'build_report.json').write_text(json.dumps(report,indent=2))
render('SnowFlower_Front',(0,-3,.458),(0,0,.458),1.39,900,1600)
render('SnowFlower_Back',(0,3,.458),(0,0,.458),1.39,900,1600)
render('SnowFlower_Oblique',(.65,-3,.66),(0,0,.458),1.39,1000,1600)
render('SnowFlower_Guard',(.22,-.60,.23),(0,0,.120),.185,1300,1100)
render('SnowFlower_BladeDetail',(.06,-.45,.50),(0,0,.44),.27,1100,1400)
render('SnowFlower_Pommel',(.07,-.10,-.29),(0,0,-.145),.100,1200,1100,False)
render('SnowFlower_Side',(3,0,.458),(0,0,.458),1.39,650,1600)
print('SNOW_FLOWER_BUILD_COMPLETE',report['triangles'],flush=True)
