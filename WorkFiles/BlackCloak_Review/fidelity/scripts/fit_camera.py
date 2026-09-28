import sys,os,json,bpy; sys.path.insert(0,os.path.dirname(__file__))
from imgutil import *; from scene_setup import *; from align import *
args=sys.argv[sys.argv.index('--')+1:]; mode=args[0]  # 'lod0' or 'mh'
OUT=r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
ref=load(r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"); refm=lum(ref)*255<235; refm_h=refm[::2,::2]
if mode=='lod0':
    clear_scene(); objs=import_lod0()
else:
    objs=[o for o in bpy.data.objects if o.type=='MESH' and o.visible_get()]
    for o in bpy.data.objects:
        if o not in objs and o.type in('MESH','CURVE','CAMERA','LIGHT'): o.hide_render=True
lo,hi=bbox(objs); tgt=((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,(lo[2]+hi[2])/2); Hh=hi[2]-lo[2]
sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.render.film_transparent=True
sc.render.resolution_x=208; sc.render.resolution_y=337; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'
res=[]
for f in (50,100):
    for yaw in range(-15,16,5):
        for pitch in (-5,0,5,10):
            for o in list(bpy.data.objects):
                if o.name.startswith("REV_Cam"): bpy.data.objects.remove(o)
            dist=(Hh/2*1.08)/(12/f)
            camera(tgt,yaw,pitch,f,dist)
            p=OUT+"tmp_fit.png"; sc.render.filepath=p; bpy.ops.render.render(write_still=True)
            a=load(p); m=a[...,3]>0.5
            v,(s,tx,ty)=best_align(m,refm_h); res.append((v,f,yaw,pitch)); print("FIT",f,yaw,pitch,round(v,4),flush=True)
res.sort(reverse=True); print("BEST",res[:8])
json.dump({"mode":mode,"target":list(map(float,tgt)),"height":float(Hh),"top":[list(map(float,r)) for r in res[:15]]},open(OUT+f"camfit_{mode}.json","w"),indent=1)
os.remove(OUT+"tmp_fit.png")
