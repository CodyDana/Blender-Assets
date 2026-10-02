"""HALL + ARMORY round (2026-10-01), stage 2 (Blender): the main hall's REAR EXTENSION and its opened centre doors, the
new 1v1 closure pieces and the moved 1v1 ring, built on the hall builder's own numbers (Scripts/dojo/hall/build_hall.py,
imported read-only), the shared roof system (Scripts/dojo/roof/roof_kit.py) and the dojo material library.

Design source (the stage-1 survey): WorkFiles/shared/armory_hall/{hall_shell_layout.json, interface.json} and
WorkFiles/dojo/build/hall_armory/survey/survey_report.json. Owner decision 2026-10-01: the armory (12 x 20 m interior,
ceiling +4.8) becomes the hall's interior; the hall FRONT stays exactly as built; the hall extends 11 m back under a
LOWER rear gable roof (roof_kit language) so the main ridge and the courtyard silhouette do not change.

New pieces (world metres, layout frame x east / y north; pivots as hall_shell_layout.json):
  SM_DKH_Bay_DoorOpen            the door bay without leaves: sill + head track + head beam (clear 1.76 x 1.843 m)  local
  SM_DKH_DoorLeaf_Parked         one hall door leaf lifted out and stood against the inside of a plaster bay        local
  SM_DKH_Frame_Open              SM_DKH_Frame with the rear posts X 17-27 removed, a raised rear beam over the opening,
                                 collision = wall hulls with the three door openings + the closed side strips  (22,29,0)
  SM_DKH_RoofUpper_BackValley    the main back slope cut along the valley Y 34.42 for X 14.1-29.9, valley iron, end boards
                                                                                                          (22,29,0)
  SM_DKH_Rear_Frame              the extension's posts, foundation, sills, skirting, wall plates, junction fillers;
                                 collision = walls + the 0.58 m cavities + the sub-floor                 (22,39.5,0)
  SM_DKH_Rear_Bay_ClerePlaster   the clerestory band cut to the extension's lower plate                            local
  SM_DKH_Rear_Bay1_Plaster / _Transom / _ClerePlaster      1 m junction-bay versions                               local
  SM_DKH_Rear_Roof               the rear gable's two slopes (south from the valley, north to the eave +5.16), verges,
                                 bargeboards with gegyo, soffit, capped rafters, frieze boards, valley iron (22,39.5,0)
  SM_DKH_Rear_RoofRidge          r4 noshi courses + cap row, plain onigawara ends (the main ridge's profile) (22,39.5,0)
  SM_DKH_Rear_RoofGable          the west gable (plaster in a timber frame); the east one = it turned 180 (22,39.5,0)
  SM_DKH_Rear_WindowBacker       a lit shoji-paper panel on a dark board behind each armory window (no collision)  local
  SM_DKX_1v1_HallRear_W / _E     the old SM_DKX_1v1_HallRear split either side of the extension (1v1 only)
  SM_DKX_1v1_RearRoof            caps the extension and its roof (1v1 only)
  SM_DGB_Boundary_1v1            the 1v1 ring rebuilt with its north side +11 m (same name, material and pivot)

Run: blender -b --factory-startup --python Scripts/dojo/hall/build_hall_rear.py -- [--quick] [--no-export]
Out: Assets/Dojo/DojoHallRear.blend (Kit), Exports/DojoKit/Hall/SM_DKH_*.fbx (new names only), Exports/DojoKit/Outside/
     SM_DKX_1v1_{HallRear_W,HallRear_E,RearRoof}.fbx, Exports/DojoKit/SM_DGB_Boundary_1v1.fbx (backed up first),
     WorkFiles/dojo/build/hall_armory/blender/{layout_hall_rear.json, qa_report.json, export_report.json,
     blockers/qa_report.json, blockers/export_report.json, build_report.json}
"""
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
for _p in (ROOT / "Scripts", ROOT / "Scripts" / "dojo", ROOT / "Scripts" / "dojo" / "roof",
           ROOT / "Scripts" / "dojo" / "materials", ROOT / "Scripts" / "dojo" / "hall", ROOT / "Scripts" / "dojo" / "outside"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import build_hall as BH  # noqa: E402  (read-only: constants and bay helpers)
import roof_kit as RK  # noqa: E402
from roof_kit import Geo  # noqa: E402
import kit1_geo as K1  # noqa: E402
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402
from kit_mesh import Piece, cobox, cbox, quad, geo_to_object, add_uv1, fix_lod, TD, TA, GRR, PL, IR, TL  # noqa: E402
import ox_common as OX  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
OUTD = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "blender"
EXPORT_HALL = ROOT / "Exports" / "DojoKit" / "Hall"
EXPORT_OUT = ROOT / "Exports" / "DojoKit" / "Outside"
EXPORT_RING = ROOT / "Exports" / "DojoKit"
BLEND = ROOT / "Assets" / "Dojo" / "DojoHallRear.blend"
SHARED = ROOT / "WorkFiles" / "shared" / "armory_hall"

# ------------------------------------------------------------------------------------------------ numbers
HP = BH.HP
FLOOR = BH.FLOOR
TN = BH.TN                                  # tan 25
CS = BH.CS
BO = BH.BO
UNDER = BH.UNDER                            # 25 deg collision plane -> rafter underside
UP_TN = BH.UP_TN                            # tan 30 (main upper roof)
UP_UNDER = BH.UP_UNDER
SP = BH.SP
# the extension (survey: hall_shell_layout.json 'extension')
RX0, RX1, RY0, RY1 = 15.0, 29.0, 34.0, 45.0
R_EAVE_Y, R_ZE = 45.9, 5.1617               # north eave line, collision height there (survey D4 rev 1)
R_VX0, R_VX1 = 14.1, 29.9                   # verges (0.9 m beyond the side walls)
R_CY = 39.5                                 # ridge line
R_Y0V = 2 * R_CY - R_EAVE_Y                 # the south slope's virtual eave (33.1)
R_ZR = R_ZE + (R_EAVE_Y - R_CY) * TN        # planes meet at the ridge
# the level valley where the rear south slope meets the main back slope (z = 5.5 + (34.9 - y) tan 30)
Y_V = (BH.UP_EAVE + BH.UP_Y1 * UP_TN - R_ZE + R_Y0V * TN) / (UP_TN + TN)
Z_V = R_ZE + (Y_V - R_Y0V) * TN


def zr_north(y):
    return R_ZE + (R_EAVE_Y - y) * TN


def zr_south(y):
    return R_ZE + (y - R_Y0V) * TN


def zmain_back(y):
    return BH.UP_EAVE + (BH.UP_Y1 - y) * UP_TN


R_PLATE_TOP = zr_north(RY1 + HP / 2) - UNDER - 0.006      # the hall's plate rule (build_hall PLATE_TOP) on the rear roof
R_PLATE_BOT = R_PLATE_TOP - 0.24
R_CLERE = (3.70, R_PLATE_BOT - FLOOR)
MAIN_REAR_BEAM = (5.52, BH.PLATE_TOP)       # survey: the main rear plate over the opening, clear of the armory coffers
ARMORY_TOP_WORLD = 5.50                     # interface.json envelope top z 5.0 hall-local
LEAF = {"w": 0.922, "t": 0.035, "h": 1.86}


# ------------------------------------------------------------------------------------------------ bay helpers (width bw)
def xi(bw):
    return HP / 2, bw - HP / 2


def xo(bw):
    a, b = xi(bw)
    return a - 0.012, b + 0.012


def head_beams_w(g, bw):
    o0, o1 = xo(bw)
    cbox(g, o0, o1, -0.07, 0.07, BH.KAMOI[0] - 0.012, BH.KAMOI[1], TD, ch=0.008)
    cbox(g, 0.0, bw, -0.17, -0.105, BH.NAGESHI[0], BH.NAGESHI[1], TD, ch=0.01)
    cbox(g, o0, o1, -0.112, 0.07, BH.KAMOI[1] - 0.012, BH.NAGESHI[1] + 0.012, TD, ch=0.004)


def bay_sill_w(g, bw):
    o0, o1 = xo(bw)
    cbox(g, o0, o1, -0.08, 0.08, -0.02, 0.045, TD, ch=0.008)


def bay_door_open():
    p = Piece("SM_DKH_Bay_DoorOpen", "building", "Hall/Bays",
              "2 m door bay with the doors open (hall + armory round, decision D1-A): the sill (top +0.045), the head "
              "track (kamoi) and the full-depth head beam (nageshi) of SM_DKH_Bay_Door without its two leaves; clear "
              "opening x 0.12-1.88 of the bay from the sill top to the head-track underside +1.888 above the floor; "
              "collision = the sill (a 4.5 cm step) and the head (z >= 1.888)")
    p.local = True
    g = p.g
    bay_sill_w(g, 2.0)
    head_beams_w(g, 2.0)
    a, b = xi(2.0)
    p.hull_box(a, b, -0.08, 0.08, -0.02, 0.045)
    p.hull_box(a, b, -0.075, 0.075, BH.KAMOI[0] - 0.012, BH.NAGESHI[1])
    p.extra = {"clear_x": [round(a, 3), round(b, 3)], "sill_top": 0.045,
               "head_track_underside": round(BH.KAMOI[0] - 0.012, 4),
               "clear_height_over_sill": round(BH.KAMOI[0] - 0.012 - 0.045, 4)}
    return p


def door_leaf_parked():
    """One hall door leaf as its own mesh: the Bay_Door leaf's rows (rail 0.08, board foot 0.34, rail 0.08, square kumiko
    7 x 9 with 36 mm bars to the top rail) on a 0.922 x 0.035 x 1.86 frame. Local: x 0..0.922 (the pivot at its left
    edge), y 0 = the face against the wall .. 0.035, z 0 = the floor it stands on. The kumiko and the iron pull face +Y
    (the room); the paper sits inside the frame and shows both ways (two quads); no dark board (it is not in a wall)."""
    p = Piece("SM_DKH_DoorLeaf_Parked", "thin", "Hall/Bays",
              "one hall door leaf lifted out of its track and stood on the floor against the inside face of a plaster "
              "bay (decision D1-A): stiles, rails, a board foot, square kumiko over the paper, an iron pull; "
              "0.922 x 0.035 x 1.86 m, pivot at its left edge on the wall side; collision = one thin box")
    p.local = True
    g = p.g
    W, T, H = LEAF["w"], LEAF["t"], LEAF["h"]
    fw = 0.055
    cbox(g, 0.0, fw, 0.0, T, 0.0, H, TD, ch=0.006)
    cbox(g, W - fw, W, 0.0, T, 0.0, H, TD, ch=0.006)
    z = 0.0
    rows = [("rail", 0.08), ("board", 0.34), ("rail", 0.08)]
    for kind, h in rows:
        if kind == "rail":
            cbox(g, fw - 0.004, W - fw + 0.004, 0.0, T, z - (0.0 if z == 0 else 0.005), z + h + 0.005, TD, ch=0.006)
        else:
            BH.panel_boards(g, fw - 0.004, W - fw + 0.004, z - 0.004, z + h + 0.004, 0.012, t=0.016, w=0.14)
        z += h
    top_rail = (H - 0.065, H)
    cbox(g, fw - 0.004, W - fw + 0.004, 0.0, T, top_rail[0], top_rail[1], TD, ch=0.006)
    # kumiko on the room side (y 0.012 .. 0.033), paper at y 0.008 (two quads, facing both ways)
    x0, x1, z0, z1 = fw - 0.002, W - fw + 0.002, z, top_rail[0]
    cols, rows_n, bar = BH.SHOJI["cols"], BH.SHOJI["rows"], BH.SHOJI["bar"]
    for i in range(1, cols):
        x = x0 + (x1 - x0) * i / cols
        cbox(g, x - bar / 2, x + bar / 2, 0.012, 0.033, z0, z1, TD, ch=0.003)
    for j in range(1, rows_n):
        zz = z0 + (z1 - z0) * j / rows_n
        cbox(g, x0, x1, 0.015, 0.030, zz - bar / 2, zz + bar / 2, TD, ch=0.003)
    xs = [x0 - 0.004] + [x0 + (x1 - x0) * i / cols for i in range(1, cols)] + [x1 + 0.004]
    zs = [z0 - 0.004] + [z0 + (z1 - z0) * j / rows_n for j in range(1, rows_n)] + [z1 + 0.004]
    for i in range(cols):
        for j in range(rows_n):
            a, b, c, d = xs[i], xs[i + 1], zs[j], zs[j + 1]
            quad(g, [(a, 0.0085, c), (b, 0.0085, c), (b, 0.0085, d), (a, 0.0085, d)], SP)          # faces -Y
            quad(g, [(a, 0.0095, c), (a, 0.0095, d), (b, 0.0095, d), (b, 0.0095, c)], SP)          # faces +Y
    # iron pull on the room face near the right stile
    xs_ = W - fw / 2
    cbox(g, xs_ - 0.016, xs_ + 0.016, T, T + 0.004, 0.92, 1.08, IR, ch=0.002)
    cbox(g, xs_ - 0.008, xs_ + 0.008, T + 0.004, T + 0.009, 0.97, 1.03, IR, ch=0.001)
    p.hull_box(0.0, W, 0.0, T, 0.0, H)
    p.extra = {"size_m": [W, T, H], "pivot": "left edge, wall side, floor"}
    return p


def bay_plaster_w(name, bw, note):
    p = Piece(name, "building", "Hall/Bays", note)
    p.local = True
    g = p.g
    o0, o1 = xo(bw)
    bay_sill_w(g, bw)
    BH.panel_boards(g, o0, o1, 0.04, 0.806, -0.065)
    cbox(g, o0, o1, -0.08, 0.06, 0.794, 0.88, TD, ch=0.008)
    cbox(g, o0, o1, -0.045, 0.045, 0.87, BH.KAMOI[0] + 0.006, PL, ch=0.004)
    head_beams_w(g, bw)
    a, b = xi(bw)
    p.hull_box(a, b, -0.075, 0.075, 0.0, BH.NAGESHI[1])
    return p


def bay_transom_w(name, bw, note):
    p = Piece(name, "building", "Hall/Bays", note)
    p.local = True
    g = p.g
    o0, o1 = xo(bw)
    T = BH.TRANSOM
    cbox(g, o0, o1, -0.045, 0.045, T[0] - 0.01, T[1] + 0.012, PL, ch=0.004)
    cbox(g, o0, o1, -0.06, 0.06, T[0], T[0] + 0.05, TD, ch=0.006)
    a, b = xi(bw)
    p.hull_box(a, b, -0.045, 0.045, T[0], T[1])
    return p


def bay_clere_w(name, bw, note):
    """build_hall.bay_clere_plaster with the extension's band (+3.70 to its lower wall plate)."""
    p = Piece(name, "building", "Hall/Bays", note)
    p.local = True
    g = p.g
    o0, o1 = xo(bw)
    c0, c1 = R_CLERE
    cbox(g, 0.0, bw, -0.08, 0.08, c0, c0 + 0.12, TD, ch=0.01)
    zs = c1 - BH.CLERE_STRIP
    cbox(g, o0, o1, -0.03, 0.045, c0 + 0.105, zs + 0.01, TD, ch=0.003)
    BH.panel_boards(g, o0, o1, c0 + 0.105, zs + 0.004, -0.058, t=0.024, w=0.18)
    cbox(g, o0, o1, -0.07, 0.05, zs - 0.02, zs + 0.05, TD, ch=0.006)
    cbox(g, o0, o1, -0.045, 0.045, zs + 0.04, c1 + 0.012, PL, ch=0.004)
    a, b = xi(bw)
    p.hull_box(a, b, -0.08, 0.08, c0, c1)
    return p


# ------------------------------------------------------------------------------------------------ frames
def foundation_run(g, xa, xb, ya, yb, rng):
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


def skirting(g, x0, y0, x1, y1, nrm, bays):
    """Skirting boards between posts along a wall line from (x0, y0) to (x1, y1); bays = list of bay lengths."""
    n = Vector((nrm[0], nrm[1], 0))
    d = Vector((x1 - x0, y1 - y0, 0)).normalized()
    s = 0.0
    for L in bays:
        a = Vector((x0, y0, 0)) + d * (s + HP / 2 + 0.002)
        b = Vector((x0, y0, 0)) + d * (s + L - HP / 2 - 0.002)
        c = (a + b) / 2 + n * 0.07 + Vector((0, 0, 0.425))
        cobox(g, c, d, n, (0, 0, 1), (b - a).length / 2, 0.015, 0.075, 0.004, TD)
        s += L


def frame_open():
    p = Piece("SM_DKH_Frame_Open", "building", "Hall",
              "hall frame with the interior opened (hall + armory round): SM_DKH_Frame without the rear posts X 17-27 "
              "at Y 34 and their foundation / sill / skirting X 15-29; over the opening the rear plate becomes a beam "
              "+5.52-5.687 clear of the armory coffers (+5.50); collision = the front wall either side of the door "
              "band, the two middle door posts, the door-head lintel (+2.388 up), the side walls, the rear wall X 13-15 "
              "/ 29-31 and solid fills of the closed side strips X 13.12-15.70 / 28.30-30.88", pivot=(22.0, 29.0, 0.0))
    g = p.g
    rng = random.Random(31)
    BX0, BX1, BY0, BY1 = BH.BX0, BH.BX1, BH.BY0, BH.BY1
    posts = [(x, y) for (x, y) in BH.hall_posts() if not (y == BY1 and 17.0 <= x <= 27.0)]
    for (x, y) in posts:
        top = BH.CPLATE_BOT if (y == BY0 and BH.RECESS["x_a"] <= x <= BH.RECESS["x_b"]) else BH.PLATE_BOT
        cbox(g, x - HP / 2, x + HP / 2, y - HP / 2, y + HP / 2, 0.35, top, TD, ch=0.014)
    fw = 0.20
    for (xa, xb, ya, yb) in ((BX0 - fw, BX1 + fw, BY0 - fw, BY0 + fw),
                             (BX0 - fw, RX0 + fw, BY1 - fw, BY1 + fw), (RX1 - fw, BX1 + fw, BY1 - fw, BY1 + fw),
                             (BX0 - fw, BX0 + fw, BY0 + fw, BY1 - fw), (BX1 - fw, BX1 + fw, BY0 + fw, BY1 - fw)):
        foundation_run(g, xa, xb, ya, yb, rng)
    sw = 0.13
    cbox(g, BX0 - sw, BX1 + sw, BY0 - sw, BY0 + sw, 0.20, 0.35, TD, ch=0.01)
    cbox(g, BX0 - sw, RX0 + sw, BY1 - sw, BY1 + sw, 0.20, 0.35, TD, ch=0.01)
    cbox(g, RX1 - sw, BX1 + sw, BY1 - sw, BY1 + sw, 0.20, 0.35, TD, ch=0.01)
    cbox(g, BX0 - sw, BX0 + sw, BY0 + sw, BY1 - sw, 0.201, 0.349, TD, ch=0.01)
    cbox(g, BX1 - sw, BX1 + sw, BY0 + sw, BY1 - sw, 0.201, 0.349, TD, ch=0.01)
    skirting(g, BX0, BY0, BX1, BY0, (0, -1), [2.0] * 9)
    skirting(g, BX1, BY1, RX1, BY1, (0, 1), [2.0])
    skirting(g, RX0, BY1, BX0, BY1, (0, 1), [2.0])
    skirting(g, BX0, BY1, BX0, BY0, (-1, 0), [2.0] * 5)
    skirting(g, BX1, BY0, BX1, BY1, (1, 0), [2.0] * 5)
    pw = 0.24
    PB, PT = BH.PLATE_BOT, BH.PLATE_TOP
    xa_, xb_ = BH.RECESS["x_a"], BH.RECESS["x_b"]
    cbox(g, BX0 - 0.30, xa_ + HP / 2, BY0 - pw / 2, BY0 + pw / 2, PB, PT, TD, ch=0.014)
    cbox(g, xb_ - HP / 2, BX1 + 0.30, BY0 - pw / 2, BY0 + pw / 2, PB, PT, TD, ch=0.014)
    cbox(g, xa_ - HP / 2 - 0.10, xb_ + HP / 2 + 0.10, BY0 - pw / 2, BY0 + pw / 2, BH.CPLATE_BOT, BH.CPLATE_TOP, TD,
         ch=0.014)
    # rear plate: full height over the closed corners, the raised beam over the opening
    cbox(g, BX0 - 0.30, RX0 + HP / 2, BY1 - pw / 2, BY1 + pw / 2, PB, PT, TD, ch=0.014)
    cbox(g, RX1 - HP / 2, BX1 + 0.30, BY1 - pw / 2, BY1 + pw / 2, PB, PT, TD, ch=0.014)
    cbox(g, RX0 + HP / 2 - 0.02, RX1 - HP / 2 + 0.02, BY1 - pw / 2, BY1 + pw / 2, MAIN_REAR_BEAM[0], MAIN_REAR_BEAM[1],
         TD, ch=0.012)
    cbox(g, BX0 - pw / 2, BX0 + pw / 2, BY0 - 0.30, BY1 + 0.30, PB - 0.001, PT - 0.002, TD, ch=0.014)
    cbox(g, BX1 - pw / 2, BX1 + pw / 2, BY0 - 0.30, BY1 + 0.30, PB - 0.001, PT - 0.002, TD, ch=0.014)
    lf = BY0 - HP / 2
    cbox(g, BX0 - HP / 2, BX1 + HP / 2, lf - 0.12, lf, BH.LEDGER_TOP - BH.LEDGER_H, BH.LEDGER_TOP, TD, ch=0.01)
    for (x, s) in ((BX0, -1), (BX1, 1)):
        xf = x + s * HP / 2
        xa, xb = sorted((xf, xf + s * 0.12))
        cbox(g, xa, xb, BY0 - HP / 2, BY1 + 0.02, BH.LEDGER_TOP - BH.LEDGER_H - 0.001, BH.LEDGER_TOP - 0.001, TD,
             ch=0.01)
    # collision (the closed body hull is gone: the interior is open)
    top = PB + 0.05
    door_head = FLOOR + BH.KAMOI[0] - 0.012                      # +2.388
    p.hull_box(BX0 - HP / 2, 19.0 + HP / 2, BY0 - HP / 2, BY0 + HP / 2, 0.0, top)       # front wall west of the doors
    p.hull_box(25.0 - HP / 2, BX1 + HP / 2, BY0 - HP / 2, BY0 + HP / 2, 0.0, top)       # front wall east
    for x in (21.0, 23.0):                                                               # the two middle door posts
        p.hull_box(x - HP / 2, x + HP / 2, BY0 - HP / 2, BY0 + HP / 2, 0.0, door_head)
    p.hull_box(19.0 - HP / 2, 25.0 + HP / 2, BY0 - HP / 2, BY0 + HP / 2, door_head, top)  # lintel over the doors
    p.hull_box(BX0 - HP / 2, BX0 + HP / 2, BY0 - HP / 2, BY1 + HP / 2, 0.0, top)        # west side wall
    p.hull_box(BX1 - HP / 2, BX1 + HP / 2, BY0 - HP / 2, BY1 + HP / 2, 0.0, top)        # east side wall
    p.hull_box(BX0 - HP / 2, RX0 + HP / 2, BY1 - HP / 2, BY1 + HP / 2, 0.0, top)        # rear wall X 13-15
    p.hull_box(RX1 - HP / 2, BX1 + HP / 2, BY1 - HP / 2, BY1 + HP / 2, 0.0, top)        # rear wall X 29-31
    p.hull_box(BX0 + HP / 2, 15.70, BY0 + HP / 2, BY1 + HP / 2, FLOOR, 5.45)            # closed west strip
    p.hull_box(28.30, BX1 - HP / 2, BY0 + HP / 2, BY1 + HP / 2, FLOOR, 5.45)            # closed east strip
    p.extra = {"rear_beam_over_the_opening": list(MAIN_REAR_BEAM), "door_head_world": round(door_head, 4),
               "posts": len(posts), "posts_removed": [[x, BY1] for x in range(17, 28, 2)],
               "side_strip_fill": {"x": [[BX0 + HP / 2, 15.70], [28.30, BX1 - HP / 2]], "z": [FLOOR, 5.45]}}
    return p


def rear_frame():
    p = Piece("SM_DKH_Rear_Frame", "building", "Hall/Rear",
              "the rear extension's frame: 0.24 m posts on X 15 / 29 at Y 35-45 and on Y 45 at X 17-27, rubble-granite "
              "foundation (0.40 wide, top +0.20), ground sills, skirting, wall plates (under the rear roof's rafters), "
              "plaster junction fillers where the side walls meet the main roof soffit; collision = the side and rear "
              "walls with their 0.58 m cavities to the armory walls (solid) and the sub-floor slab",
              pivot=(22.0, R_CY, 0.0))
    g = p.g
    rng = random.Random(37)
    posts = [(RX0, y) for y in (35.0, 37.0, 39.0, 41.0, 43.0, 45.0)] + \
            [(RX1, y) for y in (35.0, 37.0, 39.0, 41.0, 43.0, 45.0)] + [(float(x), RY1) for x in range(17, 28, 2)]
    for (x, y) in posts:
        cbox(g, x - HP / 2, x + HP / 2, y - HP / 2, y + HP / 2, 0.35, R_PLATE_BOT, TD, ch=0.014)
    fw = 0.20
    for (xa, xb, ya, yb) in ((RX0 - fw, RX0 + fw, RY0 + fw, RY1 + fw), (RX0 - fw, RX1 + fw, RY1 - fw, RY1 + fw),
                             (RX1 - fw, RX1 + fw, RY0 + fw, RY1 - fw)):
        foundation_run(g, xa, xb, ya, yb, rng)
    sw = 0.13
    cbox(g, RX0 - sw, RX0 + sw, RY0 + sw, RY1 + sw, 0.201, 0.349, TD, ch=0.01)
    cbox(g, RX0 - sw, RX1 + sw, RY1 - sw, RY1 + sw, 0.20, 0.35, TD, ch=0.01)
    cbox(g, RX1 - sw, RX1 + sw, RY0 + sw, RY1 - sw, 0.201, 0.349, TD, ch=0.01)
    bays = [1.0] + [2.0] * 5
    skirting(g, RX0, RY0, RX0, RY1, (-1, 0), bays)
    skirting(g, RX1, RY1, RX0, RY1, (0, 1), [2.0] * 7)
    skirting(g, RX1, RY0, RX1, RY1, (1, 0), bays)
    pw = 0.24
    cbox(g, RX0 - pw / 2, RX0 + pw / 2, RY0, RY1 + 0.30, R_PLATE_BOT, R_PLATE_TOP, TD, ch=0.014)
    cbox(g, RX1 - pw / 2, RX1 + pw / 2, RY0, RY1 + 0.30, R_PLATE_BOT - 0.001, R_PLATE_TOP - 0.001, TD, ch=0.014)
    cbox(g, RX0 - 0.30, RX1 + 0.30, RY1 - pw / 2, RY1 + pw / 2, R_PLATE_BOT + 0.001, R_PLATE_TOP + 0.001, TD,
         ch=0.014)
    # junction fillers: in the gable plane between the gable's south rake and the main roof soffit, Y 34.0 -> the valley
    x_face = RX0 - 0.045

    def zg(y):
        return R_PLATE_TOP + (y - gable_y0()) * TN
    for xf, fx in ((x_face, -1), (44.0 - x_face, 1)):
        pts = [Vector((xf, RY0, zg(RY0) - 0.004)), Vector((xf, RY0, zmain_back(RY0) - UP_UNDER - 0.006)),
               Vector((xf, Y_V, zg(Y_V) - 0.002))]
        K1.prism(g, pts, (fx, 0, 0), 0.10, PL, frame=(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
    # collision
    pt = R_PLATE_TOP
    p.hull_box(RX0 - HP / 2, 15.70, RY0, RY1 + HP / 2, 0.0, pt)          # west wall + cavity
    p.hull_box(28.30, RX1 + HP / 2, RY0, RY1 + HP / 2, 0.0, pt)          # east wall + cavity
    p.hull_box(RX0 - HP / 2, RX1 + HP / 2, 44.30, RY1 + HP / 2, 0.0, pt)  # rear wall + cavity
    p.hull_box(RX0 + HP / 2, RX1 - HP / 2, RY0, RY1 - HP / 2, 0.0, FLOOR)  # sub-floor under the armory floor
    p.extra = {"posts": len(posts), "wall_plate": [round(R_PLATE_BOT, 4), round(R_PLATE_TOP, 4)],
               "cavity_m": round(15.70 - (RX0 + HP / 2), 3), "junction_filler_y": [RY0, round(Y_V, 4)]}
    return p


def gable_y0():
    """South end of the gable's base where its rake meets the rafter underside (the base sits on the wall plate)."""
    return RY0 - (zr_south(RY0) - UNDER - R_PLATE_TOP) / TN


# ------------------------------------------------------------------------------------------------ roofs
RAFTER_FLOOR = ARMORY_TOP_WORLD + 0.022     # interface rule: shell over the armory >= its top + 0.02


def lift_over_armory(o, pivot, xa=15.70, xb=28.30, ya=24.0, yb=44.30, z=RAFTER_FLOOR):
    """Raise every vertex over the armory's plan that hangs below `z` to `z` (no new topology): the rafter ends at the
    valley line, whose lower corners met the coffer tops (+5.50) within a millimetre. Returns the count moved."""
    P = Vector(pivot)
    n = 0
    for v in o.data.vertices:
        w = v.co + P
        if xa <= w.x <= xb and ya <= w.y <= yb and w.z < z:
            v.co.z = z - P.z
            n += 1
    o.data.update()
    return n


def main_back_valley():
    """The main upper roof regenerated with build_hall's exact irimoya call (deterministic), its back slope cut along
    the valley for X 14.1-29.9: three convex clips (west of the rear verge, east of it, and the strip south of the
    valley), plus the valley iron on this plane and end boards on the two cut eave stubs."""
    up = RK.irimoya(BH.UP_X0, BH.UP_X1, BH.UP_Y0, BH.UP_Y1, BH.UP_EAVE, pitch=BH.UP_PITCH, gable_in=BH.GABLE_IN,
                    verge_ov=0.45, overhang=0.9, upturn=0.12, reach=3.2, gable_style="plaster", gable_frame=True,
                    rafter_spacing=0.30, rafter_caps=True, blocking=True, front_recess=BH.RECESS,
                    ridge_layers=(0.52, 0.46), ridge_mid_roll=0.085, ridge_top_layers=(0.36,), rivets=False,
                    oni_style="onigawara", oni=(0.56, 0.82, 0.46), hip_end="disc", diag_oni=(0.36, 0.42, 0.20),
                    ridge_hull_drop=0.08, ridge_courses=4)
    back = up["slope_back"]
    n_full = len(back.f)
    gA = RK.plan_clip(back, (R_VX0, 0.0), (R_VX0, 1.0), (R_VX0 - 1.0, 30.0))
    gB = RK.plan_clip(back, (R_VX1, 0.0), (R_VX1, 1.0), (R_VX1 + 1.0, 30.0))
    gC = RK.plan_clip(back, (R_VX0, 0.0), (R_VX0, 1.0), (22.0, 30.0))
    gC = RK.plan_clip(gC, (R_VX1, 0.0), (R_VX1, 1.0), (22.0, 30.0))
    gC = RK.plan_clip(gC, (0.0, Y_V), (1.0, Y_V), (22.0, 30.0))
    g = Geo()
    for part in (gA, gB, gC):
        g.extend(part)
    sn, cs = math.sin(math.radians(30.0)), math.cos(math.radians(30.0))
    nrm = Vector((0, sn, cs))
    # valley iron on this plane: 0.20 m (plan) up-slope from the valley line, just over the roll tops
    yc = Y_V - 0.10
    c = Vector((22.0, yc, zmain_back(yc))) + nrm * 0.009
    K1.obox(g, c, (1, 0, 0), (0, -cs, sn), nrm, (R_VX1 - R_VX0) / 2, 0.10 / cs + 0.01, 0.003, IR)
    # end boards on the cut eave stubs, just outside the rear verges' bargeboards
    for xb, d in ((R_VX0 - 0.03, -1), (R_VX1 + 0.03, 1)):
        ya, yb = Y_V, BH.UP_Y1 + 0.03
        za_t, zb_t = zmain_back(ya) + 0.05, zmain_back(yb) + 0.05
        pts = [Vector((xb, ya, za_t)), Vector((xb, yb, zb_t)), Vector((xb, yb, zb_t - 0.36)), Vector((xb, ya, za_t - 0.36))]
        K1.prism(g, pts, (d, 0, 0), 0.03, TD, frame=(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
    # collision: the back slope's two slabs, the lower trapezoid split like the geometry
    lower = [(31.9, 34.9), (12.1, 34.9), (14.6, 32.4), (29.4, 32.4)]
    upper = [(29.85, 32.4), (14.15, 32.4), (14.15, 29.0), (29.85, 29.0)]
    pa = RK.clip_poly2(lower, (R_VX0, 0.0), (R_VX0, 1.0), (R_VX0 - 1.0, 34.0))
    pb = RK.clip_poly2(lower, (R_VX1, 0.0), (R_VX1, 1.0), (R_VX1 + 1.0, 34.0))
    pc = RK.clip_poly2(lower, (R_VX0, 0.0), (R_VX0, 1.0), (22.0, 33.0))
    pc = RK.clip_poly2(pc, (R_VX1, 0.0), (R_VX1, 1.0), (22.0, 33.0))
    pc = RK.clip_poly2(pc, (0.0, Y_V), (1.0, Y_V), (22.0, 33.0))
    zf = lambda q: zmain_back(q[1])  # noqa: E731
    hulls = [RK.slab([(q[0], q[1], zf(q)) for q in poly]) for poly in (pa, pb, pc, upper)
             if len(poly) >= 3 and RK.poly2_area(poly) > 0.02]
    tris_full = sum(len(f) - 2 for f in back.f)
    return g, hulls, {"faces_full_back_slope": n_full, "tris_full_back_slope": tris_full,
                      "tris_after_cut": sum(len(f) - 2 for f in g.f), "faces_after_cut": len(g.f),
                      "numbers_main": up["numbers"]}


def rear_roof():
    """The rear gable (roof_kit.gable_roof's halves, built here without the ridge and gable faces, which are their own
    pieces): the slope frame has its eave at the virtual south eave Y 33.1 and is turned 180 about the ridge line for
    the north slope (eave Y 45.9, collision +5.1617); the south slope is clipped along the valley."""
    x0, x1 = R_VX0, R_VX1
    W = x1 - x0
    run_r = R_EAVE_Y - R_CY
    s_ridge = (run_r - 0.18) / CS
    C, nc = RK._courses(s_ridge)
    rs = RK.RoofSlope((x0, R_Y0V), (x1, R_Y0V), R_ZE, BH.PITCH)
    half = Geo()
    RK.tile_field(half, rs.sl, 0.0, W, 0.0, s_ridge, C, TL, eave=True, roll_margin=0.16)
    RK.sarking(half, rs, 0.0, W, -0.04, s_ridge + 0.1, nstrips=10)
    RK.rafters(half, rs, 0.10, W - 0.10, -0.07, s_ridge, spacing=0.30, caps=True)
    RK.eave_trim(half, rs, 0.0, W)
    RK.eave_blocking(half, rs, 0.12, W - 0.12, R_EAVE_Y - RY1)
    for ue, inw in ((0.0, 1), (W, -1)):
        RK.verge(half, rs, ue, 0.0, s_ridge + 0.10, inward=inw, disc=0.085, board=True)
    rot = Matrix.Translation((22.0, R_CY, 0)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation((-22.0, -R_CY, 0))
    north = half.transformed(rot)
    south = RK.plan_clip(half, (0.0, Y_V), (1.0, Y_V), (22.0, R_CY))
    g = Geo()
    g.extend(north)
    g.extend(south)
    # valley iron on this plane (0.20 m plan up-slope from the valley line)
    sn, cs = math.sin(math.radians(BH.PITCH)), math.cos(math.radians(BH.PITCH))
    nrm = Vector((0, -sn, cs))
    yc = Y_V + 0.10
    c = Vector((22.0, yc, zr_south(yc))) + nrm * 0.009
    K1.obox(g, c, (1, 0, 0), (0, cs, sn), nrm, W / 2, 0.10 / cs + 0.01, 0.003, IR)
    # a plain hanging board (gegyo) under each verge apex
    for xv, fx in ((x0, -1), (x1, 1)):
        za = R_ZR - BO - 0.03 - 0.05
        xp = xv - fx * 0.01
        poly = [(xp, R_CY - 0.16, za - 0.30), (xp, R_CY + 0.16, za - 0.30), (xp, R_CY + 0.22, za - 0.12),
                (xp, R_CY, za), (xp, R_CY - 0.22, za - 0.12)]
        K1.prism(g, [Vector(q) for q in poly], (fx, 0, 0), 0.05, TD,
                 frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))))
    hulls = [RK.slab([(x0, Y_V, Z_V), (x1, Y_V, Z_V), (x1, R_CY, R_ZR), (x0, R_CY, R_ZR)]),
             RK.slab([(x1, R_EAVE_Y, R_ZE), (x0, R_EAVE_Y, R_ZE), (x0, R_CY, R_ZR), (x1, R_CY, R_ZR)])]
    return g, hulls, {"course_m": round(C, 4), "courses_per_half": nc}


def rear_ridge():
    gR = Geo()
    ridge_roll = 0.12
    rtop, z0r = RK.ridge(gR, (R_VX0 + 0.20, R_CY), (R_VX1 - 0.20, R_CY), R_ZR, widths=(0.52, 0.46), h=0.065,
                         roll_r=ridge_roll, mid_roll=0.085, top_layers=(0.36,), rivets=False, courses=4)
    oW, oH, oT = 0.56, 0.82, 0.46
    for xe, f in ((R_VX0 + 0.02, -1), (R_VX1 - 0.02, 1)):
        RK.onigawara(gR, (xe - f * oT / 2, R_CY, z0r - 0.10), (f, 0, 0), oW, oH, oT, TL,
                     cap_z=(rtop - ridge_roll - 0.016) - (z0r - 0.10), cap_r=ridge_roll)
    oni_top = z0r - 0.10 + oH
    hr = [[(x, y, z) for x in (R_VX0 + 0.20, R_VX1 - 0.20) for y in (R_CY - 0.28, R_CY + 0.28)
           for z in (R_ZR - 0.13, rtop - 0.08)]]
    for xe, f in ((R_VX0 + 0.02, -1), (R_VX1 - 0.02, 1)):
        hr.append([(x, y, z) for x in (xe, xe - f * oT) for y in (R_CY - oW / 2, R_CY + oW / 2)
                   for z in (z0r - 0.10, oni_top)])
    return gR, hr, {"planes_meet": round(R_ZR, 4), "ridge_cap_top": round(rtop, 4), "ridge_end_top": round(oni_top, 4)}


def rear_gable():
    g = Geo()
    y0 = gable_y0()
    y1 = 2 * R_CY - y0
    z_apex = R_ZR - UNDER
    RK.gable_face(g, RX0 - 0.045, y0, y1, R_PLATE_TOP, R_CY, z_apex, facing=-1, style="plaster", tie_h=0.02,
                  tie_drop=0.0, frame=True)
    hull = [(x, y, z) for x in (RX0 - 0.06, RX0 + 0.06) for (y, z) in ((y0, R_PLATE_TOP), (y1, R_PLATE_TOP),
                                                                        (R_CY, z_apex))]
    return g, [hull], {"base_y": [round(y0, 4), round(y1, 4)], "base_z": round(R_PLATE_TOP, 4),
                       "apex_z": round(z_apex, 4)}


def window_backer():
    p = Piece("SM_DKH_Rear_WindowBacker", "nocollision", "Hall/Rear",
              "a lit shoji-paper panel 3.60 x 1.55 m (12 x 5 unit-UV cells on M_DJ_ShojiPaper) on a dark board with a "
              "thin frame, stood 0.15 m outside an armory window in the closed side strips / cavities so the window's "
              "open lattice reads lit; paper faces local +Y, centred on the pivot; no collision")
    p.local = True
    g = p.g
    w, h, cols, rows_n = 3.60, 1.55, 12, 5
    for i in range(cols):
        for j in range(rows_n):
            a, b = -w / 2 + w * i / cols, -w / 2 + w * (i + 1) / cols
            c, d = -h / 2 + h * j / rows_n, -h / 2 + h * (j + 1) / rows_n
            quad(g, [(a, 0.0, c), (a, 0.0, d), (b, 0.0, d), (b, 0.0, c)], SP)
    cbox(g, -w / 2 - 0.02, w / 2 + 0.02, -0.022, -0.004, -h / 2 - 0.02, h / 2 + 0.02, TD, ch=0.002)
    for (x0, x1, z0, z1) in ((-w / 2 - 0.04, -w / 2, -h / 2 - 0.04, h / 2 + 0.04), (w / 2, w / 2 + 0.04, -h / 2 - 0.04,
                              h / 2 + 0.04), (-w / 2, w / 2, -h / 2 - 0.04, -h / 2), (-w / 2, w / 2, h / 2, h / 2 + 0.04)):
        cbox(g, x0, x1, -0.022, 0.012, z0, z1, TD, ch=0.004)
    p.wear = False
    return p


# ------------------------------------------------------------------------------------------------ 1v1 pieces
CEIL = 20.0
HALLREAR_W = (10.40, 14.88, 34.00, 34.10, 0.0, CEIL)
HALLREAR_E = (29.12, 33.60, 34.00, 34.10, 0.0, CEIL)
REARROOF = (13.90, 30.10, 34.10, 46.10, 5.128, CEIL)
RING_NEW = [(-1.1, 45.1, -1.1, -1.0, 0, 20), (-1.1, 45.1, 48.0, 48.1, 0, 20), (-1.1, -1.0, -1.0, 48.0, 0, 20),
            (45.0, 45.1, -1.0, 48.0, 0, 20), (-1.1, 45.1, -1.1, 48.1, 20, 20.1),
            (12.1, 31.9, 29.0, 29.1, 5.3, 20),
            (-1.0, 7.6, 31.7, 31.8, 3.0, 20), (36.4, 45.0, 31.7, 31.8, 3.0, 20),
            (7.6, 10.5, 31.0, 31.1, 3.0, 20), (33.5, 36.4, 31.0, 31.1, 3.0, 20),
            (7.6, 36.4, 47.0, 48.0, 2.0, 20)]


def blocker_pieces():
    P = []
    for name, box, note in (
            ("SM_DKX_1v1_HallRear_W", HALLREAR_W, "the alley closure's south face west of the extension (the old "
             "SM_DKX_1v1_HallRear X 10.4-33.6 split: its middle would cut the hall interior; the extension's closed walls "
             "take over there)"),
            ("SM_DKX_1v1_HallRear_E", HALLREAR_E, "the alley closure's south face east of the extension (the old "
             "SM_DKX_1v1_HallRear split)"),
            ("SM_DKX_1v1_RearRoof", REARROOF, "caps the rear extension and its roof (out of the 1v1); bottom +5.128, "
             "above everything a player reaches inside (the armory ceiling is +5.30)")):
        p = Piece(name, "boundary", "Boundary_1v1",
                  "hall + armory round, 1v1 ONLY (the BR drops it): invisible Pawn-only blocker, hidden in game, up to "
                  "the 1v1 ceiling +20.0 - " + note,
                  pivot=(round((box[0] + box[1]) / 2, 4), round((box[2] + box[3]) / 2, 4), 0.0))
        OX_box(p.g, box, OX.BLOCK)
        p.hull_box(*box)
        p.wear = False
        p.extra = {"boxes_world": [list(box)], "onev1_only": True}
        P.append(p)
    ring = Piece("SM_DGB_Boundary_1v1", "boundary", "Boundary_1v1",
                 "invisible Pawn-only blockers of the 1v1 (spec 5.4); hall + armory round: the north side, the north "
                 "wall-top hull and the west / east sides follow the compound's back wall to Y 47-48 (+11 m)",
                 pivot=(-1.1, -1.1, 0.0))
    for b in RING_NEW:
        # the (hidden) visual boxes are inset 1 mm so no two share a vertex or an edge; the UCX hulls are exact
        OX_box(ring.g, (b[0] + 0.001, b[1] - 0.001, b[2] + 0.001, b[3] - 0.001, b[4] + 0.001, b[5] - 0.001),
               "M_DGB_Boundary")
        ring.hull_box(*b)
    ring.wear = False
    ring.extra = {"boxes_world": [list(b) for b in RING_NEW]}
    P.append(ring)
    return P


def OX_box(g, b, mat):
    x0, x1, y0, y1, z0, z1 = b
    v = [Vector((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    g.add(v, f, mat, None, jit=False)


def dgb_boundary_material():
    """The grey-box ring's own material name (M_DGB_Boundary) as a flat preview colour (the piece is hidden in game)."""
    m = bpy.data.materials.get("M_DGB_Boundary") or bpy.data.materials.new("M_DGB_Boundary")
    m.diffuse_color = (0.9, 0.2, 0.9, 0.3)
    return m


# ------------------------------------------------------------------------------------------------ main
def hall_pieces():
    P = [bay_door_open(), door_leaf_parked(), frame_open()]
    g, hulls, nb = main_back_valley()
    pc = Piece("SM_DKH_RoofUpper_BackValley", "roof", "Hall/Roof",
               "upper roof, back slope, cut for the rear extension (hall + armory round): SM_DKH_RoofUpper_Back with a "
               "notch X 14.1-29.9 north of the level valley Y 34.42 (+5.777) where the rear roof's south slope meets "
               "it, iron valley flashing on this side, end boards on the two cut eave stubs under the rear verges; "
               "collision = the back slope's slabs split the same way", pivot=(22.0, 29.0, 0.0))
    pc.g, pc.hulls, pc.wear, pc.nanite, pc.extra = g, hulls, False, True, {"valley": nb}
    P.append(pc)
    P.append(rear_frame())
    P.append(bay_clere_w("SM_DKH_Rear_Bay_ClerePlaster", 2.0,
                         "the extension's band between the head-beam transom and its lower wall plate (+3.70 to "
                         f"+{R_CLERE[1]:.3f} above the floor): sill rail, dark vertical boarding, a rail and the cream "
                         "plaster strip under the plate (SM_DKH_Bay_ClerePlaster cut to the rear roof)"))
    P.append(bay_plaster_w("SM_DKH_Rear_Bay1_Plaster", 1.0, "1 m version of SM_DKH_Bay_Plaster (the junction bay Y "
                                                             "34-35 where the extension's side walls start)"))
    P.append(bay_transom_w("SM_DKH_Rear_Bay1_Transom", 1.0, "1 m version of SM_DKH_Bay_Transom"))
    P.append(bay_clere_w("SM_DKH_Rear_Bay1_ClerePlaster", 1.0, "1 m version of SM_DKH_Rear_Bay_ClerePlaster"))
    g, hulls, nr = rear_roof()
    pr = Piece("SM_DKH_Rear_Roof", "roof", "Hall/Roof",
               "the rear extension's gable roof (kirizuma, 25 deg, roof_kit language): the north slope from the eave "
               "+5.16 at Y 45.9, the south slope from the valley Y 34.42 to the ridge line Y 39.5, verges with discs "
               "and bargeboards, a hanging board under each verge apex, soffit, closely spaced capped rafters, frieze "
               "boards over the rear wall, iron valley flashing; collision = one walkable slab per slope",
               pivot=(22.0, R_CY, 0.0))
    pr.g, pr.hulls, pr.wear, pr.nanite, pr.extra = g, hulls, False, True, nr
    P.append(pr)
    g, hulls, nd = rear_ridge()
    pd = Piece("SM_DKH_Rear_RoofRidge", "roof", "Hall/Roof",
               "the rear roof's ridge in the main ridge's profile: bed, four noshi courses of real tiles, the round "
               "cap-tile row; plain onigawara ends; collision = the ridge box (0.08 under the crown) and the two ends",
               pivot=(22.0, R_CY, 0.0))
    pd.g, pd.hulls, pd.wear, pd.nanite, pd.extra = g, hulls, False, True, nd
    P.append(pd)
    g, hulls, ng = rear_gable()
    pg = Piece("SM_DKH_Rear_RoofGable", "roof", "Hall/Roof",
               "the rear roof's west gable on the extension's side wall: a cream plaster triangle in a timber frame "
               "(beam, studs, king post) from the wall plate to the rafter underside; placed twice (the east one turned "
               "180 deg about the ridge line); collision = a thin wedge", pivot=(22.0, R_CY, 0.0))
    pg.g, pg.hulls, pg.wear, pg.extra = g, hulls, False, ng
    P.append(pg)
    P.append(window_backer())
    return P


def weld(o, dist=1e-5):
    """Merge coincident vertices (QA no_coincident_vertices): returns how many were removed."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist)
    n1 = len(bm.verts)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return n0 - n1


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def main():
    t0 = time.time()
    assert_owner("DojoHall", "claude")
    assert_owner("DojoKit", "claude")
    assert_owner("DojoOutside", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    P = hall_pieces()
    objs, stats = {}, {}
    for p in P:
        t1 = time.time()
        o, bad = geo_to_object(p, kit)
        objs[p.name] = o
        stats[p.name] = {"tris": sum(len(pl.vertices) - 2 for pl in o.data.polygons), "bad_faces": bad,
                         "sec": round(time.time() - t1, 1)}
        print("BUILT", p.name, stats[p.name], flush=True)
    merged = {"SM_DKH_RoofUpper_BackValley": weld(objs["SM_DKH_RoofUpper_BackValley"])}   # the three clips' seams
    lifted = {"SM_DKH_RoofUpper_BackValley": lift_over_armory(objs["SM_DKH_RoofUpper_BackValley"], (22.0, 29.0, 0.0)),
              "SM_DKH_Rear_Roof": lift_over_armory(objs["SM_DKH_Rear_Roof"], (22.0, R_CY, 0.0))}
    print("LIFTED", lifted, flush=True)
    for o in objs.values():
        idx = [i for i, m in enumerate(o.data.materials) if m.name == SP]
        if idx:
            djm.unit_uv(o, faces=[pl.index for pl in o.data.polygons if pl.material_index in idx])
    calm = {}
    for name in ("SM_DKH_Rear_Bay_ClerePlaster", "SM_DKH_Rear_Bay1_Plaster", "SM_DKH_Rear_Bay1_ClerePlaster",
                 "SM_DKH_DoorLeaf_Parked"):
        calm[name] = BH.calm_boards(objs[name])
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
    # ---- 1v1 pieces (the outside kit's blocker recipe)
    bk = bpy.data.collections.new("Blockers")
    sc.collection.children.link(bk)
    dgb_boundary_material()
    _orig = OX.material
    OX.material = lambda n: bpy.data.materials["M_DGB_Boundary"] if n == "M_DGB_Boundary" else _orig(n)  # noqa: E731
    BP = blocker_pieces()
    bobjs = {}
    for p in BP:
        o, bad = OX.geo_to_object(p, bk)
        o["kit"] = "greybox" if p.name.startswith("SM_DGB_") else "outside"
        bobjs[p.name] = o
        stats[p.name] = {"tris": OX.tris_of(o), "bad_faces": bad}
    # ---- QA + export (hall pieces: build_hall's recipe)
    qa, exp = {}, {}
    waive = {"uv0_tile_range", "uv_no_overlap"}
    OUTD.mkdir(parents=True, exist_ok=True)
    if not QUICK:
        for p in P:
            add_uv1(objs[p.name])
        kit.hide_viewport = False
        for p in P:
            o = objs[p.name]
            has_glow = any(m.name in (KM.GL, SP) for m in o.data.materials)
            ntri = stats[p.name]["tris"]
            r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25,
                         require_ucx=p.cls != "nocollision", overlap_method="operator" if ntri > 40000 else "sat")
            w = set(waive) | ({"texel_density"} if has_glow else set())
            fails = [c for c in r["checks"] if not c["passed"]]
            hard = [c for c in fails if c["name"] not in w]
            qa[p.name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in w}),
                          "tris": r["triangles"].get(p.name),
                          "texel_qa": next((c["detail"] for c in r["checks"] if c["name"] == "texel_density"), ""),
                          "ucx": sum(1 for c in o.children if c.name.startswith("UCX_"))}
            print("QA", p.name, len(hard), sorted({c["name"] for c in fails}), flush=True)
            for c in hard:
                print("  FAIL", p.name, c["name"], str(c["detail"])[:240], flush=True)
        hard_total = sum(len(v["hard_fails"]) for v in qa.values())
        write_json(OUTD / "qa_report.json", qa)
        print(f"QA hall rear: {len(P)} pieces, hard fails {hard_total}", flush=True)
        if "--no-export" not in ARGS and hard_total == 0:
            EXPORT_HALL.mkdir(parents=True, exist_ok=True)
            for p in P:
                o = objs[p.name]
                tris = qa[p.name]["tris"]
                if p.nanite or tris < 400:
                    r = export_fbx(str(EXPORT_HALL / f"{p.name}.fbx"), [o], kind="static", sidecar=False)
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
                r = export_fbx(str(EXPORT_HALL / f"{p.name}.fbx"), [grp], kind="static", sidecar=True)
                exp[p.name] = {"lods": 3, "lod_tris": [lq["triangles"].get(x.name) for x in [c0] + lods],
                               "lod_qa_fails": [(c["name"], c["object"], str(c["detail"])[:120]) for c in lod_hard],
                               "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
                for ob in list(tmpc.objects):
                    bpy.data.objects.remove(ob, do_unlink=True)
                bpy.data.collections.remove(tmpc)
            write_json(OUTD / "export_report.json", exp)
            print(f"exported {len(exp)} hall FBX", flush=True)
        kit.hide_viewport = True
        # blockers: back up the ring first, then the outside kit's own QA + export
        bk_dir = OUTD / "blockers"
        bk_dir.mkdir(parents=True, exist_ok=True)
        bak = OUTD / "start_backup" / "SM_DGB_Boundary_1v1.fbx"
        if not bak.exists() and (EXPORT_RING / "SM_DGB_Boundary_1v1.fbx").exists():
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(EXPORT_RING / "SM_DGB_Boundary_1v1.fbx", bak)
        no_exp = "--no-export" in ARGS
        bq, be = OX.qa_and_export([p for p in BP if not p.name.startswith("SM_DGB_")], bobjs, bk, EXPORT_OUT, bk_dir,
                                  no_export=no_exp)
        (bk_dir / "ring").mkdir(exist_ok=True)
        rq, re_ = OX.qa_and_export([p for p in BP if p.name.startswith("SM_DGB_")], bobjs, bk, EXPORT_RING,
                                   bk_dir / "ring", no_export=no_exp)
        qa.update({k: v for k, v in {**bq, **rq}.items()})
        exp.update({**be, **re_})
    # ---- layout of the new pieces (world bboxes per piece at the pivot / local origin)
    LH = {"date": "2026-10-01", "stage": "hall + armory round, stage 2 (Blender): rear extension + opened doors",
          "roof_kit": RK.VERSION, "numbers": {
              "valley": {"y": round(Y_V, 4), "z": round(Z_V, 4)},
              "rear_roof": {"eave_y": R_EAVE_Y, "eave_z": R_ZE, "pitch_deg": BH.PITCH, "verges_x": [R_VX0, R_VX1],
                            "ridge_y": R_CY, "planes_meet": round(R_ZR, 4)},
              "rear_wall_plate": [round(R_PLATE_BOT, 4), round(R_PLATE_TOP, 4)],
              "rear_clere_band_above_floor": [R_CLERE[0], round(R_CLERE[1], 4)],
              "main_rear_beam": list(MAIN_REAR_BEAM),
              "main_wall_plate": [round(BH.PLATE_BOT, 4), round(BH.PLATE_TOP, 4)],
              "gable_y0": round(gable_y0(), 4)},
          "pieces": {}}
    for p in P + BP:
        o = objs.get(p.name) or bobjs.get(p.name)
        bb = [Vector(c) for c in o.bound_box]
        LH["pieces"][p.name] = {"class": p.cls, "folder": p.folder, "note": p.note, "tris": stats[p.name]["tris"],
                                "ucx": len(p.hulls), "nanite": p.nanite, "local": p.local,
                                "wear_baked": bool(p.wear and not QUICK),
                                "pivot_world": None if p.local else [round(v, 4) for v in p.pivot],
                                "slots": [m.name for m in o.data.materials],
                                "bbox_local": [round(min(c[i] for c in bb), 4) for i in range(3)] +
                                              [round(max(c[i] for c in bb), 4) for i in range(3)],
                                "lods": exp.get(p.name, {}).get("lods"), "lod_tris": exp.get(p.name, {}).get("lod_tris"),
                                **({"extra": p.extra} if p.extra else {})}
    write_json(OUTD / "layout_hall_rear.json", LH)
    rep = {"calm_boards": calm, "welded_vertices": merged, "lifted_over_armory": lifted, "stats": stats, "seconds": round(time.time() - t0, 1), "quick": QUICK,
           "qa_hard_total": sum(len(v["hard_fails"]) for v in qa.values()) if qa else None,
           "exported": sorted(exp)}
    write_json(OUTD / "build_report.json", rep)
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND, "seconds", rep["seconds"], "qa_hard", rep["qa_hard_total"], flush=True)


if __name__ == "__main__":
    main()
