import bpy, sys, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
for fn in ("TV3_SM_AR01_LOD1", "TV3_SM_AR01_LOD2", "TV3_SM_AR01_LOD0"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(HERE / "tanexp" / f"{fn}.fbx"))
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]; me = ob.data
    s = ob.matrix_world.to_scale()[0] * 1000
    V = np.array([v.co for v in me.vertices]) * s
    T = np.array([p.vertices[:] for p in me.polygons])
    L = np.stack([np.linalg.norm(V[T[:, (k + 1) % 3]] - V[T[:, k]], axis=1) for k in range(3)], 1)
    UV = np.array([d.uv for d in me.uv_layers[0].data]); LT = np.array([p.loop_indices[:] for p in me.polygons])
    ua = 0.5 * np.abs((UV[LT[:,1],0]-UV[LT[:,0],0])*(UV[LT[:,2],1]-UV[LT[:,0],1])-(UV[LT[:,2],0]-UV[LT[:,0],0])*(UV[LT[:,1],1]-UV[LT[:,0],1]))
    # duplicate positions
    uq, cnt = np.unique(np.round(V, 6), axis=0, return_counts=True)
    print("D7", fn, "tris", len(T), "minedge", L.min(), "edges<1e-3mm", int((L < 1e-3).sum()), "<1e-5", int((L < 1e-5).sum()),
          "dup_positions", int((cnt > 1).sum()), "uv_area0", int((ua < 1e-14).sum()), "uv_area<1e-12", int((ua < 1e-12).sum()))
