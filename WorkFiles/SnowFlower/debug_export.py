import bpy,json
from pathlib import Path
R=Path(r'C:\Users\Cody\Desktop\Blender_Projects')
bpy.ops.wm.open_mainfile(filepath=str(R/'Assets/SnowFlower/SnowFlower_Game.blend'))
o=bpy.data.objects['SM_SnowFlower'];o.data.calc_loop_triangles()
print('GAME',len(o.data.vertices),len(o.data.polygons),len(o.data.loop_triangles),'mods',[(m.name,m.type) for m in o.modifiers],flush=True)
print('VALIDATE',o.data.validate(verbose=True,clean_customdata=True),flush=True)
o.data.calc_loop_triangles();print('AFTER',len(o.data.vertices),len(o.data.loop_triangles),flush=True)
for f in ['SM_SnowFlower.fbx','SM_SnowFlower_LOD1.fbx','SM_SnowFlower_LOD2.fbx']:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(R/'Exports/SnowFlower'/f),use_anim=False)
    counts=[]
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH':
            ob.data.calc_loop_triangles();counts.append((ob.name,len(ob.data.vertices),len(ob.data.loop_triangles)))
    print('FBX_COUNT',f,counts,flush=True)
