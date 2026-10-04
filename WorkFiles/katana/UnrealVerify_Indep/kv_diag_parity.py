"""Diagnostic (not a gate): list every ray hit along +Y from the enclosure-test failures, and the surface pieces hit."""
import json, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Indep")
import kv_common as C
geo = json.loads((C.HERE / "kvB_geometry.json").read_text())
P = np.array(geo["SM_Katana_Saya"][0]["positions"]); T = np.array(geo["SM_Katana_Saya"][0]["triangles"])[:, -3:]
tree = BVHTree.FromPolygons([tuple(p) for p in P], [tuple(t) for t in T], all_triangles=True, epsilon=0.0)
# edge-adjacency: count how many triangles share each edge (open edges = 1)
from collections import Counter
E = Counter()
for t in T:
    for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
        E[(min(a, b), max(a, b))] += 1
cnt = Counter(E.values())
print("EDGE_SHARE_COUNTS", dict(cnt))
openE = [e for e, c in E.items() if c == 1]
if openE:
    V = P[np.array(openE).ravel()]
    print("OPEN_EDGE_BBOX", V.min(0).round(3).tolist(), V.max(0).round(3).tolist())
# position-welded edge counts (Unreal splits vertices on UV seams? positions are unique vertex ids in MeshDescription)
for p in ([0.2611, 0.286, -0.8458], [-0.271, 0.2153, -0.2818]):
    for d in ((0, 1, 0), (0.05, 1, 0.03), (-0.04, 1, -0.05)):
        dv = Vector(d).normalized(); org = Vector(p); hits = []
        for _ in range(20):
            loc, nor, idx, dist = tree.ray_cast(org, dv, 50)
            if loc is None:
                break
            hits.append((round(loc.y, 4), round(loc.z, 3), idx, round(nor.dot(dv), 3)))
            org = loc + dv * 1e-5
        print("RAY", p, d, len(hits), hits)
