import bpy
from mathutils import Vector
for name in ("SM_DKX_Ridge1", "SM_DKX_FarGround", "SM_DKX_FarTown"):
    o = bpy.data.objects.get(name)
    me = o.data
    up = inward = n = 0
    for p in me.polygons[:4000]:
        c = p.center
        r = Vector((c.x, c.y, 0.0))
        if r.length < 1e-6:
            continue
        n += 1
        up += p.normal.z > 0
        inward += p.normal.dot(-r.normalized()) > 0
    print("NORM", name, "faces", len(me.polygons), "sampled", n, "normal up", up, "inward", inward)
