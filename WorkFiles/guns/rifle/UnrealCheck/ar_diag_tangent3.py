import bpy, json, sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ar_common as C
out = {}
for fn in ("SM_AR01.fbx", "SM_AR01_Mag.fbx", "SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    for ob in [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("UCX_")]:
        me = ob.data
        s = ob.matrix_world.to_scale()[0] * 1000
        me.calc_tangents(uvmap=me.uv_layers[0].name)
        V = np.array([v.co for v in me.vertices]) * s
        UV = np.array([d.uv for d in me.uv_layers[0].data])
        T = np.array([l.tangent for l in me.loops])
        N = np.array([l.normal for l in me.loops])
        bad = set(np.where(np.linalg.norm(T, axis=1) < 1e-4)[0].tolist())
        lp = {}
        for p in me.polygons:
            for li in p.loop_indices:
                lp[li] = p
        cats = {"short_edge_lt_0.02mm": 0, "uv_squash_lt_5pct": 0, "other": 0}
        ex = []
        for li in bad:
            v = me.loops[li].vertex_index
            # faces sharing vertex AND uv coordinate (same tangent group candidate)
            faces = [p for p in me.polygons if v in p.vertices]
            minE = 1e9; minR = 1e9
            for p in faces:
                lis = list(p.loop_indices)
                P = V[[me.loops[i].vertex_index for i in lis]]; U = UV[lis]
                e3 = [np.linalg.norm(P[(k+1)%3]-P[k]) for k in range(3)]
                minE = min(minE, min(e3))
                a3 = 0.5*np.linalg.norm(np.cross(P[1]-P[0], P[2]-P[0])); au = 0.5*abs((U[1][0]-U[0][0])*(U[2][1]-U[0][1])-(U[2][0]-U[0][0])*(U[1][1]-U[0][1]))
                minR = min(minR, au / max(a3, 1e-12))
            if minE < 0.02: cats["short_edge_lt_0.02mm"] += 1
            else: cats["other"] += 1
            if len(ex) < 6 and minE >= 0.02:
                ex.append({"pos": np.round(V[v], 2).tolist(), "n": np.round(N[li], 3).tolist(), "min_edge": round(float(minE), 4),
                           "faces": [{"uv": np.round(UV[list(p.loop_indices)], 5).tolist(), "p": np.round(V[list(p.vertices)], 2).tolist()} for p in faces][:6]})
        out[f"{fn}:{ob.name}"] = {"bad": len(bad), **cats, "examples_other": ex}
(HERE / "ar_diag_tangent3.json").write_text(json.dumps(out, indent=1, default=float))
