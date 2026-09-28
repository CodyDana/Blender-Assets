"""Close-out: vertices outside the single hull, per LOD and material (read-only on the blend)."""
import bpy, numpy as np, json
h = bpy.data.objects["UCX_SM_BlackHat_LOD0_00"]
mw = np.array(h.matrix_world)
HV = np.array([(h.matrix_world @ v.co)[:] for v in h.data.vertices]) * 1000
planes = []
for p in h.data.polygons:
    n = np.array((h.matrix_world.to_3x3() @ p.normal).normalized()[:]); c = np.array((h.matrix_world @ p.center)[:]) * 1000
    planes.append((n, float(n @ c)))
floor = HV[:, 2].min()
res = {"hull_vertices": len(HV), "floor_z_mm": round(float(floor), 3)}
for name in ("SM_BlackHat_LOD0", "SM_BlackHat_LOD1", "SM_BlackHat_LOD2"):
    o = bpy.data.objects[name]; me = o.data
    P = np.array([(o.matrix_world @ v.co)[:] for v in me.vertices]) * 1000
    mat = np.zeros(len(P), int)
    for p in me.polygons:
        for vi in p.vertices: mat[vi] = max(mat[vi], p.material_index)
    d = np.max(np.stack([P @ n - off for n, off in planes], 1), 1)
    out = d > 0
    above = out & (P[:, 2] > floor)
    res[name] = {"outside": int(out.sum()), "outside_straw": int((out & (mat == 0)).sum()),
                 "outside_cloth_above_floor": int((above & (mat == 1)).sum()),
                 "worst_above_floor_mm": round(float(d[above].max()), 2) if above.any() else 0.0,
                 "straw_min_inside_mm": round(float(-d[mat == 0].max()), 3)}
print("HULL " + json.dumps(res))
