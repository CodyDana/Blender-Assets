"""ROUND 4 (2026-09-29): the DRUM PAVILION STRUCTURE (SE), SM_DKV_*, on the shared roof system
(Scripts/dojo/roof/roof_kit.py 1.3.0), the shared kit mesh module (roof/kit_mesh.py) and the shared material library.

Reference (look): References/Dojo/dojo_drum_pavilion_ref.png (AI-generated modelling reference, REFERENCE_LOG.md):
granite plinth of rough-faced ashlar courses with a front stair, four timber posts on stone pedestals, bracketed
eaves (bearing blocks + bracket arms under the eave beams, tie beams with projecting ends, short struts, knee braces),
parallel rafters with pale end grain under a plain fascia, a square pyramid (hogyo) tile roof with hip rolls ending in
round end tiles, gently upswept corners, and a plain ball finial on a square cap. No faces, crests or text.
Spec (size, wins): WorkFiles/world/DOJO_ARENA_SPEC.md 4.5: plinth X 39-43, Y 1-5, top +1.0 (a mantle surface); roof
X 38.4-43.6, Y 0.4-5.6 (5.2 x 5.2), eave +3.25, apex +4.5 (25.68 deg: walkable).
Gameplay (the grey-box's proven numbers, build_dojo_greybox.py / layout.json): the plinth mantle (+1.0 from the west
yard at (38.64, 3.0)); route 7's landing pad X 37.65-38.4, Y 2.25-3.75, flat top +3.25 at the west eave (GASP cannot
mantle onto a sloped eave, GASP_TRAVERSAL.md 4), reached by a 2.0 m mantle from the crate (X 36.35-37.35, the stone
kit's); the roof collision = the grey-box's four triangular slabs, exactly.
The taiko is a SEPARATE asset (Exports/DojoKit/Props/taiko, layout_taiko.json: stand at (41, 3, +1.0), drum top +2.85,
collision top +2.91): the pavilion only gives it its floor; every beam stays clear of it.

Deviation (flagged): the sheet's front stair faces the viewer who sees the drum body side-on, i.e. the courtyard (west)
in this layout. The west face carries route 7's crate (centred on Y 3.0, 1.0 m out) and the plinth-mantle stance at
(38.64, 3.0), so the stair is on the NORTH face (X 40-42), the drum head side, towards the east yard. The sheet's side
view shows the same stair in profile ("side steps"): the top view has one stair only, so one stair is built.

Pieces (grey-box world frame, metres; pivots in layout_pavilion.json):
  SM_DKV_Plinth      granite plinth, 3 rough-faced ashlar courses (corner bond), flush flag paving, 4-riser north stair
                     (treads +0.25 / +0.50 / +0.75, 0.40 m deep)                                   ground
  SM_DKV_Frame       stone pedestals, 4 posts, bearing blocks, bracket arms, eave beams (keta) with crossed ends, tie
                     beams (nuki) with projecting ends, struts, knee braces, the crossed ceiling ties and king post
                                                                                                   thin (posts)
  SM_DKV_RoofQuarter one roof face + its hip (instanced 4x about (41, 3)): tiles, eave end discs, sarking, parallel
                     rafters, hip rafter, fascia, hip roll ending in a round end tile, corner upsweep           roof
  SM_DKV_Finial      square cap + neck + plain ball at the apex                                      roof
  SM_DKV_EavePad     route 7's landing: a flat timber eave deck, top +3.25, 1.5 x 0.75 m, on two joists strapped to
                     the rafter tails (the hall's EaveLanding language)                              landing

Run: blender -b --factory-startup --python Scripts/dojo/pavilion/build_pavilion.py -- [--quick] [--no-export]
     [--no-context]
Out: Assets/Dojo/DojoPavilion.blend (Kit = the pavilion pieces + the showcase compound's pieces, Assembly = the
     showcase with the pavilion in place of the grey-box pavilion), Exports/DojoKit/Pavilion/SM_DKV_*.fbx,
     WorkFiles/dojo/build/shed_pavilion/{layout_pavilion.json, layout_pavilion_checks.json, pavilion/qa_report.json,
     pavilion/export_report.json, pavilion/pavilion_report.json}
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "shed"))
import sp_common as SP  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
import roof_kit as RK  # noqa: E402
import kit1_geo as K  # noqa: E402
import dojo_materials as djm  # noqa: E402
import kit_mesh as KM  # noqa: E402
from kit_mesh import Piece, cbox, member, cobox, TD, TA, GR, IR, TL  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
OUTW = SP.SPW / "pavilion"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Pavilion"
BLEND = ROOT / "Assets" / "Dojo" / "DojoPavilion.blend"

# ------------------------------------------------------------------------------------------------ numbers (world)
CX, CY = 41.0, 3.0
PX0, PX1, PY0, PY1, PTOP = 39.0, 43.0, 1.0, 5.0, 1.0
RX0, RX1, RY0, RY1 = 38.4, 43.6, 0.4, 5.6
EAVE, APEX = 3.25, 4.5
HALF = 2.6
TN = (APEX - EAVE) / HALF
PITCH = math.degrees(math.atan(TN))
CS = math.cos(math.radians(PITCH))
SN = math.sin(math.radians(PITCH))
BO = RK.base_off(PITCH)
RAF_D = 0.10
UNDER = BO + (0.004 + 0.025 + RAF_D) / CS          # collision plane -> rafter underside (vertical)
SARK_UNDER = BO + (0.004 + 0.025) / CS             # collision plane -> sarking underside
POST = 1.45                                        # post centres at CX +- POST, CY +- POST (span 2.9 m)
PW = 0.32                                          # the sheet's heavy posts (about 0.31 m at its 1.8 m scale)
RUN_POST = HALF - POST                             # 1.15: eave line -> post line
KETA_W, KETA_H = 0.22, 0.24
KETA_TOP = EAVE + (RUN_POST - KETA_W / 2) * TN - UNDER - 0.003    # rafters bear on the keta's outer arris
KETA_BOT = KETA_TOP - KETA_H
ARM_H, DAITO_H = 0.14, 0.14
ARM_BOT = KETA_BOT - ARM_H
POST_TOP = ARM_BOT - DAITO_H
NUKI = (2.745, 2.875)                              # tie beam: 1.745 m clear over the plinth (capsule 1.72)
NUKI_W = 0.14
# the sheet's bracketed eave: an outer eave purlin (degeta) ring under the rafters 0.40 m inside the eave line, carried
# by cantilever bracket arms (sashi-hijiki) through the posts and a diagonal arm at each corner; in elevation it is the
# heavy beam right under the rafter ends, with the tie beam (nuki) and struts below it (the sheet's two-beam band)
DEG_RUN, DEG_W, DEG_H = 0.40, 0.16, 0.18
DEG_TOP = EAVE + (DEG_RUN - DEG_W / 2) * TN - UNDER - 0.002
DEG_BOT = DEG_TOP - DEG_H
CANT_H, CANT_W = 0.14, 0.16
PED_TOP = 1.36
# 0.40 m treads (the hall's): the walk check's 0.35 m-radius margin run cannot centre a capsule on 0.35 m treads
STAIR = {"x": (40.0, 42.0), "treads": [((5.0, 5.40), 0.75), ((5.40, 5.80), 0.50), ((5.80, 6.20), 0.25)]}
PAD = (37.65, 38.4, 2.25, 3.75, 3.25)              # route 7 landing (grey-box SM_DGB_Landing_PavilionPad)
HIP_STOP = 0.22                                    # hips stop this far (plan, along the diagonal) from the apex
UPTURN, REACH = 0.08, 1.8
REPLACED = ["SM_DGB_Pavilion", "SM_DGB_Pavilion_NoDrum", "SM_DGB_Pavilion_Roof", "SM_DGB_Landing_PavilionPad"]
POSTS = [(CX + sx * POST, CY + sy * POST) for sx in (-1, 1) for sy in (-1, 1)]


def zcol(run):
    return EAVE + run * TN


# ------------------------------------------------------------------------------------------------ plinth
def ashlar_run(g, face, a0, a1, z0, z1, rng, lmin=0.55, lmax=1.10, depth=0.30, end_trim=(0.0, 0.0)):
    """One course of rough-faced blocks along a plinth face. face: (origin point on the face line at a=0, along unit
    vector, inward unit vector). Blocks from a0 to a1 (face coordinates), each hewn_box with its outer face pitched."""
    o, al, inw = face
    a = a0
    while a < a1 - 1e-6:
        L = rng.uniform(lmin, lmax)
        if a1 - (a + L) < lmin * 0.6:
            L = a1 - a
        b = min(a1, a + L)
        gap = 0.0045
        aa, bb = a + gap, b - gap
        c = o + al * ((aa + bb) / 2) + inw * (depth / 2 + 0.006) + Vector((0, 0, (z0 + z1) / 2))
        K.hewn_box(g, c, (al, inw, Vector((0, 0, 1))), ((bb - aa) / 2, depth / 2, (z1 - z0) / 2 - 0.003),
                   rng.uniform(0.012, 0.02), rng.randint(1, 10 ** 6), GR, exposed=("-d",),
                   pitch=rng.uniform(0.008, 0.013), rough=0.003)
        a = b


def plinth():
    p = Piece("SM_DKV_Plinth", "ground", "Pavilion",
              "granite plinth X 39-43, Y 1-5, top +1.0 (the grey-box mantle surface): three rough-faced ashlar courses "
              "in corner bond, flush flag paving, the 4-riser north stair X 40-42 (treads +0.25 / +0.50 / +0.75, "
              "0.35 m)", pivot=(CX, CY, 0.0))
    g = p.g
    rng = random.Random(4103)
    courses = [(-0.05, 0.34), (0.34, 0.67), (0.67, PTOP)]     # the bottom course is bedded 5 cm below the ground
    faces = {"S": (Vector((PX0, PY0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), PX1 - PX0),
             "N": (Vector((PX1, PY1, 0)), Vector((-1, 0, 0)), Vector((0, -1, 0)), PX1 - PX0),
             "W": (Vector((PX0, PY1, 0)), Vector((0, -1, 0)), Vector((1, 0, 0)), PY1 - PY0),
             "E": (Vector((PX1, PY0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), PY1 - PY0)}
    for k, (z0, z1) in enumerate(courses):
        dep = 0.32 if k < 2 else 0.36                      # the top course is the coping
        for key, (o, al, inw, L) in faces.items():
            full = (key in "SN") == (k % 2 == 0)          # corner bond: long faces run through on even courses
            a0, a1 = (0.0, L) if full else (dep + 0.004, L - dep - 0.004)
            ashlar_run(g, (o, al, inw), a0, a1, z0, z1, rng, depth=dep)
    # core behind the joints (the joints read as dark grooves, never see-through), and a buried base slab to the
    # plinth line so no ground-kit edge shows at the foot of the pitched faces
    cbox(g, PX0 + 0.03, PX1 - 0.03, PY0 + 0.03, PY1 - 0.03, 0.0, PTOP - 0.012, GR, ch=0.004)
    cbox(g, PX0 + 0.001, PX1 - 0.001, PY0 + 0.001, PY1 - 0.001, -0.06, 0.012, GR, ch=0.003)
    # flag paving inside the coping (top flush at +1.0: the walkable plane)
    ci = 0.36 + 0.012
    xs = [PX0 + ci, CX - 0.55, CX + 0.55, PX1 - ci]
    ys = [PY0 + ci, CY - 0.55, CY + 0.55, PY1 - ci]
    for i in range(3):
        for j in range(3):
            dz = rng.uniform(-0.003, 0.0)
            cbox(g, xs[i] + 0.004, xs[i + 1] - 0.004, ys[j] + 0.004, ys[j + 1] - 0.004, PTOP - 0.08, PTOP + dz, GR,
                 ch=0.01)
    # the north stair: three long step blocks, each split once (a joint near the middle), riser faces pitched
    sx0, sx1 = STAIR["x"]
    for k, ((ya, yb), top) in enumerate(STAIR["treads"]):
        xm = CX + rng.uniform(-0.25, 0.25)
        for (xa, xb) in ((sx0, xm), (xm, sx1)):
            zb = top - 0.25 - (0.05 if k == 2 else 0.0)                  # the bottom step bedded 5 cm
            c = Vector(((xa + xb) / 2, (PY1 + yb) / 2, (zb + top) / 2))
            K.hewn_box(g, c, (Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))),
                       ((xb - xa) / 2 - 0.004, (yb - PY1) / 2 - 0.002, (top - zb) / 2 - 0.002), 0.016,
                       rng.randint(1, 10 ** 6),
                       GR, exposed=("-d", "-a", "+a"), pitch=0.008, rough=0.002)
        p.hull_box(sx0, sx1, PY1, yb, 0.0, top)
    p.hull_box(PX0, PX1, PY0, PY1, 0.0, PTOP)
    return p


# ------------------------------------------------------------------------------------------------ frame
def pedestal(g, x, y, rng):
    """The sheet's stone pedestal: a wide base slab and a square block with a chamfered (tapered) top."""
    K.hewn_box(g, Vector((x, y, PTOP + 0.05)), (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
               (0.33, 0.33, 0.05), 0.012, rng.randint(1, 10 ** 6), GR, exposed=("-a", "+a", "-d", "+d"), pitch=0.004,
               rough=0.002)
    r0, r1 = 0.27 * math.sqrt(2), 0.20 * math.sqrt(2)
    K.lathe(g, Vector((x, y, PTOP + 0.10)), (0, 0, 1), (1, 1, 0),
            [(0.0, r0), (0.19, r0), (PED_TOP - PTOP - 0.10, r1), (PED_TOP - PTOP - 0.10, 0.0)], GR, nseg=4)


def arm(g, c, along, L=0.96, w=0.18, h=ARM_H, taper=0.12, drop=0.06):
    """Bracket arm (funahijiki): a timber whose lower edge tapers up to both ends (the boat shape)."""
    al = Vector(along).normalized()
    side = Vector((0, 0, 1)).cross(al).normalized()
    top = c.z + h / 2
    bot = c.z - h / 2
    pts = []
    for (t, z) in ((-L / 2, top), (L / 2, top), (L / 2, top - drop), (L / 2 - taper, bot), (-L / 2 + taper, bot),
                   (-L / 2, top - drop)):
        pts.append(Vector((c.x, c.y, 0)) + al * t + Vector((0, 0, z)) + side * (w / 2))
    K.prism(g, pts, side, w, TA, frame=(al, side, Vector((0, 0, 1))))


def frame():
    p = Piece("SM_DKV_Frame", "thin", "Pavilion",
              "stone pedestals, four 0.32 m posts, bearing blocks, bracket arms, eave beams (keta) crossing at the "
              "corners, tie beams (nuki, underside +2.80: 1.80 m over the plinth) with projecting ends, struts, knee "
              "braces, the crossed ceiling ties and king post over the drum (clear of the taiko: its collision top "
              "+2.91)", pivot=(CX, CY, 0.0))
    g = p.g
    rng = random.Random(733)
    for (x, y) in POSTS:
        pedestal(g, x, y, rng)
        cbox(g, x - PW / 2, x + PW / 2, y - PW / 2, y + PW / 2, PED_TOP - 0.01, POST_TOP, TA, ch=0.018)
        cbox(g, x - 0.19, x + 0.19, y - 0.19, y + 0.19, POST_TOP, POST_TOP + DAITO_H, TA, ch=0.016)   # bearing block
        zc = ARM_BOT + ARM_H / 2
        arm(g, Vector((x, y, zc)), (1, 0, 0))
        arm(g, Vector((x, y, zc)), (0, 1, 0))
        p.hull_box(x - 0.27, x + 0.27, y - 0.27, y + 0.27, PTOP, PED_TOP)
        p.hull_box(x - PW / 2, x + PW / 2, y - PW / 2, y + PW / 2, PED_TOP, KETA_BOT)
    lo, hi = CX - POST, CX + POST
    ylo, yhi = CY - POST, CY + POST
    # eave beams (keta) on the four post lines, the ends crossing 0.40 m past the corner posts
    ext = 0.40
    for y in (ylo, yhi):
        cbox(g, lo - ext, hi + ext, y - KETA_W / 2, y + KETA_W / 2, KETA_BOT, KETA_TOP, TA, ch=0.016)
    for x in (lo, hi):
        cbox(g, x - KETA_W / 2 + 0.004, x + KETA_W / 2 - 0.004, ylo - ext, yhi + ext, KETA_BOT + 0.004,
             KETA_TOP - 0.004, TA, ch=0.016)
    # outer eave purlin ring (degeta), crossing at the corners with 0.14 m projecting ends
    dlo, dhi = RX0 + DEG_RUN, RX1 - DEG_RUN
    dylo, dyhi = RY0 + DEG_RUN, RY1 - DEG_RUN
    de = 0.14
    for y in (dylo, dyhi):
        cbox(g, dlo - de, dhi + de, y - DEG_W / 2, y + DEG_W / 2, DEG_BOT, DEG_TOP, TA, ch=0.014)
    for x in (dlo, dhi):
        cbox(g, x - DEG_W / 2 + 0.004, x + DEG_W / 2 - 0.004, dylo - de, dyhi + de, DEG_BOT + 0.004, DEG_TOP - 0.004,
             TA, ch=0.014)
    # cantilever bracket arms through each post (both outward directions) and one diagonal arm to the corner crossing
    ct = DEG_BOT - 0.06                                  # a 6 cm bearing block (makito) between arm and purlin
    cb = ct - CANT_H
    for (x, y) in POSTS:
        sx = -1 if x < CX else 1
        sy = -1 if y < CY else 1
        xe = (dlo if sx < 0 else dhi) + sx * 0.16
        ye = (dylo if sy < 0 else dyhi) + sy * 0.16
        cbox(g, min(x - sx * 0.30, xe), max(x - sx * 0.30, xe), y - CANT_W / 2, y + CANT_W / 2, cb, ct, TA, ch=0.012)
        cbox(g, x - CANT_W / 2 + 0.003, x + CANT_W / 2 - 0.003, min(y - sy * 0.30, ye), max(y - sy * 0.30, ye),
             cb + 0.003, ct - 0.003, TA, ch=0.012)
        a = Vector((x, y, (cb + ct) / 2))
        b = Vector((dlo if sx < 0 else dhi, dylo if sy < 0 else dyhi, (cb + ct) / 2)) +             Vector((sx, sy, 0)).normalized() * 0.16
        member(g, a, b, CANT_W, CANT_H - 0.006, TA, ch=0.012)
        # a bearing block (makito) under each degeta over the arm end
        for (bx, by) in ((dlo if sx < 0 else dhi, y), (x, dylo if sy < 0 else dyhi)):
            cbox(g, bx - 0.085, bx + 0.085, by - 0.085, by + 0.085, ct - 0.004, DEG_BOT + 0.004, TA, ch=0.008)
    # tie beams (nuki) through the posts, ends projecting 0.25 m
    ne = 0.25
    for y in (ylo, yhi):
        cbox(g, lo - ne, hi + ne, y - NUKI_W / 2, y + NUKI_W / 2, NUKI[0], NUKI[1], TA, ch=0.012)
    for x in (lo, hi):
        cbox(g, x - NUKI_W / 2 + 0.003, x + NUKI_W / 2 - 0.003, ylo - ne, yhi + ne, NUKI[0] + 0.02, NUKI[1] + 0.02,
             TA, ch=0.012)
    # struts (tsuka) with a small bearing block between the tie beam and the eave beam, two per side
    for t in (-0.50, 0.50):
        for (x, y) in ((CX + t, ylo), (CX + t, yhi), (lo, CY + t), (hi, CY + t)):
            zt = KETA_BOT - 0.06
            cbox(g, x - 0.055, x + 0.055, y - 0.055, y + 0.055, NUKI[1] + 0.02, zt, TA, ch=0.008)
            cbox(g, x - 0.085, x + 0.085, y - 0.075, y + 0.075, zt, KETA_BOT, TA, ch=0.008)
    # knee braces (hozue): post -> tie beam underside, towards the span
    for (x, y) in POSTS:
        for d in (Vector((1 if x < CX else -1, 0, 0)), Vector((0, 1 if y < CY else -1, 0))):
            zb = NUKI[0] + (0.03 if abs(d.y) > 0.5 else 0.01)   # the Y-running tie beams sit 2 cm higher
            a = Vector((x, y, NUKI[0] - 0.42)) + d * (PW / 2 - 0.01)
            b = Vector((x, y, zb)) + d * (PW / 2 + 0.40)
            member(g, a, b, 0.09, 0.09, TA, ch=0.008)
    # ceiling ties crossing over the drum (framed into the eave beams) and the king post up to the hip rafters
    cbox(g, lo + KETA_W / 2 - 0.01, hi - KETA_W / 2 + 0.01, CY - 0.09, CY + 0.09, KETA_BOT + 0.02, KETA_TOP - 0.02, TA,
         ch=0.014)
    cbox(g, CX - 0.09, CX + 0.09, ylo + KETA_W / 2 - 0.01, yhi - KETA_W / 2 + 0.01, KETA_BOT + 0.03, KETA_TOP - 0.01,
         TA, ch=0.014)
    kp_top = APEX - SARK_UNDER - 0.14
    cbox(g, CX - 0.10, CX + 0.10, CY - 0.10, CY + 0.10, KETA_TOP - 0.01, kp_top, TA, ch=0.014)
    p.extra = {"post_centres": [[round(a, 3), round(b, 3)] for a, b in POSTS], "post_w": PW,
               "pedestal_top": PED_TOP, "post_top": round(POST_TOP, 4), "keta": [round(KETA_BOT, 4),
                                                                                  round(KETA_TOP, 4)],
               "nuki": list(NUKI), "headroom_over_plinth_under_nuki_m": round(NUKI[0] - PTOP, 3),
               "degeta": {"run_from_eave": DEG_RUN, "z": [round(DEG_BOT, 4), round(DEG_TOP, 4)]},
               "bracket_arms_z": [round(DEG_BOT - 0.06 - CANT_H, 4), round(DEG_BOT - 0.06, 4)],
               "ceiling_ties_bottom": round(KETA_BOT + 0.02, 4), "king_post_top": round(kp_top, 4)}
    return p


# ------------------------------------------------------------------------------------------------ roof
def slope_normal(face):
    """Outward normal of a roof face: 'S' (eave Y 0.4), 'E', 'N', 'W'."""
    return {"S": Vector((0, -SN, CS)), "E": Vector((SN, 0, CS)), "N": Vector((0, SN, CS)),
            "W": Vector((-SN, 0, CS))}[face]


def hip_rafter(g, corner):
    """The corner's hip rafter (sumigi) under the hip line, from 0.12 m past the eave corner (plan) to the king post;
    its top follows the sarking underside along the hip."""
    c2 = Vector((corner[0], corner[1], 0.0))
    ap = Vector((CX, CY, 0.0))
    dirp = (ap - c2).normalized()
    Ld = (ap - c2).length

    def top_at(d):          # d: plan distance from the eave corner along the diagonal
        run = d / math.sqrt(2.0)
        return zcol(run) - SARK_UNDER - 0.004
    d0, d1 = -0.12, Ld - 0.12
    a = c2 + dirp * d0
    b = c2 + dirp * d1
    ta = Vector((a.x, a.y, top_at(d0)))
    tb = Vector((b.x, b.y, top_at(d1)))
    ax = (tb - ta).normalized()
    up = Vector((0, 0, 1))
    up = (up - ax * up.dot(ax)).normalized()
    h, w = 0.22, 0.15
    member(g, ta - up * (h / 2), tb - up * (h / 2), w, h, TA, ch=0.012)


def roof_quarter():
    """The SOUTH face (eave Y 0.4, X 38.4-43.6) and the SE hip; the other faces are this piece turned 90/180/270 deg
    about (41, 3). The corner upsweep is 4-fold symmetric, so the turned pieces meet exactly."""
    p = Piece("SM_DKV_RoofQuarter", "roof", "Pavilion",
              "one face of the pyramid (hogyo) roof + its hip, instanced 4x about (41, 3): tiles in courses with round "
              "end discs at the eave, sarking, parallel rafters (pale end grain), the hip rafter, fascia, hip roll "
              "(3 noshi courses + cap row) ending in a round end tile, 8 cm corner upsweep; collision = the grey-box "
              "triangle slab (eave +3.25 -> apex +4.5)", pivot=(CX, CY, 0.0))
    W = RX1 - RX0
    rs = RK.RoofSlope((RX0, RY0), (RX1, RY0), EAVE, PITCH)
    s_top = HALF / CS
    C, n_c = RK._courses(s_top - 0.05)
    g = K.Geo()
    RK.tile_field(g, rs.sl, 0.0, W, 0.0, s_top - 0.02, C, TL, eave=True, phase=0.10, roll_margin=0.0)
    RK.sarking(g, rs, 0.0, W, -0.04, s_top, nstrips=8)
    n = max(1, int(round(W / 0.30)))
    u_raf = [W * (i + 0.5) / n for i in range(n)]
    for u in u_raf:
        s_end = min(s_top, min(u, W - u) / CS + 0.05)
        if s_end > 0.05:
            RK.rafters(g, rs, 0, 0, -0.07, s_end, u_list=[u], caps=False)
    RK.eave_trim(g, rs, 0.0, W, fascia_h=0.10)
    apex2 = (CX, CY)
    g = RK.plan_clip(g, (RX0, RY0), apex2, (CX, RY0 + 0.3))
    g = RK.plan_clip(g, (RX1, RY0), apex2, (CX, RY0 + 0.3))
    # SE hip (collision points along the hip line), ends in the round end tile; hip rafter under it
    a = Vector((RX1, RY0, EAVE))
    dplan = (Vector((CX, CY, 0)) - Vector((RX1, RY0, 0))).length
    dirp = (Vector((CX, CY, 0)) - Vector((RX1, RY0, 0))).normalized()
    bp = Vector((RX1, RY0, 0)) + dirp * (dplan - HIP_STOP)
    b = Vector((bp.x, bp.y, zcol((dplan - HIP_STOP) / math.sqrt(2.0))))
    hip_top = RK.hip_roll(g, a, b, slope_normal("S"), slope_normal("E"), courses=3, w0=0.30, dw=0.03, h=0.05,
                          roll_r=0.085, end="disc", end_r=0.115, seed=19)
    hip_rafter(g, (RX1, RY0))
    corners = [(RX0, RY0), (RX1, RY0), (RX1, RY1), (RX0, RY1)]
    fn = RK.sag_warp([], 0.0, corners=corners, upturn=UPTURN, reach=REACH)
    K.warp(g, fn)
    p.g = g
    p.hulls.append(RK.slab([(RX0, RY0, EAVE), (RX1, RY0, EAVE), (CX, CY, APEX)]))
    p.extra = {"pitch_deg": round(PITCH, 3), "course_m": round(C, 4), "courses": n_c, "rafters": n,
               "rafter_spacing_m": round(W / n, 3), "hip_cap_top_above_line_m": round(hip_top, 3),
               "corner_upturn_m": UPTURN, "upturn_reach_m": REACH, "hip_stop_from_apex_plan_m": HIP_STOP}
    return p


def finial():
    p = Piece("SM_DKV_Finial", "roof", "Pavilion",
              "apex finial: a square tile cap over the hip ends with a flared cornice, an iron neck and a plain iron "
              "ball (no symbol)", pivot=(CX, CY, 0.0))
    g = p.g
    z0 = 4.38
    cbox(g, CX - 0.30, CX + 0.30, CY - 0.30, CY + 0.30, z0, 4.66, TL, ch=0.02)
    cbox(g, CX - 0.34, CX + 0.34, CY - 0.34, CY + 0.34, 4.66, 4.715, TL, ch=0.015)
    cbox(g, CX - 0.24, CX + 0.24, CY - 0.24, CY + 0.24, 4.715, 4.75, TL, ch=0.01)
    K.lathe(g, Vector((CX, CY, 4.75)), (0, 0, 1), (1, 0, 0),
            [(0.0, 0.10), (0.02, 0.10), (0.03, 0.065), (0.07, 0.06), (0.07, 0.0)], IR, nseg=20)
    rb = 0.15
    zc = 4.80 + rb - 0.012
    prof = []
    for k in range(0, 17):
        th = -math.pi / 2 + math.pi * k / 16
        prof.append((rb * math.sin(th), rb * math.cos(th) if 0 < k < 16 else 0.0))
    K.lathe(g, Vector((CX, CY, zc)), (0, 0, 1), (1, 0, 0), prof, IR, nseg=24)
    for i in range(len(g.f)):
        if g.fm[i] == IR:
            g.fsm[i] = True
    p.hull_box(CX - 0.34, CX + 0.34, CY - 0.34, CY + 0.34, 4.30, zc + rb)
    p.extra = {"ball_r": rb, "top_z": round(zc + rb, 4), "cap": [z0, 4.75]}
    return p


# ------------------------------------------------------------------------------------------------ route 7 landing
def eave_pad(u_raf_y):
    """Route 7's landing at the west eave: X 37.65-38.4, Y 2.25-3.75, flat top +3.25 (the grey-box pad). Boards along
    the eave (Y) on two joists whose inner ends lie on two rafter tails, strapped with iron (the hall's EaveLanding)."""
    x0, x1, y0, y1, top = PAD
    p = Piece("SM_DKV_EavePad", "landing", "Pavilion",
              "route-7 landing at the pavilion's west eave: a flat timber eave deck, top +3.25, 1.5 x 0.75 m in front of "
              "the eave (GASP cannot mantle onto a sloped eave; GASP_TRAVERSAL.md 4), on two joists strapped onto the "
              "rafter tails", pivot=(x1, (y0 + y1) / 2, 0.0))
    g = p.g
    bt = 0.045
    nb = 5
    bw = (x1 - x0 - 0.02) / nb
    for i in range(nb):
        xa = x0 + 0.005 + i * bw
        cbox(g, xa + 0.003, xa + bw - 0.003, y0, y1, top - bt, top, TA, ch=0.005)
    cbox(g, x0 - 0.045, x0, y0 - 0.02, y1 + 0.02, top - 0.15, top + 0.005, TD, ch=0.008)          # front fascia
    for (ya, yb) in ((y0 - 0.045, y0), (y1, y1 + 0.045)):
        cbox(g, x0 - 0.045, x1 - 0.02, ya, yb, top - 0.13, top + 0.004, TD, ch=0.008)             # side boards
    jt = top - bt
    tail_x = RX0 - 0.07 * CS
    raf_top = EAVE - BO - (0.004 + 0.025) / CS
    for yj in u_raf_y:
        cbox(g, x0, x1 - 0.004, yj - 0.05, yj + 0.05, jt - 0.10, jt, TD, ch=0.01)                    # joist
        for s in (-1, 1):                                                                           # strap to the tail
            ys = yj + s * 0.056
            member(g, Vector((x1 - 0.13, ys, jt - 0.02)), Vector((tail_x + 0.03, ys, raf_top - 0.07)), 0.03, 0.006,
                   IR, up=(0, s, 0), ch=0.001)
        cbox(g, x0 + 0.08, x0 + 0.12, yj - 0.056, yj + 0.056, jt - 0.105, jt - 0.098, IR, ch=0.001)
    p.hull_box(x0, x1, y0, y1, top - 0.20, top)
    p.extra = {"deck_top": top, "box": list(PAD[:4]), "joists_y": [round(y, 4) for y in u_raf_y]}
    return p


def west_rafter_ys():
    """World Y of the two west-face rafters nearest Y 2.6 and 3.4 (the west face = the south face turned -90 deg: its
    rafter u runs from Y 5.6 down, u = 5.6 - Y)."""
    W = RX1 - RX0
    n = max(1, int(round(W / 0.30)))
    ys = [RY1 - W * (i + 0.5) / n for i in range(n)]
    return [min(ys, key=lambda y: abs(y - 2.62)), min(ys, key=lambda y: abs(y - 3.38))]


# ------------------------------------------------------------------------------------------------ layout
def instances():
    c = (CX, CY, 0.0)
    inst = [("SM_DKV_Plinth", c, 0.0), ("SM_DKV_Frame", c, 0.0), ("SM_DKV_Finial", c, 0.0)]
    for r in (0.0, 90.0, 180.0, 270.0):
        inst.append(("SM_DKV_RoofQuarter", c, r))
    inst.append(("SM_DKV_EavePad", (PAD[1], (PAD[2] + PAD[3]) / 2, 0.0), 0.0))
    return inst


def finial_uv(obj):
    """The finial's iron (neck + ball): a cylindrical wrap in metres / the 2 m Iron tile (5.12 px/cm), moved into a
    rust-free window of T_DJ_Iron (measured on its ORM metal channel: u 0.11-0.66, v 0.87-1.22 has no rust), so the
    plain ball reads as one dark metal, not a rust-capped ball."""
    import bmesh
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.loops.layers.uv["UVMap"]
    iron = [i for i, m in enumerate(me.materials) if m.name.split(".")[0] == IR]
    circ = 2 * math.pi * 0.15
    for f in bm.faces:
        if f.material_index not in iron:
            continue
        angs = [math.atan2(l.vert.co.y, l.vert.co.x) for l in f.loops]
        ref = angs[0]
        angs = [a + (2 * math.pi if a - ref < -math.pi else (-2 * math.pi if a - ref > math.pi else 0.0)) for a in angs]
        for l, a in zip(f.loops, angs):
            r = math.hypot(l.vert.co.x, l.vert.co.y)
            u = (a + math.pi) / (2 * math.pi) * circ / 2.0
            v = (l.vert.co.z - 4.75) / 2.0
            l[lay].uv = (0.14 + u, 0.90 + v)
    bm.to_mesh(me)
    bm.free()


def main():
    tm = SP.timer()
    assert_owner("DojoPavilion", "claude")
    sc, kit, asm = SP.new_scene()
    OUTW.mkdir(parents=True, exist_ok=True)
    P = [plinth(), frame(), roof_quarter(), finial(), eave_pad(west_rafter_ys())]
    for p in P:
        p.kit = "pavilion"
    objs, stats = {}, {}
    for p in P:
        o, bad = SP.geo_to_object(p, kit)
        if p.name == "SM_DKV_Finial":
            finial_uv(o)
        objs[p.name] = o
        stats[p.name] = {"tris": SP.tris_of(o), "bad_faces": bad}
        print("BUILT", p.name, stats[p.name], flush=True)
    for p in P:
        if stats[p.name]["tris"] >= 2000:
            p.nanite = True
            objs[p.name]["nanite"] = True
    if not QUICK:
        for p in P:
            if p.wear and p.name != "SM_DKV_RoofQuarter":
                djm.bake_wear(objs[p.name])
    pieces = {p.name: p for p in P}
    inst = SP.link_instances([SP.place(*i) for i in instances()], pieces, objs, asm, "pavilion", "v")
    kit.hide_render = True
    kit.hide_viewport = True
    LX = {
        "date": "2026-09-29", "stage": "round 4: drum pavilion structure (SE)",
        "units": "m, grey-box world frame (X east, Y north, Z up; Unreal (x*100, -y*100, z*100), yaw = -rot_z)",
        "roof_kit": {"module": "Scripts/dojo/roof/roof_kit.py", "version": RK.VERSION},
        "material_library": "Scripts/dojo/materials (M_DJ_*), textures Exports/DojoKit/Materials/Textures",
        "export_dir": "Exports/DojoKit/Pavilion",
        "pieces": {p.name: {"class": p.cls, "folder": p.folder, "note": p.note, "ucx": len(p.hulls),
                            "tris": stats[p.name]["tris"], "slots": [m.name for m in objs[p.name].data.materials],
                            "nanite": p.nanite, "kit": "pavilion", "fbx": f"Exports/DojoKit/Pavilion/{p.name}.fbx",
                            "pivot_world": [round(v, 4) for v in p.pivot],
                            **({"extra": p.extra} if p.extra else {})} for p in P},
        "instances": inst,
        "replaces_greybox": REPLACED,
        "taiko": {"layout": "WorkFiles/dojo/build/props/taiko/layout_taiko.json", "note": "separate asset; stands on "
                  "the plinth at (41, 3, +1.0), drum top +2.85 (collision +2.91); nothing of the pavilion is placed "
                  "in its box X 40.28-41.72, Y 2.22-3.78, z 1.0-2.91"},
        "numbers": {
            "plinth": [PX0, PX1, PY0, PY1, PTOP], "roof": [RX0, RX1, RY0, RY1], "eave": EAVE, "apex": APEX,
            "pitch_deg": round(PITCH, 3),
            "stair": {"face": "north", "x": list(STAIR["x"]),
                      "treads": [{"y": list(t), "top": z} for t, z in STAIR["treads"]], "risers_m": 0.25,
                      "why_north": "the west face carries route 7's crate and the plinth-mantle stance (38.64, 3.0)"},
            "posts": {"centres": [[round(a, 3), round(b, 3)] for a, b in POSTS], "w": PW, "pedestal_top": PED_TOP},
            "keta": [round(KETA_BOT, 4), round(KETA_TOP, 4)], "nuki": list(NUKI),
            "headroom_over_plinth_m": {"under_nuki": round(NUKI[0] - PTOP, 3),
                                       "under_eave_beam_keta": round(KETA_BOT - PTOP, 3),
                                       "note": "R5 (2.5 m) cannot hold under a +3.25 eave over a +1.0 plinth (spec); "
                                               "the capsule is 1.72 m"},
            "landing_pad": {"box": list(PAD[:4]), "top": PAD[4], "route": "7",
                            "marker": "Landing_PavilionPad [37.65, 38.4, 2.25, 3.75, 1.5, 3.25] (unchanged)"},
            "collision": "roof: the grey-box's four triangular slabs (eave +3.25 -> apex +4.5, 0.2 m thick); plinth "
                         "box +1.0; stair 3 boxes; pad = the grey-box pad; posts + pedestals thin; finial box",
        },
    }
    (SP.SPW / "layout_pavilion.json").write_text(json.dumps(LX, indent=1), encoding="utf-8")
    qa, exp = SP.qa_and_export(P, objs, kit, EXPORT_DIR, OUTW, quick=QUICK, no_export="--no-export" in ARGS)
    if "--no-context" not in ARGS:
        SP.compose_checks(kit, asm, REPLACED, LX, "pavilion", "SM_DKV_", SP.SPW / "layout_pavilion_checks.json",
                          "round 4 pavilion checks: the showcase with SM_DKV_* in place of the grey-box pavilion",
                          extra_walk={"north_stair_up_onto_the_plinth_to_the_drum": (0.0, [(41.0, 7.0), (41.0, 5.4),
                                                                                           (41.0, 4.2)]),
                                      "plinth_drummer_stance_across_the_north_head": (1.0, [(40.2, 4.35),
                                                                                             (41.8, 4.35)]),
                                      "CONTROL_plinth_north_face_beside_the_stair": (0.0, [(39.6, 7.0), (39.6, 4.5)])})
    rep = {"pieces": {p.name: {"class": p.cls, "tris": stats[p.name]["tris"], "nanite": p.nanite, "ucx": len(p.hulls),
                               "bad_faces": stats[p.name]["bad_faces"]} for p in P},
           "tris_unique": sum(stats[p.name]["tris"] for p in P),
           "tris_placed": sum(stats[i["piece"]]["tris"] for i in inst), "instances": len(inst),
           "qa_hard_fails": sum(len(v["hard_fails"]) for v in qa.values()) if qa else None,
           "exported": sorted(exp), "seconds": tm(), "quick": QUICK}
    (OUTW / "pavilion_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    SP.save_blend(BLEND)
    print("DONE pavilion", json.dumps(rep["pieces"]), rep["seconds"], flush=True)


if __name__ == "__main__":
    main()
