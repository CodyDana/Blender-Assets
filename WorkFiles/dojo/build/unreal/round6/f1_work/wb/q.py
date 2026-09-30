import bpy, collections
c=collections.Counter()
for o in bpy.data.objects:
    if 'DKX' in o.name or 'DK_Wall' in o.name:
        c[(o.name.split('.')[0][:22], o.type, o.hide_render, o.instance_type, tuple(x.name for x in o.users_collection)[:1])]+=1
for k,v in list(c.items())[:40]: print(k,v)
print([ (x.name, x.hide_render) for x in bpy.data.collections][:30])
