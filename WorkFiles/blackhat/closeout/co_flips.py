"""Close-out: faces whose geometric normal disagrees with their corner normals, and tiny-UV faces, per LOD / material / region."""
import bpy, numpy as np, json
res = {}
for ob in sorted([o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("SM_BlackHat_LOD")], key=lambda o: o.name):
    me = ob.data
    uv = me.uv_layers[0].data
    ln = np.zeros(len(me.loops) * 3); me.loops.foreach_get("normal", ln); ln = ln.reshape(-1, 3)
    out = []
    for p in me.polygons:
        ls = range(p.loop_start, p.loop_start + p.loop_total)
        dn = min(float(np.dot(p.normal, ln[i])) for i in ls)
        U = np.array([uv[i].uv[:] for i in ls])
        a = 0.0
        for k in range(1, len(U) - 1):
            e1, e2 = U[k] - U[0], U[k + 1] - U[0]; a += 0.5 * (e1[0] * e2[1] - e1[1] * e2[0])
        if dn < 0.0 or abs(a) < 1e-9:
            c = np.array(p.center) * 1000.0
            out.append({"mat": me.materials[p.material_index].name, "dot": round(float(dn), 3), "uv_area": float(a), "c_mm": [round(v, 1) for v in c],
                        "r": round(float(np.hypot(c[0], c[1])), 1)})
    res[ob.name] = {"count": len(out), "by_mat": {m: sum(1 for o in out if o["mat"] == m) for m in set(o["mat"] for o in out)}, "ex": out[:8]}
print("FLIPS " + json.dumps(res, default=float))
