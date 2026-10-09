import bpy, sys, json, math, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
from gunlib import tspace as TS
d = json.loads((HERE / "ar_fbxa_ntb.json").read_text())
for name in sys.argv[sys.argv.index("--") + 1:]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(HERE / "tanexp" / f"{name}.fbx"))
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]; me = ob.data
    s = ob.matrix_world.to_scale()[0] * 1000
    UV, LV, V, CN = TS._arrays(me, "UV0")
    T, B = TS.frames(me, "UV0")
    Vm = V * s
    for pc in d["ue_" + name]["zero_pos_cm"][:4]:
        p = np.array(pc) * 10
        cands = [np.array([p[0], p[1], p[2]]), np.array([p[0], -p[1], p[2]])]
        dist = [np.linalg.norm(Vm - c, axis=1) for c in cands]
        k = int(np.argmin([x.min() for x in dist])); vi = int(np.argmin(dist[k]))
        print("Z9", name, "ue", pc, "-> v", vi, round(float(dist[k][vi]), 4), "mm")
        for q in me.polygons:
            if vi in q.vertices:
                L = list(q.loop_indices)
                lj = [j for j in L if LV[j] == vi][0]
                P = Vm[[LV[j] for j in L]]
                i = L.index(lj)
                e1 = P[(i + 1) % 3] - P[i]; e2 = P[(i + 2) % 3] - P[i]
                n = CN[lj]
                e1p = e1 - n * (e1 @ n); e2p = e2 - n * (e2 @ n)
                ang = math.degrees(math.atan2(np.linalg.norm(np.cross(e1p, e2p)), e1p @ e2p))
                ua = 0.5 * ((UV[L[1]][0]-UV[L[0]][0])*(UV[L[2]][1]-UV[L[0]][1])-(UV[L[2]][0]-UV[L[0]][0])*(UV[L[1]][1]-UV[L[0]][1]))
                print("   f", q.index, "P", np.round(P, 3).tolist(), "uv", np.round(UV[L], 7).tolist(), "uvA", ua,
                      "cn", np.round(n, 3).tolist(), "fn", np.round(q.normal, 3).tolist(), "projang", round(ang, 4), "T", np.round(T[lj], 3).tolist())
