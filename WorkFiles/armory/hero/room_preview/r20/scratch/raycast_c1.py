# raycast_c1.py: what C1 pixels (x, y on 1448 x 1086) see, through glass. blender -b <blend> --python raycast_c1.py -- x y0 y1 step
import sys
import bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
x, y0, y1, st = (int(v) for v in a[:4])
f = 40 / 36 * 1448
cy = 1086 / 2 - 0.315 * 1448
cam = Vector((6.0, -4.18, 3.39))
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
for y in range(y0, y1, st):
    d = Vector(((x - 724) / f, 1.0, -(y - cy) / f)).normalized()
    o = cam.copy()
    hits = []
    for _ in range(20):
        ok, loc, nrm, idx, ob, mw = sc.ray_cast(dg, o, d)
        if not ok:
            break
        mat = ""
        try:
            me = ob.data
            mat = me.materials[me.polygons[idx].material_index].name if me.materials else ""
        except Exception:
            pass
        hits.append(f"{ob.name.split('__')[0]}[{mat}]@({loc.x:.2f},{loc.y:.2f},{loc.z:.2f})")
        if "Glass" not in mat:
            break
        o = loc + d * 0.001
    print("RAY", y, len(hits), hits[-1])
