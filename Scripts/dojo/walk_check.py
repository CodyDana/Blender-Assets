"""Grey-box ground-route clearance for GASP's capsule, measured against the UCX collision hulls (the same hulls Unreal
imports; dj_verify checks the counts). Unreal capsule traces do not collide in a -nullrhi commandlet (armory finding), so
the geometric check runs here, adapted from Scripts/armory/walk_check.py.

Capsule: GASP SandboxCharacter_CMC (read by dj_gasp_inspect.py): radius 0.30 m, half height 0.86 m (1.72 m tall);
CharacterMovement MaxStepHeight 0.45 m. A route sample is clear when no Pawn-blocking hull whose z range reaches into the
body band (floor + 0.20 .. floor + 1.72) comes within the radius horizontally; a hull within the radius whose top is at
most 0.45 above the current floor is stepped onto (the floor rises to it). Hulls are taken as axis-aligned boxes; the
routes are all at ground, veranda or wall-top level where every hull is a box (sloped roof hulls are far above the band).
Every route is also run at the spec's 0.35 m radius (Manny) as a margin figure. CONTROL routes must be blocked.

Run: blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/walk_check.py
Result: WorkFiles/dojo/build/walk_check.json
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
import sys  # noqa: E402
_A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
# optional: -- --layout <file in WorkFiles/dojo/build> --out <path relative to WorkFiles/dojo/build> (KIT 1 reruns)
LAYOUT_NAME = _A[_A.index("--layout") + 1] if "--layout" in _A else "layout.json"
OUT_NAME = _A[_A.index("--out") + 1] if "--out" in _A else "walk_check.json"
L = json.loads((WORK / LAYOUT_NAME).read_text(encoding="utf-8"))
BAND0, HEIGHT, STEP = 0.20, 1.72, 0.45
classes = L["collision_classes"]
cls_of = {p: v["class"] for p, v in L["pieces"].items()}
kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
from mathutils import Matrix  # noqa: E402
import math  # noqa: E402
OPEN = {it["piece"]: it for it in L.get("kit1", {}).get("gate_leaf_placements", {}).get("open", [])}


def hull_list(open_leaves=False, exclude=()):
    """Pawn-blocking hulls as world AABBs; open_leaves: the kit-1 gate leaves at their layout 'open' placement;
    exclude: collision classes left out (e.g. the 1v1 boundary for a battle-royale route)."""
    out = []
    for inst in bpy.data.collections["Assembly"].objects:
        piece = inst.name.split("__")[0]
        src = kit.get(piece)
        if src is None or classes[cls_of[piece]]["pawn"] != "block" or cls_of[piece] in exclude:
            continue
        mw = inst.matrix_world
        if open_leaves and piece in OPEN:
            it = OPEN[piece]
            mw = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
        for h in src.children:
            if h.name.startswith("UCX_"):
                pts = [mw @ (h.matrix_local @ Vector(c)) for c in h.bound_box]
                out.append((min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts),
                            min(p.z for p in pts), max(p.z for p in pts), inst.name))
    return out


HULLS = {False: hull_list(False), True: hull_list(True, ("boundary",))}
hulls = HULLS[False]


def probe(x, y, floor, r, hulls=None):
    hulls = HULLS[False] if hulls is None else hulls
    new_floor = floor
    near = []
    for (x0, x1, y0, y1, z0, z1, name) in hulls:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        if (dx * dx + dy * dy) ** 0.5 < r:
            near.append((z0, z1, name, dx == 0.0 and dy == 0.0))
    for z0, z1, name, under in near:
        if z1 <= floor + STEP:
            if under:
                new_floor = max(new_floor, z1)
        elif z0 < floor + HEIGHT and z1 > floor + BAND0:
            return name, floor
    return None, new_floor


def run(r):
    out = {}
    for name, rt in L["walk_routes"].items():
        pts, floor, hits, clear_min = rt["points"], rt["floor_z"], [], None
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 0.02))
            for i in range(n + 1):
                t = i / n
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                b, floor = probe(x, y, floor, r, HULLS[rt.get("leaves") == "open"])
                if b:
                    hits.append({"at_m": [round(x, 2), round(y, 2)], "hull_of": b, "floor_m": round(floor, 3)})
                    break
            if hits:
                break
        out[name] = {"clear": not hits, "first_block": hits[0] if hits else None, "end_floor_m": round(floor, 3),
                     "start_floor_m": rt["floor_z"]}
    return out


res = {"capsule": {"radius_m": 0.30, "height_m": HEIGHT, "step_m": STEP, "source": "GASP SandboxCharacter_CMC CDO"},
       "n_hulls_pawn": len(hulls), "routes": run(0.30), "routes_r035_spec": run(0.35)}
res["control_blocked"] = all(not v["clear"] for k, v in res["routes"].items() if k.startswith("CONTROL"))
res["passed"] = res["control_blocked"] and all(v["clear"] for k, v in res["routes"].items() if not k.startswith("CONTROL"))
res["passed_r035"] = (all(not v["clear"] for k, v in res["routes_r035_spec"].items() if k.startswith("CONTROL"))
                      and all(v["clear"] for k, v in res["routes_r035_spec"].items() if not k.startswith("CONTROL")))
(WORK / OUT_NAME).write_text(json.dumps(res, indent=1), encoding="utf-8")
print("WALK", json.dumps({k: (v["clear"], v["first_block"]) for k, v in res["routes"].items()}), "passed", res["passed"],
      "passed_r035", res["passed_r035"])
