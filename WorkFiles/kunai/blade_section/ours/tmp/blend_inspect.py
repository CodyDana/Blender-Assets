import bpy
for o in bpy.data.objects:
    if 'Kunai' in o.name or 'kunai' in o.name.lower():
        print('OBJ', o.name, o.type, [m.name for m in o.data.materials] if o.type=='MESH' else '', o.hide_render, tuple(round(v,4) for v in o.location), tuple(round(v,4) for v in o.rotation_euler), o.parent.name if o.parent else None, len(o.data.polygons) if o.type=='MESH' else '')
print('ALLOBJ', len(bpy.data.objects))
for m in bpy.data.materials:
    if 'Kunai' in m.name:
        print('MAT', m.name, [ (n.type, n.image.name if getattr(n,'image',None) else '') for n in m.node_tree.nodes])
for i in bpy.data.images:
    if 'Kunai' in i.name: print('IMG', i.name, i.filepath, i.packed_file is not None, tuple(i.size))
print('COLL', [c.name for c in bpy.data.collections])
print('SCENES', [s.name for s in bpy.data.scenes])
