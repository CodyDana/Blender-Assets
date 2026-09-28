"""Dump every mesh object of the open blend to <out>/<name>.npz (read-only; never saves)."""
import bpy, sys, json
import numpy as np
out = sys.argv[sys.argv.index("--") + 1]
info = {}
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    me = obj.data
    me.calc_loop_triangles()
    V, L, P, E = len(me.vertices), len(me.loops), len(me.polygons), len(me.edges)
    co = np.empty(V * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
    ls = np.empty(P, dtype=np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(P, dtype=np.int64); me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(L, dtype=np.int64); me.loops.foreach_get("vertex_index", lv)
    ed = np.empty(E * 2, dtype=np.int64); me.edges.foreach_get("vertices", ed)
    T = len(me.loop_triangles)
    tri = np.empty(T * 3, dtype=np.int64); me.loop_triangles.foreach_get("vertices", tri)
    tril = np.empty(T * 3, dtype=np.int64); me.loop_triangles.foreach_get("loops", tril)
    trip = np.empty(T, dtype=np.int64); me.loop_triangles.foreach_get("polygon_index", trip)
    d = dict(co=co.reshape(-1, 3).astype(np.float64), loop_start=ls, loop_total=lt, loop_vert=lv,
             edges=ed.reshape(-1, 2), tri=tri.reshape(-1, 3), tri_loops=tril.reshape(-1, 3), tri_poly=trip,
             matrix_world=np.array(obj.matrix_world, dtype=np.float64))
    if me.uv_layers:
        uv = np.empty(L * 2, dtype=np.float32); me.uv_layers[0].data.foreach_get("uv", uv)
        d["uv"] = uv.reshape(-1, 2).astype(np.float64)
    try:
        cn = np.empty(L * 3, dtype=np.float32); me.corner_normals.foreach_get("vector", cn)
        d["corner_normals"] = cn.reshape(-1, 3).astype(np.float64)
    except Exception as exc:
        print("corner_normals failed", obj.name, exc)
    pn = np.empty(P * 3, dtype=np.float32); me.polygons.foreach_get("normal", pn)
    d["poly_normals"] = pn.reshape(-1, 3).astype(np.float64)
    for a in me.attributes:
        if a.name in ("sharp_edge", "sharp_face") and a.domain in ("EDGE", "FACE"):
            n = E if a.domain == "EDGE" else P
            arr = np.zeros(n, dtype=bool); a.data.foreach_get("value", arr); d[a.name] = arr
        elif a.name.startswith("shuriken_") and a.domain == "POINT" and a.data_type == "FLOAT":
            arr = np.empty(V, dtype=np.float32); a.data.foreach_get("value", arr); d[a.name] = arr.astype(np.float64)
    np.savez(f"{out}/{obj.name}.npz", **d)
    info[obj.name] = {"verts": V, "polys": P, "tris": T, "parent": obj.parent.name if obj.parent else None}
print("DUMP", json.dumps(info))
