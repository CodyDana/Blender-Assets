import bpy, json, sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ar_common as C
out = {}
bpy.ops.import_scene.fbx(filepath=str(C.EXP / "SM_AR01.fbx"))
for lodname in ("SM_AR01_LOD0", "SM_AR01_LOD1"):
    ob = bpy.data.objects[lodname]
    me = ob.data
    s = ob.matrix_world.to_scale()[0] * 1000
    me.calc_tangents(uvmap="UV0")
    V = np.array([v.co for v in me.vertices]) * s
    UV = np.array([d.uv for d in me.uv_layers["UV0"].data])
    T = np.array([l.tangent for l in me.loops])
    bad = np.where(np.linalg.norm(T, axis=1) < 1e-4)[0]
    badv = {me.loops[i].vertex_index for i in bad}
    recs = []
    dens = []
    for p in me.polygons:
        li = list(range(p.loop_start, p.loop_start + p.loop_total))
        P = V[[me.loops[i].vertex_index for i in li]]
        U = UV[li]
        a3 = 0.0; au = 0.0
        for k in range(1, len(li) - 1):
            a3 += 0.5 * np.linalg.norm(np.cross(P[k] - P[0], P[k + 1] - P[0]))
            au += 0.5 * abs((U[k][0] - U[0][0]) * (U[k + 1][1] - U[0][1]) - (U[k + 1][0] - U[0][0]) * (U[k][1] - U[0][1]))
        res = 4096 if me.materials[p.material_index].name.endswith("Metal") else (2048 if "Furniture" in me.materials[p.material_index].name else 1024)
        d = au * res * res / max(a3, 1e-12)
        dens.append(d)
        if any(me.loops[i].vertex_index in badv for i in li):
            # edge lengths in 3D and in UV px
            e3 = [float(np.linalg.norm(P[(k + 1) % len(li)] - P[k])) for k in range(len(li))]
            eu = [float(np.linalg.norm((U[(k + 1) % len(li)] - U[k]) * res)) for k in range(len(li))]
            recs.append({"poly": p.index, "n": len(li), "mat": me.materials[p.material_index].name, "area_mm2": round(a3, 5),
                         "uv_area_px2": round(au * res * res, 6), "density_px2_per_mm2": round(d, 3),
                         "edges_mm": [round(x, 4) for x in e3], "edges_px": [round(x, 4) for x in eu],
                         "smooth": p.use_smooth, "c": np.round(P.mean(0), 2).tolist()})
    dens = np.array(dens)
    out[lodname] = {"bad_loops": len(bad), "bad_verts": len(badv), "polys": len(me.polygons),
                    "density_median": float(np.median(dens)),
                    "density_lt_1pct_median": int((dens < 0.01 * np.median(dens)).sum()),
                    "density_lt_1e-3": int((dens < 1e-3).sum()),
                    "adjacent_polys": recs[:60]}
(HERE / "ar_diag_tangent2.json").write_text(json.dumps(out, indent=1, default=float))
