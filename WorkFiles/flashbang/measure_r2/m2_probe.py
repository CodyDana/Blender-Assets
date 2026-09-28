import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath="C:/Users/Cody/Desktop/Blender_Projects/Exports/Flashbang/SM_Flashbang.fbx")
for o in bpy.data.objects:
    print("M2P", o.name, o.type, o.parent.name if o.parent else None, tuple(round(x,4) for x in o.matrix_world.translation), tuple(round(x,4) for x in o.dimensions), len(o.data.polygons) if o.type=='MESH' else '', [m.name for m in o.data.materials] if o.type=='MESH' else '', [u.name for u in o.data.uv_layers] if o.type=='MESH' else '')
