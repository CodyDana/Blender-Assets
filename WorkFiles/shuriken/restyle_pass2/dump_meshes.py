import bpy, sys, json, numpy as np
out = sys.argv[sys.argv.index("--") + 1]
info = {}
for obj in bpy.data.objects:
    if obj.type != "MESH" or not obj.name.startswith("SM_Shuriken_"):
        continue
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", tri)
    np.savez(f"{out}/{obj.name}.npz", co=co.reshape(-1, 3), tri=tri.reshape(-1, 3))
    info[obj.name] = {"verts": len(me.vertices), "tris": len(me.loop_triangles), "matrix_identity": obj.matrix_world.is_identity if hasattr(obj.matrix_world,'is_identity') else None}
print(json.dumps(info, indent=1))
