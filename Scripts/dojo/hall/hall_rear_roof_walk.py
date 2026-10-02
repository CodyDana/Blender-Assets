"""HALL + ARMORY round (2026-10-01): roof walks over the rear extension's lower gable roof and the valley where it meets
the main back slope, with the GASP capsule (r 0.30, half height 0.86, step 0.45, walkable 44.77 deg) on the real UCX
hulls (the resting rule of Scripts/dojo/hall/hall_roof_walk.py, copied; that file is not changed). The rear roof is out
of the 1v1 (SM_DKX_1v1_RearRoof + SM_DKX_1v1_HallUpperRear + the ring's ridge hull): its walks run in the BR hull set
(class 'boundary' left out); the 1v1 CONTROLs must block.

Run: blender -b --factory-startup Assets/Dojo/DojoShowcase_HallArmory.blend --python Scripts/dojo/hall/hall_rear_roof_walk.py
     -- --layout hall_armory/blender/layout_checks.json --out hall_armory/blender/checks/rear_roof_walk.json
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
# optional (combined showcase reruns, 2026-09-28): -- --layout <file in WorkFiles/dojo/build> --out <path in it>
LAYOUT_NAME = _A[_A.index("--layout") + 1] if "--layout" in _A else "hall_armory/blender/layout_checks.json"
OUT_NAME = _A[_A.index("--out") + 1] if "--out" in _A else "hall_armory/blender/checks/rear_roof_walk.json"
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


def rest(x, y, z_guess):
    z = z_guess + 0.6 + HH
    while z > z_guess - 0.8 + HH:
        if sphere_hit(Vector((x, y, z - (HH - R))), R):
            return z - HH
        z -= 0.004
    return None


PATHS = {
    # BR: from the main back slope down into the level valley, up the rear south slope, over the rear ridge, down to the
    # north eave
    "br_main_back_slope_down_the_valley_up_over_the_rear_ridge_to_the_north_eave":
        ("br", 7.2, [(22.0, 31.5), (22.0, 34.42), (22.0, 39.2), (22.0, 39.8), (22.0, 45.6)]),
    "br_along_the_valley": ("br", 5.8, [(15.0, 34.42), (29.0, 34.42)]),
    "br_across_the_valley_near_the_west_verge": ("br", 6.6, [(14.6, 33.3), (14.6, 35.6)]),
    "br_main_eave_stub_west_onto_the_rear_verge": ("br", 5.65, [(12.6, 34.65), (15.2, 34.65)]),
    "br_main_eave_stub_east_onto_the_rear_verge": ("br", 5.65, [(31.4, 34.65), (28.8, 34.65)]),
    "br_rear_ridge_along": ("br", 8.0, [(15.0, 39.5), (29.0, 39.5)]),
    "br_rear_north_slope_along_the_eave": ("br", 5.3, [(14.6, 45.5), (29.4, 45.5)]),
    "br_rear_south_slope_diagonal": ("br", 6.2, [(15.0, 35.0), (29.0, 39.0)]),
    # 1v1 controls: the rear roof is sealed
    "CONTROL_1v1_main_back_slope_into_the_rear_roof": ("1v1", 5.9, [(22.0, 34.0), (22.0, 36.0)]),
    "CONTROL_1v1_west_lower_roof_north_into_the_rear_yard": ("1v1", 3.9, [(11.6, 32.6), (11.6, 35.0)]),
    "CONTROL_1v1_east_lower_roof_north_into_the_rear_yard": ("1v1", 3.9, [(32.4, 32.6), (32.4, 35.0)]),
    "CONTROL_1v1_main_eave_stub_onto_the_rear_verge": ("1v1", 5.65, [(12.6, 34.65), (15.2, 34.65)]),
    # BR control: the verge is an edge (no support past it)
    "CONTROL_br_off_the_rear_verge_west": ("br", 6.4, [(14.4, 37.0), (13.4, 37.0)]),
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
res = {"capsule": {"r": R, "half_height": HH, "step": STEP, "walkable_deg": WALK_DEG}, "paths": out, "passed": ok}
(WORK / OUT_NAME).parent.mkdir(parents=True, exist_ok=True)
(WORK / OUT_NAME).write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in out.items():
    print("REARWALK", k, v["clear"], v["blocked"], "end", v["end_feet_m"], "rise", v["max_rise_per_2cm_m"], "slope",
          v["max_floor_slope_deg"])
print("REARWALK passed", ok)
