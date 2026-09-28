import bpy
for m in bpy.data.materials:
    if not m.node_tree: continue
    print("MAT",m.name, m.blend_method if hasattr(m,'blend_method') else '')
    for n in m.node_tree.nodes:
        vals={}
        for i in n.inputs:
            if not i.is_linked and hasattr(i,'default_value'):
                v=i.default_value
                try: v=tuple(round(x,3) for x in v)
                except TypeError: v=round(v,3) if isinstance(v,float) else v
                if i.name in('Base Color','Roughness','Metallic','Strength','Scale','Vector','Specular IOR Level','Sheen Weight','Coat Weight'): vals[i.name]=v
        extra = getattr(n,'operation','') or getattr(n,'space','')
        print("  N",n.type,n.name,extra,vals,[(l.from_node.name,l.from_socket.name,l.to_socket.name) for i in n.inputs for l in i.links])
