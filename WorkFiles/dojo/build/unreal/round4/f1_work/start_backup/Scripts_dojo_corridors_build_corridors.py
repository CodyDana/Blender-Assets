"""KIT 5 (part): the two COVERED CORRIDORS (watari-roka) between the outbuildings and the hall, built as BAY MODULES on
the shared roof system (Scripts/dojo/roof/roof_kit.py 1.3.0), the shared mesh module (Scripts/dojo/roof/kit_mesh.py)
and the shared dojo material library (Scripts/dojo/materials). Nothing here edits those modules.

Spec (wins on size): WorkFiles/world/DOJO_ARENA_SPEC.md 4.5 (floor +0.5, roof +3.0 .. +3.7, about 3 m wide, north side
walled). Grey-box (the source of truth for positions, Scripts/dojo/build_dojo_greybox.py): Corridor_W floor X 7.0-11.0,
roof X 7.6-10.5, Y 29.5-32.5, gable along X with eaves +3.0 at Y 29.5 / 32.5 and the ridge +3.70 at Y 31.0; Corridor_E
= its mirror about X 22 (floor X 33.0-37.0, roof X 33.5-36.4). Route 3 (outbuilding roof -> corridor roof -> the hall's
side lower roof) is walk-off drops only (1.22 m and 0.51 m in the grey-box).
Look: References/Dojo/dojo_corridor_ref.png (AI-generated modelling reference, REFERENCE_LOG.md): posts on stone
pedestals over a granite paving course; one long side closed (vertical-board wainscot, rail, cream plaster, head beam);
the other open with a low square-lattice rail; a raised plank floor on an edge beam; a kawara gable roof with plain
rafter ends, a ridge of noshi + cap tiles, a gutter + downpipe on the open eave; an OPEN gable end (tie beam, king
post, ridge purlin, bargeboards) at the hall; the roof tucks under the outbuilding's verge.

Layout (world, metres; the W corridor; E = the mirror about X 22):
  outbuilding gable wall face X 7.0 (grey-box storehouse body X 0-7.0) -> corridor work from X 7.02
  post lines X 7.30 and 10.05 (ONE 2.75 m bay; the sheet's bays are about 2.5 m) at Y 29.85 (open) / 32.15 (closed)
  the roof: S eave Y 29.5, N eave Y 32.5, +3.0; ridge line Y 31.0 at +3.6995 (25 deg); from the outbuilding wall
  (X 7.02, under its verge X 7.0-7.6) to the gable verge X 10.30 (the hall's west gutter starts at X 10.34)
  floor +0.5 from X 7.02 to the hall veranda's edge X 11.0

Pieces (SM_DKC_*; a BAY MODULE = Bay_Floor + Bay_Frame + Bay_Wall + Bay_Roof, all L = 2.75 m from the post line at
local x 0, split by collision class; a run of n bays is closed by one PostFrame; end pieces close the ends):
  Bay_Floor        plank deck on edge beam, sill, joists, centre beam on footing stones, granite paving   ground
  Bay_Frame        the post frame at x 0 (2 posts on granite pedestals, tie beam, king post, bracket arm) +
                   eave beams (keta) both sides, ridge purlin, the open side's lattice rail              thin
  Bay_Wall         the closed side between the posts: board wainscot, rail, plaster, head beam       building
  Bay_Roof         tiles, sarking, rafters, fascia, ridge (noshi + cap tiles), the open eave's gutter  roof
  PostFrame        the closing post frame (as the bay's)                                                 thin
  EndWall_W_Base / _E_Base      floor + closed-wall strip from the post to the outbuilding wall     building
  EndWall_W_Roof / _E_Roof      the roof strip under the outbuilding verge: wall flashing, ridge cap at the wall,
                                gutter end, beam stubs                                               roof
  EndGable_W_Floor / _E_Floor   the deck from the gable post to the hall veranda (X 10.05-11.0)       ground
  EndGable_W_Roof / _E_Roof     the gable overhang: verges + bargeboards, onigawara, gutter end, beam stubs  roof
  Downpipe         from the open eave's gutter at the outbuilding-end post (a swan neck, clamps, shoe)   thin
  (_W = the west corridor's piece; _E = the same piece mirrored in X for the east corridor, built as its own mesh:
   no negative scale in Unreal.)

Run: blender -b --factory-startup --python Scripts/dojo/corridors/build_corridors.py -- [--quick] [--no-export]
     [--no-context]
Out: Assets/Dojo/DojoCorridors.blend (Kit = corridor pieces + the hall blend's compound for the checks, Assembly = the
     compound with the corridors in place of the grey-box corridors), Exports/DojoKit/Corridors/SM_DKC_*.fbx,
     WorkFiles/dojo/build/corridors/{layout_corridors.json, layout_corridors_checks.json, qa_report.json,
     export_report.json, corridors_report.json}
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "roof"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import roof_kit as RK  # noqa: E402
from roof_kit import Geo  # noqa: E402
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402
from kit_mesh import Piece, cbox, geo_to_object, add_uv1, fix_lod, TD, TDE, TA, TAE, GR, PL, IR, TL  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
WORK = ROOT / "WorkFiles" / "dojo" / "build"
CW = WORK / "corridors"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Corridors"
BLEND = ROOT / "Assets" / "Dojo" / "DojoCorridors.blend"
CONTEXT_BLEND = ROOT / "Assets" / "Dojo" / "DojoHall.blend"          # read only: the showcase compound + the hall
CONTEXT_LAYOUT = WORK / "hall" / "layout_hall_checks.json"

# ------------------------------------------------------------------------------------------------ numbers (world)
PITCH = 25.0
TN = math.tan(math.radians(PITCH))
CS = math.cos(math.radians(PITCH))
BO = RK.base_off(PITCH)
UNDER = BO + 0.004 + 0.025 + 0.10          # collision plane -> rafter underside (the hall's rule)
FLOOR = 0.5
EAVE = 3.0
YS, YN, CY = 29.5, 32.5, 31.0              # eave lines and ridge line (grey-box)
RUN = (YN - YS) / 2
ZR = EAVE + RUN * TN                       # +3.6995: the planes meet (grey-box ridge +3.70)
X_OUT = 7.0                                # the outbuilding's gable wall face (grey-box storehouse body X 0-7.0)
X_WALL = X_OUT + 0.02                      # corridor work starts 2 cm off it
X_OUT_VERGE = 7.6                          # the outbuilding roof's verge (grey-box roof X -1.0 .. 7.6)
X0, L = 7.30, 2.75                         # the bay: post line to post line (11 tile pitches of 0.25)
X1 = X0 + L                                # 10.05
X_VERGE = 10.30                            # the gable verge edge (hall side)
X_HALL_EAVE, X_HALL_GUTTER = 10.5, 10.34   # the hall's side lower-roof eave and its gutter's outer face (layout_hall)
X_DECK, X_VERANDA = 10.99, 11.0            # the deck runs to the hall veranda's edge
MIRROR = 22.0                              # E corridor = mirror about X 22 (spec: the compound is mirror-symmetric)
PS, PN = 29.85, 32.15                      # post lines: 0.35 m inside each eave (the sheet's end view overhang)
PW = 0.18                                  # post
P_ = RK.P                                  # tile pitch 0.25


def zplane(y):
    return EAVE + min(y - YS, YN - y) * TN


KETA_H, KETA_W = 0.20, 0.16
KETA_TOP = zplane(PS) - UNDER - 0.004      # eave beam top under the rafters (+2.914)
KETA_BOT = KETA_TOP - KETA_H               # +2.714: 2.21 m over the floor (tie beams too)
PURLIN_H, PURLIN_W = 0.18, 0.15
PURLIN_TOP = ZR - UNDER - 0.004            # ridge purlin under the rafters at the ridge
PED_TOP = 0.26                             # granite pedestal top
DECK_Y0, DECK_Y1 = 29.77, 32.08            # deck boards: the open edge (1 cm over the edge beam) to the wall's inner face
BOARD_T = 0.032
WALL_Y = (32.08, 32.22)                    # the closed wall (centred on the post line PN)
RAIL_Y = (29.80, 29.90)                    # the lattice rail (centred on the post line PS)
RAIL = {"bottom": (FLOOR, 0.57), "top": (1.10, 1.15), "cap": (1.15, 1.19), "cols": 13, "rows": 4}
WALLZ = {"sill": (FLOOR, 0.56), "boards": (0.56, 1.40), "rail": (1.40, 1.48), "plaster": (1.47, 2.53),
         "head": (2.52, KETA_BOT)}
PAVE = {"y": (29.36, 32.64), "top": 0.025, "rows": 9}
S_RIDGE = (RUN - 0.18) / CS                # tile field run up the slope (gable_roof's rule)
C_COURSE, N_COURSE = RK._courses(S_RIDGE)
RIDGE_W, RIDGE_H, RR = (0.36, 0.32), 0.06, 0.085   # two noshi courses + the cap row (the sheet's light ridge)
Z0R = ZR - 0.02                            # noshi base (roof_kit.ridge's rule)
ZBED = ZR - 0.13
KZ = Z0R + RIDGE_H * len(RIDGE_W) + RR * 0.45
RTOP = KZ + RR + 0.016                     # = roof_kit.ridge_top_legacy(ZR, RIDGE_W, RIDGE_H, RR)
RIDGE_HULL_HW = 0.19
ONI = (0.46, 0.52, 0.26)                   # onigawara envelope W x H x T at the gable (plain: no face / crest symbol)
ZG = EAVE - BO - 0.055                     # gutter rim (the hall's rule)
GOFF = 0.09
YG = YS - GOFF                             # the open eave's gutter line (Y 29.41)
DP_Y = 29.58                               # downpipe line: clear of the pedestal (Y 29.65) and 0.135 off the post face
RS_S = RK.RoofSlope((X0, YS), (X0 + 1.0, YS), EAVE, PITCH)    # u = X - X0 (tile rolls at X0 + (k + 0.5) P)
RS_N = RK.RoofSlope((X1, YN), (X1 - 1.0, YN), EAVE, PITCH)    # u = X1 - X (the same roll lines: L = 11 P)
assert abs(L / P_ - round(L / P_)) < 1e-9


def u_of(rs, x):
    return (x - X0) if rs is RS_S else (X1 - x)


# ------------------------------------------------------------------------------------------------ small parts
def frustum(g, cx, cy, z0, z1, h0, h1, mat):
    """A square frustum (pedestal taper): half size h0 at z0 to h1 at z1."""
    v = [(cx - h0, cy - h0, z0), (cx + h0, cy - h0, z0), (cx + h0, cy + h0, z0), (cx - h0, cy + h0, z0),
         (cx - h1, cy - h1, z1), (cx + h1, cy - h1, z1), (cx + h1, cy + h1, z1), (cx - h1, cy + h1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    g.add([Vector(p) for p in v], f, mat, None)
    return g


def member_x(g, xa, xb, yc, w, z0, z1, mat=TD, ch=0.010):
    """A timber member along X (1 mm short of each end: module joints never share a face)."""
    cbox(g, xa + 0.001, xb - 0.001, yc - w / 2, yc + w / 2, z0, z1, mat, ch=ch)


def bracket_arm(g, x, y, z_top, half=0.24, h=0.12, t=0.10):
    """The sheet's bracket arm (hanahijiki) under the eave beam on an open-side post: a flat top, the underside
    curving up to thin tips (a convex profile in the X-Z plane, extruded t across)."""
    A, B = half - 0.10, h - 0.045
    poly = [(x - half, z_top), (x + half, z_top), (x + half, z_top - 0.045)]
    for k in range(1, 6):                       # convex arcs centred inside the arm (prism needs a convex outline)
        a = math.pi / 2 * k / 6
        poly.append((x + 0.10 + A * math.cos(a), z_top - 0.045 - B * math.sin(a)))
    poly += [(x + 0.10, z_top - h), (x - 0.10, z_top - h)]
    for k in range(5, 0, -1):
        a = math.pi / 2 * k / 6
        poly.append((x - 0.10 - A * math.cos(a), z_top - 0.045 - B * math.sin(a)))
    poly.append((x - half, z_top - 0.045))
    pts = [Vector((px, y + t / 2, pz)) for (px, pz) in poly]
    RK.prism(g, pts, (0, 1, 0), t, TD, frame=(Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))))


# ------------------------------------------------------------------------------------------------ floor
def floor_strip(g, hulls, xa, xb, kind="bay"):
    """The raised plank floor from xa to xb: boards along X (+0.5) on a dark backing, the open side's edge beam, the
    closed side's sill (the wall stands on it), joists, the supports under it, and the granite paving at grade.
    kind: 'bay' (a centre beam on two short posts), 'wall' (the strip at the outbuilding wall), 'gable' (the run to the
    hall veranda: short posts under the edge beam and sill near the veranda, an end joist)."""
    rng = random.Random(int(xa * 1000) + 7)
    n = 15
    pitch = (DECK_Y1 - DECK_Y0) / n
    for i in range(n):
        ya = DECK_Y0 + i * pitch
        cbox(g, xa + 0.002, xb - 0.002, ya + 0.0025, ya + pitch - 0.0025, FLOOR - BOARD_T + rng.uniform(-0.002, 0.0),
             FLOOR, TA, ch=0.004)
    cbox(g, xa + 0.003, xb - 0.003, DECK_Y0 + 0.02, DECK_Y1 - 0.01, FLOOR - BOARD_T - 0.016, FLOOR - BOARD_T - 0.004,
         TD, ch=0.002)                                                    # dark backing: the joints show shadow
    eb = (0.30, FLOOR - BOARD_T)
    member_x(g, xa, xb, 29.855, 0.14, eb[0], eb[1])                        # open-side edge beam (posts stand proud)
    member_x(g, xa, xb, (WALL_Y[0] + WALL_Y[1]) / 2, WALL_Y[1] - WALL_Y[0], 0.30, FLOOR)   # closed-side sill
    nj = max(1, int(round((xb - xa) / 0.9)))
    for i in range(nj):
        xc = xa + (xb - xa) * (i + 0.5) / nj
        if kind == "wall":
            xc = xa + 0.06
        cbox(g, xc - 0.045, xc + 0.045, 29.925, WALL_Y[0], 0.36, FLOOR - BOARD_T, TD, ch=0.008)
    if kind == "bay":
        cbox(g, xa + 0.15, xb - 0.15, CY - 0.06, CY + 0.06, 0.24, 0.36, TD, ch=0.01)          # centre beam (obiki)
        for xc in (xa + (xb - xa) / 4, xa + 3 * (xb - xa) / 4):
            cbox(g, xc - 0.045, xc + 0.045, CY - 0.045, CY + 0.045, 0.07, 0.24, TD, ch=0.008)  # short posts
            cbox(g, xc - 0.11, xc + 0.11, CY - 0.11, CY + 0.11, -0.03, 0.07 + rng.uniform(-0.005, 0.005), GR,
                 ch=0.02)
    elif kind == "gable":
        xc = xb - 0.14
        cbox(g, xb - 0.09, xb, 29.925, WALL_Y[0], 0.36, FLOOR - BOARD_T, TD, ch=0.008)         # end joist
        for yc in (29.855, (WALL_Y[0] + WALL_Y[1]) / 2):
            cbox(g, xc - 0.055, xc + 0.055, yc - 0.055, yc + 0.055, 0.07, 0.30, TD, ch=0.008)
            cbox(g, xc - 0.12, xc + 0.12, yc - 0.12, yc + 0.12, -0.03, 0.07, GR, ch=0.02)
    paving(g, xa, xb)
    hulls.append([(x, y, z) for x in (xa, xb) for y in (DECK_Y0, WALL_Y[1]) for z in (0.0, FLOOR)])


def paving(g, xa, xb):
    """Cut granite paving at grade under the corridor (the sheet's paving course): 9 rows across, blocks on a grid
    anchored at the post line X0 (6 per bay), alternate rows offset by half a block; joints 8 mm."""
    y0, y1 = PAVE["y"]
    rows = PAVE["rows"]
    rh = (y1 - y0) / rows
    bl = L / 6
    rng = random.Random(int(xa * 997) + 3)
    for r in range(rows):
        off = 0.5 * bl if r % 2 else 0.0
        k0 = math.floor((xa - X0 - off) / bl) - 1
        k1 = math.ceil((xb - X0 - off) / bl) + 1
        for k in range(k0, k1 + 1):
            a = max(xa, X0 + off + k * bl)
            b = min(xb, X0 + off + (k + 1) * bl)
            if b - a < 0.03:
                continue
            ya, yb = y0 + r * rh, y0 + (r + 1) * rh
            cbox(g, a + 0.004, b - 0.004, ya + 0.004, yb - 0.004, -0.05, PAVE["top"] + rng.uniform(-0.004, 0.003), GR,
                 ch=rng.uniform(0.010, 0.016))


# ------------------------------------------------------------------------------------------------ frame
def post_frame(g, hulls, x):
    """One post frame at X = x: two posts on granite pedestals (base slab + taper), a tie beam across at the eave-beam
    level, a king post up to the ridge purlin, and the bracket arm under the open side's eave beam."""
    for y in (PS, PN):
        cbox(g, x - 0.20, x + 0.20, y - 0.20, y + 0.20, -0.04, 0.06, GR, ch=0.015)
        frustum(g, x, y, 0.06, PED_TOP, 0.17, 0.14, GR)
        cbox(g, x - PW / 2, x + PW / 2, y - PW / 2, y + PW / 2, PED_TOP - 0.01, KETA_BOT + 0.01, TD, ch=0.012)
        hulls.append([(xx, yy, z) for xx in (x - 0.17, x + 0.17) for yy in (y - 0.17, y + 0.17)
                      for z in (0.0, PED_TOP)])
        hulls.append([(xx, yy, z) for xx in (x - PW / 2, x + PW / 2) for yy in (y - PW / 2, y + PW / 2)
                      for z in (PED_TOP, KETA_BOT)])
    cbox(g, x - 0.07, x + 0.07, PS - PW / 2 - 0.06, PN + PW / 2 + 0.06, KETA_BOT + 0.002, KETA_TOP - 0.002, TD,
         ch=0.012)                                                                            # tie beam
    cbox(g, x - 0.07, x + 0.07, CY - 0.07, CY + 0.07, KETA_TOP - 0.01, PURLIN_TOP - PURLIN_H + 0.01, TD, ch=0.01)
    bracket_arm(g, x, PS, KETA_BOT)


def span_members(g, xa, xb):
    """Eave beams (keta) on both post lines and the ridge purlin (munagi), xa -> xb."""
    member_x(g, xa, xb, PS, KETA_W, KETA_BOT, KETA_TOP, ch=0.012)
    member_x(g, xa, xb, PN, KETA_W, KETA_BOT, KETA_TOP, ch=0.012)
    member_x(g, xa, xb, CY, PURLIN_W, PURLIN_TOP - PURLIN_H, PURLIN_TOP, ch=0.012)


def lattice_rail(g, hulls, xa, xb):
    """The open side's low square-lattice rail between two post faces (the sheet: about 13 x 4 openings per bay, a
    bottom rail on the deck, a top rail and a flat cap)."""
    ya, yb = RAIL_Y
    ym = (ya + yb) / 2
    cbox(g, xa, xb, ya, yb, RAIL["bottom"][0], RAIL["bottom"][1], TD, ch=0.008)
    cbox(g, xa, xb, ya, yb, RAIL["top"][0], RAIL["top"][1], TD, ch=0.008)
    cbox(g, xa - 0.004, xb + 0.004, ya - 0.015, yb + 0.015, RAIL["cap"][0], RAIL["cap"][1], TD, ch=0.008)
    z0, z1 = RAIL["bottom"][1], RAIL["top"][0]
    nc, nr = RAIL["cols"], RAIL["rows"]
    for i in range(1, nc):
        xc = xa + (xb - xa) * i / nc
        cbox(g, xc - 0.014, xc + 0.014, ym - 0.014, ym + 0.014, z0 - 0.004, z1 + 0.004, TD, ch=0.003)
    for j in range(1, nr):
        zc = z0 + (z1 - z0) * j / nr
        cbox(g, xa, xb, ym - 0.011, ym + 0.011, zc - 0.012, zc + 0.012, TD, ch=0.003)
    hulls.append([(x, y, z) for x in (xa, xb) for y in (ya - 0.015, yb + 0.015) for z in (FLOOR, RAIL["cap"][1])])


# ------------------------------------------------------------------------------------------------ closed wall
def wall_panel(g, hulls, xa, xb, battens=True):
    """The closed side (alley side, both faces alike) from xa to xb: a bottom rail on the sill, a vertical-board
    wainscot (boards about 12 cm, thin battens on the outer face every 4 boards), a proud rail, cream plaster set back
    between the rails, a head beam under the eave beam (no slot to the sky)."""
    y0, y1 = WALL_Y
    cbox(g, xa, xb, y0 + 0.01, y1 - 0.01, WALLZ["sill"][0], WALLZ["sill"][1], TD, ch=0.006)
    zb0, zb1 = WALLZ["boards"]
    cbox(g, xa, xb, y0 + 0.028, y1 - 0.028, zb0 - 0.004, zb1 + 0.004, TD, ch=0.002)            # board core
    n = max(1, int(round((xb - xa) / 0.12)))
    bw = (xb - xa) / n
    for i in range(n):
        a, b = xa + i * bw + 0.001, xa + (i + 1) * bw - 0.001
        cbox(g, a, b, y1 - 0.030, y1 - 0.010, zb0, zb1, TD, ch=0.0025)                          # outer boards
        cbox(g, a, b, y0 + 0.010, y0 + 0.030, zb0, zb1, TD, ch=0.0025)                          # inner boards
    if battens:
        for i in range(4, n, 4):
            xc = xa + i * bw
            cbox(g, xc - 0.018, xc + 0.018, y1 - 0.012, y1 + 0.004, zb0 + 0.01, zb1 - 0.01, TD, ch=0.003)
    cbox(g, xa, xb, y0 + 0.005, y1 - 0.005, WALLZ["rail"][0], WALLZ["rail"][1], TD, ch=0.008)
    cbox(g, xa, xb, y0 + 0.03, y1 - 0.03, WALLZ["plaster"][0], WALLZ["plaster"][1], PL, ch=0.004)
    cbox(g, xa, xb, y0 + 0.005, y1 - 0.005, WALLZ["head"][0], WALLZ["head"][1] - 0.002, TD, ch=0.008)
    hulls.append([(x, y, z) for x in (xa, xb) for y in (y0, y1) for z in (FLOOR, KETA_BOT)])


# ------------------------------------------------------------------------------------------------ roof
def roll_skips(rs, xa, xb):
    """Tile-roll centres (as u) to leave out: the roll under the wall flashing at the outbuilding wall and the one
    under the verge stack at the gable."""
    out = []
    for k in range(-4, 16):
        xc = X0 + (k + 0.5) * P_
        if not (xa - 0.3 < xc < xb + 0.3):
            continue
        if abs(xc - X_WALL) < 0.24 or abs(xc - X_VERGE) < 0.20:
            out.append(u_of(rs, xc))
    return tuple(out)


def roof_strip(g, xa, xb, wall=False, gable=False):
    """Both slopes of the gable roof over xa -> xb: tiles (rolls on the kit-wide 0.25 m lines from X0), sarking,
    plain rafter ends (the sheet: no iron caps), the fascia; wall=True: a noshi flashing up each slope against the
    outbuilding wall at xa; gable=True: verges with bargeboards at X_VERGE (= xb)."""
    for rs in (RS_S, RS_N):
        ua, ub = sorted((u_of(rs, xa), u_of(rs, xb)))
        RK.tile_field(g, rs.sl, ua, ub, 0.0, S_RIDGE, C_COURSE, RK.TILE, eave=True, phase=0.0, roll_margin=0.0,
                      u_skip=roll_skips(rs, xa, xb))
        RK.sarking(g, rs, ua, ub, -0.04, S_RIDGE + 0.1, nstrips=10)
        n = max(1, int(round((xb - xa) / 0.30)))
        xs = [xa + (xb - xa) * (i + 0.5) / n for i in range(n)]
        RK.rafters(g, rs, 0, 0, -0.07, S_RIDGE, u_list=[u_of(rs, x) for x in xs], caps=False)
        RK.eave_trim(g, rs, ua, ub)
        if wall:
            uf = u_of(rs, X_WALL + 0.12)
            RK.wall_flashing(g, rs.at(uf, 0.03, 0.02), rs.at(uf, S_RIDGE - 0.04, 0.02), rs.sl.N,
                             seed=23 if rs is RS_S else 29)
        if gable:
            RK.verge(g, rs, u_of(rs, X_VERGE), 0.0, S_RIDGE + 0.10, inward=-1 if rs is RS_S else 1, disc=0.085,
                     board=True)
    return g


def ridge_seg(g, xa, xb, cap_a=False, cap_b=False, seed=41):
    """The ridge over xa -> xb: a bed under the bottom course, two courses of real noshi tiles and the round cap-tile
    row (roof_kit.noshi_tiles / cap_row, the round-4 parts; ridge()'s heights for these widths). cap_a / cap_b close
    that end (the outbuilding wall); open ends meet the next module flush."""
    c = Vector(((xa + xb) / 2, CY, (ZBED + Z0R) / 2))
    RK.obox(g, c, (1, 0, 0), (0, 1, 0), (0, 0, 1), (xb - xa) / 2 - 0.001, (RIDGE_W[0] - 0.03) / 2, (Z0R - ZBED) / 2,
            RK.TILE)
    RK.noshi_tiles(g, Vector((xa + 0.001, CY, Z0R)), Vector((xb - 0.001, CY, Z0R)), (0, 0, 1), list(RIDGE_W),
                   [RIDGE_H] * len(RIDGE_W), RK.TILE, seg=0.36, seed=seed, ends=(cap_a, cap_b))
    RK.cap_row(g, Vector((xa + 0.002, CY, KZ)), Vector((xb - 0.002, CY, KZ)), (0, 0, 1), RR, seg=0.30,
               cap_start=cap_a, cap_end=cap_b)


def gutter_seg(g, xa, xb, cap_a=False, cap_b=False):
    RK.gutter(g, [(xa, YG, ZG), (xb, YG, ZG)], fascia_side=(0, 1, 0), caps=(cap_a, cap_b))


def roof_hulls(hulls, xa, xb):
    hulls.append(RK.slab([(xa, YS, EAVE), (xb, YS, EAVE), (xb, CY, ZR), (xa, CY, ZR)]))
    hulls.append(RK.slab([(xb, YN, EAVE), (xa, YN, EAVE), (xa, CY, ZR), (xb, CY, ZR)]))
    hulls.append([(x, y, z) for x in (xa, xb) for y in (CY - RIDGE_HULL_HW, CY + RIDGE_HULL_HW)
                  for z in (ZR - 0.13, RTOP)])


# ------------------------------------------------------------------------------------------------ pieces
def piece(name, cls, note, pivot_x, local_hulls=None):
    p = Piece(name, cls, "Corridors", note, pivot=(pivot_x, CY, 0.0))
    p.kit = "corridors"
    return p


def bay_floor():
    p = piece("SM_DKC_Bay_Floor", "ground",
              "BAY MODULE floor (2.75 m, post line to post line): plank deck +0.5 on the open side's edge beam and the "
              "closed side's sill, joists, a centre beam on two short posts and footing stones, cut granite paving "
              "at grade", X0)
    floor_strip(p.g, p.hulls, X0, X1, "bay")
    return p


def bay_frame():
    p = piece("SM_DKC_Bay_Frame", "thin",
              "BAY MODULE frame: the post frame at local x 0 (two 0.18 m posts on granite pedestals, tie beam, king "
              "post, the open side's bracket arm), eave beams (keta) on both post lines, the ridge purlin, and the open "
              "side's low square-lattice rail between the posts (thin uprights: block the pawn, ignore camera and "
              "visibility)", X0)
    post_frame(p.g, p.hulls, X0)
    span_members(p.g, X0, X1)
    lattice_rail(p.g, p.hulls, X0 + PW / 2 - 0.004, X1 - PW / 2 + 0.004)
    return p


def bay_wall():
    p = piece("SM_DKC_Bay_Wall", "building",
              "BAY MODULE closed side (the alley side) between the posts: bottom rail, vertical-board wainscot with "
              "battens, a proud rail, cream plaster, head beam under the eave beam; both faces alike", X0)
    wall_panel(p.g, p.hulls, X0 + PW / 2 - 0.012, X1 - PW / 2 + 0.012)
    return p


def bay_roof():
    p = piece("SM_DKC_Bay_Roof", "roof",
              "BAY MODULE roof segment (2.75 m): both 25 deg slopes (eaves +3.0 at Y 29.5 / 32.5, the planes meet at "
              "+3.70), kawara tiles on the kit-wide 0.25 m roll lines, sarking, plain rafter ends, fascia, the ridge "
              "(two courses of real noshi tiles + the cap-tile row, open ends meeting the next module), the open "
              "eave's half-round gutter on hooked brackets; one flat collision slab per slope + the ridge box", X0)
    roof_strip(p.g, X0, X1)
    ridge_seg(p.g, X0, X1)
    gutter_seg(p.g, X0, X1)
    roof_hulls(p.hulls, X0, X1)
    p.wear = False
    return p


def post_frame_piece():
    p = piece("SM_DKC_PostFrame", "thin",
              "the post frame that closes a run of bays (as the bay's own at x 0): two posts on granite pedestals, tie "
              "beam, king post, bracket arm", X1)
    post_frame(p.g, p.hulls, X1)
    return p


def end_wall_base_geo():
    g, hulls = Geo(), []
    floor_strip(g, hulls, X_WALL, X0, "wall")
    wall_panel(g, hulls, X_WALL, X0 - PW / 2 + 0.012, battens=False)
    # the closed wall's hull merged with the floor strip's is fine (two hulls); nothing on the open side (the rail
    # starts at the first post, as the sheet)
    return g, hulls


def end_wall_roof_geo():
    g, hulls = Geo(), []
    roof_strip(g, X_WALL, X0, wall=True)
    ridge_seg(g, X_WALL, X0, cap_a=True, seed=43)
    gutter_seg(g, X_WALL + 0.02, X0, cap_a=True)
    span_members(g, X_WALL, X0)
    roof_hulls(hulls, X_WALL, X0)
    return g, hulls


def end_gable_floor_geo():
    g, hulls = Geo(), []
    floor_strip(g, hulls, X1, X_DECK, "gable")
    hulls[-1] = [(x, y, z) for x in (X1, X_VERANDA) for y in (DECK_Y0, WALL_Y[1]) for z in (0.0, FLOOR)]
    return g, hulls


def end_gable_roof_geo():
    g, hulls = Geo(), []
    roof_strip(g, X1, X_VERGE, gable=True)
    oW, oH, oT = ONI
    xe = X_VERGE - 0.02
    # the bay's ridge ends open at X1; the onigawara (plain) stands over that end, its show face at the verge
    RK.obox(g, Vector(((X1 + xe - oT) / 2 + 0.02, CY, (ZBED + Z0R) / 2)), (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (xe - oT - X1) / 2 + 0.04, (RIDGE_W[0] - 0.03) / 2, (Z0R - ZBED) / 2, RK.TILE)
    RK.ridge_end_any(g, Vector((xe - oT / 2, CY, Z0R - 0.08)), (1, 0, 0), oW, oH, oT, "onigawara", RK.TILE,
                     cap_z=KZ - (Z0R - 0.08), cap_r=RR)
    gutter_seg(g, X1, X_VERGE - 0.02, cap_b=True)
    # beam stubs to the gable: the eave beams and the ridge purlin end show in the open gable (the sheet's 3/4 view)
    member_x(g, X1, X_VERGE - 0.05, PS, KETA_W, KETA_BOT, KETA_TOP, ch=0.012)
    member_x(g, X1, X_VERGE - 0.05, PN, KETA_W, KETA_BOT, KETA_TOP, ch=0.012)
    member_x(g, X1, X_VERGE - 0.04, CY, PURLIN_W, PURLIN_TOP - PURLIN_H, PURLIN_TOP, ch=0.012)
    roof_hulls(hulls, X1, X_VERGE)
    return g, hulls


MIRROR_M = Matrix(((-1.0, 0.0, 0.0, 2 * MIRROR), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0)))


def mirrored(g, hulls):
    """The E corridor's copy of a W end piece: geometry mirrored about X 22 (winding reversed, normals stay out), the
    tile UV frames' first axis flipped so the tile texture is not mirrored; hulls mirrored."""
    gm = g.transformed(MIRROR_M, mirror=True)
    gm.fr = [None if fr is None else (-fr[0], fr[1], fr[2]) for fr in gm.fr]
    hm = [[(2 * MIRROR - x, y, z) for (x, y, z) in h] for h in hulls]
    return gm, hm


def end_pieces():
    P = []
    spec = [
        ("EndWall", "Base", "building", end_wall_base_geo, X0,
         "END piece at the outbuilding: the floor strip from the first post to the outbuilding's gable wall (2 cm off "
         "it) and the closed wall's strip there"),
        ("EndWall", "Roof", "roof", end_wall_roof_geo, X0,
         "END piece at the outbuilding: the roof strip that tucks under the outbuilding's verge to its gable wall "
         "(noshi flashing up each slope against the wall, the ridge capped at the wall, the gutter's end), the eave "
         "beam and ridge purlin stubs into the wall"),
        ("EndGable", "Floor", "ground", end_gable_floor_geo, X1,
         "END piece at the hall: the deck from the last post to the hall veranda's edge (X 11.0), an end joist, short "
         "posts on footing stones, paving"),
        ("EndGable", "Roof", "roof", end_gable_roof_geo, X1,
         "END piece at the hall: the open gable overhang (0.25 m past the last post, clear of the hall's side gutter): "
         "verges with round verge rolls, end discs and bargeboards, a plain onigawara (bullnose tiers, arched tile, "
         "plain round crest, cap-end disc, lobes: no face or symbol) on the ridge end, the gutter's end, the eave "
         "beam and ridge purlin ends"),
    ]
    for kind, part, cls, fn, px, note in spec:
        g, hulls = fn()
        pw = Piece(f"SM_DKC_{kind}_W_{part}", cls, "Corridors", note + " (west corridor)", pivot=(px, CY, 0.0))
        pw.g, pw.hulls, pw.kit = g, hulls, "corridors"
        gm, hm = mirrored(g, hulls)
        pe = Piece(f"SM_DKC_{kind}_E_{part}", cls, "Corridors", note + " (east corridor: the west piece mirrored about "
                   "X 22, its own mesh)", pivot=(2 * MIRROR - px, CY, 0.0))
        pe.g, pe.hulls, pe.kit = gm, hm, "corridors"
        if cls == "roof":
            pw.wear = pe.wear = False
        P += [pw, pe]
    return P


def downpipe():
    """Local: the foot at (0, 0, 0) on the pipe axis (world (X0, 29.58) W / (44 - X0, 29.58) E, rot 0: the piece lies
    in its local Y-Z plane, so the same mesh serves both corridors); the outlet in the gutter at local y -0.17; clamps
    toward +Y (the post's outer face)."""
    p = Piece("SM_DKC_Downpipe", "thin", "Corridors",
              "round downpipe from the open eave's gutter at the outbuilding-end post (the sheet's end view): outlet "
              "collar, a two-bend swan neck back toward the post, strap clamps, a shoe at the paving")
    p.local = True
    p.kit = "corridors"
    g = p.g
    dy = YG - DP_Y
    top = ZG - 0.04
    RK.downpipe(g, [(0, dy, top), (0, dy, ZG - 0.24), (0, 0, ZG - 0.62), (0, 0, 0.14)], r=0.045, bend_r=0.14,
                clamps=(0.95, 1.85), clamp_to=(0, 1, 0))
    RK.tube(g, [Vector((0, dy, ZG - 0.075)), Vector((0, dy, ZG - 0.12))], 0.056, IR, cap0=True, cap1=True)
    for z in (0.95, 1.85):                      # flat iron stays from each clamp to the post face (PS - PW / 2)
        cbox(g, -0.011, 0.011, 0.05, PS - PW / 2 - DP_Y + 0.004, z - 0.014, z + 0.014, IR, ch=0.002)
    p.hull_box(-0.05, 0.05, -0.05, 0.05, 0.0, ZG - 0.62)
    p.extra = {"outlet_local": [0.0, round(dy, 4), round(top, 4)]}
    return p


# ------------------------------------------------------------------------------------------------ boards (copied rule)
def calm_boards(obj, seed=4242, jitter=0.035, set_name="TimberDark", deck=False):
    """The hall kit's board rule (Scripts/dojo/hall/build_hall.py calm_boards, copied: a kit never imports the hall
    builder): every board of a panel samples the same window of the timber tile with a small jitter, so a panel
    keeps one tone (no barcode). deck=True: TimberAged deck boards (under 3.5 cm thick, 10-20 cm wide, >= 0.5 m)."""
    me = obj.data
    face_m, end_m = (TA, TAE) if deck else (TD, TDE)
    td = [i for i, m in enumerate(me.materials) if m.name in (face_m, end_m)]
    ends = [i for i, m in enumerate(me.materials) if m.name == end_m]
    if not td or not ends:
        return 0
    end_i = ends[0]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    fset = {f.index for f in bm.faces if f.material_index in td}
    seen, boards_ = set(), []
    for fi in sorted(fset):
        if fi in seen:
            continue
        stack, part = [bm.faces[fi]], []
        seen.add(fi)
        while stack:
            c = stack.pop()
            part.append(c.index)
            for e in c.edges:
                for f2 in e.link_faces:
                    if f2.index in fset and f2.index not in seen:
                        seen.add(f2.index)
                        stack.append(f2)
        vs = [v.co for i in part for v in bm.faces[i].verts]
        dx = max(v.x for v in vs) - min(v.x for v in vs)
        dy = max(v.y for v in vs) - min(v.y for v in vs)
        dz = max(v.z for v in vs) - min(v.z for v in vs)
        if deck:
            if dz <= 0.035 and 0.10 <= min(dx, dy) <= 0.20 and max(dx, dy) >= 0.5:
                boards_.append(part)
        elif dy <= 0.035 and 0.05 <= dx <= 0.20 and dz >= 0.12:
            boards_.append(part)
    bm.free()
    rng = random.Random(seed)
    for part in boards_:
        djm.grain_uv(obj, set_name, end_set=set_name + "End", faces=part, end_material_index=end_i, seed=seed)
        uv = me.uv_layers["UVMap"].data
        du, dv = rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)
        for fi in part:
            for li in me.polygons[fi].loop_indices:
                uv[li].uv = (uv[li].uv[0] + du, uv[li].uv[1] + dv)
    return len(boards_)


# ------------------------------------------------------------------------------------------------ layout
def instances():
    """(piece, loc, rot) for both corridors. Every piece at rot 0: the bay modules and the PostFrame are the same mesh
    in both corridors (a bay's post frame is at its west end in both); the ends are per-corridor meshes."""
    out = []
    for side, xb0 in (("W", X0), ("E", 2 * MIRROR - X1)):
        for part in ("Floor", "Frame", "Wall", "Roof"):
            out.append((f"SM_DKC_Bay_{part}", (xb0, CY, 0.0), 0.0, side))
        out.append(("SM_DKC_PostFrame", (xb0 + L, CY, 0.0), 0.0, side))
    for part in ("Base", "Roof"):
        out.append((f"SM_DKC_EndWall_W_{part}", (X0, CY, 0.0), 0.0, "W"))
        out.append((f"SM_DKC_EndWall_E_{part}", (2 * MIRROR - X0, CY, 0.0), 0.0, "E"))
    for part in ("Floor", "Roof"):
        out.append((f"SM_DKC_EndGable_W_{part}", (X1, CY, 0.0), 0.0, "W"))
        out.append((f"SM_DKC_EndGable_E_{part}", (2 * MIRROR - X1, CY, 0.0), 0.0, "E"))
    out.append(("SM_DKC_Downpipe", (X0, DP_Y, 0.0), 0.0, "W"))
    out.append(("SM_DKC_Downpipe", (2 * MIRROR - X0, DP_Y, 0.0), 0.0, "E"))
    return out


REPLACED = ["SM_DGB_Corridor_W", "SM_DGB_Corridor_W_Roof", "SM_DGB_Corridor_E", "SM_DGB_Corridor_E_Roof"]


def place(piece_, loc, rot, side):
    return {"piece": piece_, "loc": [round(v, 4) for v in loc], "rot_z": float(rot), "corridor": side}


# ------------------------------------------------------------------------------------------------ main
def main():
    t0 = time.time()
    assert_owner("DojoCorridors", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    P = [bay_floor(), bay_frame(), bay_wall(), bay_roof(), post_frame_piece()] + end_pieces() + [downpipe()]
    objs, stats = {}, {}
    for p in P:
        t1 = time.time()
        o, bad = geo_to_object(p, kit)
        o["kit"] = "corridors"
        objs[p.name] = o
        stats[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                         "sec": round(time.time() - t1, 1)}
        print("BUILT", p.name, stats[p.name], flush=True)
    calm = {}
    for p in P:
        o = objs[p.name]
        n = calm_boards(o) if p.cls == "building" or p.name == "SM_DKC_Bay_Wall" else 0
        n2 = calm_boards(o, seed=5151, jitter=0.12, set_name="TimberAged", deck=True) if p.cls in ("ground", "building") \
            else 0
        if n or n2:
            calm[p.name] = [n, n2]
    print("CALM boards", calm, flush=True)
    for p in P:
        p.nanite = stats[p.name]["tris"] >= 2000
        objs[p.name]["nanite"] = p.nanite
    if not QUICK:
        for p in P:
            if p.wear:
                t1 = time.time()
                djm.bake_wear(objs[p.name])
                print("WEAR", p.name, round(time.time() - t1, 1), flush=True)
    # ---- layout (grey-box world frame)
    inst = [place(*i) for i in instances()]
    pieces = {p.name: p for p in P}
    for it in inst:
        p = pieces[it["piece"]]
        it.update({"folder": f"Corridors/{it['corridor']}", "collision_class": p.cls, "kit": "corridors"})
    for n, it in enumerate(inst):
        o = bpy.data.objects.new(f"{it['piece']}__c{n:03d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
        asm.objects.link(o)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    kit.hide_render = True
    kit.hide_viewport = True
    CW.mkdir(parents=True, exist_ok=True)
    numbers = {
        "floor": FLOOR, "eave": EAVE, "eave_lines_y": [YS, YN], "ridge_line_y": CY, "planes_meet": round(ZR, 4),
        "pitch_deg": PITCH, "ridge_cap_top": round(RTOP, 4), "ridge_noshi_base": round(Z0R, 4),
        "ridge_courses": len(RIDGE_W), "ridge_cap_r": RR, "tile_course_m": round(C_COURSE, 4), "courses": N_COURSE,
        "bay_length": L, "post_lines_x_W": [X0, X1], "post_lines_x_E": [round(2 * MIRROR - X1, 4),
                                                                       round(2 * MIRROR - X0, 4)],
        "post_lines_y": [PS, PN], "post": PW, "pedestal_top": PED_TOP,
        "keta": [round(KETA_BOT, 4), round(KETA_TOP, 4)], "tie_beam": [round(KETA_BOT, 4), round(KETA_TOP, 4)],
        "ridge_purlin": [round(PURLIN_TOP - PURLIN_H, 4), round(PURLIN_TOP, 4)],
        "headroom_under_tie_beams_and_keta_m": round(KETA_BOT - FLOOR, 3),
        "rail_top_above_floor_m": round(RAIL["cap"][1] - FLOOR, 3),
        "wall": {k: [round(a, 3), round(b, 3)] for k, (a, b) in WALLZ.items()},
        "roof_x_W": [X_WALL, X_VERGE], "roof_x_E": [round(2 * MIRROR - X_VERGE, 4), round(2 * MIRROR - X_WALL, 4)],
        "roof_hull_x_W": [X_WALL, X_VERGE], "deck_x_W": [X_WALL, X_VERANDA],
        "deck_x_E": [2 * MIRROR - X_VERANDA, round(2 * MIRROR - X_WALL, 4)], "deck_y": [DECK_Y0, WALL_Y[1]],
        "gutter": {"rim_z": round(ZG, 4), "line_y": YG, "x_W": [X_WALL + 0.02, X_VERGE - 0.02]},
        "downpipe_xy": {"W": [X0, DP_Y], "E": [2 * MIRROR - X0, DP_Y]},
        "neighbours": {"outbuilding_wall_x_W": X_OUT, "outbuilding_verge_x_W": X_OUT_VERGE,
                       "hall_side_eave_x_W": X_HALL_EAVE, "hall_side_gutter_outer_face_x_W": X_HALL_GUTTER,
                       "note": "grey-box storehouse/residence (their round-4 builds keep the grey-box body and roof "
                               "planes) and the hall's layout_hall.json; the corridor ends 4 cm short of the hall's "
                               "side gutter and runs under the outbuilding verge to its gable wall"},
        "greybox": {"roof_x_W": [7.6, 10.5], "floor_x_W": [7.0, 11.0], "posts_y": [29.5, 29.7], "wall_y": [32.3, 32.5]},
    }
    LC = {
        "date": "2026-09-29", "stage": "round 4: the two covered corridors (bay modules)",
        "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
        "roof_kit": {"module": "Scripts/dojo/roof/roof_kit.py", "version": RK.VERSION},
        "material_library": "Scripts/dojo/materials (M_DJ_*), textures Exports/DojoKit/Materials/Textures",
        "module_rule": "a corridor = EndWall_<c>_Base + EndWall_<c>_Roof at its outbuilding end, n x (Bay_Floor + "
                       "Bay_Frame + Bay_Wall + Bay_Roof) every 2.75 m from its west post line, one PostFrame at the "
                       "last post line, EndGable_<c>_Floor + EndGable_<c>_Roof at the hall end, a Downpipe at the "
                       "outbuilding-end post; both grey-box gaps take n = 1",
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": stats[p.name]["tris"], "slots": [m.name for m in objs[p.name].data.materials],
                            "nanite": p.nanite, "kit": "corridors",
                            "pivot_world": None if p.local else [round(v, 4) for v in p.pivot],
                            **({"extra": p.extra} if p.extra else {})} for p in P},
        "instances": inst,
        "replaces_greybox": REPLACED,
        "numbers": numbers,
    }
    (CW / "layout_corridors.json").write_text(json.dumps(LC, indent=1), encoding="utf-8")
    # ---- QA + export
    qa, exp = {}, {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    if not QUICK:
        for p in P:
            add_uv1(objs[p.name])
        kit.hide_viewport = False
        for p in P:
            o = objs[p.name]
            ntri = stats[p.name]["tris"]
            r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25,
                         overlap_method="operator" if ntri > 40000 else "sat")
            fails = [c for c in r["checks"] if not c["passed"]]
            hard = [c for c in fails if c["name"] not in waive]
            tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
            qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                          "tris": r["triangles"].get(p.name), "texel_qa": tex,
                          "texel_library_p5_p50_p95": djm.texel_density(o), "ucx": len(p.hulls)}
            print("QA", p.name, len(hard), sorted({c["name"] for c in fails}), flush=True)
        kit.hide_viewport = True
        hard_total = sum(len(v["hard_fails"]) for v in qa.values())
        print(f"QA corridors: {len(P)} pieces, hard fails {hard_total}", flush=True)
        for k, v in qa.items():
            for c in v["hard_fails"]:
                print("  FAIL", k, c["name"], str(c["detail"])[:240])
        (CW / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
        if "--no-export" not in ARGS and hard_total == 0:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            kit.hide_viewport = False
            for p in P:
                o = objs[p.name]
                tris = qa[p.name]["tris"]
                if p.nanite or tris < 400:
                    r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [o], kind="static", sidecar=False)
                    exp[p.name] = {"lods": 1, "lod_tris": [tris], "nanite": p.nanite, "warnings": r["warnings"]}
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
                    fix_lod(lo, clamp_to=c0)
                grp = make_lod_group(p.name, [c0] + lods)
                lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
                lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive | {"texel_density"}]
                r = export_fbx(str(EXPORT_DIR / f"{p.name}.fbx"), [grp], kind="static", sidecar=True)
                exp[p.name] = {"lods": 3, "lod_tris": [lq["triangles"].get(x.name) for x in [c0] + lods],
                               "lod_qa_fails": [(c["name"], c["object"], str(c["detail"])[:120]) for c in lod_hard],
                               "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
                for ob in list(tmpc.objects):
                    bpy.data.objects.remove(ob, do_unlink=True)
                bpy.data.collections.remove(tmpc)
            kit.hide_viewport = True
            (CW / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
            print(f"exported {len(exp)} FBX to {EXPORT_DIR}", flush=True)
    if "--no-context" not in ARGS:
        compose_checks(kit, asm, LC)
    rep = {"calm_boards": calm, "pieces": {p.name: {"class": p.cls, "tris": stats[p.name]["tris"], "nanite": p.nanite,
                                                    "ucx": len(p.hulls), "bad_faces": stats[p.name]["bad_faces"]}
                                           for p in P},
           "tris_total_unique": sum(stats[p.name]["tris"] for p in P),
           "tris_placed": sum(stats[it["piece"]]["tris"] for it in inst),
           "instances": len(inst), "seconds": round(time.time() - t0, 1), "quick": QUICK}
    (CW / "corridors_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "seconds", rep["seconds"], flush=True)


def compose_checks(kit, asm, LC):
    """Load the hall blend's compound (read only: its Kit pieces + UCX and its Assembly instances, i.e. the showcase with
    the hall) minus the grey-box corridors; write layout_corridors_checks.json (layout_hall_checks.json with the
    corridors swapped in, plus corridor walk routes)."""
    if not CONTEXT_BLEND.exists():
        print("no context blend; checks skipped")
        return

    def base_of(name):
        b = name.split("__")[0].split(".")[0]
        if b.startswith("UCX_"):
            b = b[4:].rsplit("_", 1)[0]
        return b

    with bpy.data.libraries.load(str(CONTEXT_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if base_of(n) not in REPLACED and not base_of(n).startswith("SM_DKC_")]
    keep = 0
    for o in dst.objects:
        if o is None:
            continue
        if "__" in o.name:
            asm.objects.link(o)
            keep += 1
        elif o.type in ("MESH", "EMPTY"):
            kit.objects.link(o)
    L_ = json.loads(CONTEXT_LAYOUT.read_text(encoding="utf-8"))
    L_["pieces"] = {k: v for k, v in L_["pieces"].items() if k not in REPLACED}
    for k, v in LC["pieces"].items():
        L_["pieces"][k] = {"class": v["class"], "kit": "corridors", "nanite": v["nanite"], "ucx": v["ucx"]}
    L_["instances"] = [i for i in L_["instances"] if i["piece"] not in REPLACED] + LC["instances"]
    W = L_["walk_routes"]
    E = lambda pts: [[2 * MIRROR - x, y] for x, y in pts]   # noqa: E731
    add = {
        "corridor_W_floor_outbuilding_end_to_the_hall_veranda": (FLOOR, [[7.45, 31.0], [12.0, 31.0]]),
        "corridor_E_floor_outbuilding_end_to_the_hall_veranda": (FLOOR, E([[7.45, 31.0], [12.0, 31.0]])),
        "CONTROL_corridor_W_through_the_closed_wall": (FLOOR, [[8.7, 31.0], [8.7, 33.2]]),
        "CONTROL_corridor_E_through_the_closed_wall": (FLOOR, E([[8.7, 31.0], [8.7, 33.2]])),
        "CONTROL_yard_up_into_corridor_W_over_the_rail": (0.0, [[8.7, 28.9], [8.7, 30.8]]),
        "CONTROL_yard_up_into_corridor_E_over_the_rail": (0.0, E([[8.7, 28.9], [8.7, 30.8]])),
    }
    for k, (fz, pts) in add.items():
        W[k] = {"floor_z": fz, "points": pts}
    L_["stage"] = "corridor kit checks: the showcase with the hall and the corridors (SM_DKC_*) in place of the " \
                  "grey-box corridors"
    L_["corridors"] = LC["numbers"]
    (CW / "layout_corridors_checks.json").write_text(json.dumps(L_, indent=1), encoding="utf-8")
    print("context: assembly instances kept", keep, "layout_corridors_checks.json written", flush=True)


if __name__ == "__main__":
    main()
