import bpy, sys, math, json
import numpy as np
root = sys.argv[sys.argv.index("--") + 1]
out = {}
for form in ("FourPoint", "EightPoint", "SquarePlate"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f"{root}/fbx/SM_Shuriken_{form}.fbx")
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        me = obj.data
        me.calc_loop_triangles()
        mw = np.array(obj.matrix_world)
        co = np.array([(obj.matrix_world @ v.co)[:] for v in me.vertices])
        tri = np.array([t.vertices[:] for t in me.loop_triangles])
        A, B, C = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
        det = np.einsum("ij,ij->i", A, np.cross(B, C))
        vol = det.sum() / 6
        cen = (det[:, None] * (A + B + C)).sum(0) / 24 / vol
        sizes = [len(p.vertices) for p in me.polygons]
        # z-mirror check of the triangle set
        key = lambda P: tuple(sorted(tuple(np.round(p / 1e-7).astype(np.int64)) for p in P))
        tris = set(key(co[t]) for t in tri)
        miss = sum(1 for t in tri if key(co[t] * np.array([1, 1, -1])) not in tris)
        # triangles vs the blend's loop triangulation
        name = obj.name
        try:
            d = np.load(f"{root}/p2/{name}.npz")
            bco, btri = d["co"], d["tri"]
            btris = set(key(bco[t]) for t in btri)
            diff = sum(1 for t in tri if key(co[t]) not in btris)
        except Exception as exc:
            diff = f"n/a {exc}"
        out[name] = {"polys": len(sizes), "max_poly_size": max(sizes), "tris": len(tri), "verts": len(co),
                     "volume_mm3": vol * 1e9, "mass_g": vol * 1e6 * 7.85, "centroid_mm": [x * 1e3 for x in cen],
                     "extent_mm": [float(x) * 1e3 for x in np.ptp(co, axis=0)],
                     "z_mirror_triangle_misses": miss, "triangles_not_in_blend_triangulation": diff,
                     "matrix_world_scale": [round(float(np.linalg.norm(mw[:3, i])), 6) for i in range(3)]}
print("FBXCHECK " + json.dumps(out))
