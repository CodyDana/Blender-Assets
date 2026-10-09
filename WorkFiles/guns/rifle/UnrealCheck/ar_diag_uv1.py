import bpy, sys, numpy as np, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
res = {}
for f, lods in (("ue_SM_AR01.fbx", ("SM_AR01_LOD0", "SM_AR01_LOD1")), ("ue_SM_AR01_Mag.fbx", ("SM_AR01_Mag_LOD1",))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(HERE / "roundtrip" / f))
    for name in lods:
        ob = bpy.data.objects[name]; me = ob.data; me.calc_loop_triangles()
        lay = me.uv_layers["LightMapUV"]; UV0 = me.uv_layers[0]
        U = np.array([d.uv for d in lay.data]); U0 = np.array([d.uv for d in UV0.data])
        LT = np.array([t.loops[:] for t in me.loop_triangles]); VT = np.array([t.vertices[:] for t in me.loop_triangles])
        V = np.array([v.co for v in me.vertices]) * ob.matrix_world.to_scale()[0] * 1000
        R = 1024
        owner = {}
        hits = []
        for ti, (a, b, c) in enumerate(U[LT]):
            mn = np.floor(np.minimum(np.minimum(a, b), c) * R).astype(int); mx = np.ceil(np.maximum(np.maximum(a, b), c) * R).astype(int)
            for y in range(max(mn[1], 0), min(mx[1], R)):
                for x in range(max(mn[0], 0), min(mx[0], R)):
                    px, py = (x + .5) / R, (y + .5) / R
                    w0 = (b[0]-px)*(c[1]-py)-(c[0]-px)*(b[1]-py); w1=(c[0]-px)*(a[1]-py)-(a[0]-px)*(c[1]-py); w2=(a[0]-px)*(b[1]-py)-(b[0]-px)*(a[1]-py)
                    if (w0>0 and w1>0 and w2>0) or (w0<0 and w1<0 and w2<0):
                        if (x, y) in owner:
                            hits.append((owner[(x, y)], ti))
                        else:
                            owner[(x, y)] = ti
        pairs = sorted(set(tuple(sorted(h)) for h in hits))
        def info(t):
            P = V[VT[t]]; a3 = 0.5*np.linalg.norm(np.cross(P[1]-P[0], P[2]-P[0]))
            u = U[LT[t]]; au = 0.5*abs((u[1][0]-u[0][0])*(u[2][1]-u[0][1])-(u[2][0]-u[0][0])*(u[1][1]-u[0][1]))
            u0 = U0[LT[t]]; au0 = 0.5*((u0[1][0]-u0[0][0])*(u0[2][1]-u0[0][1])-(u0[2][0]-u0[0][0])*(u0[1][1]-u0[0][1]))
            return {"a3_mm2": round(float(a3), 4), "uv1_area_px2": round(float(au*R*R), 3), "uv0_signed_area": float(au0), "c": np.round(P.mean(0), 1).tolist()}
        res[name] = {"overlap_pairs": len(pairs), "examples": [[info(a), info(b)] for a, b in pairs[:6]]}
(HERE / "ar_diag_uv1.json").write_text(json.dumps(res, indent=1))
