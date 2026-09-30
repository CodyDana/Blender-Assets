"""KIT 1: perimeter wall + main gatehouse for the dojo courtyard arena, built on the grey-box layout.

Specs: WorkFiles/world/DOJO_ARENA_SPEC.md (heights, climbs, collision classes), WorkFiles/world/STYLE_GUIDE.md (palette,
texel density, IP). Look: References/Dojo/dojo_wall_ref.png and dojo_gatehouse_ref.png (AI-generated modelling reference,
REFERENCE_LOG.md). Decisions and deviations: WorkFiles/dojo/build/BUILD_NOTES.md, sections "KIT 1" and "KIT 1 fix f1".

WALL KIT (modular, every module's pivot on the INNER face at its own base; the wall runs along local +X, the inner face
is local y = 0, the thickness goes to local -Y; the cross-section is symmetric, so a module turned 180 deg fits too):
  SM_DK_WallFooting_{1,2,4}m      0.65 m granite footing (about a third of the wall, as the sheet): a row of squared
                                  capstones over three courses of rough polygonal field stone, moss in the joints (R)
  SM_DK_WallFooting_End / _Corner the same, wrapping the exposed end / corner in quoins
  SM_DK_WallBody_{1,2,4}m_T{200,250,300}   earthen plaster from +0.65 to the cap (tops 2.0 / 2.5 / 3.0 m); grime in
                                  vertex colour G; plaster is mapped in world space (height-independent)
  SM_DK_WallCap_{1,2,4}m          kawara cap (the shared tile system), 8 deg, widened for the 1.0 m wall; the collision
                                  is ONE flat box whose top is the wall top; the ridge roll stands 6.5 cm above it so
                                  every tile at the wall faces stays within 0.15 m of the walk plane (spec 4.1, f1)
  SM_DK_WallCap_End               1 m cap with the gabled end (tie beam, bargeboards, verge rolls, ridge-end discs)
  SM_DK_WallCap_Corner            1 x 1 m corner cap: mitred ridge + round finial, hip roll outside, valley roll inside
  SM_DK_Wall_StepPier             1 m stepped wall section, flat walkable top +3.25 (route 2 landing), gabled both ends
  SM_DK_Wall_GateReturn_W / _E    f1: beside the gatehouse the wall turns north (a corner module) and returns 2 m at
                                  +2.0 to a 1 x 1 m stepped block at the courtyard eave corner (flat top +3.25, route 6
                                  landing); a stepped join (+3.0) under the verge closes the wall line to the wall post
  SM_DK_Wall_FramePier            f1: the wall sheet's freestanding timber-framed pier (slab plinth, stone base, posts
                                  and beams, exposed earthen panels, gabled cap); a terminal for the BR wall openings
GATEHOUSE (pivot at the gate centre on the inner wall face, world (22, 0, 0)):
  SM_DK_Gate_Frame (door posts, wall posts, front + rear corner posts on plinth blocks, bracket clusters, layered eave
  beams, tie beams, gables, lintel, plank side panels), SM_DK_Gate_Roof (plain gable / kirizuma 8 x 5 m, eave +3.25,
  slope planes meeting at +4.416, verge bargeboards, verge rolls, plain round stacked ridge-end tiles),
  SM_DK_Gate_Leaf_L / _R (pivot on the hinge axis), SM_DK_Gate_Lamp (x4), SM_DK_Gate_Paving

ROUND 2 (2026-09-28, BUILD_NOTES "KIT 1 round 2"): the route-6 eave stands are removed (nothing stands outside the
gate roof; route 6 cannot be built inside it: route6_study); the footing is hewn polygonal rubble modelled on the
library GraniteRubble texture's own stone cells under a hewn capstone course, with flush quoins at ends and corners;
every material comes from the shared dojo material library (Scripts/dojo/materials) with its 'Wear' weathering; the
gate paving's courtyard apron stops at Y 2.0 (the sand field's edge).

Run: blender -b --factory-startup --python Scripts/dojo/build_kit1.py -- [--no-export] [--no-lods]
Out: Assets/Dojo/DojoKit1.blend, Exports/DojoKit/Kit1/SM_DK_*.fbx, WorkFiles/dojo/build/layout.json (kit 1 in place of
the grey-box wall and gate), WorkFiles/dojo/build/kit1/{qa_report,export_report,kit1_report}.json
Re-running build_dojo_greybox.py overwrites layout.json: re-run this script after it.
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import kit1_geo as G  # noqa: E402
from kit1_geo import Geo, Slope  # noqa: E402

WORK = ROOT / "WorkFiles" / "dojo" / "build"
K1 = WORK / "kit1"
TEX = ROOT / "Exports" / "DojoKit" / "Kit1" / "Textures"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Kit1"
GREY_BLEND = ROOT / "Assets" / "Dojo" / "DojoGreybox.blend"
BLEND = ROOT / "Assets" / "Dojo" / "DojoKit1.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ------------------------------------------------------------------------------------------------ numbers
WALL_T = 1.0
FOOT_H = 0.60                    # f2: 0.65 -> 0.60 (the sheet's footing is about 0.53 of a 1.9 m wall)
CAPSTONE_H = 0.19                # the squared block course on top of the footing
PROUD = 0.015                    # f2: rubble rims stand 1.5 cm proud of the plaster plane, their cushions 4-6 cm
CAP_OVER = 0.20                  # cap eave beyond the wall face (sheet: about 0.15-0.2)
CAP_TH = math.radians(21.0)      # f2: 8 -> 21 deg (the judge: the cap read as a thin strip; the sheet's is 30-35);
                                 # 21 deg is the steepest that keeps every tile within 0.15 m of the flat walk plane
CAP_BASE = 0.04                  # tile base plane above the body top at the eave line
CAP_COURSES = 4                  # f2: four courses per slope (the sheet shows 4-5 in the front view)
RIDGE_HW = 0.15                  # tile field stops this far from the ridge line (under the noshi)
NOSHI_BED = 0.030                # ridge bed above the tile base at the ridge
NOSHI_N = 3                      # f2: three noshi layers (was two)
NOSHI_H = 0.035                  # f2: 30 -> 35 mm
NOSHI_W = [0.36, 0.32, 0.28]
KAN_GAP = 0.012                  # noshi top -> ridge roll axis
KAN_R = 0.052                    # ridge roll radius
CAP_SINK = 0.075                 # the ridge roll's top stands this far above the flat walk plane (the wall top)
TOPS = {"T200": 2.0, "T250": 2.5, "T300": 3.0}
ONI_W_W, ONI_W_H, ONI_W_T = 0.36, 0.44, 0.14   # f2: the wall cap's stacked ridge-end tile (width, height, depth)
GATE_EAVE, GATE_RIDGE = 3.25, 4.4
PITCH = math.radians(25.0)
PIER_TOP = 3.25
GC = Vector((22.0, 0.0, 0.0))    # gatehouse pivot (world)

# r2: every kit-1 material comes from the SHARED DOJO MATERIAL LIBRARY (Scripts/dojo/materials, v1.0.0; textures
# Exports/DojoKit/Materials/Textures/T_DJ_*): the gate's aged timber (side + end grain), granite (cut stone), granite
# rubble (the footing's field stones, modelled on the texture's own stone cells), iron, earthen plaster, roof tile and
# the amber lamp glass. Weathering = the library's 'Wear' corner colour (bake_wear: R grime, G edge, B ground dirt).
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402
import dojo_tex_gen as djt  # noqa: E402

T_, TE, IR, GR, RB, TL, EP, LG = ("M_DJ_TimberAged", "M_DJ_TimberAgedEnd", "M_DJ_Iron", "M_DJ_Granite",
                                  "M_DJ_GraniteRubble", "M_DJ_RoofTile", "M_DJ_PlasterEarth", "M_DJ_GlassAmber")
MO = TL                          # r2: ridge / cap beds under the tiles take the tile material (no cream line)
UL = TL                          # r2: the underlay under the gate tiles takes the tile material (never seen)
EC = "M_DK_EarthCore"            # the frame pier's exposed straw-earth panel: NOT in the library (kit-1 set kept, flagged)
LIB = {T_: "TimberAged", TE: "TimberAgedEnd", IR: "Iron", GR: "Granite", RB: "GraniteRubble", TL: "RoofTile",
       EP: "PlasterEarth", LG: "GlassAmber"}
# kept only for EC (the old kit-1 builder): name: (texture set, tile m, params)
MATERIALS = {EC: ("EarthCore", 4.0, {"world": True, "grime": 0.45})}


def tile_of(m):
    if m in LIB:
        tm = djt.SETS[LIB[m]]["tile_m"]
        return tm[0] if tm else 1.0
    return MATERIALS[m][1]


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5)) + (1.0,)


def clamp01(x):
    return max(0.0, min(1.0, x))


# ------------------------------------------------------------------------------------------------ vertex colour rules
def moss_rule(z_top=0.42, grime=0.0):
    def f(co):
        n = noise.noise(co * 3.1) * 0.5 + 0.5
        m = clamp01((z_top - co.z) / z_top) ** 1.3 * (0.30 + 0.70 * n)
        return (m, grime, 1.0)
    return f


def stone_moss(z_top=FOOT_H):
    """Per-vertex moss for the field stones: strongest in the joints and low down, a touch on the upper faces."""
    def f(v, joint, upf):
        nz = noise.noise(v * 3.1) * 0.5 + 0.5
        low = clamp01((z_top - v.z) / z_top) ** 1.1
        streak = clamp01((0.22 - v.z) / 0.22) * (0.5 + 0.5 * (noise.noise(Vector((v.x * 6.0, v.y * 6.0, 0.3))) * 0.5 + 0.5))
        return clamp01((0.18 + 0.82 * joint) * (0.30 + 0.70 * low) * (0.30 + 0.70 * nz) + 0.35 * upf * nz
                       + 0.55 * streak)
    return f


def grime_rule(z_lo, z_hi, top=0.50, bottom=0.35):
    """f2: mottled water staining on the plaster (G): darkest under the cap's drip line, fading down over `top`, and a
    splash band above the footing; broken up by low-frequency noise (the material adds the vertical streaks)."""
    def f(co):
        nz = noise.noise(Vector((co.x * 1.7, co.y * 1.7, co.z * 0.5))) * 0.5 + 0.5
        g = max(0.90 * clamp01(1 - (z_hi - co.z) / top) ** 0.8, 0.65 * clamp01(1 - (co.z - z_lo) / bottom))
        return (0.0, clamp01(g * (0.50 + 0.70 * nz)), 1.0)
    return f


def wood_rule(co):
    """f2 weathered timber (G): grime and splash rising from the ground (the lower 0.9 m), soft vertical streaks under
    the eaves, patchy."""
    nz = noise.noise(Vector((co.x * 2.1, co.y * 2.1, co.z * 0.6))) * 0.5 + 0.5
    streak = max(0.0, noise.noise(Vector((co.x * 9.0, co.y * 9.0, 0.37))) - 0.15) * 1.2
    low = clamp01((0.9 - co.z) / 0.9) ** 1.3
    return (0.0, clamp01(0.85 * low * (0.55 + 0.6 * nz) + 0.35 * streak * (0.4 + 0.6 * nz)), 1.0)


# ------------------------------------------------------------------------------------------------ piece container
class Piece:
    def __init__(self, name, cls, folder, note):
        self.name, self.cls, self.folder, self.note = name, cls, folder, note
        self.g = Geo()
        self.hulls = []          # point lists (piece local)
        self.nanite = False
        self.extra = {}
        self.wood_grime = False  # f2: timber faces get ground grime / weathering streaks in vertex colour G
        self.ground_z = None     # r2: bake_wear's ground level in piece space (None = the piece's lowest point)

    def hull_box(self, x0, x1, y0, y1, z0, z1):
        self.hulls.append([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
        return self

    def hull_pts(self, pts):
        self.hulls.append([tuple(p) for p in pts])
        return self


def lattice_surface(g, xs, ys, zs, mat, vc=None, frame=None):
    """The closed surface of a box subdivided at the given coordinates (welded, outward quads)."""
    grid, verts, faces = {}, [], []

    def vid(i, j, k):
        if (i, j, k) not in grid:
            grid[(i, j, k)] = len(verts)
            verts.append((xs[i], ys[j], zs[k]))
        return grid[(i, j, k)]

    nx, ny, nz = len(xs) - 1, len(ys) - 1, len(zs) - 1
    for (fixed, val, a1, n1, a2, n2, flip) in ((0, 0, 1, ny, 2, nz, True), (0, nx, 1, ny, 2, nz, False),
                                               (1, 0, 0, nx, 2, nz, False), (1, ny, 0, nx, 2, nz, True),
                                               (2, 0, 0, nx, 1, ny, True), (2, nz, 0, nx, 1, ny, False)):
        for p in range(n1):
            for q in range(n2):
                quad = []
                for (dp, dq) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    ijk = [0, 0, 0]
                    ijk[fixed] = val
                    ijk[a1] = p + dp
                    ijk[a2] = q + dq
                    quad.append(vid(*ijk))
                faces.append(tuple(reversed(quad)) if flip else tuple(quad))
    g.add(verts, faces, mat, frame, vc)
    return g


# ------------------------------------------------------------------------------------------------ footing stones (r2)
# r2 (the judge: the sheet's footing is rough-hewn, chisel-faced POLYGONAL rubble with deep irregular joints and moss,
# not rounded pillows; use the library's granite rubble): the field stones are the library GraniteRubble texture's own
# stone cells (G.rubble_cells), each modelled as a hewn stone (crisp irregular chamfer, pitched flat-shaded face, a
# little tilt) and UV-mapped so the texture's stone lands on it; 1.2-2 cm joints, 3.5-5 cm deep, down to a recessed
# rubble core. The capstone course is squared hewn blocks in the library Granite. Quoins are squared hewn blocks
# flush with both faces (no stone stands past an end face).
JOINT_HALF = (0.005, 0.009)      # per-stone half joint (so joints are 1.0-1.8 cm, irregular)
CORE_IN = 0.022                  # the rubble core's face behind the plaster plane (joints 3.5-5 cm deep)
STONE_DEPTH = 0.10               # how far each stone runs back into the core
QUOIN = 0.38                     # quoin block size along each face


def rubble_zone(g, origin, t, n, a0, a1, z0, z1, seed, rng):
    """The field stones of one face window [a0, a1] x [z0, z1] (local a along t, z up): the texture's cells at a random
    tile offset (so every face and module shows other stones), each a hewn stone."""
    u0m, v0m = rng.uniform(0.0, 4.0), rng.uniform(0.0, 4.0)

    def uv_fn(a, z, u0m=u0m, v0m=v0m):
        return ((u0m + a) / 4.0, (v0m + z) / 4.0)

    n_st = 0
    for i, (cell, _key) in enumerate(G.rubble_cells(u0m, v0m, a0, a1, z0, z1)):
        inner = G.inset_convex(G.clean_poly(cell), rng.uniform(*JOINT_HALF))
        if inner is None or abs(G.poly_area(inner)) < 0.0025:
            continue
        w_ = max(p_[0] for p_ in inner) - min(p_[0] for p_ in inner)
        h_ = max(p_[1] for p_ in inner) - min(p_[1] for p_ in inner)
        if min(w_, h_) < 0.045:
            continue
        ch = min(rng.uniform(0.014, 0.024), 0.22 * min(w_, h_))
        r = G.hewn_stone(g, inner, origin, t, n, STONE_DEPTH, PROUD + rng.uniform(-0.004, 0.010), seed * 997 + i, RB,
                         uv_fn=uv_fn, chamfer=ch, pitch=rng.uniform(0.006, 0.014), tilt=0.035, step=0.05)
        n_st += r is not None
    return n_st


def capstone_row(g, origin, t, n, a0, a1, seed, rng, gap=0.014):
    """The squared capstone course (zc0 .. FOOT_H) over [a0, a1]: hewn blocks 0.26-0.50 m long."""
    zc0 = FOOT_H - CAPSTONE_H
    t, n = Vector(t), Vector(n)
    up = Vector((0, 0, 1))
    length = a1 - a0
    widths = []
    a = 0.0
    while a < length - 1e-6:
        w = rng.uniform(0.26, 0.50)
        widths.append(w)
        a += w
    k = length / sum(widths)
    a = a0
    dep = 0.14
    for i, w in enumerate(widths):
        w *= k
        front = PROUD + 0.010 + rng.uniform(-0.003, 0.006)
        c = Vector(origin) + t * (a + w / 2) + n * (front - dep / 2) + up * ((zc0 + FOOT_H) / 2 - 0.002)
        G.hewn_box(g, c, (t, -n, up), (w / 2 - gap / 2, dep / 2, CAPSTONE_H / 2 - gap / 2),
                   rng.uniform(0.012, 0.020), seed * 131 + i, GR, exposed=("-d",), pitch=rng.uniform(0.006, 0.012))
        a += w


def stone_face(g, origin, t, n, length, seed, a_lo=0.0, a_hi=None):
    """One exposed footing face (origin at a = 0 on the face plane at z = 0, t = along, n = outward): capstones over
    [a_lo, a_hi], field stones below (from 6 cm under the ground to the capstones)."""
    rng = random.Random(seed * 7 + 3)
    a_hi = length if a_hi is None else a_hi
    zc0 = FOOT_H - CAPSTONE_H
    capstone_row(g, origin, t, n, a_lo, a_hi, seed, rng)
    rubble_zone(g, origin, t, n, a_lo, a_hi, -0.06, zc0, seed, rng)
    return g


def quoin(g, corner, n1, n2, seed, q=QUOIN, gap=0.014):
    """Corner stones: three courses (the capstone course and two below) of squared hewn blocks q x q in plan whose
    two outer faces stand PROUD + 1 cm off both face planes (flush, never past them); corner = the corner point of
    the two face planes at z = 0; n1 / n2 = the two outward normals."""
    n1, n2, up = Vector(n1).normalized(), Vector(n2).normalized(), Vector((0, 0, 1))
    rng = random.Random(seed * 13 + 1)
    zc0 = FOOT_H - CAPSTONE_H
    courses = ((zc0, FOOT_H), (zc0 / 2, zc0), (-0.06, zc0 / 2))
    for i, (z0, z1) in enumerate(courses):
        pr = PROUD + 0.010 + rng.uniform(-0.002, 0.005)
        la, lb = q - rng.uniform(0.0, 0.012), q - rng.uniform(0.0, 0.012)
        c = Vector(corner) + (-n2) * ((la - pr) / 2) + (-n1) * ((lb - pr) / 2) + up * ((z0 + z1) / 2)
        G.hewn_box(g, c, (-n2, -n1, up), ((la + pr) / 2 - gap / 2, (lb + pr) / 2 - gap / 2, (z1 - z0) / 2 - gap / 2),
                   rng.uniform(0.014, 0.022), seed * 31 + i, GR, exposed=("-a", "-d"), pitch=0.010)
    return g


def footing(x0, x1, y0, y1, faces, quoins, seed, z_top=FOOT_H):
    """faces: subset of '-y', '+y', '-x', '+x' that show stones; quoins: corners like ('-x', '-y')."""
    g = Geo()
    q = QUOIN + 0.005
    # the recessed rubble core the stones are set into (it shows only deep in the joints)
    G.box(g, x0 + (CORE_IN if "-x" in faces else 0), x1 - (CORE_IN if "+x" in faces else 0),
          y0 + (CORE_IN if "-y" in faces else 0), y1 - (CORE_IN if "+y" in faces else 0), -0.06, z_top - 0.002, RB)

    def span(lo, hi, lo_key, hi_key, other):
        a = lo + (q if (lo_key, other) in quoins or (other, lo_key) in quoins else 0.0)
        b = hi - (q if (hi_key, other) in quoins or (other, hi_key) in quoins else 0.0)
        return a, b

    if "-y" in faces:
        a, b = span(x0, x1, "-x", "+x", "-y")
        stone_face(g, (x0, y0, 0), (1, 0, 0), (0, -1, 0), x1 - x0, seed + 1, a - x0, b - x0)
    if "+y" in faces:
        a, b = span(x0, x1, "-x", "+x", "+y")
        stone_face(g, (x1, y1, 0), (-1, 0, 0), (0, 1, 0), x1 - x0, seed + 2, x1 - b, x1 - a)
    if "-x" in faces:
        a, b = span(y0, y1, "-y", "+y", "-x")
        stone_face(g, (x0, y1, 0), (0, -1, 0), (-1, 0, 0), y1 - y0, seed + 3, y1 - b, y1 - a)
    if "+x" in faces:
        a, b = span(y0, y1, "-y", "+y", "+x")
        stone_face(g, (x1, y0, 0), (0, 1, 0), (1, 0, 0), y1 - y0, seed + 4, a - y0, b - y0)
    for i, (kx, ky) in enumerate(quoins):
        cx = x0 if kx == "-x" else x1
        cy = y0 if ky == "-y" else y1
        n1 = Vector((0, -1, 0)) if ky == "-y" else Vector((0, 1, 0))
        n2 = Vector((-1, 0, 0)) if kx == "-x" else Vector((1, 0, 0))
        quoin(g, (cx, cy, 0), n1, n2, seed + 10 + i)
    return g


# ------------------------------------------------------------------------------------------------ cap
def cap_dims(thick=WALL_T, over=CAP_OVER):
    half = thick / 2 + over
    run = half - RIDGE_HW
    tn = math.tan(CAP_TH)
    base_ridge = CAP_BASE + run * tn
    noshi0 = base_ridge + NOSHI_BED
    kan_c = noshi0 + NOSHI_N * NOSHI_H + KAN_GAP
    top = kan_c + KAN_R
    return {"half": half, "run": run, "s_len": run / math.cos(CAP_TH), "base_ridge": base_ridge, "noshi0": noshi0,
            "kan_c": kan_c, "visual_top": top, "H": top - CAP_SINK, "apex": CAP_BASE + half * tn}


CD = cap_dims()
CAP_H = CD["H"]                  # the cap's collision top above its pivot (= the wall top)


def cap_geo(xa, xb, thick=WALL_T, over=CAP_OVER, gable_lo=False, gable_hi=False, ledger=True, close_hi=False):
    """A straight cap from x = xa to xb over a wall y in [-thick, 0]. gable_*: close that end with a verge (the
    geometry then runs `over` past the end)."""
    d = cap_dims(thick, over)
    g = Geo()
    yc = -thick / 2
    x0 = xa - (over if gable_lo else 0.0)
    x1 = xb + (over if gable_hi else 0.0)
    L = x1 - x0
    tn, cs = math.tan(CAP_TH), math.cos(CAP_TH)
    s_len = d["s_len"]
    C = s_len / CAP_COURSES                           # f2: four courses per slope (f1: three)
    slA = Slope((x0, yc - d["half"], CAP_BASE), (1, 0, 0), (0, cs, math.sin(CAP_TH)))
    slB = Slope((x1, yc + d["half"], CAP_BASE), (-1, 0, 0), (0, -cs, math.sin(CAP_TH)))
    phA = (xa - x0) % G.P
    phB = (x1 - xa) % G.P
    for sl, ph, (lo_g, hi_g) in ((slA, phA, (gable_lo, gable_hi)), (slB, phB, (gable_hi, gable_lo))):
        verge_u = []
        if lo_g:
            verge_u.append(0.045)
        if hi_g:
            verge_u.append(L - 0.045)
        G.tile_field(g, sl, 0.0, L, 0.0, s_len, C, TL, eave=True, phase=ph,
                     roll_margin=0.06 if (lo_g or hi_g) else 0.0)
        for uv in verge_u:
            G.roll_run(g, sl, uv, 0.0, s_len, C, TL, eave=True)
        ob_s = over / cs
        G.obox(g, sl.at(L / 2, ob_s / 2, -0.014), sl.U, sl.S, sl.N, L / 2, ob_s / 2, 0.012, T_)
    for side in (-1, 1):
        ye = yc + side * d["half"]
        G.box(g, x0, x1, min(ye, ye - side * 0.028), max(ye, ye - side * 0.028), CAP_BASE - 0.07, CAP_BASE - 0.004, T_,
              grain="x")
        if ledger:
            yf = yc + side * thick / 2
            G.box(g, xa if not gable_lo else xa - 0.02, xb if not gable_hi else xb + 0.02,
                  min(yf, yf + side * 0.022), max(yf, yf + side * 0.022), -0.055, 0.0, T_, grain="x")
    zf = CAP_BASE + over * tn
    G.prism(g, [(xb, -thick, 0.0), (xb, 0.0, 0.0), (xb, 0.0, zf), (xb, yc, d["apex"] - 0.02), (xb, -thick, zf)],
            (1, 0, 0), xb - xa, MO)
    # f1: at a plain module end the ridge bed and the noshi run to the exact end, so neighbouring modules' ridges meet
    # with no gap (the renders showed light ticks at the module joints); gable ends keep their small inset
    ia, ib = (0.01 if gable_lo else 0.0), (0.01 if gable_hi else 0.0)
    G.box(g, x0 + ia, x1 - ib, yc - 0.17, yc + 0.17, d["base_ridge"] - 0.02, d["noshi0"], MO)
    G.noshi_stack(g, (x0 + ia / 2, yc, d["noshi0"]), (x1 - ib / 2, yc, d["noshi0"]), (0, 0, 1), NOSHI_W[:NOSHI_N], NOSHI_H,
                  TL, seg=0.25, seed=int(1000 * (xb - xa)) + (7 if gable_lo else 0) + (3 if gable_hi else 0))
    kz = d["kan_c"]
    G.roll_line(g, (x0, yc, kz), (x1, yc, kz), (0, 0, 1), TL, r=KAN_R, seg=0.25,
                disc_start=0.062 if gable_lo else None, disc_end=0.062 if gable_hi else None)
    if close_hi:      # a plain tile end plate closing the section (the gate step pier's end under the verge)
        G.prism(g, [(xb, yc - d["half"], CAP_BASE - 0.07), (xb, yc + d["half"], CAP_BASE - 0.07),
                    (xb, yc + d["half"], CAP_BASE + 0.07), (xb, yc, d["visual_top"]), (xb, yc - d["half"], CAP_BASE + 0.07)],
                (1, 0, 0), 0.02, TL, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
    for (on, xe, sgn) in ((gable_lo, x0, -1), (gable_hi, x1, 1)):
        if not on:
            continue
        xin = xa if sgn < 0 else xb
        # gable board on the wall end plane
        G.prism(g, [(xin, yc - d["half"] + 0.05, CAP_BASE - 0.07), (xin, yc + d["half"] - 0.05, CAP_BASE - 0.07),
                    (xin, yc + d["half"] - 0.05, CAP_BASE), (xin, yc, d["apex"]), (xin, yc - d["half"] + 0.05, CAP_BASE)],
                (sgn, 0, 0), 0.03, EP, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
        # f1: the sheet's end frame: a small timber tie beam across the gable with square ends past both eaves
        xt0, xt1 = (xin, xin + sgn * 0.075)
        G.box(g, min(xt0, xt1), max(xt0, xt1), yc - d["half"] - 0.05, yc + d["half"] + 0.05, CAP_BASE - 0.13,
              CAP_BASE - 0.05, T_, grain="y")
        # bargeboards under the verge, standing proud of the gable (the sheet's end elevation)
        for sl in (slA, slB):
            u = 0.03 if (sl is slA) == (sgn < 0) else L - 0.03
            G.obox(g, sl.at(u, s_len / 2 - 0.01, -0.075), sl.S, sl.U, sl.N, s_len / 2 + 0.03, 0.028, 0.068, T_)
        # a short king post from the tie beam to the apex
        G.box(g, min(xin, xin + sgn * 0.06), max(xin, xin + sgn * 0.06), yc - 0.05, yc + 0.05, CAP_BASE - 0.05,
              d["apex"] - 0.06, T_, grain="z")
        # f2: the sheet's tall stacked ridge-end tile (onigawara, plain) standing on the ridge end at the verge
        G.onigawara(g, (xe - sgn * ONI_W_T / 2, yc, d["base_ridge"] - 0.02), (sgn, 0, 0), (0, 0, 1), ONI_W_W, ONI_W_H,
                    ONI_W_T, TL)
    if close_hi:      # f2: the ridge stops against a post (the gate join): its end tile stands at the stop
        G.onigawara(g, (xb - 0.045 - ONI_W_T / 2, yc, d["base_ridge"] - 0.02), (1, 0, 0), (0, 0, 1), ONI_W_W * 0.9,
                    ONI_W_H * 0.9, ONI_W_T, TL)
    return g, d


def corner_cap():
    """The 1 x 1 m corner block's cap (block x in [-1, 0], y in [-1, 0]; legs leave through x = 0 and y = 0)."""
    d = CD
    leg, _ = cap_geo(-1.25, 0.0)
    leg = G.clip(leg, [((0, 0, 0), (1, -1, 0))])            # x-leg keeps x > y
    g = G.weld(Geo().extend(leg).extend(G.reflect_xy(leg)), 1e-6)   # the two cut faces meet exactly on x = y
    tn, cs = math.tan(CAP_TH), math.cos(CAP_TH)
    yc = -0.5
    top_off = G.TILE_TOP / cs

    def ztop(dy):
        return CAP_BASE + (d["half"] - dy) * tn + top_off

    a = RIDGE_HW
    # hip roll (outside) along the diagonal, relief disc at the eave corner
    p0 = Vector((yc - a, yc - a, ztop(a) + 0.01))
    p1 = Vector((yc - d["half"] + 0.03, yc - d["half"] + 0.03, ztop(d["half"] - 0.03) + 0.01))
    G.roll_line(g, p0, p1, (0.35, 0.35, 1.0), TL, r=0.055, seg=0.22, disc_end=0.07)
    # f1: valley (inside): a board under the cut roll ends plus a mitred cover roll along the valley line
    v0 = Vector((yc + a, yc + a, CAP_BASE + (d["half"] - a) * tn + 0.02))
    v1 = Vector((yc + d["half"], yc + d["half"], CAP_BASE + 0.02))
    ax = (v1 - v0).normalized()
    side = Vector((0, 0, 1)).cross(ax).normalized()
    G.obox(g, (v0 + v1) / 2, ax, side, ax.cross(side), (v1 - v0).length / 2, 0.08, 0.012, TL)
    q0 = Vector((yc + a, yc + a, ztop(a) + 0.004))
    q1 = Vector((yc + d["half"] - 0.03, yc + d["half"] - 0.03, ztop(d["half"] - 0.03) + 0.004))
    G.roll_line(g, q0, q1, (-0.35, -0.35, 1.0), TL, r=0.052, seg=0.22, disc_end=0.066)
    # f1: a round finial where the mitred ridges meet (the sheet's V view): stepped base, neck, ball
    # f2: the sheet's large ball-topped block where the ridges meet: a two-tier square stack turned 45 deg (square to
    # the diagonal), a collar and a big ball
    kz = d["kan_c"]
    zb0 = d["base_ridge"] - 0.02
    dg = Vector((1, 1, 0)).normalized()
    sd = Vector((-1, 1, 0)).normalized()
    c0 = Vector((yc, yc, 0.0))
    G.obox(g, c0 + Vector((0, 0, (zb0 + kz + 0.02) / 2)), dg, sd, (0, 0, 1), 0.20, 0.20, (kz + 0.02 - zb0) / 2, TL)
    G.obox(g, c0 + Vector((0, 0, kz + 0.02 + 0.012)), dg, sd, (0, 0, 1), 0.215, 0.215, 0.012, TL)
    G.obox(g, c0 + Vector((0, 0, kz + 0.044 + 0.035)), dg, sd, (0, 0, 1), 0.15, 0.15, 0.035, TL)
    G.lathe(g, (yc, yc, kz + 0.114), (0, 0, 1), (1, 0, 0),
            [(0.0, 0.0), (0.0, 0.070), (0.030, 0.070), (0.040, 0.050), (0.060, 0.085), (0.100, 0.112), (0.150, 0.118),
             (0.200, 0.105), (0.240, 0.072), (0.262, 0.036), (0.268, 0.0)], TL, nseg=20)
    return g


# ------------------------------------------------------------------------------------------------ wall pieces
def body_geo(x0, x1, y0, y1, z0, z1, mat, step=0.5):
    g = Geo()
    xs = [x0 + (x1 - x0) * i / max(1, round((x1 - x0) / step)) for i in range(int(max(1, round((x1 - x0) / step))) + 1)]
    ys = [y0 + (y1 - y0) * i / max(1, round((y1 - y0) / step)) for i in range(int(max(1, round((y1 - y0) / step))) + 1)]
    zs = sorted({z0, min(z1, z0 + 0.15), min(z1, z0 + 0.35), max(z0, z1 - 0.50), max(z0, z1 - 0.25),
                 max(z0, z1 - 0.10), z1})
    lattice_surface(g, xs, ys, zs, mat, vc=grime_rule(z0, z1))
    return g


PIER_Y = (-1.2, 0.2)       # 1.4 m deep, centred on the wall (0.2 proud of both faces): rotation-safe, and a capsule
                            # can stand in line with the gate ridge (y 0) for route 6


def step_pier(name, length, gable_lo, gable_hi, note, seed):
    """A stepped wall section (the wall's own footing / plaster / cap, raised, 1.4 m deep like the grey-box pier): flat
    walkable top +3.25 over its first 1.0 m; any further length (the gate one) is tucked under the gate verge and
    blocks up to +3.74."""
    p = Piece(name, "landing", "Landings", note)
    th = PIER_Y[1] - PIER_Y[0]
    pd = cap_dims(th)
    pz = PIER_TOP - pd["H"]
    faces = ["-y", "+y"] + (["-x"] if gable_lo else []) + (["+x"] if gable_hi else [])
    quo = ([("-x", "-y"), ("-x", "+y")] if gable_lo else []) + ([("+x", "-y"), ("+x", "+y")] if gable_hi else [])
    g = footing(0, length, PIER_Y[0], PIER_Y[1], tuple(faces), tuple(quo), seed)
    g.extend(body_geo(0, length, PIER_Y[0], PIER_Y[1], FOOT_H, pz, EP, step=0.8))
    cg, _ = cap_geo(0, length, thick=th, gable_lo=gable_lo, gable_hi=gable_hi, close_hi=not gable_hi)
    g.extend(cg.transformed(Matrix.Translation((0, PIER_Y[1], pz))))
    p.g = g
    p.hull_box(0, min(1.0, length), PIER_Y[0], PIER_Y[1], 0, PIER_TOP)
    if length > 1.0:
        p.hull_box(1.0, length, PIER_Y[0], PIER_Y[1], 0, 3.74)
    p.nanite = True
    p.extra = {"body_top": round(pz, 4), "walk_top": PIER_TOP, "flat_landing_x": [0.0, min(1.0, length)]}
    return p


JOIN_L = 0.49              # (f2: stops 1 cm short of the cluster so nothing touches) f2: the wall's last 0.5 m before the gate's wall-end post cluster (world x 18.0 .. 18.5 /
                           # 25.5 .. 26.0), under the gate verge
STAND_X = (-0.40, 0.40)    # f2 route-6 eave stand (piece local; pivot world (17.52, 0.25, 0) west, (26.48, 0.25, 0)
STAND_Y = (0.0, 2.65)      # east): world x 17.12 .. 17.92 (8 cm short of the verge at 18.0), y 0.25 .. 2.90
STAND_PIVOTS = [(17.52, 0.25, 0.0), (26.48, 0.25, 0.0)]
DECK_Z0 = 2.90             # edge beam underside (f2: a slimmer deck edge, 0.35 m)


def gate_join():
    """f2 (the judge and the main session: no plaster piers; the wall runs into the gate's timber post cluster at its
    own height, the cap tucked under the gate eave, its end tile stopping against the post): the last 0.5 m of the
    T200 wall, footing + plaster body + cap in one piece, the cap closed at +X by an end plate and a stacked ridge-end
    tile against the post. Wall frame (pivot on the inner face at the base, runs along +X); the east one is the same
    piece turned 180 deg."""
    p = Piece("SM_DK_Wall_GateJoin", "building", "Wall",
              "the wall's last 0.5 m into the gate's post cluster (T200): footing, plaster, cap ending in an end tile "
              "against the post, under the gate verge")
    zb200 = TOPS["T200"] - CAP_H
    g = footing(0, JOIN_L, -WALL_T, 0, ("-y", "+y"), (), 131)
    g.extend(body_geo(0, JOIN_L, -WALL_T, 0, FOOT_H, zb200, EP, step=0.25))
    cg, _ = cap_geo(0, JOIN_L, close_hi=True)
    g.extend(cg.transformed(Matrix.Translation((0, 0, zb200))))
    p.g = g
    p.hull_box(0, JOIN_L, -WALL_T, 0, 0, TOPS["T200"])
    p.nanite = True
    p.extra = {"length": JOIN_L, "top": TOPS["T200"]}
    return p


def gate_stand():
    """f2 route 6 (the grey-box way: a flat landing at the eave; the roof stays the sheet's plain gable; no plaster
    pier): an open timber eave stand at each courtyard-side corner of the gatehouse, in the gate's own timber: six
    posts on granite plinths, through-rails, knee braces, edge beams and a plank deck whose flat top is the eave
    height (+3.25). It runs from the wall's courtyard face to past the courtyard eave: the wall-top runner mantles
    1.25 m onto its south end (as onto the grey-box pier) and steps east onto the N eave (+3.34 at y 2.3). Symmetric
    in x: the same piece stands on both sides. Pivot: the deck's south edge centre at the ground."""
    p = Piece("SM_DK_Gate_Stand", "landing", "Landings",
              "route-6 eave stand: open timber deck +3.25 on six posts (0.8 x 2.65 m), beside the gatehouse's courtyard "
              "eave corner; mantle 1.25 from the wall top, step onto the eave")
    g = p.g
    x0, x1 = STAND_X
    y0, y1 = STAND_Y
    top = PIER_TOP
    pxs = (-0.30, 0.30)
    pys = (0.14, 2.51)          # f2 review: four corner posts only (six read as a scaffold)
    for i, py in enumerate(pys):
        for j, px in enumerate(pxs):
            plinth(g, px - 0.16, px + 0.16, py - 0.16, py + 0.16, 0.40, 61 + 3 * i + j)
            post(g, px, py, 0.09, 0.09, 0.40, DECK_Z0, bolts=False)
            for sd in (-1, 1):      # iron strap at the post head
                G.box(g, px - 0.094, px + 0.094, py + sd * 0.094 - (0.004 if sd < 0 else 0.0),
                      py + sd * 0.094 + (0.004 if sd > 0 else 0.0), DECK_Z0 - 0.26, DECK_Z0 - 0.02, IR, grain="z")
    # one through-rail (nuki) along each long side and across each end, at the gate's mid-rail height
    for px in pxs:
        G.box(g, px - 0.035, px + 0.035, pys[0] - 0.14, pys[-1] + 0.14, 1.70, 1.82, T_, grain="y")
    for py in pys:
        G.box(g, pxs[0] - 0.14, pxs[1] + 0.14, py - 0.035, py + 0.035, 1.70, 1.82, T_, grain="x")
    # edge beams along y (square ends past the end posts), one knee brace from each post in towards the span
    for px in pxs:
        G.box(g, px - 0.08, px + 0.08, y0 - 0.02, y1 + 0.02, DECK_Z0, DECK_Z0 + 0.16, T_, grain="y")
        for py, sd in ((pys[0], 1), (pys[-1], -1)):
            a = Vector((px, py + sd * 0.09, DECK_Z0 - 0.50))
            b = Vector((px, py + sd * 0.55, DECK_Z0 + 0.01))
            ax = (b - a).normalized()
            G.obox(g, (a + b) / 2, ax, (1, 0, 0), ax.cross(Vector((1, 0, 0))), (b - a).length / 2, 0.045, 0.045, T_)
    # joists across x, a plank deck along y (flat top = +3.25), an edge board round the deck
    jz0, jz1 = DECK_Z0 + 0.16, top - 0.07
    k = 0
    yj = y0 + 0.10
    while yj < y1 - 0.05:
        G.box(g, x0 + 0.03, x1 - 0.03, yj - 0.05, yj + 0.05, jz0, jz1, T_, grain="x")
        yj += 0.42
        k += 1
    npk = 5
    wpk = (x1 - x0 - 0.10) / npk
    for i in range(npk):
        xa = x0 + 0.05 + i * wpk + 0.004
        xb = x0 + 0.05 + (i + 1) * wpk - 0.004
        G.box(g, xa, xb, y0 + 0.05, y1 - 0.05, jz1, top - 0.002 + (0.001 if i % 2 else 0.0), T_, grain="y")
    for (xa, xb) in ((x0, x0 + 0.05), (x1 - 0.05, x1)):
        G.box(g, xa, xb, y0, y1, DECK_Z0 + 0.12, top, T_, grain="y")
    for (ya, yb) in ((y0, y0 + 0.05), (y1 - 0.05, y1)):
        G.box(g, x0 + 0.05, x1 - 0.05, ya, yb, DECK_Z0 + 0.12, top, T_, grain="x")
    # collision: the deck (the landing), the posts on their plinths
    p.hull_box(x0, x1, y0, y1, DECK_Z0, top)
    for py in pys:
        for px in pxs:
            p.hull_box(px - 0.16, px + 0.16, py - 0.16, py + 0.16, 0.0, DECK_Z0)
    for px in pxs:          # the long-side through-rails (+1.70): no standing capsule walks in under the deck
        p.hull_box(px - 0.035, px + 0.035, pys[0], pys[-1], 1.70, 1.82)
    p.nanite = True
    p.extra = {"deck_top": top, "deck_underside": DECK_Z0, "local_x": list(STAND_X), "local_y": list(STAND_Y),
               "pivots_world": [list(v) for v in STAND_PIVOTS]}
    return p


SLAB_H = 0.08
APRON_Y1 = 2.0            # r2: the gate paving's courtyard edge (world Y 2.0 = the sand field's south edge)


def frame_pier():
    """The wall sheet's freestanding timber-framed pier (bottom right of dojo_wall_ref.png): a granite slab plinth, the
    squared stone base, a post-and-beam frame (corner posts, sill, head beams with square ends past the posts), an
    exposed earthen panel recessed between the timbers on all four faces, and the gabled kawara cap at the wall top.
    1.0 x 1.0 m, the wall's own frame (runs along +x, inner face y = 0, pivot at the base); a wall terminal for the BR
    openings (the wickets are solid wall in the 1v1, so it is not placed in the 1v1 layout)."""
    p = Piece("SM_DK_Wall_FramePier", "building", "Wall",
              "freestanding timber-framed pier 1 x 1 m: slab plinth, stone base, post-and-beam frame, exposed earthen "
              "panels, gabled cap (top +2.0)")
    g = Geo()
    poly = [(-0.14, -1.14), (1.14, -1.14), (1.14, 0.14), (-0.14, 0.14)]
    G.polystone(g, poly, (0, 0, SLAB_H - 0.004), (1, 0, 0), (0, 0, 1), 0.14, 0.0, 211, GR, chamfer=0.018, bulge=0.003,
                rough=0.004, step=0.14,
                moss=lambda v, j, u: clamp01(0.10 + 0.5 * (noise.noise(v * 4.0) * 0.5 + 0.5) * (1.0 - u)), grime=0.5)
    # f2 (the sheet): an ashlar base of big squared blocks on the slab, two courses, the joints crossing
    gap = 0.012
    ch = FOOT_H / 2
    for ci in range(2):
        za, zb_ = SLAB_H + ci * ch, SLAB_H + (ci + 1) * ch
        halves = (((0.0, 0.5), (-WALL_T, 0.0)), ((0.5, 1.0), (-WALL_T, 0.0))) if ci == 0 else                  (((0.0, 1.0), (-WALL_T, -0.5)), ((0.0, 1.0), (-0.5, 0.0)))
        for bi, ((xa, xb), (ya, yb)) in enumerate(halves):
            G.rounded_stone(g, ((xa + xb) / 2, (ya + yb) / 2, (za + zb_) / 2), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                            ((xb - xa) / 2 - gap / 2, (yb - ya) / 2 - gap / 2, ch / 2 - gap / 2),
                            0.03, 223 + 5 * ci + bi, GR, bulge=0.006, rough=0.008, n=(5, 5, 3),
                            vc=moss_rule(FOOT_H + SLAB_H, grime=0.45))
    G.box(g, 0.02, 0.98, -WALL_T + 0.02, -0.02, SLAB_H, SLAB_H + FOOT_H - 0.004, MO)
    z0 = SLAB_H + FOOT_H
    zc = TOPS["T200"] - CAP_H                   # the cap sits where the wall's T200 cap sits
    zh1 = zc - 0.055                            # head beam top (under the cap's ledgers)
    zh0 = zh1 - 0.17
    ps = 0.15
    # earthen core (recessed 3 cm behind the timbers on every face)
    rec = 0.03
    zl = zh0 - 0.16                             # f2: a grey stone lintel band under the head beam (the sheet)
    lattice_surface(g, [rec, 0.5, 1 - rec], [-WALL_T + rec, -0.5, -rec], [z0 + 0.10, (z0 + zl) / 2, zl], EC,
                    vc=lambda co: (0.0, 0.25 + 0.20 * (noise.noise(co * 5.0) * 0.5 + 0.5), 1.0))
    for (ya, yb, xa, xb) in ((-WALL_T + 0.005, -WALL_T + 0.16, ps, 1 - ps), (-0.16, -0.005, ps, 1 - ps),
                             (-WALL_T + ps, -ps, 0.005, 0.16), (-WALL_T + ps, -ps, 1 - 0.16, 0.995)):
        G.rounded_stone(g, ((xa + xb) / 2, (ya + yb) / 2, (zl + zh0) / 2), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                        ((xb - xa) / 2, (yb - ya) / 2, (zh0 - zl) / 2 - 0.004), 0.012, int(1000 * (xa + ya)) % 97 + 5,
                        GR, bulge=0.002, rough=0.004, n=(4, 2, 2), vc=moss_rule(0.01, grime=0.35))
    # corner posts
    for (xa, xb) in ((0.0, ps), (1 - ps, 1.0)):
        for (ya, yb) in ((-WALL_T, -WALL_T + ps), (-ps, 0.0)):
            G.box(g, xa, xb, ya, yb, z0, zh1, T_, grain="z")
    # sill beams on the base (all four sides), head beams with square ends past the posts
    G.box(g, 0.0, 1.0, -WALL_T, -WALL_T + 0.12, z0, z0 + 0.10, T_, grain="x")
    G.box(g, 0.0, 1.0, -0.12, 0.0, z0, z0 + 0.10, T_, grain="x")
    G.box(g, 0.0, 0.12, -WALL_T + ps, -ps, z0, z0 + 0.10, T_, grain="y")
    G.box(g, 1 - 0.12, 1.0, -WALL_T + ps, -ps, z0, z0 + 0.10, T_, grain="y")
    for (ya, yb) in ((-WALL_T - 0.012, -WALL_T + 0.13), (-0.13, 0.012)):
        G.box(g, -0.09, 1.09, ya, yb, zh0, zh1, T_, grain="x")
    for (xa, xb) in ((-0.012, 0.13), (0.87, 1.012)):
        G.box(g, xa, xb, -WALL_T - 0.09, 0.09, zh0 + 0.02, zh1 - 0.02, T_, grain="y")
    # a mid rail on each face (the sheet's panel is split low by a rail over the stone base)
    for (ya, yb) in ((-WALL_T, -WALL_T + 0.08), (-0.08, 0.0)):
        G.box(g, ps, 1 - ps, ya, yb, zh0 - 0.34, zh0 - 0.26, T_, grain="x")
    for (xa, xb) in ((0.0, 0.08), (0.92, 1.0)):
        G.box(g, xa, xb, -WALL_T + ps, -ps, zh0 - 0.34, zh0 - 0.26, T_, grain="y")
    # a plaster band between the head beam and the cap's ledgers is covered by the ledgers; the cap, gabled both ends
    cg, _ = cap_geo(0, 1, gable_lo=True, gable_hi=True)
    g.extend(cg.transformed(Matrix.Translation((0, 0, zc))))
    p.g = g
    p.hull_box(-0.14, 1.14, -1.14, 0.14, 0, SLAB_H)
    p.hull_box(0, 1, -WALL_T, 0, 0, TOPS["T200"])
    p.nanite = True
    p.extra = {"top": TOPS["T200"], "slab_h": SLAB_H, "base_top": round(z0, 3), "cap_z": round(zc, 4)}
    return p


def wall_pieces():
    P = []
    zb = {k: round(v - CAP_H, 4) for k, v in TOPS.items()}
    seeds = {1: 11, 2: 23, 4: 47}
    for L in (1, 2, 4):
        p = Piece(f"SM_DK_WallFooting_{L}m", "building", "Wall", f"granite footing {L} m, {FOOT_H} m tall")
        p.g = footing(0, L, -WALL_T, 0, ("-y", "+y"), (), seeds[L])
        p.hull_box(0, L, -WALL_T, 0, 0, FOOT_H)
        p.nanite = True
        P.append(p)
        for key, top in TOPS.items():
            b = Piece(f"SM_DK_WallBody_{L}m_{key}", "building", "Wall",
                      f"earthen plaster body {L} m, +{FOOT_H} -> {zb[key]:.3f} (wall top {top})")
            b.g = body_geo(0, L, -WALL_T, 0, 0.0, zb[key] - FOOT_H, EP)
            b.hull_box(0, L, -WALL_T, 0, 0, zb[key] - FOOT_H)
            b.extra = {"pivot_z": FOOT_H, "top": top}
            P.append(b)
        c = Piece(f"SM_DK_WallCap_{L}m", "building", "Wall", f"kawara wall cap {L} m, flat walkable collision")
        c.g, _ = cap_geo(0, L)
        c.hull_box(0, L, -WALL_T, 0, 0, CAP_H)
        c.nanite = True
        P.append(c)
    e = Piece("SM_DK_WallFooting_End", "building", "Wall", "granite footing 1 m wrapping the +X end in stone")
    e.g = footing(0, 1, -WALL_T, 0, ("-y", "+y", "+x"), (("+x", "-y"), ("+x", "+y")), 71)
    e.hull_box(0, 1, -WALL_T, 0, 0, FOOT_H)
    e.nanite = True
    P.append(e)
    ec = Piece("SM_DK_WallCap_End", "building", "Wall", "1 m wall cap with the gabled end at +X")
    ec.g, _ = cap_geo(0, 1, gable_hi=True)
    ec.hull_box(0, 1, -WALL_T, 0, 0, CAP_H)
    ec.nanite = True
    P.append(ec)
    cf = Piece("SM_DK_WallFooting_Corner", "building", "Wall", "1 x 1 m corner footing, quoin at the outer corner")
    cf.g = footing(-1, 0, -1, 0, ("-x", "-y"), (("-x", "-y"),), 83)
    cf.hull_box(-1, 0, -1, 0, 0, FOOT_H)
    cf.nanite = True
    P.append(cf)
    cc = Piece("SM_DK_WallCap_Corner", "building", "Wall", "1 x 1 m corner cap: mitred ridge + finial, hip out, valley in")
    cc.g = corner_cap()
    cc.hull_box(-1, 0, -1, 0, 0, CAP_H)
    cc.nanite = True
    P.append(cc)
    P.append(step_pier("SM_DK_Wall_StepPier", 1.0, True, True,
                       "stepped wall section 1 m, flat walkable top +3.25 (route 2 landing), gabled both ends", 97))
    P.append(gate_join())
    # r2: SM_DK_Gate_Stand removed (the judge's #1: the free-standing timber frames outside the gate roof read as
    # scaffolding). gate_stand() is kept below for the record only; nothing builds or places it.
    P.append(frame_pier())
    return P, zb


# ------------------------------------------------------------------------------------------------ gatehouse numbers
TN = math.tan(PITCH)
CS = math.cos(PITCH)
BASE_OFF = G.TILE_TOP / CS          # vertical offset collision plane -> tile base plane
GX, GY = 4.0, 2.5                   # roof half sizes (8 x 5 m, spec)
GP = 3.2                            # gable plane / corner and wall posts (x)
PY = 1.75                           # front / rear post lines (y)
HINGE_X, HINGE_Y, LEAF_Z = 2.24, -0.66, 0.11
LEAF_W, LEAF_H, LEAF_TT = 2.237, 3.385, 0.24     # leaf width, height, total thickness incl. hardware
RAFT_STUB = (1.40, 2.36)            # courtyard-side rafters here stop at the rear keta (the leaves' swing, measured)
UNDER = 0.1225 + 0.004 + 0.025 + 0.10   # collision plane -> rafter underside (tiles, sarking, rafter)
VERGE_U = 0.14                      # f2: the verge stack's centre line, in from the verge edge
PAN_TOP = 0.030                     # f2: the verge stack's seat above the tile base plane
RIDGE_NOSHI = [0.46, 0.43, 0.40, 0.37, 0.34]   # f2: five ridge noshi layers (was three)
ONI_W, ONI_H, ONI_T = 0.66, 0.78, 0.40         # f2: the gate's stacked ridge-end tiles (deep: a block from the front)
LAMP_SCALE = 1.25                   # f2: bigger lanterns
STEP_TOP = 0.24                     # f2: the step stones in front of the door posts
PL_H = 0.45                         # f2: post plinth height (the sheet: about 0.4-0.5 m)
CL_X = (3.00, 3.50)                 # f2: the wall-end post cluster (|x|); the wall ends at |x| = 3.50 (world 18.5 / 25.5)


def zcol_s(y):
    """Collision (tile top) height of the S / N slopes at |y|."""
    return GATE_EAVE + (GY - abs(y)) * TN


ZR = zcol_s(0.0)                    # the slope planes meet here (4.4158)


def roof_under(y):
    """Rafter underside at |y| (the lowest roof timber over a point)."""
    return zcol_s(y) - UNDER


def gate_roof():
    p = Piece("SM_DK_Gate_Roof", "roof", "Gatehouse",
              "kirizuma (plain gable) roof 8 x 5 m: eave +3.25 front and back, slope planes meet at +4.416, verge "
              "bargeboards and rolls, plain round stacked ridge-end tiles")
    g = Geo()
    s_ridge = (GY - 0.19) / CS
    C = s_ridge / 9.0                 # f1: nine courses per slope
    zb0 = GATE_EAVE - BASE_OFF
    sn = math.sin(PITCH)
    rafter_x = [s * (0.225 + 0.45 * k) for k in range(9) for s in (-1, 1)]
    rafter_x = [x for x in rafter_x if abs(x) < GX - 0.1]
    for sgn in (-1, 1):
        if sgn < 0:
            sl = Slope((-GX, -GY, zb0), (1, 0, 0), (0, CS, sn))
        else:
            sl = Slope((GX, GY, zb0), (-1, 0, 0), (0, -CS, sn))
        G.tile_field(g, sl, 0.0, 2 * GX, 0.0, s_ridge, C, TL, eave=True, phase=0.0, roll_margin=0.26)
        # f2 verge (the sheet's framed gable edges): along each verge a stack of flat verge tiles (two layers) under a
        # big round verge roll, ending at the eave corner in a small stacked end tile; the edge tiles hang over the
        # bargeboard
        for u in (VERGE_U, 2 * GX - VERGE_U):
            a0 = sl.at(u, 0.02, PAN_TOP)
            a1 = sl.at(u, s_ridge - 0.02, PAN_TOP)
            htop = G.noshi_stack(g, a0, a1, sl.N, [0.26, 0.22], 0.042, TL, seg=0.30, seed=int(u * 100) + 5)
            # r2: the roll's open underside (its arc stops 18 deg below the axis) now sits ON the stack (the side
            # view showed a sky slit along both verges: the arc edge stood 2.7 cm over the stack top)
            G.roll_line(g, sl.at(u, 0.03, PAN_TOP + htop + 0.018), sl.at(u, s_ridge - 0.05, PAN_TOP + htop + 0.018),
                        sl.N, TL, r=0.075, seg=C, disc_start=None)
            G.onigawara(g, sl.at(u, 0.0, PAN_TOP - 0.10) + sl.S * 0.07, -sl.S, sl.N, 0.30, 0.34, 0.14, TL)
            uu = 0.004 if u < GX else 2 * GX - 0.004
            a = sl.at(uu, 0.0, 0.0)
            b = sl.at(uu, s_ridge + 0.08, 0.0)
            ax = (b - a).normalized()
            G.obox(g, (a + b) / 2 - sl.N * 0.035, ax, sl.U, sl.N, (b - a).length / 2, 0.008, 0.045, TL)
        zu = lambda y: zcol_s(y) - BASE_OFF - 0.004   # noqa: E731
        # sarking (timber underside). f2: in 16 strips up the slope, so it follows the slope sag with the tiles (f1 was
        # one flat board: the tiles sagged 3 cm below it mid-slope and the brown board showed between the courses)
        nst = 16
        for k_ in range(nst):
            ya_, yb_ = GY * (1 - k_ / nst), GY * (1 - (k_ + 1) / nst)
            poly = [(-GX, sgn * ya_, zu(ya_)), (GX, sgn * ya_, zu(ya_)), (GX, sgn * yb_, zu(yb_)),
                    (-GX, sgn * yb_, zu(yb_))]      # f2: to the verge edge (no one-sided tile strip seen from below)
            if sgn > 0:
                poly = list(reversed(poly))
            G.prism(g, poly, sl.N, 0.025, T_, frame=(sl.S, sl.U, sl.N))
        # kayaoi (thin fascia) at the eave over the rafter tails
        ye0, ye1 = sgn * (GY - 0.07), sgn * (GY - 0.015)
        G.box(g, -GX + 0.02, GX - 0.02, min(ye0, ye1), max(ye0, ye1), zb0 - 0.055, zb0 - 0.006, T_, grain="x")
        # rafters with square tails showing under the kayaoi
        for x in rafter_x:
            # over the leaves' swing (courtyard side) the rafters are tail stubs resting on the rear keta: a full
            # rafter's underside drops below the leaf top (+3.495) beyond y +1.435
            stub = sgn > 0 and RAFT_STUB[0] <= abs(x) <= RAFT_STUB[1]
            ya, yb = sgn * (GY - 0.05), sgn * (1.64 if stub else 0.12)
            a = Vector((x, ya, zu(GY - 0.05) - 0.025 - 0.05))
            b = Vector((x, yb, zu(abs(yb)) - 0.025 - 0.05 - 0.03))   # f2: 3 cm lower inboard (clear of the slope sag)
            ax = (b - a).normalized()
            G.obox(g, (a + b) / 2, ax, (1, 0, 0), ax.cross(Vector((1, 0, 0))), (b - a).length / 2, 0.045, 0.05, T_)
    # bargeboards (hafu) under the verges, a hanging board (gegyo) at each apex
    for sx in (-1, 1):
        xb = sx * (GX - 0.035)
        for sy in (-1, 1):
            a = Vector((xb, sy * (GY + 0.02), zcol_s(GY) - BASE_OFF - 0.004 - 0.13))
            b = Vector((xb, 0.0, ZR - BASE_OFF - 0.004 - 0.13))
            ax = (b - a).normalized()
            w = ax.cross(Vector((1, 0, 0))).normalized()
            if w.z < 0:
                w = -w
            G.obox(g, (a + b) / 2, ax, (1, 0, 0), w, (b - a).length / 2 + 0.02, 0.028, 0.13, T_)
            # a small end block at the bargeboard foot
            G.box(g, xb - 0.045, xb + 0.045, sy * (GY + 0.02) - 0.07, sy * (GY + 0.02) + 0.07,
                  zcol_s(GY) - BASE_OFF - 0.30, zcol_s(GY) - BASE_OFF - 0.16, T_, grain="y")
        za = ZR - BASE_OFF - 0.004
        G.prism(g, [(xb, -0.16, za - 0.22), (xb, 0.16, za - 0.22), (xb, 0.20, za - 0.08), (xb, 0.0, za),
                    (xb, -0.20, za - 0.08)], (sx, 0, 0), 0.05, T_,
                frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
    # f2 ridge (the sheet's heavy ridge): mortar bed, five stacked noshi layers, a big round ridge roll; at each end a
    # heavy stacked ridge-end tile (onigawara, plain: no symbol) whose round face looks out over the gable
    zr0 = ZR - 0.10
    G.box(g, -GX + 0.06, GX - 0.06, -0.24, 0.24, ZR - BASE_OFF - 0.02, zr0, MO)
    top = G.noshi_stack(g, (-GX + 0.20, 0, zr0), (GX - 0.20, 0, zr0), (0, 0, 1), RIDGE_NOSHI, 0.048, TL, seg=0.3,
                        seed=41)
    kz = zr0 + top + 0.022          # r2: 0.030 -> 0.022, the roll's arc edges sit on the top noshi (no hairline slit)
    G.roll_line(g, (-GX + 0.25, 0, kz), (GX - 0.25, 0, kz), (0, 0, 1), TL, r=0.085, seg=0.3)
    oni_base = zr0 - 0.08
    for sx in (-1, 1):
        oni_h = G.onigawara(g, (sx * (GX + 0.02 - ONI_T / 2), 0, oni_base), (sx, 0, 0), (0, 0, 1), ONI_W, ONI_H, ONI_T,
                            TL)
    oni_top = oni_base + oni_h
    # f1: a gentle sag of the slopes (about 3 cm mid-slope) and a slight upturn of the eave towards the corners
    def sag(v):
        # f2: continuous at the eave (f1 cut the upturn off at |y| > GY + 0.1, which twisted the bargeboard feet)
        ay = abs(v.y)
        s = max(0.0, min(1.0, (GY - ay) / GY))
        dz = -0.03 * math.sin(math.pi * s)
        dz += 0.05 * max(0.0, (abs(v.x) - 2.0) / 2.0) ** 2 * max(0.0, min(1.0, 1.0 - (GY - ay) / 1.0))
        return Vector((0, 0, dz))
    G.warp(g, sag)
    p.g = g
    # collision: one flat plane per slope (0.2 m slabs), the ridge stack, the two ridge-end tiles
    sl_th = 0.2

    def slab(poly):
        pts = [Vector(q) for q in poly]
        return pts + [q - Vector((0, 0, sl_th)) for q in pts]

    for sgn in (-1, 1):
        p.hull_pts(slab([(-GX, sgn * GY, zcol_s(GY)), (GX, sgn * GY, zcol_s(GY)), (GX, 0.0, ZR), (-GX, 0.0, ZR)]))
    p.hull_box(-GX + 0.06, GX - 0.06, -0.24, 0.24, zr0, kz + 0.085)
    for sx in (-1, 1):
        p.hull_box(min(sx * (GX + 0.02 - ONI_T), sx * (GX + 0.04)), max(sx * (GX + 0.02 - ONI_T), sx * (GX + 0.04)),
                   -ONI_W / 2, ONI_W / 2, oni_base, oni_top)
    p.nanite = True
    p.extra = {"ridge_roll_top": round(kz + 0.085, 3), "planes_meet": round(ZR, 4), "ridge_end_top": round(oni_top, 3),
               "ridge_end_face_x": GX + 0.02, "ridge_noshi_layers": len(RIDGE_NOSHI), "gable_x": GP, "verge_x": GX, "pitch_deg": 25.0,
               "sag_mid_slope_m": 0.03, "eave_corner_upturn_m": 0.05}
    return p


def post(g, x, y, hx, hy, z0, z1, bolts=True):
    G.box(g, x - hx, x + hx, y - hy, y + hy, z0, z1, T_, grain="z")
    if bolts:
        for zb in (z1 - 0.35, z0 + 0.6):
            for (fx, fy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                c = Vector((x + fx * (hx + 0.004), y + fy * (hy + 0.004), zb))
                n = Vector((fx, fy, 0))
                G.obox(g, c, Vector((0, 0, 1)), Vector((-fy, fx, 0)), n, 0.08, min(hx, hy) * 0.7, 0.004, IR)
                G.dome(g, c + n * 0.004, n, (0, 0, 1), 0.018, IR, nseg=8, rings=2)


def plinth(g, x0, x1, y0, y1, z1, seed):
    """A squared granite plinth block (the sheet's post bases). r2: a hewn block (crisp 2 cm chamfers, pitched
    sides) in the library Granite."""
    G.hewn_box(g, ((x0 + x1) / 2, (y0 + y1) / 2, z1 / 2), ((1, 0, 0), (0, -1, 0), (0, 0, 1)),
               ((x1 - x0) / 2, (y1 - y0) / 2, z1 / 2), 0.02, seed, GR, exposed=("-a", "+a", "-d", "+d"), pitch=0.006)


def plank_panel(g, x0, x1, y0, y1, z0, z1, n_planks, ch=0.012):
    """Vertical planks with deep V grooves between x0..x1 (plank faces at y0 / y1)."""
    w = (x1 - x0) / n_planks
    for i in range(n_planks):
        a, b = x0 + i * w, x0 + (i + 1) * w
        poly = [(a + ch, y0, z1), (b - ch, y0, z1), (b, y0 + ch, z1), (b, y1 - ch, z1), (b - ch, y1, z1),
                (a + ch, y1, z1), (a, y1 - ch, z1), (a, y0 + ch, z1)]
        G.prism(g, poly, (0, 0, 1), z1 - z0, T_, frame=(Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))))


def gate_frame():
    p = Piece("SM_DK_Gate_Frame", "building", "Gatehouse",
              "gatehouse frame: door posts, wall posts, front + rear corner posts on plinths, bracket clusters, layered "
              "eave beams, tie beams, gables, lintel, plank side panels")
    g = p.g
    for sx in (-1, 1):
        # plinth blocks
        # f2: tall cut-stone plinths (the sheet: about 0.4-0.5 m) under every post
        for sy in (-1, 1):
            plinth(g, sx * GP - 0.28, sx * GP + 0.28, sy * PY - 0.28, sy * PY + 0.28, PL_H, 7 + sx + 3 * sy)
        plinth(g, min(sx * CL_X[0], sx * CL_X[1]), max(sx * CL_X[0], sx * CL_X[1]), -1.08, 0.08, PL_H, 17 + sx)
        plinth(g, min(sx * 2.245, sx * 2.62), max(sx * 2.245, sx * 2.62), -0.95, -0.10, PL_H, 21 + sx)
        plinth(g, min(sx * 2.62, sx * 3.00), max(sx * 2.62, sx * 3.00), -0.66, -0.34, PL_H, 25 + sx)
        # corner posts + bracket clusters (daito, crossed bracket arms, small blocks)
        for sy in (-1, 1):
            cx, cy = sx * GP, sy * PY
            post(g, cx, cy, 0.18, 0.18, PL_H, 2.70)
            G.box(g, cx - 0.23, cx + 0.23, cy - 0.23, cy + 0.23, 2.70, 2.84, T_, grain="x")
            G.box(g, cx - 0.62, cx + 0.62, cy - 0.08, cy + 0.08, 2.84, 2.98, T_, grain="x")
            G.box(g, cx - 0.08, cx + 0.08, cy - 0.62, cy + 0.62, 2.84, 2.98, T_, grain="y")
            for (dx, dy) in ((-0.52, 0), (0.52, 0), (0, -0.52), (0, 0.52), (0, 0)):
                G.box(g, cx + dx - 0.10, cx + dx + 0.10, cy + dy - 0.10, cy + dy + 0.10, 2.98, 3.06, T_, grain="x")
        # wall post (the gable's centre post) inside the f2 wall-end post cluster: the wall (y -1 .. 0) runs into it at
        # its own height; heavy face posts at both wall faces, vertical planks between them on both sides
        post(g, sx * GP, -0.5, 0.18, 0.18, PL_H, 3.06)
        cxa, cxb = sorted((sx * CL_X[0], sx * CL_X[1]))
        for (ya, yb) in ((-1.02, -0.74), (-0.26, 0.02)):
            post(g, (cxa + cxb) / 2 + sx * 0.03, (ya + yb) / 2, (cxb - cxa) / 2 - 0.03, (yb - ya) / 2, PL_H, 3.06,
                 bolts=False)       # (no plates on the face the wall abuts)
            for zb_ in (1.30, 2.60):
                for fy in (-1, 1):
                    yf = (ya + yb) / 2 + fy * ((yb - ya) / 2 + 0.004)
                    G.obox(g, ((cxa + cxb) / 2 + sx * 0.03, yf, zb_), (0, 0, 1), (1, 0, 0), (0, fy, 0), 0.08, 0.14,
                           0.004, IR)
                    G.dome(g, ((cxa + cxb) / 2 + sx * 0.03, yf + fy * 0.004, zb_), (0, fy, 0), (0, 0, 1), 0.02, IR,
                           nseg=8, rings=2)
        for xp in (sx * (CL_X[0] + 0.07), sx * (CL_X[1] - 0.04)):
            xa_p, xb_p = sorted((xp - 0.03, xp + 0.03))
            nps_ = 3
            for i in range(nps_):
                ya_ = -0.74 + i * 0.48 / nps_ + 0.004
                yb_ = -0.74 + (i + 1) * 0.48 / nps_ - 0.004
                G.box(g, xa_p, xb_p, ya_, yb_, PL_H, 3.06, T_, grain="z")
        # f2 (the sheet's side elevation): a big square block (kagami) on the gable face where the tie beam crosses
        # the wall post, bolted iron plates above and below it, iron straps round the post
        xo = sx * CL_X[1]
        G.box(g, min(xo, xo + sx * 0.075), max(xo, xo + sx * 0.075), -0.76, -0.24, 2.78, 3.30, T_, grain="z")
        G.box(g, min(xo, xo + sx * 0.012), max(xo, xo + sx * 0.012), -0.66, -0.34, 2.44, 2.72, IR, grain="z")
        for yb in (-0.60, -0.40):
            for zz in (2.50, 2.66):
                G.dome(g, (xo + sx * 0.012, yb, zz), (sx, 0, 0), (0, 0, 1), 0.020, IR, nseg=8, rings=2)
        xf = xo + sx * 0.075
        for zc_ in (2.86, 3.22):
            G.box(g, min(xf, xf + sx * 0.010), max(xf, xf + sx * 0.010), -0.765, -0.235, zc_ - 0.03, zc_ + 0.03, IR,
                  grain="y")
            for yb in (-0.70, -0.30):
                G.dome(g, (xf + sx * 0.010, yb, zc_), (sx, 0, 0), (0, 0, 1), 0.022, IR, nseg=10, rings=2)
        G.dome(g, (xf, -0.5, 3.04), (sx, 0, 0), (0, 0, 1), 0.05, IR, nseg=14, rings=3)
        # door post (heavy, 0.375 x 0.84) with pintle plates on its inner face
        xa, xb = sorted((sx * 2.25, sx * 2.625))
        G.box(g, xa, xb, -0.92, -0.08, PL_H, 3.85, T_, grain="z")
        for zc in (LEAF_Z + 0.80, LEAF_Z + 2.55):
            xi = sx * 2.25
            G.box(g, min(xi, xi - sx * 0.008), max(xi, xi - sx * 0.008), -0.84, -0.70, zc - 0.12, zc + 0.12, IR)
        for zb in (0.9, 2.2, 3.3):
            G.box(g, xa - 0.004, xb + 0.004, -0.924, -0.076, zb - 0.035, zb + 0.035, IR, grain="x")
        # plank side panel between the door post and the wall post, framed by rails
        pa, pb = sorted((sx * 2.625, sx * 3.02))
        G.box(g, pa, pb, -0.60, -0.40, PL_H, PL_H + 0.12, T_, grain="x")
        G.box(g, pa, pb, -0.60, -0.40, 3.38, 3.50, T_, grain="x")
        plank_panel(g, pa, pb, -0.58, -0.42, PL_H + 0.12, 3.38, 3)
        for (ya, yb) in ((-0.64, -0.58), (-0.42, -0.36)):
            G.box(g, pa, pb, ya, yb, 1.70, 1.82, T_, grain="x")          # mid rail on both faces
        # f1: the courtyard half of each side is closed by a vertical-plank panel from the wall post to the rear corner
        # post, on a granite sill (the return wall runs outside it; no capsule-sized gap is left between them)
        xa_, xb_ = sorted((sx * GP - 0.06, sx * GP + 0.06))
        plinth(g, xa_ - 0.03, xb_ + 0.03, 0.10, 1.46, PL_H, 31 + sx)
        nps = 4
        wps = (1.57 - 0.02) / nps
        for i in range(nps):
            ya_, yb_ = 0.02 + i * wps + 0.005, 0.02 + (i + 1) * wps - 0.005
            G.box(g, xa_ + 0.01, xb_ - 0.01, ya_, yb_, PL_H, 3.06, T_, grain="z")
        for (zr0_, zr1_) in ((PL_H, PL_H + 0.14), (1.70, 1.82), (2.92, 3.06)):
            G.box(g, xa_, xb_, 0.02, 1.57, zr0_, zr1_, T_, grain="y")
        # tie beam along y at the gable (ends past the eave beams as square blocks)
        G.box(g, sx * GP - 0.11, sx * GP + 0.11, -2.02, 2.02, 3.06, 3.30, T_, grain="y")
        # gable: centre block, king post, short tie, block under the ridge beam, dark board infill (set back)
        G.box(g, sx * GP - 0.14, sx * GP + 0.14, -0.14, 0.14, 3.30, 3.42, T_, grain="x")
        G.box(g, sx * GP - 0.08, sx * GP + 0.08, -0.09, 0.09, 3.42, 3.98, T_, grain="z")
        G.box(g, sx * GP - 0.06, sx * GP + 0.06, -0.62, 0.62, 3.64, 3.74, T_, grain="y")
        G.box(g, sx * GP - 0.12, sx * GP + 0.12, -0.12, 0.12, 3.86, 3.98, T_, grain="x")
        # f2: heavier stacked bracket blocks on the tie beam under the mid purlins (two tiers each side)
        for sy in (-1, 1):
            ztop = roof_under(0.97) - 0.12
            G.box(g, sx * GP - 0.13, sx * GP + 0.13, sy * 0.9 - 0.16, sy * 0.9 + 0.16, 3.30, 3.30 + (ztop - 3.30) * 0.45,
                  T_, grain="y")
            G.box(g, sx * GP - 0.10, sx * GP + 0.10, sy * 0.9 - 0.24, sy * 0.9 + 0.24, 3.30 + (ztop - 3.30) * 0.45,
                  3.30 + (ztop - 3.30) * 0.62, T_, grain="y")
            G.box(g, sx * GP - 0.09, sx * GP + 0.09, sy * 0.9 - 0.10, sy * 0.9 + 0.10, 3.30 + (ztop - 3.30) * 0.62,
                  ztop, T_, grain="z")
        yb_ = GY - (3.30 + 0.02 + UNDER - GATE_EAVE) / TN
        xin = sx * (GP - 0.10)
        tri = [(xin, -yb_, 3.30), (xin, yb_, 3.30), (xin, 0.0, roof_under(0.0) - 0.02)]
        if sx < 0:
            tri = [tri[1], tri[0], tri[2]]
        G.prism(g, tri, (sx, 0, 0), 0.03, T_, frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
        for kb in range(-6, 7):
            yb = kb * 0.26
            ztop_b = roof_under(yb) - 0.03
            if ztop_b - 3.30 < 0.08 or abs(yb) > yb_:
                continue
            G.box(g, min(xin, xin + sx * 0.02), max(xin, xin + sx * 0.02), yb - 0.03, yb + 0.03, 3.30, ztop_b, T_,
                  grain="z")
    # layered eave beams on the front and rear post lines: lower beam, keta, dentil blocks under the keta's outer edge
    for sy in (-1, 1):
        cy = sy * PY
        G.box(g, -3.90, 3.90, cy - 0.09, cy + 0.09, 3.06, 3.20, T_, grain="x")
        G.box(g, -3.95, 3.95, cy - 0.14, cy + 0.14, 3.20, 3.36, T_, grain="x")
        yo0, yo1 = sorted((cy + sy * 0.09, cy + sy * 0.19))
        for k in range(-8, 9):
            x = k * 0.40
            if abs(abs(x) - GP) < 0.3:
                continue
            G.box(g, x - 0.055, x + 0.055, yo0, yo1, 3.10, 3.20, T_, grain="y")
        # keta end blocks past the corner posts
        for sx in (-1, 1):
            G.box(g, min(sx * 3.95, sx * 4.07), max(sx * 3.95, sx * 4.07), cy - 0.16, cy + 0.16, 3.18, 3.36, T_,
                  grain="y")
    # ridge beam and mid purlins (their ends show in the gables)
    G.box(g, -3.95, 3.95, -0.10, 0.10, 3.98, roof_under(0.0) - 0.004, T_, grain="x")
    for sy in (-1, 1):
        G.box(g, -3.95, 3.95, sy * 0.9 - 0.07, sy * 0.9 + 0.07, roof_under(0.97) - 0.12, roof_under(0.97) - 0.004, T_,
              grain="x")
    # lintel over the doors and the side panels (deep), head rail on it
    G.box(g, -3.02, 3.02, -0.80, -0.24, 3.50, 3.85, T_, grain="x")
    # collision
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.hull_box(sx * GP - 0.28, sx * GP + 0.28, sy * PY - 0.28, sy * PY + 0.28, 0.0, 2.70)
        p.hull_box(min(sx * 2.25, sx * 2.625), max(sx * 2.25, sx * 2.625), -0.95, -0.08, 0.0, 3.85)
        p.hull_box(min(sx * 2.625, sx * 3.38), max(sx * 2.625, sx * 3.38), -0.70, -0.30, 0.0, 3.50)
        p.hull_box(sx * GP - 0.11, sx * GP + 0.11, -2.02, 2.02, 3.06, 3.30)
        p.hull_box(sx * GP - 0.09, sx * GP + 0.09, 0.02, 1.57, 0.0, 3.06)           # courtyard-half side panel
        p.hull_box(min(sx * CL_X[0], sx * CL_X[1]), max(sx * CL_X[0], sx * CL_X[1]), -1.08, 0.08, 0.0, 3.06)   # f2 cluster
        # the gable (tie beam up to the roof): nobody climbs into the roof space
        p.hull_pts([(sx * GP - 0.10, -yb_, 3.30), (sx * GP - 0.10, yb_, 3.30), (sx * GP + 0.10, -yb_, 3.30),
                    (sx * GP + 0.10, yb_, 3.30), (sx * GP - 0.10, 0.0, roof_under(0.0)),
                    (sx * GP + 0.10, 0.0, roof_under(0.0))])
    for sy in (-1, 1):
        p.hull_box(-3.95, 3.95, sy * PY - 0.14, sy * PY + 0.14, 3.06, 3.36)
    p.hull_box(-3.02, 3.02, -0.80, -0.24, 3.50, 3.85)
    p.nanite = True
    p.extra = {"passage_headroom_m": 3.06, "door_posts_inner_x": 2.25, "corner_posts": [GP, PY]}
    return p


def gate_leaf():
    """The LEFT leaf: pivot on the hinge axis at the courtyard face, bottom; the leaf runs along +X (local x 0.004 ..
    LEAF_W), its street face at y = -LEAF_TT; it opens by rotating +90 deg (inward). Nothing goes below local x 0
    (the door post's hull) or outside y in [-LEAF_TT, 0]."""
    g = Geo()
    x0, x1 = 0.004, LEAF_W
    H = LEAF_H
    st = 0.14
    yc0, yc1 = -0.16, -0.04          # core (stiles, rails, planks)
    G.box(g, x0, x0 + st, yc0, yc1, 0, H, T_, grain="z")
    G.box(g, x1 - st, x1, yc0, yc1, 0, H, T_, grain="z")
    G.box(g, x0 + st, x1 - st, yc0, yc1, 0, 0.14, T_, grain="x")
    G.box(g, x0 + st, x1 - st, yc0, yc1, H - 0.14, H, T_, grain="x")
    plank_panel(g, x0 + st, x1 - st, yc0 + 0.008, yc1 - 0.008, 0.14, H - 0.14, 8, ch=0.014)
    # street face: three battens with rows of round-head nails
    yo = yc0
    bat = [(0.20, 0.38), (1.62, 1.82), (H - 0.42, H - 0.24)]
    for (za, zb_) in bat:
        G.box(g, x0 + 0.02, x1 - 0.02, yo - 0.04, yo, za, zb_, T_, grain="x")
        for zrow in (za + 0.045, zb_ - 0.045):
            xs = x0 + 0.09
            while xs < x1 - 0.06:
                G.dome(g, (xs, yo - 0.04, zrow), (0, -1, 0), (0, 0, 1), 0.016, IR, nseg=8, rings=2)
                xs += 0.15
    # two long L-shaped strap hinges with spear tips (about 60 % of the leaf), nailed
    ys = yo - 0.012
    for zc in (0.80, 2.55):
        G.box(g, x0 + 0.005, x0 + 0.60 * LEAF_W, ys, yo, zc - 0.045, zc + 0.045, IR, grain="x")
        G.box(g, x0 + 0.02, x0 + 0.11, ys, yo, zc - 0.30, zc + 0.30, IR, grain="z")        # the L's leg
        xt = x0 + 0.60 * LEAF_W
        tip = [(xt - 0.02, ys, zc - 0.07), (xt + 0.20, ys, zc), (xt - 0.02, ys, zc + 0.07), (xt - 0.05, ys, zc)]
        G.prism(g, list(reversed(tip)), (0, -1, 0), 0.012, IR)
        xn = x0 + 0.20
        while xn < xt - 0.05:
            G.dome(g, (xn, ys, zc), (0, -1, 0), (0, 0, 1), 0.021, IR, nseg=8, rings=2)
            xn += 0.22
        for zn in (zc - 0.22, zc + 0.22):
            G.dome(g, (x0 + 0.065, ys, zn), (0, -1, 0), (0, 0, 1), 0.019, IR, nseg=8, rings=2)
        # knuckle round the pintle (inside the hinge stile's footprint: x >= 0)
        G.lathe(g, (0.030, -0.10, zc - 0.10), (0, 0, 1), (1, 0, 0), [(0.0, 0.0), (0.0, 0.026), (0.20, 0.026), (0.20, 0.0)],
                IR, nseg=10)
    # large round studs and a ring knocker at the meeting stile, on the middle batten
    mz = (bat[1][0] + bat[1][1]) / 2
    yb = yo - 0.04
    # f2: a big round boss on a washer plate beside the ring pull, at the meeting stile (the sheet's two bosses)
    # (a low boss: it stands 36 mm proud of the batten, inside the leaf's 0.24 m thickness, so the open leaves keep
    # the 4.0 m clear passage)
    G.lathe(g, (x1 - 0.10, yb, mz), (0, -1, 0), (0, 0, 1), [(0.0, 0.0), (0.0, 0.088), (0.006, 0.088), (0.006, 0.0)],
            IR, nseg=20)
    G.lathe(g, (x1 - 0.10, yb - 0.006, mz), (0, -1, 0), (0, 0, 1),
            [(0.0, 0.068), (0.010, 0.064), (0.020, 0.052), (0.027, 0.034), (0.030, 0.016), (0.031, 0.0)], IR, nseg=20)
    G.dome(g, (x1 - 0.30, yb, mz + 0.04), (0, -1, 0), (0, 0, 1), 0.038, IR, nseg=12, rings=3)
    ring = [(0.012 * math.sin(2 * math.pi * k / 8), 0.062 + 0.011 * math.cos(2 * math.pi * k / 8)) for k in range(8)]
    G.lathe(g, (x1 - 0.30, yb - 0.022, mz - 0.02), (0, -1, 0), (0, 0, 1), ring, IR, nseg=16)
    # courtyard face: three battens with studs and two diagonal braces (the courtyard side is what the 1v1 sees)
    for (za, zb_) in ((0.30, 0.50), (1.60, 1.80), (H - 0.52, H - 0.32)):
        G.box(g, x0 + 0.02, x1 - 0.02, yc1, 0.0, za, zb_, T_, grain="x")
        for zrow in (za + 0.05, zb_ - 0.05):
            xs = x0 + 0.14
            while xs < x1 - 0.1:
                G.dome(g, (xs, -0.012, zrow), (0, 1, 0), (0, 0, 1), 0.012, IR, nseg=8, rings=2)
                xs += 0.36
    for (za, zb_) in ((0.50, 1.60), (1.80, H - 0.52)):
        a = Vector((x0 + 0.12, yc1 / 2, za + 0.06))
        b = Vector((x1 - 0.12, yc1 / 2, zb_ - 0.06))
        ax = (b - a).normalized()
        G.obox(g, (a + b) / 2, ax, (0, 1, 0), ax.cross(Vector((0, 1, 0))), (b - a).length / 2, -yc1 / 2 - 0.002, 0.07, T_)
    return g


def gate_leaves():
    L = Piece("SM_DK_Gate_Leaf_L", "building", "Gatehouse", "left gate leaf, pivot on the hinge axis (opens +90)")
    L.g = gate_leaf()
    L.hull_box(0.0, LEAF_W, -LEAF_TT, 0.0, 0.0, LEAF_H)
    L.nanite = True
    R = Piece("SM_DK_Gate_Leaf_R", "building", "Gatehouse", "right gate leaf, pivot on the hinge axis (opens -90)")
    R.g = G.mirror_x(gate_leaf())
    R.hull_box(-LEAF_W, 0.0, -LEAF_TT, 0.0, 0.0, LEAF_H)
    R.nanite = True
    return [L, R]


def gate_lamp():
    """Bracket lantern (f1: the sheet's lantern): an iron wall plate, a scrolled bracket arm, a tall glazed lantern
    (iron frame, four glass panes, flared base, hipped cap, finial ring). Pivot on the post face at the plate centre;
    the lantern stands out along -Y."""
    p = Piece("SM_DK_Gate_Lamp", "thin", "Gatehouse", "iron bracket lantern, warm emissive glass (x4 on the corner posts)")
    g = p.g
    G.box(g, -0.05, 0.05, -0.02, 0.0, -0.36, 0.26, IR, grain="z")                       # wall plate
    for zz in (-0.30, 0.20):
        G.dome(g, (0, -0.02, zz), (0, -1, 0), (0, 0, 1), 0.016, IR, nseg=8, rings=2)
    # scrolled arm: from the plate out to the hanger, curling down and back under itself
    cen, ups, rad = [], [], []
    for i in range(15):
        t = i / 14
        y = -0.02 - 0.30 * t
        z = 0.20 + 0.05 * math.sin(math.pi * t)
        cen.append(Vector((0, y, z)))
        ups.append(Vector((1, 0, 0)))
        rad.append(0.013)
    G.sweep(g, cen, ups, rad, IR, arc=(0.0, 350.0), nseg=8)
    sc = []
    for i in range(13):
        a = math.pi * 0.5 + 1.7 * math.pi * i / 12
        rr = 0.075 * (1 - 0.45 * i / 12)
        sc.append(Vector((0, -0.12 + rr * math.cos(a), 0.12 + rr * math.sin(a))))
    G.sweep(g, sc, [Vector((1, 0, 0))] * len(sc), [0.010] * len(sc), IR, arc=(0.0, 350.0), nseg=8)
    a, b = Vector((0, -0.02, -0.12)), Vector((0, -0.20, 0.16))
    ax = (b - a).normalized()
    G.obox(g, (a + b) / 2, ax, (1, 0, 0), ax.cross(Vector((1, 0, 0))), (b - a).length / 2, 0.010, 0.010, IR)   # stay
    G.lathe(g, (0, -0.32, 0.13), (0, 0, 1), (1, 0, 0), [(0.0, 0.0), (0.0, 0.012), (0.08, 0.012), (0.08, 0.0)], IR,
            nseg=8)                                                                        # hanger rod
    # the lantern: centre (0, -0.32), body z -0.28 .. 0.06
    cy = -0.32
    G.lathe(g, (0, cy, -0.36), (0, 0, 1), (1, 0, 0), [(0.0, 0.0), (0.0, 0.05), (0.03, 0.11), (0.06, 0.13), (0.08, 0.13),
                                                     (0.08, 0.0)], IR, nseg=4)             # flared base (square)
    for sx in (-1, 1):
        for sy in (-1, 1):
            G.box(g, sx * 0.11 - 0.012, sx * 0.11 + 0.012, cy + sy * 0.11 - 0.012, cy + sy * 0.11 + 0.012, -0.28, 0.06,
                  IR, grain="z")
    G.box(g, -0.10, 0.10, cy - 0.10, cy + 0.10, -0.28, 0.06, LG)                          # glass
    for zz in (-0.28, -0.11, 0.06):
        for sy in (-1, 1):
            G.box(g, -0.12, 0.12, cy + sy * 0.11 - 0.008, cy + sy * 0.11 + 0.008, zz - 0.008, zz + 0.008, IR, grain="x")
        for sx in (-1, 1):
            G.box(g, sx * 0.11 - 0.008, sx * 0.11 + 0.008, cy - 0.12, cy + 0.12, zz - 0.008, zz + 0.008, IR, grain="y")
    G.lathe(g, (0, cy, 0.06), (0, 0, 1), (1, 1, 0), [(0.0, 0.0), (0.0, 0.18), (0.02, 0.18), (0.07, 0.10), (0.10, 0.05),
                                                    (0.11, 0.035), (0.11, 0.0)], IR, nseg=4)   # hipped cap
    ring = [(0.008 * math.sin(2 * math.pi * k / 8), 0.035 + 0.008 * math.cos(2 * math.pi * k / 8)) for k in range(8)]
    G.lathe(g, (0, cy, 0.215), (1, 0, 0), (0, 0, 1), ring, IR, nseg=12)                    # finial ring
    # f2: the sheet's lanterns read bigger: the whole lamp scaled 1.25 about its wall-plate pivot
    k = LAMP_SCALE
    p.g = g.transformed(Matrix.Scale(k, 4))
    p.hull_box(-0.14 * k, 0.14 * k, -0.46 * k, 0.0, -0.40 * k, 0.30 * k)
    p.extra = {"light_local": [0.0, cy * k, -0.11 * k], "scale": k}
    return p


def slab_field(g, rng, x0, x1, y0, y1, top, big=False, moss=0.05, grime=0.35):
    """Granite paving slabs of varied sizes over a rectangle (rows of random depth, random lengths, a few big ones)."""
    y = y0
    while y < y1 - 0.05:
        d = min(rng.uniform(0.40, 0.80 if big else 0.62), y1 - y)
        if y1 - (y + d) < 0.22:
            d = y1 - y
        x = x0
        while x < x1 - 0.05:
            w = min(rng.uniform(0.45, 1.30), x1 - x)
            if x1 - (x + w) < 0.28:
                w = x1 - x
            gp = 0.008
            jj = [rng.uniform(-0.006, 0.006) for _ in range(4)]
            poly = [(x + gp + jj[0], y + gp), (x + w - gp, y + gp + jj[1]), (x + w - gp + jj[2], y + d - gp),
                    (x + gp, y + d - gp + jj[3])]
            G.polystone(g, poly, (0, 0, top - 0.004), (1, 0, 0), (0, 0, 1), 0.10, 0.0, rng.randrange(10 ** 6), GR,
                        chamfer=0.012, bulge=0.004, rough=0.003, step=0.12,
                        moss=(lambda v, j, u, m=moss: clamp01(m + 0.55 * j * (0.4 + 0.6 * (noise.noise(v * 4.0) * 0.5 + 0.5)))),
                        grime=grime)
            x += w
        y += d


def gate_paving():
    rng = random.Random(5)
    p = Piece("SM_DK_Gate_Paving", "ground", "Gatehouse",
              "granite paving of varied slabs: front step +0.05, apron +0.10, threshold +0.10, courtyard side +0.03")
    g = p.g
    slab_field(g, rng, -3.2, 3.2, -3.0, -2.5, 0.05, big=True)
    slab_field(g, rng, -3.9, 3.9, -2.5, -1.25, 0.10)
    slab_field(g, rng, -3.36, 3.36, -1.25, -1.05, 0.10)            # clear of the 1.4 m step piers (|x| > 3.38)
    for sx in (-1, 1):
        a, b = sorted((sx * 2.25, sx * 3.36))
        slab_field(g, rng, a, b, -1.05, -0.95, 0.10)
    # granite threshold: two long stones (flat top +0.10, the closed leaves hang 1 cm over it), moss and grime
    for (xa, xb) in ((-2.24, 0.0), (0.0, 2.24)):
        G.polystone(g, [(xa + 0.006, -1.05), (xb - 0.006, -1.05), (xb - 0.006, -0.55), (xa + 0.006, -0.55)],
                    (0, 0, 0.098), (1, 0, 0), (0, 0, 1), 0.12, 0.0, int(xa * 10) % 97 + 3, GR, chamfer=0.016,
                    bulge=0.0, rough=0.002, step=0.15,
                    moss=lambda v, j, u: clamp01(0.08 + 0.6 * j * (noise.noise(v * 5.0) * 0.5 + 0.5)), grime=0.6)
    slab_field(g, rng, -2.24, 2.24, -0.55, 0.0, 0.03)
    slab_field(g, rng, -3.36, 3.36, 0.0, 0.25, 0.03)
    # r2 (the showcase junction): the courtyard apron stops at Y 2.0, where the sand field's edging boards begin
    # (it lapped 0.4 m over the sand at X 18.1-21 and 23-25.9)
    slab_field(g, rng, -3.9, 3.9, 0.25, APRON_Y1, 0.03)
    # f2 (the sheet's front): a squared step stone in front of each door-post plinth, 0.14 m above the apron
    for sx in (-1, 1):
        xa, xb = sorted((sx * 2.22, sx * 3.02))
        G.rounded_stone(g, ((xa + xb) / 2, -1.20, (0.02 + STEP_TOP) / 2), ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                        ((xb - xa) / 2, 0.22, (STEP_TOP - 0.02) / 2), 0.03, 91 + sx, GR, bulge=0.006, rough=0.006,
                        n=(5, 3, 2), vc=moss_rule(STEP_TOP + 0.05, grime=0.45))
        p.hull_box(xa, xb, -1.42, -0.98, -0.08, STEP_TOP)
    p.hull_box(-3.2, 3.2, -3.0, -2.5, -0.08, 0.05)
    p.hull_box(-3.9, 3.9, -2.5, -1.25, -0.08, 0.10)
    p.hull_box(-3.36, 3.36, -1.25, -0.95, -0.08, 0.10)
    p.hull_box(-2.24, 2.24, -1.05, -0.55, -0.08, 0.10)
    p.hull_box(-2.24, 2.24, -0.55, 0.0, -0.08, 0.03)
    p.hull_box(-3.36, 3.36, 0.0, 0.25, -0.08, 0.03)
    p.hull_box(-3.9, 3.9, 0.25, APRON_Y1, -0.08, 0.03)
    p.nanite = True
    return p


# ------------------------------------------------------------------------------------------------ materials
def build_material(name):
    tex, tile, p = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if tex is None:
        bsdf.inputs["Base Color"].default_value = hexcol(p["color"])
        bsdf.inputs["Roughness"].default_value = p.get("rough", 0.8)
        if "emit" in p:
            bsdf.inputs["Emission Color"].default_value = hexcol(p["emit_color"])
            bsdf.inputs["Emission Strength"].default_value = p["emit"]
        mat.diffuse_color = hexcol(p["color"])
        return mat

    def img(suffix, noncolor, vec=None):
        node = nt.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(TEX / f"T_DK_{tex}_{suffix}.png"), check_existing=True)
        if noncolor:
            image.colorspace_settings.name = "Non-Color"
        node.image = image
        if vec is not None:
            nt.links.new(vec, node.inputs["Vector"])
        return node

    if p.get("world"):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        nsep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], nsep.inputs[0])

        def vec2(a, b):
            c = nt.nodes.new("ShaderNodeCombineXYZ")
            for i, src in enumerate((a, b)):
                m = nt.nodes.new("ShaderNodeMath")
                m.operation = "DIVIDE"
                m.inputs[1].default_value = tile
                nt.links.new(sep.outputs[src], m.inputs[0])
                nt.links.new(m.outputs[0], c.inputs[i])
            return c.outputs[0]

        cols, orms, nrms, ws = [], [], [], []
        for (a, b, nrm_axis) in ((1, 2, 0), (0, 2, 1), (0, 1, 2)):
            v = vec2(a, b)
            cols.append(img("BC", False, v).outputs["Color"])
            orms.append(img("ORM", True, v).outputs["Color"])
            ab = nt.nodes.new("ShaderNodeMath")
            ab.operation = "ABSOLUTE"
            nt.links.new(nsep.outputs[nrm_axis], ab.inputs[0])
            pw = nt.nodes.new("ShaderNodeMath")
            pw.operation = "POWER"
            pw.inputs[1].default_value = 6.0
            nt.links.new(ab.outputs[0], pw.inputs[0])
            ws.append(pw.outputs[0])
        s1 = nt.nodes.new("ShaderNodeMath")
        nt.links.new(ws[0], s1.inputs[0])
        nt.links.new(ws[1], s1.inputs[1])
        s2 = nt.nodes.new("ShaderNodeMath")
        nt.links.new(s1.outputs[0], s2.inputs[0])
        nt.links.new(ws[2], s2.inputs[1])

        def blend3(outs):
            acc = None
            for o, w in zip(outs, ws):
                d = nt.nodes.new("ShaderNodeMath")
                d.operation = "DIVIDE"
                nt.links.new(w, d.inputs[0])
                nt.links.new(s2.outputs[0], d.inputs[1])
                m = nt.nodes.new("ShaderNodeVectorMath")
                m.operation = "SCALE"
                nt.links.new(o, m.inputs[0])
                nt.links.new(d.outputs[0], m.inputs["Scale"])
                if acc is None:
                    acc = m.outputs[0]
                else:
                    ad = nt.nodes.new("ShaderNodeVectorMath")
                    nt.links.new(acc, ad.inputs[0])
                    nt.links.new(m.outputs[0], ad.inputs[1])
                    acc = ad.outputs[0]
            return acc

        bc_out = blend3(cols)
        orm_out = blend3(orms)
        nrm_out = None
        # relief from the normal map's height proxy: the ORM's AO carries cracks and trowel lines (f1: stronger)
        hsep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm_out, hsep.inputs["Color"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(bc_out, bw.inputs[0])
        addh = nt.nodes.new("ShaderNodeMath")
        nt.links.new(bw.outputs[0], addh.inputs[0])
        nt.links.new(hsep.outputs[0], addh.inputs[1])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.45
        bump.inputs["Distance"].default_value = 0.004
        nt.links.new(addh.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UV0"
        bc = img("BC", False, uvn.outputs[0])
        orm = img("ORM", True, uvn.outputs[0])
        nrm = img("N", True, uvn.outputs[0])
        bc_out, orm_out, nrm_out = bc.outputs["Color"], orm.outputs["Color"], nrm.outputs["Color"]
    col = bc_out
    if p.get("tint"):          # f1 EarthCore: the plaster set multiplied by a tint (UE: the MI's Tint parameter)
        tm = nt.nodes.new("ShaderNodeMix")
        tm.data_type = "RGBA"
        tm.blend_type = "MULTIPLY"
        tm.inputs["Factor"].default_value = 1.0
        nt.links.new(col, tm.inputs["A"])
        tm.inputs["B"].default_value = hexcol(p["tint"])          # plaster x tint = the sheet's muddy earth brown
        col = tm.outputs["Result"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    asep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(attr.outputs["Color"], asep.inputs[0])
    if p.get("grime"):
        geo2 = nt.nodes.new("ShaderNodeNewGeometry")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (7.0, 7.0, 0.35)
        nt.links.new(geo2.outputs["Position"], mp.inputs["Vector"])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 2.0
        nz.inputs["Detail"].default_value = 4.0
        nt.links.new(mp.outputs[0], nz.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.35
        mr.inputs["From Max"].default_value = 0.65
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(asep.outputs[1], mul.inputs[0])
        nt.links.new(mr.outputs[0], mul.inputs[1])
        k = nt.nodes.new("ShaderNodeMath")
        k.operation = "MULTIPLY"
        k.inputs[1].default_value = p["grime"]
        nt.links.new(mul.outputs[0], k.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        nt.links.new(k.outputs[0], mix.inputs["Factor"])
        nt.links.new(col, mix.inputs["A"])
        mix.inputs["B"].default_value = hexcol(p.get("grime_color", "#6A5A48"))   # f2: per material (tiles: grey dirt)
        col = mix.outputs["Result"]
    if p.get("moss"):
        mm = nt.nodes.new("ShaderNodeTexImage")
        mimg = bpy.data.images.load(str(TEX / "T_DK_MossMask_M.png"), check_existing=True)
        mimg.colorspace_settings.name = "Non-Color"
        mm.image = mimg
        geo3 = nt.nodes.new("ShaderNodeNewGeometry")
        mp3 = nt.nodes.new("ShaderNodeMapping")
        mp3.inputs["Scale"].default_value = (1.3, 1.3, 1.3)
        nt.links.new(geo3.outputs["Position"], mp3.inputs["Vector"])
        mm.projection = "BOX"
        mm.projection_blend = 0.3
        nt.links.new(mp3.outputs[0], mm.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.10
        mr.inputs["From Max"].default_value = 0.40
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(asep.outputs[0], mul.inputs[0])
        nt.links.new(mm.outputs["Color"], mul.inputs[1])
        nt.links.new(mul.outputs[0], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        nt.links.new(mr.outputs[0], mix.inputs["Factor"])
        nt.links.new(col, mix.inputs["A"])
        mix.inputs["B"].default_value = hexcol("#56613A")
        col = mix.outputs["Result"]
    nt.links.new(col, bsdf.inputs["Base Color"])
    osep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm_out, osep.inputs["Color"])
    if p.get("crest"):     # f2: the round tiles' crests (vertex colour R = 1) get a silver sheen: smoother, more metallic
        rr = nt.nodes.new("ShaderNodeMapRange")
        nt.links.new(asep.outputs[0], rr.inputs["Value"])
        rr.inputs["To Min"].default_value = 1.0
        rr.inputs["To Max"].default_value = 0.62
        rm = nt.nodes.new("ShaderNodeMath")
        rm.operation = "MULTIPLY"
        nt.links.new(osep.outputs[1], rm.inputs[0])
        nt.links.new(rr.outputs[0], rm.inputs[1])
        nt.links.new(rm.outputs[0], bsdf.inputs["Roughness"])
        mm_ = nt.nodes.new("ShaderNodeMapRange")
        nt.links.new(asep.outputs[0], mm_.inputs["Value"])
        mm_.inputs["To Min"].default_value = 0.0
        mm_.inputs["To Max"].default_value = 0.30
        ma = nt.nodes.new("ShaderNodeMath")
        ma.operation = "ADD"
        ma.use_clamp = True
        nt.links.new(osep.outputs[2], ma.inputs[0])
        nt.links.new(mm_.outputs[0], ma.inputs[1])
        nt.links.new(ma.outputs[0], bsdf.inputs["Metallic"])
    else:
        nt.links.new(osep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(osep.outputs[2], bsdf.inputs["Metallic"])
    if nrm_out is not None:
        sn = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(nrm_out, sn.inputs["Color"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sn.outputs[1], inv.inputs[1])
        cmb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sn.outputs[0], cmb.inputs[0])
        nt.links.new(inv.outputs[0], cmb.inputs[1])
        nt.links.new(sn.outputs[2], cmb.inputs[2])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.uv_map = "UV0"
        nt.links.new(cmb.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat.diffuse_color = hexcol(p["tint"]) if p.get("tint") else hexcol({"EarthPlaster": "#B9A488", "Granite": "#8A8680", "RoofTile": "#50565E",
                                "Timber": "#45352A", "Iron": "#3A3937", "EarthCore": "#6C5139"}[tex])
    return mat


# ------------------------------------------------------------------------------------------------ mesh build
def _part_offset(pid, salt=0):
    r = random.Random(pid * 7919 + salt * 104729 + 17)
    return r.uniform(0.0, 1.0), r.uniform(0.0, 1.0)


def _box_uv(co, n, tile):
    """The library's box projection (dojo_materials.box_uv): every face upright and unmirrored seen from outside."""
    ax = max(range(3), key=lambda k: abs(n[k]))
    s = 1.0 if n[ax] >= 0 else -1.0
    if ax == 0:
        u, v = s * co.y, co.z
    elif ax == 1:
        u, v = -s * co.x, co.z
    else:
        u, v = co.x, s * co.y
    return u / tile, v / tile


def build_mesh(piece, coll):
    """r2: UV0 in the library's tile units (every material samples at scale 1):
    - explicit per-vertex UVs where the Geo carries them (the rubble stones on the GraniteRubble texture's own cells);
    - roof tile and the kit's EarthCore: the part's frame projection (as before);
    - granite, rubble core, iron: the library box projection with a random offset PER PART (every stone and every
      iron plate samples its own patch of the tile: per-stone variation);
    - earthen plaster: the library box projection without offsets (continuous inside a piece; Blender previews it in
      world space, Unreal world-aligns it: modules of any length stay continuous);
    - timber: the library's grain_uv (U along each member, end grain on M_DJ_TimberAgedEnd);
    - lamp glass: the library's unit_uv (one hotspot per pane).
    Weathering: the library's bake_wear ('Wear' corner colour: R grime / occlusion, G edge wear on narrow bevels only,
    B ground dirt from the piece's ground level)."""
    g = piece.g
    mats = []
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV0")
    vs = [bm.verts.new(p) for p in g.v]
    bad = 0
    face_mat = []
    face_smooth = []
    for fi, f in enumerate(g.f):
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            bad += 1
            continue
        m = g.fm[fi]
        if m not in mats:
            mats.append(m)
        face.material_index = mats.index(m)
        face_mat.append(m)
        face_smooth.append(g.fsm[fi] if fi < len(g.fsm) else False)
        face.normal_update()
        n = face.normal
        tile = tile_of(m)
        pid = g.fp[fi] if fi < len(g.fp) else 0
        if all(i in g.vuv for i in f):
            for loop, vidx in zip(face.loops, f):
                loop[uvl].uv = g.vuv[vidx]
            continue
        if m in (TL, EC) or m not in LIB:
            fr = g.fr[fi]
            axes = list(fr) if fr is not None else [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
            ni = max(range(3), key=lambda i: abs(n.dot(axes[i])))
            inplane = [i for i in range(3) if i != ni]
            ui = 0 if 0 in inplane else inplane[0]
            vi = [i for i in inplane if i != ui][0]
            U, Vv = axes[ui], axes[vi]
            for loop in face.loops:
                co = loop.vert.co
                loop[uvl].uv = (co.dot(U) / tile, co.dot(Vv) / tile)
            continue
        ou, ov = (0.0, 0.0) if m == EP else _part_offset(pid, sum(map(ord, m)) % 97)
        for loop in face.loops:
            u, v = _box_uv(loop.vert.co, n, tile)
            loop[uvl].uv = (u + ou, v + ov)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    mesh = bpy.data.meshes.new(piece.name)
    bm.to_mesh(mesh)
    bm.free()
    if T_ in mats and TE not in mats:
        mats.append(TE)                     # the end-grain slot (grain_uv moves the end faces onto it)
    for m in mats:
        mesh.materials.append(bpy.data.materials[m])
    if any(face_smooth):        # r2: the hewn stones' faces are smooth-shaded (their chamfers and sides stay flat)
        mesh.polygons.foreach_set("use_smooth", face_smooth)
    obj = bpy.data.objects.new(piece.name, mesh)
    coll.objects.link(obj)
    wood = [i for i, m in enumerate(face_mat) if m == T_]
    if wood:
        djm.grain_uv(obj, "TimberAged", end_set="TimberAgedEnd", faces=wood, end_material_index=mats.index(TE),
                     seed=len(piece.name), uv_map="UV0")
    glass = [i for i, m in enumerate(face_mat) if m == LG]
    if glass:
        djm.unit_uv(obj, faces=glass, uv_map="UV0")
    if TE in mats and not any(p.material_index == mats.index(TE) for p in mesh.polygons):
        # no end faces after all: drop the unused slot
        idx = mats.index(TE)
        mesh.materials.pop(index=idx)
        mats.pop(idx)
    add_uv1(obj)
    wear = djm.bake_wear(obj, ground_z=piece.ground_z)
    obj["wear_bevel_faces"] = wear["bevel_faces"]
    for i, pts in enumerate(piece.hulls):
        hb = bmesh.new()
        hv = [hb.verts.new(Vector(p)) for p in pts]
        bmesh.ops.convex_hull(hb, input=hv)
        for v in [v for v in hb.verts if not v.link_faces]:
            hb.verts.remove(v)
        hm = bpy.data.meshes.new(f"UCX_{piece.name}_{i:02d}")
        hb.to_mesh(hm)
        hb.free()
        h = bpy.data.objects.new(f"UCX_{piece.name}_{i:02d}", hm)
        coll.objects.link(h)
        h.parent = obj
        h.hide_render = True
        h.display_type = "WIRE"
    obj["nanite"] = piece.nanite
    return obj, bad


def fix_lod(obj):
    """After a Collapse decimate: drop faces that make an edge non-manifold (> 2 faces) and re-pack UV1 (decimation
    folds the lightmap islands)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    extra = set()
    for e in bm.edges:
        if len(e.link_faces) > 2:
            for f in sorted(e.link_faces, key=lambda f: f.calc_area())[:len(e.link_faces) - 2]:
                extra.add(f)
    if extra:
        bmesh.ops.delete(bm, geom=list(extra), context="FACES")
    wire = [e for e in bm.edges if not e.link_faces]           # f1: collapse can leave face-less (wire) edges
    if wire:
        bmesh.ops.delete(bm, geom=wire, context="EDGES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    me = obj.data
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0
    obj["lod_fixed_faces"] = len(extra)


def add_uv1(obj):
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


# ------------------------------------------------------------------------------------------------ layout
def place(piece, loc, rot):
    return {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": float(rot)}


def run_module(side, a, L):
    """World pivot + rotation of a module that occupies [a, a + L] along a side's run coordinate."""
    if side == "S":
        return (a, 0.0, 0.0), 0.0
    if side == "N":
        return (a + L, 36.0, 0.0), 180.0
    if side == "W":
        return (0.0, a + L, 0.0), -90.0
    if side == "E":
        return (44.0, a, 0.0), 90.0
    raise ValueError(side)


def flipped(loc, rot, L):
    """The same module turned 180 deg about its centre line (pivot moves to local (L, -1))."""
    R = Matrix.Rotation(math.radians(rot), 4, "Z")
    far = Matrix.Translation(loc) @ R @ Vector((L, -WALL_T, 0.0))
    return (far.x, far.y, 0.0), (rot + 180.0 + 180.0) % 360.0 - 180.0


RUNS = {   # side: list of (start, length) modules, from the grey-box wall runs (the piers cover the joints they hide)
    "S": [(0, 4), (4, 4), (8, 4), (12, 4), (16, 2), (26, 2), (28, 4), (32, 4), (36, 4), (40, 4)],   # f2: straight in
    "N": [(x, 4) for x in range(0, 44, 4)],
    "W": [(0, 4), (4, 4), (8, 4), (12, 4), (16, 4), (20, 4), (24, 2), (26, 1), (27, 1), (28, 4), (32, 4)],
    "E": [(0, 4), (4, 4), (8, 4), (12, 4), (16, 4), (20, 4), (24, 2), (26, 1), (27, 1), (28, 4), (32, 4)],
}
CORNERS = [((0.0, 0.0, 0.0), 0.0), ((44.0, 0.0, 0.0), 90.0), ((44.0, 36.0, 0.0), 180.0), ((0.0, 36.0, 0.0), -90.0)]
GATE_CORNERS = []          # f2: the wall no longer turns beside the gatehouse; it runs straight into the post cluster
# f2: the wall's last 0.5 m each side (the east one turned 180 deg: pivot at the far corner) and the route-6 eave stands
JOINS = [((18.0, 0.0, 0.0), 0.0), ((26.0, -1.0, 0.0), 180.0)]
PIERS = [("SM_DK_Wall_GateJoin", *JOINS[0]), ("SM_DK_Wall_GateJoin", *JOINS[1]),
         ("SM_DK_Wall_StepPier", (-1.0, 26.4, 0.0), 90.0), ("SM_DK_Wall_StepPier", (44.0, 26.4, 0.0), 90.0)]
LEAF_CLOSED = [((GC.x - HINGE_X, HINGE_Y, LEAF_Z), 0.0), ((GC.x + HINGE_X, HINGE_Y, LEAF_Z), 0.0)]
LEAF_OPEN = [((GC.x - HINGE_X, HINGE_Y, LEAF_Z), 90.0), ((GC.x + HINGE_X, HINGE_Y, LEAF_Z), -90.0)]
LAMPS = [((GC.x - GP, -PY - 0.18, 2.35), 0.0), ((GC.x + GP, -PY - 0.18, 2.35), 0.0),
         ((GC.x - GP, PY + 0.18, 2.35), 180.0), ((GC.x + GP, PY + 0.18, 2.35), 180.0)]


def lamp_light_world(loc, rot, local):
    return list(Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot), 4, "Z") @ Vector(local))


def kit1_instances(zb):
    inst = []
    k = 0
    for side, mods in RUNS.items():
        for (a, L) in mods:
            loc, rot = run_module(side, a, L)
            floc, frot = (flipped(loc, rot, L) if k % 2 else (loc, rot))
            inst.append(place(f"SM_DK_WallFooting_{L}m", floc, frot))
            inst.append(place(f"SM_DK_WallBody_{L}m_T200", (loc[0], loc[1], FOOT_H), rot))
            inst.append(place(f"SM_DK_WallCap_{L}m", (loc[0], loc[1], zb["T200"]), rot))
            k += 1
    for loc, rot in CORNERS + GATE_CORNERS:
        inst.append(place("SM_DK_WallFooting_Corner", loc, rot))
        off = Matrix.Rotation(math.radians(rot), 4, "Z") @ Vector((-1.0, 0.0, 0.0))
        inst.append(place("SM_DK_WallBody_1m_T200", (loc[0] + off.x, loc[1] + off.y, FOOT_H), rot))
        inst.append(place("SM_DK_WallCap_Corner", (loc[0], loc[1], zb["T200"]), rot))
    for piece, loc, rot in PIERS:
        inst.append(place(piece, loc, rot))
    inst.append(place("SM_DK_Gate_Frame", tuple(GC), 0.0))
    inst.append(place("SM_DK_Gate_Roof", tuple(GC), 0.0))
    inst.append(place("SM_DK_Gate_Paving", tuple(GC), 0.0))
    inst.append(place("SM_DK_Gate_Leaf_L", *LEAF_CLOSED[0]))
    inst.append(place("SM_DK_Gate_Leaf_R", *LEAF_CLOSED[1]))
    for loc, rot in LAMPS:
        inst.append(place("SM_DK_Gate_Lamp", loc, rot))
    return inst


def roof_z_at(y):
    """The gate roof's collision plane height at |y| (ridge +4.416, eave +3.25)."""
    return zcol_s(min(abs(y), GY))


def route6_study():
    """r2: route 6 with NOTHING outside the gate roof's footprint (X 18-26, Y -2.5..2.5). Measured, not assumed:
    the roof is only reachable across its perimeter; the eaves (+3.25) are the N and S edges, the verges slope
    +3.25 -> +4.42 (GASP cannot mantle onto a slope: GASP_TRAVERSAL.md 4). A flat landing reachable from the wall top
    (+2.0) must be (a) outside the eave line to meet an eave, or (b) under the roof, where a standing capsule (1.72 m)
    needs the roof above it. Returns the numbers for layout.json and BUILD_NOTES."""
    cap_h = 1.72
    # the highest floor a standing capsule fits on under the roof, at each |y| (the rafter underside is lower still)
    rows = []
    for y in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        rows.append({"abs_y": y, "roof_collision_z": round(roof_z_at(y), 3), "rafter_underside_z": round(roof_under(y), 3),
                     "max_standing_floor_z": round(roof_under(y) - cap_h, 3)})
    y_wall_top_limit = GY - ((2.0 + cap_h) - GATE_EAVE + UNDER) / TN     # |y| where a +2.0 floor loses its headroom
    return {"status": "NOT BUILDABLE inside the roof footprint",
            "why": ("every point of the gate roof's plan is under the roof: a landing there has at most "
                    f"{rows[0]['max_standing_floor_z']} m of floor under the ridge (a capsule standing on +2.0 "
                    f"keeps its head clear only to |y| {y_wall_top_limit:.2f}, still {GY - y_wall_top_limit:.2f} m inside "
                    "the eave), so nothing under the roof can put a runner above the eave; a flat landing at +3.25 "
                    "next to an eave has to stand outside the eave line (the grey-box piers and eave pads all stand "
                    "outside their eaves); the verges slope, and the gable's ridge-end tiles top +5.04 (3.04 m over "
                    "the wall top, over GASP's 2.75 m mantle)"),
            "headroom_under_roof": rows, "wall_top_headroom_limit_abs_y": round(y_wall_top_limit, 3),
            "options": ["drop route 6 (the gatehouse roof is then reachable only in the BR, e.g. by the spec's jump "
                        "shortcut, which GASP cannot do onto a slope either)",
                        "re-admit a landing outside the roof, built as architecture (e.g. a stone sleeve pier with a "
                        "flat top +3.25 at a courtyard eave corner): the user's call",
                        "a flat collision band under the N eave tiles plus a climb prop in front of it (the cistern "
                        "pattern of route 4): the prop would stand on the fight floor (Y 2-19), which the spec keeps "
                        "empty"]}


def route6_update(L, roof):
    """r2: the route-6 eave stands are gone (the judge's #1) and route 6 cannot be built with nothing outside the gate
    roof (route6_study). Its markers and climb steps come out of layout.json; the wall-top runs now end at the verge;
    the walk CONTROLs keep proving the wall top does not lead into the gate."""
    markers = [m for m in L["traversal_markers"]
               if m["name"] not in ("Landing_GateRidge_W", "Landing_GateRidge_E", "Landing_Pier_GW", "Landing_Pier_GE")]
    for m in markers:
        if m["name"] in ("Landing_Pier_SW", "Landing_Pier_SE"):
            m["box"] = {"Landing_Pier_SW": [-1.2, 0.2, 26.4, 27.4, 0, PIER_TOP],
                        "Landing_Pier_SE": [43.8, 45.2, 26.4, 27.4, 0, PIER_TOP]}[m["name"]]
    L["climb_routes"] = [r for r in L["climb_routes"] if r["route"] != "6"]
    # r2: the showcase round-2 marker policy (Scripts/dojo/showcase/marker_policy.py) applies here too: the pavilion pad
    # starts at +1.50 (the plinth stance's trace no longer starts inside it) and the grey-box wall-stub markers beside
    # the gate (buried in the gate frame) are gone
    sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "showcase"))
    import marker_policy  # noqa: E402
    markers, rep = marker_policy.apply(markers, L["climb_routes"])
    L["traversal_markers"] = markers
    L.setdefault("kit1_marker_policy", rep)
    wr = L["walk_routes"]
    for k in ("CONTROL_step_pier_under_the_verge", "CONTROL_return_wall_top_into_the_step_block",
              "CONTROL_wall_top_under_the_west_stand_deck", "courtyard_ground_round_the_west_stand",
              "CONTROL_pocket_between_the_west_stand_and_the_gate_side",
              "CONTROL_under_the_west_stand_into_the_pocket"):
        wr.pop(k, None)
    wr["south_wall_top_run_west"] = {"floor_z": 2.0, "points": [[-0.5, -0.5], [17.6, -0.5]],
                                     "note": "r2: the wall-top run ends at the gate verge (no route-6 stand)"}
    wr["south_wall_top_run_east"] = {"floor_z": 2.0, "points": [[44.5, -0.5], [26.4, -0.5]]}
    wr["CONTROL_wall_top_into_gate_pier"] = {"floor_z": 2.0, "points": [[15.0, -0.5], [18.9, -0.5]],
                                             "note": "the wall top ends under the verge at the post cluster"}
    wr["CONTROL_wall_top_into_gate_post_east"] = {"floor_z": 2.0, "points": [[29.0, -0.5], [25.1, -0.5]]}
    wr["courtyard_ground_past_the_gate_corner_west"] = {"floor_z": 0.0, "points": [[16.2, 1.0], [16.2, 3.6], [19.5, 3.6]],
                                                        "note": "r2: the ground beside the gate is open again"}
    wr["gate_open_passage_street_to_courtyard"] = {"floor_z": 0.0, "points": [[22.0, -3.6], [22.0, 3.0]],
                                                   "leaves": "open", "note": "run with the open leaves"}


def lib_materials():
    """The library materials kit 1 uses. M_DJ_PlasterEarth is previewed with the library's box projection reading
    WORLD position (the Unreal recipe world-aligns it), so wall modules of any length stay continuous."""
    for m in LIB:
        if m != EP:
            djm.make_material(m)
            continue
        mat = djm.make_material(EP, projection="BOX", box_blend=0.25)
        nt = mat.node_tree
        tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        for lk in [lk for lk in nt.links if lk.from_node == tc]:
            to = lk.to_socket
            nt.links.remove(lk)
            nt.links.new(geo.outputs["Position"], to)
        mat["dj_preview"] = "world box projection (Unreal: world-aligned)"


# ------------------------------------------------------------------------------------------------ main
REPLACED = {"SM_DGB_Wall_S_W1", "SM_DGB_Wall_S_W2", "SM_DGB_Wall_S_E1", "SM_DGB_Wall_S_E2", "SM_DGB_Wall_W_S",
            "SM_DGB_Wall_W_N", "SM_DGB_Wall_E_S", "SM_DGB_Wall_E_N", "SM_DGB_Wall_N", "SM_DGB_Landing_Pier",
            "SM_DGB_Gatehouse", "SM_DGB_Gate_Leaves", "SM_DGB_Gatehouse_Roof"}


def main():
    t0 = time.time()
    assert_owner("DojoKit", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    grey_layout_path = WORK / "layout_greybox.json"
    if not grey_layout_path.exists():
        raise SystemExit("layout_greybox.json missing (run build_dojo_greybox.py first)")
    GL = json.loads(grey_layout_path.read_text(encoding="utf-8"))
    for name in MATERIALS:
        build_material(name)
    lib_materials()
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    keep = [n for n in GL["pieces"] if n not in REPLACED]
    with bpy.data.libraries.load(str(GREY_BLEND), link=False) as (src, dst):
        wanted = set(keep)
        dst.objects = [n for n in src.objects if n in wanted or any(n.startswith(f"UCX_{k}_") for k in wanted)]
    for o in dst.objects:
        kit.objects.link(o)
    objs = {n: bpy.data.objects[n] for n in keep}
    WP, zb = wall_pieces()
    roof = gate_roof()
    lamp = gate_lamp()
    P = WP + [gate_frame(), roof] + gate_leaves() + [lamp, gate_paving()]
    for p in P:     # r2: bake_wear's ground level per piece (piece space): no ground dirt on caps, roof, lamp
        if p.name.startswith(("SM_DK_WallCap", "SM_DK_Gate_Lamp")):
            p.ground_z = -5.0
        elif p.name in ("SM_DK_Gate_Roof", "SM_DK_Gate_Frame"):
            p.ground_z = 0.0
        elif p.name.startswith("SM_DK_Gate_Leaf"):
            p.ground_z = -LEAF_Z
        elif p.name == "SM_DK_Gate_Paving":
            p.ground_z = -0.25
    build_stats = {}
    for p in P:
        t1 = time.time()
        o, bad = build_mesh(p, kit)
        objs[p.name] = o
        build_stats[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                               "sec": round(time.time() - t1, 2)}
        print("BUILT", p.name, build_stats[p.name])
    # STYLE_GUIDE 7: Nanite on every opaque static piece over about 2k triangles
    for p in P:
        if build_stats[p.name]["tris"] >= 2000 and p.name != "SM_DK_Gate_Lamp":
            p.nanite = True
            objs[p.name]["nanite"] = True
    kit.hide_render = True
    kit.hide_viewport = True
    inst = [dict(i) for i in GL["instances"] if i["piece"] not in REPLACED]
    k1 = kit1_instances(zb)
    pieces_k1 = {p.name: p for p in P}
    for it in k1:
        p = pieces_k1[it["piece"]]
        it.update({"folder": p.folder, "collision_class": p.cls, "note": p.note})
    inst += k1
    for n, it in enumerate(inst):
        o = bpy.data.objects.new(f"{it['piece']}__{n:03d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it.get("rot_z", 0.0)), 4, "Z")
        asm.objects.link(o)
        if it["collision_class"] == "boundary":
            o.hide_render = True
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    L = dict(GL)
    L["pieces"] = {k: v for k, v in GL["pieces"].items() if k not in REPLACED}
    for p in P:
        o = objs[p.name]
        L["pieces"][p.name] = {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                               "tris": build_stats[p.name]["tris"], "slots": [m.name for m in o.data.materials],
                               "nanite": p.nanite, "kit": "kit1", **({"extra": p.extra} if p.extra else {})}
    L["instances"] = inst
    L["materials_kit1"] = {m: {"library": LIB[m], "tile_m": tile_of(m),
                               "textures": [f"Exports/DojoKit/Materials/Textures/T_DJ_{LIB[m]}_{x}.png"
                                            for x in ("BC", "N", "ORM")]} for m in LIB}
    L["materials_kit1"][EC] = {"texture": "EarthCore", "tile_m": 4.0, "kit_only": True,
                               "textures": [f"Exports/DojoKit/Kit1/Textures/T_DK_EarthCore_{x}.png" for x in ("BC", "N", "ORM")]}
    route6_update(L, roof)
    L["kit1"] = {
        "date": "2026-09-28", "round": "r2",
        "cap_height_m": round(CAP_H, 4), "cap_visual_top_m": round(CD["visual_top"], 4),
        "cap_pitch_deg": round(math.degrees(CAP_TH), 2), "cap_noshi0_m": round(CD["noshi0"], 4), "cap_noshi_h_m": NOSHI_H,
        "cap_ridge_roll_above_walk_plane_m": CAP_SINK, "cap_courses": CAP_COURSES,
        "cap_noshi_layers": NOSHI_N,
        "gate_joins": {"piece": "SM_DK_Wall_GateJoin", "placements": [list(j[0]) + [j[1]] for j in JOINS],
                       "world_x": [[18.0, round(18.0 + JOIN_L, 3)], [round(26.0 - JOIN_L, 3), 26.0]], "top": TOPS["T200"]},
        "route6": route6_study(),
        "gate_paving_apron_y1": APRON_Y1,
        "material_library": {"version": djm.VERSION, "materials": sorted(LIB), "kit_only": [EC],
                             "textures": "Exports/DojoKit/Materials/Textures/T_DJ_*",
                             "wear": "'Wear' corner colour from dojo_materials.bake_wear (R grime, G edge, B dirt)",
                             "plaster": "M_DJ_PlasterEarth: world-aligned in Unreal (Blender previews it in world space)"},
        "frame_pier": {"piece": "SM_DK_Wall_FramePier", "placed": False,
                       "note": "kit piece for the BR wall openings; the wickets are solid wall in the 1v1"},
        "cap_eave_overhang_m": CAP_OVER, "body_top_z": zb, "wall_tops": TOPS, "footing_h": FOOT_H,
        "wall_variants": {k: [{"piece": "SM_DK_WallFooting_4m", "z": 0.0},
                              {"piece": f"SM_DK_WallBody_4m_{k}", "z": FOOT_H},
                              {"piece": "SM_DK_WallCap_4m", "z": zb[k]}] for k in TOPS},
        "gate_leaf_placements": {
            "closed": [place("SM_DK_Gate_Leaf_L", *LEAF_CLOSED[0]), place("SM_DK_Gate_Leaf_R", *LEAF_CLOSED[1])],
            "open": [place("SM_DK_Gate_Leaf_L", *LEAF_OPEN[0]), place("SM_DK_Gate_Leaf_R", *LEAF_OPEN[1])]},
        "gate_leaf": {"hinge_local": [HINGE_X, HINGE_Y, LEAF_Z], "width": LEAF_W, "height": LEAF_H,
                      "thickness_total": LEAF_TT},
        "lamp_lights_world": [[round(c, 4) for c in lamp_light_world(loc, rot, lamp.extra["light_local"])]
                              for loc, rot in LAMPS],
        "gate_roof": {"form": "kirizuma (plain gable)", "eave": GATE_EAVE, "ridge_planes_meet": round(ZR, 4),
                      "gable_x_local": GP, "verge_x_local": GX, "pitch_deg": 25.0, **roof.extra},
        "replaced_greybox": sorted(REPLACED),
    }
    K1.mkdir(parents=True, exist_ok=True)
    tmp = WORK / "layout.json.kit1tmp"
    tmp.write_text(json.dumps(L, indent=1), encoding="utf-8")
    import os
    os.replace(tmp, WORK / "layout.json")          # atomic: parallel stages read the grey-box positions from it
    (K1 / "layout_kit1.json").write_text(json.dumps({"pieces": {k: v for k, v in L["pieces"].items() if v.get("kit") == "kit1"},
                                                     "instances": k1, "materials": L["materials_kit1"], "kit1": L["kit1"]},
                                                    indent=1), encoding="utf-8")
    qa = {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    for p in P:
        o = objs[p.name]
        # r2: the lamp is iron (2 m tiles on 1024 px) + unit-UV glass panes: qa_check assumes ONE texture size per
        # object, so its texel figure means nothing there; the library's per-slot texel_density is recorded instead
        tex_target = None if p.name == "SM_DK_Gate_Lamp" else 5.12
        r = qa_check([o], require_uv1=True, texel_density=tex_target, tolerance=0.25)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
        qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                      "tris": r["triangles"].get(p.name), "texel": tex,
                      "texel_library_per_slot": djm.texel_density(o, uv_map="UV0")}
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA kit1: {len(P)} pieces, hard fails {hard_total}")
    for k, v in qa.items():
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:220])
    exp = {}
    if "--no-export" not in ARGS and hard_total == 0:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        kit.hide_viewport = False
        for p in P:
            o = objs[p.name]
            tris = qa[p.name]["tris"]
            if "--no-lods" in ARGS or tris < 400:
                r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [o], kind="static", sidecar=False)
                exp[p.name] = {"lods": 1, "lod_tris": [tris], "warnings": r["warnings"], "objects": r["objects"]}
                continue
            tmpc = bpy.data.collections.new("TmpLOD")
            sc.collection.children.link(tmpc)
            c0 = o.copy()
            c0.data = o.data.copy()
            c0.name = f"{p.name}_LOD0"
            tmpc.objects.link(c0)
            for h in o.children:
                hc = h.copy()
                hc.data = h.data.copy()
                hc.name = h.name.replace(f"UCX_{p.name}_", f"UCX_{p.name}_LOD0_")
                tmpc.objects.link(hc)
                hc.parent = c0
            lods = decimate_lods(c0, (0.5, 0.25))
            for lo in lods:
                fix_lod(lo)
            grp = make_lod_group(p.name, [c0] + lods)
            lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
            lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive]
            r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [grp], kind="static", sidecar=True)
            exp[p.name] = {"lods": 3, "lod_tris": [lq["triangles"].get(x.name) for x in [c0] + lods],
                           "lod_qa_fails": [(c["name"], c["object"], str(c["detail"])[:120]) for c in lod_hard],
                           "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
            for ob in list(tmpc.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(tmpc)
        kit.hide_viewport = True
        (K1 / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
        print(f"exported {len(exp)} FBX to {EXPORT_DIR}")
    (K1 / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    rep = {"pieces": {p.name: {"class": p.cls, "tris": build_stats[p.name]["tris"], "nanite": p.nanite,
                               "ucx": len(p.hulls), "slots": [m.name for m in objs[p.name].data.materials],
                               "lods": exp.get(p.name, {}).get("lod_tris")} for p in P},
           "tris_total_unique": sum(build_stats[p.name]["tris"] for p in P),
           "instances_kit1": len(k1), "instances_total": len(inst), "cap_h": CAP_H, "body_top_z": zb,
           "bad_faces": {k: v["bad_faces"] for k, v in build_stats.items() if v["bad_faces"]},
           "qa_hard_fails": hard_total, "seconds": round(time.time() - t0, 1)}
    (K1 / "kit1_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "seconds", rep["seconds"])


main()
