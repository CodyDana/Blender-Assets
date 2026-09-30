"""VERIFY r6 (independent verifier): the 1v1 rear seal, measured in the ENGINE on L_Dojo as saved (fresh read-only
pythonscript commandlet, -nullrhi; nothing is saved; the only file written is verify_r6/<DJ_OUT>, default
ue_alley_suite.json). Pawn-profile capsule traces on simple collision; TRV_ markers ignored everywhere (they are
Traversable-only). My own attempts, not the builders' routes:

A. FLOOD (DJ_PARTS contains 'flood'): a FLYING capsule (r 30, hh 86 = GASP CMC) flooded on a 0.1 m plan grid x 0.2 m
   height grid, 6-connected, through X -1.0..45.0, Y 23.0..37.0, capsule bottom +0.02..+18.22 (top below the +20 m
   ceiling), seeded from every free cell on the Y 23.0 plane (the courtyard / veranda front / wall tops / every roof
   front edge / open air: everything south of the rear is taken as reachable, which is GENEROUS). Any jump, double jump,
   mantle, fall or walk is a subset of what it can do. A cell is free when a 0.1 cm capsule sweep there has no blocking
   or start-penetrating hit. Leak = any reached cell inside a rear target box. r 35 is not flooded: its free set is a
   subset of r 30's, so an r 30 seal implies an r 35 seal. Mode '1v1' = everything; mode 'br' = the actors tagged
   'Dojo/Boundary_1v1' also ignored, local (X 4..40, Y 28..37, bottoms +0.02..+6.02, seeded on Y 28.0) - it must OPEN
   the targets (the group is separable and it is what seals).
B. ATTEMPTS (DJ_PARTS contains 'walk'): floor-following walks (step-up 45 cm by a Pawn line trace, as the in-engine walk
   gate) and fixed-height 'fly' sweeps (feet at standing, single-jump 1.28, double-jump ~2.6 and higher), both sides,
   r 30 and r 35, modes 1v1 and br: from the ground (side yard, corridor floor and end deck, veranda side and rear end),
   from fence tops, corridor roofs, the hall's lower side roofs, the upper roof, outbuilding roofs, the wall tops, and
   high flights. 1v1: every attempt must be blocked before it enters a target (or cannot start: start blocked).
C. MANTLE REPLAYS (DJ_PARTS contains 'mantle'): every TRV marker ledge, sampled every 0.5 m (30 cm from the ends):
   stance = ledge + outward normal x 0.55 m on the floor below it; GASP rule: the forward capsule trace (r 30, hh 60,
   Traversable channel) must hit the marker, height 0.26..2.75 m, stance free; landing = capsule on the top 0.35 m
   inside the ledge, free. A mantle whose stance is outside every target and whose landing is inside one is a leak.
D. GROUP (always): the tagged group (labels, meshes, folders, hidden, collision) listed for the report.
"""
import json
import math
import os
import time
from array import array
from collections import deque
from pathlib import Path

import unreal

VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r6")
V = unreal.Vector
PARTS = os.environ.get("DJ_PARTS", "flood,walk,mantle").split(",")
OUT = VD / os.environ.get("DJ_OUT", "ue_alley_suite.json")
TAG = "Dojo/Boundary_1v1"
HH = 86.0
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
ACTS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
CTX = ACTS[0]
TRV = [a for a in ACTS if a.get_actor_label().startswith("TRV_")]
GROUP = [a for a in ACTS if any(str(t) == TAG for t in a.get_editor_property("tags"))]
RING = [a for a in ACTS if a.get_actor_label().startswith("SM_DGB_Boundary_1v1")]
IGN = {"1v1": TRV, "br": TRV + GROUP, "noring": TRV + RING}
NT = [0]


def mirror_box(b):
    return (round(44.0 - b[1], 3), round(44.0 - b[0], 3)) + tuple(b[2:])


# rear targets (x0, x1, y0, y1, lowest capsule bottom): spec 4.6 / 5.2 / 5.4 - the strip behind the hall, both
# pockets behind the corridors, the corridors' north slopes, the outbuildings' north roof halves, the upper roof's rear
# half, the north wall top
TARGETS = {}
for sd, f in (("W", lambda b: b), ("E", mirror_box)):
    TARGETS[f"pocket_{sd}"] = f((7.15, 10.35, 32.40, 35.95, -1.0))
    TARGETS[f"corridor_north_slope_{sd}"] = f((7.20, 10.30, 31.20, 32.30, 2.60))
    TARGETS[f"outbuilding_north_roof_{sd}"] = f((-0.95, 6.95, 31.90, 35.95, 3.00))
TARGETS["strip_behind_the_hall"] = (10.55, 33.45, 34.20, 35.95, -1.0)
TARGETS["hall_upper_rear_half"] = (12.20, 31.80, 29.25, 33.95, 5.40)
TARGETS["north_wall_top"] = (-0.95, 44.95, 36.05, 36.95, 1.90)


def in_target(x, y, zb):
    for k, (x0, x1, y0, y1, z0) in TARGETS.items():
        if x0 <= x <= x1 and y0 <= y <= y1 and zb >= z0:
            return k
    return None


def hit(h):
    t = h.to_tuple() if h else None
    if not t or not (t[0] or t[1]):
        return None
    return {"start_pen": bool(t[1]), "impact_bl_m": [round(t[5].x / 100, 3), round(-t[5].y / 100, 3), round(t[5].z / 100, 3)],
            "actor": t[9].get_actor_label() if t[9] else None}


def cap_free(x, y, zc, r, ign, hh=HH):
    NT[0] += 1
    h = unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, V(x * 100, -y * 100, zc), V(x * 100 + 0.1, -y * 100, zc),
                                                             r, hh, "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    return not (t and (t[0] or t[1]))


def floor_below(x, y, z_from, ign, depth=167.0):
    h = hit(unreal.SystemLibrary.line_trace_single_by_profile(CTX, V(x * 100, -y * 100, z_from), V(x * 100, -y * 100, z_from - depth),
                                                              "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True))
    return h


# ------------------------------------------------------------------------------------------------ A. flood
def flood(mode, x0, x1, y0, y1, zb0, zb1, dx=0.1, dz=0.2, r=30.0):
    t0 = time.time()
    ign = IGN[mode]
    nx, ny, nz = int(round((x1 - x0) / dx)) + 1, int(round((y1 - y0) / dx)) + 1, int(round((zb1 - zb0) / dz)) + 1
    N = nx * ny * nz
    st = bytearray(N)          # 0 unknown, 1 free, 2 blocked
    seen = bytearray(N)
    parent = array("i", [-1]) * N

    def idx(i, j, k):
        return (k * ny + j) * nx + i

    def xyz(n):
        k, rem = divmod(n, nx * ny)
        j, i = divmod(rem, nx)
        return x0 + i * dx, y0 + j * dx, zb0 + k * dz

    def free(n):
        s = st[n]
        if s == 0:
            x, y, zb = xyz(n)
            s = 1 if cap_free(x, y, zb * 100 + HH, r, ign) else 2
            st[n] = s
        return s == 1

    q = deque()
    n_seed = 0
    for k in range(nz):
        for i in range(nx):
            n = idx(i, 0, k)
            if free(n):
                seen[n] = 1
                q.append(n)
                n_seed += 1
    reached = 0
    tgt = {k: {"box": list(v), "reached_cells": 0, "first": None} for k, v in TARGETS.items()}
    first_leak = None
    last = time.time()
    while q:
        n = q.popleft()
        reached += 1
        x, y, zb = xyz(n)
        tk = in_target(x, y, zb)
        if tk:
            tg = tgt[tk]
            tg["reached_cells"] += 1
            if tg["first"] is None:
                path, m = [], n
                while m != -1 and len(path) < 4000:
                    path.append([round(v, 2) for v in xyz(m)])
                    m = parent[m]
                tg["first"] = {"cell_bl_m": [round(x, 2), round(y, 2), round(zb, 2)], "path_back_every_10": path[::10]}
                if first_leak is None:
                    first_leak = tk
        k, rem = divmod(n, nx * ny)
        j, i = divmod(rem, nx)
        for (a, b, c) in ((i + 1, j, k), (i - 1, j, k), (i, j + 1, k), (i, j - 1, k), (i, j, k + 1), (i, j, k - 1)):
            if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz:
                m = (c * ny + b) * nx + a
                if not seen[m] and free(m):
                    seen[m] = 1
                    parent[m] = n
                    q.append(m)
        if time.time() - last > 30:
            last = time.time()
            unreal.log(f"V6_FLOOD {mode} reached {reached} queue {len(q)} traces {NT[0]} {round(last - t0)} s")
    # plan: per (i, j) 2 = reached with a bottom <= +0.62, 1 = reached higher only, 0 = free somewhere, never reached,
    # 9 = never free (or never tested)
    plan = []
    for j in range(ny):
        row = []
        for i in range(nx):
            low = anyr = anyf = False
            for k in range(nz):
                n = idx(i, j, k)
                if seen[n]:
                    anyr = True
                    if zb0 + k * dz <= 0.62:
                        low = True
                if st[n] == 1:
                    anyf = True
            row.append("2" if low else "1" if anyr else "0" if anyf else "9")
        plan.append("".join(row))
    return {"mode": mode, "region": {"x": [x0, x1], "y": [y0, y1], "capsule_bottom": [zb0, zb1], "dx": dx, "dz": dz, "r_cm": r,
                                     "hh_cm": HH, "cells": N},
            "seed_cells": n_seed, "reached": reached, "tested": sum(1 for s in st if s), "free": sum(1 for s in st if s == 1),
            "targets": tgt, "leaks": sorted(k for k, v in tgt.items() if v["reached_cells"]),
            "sec": round(time.time() - t0, 1), "plan_rows_y_up": plan, "plan_x0": x0, "plan_y0": y0, "plan_dx": dx}


# ------------------------------------------------------------------------------------------------ B. attempts
def start_hit(x, y, zc, r, ign, hh=HH):
    return hit(unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, V(x * 100, -y * 100, zc), V(x * 100 + 0.1, -y * 100, zc),
                                                                     r, hh, "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True))


def walk(pts, floor_z, ign, r):
    """floor-following Pawn capsule sweep, as the in-engine walk gate: body band floor+47..+172 (centre floor+109.5, hh
    62.5; below it the CMC steps up <= 45 cm and slides on slopes), floor = Pawn line trace down from floor+47 at every
    5 cm sample. Stops at the first blocking hit; records whether the capsule ENTERED a target before (a leak)."""
    floor = floor_z * 100
    prev, entered = None, None
    sh = start_hit(pts[0][0], pts[0][1], floor + 109.5, r, ign, 62.5)
    if sh:
        return {"clear": False, "start_blocked": True, "start_block": sh, "entered": None}
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(xb - xa, yb - ya) / 0.05))
        for s in range(n + 1):
            x, y = xa + (xb - xa) * s / n, ya + (yb - ya) * s / n
            f = floor_below(x, y, floor + 47, ign)
            if f and not f["start_pen"]:
                floor = f["impact_bl_m"][2] * 100
            c = V(x * 100, -y * 100, floor + 109.5)
            if prev is not None:
                NT[0] += 1
                h = hit(unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, prev, c, r, 62.5, "Pawn", False, ign,
                                                                             unreal.DrawDebugTrace.NONE, True))
                if h:
                    return {"clear": False, "at_bl_m": [round(x, 2), round(y, 2), round(floor / 100, 3)], **h, "entered": entered}
            tk = in_target(x, y, floor / 100)
            if tk and entered is None:
                entered = {"target": tk, "at_bl_m": [round(x, 2), round(y, 2), round(floor / 100, 3)]}
            prev = c
    return {"clear": True, "end_floor_m": round(floor / 100, 3), "entered": entered}


def fly(pts, feet_z, ign, r):
    zc = feet_z * 100 + HH + 2
    sh = start_hit(pts[0][0], pts[0][1], zc, r, ign)
    lifted = 0.0
    while sh and lifted < 0.6:        # a start inside something: lift the start up to 60 cm (a jump from there)
        lifted += 0.05
        zc += 5.0
        sh2 = start_hit(pts[0][0], pts[0][1], zc, r, ign)
        if not sh2:
            sh = None
            break
    if sh:
        return {"clear": False, "start_blocked": True, "start_block": sh, "entered": None}
    feet_z += lifted
    entered = None
    prev = None
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(xb - xa, yb - ya) / 0.05))
        for s in range(n + 1):
            x, y = xa + (xb - xa) * s / n, ya + (yb - ya) * s / n
            c = V(x * 100, -y * 100, zc)
            if prev is not None:
                NT[0] += 1
                h = hit(unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, prev, c, r, HH, "Pawn", False, ign,
                                                                             unreal.DrawDebugTrace.NONE, True))
                if h:
                    return {"clear": False, "at_bl_m": [round(x, 2), round(y, 2), round(feet_z, 2)], **h, "entered": entered,
                            "lifted_m": round(lifted, 2)}
            tk = in_target(x, y, feet_z + 0.02)
            if tk and entered is None:
                entered = {"target": tk, "at_bl_m": [round(x, 2), round(y, 2), round(feet_z, 2)]}
            prev = c
    return {"clear": True, "entered": entered, "lifted_m": round(lifted, 2)}


def top_surface(x, y, ign, z_from=19.0, z_to=-1.0):
    h = hit(unreal.SystemLibrary.line_trace_single_by_profile(CTX, V(x * 100, -y * 100, z_from * 100), V(x * 100, -y * 100, z_to * 100),
                                                              "Pawn", False, ign, unreal.DrawDebugTrace.NONE, True))
    return h["impact_bl_m"][2] if h else None


# name: (kind, start: float floor/feet z | 'top' (the highest Pawn surface at the first point) | ('top+', dz), points W side)
ATTEMPTS = {
    # ground
    "ground_side_yard_north_through_the_corridor_mid": ("walk", 0.0, [(8.6, 28.6), (8.6, 35.6)]),
    "ground_side_yard_north_at_the_corridor_end": ("walk", 0.0, [(10.3, 28.6), (10.3, 35.6)]),
    "ground_side_yard_under_the_veranda_edge_north": ("walk", 0.0, [(10.75, 28.6), (10.75, 35.6)]),
    "ground_courtyard_along_the_veranda_side_to_the_strip": ("walk", 0.0, [(10.75, 21.0), (10.75, 35.0), (22.0, 35.0)]),
    "corridor_floor_to_the_end_then_north": ("walk", 0.5, [(7.6, 31.0), (10.62, 31.0), (10.62, 35.6)]),
    "corridor_floor_north_edge_along": ("walk", 0.5, [(7.6, 31.9), (10.62, 31.9), (10.62, 35.6)]),
    "corridor_end_deck_north_then_west": ("walk", 0.5, [(10.45, 31.0), (10.45, 33.6), (8.4, 33.6), (8.4, 35.6)]),
    "veranda_side_to_its_rear_end_then_west": ("walk", 0.5, [(11.6, 28.0), (11.6, 33.85), (8.0, 33.85)]),
    "veranda_side_rear_end_north_into_the_strip": ("walk", 0.5, [(12.0, 30.0), (12.0, 35.6), (22.0, 35.3)]),
    "veranda_side_rear_end_diagonal_nw": ("walk", 0.5, [(11.8, 33.2), (9.5, 35.5)]),
    "ground_west_wall_foot_north": ("walk", 0.0, [(0.4, 24.0), (0.4, 35.6)]),
    "ground_side_yard_along_the_storehouse_east_wall": ("walk", 0.0, [(7.4, 26.0), (7.4, 35.6)]),
    # jumps / double jumps from the ground and the veranda (fixed feet)
    "jump_side_yard_over_the_corridor": ("fly", 1.28, [(8.6, 28.6), (8.6, 35.6)]),
    "double_jump_side_yard_over_the_corridor": ("fly", 2.6, [(8.6, 28.6), (8.6, 35.6)]),
    "jump_veranda_over_the_pocket_fence": ("fly", 1.8, [(11.6, 33.0), (8.4, 33.0)]),
    "double_jump_veranda_over_the_pocket_fence": ("fly", 3.1, [(11.6, 33.0), (8.4, 33.0)]),
    "jump_veranda_over_the_alley_fence": ("fly", 1.8, [(12.0, 33.2), (12.0, 35.6)]),
    "double_jump_veranda_over_the_alley_fence": ("fly", 3.1, [(12.0, 33.2), (12.0, 35.6)]),
    # fence tops (a double jump could land on them)
    "on_the_pocket_fence_top_into_the_pocket": ("fly", 2.02, [(10.55, 33.0), (8.4, 33.0)]),
    "on_the_pocket_fence_top_north_along": ("fly", 2.02, [(10.55, 32.6), (10.55, 35.6)]),
    "on_the_alley_fence_top_into_the_strip": ("fly", 2.02, [(11.5, 34.05), (11.5, 35.6)]),
    "on_the_alley_fence_top_west_into_the_pocket": ("fly", 2.02, [(11.5, 34.05), (8.4, 34.05)]),
    # corridor roofs
    "corridor_roof_south_slope_walk_over_the_ridge": ("walk", ("top",), [(9.0, 30.0), (9.0, 33.6)]),
    "corridor_roof_ridge_hop_north": ("fly", 3.9, [(9.0, 30.6), (9.0, 33.6)]),
    "corridor_roof_ridge_double_jump_north": ("fly", 5.2, [(9.0, 30.6), (9.0, 33.6)]),
    "corridor_roof_east_end_into_the_pocket": ("fly", 3.6, [(10.2, 30.6), (10.2, 33.6)]),
    # the hall's lower side roof
    "lower_side_roof_walk_to_its_north_end_and_on": ("walk", ("top",), [(11.6, 29.0), (11.6, 35.6)]),
    "lower_side_roof_walk_west_off_the_eave": ("walk", ("top",), [(11.7, 33.0), (8.4, 33.0)]),
    "lower_side_roof_hop_west_into_the_pocket": ("fly", 3.7, [(11.5, 33.0), (8.4, 33.0)]),
    "lower_side_roof_double_jump_west": ("fly", 5.0, [(11.5, 32.0), (8.4, 32.0)]),
    "lower_side_roof_hop_north_into_the_strip": ("fly", 3.8, [(11.9, 33.2), (11.9, 35.6)]),
    "lower_side_roof_double_jump_onto_the_upper_hip_rear": ("fly", 6.1, [(11.6, 31.5), (13.5, 31.5)]),
    "lower_side_roof_double_jump_north_high": ("fly", 5.8, [(11.9, 32.0), (11.9, 35.6)]),
    # the hall's upper roof (front slope is legal up to the ridge)
    "upper_roof_front_slope_walk_over_the_ridge": ("walk", ("top",), [(22.0, 26.5), (22.0, 35.6)]),
    "upper_roof_front_slope_walk_over_the_ridge_off_centre": ("walk", ("top",), [(14.0, 26.5), (14.0, 35.6)]),
    "upper_roof_ridge_jump_north": ("fly", 9.0, [(22.0, 28.4), (22.0, 35.6)]),
    "upper_roof_hip_walk_round_the_west_end": ("walk", ("top",), [(12.8, 26.5), (12.8, 33.5)]),
    "upper_roof_ridge_double_jump_north": ("fly", 10.5, [(18.0, 28.4), (18.0, 35.6)]),
    # outbuilding roofs (south halves legal)
    "outbuilding_roof_walk_north_over_the_cut": ("walk", ("top",), [(3.5, 29.5), (3.5, 35.6)]),
    "outbuilding_roof_walk_north_near_the_corridor": ("walk", ("top",), [(6.5, 29.5), (6.5, 35.6)]),
    "outbuilding_roof_jump_north": ("fly", 5.3, [(3.5, 30.5), (3.5, 35.6)]),
    "outbuilding_roof_east_onto_the_corridor_north_slope": ("fly", 4.1, [(6.4, 31.4), (9.0, 31.7)]),
    # wall tops
    "west_wall_top_north_round_the_corner": ("walk", 2.0, [(-0.5, 26.0), (-0.5, 36.5), (9.0, 36.5), (9.0, 35.2)]),
    "west_wall_top_north_end_jump_east": ("fly", 3.3, [(-0.5, 30.0), (-0.5, 35.6), (5.0, 35.6)]),
    "west_wall_top_off_east_into_the_rear": ("fly", 2.02, [(-0.5, 33.0), (6.0, 33.0)]),
    # high flights (the +20 ceiling above)
    "flight_over_the_hall_at_9_5": ("fly", 9.5, [(20.0, 20.0), (20.0, 35.6)]),
    "flight_over_the_hall_at_15": ("fly", 15.0, [(20.0, 20.0), (20.0, 35.6)]),
    "flight_over_the_hall_at_18": ("fly", 18.0, [(24.0, 20.0), (24.0, 35.6)]),
    "flight_over_the_corridor_at_7": ("fly", 7.0, [(9.0, 24.0), (9.0, 35.6)]),
    "flight_over_the_outbuilding_at_8": ("fly", 8.0, [(3.0, 24.0), (3.0, 35.6)]),
}
CENTRE_ONLY = {"flight_over_the_hall_at_9_5", "flight_over_the_hall_at_15", "flight_over_the_hall_at_18",
               "upper_roof_front_slope_walk_over_the_ridge", "upper_roof_ridge_jump_north", "upper_roof_ridge_double_jump_north"}


def mirror_pt(p):
    return (round(44.0 - p[0], 4), p[1])


def run_attempts():
    out = {}
    for mode in ("1v1", "br"):
        ign = IGN[mode]
        for r in (30.0, 35.0):
            for name, (kind, z, pts) in ATTEMPTS.items():
                for sd in ("W", "E"):
                    if sd == "E" and name in CENTRE_ONLY:
                        continue
                    P = pts if sd == "W" else [mirror_pt(p) for p in pts]
                    if isinstance(z, tuple):
                        zz = top_surface(P[0][0], P[0][1], IGN["1v1"])
                        if zz is None:
                            out.setdefault(f"{name}_{sd}", {})[f"{mode}_r{int(r)}"] = {"error": "no start surface"}
                            continue
                    else:
                        zz = z
                    res = walk(P, zz, ign, r) if kind == "walk" else fly(P, zz, ign, r)
                    res.update({"kind": kind, "start_z_m": round(zz, 3), "path": P})
                    out.setdefault(f"{name}_{sd}", {})[f"{mode}_r{int(r)}"] = res
    leaks = sorted(k for k, v in out.items() for m, rr in v.items() if m.startswith("1v1") and rr.get("entered"))
    br_open = sorted(k for k, v in out.items() if (v.get("br_r30") or {}).get("entered"))
    return {"attempts": out, "n_attempts": len(out), "leaks_1v1": leaks, "opened_in_br_r30": br_open,
            "passed": not leaks}


# ------------------------------------------------------------------------------------------------ C. mantle replays
def trv_boxes():
    L = json.loads((Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\showcase\layout_showcase.json")).read_text(encoding="utf-8"))
    return {m["name"]: m["box"] for m in L["traversal_markers"]}


def run_mantles():
    tq = next(getattr(unreal.TraceTypeQuery, n) for n in dir(unreal.TraceTypeQuery) if n.upper() == "ECC_TRAVERSABLE")
    by = {a.get_actor_label(): a for a in TRV}
    rows, leaks = [], []
    for name, (x0, x1, y0, y1, z0, z1) in trv_boxes().items():
        ledges = {"N": ((x0, y1), (x1, y1), (0, 1)), "S": ((x0, y0), (x1, y0), (0, -1)),
                  "W": ((x0, y0), (x0, y1), (-1, 0)), "E": ((x1, y0), (x1, y1), (1, 0))}
        for lk, ((ax, ay), (bx, by_), (nx, ny)) in ledges.items():
            ln = math.hypot(bx - ax, by_ - ay)
            if ln < 0.6:
                continue
            ns = max(1, int((ln - 0.6) / 0.5))
            for s in range(ns + 1):
                t = (0.3 + (ln - 0.6) * s / ns) / ln
                px, py = ax + (bx - ax) * t, ay + (by_ - ay) * t
                sx, sy = px + nx * 0.55, py + ny * 0.55
                f = floor_below(sx, sy, z1 * 100 - 26, IGN["1v1"], depth=400.0)
                if not f or f["start_pen"]:
                    continue
                fz = f["impact_bl_m"][2]
                h = z1 - fz
                row = {"marker": name, "ledge": lk, "at": [round(px, 2), round(py, 2)], "stance": [round(sx, 2), round(sy, 2), round(fz, 3)],
                       "height_m": round(h, 3)}
                if not (0.26 < h <= 2.75):
                    row["result"] = "height out of range"
                    rows.append(row)
                    continue
                if not cap_free(sx, sy, fz * 100 + HH + 2, 30.0, IGN["1v1"]):
                    row["result"] = "stance blocked"
                    rows.append(row)
                    continue
                zc = fz * 100 + HH + 1.9
                ht = hit(unreal.SystemLibrary.capsule_trace_single(CTX, V(sx * 100, -sy * 100, zc), V(sx * 100 - nx * 75, -sy * 100 + ny * 75, zc),
                                                                   30.0, 60.0, tq, False, [], unreal.DrawDebugTrace.NONE, True))
                if not ht or ht["actor"] != "TRV_" + name:
                    row["result"] = f"forward trace misses the marker ({ht['actor'] if ht else None})"
                    rows.append(row)
                    continue
                lx, ly = px - nx * 0.35, py - ny * 0.35
                land_free = cap_free(lx, ly, z1 * 100 + HH + 2, 30.0, IGN["1v1"])
                row.update({"landing": [round(lx, 2), round(ly, 2), z1], "landing_free": land_free,
                            "stance_target": in_target(sx, sy, fz), "landing_target": in_target(lx, ly, z1)})
                row["result"] = "mantle"
                if land_free and row["landing_target"] and not row["stance_target"]:
                    leaks.append(row)
                rows.append(row)
    mant = [r for r in rows if r["result"] == "mantle"]
    return {"n_samples": len(rows), "n_mantles": len(mant), "n_landing_free": sum(1 for r in mant if r["landing_free"]),
            "landings_in_targets": [r for r in mant if r["landing_free"] and r["landing_target"]],
            "stances_in_targets": [r for r in mant if r["stance_target"]],
            "leaks": leaks, "rows": rows, "passed": not leaks}


# ------------------------------------------------------------------------------------------------ D. group
def group_info():
    rows = []
    for a in GROUP:
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        sm = smc.get_editor_property("static_mesh") if smc else None
        rows.append({"label": a.get_actor_label(), "mesh": sm.get_name() if sm else None, "folder": str(a.get_folder_path()),
                     "hidden_in_game": bool(a.get_editor_property("hidden")),
                     "tags": [str(t) for t in a.get_editor_property("tags")]})
    return {"n": len(rows), "actors": sorted(rows, key=lambda r: r["label"])}


def main():
    t0 = time.time()
    rep = {"verifier": "independent r6", "parts": PARTS, "targets": {k: list(v) for k, v in TARGETS.items()},
           "n_trv_ignored": len(TRV), "group": group_info(), "ring_actors": [a.get_actor_label() for a in RING]}
    try:
        if "walk" in PARTS:
            rep["B_attempts"] = run_attempts()
        if "mantle" in PARTS:
            rep["C_mantles"] = run_mantles()
        if "flood" in PARTS:
            rep["A_flood_1v1"] = flood("1v1", -1.0, 45.0, 23.0, 37.0, 0.02, 18.22)
        if "floodbr" in PARTS:
            rep["A_flood_br"] = flood("br", 4.0, 40.0, 28.0, 37.0, 0.02, 6.02)
        if "flood35" in PARTS:    # r 35 (the spec capsule), same region
            rep["A_flood_1v1_r35"] = flood("1v1", -1.0, 45.0, 23.0, 37.0, 0.02, 18.22, r=35.0)
        if "floodfine" in PARTS:  # r 30 on a 0.1 m height grid, below +8.02 (every roof edge and eave)
            rep["A_flood_1v1_dz01"] = flood("1v1", -1.0, 45.0, 23.0, 37.0, 0.02, 8.02, dz=0.1)
        if "floodnoring" in PARTS:  # the grey-box ring ignored too: does the round-6 set seal on its own (inside X -1..45,
            # Y <= 37, below +20)?
            rep["A_flood_noring"] = flood("noring", -1.0, 45.0, 23.0, 37.0, 0.02, 18.22)
    except Exception:  # noqa: BLE001
        import traceback
        rep["error"] = traceback.format_exc()[-4000:]
    rep["traces"] = NT[0]
    rep["sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    unreal.log(f"V6_ALLEY_DONE parts={PARTS} sec={rep['sec']} traces={NT[0]} error={'error' in rep}")


main()
