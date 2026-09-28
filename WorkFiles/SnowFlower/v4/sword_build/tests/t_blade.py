import sys, time, math
sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import sfv4_spec as S, sfv4_blade as B, sfv4_mesh as M, sfv4_rev3 as R3
col=bpy.context.scene.collection
t=time.time()
for lv in (0,1,2):
    mb=M.MB(f'blade{lv}'); B.blade_steel(mb,lv)
    for sd in (-1,1): B.relief_low(mb,sd,lv)
    ob=mb.to_object(f'LOD{lv}',col); ob.location.x=0.2*lv
    print('LOD',lv,'tris',mb.tri_count(),'islands',len(mb.islands()))
mbh=M.MB('bh'); B.blade_steel(mbh,'high')
sink=R3.Sink('relief')
for sd in (-1,1): B.relief_high(sink,sd)
tot=mbh.tri_count()+sum(m.tri_count() for m in sink.mbs.values())
print('high tris',tot, time.time()-t)
ob=mbh.to_object('high',col); ob.location.x=-0.2
for k,m in sink.mbs.items():
    o=m.to_object(f'rel{k}',col,recalc=False); o.location.x=-0.2
bpy.ops.wm.save_as_mainfile(filepath=r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/sword_build/tests/t_blade.blend')
