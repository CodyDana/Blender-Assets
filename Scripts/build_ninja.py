import bpy, bmesh, math, sys
from mathutils import Vector

# ------------------------------------------------------------------
# Stylized human male in a ninja outfit - procedural build
# Body = Skin-modifier skeleton; outfit + katana layered on top.
# ------------------------------------------------------------------
A = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT_BLEND  = A[0] if len(A) > 0 else "//Ninja.blend"
OUT_RENDER = A[1] if len(A) > 1 else "//ninja.png"
ANGLE      = A[2] if len(A) > 2 else "hero"

def wipe():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for b in list(blk):
            if b.users == 0: blk.remove(b)
wipe()
scene = bpy.context.scene
NINJA = bpy.data.collections.new("Ninja")
scene.collection.children.link(NINJA)
def link(o):
    for c in o.users_collection: c.objects.unlink(o)
    NINJA.objects.link(o); return o

# ---------------- materials ----------------
def mat(name, base, metallic=0.0, rough=0.6, emit=None, emit_str=0.0, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    def sv(k,v):
        if k in b.inputs: b.inputs[k].default_value = v
    sv("Base Color", (*base,1)); sv("Metallic", metallic); sv("Roughness", rough)
    sv("Sheen Weight", sheen)
    if emit is not None:
        sv("Emission Color", (*emit,1)); sv("Emission Strength", emit_str)
    return m
m_suit  = mat("Suit",  (0.022,0.023,0.030), rough=0.72, sheen=0.3)   # black cloth
m_suit2 = mat("SuitPanel", (0.040,0.042,0.052), rough=0.6, sheen=0.2) # slightly lighter panels
m_accent= mat("Accent",(0.34,0.03,0.035), rough=0.55, sheen=0.35)    # deep red scarf/sash
m_wrap  = mat("Wrap",  (0.075,0.075,0.085), rough=0.85)              # dark gray wraps
m_skin  = mat("Skin",  (0.62,0.44,0.34), rough=0.5)
m_eye   = mat("EyeWhite",(0.86,0.86,0.88), rough=0.35)
m_pup   = mat("Pupil", (0.02,0.02,0.03), rough=0.4)
m_metal = mat("Metal", (0.62,0.64,0.68), metallic=1.0, rough=0.22)
m_gold  = mat("GoldTrim",(0.58,0.42,0.10), metallic=1.0, rough=0.3)
m_lacq  = mat("Lacquer",(0.015,0.015,0.02), rough=0.18)              # katana saya
m_wood  = mat("Handle",(0.05,0.02,0.02), rough=0.5)

def assign(o,m):
    o.data.materials.clear(); o.data.materials.append(m); return o
def smooth(o):
    for p in o.data.polygons: p.use_smooth = True
    return o

# ---------------- body via Skin modifier ----------------
# skeleton: (name, x,y,z, radius). front = -Y (toward camera)
J = {}
def jt(name,x,y,z,r): J[name]=(len(J),(x,y,z),r)
# center chain  (broad chest -> narrow waist = masculine V-taper)
jt("pelvis", 0,0,0.98,0.140); jt("spine",0,0,1.15,0.120); jt("chest",0,0,1.40,0.175)
jt("neck",0,0,1.55,0.078); jt("head",0,0,1.67,0.135); jt("htop",0,0,1.82,0.100)
# arms (left, +x) - hang straighter, slight outward A
jt("shL",0.195,0,1.47,0.088); jt("elL",0.29,0.0,1.15,0.058); jt("wrL",0.345,0.0,0.90,0.043); jt("haL",0.365,0.0,0.80,0.050)
jt("shR",-0.195,0,1.47,0.088); jt("elR",-0.29,0.0,1.15,0.058); jt("wrR",-0.345,0.0,0.90,0.043); jt("haR",-0.365,0.0,0.80,0.050)
# legs
jt("hipL",0.10,0,0.92,0.100); jt("knL",0.135,-0.01,0.50,0.072); jt("anL",0.135,0,0.08,0.052); jt("toL",0.135,-0.17,0.035,0.055)
jt("hipR",-0.10,0,0.92,0.100); jt("knR",-0.135,-0.01,0.50,0.072); jt("anR",-0.135,0,0.08,0.052); jt("toR",-0.135,-0.17,0.035,0.055)

BONES = [("pelvis","spine"),("spine","chest"),("chest","neck"),("neck","head"),("head","htop"),
         ("chest","shL"),("shL","elL"),("elL","wrL"),("wrL","haL"),
         ("chest","shR"),("shR","elR"),("elR","wrR"),("wrR","haR"),
         ("pelvis","hipL"),("hipL","knL"),("knL","anL"),("anL","toL"),
         ("pelvis","hipR"),("hipR","knR"),("knR","anR"),("anR","toR")]

bm = bmesh.new()
verts = [None]*len(J)
for name,(idx,co,r) in J.items():
    verts[idx] = bm.verts.new(co)
bm.verts.ensure_lookup_table()
for a,b in BONES:
    bm.edges.new((verts[J[a][0]], verts[J[b][0]]))
me = bpy.data.meshes.new("NinjaBody"); bm.to_mesh(me); bm.free()
body = bpy.data.objects.new("NinjaBody", me); link(body)
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.modifier_add(type='SKIN')
sk = me.skin_vertices[0]
for name,(idx,co,r) in J.items():
    sk.data[idx].radius = (r, r)
sk.data[J["pelvis"][0]].use_root = True
# a touch of skin resize on chest for shoulders width already via radius
bpy.ops.object.modifier_apply(modifier=body.modifiers[0].name)
smooth(body)
subs = body.modifiers.new("Subsurf",'SUBSURF'); subs.levels=2; subs.render_levels=2
assign(body, m_suit)

# ---------------- helpers ----------------
def band(name, loc, major, minor, rot=(0,0,0), scale=(1,1,1), m=m_accent):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot)
    o=bpy.context.active_object; o.name=name; link(o); o.scale=scale
    smooth(assign(o,m)); return o

def curve_tube(name, pts, r, m, radii=None, flatten=1.0, res=4, tilt=None):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'
    cu.bevel_depth=r; cu.bevel_resolution=res; cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for i,p in enumerate(pts):
        bp=sp.bezier_points[i]; bp.co=Vector(p)
        bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
        bp.radius = radii[i] if radii else 1.0
    o=bpy.data.objects.new(name,cu); link(o); o.data.materials.append(m)
    if flatten!=1.0: o.scale=(1.0,flatten,1.0)
    return o

def box(name, loc, dims, rot=(0,0,0), m=m_suit):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o=bpy.context.active_object; o.name=name; link(o)
    o.scale=(dims[0]/2,dims[1]/2,dims[2]/2); assign(o,m); return o

# ---------------- face: slim eye slit with eyes ----------------
# narrow skin band across eye line (head center 1.66, front y ~ -0.15)
strip = box("EyeStrip",(0,-0.118,1.678),(0.215,0.072,0.034), m=m_skin)
strip.rotation_euler=(math.radians(3),0,0)
bev=strip.modifiers.new("b",'BEVEL'); bev.width=0.013; bev.segments=2
smooth(strip)
def eye(name,x):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.025, location=(x,-0.160,1.680))
    o=bpy.context.active_object; o.name=name; link(o); o.scale=(1.15,0.45,0.5)
    o.rotation_euler=(0,0,math.radians(-8 if x>0 else 8))
    smooth(assign(o,m_eye))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.013, location=(x,-0.180,1.678))
    p=bpy.context.active_object; p.name=name+"_pup"; link(p); p.scale=(1,0.45,1)
    smooth(assign(p,m_pup))
eye("EyeL",0.056); eye("EyeR",-0.056)

# ---------------- headband + forehead plate ----------------
hb = band("Headband",(0,0.0,1.737),0.132,0.024, rot=(0,0,0),
          scale=(1.0,0.98,1.0), m=m_accent)
plate = box("Plate",(0,-0.138,1.742),(0.135,0.03,0.05), m=m_metal)
plate.rotation_euler=(math.radians(4),0,0)
pb=plate.modifiers.new("b",'BEVEL'); pb.width=0.008; pb.segments=2; smooth(plate)
# two slim headband tails flowing down the back
curve_tube("HB_tail1",[(0.045,0.135,1.725),(0.075,0.205,1.52),(0.055,0.225,1.28),(0.09,0.225,1.02),(0.07,0.215,0.86)],
           0.032, m_accent, radii=[1,0.92,0.82,0.62,0.32], flatten=0.28)
curve_tube("HB_tail2",[(-0.02,0.135,1.72),(-0.035,0.205,1.50),(-0.02,0.225,1.24),(-0.05,0.225,0.98),(-0.03,0.215,0.82)],
           0.028, m_accent, radii=[1,0.88,0.78,0.58,0.30], flatten=0.28)

# ---------------- slim high collar (mask base) ----------------
band("Collar",(0,0,1.505),0.100,0.030, rot=(0,0,0), scale=(1.05,0.95,1.0), m=m_suit2)

# ---------------- chest strap (bandolier: over right shoulder to left hip) ----------------
curve_tube("ChestStrap",[(0.185,-0.075,1.50),(0.075,-0.155,1.30),(-0.06,-0.145,1.10),(-0.15,-0.085,0.99)],
           0.028, m_suit2, radii=[0.9,1.0,1.0,0.9], flatten=0.42)

# ---------------- waist sash + knot + hanging ends ----------------
band("Sash",(0,0,1.00),0.150,0.040, rot=(0,0,0), scale=(1.02,0.82,0.85), m=m_accent)
knot = box("Knot",(0.10,-0.115,1.0),(0.065,0.055,0.075), m=m_accent)
kb=knot.modifiers.new("b",'BEVEL'); kb.width=0.022; kb.segments=3; smooth(knot)
curve_tube("Sash_end1",[(0.11,-0.115,0.97),(0.13,-0.135,0.82),(0.11,-0.125,0.66),(0.13,-0.115,0.54)],
           0.038, m_accent, radii=[1,0.9,0.8,0.55], flatten=0.32)
curve_tube("Sash_end2",[(0.085,-0.12,0.97),(0.10,-0.14,0.80),(0.075,-0.13,0.62),(0.095,-0.12,0.50)],
           0.032, m_accent, radii=[1,0.85,0.72,0.5], flatten=0.32)

# ---------------- wrist + shin wraps + belt pouch ----------------
for jn in ("wrL","wrR"):
    _,co,_=J[jn]
    sx = 1 if co[0]>0 else -1
    for k in range(3):
        band(f"wristwrap_{jn}_{k}",(co[0]-sx*0.018*k, co[1], co[2]+0.075*k),0.050,0.013,
             rot=(0, math.radians(12*sx), 0), m=m_wrap)
# shin wraps
for jn in ("anL","anR"):
    _,co,_=J[jn]
    for k in range(3):
        band(f"shin_{jn}_{k}",(co[0],co[1],co[2]+0.11+0.075*k),0.072,0.016,
             rot=(0,0,0), scale=(1,1,1), m=m_wrap)
# thigh pouch (side of right thigh)
pouch=box("Pouch",(0.185,-0.02,0.80),(0.075,0.06,0.11), m=m_wrap)
pouch.rotation_euler=(0,math.radians(6),0)
pb2=pouch.modifiers.new("b",'BEVEL'); pb2.width=0.018; pb2.segments=2; smooth(pouch)

# ---------------- katana on the back (diagonal) ----------------
# saya (scabbard) as a slightly tapered tube, handle + tsuba + tip
saya_pts=[(-0.16,0.20,0.72),(0.02,0.22,1.05),(0.20,0.22,1.38),(0.34,0.21,1.62)]
saya=curve_tube("Saya",saya_pts,0.028,m_lacq,radii=[0.8,1.0,1.0,0.95],res=6)
# handle continues past the top
tsuka_pts=[(0.34,0.21,1.62),(0.44,0.205,1.80),(0.50,0.20,1.92)]
tsuka=curve_tube("Tsuka",tsuka_pts,0.026,m_wood,radii=[1.0,0.95,0.9],res=6)
# tsuba guard
band("Tsuba",(0.36,0.21,1.66),0.055,0.012, rot=(0,math.radians(58),0), scale=(1,1,1), m=m_gold)
# saya cord wrap
band("SayaCord",(0.10,0.22,1.20),0.035,0.008, rot=(0,math.radians(56),0), m=m_gold)

# ---------------- ground + backdrop ----------------
bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))
floor=bpy.context.active_object; floor.name="Floor"; link(floor)
assign(floor, mat("Floor",(0.05,0.05,0.06), rough=0.9))

# ---------------- world ----------------
world=bpy.data.worlds.new("W"); scene.world=world; world.use_nodes=True
wb=world.node_tree.nodes.get("Background")
wb.inputs["Color"].default_value=(0.045,0.045,0.055,1); wb.inputs["Strength"].default_value=1.0

# ---------------- lights ----------------
def light(name,kind,loc,energy,size=3.0,color=(1,1,1)):
    ld=bpy.data.lights.new(name,kind); ld.energy=energy
    if kind=='AREA': ld.size=size
    ld.color=color
    o=bpy.data.objects.new(name,ld); o.location=loc; scene.collection.objects.link(o)
    d=Vector((0,0,1.1))-Vector(loc); o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    return o
light("Key",'AREA',(-3,-4,4),900,size=5,color=(1.0,0.97,0.92))
light("Fill",'AREA',(4,-3,2),260,size=6,color=(0.7,0.78,1.0))
light("Rim",'AREA',(2,4,4),600,size=4,color=(0.8,0.7,1.0))

# ---------------- camera ----------------
cam_d=bpy.data.cameras.new("Cam"); cam_d.lens=68
cam=bpy.data.objects.new("Cam",cam_d)
if ANGLE=="back":
    cam.location=(1.4,4.9,1.35)
else:
    cam.location=(1.35,-4.95,1.22)
scene.collection.objects.link(cam)
look=Vector((0,0,1.02))-Vector(cam.location); cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
scene.camera=cam

# ---------------- render ----------------
scene.render.engine='CYCLES'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    for dt in ('OPTIX','CUDA'):
        try:
            prefs.compute_device_type=dt; prefs.get_devices()
            if any(d.type!='CPU' for d in prefs.devices):
                for d in prefs.devices: d.use=True
                scene.cycles.device='GPU'; break
        except Exception: continue
except Exception: pass
scene.cycles.samples=128; scene.cycles.use_denoising=True
scene.render.resolution_x=820; scene.render.resolution_y=1180
for vt in ('Khronos PBR Neutral','AgX','Standard'):
    try: scene.view_settings.view_transform=vt; break
    except Exception: continue

bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT_BLEND))
scene.render.filepath=bpy.path.abspath(OUT_RENDER)
scene.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
print("[ninja] DONE ->", bpy.path.abspath(OUT_BLEND), "|", bpy.path.abspath(OUT_RENDER))
