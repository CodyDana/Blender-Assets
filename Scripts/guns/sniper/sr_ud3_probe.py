"""SR01 debug aid (W3 Part 0, UD3 / UD2): on the opened blend, print where every float32 zero-tangent corner (UV0) and
every UD2 micro edge / needle sits (frame M mm), with the corner's faces and angles. Usage:
blender -b --factory-startup Assets/Guns/SR01.blend --python sr_ud3_probe.py [-- --parts barrel,chassis]"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
import bpy  # noqa: E402
from sr_common import GRIP, PARTS_COLL, SCRATCH  # noqa: E402
from gunlib import tspace as TS, bl  # noqa: E402
from gunlib.ud import _tri_metrics, MIN_EDGE_MM, MIN_HEIGHT_MM  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = argv[argv.index("--parts") + 1].split(",") if "--parts" in argv else None
out = {}
for ob in bpy.data.collections[PARTS_COLL].objects:
    if ob.type != "MESH" or (only and ob.name not in only):
        continue
    me = ob.data
    rec = {}
    if me.uv_layers:
        uvn = "UV0" if "UV0" in me.uv_layers else me.uv_layers[0].name
        z = TS.float32_zero_corners(me, uvn)
        mw = np.array(ob.matrix_world)
        cs = []
        for li in z:
            lp = me.loops[int(li)]
            v = me.vertices[lp.vertex_index]
            p = (mw @ np.r_[np.array(v.co), 1.0])[:3] * 1000.0 + GRIP
            faces = [f for f in me.polygons if lp.vertex_index in f.vertices]
            fa = []
            for f in faces:
                vs = list(f.vertices)
                k = vs.index(lp.vertex_index)
                a = np.array(me.vertices[vs[(k + 1) % len(vs)]].co) - np.array(v.co)
                b = np.array(me.vertices[vs[k - 1]].co) - np.array(v.co)
                ang = np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b)), a @ b))
                el = [round(float(np.linalg.norm(np.array(me.vertices[vs[(j + 1) % len(vs)]].co) - np.array(me.vertices[vs[j]].co))) * 1000, 3) for j in range(len(vs))]
                fa.append({"f": f.index, "ang": round(float(ang), 4), "n": [round(x, 3) for x in f.normal], "edges_mm": el})
            cs.append({"loop": int(li), "v": lp.vertex_index, "M": np.round(p, 3).tolist(), "faces": fa})
        rec["zero_corners"] = cs
    V, T = bl.tris_np(ob)
    area, L, height, drop, corner = _tri_metrics(V, T)
    E = np.sort(np.c_[T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]].reshape(-1, 2), axis=1)
    E = np.unique(E, axis=0)
    el = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    short = np.nonzero(el < MIN_EDGE_MM)[0]
    rec["short_edges"] = [[np.round(V[E[i]].mean(0) - GRIP, 3).tolist(), round(float(el[i]), 4)] for i in short]
    nd = np.nonzero(height < MIN_HEIGHT_MM)[0]
    rec["needles"] = [[np.round(V[T[i]] - GRIP, 3).tolist(), round(float(height[i]), 4)] for i in nd]
    if rec.get("zero_corners") or rec["short_edges"] or rec["needles"]:
        out[ob.name] = rec
        print("UD3PROBE", ob.name, json.dumps(rec)[:3000])
(SCRATCH.parent / "w3").mkdir(exist_ok=True)
(SCRATCH.parent / "w3" / "ud3_probe.json").write_text(json.dumps(out, indent=1))
print("UD3PROBE_DONE", len(out))
