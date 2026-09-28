"""Close-out: find loops with near-zero MikkTSpace tangents / bitangents (UE FBXImport tolerance 1e-4) per LOD and part."""
import bpy, numpy as np, json, sys
res = {}
for ob in bpy.data.objects:
    if ob.type != 'MESH' or not ob.name.startswith("SM_BlackHat_LOD"):
        continue
    me = ob.data
    me.calc_tangents(uvmap=me.uv_layers[0].name)
    n = len(me.loops)
    T = np.zeros(n * 3); me.loops.foreach_get("tangent", T); T = T.reshape(-1, 3)
    Bs = np.zeros(n); me.loops.foreach_get("bitangent_sign", Bs)
    N = np.zeros(n * 3); me.loops.foreach_get("normal", N); N = N.reshape(-1, 3)
    B = np.cross(N, T) * Bs[:, None]
    bad = (np.linalg.norm(T, axis=1) < 1e-4) | (np.linalg.norm(B, axis=1) < 1e-4)
    # also tangent nearly parallel to normal (degenerate after orthonormalisation)
    par = np.abs((T * N).sum(1)) > 0.9999
    lp = np.zeros(n, int)
    for p in me.polygons:
        lp[p.loop_start:p.loop_start + p.loop_total] = p.index
    mats = [me.materials[p.material_index].name if me.materials else "" for p in me.polygons]
    bi = np.where(bad | par)[0]
    polys = sorted(set(lp[bi].tolist()))
    info = []
    for pi in polys[:12]:
        p = me.polygons[pi]
        c = np.array(p.center)
        info.append({"poly": pi, "mat": mats[pi], "center": [round(v, 4) for v in c], "r_mm": round(float(np.hypot(c[0], c[1])) * (1000 if ob.dimensions.x < 5 else 1), 2),
                     "area": p.area})
    res[ob.name] = {"loops": n, "bad_loops": int(bad.sum()), "parallel_loops": int(par.sum()), "polys": len(polys), "examples": info}
print("TANG " + json.dumps(res))
