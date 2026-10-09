"""Detail part FRONT SIGHT: the cast sight block (a sleeve round the barrel, squarish on top where the ears land and
round below, the two thick rolled ears cast in one piece with it, the flush boss with its raised ring rim and scribed
arc, the rounded window, the blind holes on the ears' inner faces, the notched cleaning-rod lug with its round rod-end
knob, the flat-headed cross pin, the front ring collar), the sight post with its windage drum, and the cleaning rod
(its T-head sits inside the lug).

Owns the objects: cleaning_rod, front_sight_block, front_sight_post.
Authority close-ups: c3 FRONT SIGHT AND MUZZLE (SIDE) and the 3/4 view; the side trace stays the authority for
position / scale (per-part L2 gate). Interfaces: barrel radius BORE_R, rod axis ROD_Z / ROD_R (gas block, front band),
the brake's rear face X 848.82 (muzzle_brake: its detent knob sits on the brake's rear ring above our front collar
r 8.7; c3 / q34 draw it on the front collar right in front of the ear - interface note in
WorkFiles/guns/rifle/review/detail/front_sight/spec_proposal.json).

Detail pass, round 2 of the second detail loop (2026-10-05, "r2b"), from the round-1 judge's design tells on c3 / q34:
- ears 4.8 thick (EAR_IN 5.6; judge: "flat plate-like slabs" vs "thicker, rounded-top forged forms"); the outer faces
  sit at |Y| 10.4, 0.6 inside the base's 11.0, so the base shows a ledge where the ears land (c3: the ear foot on the
  sleeve's top line; judge: "thin flat ledge plate" vs "chunkier stepped casting"). Every ear outline / window edge
  is rolled: R 2.0 outer faces, R 1.4 inner faces, R 1.1 at the window floor and the cavity-floor fillets, down to
  Z 8.0 (RIM_Z0); top corners R 4.0, the knee where the vertical rear edge meets the rake R 8.0.
- base: superellipse sections (exponent 3.5 on top, 2.4 below; |Y| 11.0, Z -10.3..11.3) lofted with the rear rim
  R 2.2 / front shoulder R 1.6 (was a rounded box with flat flanks that read as one flat plate with the ears).
- window: same position (side trace), corners R 2.2 / 2.6 / 3.0 / 2.4 with the 2.0 rolled rim.
- boss r 4.2 (was 3.7) with its raised ring rim; the scribed groove (0.45 wide, 0.3 deep) is a longer sagging curve
  from the boss's lower rear edge towards the rake.
- far-ear inner face: blind hole dia 4.8 near the top front, the round-ended slot, the drum counterbore r 2.4; the
  windage drum is r 2.0 (judge: "a small dark block in the gap").
- cross pin: flat heads r 2.6, edge R 0.35, square to the curved flank and 0.42 proud of it (judge: "a larger
  flat-headed pin"; round 1 had domed heads).
- cleaning-rod lug: one rounded body (no width step), rounded rear end, a narrow notch, then a round rod-end knob with
  a rounded nose (judge: "a shorter, more rounded clip with a visible rod-end shape").
- open (R36, deferred): c3 / q34 draw the ears ~0.7-0.8 as wide front-to-back for their height; EAR_SX (env
  FS_EAR_SX) builds that variant for review, the default 1.0 keeps the side trace (L2).
Not built here: the detent knob (muzzle_brake owns it).

LAST SHAPE ROUND (2026-10-05, orchestrator ruling 7; realism judges: the windage drum spanning the ears at mid height
read as a horizontal CROSSBAR in the first-person view, with open space under it). On the real pattern (scratch/
realref photos: the drum's end is the round boss on the ear ABOVE the see-through window) the drum sits in the solid
cast BRIDGE that joins the ears' lower halves, and the post rises from it with open space between the ears above it.
So the space between the ears is solid up to BRIDGE_Z (just over the drum; the window still tunnels through it, the
side silhouette is unchanged), the drum is inside it (only its ends show, as the bosses), and the post with its
threaded shank stands in a hole in the bridge top up to the unchanged tip (Z 45.0, B4). A first try put the drum low
at the floor (Z 11.6): its post then crossed the window (L3 window bbox and per-part IoU failed) -- and the photos
put the drum above the window.
"""
from __future__ import annotations

import os

import numpy as np

from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP
from rifle_parts2 import BORE_R, ROD_Z, ROD_R, ycyl, xcyl

# Ear front-to-back scale about the front edge X 833 (1.0 = the side trace, the L2 authority; c3 / q34 draw the ears
# ~0.7-0.8 as wide for their height - an open proportion conflict, see review/detail/front_sight/spec_proposal.json).
EAR_SX = float(os.environ.get("FS_EAR_SX", "1.0"))


def sx(x):
    return 833.0 + (x - 833.0) * EAR_SX


def ear_out_y(z):
    """|Y| of the ears' (tapered) outer faces at height z: ONE plane per side (not clamped, so the prism's outline caps
    stay planar; below Z 11 the hood is inside the base anyway)."""
    u = (z - EAR_TAPER_Z0) / (EAR_TOP_Z - EAR_TAPER_Z0)
    return EAR_OUT + u * (EAR_OUT_TOP - EAR_OUT)


def ear_face_normal(side):
    """Outward unit normal of the tapered outer face on side +-1 (y, z components)."""
    k = (EAR_OUT - EAR_OUT_TOP) / (EAR_TOP_Z - EAR_TAPER_Z0)
    n = np.array([0.0, float(side), k])
    return n / np.linalg.norm(n)


EAR_IN, EAR_OUT = 5.2, 10.0       # integration r2b: ledge 0.6 -> 1.0 (judge: c3 draws the ear as a post with a shoulder where it meets the block; 1.4 left the block non-manifold); ears 4.8 thick
                                  # the base shows a ledge where they land, c3; the TOP silhouette there is the base)
# DETAIL FIX (2026-10-05, user checklist 2): the tower TAPERS (real cast pattern: the ears' outer faces lean in toward
# the top, the ears ~2.8 thick at the top / 4.8 at the base; r2b's constant-width ears read as two flat slabs); the
# outer faces are planes through |Y| EAR_OUT at Z EAR_TAPER_Z0 and EAR_OUT_TOP at the top Z 49.4 (planar caps)
EAR_OUT_TOP = 8.0
EAR_TAPER_Z0, EAR_TOP_Z = 11.0, 49.4
EAR_RIM = 1.4                     # rolled round on every ear outline / window edge (weighted bevel, weight 1 = 1.4 mm;
                                  # detail fix 2.0 -> 1.4: the thinner top must keep a flat after both rims: worn round tops)
W_IN, W_LOW = 0.7, 0.55           # rim weights: inner faces (0.98 mm), window floor / cavity floor edges (0.77 mm)
FLOOR_Z = 11.9                    # (round 2b cavity floor; the rim / edge weight predicates still key to it)
BRIDGE_Z = 33.4                   # last shape round: the cast bridge between the ears' lower halves (cavity floor)
RIM_Z0 = 8.0                      # the ears' rolled rims run down to here (the outer faces meet the base at Z ~7.1)
WIN_Z0 = 12.2                     # window floor
BOX_W, BOX_ZT, BOX_ZB = 11.0, 11.3, -10.3
BOX_NT, BOX_NB = 3.5, 2.4         # r2b: base section = superellipse halves (squarish top that takes the ears, round
                                  # sleeve-like lower half; c3 / q34 shade it as a round cast sleeve)
BOX_NPTS = 34                     # detail fix: 40 -> 34 (triangle budget)
BOX_X = (806.1, 837.0)
BOX_RIM = (2.2, 1.6)              # rear rim, front shoulder
RING = (836.6, 839.6, 9.7)        # ring collar in front of the box
COLLAR_R, COLLAR_X1 = 8.7, 842.8
FRONT_COLLAR_R = 8.7              # the collar under the brake's detent knob (integration round: was 10.1, as wide as the
                                  # brake, so the brake read long with a seam; c3: sleeve band -> narrow ring -> brake)
HEAD_X = (811.0, 815.5)           # rod T-head inside the lug
HEAD_W = 2.5
BOSS = (sx(824.7), 29.9, 4.2)         # X, Z, radius (r2b: c3 boss larger, 3.7 -> 4.2)
BOSS_RIM_H, BOSS_FACE_H, BOSS_RIM_W = 0.62, 0.45, 0.4   # integration r2b: 0.32 / 0.18 -> 0.62 / 0.45 (judge: c3 draws the circle as a raised plug with a rim)
BOSS_H, BOSS_EDGE = 1.0, 0.3      # DETAIL FIX: a raised round windage-drum boss (flat face 1.0 proud of the tapered face,
                                  # 0.3 rolled edge) in place of r2b's flush disc with a ring rim
# scribed curve leaving the boss's lower rear edge towards the rake (c3: tangent-ish to the boss, sagging slightly)
SCRIBE = [(sx(824.7) - 3.6, 27.2), (sx(824.7) - 5.2, 26.55), (sx(824.7) - 6.9, 26.35), (sx(824.7) - 8.6 * min(1.0, EAR_SX + 0.1), 26.75)]
SCRIBE_W, SCRIBE_D = 0.45, 0.3
DRUM = (sx(825.3), 31.0, 2.0)         # windage drum X, Z, radius (inside the bridge since the last shape round)
POST_HOLE = (1.6, 3.0)                # last shape round: the post's hole in the bridge top (radius, depth)
EAR_TOP_R = float(os.environ.get("FS_EAR_TOP_R", "7.0"))   # ear top corners: last shape round 5.0 -> 7.0 (rounded tops; per-part L2 0.9517, 6.0 left a boolean crack)
CBORE_R = 2.4                         # r2b: drum 2.8 -> 2.0 (judge: a dark block in the gap; c3 shows an open slot)
TOP_HOLE = (sx(829.4), 43.4, 2.4, 2.0)                           # X, Z, radius, depth (blind, inner faces)
SLOT = G.rounded_rect(sx(829.3), sx(831.7), 27.5, 34.5, 0.49 * (sx(831.7) - sx(829.3)), 3)     # round-ended slot on the inner faces, 1.4 deep
PIN = (830.5, -5.0, 2.0)          # cross pin X, Z, radius
DET_X, DET_R, DET_H = 845.2, 1.9, 2.7   # detail fix: detent housing on the front collar (top Z 9.7, pin to 10.2)
PIN_HEAD = (2.6, 0.42)            # r2b: flat pin head radius / proud of the flank (c3: a larger flat-headed pin)


# ======================================================================================== outlines
def ear_outline() -> np.ndarray:
    """Ear side outline (XZ): rear rake (side trace), vertical upper rear edge, rounded top corners, flat top, vertical
    front edge. Below the box top the outline steps forward to X 807.6 so it stays inside the box's rear rim."""
    xr = 806.3 + (816.5 - 806.3) * (11.0 - 9.6) / (37.0 - 9.6)          # rake at Z 11.0
    P = np.array([(sx(807.6), 2.0), (833.0, 2.0), (833.0, 49.4), (sx(816.5), 49.4), (sx(816.5), 37.0), (sx(xr), 11.0),
                  (sx(807.6), 9.0)], float)
    return G.fillet(G.ccw(P), 1.0, 7, radii=[0.0, 0.0, EAR_TOP_R, EAR_TOP_R, 8.0, 0.0, 0.0])   # detail fix R 5; last round EAR_TOP_R


def window_outline() -> np.ndarray:
    # stage-7 fix round (craft review: 'a near-rectangle; the sheet's window is a trapezoid whose rear edge runs
    # parallel to the tower's raked rear, narrow top, wide bottom'): the rear edge now runs exactly with the rake
    # (ear_outline: 10.2 mm over 27.4 mm, i.e. 3.57 mm over the window's 9.6 mm), the bottom 0.6 mm wider at the rear,
    # and the corner rounds tighter (2.2-3.0 -> 1.2-1.8) so the slant reads instead of a rounded box
    rake = (816.5 - 806.3) / (37.0 - 9.6)
    xb = 812.8
    P = np.array([(sx(xb), WIN_Z0), (sx(827.2), WIN_Z0), (sx(827.2), 21.8), (sx(xb + rake * (21.8 - WIN_Z0)), 21.8)],
                 float)
    return G.fillet(G.ccw(P), 1.0, 5, radii=[1.2, 1.6, 1.8, 1.4])


def box_section(inset=0.0) -> np.ndarray:
    """YZ section of the base (CCW in YZ), shrunk by `inset` (constant vertex count): two superellipse halves about
    Z (BOX_ZT + BOX_ZB) / 2, half width BOX_W, exponent BOX_NT above (squarish shoulders that take the ears) and
    BOX_NB below (a round sleeve). Points are spaced by arc length plus turning, so the shoulders get the vertices."""
    zc = 0.5 * (BOX_ZT + BOX_ZB)
    a, b = BOX_W - inset, 0.5 * (BOX_ZT - BOX_ZB) - inset
    t = np.linspace(0.0, 2.0 * np.pi, 4000, endpoint=False)
    c, sn = np.cos(t), np.sin(t)
    n = np.where(sn >= 0.0, BOX_NT, BOX_NB)
    P = np.c_[a * np.sign(c) * np.abs(c) ** (2.0 / n), zc + b * np.sign(sn) * np.abs(sn) ** (2.0 / n)]
    d = np.diff(np.vstack([P, P[:1]]), axis=0)
    seg = np.linalg.norm(d, axis=1)
    ang = np.arctan2(d[:, 1], d[:, 0])
    turn = np.abs((np.diff(np.r_[ang, ang[0]]) + np.pi) % (2.0 * np.pi) - np.pi)
    w = seg + 6.0 * turn
    m = np.r_[0.0, np.cumsum(w)[:-1]]
    u = np.linspace(0.0, w.sum(), BOX_NPTS if LOD.LEVEL == 1 else LOD.ring(BOX_NPTS), endpoint=False)     # LOD2: fewer section points (LOD1 keeps them: a 17-point box met the 16-sided collars in coincident faces)
    idx = np.searchsorted(m, u).clip(0, len(P) - 1)
    return G.ccw(P[idx])


# ======================================================================================== solids
def base_box() -> MS.Mesh:
    """The cast base as one loft of rounded-rectangle sections along X with a rounded rear rim and front shoulder."""
    x0, x1 = BOX_X
    rr, rf = BOX_RIM
    rings = []
    for th in np.radians([0.0, 30.0, 60.0, 90.0]):
        rings.append((x0 + rr * (1 - np.cos(th)), rr * (1 - np.sin(th))))
    for th in np.radians([90.0, 60.0, 30.0, 0.0]):
        rings.append((x1 - rf * (1 - np.cos(th)), rf * (1 - np.sin(th))))
    R = []
    for x, ins in rings:
        S = box_section(ins)
        R.append(np.c_[np.full(len(S), x), S[:, 0], S[:, 1]])
    return MS.loft(R)


def front_collars() -> MS.Mesh:
    """Ring collar r 9.7 (rounded front edge R 0.6) then the collar r 8.7 to X 842.8, one revolve."""
    x0, x1, r = RING
    prof = [(0.0, 0.0), (0.0, r), (x1 - x0 - 0.6, r)]
    prof += [(x1 - x0 - 0.6 + 0.6 * np.sin(t), r - 0.6 + 0.6 * np.cos(t)) for t in np.linspace(0.0, np.pi / 2, 4)][1:]
    prof += [(x1 - x0, COLLAR_R), (COLLAR_X1 - x0, COLLAR_R), (COLLAR_X1 - x0, 0.0)]
    return MS.revolve(prof, (x0, 0.0, 0.0), (1.0, 0.0, 0.0), 32, phase_deg=5.625)


def hood() -> MS.Mesh:
    """Ears + floor as ONE cast solid: the ear outline at full width; the space between the ears (cavity, cut later)
    leaves the two ears standing on the floor. DETAIL FIX: the outer faces taper in toward the top (ear_out_y: planar,
    so the caps stay flat n-gons)."""
    m = MS.prism(ear_outline(), -EAR_OUT, EAR_OUT)
    V = m.verts()
    V[:, 1] = np.sign(V[:, 1]) * np.array([ear_out_y(z) for z in V[:, 2]])
    out = MS.Mesh()
    out.add_verts(V)
    out.F = list(m.F)
    return out


def cavity() -> MS.Mesh:
    return MS.box(800.0, 840.0, -EAR_IN, EAR_IN, BRIDGE_Z, 60.0)


def _ybetween(s, a, b):
    return min(s * a, s * b), max(s * a, s * b)


def inner_face_cuts() -> list:
    """On each ear's inner face: the drum's counterbore, the large blind hole near the top front and the round-ended
    vertical slot (c3 / q34 show them on the far ear between the ears)."""
    out = []
    # last shape round: the post's hole in the bridge top (the drum is inside the bridge; the counterbores and the
    # round-ended slot of round 2b straddled the bridge top and are gone)
    out.append(MS.cylinder((DRUM[0], 0.0, BRIDGE_Z - POST_HOLE[1]), (DRUM[0], 0.0, BRIDGE_Z + 2.0), POST_HOLE[0], 16))
    for s in (-1, 1):
        x, z, r, d = TOP_HOLE
        out.append(ycyl(x, z, r, *_ybetween(s, EAR_IN - 1.0, EAR_IN + d), 20))
    return out


def scribe_outline() -> np.ndarray:
    """Closed XZ outline of the scribed curve: the polyline SCRIBE smoothed (Chaikin), offset +-SCRIBE_W / 2 with
    round ends; it starts under the boss rim so the groove runs out of the boss edge."""
    P = np.asarray(SCRIBE, float)
    for _ in range(3):                                  # open Chaikin
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1])
        P = np.array(Q)
    L = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]     # resample: 8 even points (tris)
    u = np.linspace(0.0, L[-1], 8)
    P = np.c_[np.interp(u, L, P[:, 0]), np.interp(u, L, P[:, 1])]
    h = SCRIBE_W / 2
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.c_[-t[:, 1], t[:, 0]]
    left, right = P + h * nrm, P - h * nrm
    a_end = np.degrees(np.arctan2(nrm[-1, 1], nrm[-1, 0]))
    end = G.arc(P[-1, 0], P[-1, 1], h, a_end, a_end - 180.0, 4)[1:-1]
    return G.ccw(np.vstack([left, end, right[::-1]]))


def arc_cuts() -> list:
    """The scribed curve on each ear's outer face (a SCRIBE_D deep groove, real geometry)."""
    P = scribe_outline()
    yf = ear_out_y(26.7)                                 # detail fix: the tapered face at the scribe's height
    return [MS.prism(P, *_ybetween(s, yf - SCRIBE_D, yf + 1.0)) for s in (-1, 1)]


def _near_details(x, z):
    """True near the boss + arc, the counterbore, the top hole and the slot (their own rounds / no bevel)."""
    d_boss = (x - BOSS[0]) ** 2 + (z - BOSS[1]) ** 2
    near_scribe = min((x - a) ** 2 + (z - b) ** 2 for a, b in SCRIBE) < 1.3 ** 2
    return (d_boss < (BOSS[2] + 0.6) ** 2 or near_scribe or (x - DRUM[0]) ** 2 + (z - DRUM[1]) ** 2 < (CBORE_R + 0.4) ** 2
            or (x - TOP_HOLE[0]) ** 2 + (z - TOP_HOLE[1]) ** 2 < (TOP_HOLE[2] + 0.4) ** 2
            or (sx(829.3) - 0.4 < x < sx(831.7) + 0.4 and 27.1 < z < 34.9))


def edge_weight(mid, d, n1, n2, dih):
    """The 0.6 process chamfer on every remaining sharp edge (dihedral >= 35), except the bore's edges (hidden in the
    barrel contact), the collars, the cross pin, the rod seat, the ear details and the ears' rims / base creases."""
    x, y, z = mid
    if dih < 35.0:
        return 0.0
    r = (y * y + z * z) ** 0.5
    if r < 7.9:                                          # bore edges
        return 0.0
    if x > 836.4 and r < 10.2:                           # ring collar / collar seams
        return 0.0
    if abs(x - PIN[0]) < PIN_HEAD[0] + 0.5 and abs(z - PIN[1]) < PIN_HEAD[0] + 0.5 and abs(y) > 8.0:   # pin head (own round)
        return 0.0
    if (y * y + (z - ROD_Z) ** 2) < (ROD_R + 0.6) ** 2 or (HEAD_X[0] - 0.2 < x < HEAD_X[1] + 0.2 and abs(y) < HEAD_W + 0.2
                                                           and abs(z - ROD_Z) < 2.8):
        return 0.0                                       # rod bore and the hidden head seat
    if abs(y) > EAR_IN - 1.0 and z > 20.0 and _near_details(x, z):
        return 0.0
    if EAR_IN - 0.25 <= abs(y) <= EAR_OUT + 0.25 and z > FLOOR_Z - 0.3:      # (the ears' rims; the bridge top too)
        return 0.0                                       # the ears' rims (the rim pass rounded them)
    return 1.0


def rim_weight(mid, d, n1, n2, dih):
    """Weighted rolled round on the ears: every outline / window edge on the ear faces (|Y| EAR_IN / EAR_OUT) above
    the box top (1.5 outer, 1.2 inner, 0.9 at the window floor and the cavity floor's fillets); not the details."""
    x, y, z = mid
    if dih < 45.0 or abs(y) < EAR_IN - 0.15 or abs(y) > ear_out_y(z) + 0.15:
        return 0.0
    if z < RIM_Z0:                                       # base creases (ear faces into the base's shoulders)
        return 0.0
    if _near_details(x, z):
        return 0.0
    if z < 13.0:
        return W_LOW
    if abs(y) < EAR_IN + 0.15 and abs(abs(y) - EAR_IN) < 0.15:
        return W_IN
    return 1.0


def boss(side) -> MS.Mesh:
    """DETAIL FIX (user checklist 2): a raised round windage-drum boss on the tapered outer face, square to it: a flat
    face BOSS_H proud with a BOSS_EDGE rolled edge (r2b: a flush disc with a raised ring rim)."""
    x, z, r = BOSS
    n = ear_face_normal(side)
    e = 0.6                                              # rooted 0.6 inside the face
    o = np.array([x, side * ear_out_y(z), z]) - n * e
    h = e + BOSS_H
    c = BOSS_EDGE
    prof = [(0.0, 0.0), (0.0, r), (h - c, r), (h - c * 0.29, r - c * 0.29), (h, r - c), (h, 0.0)]
    return MS.revolve(prof, tuple(o), tuple(n), 24)


def _flank_y(z) -> float:
    """|Y| of the base's (uninset) side at height z."""
    zc = 0.5 * (BOX_ZT + BOX_ZB)
    b = 0.5 * (BOX_ZT - BOX_ZB)
    n = BOX_NT if z >= zc else BOX_NB
    return BOX_W * max(0.0, 1.0 - abs((z - zc) / b) ** n) ** (1.0 / n)


def _flank_normal(z):
    """Unit outward normal (ny, nz) of the base's +Y flank at height z."""
    h = 0.01
    dy = (_flank_y(z + h) - _flank_y(z - h)) / (2 * h)
    n = np.array([1.0, -dy])
    return n / np.linalg.norm(n)


def cross_pin() -> list:
    """Cross pin through the base below the barrel axis; flat heads (rounded edge R 0.35) square to the curved flank,
    standing PIN_HEAD[1] proud of it (c3: a larger flat-headed pin)."""
    x, z, r = PIN
    rh, hp = PIN_HEAD
    yf = _flank_y(z)
    ny, nz = _flank_normal(z)
    out = [ycyl(x, z, r, -yf + 0.5, yf - 0.5, 16)]
    L = 1.6 + hp
    prof = [(0.0, 0.0), (0.0, rh), (L - 0.35, rh), (L - 0.1, rh - 0.1), (L, rh - 0.35), (L, 0.0)]
    for s in (-1, 1):
        o = (x, s * (yf - 1.6 * ny), z - 1.6 * nz)          # starts 1.6 inside the flank, along the normal
        out.append(MS.revolve(prof, o, (0.0, s * ny, nz), 20))
    return out


def rod_lug() -> MS.Mesh:
    """c3's cleaning-rod lug as one loft of rounded YZ sections (X, half width, bottom Z, corner r); the top runs
    inside the base. r2b (judge: 'a shorter, more rounded clip with a visible rod-end shape'): one rounded body with
    a rounded rear end, a narrow notch, then a round rod-end knob with a rounded nose (no width step)."""
    top = -8.0
    # DETAIL FIX (user checklist 2): a STEPPED lug: the full-width rear body, a step in to a narrower, 0.6 mm shallower
    # front tier (the rod seat), the notch, the rod-end knob, the rounded nose (r2b: one rounded body)
    st = [(809.9, 3.0, -10.6, 1.2), (810.4, 3.4, -13.6, 1.8), (811.4, 3.8, -15.1, 2.3), (812.6, 3.8, -15.7, 2.5),
          (820.6, 3.8, -15.7, 2.5), (821.6, 3.6, -15.5, 2.3), (822.6, 3.0, -15.1, 1.9),     # the step (1.0 mm runs: the 0.6 chamfer must fit)
          (829.0, 3.0, -15.1, 1.9), (830.0, 2.9, -14.9, 1.8),
          (830.7, 2.1, -14.0, 1.2), (832.5, 2.1, -14.0, 1.2),            # the notch
          (833.1, 3.0, -15.1, 2.3), (835.0, 3.0, -15.1, 2.3),            # round rod-end knob
          (836.2, 2.7, -14.7, 2.1), (837.0, 2.0, -13.8, 1.6), (837.5, 1.1, -12.4, 0.9)]   # rounded nose
    rings = []
    for x, w, zb, r in st:
        S = G.rounded_rect(-w, w, zb, top, r, 2)
        rings.append(np.c_[np.full(len(S), x), S[:, 0], S[:, 1]])
    n = {len(r) for r in rings}
    assert len(n) == 1, n
    return MS.loft(rings)


# ======================================================================================== parts
def cleaning_rod() -> PartDef:
    r = xcyl(0.0, ROD_Z, ROD_R, 641.0, HEAD_X[0] + 2.0, 16)
    head = MS.box(HEAD_X[0], HEAD_X[1], -HEAD_W, HEAD_W, ROD_Z - 2.6, ROD_Z + 2.6)
    return PartDef("cleaning_rod", [r], unions=[head], cls="M-round", recipe=[(0.4, 2, 30.0)])


# rolled rims first (2 segments), then the process chamfer on the remaining sharp visible edges
RECIPE = [(EAR_RIM, 2, "W", rim_weight), (0.6, 1, "W", edge_weight)]     # rims 2 segments (budget; 3 looked the same at c3)


def front_sight_block() -> PartDef:
    front_collar2 = MS.cylinder((842.6, 0, 0), (848.78, 0, 0), FRONT_COLLAR_R, 32, phase_deg=5.625)   # off the collar's vertex planes
    # DETAIL FIX (user checklist 3): the brake's detent as a small boss at the front sight's base (the real pattern's
    # spring detent sits in the sight base and bears on the brake): a round housing r 1.9 standing 1.0 proud of the
    # front collar with a rolled top, the pin head r 0.75 in it (replaces the brake's detent block / this plunger)
    plunger = MS.revolve([(0.0, 0.0), (0.0, DET_R), (DET_H - 0.3, DET_R), (DET_H - 0.09, DET_R - 0.09), (DET_H, DET_R - 0.3),
                          (DET_H, 0.75), (DET_H + 0.38, 0.75), (DET_H + 0.5, 0.63), (DET_H + 0.5, 0.0)],
                         (DET_X, 0.0, 7.0), (0.0, 0.0, 1.0), 16)
    unions = [base_box(), front_collars(), rod_lug(), front_collar2]
    if LOD.LEVEL < 2:                     # LOD2: the bosses, detent and cross pin are painted only (sub-pixel at 6.7 m)
        unions += [boss(1), boss(-1), plunger] + cross_pin()
    p = PartDef("front_sight_block", [hood()], unions=unions, cls="M-chamfer-front", recipe=RECIPE,
                spec_id="front_sight_block")
    win = window_outline()
    p.cutters = [xcyl(0.0, 0.0, BORE_R + GAP, 800.0, 850.0, 48), cavity(),      # 48: facets clear the barrel's vertices
                 MS.prism(win, -12.0, 12.0),
                 MS.box(HEAD_X[0] - 0.5, HEAD_X[1] + GAP,     # 0.5 behind the head: room for its rod fillet
                         -HEAD_W - GAP, HEAD_W + GAP, ROD_Z - 2.6 - GAP, ROD_Z + 2.6 + GAP),
                 xcyl(0.0, ROD_Z, ROD_R + GAP, 800.0, HEAD_X[0] + 0.1, 16)]
    if LOD.LEVEL < 2:
        p.cutters += inner_face_cuts()
    p.post_cutters = [] if (os.environ.get("FS_NOSCRIBE") or LOD.LEVEL >= 2) else arc_cuts()     # after the bevels: a crisp scribed line
    return p


def flat_face_normals(ob, tol=0.99995) -> int:
    """Corner normals of every planar face facing +-Y (the ear faces, the boss and the groove floors) := the face
    normal. The booleans leave long sliver triangles across the ear faces; weighted normals then smear the small
    grooves' and holes' rim normals across them (round-2 r2i1-r2i3: a dark wedge beside the boss)."""
    me = ob.data
    cn = np.array([c.vector[:] for c in me.corner_normals], float)
    n = 0
    # detail fix: the tapered outer faces (and the boss faces square to them) are planar too
    taper = [ear_face_normal(sd) for sd in (-1, 1)]
    for poly in me.polygons:
        pn = np.array(poly.normal[:])
        if abs(poly.normal[1]) > tol or any(float(pn @ t) > tol for t in taper):
            for li in poly.loop_indices:
                cn[li] = poly.normal[:]
            n += 1
    me.normals_split_custom_set([tuple(v) for v in cn])
    return n


def front_sight_block_obj(coll, offset):
    from gunlib.parts import build_part
    p = front_sight_block()
    ob = build_part(p, coll, offset)
    ob["fs_flat_faces"] = flat_face_normals(ob)
    return ob


def front_sight_post() -> PartDef:
    # last shape round: the post stands in its hole in the bridge top (the drum inside the bridge is not modelled:
    # unseen): a threaded shank r 1.45 (0.15 off the hole wall, 0.2 off its floor), a short taper, the round post r 1.0
    # to the tip (Z 45.0, B4 / L4 sight line)
    z0 = BRIDGE_Z - POST_HOLE[1] + 0.2
    post = MS.revolve([(0.0, 0.0), (0.0, 1.45), (BRIDGE_Z + 2.4 - z0, 1.45), (BRIDGE_Z + 4.0 - z0, 1.0),
                       (45.0 - z0, 1.0), (45.0 - z0, 0.0)], (DRUM[0], 0.0, z0), (0.0, 0.0, 1.0), 12)
    return PartDef("front_sight_post", [post], cls="M-round", recipe=[(0.3, 1, 30.0)],
                   spec_id="front_sight_ears_post")


# ======================================================================================== module interface
OBJECTS = ('cleaning_rod', 'front_sight_block', 'front_sight_post')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c3', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("cleaning_rod", cleaning_rod), ("front_sight_block", front_sight_block_obj), ("front_sight_post", front_sight_post),)}
