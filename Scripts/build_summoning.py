import bpy, bmesh, math, random
from mathutils import Vector

# fresh file
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
scene=bpy.context.scene
coll=bpy.data.collections.new("SummoningJutsu"); scene.collection.children.link(coll)
random.seed(7)

def mat(name, base, rough=0.6, metallic=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*base,1)
    b.inputs["Roughness"].default_value=rough
    b.inputs["Metallic"].default_value=metallic
    return m
m_floor=mat("Jutsu_Floor",(0.92,0.92,0.90),0.55)
m_ink  =mat("Jutsu_Ink",(0.004,0.004,0.004),0.95)

# ---------------- white floor ----------------
bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0,0,0))
floor=bpy.context.active_object; floor.name="Floor"
for c in floor.users_collection: c.objects.unlink(floor)
coll.objects.link(floor)
floor.data.materials.append(m_floor)

# ---------------- script-stroke seal ----------------
bm=bmesh.new()
Z=0.0015
def stroke(cx,cy,ang,L,wdt):
    ca,sa=math.cos(ang),math.sin(ang)
    hx,hy=ca*L/2, sa*L/2
    px,py=-sa*wdt/2, ca*wdt/2
    vs=[bm.verts.new((cx-hx-px, cy-hy-py, Z)),
        bm.verts.new((cx+hx-px, cy+hy-py, Z)),
        bm.verts.new((cx+hx+px, cy+hy+py, Z)),
        bm.verts.new((cx-hx+px, cy-hy+py, Z))]
    bm.faces.new(vs)
def glyph(cx,cy,base_ang):
    n=random.randint(3,5)
    for k in range(n):
        ang=base_ang + math.radians(random.choice((0,0,0,20,-20,40,-40,90)) + random.uniform(-12,12))
        L=random.uniform(0.035,0.075)
        w=random.uniform(0.007,0.013)
        ox=random.uniform(-0.016,0.016); oy=random.uniform(-0.016,0.016)
        stroke(cx+ox, cy+oy, ang, L, w)

def circle_path(r, step=0.033):
    n=max(12,int(2*math.pi*r/step))
    for i in range(n):
        a=2*math.pi*i/n + random.uniform(-0.01,0.01)
        rr=r + random.uniform(-0.012,0.012)
        glyph(rr*math.cos(a), rr*math.sin(a), a+math.pi/2)
def spoke_path(a, r0, r1, step=0.038):
    n=int((r1-r0)/step)
    for i in range(n):
        r=r0+(r1-r0)*i/max(1,n-1) + random.uniform(-0.012,0.012)
        off=random.uniform(-0.014,0.014)
        ca,sa=math.cos(a),math.sin(a)
        glyph(r*ca - sa*off, r*sa + ca*off, a)

circle_path(0.55)                # inner circle
circle_path(0.85)                # outer circle
for k in range(8):               # 8 radiating script lines
    a=k*math.pi/4
    spoke_path(a, 0.07, 1.55)

bm.normal_update()
me=bpy.data.meshes.new("SealScript"); bm.to_mesh(me); bm.free()
seal=bpy.data.objects.new("SealScript",me); coll.objects.link(seal)
seal.data.materials.append(m_ink)
print("strokes:",len(me.polygons))

# ---------------- world / lights / cameras ----------------
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
# top-down view
cam.location=(0,0,3.2); cam.rotation_euler=(0,0,0)
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Renders\jutsu_top.png"
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_mainfile()
print("SUMMONING_OK")
