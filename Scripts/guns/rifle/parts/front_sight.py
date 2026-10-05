"""Detail part FRONT SIGHT: the cast sight block (a boxy base round the barrel with squared, rounded shoulders, the two
thick rolled ears cast in one piece with it, the flush boss with its raised ring rim and scribed arc, the rounded
window, the blind holes on the ears' inner faces, the stepped and notched cleaning-rod lug, the domed cross pin, the
front ring collar), the sight post with its windage drum, and the cleaning rod (its T-head sits inside the lug).

Owns the objects: cleaning_rod, front_sight_block, front_sight_post.
Authority close-ups: c3 FRONT SIGHT AND MUZZLE (SIDE) and the 3/4 view; the side trace stays the authority for
position / scale (per-part L2 gate). Interfaces: barrel radius BORE_R, rod axis ROD_Z / ROD_R (gas block, front band),
the brake's rear face X 848.82 (muzzle_brake: its detent latch sits on the brake's rear ring and hangs 0.03 mm above
our front collar r 10.1 at X 847.6-848.82, so nothing of ours rises above r 10.1 there).

Detail pass round 2 (2026-10-05), every change from the round-1 blind judge's design tells checked on c3 / q34:
- base: a loft of rounded-box sections (|Y| 11.0, Z -10.3..11.3, top shoulders R 3.2, flanks bulging 1.2, round
  lower half R 7.0), not a turned cylinder; rear rim R 2.2, front shoulder R 1.6 (judge: "boxier, integrated top,
  squarer front shoulders"; c3 / q34 still shade it like a round casting). The ears' outer faces run down into the
  top shoulders, so the round-1 platform plate with its hard step is gone. The base ends at X 837.0 (side trace: top
  10.8 to X 837, 9.8 at 838-839) and a ring collar r 9.7 (X 836.6-839.6, rounded front edge) carries on to the
  collar r 8.7 (to 842.8) as c3 draws it.
- ears: 3.8 thick (was 3.4; outer width 21.4 kept), every outline / window edge rolled with a 1.5 mm round (3
  segments) on the outer faces and 1.2 on the inner faces, top corners R 3.0 front / R 3.5 rear (judge: "thick and
  rounded, radiused tops, rolled tubular look; the top edge curves down into the ear with a rounded cap"). The ear
  outline (rake, vertical upper rear edge, top) stays on the side trace (L2).
- window: same position, corners R 1.6 / 2.2 / 2.6 / 2.0 and the 1.5 rolled rim: a rounded opening in a chunky frame.
- boss: a mostly flush disc (proud 0.18) with a raised ring rim (0.32 proud, 0.4 wide) and a scribed groove (0.36
  wide, 0.22 deep, cut after the bevels) leaving its lower rear edge towards the rake, as c3 draws it (round 1: a
  solid raised disc read as a dome rivet). Planar +-Y faces get face-normal corner normals (flat_face_normals).
- inner faces of the ears (seen on the far ear through the gap in c3 / q34): a large blind hole dia 4.0 near the
  top front and a round-ended vertical slot below it (2.4 x 7.0), plus the drum counterbore (r 3.3); no through
  holes (the side panels show none on the outer faces). The windage drum is r 2.8.
- open: c3 / q34 draw the ears ~0.7-0.8 as wide front-to-back for their height; EAR_SX (env FS_EAR_SX) builds that
  variant for review, the default 1.0 keeps the side trace (L2 0.961; the 0.78 variant scores L2 0.865).
- cavity floor between the ears at Z 11.9 with 0.9 fillets into the ears' inner faces ("filleted inner corners").
- cross pin moved to c3's position (X 830.5, Z -5.0), domed heads on the box's flat sides.
- cleaning-rod lug: c3's stepped, notched lug (unchanged from round 1).
Not built here: the detent latch (muzzle_brake owns it).
"""
from __future__ import annotations

import os

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP
from rifle_parts2 import BORE_R, ROD_Z, ROD_R, ycyl, xcyl

# Ear front-to-back scale about the front edge X 833 (1.0 = the side trace, the L2 authority; c3 / q34 draw the ears
# ~0.7-0.8 as wide for their height - an open proportion conflict, see review/detail/front_sight/spec_proposal.json).
EAR_SX = float(os.environ.get("FS_EAR_SX", "1.0"))


def sx(x):
    return 833.0 + (x - 833.0) * EAR_SX


EAR_IN, EAR_OUT = 6.9, 10.7       # ears 3.8 thick (outer width 21.4 = TOP panel)
EAR_RIM = 1.5                     # rolled round on every ear outline / window edge (weighted bevel, weight 1 = 1.5 mm)
W_IN, W_LOW = 0.8, 0.6            # rim weights: inner faces (1.2 mm), window floor / cavity floor edges (0.9 mm)
FLOOR_Z = 11.9                    # cavity floor between the ears
WIN_Z0 = 12.2                     # window floor
BOX_W, BOX_ZT, BOX_ZB = 11.0, 11.3, -10.3
BOX_RT, BOX_RB = 5.0, 9.0        # top shoulders (the ears land on them) / round lower half (integration round: rounder,
                                  # c3 draws the base as a round sleeve band; was 3.2 / 7.0)
BOX_BULGE = 1.2                   # the flanks are slightly convex (c3 / q34: the base shades like a round casting)
BOX_X = (806.1, 837.0)
BOX_RIM = (2.2, 1.6)              # rear rim, front shoulder
RING = (836.6, 839.6, 9.7)        # ring collar in front of the box
COLLAR_R, COLLAR_X1 = 8.7, 842.8
FRONT_COLLAR_R = 8.7              # the collar under the brake's detent knob (integration round: was 10.1, as wide as the
                                  # brake, so the brake read long with a seam; c3: sleeve band -> narrow ring -> brake)
HEAD_X = (811.0, 815.5)           # rod T-head inside the lug
HEAD_W = 2.5
BOSS = (sx(824.7), 29.9, 3.7)         # X, Z, radius
BOSS_RIM_H, BOSS_FACE_H, BOSS_RIM_W = 0.32, 0.18, 0.4
# scribed curve leaving the boss's lower rear edge towards the rake (c3: tangent-ish to the boss, sagging slightly)
SCRIBE = [(sx(824.7) - 3.1, 27.3), (sx(824.7) - 4.3, 27.05), (sx(824.7) - 5.7, 26.95), (sx(824.7) - 7.3 * min(1.0, EAR_SX + 0.1), 26.95)]
SCRIBE_W, SCRIBE_D = 0.36, 0.22
DRUM = (sx(825.3), 31.0, 2.8)         # windage drum X, Z, radius (post part); sits 0.9 deep in each ear's counterbore
CBORE_R = 3.3
TOP_HOLE = (sx(829.4), 43.4, 2.0, 2.0)                           # X, Z, radius, depth (blind, inner faces)
SLOT = G.rounded_rect(sx(829.3), sx(831.7), 27.5, 34.5, 0.49 * (sx(831.7) - sx(829.3)), 3)     # round-ended slot on the inner faces, 1.4 deep
PIN = (830.5, -5.0, 2.0)          # cross pin X, Z, radius


# ======================================================================================== outlines
def ear_outline() -> np.ndarray:
    """Ear side outline (XZ): rear rake (side trace), vertical upper rear edge, rounded top corners, flat top, vertical
    front edge. Below the box top the outline steps forward to X 807.6 so it stays inside the box's rear rim."""
    xr = 806.3 + (816.5 - 806.3) * (11.0 - 9.6) / (37.0 - 9.6)          # rake at Z 11.0
    P = np.array([(sx(807.6), 2.0), (833.0, 2.0), (833.0, 49.4), (sx(816.5), 49.4), (sx(816.5), 37.0), (sx(xr), 11.0),
                  (sx(807.6), 9.0)], float)
    return G.fillet(G.ccw(P), 1.0, 5, radii=[0.0, 0.0, 3.0, 3.5, 3.0, 0.0, 0.0])


def window_outline() -> np.ndarray:
    P = np.array([(sx(813.4), WIN_Z0), (sx(827.2), WIN_Z0), (sx(827.2), 21.8), (sx(816.4), 21.8)], float)
    return G.fillet(G.ccw(P), 1.0, 4, radii=[1.6, 2.2, 2.6, 2.0])


def box_section(inset=0.0) -> np.ndarray:
    """YZ section of the base (CCW in YZ), shrunk by `inset` (constant vertex count): top shoulders R BOX_RT, a round
    lower half R BOX_RB, flanks bulging BOX_BULGE between them (the corner arcs sit at |Y| BOX_W - BOX_BULGE)."""
    b = BOX_BULGE
    w, zt, zb = BOX_W - b - inset, BOX_ZT - inset, BOX_ZB + inset
    rt, rb = max(BOX_RT - inset, 0.05), max(BOX_RB - inset, 0.05)
    za, zc = zb + rb, zt - rt                       # flank from za up to zc
    flank = [(w + b * (1 - ((z - (za + zc) / 2) / ((zc - za) / 2)) ** 2), z) for z in np.linspace(za, zc, 7)[1:-1]]
    pts = [G.arc(w - rb, za, rb, -90.0, 0.0, 9)[:-1], np.array([(w, za)] + flank + [(w, zc)]),
           G.arc(w - rt, zc, rt, 0.0, 90.0, 5)[1:], G.arc(-w + rt, zc, rt, 90.0, 180.0, 5)[:-1],
           np.array([(-w, zc)] + [(-y, z) for y, z in flank[::-1]] + [(-w, za)]),
           G.arc(-w + rb, za, rb, 180.0, 270.0, 9)[1:]]
    return G.dedupe(np.vstack(pts))


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
    leaves the two ears standing on the floor."""
    return MS.prism(ear_outline(), -EAR_OUT, EAR_OUT)


def cavity() -> MS.Mesh:
    return MS.box(800.0, 840.0, -EAR_IN, EAR_IN, FLOOR_Z, 60.0)


def _ybetween(s, a, b):
    return min(s * a, s * b), max(s * a, s * b)


def inner_face_cuts() -> list:
    """On each ear's inner face: the drum's counterbore, the large blind hole near the top front and the round-ended
    vertical slot (c3 / q34 show them on the far ear between the ears)."""
    out = []
    for s in (-1, 1):
        out.append(ycyl(DRUM[0], DRUM[1], CBORE_R, *_ybetween(s, 6.0, EAR_IN + 0.9), 20))
        x, z, r, d = TOP_HOLE
        out.append(ycyl(x, z, r, *_ybetween(s, 6.0, EAR_IN + d), 20))
        out.append(MS.prism(SLOT, *_ybetween(s, 6.0, EAR_IN + 1.4)))
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
    return [MS.prism(P, *_ybetween(s, EAR_OUT - SCRIBE_D, EAR_OUT + 1.0)) for s in (-1, 1)]


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
    if abs(x - PIN[0]) < PIN[2] + 0.8 and abs(z - PIN[1]) < PIN[2] + 0.8 and abs(y) > 9.0:     # domed cross pin
        return 0.0
    if (y * y + (z - ROD_Z) ** 2) < (ROD_R + 0.6) ** 2 or (HEAD_X[0] - 0.2 < x < HEAD_X[1] + 0.2 and abs(y) < HEAD_W + 0.2
                                                           and abs(z - ROD_Z) < 2.8):
        return 0.0                                       # rod bore and the hidden head seat
    if abs(y) > EAR_IN - 1.0 and z > 20.0 and _near_details(x, z):
        return 0.0
    if EAR_IN - 0.25 <= abs(y) <= EAR_OUT + 0.25 and z > FLOOR_Z - 0.3:
        return 0.0                                       # the ears' rims (the rim pass rounded them)
    if abs(y) > EAR_OUT - 0.4 and z > 9.0 and 806.0 < x < 833.5:
        return 0.0                                       # crease where the ear faces run into the box's top corner
    return 1.0


def rim_weight(mid, d, n1, n2, dih):
    """Weighted rolled round on the ears: every outline / window edge on the ear faces (|Y| EAR_IN / EAR_OUT) above
    the box top (1.5 outer, 1.2 inner, 0.9 at the window floor and the cavity floor's fillets); not the details."""
    x, y, z = mid
    if dih < 45.0 or abs(y) < EAR_IN - 0.15 or abs(y) > EAR_OUT + 0.15:
        return 0.0
    if z < BOX_ZT + 0.3:                                 # base creases (ear faces into the box)
        return 0.0
    if _near_details(x, z):
        return 0.0
    if z < 13.0:
        return W_LOW
    if abs(y) < EAR_IN + 0.15 and abs(abs(y) - EAR_IN) < 0.15:
        return W_IN
    return 1.0


def boss(side) -> MS.Mesh:
    """Flush disc with a raised ring rim: rim proud BOSS_RIM_H (outer chamfer 0.12), face proud BOSS_FACE_H."""
    x, z, r = BOSS
    y0 = side * (EAR_OUT - 0.3)
    e = 0.3
    prof = [(0.0, 0.0), (0.0, r), (e + BOSS_RIM_H - 0.08, r), (e + BOSS_RIM_H, r - 0.08),
            (e + BOSS_RIM_H, r - BOSS_RIM_W), (e + BOSS_FACE_H, r - BOSS_RIM_W - 0.12)]     # flat n-gon face (no pole)
    return MS.revolve(prof, (x, y0, z), (0.0, side, 0.0), 24)


def cross_pin() -> list:
    """Cross pin through the base below the barrel axis, domed heads proud of the box's flat sides (c3)."""
    x, z, r = PIN
    yb = BOX_W
    out = [ycyl(x, z, r, -yb, yb, 16)]
    for s in (-1, 1):
        out.append(MS.dome((x, s * yb, z), (0.0, s, 0.0), r, 0.5, 16, 2))
    return out


def rod_lug() -> MS.Mesh:
    """c3's stepped, notched cleaning-rod lug as one loft of rounded YZ sections (X, half width, bottom Z, corner r);
    the top runs inside the base."""
    top = -8.0
    st = [(809.8, 3.6, -9.8, 0.9), (810.4, 3.6, -14.2, 1.4), (812.6, 3.6, -15.8, 1.6),
          (824.0, 3.6, -15.8, 1.6),
          (824.0, 2.9, -15.5, 1.4), (829.6, 2.9, -15.5, 1.4),            # step down (c3: the face at the joint)
          (829.6, 3.6, -15.8, 1.6), (831.0, 3.6, -15.8, 1.6),            # shoulder (c3: the lit forward face)
          (832.4, 2.0, -13.9, 1.0), (835.0, 2.0, -13.9, 1.0),            # neck = the notch
          (835.0, 2.7, -14.3, 1.3), (837.0, 2.7, -14.3, 1.3), (837.8, 2.2, -13.0, 1.0)]   # end knob
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


# rolled rims first (3 segments), then the process chamfer on the remaining sharp visible edges
RECIPE = [(EAR_RIM, 2, "W", rim_weight), (0.6, 1, "W", edge_weight)]     # integration round: rims 2 segments (budget; were 3)


def front_sight_block() -> PartDef:
    front_collar2 = MS.cylinder((842.6, 0, 0), (848.78, 0, 0), FRONT_COLLAR_R, 32, phase_deg=5.625)   # off the collar's vertex planes
    plunger = MS.cylinder((841.2, 0, 7.0), (841.2, 0, 9.1), 1.1, 12)
    unions = [base_box(), front_collars(), rod_lug(), front_collar2, boss(1), boss(-1), plunger] + cross_pin()
    p = PartDef("front_sight_block", [hood()], unions=unions, cls="M-chamfer-front", recipe=RECIPE,
                spec_id="front_sight_block")
    win = window_outline()
    p.cutters = [xcyl(0.0, 0.0, BORE_R + GAP, 800.0, 850.0, 48), cavity(),      # 48: facets clear the barrel's vertices
                 MS.prism(win, -12.0, 12.0),
                 MS.box(HEAD_X[0] - 0.5, HEAD_X[1] + GAP,     # 0.5 behind the head: room for its rod fillet
                         -HEAD_W - GAP, HEAD_W + GAP, ROD_Z - 2.6 - GAP, ROD_Z + 2.6 + GAP),
                 xcyl(0.0, ROD_Z, ROD_R + GAP, 800.0, HEAD_X[0] + 0.1, 16)]
    p.cutters += inner_face_cuts()
    p.post_cutters = [] if os.environ.get("FS_NOSCRIBE") else arc_cuts()     # after the bevels: a crisp scribed line
    return p


def flat_face_normals(ob, tol=0.99995) -> int:
    """Corner normals of every planar face facing +-Y (the ear faces, the boss and the groove floors) := the face
    normal. The booleans leave long sliver triangles across the ear faces; weighted normals then smear the small
    grooves' and holes' rim normals across them (round-2 r2i1-r2i3: a dark wedge beside the boss)."""
    me = ob.data
    cn = np.array([c.vector[:] for c in me.corner_normals], float)
    n = 0
    for poly in me.polygons:
        if abs(poly.normal[1]) > tol:
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
    drum = ycyl(DRUM[0], DRUM[1], DRUM[2], -(EAR_IN + 0.9) + GAP, EAR_IN + 0.9 - GAP, 20)
    post = MS.cylinder((DRUM[0], 0, DRUM[1] + DRUM[2] - 1.0), (DRUM[0], 0, 45.0), 1.0, 12)
    return PartDef("front_sight_post", [drum], unions=[post], cls="M-round", recipe=[(0.3, 1, 30.0)],
                   spec_id="front_sight_ears_post")


# ======================================================================================== module interface
OBJECTS = ('cleaning_rod', 'front_sight_block', 'front_sight_post')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c3', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("cleaning_rod", cleaning_rod), ("front_sight_block", front_sight_block_obj), ("front_sight_post", front_sight_post),)}
