"""KIT 1: can a GASP capsule walk route 6 from where it lands (f2: on the south end of the timber eave stand at +3.25
beside the gatehouse's courtyard eave corner, after the 1.25 m mantle from the south wall top) onto the eave corner and over the roof, and back
(the roof as a usable platform, spec 5.2)? A capsule (r 0.30, half height 0.86) is set down on the UCX hulls at 2 cm steps along each path
(the same resting rule as climb_check.py), and each sample must be free of every other Pawn-blocking hull 2 cm above
its rest, the rise per step must stay under the 0.45 m step height and the local slope under 44.77 deg (GASP CMC).

Run: blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/roof_walk_check.py
Out: WorkFiles/dojo/build/kit1/roof_walk_check.json
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
import sys  # noqa: E402
_A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
# optional (showcase reruns): -- --layout <file in WorkFiles/dojo/build> --out <path relative to WorkFiles/dojo/build>
LAYOUT_NAME = _A[_A.index("--layout") + 1] if "--layout" in _A else "layout.json"
OUT_NAME = _A[_A.index("--out") + 1] if "--out" in _A else "kit1/roof_walk_check.json"
L = json.loads((WORK / LAYOUT_NAME).read_text(encoding="utf-8"))
R, HH, STEP, WALK_DEG = 0.30, 0.86, 0.45, 44.77
cls_of = {p: v["class"] for p, v in L["pieces"].items()}
kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}


def build_bvh(with_boundary):
    verts, polys = [], []
    for inst in bpy.data.collections["Assembly"].objects:
        piece = inst.name.split("__")[0]
        if piece not in kit or L["collision_classes"][cls_of[piece]]["pawn"] != "block":
            continue
        if cls_of[piece] == "boundary" and not with_boundary:
            continue
        for h in kit[piece].children:
            if not h.name.startswith("UCX_"):
                continue
            bm = bmesh.new()
            bm.from_mesh(h.data)
            mw = inst.matrix_world @ h.matrix_local
            base = len(verts)
            verts += [mw @ v.co for v in bm.verts]
            polys += [[base + v.index for v in f.verts] for f in bm.faces]
            bm.free()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0)


BVHS = {"1v1": build_bvh(True), "br": build_bvh(False)}
BVH = None


def sphere_hit(p, r):
    hit = BVH.find_nearest(p, r)
    return hit[0] is not None and hit[3] < r - 1e-4


def capsule_blocked(c):
    a = HH - R
    n = int(math.ceil(2 * a / 0.05))
    return any(sphere_hit(c + Vector((0, 0, -a + 2 * a * i / n)), R) for i in range(n + 1))


def rest(x, y, z_guess):
    """Lower the capsule from z_guess + 0.6 until its bottom sphere touches; returns the feet height or None."""
    z = z_guess + 0.6 + HH
    while z > z_guess - 0.8 + HH:
        if sphere_hit(Vector((x, y, z - (HH - R))), R):
            return z - HH
        z -= 0.004
    return None


_S = L["kit1"]["gate_stands"]
WX = sum(_S["world_x"][0]) / 2            # f2: the eave stands' centre lines (the route-6 mantle lands on their south end)
EX = sum(_S["world_x"][1]) / 2
Y_LAND = _S["world_y"][0] + 0.40          # where the capsule stands after the mantle (0.4 m in from the front ledge)
PATHS = {   # name: (bvh, start feet, points). 1v1 = with the 1v1 boundary (the south half of the roof is out of bounds)
    # f2 (plain gable, the grey-box way, no plaster pier): route 6 lands on the south end of the timber eave stand
    # (+3.25) after the 1.25 m mantle from the south wall top, walks north along the deck, steps onto the N eave corner
    # and walks the N slope; and the way back onto the stand
    "1v1_route6_west_stand_along_the_deck_onto_N_eave_to_centre": ("1v1", 3.25, [(WX, Y_LAND), (WX, 2.30), (19.5, 2.30),
                                                                                 (22.0, 2.2)]),
    "1v1_route6_east_stand_along_the_deck_onto_N_eave_to_centre": ("1v1", 3.25, [(EX, Y_LAND), (EX, 2.30), (24.5, 2.30),
                                                                                 (22.0, 2.2)]),
    "1v1_N_slope_along_the_eave": ("1v1", 3.30, [(18.3, 2.2), (25.7, 2.2)]),
    "1v1_N_eave_up_to_the_ridge": ("1v1", 3.30, [(22.0, 2.3), (22.0, 0.15)]),
    "1v1_N_slope_back_onto_the_west_stand": ("1v1", 3.40, [(19.5, 2.30), (WX, 2.30), (WX, Y_LAND)]),
    "br_over_the_ridge_S_to_N": ("br", 3.8, [(22.0, -1.5), (22.0, 1.5)]),
}
out = {}
for name, (bk, z0, pts) in PATHS.items():
    BVH = BVHS[bk]
    feet, prev, worst_rise, worst_slope, blocked = z0, None, 0.0, 0.0, None
    samples = 0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.02))
        for i in range(n + 1):
            x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
            f = rest(x, y, feet)
            samples += 1
            if f is None:
                blocked = {"at": [round(x, 2), round(y, 2)], "why": "no support"}
                break
            c = Vector((x, y, f + HH + 0.02))
            if capsule_blocked(c):
                blocked = {"at": [round(x, 2), round(y, 2)], "feet": round(f, 3), "why": "capsule overlaps a hull"}
                break
            hit = BVH.ray_cast(Vector((x, y, f + 0.5)), Vector((0, 0, -1)), 1.5)
            if hit[1] is not None:
                ang = math.degrees(math.acos(max(-1.0, min(1.0, abs(hit[1].z)))))
                if ang < 80.0:          # a vertical face under the centre is a step edge, not a floor
                    worst_slope = max(worst_slope, ang)
            if prev is not None:
                rise = f - prev[2]
                worst_rise = max(worst_rise, rise)
                if rise > STEP:
                    blocked = {"at": [round(x, 2), round(y, 2)], "why": f"rise {rise:.2f} > step"}
                    break
            prev = (x, y, f)
            feet = f
        if blocked:
            break
    out[name] = {"clear": blocked is None, "blocked": blocked, "samples": samples, "end_feet_m": round(feet, 3),
                 "max_rise_per_2cm_m": round(worst_rise, 4), "max_floor_slope_deg": round(worst_slope, 1),
                 "slope_ok": worst_slope <= WALK_DEG}
res = {"capsule": {"r": R, "half_height": HH, "step": STEP, "walkable_deg": WALK_DEG}, "paths": out,
       "passed": all(v["clear"] and v["slope_ok"] for v in out.values())}
(WORK / OUT_NAME).parent.mkdir(parents=True, exist_ok=True)
(WORK / OUT_NAME).write_text(json.dumps(res, indent=1), encoding="utf-8")
print("ROOFWALK", json.dumps(out), "passed", res["passed"])
