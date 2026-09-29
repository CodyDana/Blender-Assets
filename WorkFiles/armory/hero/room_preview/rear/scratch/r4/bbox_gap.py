import bpy
from mathutils import Vector


def wb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


objs = [o for o in bpy.data.objects if o.type in ("MESH", "EMPTY") and "__" in o.name]
want = ("SM_AK_Lantern", "SM_AK_StairNewel", "SM_AK_Post_Heavy", "SM_AK_Steps_22", "SM_AK_Platform_Side",
        "SM_AK_Case_Tall", "SM_AK_H_CornerShowcase", "SM_AK_RearAlcove", "SM_AK_SillLedge", "SM_AK_Case_Hero",
        "SM_AK_Vase_Plum_L", "SM_AK_H_PaintingBase")
sel = []
for o in objs:
    if o.name.split("__")[0].startswith(want):
        if o.type == "EMPTY" and o.instance_collection:
            mn = [1e9] * 3
            mx = [-1e9] * 3
            for c in o.instance_collection.all_objects:
                if c.type != "MESH" or c.name.startswith("UCX_"):
                    continue
                pts = [o.matrix_world @ (c.matrix_world @ Vector(v)) for v in c.bound_box]
                for i in range(3):
                    mn[i] = min(mn[i], min(p[i] for p in pts))
                    mx[i] = max(mx[i], max(p[i] for p in pts))
            sel.append((o.name, mn, mx))
        elif o.type == "MESH":
            mn, mx = wb(o)
            sel.append((o.name, mn, mx))
print("N", len(sel))
for i, (a, amn, amx) in enumerate(sel):
    if not a.startswith(("SM_AK_Lantern", "SM_AK_H_CornerShowcase", "SM_AK_Case_Hero")):
        continue
    for b, bmn, bmx in sel:
        if b == a or b.startswith(a.split("__")[0] + "__") and False:
            continue
        gap = max(max(bmn[k] - amx[k], amn[k] - bmx[k]) for k in range(3))
        if gap < 0.08 and not (a.startswith("SM_AK_Lantern") and b.startswith("SM_AK_LanternPedestal") and abs(amn[0] - bmn[0]) < 0.05):
            print("GAP", a, b, round(gap, 4), [round(v, 3) for v in amn + amx])
