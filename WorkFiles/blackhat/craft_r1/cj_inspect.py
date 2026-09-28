import bpy, json
out={}
for o in bpy.data.objects:
    d={'type':o.type,'loc':list(o.location),'rot':list(o.rotation_euler),'dims':list(o.dimensions),'parent':o.parent.name if o.parent else None,'hide_render':o.hide_render,'colls':[c.name for c in o.users_collection]}
    if o.type=='MESH':
        me=o.data; d['verts']=len(me.vertices); d['tris']=sum(len(p.vertices)-2 for p in me.polygons)
        d['mats']=[m.name if m else None for m in me.materials]; d['uvs']=[u.name for u in me.uv_layers]
        d['mods']=[m.type for m in o.modifiers]
    out[o.name]=d
mats={}
for m in bpy.data.materials:
    if m.node_tree:
        mats[m.name]=[(n.type,n.name,getattr(getattr(n,'image',None),'name',None)) for n in m.node_tree.nodes]
out['_materials']=mats
out['_images']={i.name:(i.filepath,list(i.size),i.colorspace_settings.name) for i in bpy.data.images}
out['_scenes']=[(s.name,s.render.engine,s.camera.name if s.camera else None) for s in bpy.data.scenes]
print("CJJSON"+json.dumps(out))
