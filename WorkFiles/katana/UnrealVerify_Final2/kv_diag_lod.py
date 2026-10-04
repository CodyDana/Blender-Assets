"""Diagnostic (not a gate): LOD-to-LOD0 surface deviation of both meshes on the Unreal read-back, plus where the
katana LOD1 vertices outside the LOD0 hulls sit relative to LOD0."""
import json, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Final2")
import kv_common as C
geo = json.loads((C.HERE / "kvB_geometry.json").read_text())
out = {}
for name in C.MESHES:
    P0 = np.array(geo[name][0]["positions"]); T0 = np.array(geo[name][0]["triangles"])[:, -3:]
    t0 = BVHTree.FromPolygons([tuple(p) for p in P0], [tuple(t) for t in T0], all_triangles=True)
    for li in (1, 2):
        P = np.array(geo[name][li]["positions"])
        d = np.array([t0.find_nearest(Vector(p))[3] for p in P])
        w = np.argsort(-d)[:5]
        out[f"{name}_LOD{li}_to_LOD0"] = {"max_mm": float(d.max() * 10), "p99_mm": float(np.percentile(d, 99) * 10),
                                          "mean_mm": float(d.mean() * 10),
                                          "worst_unreal_cm": [[*P[i].round(3).tolist(), round(float(d[i] * 10), 3)] for i in w]}
        # also LOD0 -> LODi (what disappears)
        T = np.array(geo[name][li]["triangles"])[:, -3:]
        tl = BVHTree.FromPolygons([tuple(p) for p in P], [tuple(t) for t in T], all_triangles=True)
        d2 = np.array([tl.find_nearest(Vector(p))[3] for p in P0])
        w2 = np.argsort(-d2)[:5]
        out[f"{name}_LOD0_to_LOD{li}"] = {"max_mm": float(d2.max() * 10), "p99_mm": float(np.percentile(d2, 99) * 10),
                                          "worst_unreal_cm": [[*P0[i].round(3).tolist(), round(float(d2[i] * 10), 3)] for i in w2]}
(C.HERE / "kv_diag_lod.json").write_text(json.dumps(out, indent=1))
print("LODDIAG", json.dumps(out))
