import bpy, json, sys, math
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
import ar_common as C
from gunlib import tspace as TS
out = {}
for fn in ("SM_AR01.fbx", "SM_AR01_Mag.fbx", "SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    for ob in [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("UCX_")]:
        me = ob.data
        s = ob.matrix_world.to_scale()[0] * 1000
        bad = TS.collapsed(me, me.uv_layers[0].name)
        lp = {}
        for p in me.polygons:
            for li in p.loop_indices: lp[li] = p
        rows = []
        for li in bad:
            p = lp[int(li)]
            L = list(p.loop_indices); k = L.index(int(li))
            P = np.array([me.vertices[me.loops[j].vertex_index].co for j in L]) * s
            a, b, c = P[k], P[(k + 1) % 3], P[(k + 2) % 3]
            def ang(o, x, y):
                u, v = x - o, y - o
                return math.degrees(math.atan2(np.linalg.norm(np.cross(u, v)), u @ v))
            angs = [ang(P[i], P[(i + 1) % 3], P[(i + 2) % 3]) for i in range(3)]
            cn = np.array(me.corner_normals[int(li)].vector)
            fnrm = np.array(p.normal)
            e = [np.linalg.norm(P[(i + 1) % 3] - P[i]) for i in range(3)]
            rows.append({"corner_angle": round(angs[k], 5), "min_angle": round(min(angs), 5), "min_edge": round(min(e), 4),
                         "max_edge": round(max(e), 3), "fn_vs_cn_deg": round(math.degrees(math.acos(max(-1, min(1, float(fnrm @ cn))))), 2)})
        a = np.array([[r["corner_angle"], r["min_edge"], r["fn_vs_cn_deg"]] for r in rows]) if rows else np.zeros((0, 3))
        out[f"{fn}:{ob.name}"] = {"bad": len(rows),
            "corner_angle_lt_0.1deg": int((a[:, 0] < 0.1).sum()) if len(a) else 0,
            "corner_angle_lt_1deg": int((a[:, 0] < 1).sum()) if len(a) else 0,
            "min_edge_lt_0.02": int((a[:, 1] < 0.02).sum()) if len(a) else 0,
            "fn_cn_gt_60": int((a[:, 2] > 60).sum()) if len(a) else 0,
            "rows": rows[:8]}
(HERE / "ar_diag_tangent5.json").write_text(json.dumps(out, indent=1, default=float))
