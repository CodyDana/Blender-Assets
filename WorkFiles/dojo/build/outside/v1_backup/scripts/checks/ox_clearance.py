"""ROUND 5 OUTSIDE: clearance of this track's pieces against every other kit's render mesh (read-only on DojoOutside.blend).
For each SM_DKX_* instance of the street (both sides, X -70..115) and the alley fences, every other kit's
render-mesh vertex that lies inside the instance's world bounding box shrunk by 5 mm is counted (per other piece).
Contacts at intended joints (the kerb under the apron's front slabs, the verge under the wall footing) are listed for the
record. Out: WorkFiles/dojo/build/outside/checks/clearance_outside.json
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "outside" / "checks" / "clearance_outside.json"
asm = list(bpy.data.collections["Assembly"].objects)


def piece(o):
    return o.name.split("__")[0]


def wbox(o, shrink=0.005):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return ([min(p[i] for p in pts) + shrink for i in range(3)], [max(p[i] for p in pts) - shrink for i in range(3)])


# round 6: the far pieces (ridge rings, far town) span the whole map in bounding box, and the SM_DKX_1v1_* blockers are
# invisible and cut through roofs by design: none of them is a visual clearance question
mine = [o for o in asm if piece(o).startswith("SM_DKX_") and not piece(o).startswith((
    "SM_DKX_Mountains", "SM_DKX_Ridge", "SM_DKX_FarTown", "SM_DKX_FarGround", "SM_DKX_Ground_", "SM_DKX_House",
    "SM_DKX_1v1_"))]
near = []
for o in mine:
    lo, hi = wbox(o)
    if hi[0] > -70 and lo[0] < 115 and hi[1] > -10 and lo[1] < 43:
        near.append((o, lo, hi))
others = [o for o in asm if not piece(o).startswith("SM_DKX_") and o.type == "MESH"
          and not piece(o).startswith("SM_DGB_Boundary")]
res = {}
for o2 in others:
    lo2, hi2 = wbox(o2, 0.0)
    cand = [(o, lo, hi) for (o, lo, hi) in near if all(lo[i] < hi2[i] and hi[i] > lo2[i] for i in range(3))]
    if not cand:
        continue
    M = o2.matrix_world
    vs = [M @ v.co for v in o2.data.vertices]
    for (o, lo, hi) in cand:
        n = sum(1 for p in vs if all(lo[i] < p[i] < hi[i] for i in range(3)))
        if n:
            k = f"{piece(o)} x {piece(o2)}"
            e = res.setdefault(k, {"verts_inside": 0, "instances": set()})
            e["verts_inside"] += n
            e["instances"].add(f"{o.name} / {o2.name}")
out = {k: {"verts_inside": v["verts_inside"], "instances": sorted(v["instances"])[:6]} for k, v in sorted(res.items())}
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items():
    print("CLEAR", k, v["verts_inside"], v["instances"][:2])
print("CLEARANCE pairs", len(out))
