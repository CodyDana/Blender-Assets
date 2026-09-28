import bpy, math, random
from mathutils import Vector

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
scene=bpy.context.scene
coll=bpy.data.collections.new("SummoningJutsu"); scene.collection.children.link(coll)
random.seed(11)

def mat(name, base, rough=0.6):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*base,1)
    b.inputs["Roughness"].default_value=rough
    return m
m_floor=mat("Jutsu_Floor",(0.92,0.92,0.90),0.55)
m_ink  =mat("Jutsu_Ink",(0.004,0.004,0.004),0.95)

bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0,0,0))
floor=bpy.context.active_object; floor.name="Floor"
for c in floor.users_collection: c.objects.unlink(floor)
coll.objects.link(floor)
floor.data.materials.append(m_floor)

FONT=bpy.data.fonts.load(r"C:\Users\Cody\Desktop\Blender_Projects\References\Fonts\MasaFont-Bold.ttf")
Z=0.0015

# summoning-jutsu vocabulary: kuchiyose no jutsu, summon, contract, blood seal, ninjutsu, seal
PHRASES=["口寄せの術","召喚","契約","血判","忍術","印"]
def char_stream():
    while True:
        for ph in PHRASES:
            for ch in ph:
                yield ch
            pass  # continuous chain, no gaps
stream=char_stream()

glyph_objs=[]
def place_char(ch,x,y,rot,size):
    cu=bpy.data.curves.new("g",'FONT')
    cu.body=ch; cu.font=FONT
    cu.size=size; cu.align_x='CENTER'; cu.align_y='CENTER'
    cu.shear=random.uniform(-0.06,0.06)
    cu.fill_mode='BOTH'
    cu.offset=0.0017
    ob=bpy.data.objects.new("g",cu)
    ob.location=(x,y,Z)
    ob.rotation_euler=(0,0,rot)
    coll.objects.link(ob)
    glyph_objs.append(ob)

ADV=0.033
def circle_text(r):
    n=int(2*math.pi*r/ADV)
    for i in range(n):
        ch=next(stream)
        if ch is None: continue
        a=2*math.pi*i/n
        # yield to the spoke lines: skip circle glyphs that would overlap a spoke chain
        d=abs(((a + math.pi/8) % (math.pi/4)) - math.pi/8)
        if d*r < 0.030: continue
        rr=r
        rot=a - math.pi/2 + math.pi + random.uniform(-0.05,0.05)
        place_char(ch, rr*math.cos(a), rr*math.sin(a), rot, random.uniform(0.065,0.100))
def spoke_text(a, r0, r1):
    n=int((r1-r0)/ADV)
    for i in range(n):
        ch=next(stream)
        if ch is None: continue
        r=r0+(r1-r0)*i/max(1,n-1)
        off=0.0
        ca,sa=math.cos(a),math.sin(a)
        rot=a - math.pi/2 + random.uniform(-0.05,0.05)
        place_char(ch, r*ca - sa*off, r*sa + ca*off, rot, random.uniform(0.065,0.100))

circle_text(0.55)
circle_text(0.85)
for k in range(8):
    spoke_text(k*math.pi/4, 0.055, 1.90)   # chains approach the center but leave a small clear gap (ref sumjutsu3)
print("glyphs placed:",len(glyph_objs))

# merge all glyph curves into one mesh via bmesh (no ops)
import bmesh
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
bm=bmesh.new()
for ob in glyph_objs:
    oe=ob.evaluated_get(deps)
    tme=oe.to_mesh()
    tme.transform(ob.matrix_world)
    bm.from_mesh(tme)
    oe.to_mesh_clear()
me=bpy.data.meshes.new("SealScript")
bm.to_mesh(me); bm.free()
seal=bpy.data.objects.new("SealScript",me)
coll.objects.link(seal)
for ob in glyph_objs: bpy.data.objects.remove(ob, do_unlink=True)
seal.data.materials.append(m_ink)
print("seal mesh faces:",len(seal.data.polygons))

w=bpy.data.worlds.new("W"); scene.world=w; w.use_nodes=True
w.node_tree.nodes.get("Background").inputs["Color"].default_value=(0.9,0.9,0.92,1)
w.node_tree.nodes.get("Background").inputs["Strength"].default_value=0.6
sd=bpy.data.lights.new("Sun",'SUN'); sd.energy=3.0; sd.angle=math.radians(15)
sun=bpy.data.objects.new("Sun",sd); scene.collection.objects.link(sun)
sun.rotation_euler=(math.radians(35),0,math.radians(30))
cd=bpy.data.cameras.new("Cam"); cd.lens=40
cam=bpy.data.objects.new("Cam",cd); scene.collection.objects.link(cam)
cam.location=(0.0,-2.6,2.0)
d=Vector((0,0.25,0))-Vector(cam.location)
cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
scene.camera=cam
scene.render.engine='CYCLES'
try:
    p=bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type='OPTIX'; p.get_devices()
    for dv in p.devices: dv.use=True
    scene.cycles.device='GPU'
except Exception as e: print(e)
scene.cycles.samples=64; scene.cycles.use_denoising=True
scene.render.resolution_x=1200; scene.render.resolution_y=800
scene.view_settings.view_transform='Standard'

bpy.ops.wm.save_as_mainfile(filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Assets\SummoningJutsu.blend")
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Renders\jutsu_persp.png"
bpy.ops.render.render(write_still=True)
cam.location=(0,0,3.2); cam.rotation_euler=(0,0,0)
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Renders\jutsu_top.png"
bpy.ops.render.render(write_still=True)
# matched-angle view like sumjutsu1 (low 3/4, seal filling frame)
cam.location=(0.0,-2.35,1.35)
d=Vector((0,0.05,0))-Vector(cam.location)
cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1193; scene.render.resolution_y=670
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Renders\jutsu_match.png"
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_mainfile()
print("SUMMONING2_OK")
