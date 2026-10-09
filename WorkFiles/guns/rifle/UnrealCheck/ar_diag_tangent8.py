import bpy, sys, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
from gunlib import tspace as TS
for fn in ("TV7_SM_AR01_LOD1", "TV7_SM_AR01_LOD2"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(HERE / "tanexp" / f"{fn}.fbx"))
    ob = [o for o in bpy.data.objects if o.type == "MESH"][0]; me = ob.data
    s = ob.matrix_world.to_scale()[0] * 1000
    UV, LV, V, CN = TS._arrays(me, "UV0")
    tex = np.where(UV[:, 0] < 0, 1 / 1024, np.where(UV[:, 0] < 1, 1 / 4096, 1 / 2048))
    tiny = TS.tiny_uv_faces(me, UV, tex)
    A3 = []
    for fi in tiny:
        p = me.polygons[fi]; P = V[list(p.vertices)] * s
        a3 = 0.5 * np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0]))
        A3.append(a3)
    A3 = np.array(A3)
    print("D8", fn, "tiny", len(tiny), "3d_area<1e-6mm2", int((A3 < 1e-6).sum()), "max3d", A3.max() if len(A3) else 0)
    for fi in tiny[:3]:
        p = me.polygons[fi]; L = list(p.loop_indices)
        print("   ", np.round(V[list(p.vertices)] * s, 4).tolist(), np.round(UV[L], 7).tolist())
    # all-face 3D degenerate check
    T = np.array([p.vertices[:] for p in me.polygons]); P = V * s
    a = 0.5 * np.linalg.norm(np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]]), axis=1)
    print("D8", fn, "faces 3d area < 1e-6 mm2:", int((a < 1e-6).sum()), "< 1e-4:", int((a < 1e-4).sum()))
