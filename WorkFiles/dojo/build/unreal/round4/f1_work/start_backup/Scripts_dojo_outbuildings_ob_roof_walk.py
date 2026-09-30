"""Outbuilding roof walks (routes 2 and 3 on the real UCX hulls): can GASP's capsule (r 0.30, half height 0.86, step
0.45, walkable 44.77 deg) step from kit 1's route-2 step pier onto the storehouse / residence south eave, walk the
south slope to the verge at Y 31.0 and walk off it onto the corridor roof (the grey-box's 1.22 m drop), and are the
closed places closed? Same resting rule as Scripts/dojo/roof_walk_check.py / hall_roof_walk.py (capsule set down every
2 cm; each sample free of every other Pawn-blocking hull 2 cm above its rest; rise per step <= 0.45; floor slope
<= 44.77 deg). A DROP path walks off an edge: after the edge the capsule must fall freely (no hull in its way) onto a
floor within `drop_max`, and the drop is reported.

Run: blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/outbuildings/ob_roof_walk.py
     [-- --layout outbuildings/layout_outbuildings_checks.json --out outbuildings/roof_walk_outbuildings.json]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
_A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LAYOUT_NAME = _A[_A.index("--layout") + 1] if "--layout" in _A else "outbuildings/layout_outbuildings_checks.json"
OUT_NAME = _A[_A.index("--out") + 1] if "--out" in _A else "outbuildings/roof_walk_outbuildings.json"
L = json.loads((WORK / LAYOUT_NAME).read_text(encoding="utf-8"))
R, HH, STEP, WALK_DEG = 0.30, 0.86, 0.45, 44.77
cls_of = {p: v["class"] for p, v in L["pieces"].items()}
kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}


def build_bvh(with_boundary):
    verts, polys = [], []
    for inst in bpy.data.collections["Assembly"].objects:
        piece = inst.name.split("__")[0]
        if piece not in kit or piece not in cls_of or L["collision_classes"][cls_of[piece]]["pawn"] != "block":
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


def rest(x, y, z_guess, below=0.8):
    z = z_guess + 0.6 + HH
    while z > z_guess - below + HH:
        if sphere_hit(Vector((x, y, z - (HH - R))), R):
            return z - HH
        z -= 0.004
    return None


OB = L.get("outbuildings", {})
PATHS = {
    # route 2: from kit 1's step pier (flat top +3.25, after the 1.25 m mantle from the wall top) straight onto the
    # south eave (+3.25 at Y 27.4), up the south slope to the route-3 line and along it to the east verge. The 1v1
    # line is Y 30.4: the grey-box's 1v1 blocker stands on the corridor ridge (Y 31.0-31.1), so the corridor is
    # walked on its south slope (as hall_roof_walk's route 3); Y 31.0 (the grey-box climb entry) is the BR line
    "route2_west_pier_onto_the_storehouse_eave_to_the_verge": ("walk", "1v1", 3.25,
                                                               [(-0.5, 26.9), (-0.5, 28.0), (0.2, 30.4), (7.3, 30.4)]),
    "route2_east_pier_onto_the_residence_eave_to_the_verge": ("walk", "1v1", 3.25,
                                                              [(44.5, 26.9), (44.5, 28.0), (43.8, 30.4), (36.7, 30.4)]),
    # route 3: walk off the verge onto the (grey-box) corridor roof, then (hall_roof_walk) on to the hall
    "route3_storehouse_verge_drop_onto_the_west_corridor_roof": ("drop", "1v1", 4.65, [(7.3, 30.4), (8.2, 30.4)]),
    "route3_residence_verge_drop_onto_the_east_corridor_roof": ("drop", "1v1", 4.65, [(36.7, 30.4), (35.8, 30.4)]),
    "br_route3_storehouse_verge_drop_on_the_greybox_line_Y31": ("drop", "br", 4.92, [(7.3, 31.0), (8.2, 31.0)]),
    "br_route3_residence_verge_drop_on_the_greybox_line_Y31": ("drop", "br", 4.92, [(36.7, 31.0), (35.8, 31.0)]),
    # moving about: along the eave, over the door canopy's roof line (nothing sticks up through the slab)
    "storehouse_south_slope_along_the_eave": ("walk", "1v1", 3.35, [(0.2, 27.7), (7.3, 27.7)]),
    "residence_south_slope_along_the_eave": ("walk", "1v1", 3.35, [(43.8, 27.7), (36.7, 27.7)]),
    "br_storehouse_over_the_ridge_to_the_north_eave": ("walk", "br", 4.9, [(3.3, 31.0), (3.3, 35.7)]),
    # controls: the 1v1 ridge blocker; the wall top under the roof (no headroom); the closed doors
    "CONTROL_1v1_storehouse_south_slope_over_the_ridge": ("walk", "1v1", 4.9, [(3.3, 31.0), (3.3, 32.6)]),
    "CONTROL_1v1_residence_south_slope_over_the_ridge": ("walk", "1v1", 4.9, [(40.7, 31.0), (40.7, 32.6)]),
    "CONTROL_west_wall_top_north_under_the_storehouse_roof": ("walk", "br", 2.0, [(-0.5, 27.9), (-0.5, 30.0)]),
    "CONTROL_into_the_storehouse_door": ("walk", "br", 0.0, [(3.5, 26.6), (3.5, 28.6)]),
    "CONTROL_into_the_residence_door": ("walk", "br", 0.0, [(39.35, 26.6), (39.35, 28.6)]),
}
out = {}
for name, (kind, bk, z0, pts) in PATHS.items():
    BVH = BVHS[bk]
    feet, prev, worst_rise, worst_slope, blocked = z0, None, 0.0, 0.0, None
    samples = 0
    drop = None
    if kind == "drop":
        (xa, ya), (xb, yb) = pts
        top = rest(xa, ya, z0)
        edge = None
        n = max(2, int(math.hypot(xb - xa, yb - ya) / 0.02))
        for i in range(n + 1):
            x, y = xa + (xb - xa) * i / n, ya + (yb - ya) * i / n
            f = rest(x, y, top if top is not None else z0, below=0.30)
            samples += 1
            if f is None:
                edge = (x, y)
                break
            if capsule_blocked(Vector((x, y, f + HH + 0.02))):
                blocked = {"at": [round(x, 2), round(y, 2)], "why": "capsule overlaps a hull before the edge"}
                break
            top = f
        if blocked is None and edge is None:
            blocked = {"why": "no edge found"}
        if blocked is None:
            # fall: from the last floor straight down at the edge sample + 0.30 (the capsule has left the edge)
            ex, ey = edge[0] + (xb - xa) / max(1e-6, math.hypot(xb - xa, yb - ya)) * 0.30, \
                edge[1] + (yb - ya) / max(1e-6, math.hypot(xb - xa, yb - ya)) * 0.30
            land = rest(ex, ey, top, below=2.5)
            z = top
            clear = True
            while land is not None and z > land + 0.01:
                if capsule_blocked(Vector((ex, ey, z + HH + 0.02))):
                    clear = False
                    break
                z -= 0.02
            if land is None:
                blocked = {"why": "no landing within 2.5 m"}
            elif not clear:
                blocked = {"why": f"hull in the fall at z {z:.2f}"}
            else:
                drop = {"edge_xy": [round(edge[0], 3), round(edge[1], 3)], "from_feet": round(top, 3),
                        "landing_xy": [round(ex, 3), round(ey, 3)], "landing_feet": round(land, 3),
                        "drop_m": round(top - land, 3)}
                feet = land
        out[name] = {"clear": blocked is None, "blocked": blocked, "samples": samples, "drop": drop,
                     "max_rise_per_2cm_m": 0.0, "max_floor_slope_deg": 0.0, "slope_ok": True, "end_feet_m": feet}
        continue
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
                if ang < 80.0:
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
    out[name] = {"clear": blocked is None, "blocked": blocked, "samples": samples, "start_feet_m": z0,
                 "end_feet_m": round(feet, 3), "max_rise_per_2cm_m": round(worst_rise, 4),
                 "max_floor_slope_deg": round(worst_slope, 1), "slope_ok": worst_slope <= WALK_DEG}
ok = all((v["clear"] and v["slope_ok"]) != k.startswith("CONTROL") for k, v in out.items())
res = {"capsule": {"r": R, "half_height": HH, "step": STEP, "walkable_deg": WALK_DEG}, "layout": LAYOUT_NAME,
       "paths": out, "passed": ok}
(WORK / OUT_NAME).write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in out.items():
    print("OBWALK", k, v["clear"], v["blocked"], "end", v["end_feet_m"], "rise", v["max_rise_per_2cm_m"], "slope",
          v["max_floor_slope_deg"], "drop", v.get("drop"))
print("OBWALK passed", ok)
