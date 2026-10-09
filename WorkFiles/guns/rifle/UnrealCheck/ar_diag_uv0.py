import bpy, sys, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
sys.path.insert(0, str(HERE)); import ar_common as C
from gunlib import lodfix
for fn in ("SM_AR01.fbx", "SM_AR01_Mag.fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(C.EXP / fn))
    for ob in sorted([o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("UCX")], key=lambda o: o.name):
        me = ob.data; me.calc_loop_triangles()
        for ln in [l.name for l in me.uv_layers]:
            U = np.array([d.uv for d in me.uv_layers[ln].data]); LT = np.array([t.loops[:] for t in me.loop_triangles])
            pr = lodfix.overlap_pairs(U[LT])
            print("UV0OV", fn, ob.name, ln, len(pr))
