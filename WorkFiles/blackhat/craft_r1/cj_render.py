import bpy, math, sys, os
from mathutils import Vector
OUT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/craft_r1/r/"
os.makedirs(OUT,exist_ok=True)
T="C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackHat/Textures/"
for im in bpy.data.images:
    if im.name.startswith("T_BlackHat"):
        im.filepath=T+im.name+".png"; im.reload()
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
sc.view_settings.view_transform='Standard'
sc.render.film_transparent=False
w=bpy.data.worlds.new("cjW"); sc.world=w; w.use_nodes=True
bg=[n for n in w.node_tree.nodes if n.type=='BACKGROUND'][0]; bg.inputs[0].default_value=(0.9,0.9,0.9,1); bg.inputs[1].default_value=0.6
objs={o.name:o for o in bpy.data.objects}
for n,o in objs.items():
    if n.startswith("UCX") or n.startswith("SOCKET"): o.hide_render=True
def show(lod):
    for i in range(3): objs[f"SM_BlackHat_LOD{i}"].hide_render=(i!=lod)
sun=bpy.data.objects.new("cjSun",bpy.data.lights.new("cjSun",'SUN')); sc.collection.objects.link(sun)
sun.data.energy=4.0; sun.data.angle=math.radians(3)
cam=bpy.data.objects.new("cjCam",bpy.data.cameras.new("cjCam")); sc.collection.objects.link(cam); sc.camera=cam
root=objs["SM_BlackHat_LodGroup"]
def aim(loc,target,lens=85):
    cam.location=Vector(loc); d=Vector(target)-cam.location
    cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); cam.data.lens=lens
def sunrot(elev,az):
    sun.rotation_euler=(math.radians(90-elev),0,math.radians(az))
def R(name,res,samples=16):
    sc.render.resolution_x,sc.render.resolution_y=res; sc.render.resolution_percentage=100
    sc.eevee.taa_render_samples=samples
    sc.render.filepath=OUT+name+".png"; bpy.ops.render.render(write_still=True)
mode=sys.argv[sys.argv.index("--")+1]
tgt=(0,0,0.07)
def orbit(dist,elev,yaw):
    e=math.radians(elev); a=math.radians(yaw+180)
    return (dist*math.cos(e)*math.sin(a), -dist*math.cos(e)*math.cos(a), tgt[2]+dist*math.sin(e))
if mode=="turn":
    show(0); sunrot(45,140)
    for i in range(12):
        root.rotation_euler=(0,0,math.radians(i*3))
        aim(orbit(3.2,18,0),tgt); R(f"turn_hero_{i:02d}",(960,540),1)
    for i in range(12):
        root.rotation_euler=(0,0,math.radians(i*3))
        aim(orbit(9.0,18,0),tgt); R(f"turn_thumb_{i:02d}",(480,270),1)
    root.rotation_euler=(0,0,0)
elif mode=="views":
    show(0)
    sunrot(8,100); aim(orbit(2.6,18,0),tgt); R("rake_low_left",(1280,720),32)
    sunrot(40,150); aim(orbit(1.3,5,35),(0.17,0.17,-0.02)); R("tails_side",(1200,900),32)
    aim(orbit(1.3,5,100),(0.2,0.15,-0.02)); R("tails_edge",(1200,900),32)
    sunrot(40,150); aim(orbit(1.2,25,-10),(0,0,0.13)); R("crown_close",(1200,900),32)
    sunrot(-60,20); aim(orbit(2.4,-50,10),(0,0,0.05)); R("under_neutral",(1200,900),32)
    sunrot(35,140); aim(orbit(1.0,15,-40),(-0.2,0.2,0.0)); R("rim_close",(1200,900),32)
elif mode=="lods":
    sunrot(45,140)
    # hat width ~648 px of 1920 (LOD0->1 switch), ~227 px (LOD1->2)
    for lod in (0,1,2):
        show(lod); aim(orbit(3.2,18,0),tgt); R(f"lod{lod}_648",(1152,648),16)
        aim(orbit(9.1,18,0),tgt); R(f"lod{lod}_227",(1152,648),16)
