"""KITS 3 + 4: the main dojo hall (18 x 10 m body, veranda, step band, two-tier roof) built on the shared roof system
(Scripts/dojo/roof/roof_kit.py), the shared kit mesh module (Scripts/dojo/roof/kit_mesh.py) and the shared dojo
material library (Scripts/dojo/materials/dojo_materials.py).

Spec (wins on size): WorkFiles/world/DOJO_ARENA_SPEC.md 4.4 + the user's decisions of 2026-10-02 (DOJO_QUEUE.md).
Look: References/Dojo/dojo_hall_front_ref.png, dojo_roof_details_ref.png, dojo1_reference2.png (AI-generated modelling
references, REFERENCE_LOG.md). Gameplay numbers: the grey-box's proven ones (build_dojo_greybox.py, layout.json,
GASP_TRAVERSAL.md): lower roof planes eave +3.0 (Y 21.5 / X 10.5 / 33.5) to +4.166 at the walls, upper roof eave +5.5
(0.9 m overhang), 25 deg, eave landing pads X 13.05-14.25 / 29.75-30.95, Y 20.75-21.5, flat top +3.0 (route 4), AC
zones X 15.0-16.2 / 27.8-29.0 on the lower roof (the modern kit's unit, top +5.10) under the walkable upper eave step
(+5.5 at Y 23.1, route 5), veranda +0.5 X 11-33 Y 22-34, a continuous two-step granite band along the front.

Fix round f1 (2026-09-28): the upper roof's front has the hall sheet's raised centre eave (X 17-27, +0.30) framed by
two descending diagonal ridges and a lit lattice frieze under it; banded + strapped ridge / hip caps with low stepped
block-and-disc ends; a chidori-hafu over each side door; plaster gables in a timber frame; closely spaced capped
rafters and frieze boards (no open rafter bays); the wall-head slot closed; full-height lattice doors; the veranda
deck to the wall.

Pieces (SM_DKH_*, grey-box world frame, metres; pivots listed in layout_hall.json):
  StepBand          granite band of two 0.25 m steps (treads 0.35 m) X 11-33 with the wide central stair (X 20-24,
                    treads 0.5 m) inside it                                                  ground
  Veranda           deck boards, edge beams, sleepers, tsuka on footing stones, rubble curb    ground
  VerandaFrame      veranda posts (0.21 m), capital blocks, eave beams (keta), hip rafters     thin (posts only)
  Frame             hall posts (0.24 m), rubble foundation, ground sills, wall plates, lower-roof ledgers; the
                    closed body collision                                                    building
  Bay_Plaster / Bay_Lattice / Bay_Door       2 m wall bays, floor to the head beam          building
  Bay_Transom                                plaster band above the head beam               building
  Bay_ClerePlaster / Bay_ClereFrieze         the band between the roofs (frieze: under the raised centre eave)
  RoofLower_Front / _SideW / _SideE          the veranda lean-to (hips, flashing, gutters)  roof
  RoofChidori_W / _E                         the gable over each side door, on the lower roof roof
  RoofUpper_Front / RoofUpper_Back / RoofUpper_End (west, turned for the east) / RoofUpper_Ridge
                                             the hip-and-gable upper roof                    roof
  Downpipe          round downpipe with a swan neck (front and rear corners)                  thin
  EaveLanding       the route-4 flat eave deck (+3.0) above each cistern                      landing

Run: blender -b --factory-startup --python Scripts/dojo/hall/build_hall.py -- [--quick] [--no-export] [--no-context]
  --quick       no UV1 / QA / export (look iterations)
  --no-context  do not load the showcase compound into the blend (then walk / climb checks cannot run on it)
Out: Assets/Dojo/DojoHall.blend (Kit = hall pieces + the showcase compound's pieces for the checks, Assembly = the
     showcase with the hall in place of the grey-box hall), Exports/DojoKit/Hall/SM_DKH_*.fbx,
     WorkFiles/dojo/build/hall/{layout_hall.json, layout_hall_checks.json, qa_report.json, export_report.json,
     hall_report.json}
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
from roof_kit import Geo  # noqa: E402,F401
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402
from kit_mesh import (Piece, cobox, cbox, member, quad, geo_to_object, add_uv1, fix_lod,  # noqa: E402,F401
                      TD, TDE, TA, TAE, GR, GRR, PL, IR, TL, GL)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
WORK = ROOT / "WorkFiles" / "dojo" / "build"
HW = WORK / "hall"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Hall"
BLEND = ROOT / "Assets" / "Dojo" / "DojoHall.blend"
SHOWCASE_BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"
SHOWCASE_LAYOUT = WORK / "showcase" / "layout_showcase.json"

# ------------------------------------------------------------------------------------------------ numbers (world)
PITCH = 25.0
TN = math.tan(math.radians(PITCH))
CS = math.cos(math.radians(PITCH))
BO = RK.base_off(PITCH)
UNDER = BO + 0.004 + 0.025 + 0.10          # collision plane -> rafter underside
FLOOR = 0.5
BX0, BX1, BY0, BY1 = 13.0, 31.0, 24.0, 34.0
VX0, VX1, VY0 = 11.0, 33.0, 22.0
HP = 0.24                                  # hall post
VP = 0.21                                  # veranda post
VPY, VPXW, VPXE = 22.15, 11.15, 32.85      # veranda post lines
LOW_EAVE, LOW_Y, LOW_XW, LOW_XE = 3.0, 21.5, 10.5, 33.5
UP_EAVE, UP_X0, UP_X1, UP_Y0, UP_Y1 = 5.5, 12.1, 31.9, 23.1, 34.9
AC_TOP = 5.10
PAD = (13.05, 14.25, 20.75, 21.5)          # grey-box eave pad (west); east = +16.7 in X
PAD_DX = 16.7
BAND = {"t1": (21.30, 21.65), "t2": (21.65, 22.0), "stair": (20.0, 24.0), "s1": (21.0, 21.50), "s2": (21.50, 22.0)}


def zlow_front(y):
    return LOW_EAVE + (y - LOW_Y) * TN


def zup_front(y):
    return UP_EAVE + (y - UP_Y0) * TN


KETA_TOP = zlow_front(VPY) - UNDER - 0.004          # veranda eave beam top (under the rafters)
KETA_H = 0.24
KETA_BOT = KETA_TOP - KETA_H
LEDGER_TOP = zlow_front(BY0 - HP / 2) - UNDER - 0.004   # lower-roof ledger on the hall walls
LEDGER_H = 0.18
PLATE_TOP = zup_front(BY0 - HP / 2) - UNDER - 0.006     # upper-roof wall plate
PLATE_H = 0.24
PLATE_BOT = PLATE_TOP - PLATE_H
DOOR_HEAD = 1.90                    # above the floor
KAMOI = (1.90, 2.02)
NAGESHI = (2.02, 2.17)
TRANSOM = (2.17, 3.70)
CLERE = (3.70, PLATE_BOT - FLOOR)   # to the wall plate
GABLE_IN = 2.5                      # round 3: 1.9 -> 2.5 (ridge / eave 0.83 -> 0.77: the hall sheet's front elevation and
                                    # reference 2 measure 0.77-0.78; the side view's upper gable about 1.5 m tall)
# round 3: the upper roof's RAISED CENTRE PLANE (the hall sheet's front + top views): between two diagonal ridges from
# the ridge ends, the centre section X 17-27 is its own plane from the ridge line to a centre eave 0.45 m behind and
# 0.45 m above the outer eave (the sheet: about 15 % of the eave-to-ridge height); the lit frieze fills the wall under
# it up to a raised centre wall plate. The outer wings keep eave +5.5 at Y 23.1 (route 5) and 25 deg.
RECESS = {"x_a": 17.0, "x_b": 27.0, "rise": 0.45, "setback": 0.45, "top_in": 0.35}
UP_ZR = UP_EAVE + (UP_Y1 - UP_Y0) / 2 * TN                 # where the planes meet at the ridge line (+8.2512)
C_YR, C_ZE, C_TN, C_DEG = RK.raised_centre_plane(UP_Y0, (UP_Y0 + UP_Y1) / 2, UP_EAVE, UP_ZR, RECESS["rise"],
                                                 RECESS["setback"])


def zup_centre(y):
    return C_ZE + (y - C_YR) * C_TN


C_UNDER = RK.base_off(C_DEG) + (0.004 + 0.025 + 0.10) / math.cos(math.radians(C_DEG))   # plane -> rafter underside
CPLATE_TOP = zup_centre(BY0 - HP / 2) - C_UNDER + 0.004     # the raised centre wall plate (X 17-27) under its rafters
CPLATE_BOT = CPLATE_TOP - 0.24
FRIEZE_H = 0.55                     # the lit lattice frieze under the raised centre eave (top = the centre wall plate)
CHIDORI = {"x_face": 11.05, "y_c": 27.0, "half_w": 2.20, "pitch": 35.0, "verge_ov": 0.35}   # over the side doors
SIDE_DOOR_Y = (26.0, 28.0)          # the side door bay (under the chidori-hafu; clear of the corridor at Y 29.5-32.5)


# ------------------------------------------------------------------------------------------------ step band
def step_band():
    p = Piece("SM_DKH_StepBand", "ground", "Hall",
              "continuous granite step band along the hall front: two 0.25 m steps (treads 0.35 m) X 11-33, the wide "
              "central stair X 20-24 (treads 0.5 m) inside it; walk up anywhere (user 2026-10-02)",
              pivot=(22.0, 22.0, 0.0))
    g = p.g
    rng = random.Random(11)
    (t1a, t1b), (t2a, t2b) = BAND["t1"], BAND["t2"]
    sx0, sx1 = BAND["stair"]
    (s1a, s1b), (s2a, s2b) = BAND["s1"], BAND["s2"]
    gap = 0.007

    def run_blocks(xa, xb, ya, yb, z0, z1, lmin, lmax, seed):
        r = random.Random(seed)
        x = xa
        while x < xb - 1e-6:
            L = r.uniform(lmin, lmax)
            if xb - (x + L) < lmin * 0.6:
                L = xb - x
            x1 = min(xb, x + L)
            dz = r.uniform(-0.004, 0.004)
            dy = r.uniform(-0.006, 0.006)
            cbox(g, x + gap / 2, x1 - gap / 2, ya + dy, yb, z0, z1 + dz, GR, ch=r.uniform(0.012, 0.02))
            x = x1

    # upper tread (full width, 0.5 top), lower tread either side of the stair, stair blocks
    run_blocks(VX0, sx0, t2a, t2b, -0.06, FLOOR, 0.9, 1.5, 3)
    run_blocks(sx1, VX1, t2a, t2b, -0.06, FLOOR, 0.9, 1.5, 4)
    run_blocks(VX0, sx0, t1a, t1b + 0.02, -0.06, 0.25, 0.9, 1.4, 5)
    run_blocks(sx1, VX1, t1a, t1b + 0.02, -0.06, 0.25, 0.9, 1.4, 6)
    # the central stair: two long blocks per tread, joints staggered (the sheet's three big slabs, two at 0.5 m)
    cbox(g, sx0 + gap / 2, 22.35 - gap / 2, s2a, s2b, -0.06, FLOOR, GR, ch=0.02)
    cbox(g, 22.35 + gap / 2, sx1 - gap / 2, s2a, s2b, -0.06, FLOOR + 0.003, GR, ch=0.02)
    cbox(g, sx0 + gap / 2, 21.55 - gap / 2, s1a, s1b + 0.02, -0.06, 0.25, GR, ch=0.02)
    cbox(g, 21.55 + gap / 2, sx1 - gap / 2, s1a, s1b + 0.02, -0.06, 0.252, GR, ch=0.02)
    _ = rng
    p.hull_box(VX0, VX1, t2a, t2b, 0.0, FLOOR)
    p.hull_box(VX0, sx0, t1a, t1b, 0.0, 0.25)
    p.hull_box(sx1, VX1, t1a, t1b, 0.0, 0.25)
    p.hull_box(sx0, sx1, s1a, s1b, 0.0, 0.25)
    p.hull_box(sx0, sx1, s2a, s2b, 0.0, FLOOR)
    p.wear = True
    return p


# ------------------------------------------------------------------------------------------------ veranda
def veranda():
    p = Piece("SM_DKH_Veranda", "ground", "Hall",
              "veranda (engawa) +0.5, 2 m wide along the front and both sides: deck boards, edge beams, sleepers, "
              "short posts on footing stones, rubble-granite curb along the sides; the boards run to the wall's "
              "skirting face on all three sides (no slot at the wall foot)", pivot=(22.0, 29.0, 0.0))
    g = p.g
    rng = random.Random(21)
    bw, bgap, bt = 0.145, 0.005, 0.032
    top = FLOOR
    # front strip: boards along X, Y 22.0 -> the skirting face (Y 23.915); the last board is ripped to fit
    y_wall = BY0 - 0.085 - 0.003
    y = VY0 + 0.004
    while y < y_wall - 0.03:
        yb_ = min(y + bw, y_wall)
        x = VX0
        first = rng.uniform(1.5, 4.0)
        cuts = [VX0]
        while True:
            x = cuts[-1] + (first if len(cuts) == 1 else rng.uniform(3.0, 4.2))
            if x >= VX1 - 0.8:
                break
            cuts.append(x)
        cuts.append(VX1)
        for a, b in zip(cuts, cuts[1:]):
            cbox(g, a + 0.002, b - 0.002, y, yb_, top - bt + rng.uniform(-0.002, 0.0), top, TA, ch=0.004)
        y += bw + bgap
    # side strips: boards along Y, from the outer edge to the skirting face (X 12.912 / 31.088), the last ripped
    for (xa, xb) in ((VX0, BX0 - 0.085 - 0.003), (BX1 + 0.085 + 0.003, VX1)):
        x = xa + 0.004
        while x < xb - 0.03:
            cuts = [y_wall + 0.004]
            while True:
                yy = cuts[-1] + rng.uniform(2.5, 4.2)
                if yy >= BY1 - 0.8:
                    break
                cuts.append(yy)
            cuts.append(BY1)
            for a, b in zip(cuts, cuts[1:]):
                cbox(g, x, min(x + bw, xb), a + 0.002, b - 0.002, top - bt + rng.uniform(-0.002, 0.0), top, TA,
                     ch=0.004)
            x += bw + bgap
    # round 3 (the measurer's white board joints in Unreal): a dark backing under the boards, so the 5 mm joints show
    # shadow, not the lit gravel below
    cbox(g, VX0 + 0.10, VX1 - 0.10, VY0 + 0.02, y_wall - 0.01, top - bt - 0.016, top - bt - 0.004, TD, ch=0.002)
    for (xa, xb) in ((VX0 + 0.10, BX0 - 0.10), (BX1 + 0.10, VX1 - 0.10)):
        cbox(g, xa, xb, y_wall, BY1 - 0.02, top - bt - 0.016, top - bt - 0.004, TD, ch=0.002)
    # edge beams (engawa-gamachi) under the board ends, sleepers (obiki) under them, tsuka on footing stones
    eb = (top - bt - 0.15, top - bt)
    cbox(g, VX0, VX1, VY0, VY0 + 0.12, eb[0], eb[1], TD, ch=0.01)                    # front (behind the granite)
    for (xa, xb) in ((VX0, VX0 + 0.13), (VX1 - 0.13, VX1)):
        cbox(g, xa, xb, VY0, BY1, eb[0], eb[1], TD, ch=0.012)
    for (xa, xb) in ((VX0, BX0 - HP / 2), (BX1 + HP / 2, VX1)):
        cbox(g, xa, xb, BY1 - 0.13, BY1, eb[0], eb[1], TD, ch=0.012)                 # back ends
    sl = (eb[0] - 0.12, eb[0])
    for xc in (VX0 + 0.35, VX1 - 0.35):
        cbox(g, xc - 0.06, xc + 0.06, VY0 + 0.1, BY1 - 0.1, sl[0], sl[1], TD, ch=0.008)
    cbox(g, VX0 + 0.3, VX1 - 0.3, VY0 + 0.45, VY0 + 0.57, sl[0], sl[1], TD, ch=0.008)
    stones = []
    for xc in (VX0 + 0.35, VX1 - 0.35):
        yy = VY0 + 0.6
        while yy < BY1 - 0.3:
            stones.append((xc, yy))
            yy += 1.0
    xx = VX0 + 1.0
    while xx < VX1 - 0.9:
        stones.append((xx, VY0 + 0.51))
        xx += 1.0
    for (xc, yc) in stones:
        sw = rng.uniform(0.26, 0.32)
        cbox(g, xc - sw / 2, xc + sw / 2, yc - sw / 2, yc + sw / 2, -0.05, 0.10 + rng.uniform(-0.01, 0.01), GR,
             ch=0.03)
        cbox(g, xc - 0.055, xc + 0.055, yc - 0.055, yc + 0.055, 0.10, sl[0], TD, ch=0.008)
    # rubble-granite curb along the side edges (the sheet's rough, mossy base course; darker than the step band)
    for (xa, xb) in ((VX0 + 0.02, VX0 + 0.30), (VX1 - 0.30, VX1 - 0.02)):
        yy = VY0 + 0.02
        while yy < BY1 - 0.05:
            L = min(rng.uniform(0.8, 1.3), BY1 - 0.02 - yy)
            if L < 0.25:
                break
            cbox(g, xa, xb, yy + 0.004, yy + L - 0.004, -0.05, 0.14 + rng.uniform(-0.01, 0.005), GRR,
                 ch=rng.uniform(0.012, 0.02))
            yy += L
    p.hull_box(VX0, VX1, VY0, BY1, 0.0, FLOOR)
    return p


def veranda_frame():
    p = Piece("SM_DKH_VerandaFrame", "thin", "Hall",
              "veranda posts 0.21 m on the 2 m bays (thin uprights: block the pawn, ignore camera and visibility), "
              "capital blocks, eave beams (keta) under the lower roof, hip rafters", pivot=(22.0, 29.0, 0.0))
    g = p.g
    posts = [(VPXW, VPY), (VPXE, VPY)] + [(x, VPY) for x in range(13, 32, 2)]
    for x in (VPXW, VPXE):
        posts += [(x, y) for y in (24.0, 26.0, 28.0, 30.0, 32.0, 33.85)]
    cap = 0.08
    for (x, y) in posts:
        cbox(g, x - VP / 2, x + VP / 2, y - VP / 2, y + VP / 2, 0.10, KETA_BOT - cap, TD, ch=0.012)
        cbox(g, x - 0.14, x + 0.14, y - 0.14, y + 0.14, KETA_BOT - cap, KETA_BOT, TD, ch=0.01)
        # a plain iron base plate where the post meets the deck (the bay close-up)
        cbox(g, x - VP / 2 - 0.012, x + VP / 2 + 0.012, y - VP / 2 - 0.012, y + VP / 2 + 0.012, FLOOR, FLOOR + 0.035,
             IR, ch=0.003)
        p.hull_box(x - VP / 2, x + VP / 2, y - VP / 2, y + VP / 2, FLOOR, KETA_BOT)
    kw = 0.18
    cbox(g, VPXW - 0.2, VPXE + 0.2, VPY - kw / 2, VPY + kw / 2, KETA_BOT, KETA_TOP, TD, ch=0.012)
    for x in (VPXW, VPXE):
        cbox(g, x - kw / 2, x + kw / 2, VPY - 0.2, BY1 + 0.08, KETA_BOT - 0.001, KETA_TOP - 0.001, TD, ch=0.012)
    # hip rafters (sumi-gi) from the eave corner over the corner post to the hall corner, under the hip rolls
    for (xe, xw, sgn) in ((LOW_XW, BX0, 1), (LOW_XE, BX1, -1)):
        a = Vector((xe - sgn * 0.02, LOW_Y - 0.02, LOW_EAVE - UNDER - 0.10))
        b = Vector((xw - sgn * 0.14, BY0 - 0.14, zlow_front(BY0) - UNDER - 0.10))
        member(g, a, b, 0.13, 0.16, TD, ch=0.01)
    p.extra = {"posts": len(posts), "keta_top": round(KETA_TOP, 4), "keta_bottom": round(KETA_BOT, 4),
               "veranda_headroom_at_the_edge_beam_m": round(KETA_BOT - FLOOR, 3)}
    return p


# ------------------------------------------------------------------------------------------------ hall frame
def hall_posts():
    pts = []
    for x in range(13, 32, 2):
        pts += [(float(x), BY0), (float(x), BY1)]
    for x in (BX0, BX1):
        pts += [(x, y) for y in (26.0, 28.0, 30.0, 32.0)]
    return pts


def frame():
    p = Piece("SM_DKH_Frame", "building", "Hall",
              "hall frame: 0.24 m posts on the 2 m bays, rubble-granite foundation, ground sills, skirting, wall "
              "plates, lower-roof ledgers (the upper roof's closely spaced capped rafters cantilever from the plates: "
              "no bracket arms); collision = the closed body (interior closed, user 2026-10-02)",
              pivot=(22.0, 29.0, 0.0))
    g = p.g
    rng = random.Random(31)
    for (x, y) in hall_posts():
        top = CPLATE_BOT if (y == BY0 and RECESS["x_a"] <= x <= RECESS["x_b"]) else PLATE_BOT
        cbox(g, x - HP / 2, x + HP / 2, y - HP / 2, y + HP / 2, 0.35, top, TD, ch=0.014)
    # foundation (rubble granite, 0.40 wide) and ground sill (dodai) round the perimeter, skirting board to the floor
    fw = 0.20
    for (xa, xb, ya, yb) in ((BX0 - fw, BX1 + fw, BY0 - fw, BY0 + fw), (BX0 - fw, BX1 + fw, BY1 - fw, BY1 + fw),
                             (BX0 - fw, BX0 + fw, BY0 + fw, BY1 - fw), (BX1 - fw, BX1 + fw, BY0 + fw, BY1 - fw)):
        horiz = (xb - xa) > (yb - ya)
        a, b = (xa, xb) if horiz else (ya, yb)
        t = a
        while t < b - 1e-6:
            L = min(rng.uniform(0.9, 1.5), b - t)
            if b - (t + L) < 0.4:
                L = b - t
            if horiz:
                cbox(g, t + 0.003, t + L - 0.003, ya, yb, -0.05, 0.20, GRR, ch=0.018)
            else:
                cbox(g, xa, xb, t + 0.003, t + L - 0.003, -0.05, 0.20, GRR, ch=0.018)
            t += L
    sw = 0.13
    cbox(g, BX0 - sw, BX1 + sw, BY0 - sw, BY0 + sw, 0.20, 0.35, TD, ch=0.01)
    cbox(g, BX0 - sw, BX1 + sw, BY1 - sw, BY1 + sw, 0.20, 0.35, TD, ch=0.01)
    cbox(g, BX0 - sw, BX0 + sw, BY0 + sw, BY1 - sw, 0.201, 0.349, TD, ch=0.01)
    cbox(g, BX1 - sw, BX1 + sw, BY0 + sw, BY1 - sw, 0.201, 0.349, TD, ch=0.01)
    # skirting boards between the posts from the sill to the floor (outer faces)
    for (x0, y0, x1, y1, nrm) in ((BX0, BY0, BX1, BY0, (0, -1)), (BX1, BY1, BX0, BY1, (0, 1)),
                                  (BX0, BY1, BX0, BY0, (-1, 0)), (BX1, BY0, BX1, BY1, (1, 0))):
        n = Vector((nrm[0], nrm[1], 0))
        d = (Vector((x1, y1, 0)) - Vector((x0, y0, 0)))
        L = d.length
        d.normalize()
        for i in range(int(round(L / 2))):
            a = Vector((x0, y0, 0)) + d * (2 * i + HP / 2 + 0.002)
            b = Vector((x0, y0, 0)) + d * (2 * i + 2 - HP / 2 - 0.002)
            c = (a + b) / 2 + n * 0.07 + Vector((0, 0, 0.425))
            cobox(g, c, d, n, (0, 0, 1), (b - a).length / 2, 0.015, 0.075, 0.004, TD)
    # wall plates (the upper roof sits on them)
    pw = 0.24
    # front plate: the outer bays at the main plate height; the centre bays (X 17-27) carry a raised plate under the
    # raised centre plane's rafters (round 3), stepping up at the posts X 17 / 27
    xa_, xb_ = RECESS["x_a"], RECESS["x_b"]
    cbox(g, BX0 - 0.30, xa_ + HP / 2, BY0 - pw / 2, BY0 + pw / 2, PLATE_BOT, PLATE_TOP, TD, ch=0.014)
    cbox(g, xb_ - HP / 2, BX1 + 0.30, BY0 - pw / 2, BY0 + pw / 2, PLATE_BOT, PLATE_TOP, TD, ch=0.014)
    cbox(g, xa_ - HP / 2 - 0.10, xb_ + HP / 2 + 0.10, BY0 - pw / 2, BY0 + pw / 2, CPLATE_BOT, CPLATE_TOP, TD, ch=0.014)
    cbox(g, BX0 - 0.30, BX1 + 0.30, BY1 - pw / 2, BY1 + pw / 2, PLATE_BOT, PLATE_TOP, TD, ch=0.014)
    cbox(g, BX0 - pw / 2, BX0 + pw / 2, BY0 - 0.30, BY1 + 0.30, PLATE_BOT - 0.001, PLATE_TOP - 0.002, TD, ch=0.014)
    cbox(g, BX1 - pw / 2, BX1 + pw / 2, BY0 - 0.30, BY1 + 0.30, PLATE_BOT - 0.001, PLATE_TOP - 0.002, TD, ch=0.014)
    # lower-roof ledgers on the front and side walls (the lean-to rafters rest on them)
    lf = BY0 - HP / 2
    cbox(g, BX0 - HP / 2, BX1 + HP / 2, lf - 0.12, lf, LEDGER_TOP - LEDGER_H, LEDGER_TOP, TD, ch=0.01)
    for (x, s) in ((BX0, -1), (BX1, 1)):
        xf = x + s * HP / 2
        xa, xb = sorted((xf, xf + s * 0.12))
        cbox(g, xa, xb, BY0 - HP / 2, BY1 + 0.02, LEDGER_TOP - LEDGER_H - 0.001, LEDGER_TOP - 0.001, TD, ch=0.01)
    # the closed body: one convex hull (hall interior closed in the 1v1)
    p.hull_box(BX0 - HP / 2, BX1 + HP / 2, BY0 - HP / 2, BY1 + HP / 2, 0.0, PLATE_BOT + 0.05)
    p.extra = {"plate_top": round(PLATE_TOP, 4), "plate_bottom": round(PLATE_BOT, 4), "ledger_top": round(LEDGER_TOP, 4),
               "centre_plate": [round(CPLATE_BOT, 4), round(CPLATE_TOP, 4)],
               "posts": len(hall_posts())}
    return p


# ------------------------------------------------------------------------------------------------ wall bays (local)
# local frame: the bay runs along +X from the left post centre (x 0) to the right post centre (x 2); the wall plane is
# y = 0, the outside is -Y; z 0 = the floor (+0.5 world). Instances: front rot 0, back 180, west -90, east +90.
XI0, XI1 = HP / 2, 2.0 - HP / 2


XO0, XO1 = XI0 - 0.012, XI1 + 0.012      # infill spans lap 12 mm into the posts (no zero-width seam to see through)


def panel_boards(g, x0, x1, z0, z1, y_face, t=0.024, w=0.18, mat=TD):
    """A board panel (koshi-ita): vertical boards about w wide laid tight (the joints read as thin dark lines) on a
    backing. calm_boards() gives every board the same tone after the mesh build (no barcode stripes)."""
    n = max(1, int(round((x1 - x0) / w)))
    bw = (x1 - x0) / n
    for i in range(n):
        cbox(g, x0 + i * bw + 0.001, x0 + (i + 1) * bw - 0.001, y_face, y_face + t, z0, z1, mat, ch=0.0025)
    cbox(g, x0, x1, y_face + t - 0.002, y_face + t + 0.02, z0, z1, mat, ch=0.002)


def lattice(g, x0, x1, z0, z1, y_face, cols, rows, bar=0.020, depth=0.026, glow=True, mat=TD):
    """A grid of square bars (kumiko) in the rectangle; a glowing paper panel just behind (opaque, the hall is closed)
    and a dark board behind the paper."""
    for i in range(1, cols):
        x = x0 + (x1 - x0) * i / cols
        cbox(g, x - bar / 2, x + bar / 2, y_face, y_face + depth, z0, z1, mat, ch=0.003)
    for j in range(1, rows):
        z = z0 + (z1 - z0) * j / rows
        cbox(g, x0, x1, y_face + 0.003, y_face + depth - 0.003, z - bar / 2, z + bar / 2, mat, ch=0.003)
    if glow:
        yg = y_face + depth + 0.008
        quad(g, [(x0 - 0.004, yg, z0 - 0.004), (x1 + 0.004, yg, z0 - 0.004), (x1 + 0.004, yg, z1 + 0.004),
                 (x0 - 0.004, yg, z1 + 0.004)], GL)
        cbox(g, x0 - 0.004, x1 + 0.004, yg + 0.004, yg + 0.02, z0 - 0.004, z1 + 0.004, TD, ch=0.002)


def slide_panel(g, xa, xb, yf, stack, t=0.035, fw=0.055, top=None):
    """One sliding door / sash from the sill (z 0.04) to the head track: two stiles, and the rows of `stack` from the
    bottom, each ("rail", h) / ("board", h) / ("lattice", h, cols, rows); the last row runs to the top rail."""
    top = KAMOI[0] if top is None else top
    cbox(g, xa, xa + fw, yf, yf + t, 0.04, top, TD, ch=0.006)
    cbox(g, xb - fw, xb, yf, yf + t, 0.04, top, TD, ch=0.006)
    z = 0.04
    for k, row in enumerate(stack):
        h = row[1] if k < len(stack) - 1 else (top - 0.06 - z)
        if row[0] == "rail":         # rows lap each other by a few mm: no zero-width seam to see through
            cbox(g, xa + fw - 0.004, xb - fw + 0.004, yf, yf + t, z - 0.005, z + h + 0.005, TD, ch=0.006)
        elif row[0] == "board":
            panel_boards(g, xa + fw - 0.004, xb - fw + 0.004, z - 0.004, z + h + 0.004, yf + 0.006, t=0.020, w=0.14)
        else:
            lattice(g, xa + fw - 0.002, xb - fw + 0.002, z, z + h, yf + 0.004, row[2], row[3])
        z += h
    cbox(g, xa + fw - 0.004, xb - fw + 0.004, yf, yf + t, top - 0.065, top, TD, ch=0.006)


def head_beams(g):
    """Head track (kamoi) over the openings and the proud head beam (nageshi). Fix round: the nageshi now has full
    depth back to the kamoi's back face (a filler behind its proud face laps the kamoi and the transom above), so the
    5 cm slot and the open band from the kamoi top to the transom are closed; the kamoi laps the panels below."""
    cbox(g, XO0, XO1, -0.07, 0.07, KAMOI[0] - 0.012, KAMOI[1], TD, ch=0.008)
    cbox(g, 0.0, 2.0, -0.17, -0.105, NAGESHI[0], NAGESHI[1], TD, ch=0.01)
    cbox(g, XO0, XO1, -0.112, 0.07, KAMOI[1] - 0.012, NAGESHI[1] + 0.012, TD, ch=0.004)


def bay_sill(g):
    cbox(g, XO0, XO1, -0.08, 0.08, -0.02, 0.045, TD, ch=0.008)


def bay_plaster():
    p = Piece("SM_DKH_Bay_Plaster", "building", "Hall/Bays",
              "2 m wall bay, floor to head beam: sill, a plain dark vertical-board wainscot (koshi-ita), rail, cream "
              "plaster panel, head track (kamoi), full-depth head beam (nageshi)")
    p.local = True
    g = p.g
    bay_sill(g)
    panel_boards(g, XO0, XO1, 0.04, 0.806, -0.065)
    cbox(g, XO0, XO1, -0.08, 0.06, 0.794, 0.88, TD, ch=0.008)
    cbox(g, XO0, XO1, -0.045, 0.045, 0.87, KAMOI[0] + 0.006, PL, ch=0.004)
    head_beams(g)
    p.hull_box(XI0, XI1, -0.075, 0.075, 0.0, NAGESHI[1])
    return p


def bay_lattice():
    p = Piece("SM_DKH_Bay_Lattice", "building", "Hall/Bays",
              "2 m lattice bay (the sheet's lit lattice bays between the plaster bays): two full-height sliding lattice "
              "panels, each a board foot, a low small-grid lattice strip, a rail and a tall square lattice (kumiko) "
              "with lit paper behind (closed, opaque); head track and head beam")
    p.local = True
    g = p.g
    bay_sill(g)
    w = (XI1 - XI0) / 2 + 0.03
    for k, (xa, yf) in enumerate(((XO0, -0.075), (XO1 - w - 0.012, -0.038))):
        slide_panel(g, xa, xa + w + 0.012, yf,
                    [("rail", 0.06), ("board", 0.12), ("rail", 0.05), ("lattice", 0.23, 8, 2), ("rail", 0.08),
                     ("lattice", 0.0, 6, 11)])
    head_beams(g)
    p.hull_box(XI0, XI1, -0.075, 0.075, 0.0, NAGESHI[1])
    return p


def bay_door():
    p = Piece("SM_DKH_Bay_Door", "building", "Hall/Bays",
              "2 m door bay: two full-height sliding lattice doors (square kumiko over about 70 % of the height with lit "
              "paper behind, a mid rail, a board foot), iron pulls, closed (the hall interior is closed in the 1v1), "
              "head track and head beam")
    p.local = True
    g = p.g
    bay_sill(g)
    w = (XI1 - XI0) / 2 + 0.03
    for k, (xa, yf) in enumerate(((XO0, -0.075), (XO1 - w - 0.012, -0.038))):
        xb = xa + w + 0.012
        slide_panel(g, xa, xb, yf, [("rail", 0.08), ("board", 0.34), ("rail", 0.08), ("lattice", 0.0, 6, 11)])
        # iron pull on the meeting stile (plain plate + recessed grip)
        fw = 0.055
        xs = xb - fw / 2 if k == 0 else xa + fw / 2
        cbox(g, xs - 0.016, xs + 0.016, yf - 0.004, yf, 0.92, 1.08, IR, ch=0.002)
        cbox(g, xs - 0.008, xs + 0.008, yf - 0.009, yf - 0.004, 0.97, 1.03, IR, ch=0.001)
    head_beams(g)
    p.hull_box(XI0, XI1, -0.075, 0.075, 0.0, NAGESHI[1])
    return p


def bay_transom():
    p = Piece("SM_DKH_Bay_Transom", "building", "Hall/Bays",
              "plaster band from the head beam to the band between the roofs (behind the lower roof on the front and "
              "sides)")
    p.local = True
    g = p.g
    cbox(g, XO0, XO1, -0.045, 0.045, TRANSOM[0] - 0.01, TRANSOM[1] + 0.012, PL, ch=0.004)
    cbox(g, XO0, XO1, -0.06, 0.06, TRANSOM[0], TRANSOM[0] + 0.05, TD, ch=0.006)
    p.hull_box(XI0, XI1, -0.045, 0.045, TRANSOM[0], TRANSOM[1])
    return p


def clere_rail(g):
    cbox(g, 0.0, 2.0, -0.08, 0.08, CLERE[0], CLERE[0] + 0.12, TD, ch=0.01)


def bay_clere_plaster():
    p = Piece("SM_DKH_Bay_ClerePlaster", "building", "Hall/Bays",
              "the plaster band between the lower roof and the upper eave: sill rail, cream plaster with a mid rail, "
              "up into the wall plate")
    p.local = True
    g = p.g
    clere_rail(g)
    cbox(g, XO0, XO1, -0.045, 0.045, CLERE[0] + 0.105, CLERE[1] + 0.012, PL, ch=0.004)
    cbox(g, XO0, XO1, -0.06, 0.06, (CLERE[0] + CLERE[1]) / 2 + 0.06, (CLERE[0] + CLERE[1]) / 2 + 0.12, TD, ch=0.006)
    p.hull_box(XI0, XI1, -0.08, 0.08, CLERE[0], CLERE[1])
    return p


def bay_clere_frieze():
    p = Piece("SM_DKH_Bay_ClereFrieze", "building", "Hall/Bays",
              "the band under the upper roof's raised centre eave: sill rail, cream plaster, and a lit lattice frieze "
              "(ranma) strip up to the raised centre wall plate, 14 x 3 small squares with lit paper behind (the "
              "sheet's only lit element between the roofs; round 3: it rises above the outer bays' wall plate, framed "
              "by the raised centre eave)")
    p.local = True
    g = p.g
    clere_rail(g)
    ztop = CPLATE_BOT - FLOOR
    zf0 = ztop - FRIEZE_H
    cbox(g, XO0, XO1, -0.045, 0.045, CLERE[0] + 0.105, zf0 + 0.01, PL, ch=0.004)
    cbox(g, XO0, XO1, -0.07, 0.05, zf0 - 0.02, zf0 + 0.05, TD, ch=0.006)
    cbox(g, XO0, XO1, -0.07, 0.05, ztop - 0.05, ztop + 0.008, TD, ch=0.006)
    lattice(g, XO0, XO1, zf0 + 0.05, ztop - 0.05, -0.058, 14, 3)
    p.hull_box(XI0, XI1, -0.08, 0.08, CLERE[0], ztop)
    return p


def calm_boards(obj, seed=4242, jitter=0.035, set_name="TimberDark", deck=False):
    """The judge's barcode wainscot: grain_uv gives every loose board a random offset into the 4 m timber tile, so
    neighbouring boards land on light and dark areas. Here every board of the wall bays samples the SAME window of the
    tile (one seed) shifted by a small jitter (+-0.035 tile = +-14 cm), so a panel keeps one tone but not one grain.
    Boards = TimberDark loose parts thinner than 3.5 cm, 5-20 cm wide and at least 12 cm tall; deck=True: the veranda's
    TimberAged deck boards (under 3.5 cm thick, 10-20 cm wide, at least 0.5 m long) with a wider jitter."""
    me = obj.data
    face_m, end_m = (TA, TAE) if deck else (TD, TDE)
    td = [i for i, m in enumerate(me.materials) if m.name in (face_m, end_m)]
    end_i = next(i for i, m in enumerate(me.materials) if m.name == end_m)
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


# ------------------------------------------------------------------------------------------------ roofs
def roof_pieces():
    # round 3 ridge / ends / hips (roof sheet panels b + c): two flat noshi, a banded half-round, a flat band and the
    # banded, strapped, riveted crown (crest still about +8.71); ridge ends = the sheet's column of chamfered blocks
    # with an arched, disc-faced top; hips end in the roll's round end tile; a small block at each diagonal's foot
    up = RK.irimoya(UP_X0, UP_X1, UP_Y0, UP_Y1, UP_EAVE, pitch=PITCH, gable_in=GABLE_IN, verge_ov=0.45, overhang=0.9,
                    upturn=0.12, reach=3.2, gable_style="plaster", gable_frame=True, rafter_spacing=0.30,
                    rafter_caps=True, blocking=True, front_recess=RECESS, ridge_layers=(0.52, 0.46),
                    ridge_mid_roll=0.085, ridge_top_layers=(0.36,), rivets=True, oni_style="stack",
                    oni=(0.56, 0.82, 0.46), hip_end="disc", diag_oni=(0.36, 0.42, 0.20))
    lo = RK.lean_to_wrap(LOW_XW, LOW_XE, LOW_Y, BY1, BX0, BX1, BY0, LOW_EAVE, pitch=PITCH, upturn=0.04, reach=2.4,
                         rafter_spacing=0.30, rafter_caps=True, hip_end="disc", rivets=True)
    ch = RK.chidori_hafu(CHIDORI["x_face"], CHIDORI["y_c"], CHIDORI["half_w"], LOW_XW, LOW_EAVE, BX0 - HP / 2,
                         main_pitch=PITCH, pitch=CHIDORI["pitch"], verge_ov=CHIDORI["verge_ov"], gable_style="plaster",
                         oni_style="stack", rivets=True)
    che = RK.chidori_hafu(CHIDORI["x_face"], CHIDORI["y_c"], CHIDORI["half_w"], LOW_XW, LOW_EAVE, BX0 - HP / 2,
                          main_pitch=PITCH, pitch=CHIDORI["pitch"], verge_ov=CHIDORI["verge_ov"],
                          gable_style="plaster", mirror_about_x=22.0, oni_style="stack", rivets=True)
    piv = (22.0, 29.0, 0.0)
    P = []
    spec = [("SM_DKH_RoofUpper_Front", up["slope_front"], up["hulls"]["slope_front"],
             "upper hip-and-gable roof, front slope: the outer wings on the main plane (eave +5.5 at Y 23.1, 25 deg); "
             "between two banded, strapped diagonal ridges from the ridge ends, the raised centre plane X 17-27 (its "
             "eave 0.45 m behind and 0.45 m above the outer eave, on the same ridge line) over the lit frieze, tile "
             "cheeks under the diagonals, a small block at each diagonal's foot; verge overhangs, "
             "banded verges, bargeboards, soffit, closely spaced rafters with X-marked iron caps, frieze boards over "
             "the wall line, fascia"),
            ("SM_DKH_RoofUpper_Back", up["slope_back"], up["hulls"]["slope_back"],
             "upper roof, back slope: the plain main slope (no centre recess; the references never show the back)"),
            ("SM_DKH_RoofUpper_End", up["end_w"], up["hulls"]["end_w"],
             "upper roof end: the hip slope, both hips (banded strapped caps, stepped disc end blocks), the gable-foot "
             "flashing and the gable (cream plaster in a timber frame: tie beam, beam, studs, king post); placed "
             "twice (west, and turned 180 deg for the east)"),
            ("SM_DKH_RoofUpper_Ridge", up["ridge"], up["hulls"]["ridge"],
             "upper roof ridge (roof sheet panel b): bed, two flat noshi, a banded half-round, a flat band, a banded "
             "round crown with a riveted iron strap every 0.40 m; the ridge ends are the sheet's column of chamfered "
             "blocks with an arched, disc-faced top and two round roll ends"),
            ("SM_DKH_RoofLower_Front", lo["front"], lo["hulls"]["front"],
             "lower (veranda) roof, front: eave +3.0 at Y 21.5, 25 deg to +4.166 at the wall, banded strapped hips "
             "with disc end blocks at the corners, wall flashing, soffit + capped rafters, the front gutter"),
            ("SM_DKH_RoofLower_SideW", lo["side_w"], lo["hulls"]["side_w"],
             "lower roof, west side: eave +3.0 at X 10.5, verge + end board at the back, wall flashing, the gutter"),
            ("SM_DKH_RoofLower_SideE", lo["side_e"], lo["hulls"]["side_e"],
             "lower roof, east side (mirror of the west)"),
            ("SM_DKH_RoofChidori_W", ch["geo"], ch["hulls"],
             "chidori-hafu on the west lower roof over the side door (Y 26-28): a 35 deg front-facing gable, plaster "
             "tympanum in a timber frame, bargeboards with a hanging board, banded verges with discs, a small ridge "
             "with a stepped disc end, iron valley flashings; one walkable hull"),
            ("SM_DKH_RoofChidori_E", che["geo"], che["hulls"],
             "chidori-hafu on the east lower roof (the west one mirrored about X 22)")]
    gz, go = lo["gutter_z"], lo["gutter_off"]
    for name, g, hulls, note in spec:
        pc = Piece(name, "roof", "Hall/Roof", note, pivot=piv)
        pc.g = g
        pc.hulls = hulls
        pc.wear = False
        pc.nanite = True
        P.append(pc)
    gut = {p_.name: p_ for p_ in P}
    RK.gutter(gut["SM_DKH_RoofLower_Front"].g, lo["gutter"]["f"], fascia_side=(0, 1, 0), caps=(False, False))
    RK.gutter(gut["SM_DKH_RoofLower_SideW"].g, lo["gutter"]["w"], fascia_side=(1, 0, 0), caps=(True, False))
    RK.gutter(gut["SM_DKH_RoofLower_SideE"].g, lo["gutter"]["e"], fascia_side=(-1, 0, 0), caps=(False, True))
    numbers = {"upper": up["numbers"], "lower": lo["numbers"], "chidori_w": ch["numbers"], "chidori_e": che["numbers"],
               "gutter_rim_z": round(gz, 4), "gutter_offset": go}
    return P, numbers


def downpipe():
    """Local: the foot at (0, 0, 0) on the pipe axis; the outlet (in the side gutter) at local x -0.54; clamps toward
    +X (the veranda post's outer face)."""
    p = Piece("SM_DKH_Downpipe", "thin", "Hall",
              "round downpipe from the side gutter outlet, a two-bend swan neck to the corner post, wall clamps, a "
              "shoe at the ground (front and rear corners)")
    p.local = True
    g = p.g
    zg = LOW_EAVE - BO - 0.055
    top = zg - 0.04
    RK.downpipe(g, [(-0.54, 0, top), (-0.54, 0, zg - 0.22), (0.0, 0, zg - 0.62), (0.0, 0, 0.14)], r=0.045,
                bend_r=0.14, clamps=(0.95, 1.95), clamp_to=(1, 0, 0))
    # a small outlet collar where the pipe leaves the gutter
    RK.tube(g, [Vector((-0.54, 0, zg - 0.075)), Vector((-0.54, 0, zg - 0.12))], 0.056, IR, cap0=True, cap1=True)
    p.hull_box(-0.05, 0.05, -0.05, 0.05, 0.0, zg - 0.62)
    p.wear = True
    p.extra = {"outlet_local": [-0.54, 0.0, round(top, 4)]}
    return p


def eave_landing():
    """Local: x centred on the pad, y 0 = the lower eave line (world Y 21.5), deck top z 3.0 (world heights)."""
    p = Piece("SM_DKH_EaveLanding", "landing", "Hall",
              "route-4 landing at the lower eave: a flat timber eave deck, top +3.0, 1.2 x 0.75 m in front of the eave "
              "(GASP cannot mantle onto a 25 deg edge; GASP_TRAVERSAL.md 4), on two cantilever joists over the gutter")
    p.local = True
    g = p.g
    hx, d = 0.60, 0.75
    top = LOW_EAVE
    bt = 0.045
    n = 5
    bw = (d - 0.02) / n
    for i in range(n):
        ya = -d + 0.005 + i * bw
        cbox(g, -hx, hx, ya + 0.003, ya + bw - 0.003, top - bt, top, TA, ch=0.005)
    cbox(g, -hx - 0.02, hx + 0.02, -d - 0.045, -d, top - 0.15, top + 0.005, TD, ch=0.008)       # front fascia
    for s in (-1, 1):
        xa, xb = sorted((s * hx, s * (hx + 0.045)))
        cbox(g, xa, xb, -d - 0.045, -0.02, top - 0.13, top + 0.004, TD, ch=0.008)                  # side boards
    jt = top - bt
    for s in (-1, 1):
        cbox(g, s * 0.40 - 0.05, s * 0.40 + 0.05, -d, 0.12, jt - 0.10, jt, TD, ch=0.01)          # joists
        for yy in (-0.62, -0.10):                                                                   # iron straps
            cbox(g, s * 0.40 - 0.056, s * 0.40 + 0.056, yy - 0.02, yy + 0.02, jt - 0.105, jt - 0.098, IR, ch=0.001)
    p.hull_box(-hx, hx, -d, 0.0, top - 0.20, top)
    p.extra = {"deck_top": top, "depth": d, "width": 2 * hx}
    return p


# ------------------------------------------------------------------------------------------------ layout
def bay_instances():
    """(piece, loc, rot) for every wall bay module (front, back, west, east). Front P L P D D D P L P as the sheet;
    the side door bay is Y 26-28 (west index 3, east index 1: under the chidori-hafu, clear of the corridors at
    Y 29.5-32.5); the frieze runs under the raised centre eave (front bays X 17-27)."""
    out = []
    front = ["P", "L", "P", "D", "D", "D", "P", "L", "P"]
    back = ["P", "L", "P", "P", "D", "P", "P", "L", "P"]
    side_w = ["P", "P", "P", "D", "P"]
    side_e = ["P", "D", "P", "P", "P"]
    clere_front = ["P", "P", "F", "F", "F", "F", "F", "P", "P"]
    kind = {"P": "SM_DKH_Bay_Plaster", "L": "SM_DKH_Bay_Lattice", "D": "SM_DKH_Bay_Door"}
    ck = {"P": "SM_DKH_Bay_ClerePlaster", "F": "SM_DKH_Bay_ClereFrieze"}
    for i in range(9):
        loc = (BX0 + 2 * i, BY0, FLOOR)
        out += [(kind[front[i]], loc, 0.0), ("SM_DKH_Bay_Transom", loc, 0.0), (ck[clere_front[i]], loc, 0.0)]
        loc = (BX1 - 2 * i, BY1, FLOOR)
        out += [(kind[back[i]], loc, 180.0), ("SM_DKH_Bay_Transom", loc, 180.0), (ck["P"], loc, 180.0)]
    for i in range(5):
        loc = (BX0, BY1 - 2 * i, FLOOR)
        out += [(kind[side_w[i]], loc, -90.0), ("SM_DKH_Bay_Transom", loc, -90.0), (ck["P"], loc, -90.0)]
        loc = (BX1, BY0 + 2 * i, FLOOR)
        out += [(kind[side_e[i]], loc, 90.0), ("SM_DKH_Bay_Transom", loc, 90.0), (ck["P"], loc, 90.0)]
    return out


def hall_instances():
    inst = []
    c = (22.0, 29.0, 0.0)
    inst += [("SM_DKH_StepBand", (22.0, 22.0, 0.0), 0.0), ("SM_DKH_Veranda", c, 0.0), ("SM_DKH_VerandaFrame", c, 0.0),
             ("SM_DKH_Frame", c, 0.0), ("SM_DKH_RoofLower_Front", c, 0.0), ("SM_DKH_RoofLower_SideW", c, 0.0),
             ("SM_DKH_RoofLower_SideE", c, 0.0), ("SM_DKH_RoofChidori_W", c, 0.0), ("SM_DKH_RoofChidori_E", c, 0.0),
             ("SM_DKH_RoofUpper_Front", c, 0.0), ("SM_DKH_RoofUpper_Back", c, 0.0),
             ("SM_DKH_RoofUpper_End", c, 0.0), ("SM_DKH_RoofUpper_End", c, 180.0), ("SM_DKH_RoofUpper_Ridge", c, 0.0)]
    inst += bay_instances()
    for (x, y, r) in ((10.95, VPY, 0.0), (33.05, VPY, 180.0), (10.95, 33.85, 0.0), (33.05, 33.85, 180.0)):
        inst.append(("SM_DKH_Downpipe", (x, y, 0.0), r))
    for dx in (0.0, PAD_DX):
        inst.append(("SM_DKH_EaveLanding", ((PAD[0] + PAD[1]) / 2 + dx, LOW_Y, 0.0), 0.0))
    return inst


REPLACED = ["SM_DGB_Hall_Veranda", "SM_DGB_Hall_StepBand", "SM_DGB_Hall_Body", "SM_DGB_Hall_RoofLower",
            "SM_DGB_Hall_RoofUpper", "SM_DGB_Landing_EavePad"]


def place(piece, loc, rot):
    return {"piece": piece, "loc": [round(v, 4) for v in loc], "rot_z": float(rot)}


# ------------------------------------------------------------------------------------------------ main
def main():
    t0 = time.time()
    assert_owner("DojoHall", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    asm = bpy.data.collections.new("Assembly")
    sc.collection.children.link(asm)
    roofs, roof_numbers = roof_pieces()
    P = [step_band(), veranda(), veranda_frame(), frame(), bay_plaster(), bay_lattice(), bay_door(), bay_transom(),
         bay_clere_plaster(), bay_clere_frieze()] + roofs + [downpipe(), eave_landing()]
    objs, stats = {}, {}
    for p in P:
        t1 = time.time()
        o, bad = geo_to_object(p, kit)
        objs[p.name] = o
        stats[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                         "sec": round(time.time() - t1, 1)}
        print("BUILT", p.name, stats[p.name], flush=True)
    calm = {}
    for name in ("SM_DKH_Bay_Plaster", "SM_DKH_Bay_Lattice", "SM_DKH_Bay_Door"):
        calm[name] = calm_boards(objs[name])
    calm["SM_DKH_Veranda"] = calm_boards(objs["SM_DKH_Veranda"], seed=5151, jitter=0.12, set_name="TimberAged",
                                         deck=True)
    print("CALM boards", calm, flush=True)
    for p in P:
        if stats[p.name]["tris"] >= 2000:
            p.nanite = True
            objs[p.name]["nanite"] = True
    if not QUICK:
        for p in P:
            if p.wear:
                t1 = time.time()
                djm.bake_wear(objs[p.name])
                print("WEAR", p.name, round(time.time() - t1, 1), flush=True)
    # ---- layout (grey-box world frame)
    inst = [place(*i) for i in hall_instances()]
    pieces = {p.name: p for p in P}
    for it in inst:
        p = pieces[it["piece"]]
        it.update({"folder": p.folder, "collision_class": p.cls, "kit": "hall"})
    for n, it in enumerate(inst):
        o = bpy.data.objects.new(f"{it['piece']}__h{n:03d}", objs[it["piece"]].data)
        o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
        asm.objects.link(o)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        it["bbox_min_max"] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                             [round(max(q[i] for q in pts), 4) for i in range(3)]
    kit.hide_render = True
    kit.hide_viewport = True
    HW.mkdir(parents=True, exist_ok=True)
    LH = {
        "date": "2026-09-28", "stage": "kits 3 + 4: hall + shared roof system, round 3 look pass", "units": "m, grey-box world frame "
        "(X east, Y north, Z up; Unreal (x*100, -y*100, z*100))",
        "roof_kit": {"module": "Scripts/dojo/roof/roof_kit.py", "version": RK.VERSION},
        "material_library": "Scripts/dojo/materials (M_DJ_*), textures Exports/DojoKit/Materials/Textures",
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": stats[p.name]["tris"], "slots": [m.name for m in objs[p.name].data.materials],
                            "nanite": p.nanite, "kit": "hall",
                            "pivot_world": None if p.local else [round(v, 4) for v in p.pivot],
                            **({"extra": p.extra} if p.extra else {})} for p in P},
        "instances": inst,
        "replaces_greybox": REPLACED,
        "numbers": {
            "floor": FLOOR, "body": [BX0, BX1, BY0, BY1], "veranda": [VX0, VX1, VY0, BY1],
            "step_band": {"tread1": {"y": list(BAND["t1"]), "top": 0.25}, "tread2": {"y": list(BAND["t2"]), "top": 0.5},
                          "stair_x": list(BAND["stair"]), "stair_tread1": {"y": list(BAND["s1"]), "top": 0.25},
                          "stair_tread2": {"y": list(BAND["s2"]), "top": 0.5}},
            "lower_roof": {"eave": LOW_EAVE, "eave_lines": {"front_y": LOW_Y, "west_x": LOW_XW, "east_x": LOW_XE},
                           "at_wall": round(zlow_front(BY0), 4), "pitch_deg": PITCH,
                           "plane": "z = 3.0 + (y - 21.5) * tan 25 (front); z = 3.0 + (x - 10.5) * tan 25 (west)"},
            "upper_roof": {"eave": UP_EAVE, "rect": [UP_X0, UP_X1, UP_Y0, UP_Y1], "pitch_deg": PITCH,
                           **roof_numbers["upper"]},
            "keta": {"top": round(KETA_TOP, 4), "bottom": round(KETA_BOT, 4)},
            "veranda_edge_headroom_m": round(KETA_BOT - FLOOR, 3),
            "r5_headroom_exceptions": {
                "status": "ACCEPTED EXCEPTION (round 3, 2026-09-28)",
                "note": "R5 asks 2.5 m wherever a player walks; the spec's fixed lower eave (+3.0 at Y 21.5, route 4) "
                        "leaves less at the veranda's outer edge and over the step band: the lower roof plane is "
                        "+3.303 at the post line (Y 22.15), so a 0.24 m eave beam under 0.245 m of tiles, sarking and "
                        "rafters cannot clear 3.0; moving the post line back to Y 22.6 would still leave the step band "
                        "under the eave at 2.2-2.5 m. Inside the post line the headroom is 2.68 m or more.",
                "veranda_keta_line_m": round(KETA_BOT - FLOOR, 3),
                "step_band_under_the_lower_eave_m": [round(LOW_EAVE - UNDER - 0.07 * math.sin(math.radians(PITCH))
                                                           - 0.5, 3),
                                                     round(LOW_EAVE - UNDER - 0.07 * math.sin(math.radians(PITCH))
                                                           - 0.25, 3)],
                "capital_blocks_m": round(KETA_BOT - 0.08 - FLOOR, 3),
                "measured_round3": {"source": "WorkFiles/dojo/build/hall/measure_r3.json (rays up to the first hall mesh, X 12-22)", "keta_line_Y22.06-22.24_m": 2.308, "capital_blocks_m": 2.228, "step_band_upper_tread_m": [2.387, 2.523], "step_band_lower_tread_m": [2.497, 2.548], "deck_Y22.3_m": [2.608, 2.73], "deck_Y22.6_m": [2.748, 2.864], "deck_Y23.0_min_m": 2.808}},
            "side_door_bay_y": list(SIDE_DOOR_Y),
            "chidori_hafu": {"w": roof_numbers["chidori_w"], "e": roof_numbers["chidori_e"]},
            "frieze": {"bays_x": [17.0, 27.0], "z": [round(CPLATE_BOT - FRIEZE_H + 0.05, 4), round(CPLATE_BOT - 0.05, 4)]},
            "upper_centre_plane": {"x": [RECESS["x_a"], RECESS["x_b"]], "eave_y": round(C_YR, 4), "eave_z": round(C_ZE, 4),
                                   "pitch_deg": round(C_DEG, 3), "wall_plate": [round(CPLATE_BOT, 4),
                                                                                round(CPLATE_TOP, 4)]},
            "wall_plate": [round(PLATE_BOT, 4), round(PLATE_TOP, 4)], "door_head_world": FLOOR + DOOR_HEAD,
            "gutter_rim_z": roof_numbers["gutter_rim_z"],
            "eave_landings": {"W": [PAD[0], PAD[1], PAD[2], PAD[3], LOW_EAVE],
                              "E": [PAD[0] + PAD_DX, PAD[1] + PAD_DX, PAD[2], PAD[3], LOW_EAVE]},
            "ac_zones": {"note": "the modern kit's SM_DKP_Modern_ACUnit_Roof stands here on the lower roof plane (its "
                                 "front feet at Y 22.0, +3.2332); casing top +5.10 (route 5); nothing of the hall "
                                 "(gutter, flashing, brackets) stands in these zones or in the stance in front",
                         "W": [15.0, 16.2, 21.98, 23.1], "E": [27.8, 29.0, 21.98, 23.1], "top": AC_TOP,
                         "stance": {"W": [15.6, 21.66], "E": [28.4, 21.66],
                                    "floor_z": round(zlow_front(21.66), 4)}},
            "upper_eave_step": {"y": UP_Y0, "z": UP_EAVE, "rise_from_ac_top": round(UP_EAVE - AC_TOP, 3),
                                "note": "the walkable upper eave: the roof slab's edge at +5.5 over Y 23.1 is a 0.40 m "
                                        "CMC walk-up step from the AC top (step height 0.45)"},
        },
    }
    (HW / "layout_hall.json").write_text(json.dumps(LH, indent=1), encoding="utf-8")
    # ---- QA + export
    qa, exp = {}, {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    if not QUICK:
        for p in P:
            o = objs[p.name]
            t1 = time.time()
            add_uv1(o)
            print("UV1", p.name, round(time.time() - t1, 1), flush=True)
        kit.hide_viewport = False          # the operator overlap test needs the objects in the view layer
        for p in P:
            o = objs[p.name]
            has_glow = any(m.name == GL for m in o.data.materials)
            # round 3: the SAT overlap test builds every candidate pair in memory; on the big tiled roofs (UV0 in tile
            # units: 70-120 million pairs) that took 15 GB and stalled the machine, so the pieces over
            # 40k tris use the pipeline's other overlap method (bpy.ops.uv.select_overlap, same checks)
            ntri = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
            r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25,
                         overlap_method="operator" if ntri > 40000 else "sat")
            w = set(waive) | ({"texel_density"} if has_glow else set())
            fails = [c for c in r["checks"] if not c["passed"]]
            hard = [c for c in fails if c["name"] not in w]
            tex = next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), "")
            lib_td = djm.texel_density(o)
            qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in w}),
                          "tris": r["triangles"].get(p.name), "texel_qa": tex, "texel_library_p5_p50_p95": lib_td}
            print("QA", p.name, len(hard), sorted({c["name"] for c in fails}), flush=True)
        kit.hide_viewport = True
        hard_total = sum(len(v["hard_fails"]) for v in qa.values())
        print(f"QA hall: {len(P)} pieces, hard fails {hard_total}", flush=True)
        for k, v in qa.items():
            for c in v["hard_fails"]:
                print("  FAIL", k, c["name"], str(c["detail"])[:240])
        (HW / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
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
            (HW / "export_report.json").write_text(json.dumps(exp, indent=1, default=str), encoding="utf-8")
            print(f"exported {len(exp)} FBX to {EXPORT_DIR}", flush=True)
    # ---- the showcase compound around it (for walk / climb checks and context renders)
    if "--no-context" not in ARGS:
        compose_checks(kit, asm, LH, stats)
    rep = {"calm_boards": calm, "pieces": {p.name: {"class": p.cls, "tris": stats[p.name]["tris"], "nanite": p.nanite,
                               "ucx": len(p.hulls), "bad_faces": stats[p.name]["bad_faces"]} for p in P},
           "tris_total_unique": sum(stats[p.name]["tris"] for p in P),
           "tris_placed": sum(stats[it["piece"]]["tris"] for it in inst),
           "instances": len(inst), "seconds": round(time.time() - t0, 1), "quick": QUICK}
    (HW / "hall_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "seconds", rep["seconds"], flush=True)


def compose_checks(kit, asm, LH, stats):
    """Load the showcase compound (read-only) around the hall: its Kit pieces + UCX and its Assembly instances, minus the
    grey-box hall; write layout_hall_checks.json (layout_showcase.json with the hall swapped in)."""
    if not SHOWCASE_BLEND.exists():
        print("no showcase blend; checks skipped")
        return
    def dropped(name):     # the grey-box hall, and (round 3) the showcase's own copy of an earlier hall build
        base = name.split(".")[0]
        if base.startswith("UCX_"):
            base = base[4:].rsplit("_", 1)[0]
        return base in REPLACED or base.startswith("SM_DKH_")

    with bpy.data.libraries.load(str(SHOWCASE_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if not dropped(n.split("__")[0])]
    keep_asm = 0
    for o in dst.objects:
        if o is None:
            continue
        piece = o.name.split("__")[0]
        if "__" in o.name:
            if piece in REPLACED:
                bpy.data.objects.remove(o, do_unlink=True)
                continue
            asm.objects.link(o)
            keep_asm += 1
        else:
            base = o.name
            if base.startswith("UCX_"):
                base = base[4:].rsplit("_", 1)[0]
            if base in REPLACED:
                bpy.data.objects.remove(o, do_unlink=True)
                continue
            if o.type in ("MESH", "EMPTY"):
                kit.objects.link(o)
    L = json.loads(SHOWCASE_LAYOUT.read_text(encoding="utf-8"))
    L["pieces"] = {k: v for k, v in L["pieces"].items() if k not in REPLACED and not k.startswith("SM_DKH_")}
    for k, v in LH["pieces"].items():
        L["pieces"][k] = {"class": v["class"], "kit": "hall", "nanite": v["nanite"], "ucx": v["ucx"]}
    L["instances"] = [i for i in L["instances"] if i["piece"] not in REPLACED and not i["piece"].startswith("SM_DKH_")]         + LH["instances"]
    for m in L["traversal_markers"]:
        if m["name"] == "Hall_Veranda":
            m["box"] = [VX0, VX1, VY0, BY1, 0.0, FLOOR]
            m["note"] = "veranda +0.5 from the side yards (hall kit: the deck starts at Y 22.0 behind the step band)"
    L["stage"] = "hall kit checks: the showcase with the hall (SM_DKH_*) in place of the grey-box hall"
    L["hall"] = LH["numbers"]
    (HW / "layout_hall_checks.json").write_text(json.dumps(L, indent=1), encoding="utf-8")
    print("context: assembly instances kept", keep_asm, "layout_hall_checks.json written", flush=True)


if __name__ == "__main__":
    main()
