"""ROUND 5 (2026-09-29): OUTSIDE + BACKGROUND of the dojo arena, SM_DKX_*. Vegetation is NOT in this round (the user:
"start with everything else and leave the vegetation for later"): trees stay grey-box stand-ins and layout_outside.json
lists clearly marked tree slots for the vegetation pass.

Look sources (AI-generated modelling references, References/Dojo/REFERENCE_LOG.md; measured only):
  dojo1_reference1  the approach side: a narrow dark verge along the wall foot, a kerb, a grey stony road, the gate's
                    granite apron, a paved landing between two street lamps at the far edge, a low timber post-and-rail
                    fence on a rubble retaining wall (the terrace edge), dark water below it, a lower lane with a board
                    fence, trees and tiled house roofs beyond; a utility pole with wires at the east end of the fence line;
                    houses and a lane beyond the west wall
  dojo1_reference2  (sunset, from the gate) tiled roofs of neighbouring houses beyond the walls on both sides, low
                    blue-grey mountain silhouettes on the horizon, trees (later)
Spec (WorkFiles/world/DOJO_ARENA_SPEC.md): 7 'on a terrace at the edge of a town, the main gate facing an approach road
with street lamps and power lines; the outside ground within 0.5 m of the courtyard level along the walls' (the wall
stays climbable from outside); 4.6 the rear-alley fences close the alley in the 1v1 (their collision is the grey-box's
EXACTLY); 5.3 collision classes.

Pieces (grey-box world frame, metres; Unreal (x*100, -y*100, z*100), yaw = -rot_z):
  street    SM_DKX_Road_W / _Gate / _E        cobble road Y -2.85..-7.75 (-3.00 in front of the apron step), crowned
            SM_DKX_Verge_W / _E               the wall-foot verge Y -0.96..-2.30 (soil; lane earth at the side-lane mouths)
            SM_DKX_Kerb_8m / _4m              granite kerb stones (near: Y -2.30..-2.50 top +0.03; far: Y -7.75..-7.95 top +0.02)
            SM_DKX_Gutter_8m / _4m            dished granite channel stones Y -2.50..-2.85 (lips -0.10)
            SM_DKX_FarVerge_W / _E            the strip on the terrace edge Y -7.95..-9.20 (poles, lamps, fence)
            SM_DKX_Landing                    granite slab landing between the street lamps X 14.4-29.6
            SM_DKX_RailFence_4m               timber post-and-rail fence on the terrace edge (Y -9.05)
            SM_DKX_Terrace_8m                 granite coping + rubble retaining wall (+0.04 -> -2.45)
            SM_DKX_Canal_8m / SM_DKX_Water    canal bed, far bank wall + coping; the water plane (-2.05)
            SM_DKX_Ground_South               the lower lane (-1.50) and the house plots beyond
            SM_DKX_BoardFence_4m              board fence along the lower lane
  ground    SM_DKX_Ground_W / _E / _N         outside ground round the compound (replaces SM_DGB_Ground_Outside), side
                                              lanes of packed earth; within 0.05 m of the courtyard level along the walls
  alley     SM_DKX_AlleyFence_W / _E          board fence + wicket gate (replaces SM_DGB_AlleyFence x2; hull IDENTICAL)
  town      SM_DKX_House_A..E                 low-detail neighbouring houses (tiled roof masses, plaster, timber)
  far       SM_DKX_FarGround                  the plain from the town edge to the ridges (flat, haze-friendly)
            SM_DKX_Mountains_Near / _Far      mountain ridge rings at 0.9-1.3 km and 1.6-2.2 km (a far MESH, see numbers)
  reuse     the modern kit's street lamps A + B, utility poles, transformer, guys, conductor / telecom spans and the
            gatehouse service drop, re-placed along the road in 'modern_instances' (their files are not touched)

Run: blender -b --factory-startup --python Scripts/dojo/outside/build_outside.py -- [--quick] [--no-export] [--no-context]
Out: Assets/Dojo/DojoOutside.blend, Exports/DojoKit/Outside/SM_DKX_*.fbx, WorkFiles/dojo/build/outside/
     {layout_outside.json, layout_outside_checks.json, qa_report.json, export_report.json, outside_report.json}
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "outside"))
import ox_common as OX  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
import kit1_geo as K  # noqa: E402
import dojo_materials as djm  # noqa: E402
from kit_mesh import Piece, cbox, cobox, member, TD, IR, GR, GRR, PL, TL, GL  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Outside"
BLEND = ROOT / "Assets" / "Dojo" / "DojoOutside.blend"
ROAD, VERGE, LANE, WATER = OX.ROAD, OX.VERGE, OX.LANE, OX.WATER
MNEAR, MFAR, FARG, PLE = OX.MNEAR, OX.MFAR, OX.FARG, OX.PLE

# ------------------------------------------------------------------------------------------------ numbers (world)
XW, XE = -86.0, 130.0                  # the local town rectangle (X), 27 x 8 m modules
YS, YN = -34.0, 76.0                   # (Y)
CX, CY = 22.0, 18.0                    # the compound centre (the sky dome's centre too)
WALL = (-1.0, 45.0, -1.0, 37.0)        # the perimeter wall's outer faces
VERGE_Y = (-0.96, -2.30)
KERB_N = (-2.30, -2.50, 0.03)          # near kerb (y0, y1, top)
GUT_Y = (-2.50, -2.85)
GUT_LIP, GUT_DIP = -0.10, 0.045
ROAD_Y = (-2.85, -7.75)
ROAD_EDGE_Z, ROAD_CROWN = -0.10, 0.05
KERB_F = (-7.75, -7.95, 0.02)          # far kerb
FARV_Y = (-7.95, -9.20)
COPE_Y, COPE_TOP = (-9.20, -9.50), 0.04
TER_BOT_Y, TER_BOT_Z = -9.75, -2.45
BANK_Y, BANK_TOP = -11.40, -1.46
WATER_Z = -2.05
LOWER_Z = -1.50
LOWLANE_Y = (-11.75, -16.60)
BFENCE_Y = -16.74
APRON_X = (18.10, 25.90)               # kit 1's gate paving (SM_DK_Gate_Paving): apron Y -1.25..-2.50 at +0.10
STEP_X = (18.80, 25.20)                # its front step Y -2.50..-3.00 at +0.05
LANDING_X = (14.40, 29.60)
GATE_ROAD_Y0 = -2.40                   # the road runs on under the apron's front step (its face at Y -3.00)
FENCE_Y = -9.05
LANES_X = {"W": (-12.0, -9.0), "E": (53.0, 56.0)}
LANE_N_Y = (41.5, 44.5)
POLE_Y = -8.55
POLES_X = [9.5 + 25.0 * k for k in range(-3, 5)]      # -65.5 .. 109.5: the modern kit's 25 m spans, extended
LAMP_B = (14.0, POLE_Y, 0.0)           # street lamp B, lantern +X (toward the landing / gate axis)
LAMP_A = (30.0, POLE_Y, 0.0)           # street lamp A, lantern -X
ALLEY = {"W": (10.5, 34.0), "E": (31.0, 34.0)}          # grey-box SM_DGB_AlleyFence pivots (min corners)
ALLEY_BOX = (2.5, 0.1, 2.0)            # its hull, EXACTLY
REPLACED = ["SM_DGB_Ground_Outside", "SM_DGB_AlleyFence"]
MODERN_STREET = ["SM_DKP_Modern_StreetLamp_A", "SM_DKP_Modern_StreetLamp_B", "SM_DKP_Modern_UtilityPole",
                 "SM_DKP_Modern_PoleTransformer", "SM_DKP_Modern_PoleGuy", "SM_DKP_Modern_Wire_Span25",
                 "SM_DKP_Modern_Wire_Telecom25", "SM_DKP_Modern_Wire_Drop12"]


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def wall_dist(x, y):
    dx = max(WALL[0] - x, 0.0, x - WALL[1])
    dy = max(WALL[2] - y, 0.0, y - WALL[3])
    return math.hypot(dx, dy)


def noise2(x, y, seed=0.0):
    return (0.45 * math.sin(0.113 * x + 0.71 + seed) * math.cos(0.089 * y + 1.3 + seed)
            + 0.30 * math.sin(0.231 * x - 0.057 * y + 2.1 + seed) + 0.25 * math.cos(0.041 * x + 0.197 * y + seed))


def in_lane(x, y):
    if LANES_X["W"][0] <= x <= LANES_X["W"][1] or LANES_X["E"][0] <= x <= LANES_X["E"][1]:
        return True
    return LANE_N_Y[0] <= y <= LANE_N_Y[1]


def ground_z(x, y):
    """Outside ground height north of the street: within 0.05 m of the courtyard level for 4 m round the walls, then a
    gentle undulation up to +-0.3 m; lanes are worn a little lower and flatter."""
    d = wall_dist(x, y)
    amp = (0.02 + 0.28 * smooth(4.0, 20.0, d)) * smooth(VERGE_Y[0], VERGE_Y[0] + 6.0, y)   # level with the verge
    z = amp * noise2(x, y)
    if in_lane(x, y):
        z = 0.5 * z - 0.03 * smooth(1.0, 4.0, d) * smooth(VERGE_Y[0], VERGE_Y[0] + 3.0, y)
    return z


def road_z(y):
    yc = (ROAD_Y[0] + ROAD_Y[1]) / 2
    hw = (ROAD_Y[0] - ROAD_Y[1]) / 2
    t = (y - yc) / hw
    return ROAD_EDGE_Z + ROAD_CROWN * max(0.0, 1.0 - t * t)


def south_z(x, y):
    """The lower level south of the canal: the lower lane at -1.50, the plots beyond with a gentle undulation."""
    z = LOWER_Z
    if y < LOWLANE_Y[1] - 0.5:
        z += 0.12 * noise2(x, y, 3.0) * smooth(0.0, 4.0, LOWLANE_Y[1] - y)
    return z


# ------------------------------------------------------------------------------------------------ mesh helpers
def add_shared(g, verts, faces, mats, frame=None, smooth=False):
    """Append one vertex list and faces of several materials to a Geo (shared vertices: no coincident duplicates at
    material borders)."""
    base = len(g.v)
    g.v += [Vector(p) for p in verts]
    for f, m in zip(faces, mats):
        g.f.append(tuple(base + i for i in f))
        g.fm.append(m)
        g.fr.append(frame)
        g.fc.append(None)
        g.fp.append(g._pid)
        g.fsm.append(bool(smooth))
    g._pid += 1
    return g


def grid(g, xs, ys, zfn, matfn, frame=None, flip=False, skirt=0.0):
    """Quads over the xs x ys lattice at z = zfn(x, y); material per quad from matfn(xc, yc); one shared vertex list.
    skirt > 0: a skirt hanging that far under every border (where two ground pieces meet with different vertex spacing,
    a hairline crack at the T-junctions shows the skirt, never the sky)."""
    idx = {}
    verts = []
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            idx[i, j] = len(verts)
            verts.append(Vector((x, y, zfn(x, y))))
    faces, mats = [], []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            f = (idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1])
            if flip:
                f = f[::-1]
            m = matfn((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2)
            if m is None:
                continue
            faces.append(f)
            mats.append(m)
    if skirt > 0:
        ctr = Vector((sum(xs) / len(xs), sum(ys) / len(ys), 0.0))
        nx, ny = len(xs) - 1, len(ys) - 1
        border = [((i, 0), (i + 1, 0)) for i in range(nx)] + [((i, ny), (i + 1, ny)) for i in range(nx)] +                  [((0, j), (0, j + 1)) for j in range(ny)] + [((nx, j), (nx, j + 1)) for j in range(ny)]
        low = {}
        for (a, b) in border:
            for k in (a, b):
                if k not in low:
                    low[k] = len(verts)
                    verts.append(verts[idx[k]] - Vector((0, 0, skirt)))
        for (a, b) in border:
            pa, pb = verts[idx[a]], verts[idx[b]]
            m = matfn((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)
            if m is None:
                continue
            q = (idx[a], idx[b], low[b], low[a])
            out = ((pa + pb) / 2 - ctr)
            out.z = 0.0
            n = (pb - pa).cross(verts[low[a]] - pa)
            faces.append(q if n.dot(out) > 0 else q[::-1])
            mats.append(m)
    add_shared(g, verts, faces, mats, frame)
    return g


def steps(a, b, step):
    n = max(1, int(round(abs(b - a) / step)))
    return [a + (b - a) * k / n for k in range(n + 1)]


def cell_hulls(p, xs, ys, zfn, cell=8.0, depth=0.35):
    """Convex UCX hulls over the lattice in cells of about `cell` m: the cell's surface points and the same points
    `depth` lower."""
    x0, x1, y0, y1 = xs[0], xs[-1], ys[0], ys[-1]
    nx = max(1, int(round((x1 - x0) / cell)))
    ny = max(1, int(round(abs(y1 - y0) / cell)))
    for i in range(nx):
        for j in range(ny):
            ca, cb = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            da, db = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
            cxs = [x for x in xs if min(ca, cb) - 1e-6 <= x <= max(ca, cb) + 1e-6]
            cys = [y for y in ys if min(da, db) - 1e-6 <= y <= max(da, db) + 1e-6]
            pts = [(x, y, zfn(x, y)) for x in cxs for y in cys]
            zmin = min(q[2] for q in pts)
            pts += [(q[0], q[1], zmin - depth) for q in pts[::max(1, len(pts) // 8)]] + \
                   [(x, y, zmin - depth) for x in (cxs[0], cxs[-1]) for y in (cys[0], cys[-1])]
            p.hulls.append(pts)


# ------------------------------------------------------------------------------------------------ street pieces
def road(name, x0, x1, y0):
    p = Piece(name, "ground", "Outside/Street",
              f"cobble road X {x0}..{x1}, Y {y0}..{ROAD_Y[1]}: crowned {ROAD_EDGE_Z:+.2f} at the edges to "
              f"{ROAD_EDGE_Z + ROAD_CROWN:+.2f} on the centre line (M_DKX_RoadCobble, world XY)",
              pivot=((x0 + x1) / 2, (y0 + ROAD_Y[1]) / 2, 0.0))
    xs = steps(x0, x1, 1.0)
    ys = sorted({y0, ROAD_Y[0], -3.0, -3.6, -4.3, -5.3, -6.3, -7.1, ROAD_Y[1]}, reverse=True)
    ys = [y for y in ys if y <= y0 + 1e-6]
    rng = random.Random(sum(map(ord, name)))
    jit = {}

    def z(x, y):
        k = (round(x, 3), round(y, 3))
        if k not in jit:
            edge = abs(y - y0) < 1e-6 or abs(y - ROAD_Y[1]) < 1e-6 or abs(x - x0) < 1e-6 or abs(x - x1) < 1e-6
            jit[k] = 0.0 if edge else rng.uniform(-0.004, 0.004)
        return road_z(y) + jit[k]
    grid(p.g, xs, ys, z, lambda a, b: ROAD, flip=True, skirt=0.2)
    cell_hulls(p, xs, ys, z)
    p.wear = False
    p.nanite = True
    p.extra = {"x": [x0, x1], "y": [y0, ROAD_Y[1]], "edge_z": ROAD_EDGE_Z, "crown_z": ROAD_EDGE_Z + ROAD_CROWN}
    return p


def verge(name, x0, x1):
    y0, y1 = VERGE_Y
    p = Piece(name, "ground", "Outside/Street",
              f"wall-foot verge X {x0}..{x1}, Y {y0}..{y1}: soil, 0.00 at the wall foot to -0.01 at the kerb; packed "
              "earth across the side-lane mouths", pivot=((x0 + x1) / 2, (y0 + y1) / 2, 0.0))
    xs = sorted(set(steps(x0, x1, 2.0)) | {v for lx in LANES_X.values() for v in lx if x0 < v < x1}
                | {v for v in (APRON_X[0] - 0.05, APRON_X[0] + 0.05, APRON_X[1] - 0.05, APRON_X[1] + 0.05) if x0 < v < x1})
    ys = [y0, (y0 + y1) / 2, y1]

    def z(x, y):
        under = smooth(APRON_X[0] - 0.05, APRON_X[0] + 0.05, x) * (1.0 - smooth(APRON_X[1] - 0.05, APRON_X[1] + 0.05, x))
        return -0.01 * (y0 - y) / (y0 - y1) - 0.03 * under
    grid(p.g, xs, ys, z, lambda a, b: LANE if in_lane(a, 0.0) and b < 0 and
         any(lx[0] <= a <= lx[1] for lx in LANES_X.values()) else VERGE, flip=True, skirt=0.2)
    cell_hulls(p, xs, ys, z, depth=0.3)
    p.wear = False
    p.nanite = len(xs) * 4 >= 2000
    return p


def far_verge(name, x0, x1):
    y0, y1 = FARV_Y
    p = Piece(name, "ground", "Outside/Street",
              f"terrace-edge strip X {x0}..{x1}, Y {y0}..{y1} at 0.00 (soil): the poles, street lamps and the rail "
              "fence stand here", pivot=((x0 + x1) / 2, (y0 + y1) / 2, 0.0))
    xs = steps(x0, x1, 2.0)
    ys = [y0, y1]
    grid(p.g, xs, ys, lambda x, y: 0.0, lambda a, b: VERGE, flip=True, skirt=0.2)
    cell_hulls(p, xs, ys, lambda x, y: 0.0, depth=0.3)
    p.wear = False
    return p


def kerb(name, L):
    """Granite kerb stones along local +X from 0 to L, 0.20 wide (local Y +-0.10), top at local 0, 0.28 deep."""
    p = Piece(name, "ground", "Outside/Street", f"granite kerb run {L} m: dressed stones 0.7-1.3 m long, 0.20 wide, "
              "0.28 deep, rounded arrises (M_DJ_Granite)", pivot=(0.0, 0.0, 0.0))
    rng = random.Random(int(L * 17))
    x = 0.0
    n = 0
    while x < L - 1e-6:
        ln = rng.uniform(0.7, 1.3)
        if L - (x + ln) < 0.45:
            ln = L - x
        x1 = min(L, x + ln)
        dz = rng.uniform(-0.004, 0.003)
        cbox(p.g, x + 0.004, x1 - 0.004, -0.10, 0.10, -0.28, dz, GR, ch=0.018)
        x = x1
        n += 1
    p.hull_box(0.0, L, -0.10, 0.10, -0.28, 0.0)
    p.extra = {"stones": n, "length": L}
    return p


def gutter(name, L):
    """Dished granite channel stones along local +X, 0.35 wide (local Y +-0.175), lips at local 0, dip 4.5 cm."""
    p = Piece(name, "ground", "Outside/Street", f"granite gutter channel {L} m: dished stones about 1 m long, 0.35 "
              "wide, lips at the road edge level, 4.5 cm dip (M_DJ_Granite)", pivot=(0.0, 0.0, 0.0))
    rng = random.Random(int(L * 31))
    hw = 0.175
    prof = [(-hw, 0.0), (-0.11, -0.022), (-0.05, -0.040), (0.0, -GUT_DIP), (0.05, -0.040), (0.11, -0.022), (hw, 0.0)]
    x = 0.0
    n = 0
    while x < L - 1e-6:
        ln = rng.uniform(0.8, 1.2)
        if L - (x + ln) < 0.45:
            ln = L - x
        xa, xb = x + 0.005, min(L, x + ln) - 0.005
        dz = rng.uniform(-0.003, 0.002)
        poly = [(xa, y, z + dz) for y, z in prof] + [(xa, hw, -0.22), (xa, -hw, -0.22)]
        K.prism(p.g, poly, (-1, 0, 0), xb - xa, GR, (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
        x = min(L, x + ln)
        n += 1
    p.hull_box(0.0, L, -hw, hw, -0.22, 0.0)
    p.extra = {"stones": n, "length": L, "dip_m": GUT_DIP}
    return p


def landing():
    x0, x1 = LANDING_X
    ya, yb = KERB_F[0], COPE_Y[0]
    top = KERB_F[2]
    p = Piece("SM_DKX_Landing", "ground", "Outside/Street",
              f"granite slab landing X {x0}..{x1}, Y {ya}..{yb} at {top:+.2f} between the street lamps (dojo1_reference1): "
              "a course of long dressed edge stones on the road side, then slab rows", pivot=((x0 + x1) / 2, (ya + yb) / 2, 0.0))
    rng = random.Random(1407)
    g = p.g
    x = x0
    while x < x1 - 1e-6:                                                  # edge course
        ln = min(rng.uniform(1.0, 1.6), x1 - x)
        if x1 - (x + ln) < 0.5:
            ln = x1 - x
        cbox(g, x + 0.006, x + ln - 0.006, ya - 0.26, ya, -0.30, top + rng.uniform(-0.004, 0.002), GR, ch=0.02)
        x += ln
    y = ya - 0.26
    while y > yb + 1e-6:
        d = min(rng.uniform(0.38, 0.62), y - yb)
        if y - d - yb < 0.22:
            d = y - yb
        x = x0
        while x < x1 - 1e-6:
            w = min(rng.uniform(0.5, 1.2), x1 - x)
            if x1 - (x + w) < 0.3:
                w = x1 - x
            cbox(g, x + 0.007, x + w - 0.007, y - d + 0.007, y - 0.007, -0.12, top + rng.uniform(-0.006, 0.002), GR,
                 ch=0.012)
            x += w
        y -= d
    p.hull_box(x0, x1, yb, ya, -0.30, top)
    p.extra = {"x": list(LANDING_X), "y": [ya, yb], "top": top}
    return p


def terrace():
    """One 8 m module of the terrace edge (pivot at the module's west end on the coping's road-side edge, Y -9.20):
    granite coping stones and the rubble retaining wall with a 6 deg batter down to the canal bed."""
    L = 8.0
    p = Piece("SM_DKX_Terrace_8m", "building", "Outside/Street",
              f"terrace edge, 8 m: granite coping Y {COPE_Y[0]}..{COPE_Y[1]} top {COPE_TOP:+.2f}, rubble retaining wall "
              f"down to {TER_BOT_Z} at Y {TER_BOT_Y} (M_DJ_GraniteRubble on the face)", pivot=(0.0, COPE_Y[0], 0.0))
    p.local = True
    p.rubble_box = True
    g = p.g
    rng = random.Random(8080)
    cw = COPE_Y[0] - COPE_Y[1]
    x = 0.0
    while x < L - 1e-6:
        ln = min(rng.uniform(0.9, 1.4), L - x)
        if L - (x + ln) < 0.5:
            ln = L - x
        cbox(g, x + 0.006, x + ln - 0.006, -cw - 0.03, 0.0, -0.20, COPE_TOP + rng.uniform(-0.005, 0.003), GR, ch=0.02)
        x += ln
    # battered rubble face: grid with small bumps, from under the coping (z -0.12) to the canal bed
    ya, za = -cw, -0.12
    yb, zb = TER_BOT_Y - COPE_Y[0], TER_BOT_Z
    xs = steps(0.0, L, 0.25)
    rows = 10
    verts, faces, idx = [], [], {}
    for j in range(rows + 1):
        t = j / rows
        for i, xv in enumerate(xs):
            bump = 0.012 * math.sin(xv * 9.1 + j * 1.7) * math.cos(xv * 4.3 - j * 2.3) if 0 < j < rows and 0 < i < len(xs) - 1 else 0.0
            idx[i, j] = len(verts)
            verts.append(Vector((xv, ya + (yb - ya) * t - bump, za + (zb - za) * t)))
    for j in range(rows):
        for i in range(len(xs) - 1):
            faces.append((idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]))
    g.add(verts, faces, GRR, (Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))), jit=False)
    p.hulls.append([(x_, y_, z_) for x_ in (0.0, L) for (y_, z_) in
                    ((0.0, COPE_TOP), (-cw, COPE_TOP), (yb, zb), (0.0, zb))])
    p.extra = {"coping_top": COPE_TOP, "face_bottom": [TER_BOT_Y, TER_BOT_Z], "batter_deg":
               round(math.degrees(math.atan((ya - yb) / (za - zb))), 2)}
    return p


def canal():
    L = 8.0
    p = Piece("SM_DKX_Canal_8m", "ground", "Outside/Street",
              f"canal module, 8 m: soil bed at {TER_BOT_Z} (Y {TER_BOT_Y}..{BANK_Y}), the far bank's rubble wall up to "
              f"{BANK_TOP:+.2f} with granite coping", pivot=(0.0, COPE_Y[0], 0.0))
    p.local = True
    p.rubble_box = True
    p.world_origin = None
    g = p.g
    y0 = COPE_Y[0]
    yb0, yb1 = TER_BOT_Y - y0, BANK_Y - y0
    cbox(g, 0.0, L, yb1 - 0.02, yb0 + 0.02, TER_BOT_Z - 0.2, TER_BOT_Z, VERGE, ch=0.002)
    # far bank rubble face (facing +Y, the terrace) with a slight batter
    xs = steps(0.0, L, 0.25)
    verts, faces, idx = [], [], {}
    rows = 5
    for j in range(rows + 1):
        t = j / rows
        for i, xv in enumerate(xs):
            idx[i, j] = len(verts)
            verts.append(Vector((xv, yb1 - 0.08 * t, TER_BOT_Z + (BANK_TOP - 0.10 - TER_BOT_Z) * t)))
    for j in range(rows):
        for i in range(len(xs) - 1):
            faces.append((idx[i, j], idx[i, j + 1], idx[i + 1, j + 1], idx[i + 1, j]))
    g.add(verts, faces, GRR, (Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))), jit=False)
    rng = random.Random(990)
    x = 0.0
    while x < L - 1e-6:
        ln = min(rng.uniform(0.9, 1.4), L - x)
        if L - (x + ln) < 0.5:
            ln = L - x
        cbox(g, x + 0.006, x + ln - 0.006, LOWLANE_Y[0] - y0, yb1 + 0.02, BANK_TOP - 0.22,
             BANK_TOP + rng.uniform(-0.005, 0.003), GR, ch=0.018)
        x += ln
    p.hull_box(0.0, L, yb1, yb0, TER_BOT_Z - 0.2, TER_BOT_Z)
    p.hull_box(0.0, L, LOWLANE_Y[0] - y0, yb1, TER_BOT_Z - 0.2, BANK_TOP)
    return p


def water():
    ya, yb = TER_BOT_Y + 0.07, BANK_Y - 0.03
    p = Piece("SM_DKX_Water", "nocollision", "Outside/Street",
              f"canal water plane X {XW}..{XE}, Y {ya}..{yb} at {WATER_Z} (M_DKX_Water): no collision (token UCX)",
              pivot=(CX, (ya + yb) / 2, WATER_Z))
    grid(p.g, steps(XW, XE, 8.0), [ya, yb], lambda x, y: WATER_Z, lambda a, b: WATER, flip=True)
    c = Vector((CX, (ya + yb) / 2, WATER_Z - 0.6))
    p.hull_box(c.x - 0.02, c.x + 0.02, c.y - 0.02, c.y + 0.02, c.z - 0.02, c.z + 0.02)
    p.wear = False
    return p


def ground_south():
    y0, y1 = LOWLANE_Y[0], YS
    p = Piece("SM_DKX_Ground_South", "ground", "Outside/Ground",
              f"the lower level X {XW}..{XE}, Y {y0}..{y1}: the lower lane (packed earth, {LOWER_Z}) and the house plots "
              "beyond (soil, a gentle undulation)", pivot=(CX, (y0 + y1) / 2, LOWER_Z))
    xs = steps(XW, XE, 2.0)
    ys = sorted({y0, LOWLANE_Y[1]} | set(steps(LOWLANE_Y[1], y1, 2.0)) | {-14.2}, reverse=True)
    grid(p.g, xs, ys, south_z, lambda a, b: LANE if b > LOWLANE_Y[1] else VERGE, flip=True, skirt=0.3)
    cell_hulls(p, xs, ys, south_z)
    p.wear = False
    p.nanite = True
    return p


def ground_north(name, x0, x1, y0, y1):
    p = Piece(name, "ground", "Outside/Ground",
              f"outside ground X {x0}..{x1}, Y {y0}..{y1}: soil within 0.05 m of the courtyard level for 4 m round the "
              "walls, then a gentle undulation (+-0.3 m); packed-earth lanes (replaces SM_DGB_Ground_Outside)",
              pivot=((x0 + x1) / 2, (y0 + y1) / 2, 0.0))
    xs = sorted(set(steps(x0, x1, 2.0)) | {v for lx in LANES_X.values() for v in lx if x0 < v < x1})
    ys = sorted(set(steps(y0, y1, 2.0)) | {v for v in LANE_N_Y if y0 < v < y1})
    grid(p.g, xs, ys, ground_z, lambda a, b: LANE if in_lane(a, b) else VERGE, skirt=0.3)
    cell_hulls(p, xs, ys, ground_z, cell=10.0)
    p.wear = False
    p.nanite = True
    return p


# ------------------------------------------------------------------------------------------------ fences
def rail_fence():
    L = 4.0
    p = Piece("SM_DKX_RailFence_4m", "thin", "Outside/Street",
              "timber post-and-rail fence, 4 m module (dojo1_reference1's terrace-edge fence): 0.10 m posts at 0 and 2 m, "
              "1.0 m tall with a pyramid top, a top rail and a mid rail through the posts (M_DJ_TimberDark)",
              pivot=(0.0, 0.0, 0.0))
    g = p.g
    for xp in (0.0, 2.0):
        cbox(g, xp - 0.05, xp + 0.05, -0.05, 0.05, -0.05, 0.96, TD, ch=0.008)
        verts = [Vector((xp - 0.05, -0.05, 0.96)), Vector((xp + 0.05, -0.05, 0.96)), Vector((xp + 0.05, 0.05, 0.96)),
                 Vector((xp - 0.05, 0.05, 0.96)), Vector((xp, 0.0, 1.02))]
        g.add(verts, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], TD, None)
    for (za, zb) in ((0.84, 0.91), (0.44, 0.50)):
        cbox(g, 0.0, L, -0.025, 0.025, za, zb, TD, ch=0.006)
    p.hull_box(-0.05, L, -0.05, 0.05, 0.0, 1.0)
    p.extra = {"height": 1.02, "posts_x": [0.0, 2.0], "rails_z": [[0.84, 0.91], [0.44, 0.50]]}
    return p


def boards(g, rng, xa, xb, y_face, t, z0, z1, mat=TD, wmin=0.12, wmax=0.18, gap=0.004, face_sign=-1):
    """Vertical boards from xa to xb, their outer face at y_face, thickness t into +y (face_sign -1: the face looks -Y)."""
    x = xa
    while x < xb - 1e-6:
        w = rng.uniform(wmin, wmax)
        if xb - (x + w) < wmin * 0.6:
            w = xb - x
        x1 = min(xb, x + w)
        ya, yb = (y_face, y_face + t) if face_sign < 0 else (y_face - t, y_face)
        cbox(g, x + gap / 2, x1 - gap / 2, ya, yb, z0 + rng.uniform(0.0, 0.01), z1 - rng.uniform(0.0, 0.008), mat,
             ch=0.003)
        x = x1


def board_fence():
    L = 4.0
    p = Piece("SM_DKX_BoardFence_4m", "building", "Outside/Street",
              "board fence, 4 m module, 1.8 m (dojo1_reference1's lower-lane fence): posts at 0 and 2 m, two back rails, "
              "vertical boards facing the lane (+Y), a cap board (M_DJ_TimberDark)", pivot=(0.0, 0.0, 0.0))
    g = p.g
    rng = random.Random(4401)
    for xp in (0.0, 2.0):
        cbox(g, xp + 0.005, xp + 0.095, -0.06, 0.03, -0.05, 1.74, TD, ch=0.008)
    for zr in (0.30, 1.45):
        cbox(g, 0.0, L, -0.06, -0.01, zr, zr + 0.08, TD, ch=0.006)
    boards(g, rng, 0.0, L, 0.03, 0.016, 0.05, 1.72, face_sign=1)
    cbox(g, 0.0, L, -0.07, 0.07, 1.72, 1.80, TD, ch=0.01)
    p.hull_box(0.0, L, -0.07, 0.07, 0.0, 1.80)
    return p


def alley_fence(side):
    """The rear-alley fence (spec 4.6; 1v1 only, opens in the BR): a board fence with a wicket gate at the veranda's
    level. Collision = the grey-box SM_DGB_AlleyFence box EXACTLY (local 0..2.5 x 0..0.1 x 0..2.0 at the grey-box pivot).
    The visual stays clear of the hall's rear corner post and its foundation stone (world X 12.80-13.75 / 30.51-31.20,
    Y 33.80-34.20) and sits behind the veranda deck's end (the deck reaches Y 34.00 at +0.50)."""
    name = f"SM_DKX_AlleyFence_{side}"
    px, py = ALLEY[side]
    p = Piece(name, "building", "Boundary_1v1",
              "rear-alley fence (spec 4.6, 1v1 only): dark vertical boards on the courtyard face, back rails, a cap "
              "board, end posts, and a braced wicket gate (0.9 m) at the veranda level with iron strap hinges and a ring "
              "pull; collision = the grey-box's 2.5 x 0.1 x 2.0 m box exactly", pivot=(px, py, 0.0))
    p.local = True
    g = K.Geo()
    rng = random.Random(70 if side == "W" else 71)
    # built for the WEST fence in local coordinates (x 0..2.5, y 0 = the courtyard face .. 0.1); the east one mirrors x
    POSTS = [(0.0, 0.09), (0.66, 0.75), (1.65, 1.74), (2.20, 2.29)]
    GATE = (0.755, 1.645, 0.52, 1.80)
    for (a, b) in POSTS:
        cbox(g, a, b, 0.005, 0.095, 0.0, 1.86, TD, ch=0.008)
    cbox(g, 0.0, 2.37, 0.0, 0.10, 1.86, 1.98, TD, ch=0.012)                     # cap board (kasagi)
    cbox(g, 0.09, 0.66, 0.055, 0.095, 0.24, 0.32, TD, ch=0.005)                  # back rails
    cbox(g, 0.09, 0.66, 0.055, 0.095, 1.40, 1.48, TD, ch=0.005)
    cbox(g, 1.74, 2.20, 0.055, 0.095, 0.24, 0.32, TD, ch=0.005)
    cbox(g, 1.74, 2.20, 0.055, 0.095, 1.40, 1.48, TD, ch=0.005)
    cbox(g, 0.75, 1.65, 0.03, 0.095, 0.42, 0.50, TD, ch=0.006)                   # gate sill (veranda level)
    cbox(g, 0.75, 1.65, 0.03, 0.095, 1.80, 1.86, TD, ch=0.005)                   # gate head
    boards(g, rng, 0.09, 0.66, 0.018, 0.017, 0.02, 1.855)
    boards(g, rng, 1.74, 2.20, 0.018, 0.017, 0.02, 1.855)
    boards(g, rng, 0.75, 1.65, 0.018, 0.017, 0.02, 0.42)                         # skirting under the gate
    # the wicket gate leaf: boards on the courtyard face, a framed back (stiles + rails + a diagonal brace)
    gx0, gx1, gz0, gz1 = GATE
    boards(g, rng, gx0 + 0.006, gx1 - 0.006, 0.020, 0.016, gz0, gz1, wmin=0.13, wmax=0.16, gap=0.003)
    cbox(g, gx0 + 0.006, gx0 + 0.066, 0.036, 0.07, gz0, gz1, TD, ch=0.004)
    cbox(g, gx1 - 0.066, gx1 - 0.006, 0.036, 0.07, gz0, gz1, TD, ch=0.004)
    for zr in (gz0 + 0.06, gz1 - 0.12):
        cbox(g, gx0 + 0.066, gx1 - 0.066, 0.036, 0.07, zr, zr + 0.06, TD, ch=0.004)
    a, b = Vector((gx0 + 0.09, 0.053, gz0 + 0.14)), Vector((gx1 - 0.09, 0.053, gz1 - 0.16))
    member(g, a, b, 0.055, 0.034, TD, up=(0, 1, 0), ch=0.004)
    # two face battens on the courtyard face (a kido gate) and the iron fittings
    for zr in (gz0 + 0.16, gz1 - 0.20):
        cbox(g, gx0 + 0.02, gx1 - 0.02, 0.006, 0.021, zr, zr + 0.07, TD, ch=0.004)
    for zr in (gz0 + 0.175, gz1 - 0.185):
        cbox(g, gx0 - 0.03, gx0 + 0.30, 0.002, 0.007, zr, zr + 0.04, IR, ch=0.0015)
        K.lathe(g, Vector((gx0 + 0.29, 0.002, zr + 0.02)), (0, -1, 0), (0, 0, 1),
                [(0.0, 0.0), (0.0, 0.009), (0.006, 0.009), (0.006, 0.0)], IR, nseg=8)
    K.lathe(g, Vector((gx1 - 0.10, 0.009, 1.10)), (0, -1, 0), (0, 0, 1),
            [(0.0, 0.0), (0.0, 0.018), (0.008, 0.018), (0.008, 0.0)], IR, nseg=10)
    cbox(g, gx1 - 0.112, gx1 - 0.088, 0.001, 0.019, 0.96, 1.08, IR, ch=0.004)          # iron pull handle
    if side == "E":
        from mathutils import Matrix
        M = Matrix.Translation((ALLEY_BOX[0], 0, 0)) @ Matrix.Scale(-1, 4, (1, 0, 0))
        g = g.transformed(M, mirror=True)
    p.g = g
    p.hulls.append([(x, y, z) for x in (0.0, ALLEY_BOX[0]) for y in (0.0, ALLEY_BOX[1]) for z in (0.0, ALLEY_BOX[2])])
    p.extra = {"hull_local": [0.0, ALLEY_BOX[0], 0.0, ALLEY_BOX[1], 0.0, ALLEY_BOX[2]], "pivot_world": [px, py, 0.0],
               "hull_world": [px, px + ALLEY_BOX[0], py, py + ALLEY_BOX[1], 0.0, ALLEY_BOX[2]],
               "gate_local_x": [GATE[0], GATE[1]] if side == "W" else [round(ALLEY_BOX[0] - GATE[1], 3),
                                                                      round(ALLEY_BOX[0] - GATE[0], 3)],
               "gate_sill_z": 0.50, "visual_x_local": [0.0, 2.37] if side == "W" else [0.13, 2.5]}
    return p


# ------------------------------------------------------------------------------------------------ round 6: 1v1 rear seal
# Spec 4.6 / 5.4: the 2 m strip behind the hall (Y 34-36) and the two pockets behind the corridors (X 7.0-10.5 /
# 33.5-37.0, Y 32.2-36) are closed in the 1v1 and open in the battle royale. verify_r5 found them open: the corridors'
# north walls stop at their last post (X 10.14 / 33.86) and the veranda's west / east edge (X 11.0 / 33.0) faces the
# pocket from Y 32.2 to 34.0, so a player walked off the corridor's end deck or the veranda into the pocket and on
# along the strip. From above, the hall's lower side roofs, the corridors' north slopes (entered from the lower roof
# at X 10.3-10.5), the storehouse / residence roofs (the 0.6 m slot between the corridor-ridge and outbuilding-ridge
# blockers of the grey-box set) and the hall's upper hips all led there too.
# The fix: (a) a visible board fence (the alley fence's style) from the corridor's last post along the lower roof's eave
# line to the alley fence, on both sides (SM_DKX_PocketFence_W / _E); (b) invisible Pawn-only curtains up to the 1v1
# ceiling (+20.0) on every edge of the sealed volume, each its own SM_DKX_1v1_* piece (class 'boundary': hidden in game;
# folder Boundary_1v1, Unreal tag 'Dojo/Boundary_1v1'), listed in layout_outside.json 'onev1_only' so the BR copy drops
# them. The set is self-contained (it repeats the grey-box set's hall ridge, outbuilding and north-wall-top rects),
# so it seals the area with only the duel level's outer ring and ceiling around it.
CEIL = 20.0
POCKET_FENCE = {"W": {"x_face": 10.60, "x_back": 10.50, "post_x": 10.14}, "E": {"x_face": 33.40, "x_back": 33.50,
                                                                                "post_x": 33.86}}
PF_Y = (32.24, 34.0)                   # from the corridor's north edge (its end deck ends at Y 32.22) to the alley fence


def mirror_box(b):
    x0, x1, y0, y1, z0, z1 = b
    return (round(44.0 - x1, 4), round(44.0 - x0, 4), y0, y1, z0, z1)


# (piece, boxes for the WEST side (mirrored about X 22 for the east piece), what it closes)
ONEV1_BLOCKERS = [
    ("PocketSide", [(10.40, 10.50, 32.22, 34.10, 0.0, CEIL), (10.40, 10.50, 31.00, 32.23, 2.75, CEIL)],
     "the pocket's open side along the hall's lower-roof eave line: full height from the corridor's north edge to the "
     "alley fence (behind the visible pocket fence and over its top), and above +2.75 from the corridor ridge (the gap "
     "X 10.30-10.50 between the corridor roof and the hall's lower side roof, and the lower roof's eave)"),
    ("CorridorRoof", [(7.00, 10.50, 31.00, 31.10, 2.75, CEIL), (6.99, 7.10, 31.00, 31.80, 2.75, CEIL)],
     "the corridor ridge from the storehouse wall to the eave-line curtain (the north slope drops into the pocket) and "
     "the link along the storehouse's east wall up to its roof cut (the grey-box set left a 0.6 m slot between them)"),
    ("OutbuildingRoof", [(-1.00, 7.10, 31.70, 31.80, 2.0, CEIL)],
     "the storehouse roof cut at Y 31.7 (its north half and the north-west wall-top corner behind it are part of the "
     "sealed area; routes 2 and 3 stay south of it)"),
]
ONEV1_SHARED = [
    ("HallRear", [(10.40, 33.60, 34.00, 34.10, 0.0, CEIL)],
     "the strip's south face: the hall's rear wall line from eave curtain to eave curtain, full height (over both "
     "alley fences, the lower side roofs' north ends and the upper roof's rear overhang)"),
    ("HallUpperRear", [(12.00, 32.00, 29.00, 29.10, 5.30, CEIL), (12.00, 12.10, 28.99, 34.10, 5.45, CEIL),
                       (31.90, 32.00, 28.99, 34.10, 5.45, CEIL)],
     "the upper roof's rear half: the ridge (spec 5.4) plus both hip eaves from the ridge to the rear wall line (from "
     "the lower side roofs a double jump reached the hips' rear halves); z0 +5.45 is at the upper eave, so the lower "
     "roof keeps every walkable metre"),
    ("NorthWallTop", [(-1.00, 45.00, 36.00, 37.00, 2.0, CEIL)],
     "the north wall top (spec 5.2, 1v1 only), the whole length: the strip's and both pockets' north side above the "
     "wall"),
]


def box_geo(g, b, mat):
    x0, x1, y0, y1, z0, z1 = b
    v = [Vector((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    g.add(v, f, mat, None, jit=False)


def onev1_blocker(name, boxes, note):
    b0 = boxes[0]
    p = Piece(name, "boundary", "Boundary_1v1",
              "round 6, 1v1 ONLY (the BR drops it): invisible Pawn-only blocker, hidden in game, up to the 1v1 ceiling "
              "+20.0 - " + note, pivot=(round((b0[0] + b0[1]) / 2, 4), round((b0[2] + b0[3]) / 2, 4), 0.0))
    for b in boxes:
        box_geo(p.g, b, OX.BLOCK)
        p.hull_box(*b)
    p.wear = False
    p.extra = {"boxes_world": [list(b) for b in boxes], "onev1_only": True}
    return p


def onev1_pieces():
    P = []
    for base, boxes, note in ONEV1_BLOCKERS:
        P.append(onev1_blocker(f"SM_DKX_1v1_{base}_W", boxes, note))
        P.append(onev1_blocker(f"SM_DKX_1v1_{base}_E", [mirror_box(b) for b in boxes], note + " (mirrored about X 22)"))
    for base, boxes, note in ONEV1_SHARED:
        P.append(onev1_blocker(f"SM_DKX_1v1_{base}", boxes, note))
    return P


def pocket_fence(side):
    """The pocket fence (spec 4.6; 1v1 only, opens in the BR): the alley fence's board-fence style (posts, vertical boards
    on the courtyard face, two back rails on the pocket side, a cap board) from the corridor's north edge to the alley
    fence's end post, along the hall's lower-roof eave line, plus a short return panel to the corridor's last post.
    Built in a local frame: x along the fence (0 at the corridor end), y 0 = the courtyard face .. 0.10; the return at the
    corridor end, y 0.10 .. 0.46. The east piece is the mirror image."""
    from mathutils import Matrix
    name = f"SM_DKX_PocketFence_{side}"
    c = POCKET_FENCE[side]
    L = round(PF_Y[1] - PF_Y[0], 4)
    p = Piece(name, "building", "Boundary_1v1",
              "round 6, 1v1 ONLY (opens in the BR): the pocket fence behind the corridor (spec 4.6), a board fence in "
              "the alley fence's style from the corridor's last post to the alley fence, 2.0 m, with a return panel to "
              "the post; collision = the fence box and the return box", pivot=(0.0, 0.0, 0.0))
    p.local = True
    g = K.Geo()
    rng = random.Random(80 if side == "W" else 81)
    cbox(g, 0.0, 0.09, 0.005, 0.095, 0.0, 1.86, TD, ch=0.008)                     # corridor-end post
    cbox(g, L - 0.09, L, 0.005, 0.095, 0.0, 1.86, TD, ch=0.008)                   # alley-end post
    mid = round(L / 2, 3)
    cbox(g, mid - 0.045, mid + 0.045, 0.005, 0.095, 0.0, 1.86, TD, ch=0.008)
    cbox(g, 0.0, L, 0.0, 0.10, 1.86, 1.98, TD, ch=0.012)                          # cap board
    for zr in (0.24, 1.40):                                                       # back rails (pocket side)
        cbox(g, 0.09, mid - 0.045, 0.055, 0.095, zr, zr + 0.08, TD, ch=0.005)
        cbox(g, mid + 0.045, L - 0.09, 0.055, 0.095, zr, zr + 0.08, TD, ch=0.005)
    boards(g, rng, 0.09, mid - 0.045, 0.018, 0.017, 0.02, 1.855)
    boards(g, rng, mid + 0.045, L - 0.09, 0.018, 0.017, 0.02, 1.855)
    # the return panel: its boards stop 2 cm short of the corridor post's foot block (world X 10.25 / 33.75, measured;
    # round-6 clearance), the collision box runs on to the post
    y = 0.10
    while y < 0.33 - 1e-6:
        w = min(0.33 - y, rng.uniform(0.10, 0.13))
        cbox(g, 0.02, 0.05, y + 0.002, y + w - 0.002, 0.02 + rng.uniform(0, 0.01), 1.855, TD, ch=0.003)
        y += w
    cbox(g, 0.0, 0.07, 0.10, 0.34, 1.86, 1.98, TD, ch=0.01)
    hulls = [(0.0, L, 0.0, 0.10, 0.0, 2.0), (0.0, 0.10, 0.10, 0.46, 0.0, 2.0)]
    if side == "W":      # local x -> world +Y, local y -> world -X; pivot (x_face, Y0)
        loc, rot = (c["x_face"], PF_Y[0], 0.0), 90.0
    else:                # mirrored: local x -> world +Y, local y -> world +X; pivot (x_face, Y0)
        g = g.transformed(Matrix.Scale(-1, 4, (0, 1, 0)), mirror=True)
        hulls = [(b[0], b[1], -b[3], -b[2], b[4], b[5]) for b in hulls]
        loc, rot = (c["x_face"], PF_Y[0], 0.0), 90.0
    M = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    p.g = g
    world = []
    for b in hulls:
        pts = [(x, y_, z) for x in b[:2] for y_ in b[2:4] for z in b[4:]]
        p.hulls.append(pts)
        wp = [M @ Vector(q) for q in pts]
        world.append([round(min(q[i] for q in wp), 4) for i in range(3)] + [round(max(q[i] for q in wp), 4)
                                                                            for i in range(3)])
    p.extra = {"placement": {"loc": list(loc), "rot_z": rot}, "hull_world_min_max": world, "length_m": L,
               "height_m": 1.98, "onev1_only": True}
    return p


# ------------------------------------------------------------------------------------------------ houses
P_TILE, A_TILE = 4.0 / 15.0, 0.058   # the kawara texture's course / roll pitch (ox_tex.KAWARA_N)


def tile_slope(g, o, U, S, s_len, u0, u1, mat=OX.KAWARA, rows=2, under=0.11, eave_board=True, frame_up=None, top_cut=0.0):
    """A corrugated tile slope: origin o on the eave line, U along the eave (unit), S up the slope (unit, 3D), from s 0 to
    s_len; the u range per row from u0(s) to u1(s) (hips shrink it). Rolls every P_TILE, 4 vertices per period;
    an underside plane `under` below (timber) and an eave board."""
    o, U, S = Vector(o), Vector(U).normalized(), Vector(S).normalized()
    N = U.cross(S).normalized()
    if N.z < 0:
        N = -N
    ncol = max(4, int(round((u1(0.0) - u0(0.0)) / (P_TILE / 4))))
    prof = [0.0, 0.30, 1.0, 0.30]         # a wide pan, a narrow round roll
    s_len = s_len - top_cut               # long slopes stop short of the ridge (the ridge roll covers the join)
    apex = u1(s_len) - u0(s_len) < 1e-3   # a hip end closes to a point
    verts, faces, uvs = [], [], []
    ss = [s_len * k / (rows - 1) for k in range(rows)]
    for jr, s in enumerate(ss):
        a, b = u0(s), u1(s)
        if apex and jr == rows - 1:
            verts.append(o + U * a + S * s)
            uvs.append((ncol / 2 * (P_TILE / 4) / 4.0, s / 4.0 - 1.0 / 30.0))
            break
        for i in range(ncol + 1):
            u = a + (b - a) * i / ncol
            edge = i == 0 or i == ncol
            off = 0.0 if edge else A_TILE * prof[i % 4]
            verts.append(o + U * u + S * s + N * off)
            # UV0 in tile units aligned with ox_tex.kawara: a pan at every 4th column, a course lip at the eave
            uvs.append((i * (P_TILE / 4) / 4.0, s / 4.0 - 1.0 / 30.0))
    m = ncol + 1
    up = U.cross(S).z >= 0
    for j in range(rows - 1):
        for i in range(ncol):
            a_ = j * m + i
            if apex and j == rows - 2:
                f = (a_, a_ + 1, (rows - 1) * m)
            else:
                f = (a_, a_ + 1, a_ + 1 + m, a_ + m)
            faces.append(f if up else f[::-1])
    g.add(verts, faces, mat, (U, S, N), jit=False, smooth=set(range(len(faces))), uvs=uvs)
    # underside
    if apex:
        uv = [o + U * u0(0.0) - N * under, o + U * u1(0.0) - N * under, o + U * u0(s_len) + S * s_len - N * under]
        g.add(uv, [(0, 2, 1)], TD, (U, S, N), jit=False)
    else:
        uv = []
        for s in (0.0, s_len):
            uv += [o + U * u0(s) + S * s - N * under, o + U * u1(s) + S * s - N * under]
        g.add(uv, [(0, 2, 3, 1)], TD, (U, S, N), jit=False)
    # eave board (fascia) along the eave edge, and the edge strip closing the gap tile -> underside
    if eave_board:
        a, b = o + U * u0(0.0), o + U * u1(0.0)
        member(g, (a + b) / 2 - U * ((b - a).length / 2) - N * (under / 2),
               (a + b) / 2 + U * ((b - a).length / 2) - N * (under / 2), 0.04, under + 0.05, TD, up=N, ch=0.006)
    return verts


def ridge_roll(g, a, b, r=0.10, mat=TL, box_w=0.30, box_h=0.16):
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    side = Vector((0, 0, 1)).cross(ax)
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    up = ax.cross(side).normalized()
    if up.z < 0:
        up = -up
    L = (b - a).length
    K.obox(g, (a + b) / 2 + up * (box_h / 2 - 0.02), ax, side, up, L / 2 + 0.05, box_w / 2, box_h / 2, mat)
    K.lathe(g, a + up * (box_h - 0.02) - ax * 0.10, ax, up, [(0.0, 0.0), (0.0, r), (L + 0.20, r), (L + 0.20, 0.0)],
            mat, arc=(-10, 190), nseg=8)


def gable_triangle(g, x, y0, y1, z0, z_apex, facing_x, mat):
    """A plaster gable triangle in the plane x (facing +-X), base y0..y1 at z0, apex over the middle."""
    ym = (y0 + y1) / 2
    v = [Vector((x, y0, z0)), Vector((x, y1, z0)), Vector((x, ym, z_apex))]
    f = [(0, 1, 2)] if facing_x < 0 else [(0, 2, 1)]
    g.add(v, f, mat, (Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
    # a timber tie beam along the base
    cbox(g, x - 0.03, x + 0.03, y0 + 0.1, y1 - 0.1, z0, z0 + 0.18,
         TD, ch=0.006)


def house_walls(g, W, D, z_top, wall_mat, storeys, rng, front_style):
    """Walls of a house on local X -W/2..W/2 (frontage), Y -D/2 (front, facing -Y) .. D/2, from the ground to z_top."""
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    cbox(g, x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, -0.40, 0.22, GR, ch=0.02)          # stone plinth
    cbox(g, x0, x1, y0, y1, 0.22, z_top, wall_mat, ch=0.01)                                  # wall body
    cbox(g, x0 - 0.02, x1 + 0.02, y0 - 0.02, y0 + 0.2, 0.22, 0.85, TD, ch=0.006)           # front base boards
    cbox(g, x0 - 0.02, x1 + 0.02, y1 - 0.2, y1 + 0.02, 0.22, 0.85, TD, ch=0.006)
    cbox(g, x0 - 0.02, x0 + 0.2, y0, y1, 0.22, 0.85, TD, ch=0.006)
    cbox(g, x1 - 0.2, x1 + 0.02, y0, y1, 0.22, 0.85, TD, ch=0.006)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):                                # corner posts
        cbox(g, cx - 0.09, cx + 0.09, cy - 0.09, cy + 0.09, 0.22, z_top, TD, ch=0.008)
    for yy in (y0, y1):                                                                      # eave beams
        cbox(g, x0 - 0.04, x1 + 0.04, yy - 0.05, yy + 0.05, z_top - 0.22, z_top, TD, ch=0.008)
    n_bays = max(2, int(round(W / 1.8)))
    for k in range(1, n_bays):                                                               # front bay posts
        xp = x0 + W * k / n_bays
        cbox(g, xp - 0.06, xp + 0.06, y0 - 0.035, y0 + 0.01, 0.85, z_top - 0.22, TD, ch=0.005)
    if storeys == 2:
        for (a, b, c, d) in ((x0, x1, y0 - 0.05, y0 + 0.02), (x0, x1, y1 - 0.02, y1 + 0.05),
                             (x0 - 0.05, x0 + 0.02, y0, y1), (x1 - 0.02, x1 + 0.05, y0, y1)):
            cbox(g, a, b, c, d, 2.85, 3.05, TD, ch=0.006)                                  # floor band
    # front openings: ground floor
    bay_w = W / n_bays
    for k in range(n_bays):
        xa, xb = x0 + bay_w * k + 0.12, x0 + bay_w * (k + 1) - 0.12
        kind = front_style[k % len(front_style)]
        if kind == "door":
            cbox(g, xa + 0.05, xb - 0.05, y0 - 0.03, y0 + 0.005, 0.25, 2.05, TD, ch=0.008)
            for xx in steps(xa + 0.05, xb - 0.05, 0.14)[1:-1]:
                cbox(g, xx - 0.006, xx + 0.006, y0 - 0.036, y0 - 0.029, 0.3, 2.0, TD, ch=0.002)
        elif kind in ("lattice", "lit"):
            cbox(g, xa, xb, y0 - 0.03, y0 + 0.005, 0.95, 1.95, TD, ch=0.006)
            if kind == "lit":     # one quad (the library's glass takes UV 0-1 per face: a box would count 26 panes)
                g.add([Vector((xa + 0.06, y0 - 0.032, 1.01)), Vector((xb - 0.06, y0 - 0.032, 1.01)),
                       Vector((xb - 0.06, y0 - 0.032, 1.89)), Vector((xa + 0.06, y0 - 0.032, 1.89))], [(0, 1, 2, 3)], GL,
                      (Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))))
            else:
                cbox(g, xa + 0.06, xb - 0.06, y0 - 0.036, y0 - 0.029, 1.01, 1.89, TD, ch=0.002)
            for xx in steps(xa + 0.06, xb - 0.06, 0.09)[1:-1]:
                cbox(g, xx - 0.008, xx + 0.008, y0 - 0.05, y0 - 0.03, 1.01, 1.89, TD, ch=0.002)
    if storeys == 2:
        for k in range(n_bays):
            if k % 2 == 1 or n_bays == 2:
                xa, xb = x0 + bay_w * k + 0.35, x0 + bay_w * (k + 1) - 0.35
                cbox(g, xa, xb, y0 - 0.03, y0 + 0.005, 3.75, 4.40, TD, ch=0.006)
                for xx in steps(xa + 0.05, xb - 0.05, 0.10)[1:-1]:
                    cbox(g, xx - 0.022, xx + 0.022, y0 - 0.06, y0 - 0.03, 3.80, 4.35, wall_mat, ch=0.004)


def house(name, W, D, storeys, roof, wall_mat, eave, front_style, seed, note):
    p = Piece(name, "building", "Outside/Town", note, pivot=(0.0, 0.0, 0.0))
    g = p.g
    rng = random.Random(seed)
    tn = math.tan(math.radians(25.0))
    ov_e, ov_v = 0.60, 0.40
    z_wall = eave + ov_e * tn          # the wall top (the roof plane at the wall line)
    house_walls(g, W, D, z_wall - 0.03, wall_mat, storeys, rng, front_style)
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    if roof in ("gable", "hip"):
        run = D / 2 + ov_e
        s_len = run / math.cos(math.radians(25.0))
        z_ridge = eave + run * tn
        if roof == "gable":
            u0 = lambda s: -W / 2 - ov_v  # noqa: E731
            u1 = lambda s: W / 2 + ov_v   # noqa: E731
            rows = 2
        else:
            half = (W - D) / 2
            u0 = lambda s: -(half + run) + s * math.cos(math.radians(25.0))      # noqa: E731
            u1 = lambda s: (half + run) - s * math.cos(math.radians(25.0))        # noqa: E731
            rows = 4
        c = math.cos(math.radians(25.0))
        sn = math.sin(math.radians(25.0))
        # front slope (eave at y0 - ov_e, rising toward +Y) and back slope (mirror)
        tile_slope(g, (0.0, y0 - ov_e, eave), (1, 0, 0), (0, c, sn), s_len, u0, u1, rows=rows, top_cut=0.03)
        tile_slope(g, (0.0, y1 + ov_e, eave), (-1, 0, 0), (0, -c, sn), s_len,
                   lambda s: -u1(s), lambda s: -u0(s), rows=rows, top_cut=0.03)
        if roof == "gable":
            ridge_roll(g, (x0 - ov_v, 0.0, z_ridge), (x1 + ov_v, 0.0, z_ridge))
            for xx, fx in ((x0, -1), (x1, 1)):
                gable_triangle(g, xx, y0, y1, z_wall, z_ridge - 0.10 - 0.05, fx, wall_mat)
                for sgn in (-1, 1):                                             # verge boards
                    a = Vector((xx + fx * (ov_v - 0.02), sgn * (D / 2 + ov_e), eave - 0.08))
                    b = Vector((xx + fx * (ov_v - 0.02), 0.0, z_ridge - 0.08))
                    member(g, a, b, 0.05, 0.22, TD, up=(0, 0, 1), ch=0.006)
        else:
            # hip slopes at the ends (the same 25 deg pitch and run as the long slopes)
            hs = run / c
            e_ = D / 2 + ov_e - 0.006          # 6 mm inside the long slopes' eave corners (no coincident vertices)
            tile_slope(g, (x1 + ov_e, 0.0, eave), (0, 1, 0), (-c, 0, sn), hs,
                       lambda s: -e_ + s * c, lambda s: e_ - s * c, rows=4)
            tile_slope(g, (x0 - ov_e, 0.0, eave), (0, -1, 0), (c, 0, sn), hs,
                       lambda s: -e_ + s * c, lambda s: e_ - s * c, rows=4)
            half = (W - D) / 2
            ridge_roll(g, (-half, 0.0, z_ridge), (half, 0.0, z_ridge))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    a = Vector((sx * (W / 2 + ov_e), sy * (D / 2 + ov_e), eave + 0.03))
                    b = Vector((sx * half, 0.0, z_ridge + 0.03))
                    K.lathe(g, a, (b - a).normalized(), (0, 0, 1),
                            [(0.0, 0.0), (0.0, 0.085), ((b - a).length, 0.085), ((b - a).length, 0.0)], TL,
                            arc=(-10, 190), nseg=6)
    elif roof == "gable_front":
        run = W / 2 + ov_e
        s_len = run / math.cos(math.radians(25.0))
        z_ridge = eave + run * tn
        c = math.cos(math.radians(25.0))
        sn = math.sin(math.radians(25.0))
        u0 = lambda s: -D / 2 - ov_v  # noqa: E731
        u1 = lambda s: D / 2 + ov_v   # noqa: E731
        tile_slope(g, (x0 - ov_e, 0.0, eave), (0, -1, 0), (c, 0, sn), s_len, lambda s: -u1(s), lambda s: -u0(s), rows=2,
                   top_cut=0.03)
        tile_slope(g, (x1 + ov_e, 0.0, eave), (0, 1, 0), (-c, 0, sn), s_len, u0, u1, rows=2, top_cut=0.03)
        ridge_roll(g, (0.0, y0 - ov_v, z_ridge), (0.0, y1 + ov_v, z_ridge))
        z_wall = eave + ov_e * tn
        for yy, fy in ((y0, -1), (y1, 1)):
            v = [Vector((x0, yy, z_wall)), Vector((x1, yy, z_wall)), Vector((0.0, yy, z_ridge - 0.15))]
            g.add(v, [(0, 1, 2)] if fy < 0 else [(0, 2, 1)], wall_mat, (Vector((1, 0, 0)), Vector((0, 0, 1)),
                                                                      Vector((0, 1, 0))))
            cbox(g, x0 + 0.1, x1 - 0.1, yy - 0.03, yy + 0.03, z_wall, z_wall + 0.18, TD, ch=0.006)
            for sgn in (-1, 1):
                a = Vector((sgn * (W / 2 + ov_e), yy + fy * (ov_v - 0.02), eave - 0.08))
                b = Vector((0.0, yy + fy * (ov_v - 0.02), z_ridge - 0.08))
                member(g, a, b, 0.05, 0.22, TD, up=(0, 0, 1), ch=0.006)
    if storeys == 2:
        # the pent roof (hisashi) along the front between the storeys
        c = math.cos(math.radians(25.0))
        sn = math.sin(math.radians(25.0))
        dep = 0.95
        tile_slope(g, (0.0, y0 - dep, 3.05), (1, 0, 0), (0, c, sn), dep / c, lambda s: -W / 2 - 0.1,
                   lambda s: W / 2 + 0.1, rows=2)
        cbox(g, x0 - 0.1, x1 + 0.1, y0 - 0.04, y0 + 0.02, 3.05 + dep * tn - 0.05, 3.05 + dep * tn + 0.10, TL, ch=0.01)
    p.hull_box(x0, x1, y0, y1, -0.4, z_wall)
    p.nanite = False
    p.extra = {"W": W, "D": D, "storeys": storeys, "roof": roof, "eave": eave}
    return p


HOUSES = {
    "SM_DKX_House_A": dict(W=7.2, D=9.0, storeys=2, roof="gable", wall_mat=PL, eave=5.2,
                           front_style=["lattice", "door", "lit", "lattice"], seed=11,
                           note="two-storey town house (machiya): gable roof along the frontage, a pent roof between the "
                                "storeys, lattice front, slatted upper windows"),
    "SM_DKX_House_B": dict(W=10.0, D=7.0, storeys=1, roof="hip", wall_mat=PLE, eave=3.1,
                           front_style=["lattice", "door", "lattice", "lit", "lattice"], seed=12,
                           note="one-storey house with a hipped roof (earthen plaster)"),
    "SM_DKX_House_C": dict(W=5.6, D=7.0, storeys=2, roof="gable_front", wall_mat=PL, eave=5.0,
                           front_style=["door", "lattice", "lattice"], seed=13,
                           note="two-storey plastered storehouse, gable to the front"),
    "SM_DKX_House_D": dict(W=14.0, D=6.2, storeys=1, roof="gable", wall_mat=PLE, eave=3.6,
                           front_style=["door", "lattice", "lit", "door", "lattice", "lattice", "door", "lit"], seed=14,
                           note="long one-and-a-half-storey row house, gable roof along the frontage"),
    "SM_DKX_House_E": dict(W=11.0, D=8.4, storeys=2, roof="hip", wall_mat=PL, eave=5.6,
                           front_style=["lattice", "lit", "door", "lattice", "lit", "lattice"], seed=15,
                           note="large two-storey house with a hipped roof and a front pent roof"),
}


def house_plan():
    """Neighbouring houses round the compound (dojo1_reference1 / 2): one row along each outer lane, a staggered second
    row behind it for a layered skyline, and a row on the lower level beyond the canal. Returns [(piece, x, y, rot)]."""
    rng = random.Random(2929)
    out = []
    order = ["SM_DKX_House_A", "SM_DKX_House_B", "SM_DKX_House_D", "SM_DKX_House_C", "SM_DKX_House_E",
             "SM_DKX_House_A", "SM_DKX_House_B", "SM_DKX_House_C", "SM_DKX_House_E", "SM_DKX_House_D"]

    def row(front, axis, a0, a1, facing_rot, k0, skip=(), gap=(1.4, 3.6), back=0.0, two_storey=None):
        """Houses along a line: axis 'y' (a west / east row) or 'x' (a north / south row). front = the front line
        coordinate; the house body lies away from the lane (sign from facing)."""
        a = a0
        k = k0
        seq = order if two_storey is None else two_storey
        while True:
            pc = seq[k % len(seq)]
            if rng.random() < 0.35:                    # round 5 f1: break the cycle (the judges: one type repeated)
                pc = rng.choice(list(HOUSES))
            h = HOUSES[pc]
            # round 5 f1: every house its own frontage length and height (instance scale on local X / Z)
            sx, sz = rng.uniform(0.82, 1.22), rng.uniform(0.86, 1.16)
            W, D = h["W"] * sx, h["D"]
            if a + W > a1:
                break
            mid = a + W / 2
            if any(s0 - W / 2 < mid < s1 + W / 2 for (s0, s1) in skip):
                a += 2.0
                continue
            depth_sign = {90.0: -1, -90.0: 1, 0.0: 1, 180.0: -1}[facing_rot]
            c = front + depth_sign * (D / 2 + back)
            if axis == "y":
                out.append((pc, c, mid, facing_rot, (round(sx, 3), 1.0, round(sz, 3))))
            else:
                out.append((pc, mid, c, facing_rot, (round(sx, 3), 1.0, round(sz, 3))))
            a += W + rng.uniform(*gap)
            k += 1

    sk = [(LANE_N_Y[0] - 0.5, LANE_N_Y[1] + 0.5)]
    row(LANES_X["W"][0] - 2.0, "y", -0.5, 75.0, 90.0, 0, skip=sk)                   # west row, facing the west lane
    row(LANES_X["W"][0] - 20.0, "y", 4.0, 72.0, 90.0, 3, skip=sk, gap=(4.0, 9.0))   # second west row
    row(LANES_X["E"][1] + 2.0, "y", -0.5, 75.0, -90.0, 5, skip=sk)                  # east row
    row(LANES_X["E"][1] + 20.0, "y", 3.0, 72.0, -90.0, 7, skip=sk, gap=(4.0, 9.0))
    tall = ["SM_DKX_House_E", "SM_DKX_House_B", "SM_DKX_House_C", "SM_DKX_House_A", "SM_DKX_House_D", "SM_DKX_House_E",
            "SM_DKX_House_C", "SM_DKX_House_B"]   # round 5 f1: single-storey and kura mixed in
    # north row, facing the north lane: mostly two-storey, so their roofs show over the storehouse and the residence
    # from the gate (dojo1_reference2)
    row(LANE_N_Y[1] + 2.0, "x", LANES_X["W"][1] + 1.5, LANES_X["E"][0] - 1.0, 0.0, 0, two_storey=tall)
    row(LANE_N_Y[1] + 16.0, "x", LANES_X["W"][1] + 3.0, LANES_X["E"][0] - 2.0, 0.0, 6, gap=(5.0, 10.0))
    row(-18.2, "x", -80.0, 126.0, 180.0, 1, gap=(1.5, 5.0))                          # beyond the lower lane
    return out


# ------------------------------------------------------------------------------------------------ far
def rect_edge_point(theta):
    """Where a ray from (CX, CY) at angle theta leaves the local town rectangle."""
    dx, dy = math.cos(theta), math.sin(theta)
    ts = []
    for (bound, d, o) in ((XW, dx, CX), (XE, dx, CX)):
        if abs(d) > 1e-9:
            t = (bound - o) / d
            if t > 0:
                ts.append(t)
    for (bound, d, o) in ((YS, dy, CY), (YN, dy, CY)):
        if abs(d) > 1e-9:
            t = (bound - o) / d
            if t > 0:
                ts.append(t)
    t = min(ts)
    return CX + dx * t, CY + dy * t


def edge_z(x, y):
    if y < LOWLANE_Y[0] + 0.5:
        return south_z(x, y)
    if y < COPE_Y[0]:
        return TER_BOT_Z
    return ground_z(x, y)


FAR_R = 430.0          # round 5 f1: the far town / far ground radius (the first ridge ring's front foot at 450 m)


def far_z_r(z0, d):
    """Far ground height d m past the town rectangle's edge (edge height z0): a gentle fall to -4 m."""
    return z0 + (-4.0 - z0) * smooth(0.0, 350.0, d)


def far_z(x, y):
    th = math.atan2(y - CY, x - CX)
    ex, ey = rect_edge_point(th)
    return far_z_r(edge_z(ex, ey) - 0.3, math.hypot(x - CX, y - CY) - math.hypot(ex - CX, ey - CY))


FACADE_ATLAS = OX.WORK / "round6" / "build" / "facade_tiles" / "tiles_atlas.json"
FAR_TILES = json.loads(FACADE_ATLAS.read_text(encoding="utf-8"))["tiles"] if FACADE_ATLAS.exists() else {}


def far_tiles(kind, w, eave):
    """Round 6: which baked facade (ox_facade.py tiles of this track's own House_A..E) a far house wears: (front, side)."""
    if kind in ("gable_front", "kura"):
        return "C_front", "A_side"
    if eave >= 5.0:                                           # two-storey
        return ("E_front", "E_side") if w > 9.0 else ("A_front", "A_side")
    if kind == "hip":
        return "B_front", "B_side"
    return ("D_front", "B_side") if w > 10.5 else ("B_front", "B_side")


def far_house(g, rng, cx, cy, ang, w, d, eave, kind, z0):
    """Round 6: one impostor-style far-town house (about 20 tris): four walls wearing the baked facade atlas
    (M_DKX_FarFacade: the front tile on the street side, a side tile on the others, a plaster patch on the gables), a
    gable / hip / gable-front roof in the town's kawara tile texture (M_DKX_FarKawara, UV0 in tile units along the eave /
    up the slope as tile_slope lays it) with eave overhangs and a 3 cm lower underside (seen from the courtyard's low
    eye). u = frontage (w), v = depth (d), rotated by ang; the front is the -v side (it faces the street)."""
    ca, sa = math.cos(ang), math.sin(ang)

    def add(vs, fs, mat, uvs):
        # a 1-3 mm offset per part: the far town sits up to 430 m from its pivot, where float32 swallows the
        # library's 0.03 mm jitter (qa_check's coincident-vertex gate); invisible at that range
        dd = Vector((rng.uniform(1e-3, 3e-3) * rng.choice((-1, 1)), rng.uniform(1e-3, 3e-3) * rng.choice((-1, 1)),
                     rng.uniform(1e-3, 3e-3)))
        g.add([v + dd for v in vs], fs, mat, None, jit=False, uvs=uvs)

    def P0(u, v, z):
        return Vector((cx + u * ca - v * sa, cy + u * sa + v * ca, z))
    front, side = far_tiles(kind, w, eave)
    hu, hv = w / 2, d / 2
    corners = [(-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv)]
    for k in range(4):              # outward walls, each running left -> right as seen from outside
        (u0, v0), (u1, v1) = corners[k], corners[(k + 1) % 4]
        T0 = FAR_TILES[front if k == 0 else side]
        if k != 0 and rng.random() < 0.5:           # mirror the plain side tiles now and then (no repeated stains)
            T0 = [T0[2], T0[1], T0[0], T0[3]]
        uv = [(T0[0], T0[1]), (T0[2], T0[1]), (T0[2], T0[3]), (T0[0], T0[3])]
        add([P0(u0, v0, z0), P0(u1, v1, z0), P0(u1, v1, eave), P0(u0, v0, eave)], [(0, 1, 2, 3)], OX.FFAC, uv)
    ov = 0.5
    tn = math.tan(math.radians(rng.uniform(22.0, 28.0)))
    cs = math.cos(math.atan(tn))
    if kind in ("gable_front", "kura"):                 # ridge along v: swap the axes (a quarter turn)
        hu, hv = hv, hu

        def P(u, v, z):
            return P0(-v, u, z)
    else:
        P = P0
    zr = eave + hv * tn                                 # ridge over the wall line's centre
    ze = eave - ov * tn                                 # the eave edge, ov past the wall

    def slope_uv(pts_uv, eave_axis, eave_at, sign):
        """UV0 in kawara tile units: along the eave (m / 4), up the slope (m / 4, a course lip at the eave)."""
        out = []
        for (u, v) in pts_uv:
            a = (u if eave_axis == "u" else v) * sign
            run = abs((v if eave_axis == "u" else u) - eave_at)
            out.append((a / 4.0, run / cs / 4.0 - 1.0 / 30.0))
        return out
    faces = []                                          # (param points [(u, v)], z list, eave axis, eave coord, sign)
    if kind == "hip" and hu > hv + 0.5:
        rl = hu - hv
        faces.append(([(-hu - ov, -hv - ov), (hu + ov, -hv - ov), (rl, 0.0), (-rl, 0.0)], [ze, ze, zr, zr], "u",
                      -hv - ov, 1))
        faces.append(([(hu + ov, hv + ov), (-hu - ov, hv + ov), (-rl, 0.0), (rl, 0.0)], [ze, ze, zr, zr], "u",
                      hv + ov, -1))
        faces.append(([(hu + ov, -hv - ov), (hu + ov, hv + ov), (rl, 0.0)], [ze, ze, zr], "v", hu + ov, 1))
        faces.append(([(-hu - ov, hv + ov), (-hu - ov, -hv - ov), (-rl, 0.0)], [ze, ze, zr], "v", -hu - ov, -1))
    else:
        faces.append(([(-hu - ov, -hv - ov), (hu + ov, -hv - ov), (hu + ov, 0.0), (-hu - ov, 0.0)], [ze, ze, zr, zr],
                      "u", -hv - ov, 1))
        faces.append(([(hu + ov, hv + ov), (-hu - ov, hv + ov), (-hu - ov, 0.0), (hu + ov, 0.0)], [ze, ze, zr, zr],
                      "u", hv + ov, -1))
        T1 = FAR_TILES[side]                            # gable triangles: the side tile's plain plaster band
        vv0, vv1 = T1[1] + 0.70 * (T1[3] - T1[1]), T1[1] + 0.96 * (T1[3] - T1[1])
        um = (T1[0] + T1[2]) / 2
        for sgn in (-1, 1):
            a, b, c = P(sgn * hu, -hv, eave), P(sgn * hu, hv, eave), P(sgn * hu, 0.0, zr - 0.05)
            uva, uvb, uvc = (T1[0] + 0.1 * (T1[2] - T1[0]), vv0), (T1[2] - 0.1 * (T1[2] - T1[0]), vv0), (um, vv1)
            if sgn > 0:
                add([a, b, c], [(0, 1, 2)], OX.FFAC, [uva, uvb, uvc])
            else:
                add([b, a, c], [(0, 1, 2)], OX.FFAC, [uva, uvb, uvc])
    dn = Vector((0.0, 0.0, -0.03))
    for pts, zs, axis, at, sign in faces:
        q = [P(u, v, z) for (u, v), z in zip(pts, zs)]
        uv = slope_uv(pts, axis, at, sign)
        idx = tuple(range(len(q)))
        add(q, [idx], OX.FKAW, uv)                                         # top
        add([v + dn for v in q], [idx[::-1]], OX.FKAW, uv)                 # 3 cm lower underside


def far_town():
    """Round 5 fix f1, round 6: the far town, roof clusters from the town rectangle out to FAR_R (430 m), so the ground
    never shows as a plain at the horizon (dojo1_reference2: distant roofs, then the hazy ranges). Districts of
    rectangular blocks (their own grid rotation per 45 deg sector), two back-to-back rows of houses per block with random
    frontage, depth, eave height and type (gable, hip, gable-front, kura, two-storey), thinning a little with distance.
    Round 6: impostor walls (the baked facade atlas) and kawara roofs instead of flat colours, and an EDGE ROW of houses
    along all four sides of the town rectangle, fronts turned to the town, so every road, lane and canal that reaches the
    rectangle's edge ends at a house front instead of the far ground's hard straight edge."""
    p = Piece("SM_DKX_FarTown", "nocollision", "Outside/Far",
              "round 6: the far town (impostor houses to 430 m, about 20 tris a house, plus an edge row closing the "
              "town rectangle): walls in M_DKX_FarFacade (an atlas baked from this track's own House_A..E), roofs in "
              "M_DKX_FarKawara; no collision (token UCX)", pivot=(CX, CY, 0.0))
    rng = random.Random(4242)
    g = p.g
    n_house, n_edge = 0, 0

    def kind_pick(r_):
        t = r_.random()
        if t < 0.50:
            return "gable", r_.uniform(2.8, 3.5)
        if t < 0.70:
            return "hip", r_.uniform(3.0, 3.6)
        if t < 0.82:
            return "gable_front", r_.uniform(4.0, 5.0)
        if t < 0.90:
            return "kura", r_.uniform(4.2, 5.2)
        return "gable", r_.uniform(5.0, 5.8)                                   # two-storey
    # the edge row: just outside each side of the rectangle, fronts to the town (the street ends at house fronts)
    EDGE_GAP, EDGE_BAND = 1.0, 14.0
    rng_e = random.Random(5151)
    # (axis the row runs along, a0, a1, house centre from its depth, yaw turning the front (-v) back into the town)
    sides = [("y", YS - 10.0, YN + 10.0, lambda dep: XE + EDGE_GAP + dep / 2, -math.pi / 2),    # east, fronts -X
             ("y", YS - 10.0, YN + 10.0, lambda dep: XW - EDGE_GAP - dep / 2, math.pi / 2),     # west, fronts +X
             ("x", XW, XE, lambda dep: YN + EDGE_GAP + dep / 2, 0.0),                           # north, fronts -Y
             ("x", XW, XE, lambda dep: YS - EDGE_GAP - dep / 2, math.pi)]                       # south, fronts +Y
    for axis, a0, a1, off, face in sides:
        t = a0 + rng_e.uniform(0.0, 2.0)
        while t < a1:
            wdt = rng_e.uniform(6.0, 12.0)
            dep = rng_e.uniform(6.5, 9.0)
            kind, eave = kind_pick(rng_e)
            c = t + wdt / 2
            hx, hy = (off(dep), c) if axis == "y" else (c, off(dep))
            z0 = far_z(hx, hy) - 0.2
            far_house(g, rng_e, hx, hy, face, wdt, dep, z0 + eave, kind, z0)
            n_edge += 1
            t += wdt + rng_e.uniform(0.3, 1.6)
    sectors = 8
    for sct in range(sectors):
        rot = math.radians(sct * 45.0 + rng.uniform(-12.0, 12.0))
        ca, sa = math.cos(rot), math.sin(rot)
        BL, BS, ST = rng.uniform(30.0, 40.0), rng.uniform(19.0, 25.0), rng.uniform(4.5, 6.5)
        n = int(FAR_R / min(BL, BS)) + 2
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                bu, bv = i * (BL + ST), j * (BS + ST)
                bx, by = CX + bu * ca - bv * sa, CY + bu * sa + bv * ca
                th = math.atan2(by - CY, bx - CX) % (2 * math.pi)
                if int(th / (2 * math.pi / sectors)) % sectors != sct:
                    continue
                r = math.hypot(bx - CX, by - CY)
                if r > FAR_R - 10.0:
                    continue
                if XW + 20.0 < bx < XE - 20.0 and YS + 20.0 < by < YN - 20.0:
                    continue
                if rng.random() < 0.08:                 # an open yard / temple ground now and then
                    continue
                for row in (-1, 1):
                    dep = rng.uniform(6.0, 9.0)
                    vv = bv + row * (BS / 2 - dep / 2 - rng.uniform(0.0, 0.8))
                    u = bu - BL / 2 + rng.uniform(0.0, 1.5)
                    while True:
                        wdt = rng.uniform(6.0, 14.0)
                        if u + wdt > bu + BL / 2:
                            break
                        uc = u + wdt / 2
                        hx, hy = CX + uc * ca - vv * sa, CY + uc * sa + vv * ca
                        u += wdt + rng.uniform(0.3, 2.2)
                        m = EDGE_GAP + EDGE_BAND + 0.5 * math.hypot(wdt, dep)        # clear of the edge row
                        if XW - m < hx < XE + m and YS - m < hy < YN + m:
                            continue
                        rr = math.hypot(hx - CX, hy - CY)
                        if rr > FAR_R or rng.random() < 0.06 + 0.22 * smooth(250.0, FAR_R, rr):
                            continue
                        kind, eave = kind_pick(rng)
                        z0 = far_z(hx, hy) - 0.2
                        far_house(g, rng, hx, hy, rot + (math.pi if row > 0 else 0.0), wdt, dep, z0 + eave, kind, z0)
                        n_house += 1
    p.hull_box(CX - 0.02, CX + 0.02, CY - 0.02, CY + 0.02, -60.02, -59.98)
    p.wear = False
    p.nanite = True
    p.extra = {"houses": n_house + n_edge, "edge_row_houses": n_edge, "radius_m": FAR_R,
               "materials": [OX.FFAC, OX.FKAW], "facade_atlas": str(FACADE_ATLAS)}
    return p


def far_ground():
    p = Piece("SM_DKX_FarGround", "nocollision", "Outside/Far",
              "the ground under the far town from the town rectangle's edge (0.3 m under it) out under the first ridge "
              "ring's foot (M_DKX_FarGround); no collision (token UCX)", pivot=(CX, CY, 0.0))
    n = 160
    # round 5 fix f1: out to FAR_R + 40 (under the first ridge ring's front foot), covered by the far town; it no
    # longer reaches the horizon as a plain (the judges' 'flat lavender plane with a hard straight edge')
    radii = [None, 60.0, 200.0, FAR_R + 40.0]
    verts, faces = [], []
    for k in range(n):
        th = 2 * math.pi * k / n
        ex, ey = rect_edge_point(th)
        r0 = math.hypot(ex - CX, ey - CY)
        z0 = edge_z(ex, ey) - 0.3
        for j, R in enumerate(radii):
            if R is None:
                verts.append(Vector((ex, ey, z0)))
            else:
                rr = max(R if j == len(radii) - 1 else R + r0, r0 + 5.0)
                verts.append(Vector((CX + math.cos(th) * rr, CY + math.sin(th) * rr, far_z_r(z0, rr - r0))))
    m = len(radii)
    for k in range(n):
        k1 = (k + 1) % n
        for j in range(m - 1):
            # round 5 f1: counter-clockwise from above (normals UP). The r5 winding faced down, so Unreal culled the
            # plain seen from above and showed the sky dome's horizon through it (the judges' 'flat lavender plane')
            faces.append((k * m + j, k * m + j + 1, k1 * m + j + 1, k1 * m + j))
    p.g.add(verts, faces, FARG, None, jit=False)
    p.hull_box(CX - 0.02, CX + 0.02, CY - 0.02, CY + 0.02, -60.02, -59.98)
    p.wear = False
    p.nanite = True
    return p


# round 6: four jagged ridge rings (front foot, ridge, back radius m; ridge base and amplitude m; seed). The round-5 f1
# rings were smooth sine sums (k^-1.05 up to 48 cycles a turn) with smooth-shaded crests: their crest normals pointed
# straight UP, i.e. at 90 deg to every view from the town, and the emissive master's default specular (0.5) turned that
# grazing angle into a bright Fresnel rim along every crest: the judges' 'outline strokes'. Round 6 builds ridged
# fractal silhouettes (crisp cusped peaks, detail down to 0.5 deg) and writes CUSTOM NORMALS that all face the compound
# (horizontal, toward its centre, tilted 12 deg up), so every view from the town meets them head-on (N.V about 0.98):
# no grazing angle anywhere, no rim, and the flat emissive colour reads as one even silhouette per range.
RIDGE_RINGS = [(450.0, 560.0, 650.0, 14.0, 32.0, 131), (800.0, 980.0, 1120.0, 28.0, 60.0, 31),
               (1300.0, 1520.0, 1700.0, 50.0, 100.0, 57), (1850.0, 2080.0, 2250.0, 85.0, 140.0, 77)]
RIDGE_N = 1440                 # samples a turn: 0.25 deg (4.4 m on ring 1, 9.1 m on ring 4)
NORMAL_TILT = 0.21             # tan(12 deg): the custom normals' upward tilt


def ridge_heights(n, seed, base, amp):
    """A periodic ridged-fractal ridgeline: a broad massing (2-7 cycles a turn) plus ridged octaves 1 - |S| (S = a sum
    of three random-phase sines per octave, normalised) from 9 to 288 cycles a turn at gain 0.55, then shaped (^1.35)
    so peaks are sharp and valleys broad. Returns n heights in [base, base + amp]."""
    rng = random.Random(seed)
    th = [2 * math.pi * i / n for i in range(n)]
    mass = [0.0] * n
    for k in range(2, 8):
        ph, a = rng.uniform(0, 2 * math.pi), k ** -1.2 * rng.uniform(0.6, 1.2)
        for i in range(n):
            mass[i] += a * math.sin(k * th[i] + ph)
    ridged = [0.0] * n
    f, gain, norm = 9, 1.0, 0.0
    while f <= 288:
        comps = [(f + rng.randint(-1, 1) * max(1, f // 8), rng.uniform(0, 2 * math.pi)) for _ in range(3)]
        for i in range(n):
            s_ = sum(math.sin(k * th[i] + ph) for k, ph in comps) / 3.0
            ridged[i] += gain * (1.0 - min(1.0, abs(s_) * 1.6)) ** 2
        norm += gain
        f *= 2
        gain *= 0.55
    lo_m, hi_m = min(mass), max(mass)
    hs = [0.55 * (mass[i] - lo_m) / (hi_m - lo_m) + 0.45 * ridged[i] / norm for i in range(n)]
    lo, hi = min(hs), max(hs)
    return [base + amp * ((h - lo) / (hi - lo)) ** 1.35 for h in hs]


def mountains(name, r_front, r_ridge, r_back, base, amp, seed, mat, note):
    p = Piece(name, "nocollision", "Outside/Far", note, pivot=(CX, CY, 0.0))
    n = RIDGE_N
    hs = ridge_heights(n, seed, base, amp)
    verts, faces = [], []
    # front foot (-14, under the far ground), a shoulder at 0.55 of the run (0.40 h), the ridge, the back fall to the
    # next ring's front foot (so no view from above looks through a gap onto the dome's horizon)
    rows = [(0.0, lambda h: -14.0), (0.55, lambda h: 0.40 * h), (1.0, lambda h: h), (None, lambda h: -14.0)]
    for i in range(n):
        th = 2 * math.pi * i / n
        h = hs[i]
        for (t, zf) in rows:
            R = r_back if t is None else r_front + (r_ridge - r_front) * t
            verts.append(Vector((CX + math.cos(th) * R, CY + math.sin(th) * R, zf(h))))
    m = len(rows)
    for i in range(n):
        i1 = (i + 1) % n
        for j in range(m - 1):
            faces.append((i * m + j, i * m + j + 1, i1 * m + j + 1, i1 * m + j))     # normals up / toward the town
    p.g.add(verts, faces, mat, None, jit=False, smooth=set(range(len(faces))))
    p.hull_box(CX - 0.02, CX + 0.02, CY - 0.02, CY + 0.02, -60.02, -59.98)
    p.wear = False
    p.nanite = True
    p.custom_normals = "toward_centre"
    # measured crispness: the steepest silhouette slope and the peak count (local maxima 20 % over their neighbours)
    dth = 2 * math.pi / n
    grad = max(abs(hs[(i + 1) % n] - hs[i]) / (r_ridge * dth) for i in range(n))
    peaks = sum(1 for i in range(n) if hs[i] > hs[i - 1] and hs[i] >= hs[(i + 1) % n]
                and hs[i] - min(hs[(i + k) % n] for k in range(-8, 9)) > 0.2 * amp)
    p.extra = {"radius_m": [r_front, r_ridge, r_back], "ridge_m": [round(min(hs), 1), round(max(hs), 1)],
               "elevation_deg_from_centre": [round(math.degrees(math.atan2(min(hs), r_ridge)), 2),
                                             round(math.degrees(math.atan2(max(hs), r_ridge)), 2)],
               "samples": n, "max_silhouette_slope": round(grad, 2), "sharp_peaks": peaks,
               "normals": "custom, toward the compound centre, tilted 12 deg up (no crest rim)"}
    return p


def set_custom_normals(obj, pivot_world):
    """Round 6: the ridge rings' custom normals: horizontal toward the compound centre, NORMAL_TILT up. The mesh is
    triangulated FIRST: the FBX exporter's own triangulation re-encodes custom normals against the new corner spaces and
    bent them by up to 25 deg (measured on the re-imported r6 first export); an all-triangle mesh passes through as is."""
    import bmesh
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="FIXED", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    nr = []
    for v in me.vertices:
        d = Vector((-(v.co.x + pivot_world[0] - CX), -(v.co.y + pivot_world[1] - CY), 0.0))
        d.normalize()
        d.z = NORMAL_TILT
        nr.append(d.normalized())
    me.normals_split_custom_set_from_vertices(nr)
    got = [me.corner_normals[i].vector for i in range(0, len(me.loops), max(1, len(me.loops) // 200))]
    return round(min(g_.z for g_ in got), 4), round(max(g_.z for g_ in got), 4)


# ------------------------------------------------------------------------------------------------ modern kit re-placement
def modern_instances():
    """The modern kit's street pieces re-placed along the road (its layout rows are read, never written): poles on the
    terrace-edge strip every 25 m from X -65.5 to 109.5 (the kit's spacing, extended to the town rectangle), their
    conductor / telecom spans shifted with them, the transformer on the X 9.5 pole, end guys, the gatehouse service
    drop re-aimed from the moved rack, street lamps B (west) and A (east) at the ends of the paved landing."""
    L = json.loads((OX.SHOWCASE_LAYOUT).read_text(encoding="utf-8"))
    if any(r.get("kit") == "outside" for r in L["instances"]):
        # round 5 fix f1: the showcase layout now carries THIS track's moved rows (Y -8.55); the modern kit's own rows
        # (Y -7.0, what the offsets below are measured from) are in the pre-round-5 showcase layout the round-5 stage
        # backed up (unreal/round5/start_backup), read-only
        L = json.loads((OX.WORK / "unreal" / "round5" / "start_backup" / "showcase_json" /
                        "layout_showcase.json").read_text(encoding="utf-8"))
    rows = [(i, r) for i, r in enumerate(L["instances"]) if r["piece"] in MODERN_STREET]
    old_y = -7.0
    dy = POLE_Y - old_y
    span_rows = {}
    drop = None
    for i, r in rows:
        if r["piece"] in ("SM_DKP_Modern_Wire_Span25", "SM_DKP_Modern_Wire_Telecom25"):
            note = r.get("note", "")
            x0 = float(note.split("pole X ")[1].split(" ->")[0])
            lab = note.split(",")[0]
            # round 5 fix f1 (whole judge delta 9: the wires clutter the skyline over the gate): the power line keeps
            # its upper crossarm (conductors A-D); the lower arm's E-H are dropped
            if x0 == -15.5 and not any(lab.endswith(f"Wire_{c}") for c in "EFGH"):
                span_rows.setdefault(r["piece"], []).append((r["loc"][0] - x0, r["loc"][1] - old_y, r["loc"][2], lab))
        if r["piece"] == "SM_DKP_Modern_Wire_Drop12":
            drop = r
    out = []

    def add(piece, loc, rot, note, scale=None):
        d = {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": round(rot, 4), "rot_xyz_deg": [0.0, 0.0, round(rot, 4)],
             "folder": "Props/Modern", "kit": "modern", "note": note}
        d["scale"] = [round(v, 5) for v in (scale or (1.0, 1.0, 1.0))]
        d["collision_class"] = "nocollision" if "Wire" in piece else "thin"
        out.append(d)
    for x in POLES_X:
        add("SM_DKP_Modern_UtilityPole", (x, POLE_Y, 0.0), 90.0,
            "round 5 outside: on the terrace-edge strip (Y -8.55), 25 m spans, crossarms across the line")
    add("SM_DKP_Modern_PoleTransformer", (9.5, POLE_Y, 0.0), 90.0, "round 5 outside: on the X 9.5 pole (feeds the drop)")
    add("SM_DKP_Modern_PoleGuy", (POLES_X[0], POLE_Y, 0.0), 90.0, "round 5 outside: west end pole, guy aimed west")
    add("SM_DKP_Modern_PoleGuy", (POLES_X[-1], POLE_Y, 0.0), -90.0, "round 5 outside: east end pole, guy aimed east")
    for a, b in zip(POLES_X, POLES_X[1:]):
        for piece, offs in sorted(span_rows.items()):
            for (ox_, oy_, oz_, lab) in offs:
                add(piece, (a + ox_, POLE_Y + oy_, oz_), 0.0, f"round 5 outside: {lab}, pole X {a} -> {b}")
    if drop is not None:
        p0 = Vector(drop["loc"]) + Vector((0.0, dy, 0.0))
        yaw0 = math.radians(drop["rot_z"])
        sx0, sz0 = drop["scale"][0], drop["scale"][2]
        p1 = Vector(drop["loc"]) + Vector((math.cos(yaw0) * 12.0 * sx0, math.sin(yaw0) * 12.0 * sx0, -3.0 * sz0))
        d = p1 - p0
        horiz = math.hypot(d.x, d.y)
        add("SM_DKP_Modern_Wire_Drop12", tuple(p0), math.degrees(math.atan2(d.y, d.x)),
            "round 5 outside: service drop from the X 9.5 pole's moved rack to the gatehouse west side (same end point "
            f"({p1.x:.2f}, {p1.y:.2f}, {p1.z:.2f}))", scale=(horiz / 12.0, 1.0, d.z / -3.0))
    add("SM_DKP_Modern_StreetLamp_B", LAMP_B, 0.0,
        "round 5 outside: street lamp B at the landing's west end on the terrace-edge strip, lantern toward the gate "
        "axis (dojo1_reference1's left lamp)")
    add("SM_DKP_Modern_StreetLamp_A", LAMP_A, 0.0,
        "round 5 outside: street lamp A at the landing's east end, lantern toward the gate axis (reference 1's right lamp)")
    replaced_rows = [i for i, _ in rows]
    return out, replaced_rows


# ------------------------------------------------------------------------------------------------ instances
def module_run(piece, L, x_start, direction, x_end, y, z, rot_pos=0.0, rot_neg=180.0, leftover=None):
    """Modules of length L from x_start toward x_end (direction +1 / -1); rot_neg turns a module to run -X from its
    pivot. leftover: (piece, L2) to fill the rest when it is >= L2."""
    out = []
    x = x_start
    while (x_end - x) * direction >= L - 1e-6:
        out.append((piece, (x, y, z), rot_pos if direction > 0 else rot_neg))
        x += direction * L
    if leftover and (x_end - x) * direction >= leftover[1] - 1e-6:
        out.append((leftover[0], (x, y, z), rot_pos if direction > 0 else rot_neg))
    return out


def instances(house_list):
    I = []
    I += [("SM_DKX_Road_W", ((XW + STEP_X[0]) / 2, (ROAD_Y[0] + ROAD_Y[1]) / 2, 0.0), 0.0),
          ("SM_DKX_Road_Gate", ((STEP_X[0] + STEP_X[1]) / 2, (GATE_ROAD_Y0 + ROAD_Y[1]) / 2, 0.0), 0.0),
          ("SM_DKX_Road_E", ((STEP_X[1] + XE) / 2, (ROAD_Y[0] + ROAD_Y[1]) / 2, 0.0), 0.0),
          ("SM_DKX_Verge_W", ((XW + CX) / 2, sum(VERGE_Y) / 2, 0.0), 0.0),
          ("SM_DKX_Verge_E", ((CX + XE) / 2, sum(VERGE_Y) / 2, 0.0), 0.0),
          ("SM_DKX_FarVerge_W", ((XW + LANDING_X[0]) / 2, sum(FARV_Y) / 2, 0.0), 0.0),
          ("SM_DKX_FarVerge_E", ((LANDING_X[1] + XE) / 2, sum(FARV_Y) / 2, 0.0), 0.0),
          ("SM_DKX_Landing", (sum(LANDING_X) / 2, (KERB_F[0] + COPE_Y[0]) / 2, 0.0), 0.0),
          ("SM_DKX_Water", (CX, (TER_BOT_Y + 0.07 + BANK_Y - 0.03) / 2, WATER_Z), 0.0),
          ("SM_DKX_Ground_South", (CX, (LOWLANE_Y[0] + YS) / 2, LOWER_Z), 0.0),
          ("SM_DKX_Ground_W", ((XW - 0.96) / 2, (VERGE_Y[0] + YN) / 2, 0.0), 0.0),
          ("SM_DKX_Ground_E", ((44.96 + XE) / 2, (VERGE_Y[0] + YN) / 2, 0.0), 0.0),
          ("SM_DKX_Ground_N", (22.0, (36.96 + YN) / 2, 0.0), 0.0),
          ("SM_DKX_AlleyFence_W", (ALLEY["W"][0], ALLEY["W"][1], 0.0), 0.0),
          ("SM_DKX_AlleyFence_E", (ALLEY["E"][0], ALLEY["E"][1], 0.0), 0.0),
          ("SM_DKX_PocketFence_W", (POCKET_FENCE["W"]["x_face"], PF_Y[0], 0.0), 90.0),
          ("SM_DKX_PocketFence_E", (POCKET_FENCE["E"]["x_face"], PF_Y[0], 0.0), 90.0),
          ("SM_DKX_FarGround", (CX, CY, 0.0), 0.0), ("SM_DKX_FarTown", (CX, CY, 0.0), 0.0)] + \
        [(f"SM_DKX_Ridge{k + 1}", (CX, CY, 0.0), 0.0) for k in range(len(RIDGE_RINGS))] +         [(p.name, tuple(p.pivot), 0.0) for p in onev1_pieces()]
    ky_n, kz_n = sum(KERB_N[:2]) / 2, KERB_N[2]
    ky_f, kz_f = sum(KERB_F[:2]) / 2, KERB_F[2]
    gy = sum(GUT_Y) / 2
    # the near kerb runs on under the apron's front edge (it carries the apron's front slabs, which sit 7 cm above it)
    I += module_run("SM_DKX_Kerb_8m", 8.0, XW, 1, XE, ky_n, kz_n, leftover=("SM_DKX_Kerb_4m", 4.0))
    I += module_run("SM_DKX_Kerb_8m", 8.0, LANDING_X[0], -1, XW, ky_f, kz_f, leftover=("SM_DKX_Kerb_4m", 4.0))
    I += module_run("SM_DKX_Kerb_8m", 8.0, LANDING_X[1], 1, XE, ky_f, kz_f, leftover=("SM_DKX_Kerb_4m", 4.0))
    # the gutter runs start 0.10 m under the apron's front step (their end stones tuck under it)
    I += module_run("SM_DKX_Gutter_8m", 8.0, STEP_X[0] + 0.10, -1, XW, gy, GUT_LIP, leftover=("SM_DKX_Gutter_4m", 4.0))
    I += module_run("SM_DKX_Gutter_8m", 8.0, STEP_X[1] - 0.10, 1, XE, gy, GUT_LIP, leftover=("SM_DKX_Gutter_4m", 4.0))
    I += module_run("SM_DKX_RailFence_4m", 4.0, LANDING_X[0], -1, XW, FENCE_Y, 0.0)
    I += module_run("SM_DKX_RailFence_4m", 4.0, LANDING_X[1], 1, XE, FENCE_Y, 0.0)
    x = XW
    while x < XE - 1e-6:
        I.append(("SM_DKX_Terrace_8m", (x, COPE_Y[0], 0.0), 0.0))
        I.append(("SM_DKX_Canal_8m", (x, COPE_Y[0], 0.0), 0.0))
        x += 8.0
    k = 0
    x = XW
    while x < XE - 4.0 + 1e-6:
        if k % 6 != 5:
            I.append(("SM_DKX_BoardFence_4m", (x, BFENCE_Y, LOWER_Z), 0.0))
        x += 4.0
        k += 1
    for (pc, hx, hy, rot, hsc) in house_list:
        h = HOUSES[pc]
        W, D = h["W"] * hsc[0], h["D"]
        zs = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                a = math.radians(rot)
                lx, ly = sx * W / 2, sy * D / 2
                wx, wy = hx + lx * math.cos(a) - ly * math.sin(a), hy + lx * math.sin(a) + ly * math.cos(a)
                zs.append(south_z(wx, wy) if wy < LOWLANE_Y[0] else ground_z(wx, wy))
        I.append((pc, (hx, hy, round(min(zs), 3)), rot, "", hsc))
    return I


TREE_SLOTS = [
    # (x, y, z, canopy_m, note) - NOT built this round (vegetation later); grey-box trunks stay only inside
    (-4.5, 5.0, 0.0, 6.0, "west band outside the wall (reference 1: trees along the west wall)"),
    (-6.0, 13.0, 0.0, 6.5, "west band"), (-4.5, 21.0, 0.0, 6.0, "west band"), (-6.0, 32.0, 0.0, 6.5, "west band"),
    (-5.0, 39.5, 0.0, 6.0, "west band, NW corner"),
    (48.5, 5.0, 0.0, 6.0, "east band outside the wall (reference 1: trees along the east wall)"),
    (50.0, 13.0, 0.0, 6.5, "east band"), (48.5, 21.0, 0.0, 6.0, "east band"), (50.0, 32.0, 0.0, 6.5, "east band"),
    (49.0, 39.5, 0.0, 6.0, "east band, NE corner"),
    (4.0, 39.3, 0.0, 6.0, "north band behind the storehouse (reference 2: trees beyond the north wall)"),
    (14.0, 39.5, 0.0, 6.5, "north band"), (29.0, 39.5, 0.0, 6.5, "north band"), (40.0, 39.3, 0.0, 6.0, "north band"),
    (16.9, -1.75, 0.0, 1.4, "shrub bed west of the gate apron on the verge (reference 1: shrubs flanking the gate)"),
    (27.1, -1.75, 0.0, 1.4, "shrub bed east of the gate apron"),
    (4.0, -14.0, LOWER_Z, 5.0, "lower lane, beyond the terrace (reference 1: trees below the terrace)"),
    (11.5, -14.5, LOWER_Z, 5.5, "lower lane"), (33.0, -14.5, LOWER_Z, 5.5, "lower lane"),
    (41.0, -14.0, LOWER_Z, 5.0, "lower lane"),
    (3.5, 16.0, 0.0, 6.4, "COURTYARD tree W (spec 4.3; the grey-box SM_DGB_Tree stays until then, not this track's)"),
    (40.5, 16.0, 0.0, 6.4, "COURTYARD tree E (spec 4.3; grey-box stays)"),
]


# ------------------------------------------------------------------------------------------------ main
def main():
    tm = OX.timer()
    assert_owner("DojoOutside", "claude")
    sc, kit, asm = OX.new_scene()
    OX.OXW.mkdir(parents=True, exist_ok=True)
    P = [road("SM_DKX_Road_W", XW, STEP_X[0], ROAD_Y[0]), road("SM_DKX_Road_Gate", STEP_X[0], STEP_X[1], GATE_ROAD_Y0),
         road("SM_DKX_Road_E", STEP_X[1], XE, ROAD_Y[0]),
         verge("SM_DKX_Verge_W", XW, CX), verge("SM_DKX_Verge_E", CX, XE),
         far_verge("SM_DKX_FarVerge_W", XW, LANDING_X[0]), far_verge("SM_DKX_FarVerge_E", LANDING_X[1], XE),
         kerb("SM_DKX_Kerb_8m", 8.0), kerb("SM_DKX_Kerb_4m", 4.0), gutter("SM_DKX_Gutter_8m", 8.0),
         gutter("SM_DKX_Gutter_4m", 4.0), landing(), rail_fence(), terrace(), canal(), water(), ground_south(),
         board_fence(),
         ground_north("SM_DKX_Ground_W", XW, -0.96, VERGE_Y[0], YN), ground_north("SM_DKX_Ground_E", 44.96, XE, VERGE_Y[0], YN),
         ground_north("SM_DKX_Ground_N", -0.96, 44.96, 36.96, YN),
         alley_fence("W"), alley_fence("E"), pocket_fence("W"), pocket_fence("E")] + onev1_pieces()
    for n, h in HOUSES.items():
        P.append(house(n, **h))
    P += [far_ground(), far_town()] + [
        mountains(f"SM_DKX_Ridge{k + 1}", rf, rr, rb, base, amp, seed, OX.RIDGES[k],
                  f"round 5 f1 ridge ring {k + 1} of 4 ({rf / 1000:.2f}-{rb / 1000:.2f} km, ridge {base:.0f}-"
                  f"{base + amp:.0f} m): its own flat emissive colour, lighter and bluer with distance (the far ridge "
                  "near the sky colour), the height fog on top; no collision (token UCX)")
        for k, (rf, rr, rb, base, amp, seed) in enumerate(
            [(r[0], r[1], (RIDGE_RINGS[j + 1][0] + 30.0 if j + 1 < len(RIDGE_RINGS) else r[2])) + r[3:]
             for j, r in enumerate(RIDGE_RINGS)])]
    for p in P:
        p.kit = "outside"
    pieces = {p.name: p for p in P}
    for p in P:
        if p.name.startswith(("SM_DKX_Kerb", "SM_DKX_Gutter", "SM_DKX_RailFence", "SM_DKX_BoardFence",
                              "SM_DKX_Terrace", "SM_DKX_Canal", "SM_DKX_House")):
            p.local = True
    objs, stats = {}, {}
    for p in P:
        o, bad = OX.geo_to_object(p, kit)
        objs[p.name] = o
        stats[p.name] = {"tris": OX.tris_of(o), "bad_faces": bad}
        if getattr(p, "custom_normals", None):
            p.extra["custom_normal_z_range"] = set_custom_normals(o, p.pivot)
        print("BUILT", p.name, stats[p.name], flush=True)
    for p in P:
        if stats[p.name]["tris"] >= 2000:
            p.nanite = True
            objs[p.name]["nanite"] = True
    if not QUICK:
        for p in P:
            if p.wear:
                djm.bake_wear(objs[p.name])
    house_list = house_plan()
    inst = OX.link_instances([OX.place(*i) for i in instances(house_list)], pieces, objs, asm, "outside", "x")
    kit.hide_render = True
    kit.hide_viewport = True
    modern, modern_replaced_rows = modern_instances()
    waive = {n: ("texel_density",) for n in ("SM_DKX_Water", "SM_DKX_FarGround", "SM_DKX_FarTown")
             + tuple(f"SM_DKX_Ridge{k + 1}" for k in range(len(RIDGE_RINGS)))
             + tuple(p.name for p in P if p.name.startswith("SM_DKX_1v1_"))}
    LX = {
        "date": "2026-09-29", "stage": "round 6: the 1v1 rear seal (pocket fences + 1v1-only blockers) and the far "
                                    "background (impostor far town, jagged ridge rings, edge row); round 5 outside + "
                                    "background (vegetation later)",
        "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
        "material_library": "Scripts/dojo/materials (M_DJ_*) for stone, timber, plaster, tile, glass; this track's "
                            "instances (recipes below) on the showcase's existing masters: M_DJ_GroundXY_Master (road, "
                            "verge, lanes) and M_DJ_Flat_Master (water, mountains, far ground)",
        "materials": OX.RECIPES,
        "textures": OX.TEXTURES,
        "textures_reused": OX.TEXTURES_REUSED,
        "export_dir": "Exports/DojoKit/Outside",
        "ue_root": OX.UE_ROOT,
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": stats[p.name]["tris"], "slots": [m.name for m in objs[p.name].data.materials],
                            "nanite": p.nanite, "kit": "outside", "fbx": f"Exports/DojoKit/Outside/{p.name}.fbx",
                            "pivot_world": [round(v, 4) for v in p.pivot], "local_pivot": p.local,
                            **({"extra": p.extra} if p.extra else {})} for p in P},
        "instances": inst,
        "replaces_greybox": REPLACED,
        "modern_instances": modern,
        "modern_replaces": {"pieces": MODERN_STREET, "showcase_rows": modern_replaced_rows,
                            "rule": "drop EVERY showcase instance of these modern pieces and place modern_instances "
                                    "instead (the modern kit's own files and layout_modern.json are not touched; lights "
                                    "follow the lamp instances through compose_showcase.lamp_lights)"},
        "onev1_only": {
            "rule": "1v1 ONLY: the duel level places these; the battle-royale copy drops every piece listed here (the "
                    "rear alley, both pockets, the north wall top and the upper roof's rear half open; the alley and "
                    "pocket fences go, the rear wicket gate in the north wall becomes the back way in). Unreal: folder "
                    "Dojo/Boundary_1v1 (actor tag 'Dojo/Boundary_1v1'); the invisible ones are class 'boundary' "
                    "(Pawn block, Camera / Visibility ignore, hidden in game, no shadow)",
            "ue_tag": "Dojo/Boundary_1v1",
            "visible": [{"piece": n, "closes": c} for n, c in (
                ("SM_DKX_AlleyFence_W", "the veranda's rear end, west (round 5, the grey-box hull)"),
                ("SM_DKX_AlleyFence_E", "the veranda's rear end, east (round 5, the grey-box hull)"),
                ("SM_DKX_PocketFence_W", "round 6: the west pocket's side from the corridor's last post to the alley "
                                         "fence (the verify_r5 gap)"),
                ("SM_DKX_PocketFence_E", "round 6: the east pocket's side, mirrored"))],
            "invisible": [{"piece": p.name, "boxes_world": p.extra["boxes_world"], "closes": p.note.split(" - ", 1)[1]}
                          for p in P if p.name.startswith("SM_DKX_1v1_")],
            "grey_box_boundary": "SM_DGB_Boundary_1v1 (the duel level's outer ring on the wall top's outer edge, the "
                                 "+20 m ceiling and the grey-box ridge rects) stays as it is; this set meets the ring at "
                                 "Y 37.0 and the ceiling at +20.0 and repeats its rear rects, so it seals on its own",
            "checks": "WorkFiles/dojo/build/round6/build/checks/alley_seal.json (ox_alley_seal.py: a flying-capsule "
                      "flood of the whole compound, 1v1 and BR, and the CONTROL paths)"},
        "tree_slots": [{"x": t[0], "y": t[1], "z": t[2], "canopy_m": t[3], "note": t[4], "status": "EMPTY - vegetation pass"}
                       for t in TREE_SLOTS],
        "houses": [{"piece": h[0], "x": round(h[1], 3), "y": round(h[2], 3), "rot_z": h[3], "scale": list(h[4])}
                   for h in house_list],
        "numbers": {
            "town_rectangle": [XW, XE, YS, YN],
            "street_y": {"verge": list(VERGE_Y), "kerb_near": list(KERB_N), "gutter": list(GUT_Y), "road": list(ROAD_Y),
                         "kerb_far": list(KERB_F), "far_verge": list(FARV_Y), "coping": list(COPE_Y),
                         "terrace_foot": [TER_BOT_Y, TER_BOT_Z], "canal_bank": [BANK_Y, BANK_TOP],
                         "water_z": WATER_Z, "lower_lane": list(LOWLANE_Y), "lower_z": LOWER_Z},
            "road_z": {"edge": ROAD_EDGE_Z, "crown": ROAD_EDGE_Z + ROAD_CROWN},
            "gate_apron_junction": {"kit1_apron_x": list(APRON_X), "kit1_front_step_x": list(STEP_X),
                                    "kit1_front_step": "Y -2.50..-3.00 top +0.05; the road meets its face at Y -3.00 "
                                                       "(a 0.14 m step), the kerb and verge butt the apron's sides at X "
                                                       "18.10 / 25.90, the gutter runs in front of the apron's corners "
                                                       "and ends at the step's ends (X 18.80 / 25.20)"},
            "landing": {"x": list(LANDING_X), "lamps": {"B": list(LAMP_B), "A": list(LAMP_A)}},
            "poles": {"x": POLES_X, "y": POLE_Y, "spans_m": 25.0},
            "lanes": {"west_x": list(LANES_X["W"]), "east_x": list(LANES_X["E"]), "north_y": list(LANE_N_Y)},
            "alley_fences": {k: {"pivot": [v[0], v[1], 0.0], "hull": [v[0], v[0] + ALLEY_BOX[0], v[1], v[1] + ALLEY_BOX[1],
                                                                     0.0, ALLEY_BOX[2]]} for k, v in ALLEY.items()},
            "mountains": "a far MESH ring (not an Unreal landscape): the showcase pipeline imports FBX static meshes in "
                         "one commandlet step with every other piece (dj_sc_import) and places them from this layout "
                         "(dj_sc_level); a Landscape needs a heightmap import through the editor's landscape tools, "
                         "which no step of the commandlet pipeline has and which is not verifiable in the same fresh "
                         "process as the meshes. The rings sit inside the 2.4 km cloud dome (look_r3.ENV sky_dome) and "
                         "take the level's ExponentialHeightFog as their haze",
        },
    }
    (OX.OXW / "layout_outside.json").write_text(json.dumps(LX, indent=1), encoding="utf-8")
    qa, exp = OX.qa_and_export(P, objs, kit, EXPORT_DIR, OX.OXW, quick=QUICK, no_export="--no-export" in ARGS,
                               extra_waive=waive)
    if "--no-context" not in ARGS:
        extra_walk = {
            "BR_approach_road_along_the_crown": (road_z(-5.3), [(-30.0, -5.3), (70.0, -5.3)], True),
            "BR_road_onto_the_gate_apron": (road_z(-6.0), [(22.0, -6.0), (22.0, -2.2)], True),
            "BR_verge_along_the_south_wall_foot_west": (0.0, [(-30.0, -1.62), (15.5, -1.62)], True),
            "BR_road_up_the_kerb_into_the_west_lane_north": (road_z(-5.3), [(-10.5, -5.3), (-10.5, -1.6), (-10.5, 40.0),
                                                                             (-10.5, 43.0), (20.0, 43.0)], True),
            "BR_lower_lane": (LOWER_Z, [(-60.0, -14.2), (100.0, -14.2)], True),
            "BR_outside_west_band_along_the_wall": (0.0, [(-2.0, 0.0), (-2.0, 36.0)], True),
            "CONTROL_alley_fence_W_from_the_veranda": (0.5, [(12.1, 33.2), (12.1, 35.2)], False),
            "CONTROL_alley_fence_E_from_the_veranda": (0.5, [(31.9, 33.2), (31.9, 35.2)], False),
            "CONTROL_alley_fence_W_ground": (0.0, [(10.75, 33.95 - 0.35), (10.75, 35.2)], False),
            "CONTROL_alley_fence_E_ground": (0.0, [(33.25, 33.95 - 0.35), (33.25, 35.2)], False),
        }
        # round 6: CONTROLs into the pockets and the strip from every side at ground / deck / fence-top level (the
        # roof-level ones need sloped hulls: ox_alley_seal.py runs them with a capsule on the real UCX)
        for sd, sx in (("W", 1.0), ("E", -1.0)):
            X = (lambda x: x) if sx > 0 else (lambda x: round(44.0 - x, 4))
            extra_walk.update({
                f"CONTROL_alley_pocket_{sd}_corridor_end_deck_north": (0.5, [(X(10.45), 31.0), (X(10.45), 33.5),
                                                                            (X(9.0), 33.5)], False),
                f"CONTROL_alley_pocket_{sd}_corridor_floor_to_the_end_then_north": (0.5, [(X(8.0), 31.0),
                                                                                         (X(10.70), 31.0),
                                                                                         (X(10.70), 33.6)], False),
                f"CONTROL_alley_pocket_{sd}_off_the_veranda_west_edge" if sd == "W" else
                f"CONTROL_alley_pocket_{sd}_off_the_veranda_east_edge": (0.5, [(X(11.6), 33.0), (X(9.0), 33.0)],
                                                                         False),
            })
        # (a side-yard route up onto the end deck and a west-wall-top route were tried and dropped: the deck's 0.5 m
        # edge and the wall's step pier stop them before the seal, so they proved nothing; ox_alley_seal.py covers both)
        # outside stances 0.45 m off the wall face: the capsule (r 0.30) stays clear of the duel level's 1v1 ring (Y -1.1..-1.0),
        # which the BR copy does not have
        vz = -0.01 * (VERGE_Y[0] - (-1.45)) / (VERGE_Y[0] - VERGE_Y[1])
        extra_climb = [
            {"route": "O", "step": "OUTSIDE (BR): verge -> south wall top", "stance": [10.0, -1.45],
             "floor_z": round(vz, 4), "face": [0, 1], "marker": "Wall_S_W1"},
            {"route": "O", "step": "OUTSIDE (BR): verge -> south wall top east", "stance": [36.0, -1.45],
             "floor_z": round(vz, 4), "face": [0, 1], "marker": "Wall_S_E2"},
            {"route": "O", "step": "OUTSIDE (BR): west ground -> west wall top", "stance": [-1.45, 10.0],
             "floor_z": round(ground_z(-1.45, 10.0), 4), "face": [1, 0], "marker": "Wall_W_S"},
            {"route": "O", "step": "OUTSIDE (BR): east ground -> east wall top", "stance": [45.45, 10.0],
             "floor_z": round(ground_z(45.45, 10.0), 4), "face": [-1, 0], "marker": "Wall_E_S"},
            {"route": "O", "step": "OUTSIDE (BR): north ground -> north wall top", "stance": [22.0, 37.45],
             "floor_z": round(ground_z(22.0, 37.45), 4), "face": [0, -1], "marker": "Wall_N"},
        ]
        OX.compose_checks(kit, asm, REPLACED, LX, "outside", "SM_DKX_",
                          OX.OXW / "layout_outside_checks.json",
                          "round 5 outside checks: the showcase with SM_DKX_* in place of the grey-box outside ground and "
                          "alley fences, and the modern street pieces re-placed along the road",
                          extra_walk=extra_walk, extra_climb=extra_climb, extra_instances=modern,
                          drop_instances=MODERN_STREET)
    rep = {"pieces": {p.name: {"class": p.cls, "tris": stats[p.name]["tris"], "nanite": p.nanite, "ucx": len(p.hulls),
                               "bad_faces": stats[p.name]["bad_faces"]} for p in P},
           "tris_unique": sum(stats[p.name]["tris"] for p in P),
           "tris_placed": sum(stats[i["piece"]]["tris"] for i in inst), "instances": len(inst),
           "houses": len(house_list), "modern_instances": len(modern),
           "qa_hard_fails": sum(len(v["hard_fails"]) for v in qa.values()) if qa else None,
           "exported": sorted(exp), "seconds": tm(), "quick": QUICK}
    (OX.OXW / "outside_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    OX.save_blend(BLEND)
    print("DONE outside", rep["instances"], "instances", rep["tris_unique"], "unique tris", rep["seconds"], "s",
          flush=True)


if __name__ == "__main__":
    main()
