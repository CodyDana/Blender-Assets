"""LANDSCAPE ROUND (world stage): shared geometry of the world build, plain Python + numpy (no Unreal, no Blender).

Everything here is in the LEVEL frame of layout_showcase.json / LANDSCAPE_PLAN.md: metres, x east, y north, z up,
courtyard z 0. Unreal cm = (x*100, -y*100, z*100); UE yaw = -rot_z (rot_z counter-clockwise from +x, Blender style).

The build-stage deviations from landscape_plan.json (each one measured against the kit's snap rules) live here:
  - WR2 (the forecourt front) sits at y -8.0, not -7.6: the kit's CornerOut arm (1 m) + one 2 m module + a CornerIn arm
    (2 m) must land WR4's face exactly on y -3.0, so the forecourt is 5.0 m deep (plan 4.6 m);
  - WR3's CornerIn is the H6 piece (top 0): WR4 is H6 and the kit has no mixed-height corner;
  - a short Wall_2m_H2 (WR1b) closes the 1 m drop on the forecourt's west edge between WR1 and flight F1;
  - lanterns stand on the CLIFF side of their landings (the kit's own rule, kit_catalog how_to_chain), not the plan's
    river-side spots, which sat on the kerb line.
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
PLAN = json.loads((ROOT / "WorkFiles/dojo/build/landscape/plan/landscape_plan.json").read_text(encoding="utf-8"))
WORLD = ROOT / "WorkFiles/dojo/build/landscape/world"

# ---------------------------------------------------------------------------------------------- landscapes (level m)
LS_VALLEY = {"name": "LS_Valley", "centre": (22.0, 18.0), "n": 2017, "spacing": 0.5, "scale_z_cm": 100.0,
             "sections": 2, "quads": 63}
LS_FAR = {"name": "LS_Far", "centre": (1500.0, 5500.0), "n": 2017, "spacing": 8.0, "scale_z_cm": 1000.0,
          "sections": 2, "quads": 63}
FAR_DROP_M = 30.0            # LS_Far sits this far below LS_Valley inside the valley footprint (plan 3.7)
FAR_EDGE_BAND_M = 24.0       # ... starting this far inside the valley's edge (LS_Far matches the valley at its edge)


def grid_axes(ls):
    """Vertex coordinates of a landscape grid: column c -> x, row r -> y (row 0 = UE local -Y = level NORTH edge)."""
    half = (ls["n"] - 1) * ls["spacing"] / 2.0
    xs = ls["centre"][0] - half + ls["spacing"] * np.arange(ls["n"])
    ys = ls["centre"][1] + half - ls["spacing"] * np.arange(ls["n"])
    return xs, ys


def ue_location_cm(ls):
    """ALandscape location: its local (0, 0) vertex = the min UE X / min UE Y corner = level (xmin, ymax)."""
    half = (ls["n"] - 1) * ls["spacing"] / 2.0
    return ((ls["centre"][0] - half) * 100.0, -(ls["centre"][1] + half) * 100.0, 0.0)


def z_to_u16(z_m, ls):
    return np.clip(np.round(32768.0 + z_m * 100.0 * 128.0 / ls["scale_z_cm"]), 0, 65535).astype(np.uint16)


def u16_to_z(h, ls):
    return (h.astype(np.float64) - 32768.0) * ls["scale_z_cm"] / 128.0 / 100.0


# ---------------------------------------------------------------------------------------------------- river
DEPTH = {"R0": 1.2, "R1": 1.2, "R2": 1.2, "R3": 1.2, "R4": 0.7, "R5": 0.7, "R6": 0.7, "R7": 0.8, "R8": 1.2,
         "R9": 2.0, "R10": 1.5, "R11": 1.5}
# it4: the rapids reach doubled (the engine river material only foams near its MaxFlowVelocity; the plan's 250-350
# cm/s left the white water invisible in it2 / it3): a visual flow value, the water depth / levels unchanged
VEL = {"R0": 100, "R1": 100, "R2": 110, "R3": 140, "R4": 520, "R5": 700, "R6": 750, "R7": 600, "R8": 160,
       "R9": 40, "R10": 80, "R11": 80}
# the valley continues past the plan's visual ends so the water does not stop in view
EXTRA_UP = {"id": "R-1", "xy": [430.0, 720.0], "water_z": 0.2, "width_m": 30.0}
EXTRA_DOWN = {"id": "R12", "xy": [-190.0, -420.0], "water_z": -10.8, "width_m": 32.0}


# LANDSCAPE FIX ROUND (judge delta 1): the reference's river is ~35 % of the CAM_LandscapeRef frame width where it
# leaves the frame (ours measured ~55 % at the plan's widths): the tail-out, the run and the pool are narrowed
WIDTH_FIX = {"R7": 13.0, "R8": 12.0, "R9": 14.0, "R10": 19.0}
# ... and the rapids reach steps down over ledges (the reference's water drops between boulder bars) instead of one
# even 3.9 % slope: the same R4 -> R7.4 drop, as RAPIDS_STEPS level runs, each ending in a short pour
RAPIDS_KEYS = (4.0, 7.4)
RAPIDS_STEPS = 7
RAPIDS_POUR = 0.22          # the share of each step's length the drop takes


def river_points():
    pts = [dict(EXTRA_UP, depth=1.2, vel=100)]
    for p in PLAN["river"]["spline"]:
        pts.append({"id": p["id"], "xy": p["xy"], "water_z": p["water_z"],
                    "width_m": WIDTH_FIX.get(p["id"], p["width_m"]),
                    "depth": DEPTH[p["id"]], "vel": VEL[p["id"]]})
    pts.append(dict(EXTRA_DOWN, depth=1.5, vel=80))
    return pts


def catmull(pts, step=2.0):
    """Centripetal Catmull-Rom through the river points (x, y) with every scalar interpolated along; dense samples
    about `step` metres apart. Returns arrays x, y, water_z, width, depth, vel, key (the source point index as float)."""
    P = np.array([p["xy"] for p in pts], float)
    S = np.array([[p["water_z"], p["width_m"], p["depth"], p["vel"]] for p in pts], float)
    Pe = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = Pe[i], Pe[i + 1], Pe[i + 2], Pe[i + 3]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** 0.5
        t2 = t1 + np.linalg.norm(p2 - p1) ** 0.5
        t3 = t2 + np.linalg.norm(p3 - p2) ** 0.5
        n = max(2, int(math.ceil(np.linalg.norm(p2 - p1) / step)))
        for k in range(n):
            u = k / n
            t = t1 + (t2 - t1) * u
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            c = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2
            s = S[i] * (1 - u) + S[i + 1] * u
            out.append([c[0], c[1], *s, i + u])
    c = P[-1]
    out.append([c[0], c[1], *S[-1], len(P) - 1.0])
    return np.array(out)


def stepped(R):
    """The rapids' water z as level runs + pours (RAPIDS_STEPS over RAPIDS_KEYS; the reach's total drop is kept)."""
    R = R.copy()
    sel = np.where((R[:, 6] >= RAPIDS_KEYS[0]) & (R[:, 6] <= RAPIDS_KEYS[1]))[0]
    if len(sel) < 4:
        return R
    seg = np.r_[0.0, np.hypot(np.diff(R[sel, 0]), np.diff(R[sel, 1]))]
    t = np.cumsum(seg) / max(seg.sum(), 1e-6)
    z0, z1 = R[sel[0], 2], R[sel[-1], 2]
    u = t * RAPIDS_STEPS
    k = np.minimum(np.floor(u), RAPIDS_STEPS - 1)
    f = u - k
    pour = np.clip((f - (1.0 - RAPIDS_POUR)) / RAPIDS_POUR, 0.0, 1.0)
    pour = pour * pour * (3 - 2 * pour)
    level = (k + pour) / RAPIDS_STEPS
    level[-1] = 1.0
    R[sel, 2] = z0 + (z1 - z0) * level
    return R


RIVER = stepped(catmull(river_points(), 2.0))


def river_fields(X, Y, chunk=40000):
    """For points (X, Y): distance to the river centre line, the interpolated water z / width / depth / velocity at the
    nearest point, and the side (+1 = left bank facing downstream, -1 = right bank: the compound's side)."""
    ax, ay = RIVER[:-1, 0], RIVER[:-1, 1]
    bx, by = RIVER[1:, 0], RIVER[1:, 1]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    xf, yf = X.ravel(), Y.ravel()
    n = xf.size
    D = np.empty(n)
    F = np.empty((n, 4))
    SIDE = np.empty(n)
    for s in range(0, n, chunk):
        px = xf[s:s + chunk, None]
        py = yf[s:s + chunk, None]
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
        qx, qy = ax + t * dx, ay + t * dy
        d2 = (px - qx) ** 2 + (py - qy) ** 2
        j = np.argmin(d2, axis=1)
        r = np.arange(j.size)
        tj = t[r, j]
        D[s:s + chunk] = np.sqrt(d2[r, j])
        F[s:s + chunk] = RIVER[j, 2:6] * (1 - tj[:, None]) + RIVER[j + 1, 2:6] * tj[:, None]
        cr = dx[j] * (py[:, 0] - ay[j]) - dy[j] * (px[:, 0] - ax[j])
        SIDE[s:s + chunk] = np.where(cr >= 0, 1.0, -1.0)
    sh = X.shape
    return D.reshape(sh), F[:, 0].reshape(sh), F[:, 1].reshape(sh), F[:, 2].reshape(sh), F[:, 3].reshape(sh), \
        SIDE.reshape(sh)


# ---------------------------------------------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def interp(x, xp, fp):
    return np.interp(x, xp, fp)


def seg_dist(X, Y, a, b):
    """Distance from points to segment a-b, the along parameter s (m) and the signed side distance."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    s = (X - ax) * ux + (Y - ay) * uy
    t = (X - ax) * (-uy) + (Y - ay) * ux      # + = left of a->b
    sc = np.clip(s, 0, L)
    d = np.hypot(X - (ax + sc * ux), Y - (ay + sc * uy))
    return d, s, t, L


def poly_contains(X, Y, poly):
    poly = np.asarray(poly, float)
    inside = np.zeros(X.shape, bool)
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        cond = ((yi > Y) != (yj > Y)) & (X < (xj - xi) * (Y - yi) / (yj - yi + 1e-12) + xi)
        inside ^= cond
        j = i
    return inside


def poly_dist(X, Y, poly):
    d = np.full(X.shape, 1e9)
    n = len(poly)
    for i in range(n):
        dd, _, _, _ = seg_dist(X, Y, poly[i], poly[(i + 1) % n])
        d = np.minimum(d, dd)
    return d


def rect_dist(X, Y, x0, x1, y0, y1):
    dx = np.maximum(np.maximum(x0 - X, 0), X - x1)
    dy = np.maximum(np.maximum(y0 - Y, 0), Y - y1)
    return np.hypot(dx, dy)


# ---------------------------------------------------------------------------------------------------- layout data
# HALL + ARMORY round (2026-10-01; WorkFiles/shared/armory_hall/interface.json site.terrace_and_terrain): the hall
# extends 11 m back for the armory interior, the compound's north wall moves +11 m (y 47-48) and the upper terrace runs
# on to y 56 (WR5 + 4 + 4 + 2 + 2 m); the north hill's spot heights move with it (0 at 56, +6 at 72, +20 at 112, then
# the old profile from y 200). HALL_ARMORY False gives the landscape round's terrain back.
HALL_ARMORY = True
TERRACE_N = 56.0 if HALL_ARMORY else 44.0
TERRACE = (-7.0, 49.0, -3.0, TERRACE_N)        # upper terrace z 0
# the landscape sits at -0.30 under the kit ground (the gravel planes are at z 0). Hall + armory: the old north wall
# (y 36-37) has moved, so the pad ends 0.5 m inside the last gravel row (y 36.0) instead of under the wall's footing,
# and a pad runs under the moved alley's gravel (x 10.5-35.5, y 45-47) to under the new wall footing (y 47.5)
COMPOUND_LOW = (-0.9, 44.9, -0.9, 35.5 if HALL_ARMORY else 36.9)
ALLEY_LOW = (10.9, 35.1, 44.9, 47.5, -0.30) if HALL_ARMORY else None
UNDER_EXTENSION = (14.6, 29.4, 33.8, 45.4, -0.30) if HALL_ARMORY else None   # landscape under the extension's floor
if HALL_ARMORY:   # the two north-strip cherry slots move back with the strip (+11 m: y 42 -> 53)
    for _s in PLAN["cherry_slots"]["slots"]:
        if _s["id"] in ("CS19", "CS20") and abs(_s["loc"][1] - 42.0) < 1e-6:
            _s["loc"] = [_s["loc"][0], _s["loc"][1] + 11.0] + list(_s["loc"][2:])
HILL_SPOTS = (([56, 72, 112, 200, 400, 700, 1500, 4000] if HALL_ARMORY else [44, 60, 100, 200, 400, 700, 1500, 4000]),
              [0, 6, 20, 45, 90, 130, 200, 320])
# hall + armory FINISH (2026-10-01; the verify's carry-over: from CAM_Ref2Match the forest / hill above the main roof
# sank with the +12 m move: 3.5 % of the frame changed, the tall cypress left of the ridge and the fir band lower). The
# hill's NATURAL surface returns to the landscape round's terrain (TERRACE_OLD / HILL_SPOTS_OLD) through a smoothstep
# band y 56 -> 72 behind the moved terrace (a steeper shoulder, the extension untouched); north of y 72 the terrain is
# the landscape round's again (make_terrain.natural). The trees still lower in the band are re-seated along the
# CAM_Ref2Match view rays (hall_armory_world.py).
TERRACE_OLD = (-7.0, 49.0, -3.0, 44.0)
HILL_SPOTS_OLD = ([44, 60, 100, 200, 400, 700, 1500, 4000], [0, 6, 20, 45, 90, 130, 200, 320])
HILL_RESTORE = (56.0, 72.0) if HALL_ARMORY else None
FORECOURT = (12.0, 34.0, -8.0, -3.0, -0.5)       # x0 x1 y0 y1 z (WR2 at y -8.0, see the module note)
W = 1.8                                          # path width

# stair path pieces (level m): kind, piece, pivot (x, y, z), rot_z (deg CCW, Blender), plus the walk footprint
#   flights: pivot = the bottom riser foot ('in' snap); local +Y = up the flight
#   landings: pivot = centre, top at z
PATH = [
    ("flight", "SM_DKT_Stair_Flight_W180_R050", (21.1, -4.0, -0.5), 0.0, "G1"),
    ("flight", "SM_DKT_Stair_Flight_W180_R050", (22.9, -4.0, -0.5), 0.0, "G2"),
    ("flight", "SM_DKT_Stair_Flight_W180_R100", (10.0, -6.5, -1.5), -90.0, "F1"),
    ("landing", "SM_DKT_Stair_LandingL_W180", (9.1, -6.5, -1.5), 0.0, "L1"),
    ("landing", "SM_DKT_Stair_LandingSB_W180", (9.1, -9.4, -1.5), 90.0, "P1a"),
    ("flight", "SM_DKT_Stair_Flight_W180_R050", (9.1, -12.4, -2.0), 0.0, "F2"),
    ("landing", "SM_DKT_Stair_Landing_W180", (9.1, -13.3, -2.0), 0.0, "L2"),
    ("landing", "SM_DKT_Stair_LandingSB_W180", (9.1, -16.2, -2.0), 90.0, "P1b1"),
    ("landing", "SM_DKT_Stair_LandingSB_W180", (9.1, -20.2, -2.0), 90.0, "P1b2"),
    ("landing", "SM_DKT_Stair_Landing_W180", (9.1, -23.1, -2.0), 0.0, "L3"),
    ("flight", "SM_DKT_Stair_Flight_W180_R200", (9.1, -28.0, -4.0), 0.0, "F3"),
    ("landing", "SM_DKT_Stair_LandingL_W180", (9.1, -28.9, -4.0), 180.0, "L4"),
    ("landing", "SM_DKT_Stair_LandingSB_W180", (6.2, -28.9, -4.0), 0.0, "P2"),
    ("landing", "SM_DKT_Stair_LandingL_W180", (3.3, -28.9, -4.0), 0.0, "L5"),
    ("flight", "SM_DKT_Stair_Flight_W180_R200", (3.3, -33.8, -6.0), 0.0, "F4"),
    ("landing", "SM_DKT_Stair_Landing_W180", (3.3, -34.7, -6.0), 0.0, "L6"),
    ("flight", "SM_DKT_Stair_Flight_W180_R100", (3.3, -37.6, -7.0), 0.0, "F5"),
    ("landing", "SM_DKT_Stair_Landing_W180", (3.3, -38.5, -7.0), 0.0, "L7"),
]
FLIGHT_RUN_RISE = {"R050": (1.0, 0.5), "R100": (2.0, 1.0), "R200": (4.0, 2.0)}


def rotz(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def path_footprints():
    """Each path piece as (cx, cy, half_len_along, half_width, rot_deg, z0, z1): an oriented box whose walking level
    goes from z0 at its local -Y end to z1 at its +Y end (flights) or is flat (landings)."""
    out = []
    for kind, piece, (x, y, z), rot, pid in PATH:
        if kind == "flight":
            run, rise = FLIGHT_RUN_RISE[piece.rsplit("_", 1)[1]]
            c = rotz((0.0, run / 2.0), rot)
            out.append({"id": pid, "cx": x + c[0], "cy": y + c[1], "hl": run / 2.0, "hw": W / 2.0, "rot": rot,
                        "z0": z, "z1": z + rise, "kind": kind})
        else:
            hl = 2.0 if "SB" in piece else W / 2.0     # LandingSB: 4.0 m along its local X
            # express the landing box with its 'along' axis on local Y: SB pieces are 4 m on local X
            if "SB" in piece:
                out.append({"id": pid, "cx": x, "cy": y, "hl": W / 2.0, "hw": hl, "rot": rot, "z0": z, "z1": z,
                            "kind": kind})
            else:
                out.append({"id": pid, "cx": x, "cy": y, "hl": W / 2.0, "hw": W / 2.0, "rot": rot, "z0": z, "z1": z,
                            "kind": kind})
    return out


def box_local(X, Y, fp):
    """Local (u across, v along) coordinates of points in an oriented footprint box."""
    c, s = math.cos(math.radians(fp["rot"])), math.sin(math.radians(fp["rot"]))
    dx, dy = X - fp["cx"], Y - fp["cy"]
    u = dx * c + dy * s
    v = -dx * s + dy * c
    return u, v


# ishigaki runs: (id, pieces [(piece, (x, y), rot_z)], top z, face outward normal, foot z nominal)
def wall_runs():
    R = []

    def run(rid, top, H, start, rot, seq, foot):
        x, y = start
        pcs = []
        for p in seq:
            pcs.append((p, (x, y), rot))
            if p.startswith("SM_DKT_Wall_4m"):
                d = rotz((4.0, 0.0), rot)
            elif p.startswith("SM_DKT_Wall_2m"):
                d = rotz((2.0, 0.0), rot)
            elif "EndL" in p:
                d = rotz((1.0, 0.0), rot)
            elif "CornerOut" in p:
                d = rotz((1.0, 1.0), rot)
                rot += 90.0
            elif "CornerIn" in p:
                d = rotz((2.0, -2.0), rot)
                rot -= 90.0
            else:
                d = (0.0, 0.0)
            x, y = x + d[0], y + d[1]
        R.append({"id": rid, "top": top, "H": H, "foot": foot, "pieces": pcs})

    run("WR1", 0.0, 2, (4.0, -3.0), 0.0,
        ["SM_DKT_Wall_EndL_H2", "SM_DKT_Wall_4m_H2", "SM_DKT_Wall_2m_H2", "SM_DKT_Wall_EndR_H2"], -2.0)
    run("WR1b", -0.5, 2, (12.0, -3.4), -90.0, ["SM_DKT_Wall_2m_H2"], -2.5)
    run("WR2_WR3_WR4_WR5", None, None, (12.0, -8.0), 0.0,
        ["SM_DKT_Wall_EndL_H4"] + ["SM_DKT_Wall_4m_H4"] * 5 + ["SM_DKT_Wall_CornerOut_H4", "SM_DKT_Wall_2m_H4",
                                                                "SM_DKT_Wall_CornerIn_H6"]
        + ["SM_DKT_Wall_4m_H6"] * 3 + ["SM_DKT_Wall_CornerOut_H6"] + ["SM_DKT_Wall_4m_H6"] * 3
        + ["SM_DKT_Wall_4m_H4"] * 5 + ["SM_DKT_Wall_4m_H3"] * 3 + ["SM_DKT_Wall_2m_H3"]
        # hall + armory round: WR5 runs on + 4 + 4 + 2 + 2 m to the new terrace edge y 56
        + (["SM_DKT_Wall_4m_H3"] * 2 + ["SM_DKT_Wall_2m_H3"] * 2 if HALL_ARMORY else []) + ["SM_DKT_Wall_EndR_H3"], None)
    # pivot z: the module top; WR2 / WR3's H4 pieces top -0.5, everything from the CornerIn_H6 on top 0
    out = []
    for r in R:
        for i, (p, xy, rot) in enumerate(r["pieces"]):
            if r["id"] == "WR2_WR3_WR4_WR5":
                top = -0.5 if i <= 7 else 0.0
            else:
                top = r["top"]
            out.append({"run": r["id"], "piece": p, "xy": xy, "rot": rot, "top": top})
    return out


# face lines for the terrain (outward normal side = the low ground): (a, b, top, foot)
WALL_FACES = [
    {"id": "WR1", "a": (4.0, -3.0), "b": (12.4, -3.0), "top": 0.0, "foot": -2.0},
    {"id": "WR1b", "a": (12.0, -3.4), "b": (12.0, -5.4), "top": -0.5, "foot": -2.5},
    {"id": "WR2", "a": (12.0, -8.0), "b": (34.0, -8.0), "top": -0.5, "foot": -4.5},
    {"id": "WR3", "a": (34.0, -8.0), "b": (34.0, -3.0), "top": -0.5, "foot": -4.5},
    {"id": "WR4", "a": (34.0, -3.0), "b": (49.0, -3.0), "top": 0.0, "foot": -6.0},
    {"id": "WR5a", "a": (49.0, -3.0), "b": (49.0, 10.0), "top": 0.0, "foot": -6.0},
    {"id": "WR5b", "a": (49.0, 10.0), "b": (49.0, 30.0), "top": 0.0, "foot": -4.0},
    {"id": "WR5c", "a": (49.0, 30.0), "b": (49.0, TERRACE_N + 1.2), "top": 0.0, "foot": -3.0},   # hall + armory: 45.2 -> 57.2
]
# the cliff (C1) top surface: spot heights (plan 3.6 / 3.7) + the SW knoll at the verge
CLIFF_POLY = [(-14.0, -3.0), (4.0, -3.0), (7.9, -7.0), (7.9, -28.0), (1.7, -29.5), (1.7, -37.5), (-6.0, -44.0),
              (-16.0, -40.0)]
CLIFF_SPOTS = [(-8, -5, 1.5), (-2, -12, 2.5), (-8, -20, 0.5), (0, -24, 1.5), (-2, -36, -1.0), (-6, -40, -3.0),
               (2, -4.5, 1.6), (-4, -3.6, 1.0), (5.5, -10, 2.4), (5.5, -18, 2.2), (6.0, -25, 1.4), (0.5, -31, 0.6),
               (0.0, -35, -0.6)]
