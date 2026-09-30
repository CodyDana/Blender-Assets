"""ROUND 4 (2026-09-29): the TRAINING SHED (SW corner), SM_DKS_*, and its empty 4-shelf rack (its own asset).

Reference (look): References/Dojo/dojo_training_shed_ref.png (AI-generated modelling reference, REFERENCE_LOG.md): a
lean-to of corrugated galvanised steel on steel purlins and channel rafters, a steel front beam on two round pipe posts
standing on concrete footing blocks (knee braces at the post heads), a rolled flashing along the high edge and angle
trims on the sides, a rear wall of dark vertical boards in a timber frame set in front of the compound wall (narrow end
panels with a rail), an empty 4-shelf wooden rack against it (three uprights, the middle one off-centre), a packed-earth
floor. No text or marks.
Spec (size, wins): WorkFiles/world/DOJO_ARENA_SPEC.md 4.5: X 0-6, Y 0-5 (the SW corner: the south compound wall behind,
the west wall at X 0), roof +3.0 at the wall to +2.5 at the front.
Gameplay (the grey-box's proven numbers, build_dojo_greybox.py / layout.json): the roof collision is the grey-box's two
slabs EXACTLY: the slope +3.0 (Y 0) -> +2.5 (Y 4.25) and the FLAT FRONT BAND Y 4.25-5.0 at +2.5 (route 7: crate
X 2.5-3.5, Y 5.3-6.3, top +1.25 -> a 1.25 m mantle onto the band; GASP cannot mantle onto a slope, GASP_TRAVERSAL.md 4).
The band is built as a believable feature: the sheets are cranked level over a purlin at Y 4.25 and run level over a
second purlin and the front beam to the eave (a two-pitch lean-to, the front 0.75 m level), so the flat collision is
the sheet itself. Nothing overhangs the wall tops (X < 0, Y < 0: the wall-top runs at X / Y -0.5 stay clear).

Pieces (grey-box world frame, metres):
  SM_DKS_Roof      corrugated sheets (8, lapped), top roll flashing, side angle trims, purlins, channel rafters, the front
                   I-beam, knee braces                                                        roof (2 slabs)
  SM_DKS_Post      one pipe post: concrete footing block, base plate + nuts, sleeve collars, cap plate (x2)    thin
  SM_DKS_BackWall  the rear board wall in its timber frame (posts, sill, head beam carrying the rafters, back rails,
                   end-panel stiles and rails), the rear knee braces                         building
  SM_DKS_Floor     the packed-earth floor pad (2 cm)                                         ground
  SM_DKS_Rack      the empty 4-shelf wooden rack (its own asset; placed against the board wall)            thin

Run: blender -b --factory-startup --python Scripts/dojo/shed/build_shed.py -- [--quick] [--no-export] [--no-context]
Out: Assets/Dojo/DojoShed.blend, Exports/DojoKit/Shed/SM_DKS_*.fbx, WorkFiles/dojo/build/shed_pavilion/
     {layout_shed.json, layout_shed_checks.json, shed/qa_report.json, shed/export_report.json, shed/shed_report.json}
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "shed"))
import sp_common as SP  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
import kit1_geo as K  # noqa: E402
import dojo_materials as djm  # noqa: E402
from kit_mesh import Piece, cbox, member, TD, TA, IR  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
OUTW = SP.SPW / "shed"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Shed"
BLEND = ROOT / "Assets" / "Dojo" / "DojoShed.blend"
GALV, CONC, EARTH = SP.GALVW, SP.CONC, SP.EARTH

# ------------------------------------------------------------------------------------------------ numbers (world)
X0, X1, Y0, Y1 = 0.0, 6.0, 0.0, 5.0
Z_BACK, Z_FRONT = 3.0, 2.5
Y_KINK = 4.25                                   # the grey-box band: Y 4.25-5.0 flat at +2.5 (route 7)
SL = (Z_BACK - Z_FRONT) / (Y_KINK - Y0)         # 0.1176: 6.71 deg
PITCH_C, DEPTH_C, T_SHEET = 0.12, 0.03, 0.0012     # f1: the sheet's bold corrugation (judges: no profile read at 15-20 m)
COVER = 8 * PITCH_C                             # f1: 0.96 m cover, 9 corrugations per sheet (one lapped)
UNDER_SHEET = DEPTH_C + T_SHEET + 0.0012        # crest -> purlin top
PURLIN_D, RAFTER_D = 0.075, 0.10
PURLIN_Y = [0.40, 1.35, 2.30, 3.25, 4.25, 4.85]
RAFTER_X = [0.42, 3.0, 5.58]
POST_X, POST_Y, POST_R = (0.42, 5.58), 4.85, 0.057
FOOT = (0.45, 0.30)
BEAM_D, BEAM_W = 0.14, 0.07
WALL_Y = (0.30, 0.44)                           # the board wall's frame (clear of the wall cap overhang to Y 0.24)
BOARD_T = 0.022
# the sheet's front view (seen from the courtyard: its right = our west) puts the middle upright 24-28 % from the WEST
RACK = {"x": (1.08, 4.78), "y": (0.49, 0.94), "h": 1.50, "shelves": [0.30, 0.68, 1.06, 1.46], "mid_frac": 0.26}
REPLACED = ["SM_DGB_Shed", "SM_DGB_Shed_Roof"]


def zc(y):
    """Sheet crest (= collision) height over Y."""
    return Z_BACK - (min(y, Y_KINK) - Y0) * SL


def n_at(y):
    """Unit normal of the sheet plane at Y."""
    if y >= Y_KINK:
        return Vector((0, 0, 1))
    return Vector((0, SL, 1)).normalized()


PURLIN_TOP = {y: zc(y) - UNDER_SHEET for y in PURLIN_Y}
BEAM_TOP = zc(POST_Y) - UNDER_SHEET - PURLIN_D - RAFTER_D
BEAM_BOT = BEAM_TOP - BEAM_D
HEAD_TOP = zc(WALL_Y[1]) - UNDER_SHEET - PURLIN_D - RAFTER_D - 0.002
HEAD_BOT = HEAD_TOP - 0.16


# ------------------------------------------------------------------------------------------------ roof
def corrugated_sheet(g, xa, xb, rng, lift_first=True):
    """One corrugated sheet from X xa to xb, Y 0 -> 5 (cranked level at Y 4.25): top + underside + edges, crest on
    the collision plane. Its first corrugation is lifted 1.4 mm so it laps over the neighbour's last one. UV0 (tile
    units, 2 m): U = X, V = the distance along the sheet (the galvanised set's streaks run down the slope)."""
    xs = []
    n = int(math.ceil((xb - xa) / (PITCH_C / 8) - 1e-6))
    for i in range(n + 1):
        xs.append(min(xb, xa + i * PITCH_C / 8))
    ys = [0.0, 0.70, 1.45, 2.20, 2.95, 3.70, Y_KINK, 4.62, Y1]
    dent = [0.0] + [rng.uniform(-0.0015, 0.0015) for _ in ys[1:-1]] + [0.0]

    def s_of(y):   # distance along the sheet from the high (rear) edge
        return min(y, Y_KINK) / math.cos(math.atan(SL)) + max(0.0, y - Y_KINK)

    def off(x):
        o = -DEPTH_C * (0.5 - 0.5 * math.cos(2 * math.pi * x / PITCH_C))
        if lift_first and x < xa + PITCH_C * 1.05:
            o += 0.0014
        return o
    top, bot, uv_t = [], [], []
    ou, ov = rng.uniform(0.0, 1.0), rng.uniform(0.0, 1.0)     # every sheet samples its own patch of the 2 m tile
    for j, y in enumerate(ys):
        for x in xs:
            z = zc(y) + off(x) + dent[j]
            top.append((x, y, z))
            bot.append((x, y, z - T_SHEET))
            uv_t.append((x / 2.0 + ou, s_of(y) / 2.0 + ov))
    m = len(xs)
    nt = len(top)
    verts = top + bot
    faces = []
    for j in range(len(ys) - 1):
        for i in range(m - 1):
            a = j * m + i
            faces.append((a, a + 1, a + 1 + m, a + m))                     # top (normal up: +X then +Y)
            faces.append((nt + a, nt + a + m, nt + a + 1 + m, nt + a + 1))   # underside
    for i in range(m - 1):   # rear and front edges
        a, b_ = i, i + 1
        faces.append((a, nt + a, nt + b_, b_))
        a2, b2 = (len(ys) - 1) * m + i, (len(ys) - 1) * m + i + 1
        faces.append((a2, b2, nt + b2, nt + a2))
    for j in range(len(ys) - 1):   # side edges
        a, c = j * m, (j + 1) * m
        faces.append((a, a + nt, c + nt, c)[::-1])
        a, c = j * m + m - 1, (j + 1) * m + m - 1
        faces.append((a, a + nt, c + nt, c))
    uvs = uv_t + uv_t
    g.add([Vector(p) for p in verts], faces, GALV, None, uvs=uvs)


def channel(g, a, b, up, depth, flange, t, mat=IR, open_dir=None):
    """A C-channel from a to b (centre of the web), `depth` along `up`, flanges `flange` wide towards open_dir."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    upv = Vector(up)
    upv = (upv - ax * upv.dot(ax)).normalized()
    side = Vector(open_dir) if open_dir is not None else upv.cross(ax)
    side = (side - ax * side.dot(ax) - upv * side.dot(upv)).normalized()
    L = (b - a).length
    c = (a + b) / 2
    K.obox(g, c, ax, side, upv, L / 2, t / 2, depth / 2, mat)                                         # web
    for sgn in (-1, 1):
        K.obox(g, c + upv * (sgn * (depth / 2 - t / 2)) + side * (flange / 2), ax, side, upv, L / 2 - 0.0005,
               flange / 2 - 0.0005, t / 2, mat)
    return g


def ibeam(g, a, b, depth, flange, t=0.008, mat=IR):
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    upv = Vector((0, 0, 1))
    side = upv.cross(ax).normalized()
    L = (b - a).length
    c = (a + b) / 2
    K.obox(g, c, ax, side, upv, L / 2, 0.003, depth / 2 - t, mat)
    for sgn in (-1, 1):
        K.obox(g, c + upv * (sgn * (depth / 2 - t / 2)), ax, side, upv, L / 2, flange / 2, t / 2, mat)


def angle_bar(g, a, b, w=0.05, t=0.005, up=(0, 0, 1), mat=IR):
    """An L angle a -> b: two legs w wide."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    upv = Vector(up)
    upv = (upv - ax * upv.dot(ax)).normalized()
    side = upv.cross(ax).normalized()
    L = (b - a).length
    c = (a + b) / 2
    K.obox(g, c + side * (w / 2 - t / 2), ax, side, upv, L / 2, w / 2, t / 2, mat)
    K.obox(g, c + upv * (w / 2 - t / 2) + side * 0.0005, ax, side, upv, L / 2 - 0.0005, t / 2, w / 2, mat)


def roof():
    p = Piece("SM_DKS_Roof", "roof", "Shed",
              "corrugated galvanised lean-to X 0-6, Y 0-5: +3.0 at the wall -> +2.5 at Y 4.25, cranked level over the "
              "last purlins to the eave (Y 4.25-5.0 flat at +2.5: route 7's landing band); 8 lapped sheets, top roll "
              "flashing, side angle trims, C purlins, channel rafters, the front I-beam, knee braces; collision = the "
              "grey-box's two slabs", pivot=(3.0, 2.5, 0.0))
    g = p.g
    rng = random.Random(606)
    k = 0
    xa = X0
    while xa < X1 - 1e-6:
        xb = min(X1, xa + COVER + PITCH_C)
        corrugated_sheet(g, xa, xb, rng, lift_first=k > 0)
        xa += COVER
        k += 1
    nsheets = k
    # top roll flashing along the high edge: an apron on the crests and a round roll with end caps
    cs = math.cos(math.atan(SL))
    ya, yb = 0.0, 0.24
    K.obox(g, Vector((3.0, (ya + yb) / 2, (zc(ya) + zc(yb)) / 2 + 0.003)), (1, 0, 0), (0, cs, -SL * cs),
           n_at(0.1), 3.0 + 0.01, (yb - ya) / 2 / cs, 0.0012, GALV)
    rr = 0.034
    K.lathe(g, Vector((X0 - 0.012, 0.045, zc(0.045) + rr * 0.72)), (1, 0, 0), (0, 0, 1),
            [(0.0, 0.0), (0.0, rr), (X1 - X0 + 0.024, rr), (X1 - X0 + 0.024, 0.0)], GALV, nseg=14)
    for xe, f in ((X0 - 0.012, -1), (X1 + 0.012, 1)):
        K.lathe(g, Vector((xe, 0.045, zc(0.045) + rr * 0.72)), (f, 0, 0), (0, 0, 1),
                [(0.0, 0.0), (0.0, rr * 1.12), (0.006, rr * 1.12), (0.006, 0.0)], GALV, nseg=14)
    # side angle trims (over the sheet edge, leg down the outside), following the crank
    for x, s in ((X0, 1), (X1, -1)):
        for (y0, y1) in ((0.0, Y_KINK), (Y_KINK, Y1)):
            a = Vector((x, y0, zc(y0) + 0.0025))
            b = Vector((x, y1, zc(y1) + 0.0025))
            ax = (b - a).normalized()
            nrm = n_at((y0 + y1) / 2)
            K.obox(g, (a + b) / 2 + Vector((s * 0.035, 0, 0)), ax, (1, 0, 0), nrm, (b - a).length / 2 + 0.002, 0.035,
                   0.0015, GALV)
            K.obox(g, (a + b) / 2 - nrm * 0.045 + Vector((-s * 0.0025, 0, 0)), ax, (1, 0, 0), nrm,
                   (b - a).length / 2 + 0.002, 0.0015, 0.045, GALV)
    # purlins (C, web normal to the sheets) across the rafters
    for y in PURLIN_Y:
        nrm = n_at(y - 0.01) if y <= Y_KINK else n_at(y)
        c = Vector((3.0, y, zc(y) - UNDER_SHEET)) - nrm * (PURLIN_D / 2)
        channel(g, c - Vector((2.96, 0, 0)), c + Vector((2.96, 0, 0)), nrm, PURLIN_D, 0.040, 0.004,
                open_dir=(0, -1, 0))
    # rafters (C channels) on the rear head beam and the front beam, cranked at Y 4.25
    for x in RAFTER_X:
        pts = [(WALL_Y[0], None), (Y_KINK, None), (POST_Y + 0.10, None)]
        for (ya_, _), (yb_, _) in zip(pts, pts[1:]):
            nrm = n_at((ya_ + yb_) / 2)
            a = Vector((x, ya_, zc(ya_) - UNDER_SHEET - PURLIN_D)) - nrm * (RAFTER_D / 2)
            b = Vector((x, yb_, zc(yb_) - UNDER_SHEET - PURLIN_D)) - nrm * (RAFTER_D / 2)
            channel(g, a, b, nrm, RAFTER_D, 0.05, 0.005, open_dir=(1 if x < 3.0 else -1, 0, 0))
    # front I-beam on the posts
    ibeam(g, Vector((X0 + 0.12, POST_Y, (BEAM_TOP + BEAM_BOT) / 2)), Vector((X1 - 0.12, POST_Y, (BEAM_TOP + BEAM_BOT)
                                                                            / 2)), BEAM_D, BEAM_W)
    # knee braces: post -> front beam (angles, in the post line)
    for x in POST_X:
        d = 1 if x < 3.0 else -1
        a = Vector((x + d * 0.06, POST_Y - 0.02, BEAM_BOT - 0.46))
        b = Vector((x + d * 0.52, POST_Y - 0.02, BEAM_BOT - 0.004))
        angle_bar(g, a, b, w=0.06, t=0.007, up=(0, 1, 0))        # f1: heavier, so they read (sheet)
    p.hulls.append(SP_slab([(X0, Y0, Z_BACK), (X1, Y0, Z_BACK), (X1, Y_KINK, Z_FRONT), (X0, Y_KINK, Z_FRONT)]))
    p.hulls.append(SP_slab([(X0, Y_KINK, Z_FRONT), (X1, Y_KINK, Z_FRONT), (X1, Y1, Z_FRONT), (X0, Y1, Z_FRONT)]))
    p.extra = {"sheets": nsheets, "corrugation_pitch_m": PITCH_C, "corrugation_depth_m": DEPTH_C,
               "slope_deg": round(math.degrees(math.atan(SL)), 3), "band": [Y_KINK, Y1, Z_FRONT],
               "purlins_y": PURLIN_Y, "rafters_x": RAFTER_X, "front_beam": [round(BEAM_BOT, 4), round(BEAM_TOP, 4)]}
    return p


def SP_slab(poly, th=0.2):
    pts = [Vector(q) for q in poly]
    return pts + [q - Vector((0, 0, th)) for q in pts]


# ------------------------------------------------------------------------------------------------ posts
def post():
    x, y = 0.0, 0.0     # built at the origin; instanced at (POST_X, POST_Y)
    p = Piece("SM_DKS_Post", "thin", "Shed",
              "round pipe post (0.114 m) on a 0.45 m concrete footing block (top +0.30): base plate with nuts, sleeve "
              "collars, cap plate under the front beam", pivot=(0.0, 0.0, 0.0))
    g = p.g
    fw, fh = FOOT
    cbox(g, x - fw / 2, x + fw / 2, y - fw / 2, y + fw / 2, -0.05, fh, CONC, ch=0.018)
    cbox(g, x - 0.11, x + 0.11, y - 0.11, y + 0.11, fh, fh + 0.012, IR, ch=0.002)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.lathe(g, Vector((x + sx * 0.078, y + sy * 0.078, fh + 0.012)), (0, 0, 1), (1, 0, 0),
                    [(0.0, 0.014), (0.012, 0.014), (0.012, 0.0)], IR, nseg=6)
            K.lathe(g, Vector((x + sx * 0.078, y + sy * 0.078, fh + 0.024)), (0, 0, 1), (1, 0, 0),
                    [(0.0, 0.006), (0.010, 0.006), (0.012, 0.0)], IR, nseg=6)
    top = BEAM_BOT - 0.012
    K.lathe(g, Vector((x, y, fh + 0.012)), (0, 0, 1), (1, 0, 0),
            [(0.0, POST_R), (top - fh - 0.012, POST_R), (top - fh - 0.012, 0.0)], IR, nseg=20)
    for (za, zb) in ((fh + 0.06, fh + 0.16), (top - 0.14, top - 0.04)):
        K.lathe(g, Vector((x, y, za)), (0, 0, 1), (1, 0, 0),
                [(0.0, POST_R - 0.001), (0.0, POST_R + 0.007), (zb - za, POST_R + 0.007), (zb - za, POST_R - 0.001)],
                IR, nseg=20)
    cbox(g, x - 0.10, x + 0.10, y - 0.07, y + 0.07, top, top + 0.012, IR, ch=0.002)
    for i in range(len(g.f)):
        if g.fm[i] == IR:
            g.fsm[i] = True
    p.hull_box(x - fw / 2, x + fw / 2, y - fw / 2, y + fw / 2, 0.0, fh)
    p.hull_box(x - 0.065, x + 0.065, y - 0.065, y + 0.065, fh, top + 0.012)
    p.extra = {"footing": [fw, fh], "pipe_r": POST_R, "top": round(top + 0.012, 4)}
    return p


# ------------------------------------------------------------------------------------------------ back wall
def back_wall():
    p = Piece("SM_DKS_BackWall", "building", "Shed",
              "rear wall of dark vertical boards in a timber frame (posts, sill, head beam carrying the rafters, back "
              "rails, end-panel stiles + rails), set in front of the compound wall (Y 0.30-0.47, clear of the wall "
              "cap); rear knee braces to the side rafters", pivot=(3.0, 0.37, 0.0))
    g = p.g
    rng = random.Random(2207)
    ya, yb = WALL_Y
    xl, xr = 0.28, 5.72
    for xa in (xl, xr - 0.14):
        cbox(g, xa, xa + 0.14, ya, yb, 0.0, HEAD_BOT, TD, ch=0.01)                       # frame posts
    cbox(g, xl - 0.08, xr + 0.08, ya, yb, HEAD_BOT, HEAD_TOP, TD, ch=0.012)               # head beam
    cbox(g, xl + 0.14, xr - 0.14, ya + 0.01, yb, 0.0, 0.10, TD, ch=0.01)                   # ground sill
    for zr in (0.92, 1.86):                                                                # back rails
        cbox(g, xl + 0.14, xr - 0.14, ya + 0.02, yb - 0.004, zr, zr + 0.09, TD, ch=0.008)
    # backing boards behind the joints (the sheet's boards read tight: no daylight between them)
    cbox(g, xl + 0.14, xr - 0.14, yb - 0.012, yb - 0.002, 0.10, HEAD_BOT, TD, ch=0.002)
    # boards (front face)
    x = xl + 0.14
    xe = xr - 0.14
    while x < xe - 1e-6:
        w = rng.uniform(0.16, 0.23)
        if xe - (x + w) < 0.10:
            w = xe - x
        x1 = min(xe, x + w)
        z0 = 0.10 + rng.uniform(0.0, 0.01)
        cbox(g, x + 0.0015, x1 - 0.0015, yb, yb + BOARD_T + rng.uniform(-0.002, 0.002), z0,
             HEAD_BOT - rng.uniform(0.0, 0.006), TD, ch=0.004)
        x = x1
    # end panels: a stile and a low rail each side (the sheet's narrow framed panels)
    for (sx0, sx1, rx0, rx1) in ((0.95, 1.03, xl + 0.14, 0.95), (4.97, 5.05, 5.05, xr - 0.14)):
        cbox(g, sx0, sx1, yb + BOARD_T - 0.002, yb + BOARD_T + 0.024, 0.10, HEAD_BOT, TD, ch=0.006)
        cbox(g, rx0, rx1, yb + BOARD_T - 0.002, yb + BOARD_T + 0.022, 0.60, 0.68, TD, ch=0.006)
    # rear knee braces (steel angle) from the frame posts to the side rafters
    for (x, xr_) in ((xl + 0.07, 0.42), (xr - 0.07, 5.58)):
        yr = 1.22
        zr_ = zc(yr) - UNDER_SHEET - PURLIN_D - RAFTER_D - 0.004
        angle_bar(g, Vector((x, yb + 0.004, HEAD_BOT - 0.55)), Vector((xr_, yr, zr_)), w=0.07, t=0.008, up=(1, 0, 0))
    p.hull_box(xl, xr, ya, yb + BOARD_T, 0.0, HEAD_TOP)
    p.extra = {"frame_y": list(WALL_Y), "board_face_y": round(yb + BOARD_T, 4), "head_beam": [round(HEAD_BOT, 4),
                                                                                             round(HEAD_TOP, 4)]}
    return p


def floor():
    p = Piece("SM_DKS_Floor", "ground", "Shed",
              "packed-earth floor pad under the shed (top +0.02, soft edge): the ground kit's soil set as M_DKS_PackedEarth", pivot=(3.0, 2.8, 0.0))
    g = p.g
    cbox(g, 0.10, 5.95, WALL_Y[1] + 0.03, 5.20, -0.02, 0.02, EARTH, ch=0.015)
    p.hull_box(0.10, 5.95, WALL_Y[1] + 0.03, 5.20, 0.0, 0.02)
    p.wear = False
    return p


# ------------------------------------------------------------------------------------------------ rack
def rack():
    x0, x1 = RACK["x"]
    y0, y1 = RACK["y"]
    H = RACK["h"]
    p = Piece("SM_DKS_Rack", "thin", "Shed",
              "empty 4-shelf wooden rack 3.7 x 0.45 x 1.5 m (f1: two-thirds of the bay): three uprights (front + back posts, the middle one 26 % "
              "from the west end, as the sheet), side bearers, three boards per shelf, a front rail under each shelf; its own asset",
              pivot=((x0 + x1) / 2, (y0 + y1) / 2, 0.0))
    g = p.g
    rng = random.Random(5150)
    pw = 0.07
    ups = [x0 + pw / 2, x0 + RACK["mid_frac"] * (x1 - x0), x1 - pw / 2]
    for xu in ups:
        for (ya, yb) in ((y0, y0 + pw), (y1 - pw, y1)):
            cbox(g, xu - pw / 2, xu + pw / 2, ya, yb, 0.0, H, TA, ch=0.008)
    for zt in RACK["shelves"]:
        zb_ = zt - 0.024
        for xu in ups:
            cbox(g, xu - 0.03, xu + 0.03, y0 + pw - 0.01, y1 - pw + 0.01, zb_ - 0.06, zb_, TA, ch=0.006)   # bearer
        bw = (y1 - y0 - 0.02) / 3
        for i in range(3):
            ya = y0 + 0.01 + i * bw
            cbox(g, x0 + 0.002, x1 - 0.002, ya + 0.003, ya + bw - 0.003, zb_, zt - rng.uniform(0.0, 0.003), TA,
                 ch=0.004)
        cbox(g, x0 + pw, x1 - pw, y1 - 0.004, y1 + 0.028, zb_ - 0.065, zb_ + 0.004, TA, ch=0.006)          # front rail
    p.hull_box(x0, x1, y0, y1 + 0.028, 0.0, H)
    p.extra = {"size": [round(x1 - x0, 3), round(y1 - y0, 3), H], "shelves_top_z": RACK["shelves"],
               "uprights_x": [round(u, 3) for u in ups]}
    return p


# ------------------------------------------------------------------------------------------------ layout
def instances():
    inst = [("SM_DKS_Roof", (3.0, 2.5, 0.0), 0.0), ("SM_DKS_BackWall", (3.0, 0.37, 0.0), 0.0),
            ("SM_DKS_Floor", (3.0, 2.8, 0.0), 0.0),
            ("SM_DKS_Rack", ((RACK["x"][0] + RACK["x"][1]) / 2, (RACK["y"][0] + RACK["y"][1]) / 2, 0.0), 0.0)]
    for x in POST_X:
        inst.append(("SM_DKS_Post", (x, POST_Y, 0.0), 0.0))
    return inst


def main():
    tm = SP.timer()
    assert_owner("DojoShed", "claude")
    sc, kit, asm = SP.new_scene()
    OUTW.mkdir(parents=True, exist_ok=True)
    P = [roof(), post(), back_wall(), floor(), rack()]
    for p in P:
        p.kit = "shed"
    objs, stats = {}, {}
    for p in P:
        o, bad = SP.geo_to_object(p, kit)
        objs[p.name] = o
        stats[p.name] = {"tris": SP.tris_of(o), "bad_faces": bad}
        print("BUILT", p.name, stats[p.name], flush=True)
    for p in P:
        if stats[p.name]["tris"] >= 2000:
            p.nanite = True
            objs[p.name]["nanite"] = True
    if not QUICK:
        for p in P:
            if p.wear:
                djm.bake_wear(objs[p.name])
    pieces = {p.name: p for p in P}
    inst = SP.link_instances([SP.place(*i) for i in instances()], pieces, objs, asm, "shed", "s")
    kit.hide_render = True
    kit.hide_viewport = True
    LX = {
        "date": "2026-09-29", "stage": "round 4: training shed (SW)",
        "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
        "material_library": "Scripts/dojo/materials (M_DJ_*); concrete: the modern kit's M_DKP_Modern_Concrete; "
                            "two new instances (recipes below, no new textures): M_DKS_GalvWeathered (the modern kit's "
                            "galvanised set on the library opaque master) and M_DKS_PackedEarth (the ground kit's soil "
                            "set on the ground XY master)",
        "materials": SP.RECIPES,
        "export_dir": "Exports/DojoKit/Shed",
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": stats[p.name]["tris"], "slots": [m.name for m in objs[p.name].data.materials],
                            "nanite": p.nanite, "kit": "shed", "fbx": f"Exports/DojoKit/Shed/{p.name}.fbx",
                            "pivot_world": [round(v, 4) for v in p.pivot],
                            **({"extra": p.extra} if p.extra else {})} for p in P},
        "instances": inst,
        "replaces_greybox": REPLACED,
        "numbers": {
            "footprint": [X0, X1, Y0, Y1], "roof": {"back": Z_BACK, "front": Z_FRONT, "slope_to_y": Y_KINK,
                                                   "slope_deg": round(math.degrees(math.atan(SL)), 3)},
            "front_band": {"y": [Y_KINK, Y1], "top": Z_FRONT, "route": "7",
                           "marker": "Shed_FrontBand [0, 6, 4.25, 5.0, 0, 2.5] (unchanged)",
                           "feature": "the sheets cranked level over the purlin at Y 4.25, a purlin at 4.85 and the "
                                      "front beam: a level front strip of the same roof"},
            "posts": {"x": list(POST_X), "y": POST_Y, "footing": list(FOOT)},
            "front_beam": [round(BEAM_BOT, 4), round(BEAM_TOP, 4)],
            "headroom_under_front_beam_m": round(BEAM_BOT, 3),
            "board_wall": {"frame_y": list(WALL_Y), "head_beam": [round(HEAD_BOT, 4), round(HEAD_TOP, 4)]},
            "rack": RACK,
            "greybox_east_wall_dropped": "the grey-box's steel east wall (X 5.8-6.0) is not in the sheet (open sides); "
                                         "no route used it",
            "collision": "roof: the grey-box's two slabs exactly; posts thin (footing + pipe); back wall box; floor "
                         "2 cm pad; rack one box (thin)",
        },
    }
    (SP.SPW / "layout_shed.json").write_text(json.dumps(LX, indent=1), encoding="utf-8")
    waive = {}
    qa, exp = SP.qa_and_export(P, objs, kit, EXPORT_DIR, OUTW, quick=QUICK, no_export="--no-export" in ARGS,
                               extra_waive=waive)
    if "--no-context" not in ARGS:
        SP.compose_checks(kit, asm, REPLACED, LX, "shed", "SM_DKS_", SP.SPW / "layout_shed_checks.json",
                          "round 4 shed checks: the showcase with SM_DKS_* in place of the grey-box shed",
                          extra_walk={"floor_into_the_shed_under_the_front_beam_along_the_rack":
                                      (0.0, [(1.2, 7.0), (1.2, 1.35), (4.8, 1.35)]),
                                      "CONTROL_shed_into_the_rack": (0.0, [(3.0, 2.0), (3.0, 0.8)])})
    rep = {"pieces": {p.name: {"class": p.cls, "tris": stats[p.name]["tris"], "nanite": p.nanite, "ucx": len(p.hulls),
                               "bad_faces": stats[p.name]["bad_faces"]} for p in P},
           "tris_unique": sum(stats[p.name]["tris"] for p in P),
           "tris_placed": sum(stats[i["piece"]]["tris"] for i in inst), "instances": len(inst),
           "qa_hard_fails": sum(len(v["hard_fails"]) for v in qa.values()) if qa else None,
           "exported": sorted(exp), "seconds": tm(), "quick": QUICK}
    (OUTW / "shed_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    SP.save_blend(BLEND)
    print("DONE shed", json.dumps(rep["pieces"]), rep["seconds"], flush=True)


if __name__ == "__main__":
    main()
