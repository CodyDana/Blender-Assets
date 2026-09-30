"""VERIFY r4: render tile CREST (the upper envelope across one tile pitch) vs the UCX walk surface, on the new roofs and,
for comparison, the hall and the gate (already accepted rounds). Own scene from the FBX + layout matrices (v4_measure).
Out: verify_r4/roof_crest.json"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("v4m_lib", str(Path(__file__).parent / "v4_measure.py"))
src = (Path(__file__).parent / "v4_measure.py").read_text(encoding="utf-8").replace("\nmain()\n", "\n")
g = {"__name__": "v4m_lib", "__file__": str(Path(__file__).parent / "v4_measure.py")}
exec(compile(src, "v4_measure.py", "exec"), g)
L = g["L"]
g["KITS"] = ("outbuildings", "corridors", "pavilion", "hall", "kit1")
KEEP = ("SM_DKO_Roof", "SM_DKC_Bay_Roof", "SM_DKV_RoofQuarter", "SM_DKH_RoofLower_Front", "SM_DKH_RoofUpper_Front",
        "SM_DK_Gate_Roof")
# only the roof pieces
orig = L["instances"]
L["instances"] = [i for i in orig if i["piece"].startswith(KEEP)]
objs = g["build_scene"]()
R = [o for k, p, n, o in objs if k == "R"]
C = [o for k, p, n, o in objs if k == "C"]
bR, bC = g["bvh_of"](R), g["bvh_of"](C)


def crest(x, y, axis, span=0.40):
    """max render z over a 0.40 m cross line (1 cm) through (x, y) along `axis` (the across-the-slope direction)."""
    best = None
    for k in range(41):
        d = -span / 2 + span * k / 40
        px, py = (x + d, y) if axis == "x" else (x, y + d)
        z = g["down"](bR, px, py)
        if z is not None and (best is None or z > best):
            best = z
    return best


pts = {  # (x, y, across-axis): mid-slope points
    "storehouse far slope": (1.2, 33.8, "y"), "storehouse near slope": (5.6, 34.4, "y"),
    "residence near slope": (38.8, 34.4, "y"),
    "corridor W south slope": (8.6, 30.2, "x"), "corridor E south slope": (35.4, 30.2, "x"),
    "pavilion west face": (39.2, 3.0, "y"), "pavilion south face": (41.0, 1.2, "x"),
    "hall lower roof front": (22.5, 21.3, "x"), "hall upper roof front": (22.5, 23.8, "x"),
    "gate roof south slope": (21.3, -0.6, "x"), "gate roof north slope": (21.3, 0.9, "x"),
}
res = {}
for k, (x, y, ax) in pts.items():
    cr = crest(x, y, ax)
    col = g["down"](bC, x, y)
    res[k] = {"at": [x, y], "render_crest_z": cr, "render_at_point": g["down"](bR, x, y), "collision_z": col,
              "collision_minus_crest_m": round(col - cr, 4) if (cr is not None and col is not None) else None}
Path(__file__).parent.joinpath("roof_crest.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in res.items():
    print("CREST", k, v)
