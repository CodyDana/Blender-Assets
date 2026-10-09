import bpy, sys, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); import ar_common as C
for fn in ("SM_AR01.fbx", "SM_AR01_Mag.fbx", "SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    for ob in sorted([o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("UCX")], key=lambda o: o.name):
        me = ob.data
        M = np.array(ob.matrix_world)
        V = np.array([v.co for v in me.vertices]); V = (V @ M[:3, :3].T + M[:3, 3]) * 1000.0
        T = np.array([p.vertices[:] for p in me.polygons])
        Vc = (V / 10.0).astype(np.float32)
        cr = np.cross(Vc[T[:, 1]] - Vc[T[:, 2]], Vc[T[:, 0]] - Vc[T[:, 2]])
        out = [int(((cr.astype(np.float64) ** 2).sum(1) < 1e-8).sum())]
        print("DG", fn, ob.name, len(T), out)
