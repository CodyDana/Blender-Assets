import bpy, sys
sc=bpy.context.scene
print("UNITS", sc.unit_settings.system, sc.unit_settings.scale_length, sc.unit_settings.length_unit)
for o in bpy.data.objects:
    extra=""
    if o.type=='MESH':
        me=o.data; extra=f"v{len(me.vertices)} tris{sum(len(p.vertices)-2 for p in me.polygons)} mats{[m.name if m else None for m in me.materials]} uv{[u.name for u in me.uv_layers]}"
    print("OBJ", o.name, o.type, tuple(round(x,4) for x in o.dimensions), tuple(round(x,4) for x in o.location), tuple(round(x,4) for x in o.scale), o.parent.name if o.parent else "-", [c.name for c in o.users_collection], extra)
for m in bpy.data.materials:
    if m.node_tree:
        print("MAT", m.name, [ (n.type, n.image.name if n.type=='TEX_IMAGE' and n.image else '') for n in m.node_tree.nodes])
for i in bpy.data.images: print("IMG", i.name, i.filepath, tuple(i.size))
