import bpy
print('COLLS', [(c.name, len(c.objects), c.hide_render) for c in bpy.data.collections])
