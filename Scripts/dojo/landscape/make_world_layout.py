"""LANDSCAPE ROUND (world stage): every placement of the world build as data (plain Python + numpy), read by
dj_ls_world.py. Level frame (metres, x east, y north, z up); the Unreal step converts (x*100, -y*100, z*100), yaw = -rot.
Ground heights come from the SAME heightmaps the landscapes are built from (world/terrain/*.r16), so every object sits
on the terrain it will actually meet.

Groups (LANDSCAPE_PLAN section in brackets):
  walls       ishigaki runs from our stone kit (3.3)             stair       the cliff stair path, kit pieces only (3.4)
  lanterns    6 path lanterns + their lights (3.4)               pines       P01-P08 SM_DKN (3.9)
  rocks       Fishermans SM_Rocks_01..04 (owned) as the hero / rapids / bank / cliff boulders (3.6)
  cherry      20 hidden CherrySlot markers (3.10)                boundary    B1-B8, Dojo/Boundary_1v1 (3.12)
  forest      ISM firs FZ1-FZ3 + billboards (FZ4 / far fill) + 5 Megaplants cypress (3.11)
  cover       ISM grass, bushes, pebbles (3.11)                  far         SM_Mountain_01 far-ridge masses (3.8)
  water       the WaterBodyRiver spline (3.5)                    fx          mist / spray anchors, the low fog volume
Also writes world/terrain/T_DJL_ValleyMask.png (R dirt, G forest floor, B moss, A river bed; 2048^2 over LS_Valley).
Run: py -3 -B make_world_layout.py        Out: world/json/world_layout.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ls_geo as G  # noqa: E402

TER = G.WORLD / "terrain"
RNG = np.random.default_rng(20260930)
FISH = "/Game/Fishermans_Cabin/Meshes"


class Height:
    def __init__(self, ls, name):
        self.ls = ls
        h = np.fromfile(TER / f"{name}.r16", dtype="<u2").reshape(ls["n"], ls["n"])
        self.z = G.u16_to_z(h, ls)
        self.xs, self.ys = G.grid_axes(ls)

    def __call__(self, x, y):
        s = self.ls["spacing"]
        c = (np.asarray(x, float) - self.xs[0]) / s
        r = (self.ys[0] - np.asarray(y, float)) / s
        c0 = np.clip(np.floor(c).astype(int), 0, self.ls["n"] - 2)
        r0 = np.clip(np.floor(r).astype(int), 0, self.ls["n"] - 2)
        fc, fr = np.clip(c - c0, 0, 1), np.clip(r - r0, 0, 1)
        z = self.z
        return (z[r0, c0] * (1 - fc) * (1 - fr) + z[r0, c0 + 1] * fc * (1 - fr) + z[r0 + 1, c0] * (1 - fc) * fr
                + z[r0 + 1, c0 + 1] * fc * fr)

    def slope_deg(self, x, y, d=None):
        d = d or self.ls["spacing"]
        gx = (self(np.asarray(x) + d, y) - self(np.asarray(x) - d, y)) / (2 * d)
        gy = (self(x, np.asarray(y) + d) - self(x, np.asarray(y) - d)) / (2 * d)
        return np.degrees(np.arctan(np.hypot(gx, gy)))

    def inside(self, x, y, margin=0.0):
        half = (self.ls["n"] - 1) * self.ls["spacing"] / 2.0
        cx, cy = self.ls["centre"]
        return (np.abs(np.asarray(x) - cx) < half - margin) & (np.abs(np.asarray(y) - cy) < half - margin)


HV = Height(G.LS_VALLEY, "LS_Valley")
HF = Height(G.LS_FAR, "LS_Far")


def ground(x, y):
    return np.where(HV.inside(x, y, 2.0), HV(x, y), HF(x, y))


def rec(group, label, mesh, x, y, z, yaw=0.0, scale=1.0, folder=None, collision="block", shadow=True, **kw):
    s = [scale] * 3 if np.isscalar(scale) else list(scale)
    r = {"group": group, "label": label, "mesh": mesh, "loc": [round(float(x), 4), round(float(y), 4), round(float(z), 4)],
         "rot_z": round(float(yaw), 4), "scale": [round(float(v), 5) for v in s], "folder": folder or group,
         "collision": collision, "shadow": shadow}
    r.update(kw)
    return r


# ---------------------------------------------------------------------------------------------------- stone kit
SK = "/Game/DojoKit/StoneKit/Meshes/"


def walls():
    out = []
    for i, w in enumerate(G.wall_runs()):
        out.append(rec("walls", f"{w['run']}_{i:02d}_{w['piece'][7:]}", SK + w["piece"], w["xy"][0], w["xy"][1], w["top"],
                       w["rot"], folder="Landscape/Terrace/Walls"))
    # the forecourt's north edge: a 0.5 m dressed step course (WallFoot) facing south, tops at z 0, with the gate stair
    for x, p in ((12.0, "4m"), (16.0, "4m"), (24.0, "4m"), (28.0, "4m"), (32.0, "2m")):
        out.append(rec("walls", f"ForecourtStep_{x:g}", SK + f"SM_DKT_WallFoot_{p}", x, -3.4, -0.06, 0.0,
                       folder="Landscape/Terrace/Walls"))
    return out


def stair():
    out = []
    for kind, piece, (x, y, z), rot, pid in G.PATH:
        out.append(rec("stair", f"{pid}_{piece[13:]}", SK + piece, x, y, z, rot, folder="Landscape/StairPath"))
    # gate stair outer cheeks (tall), then the low cliff-side cheeks, kerbs, rails
    C = [("SM_DKT_Stair_Cheek_R050", 20.0, -4.0, -0.5, 0.0), ("SM_DKT_Stair_Cheek_R050", 24.0, -4.0, -0.5, 0.0),
         ("SM_DKT_Stair_Cheek_Low_R100", 10.0, -5.4, -1.5, -90.0),
         ("SM_DKT_Stair_Cheek_Low_R050", 8.0, -12.4, -2.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_R200", 8.0, -28.0, -4.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_R200", 2.2, -33.8, -6.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_R100", 2.2, -37.6, -7.0, 0.0),
         # landing / path sides on the cliff (west)
         ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -7.4, -1.5, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -11.4, -1.5, 0.0), ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -9.6, -1.5, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -14.2, -2.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -22.2, -2.0, 0.0), ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -20.4, -2.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -18.6, -2.0, 0.0), ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -16.8, -2.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L120", 8.0, -15.4, -2.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 8.0, -24.0, -2.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 4.2, -27.8, -4.0, -90.0), ("SM_DKT_Stair_Cheek_Low_L180", 6.0, -27.8, -4.0, -90.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 2.4, -27.8, -4.0, -90.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 2.2, -29.8, -4.0, 0.0),
         ("SM_DKT_Stair_Cheek_Low_L180", 2.2, -35.6, -6.0, 0.0)]
    for i, (p, x, y, z, r) in enumerate(C):
        out.append(rec("stair", f"Cheek_{i:02d}_{p[14:]}", SK + p, x, y, z, r, folder="Landscape/StairPath/Cheeks"))
    K = [(10.115, -11.4, -1.5, 0.0), (10.115, -9.6, -1.5, 0.0),
         (10.115, -14.2, -2.0, 0.0),
         (10.115, -22.2, -2.0, 0.0), (10.115, -20.4, -2.0, 0.0), (10.115, -18.6, -2.0, 0.0), (10.115, -16.8, -2.0, 0.0),
         (10.115, -24.0, -2.0, 0.0),
         (10.115, -29.8, -4.0, 0.0), (8.2, -29.915, -4.0, -90.0),
         (4.2, -29.915, -4.0, -90.0), (6.0, -29.915, -4.0, -90.0),
         (4.315, -35.6, -6.0, 0.0),
         (4.315, -39.4, -7.0, 0.0), (2.4, -39.515, -7.0, -90.0), (2.285, -37.6, -7.0, 180.0)]
    for i, (x, y, z, r) in enumerate(K):
        out.append(rec("stair", f"Kerb_{i:02d}", SK + "SM_DKT_Stair_Kerb_L180", x, y, z, r,
                       folder="Landscape/StairPath/Kerbs"))
    R = [("SM_DKT_Stair_Rail_Slope_R200", 9.8333, -28.1667, -4.0, 0.0),
         ("SM_DKT_Stair_Rail_Slope_R200", 4.0333, -33.9667, -6.0, 0.0),
         ("SM_DKT_Stair_Rail_Slope_R100", 4.0333, -37.7667, -7.0, 0.0),
         ("SM_DKT_Stair_Rail_Flat_L180", 9.8333, -24.1667, -2.0, 0.0),
         ("SM_DKT_Stair_Rail_Flat_L180", 4.0333, -35.7667, -6.0, 0.0),
         ("SM_DKT_Stair_Rail_Flat_L150", 9.8333, -28.1667, -4.0, 180.0),
         ("SM_DKT_Stair_Rail_CornerPost", 9.8333, -29.6333, -4.0, 0.0)]
    for y0 in (-22.3667, -20.5667, -18.7667, -16.9667):
        R.append(("SM_DKT_Stair_Rail_EndPost", 9.8333, y0, -2.0, 0.0))
        R.append(("SM_DKT_Stair_Rail_Flat_L180", 9.8333, y0, -2.0, 0.0))
    R.append(("SM_DKT_Stair_Rail_EndPost", 9.8333, -15.1667, -2.0, 0.0))
    for x0 in (9.8333, 8.0333, 6.2333):
        R.append(("SM_DKT_Stair_Rail_Flat_L180", x0, -29.6333, -4.0, 90.0))
        R.append(("SM_DKT_Stair_Rail_EndPost", x0 - 1.8, -29.6333, -4.0, 0.0))
    for i, (p, x, y, z, r) in enumerate(R):
        out.append(rec("stair", f"Rail_{i:02d}_{p[18:]}", SK + p, x, y, z, r, folder="Landscape/StairPath/Rails",
                       collision="thin"))
    return out


LANTERNS = [("Timber", 19.2, -4.6, -0.5, 0.0, "gate stair (left)"), ("Timber", 8.55, -5.95, -1.5, 90.0, "L1"),
            ("Timber", 8.55, -13.3, -2.0, 90.0, "L2"), ("Stone", 8.6, -23.1, -2.0, 90.0, "L3 (long-flight head)"),
            ("Timber", 2.75, -34.7, -6.0, 90.0, "L6"), ("Stone", 2.75, -38.9, -7.0, 90.0, "L7 (river landing)")]
# hall + armory round (2026-10-01; the landscape verify's carry-over): lanterns 3 / 4 / 6 stood 0.35-0.4 m inside the
# 1.8 m tread (the centre lane snagged them; 0.90 m clear at L3): they move to the cheek side, off the tread. L2 / L3:
# onto the low cliff-side cheek (x 7.8-8.2, top walk + 0.117), centre x 7.95, so even the lantern's widest hull
# (r 0.24 / 0.242) ends at x 8.19 < the tread edge 8.2. L7: onto the west kerb / ground, centre x 2.15 (hulls 1.91-2.39
# against the tread edge 2.4); z = the kerb top or the ground there, whichever is higher (hall_armory_world.py).
LANTERN_MOVES = {3: (7.95, -13.3, -2.0 + 0.117), 4: (7.95, -23.1, -2.0 + 0.117), 6: (2.15, -38.9, None)}
# hall + armory FINISH (2026-10-01, the verify's carry-over): lantern 5 (L6, timber) stood at x 2.75, 0.35 m inside the
# L6 landing's tread (x 2.4-4.2) and snagged the r 35 centre lane. It moves onto the west low cheek Cheek_21 (x 2.0-2.4,
# y -35.6..-33.8, top walk + 0.117) at x 2.15 like L7: its widest hull (r 0.24) ends at x 2.39 < the tread edge 2.4.
LANTERN_MOVES[5] = (2.15, -34.7, -6.0 + 0.117)
if G.HALL_ARMORY:
    LANTERNS = [(k, *(LANTERN_MOVES[i + 1][:2] if i + 1 in LANTERN_MOVES else (x, y)),
                 (LANTERN_MOVES[i + 1][2] if (i + 1 in LANTERN_MOVES and LANTERN_MOVES[i + 1][2] is not None) else z),
                 r, n) for i, (k, x, y, z, r, n) in enumerate(LANTERNS)]


def lanterns():
    out, lights = [], []
    for i, (kind, x, y, z, r, note) in enumerate(LANTERNS):
        out.append(rec("lanterns", f"Lantern_{i + 1}_{kind}_{note.split()[0]}", SK + f"SM_DKT_Stair_Lantern_{kind}", x, y, z,
                       r, folder="Landscape/StairPath/Lanterns", collision="thin", note=note))
        lz = 1.02 if kind == "Timber" else 0.6
        lights.append({"name": f"Light_PathLantern_{i + 1}", "loc": [x, y, z + lz], "kelvin": 2550.0,
                       "candela_rel_lantern_tall": 0.55, "radius_m": 6.0, "shadows": False, "note": note})
    return out, lights


# ---------------------------------------------------------------------------------------------------- pines
PINES = [("P01", "PineA1", 26.0, -4.6, 200, 1.10, "A"), ("P02", "PineC1", 10.8, -2.1, 135, 1.00, "C"),
         ("P03", "PineD1", 5.8, -17.5, 70, 1.15, "D"), ("P04", "PineD2", 13.8, -30.5, 250, 1.20, "D"),
         ("P05", "PineB1", -4.5, 9.0, 30, 1.20, "B"), ("P06", "PineC2", 47.0, 3.0, 290, 1.00, "C"),
         ("P07", "PineB2", 47.0, 24.0, 160, 1.15, "B"), ("P08", "PineA2", -3.5, 33.0, 10, 1.25, "A")]


def pines():
    out = []
    PM = "/Game/DojoKit/Pines/Meshes/"
    for pid, v, x, y, yaw, s, mnd in PINES:
        z = float(ground(x, y))
        if -1.0 <= x <= 49.0 and -3.0 <= y <= G.TERRACE[3]:
            z = 0.0
        if 12 <= x <= 34 and -8 <= y <= -3.5:
            z = -0.5
        parts = [("Trunk", "trunk"), ("Foliage", "nocollision")] + ([("Rock", "block")] if v.startswith("PineD") else [])
        for part, col in parts:
            out.append(rec("pines", f"{pid}_{v}_{part}", PM + f"SM_DKN_{v}_{part}", x, y, z, yaw, s, folder=f"Landscape/Pines/{pid}",
                           collision=col, wpo_disable_cm=5000.0 if part == "Foliage" else None,
                           shadow_invalidation="Rigid" if part == "Foliage" else None))
        out.append(rec("pines", f"{pid}_{v}_Mound", PM + f"SM_DKN_BaseMound_{mnd}", x, y, z, yaw, s,
                       folder=f"Landscape/Pines/{pid}", collision="lowblock"))
    return out


# ---------------------------------------------------------------------------------------------------- rocks
ROCK = [f"{FISH}/Rocks/SM_Rocks_0{i}" for i in (1, 2, 3)]
SLAB = f"{FISH}/Rocks/SM_Rocks_04"
ROCK_MI = "/Game/DojoLandscape/Materials/MI_DJL_Rocks_Granite"


def rfields(x, y):
    X, Y = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float))
    return G.river_fields(X, Y)


def rock(label, x, y, size, bury=0.25, folder="Landscape/Rocks", mesh=None, tilt=8.0, **kw):
    m = mesh or ROCK[int(RNG.integers(0, 3))]
    return rec("rocks", label, m, x, y, float(ground(x, y)), float(RNG.uniform(0, 360)), 1.0, folder=folder,
               size_m=round(float(size), 3), bury=bury, pitch=round(float(RNG.uniform(-tilt, tilt)), 2),
               roll=round(float(RNG.uniform(-tilt, tilt)), 2), material=ROCK_MI, **kw)


def path_clear(x, y, m):
    for fp in G.path_footprints():
        u, v = G.box_local(np.array([x]), np.array([y]), fp)
        if abs(u[0]) < fp["hw"] + m and abs(v[0]) < fp["hl"] + m:
            return False
    return True


def rocks():
    out = []
    # 21 hero targets (plan): size 2 x radius; in-water ones sunk so 30-40 % emerge
    for i, h in enumerate(G.PLAN["hero_boulders"]):
        x, y = h["xy"]
        D, WZ, WID = [a[0] for a in rfields(x, y)[:3]]
        inw = D < WID / 2
        out.append(rock(f"Hero_{i + 1:02d}", x, y, 2.1 * h["plan_radius_m"], bury=0.3 if inw else 0.22,
                        folder="Landscape/Rocks/Hero", in_water=bool(inw), water_z=round(float(WZ), 3)))
    # extra rapids stones R4..R7 (smaller, in the channel)
    k = 0
    idx = np.where((G.RIVER[:, 6] >= 4.0) & (G.RIVER[:, 6] <= 7.4))[0]
    while k < 9:
        j = int(RNG.choice(idx))
        cx, cy, wz, wid = G.RIVER[j, 0], G.RIVER[j, 1], G.RIVER[j, 2], G.RIVER[j, 3]
        a = RNG.uniform(0, 2 * math.pi)
        rr = RNG.uniform(0, wid / 2 - 1.5)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        out.append(rock(f"Rapids_{k + 1:02d}", x, y, RNG.uniform(0.55, 1.1), bury=0.35, folder="Landscape/Rocks/Rapids",
                        in_water=True, water_z=round(float(wz), 3)))
        k += 1
    # BF3 mossy bank between the stair and the rapids
    k = 0
    poly = [(10.5, -8), (26, -10), (30, -24), (20, -44), (12, -40), (11, -24)]
    while k < 9:
        x, y = RNG.uniform(10.5, 30), RNG.uniform(-44, -8)
        if not G.poly_contains(np.array([x]), np.array([y]), poly)[0] or not path_clear(x, y, 2.2):
            continue
        D, WZ, WID = [a[0] for a in rfields(x, y)[:3]]
        if D < WID / 2 + 1.0:
            continue
        out.append(rock(f"Bank_{k + 1:02d}", x, y, RNG.uniform(1.0, 2.4), bury=0.3, folder="Landscape/Rocks/Bank"))
        k += 1
    # C1 cliff face chunks (the reference's rounded granite cliff) set into the face west of the path
    k = 0
    for y in np.arange(-8.2, -27.0, -2.3):
        out.append(rock(f"Cliff_{k + 1:02d}", 5.6 + RNG.uniform(-0.3, 0.2), y + RNG.uniform(-0.4, 0.4),
                        RNG.uniform(2.2, 3.3), bury=0.45, folder="Landscape/Rocks/Cliff", tilt=14.0))
        k += 1
    for y in np.arange(-30.2, -37.5, -2.4):
        out.append(rock(f"Cliff_{k + 1:02d}", -0.6 + RNG.uniform(-0.3, 0.2), y, RNG.uniform(2.4, 3.4), bury=0.45,
                        folder="Landscape/Rocks/Cliff", tilt=14.0))
        k += 1
    for (x, y, s) in ((2.0, -4.2, 1.8), (-1.5, -4.6, 1.5), (3.4, -5.6, 1.3), (-4.5, -12, 1.4), (-1.0, -20, 1.2),
                      (-6, -27, 1.6), (-3.5, -38, 1.5), (-9, -8, 1.2)):
        out.append(rock(f"CliffTop_{k + 1:02d}", x, y, s, bury=0.35, folder="Landscape/Rocks/Cliff"))
        k += 1
    # FIX ROUND (delta 8): the cliff-face chunks sat on the cliff LIP (their xy is on the cliff top, bury 0.45), so one
    # read as a boulder perched over the stair: they now sink to about a quarter of their height over the lip
    # it2 still showed a chunk perched on the lip from the river landing: they now stand at the FOOT of the face (the
    # path-side ground 1 m out from the face, x 7.9 / 1.7), their centres inside the cliff, so their river-side halves
    # bulge out of the face as the reference's stacked rounded cliff boulders
    for r in out:
        if r["label"].startswith("Cliff_"):
            fx = 7.9 if r["loc"][0] > 3.0 else 1.7
            r["loc"][2] = round(float(ground(fx + 1.0, r["loc"][1])), 4)
            r["bury"] = 0.3
    # far-bank edge boulders and the lower west bank by the landing / pool
    k = 0
    for key in np.linspace(3.2, 10.2, 16):
        j = int(np.argmin(np.abs(G.RIVER[:, 6] - key)))
        cx, cy, wz, wid = G.RIVER[j, 0], G.RIVER[j, 1], G.RIVER[j, 2], G.RIVER[j, 3]
        nx, ny = G.RIVER[min(j + 1, len(G.RIVER) - 1), 0] - cx, G.RIVER[min(j + 1, len(G.RIVER) - 1), 1] - cy
        n = math.hypot(nx, ny) or 1.0
        lx, ly = -ny / n, nx / n                  # left of downstream = the far bank
        side = 1.0 if k % 3 else -1.0
        if side < 0 and key < 7.5:
            side = 1.0
        d = wid / 2 + RNG.uniform(0.2, 1.8)
        x, y = cx + side * lx * d, cy + side * ly * d
        if not path_clear(x, y, 2.0):
            continue
        out.append(rock(f"Edge_{k + 1:02d}", x, y, RNG.uniform(1.0, 2.2), bury=0.3, folder="Landscape/Rocks/Edge"))
        k += 1
    for i, (x, y) in enumerate(((10, -52), (0, -70), (14, -60), (-12, -95))):
        out.append(rock(f"BedSlab_{i + 1}", x, y, RNG.uniform(2.0, 2.8), bury=0.4, mesh=SLAB,
                        folder="Landscape/Rocks/Bed", tilt=4.0))
    out += rapids_boulders(out) + bank_boulders(out)
    return out


# Fishermans SM_Rocks_01..03 height / max footprint (asset-registry boxes, plan 1 #6); the actor scale squashes z 0.85
ROCK_H = {ROCK[0]: 169.0 / 191.0, ROCK[1]: 213.0 / 251.0, ROCK[2]: 195.0 / 204.0}


def _spaced(x, y, placed, gap):
    return all(math.hypot(x - px, y - py) > gap for px, py in placed)


def rapids_boulders(existing):
    """FIX ROUND (judge blocker 1 / delta 1): the reference's rapids step over dozens of rounded boulders (ref x480-900,
    y880-1300); the world stage's rapids stones sat 0.15-0.3 m UNDER the water. 34 more channel boulders, owned
    Fishermans rocks 1.3-2.6 m, each with its TOP set 0.35-1.1 m over the local water (top_z) and its foot checked to
    reach the bed (a bigger size when it would float); about half sit on the step lips (the pours) as boulder bars."""
    out = []
    placed = [tuple(r["loc"][:2]) for r in existing]
    R = G.RIVER
    sel = np.where((R[:, 6] >= 4.0) & (R[:, 6] <= 8.3))[0]          # it5: down to key 8.3 with the white water
    dz = np.r_[0.0, np.diff(R[:, 2])]
    lips = [j for j in sel[1:] if dz[j] < -0.05 and dz[j - 1] >= -0.05]          # the first sample of each pour
    targets = []
    for j in lips:
        for f in (-0.36, -0.12, 0.1, 0.33):
            targets.append((j, f + RNG.uniform(-0.06, 0.06)))
    while len(targets) < 56:
        targets.append((int(RNG.choice(sel)), RNG.uniform(-0.42, 0.42)))
    k = 0
    for j, f in targets:
        if k >= 40:
            break
        cx, cy, wz, wid = R[j, 0], R[j, 1], R[j, 2], R[j, 3]
        n2 = R[min(j + 1, len(R) - 1), :2] - R[max(j - 1, 0), :2]
        n2 = n2 / (np.linalg.norm(n2) or 1.0)
        x, y = cx - n2[1] * f * wid, cy + n2[0] * f * wid
        if not _spaced(x, y, placed, 1.9):
            continue
        m = ROCK[int(RNG.integers(0, 3))]
        size = float(RNG.uniform(1.3, 2.2))
        emerge = float(RNG.uniform(0.35, 1.1))       # it1: 0.15-0.75 m read as specks under the foam
        bed = float(ground(x, y))
        top = wz + emerge
        while size * ROCK_H[m] * 0.85 < top - bed + 0.12 and size < 2.6:
            size += 0.1
        if size * ROCK_H[m] * 0.85 < top - bed + 0.05:
            continue
        out.append(rock(f"RapidsB_{k + 1:02d}", x, y, size, bury=0.0, folder="Landscape/Rocks/RapidsBars", mesh=m,
                        in_water=True, water_z=round(float(wz), 3), top_z=round(float(top), 3), tilt=10.0,
                        on_lip=bool(j in lips)))
        placed.append((x, y))
        k += 1
    return out


def bank_boulders(existing):
    """FIX ROUND (delta 2): the reference's banks are boulder-strewn and mossy (right bank x780-1024, y950-1400); ours
    were one smooth slope. 70 owned rocks 0.8-2.6 m along both banks of R3..R9 within 0.5-9 m of the water (more on the
    far bank, which the reference camera sees), seated 25-40 % deep, off the paths and the cherry-slot canopies."""
    out = []
    placed = [tuple(r["loc"][:2]) for r in existing]
    R = G.RIVER
    idx = np.where((R[:, 6] >= 3.0) & (R[:, 6] <= 9.6))[0]
    slots = G.PLAN["cherry_slots"]["slots"]
    k = tries = 0
    while k < 70 and tries < 6000:
        tries += 1
        j = int(RNG.choice(idx))
        cx, cy, wid = R[j, 0], R[j, 1], R[j, 3]
        n2 = R[min(j + 1, len(R) - 1), :2] - R[max(j - 1, 0), :2]
        n2 = n2 / (np.linalg.norm(n2) or 1.0)
        side = 1.0 if RNG.uniform() < 0.68 else -1.0          # +1 = left of downstream = the far bank
        d = wid / 2 + RNG.uniform(0.5, 9.0)
        x, y = cx - side * n2[1] * d, cy + side * n2[0] * d
        if not path_clear(x, y, 1.6) or not _spaced(x, y, placed, 2.4):
            continue
        if side < 0 and (-10 < x < 52 and -9 < y < G.TERRACE[3] + 3.0):
            continue                                            # never on the terrace / against the ishigaki
        if any(math.hypot(x - s["loc"][0], y - s["loc"][1]) < s["canopy_m"] / 2 for s in slots):
            continue
        if HV.slope_deg(np.array([x]), np.array([y]), 1.0)[0] > 55:     # it3: the steep 0-6 m bank too
            continue
        out.append(rock(f"BankB_{k + 1:02d}", x, y, RNG.uniform(0.8, 2.6), bury=RNG.uniform(0.25, 0.4),
                        folder="Landscape/Rocks/Banks"))
        placed.append((x, y))
        k += 1
    return out


# ---------------------------------------------------------------------------------------------------- cherry slots
def cherry():
    out = []
    for s in G.PLAN["cherry_slots"]["slots"]:
        x, y, z = s["loc"]
        if s["id"] in ("CS01", "CS02"):
            z = 0.0
        elif -7 <= x <= 49 and -3 <= y <= G.TERRACE[3]:
            z = 0.0
        else:
            z = float(ground(x, y))
        out.append(rec("cherry", f"CherrySlot_{s['id']}", "/Engine/BasicShapes/Cylinder", x, y, z, 0.0,
                       [s["canopy_m"], s["canopy_m"], s["height_m"]], folder="CherrySlots", collision="none",
                       shadow=False, hidden=True, tags=["CherrySlot", s["id"], "CherrySlotFX"], height_m=s["height_m"],
                       canopy_m=s["canopy_m"], note=s["note"], slot_collision=s["collision"]))
    return out


# ---------------------------------------------------------------------------------------------------- boundary
B_LINES = [("B1_forecourt_front", (11.4, -7.75), (34.25, -7.75), -0.5), ("B2_forecourt_east", (34.25, -7.75), (34.25, -3.0), -0.5),
           ("B3_stair_head", (12.2, -2.75), (12.2, -8.0), -0.5), ("B4_SE_edge", (34.25, -2.75), (48.75, -2.75), 0.0),
           ("B5_east_edge", (48.75, -2.75), (48.75, G.TERRACE[3]), 0.0),
           ("B6_north_edge", (-7.0, G.TERRACE[3]), (49.0, G.TERRACE[3]), 0.0),
           ("B7_west_edge", (-7.0, -3.0), (-7.0, G.TERRACE[3]), 0.0), ("B8_SW_verge", (-7.0, -2.75), (12.2, -2.75), 0.0)]
# hall + armory round: B5 / B6 / B7 follow the terrace edge to y 56 (G.TERRACE[3])


def boundary():
    out = []
    for bid, a, b, z0 in B_LINES:
        L = math.hypot(b[0] - a[0], b[1] - a[1]) + 0.5
        yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        # the engine cube is 1 m, centred: centre z = base + 3 m
        out.append(rec("boundary", f"Boundary1v1_{bid}", "/Engine/BasicShapes/Cube", cx, cy, z0 + 3.0, yaw, [L, 0.5, 6.0],
                       folder="Boundary_1v1", collision="boundary", shadow=False, hidden=True,
                       tags=["Boundary_1v1", "TerraceEdge", "Dojo/Boundary_1v1"], line={"from": a, "to": b, "z0": z0}))
    return out


# ---------------------------------------------------------------------------------------------------- forests
FIRS = [f"{FISH}/Foliage/Tree/SM_Fir_Tree_0{i}" for i in range(1, 9)]
FIR_W = np.array([0.12] * 5 + [0.4 / 3] * 3)
FIR_W = FIR_W / FIR_W.sum()
# FIX ROUND (judge blocker 2 / delta 2): the forest zones carry a closed canopy (the reference's 'dense blue-green
# forested ridges'); FZ1 / FZ2 now start on the new rim slope behind the hall (rim(), make_terrain.py), 3 m off the
# terrace; the sun-ray filter (sun_blocks) still drops every tree that would shade the sand or the hall front
_FZN = G.TERRACE[3] + 3.0 if G.HALL_ARMORY else 47.0     # hall + armory round: FZ1 starts 3 m off the moved terrace (58... 59)
FZ = [("FZ1_north_hill", [(-40, _FZN), (95, _FZN), (130, 210), (-70, 210)]),
      ("FZ2_west_ridge", [(-170, -80), (-16, -80), (-16, -2), (-10, 2), (-10, _FZN), (-40, _FZN), (-170, 130)]),
      ("FZ3_east_valley", [(92, -80), (260, -70), (330, 320), (140, 270), (104, 95), (88, 20)]),
      # build addition: the far bank E1 (plan 3.6) carried no trees and read as a bare levee; firs 14 m or more from
      # the water (the cherry-slot row keeps its clearances, the camera wedge stays open)
      ("FZ3b_far_bank", [(70, 45), (69, 15), (65, -20), (45, -27), (33, -38), (27, -52), (45, -75), (100, -70),
                         (92, 20), (100, 95), (80, 60)])]
WEDGE = [(4.8, -70.0), (-14.0, -2.0), (54.0, -2.0)]
CYPRESS = [(5.0, 49.5), (16.0, 50.5), (28.0, 51.0), (38.0, 49.5), (46.0, 48.5)]
if G.HALL_ARMORY:   # hall + armory round: the cypress row behind the hall moves back with the terrace (+12 m)
    CYPRESS = [(x, y + 12.0) for x, y in CYPRESS]


SUN_EL = math.radians(9.08)
SUN_H = np.array([math.cos(math.radians(187.29)), math.sin(math.radians(187.29))])   # toward the sun (Blender az)
_SX, _SY = np.meshgrid(np.arange(2.0, 43.0, 3.0), np.arange(1.0, 21.0, 3.0))
SAND = np.c_[_SX.ravel(), _SY.ravel()]                          # the courtyard sand / yards the sun must reach
# FIX ROUND: the forest now grows on the rim slope west of the hall; the hall front (veranda, shoji band, z 2.5) and the
# west kura's yard face keep their sun too
_HX = np.arange(1.0, 44.0, 3.0)
SUN_TARGETS = np.r_[np.c_[SAND, np.zeros(len(SAND))], np.c_[_HX, np.full(len(_HX), 21.0), np.full(len(_HX), 2.5)],
                    np.c_[np.full(4, 4.0), np.arange(22.0, 34.0, 3.0), np.full(4, 2.0)]]


def sun_blocks(X, Y, top):
    """True where an object at (X, Y) whose top is at `top` (level z, m) cuts the sun ray to any sun target (the sand
    points at z 0, the hall front and the west kura face; 3 m wide)."""
    X, Y, top = np.atleast_1d(X), np.atleast_1d(Y), np.atleast_1d(top)
    dx = X[:, None] - SUN_TARGETS[None, :, 0]
    dy = Y[:, None] - SUN_TARGETS[None, :, 1]
    t = dx * SUN_H[0] + dy * SUN_H[1]
    lat = np.abs(dx * SUN_H[1] - dy * SUN_H[0])
    return ((t > 0) & (lat < 3.0) & (top[:, None] > SUN_TARGETS[None, :, 2] + t * math.tan(SUN_EL))).any(1)


def keepout(X, Y, extra_slots=2.0):
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    bad = (X > -10) & (X < 52) & (Y > -6) & (Y < G.TERRACE[3] + 3.0)   # hall + armory: 47 -> 59
    bad |= G.poly_contains(X, Y, WEDGE)
    D, WZ, WID = G.river_fields(X, Y)[:3]
    bad |= (D - WID / 2) < 4.0
    for s in G.PLAN["cherry_slots"]["slots"]:
        bad |= np.hypot(X - s["loc"][0], Y - s["loc"][1]) < s["canopy_m"] / 2 + extra_slots
    for cx, cy in CYPRESS:
        bad |= np.hypot(X - cx, Y - cy) < 6.0
    bad |= G.poly_contains(X, Y, G.CLIFF_POLY) & (Y > -20)
    return bad


def poisson(poly, dens_fn, spacing, n_try, ground_fn, max_slope):
    P = np.array(poly, float)
    x0, y0 = P.min(0)
    x1, y1 = P.max(0)
    X = RNG.uniform(x0, x1, n_try)
    Y = RNG.uniform(y0, y1, n_try)
    ok = G.poly_contains(X, Y, poly) & ~keepout(X, Y)
    ok &= RNG.uniform(0, 1, n_try) < dens_fn(X, Y)
    X, Y = X[ok], Y[ok]
    sl = HV.slope_deg(X, Y, 2.0)
    keep = sl < max_slope
    X, Y = X[keep], Y[keep]
    cell = spacing
    grid = {}
    out = []
    for x, y in zip(X, Y):
        ci, cj = int(x // cell), int(y // cell)
        near = False
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for (px, py) in grid.get((ci + di, cj + dj), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < spacing ** 2:
                        near = True
                        break
                if near:
                    break
            if near:
                break
        if not near:
            grid.setdefault((ci, cj), []).append((x, y))
            out.append((x, y))
    return out


def forests():
    ism = []
    by_mesh = {m: [] for m in FIRS}
    counts = {}
    # FIX ROUND: a closed canopy (the world stage's 1 per 35-70 m2 at >= 5 m spacing left bare tan slopes between the
    # trees): every candidate kept, 4.2 m Poisson spacing (crowns 4.9-6.8 m wide overlap), slopes to 40 deg; the far
    # bank from 8 m off the water (the cherry slots keep their clearance)
    for zid, poly in FZ:
        if zid.startswith("FZ3b"):
            def dens(X, Y):
                D, WZ, WID = G.river_fields(X, Y)[:3]
                return np.where((D - WID / 2) < 8.0, 0.0, 1.0)
        elif zid.startswith("FZ3"):
            def dens(X, Y):
                d = np.full(X.shape, 1.0)
                for s in G.PLAN["cherry_slots"]["slots"][12:18]:
                    d = np.where(np.hypot(X - s["loc"][0], Y - s["loc"][1]) < 12, 0.35, d)
                return d
        else:
            dens = lambda X, Y: np.full(X.shape, 1.0)   # noqa: E731
        Pp = np.array(poly, float)
        area = abs(np.sum(Pp[:, 0] * np.roll(Pp[:, 1], -1) - np.roll(Pp[:, 0], -1) * Pp[:, 1]) / 2)
        pts = poisson(poly, dens, 4.2, int(area / 25.0 * 5.0), ground, 40.0)
        counts[zid] = len(pts)
        if pts:
            P = np.array(pts)
            blk = sun_blocks(P[:, 0], P[:, 1], ground(P[:, 0], P[:, 1]) + 17.0)
            counts[zid + "_sun_dropped"] = int(blk.sum())
            pts = [p for p, b in zip(pts, blk) if not b]
            counts[zid] = len(pts)
        for x, y in pts:
            m = FIRS[int(RNG.choice(8, p=FIR_W))]
            # FIX ROUND (delta 10): the fir meshes' bounding box reaches 4.2-6.4 m under the pivot while the geometry
            # (the root flare) ends 1.3-2.2 m under it (probe_fir.json), and the ISM bottom was placed from the BOX: the
            # trunks stood 3.6-5.8 m in the air. They are now placed by the pivot (the trunk base, pivot_ground) 0.25 m
            # into the ground, so the roots are buried.
            # The root flare also hung in the air on the downhill side of a
            # slope: the trunk base goes to the LOWEST ground within 2.2 m (8 ring samples) minus 0.15 m
            ring = [float(ground(x + 2.2 * math.cos(a), y + 2.2 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
            z = min(float(ground(x, y)), min(ring)) - 0.15
            near = math.hypot(x - 22.0, y - 18.0) < 160.0
            by_mesh[m].append([x, y, z, float(RNG.uniform(0, 360)), float(RNG.uniform(0.85, 1.18)), zid,
                               "near" if near else "far"])
    for m, rows in by_mesh.items():
        # shadows only within 160 m of the compound (ShadowDepths cost; the far canopy reads by its own colour)
        for band, shadow in (("near", True), ("far", False)):
            rr = [r[:6] for r in rows if r[6] == band]
            if rr:
                ism.append({"group": "forest", "name": "Forest_" + m.rsplit("/", 1)[1] + ("" if band == "near" else "_Far"),
                            "mesh": m, "rows": rr, "folder": "Landscape/Forest", "collision": "block", "shadow": shadow,
                            "wpo_disable_cm": 6000.0, "bury_m": 0.25, "cull_cm": 0, "pivot_ground": True,
                            "material_swaps": {"MI_Tree_Leaves": "/Game/DojoLandscape/Materials/MI_DJL_FirLeaves"}})
    # billboards: the far hills in the valley (beyond 230 m) and LS_Far to 2.6 km, north-west through east-south-east
    bb = []
    # FIX ROUND (delta 2): the mid hills read as bare tan earth with a sparse scatter (1 per ~200 m2): the near ring
    # (230-900 m, what the reference camera and the gate see as 'forested ridges') now ~1 per 25 m2, beyond ~1 per 110 m2
    n1, n2 = 40000, 200000
    ang = np.r_[RNG.uniform(math.radians(-65), math.radians(115), n1), RNG.uniform(math.radians(-65), math.radians(115), n2)]
    r = np.r_[np.sqrt(RNG.uniform(230.0 ** 2, 900.0 ** 2, n1)), np.sqrt(RNG.uniform(900.0 ** 2, 2600.0 ** 2, n2))]
    n_try = n1 + n2
    X, Y = 22.0 + r * np.sin(ang), 18.0 + r * np.cos(ang)
    Z = ground(X, Y)
    D, WZ, WID = G.river_fields(X, Y, chunk=20000)[:3]
    sl = np.where(HV.inside(X, Y, 2.0), HV.slope_deg(X, Y, 3.0), HF.slope_deg(X, Y, 8.0))
    dens = np.where(r < 900.0, 0.85, 0.42)
    ok = (sl < 40) & (Z < 900) & ((D - WID / 2) > 8) & (RNG.uniform(0, 1, n_try) < dens) & ~G.poly_contains(X, Y, WEDGE)
    for zid, poly in FZ:
        ok &= ~G.poly_contains(X, Y, poly)
    sb = np.zeros(ok.shape, bool)
    idx = np.where(ok)[0]
    for s in range(0, len(idx), 4000):
        j = idx[s:s + 4000]
        sb[j] = sun_blocks(X[j], Y[j], Z[j] + 14.0)
    counts["billboards_sun_dropped"] = int(sb.sum())
    ok &= ~sb
    for x, y, z in zip(X[ok], Y[ok], Z[ok]):
        # fix round: the billboard card is 4 x 4 m (probe_fir.json); x 2.6-3.6 matches the 10-16 m firs (it was x 0.9-1.3:
        # 4-5 m 'tiny conifers' on the hills)
        bb.append([float(x), float(y), float(z), float(RNG.uniform(0, 360)), float(RNG.uniform(2.6, 3.6)), "billboard"])
    counts["billboards"] = len(bb)
    ism.append({"group": "forest", "name": "Forest_Billboards", "foliage_type": f"{FISH}/Foliage/Tree/SMF_Fir_Tree_Billboard",
                "rows": bb, "folder": "Landscape/Forest", "collision": "none", "shadow": False, "bury_m": 0.3,
                "cull_cm": 0, "material_swaps": {"MI_Tree_Leaves": "/Game/DojoLandscape/Materials/MI_DJL_FirLeaves",
                                                 "MI_Tree_Billboard": "/Game/DojoLandscape/Materials/MI_DJL_FirBillboard"}})
    cyp = []
    for i, (x, y) in enumerate(CYPRESS):
        cyp.append(rec("forest", f"Cypress_{i + 1}", "/Game/Megaplant_Library/Tree_Japanese_Cypress/Tree_Japanese_Cypress_01/"
                       f"Tree_Japanese_Cypress_01_{'ABCDE'[i]}", x, y, float(ground(x, y)) - 0.2, float(RNG.uniform(0, 360)),
                       1.0, folder="Landscape/Forest/Cypress", collision="skeletal", skeletal=True))
    counts["cypress"] = len(cyp)
    return ism, cyp, counts


# ---------------------------------------------------------------------------------------------------- ground cover
def cover():
    ism = []
    counts = {}
    grass = [f"{FISH}/Foliage/Grass/SM_Grass_0{i}" for i in range(1, 8)]
    bush = [f"{FISH}/Foliage/Bush/SM_Bush_{i:02d}" for i in range(1, 11)]
    peb = [f"{FISH}/Small_Rocks/SM_Small_Rocks_0{i}" for i in range(1, 6)]
    G_rows = {m: [] for m in grass}

    def add_grass(x, y, z):
        m = grass[int(RNG.integers(0, 7))]
        G_rows[m].append([float(x), float(y), float(z), float(RNG.uniform(0, 360)), float(RNG.uniform(0.8, 1.3)), "grass"])

    def strip_ok(x, y):
        if -1.2 <= x <= 45.2 and -1.2 <= y <= 37.2:
            return False                      # never inside the compound / on its walls
        if 17.0 <= x <= 27.0 and -4.2 <= y <= -0.8:
            return False                      # the gate / gate stair
        for pid, v, px, py, *_ in PINES:
            if math.hypot(x - px, y - py) < 1.2:
                return False
        return path_clear(x, y, 1.0)
    # terrace strips (z 0), density ~0.55 / m2
    for (x0, x1, y0, y1) in ((-6.8, -1.3, -2.8, 43.8), (-6.8, 48.8, 37.3, 43.8), (45.3, 48.6, -2.8, 43.8),
                             (-6.8, 48.8, -2.8, -1.3)):
        n = int((x1 - x0) * (y1 - y0) * 0.55)
        for x, y in zip(RNG.uniform(x0, x1, n), RNG.uniform(y0, y1, n)):
            if strip_ok(x, y):
                add_grass(x, y, 0.0)
    # banks, the cliff top, the hill edge (off the water, off the paths, gentle slopes)
    for poly, dens in (([(10.5, -8), (26, -10), (30, -24), (20, -44), (12, -40), (11, -24)], 0.5),
                       (G.CLIFF_POLY, 0.35), ([(-30, 44.5), (60, 44.5), (60, 75), (-30, 75)], 0.45),
                       ([(1.7, -37), (12, -38), (13, -50), (-2, -60), (-8, -48)], 0.4),
                       ([(70, 45), (69, 15), (65, -20), (45, -27), (33, -38), (27, -52), (45, -75), (100, -70), (92, 20),
                         (100, 95), (80, 60)], 0.12)):
        P = np.array(poly, float)
        (x0, y0), (x1, y1) = P.min(0), P.max(0)
        n = int((x1 - x0) * (y1 - y0) * dens)
        X, Y = RNG.uniform(x0, x1, n), RNG.uniform(y0, y1, n)
        ok = G.poly_contains(X, Y, poly)
        X, Y = X[ok], Y[ok]
        D, WZ, WID = G.river_fields(X, Y)[:3]
        sl = HV.slope_deg(X, Y, 0.5)
        keep = ((D - WID / 2) > 0.8) & (sl < 32)
        for x, y in zip(X[keep], Y[keep]):
            if strip_ok(x, y):
                add_grass(x, y, float(ground(x, y)))
    # FIX ROUND (delta 8): moss and grass tufts along the stair edges (the reference's green step margins): a band
    # 0.15-0.9 m outside every path piece's footprint, off the pieces and the lanterns, at the ground there
    n_edge = 0
    for fp in G.path_footprints():
        per = int((fp["hl"] * 2 + fp["hw"] * 2) * 2.2)
        for _ in range(per):
            side = RNG.choice([-1.0, 1.0])
            if RNG.uniform() < 0.5:
                u, v = side * (fp["hw"] + RNG.uniform(0.15, 0.9)), RNG.uniform(-fp["hl"], fp["hl"])
            else:
                u, v = RNG.uniform(-fp["hw"], fp["hw"]), side * (fp["hl"] + RNG.uniform(0.15, 0.9))
            c, s_ = math.cos(math.radians(fp["rot"])), math.sin(math.radians(fp["rot"]))
            x, y = fp["cx"] + u * c - v * s_, fp["cy"] + u * s_ + v * c
            if not path_clear(x, y, 0.1) or any(math.hypot(x - lx, y - ly) < 0.6 for _k, lx, ly, *_r in LANTERNS):
                continue
            if -1.2 <= x <= 45.2 and -1.2 <= y <= 37.2:
                continue
            m = grass[int(RNG.integers(0, 7))]
            G_rows[m].append([float(x), float(y), float(ground(x, y)), float(RNG.uniform(0, 360)),
                              float(RNG.uniform(0.55, 0.95)), "stair_edge"])
            n_edge += 1
    counts["grass_stair_edge"] = n_edge
    for m, rows in G_rows.items():
        if rows:
            ism.append({"group": "cover", "name": "Grass_" + m.rsplit("/", 1)[1], "mesh": m, "rows": rows,
                        "folder": "Landscape/Cover", "collision": "none", "shadow": False, "wpo_disable_cm": 3000.0,
                        "bury_m": 0.03, "cull_cm": 9000})
    counts["grass"] = sum(len(v) for v in G_rows.values())
    # bushes: forecourt corners, the bank along the stair, the far bank edge, the cliff top, the north strip
    B_rows = {m: [] for m in bush}
    spots = [(13.0, -7.3), (33.2, -7.3), (13.2, -3.9), (33.0, -4.0), (12.8, -9.5), (11.4, -15.0), (11.6, -19.5),
             (11.3, -25.5), (11.6, -32.0), (6.2, -32.5), (5.2, -40.5), (1.5, -41.5), (-2.0, -6.5), (-4.0, -15.5),
             (2.5, -23.0), (-2.5, -28.5), (-6.0, 42.5), (6.0, 42.8), (30.0, 42.6), (44.0, 42.5), (-6.0, 26.0),
             (47.8, 33.0), (47.8, 10.0), (-6.2, 5.0), (15.0, -35.0), (24.5, -38.5), (19.0, -13.5)]
    D, WZ, WID = G.river_fields(np.array([s[0] for s in spots]), np.array([s[1] for s in spots]))[:3]
    for (x, y), d, w in zip(spots, D, WID):
        if d - w / 2 < 1.0 or not path_clear(x, y, 0.7):
            continue
        z = 0.0 if (-7 <= x <= 49 and -3 <= y <= G.TERRACE[3]) else (-0.5 if (12 <= x <= 34 and -8 <= y <= -3.5) else float(ground(x, y)))
        m = bush[int(RNG.integers(0, 10))]
        B_rows[m].append([x, y, z, float(RNG.uniform(0, 360)), float(RNG.uniform(0.8, 1.2)), "bush"])
    # far bank bush line (it4: 22 -> 60, two rows)
    for key in np.concatenate([np.linspace(3.0, 10.0, 34), np.linspace(3.2, 9.8, 26)]):
        j = int(np.argmin(np.abs(G.RIVER[:, 6] - key)))
        cx, cy, wid = G.RIVER[j, 0], G.RIVER[j, 1], G.RIVER[j, 3]
        nx, ny = G.RIVER[min(j + 1, len(G.RIVER) - 1), 0] - cx, G.RIVER[min(j + 1, len(G.RIVER) - 1), 1] - cy
        n = math.hypot(nx, ny) or 1.0
        d = wid / 2 + RNG.uniform(2.0, 11.0)
        x, y = cx - ny / n * d, cy + nx / n * d
        m = bush[int(RNG.integers(0, 10))]
        B_rows[m].append([float(x), float(y), float(ground(x, y)), float(RNG.uniform(0, 360)), float(RNG.uniform(0.9, 1.4)),
                          "bush"])
    # FIX ROUND (delta 2 / 8): the reference's rounded shrubs between the bank boulders (both banks R3..R9, 1-10 m off
    # the water) and on the BF3 bank below the stair rails
    nb = 0
    for _ in range(400):
        if nb >= 70:
            break
        j = int(RNG.choice(np.where((G.RIVER[:, 6] >= 3.0) & (G.RIVER[:, 6] <= 9.6))[0]))
        cx, cy, wid = G.RIVER[j, 0], G.RIVER[j, 1], G.RIVER[j, 3]
        nx, ny = G.RIVER[min(j + 1, len(G.RIVER) - 1), 0] - cx, G.RIVER[min(j + 1, len(G.RIVER) - 1), 1] - cy
        n = math.hypot(nx, ny) or 1.0
        side = 1.0 if RNG.uniform() < 0.6 else -1.0
        d = wid / 2 + RNG.uniform(1.0, 10.0)
        x, y = cx - side * ny / n * d, cy + side * nx / n * d
        if not path_clear(x, y, 0.9) or (-10 < x < 52 and -9 < y < G.TERRACE[3] + 3.0):
            continue
        if HV.slope_deg(np.array([x]), np.array([y]), 1.0)[0] > 46:
            continue
        m = bush[int(RNG.integers(0, 10))]
        B_rows[m].append([float(x), float(y), float(ground(x, y)), float(RNG.uniform(0, 360)), float(RNG.uniform(0.8, 1.3)),
                          "bush_bank"])
        nb += 1
    counts["bushes_bank_fix"] = nb
    # fix round it3 (delta 12): shrubs on the west sun corridor (the bare pale plateau behind the west wall), each kept
    # only where its top (2.4 m x scale) stays under the 9.08 deg sun line to every sun target (sun_blocks)
    nc = 0
    for _ in range(900):
        if nc >= 55:
            break
        x, y = RNG.uniform(-70.0, -9.0), RNG.uniform(-10.0, 30.0)
        s_ = float(RNG.uniform(0.9, 1.4))
        z = float(ground(x, y))
        if sun_blocks(np.array([x]), np.array([y]), np.array([z + 2.4 * s_]))[0]:
            continue
        if HV.slope_deg(np.array([x]), np.array([y]), 1.0)[0] > 30 or G.poly_contains(np.array([x]), np.array([y]), G.CLIFF_POLY)[0]:
            continue
        m = bush[int(RNG.integers(0, 10))]
        B_rows[m].append([x, y, z, float(RNG.uniform(0, 360)), s_, "bush_corridor"])
        nc += 1
    counts["bushes_sun_corridor"] = nc
    for m, rows in B_rows.items():
        if rows:
            ism.append({"group": "cover", "name": "Bush_" + m.rsplit("/", 1)[1], "mesh": m, "rows": rows,
                        "folder": "Landscape/Cover", "collision": "none", "shadow": True, "wpo_disable_cm": 3000.0,
                        "bury_m": 0.08, "cull_cm": 0})
    counts["bushes"] = sum(len(v) for v in B_rows.values())
    # waterline pebbles along both banks of the near river (R3..R9)
    P_rows = {m: [] for m in peb}
    idx = np.where((G.RIVER[:, 6] >= 3.0) & (G.RIVER[:, 6] <= 10.0))[0]
    for _ in range(420):
        j = int(RNG.choice(idx))
        cx, cy, wid = G.RIVER[j, 0], G.RIVER[j, 1], G.RIVER[j, 3]
        nx, ny = G.RIVER[min(j + 1, len(G.RIVER) - 1), 0] - cx, G.RIVER[min(j + 1, len(G.RIVER) - 1), 1] - cy
        n = math.hypot(nx, ny) or 1.0
        s = 1.0 if RNG.uniform() < 0.5 else -1.0
        d = wid / 2 + RNG.uniform(-0.4, 1.4)
        x, y = cx - s * ny / n * d, cy + s * nx / n * d
        m = peb[int(RNG.integers(0, 5))]
        P_rows[m].append([float(x), float(y), float(ground(x, y)), float(RNG.uniform(0, 360)), float(RNG.uniform(1.5, 4.0)),
                          "pebble"])
    for m, rows in P_rows.items():
        ism.append({"group": "cover", "name": "Pebbles_" + m.rsplit("/", 1)[1], "mesh": m, "rows": rows,
                    "folder": "Landscape/Cover", "collision": "none", "shadow": False, "bury_m": 0.03, "cull_cm": 6000})
    counts["pebbles"] = sum(len(v) for v in P_rows.values())
    return ism, counts


# ---------------------------------------------------------------------------------------------------- far meshes
def far_meshes():
    out = []
    for i, (x, y, sxy, sz, yaw) in enumerate(((1300.0, 3900.0, 13.0, 11.0, 20.0), (2700.0, 3650.0, 15.0, 9.0, 75.0),
                                              (3600.0, 4700.0, 12.0, 12.0, 130.0), (500.0, 4800.0, 14.0, 10.0, 200.0))):
        out.append(rec("far", f"FarRidge_{i + 1}", f"{FISH}/Mountains/SM_Mountain_01", x, y, float(HF(x, y)) - 25.0, yaw,
                       [sxy, sxy, sz], folder="Landscape/Far", collision="none", shadow=True,
                       material="/Game/DojoLandscape/Materials/MI_DJL_Mountain"))
    return out


# ---------------------------------------------------------------------------------------------------- water + fx
def water():
    pts = []
    R = G.RIVER
    # FIX ROUND: every 2 m sample through the stepped rapids (the pours are 1-2 m long), every 6 m elsewhere
    sel = sorted(set(range(0, len(R), 3)) | set(int(j) for j in np.where((R[:, 6] >= 3.8) & (R[:, 6] <= 7.7))[0]))
    if sel[-1] != len(R) - 1:
        sel.append(len(R) - 1)
    for j in sel:
        pts.append({"xy": [round(float(R[j, 0]), 3), round(float(R[j, 1]), 3)], "water_z": round(float(R[j, 2]), 3),
                    "width_m": round(float(R[j, 3]), 3), "depth_m": round(float(R[j, 4]), 3),
                    "velocity_cm_s": round(float(R[j, 5]), 1), "key": round(float(R[j, 6]), 3)})
    return {"body": "WaterBodyRiver", "label": "River_Main", "material": "/Game/DojoLandscape/Materials/MI_DJL_River",
            "affects_landscape": False, "points": pts,
            "zone": {"label": "WaterZone_Valley", "centre": [60.0, 100.0, -5.0], "extent_m": [1600.0, 1600.0],
                     "rt_resolution": 2048}}


def foam_strips_tail(key):
    """it4: the graded fade at the reach's two ends: 0..5 = denser..fainter, None inside the core reach"""
    # it5: the white water runs to key 8.3 (R7.3, the reference frame's y ~1250, where the reference's rapids still
    # foam), then fades to key 9.0 (the plan's run past the landing); it4's tail from key 7.35 thinned the core boxes
    if key > 8.3:
        return min(5, int((key - 8.3) / (9.0 - 8.3) * 6))
    if key < 4.15:
        return min(5, int((4.15 - key) / (4.15 - 3.8) * 3) + 3)
    return None


def foam_mi(key, drop):
    t = foam_strips_tail(key)
    if t is not None:
        return f"MI_DJL_RapidsFoamTail_{t}"
    return "MI_DJL_RapidsFoamDrop" if drop else "MI_DJL_RapidsFoam"


def foam_strips():
    """The rapids' white water: one 1 m engine plane per ~6 m of the R4..R7.4 reach, 3 cm over the water surface, 85 %
    of the channel width, yawed along the flow, the foam material (M_DJL_RapidsFoam) panning down-stream in world UVs."""
    # FIX ROUND (delta 1): one strip per 2 m sample (was per 6 m), PITCHED to the stepped water, 6 cm over it; the
    # pours (water dropping > 5 cm over the strip) take the dense drop foam MI, the runs the streaked run MI; 92 % of
    # the width (the boulders' own wakes and the bank margins finish the edges)
    out = []
    R = G.RIVER
    idx = [j for j in range(0, len(R) - 1) if 3.8 <= R[j, 6] <= 9.0]     # it5: the white water fades out by key 9.0
    for k, j in enumerate(idx):
        a, b = R[j], R[j + 1]
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        run = math.hypot(b[0] - a[0], b[1] - a[1])
        L = run + 0.2           # it1: a 0.5 m overlap doubled the foam in bands; it2: 0.03 left dark seams at the pours
        yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        dz = float(b[2] - a[2])
        wz = (a[2] + b[2]) / 2 + 0.06
        wid = 0.92 * (a[3] + b[3]) / 2
        drop = dz < -0.05
        out.append(rec("fx", f"RapidsFoam_{k + 1:02d}", "/Engine/BasicShapes/Plane", cx, cy, wz, yaw, [L, wid, 1.0],
                       folder="Landscape/Water/Foam", collision="none", shadow=False,
                       pitch=round(math.degrees(math.atan2(dz, run)), 3),
                       material="/Game/DojoLandscape/Materials/" + foam_mi(float(a[6]), drop),
                       key=round(float(a[6]), 3), pour=drop))
    return out


def fx():
    anchors = []
    # FIX ROUND (blocker 5 / delta 6): the key-4.6 anchor (upstream, at the bend) fed the steam plume the reference
    # does not have (its river recedes calmly upstream): mist only over the stepped rapids below the SE corner
    for i, key in enumerate((5.8, 6.9)):
        j = int(np.argmin(np.abs(G.RIVER[:, 6] - key)))
        anchors.append({"label": f"FXAnchor_Mist_{i + 1}", "loc": [float(G.RIVER[j, 0]), float(G.RIVER[j, 1]),
                                                                  float(G.RIVER[j, 2]) + 0.3], "kind": "mist"})
    fog = {"label": "LocalFog_Rapids", "centre": [42.0, -14.0, -4.8], "yaw": -25.0, "size_m": [44.0, 18.0, 4.0],
           "note": "the low mist bank along R4..R8 (plan 3.5); owned NiagaraExamples fog is a plugin mount, not copied"}
    return anchors, fog


# ---------------------------------------------------------------------------------------------------- mask
def valley_mask(path):
    ls = G.LS_VALLEY
    n = 2048
    half = (ls["n"] - 1) * ls["spacing"] / 2.0
    xs = ls["centre"][0] - half + (np.arange(n) + 0.5) * (2 * half / n)
    ys = ls["centre"][1] + half - (np.arange(n) + 0.5) * (2 * half / n)
    X, Y = np.meshgrid(xs, ys)
    D, WZ, WID = G.river_fields(X[::2, ::2], Y[::2, ::2])[:3]
    D = np.kron(D, np.ones((2, 2)))
    WID = np.kron(WID, np.ones((2, 2)))
    dp = D - WID / 2
    R = np.zeros(X.shape)
    for fp in G.path_footprints():
        u, v = G.box_local(X, Y, fp)
        d = np.hypot(np.maximum(np.abs(u) - fp["hw"], 0), np.maximum(np.abs(v) - fp["hl"], 0))
        R = np.maximum(R, 1 - G.smoothstep(0.2, 1.4, d))
    fx0, fx1, fy0, fy1, _ = G.FORECOURT
    R = np.maximum(R, ((X > fx0) & (X < fx1) & (Y > fy0) & (Y < fy1 - 0.5)).astype(float) * 0.85)
    for a, b in (((3.3, -39.5), (-6, -52)), ((-6, -52), (-22, -70)), ((-22, -70), (-45, -100))):   # the BR trail SW
        d, _, _, _ = G.seg_dist(X, Y, a, b)
        R = np.maximum(R, 1 - G.smoothstep(0.6, 1.6, d))
    R = np.maximum(R, (1 - G.smoothstep(0.0, 1.8, np.abs(dp))) * 0.75)                        # wet margins
    Gm = np.zeros(X.shape)
    for zid, poly in FZ:
        Gm = np.maximum(Gm, G.poly_contains(X, Y, poly).astype(float))
    # the hills beyond the near field are forest floor under the billboard forest (plan FZ4: canopy beyond)
    Rr = np.hypot(X - 22.0, Y - 18.0)
    Gm = np.maximum(Gm, G.smoothstep(180.0, 260.0, Rr) * (dp > 8.0))
    Bm = np.zeros(X.shape)
    for poly in ([(10.5, -8), (26, -10), (30, -24), (20, -44), (12, -40), (11, -24)], G.CLIFF_POLY,
                 [(1.7, -37), (12, -38), (13, -50), (-2, -60), (-8, -48)]):
        Bm = np.maximum(Bm, G.poly_contains(X, Y, poly).astype(float) * 0.8)
    # fix round (delta 2): the mossy band of the banks runs 0.5-14 m off the water (was 1-7 m at 0.6)
    Bm = np.maximum(Bm, ((dp > 0.5) & (dp < 20.0)).astype(float) * 0.85)      # it3: to 20 m
    for f in G.WALL_FACES:
        d, s, t, L = G.seg_dist(X, Y, f["a"], f["b"])
        Bm = np.maximum(Bm, ((-t > 0) & (-t < 2.5) & (s > -1) & (s < L + 1)).astype(float) * 0.9)
    A = (1 - G.smoothstep(-0.8, 0.3, dp))
    img = np.stack([R, Gm, Bm, A], -1)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA")
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(path)
    return {"file": str(path), "size": n, "texel_m": round(2 * half / n, 4),
            "coverage": {c: round(float(np.asarray(im)[..., i].mean() / 255), 4) for i, c in enumerate("RGBA")}}


def main():
    W = {"frame": G.PLAN["frame"], "date": "2026-09-30"}
    rep = json.loads((TER / "terrain_report.json").read_text(encoding="utf-8"))
    W["landscapes"] = []
    for key, ls in (("LS_Valley", G.LS_VALLEY), ("LS_Far", G.LS_FAR)):
        r = rep[key]
        W["landscapes"].append({"label": key, "raw": str(TER / f"{key}.r16"), "n": ls["n"], "sections": ls["sections"],
                                "quads": ls["quads"], "location_cm": r["ue_location_cm"], "scale": r["scale_cm"],
                                "material": f"/Game/DojoLandscape/Materials/MI_DJL_{'Valley' if key == 'LS_Valley' else 'Far'}",
                                "nanite": True})
    W["mask"] = valley_mask(TER / "T_DJL_ValleyMask.png")
    W["actors"] = walls() + stair()
    la, lights = lanterns()
    W["actors"] += la + pines() + rocks() + cherry() + boundary() + far_meshes() + foam_strips()
    fism, cyp, fc = forests()
    cism, cc = cover()
    W["actors"] += cyp
    W["ism"] = fism + cism
    W["lights"] = lights
    W["water"] = water()
    W["path_footprints"] = G.path_footprints()      # fix round: for the FX step (UE Python has no numpy)
    W["fx_anchors"], W["fog"] = fx()
    counts = {}
    for a in W["actors"]:
        counts[a["group"]] = counts.get(a["group"], 0) + 1
    # the terrain itself: march every sand point's sun ray over the two heightmaps to 6 km (terrain-only shadow)
    lit = []
    for sx, sy in SAND:
        tt = np.concatenate([np.arange(2.0, 200.0, 1.0), np.arange(200.0, 6000.0, 8.0)])
        hx, hy = sx + SUN_H[0] * tt, sy + SUN_H[1] * tt
        lit.append(bool((ground(hx, hy) < tt * math.tan(SUN_EL)).all()))
    W["sun_check"] = {"sun_el_deg": 9.08, "sun_az_from_x_deg": 187.29, "sand_points": len(lit),
                      "terrain_lit_pct": round(100.0 * sum(lit) / len(lit), 1),
                      "note": "terrain-only (the compound's own walls / buildings still cast their round-9 shadows)"}
    W["counts"] = {"actors_by_group": counts, "ism_instances": {i["name"]: len(i["rows"]) for i in W["ism"]},
                   "forest": fc, "cover": cc, "lights": len(lights), "water_points": len(W["water"]["points"])}
    out = G.WORLD / "json" / "world_layout.json"
    out.write_text(json.dumps(W, indent=0), encoding="utf-8")
    print("WORLD_LAYOUT", json.dumps(W["counts"]["actors_by_group"]), json.dumps(fc), json.dumps(cc),
          "water pts", len(W["water"]["points"]), "mask", json.dumps(W["mask"]["coverage"]))


main()
