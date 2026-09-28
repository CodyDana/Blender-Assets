import sys,os,json,bpy,math,mathutils; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *; from scene_setup import *; from align import *
from bpy_extras.object_utils import world_to_camera_view
args=sys.argv[sys.argv.index('--')+1:]; mode,tag,focal,yaw,pitch=args[0],args[1],float(args[2]),float(args[3]),float(args[4])
OUT=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
SS=3; RW,RH=417,674
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"); refm=lum(ref)*255<235
sc=bpy.context.scene
if mode=='lod0':
    clear_scene(); objs=import_lod0(); shipped_materials(objs)
else:
    objs=[o for o in bpy.data.objects if o.type=='MESH' and o.visible_get() and o.name.startswith(args[5])] if len(args)>5 else []
    for o in list(bpy.data.objects):
        if o not in objs and o.type in('MESH','CURVE','LIGHT','CAMERA','SURFACE','META','FONT'): o.hide_render=True
    for o in objs: o.hide_render=False
    shipped_materials(objs, 7.8125)
print("OBJS",[o.name for o in objs])
lo,hi=bbox(objs); tgt=((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(lo[2]+hi[2])/2); Hh=hi[2]-lo[2]
for o in list(bpy.data.objects):
    if o.name.startswith("REV_"): bpy.data.objects.remove(o)
cam=camera(tgt,yaw,pitch,focal,(Hh/2*1.08)/(12/focal)); lights(tgt)
sc.render.engine='CYCLES'
try:
    pr=bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type='OPTIX'; pr.get_devices()
    for d in pr.devices: d.use=True
    sc.cycles.device='GPU'
except Exception as e: print("GPU fail",e)
sc.view_settings.view_transform='Standard'; sc.view_settings.look='None'; sc.view_settings.exposure=0; sc.view_settings.gamma=1
sc.render.film_transparent=True; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'; sc.render.image_settings.color_depth='8'
# calibration: albedo-1 diffuse card at target facing camera must read 0.95 linear
pl=bpy.data.meshes.new("REV_cal"); pl.from_pydata([(-.3,0,-.3),(.3,0,-.3),(.3,0,.3),(-.3,0,.3)],[],[(0,1,2,3)])
po=bpy.data.objects.new("REV_cal",pl); sc.collection.objects.link(po); po.location=tgt; po.location.y=lo[1]-0.05
po.rotation_euler=(0,0,math.radians(yaw))
cm=bpy.data.materials.new("REV_calm"); cm.use_nodes=True; b=cm.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(1,1,1,1); b.inputs['Roughness'].default_value=1; b.inputs['Specular IOR Level'].default_value=0; pl.materials.append(cm)
for o in objs: o.hide_render=True
sc.view_settings.view_transform='Raw' if False else 'Standard'
sc.render.resolution_x=64; sc.render.resolution_y=104; sc.cycles.samples=64; sc.cycles.use_denoising=False
sc.render.filepath=OUT+"tmp_cal.exr"; sc.render.image_settings.file_format='OPEN_EXR'
bpy.ops.render.render(write_still=True)
im=bpy.data.images.load(OUT+"tmp_cal.exr"); a=np.array(im.pixels[:]).reshape(104,64,4); v=float(a[40:64,24:40,:3].mean()); bpy.data.images.remove(im); os.remove(OUT+"tmp_cal.exr")
calv=v; k=0.95/v; print("CAL value",v,"scale",k)
for o in sc.objects:
    if o.type=='LIGHT': o.data.energy*=k
sc.world.node_tree.nodes['Background'].inputs[1].default_value*=k
bpy.data.objects.remove(po)
for o in objs: o.hide_render=False
sc.render.image_settings.file_format='PNG'
sc.render.resolution_x=RW*SS; sc.render.resolution_y=RH*SS; sc.cycles.samples=384; sc.cycles.use_denoising=True
raw=OUT+f"render_{tag}_raw.png"; sc.render.filepath=raw; bpy.ops.render.render(write_still=True)
a=load(raw); m=a[...,3]>0.5
v,(s,tx,ty)=best_align(m[::SS,::SS],refm); s=s/SS  # coarse at 1x
# refine at full ref res with supersampled mask
mf=m.astype(np.float32); best=(0,None)
for ds in (0.99,0.995,1,1.005,1.01):
    for dx in np.arange(-1.5,1.6,0.5):
        for dy in np.arange(-1.5,1.6,0.5):
            mm=warp(mf,s*ds,tx+dx,ty+dy,refm.shape,1)>0.5; q=iou(mm,refm)
            if q>best[0]: best=(q,(s*ds,tx+dx,ty+dy))
v,(s,tx,ty)=best; print("ALIGN iou",v,s,tx,ty)
rgb=a[...,:3]*a[...,3:4]+(1-a[...,3:4])  # over white (display space)
# supersampled warp: average SSxSS subsamples
acc=np.zeros((RH,RW,3),np.float32); accm=np.zeros((RH,RW),np.float32)
for i in range(SS):
    for j in range(SS):
        ox=(i+0.5)/SS-0.5; oy=(j+0.5)/SS-0.5
        acc+=warp(rgb,s,tx-ox,ty-oy,(RH,RW),1); accm+=warp(mf,s,tx-ox,ty-oy,(RH,RW),1)
ours=acc/SS/SS; oursm=accm/SS/SS
# pixels outside the render frame -> white
ours=np.where((ours.sum(2)==0)[...,None],1,ours)
save(np.clip(ours,0,1),OUT+f"ours_{tag}_refframe.png")
np.save(OUT+f"ours_{tag}_mask.npy",oursm)
# project 3D landmarks to ref pixels
def proj(p):
    c=world_to_camera_view(sc,cam,mathutils.Vector(p)); x=c.x*RW*SS; y=(1-c.y)*RH*SS
    return [float(s*x+tx), float(s*y+ty)]
lm={}
for o in objs:
    if 'Ring' in o.name or 'BlackenedRing' in o.name:
        vs=np.array([o.matrix_world@vv.co for vv in o.data.vertices]); lm['clasp_ring_centre']=proj(vs.mean(0))
json.dump({"tag":tag,"mode":mode,"focal":focal,"yaw":yaw,"pitch":pitch,"cal_value":calv,"light_scale":k,"align":{"iou":float(best[0]),"s":s,"tx":tx,"ty":ty},"cam_loc":list(cam.location),"target":list(tgt),"landmarks3d":lm,"objects":[o.name for o in objs]},open(OUT+f"render_{tag}.json","w"),indent=1,default=float)
print("DONE",lm)
