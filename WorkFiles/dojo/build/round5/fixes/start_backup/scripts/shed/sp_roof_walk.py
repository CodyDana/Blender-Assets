"""Round 4: can a GASP capsule walk the shed and pavilion roofs from where route 7 lands it (the shed's front band, the
pavilion's eave pad) and on over the real roof hulls? The machinery is Scripts/dojo/roof_walk_check.py's (copied, not
imported: that script runs its kit-1 paths at import): a capsule (r 0.30, half height 0.86) is set down on the UCX
hulls at 2 cm steps along each path; each sample must be free of every other Pawn-blocking hull 2 cm above its rest,
the rise per step under the 0.45 m step height and the local slope under 44.77 deg (GASP CMC). CONTROL paths must be
blocked.

Run: blender -b --factory-startup Assets/Dojo/DojoShed.blend --python Scripts/dojo/shed/sp_roof_walk.py -- --asset shed
     blender -b --factory-startup Assets/Dojo/DojoPavilion.blend --python Scripts/dojo/shed/sp_roof_walk.py -- --asset pavilion
Out: WorkFiles/dojo/build/shed_pavilion/checks/roof_walk_<asset>.json
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
ASSET = _A[_A.index("--asset") + 1] if "--asset" in _A else "shed"
L = json.loads((WORK / "shed_pavilion" / f"layout_{ASSET}_checks.json").read_text(encoding="utf-8"))
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
    z = z_guess + 0.6 + HH
    while z > z_guess - 0.8 + HH:
        if sphere_hit(Vector((x, y, z - (HH - R))), R):
            return z - HH
        z -= 0.004
    return None


if ASSET == "shed":
    PATHS = {   # (bvh, start feet, points)
        "route7_band_landing_along_the_band": ("1v1", 2.5, [(3.0, 4.62), (0.55, 4.62), (5.45, 4.62)]),
        "route7_band_up_the_lean_to_to_the_back": ("1v1", 2.5, [(3.0, 4.62), (3.0, 0.45)]),
        "lean_to_across_near_the_back": ("1v1", 2.95, [(0.45, 0.6), (5.55, 0.6)]),
        "lean_to_down_back_onto_the_band": ("1v1", 2.95, [(1.5, 0.6), (1.5, 4.7)]),
        "lean_to_west_edge_down_onto_the_west_wall_top": ("1v1", 2.8, [(0.6, 2.0), (-0.5, 2.0)]),
    }
else:
    PATHS = {
        "route7_pad_landing_onto_the_west_face_up_to_the_finial": ("1v1", 3.25, [(38.05, 3.0), (38.6, 3.0),
                                                                                (40.35, 3.0)]),
        "pad_along_the_deck": ("1v1", 3.25, [(38.05, 2.55), (38.05, 3.45)]),
        "west_face_round_the_SW_hip_onto_the_south_face": ("1v1", 3.35, [(38.8, 3.0), (39.0, 1.4), (40.4, 0.85),
                                                                        (41.6, 0.85)]),
        "south_face_up_to_the_finial": ("1v1", 3.3, [(41.0, 0.8), (41.0, 2.25)]),
        "north_face_round_the_NW_hip_back_to_the_pad": ("1v1", 3.4, [(41.0, 5.1), (39.4, 5.0), (38.9, 3.6),
                                                                    (38.05, 3.4)]),
        "CONTROL_into_the_finial": ("1v1", 4.2, [(41.0, 2.0), (41.0, 3.0)]),
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
    ok = (blocked is None and worst_slope <= WALK_DEG)
    if name.startswith("CONTROL"):
        ok = blocked is not None
    out[name] = {"clear": blocked is None, "blocked": blocked, "samples": samples, "end_feet_m": round(feet, 3),
                 "max_rise_per_2cm_m": round(worst_rise, 4), "max_floor_slope_deg": round(worst_slope, 1),
                 "slope_ok": worst_slope <= WALK_DEG, "pass": ok}
res = {"asset": ASSET, "capsule": {"r": R, "half_height": HH, "step": STEP, "walkable_deg": WALK_DEG}, "paths": out,
       "passed": all(v["pass"] for v in out.values())}
dst = WORK / "shed_pavilion" / "checks" / f"roof_walk_{ASSET}.json"
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("ROOFWALK", ASSET, json.dumps({k: (v["pass"], v["blocked"], v["end_feet_m"]) for k, v in out.items()}),
      "passed", res["passed"])
