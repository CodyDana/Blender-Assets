"""Hall roof walks: can the GASP capsule (r 0.30, half height 0.86, step 0.45, walkable 44.77 deg) walk the hall's
roofs along routes 3, 4 and 5 on the real UCX hulls (the same resting rule as Scripts/dojo/roof_walk_check.py, whose
paths are kit-1-specific)? Each path sets the capsule down every 2 cm; each sample must be free of every other
Pawn-blocking hull 2 cm above its rest, with the rise per step under 0.45 m and the floor slope under 44.77 deg.
CONTROL paths must block.

Run: blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/hall_roof_walk.py
Out: WorkFiles/dojo/build/hall/roof_walk_hall.json
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
LAYOUT_NAME = _A[_A.index("--layout") + 1] if "--layout" in _A else "hall/layout_hall_checks.json"
OUT_NAME = _A[_A.index("--out") + 1] if "--out" in _A else "hall/roof_walk_hall.json"
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


H = L["hall"]
st = H["ac_zones"]["stance"]
PATHS = {
    # route 3: off the (grey-box) corridor roof's south slope (the 1v1 ridge blocker stands on its ridge, Y 31.0) down
    # onto the hall's west lower roof, then up it toward the wall
    "route3_corridor_roof_down_onto_the_west_lower_roof": ("1v1", 3.42, [(9.6, 30.4), (11.2, 30.4), (11.6, 30.4)]),
    "route3_east_corridor_roof_onto_the_east_lower_roof": ("1v1", 3.42, [(34.4, 30.4), (32.8, 30.4), (32.4, 30.4)]),
    # route 4: from the landing deck (after the 1.75 mantle) onto the lower roof and along it to the AC stance
    "route4_eave_landing_onto_the_lower_roof_to_the_AC_stance": ("1v1", 3.0, [(13.65, 21.05), (13.65, 21.6),
                                                                              (st["W"][0], 21.6), (st["W"][0], st["W"][1])]),
    "route4_east_landing_onto_the_lower_roof_to_the_AC_stance": ("1v1", 3.0, [(30.35, 21.05), (30.35, 21.6),
                                                                              (st["E"][0], 21.6), (st["E"][0], st["E"][1])]),
    # route 5: from the AC top (+5.10, after the mantle) the 0.40 step onto the upper eave, then up to the 1v1 ridge
    "route5_AC_top_step_onto_the_upper_eave_and_up_the_slope": ("1v1", 5.10, [(15.6, 22.55), (15.6, 23.4),
                                                                               (15.6, 28.4)]),
    "route5_east_AC_top_onto_the_upper_eave": ("1v1", 5.10, [(28.4, 22.55), (28.4, 23.4), (28.4, 26.0)]),
    # moving about the roofs
    "lower_front_roof_between_the_ACs": ("1v1", 3.35, [(16.9, 22.3), (27.1, 22.3)]),
    "lower_roof_round_the_west_hip_corner_over_the_chidori": ("1v1", 3.4, [(11.3, 29.6), (11.3, 23.2), (12.0, 22.1),
                                                                           (13.4, 22.0)]),
    # fix round f1: across the whole front slope, stepping over both descending diagonal ridges (0.25 m hulls) and the
    # raised centre eave's slope; and up past the diagonal to the ridge on the east side too
    "upper_front_slope_across_both_diagonal_ridges": ("1v1", 6.0, [(14.2, 24.6), (29.8, 24.6)]),
    "route5_east_up_over_the_diagonal_ridge": ("1v1", 6.0, [(28.4, 23.4), (28.4, 28.4)]),
    # the side lower roofs carry a chidori-hafu (Y 24.6-29.4 at the eave): walk up and over it along the roof
    "lower_roof_over_the_east_chidori": ("1v1", 3.4, [(32.7, 29.4), (32.7, 23.4)]),
    "br_upper_roof_over_the_ridge": ("br", 7.9, [(22.0, 28.2), (22.0, 29.9)]),
    # controls: the clerestory wall above the lower roof blocks; the gable face under the verge blocks
    "CONTROL_lower_roof_up_under_the_upper_eave_to_the_clerestory": ("1v1", 3.6, [(20.0, 22.8), (20.0, 24.3)]),
    "CONTROL_upper_end_slope_into_the_gable": ("br", 5.6, [(12.4, 29.0), (14.8, 29.0)]),
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
(WORK / OUT_NAME).write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in out.items():
    print("ROOFWALK", k, v["clear"], v["blocked"], "end", v["end_feet_m"], "rise", v["max_rise_per_2cm_m"], "slope",
          v["max_floor_slope_deg"])
print("ROOFWALK passed", ok)
