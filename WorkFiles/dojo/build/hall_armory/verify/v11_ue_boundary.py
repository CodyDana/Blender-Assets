# HALL + ARMORY VERIFIER (independent): the landscape verifier's v10 boundary script for the extended hall: the ring's
# north side at y 48.1 (FBX audit: local 0..49.2 at -1.1), the B-polygon's north edge at y 56 (world_layout_delta B6),
# the layout's 88 walk routes with MY walker v2 (CMC order: move flat first, step up only when blocked, the lift clamped
# under a ceiling such as the door head), MY interior walking flood (courtyard -> step band -> veranda -> doors ->
# interior), BR / 1v1 walks over the new rear roof, the stair after the lantern move, flood1v1 / floodbr / arcs1v1.
"""VERIFY LANDSCAPE ROUND (independent verifier): the 1v1 boundary on the terrace, its separability, and the stair path,
with MY OWN capsule attempts (not the builder's B-line CONTROLs or its L5 stair walk). A fresh read-only pythonscript
commandlet (-nullrhi) on L_Dojo as saved; nothing is saved; the only file written is landscape/verify/<DJ_OUT>.

Frame: Blender metres (x east, y north, z up; courtyard 0); UE cm = (x*100, -y*100, z*100). Capsule = GASP r 30 (and
35), half height 86. Pawn profile sweeps on simple collision; TRV_ markers always ignored (Traversable only).
Modes: 1v1 = everything; bonly = the old grey-box ring SM_DGB_Boundary_1v1 ignored too (the new terrace B-lines and
the rest of the group kept: do the terrace blockers hold on their own?); br = the whole 'Dojo/Boundary_1v1' group
ignored (must open the terrace: separable).

Parts (DJ_PARTS):
  height   : the highest standable surface inside the ring footprint (walkable hit nz >= 0.70 and the capsule fits),
             every layer per 0.25 m column -> the flood ceiling = that + 2.55 m (double-jump apex) + 0.30 m.
  flood1v1 : a FLYING capsule (a superset of every walk / jump / fall / mantle) flooded 6-connected on a 0.25 m lattice
             (offset from every earlier lattice: x0 -13.93, y0 -15.93, bottom -2.91) from the free cells around the two
             player starts; LEAK = any reached cell whose centre is outside the ring footprint (x -1.1..45.1,
             y -1.1..37.1) or outside the terrace B-polygon.
  floodbr  : the same at 0.5 m with the group ignored, over y down to -42 (the stair foot): must reach outside.
  arcs1v1  : walk / jump / double / double-late arcs (300 / 450 / 650 cm/s, 24 headings, 30 Hz sweeps, slide on walls,
             land on walkable floors, 3 s) from every standable surface (0.4 m grid) inside the ring within 4 m of its
             edge or 3 m+ high; LEAK = capsule centre outside the ring footprint.
  arcsB    : mode bonly, from every standable surface within 8 m of a B-line (0.5 m grid, 16 headings, 450 / 650);
             LEAK = capsule centre outside the B-polygon. Information (the 1v1 runs with the ring).
  stair    : my own GASP walker down and up the cliff stair path (gate apron -> L7) on 3 lanes (centre, +-0.30 m) at
             r 30 and r 35, mode br: per 5 cm sample a Pawn line trace finds the floor (rise <= 45 cm, drop <= 45 cm,
             floor nz >= 0.71 = UE's 44.77 deg), then the full capsule must fit there and sweep clear from the last
             sample. The same centre lane in mode 1v1 must be BLOCKED (a control).
"""
import json
import math
import os
import time
from array import array
from collections import deque
from pathlib import Path

import unreal

VD = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/verify/json")
V = unreal.Vector
PARTS = os.environ.get("DJ_PARTS", "height,routes,stair,flood1v1,floodbr,arcs1v1,arcsB").split(",")
OUT = VD / os.environ.get("DJ_OUT", "ue_boundary.json")
TAG = "Dojo/Boundary_1v1"
HH = 86.0
G = 980.0
JZ = 500.0
DT = 1.0 / 30.0

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Dojo/Maps/L_Dojo")
ACTS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
CTX = ACTS[0]
TRV = [a for a in ACTS if a.get_actor_label().startswith("TRV_")]
GROUP = [a for a in ACTS if any(str(t) == TAG for t in a.get_editor_property("tags"))]
RING = [a for a in ACTS if a.get_actor_label().startswith("SM_DGB_Boundary_1v1")]
BL = [a for a in ACTS if a.get_actor_label().startswith("Boundary1v1_B")]
IGN = {"1v1": TRV, "bonly": TRV + RING, "br": TRV + GROUP}
NT = [0]
RINGF = (-1.1, 45.1, -1.1, 48.1)
GROUP_LABELS = {a.get_actor_label() for a in GROUP}   # tops of the boundary group are never launch surfaces (the floods
SURF_ZMAX = [99.0]                                      # never reach them); arcs also cap launch z at the flood ceiling


def in_ring(x, y):
    return RINGF[0] < x < RINGF[1] and RINGF[2] < y < RINGF[3]


def in_bpoly(x, y):
    return (-7.0 < x < 48.75 and -2.75 < y < 56.0) or (12.2 < x < 34.25 and -7.75 < y <= -2.75)


def bdist(x, y):
    """distance from a point inside the B-polygon to its boundary (approx: min over the 8 segments)."""
    segs = [((-7, -2.75), (-7, 56)), ((-7, 56), (48.75, 56)), ((48.75, 56), (48.75, -2.75)), ((48.75, -2.75), (34.25, -2.75)),
            ((34.25, -2.75), (34.25, -7.75)), ((34.25, -7.75), (12.2, -7.75)), ((12.2, -7.75), (12.2, -2.75)), ((12.2, -2.75), (-7, -2.75))]
    best = 1e9
    for (ax, ay), (bx, by) in segs:
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def ht(h):
    t = h.to_tuple() if h else None
    if not t or not (t[0] or t[1]):
        return None
    return {"start_pen": bool(t[1]), "time": float(t[2]), "loc": t[4], "imp": t[5], "n": t[7] if len(t) > 7 else None,
            "actor": t[9].get_actor_label() if t[9] else None}


def cap_sweep(a, b, r, ign, hh=HH):
    NT[0] += 1
    return ht(unreal.SystemLibrary.capsule_trace_single_by_profile(CTX, a, b, r, hh, "Pawn", False, ign,
                                                                   unreal.DrawDebugTrace.NONE, True))


def cap_free_at(x, y, zf, r, ign, hh=HH):
    c = V(x * 100, -y * 100, zf * 100 + hh + 1.0)
    return cap_sweep(c, V(c.x + 0.1, c.y, c.z), r, ign, hh) is None


def line_down(x, y, z_from_m, depth_m, ign):
    NT[0] += 1
    return ht(unreal.SystemLibrary.line_trace_single_by_profile(CTX, V(x * 100, -y * 100, z_from_m * 100),
                                                                V(x * 100, -y * 100, (z_from_m - depth_m) * 100), "Pawn", False,
                                                                ign, unreal.DrawDebugTrace.NONE, True))


def nz(h):
    n = h["n"]
    return n.z if n is not None else 1.0


def surfaces(xr, yr, grid, ign, keep, ztop=26.0, zmin=-9.0):
    pts = []
    y = yr[0]
    while y <= yr[1] + 1e-6:
        x = xr[0]
        while x <= xr[1] + 1e-6:
            z = ztop
            for _ in range(10):
                h = line_down(x, y, z, z - zmin + 1.0, ign)
                if not h or h["start_pen"]:
                    break
                zf = h["imp"].z / 100
                if nz(h) >= 0.70 and keep(x, y, zf) and h["actor"] not in GROUP_LABELS and zf <= SURF_ZMAX[0]:
                    pts.append((round(x, 2), round(y, 2), round(zf, 3)))
                z = zf - 0.05
                if z < zmin:
                    break
            x += grid
        y += grid
    return pts


# ------------------------------------------------------------------------------------------------ height
def run_height():
    t0 = time.time()
    # the group (ring, fences, invisible blockers, B-lines) is ignored here: their tops are not places a player can stand
    pts = surfaces((-1.0, 45.0), (-1.0, 48.0), 0.25, IGN["br"], lambda x, y, z: in_ring(x, y))
    fit = []
    for p in sorted(pts, key=lambda p: -p[2]):
        if cap_free_at(p[0], p[1], p[2] + 0.03, 30.0, IGN["br"]):
            fit.append(p)
            if len(fit) >= 20:
                break
    top = fit[0][2] if fit else None
    return {"n_surfaces": len(pts), "highest_standable": fit[:20], "max_standable_z_m": top,
            "ceiling_bottom_m": round(top + 2.55 + 0.30, 2) if top is not None else None, "sec": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------ flood
def flood(mode, r, x0, x1, y0, y1, zb0, zb1, dx, dz, seeds_xy, leak_fn):
    t0 = time.time()
    ign = IGN[mode]
    nx, ny, nzc = int(round((x1 - x0) / dx)) + 1, int(round((y1 - y0) / dx)) + 1, int(round((zb1 - zb0) / dz)) + 1
    N = nx * ny * nzc
    st = bytearray(N)
    seen = bytearray(N)
    parent = array("i", [-1]) * N

    def xyz(n):
        k, rem = divmod(n, nx * ny)
        j, i = divmod(rem, nx)
        return x0 + i * dx, y0 + j * dx, zb0 + k * dz

    def free(n):
        s = st[n]
        if s == 0:
            x, y, zb = xyz(n)
            s = 1 if cap_free_at(x, y, zb - 0.01, r, ign) else 2
            st[n] = s
        return s == 1

    q = deque()
    for (sx, sy) in seeds_xy:
        for k in range(nzc):
            zb = zb0 + k * dz
            if not (0.0 <= zb <= 0.8):
                continue
            for j in range(max(0, int((sy - 1.0 - y0) / dx)), min(ny, int((sy + 1.0 - y0) / dx) + 2)):
                for i in range(max(0, int((sx - 1.0 - x0) / dx)), min(nx, int((sx + 1.0 - x0) / dx) + 2)):
                    n = (k * ny + j) * nx + i
                    if not seen[n] and free(n):
                        seen[n] = 1
                        q.append(n)
    seeds = len(q)
    reached, leaks, first = 0, 0, None
    ext = [1e9, -1e9, 1e9, -1e9, 1e9, -1e9]
    last = time.time()
    leak_cells = []
    while q:
        n = q.popleft()
        reached += 1
        x, y, zb = xyz(n)
        ext = [min(ext[0], x), max(ext[1], x), min(ext[2], y), max(ext[3], y), min(ext[4], zb), max(ext[5], zb)]
        lk = leak_fn(x, y, zb)
        if lk:
            leaks += 1
            if len(leak_cells) < 50:
                leak_cells.append([round(x, 2), round(y, 2), round(zb, 2), lk])
            if first is None:
                path, m = [], n
                while m != -1 and len(path) < 4000:
                    path.append([round(v, 2) for v in xyz(m)])
                    m = parent[m]
                first = {"cell_bl_m": [round(x, 2), round(y, 2), round(zb, 2)], "why": lk, "path_every_10": path[::10]}
        k, rem = divmod(n, nx * ny)
        j, i = divmod(rem, nx)
        for (a, b, c) in ((i + 1, j, k), (i - 1, j, k), (i, j + 1, k), (i, j - 1, k), (i, j, k + 1), (i, j, k - 1)):
            if 0 <= a < nx and 0 <= b < ny and 0 <= c < nzc:
                m = (c * ny + b) * nx + a
                if not seen[m] and free(m):
                    seen[m] = 1
                    parent[m] = n
                    q.append(m)
        if time.time() - last > 30:
            last = time.time()
            unreal.log(f"V10B_FLOOD {mode} r{int(r)} reached {reached} queue {len(q)} leaks {leaks}")
    # did the flood touch the lattice edge? (an edge cell reached = the box was too small to judge)
    edge = 0
    for n in range(N):
        if seen[n]:
            k, rem = divmod(n, nx * ny)
            j, i = divmod(rem, nx)
            if i in (0, nx - 1) or j in (0, ny - 1) or k == nzc - 1:
                edge += 1
    return {"mode": mode, "r_cm": r, "grid": {"x": [x0, x1], "y": [y0, y1], "bottom": [zb0, zb1], "dx": dx, "dz": dz, "cells": N},
            "seeds": seeds, "reached": reached, "tested": sum(1 for s in st if s), "leak_cells": leaks,
            "first_leak": first, "leak_samples": leak_cells,
            "reached_extent_bl_m": [round(v, 2) for v in ext], "reached_on_lattice_edge_or_ceiling": edge,
            "sec": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------ arcs (the v9 model)
def sim(x, y, zf, yaw, speed, mode, r, ign, leak_fn):
    c = V(x * 100, -y * 100, zf * 100 + HH + 1.0)
    vx, vy = speed * math.cos(yaw), -speed * math.sin(yaw)
    vz = JZ if mode != "walk" else 0.0
    grounded = mode == "walk"
    t, t_apex, jumps = 0.0, None, 1 if mode != "walk" else 0
    for _step in range(int(3.0 / DT)):
        t += DT
        if grounded:
            up = V(c.x, c.y, c.z + 45.0)
            h = cap_sweep(c, up, r, ign)
            top = up if h is None else h["loc"]
            fwd = V(top.x + vx * DT, top.y + vy * DT, top.z)
            h = cap_sweep(top, fwd, r, ign)
            if h is not None:
                n = h["n"]
                if n is None:
                    break
                d = vx * n.x + vy * n.y
                vx, vy = vx - d * n.x, vy - d * n.y
                fwd = h["loc"]
                if math.hypot(vx, vy) < 30:
                    break
            down = V(fwd.x, fwd.y, fwd.z - 45.0 - 50.0)
            h = cap_sweep(fwd, down, r, ign)
            if h is not None and not h["start_pen"] and nz(h) >= 0.70:
                c = h["loc"]
            else:
                c = V(fwd.x, fwd.y, fwd.z - 45.0) if h is None else h["loc"]
                grounded, vz = False, 0.0
        else:
            if mode in ("double", "double_late") and jumps == 1:
                if t_apex is None and vz <= 0:
                    t_apex = t
                if t_apex is not None and (mode == "double" or t - t_apex >= 0.25):
                    vz, jumps = JZ, 2
            nvz = vz - G * DT
            nxt = V(c.x + vx * DT, c.y + vy * DT, c.z + (vz + nvz) * 0.5 * DT)
            vz = nvz
            h = cap_sweep(c, nxt, r, ign)
            if h is None:
                c = nxt
            elif h["start_pen"]:
                break
            else:
                c = h["loc"]
                n = h["n"]
                if n is not None and n.z >= 0.70 and vz <= 0:
                    grounded, vz = True, 0.0
                elif n is not None:
                    d = vx * n.x + vy * n.y + vz * n.z
                    vx, vy, vz = vx - d * n.x, vy - d * n.y, vz - d * n.z
        fx, fy, fz = c.x / 100, -c.y / 100, (c.z - HH - 1.0) / 100
        lk = leak_fn(fx, fy, fz)
        if lk:
            return {"why": lk, "at_bl_m": [round(fx, 2), round(fy, 2), round(fz, 2)], "t_s": round(t, 2)}
        if fz < -12.0:
            break
    return None


def run_arcs(mode, pts, headings, speeds, modes, walk_speed, leak_fn, r=30.0):
    t0 = time.time()
    ign = IGN[mode]
    launch = []
    for p in pts:
        for dzz in (0.02, 0.04, 0.06, 0.08, 0.12, 0.16, 0.20):
            if cap_free_at(p[0], p[1], p[2] + dzz, r, ign):
                launch.append((p[0], p[1], round(p[2] + dzz - 0.02, 3)))
                break
    n, leaks, firsts, lp = 0, 0, [], []
    for (x, y, zf) in launch:
        for k in range(headings):
            yaw = math.radians(k * 360.0 / headings)
            combos = [(sp, m) for sp in speeds for m in modes] + [(walk_speed, "walk")]
            for sp, m in combos:
                e = sim(x, y, zf + 0.02, yaw, sp, m, r, ign, leak_fn)
                n += 1
                if e:
                    leaks += 1
                    if len(firsts) < 40:
                        firsts.append({"launch_bl_m": [x, y, zf], "heading_deg": round(k * 360.0 / headings, 1), "speed": sp,
                                       "mode": m, **e})
                    if [x, y, zf] not in lp and len(lp) < 60:
                        lp.append([x, y, zf])
        if time.time() - t0 > 60 and n % 3000 < len(combos):
            unreal.log(f"V10B_ARCS {mode} {n} attempts {leaks} leaks traces {NT[0]}")
    return {"mode": mode, "r_cm": r, "surfaces": len(pts), "launch_points": len(launch), "attempts": n, "leaks": leaks,
            "leak_examples": firsts, "leak_launch_points": lp,
            "launch_z_max_m": max((p[2] for p in launch), default=None), "sec": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------ stair walker
STAIR = [(22.0, -2.3), (22.0, -5.0), (12.6, -6.5), (9.1, -6.5), (9.1, -28.9), (3.3, -28.9), (3.3, -39.0)]


def lane(pts, off):
    out = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        out.append((x - dy / L * off, y + dx / L * off))
    return out


def walk(pts, r, ign, z_start):
    floor = z_start
    prev = None
    rows = {"samples": 0, "max_rise_cm": 0.0, "max_drop_cm": 0.0, "min_floor_nz": 1.0, "floor_actors": {}}
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        nseg = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
        for k in range(nseg + 1):
            x, y = x0 + (x1 - x0) * k / nseg, y0 + (y1 - y0) * k / nseg
            a0 = V(x * 100, -y * 100, (floor + 0.47) * 100 + HH + 1.0)
            h = cap_sweep(a0, V(a0.x, a0.y, a0.z - 147.0), r, ign)
            if not h or h["start_pen"]:
                return {**rows, "clear": False, "why": "no floor within +0.47 / -1.0 m" if not h else "no room at step height",
                        "at_bl_m": [round(x, 2), round(y, 2), round(floor, 3)], "actor": h["actor"] if h else None}
            zf = (h["loc"].z - HH - 1.0) / 100
            if nz(h) < 0.71:   # an edge contact: accept if the centre line finds a walkable floor at the same height
                lh = line_down(x, y, zf + 0.10, 0.25, ign)
                if lh and not lh["start_pen"] and nz(lh) >= 0.71 and abs(lh["imp"].z / 100 - zf) <= 0.06:
                    h = lh
            d = zf - floor
            if d > 0.45:
                return {**rows, "clear": False, "why": f"rise {d * 100:.1f} cm > 45", "at_bl_m": [round(x, 2), round(y, 2), round(zf, 3)],
                        "actor": h["actor"]}
            if -d > 0.45:
                return {**rows, "clear": False, "why": f"drop {-d * 100:.1f} cm > 45", "at_bl_m": [round(x, 2), round(y, 2), round(zf, 3)],
                        "actor": h["actor"]}
            if nz(h) < 0.71:
                return {**rows, "clear": False, "why": f"floor nz {nz(h):.3f} < 0.71", "at_bl_m": [round(x, 2), round(y, 2), round(zf, 3)],
                        "actor": h["actor"]}
            rows["max_rise_cm"] = max(rows["max_rise_cm"], round(d * 100, 2))
            rows["max_drop_cm"] = max(rows["max_drop_cm"], round(-d * 100, 2))
            rows["min_floor_nz"] = min(rows["min_floor_nz"], round(nz(h), 4))
            rows["floor_actors"][h["actor"]] = rows["floor_actors"].get(h["actor"], 0) + 1
            floor = zf
            c = V(x * 100, -y * 100, floor * 100 + HH + 2.0)
            if not cap_free_at(x, y, floor + 0.01, r, ign):
                blk = cap_sweep(c, V(c.x + 0.1, c.y, c.z), r, ign)
                return {**rows, "clear": False, "why": "capsule does not fit", "at_bl_m": [round(x, 2), round(y, 2), round(floor, 3)],
                        "actor": blk["actor"] if blk else None}
            if prev is not None:
                # sweep lifted by the rise (a step-up), as the CMC does
                lift = max(0.0, c.z - prev.z)
                a = V(prev.x, prev.y, prev.z + lift)
                s = cap_sweep(a, V(c.x, c.y, c.z + 0.5), r, ign) if lift <= 45.0 else None
                if s is not None:
                    return {**rows, "clear": False, "why": "sweep blocked", "at_bl_m": [round(x, 2), round(y, 2), round(floor, 3)],
                            "actor": s["actor"]}
            prev = c
            rows["samples"] += 1
    return {**rows, "clear": True, "end_bl_m": [round(pts[-1][0], 2), round(pts[-1][1], 2), round(floor, 3)]}


def run_routes():
    """every layout walk route with my capsule walker (CMC-like capsule floor): CONTROLs must be blocked, the rest
    clear; 'leaves: open' routes in mode br (as walk_check)."""
    L = json.loads(Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/showcase/layout_showcase.json").read_text(encoding="utf-8"))
    out = {}
    for name, rt in L["walk_routes"].items():
        ign = IGN["br"] if rt.get("leaves") == "open" else IGN["1v1"]
        res = walk2([tuple(p) for p in rt["points"]], 30.0, ign, rt["floor_z"])
        res35 = walk2([tuple(p) for p in rt["points"]], 35.0, ign, rt["floor_z"])
        res["clear_r35"] = res35["clear"]
        res.pop("floor_actors", None)
        out[name] = res
    bad = [k for k, v in out.items() if (k.startswith("CONTROL") and v["clear"]) or (not k.startswith("CONTROL") and not v["clear"])]
    return {"routes": out, "not_as_expected": bad}


def run_stair():
    out = {}
    for r in (30.0, 35.0):
        for off in (0.0, 0.15, 0.3, 0.45, -0.3):
            p = lane(STAIR, off)
            out[f"down_r{int(r)}_off{off:+.1f}"] = walk(p, r, IGN["br"], 0.0)
            end = out[f"down_r{int(r)}_off{off:+.1f}"]
            zs = end.get("end_bl_m", [0, 0, -7.0])[2]
            out[f"up_r{int(r)}_off{off:+.1f}"] = walk(list(reversed(p)), r, IGN["br"], zs)
    out["CONTROL_1v1_down_r30_centre"] = walk(STAIR, 30.0, IGN["1v1"], 0.0)
    lanes = {k: v["clear"] for k, v in out.items() if not k.startswith("CONTROL")}
    # end to end = for each radius, at least one lane clear in BOTH directions
    ok = {}
    for r in (30, 35):
        ok[r] = [off for off in ("+0.0", "+0.1", "+0.2", "+0.3", "+0.5", "-0.3") if lanes.get(f"down_r{r}_off{off}") and lanes.get(f"up_r{r}_off{off}")]
    out["lanes_clear_both_ways"] = ok
    out["width"] = stair_width()
    out["passed"] = all(ok[r] for r in ok) and not out["CONTROL_1v1_down_r30_centre"]["clear"]
    return out


def stair_width(r=30.0):
    """every 0.25 m along the path: lateral offsets -1.0..+1.0 m (0.05) where the standing capsule fits on the floor
    (capsule floor sweep from the centreline floor + 0.47 m); the widest contiguous run + 2 r = the clear width."""
    ign = IGN["br"]
    rows, floor = [], 0.0
    for (x0, y0), (x1, y1) in zip(STAIR, STAIR[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        nx_, ny_ = -(y1 - y0) / L, (x1 - x0) / L
        for k in range(int(L / 0.25) + 1):
            cx, cy = x0 + (x1 - x0) * k * 0.25 / L, y0 + (y1 - y0) * k * 0.25 / L
            lh = line_down(cx + nx_ * 0.6, cy + ny_ * 0.6, floor + 0.6, 1.5, ign)
            if lh and not lh["start_pen"]:
                floor = lh["imp"].z / 100
            free = []
            for j in range(41):
                off = -1.0 + 0.05 * j
                x, y = cx + nx_ * off, cy + ny_ * off
                a0 = V(x * 100, -y * 100, (floor + 0.47) * 100 + HH + 1.0)
                h = cap_sweep(a0, V(a0.x, a0.y, a0.z - 100.0), r, ign)
                okk = bool(h and not h["start_pen"] and abs((h["loc"].z - HH - 1.0) / 100 - floor) <= 0.25)
                if okk:
                    zf = (h["loc"].z - HH - 1.0) / 100
                    okk = cap_free_at(x, y, zf + 0.01, r, ign)
                free.append(okk)
            best, run, bs = 0, 0, None
            for j, f in enumerate(free):
                run = run + 1 if f else 0
                if run > best:
                    best, bs = run, j - run + 1
            width = round((best - 1) * 0.05 + 2 * r / 100, 2) if best else 0.0
            rows.append({"at_bl_m": [round(cx, 2), round(cy, 2), round(floor, 2)], "clear_width_m": width,
                         "run_offsets_m": [round(-1.0 + 0.05 * bs, 2), round(-1.0 + 0.05 * (bs + best - 1), 2)] if best else None})
    w = [r_["clear_width_m"] for r_ in rows]
    narrow = sorted(rows, key=lambda r_: r_["clear_width_m"])[:12]
    return {"samples": len(rows), "min_clear_width_m": min(w), "median_clear_width_m": sorted(w)[len(w) // 2],
            "n_under_0_9m": sum(1 for v in w if v < 0.9), "narrowest": narrow}


# ------------------------------------------------------------------------------------------------ VERIFIER v11 additions
SKIN = 2.0
UNWALK_KEYS = ("_Glass__", "_Plinth__", "SM_AK_Lantern", "SM_AK_H_LanternStand", "SM_AK_Vase")


def unwalkable(actor_label):
    return bool(actor_label) and actor_label.startswith("SM_AK_") and any(k in actor_label for k in UNWALK_KEYS)


def _floor_below(cx, cy, cz, depth, r, ign):
    """capsule centre (cm) swept straight down by depth cm: (hit, floor_z_m) with the v10 edge-contact rule."""
    h = cap_sweep(V(cx, cy, cz), V(cx, cy, cz - depth), r, ign)
    if not h or h["start_pen"]:
        return h, None
    zf = (h["loc"].z - HH - 1.0) / 100
    if nz(h) < 0.71:
        lh = line_down(cx / 100, -cy / 100, zf + 0.10, 0.25, ign)
        if lh and not lh["start_pen"] and nz(lh) >= 0.71 and abs(lh["imp"].z / 100 - zf) <= 0.06:
            h = dict(h, n=lh["n"], actor=lh["actor"])
    lo = h["loc"]
    h = dict(h, loc=V(lo.x, lo.y, lo.z + SKIN))   # keep a 2 cm skin over the floor (no contact at the next sweep start)
    return h, zf


def step(c, tx, ty, r, ign, max_drop=0.5):
    """one CMC-like move of the standing capsule centre c (cm vector) to plan point (tx, ty) m.
    Returns (new centre, floor m, actor, None) or (None, None, actor, why)."""
    t = V(tx * 100, -ty * 100, c.z)
    h = cap_sweep(c, t, r, ign)
    lift = 0.0
    if h is not None:
        if h["start_pen"]:
            return None, None, h["actor"], "start penetrating"
        up = cap_sweep(c, V(c.x, c.y, c.z + 45.0), r, ign)       # step-up, clamped by any ceiling (door head)
        full = 45.0 if up is None else max(0.0, up["loc"].z - c.z - 1.0)   # CMC pulls back off a ceiling contact
        h2, ok = None, False
        for lift in sorted({full, max(0.0, full - 3.0), max(0.0, full - 6.0), max(0.0, full - 9.0), max(0.0, full - 12.0),
                            max(0.0, full - 18.0)}, reverse=True):
            top = V(c.x, c.y, c.z + lift)
            if lift > 0 and cap_sweep(c, top, r, ign) is not None:
                continue
            t2 = V(t.x, t.y, top.z)
            h2 = cap_sweep(top, t2, r, ign)
            if h2 is None:
                ok = True
                break
        if not ok:
            return None, None, h2["actor"] if h2 else None, f"blocked (lift up to {full:.1f} cm)"
        t = t2
    fh, zf = _floor_below(t.x, t.y, t.z, lift + max_drop * 100 + 1.0, r, ign)
    if fh is None or zf is None:
        return None, None, fh["actor"] if fh else None, "no floor (drop)" if fh is None else "floor start penetrating"
    if nz(fh) < 0.71:
        return None, None, fh["actor"], f"floor nz {nz(fh):.3f}"
    if unwalkable(fh["actor"]):
        return None, None, fh["actor"], "unwalkable prop (D6)"
    c2 = fh["loc"]
    return c2, zf, fh["actor"], None


def walk2(pts, r, ign, z_start):
    """the layout route with step(): 5 cm samples; rise <= 45 cm, drop <= 50 cm."""
    x0, y0 = pts[0]
    fh, zf = _floor_below(x0 * 100, -y0 * 100, (z_start + 0.30) * 100 + HH + 1.0, 80.0, r, ign)
    if fh is None or zf is None:
        return {"clear": False, "why": "no start floor", "at_bl_m": [x0, y0, z_start], "actor": fh["actor"] if fh else None}
    c, floor = fh["loc"], zf
    rows = {"samples": 0, "max_rise_cm": 0.0, "max_drop_cm": 0.0}
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / 0.05))
        for k in range(1, n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            c2, z2, act, why = step(c, x, y, r, ign)
            if why:
                return {**rows, "clear": False, "why": why, "at_bl_m": [round(x, 2), round(y, 2), round(floor, 3)], "actor": act}
            d = z2 - floor
            rows["max_rise_cm"] = max(rows["max_rise_cm"], round(d * 100, 2))
            rows["max_drop_cm"] = max(rows["max_drop_cm"], round(-d * 100, 2))
            c, floor = c2, z2
            rows["samples"] += 1
    return {**rows, "clear": True, "end_bl_m": [round(pts[-1][0], 2), round(pts[-1][1], 2), round(floor, 3)]}


def run_interior():
    """walking flood (2.5D, one floor per cell, 8-neighbour, step() moves) on a 0.2 m grid from the courtyard at
    (22, 16) over X 12.1..31.9, Y 14.1..46.9, mode 1v1, r 30 (and the reached set at r 35 counted separately).
    Reports: interior floor cells reached (inside the armory walls X 16..28, Y 24.12..44), free interior floor cells
    NOT reached (free = a downward trace from +3.6 m finds a floor below the ceiling and the capsule fits), every reached
    cell inside the hall but outside the armory walls (side strips / cavities: a leak), the dais deck reached, the
    floor actors stood on (props?)."""
    t0 = time.time()
    out = {}
    for r in (30.0, 35.0):
        ign = IGN["1v1"]
        g, X0, Y0, NX, NY = 0.2, 12.1, 14.1, 100, 165
        fh, zf = _floor_below(22.0 * 100, -16.0 * 100, 1.0 * 100 + HH + 1.0, 150.0, r, ign)
        seen = {(50, 9): (fh["loc"], zf)}
        q = deque([(50, 9)])
        floor_actors = {}
        while q:
            i, j = q.popleft()
            c, z = seen[(i, j)]
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                a, b = i + di, j + dj
                if not (0 <= a < NX and 0 <= b < NY) or (a, b) in seen:
                    continue
                c2, z2, act, why = step(c, X0 + a * g, Y0 + b * g, r, ign)
                if why or z2 - z > 0.45:
                    continue
                if not cap_free_at(X0 + a * g, Y0 + b * g, z2 + 0.01, r, ign):
                    continue
                seen[(a, b)] = (c2, z2)
                floor_actors[act] = floor_actors.get(act, 0) + 1
                q.append((a, b))
        inside = lambda x, y: 16.0 < x < 28.0 and 24.12 < y < 44.0
        hall_not_armory = lambda x, y: (13.12 < x < 15.7 or 28.3 < x < 30.88) and 24.12 < y < 44.88
        reached = {(i, j): v for (i, j), v in seen.items()}
        rin = [(X0 + i * g, Y0 + j * g, v[1]) for (i, j), v in reached.items() if inside(X0 + i * g, Y0 + j * g)]
        leaks = [[round(X0 + i * g, 2), round(Y0 + j * g, 2), round(v[1], 3)] for (i, j), v in reached.items()
                 if hall_not_armory(X0 + i * g, Y0 + j * g) or (Y0 + j * g > 44.3) or (Y0 + j * g > 34.12 and not 14.88 < X0 + i * g < 29.12)]
        # free interior floor cells (independent of connectivity)
        free_cells, unreached = 0, []
        for i in range(NX):
            for j in range(NY):
                x, y = X0 + i * g, Y0 + j * g
                if not inside(x, y):
                    continue
                lh = line_down(x, y, 3.6, 3.4, ign)
                if not lh or lh["start_pen"] or nz(lh) < 0.71 or unwalkable(lh["actor"]):
                    continue
                zf2 = lh["imp"].z / 100
                if not cap_free_at(x, y, zf2 + 0.02, r, ign):
                    continue
                free_cells += 1
                if (i, j) not in reached:
                    unreached.append([round(x, 2), round(y, 2), round(zf2, 3), lh["actor"]])
        dais = [p for p in rin if p[2] > 1.0]
        out[f"r{int(r)}"] = {"reached_cells": len(reached), "interior_reached_cells": len(rin), "interior_free_cells": free_cells,
                             "interior_free_unreached": len(unreached), "unreached_examples": unreached[:80],
                             "leaks_into_hidden_strips_or_cavities": leaks[:40], "n_leaks": len(leaks),
                             "dais_cells_reached": len(dais), "max_floor_reached_m": round(max((p[2] for p in rin), default=0), 3),
                             "max_y_reached": round(max((Y0 + j * g for (i, j) in reached), default=0), 2),
                             "floor_actors_top": sorted(floor_actors.items(), key=lambda kv: -kv[1])[:40],
                             "props_stood_on": sorted(k for k in floor_actors if k and ("SM_AK_" in k and unwalkable(k)))}
        unreal.log(f"VHA_INTERIOR r{int(r)} reached {len(reached)} interior {len(rin)}/{free_cells} leaks {len(leaks)}")
    out["reached_cells"] = out["r30"]["reached_cells"]
    out["leaks_into_targets"] = out["r30"]["n_leaks"] + out["r35"]["n_leaks"]
    out["sec"] = round(time.time() - t0, 1)
    return out


def run_rearroof():
    """BR (the whole 1v1 group ignored): walk the main roof's back slope over the valley, up the rear roof to its ridge
    and down to the north eave on x 17 / 22 / 27, and back; 1v1 controls: the same lines and a walk from the front half
    over the main ridge must be BLOCKED; plus BR ground -> rear eave is NOT a walk (climb only: Blender climb check)."""
    out = {}

    def start_on(x, y, ign):
        lh = line_down(x, y, 14.0, 10.0, ign)
        return None if not lh or lh["start_pen"] else lh["imp"].z / 100

    for x in (17.0, 22.0, 27.0):
        for mode in ("br", "1v1"):
            ign = IGN[mode]
            z0 = start_on(x, 31.0, IGN["br"])
            line = [(x, 31.0), (x, 34.42), (x, 40.16), (x, 45.6)]
            out[f"{mode}_x{x:g}_back_slope_over_valley_ridge_to_north_eave"] = walk2(line, 30.0, ign, z0) if z0 else {"clear": False, "why": "no start"}
            z1 = start_on(x, 45.4, IGN["br"])
            out[f"{mode}_x{x:g}_north_eave_up_over_rear_ridge_to_valley"] = walk2(list(reversed(line))[:3], 30.0, ign, z1) if z1 else {"clear": False, "why": "no start"}
    # 1v1 from the legal front half over the main ridge into the rear half
    for x in (17.0, 22.0, 27.0):
        z0 = start_on(x, 26.5, IGN["1v1"])
        out[f"CONTROL_1v1_x{x:g}_front_half_over_main_ridge"] = walk2([(x, 26.5), (x, 29.15), (x, 31.5)], 30.0, IGN["1v1"], z0) if z0 else {"clear": False, "why": "no start"}
    # the rear roof's gable verges (BR): walk along the ridge from west verge to east verge
    z = start_on(15.0, 40.16, IGN["br"])
    out["br_along_rear_ridge_W_to_E"] = walk2([(15.0, 40.16), (29.0, 40.16)], 30.0, IGN["br"], z) if z else {"clear": False, "why": "no start"}
    br_ok = all(v["clear"] for k, v in out.items() if k.startswith("br_"))
    ctl_ok = all(not v["clear"] for k, v in out.items() if k.startswith("CONTROL"))
    out["info_1v1_lines_from_closed_back_slope_clear"] = [k for k, v in out.items() if k.startswith("1v1_") and isinstance(v, dict) and v.get("clear")]
    out["summary"] = {"br_all_clear": br_ok, "1v1_all_blocked": ctl_ok}
    out["passed"] = br_ok and ctl_ok
    return out


def main():
    t0 = time.time()
    rep = {"verifier": "independent hall+armory v11", "parts": PARTS, "ring": [a.get_actor_label() for a in RING],
           "blines": sorted(a.get_actor_label() for a in BL), "group": sorted(a.get_actor_label() for a in GROUP),
           "n_trv": len(TRV)}

    def save():
        rep["traces"] = NT[0]
        rep["sec"] = round(time.time() - t0, 1)
        OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")

    starts = [(14.5, 10.5), (29.5, 10.5)]
    ceil = float(os.environ.get("DJ_CEIL", "0"))
    try:
        if "height" in PARTS:
            rep["height"] = run_height()
            ceil = ceil or rep["height"]["ceiling_bottom_m"]
            unreal.log(f"V10B_HEIGHT {rep['height']['max_standable_z_m']} ceil {ceil}")
            save()
        ceil = ceil or 16.0
        rep["ceiling_bottom_m"] = ceil
        if "routes" in PARTS:
            rep["routes"] = run_routes()
            unreal.log(f"V10B_ROUTES bad={rep['routes']['not_as_expected']}")
            save()
        if "interior" in PARTS:
            rep["interior"] = run_interior()
            unreal.log(f"VHA_INTERIOR reached {rep['interior'].get('reached_cells')} leaks {rep['interior'].get('leaks_into_targets')}")
            save()
        if "rearroof" in PARTS:
            rep["rearroof"] = run_rearroof()
            unreal.log(f"VHA_REARROOF {rep['rearroof'].get('summary')}")
            save()
        if "stair" in PARTS:
            rep["stair"] = run_stair()
            unreal.log(f"V10B_STAIR passed={rep['stair']['passed']}")
            save()
        if "flood1v1" in PARTS:
            leak = lambda x, y, zb: ("outside ring" if not in_ring(x, y) else None) or ("outside B-poly" if not in_bpoly(x, y) else None)
            rep["flood1v1_r30"] = flood("1v1", 30.0, -13.93, 57.07, -15.93, 52.07, -2.91, ceil, 0.25, 0.25, starts, leak)
            unreal.log(f"V10B_FLOOD1v1 leaks {rep['flood1v1_r30']['leak_cells']}")
            save()
            rep["flood1v1_r35"] = flood("1v1", 35.0, -13.87, 57.13, -15.87, 52.13, -2.83, ceil, 0.3, 0.3, starts, leak)
            save()
        if "floodbr" in PARTS:
            out_ring = lambda x, y, zb: "outside ring" if not in_ring(x, y) else None
            rep["floodbr_r30"] = flood("br", 30.0, -13.9, 57.1, -42.4, 52.1, -8.9, min(ceil, 8.0), 0.5, 0.5, starts, out_ring)
            rep["floodbr_r30"]["note"] = "leak_cells here = cells reached outside the ring (must be > 0: separable)"
            save()
            rep["floodbonly_r30"] = flood("bonly", 30.0, -13.9, 57.1, -16.4, 52.1, -2.9, min(ceil, 8.0), 0.5, 0.5, starts,
                                          lambda x, y, zb: "outside B-poly" if not in_bpoly(x, y) else None)
            rep["floodbonly_r30"]["note"] = ("ring ignored, B-lines kept, ceiling capped at 8 m feet (a flying capsule "
                                             "passes over any 6 m line): information only")
            save()
        SURF_ZMAX[0] = ceil
        if "arcs1v1" in PARTS:
            keep = lambda x, y, z: in_ring(x, y) and (min(x - RINGF[0], RINGF[1] - x, y - RINGF[2], RINGF[3] - y) <= 4.0 or z >= 3.0)
            # surfaces found with the group ignored (the ring's top hull would shadow every column from above); the
            # arcs themselves run with everything (mode 1v1)
            pts = surfaces((-0.95, 45.0), (-0.95, 48.0), 0.45, IGN["br"], keep)
            rep["arcs1v1_r30"] = run_arcs("1v1", pts, 20, (300.0, 450.0, 650.0), ("jump", "double", "double_late"), 450.0,
                                          lambda x, y, z: "outside ring" if not in_ring(x, y) else None)
            unreal.log(f"V10B_ARCS1v1 leaks {rep['arcs1v1_r30']['leaks']}")
            save()
        if "arcsB" in PARTS:
            keep = lambda x, y, z: in_bpoly(x, y) and bdist(x, y) <= 8.0
            pts = surfaces((-7.0, 48.75), (-7.75, 56.0), 0.5, IGN["bonly"], keep)
            rep["arcsB_r30"] = run_arcs("bonly", pts, 16, (450.0, 650.0), ("jump", "double", "double_late"), 650.0,
                                        lambda x, y, z: "outside B-poly" if not in_bpoly(x, y) else None)
            unreal.log(f"V10B_ARCSB leaks {rep['arcsB_r30']['leaks']}")
            save()
    except Exception:  # noqa: BLE001
        import traceback
        rep["error"] = traceback.format_exc()[-4000:]
    save()
    unreal.log(f"VHA_BOUNDARY_DONE error={'error' in rep}")


main()
