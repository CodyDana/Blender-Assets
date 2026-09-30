"""Read-only probe on DojoShowcase.blend: around the west route-2 pier (X -1.2..0.2, Y 26.4..27.6), for each x strip, the
lowest z of every outbuilding roof mesh face at Y < 27.6 and its min Y; and the pier's max Y / top by x strip."""
import bpy, json
from mathutils import Vector
asm = bpy.data.collections["Assembly"].objects
def verts(o):
    mw = o.matrix_world
    return [mw @ v.co for v in o.data.vertices]
res = {"roof": {}, "pier": {}}
for o in asm:
    p = o.name.split("__")[0]
    if o.type != "MESH":
        continue
    if p.startswith("SM_DKO_Roof") or p.startswith("SM_DKO_Store_Gable") or p.startswith("SM_DKO_Gutter"):
        vs = [v for v in verts(o) if -1.3 < v.x < 0.3 and v.y < 27.7 and 26.0 < v.y]
        for v in vs:
            k = round(v.x * 5) / 5
            r = res["roof"].setdefault(p, {}).setdefault(k, [99, 99])
            r[0] = min(r[0], round(v.y, 3)); r[1] = min(r[1], round(v.z, 3))
    if p == "SM_DK_Wall_StepPier" and o.matrix_world.translation.x < 0:
        vs = verts(o)
        for v in vs:
            if v.z > 2.6:
                k = round(v.x * 5) / 5
                r = res["pier"].setdefault(k, [0, 0, 99])
                r[0] = max(r[0], round(v.y, 3)); r[1] = max(r[1], round(v.z, 3))
        res["pier_bbox"] = [[round(min(v[i] for v in vs), 3) for i in range(3)], [round(max(v[i] for v in vs), 3) for i in range(3)]]
        body = [v for v in vs if v.y > 27.3]
        res["pier_zs_near_north_end"] = sorted({round(v.z, 2) for v in body})[:40]
print("PROBE", json.dumps(res))
