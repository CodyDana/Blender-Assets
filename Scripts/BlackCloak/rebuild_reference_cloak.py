"""Reference-landmark reconstruction of the separate cloak, revision 2.

Front panel boundaries are authored in the original 417 x 674 reference pixel
space. Depth, hidden construction and rear folds are modeled interpretations.
Shared low-level mesh/studio helpers come from build_cloak.py.
"""
from pathlib import Path
import os
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
base=(ROOT/'Scripts/BlackCloak/build_cloak.py').read_text()
prefix=base.split('def lower_panel')[0]
prefix=prefix.replace('fabric=textile()', "sys.path.insert(0,str(ROOT/'Scripts/BlackCloak'))\nfrom refined_textile import make_refined_textile\nfabric=make_refined_textile(TEX)")
exec(compile(prefix,'build_cloak_shared','exec'))
exec(compile(base[base.index('def tube('):base.index('# Rolled hems')],'build_cloak_tube','exec'))
S=1.72/654
REV=ROOT/'Renders/BlackCloak/ReferenceRevision';REV.mkdir(parents=True,exist_ok=True)

def gauss(x,c,w):return math.exp(-((x-c)/w)**2)
def path(points,t):
    # Piecewise cubic Hermite interpolation preserves authored corner/endpoints.
    t=max(0,min(1,t));q=t*(len(points)-1);i=min(int(q),len(points)-2);f=q-i
    a=np.array(points[max(0,i-1)],float);b=np.array(points[i],float)
    c=np.array(points[i+1],float);d=np.array(points[min(len(points)-1,i+2)],float)
    m0=(c-a)*.5;m1=(d-b)*.5
    return tuple((2*f**3-3*f*f+1)*b+(f**3-2*f*f+f)*m0+(-2*f**3+3*f*f)*c+(f**3-f*f)*m1)
def P(px,py,depth):return ((px-202)*S,depth,(665-py)*S)
def orient_front(ob):
    bm=bmesh.new();bm.from_mesh(ob.data)
    if sum(f.normal.y*f.calc_area() for f in bm.faces)>0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(ob.data);bm.free()
def panel(name,left,right,depth,folds=(),nu=70,nv=100,edge_noise=0):
    def fn(u,v):
        l=path(left,v);r=path(right,v);px=lerp(l[0],r[0],u);py=lerp(l[1],r[1],u)
        if name=='Cloak_OverlappingFrontPanel':
            hx,hy=path([(210,533),(228,551),(248,566),(268,582),(296,599),(322,612),(347,626),(374,640)],u)
            px+=(hx-lerp(left[-1][0],right[-1][0],u))*v**10
            py+=(hy-lerp(left[-1][1],right[-1][1],u))*v**10
        y=depth(u,v,px,py)
        for center,width,amplitude,drift in folds:
            c=center+drift*math.sin(math.pi*v*.85)
            y+=amplitude*gauss(u,c,width)*ease(v/.22)
        # Tiny, deliberately non-periodic edge irregularity, confined to hem.
        if edge_noise:py+=edge_noise*(gauss(u,.12,.014)-.7*gauss(u,.24,.011)+.6*gauss(u,.39,.018)-.8*gauss(u,.52,.01))*v**32
        return P(px,py,y),(u*max(.12,abs(r[0]-l[0])*S),v*max(.1,abs(left[-1][1]-left[0][1])*S))
    ob=grid(name,fn,nu,nv);orient_front(ob);ob['reference_construction']='Front boundary traced in source image coordinates; authored depth.'
    return ob

# Full circumferential undercloak. Fold valleys are individually positioned,
# with different widths and depths, rather than a sinusoidal pleat array.
def undercloak(u,v):
    a=lerp(.09,TAU-.09,u);t=ease(v/.14)
    rx=lerp(.115,.284,t) if v<.14 else lerp(.284,.483,(v-.14)/.86)
    ry=lerp(.096,.150,t) if v<.14 else lerp(.150,.273,(v-.14)/.86)
    angles=[.20,.49,.92,1.43,1.92,2.51,3.02,3.45,4.01,4.55,5.12,5.53,5.91]
    amplitudes=[-.040,.026,-.030,.018,-.024,.038,-.016,.024,-.034,.017,-.033,.030,-.041]
    widths=[.10,.15,.17,.20,.12,.22,.16,.21,.16,.15,.13,.12,.09]
    fold=sum(amp*gauss(a,c+.025*math.sin(v*3+c),w) for c,amp,w in zip(angles,amplitudes,widths))*ease(v/.28)
    z=lerp(1.577,.105,v)
    # Separate independent valleys reach different hem heights.
    z+=v**12*(.013*gauss(a,.5,.23)-.016*gauss(a,1.18,.19)+.009*gauss(a,2.55,.38)-.011*gauss(a,4.6,.22))
    return ((rx+fold)*math.sin(a),.032-(ry+fold)*math.cos(a),z),(u*2.55,v*1.54)
core=grid('Cloak_LongDrape',undercloak,168,90)

panel('Cloak_RightInnerLongLeaf',
      [(246,272),(255,377),(263,483),(268,578),(274,649)],
      [(271,287),(290,379),(300,489),(303,583),(310,652)],
      lambda u,v,x,y:-.172-.055*v,
      [(.38,.27,-.023,-.03),(.91,.10,.016,.02)],45,96)

# Left floor-length strip and the deep inner opening remain separate sheets.
panel('Cloak_LeftLongLeaf',
      [(111,99),(99,204),(83,338),(64,487),(41,645)],
      [(125,104),(132,224),(127,367),(117,522),(89,661)],
      lambda u,v,x,y:-.218-.090*v+.016*u,
      [(.17,.17,-.025,.035),(.84,.12,.023,-.015)],60,110)
panel('Cloak_InnerLeftFall',
      [(122,111),(119,258),(113,388),(109,526),(119,636)],
      [(139,123),(149,288),(155,411),(151,537),(137,637)],
      lambda u,v,x,y:-.201-.050*v,
      [(.55,.23,-.024,.08)],35,92)

# Broad central/right leaf: pointed diagonal lower edge, quiet cloth planes.
panel('Cloak_OverlappingFrontPanel',
      [(126,118),(148,219),(165,288),(177,366),(192,447),(210,533)],
      [(151,124),(260,265),(295,361),(326,457),(350,552),(374,640)],
      lambda u,v,x,y:-.226-.088*v+.070*u**4,
      [(.08,.13,-.020,.02),(.76,.12,.036,-.045),(.94,.075,-.027,0)],96,128,1.5)

# The shorter left falls have their own edges. Do not fuse their notches into
# the full-length skirt's hem.
panel('Cloak_LeftWing',
      [(91,82),(58,150),(43,222),(26,284),(10,332)],
      [(111,88),(119,171),(105,251),(93,326),(82,391)],
      lambda u,v,x,y:-.165-.09*u-.026*v+.035*(1-u)**6*v**4,
      [(.35,.17,-.025,.07),(.68,.09,.022,-.06)],64,100)
panel('Cloak_GatheredSideFall',
      [(113,100),(77,246),(46,364),(34,392),(43,414),(39,447),(44,451),(44,473),(49,478),(47,491),(60,554)],
      [(124,110),(125,245),(104,342),(94,371),(89,400),(81,436),(77,455),(74,473),(69,496),(65,529),(62,557)],
      lambda u,v,x,y:-.255-.09*v+.012*u,
      [(.17,.16,-.016,.025),(.70,.13,.018,-.08)],60,150,0)

# Front shoulder layers share depth rules but have separately traced contours.
MANTLES={}
def mantle(name,top,bottom,layer,nu=112,nv=44):
    def fn(u,v):
        a=path(top,u);b=path(bottom,u);x=lerp(a[0],b[0],v);py=lerp(a[1],b[1],v)
        # Evaluate the shared shoulder surface in physical image coordinates,
        # not each panel's local u: different u maps otherwise interpenetrate.
        y=-.258-.00012*(py-90)+.22*ease((x-215)/175)
        y-=(2-layer)*.017
        # Soft tension creases fan from the clasp and die into broad planes.
        y+=(-.007*gauss(v,.22+.18*u,.10)+.009*gauss(v,.43+.08*u,.085)
            -.009*gauss(v,.62-.08*u,.15))*math.sin(math.pi*u)**.5
        y-=.014*math.sin(math.pi*v)*math.sin(math.pi*u)
        # Cloth turns under at free outer tip rather than presenting a flat cut.
        y+=.018*u**12*v**6
        return P(x,py,y),(u*1.0,v*(.27+.30*layer))
    MANTLES[layer]=fn
    ob=grid(name,fn,nu,nv);orient_front(ob);return ob
mantle('Cloak_DiagonalShawl',
       [(116,94),(153,108),(211,124),(285,146),(341,195)],
       [(125,119),(151,158),(184,197),(224,241),(268,284),(313,322),(357,354),(402,380)],2,130,90)
mantle('Cloak_MiddleMantle',
       [(114,95),(143,103),(172,113),(206,116),(243,109),(285,100),(307,109)],
       [(122,111),(154,143),(194,164),(240,181),(287,194),(340,205),(346,214)],1,116,46)
mantle('Cloak_UpperMantle',
       [(111,78),(121,82),(139,96),(172,105),(204,107),(238,99),(276,77),(298,78)],
       [(120,103),(151,124),(194,143),(245,158),(294,169),(337,180)],0,116,42)

panel('Cloak_RightWingReturn',
      [(320,202),(320,276),(325,348),(329,410),(334,480)],
      [(345,211),(381,303),(402,380),(373,422),(365,447)],
      lambda u,v,x,y:-.055+.17*(1-u)*math.sin(math.pi*v)+.015*v,
      [(.30,.23,.028,0)],54,90)

# Small left shoulder cape and rear wraps give actual volume from all views.
panel('Cloak_LeftShoulder',[(125,67),(104,75),(88,83)],[(117,96),(91,129),(58,150)],
      lambda u,v,x,y:-.142-.060*(1-u)+.035*v,[ ],48,28)
def rear_mantle(level):
    def raw(u,v):
        a=lerp(math.pi/2,3*math.pi/2,u)
        py=lerp(63,147+48*level,v)+10*math.sin(a*2+.6)*v
        depth=(py-63)*S
        rx=float(np.interp(depth,[0,.12,.26,.48,.70],[.14,.24,.30,.35,.40]))
        ry=float(np.interp(depth,[0,.12,.26,.48,.70],[.106,.15,.20,.25,.29]))
        outer=(2-level)*.011*ease(v/.10);rx+=outer;ry+=outer
        radial=(.006*math.sin(5*a+depth*3)+.003*math.sin(9*a-depth*2))*min(1,depth/.20)
        return Vector(((rx+radial)*math.sin(a)-.021,.015-(ry+radial)*math.cos(a),P(202,py,0)[2]))
    def fn(u,v):
        p=raw(u,v)
        right=Vector(MANTLES[level](1,v)[0]);left=Vector(MANTLES[level](0,v)[0])
        p+=(right-raw(0,v))*math.exp(-(u*5)**2)+(left-raw(1,v))*math.exp(-((1-u)*5)**2)
        return p,(u*1.2,v*(.24+.13*level))
    return fn
for k in (2,):grid('Cloak_RearMantle_%d'%k,rear_mantle(k),140,60)

# Collar: one continuous open cowl plus irregular overlapping front folds.
# Different traced sag curves replace the five lathed horizontal bands.
def cowl(u,v):
    a=TAU*u;ca=math.cos(a);front=max(0,ca)
    radius=lerp(76,49,v);py=lerp(77+31*front+5*math.sin(a),19+12*ca,v)
    radial=.002*math.sin(3*a+v*8)*math.sin(math.pi*v)
    return ((192-202)*S+(radius*S+radial)*math.sin(a),-.002-(lerp(.287,.105,v**.72)+radial)*ca,P(202,py,0)[2]),(u*.86,v*.22)
collar=grid('Cloak_WrappedCowl',cowl,160,54)
bm=bmesh.new();bm.from_mesh(collar.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bm.to_mesh(collar.data);bm.free()
curves=[
 [(144,25),(160,35),(181,43),(204,45),(224,38),(240,28)],
 [(139,39),(156,50),(182,57),(207,58),(230,52),(248,43)],
 [(132,51),(149,67),(176,76),(202,77),(232,68),(259,58)],
 [(125,66),(143,84),(172,96),(204,99),(237,89),(269,68)],
 [(121,82),(139,96),(172,105),(204,107),(238,99),(276,77)]]
for k,edge in enumerate(curves):
    def scarf(u,v,k=k,edge=edge):
        a=TAU*u;ca=math.cos(a);t=(math.sin(a)+1)/2
        px,front_py=path(edge,t);cx=(edge[-1][0]+edge[0][0])/2
        rear_py=lerp(edge[0][1],edge[-1][1],t)-4*max(0,-ca)+2*math.sin(a*3+k)
        py=front_py if ca>=0 else rear_py
        width=[17,20,24,25,20][k]*(.72+.28*abs(ca))
        py-=width*(1-v)
        px=cx+(px-cx)*(1-.045*(1-v))
        radius=[.134,.175,.232,.305,.342][k] if ca>=0 else .112+k*.006
        radius-=.024*(1-v)
        radius+=.012*math.sin(math.pi*v)**.7*(.8+.2*math.sin(a*3+k))
        depth=-.009-radius*ca
        # A local compression tuck changes crease depth without adding a new
        # evenly spaced rib around the entire neck.
        depth+=.004*gauss(t,.19,.065)*math.sin(v*5)*max(0,ca)
        return P(px,py,depth),(u*(edge[-1][0]-edge[0][0])*S*math.pi,v*width*S)
    ob=grid('Cloak_ScarfWrap_%02d'%(k+1),scarf,180,24)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bm.to_mesh(ob.data);bm.free()
    ob['cloth_max_distance_m']=.025

# Replace the construction strips by a continuous sculpted scarf surface.
# Lofting the traced creases avoids exposed cut strip ends and tube-like tiers.
for ob in list(cloth):
    if 'Cowl' in ob.name or 'ScarfWrap' in ob.name:
        cloth.remove(ob);patterns.pop(ob.name,None);bpy.data.objects.remove(ob,do_unlink=True)
def scarf_ring(k,a):
    ca=math.cos(a);t=(math.sin(a)+1)/2
    if k==0:
        return 192+49*math.sin(a),19+12*ca,.106,-.002
    edge=curves[k-1];px,py=path(edge,t)
    if ca<0:py=lerp(edge[0][1],edge[-1][1],t)+(-4+1.5*math.sin(a*3+k))*(-ca)
    front_radii=[.132,.169,.219,.281,.324]
    center=-.009-.011*k
    radius=front_radii[k-1]+center if ca>=0 else .106+.002*k
    return px,py,radius,center
def sculpted_scarf(u,v):
    a=TAU*u;q=v*5;k=min(int(q),4);f=q-k
    px0,py0,r0,c0=scarf_ring(k,a);px1,py1,r1,c1=scarf_ring(k+1,a)
    px=lerp(px0,px1,f);py=lerp(py0,py1,f)
    radius=lerp(r0,r1,f)
    # Rounded overfold then a locally compressed valley, varying around neck.
    strength=.014+.008*(.5+.5*math.sin(a*3+k*.8))
    radius+=strength*math.sin(math.pi*f)**.7-.005*gauss(f,.95,.055)*math.sin(math.pi*f)**.3
    py+=1.2*math.sin(a*3+k)*math.sin(math.pi*f)
    # Small left-side compressions break the otherwise regular stacked sweep.
    tuck=gauss(math.sin(a),-.78,.16)*max(0,math.cos(a))
    py+=2.2*tuck*math.sin(v*TAU*3.6+.3)
    radius+=.003*tuck*math.sin(v*TAU*3.6+1)
    front=max(0,math.cos(a))
    radius+=.013*gauss(math.sin(a),-.48,.40)*front*gauss(v,.32+.13*math.sin(a),.045)
    radius-=.008*gauss(math.sin(a),-.50,.35)*front*gauss(v,.38+.13*math.sin(a),.025)
    radius+=.013*gauss(math.sin(a),.48,.40)*front*gauss(v,.79-.14*math.sin(a),.040)
    y=lerp(c0,c1,f)-radius*math.cos(a)
    return P(px,py,y),(u*.91,v*.29)
collar=grid('Cloak_WrappedCowl',sculpted_scarf,208,155)
bm=bmesh.new();bm.from_mesh(collar.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bm.to_mesh(collar.data);bm.free()
collar['cloth_max_distance_m']=.025

# Dark, compact shoulder ring and a discreet pin.
metal.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.012,.013,.012,1)
metal.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=1
metal.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.73
clasp=Vector(P(117,90,-.319));pts=[]
for i in range(97):
    a=TAU*i/96;pts.append(clasp+Vector((.024*math.cos(a),.0015*math.cos(a),.025*math.sin(a))))
hardware.append(tube('Clasp_BlackenedRing',pts,.0050,metal,12))
hardware.append(tube('Clasp_Pin',[clasp+Vector((-.016,-.004,-.015)),clasp+Vector((.015,-.004,.018))],.0014,metal,8))
# Recessed cloth loop sits behind the ring, without bright broad tabs.
loop=[clasp+Vector((-.014,.006,-.027)),clasp+Vector((-.002,.007,-.010)),clasp+Vector((.006,.007,.010)),clasp+Vector((.010,.008,.030))]
hardware.append(tube('Clasp_DarkLoop',loop,.004,leather,8))

for ob in cloth:ob['component']='fabric'
for ob in hardware:ob['component']='clasp'
s['asset_description']='Reference-landmark revision: asymmetric black cloak with broad leaf panels, irregular scarf collar, gathered shoulder and dark clasp.'
s['reference']=str(ROOT/'References/BlackCloak/blackcloak.png')
s['reference_limits']='Visible front shapes traced from reference; depth, rear and hidden construction are interpreted. Not an exact reconstruction.'
s['cloth_status']='Sculpted rest drape; runtime cloth and collision are not configured.'

exec(compile(base[base.index('def studio_obj('):base.index("cam.data.type='ORTHO';cam.data.ortho_scale=1.95")],'build_cloak_studio','exec'))
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.8,.8,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.18
floor.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.83,.83,.83,1)
bpy.data.objects['Key'].data.energy=360;bpy.data.objects['Fill'].data.energy=150;bpy.data.objects['Rim'].data.energy=220
s.view_settings.view_transform='Standard';s.view_settings.look='None'
# Keep a white photographic backdrop while retaining the real ground shadow.
floor.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(1,1,1,1)
floor.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=0
worldnodes=s.world.node_tree.nodes;worldlinks=s.world.node_tree.links
white=worldnodes.new('ShaderNodeBackground');white.inputs[0].default_value=(1,1,1,1);white.inputs[1].default_value=1
lightpath=worldnodes.new('ShaderNodeLightPath');mix=worldnodes.new('ShaderNodeMixShader')
worldlinks.new(lightpath.outputs['Is Camera Ray'],mix.inputs[0]);worldlinks.new(worldnodes.get('Background').outputs[0],mix.inputs[1]);worldlinks.new(white.outputs[0],mix.inputs[2]);worldlinks.new(mix.outputs[0],worldnodes.get('World Output').inputs[0])
cam.data.type='ORTHO';cam.data.ortho_scale=674*S;cam.location=(6.5*S,-4,P(202,337,0)[2]);cam.rotation_euler=(Vector((6.5*S,0,P(202,337,0)[2]))-cam.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=834;s.render.resolution_y=1348;s.cycles.samples=40
s.render.filepath=str(REV/'Revision_Front.png')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT');core.select_set(True);bpy.context.view_layer.objects.active=core
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BlackCloak_candidate.blend'))
(OUT/'build_report.json').write_text(json.dumps({'revision':2,'patterns':patterns,'meshes':[o.name for o in cloth+hardware],'reference_sha256':hashlib.sha256((ROOT/'References/BlackCloak/blackcloak.png').read_bytes()).hexdigest()},indent=2))
bpy.ops.render.render(write_still=True)
if os.environ.get('CLOAK_FRONT_ONLY')!='1':
    RENDERS=REV
    render('Revision_ThreeQuarter',(2.6,-4,1.5),(0,0,.87),1.94)
    render('Revision_Back',(-.15,4,1.4),(0,0,.87),1.93)
    render('Revision_Collar',(.08,-4,1.68),(-.02,-.03,1.535),.68,1100,1000)
print('REFERENCE_CLOAK_REBUILT',flush=True)
