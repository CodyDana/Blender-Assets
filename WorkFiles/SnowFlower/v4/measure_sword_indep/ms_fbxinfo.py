import bpy, mathutils
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.fbx(filepath=r"C:/Users/Cody/Desktop/Blender_Projects/Exports/SnowFlower/v4/SM_SnowFlower.fbx")
bpy.context.view_layer.update()
for o in bpy.data.objects:
    s = f"{o.name} {o.type} parent={o.parent.name if o.parent else None} scale={tuple(round(v,4) for v in o.scale)}"
    if o.type=='MESH':
        bb=[o.matrix_world@mathutils.Vector(c) for c in o.bound_box]
        mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
        tris=sum(len(p.vertices)-2 for p in o.data.polygons)
        s+=f" tris={tris} mats={[m.name if m else None for m in o.data.materials]} uvs={[u.name for u in o.data.uv_layers]} min={[round(v*1000,1) for v in mn]} max={[round(v*1000,1) for v in mx]}"
    print("OBJ",s)
