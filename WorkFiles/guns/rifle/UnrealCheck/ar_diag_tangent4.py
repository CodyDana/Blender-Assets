import bpy, json, sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
import ar_common as C
from gunlib import tspace as TS
bpy.ops.import_scene.fbx(filepath=str(C.EXP / "SM_AR01_Mag.fbx"))
for name in ("SM_AR01_Mag_LOD2", "SM_AR01_Mag_LOD0"):
    ob = bpy.data.objects[name]; me = ob.data
    bad = TS.collapsed(me, "UV0")
    T, B = TS.frames(me, "UV0")
    s = ob.matrix_world.to_scale()[0] * 1000
    lp = {}
    for p in me.polygons:
        for li in p.loop_indices: lp[li] = p
    for li in bad[:3]:
        p = lp[int(li)]
        v = me.loops[li].vertex_index
        print("BAD", name, li, "T", T[li].round(4), "B", B[li].round(4), "n", np.round(me.corner_normals[li].vector, 4), "uv", np.round(me.uv_layers[0].data[li].uv, 6))
        # all corners at this vertex
        for q in me.polygons:
            if v in q.vertices:
                for lj in q.loop_indices:
                    if me.loops[lj].vertex_index == v:
                        P = np.array([me.vertices[me.loops[k].vertex_index].co for k in q.loop_indices]) * s
                        U = np.array([me.uv_layers[0].data[k].uv for k in q.loop_indices])
                        print("   face", q.index, "corner", lj, "uv", np.round(U, 6).tolist(), "P", np.round(P, 3).tolist(),
                              "fn", np.round(q.normal, 3).tolist(), "cn", np.round(me.corner_normals[lj].vector, 3).tolist(), "T", T[lj].round(3).tolist())
