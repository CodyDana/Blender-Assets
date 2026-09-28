# sm_m08: list objects of the rev-3 game blend (read-only; never saved)
import bpy
from mathutils import Vector
print("FILE", bpy.data.filepath, "unit scale", bpy.context.scene.unit_settings.scale_length)
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == 'MESH':
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
        print("%-40s %-6s tris %7d mats %-40s min %s max %s" % (o.name, o.type, sum(len(p.vertices)-2 for p in o.data.polygons), [m.name for m in o.data.materials if m], [round(x,4) for x in mn], [round(x,4) for x in mx]))
    else:
        print("%-40s %-6s loc %s parent %s" % (o.name, o.type, [round(x,4) for x in o.matrix_world.translation], o.parent.name if o.parent else None))
