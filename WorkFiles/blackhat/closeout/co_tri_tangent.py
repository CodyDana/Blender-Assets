"""Diagnostic: per-corner triangle tangent (dP/du, dP/dv from UV0) projected off the corner normal; smallest ones, LOD0 cloth."""
import bpy, numpy as np, json
ob = bpy.data.objects["SM_BlackHat_LOD0"]; me = ob.data
me.calc_loop_triangles()
uv = np.zeros(len(me.loops) * 2); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
ln = np.zeros(len(me.loops) * 3); me.loops.foreach_get("normal", ln); ln = ln.reshape(-1, 3)
co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) * 1000
rows = []
for t in me.loop_triangles:
    if t.material_index != 1: continue
    L = list(t.loops); V = list(t.vertices)
    P = co[V]; U = uv[L]
    e1, e2 = P[1] - P[0], P[2] - P[0]; d1, d2 = U[1] - U[0], U[2] - U[0]
    det = d1[0] * d2[1] - d1[1] * d2[0]
    area = 0.5 * np.linalg.norm(np.cross(e1, e2))
    if abs(det) < 1e-14:
        rows.append((0.0, "uvdet0", P.mean(0).tolist(), area)); continue
    Tu = (e1 * d2[1] - e2 * d1[1]) / det; Tv = (e2 * d1[0] - e1 * d2[0]) / det
    for k in range(3):
        n = ln[L[k]]
        for nm, T in (("t", Tu), ("b", Tv)):
            Tp = T - (T @ n) * n
            rel = np.linalg.norm(Tp) / max(np.linalg.norm(T), 1e-12)
            rows.append((float(rel), nm, P.mean(0).tolist(), float(area), float(np.linalg.norm(n))))
rows.sort(key=lambda r: r[0])
print("TT " + json.dumps([[round(r[0], 5), r[1], [round(v, 1) for v in r[2]], round(r[3], 4)] + ([round(r[4], 3)] if len(r) > 4 else []) for r in rows[:15]]))
