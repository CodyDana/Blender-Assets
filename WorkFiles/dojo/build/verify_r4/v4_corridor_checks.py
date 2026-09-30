"""Corridor checks on Assets/Dojo/DojoCorridors.blend (the showcase compound with the hall and the corridors):

1. ROOF WALK (route 3 and moving about the corridor roofs): the GASP capsule (r 0.30, half height 0.86, step 0.45,
   walkable 44.77 deg) set down on the UCX hulls every 2 cm along each path (Scripts/dojo/hall/hall_roof_walk.py's
   resting rule); each sample must be free of every other Pawn-blocking hull 2 cm above its rest, the rise per sample
   under 0.45 m and the floor slope under 44.77 deg. CONTROL paths must block.
2. CLEARANCE (the corridor meshes against their neighbours, render meshes, world space): intersecting triangle pairs
   (BVHTree.overlap) and the minimum distance from each corridor piece to the hall's side roof (its gutter), the hall
   veranda, the outbuilding body and roof slab; plus the gap from the corridor's highest points to the outbuilding
   roof's collision plane under which the outbuilding's own verge structure hangs (tile base 0.116 + bargeboard 0.29
   below the plane in roof_kit.gable_roof = 0.41 m).
Run: blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/corridors/corridor_checks.py
Out: WorkFiles/dojo/build/corridors/roof_walk_corridors.json, clearance_corridors.json
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
CW = WORK / "verify_r4"
L = json.loads((WORK / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
R, HH, STEP, WALK_DEG = 0.30, 0.86, 0.45, 44.77
cls_of = {p: v["class"] for p, v in L["pieces"].items()}
kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
ASM = list(bpy.data.collections["Assembly"].objects)


def piece_of(o):
    return o.name.split("__")[0]


# ------------------------------------------------------------------------------------------------ 1 roof walk
def build_bvh(with_boundary):
    verts, polys = [], []
    for inst in ASM:
        piece = piece_of(inst)
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
    while z > z_guess - 1.6 + HH:
        if sphere_hit(Vector((x, y, z - (HH - R))), R):
            return z - HH
        z -= 0.004
    return None


E = lambda pts: [(44.0 - x, y) for (x, y) in pts]   # noqa: E731
PATHS = {
    # route 3 (grey-box: storehouse roof -> corridor roof drop 1.22 m -> hall lower roof drop 0.51 m): off the
    # outbuilding roof's verge onto the corridor's south slope (the 1v1 ridge blockers stand on both ridges), along it
    # and off its gable onto the hall's side lower roof, then a few steps up it
    "route3_W_outbuilding_roof_onto_the_corridor_onto_the_hall_lower_roof": ("1v1", 4.66, [(7.0, 30.4), (9.6, 30.4),
                                                                                          (11.6, 30.4)]),
    "route3_E_outbuilding_roof_onto_the_corridor_onto_the_hall_lower_roof": ("1v1", 4.66, E([(7.0, 30.4), (9.6, 30.4),
                                                                                            (11.6, 30.4)])),
    "corridor_W_along_the_south_slope_by_the_eave": ("1v1", 3.25, [(7.95, 29.95), (10.15, 29.95)]),
    "corridor_W_up_the_south_slope_to_the_ridge_blocker": ("1v1", 3.1, [(9.0, 29.75), (9.0, 30.62)]),
    "corridor_E_along_the_south_slope_by_the_eave": ("1v1", 3.25, E([(7.95, 29.95), (10.15, 29.95)])),
    "br_corridor_W_over_the_ridge": ("br", 3.5, [(9.0, 30.2), (9.0, 31.8)]),
    "br_corridor_W_north_slope_off_the_gable_onto_the_hall_roof": ("br", 3.42, [(9.6, 31.6), (11.6, 31.6)]),
    "br_corridor_E_over_the_ridge": ("br", 3.5, E([(9.0, 30.2), (9.0, 31.8)])),
    # f1 (gable-front outbuildings): the corridor roof runs into the outbuilding's near slope, so walking back up onto
    # it is now a walk (route 3 both ways, spec 4.5); the old 'back up' control is replaced by it, and the controls
    # are the 1v1 ridge blockers (corridor ridge Y 31.0-31.1, outbuilding Y 31.7-31.8)
    "corridor_W_back_up_onto_the_outbuilding_near_slope": ("1v1", 3.42, [(9.0, 30.4), (5.0, 30.4)]),
    "corridor_E_back_up_onto_the_outbuilding_near_slope": ("1v1", 3.42, E([(9.0, 30.4), (5.0, 30.4)])),
    "CONTROL_1v1_corridor_W_over_its_ridge_blocker": ("1v1", 3.42, [(9.0, 30.4), (9.0, 31.8)]),
    "CONTROL_1v1_corridor_E_over_its_ridge_blocker": ("1v1", 3.42, E([(9.0, 30.4), (9.0, 31.8)])),
}
walk = {}
for name, (bk, z0, pts) in PATHS.items():
    BVH = BVHS[bk]
    feet, prev, worst_rise, worst_slope, blocked, drops = z0, None, 0.0, 0.0, None, []
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
                if rise < -0.10:
                    drops.append({"at": [round(x, 2), round(y, 2)], "drop_m": round(-rise, 3),
                                  "from": round(prev[2], 3), "to": round(f, 3)})
                if rise > STEP:
                    blocked = {"at": [round(x, 2), round(y, 2)], "why": f"rise {rise:.2f} > step"}
                    break
            prev = (x, y, f)
            feet = f
        if blocked:
            break
    walk[name] = {"clear": blocked is None, "blocked": blocked, "samples": samples, "start_feet_m": z0,
                  "end_feet_m": round(feet, 3), "max_rise_per_2cm_m": round(worst_rise, 4),
                  "max_floor_slope_deg": round(worst_slope, 1), "slope_ok": worst_slope <= WALK_DEG,
                  "walk_off_drops": drops}
ok = all((v["clear"] and v["slope_ok"]) != k.startswith("CONTROL") for k, v in walk.items())
res = {"capsule": {"r": R, "half_height": HH, "step": STEP, "walkable_deg": WALK_DEG}, "paths": walk, "passed": ok}
(CW / "corridor_roof_walk_showcase.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in walk.items():
    print("ROOFWALK", k, v["clear"], v["blocked"], "end", v["end_feet_m"], "rise", v["max_rise_per_2cm_m"], "slope",
          v["max_floor_slope_deg"], "drops", [d["drop_m"] for d in v["walk_off_drops"]])
print("ROOFWALK passed", ok)


# ------------------------------------------------------------------------------------------------ 2 clearance
def world_tris(objs):
    verts, polys = [], []
    for o in objs:
        me = o.data
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
    return verts, polys


def bvh_of(objs):
    v, p = world_tris(objs)
    return BVHTree.FromPolygons(v, p, epsilon=0.0), v


def min_dist(src_verts, bvh, cap=2.0):
    best = (cap, None)
    for v in src_verts:
        hit = bvh.find_nearest(v, cap)
        if hit[0] is not None and hit[3] < best[0]:
            best = (hit[3], [round(c, 3) for c in v])
    return round(best[0], 4), best[1]


corr = [o for o in ASM if piece_of(o).startswith("SM_DKC_")]
out = {}
for side, pred in (("W", lambda o: o.matrix_world.translation.x < 22.0), ("E", lambda o: o.matrix_world.translation.x
                                                                                  >= 22.0)):
    mine = [o for o in corr if pred(o)]
    xs = [(o.matrix_world @ Vector(c)).x for o in mine for c in o.bound_box]
    ys = [(o.matrix_world @ Vector(c)).y for o in mine for c in o.bound_box]
    lo, hi = Vector((min(xs) - 1.0, min(ys) - 1.0)), Vector((max(xs) + 1.0, max(ys) + 1.0))
    neigh = []
    for o in ASM:
        p = piece_of(o)
        if p.startswith("SM_DKC_") or p.startswith("SM_DGB_Boundary") or o.type != "MESH":
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if max(b.x for b in bb) < lo.x or min(b.x for b in bb) > hi.x or max(b.y for b in bb) < lo.y or \
                min(b.y for b in bb) > hi.y:
            continue
        neigh.append(o)
    rep = {"neighbours": sorted({piece_of(o) for o in neigh}), "overlaps": {}, "min_dist": {}}
    for mo in mine:
        mb, mv = bvh_of([mo])
        for no in neigh:
            nb, _ = bvh_of([no])
            pairs = mb.overlap(nb)
            if pairs:
                zs = []
                for (i, j) in pairs[:4000]:
                    poly = mo.data.polygons[i]
                    zs.append(max((mo.matrix_world @ mo.data.vertices[k].co).z for k in poly.vertices))
                rep["overlaps"].setdefault(piece_of(mo), {})[piece_of(no)] = {
                    "pairs": len(pairs), "max_z_of_my_faces": round(max(zs), 3)}
    key = {"SM_DKH_RoofLower_SideW" if side == "W" else "SM_DKH_RoofLower_SideE": "hall side lower roof + gutter",
           "SM_DKH_Veranda": "hall veranda", "SM_DKH_VerandaFrame": "hall veranda frame",
           ("SM_DGB_Storehouse" if side == "W" else "SM_DGB_Residence"): "outbuilding body",
           ("SM_DGB_Storehouse_Roof" if side == "W" else "SM_DGB_Residence_Roof"): "outbuilding roof slab",
           "SM_DKH_RoofChidori_W" if side == "W" else "SM_DKH_RoofChidori_E": "hall chidori-hafu"}
    for mo in mine:
        mv = [mo.matrix_world @ v.co for v in mo.data.vertices]
        for pn, label in key.items():
            objs = [o for o in neigh if piece_of(o) == pn]
            if not objs:
                continue
            nb, _ = bvh_of(objs)
            d, at = min_dist(mv, nb)
            if d < 2.0:
                rep["min_dist"].setdefault(piece_of(mo), {})[pn] = {"m": d, "at": at, "what": label}
    # the corridor's highest points under the outbuilding roof plane (grey-box slab top = the collision plane)
    out_roof = "SM_DGB_Storehouse_Roof" if side == "W" else "SM_DGB_Residence_Roof"
    xin = (lambda x: x < 7.6) if side == "W" else (lambda x: x > 36.4)
    worst = None
    for mo in mine:
        for v in mo.data.vertices:
            w = mo.matrix_world @ v.co
            if not xin(w.x):
                continue
            plane = 3.25 + (w.y - 27.4) * 2.0 / 4.3 if w.y <= 31.7 else 3.25 + (36.0 - w.y) * 2.0 / 4.3
            gap = plane - w.z
            if worst is None or gap < worst[0]:
                worst = (gap, [round(c, 3) for c in w], piece_of(mo))
    rep["under_outbuilding_verge"] = {
        "min_gap_to_the_roof_plane_m": round(worst[0], 3), "at": worst[1], "piece": worst[2],
        "outbuilding_structure_below_the_plane_m": 0.41, "margin_m": round(worst[0] - 0.41, 3),
        "note": "gable_roof's verge: tile base 0.116 m + bargeboard 0.03 + 0.26 m below the collision plane"}
    out[side] = rep
    print("CLEARANCE", side, json.dumps({"overlaps": rep["overlaps"], "under_verge": rep["under_outbuilding_verge"]}))
    for k, v in rep["min_dist"].items():
        print("  MIN", side, k, {kk: vv["m"] for kk, vv in v.items()})
(CW / "corridor_clearance_showcase.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
