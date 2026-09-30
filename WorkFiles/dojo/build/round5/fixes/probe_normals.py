import bpy
from mathutils import Vector
o = bpy.data.objects["SM_DKP_Train_WoodenDummy"]
me = o.data
cn = me.corner_normals
angs = []; flat = 0; tot = 0
for p in me.polygons:
    c = p.center
    if 0.75 < c.z < 0.95 and abs(Vector((c.x, c.y)).length - 0.16) < 0.008 and abs(p.normal.z) < 0.2:
        tot += 1
        flat += (not p.use_smooth)
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            angs.append(Vector((v.x, v.y, 0)).normalized().angle(Vector(cn[li].vector)) * 57.3)
angs.sort()
print("PROBE faces", tot, "flat", flat, "angles p50/p90/max", angs[len(angs)//2], angs[int(len(angs)*0.9)], angs[-1])
