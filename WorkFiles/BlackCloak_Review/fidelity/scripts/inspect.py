import bpy, sys
dg=bpy.context.evaluated_depsgraph_get()
print("SCENES",[s.name for s in bpy.data.scenes])
for c in bpy.data.collections: print("COLL",c.name,[o.name for o in c.objects][:40], c.hide_render)
for o in bpy.data.objects:
    info=""
    if o.type=='MESH':
        e=o.evaluated_get(dg); m=e.to_mesh(); m.calc_loop_triangles()
        info=f"tris={len(m.loop_triangles)} verts={len(m.vertices)} uvs={[u.name for u in o.data.uv_layers]} mats={[s.material.name if s.material else None for s in o.material_slots]} mods={[md.type for md in o.modifiers]}"
        e.to_mesh_clear()
    print("OBJ",o.name,o.type,"hide_render",o.hide_render,"par",o.parent.name if o.parent else None,[round(x,3) for x in o.dimensions],[round(x,3) for x in o.location],info)
for m in bpy.data.materials:
    if m.node_tree:
        print("MAT",m.name,[(n.type,n.image.name if getattr(n,'image',None) else '') for n in m.node_tree.nodes])
for i in bpy.data.images: print("IMG",i.name,i.filepath,i.size[:],i.packed_file is not None)
sc=bpy.context.scene; print("CAM",sc.camera, sc.render.engine, sc.view_settings.view_transform)
