import sys, time
sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import sfv4_assemble as A
col=bpy.context.scene.collection
mats=[]
cols=[(.3,.33,.38),(.8,.8,.8),(.6,.6,.62),(.05,.05,.06),(.08,.09,.11),(.5,.5,.5),(.03,.03,.03),(.1,.1,.1)]
for i,c in enumerate(cols):
    m=bpy.data.materials.new(f'hm{i}'); m.diffuse_color=(*c,1); mats.append(m)
lm=[bpy.data.materials.new('steel'),bpy.data.materials.new('wrap')]
lm[0].diffuse_color=(.55,.57,.6,1); lm[1].diffuse_color=(.06,.06,.06,1)
t=time.time()
tot={}
for lv in (0,1,2):
    L=A.build_low(lv)
    tot[lv]={k:v.tri_count() for k,v in L.items()}
    for k,mb in L.items():
        o=mb.to_object(f'{k}_L{lv}',col,materials=lm); o.location.x=0.16*(lv+1)
print('LOW',tot, {lv:sum(v.values()) for lv,v in tot.items()}, time.time()-t)
H=A.build_high()
ht=0
for part,d in H.items():
    for m,mb in d.items():
        ht+=mb.tri_count()
        o=mb.to_object(f'H_{part}_{m}',col,materials=mats,recalc=False)
print('HIGH tris',ht,time.time()-t)
bpy.ops.wm.save_as_mainfile(filepath=r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sword_build/tests/t_all.blend')
