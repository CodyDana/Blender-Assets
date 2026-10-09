import bpy, json, sys, math
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[3] / "Scripts" / "guns"))
import ar_common as C
from gunlib import tspace as TS
bpy.ops.import_scene.fbx(filepath=str(C.EXP / "SM_AR01.fbx"))
ob = bpy.data.objects["SM_AR01_LOD3"]; me = ob.data
T, B = TS.frames(me, "UV0")
bad = TS.collapsed(me, "UV0")
s = ob.matrix_world.to_scale()[0] * 1000
lp = {}
for p in me.polygons:
    for li in p.loop_indices: lp[li] = p
for li in bad[:4]:
    p = lp[int(li)]; v = me.loops[li].vertex_index
    print("BAD", li, "T", T[li].round(3), "B", B[li].round(3), "cn", np.round(me.corner_normals[li].vector, 3), "uv", np.round(me.uv_layers[0].data[li].uv, 6))
    for q in me.polygons:
        if v in q.vertices:
            P = np.array([me.vertices[me.loops[k].vertex_index].co for k in q.loop_indices]) * s
            U = np.array([me.uv_layers[0].data[k].uv for k in q.loop_indices])
            lj = [k for k in q.loop_indices if me.loops[k].vertex_index == v][0]
            print("   f", q.index, "uv", np.round(U, 5).tolist(), "P", np.round(P, 2).tolist(), "fn", np.round(q.normal, 3).tolist(),
                  "cn", np.round(me.corner_normals[lj].vector, 3).tolist(), "T", T[lj].round(3).tolist(), "B", B[lj].round(3).tolist())
