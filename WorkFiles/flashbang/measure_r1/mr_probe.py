import bpy, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r"C:/Users/Cody/Desktop/Blender_Projects/Exports/Flashbang/SM_Flashbang.fbx")
for o in bpy.data.objects:
    d = o.dimensions
    print("OBJ", o.name, o.type, o.parent.name if o.parent else None, tuple(round(x,4) for x in o.location), tuple(round(x,4) for x in d), tuple(round(x,3) for x in o.scale))
    if o.type=='MESH':
        print("   mats", [m.name if m else None for m in o.data.materials], "uv", [u.name for u in o.data.uv_layers], "polys", len(o.data.polygons))
