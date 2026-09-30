import bpy
from mathutils import kdtree
o = bpy.data.objects.get("SM_DKX_FarTown")
me = o.data
kd = kdtree.KDTree(len(me.vertices))
for v in me.vertices:
    kd.insert(v.co, v.index)
kd.balance()
pairs = []
for v in me.vertices:
    for co, i, d in kd.find_range(v.co, 1e-6):
        if i > v.index:
            pairs.append((v.index, i, tuple(round(c, 3) for c in v.co)))
print("PAIRS", len(pairs), pairs[:10])
# faces using them
vs = {p[0] for p in pairs} | {p[1] for p in pairs}
fs = [(pl.index, len(pl.vertices), [me.materials[pl.material_index].name]) for pl in me.polygons if set(pl.vertices) & vs]
print("FACES", fs[:20])
