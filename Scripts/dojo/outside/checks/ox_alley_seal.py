"""ROUND 6 (2026-09-29) OUTSIDE track: is the 1v1 rear area (the strip behind the hall, both pockets behind the
corridors, the corridors' north slopes, the outbuildings' north roof halves, the hall's upper rear half and the north
wall top) sealed, from every side and at every height? Measured on the real UCX hulls of the combined compose in
Assets/Dojo/DojoOutside.blend (the showcase + this track), Pawn-blocking classes from layout_outside_checks.json.

1. FLOOD (the strongest test): a FLYING capsule (GASP r 0.30, 1.72 m; it may be anywhere its body fits, so every jump,
   double jump, mantle, fall or roof walk is a subset of what it can do) is flooded through the whole compound inside
   the 1v1 ring (X -1..45, Y -1..37, bottoms +0.05..+18.25 under the +20 ceiling) from the courtyard centre. Grid 0.1 m
   in plan, 0.1 m slices; a slice cell is free when the disc of radius r at that height clears every hull's section
   (convex polygon distance), a capsule cell when 18 slices from its bottom (1.7 m) are free. Discretisation only ever
   UNDER-blocks (thin hulls between slices, the 1.72 m body sampled over 1.7 m), so a reported seal is conservative.
   Modes: '1v1' (everything), 'r5' (without this round's pocket fences and SM_DKX_1v1_* blockers: must reproduce the
   verify_r5 leak), 'br' (without any 'boundary' class and without the four 1v1 fences: the BR opens the area).
2. CONTROL paths: a capsule swept every 2 cm at a fixed feet height (standing, on a fence top, on a roof, at a double
   jump's height) from each side into the area: all must block in '1v1'. POSITIVE paths beside the new blockers
   (corridor floor, veranda side, lower side roof, corridor south slope) must stay clear.

Run: blender -b --factory-startup Assets/Dojo/DojoOutside.blend --python Scripts/dojo/outside/checks/ox_alley_seal.py
     -- [--out round6/build/checks/alley_seal.json] [--modes 1v1,r5,br]
Out: WorkFiles/dojo/build/<out> (+ <out>_plan.json: the reached plan per mode for ox_alley_seal_plot.py)
"""
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
_A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = WORK / (_A[_A.index("--out") + 1] if "--out" in _A else "round6/build/checks/alley_seal.json")
MODES = (_A[_A.index("--modes") + 1] if "--modes" in _A else "1v1,r5,br").split(",")
OUT.parent.mkdir(parents=True, exist_ok=True)
L = json.loads((WORK / "outside" / "layout_outside_checks.json").read_text(encoding="utf-8"))
CLS = {p: v["class"] for p, v in L["pieces"].items()}
R, HH, BODY = 0.30, 0.86, 1.72
kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
ROUND6 = ("SM_DKX_PocketFence_", "SM_DKX_1v1_")
FENCES_1V1 = ("SM_DKX_PocketFence_", "SM_DKX_AlleyFence_")


def included(piece, mode):
    if piece not in CLS or L["collision_classes"][CLS[piece]]["pawn"] != "block":
        return False
    if mode == "r5" and piece.startswith(ROUND6):
        return False
    if mode == "br" and (CLS[piece] == "boundary" or piece.startswith(FENCES_1V1)):
        return False
    return True


def hulls(mode):
    """World-space convex hulls: (verts (n, 3) array, edges [(i, j)], piece)."""
    out = []
    for inst in bpy.data.collections["Assembly"].objects:
        piece = inst.name.split("__")[0]
        if piece not in kit or not included(piece, mode):
            continue
        for h in kit[piece].children:
            if not h.name.startswith("UCX_"):
                continue
            mw = inst.matrix_world @ h.matrix_local
            vs = np.array([tuple(mw @ v.co) for v in h.data.vertices])
            es = [tuple(e.vertices) for e in h.data.edges]
            out.append((vs, es, piece))
    return out


# ------------------------------------------------------------------------------------------------ 1. flood
X0, Y0, DX = -1.0, -1.0, 0.1
NX, NY = 460, 380
XS = X0 + DX / 2 + DX * np.arange(NX)
YS = Y0 + DX / 2 + DX * np.arange(NY)
Z0S, DZ, NZ = 0.05, 0.1, 200
ZS = Z0S + DZ * np.arange(NZ)
WIN = 18                                   # slices a capsule needs (1.7 m sampled; the real body is 1.72: conservative)
NB = NZ - WIN + 1                          # capsule bottoms: +0.05 .. +18.25 (top 19.95 under the +20 ceiling)


def hull2d(pts):
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def section(vs, es, z):
    pts = [(v[0], v[1]) for v in vs if abs(v[2] - z) < 1e-9]
    for i, j in es:
        a, b = vs[i], vs[j]
        if (a[2] - z) * (b[2] - z) < 0:
            t = (z - a[2]) / (b[2] - a[2])
            pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return hull2d(pts)


def mark(blk, poly):
    """blk[j, i] |= disc of radius R at the cell centre touches the convex polygon (CCW)."""
    P = np.array(poly)
    xmin, ymin = P.min(0) - R
    xmax, ymax = P.max(0) + R
    i0, i1 = max(0, int((xmin - X0) / DX) - 1), min(NX, int((xmax - X0) / DX) + 2)
    j0, j1 = max(0, int((ymin - Y0) / DX) - 1), min(NY, int((ymax - Y0) / DX) + 2)
    if i0 >= i1 or j0 >= j1:
        return
    gx, gy = np.meshgrid(XS[i0:i1], YS[j0:j1])
    if len(P) == 1:
        d = np.hypot(gx - P[0, 0], gy - P[0, 1])
        blk[j0:j1, i0:i1] |= d < R
        return
    inside = np.ones_like(gx, dtype=bool)
    dmin = np.full(gx.shape, 1e9)
    n = len(P)
    for k in range(n):
        a, b = P[k], P[(k + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        L2 = ex * ex + ey * ey
        if n > 2:
            inside &= (ex * (gy - a[1]) - ey * (gx - a[0])) >= 0
        t = np.clip(((gx - a[0]) * ex + (gy - a[1]) * ey) / max(L2, 1e-12), 0.0, 1.0)
        dmin = np.minimum(dmin, np.hypot(gx - (a[0] + t * ex), gy - (a[1] + t * ey)))
    if n <= 2:
        inside[:] = False
    blk[j0:j1, i0:i1] |= inside | (dmin < R)


def free_slices(H):
    blocked = np.zeros((NZ, NY, NX), dtype=bool)
    for vs, es, _ in H:
        z0, z1 = vs[:, 2].min(), vs[:, 2].max()
        ks = np.nonzero((ZS > z0) & (ZS < z1))[0]
        for k in ks:
            poly = section(vs, es, ZS[k])
            if poly:
                mark(blocked[k], poly)
    return ~blocked


def capsule_free(free):
    c = np.concatenate([np.zeros((1, NY, NX), dtype=np.int32), np.cumsum(~free, axis=0, dtype=np.int32)], axis=0)
    return (c[WIN:WIN + NB] - c[:NB]) == 0


def flood(cap, seed):
    reach = np.zeros_like(cap)
    reach[seed] = cap[seed]
    it = 0
    while True:
        it += 1
        before = int(reach.sum())
        for ax in (2, 1, 0):
            f = np.moveaxis(cap, ax, -1)
            r = np.moveaxis(reach, ax, -1)
            shp = f.shape
            f2 = f.reshape(-1, shp[-1])
            r2 = r.reshape(-1, shp[-1])
            start = f2 & ~np.concatenate([np.zeros((f2.shape[0], 1), dtype=bool), f2[:, :-1]], axis=1)
            ids = np.cumsum(start.ravel()).reshape(f2.shape) * f2
            hit = np.zeros(int(ids.max()) + 1, dtype=bool)
            hit[ids[r2 & f2]] = True
            hit[0] = False
            r2 = hit[ids]
            reach = np.moveaxis(r2.reshape(shp), -1, ax).copy()
        if int(reach.sum()) == before:
            return reach, it


def box_mask(x0, x1, y0, y1, zb0=-1.0):
    m = np.zeros((NB, NY, NX), dtype=bool)
    ii = (XS >= x0) & (XS <= x1)
    jj = (YS >= y0) & (YS <= y1)
    kk = ZS[:NB] >= zb0
    m[np.ix_(kk, jj, ii)] = True
    return m


def mirror(b):
    return (44.0 - b[1], 44.0 - b[0]) + tuple(b[2:])


TARGETS = {}
for sd, f in (("W", lambda b: b), ("E", mirror)):
    TARGETS[f"pocket_{sd}"] = f((7.10, 10.35, 32.35, 35.95, -1.0))
    TARGETS[f"corridor_north_slope_{sd}"] = f((7.15, 10.35, 31.15, 32.30, 2.60))
    TARGETS[f"outbuilding_north_roof_{sd}"] = f((-0.95, 7.00, 31.85, 35.95, 3.00))
TARGETS["strip_behind_the_hall"] = (10.55, 33.45, 34.15, 35.95, -1.0)
TARGETS["hall_upper_rear_half"] = (12.20, 31.80, 29.20, 33.95, 5.40)
TARGETS["north_wall_top"] = (-0.95, 44.95, 36.00, 36.95, 1.95)
SEED = (0, int((10.0 - Y0) / DX), int((22.0 - X0) / DX))   # the courtyard centre, capsule on the sand


def run_flood(mode):
    t0 = time.time()
    H = hulls(mode)
    free = free_slices(H)
    cap = capsule_free(free)
    reach, it = flood(cap, SEED)
    res = {"hulls": len(H), "capsule_cells_free": int(cap.sum()), "reached": int(reach.sum()), "sweeps": it,
           "seconds": round(time.time() - t0, 1), "targets": {}}
    for name, b in TARGETS.items():
        m = box_mask(*b)
        hit = reach & m
        e = {"box": [round(v, 3) for v in b], "free_cells": int((cap & m).sum()), "reached_cells": int(hit.sum())}
        if e["reached_cells"]:
            kk, jj, ii = np.nonzero(hit)
            k = int(np.argmin(kk))
            e["lowest_reached"] = [round(float(XS[ii[k]]), 2), round(float(YS[jj[k]]), 2), round(float(ZS[kk[k]]), 2)]
        res["targets"][name] = e
    res["sealed"] = all(v["reached_cells"] == 0 for v in res["targets"].values())
    # plan of the rear area (X 4..40, Y 26..37): 2 = reached at a ground bottom (<= +0.6), 1 = reached higher only,
    # 0 = free but not reached, 9 = never free
    i0, i1, j0, j1 = int((4.0 - X0) / DX), int((40.0 - X0) / DX), int((26.0 - Y0) / DX), NY
    low = reach[:6, j0:j1, i0:i1].any(0)
    anyr = reach[:, j0:j1, i0:i1].any(0)
    anyf = cap[:, j0:j1, i0:i1].any(0)
    plan = np.where(low, 2, np.where(anyr, 1, np.where(anyf, 0, 9)))
    return res, {"x0": 4.0, "y0": 26.0, "dx": DX, "rows_y_up": ["".join(str(int(c)) for c in row) for row in plan]}


# ------------------------------------------------------------------------------------------------ 2. CONTROL paths
def bvh(mode):
    verts, polys = [], []
    for inst in bpy.data.collections["Assembly"].objects:
        piece = inst.name.split("__")[0]
        if piece not in kit or not included(piece, mode):
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


def capsule_hit(T, c):
    a = HH - R
    n = int(math.ceil(2 * a / 0.05))
    for i in range(n + 1):
        p = c + Vector((0, 0, -a + 2 * a * i / n))
        hit = T.find_nearest(p, R)
        if hit[0] is not None and hit[3] < R - 1e-4:
            return True
    return False


def sweep(T, feet, pts):
    if capsule_hit(T, Vector((pts[0][0], pts[0][1], feet + HH))):
        return {"clear": False, "start_blocked": True}
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.02))
        for i in range(n + 1):
            x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
            if capsule_hit(T, Vector((x, y, feet + HH))):
                return {"clear": False, "blocked_at": [round(x, 2), round(y, 2), round(feet, 2)]}
    return {"clear": True}


def mx(p):
    return (round(44.0 - p[0], 4), p[1])


CONTROLS = {  # name: (feet z, path) for the WEST side; '_E' twins are mirrored about X 22
    "ground_corridor_end_deck_north": (0.52, [(10.45, 31.0), (10.45, 33.5), (9.0, 33.5)]),
    "ground_corridor_floor_end_then_north": (0.52, [(8.0, 31.0), (10.60, 31.0), (10.60, 33.6)]),
    "ground_off_the_veranda_side_edge": (0.52, [(11.6, 33.0), (9.0, 33.0)]),
    "ground_side_yard_up_onto_the_end_deck_and_north": (0.52, [(10.45, 29.3), (10.45, 33.5)]),
    "jump_from_the_veranda_over_the_pocket_fence": (0.9, [(11.6, 33.0), (9.0, 33.0)]),
    "jump_from_the_veranda_over_the_alley_fence": (0.9, [(12.0, 33.2), (12.0, 35.3)]),
    "double_jump_from_the_lower_roof_over_the_pocket_fence": (3.6, [(11.6, 33.0), (9.0, 33.0)]),
    "lower_side_roof_off_the_eave_into_the_pocket": (3.42, [(11.25, 33.0), (9.0, 33.0)]),
    "lower_side_roof_off_its_north_end_into_the_strip": (3.70, [(11.85, 33.2), (11.85, 35.3)]),
    "lower_side_roof_hop_onto_the_corridor_north_slope": (3.95, [(11.25, 31.6), (9.0, 31.6)]),
    "corridor_roof_over_the_ridge_double_jump": (4.2, [(9.0, 30.4), (9.0, 33.6)]),
    "outbuilding_roof_north_past_the_cut": (4.6, [(5.0, 30.5), (5.0, 33.6)]),
    "outbuilding_roof_slot_onto_the_corridor_north_slope": (4.0, [(6.6, 31.35), (8.8, 31.6)]),
    "lower_side_roof_double_jump_onto_the_upper_hip_rear": (6.1, [(11.6, 31.0), (12.6, 31.0)]),
    "upper_roof_over_the_ridge_to_the_rear_eave": (9.5, [(22.0, 28.4), (22.0, 35.3)]),
    "high_flight_over_the_hall": (15.0, [(20.0, 20.0), (20.0, 35.5)]),
    "west_wall_top_round_the_north_west_corner": (2.02, [(-0.5, 26.0), (-0.5, 36.5), (8.5, 36.5), (8.5, 35.0)]),
}
POSITIVES = {  # must stay CLEAR in the 1v1 (beside the new blockers)
    "corridor_floor_outbuilding_end_to_the_veranda": (0.52, [(7.45, 31.0), (12.0, 31.0)]),
    "veranda_side_to_its_rear_end": (0.52, [(12.0, 23.0), (12.0, 33.65)]),
    "lower_side_roof_along_to_its_north_end": (3.56, [(11.6, 30.0), (11.6, 33.65)]),
    "corridor_south_slope_to_the_lower_side_roof": (3.56, [(9.6, 30.4), (11.6, 30.4)]),
    "side_yard_along_the_corridor_front": (0.02, [(8.0, 29.1), (10.6, 29.1)]),
}


def run_paths():
    out = {}
    for mode in ("1v1", "br"):
        T = bvh(mode)
        for sd in ("W", "E"):
            for name, (z, pts) in CONTROLS.items():
                if sd == "E" and name in ("upper_roof_over_the_ridge_to_the_rear_eave", "high_flight_over_the_hall"):
                    continue
                P = pts if sd == "W" else [mx(p) for p in pts]
                out.setdefault(f"CONTROL_{name}_{sd}", {})[mode] = sweep(T, z, P) | {"feet": z, "path": P}
            if mode == "1v1":
                for name, (z, pts) in POSITIVES.items():
                    P = pts if sd == "W" else [mx(p) for p in pts]
                    out[f"POSITIVE_{name}_{sd}"] = {"1v1": sweep(T, z, P) | {"feet": z, "path": P}}
    return out


def main():
    rep = {"date": "2026-09-29", "capsule": {"r": R, "height": BODY}, "grid": {"dx": DX, "dz": DZ, "window": WIN},
           "flood": {}, "plans": {}}
    plans = {}
    for mode in MODES:
        res, plan = run_flood(mode)
        rep["flood"][mode] = res
        plans[mode] = plan
        print("FLOOD", mode, json.dumps({k: v["reached_cells"] for k, v in res["targets"].items()}), "sealed",
              res["sealed"], res["seconds"], "s", flush=True)
    rep["paths"] = run_paths()
    ctl = {k: v for k, v in rep["paths"].items() if k.startswith("CONTROL_")}
    pos = {k: v for k, v in rep["paths"].items() if k.startswith("POSITIVE_")}
    rep["summary"] = {
        "sealed_1v1": rep["flood"].get("1v1", {}).get("sealed"),
        "r5_leaks_reproduced": (not rep["flood"]["r5"]["sealed"]) if "r5" in rep["flood"] else None,
        "br_opens": (not rep["flood"]["br"]["sealed"]) if "br" in rep["flood"] else None,
        "controls_blocked_1v1": sum(1 for v in ctl.values() if not v["1v1"]["clear"]
                                    and not v["1v1"].get("start_blocked")), "controls": len(ctl),
        "controls_invalid_start": sorted(k for k, v in ctl.items() if v["1v1"].get("start_blocked")),
        "controls_open_in_br": sum(1 for v in ctl.values() if v.get("br", {}).get("clear")),
        # a CONTROL whose 1v1 block is the round-6 / 1v1 set (not the buildings): clear in the BR, or blocked there
        # only further along the path
        "controls_blocked_by_the_1v1_set": sorted(k for k, v in ctl.items() if not v["1v1"]["clear"] and (
            v["br"]["clear"] or v["br"].get("blocked_at") != v["1v1"].get("blocked_at"))),
        "positives_clear": sum(1 for v in pos.values() if v["1v1"]["clear"]), "positives": len(pos)}
    rep["passed"] = bool(rep["summary"]["sealed_1v1"] and rep["summary"]["controls_blocked_1v1"] == len(ctl)
                         and rep["summary"]["positives_clear"] == len(pos))
    OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    OUT.with_name(OUT.stem + "_plan.json").write_text(json.dumps(plans), encoding="utf-8")
    print("SEAL", json.dumps(rep["summary"]), "passed", rep["passed"], flush=True)


main()
