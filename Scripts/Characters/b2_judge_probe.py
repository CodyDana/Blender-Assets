import bpy
for c in bpy.data.collections:
    print("COLL", c.name, [o.name for o in c.objects][:50], c.hide_render)
for o in bpy.data.objects:
    if o.type=='MESH' and not o.name.startswith('TEST'):
        mats=[]
        for m in o.data.materials:
            imgs=[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m and m.node_tree else []
            mats.append((m.name if m else None, imgs))
        print("OBJ", o.name, o.hide_render, [c.name for c in o.users_collection], mats)
for o in bpy.data.objects:
    if o.type!='MESH': print("NONMESH", o.name, o.type)
print("ENGINE", bpy.context.scene.render.engine, bpy.context.scene.camera)
for i in bpy.data.images: print("IMG", i.name, i.size[:], i.packed_file is not None)
