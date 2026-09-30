"""VERIFY r8 (final, independent verifier): the 1v1 rear seal on L_Dojo as saved, MY OWN capsule attempts (not the
builders' CONTROL routes, not the first r6 verifier's scripted paths). A fresh read-only pythonscript commandlet
(-nullrhi); nothing is saved; the only file written is verify_r8/<DJ_OUT> (default ue_alley_own.json).
Traces: Pawn-profile capsule sweeps on simple collision; TRV_ markers ignored (Traversable-only) except in the mantle
forward trace, which uses the Traversable channel as GASP does.

Targets (spec 4.6 / 5.2 / 5.4; X/Y in Blender metres, north = +Y; z = the capsule's feet):
  strip behind the hall, both pockets behind the corridors, the corridors' north slopes, the outbuildings' north roof
  halves, the upper roof's rear half, the north wall top and anything north of it.

A. ARCS (DJ_PARTS 'arcs'): launch points = every standable surface (a Pawn line trace hit with a walkable normal,
   nz >= 0.70, several layers per column by re-tracing below each hit) on a 0.25 m plan grid (DJ_GRID) over X -1..45, Y 24..36.9,
   outside every target, where the standing capsule fits (the start lifted up to 0.20 m until it does: sloped roofs). From each: 24 headings (every 15 deg, DJ_HEADINGS) x speeds 350 / 500 /
   700 cm/s x modes: WALK (floor-following, step-up 45 cm, walks off edges and falls), JUMP (vz 500, g 980: apex
   1.276 m), DOUBLE (second vz 500 at the apex: ~2.55 m), DOUBLE_LATE (second jump 0.25 s after the apex). 30 Hz
   capsule sweeps; walls slide the velocity (the normal part removed), walkable floors land and the walk continues on
   them; 3.0 s per attempt. A LEAK = the capsule's feet inside a target at any step. Radii 30 and 35 (hh 86 = GASP).
   Mode 1v1 = everything; mode br = the 'Dojo/Boundary_1v1' group ignored too (must open targets: separable).
B. FLOOD (DJ_PARTS 'flood'/'flood35'/'floodbr'): a flying r 30 (or 35) capsule flooded 6-connected on a lattice OFFSET
   from the first verifier's (plan 0.1 m from X -0.95 / Y 23.05; height 0.15 m from +0.05), X -0.95..44.95,
   Y 23.05..36.95, capsule bottom +0.05..+18.05, seeded from every free cell on the Y 23.05 plane (all of the legal
   south is taken as reachable: generous). A superset of any jump / mantle / fall / walk.
C. MANTLES (DJ_PARTS 'mantle'): every TRV marker ledge (all four edges), sampled every 0.25 m (20 cm from the ends),
   stance 0.55 m out on the floor below, GASP rule (the forward capsule r 30 hh 60 on the Traversable channel must hit
   that marker, 0.26 < height <= 2.75, stance free), landing capsule 0.35 m in on the top; whether the Pawn path
   stance -> up -> over -> landing is clear. A LEAK = stance outside every target, landing free and inside one.
   Also: any TRV marker whose top lies inside a target (a ledge offered inside the closed area).
"""
import json
import math
import os
import time
from array import array
from collections import deque
from pathlib import Path

import unreal

VD = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\verify_r8")
LAYOUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\showcase\layout_showcase.json")
V = unreal.Vector
PARTS = os.environ.get("DJ_PARTS", "arcs,mantle,flood,floodbr").split(",")
OUT = VD / os.environ.get("DJ_OUT", "ue_alley_own.json")
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
IGN = {"1v1": TRV, "br": TRV + GROUP}
NT = [0]


def mx(b):   # mirror a (x0, x1, y0, y1, zfeet) box about X 22
    return (round(44.0 - b[1], 3), round(44.0 - b[0], 3)) + tuple(b[2:])


TARGETS = {"strip_behind_hall": (10.45, 33.55, 34.12, 36.0, -1.0),
           "hall_upper_rear_half": (12.15, 31.85, 29.15, 34.0, 5.45),
           "north_wall_top_and_beyond": (-1.5, 45.5, 36.02, 40.0, -1.0)}
for sd, f in (("W", lambda b: b), ("E", mx)):
    TARGETS[f"pocket_{sd}"] = f((7.12, 10.38, 32.3, 36.0, -1.0))
    TARGETS[f"corridor_north_slope_{sd}"] = f((7.12, 10.38, 31.12, 32.3, 2.5))
    TARGETS[f"outbuilding_north_roof_{sd}"] = f((-0.95, 7.12, 31.82, 36.0, 3.0))   # to the corridor box: no seam at X 6.98-7.12


def in_target(x, y, zf):
    for k, (x0, x1, y0, y1, z0) in TARGETS.items():
        if x0 <= x <= x1 and y0 <= y <= y1 and zf >= z0:
            return k
    return None


def ht(h):
    t = h.to_tuple() if h else None
    if not t or not (t[0] or t[1]):
        return None
    return {"start_pen": bool(t[1]), "time": float(t[2]), "loc": t[4], "imp": t[5], "n": t[7] if len(t) > 7 else None,
            "actor": t[9].get_actor_label() if t[9] else None}


def cap_sweep(a, b, r, ign, hh=HH):
    """a, b = capsule CENTRES (UE cm vectors)."""
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


# ------------------------------------------------------------------------------------------------ A. arcs
GRID = float(os.environ.get("DJ_GRID", "0.25"))
HEADINGS = int(os.environ.get("DJ_HEADINGS", "24"))


def surfaces(ign):
    """standable surfaces: per 0.5 m column, trace down from +19 m, record each walkable hit, continue 5 cm below it."""
    pts = []
    y = 24.0
    while y <= 36.9 + 1e-6:
        x = -1.0
        while x <= 45.0 + 1e-6:
            z = 19.0
            for _ in range(8):
                h = line_down(x, y, z, z + 1.5, ign)
                if not h or h["start_pen"]:
                    break
                zf = h["imp"].z / 100
                if nz(h) >= 0.70 and not in_target(x, y, zf):
                    pts.append((round(x, 2), round(y, 2), round(zf, 3)))
                z = zf - 0.05
                if z < -1.0:
                    break
            x += GRID
        y += GRID
    return pts


def sim(x, y, zf, yaw, speed, mode, r, ign):
    """one attempt; returns (entered_target or None, end state, steps)."""
    c = V(x * 100, -y * 100, zf * 100 + HH + 1.0)
    vx, vy = speed * math.cos(yaw), -speed * math.sin(yaw)       # UE frame (y flipped)
    vz = JZ if mode != "walk" else 0.0
    grounded = mode == "walk"
    t, t_apex, jumps = 0.0, None, 1 if mode != "walk" else 0
    entered = None
    for _step in range(int(3.0 / DT)):
        t += DT
        if grounded:
            # step-up walk: lift 45, sweep horizontally, drop to the floor (<= 45 + 50 cm), walkable
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
                vx, vy = vx - d * n.x, vy - d * n.y           # slide along the wall
                fwd = h["loc"]
                if math.hypot(vx, vy) < 30:
                    break
            down = V(fwd.x, fwd.y, fwd.z - 45.0 - 50.0)
            h = cap_sweep(fwd, down, r, ign)
            if h is not None and not h["start_pen"] and nz(h) >= 0.70:
                c = h["loc"]
            else:
                c = V(fwd.x, fwd.y, fwd.z - 45.0) if h is None else h["loc"]
                grounded, vz = False, 0.0                     # walked off an edge
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
                    grounded, vz = True, 0.0                 # landed: keep walking the same heading
                    if speed == 0:
                        break
                elif n is not None:
                    d = vx * n.x + vy * n.y + vz * n.z
                    vx, vy, vz = vx - d * n.x, vy - d * n.y, vz - d * n.z
        fx, fy, fz = c.x / 100, -c.y / 100, (c.z - HH - 1.0) / 100
        tk = in_target(fx, fy, fz)
        if tk and entered is None:
            entered = {"target": tk, "at_bl_m": [round(fx, 2), round(fy, 2), round(fz, 2)], "t_s": round(t, 2)}
            break
        if fz < -3.0:
            break
    return entered, [round(c.x / 100, 2), round(-c.y / 100, 2), round((c.z - HH - 1.0) / 100, 2)]


STRIDE = int(os.environ.get("DJ_ARC_STRIDE", "1"))
BR_STRIDE = int(os.environ.get("DJ_ARC_BR_STRIDE", "3"))
ARC_SETS = os.environ.get("DJ_ARC_SETS", "1v1_r30,1v1_r35,br_r30").split(",")


def run_arcs():
    out = {"stride": STRIDE, "br_stride": BR_STRIDE, "grid_m": GRID, "headings": HEADINGS}
    pts1 = surfaces(IGN["1v1"])
    out["surfaces_1v1"] = len(pts1)
    for mode_set in ("1v1", "br"):
        ign = IGN[mode_set]
        if not any(a.startswith(mode_set) for a in ARC_SETS):
            continue
        pts = pts1 if mode_set == "1v1" else surfaces(ign)
        for r in (30.0, 35.0) if mode_set == "1v1" else (30.0,):
            if f"{mode_set}_r{int(r)}" not in ARC_SETS:
                continue
            t0 = time.time()
            sd = STRIDE if mode_set == "1v1" else BR_STRIDE * STRIDE
            launch = []
            for p in pts[::sd]:      # lift the start up to 0.20 m until the capsule fits (sloped roofs: ~3 cm)
                for dz in (0.02, 0.04, 0.06, 0.08, 0.12, 0.16, 0.20):
                    if cap_free_at(p[0], p[1], p[2] + dz, r, ign):
                        launch.append((p[0], p[1], round(p[2] + dz - 0.02, 3)))
                        break
            n, leaks, by_target, first, launch_by = 0, 0, {}, {}, {}
            for (x, y, zf) in launch:
                for k in range(HEADINGS):
                    yaw = math.radians(k * 360.0 / HEADINGS)
                    for sp in (350.0, 500.0, 700.0):
                        for mode in ("walk", "jump", "double", "double_late"):
                            if mode == "walk" and sp != 500.0:
                                continue
                            ent, _end = sim(x, y, zf + 0.02, yaw, sp, mode, r, ign)
                            n += 1
                            if ent:
                                leaks += 1
                                by_target[ent["target"]] = by_target.get(ent["target"], 0) + 1
                                ls = launch_by.setdefault(ent["target"], [])
                                if [x, y, zf] not in ls and len(ls) < 12:
                                    ls.append([x, y, zf])
                                if ent["target"] not in first:
                                    first[ent["target"]] = {"launch_bl_m": [x, y, zf], "heading_deg": round(k * 360.0 / HEADINGS, 1), "speed": sp,
                                                            "mode": mode, **ent}
                if time.time() - t0 > 60 and n % 2000 == 0:
                    unreal.log(f"V8F_ARCS {mode_set} r{int(r)} {n} attempts {leaks} entries traces {NT[0]}")
            out[f"{mode_set}_r{int(r)}"] = {"surfaces": len(pts), "launch_points": len(launch), "attempts": n,
                                            "entries": leaks, "entries_by_target": by_target, "first_entry_per_target": first,
                                            "launch_points_per_target": launch_by, "launch_north_of_31_8": sorted([list(p) for p in launch if p[1] > 31.8])[:200],
                                            "sec": round(time.time() - t0, 1)}
            unreal.log(f"V8F_ARCS {mode_set} r{int(r)} done {n} attempts, {leaks} entries {by_target}")
    out["passed"] = all(v["entries"] == 0 for k, v in out.items() if k.startswith("1v1_"))
    out["br_opens_targets"] = sorted((out.get("br_r30") or {}).get("entries_by_target", {}))
    return out


# ------------------------------------------------------------------------------------------------ B. flood
def flood(mode, r=30.0, x0=-0.95, x1=44.95, y0=23.05, y1=36.95, zb0=0.05, zb1=18.05, dx=0.1, dz=0.15):
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
    for k in range(nzc):
        for i in range(nx):
            n = k * ny * nx + i
            if free(n):
                seen[n] = 1
                q.append(n)
    seeds = len(q)
    reached = 0
    tg = {k: {"cells": 0, "first": None} for k in TARGETS}
    last = time.time()
    while q:
        n = q.popleft()
        reached += 1
        x, y, zb = xyz(n)
        tk = in_target(x, y, zb)
        if tk:
            e = tg[tk]
            e["cells"] += 1
            if e["first"] is None:
                path, m = [], n
                while m != -1 and len(path) < 3000:
                    path.append([round(v, 2) for v in xyz(m)])
                    m = parent[m]
                e["first"] = {"cell_bl_m": [round(x, 2), round(y, 2), round(zb, 2)], "path_every_10": path[::10]}
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
            unreal.log(f"V8F_FLOOD {mode} r{int(r)} reached {reached} queue {len(q)}")
    # the northmost reached Y per X column band (1 m), any height: where the reachable space ends
    north = {}
    for n in range(N):
        if seen[n]:
            x, y, zb = xyz(n)
            b = int(math.floor(x))
            if y > north.get(b, -1):
                north[b] = round(y, 2)
    return {"mode": mode, "r_cm": r, "grid": {"x": [x0, x1], "y": [y0, y1], "bottom": [zb0, zb1], "dx": dx, "dz": dz, "cells": N},
            "seeds": seeds, "reached": reached, "tested": sum(1 for s in st if s),
            "targets": tg, "leaks": sorted(k for k, v in tg.items() if v["cells"]),
            "northmost_reached_y_per_1m_x": dict(sorted(north.items())), "sec": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------ C. mantles
def run_mantles():
    L = json.loads(LAYOUT.read_text(encoding="utf-8"))
    tq = next(getattr(unreal.TraceTypeQuery, n) for n in dir(unreal.TraceTypeQuery) if n.upper() == "ECC_TRAVERSABLE")
    ign = IGN["1v1"]
    rows, leaks, leaks_ign_path, inside = [], [], [], []
    for m in L["traversal_markers"]:
        name, (x0, x1, y0, y1, z0, z1) = m["name"], m["box"]
        for (cx, cy) in ((x0 + 0.05, y0 + 0.05), (x1 - 0.05, y0 + 0.05), (x0 + 0.05, y1 - 0.05), (x1 - 0.05, y1 - 0.05),
                         ((x0 + x1) / 2, (y0 + y1) / 2)):
            tk = in_target(cx, cy, z1)
            if tk:
                inside.append({"marker": name, "top_point": [round(cx, 2), round(cy, 2), z1], "target": tk})
        edges = {"N": ((x0, y1), (x1, y1), (0, 1)), "S": ((x0, y0), (x1, y0), (0, -1)),
                 "W": ((x0, y0), (x0, y1), (-1, 0)), "E": ((x1, y0), (x1, y1), (1, 0))}
        for ek, ((ax, ay), (bx, by), (ex, ey)) in edges.items():
            ln = math.hypot(bx - ax, by - ay)
            if ln < 0.45:
                continue
            ns = max(1, int(round((ln - 0.4) / 0.25)))
            for s in range(ns + 1):
                u = (0.2 + (ln - 0.4) * s / ns) / ln
                px, py = ax + (bx - ax) * u, ay + (by - ay) * u
                sx, sy = px + ex * 0.55, py + ey * 0.55
                f = line_down(sx, sy, z1 - 0.26, 4.5, ign)
                if not f or f["start_pen"]:
                    continue
                fz = f["imp"].z / 100
                hgt = z1 - fz
                row = {"marker": name, "edge": ek, "ledge_bl_m": [round(px, 2), round(py, 2), z1],
                       "stance_bl_m": [round(sx, 2), round(sy, 2), round(fz, 3)], "height_m": round(hgt, 3)}
                if not (0.26 < hgt <= 2.75):
                    row["result"] = "height out of range"
                    rows.append(row)
                    continue
                if not cap_free_at(sx, sy, fz + 0.02, 30.0, ign):
                    row["result"] = "stance blocked"
                    rows.append(row)
                    continue
                zc = fz * 100 + HH + 2.0
                NT[0] += 1
                fh = ht(unreal.SystemLibrary.capsule_trace_single(CTX, V(sx * 100, -sy * 100, zc),
                                                                  V(sx * 100 - ex * 80, -sy * 100 + ey * 80, zc), 30.0, 60.0, tq,
                                                                  False, [], unreal.DrawDebugTrace.NONE, True))
                if not fh or fh["actor"] != "TRV_" + name:
                    row["result"] = f"forward trace misses ({fh['actor'] if fh else None})"
                    rows.append(row)
                    continue
                lx, ly = px - ex * 0.35, py - ey * 0.35
                land_free = cap_free_at(lx, ly, z1 + 0.02, 30.0, ign)
                # Pawn path: stance centre -> straight up to the ledge top + hh -> over to the landing centre
                a = V(sx * 100, -sy * 100, zc)
                b = V(sx * 100, -sy * 100, z1 * 100 + HH + 3.0)
                c = V(lx * 100, -ly * 100, z1 * 100 + HH + 3.0)
                p1 = cap_sweep(a, b, 30.0, ign)
                p2 = cap_sweep(b, c, 30.0, ign) if p1 is None else None
                path_clear = p1 is None and p2 is None
                blk = p1 or p2
                row.update({"result": "mantle", "landing_bl_m": [round(lx, 2), round(ly, 2), z1], "landing_free": land_free,
                            "path_clear": path_clear, "path_block_actor": blk["actor"] if blk else None,
                            "stance_target": in_target(sx, sy, fz), "landing_target": in_target(lx, ly, z1)})
                if land_free and row["landing_target"] and not row["stance_target"]:
                    leaks_ign_path.append(row)
                    if path_clear:
                        leaks.append(row)
                rows.append(row)
    mant = [r for r in rows if r["result"] == "mantle"]
    return {"n_markers": len(L["traversal_markers"]), "n_samples": len(rows), "n_gasp_valid": len(mant),
            "n_landing_free": sum(1 for r in mant if r["landing_free"]),
            "n_landing_free_and_path_clear": sum(1 for r in mant if r["landing_free"] and r["path_clear"]),
            "markers_with_top_in_target": inside, "leaks": leaks, "leaks_if_path_ignored": leaks_ign_path,
            "landings_in_targets_any": [r for r in mant if r["landing_target"]],
            "passed": not leaks and not leaks_ign_path, "rows": rows}


def main():
    t0 = time.time()
    rep = {"verifier": "independent r8", "parts": PARTS, "targets": {k: list(v) for k, v in TARGETS.items()},
           "n_trv": len(TRV), "group": sorted(a.get_actor_label() for a in GROUP)}
    try:
        if "mantle" in PARTS:
            rep["C_mantles"] = run_mantles()
            unreal.log(f"V8F_MANTLE done passed={rep['C_mantles']['passed']}")
        if "flood" in PARTS:
            rep["B_flood_1v1_r30"] = flood("1v1", 30.0)
        if "flood35" in PARTS:
            rep["B_flood_1v1_r35"] = flood("1v1", 35.0)
        if "floodbr" in PARTS:
            rep["B_flood_br_r30"] = flood("br", 30.0, x0=3.05, x1=40.95, y0=28.05, y1=36.95, zb0=0.05, zb1=7.55)
        if "arcs" in PARTS:
            rep["A_arcs"] = run_arcs()
    except Exception:  # noqa: BLE001
        import traceback
        rep["error"] = traceback.format_exc()[-4000:]
    rep["traces"] = NT[0]
    rep["sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    unreal.log(f"V8F_ALLEY_DONE parts={PARTS} sec={rep['sec']} traces={NT[0]} error={'error' in rep}")


main()
