"""Detail part TRIGGER GUARD (+ TRIGGER): the guard loop with its flange under the receiver and the mag
catch cheeks + pin, and the trigger (hinged, bone "trigger").

Owns the objects: trigger, trigger_guard. Authority close-ups: c6 PISTOL GRIP AND TRIGGER (LEFT, drawn from the true
left), c1 (right) and the 3/4 view. Interfaces: the receiver's bottom ledge (ledge_z), the trigger slot
(X 301.5-329, Y +-3.25), TRIG_PIVOT (B3 trigger sweep), CATCH_PIVOT (mag_catch in receiver_right), the grip's front
leg cut GRIP_LEG (grip: X 298.4-303.3 above Z -60).

Detail pass round 2 (2026-10-05, first run, in git at 5893f738): loop lofted from a stamped section, front-leg gusset
removed, cheeks down to the paddle, trigger re-traced from c1 / c6.

Detail pass round 2b (2026-10-05, re-run on the integrated build; method: c1 / c6 rectified onto the part's XZ plane at
the solved part cameras by trigger_guard_r2.py, read at 1 mm rows, ROUGH LOOK renders at the part cameras). Round-1
blind tells and what changed:
- trigger "broader at the top, thick tip; ours thinner and hook-like": c1 draws the receiver bottom ~2.3 mm higher
  than the side trace, so its trigger rows are mapped into our opening (x 0.914 in Z); the sloped shoulder now reaches
  X 306-308 just below the flange with a crisp knee, the tip is a blunt ~2 mm round end. Side L2 trigger IoU 0.895 ->
  0.946 (the side trace agrees);
- trigger chrome streak (render tell in every round): the bevel-modifier "rounds" on the blade were clamped to ~0.06 mm
  by the cap triangulation, leaving a flat 6 mm finger face the c1 camera (4.5 deg toward the muzzle) sees at grazing
  incidence. The blade is now a profiled extrusion (blade_mesh): a shallow concave finger face (0.8 mm) with 0.15 mm
  edge breaks that runs round the tip, and a 0.45 mm rear roll; c1 / c6 show the same dark line / light band / dark
  outline along the front edge;
- loop "thicker flat strap with a bevelled lip, boxier rear corner": the side face is two rounded beads either side of
  a V groove (c1: three dark lines with two light ones), the corners have 8 segments (6 showed facets), inner radii
  rear 6 / front 8 (c1 rows; round 2 had them swapped), front outer R 11, bottom bar 0.3 mm deeper (c1);
- "a separate block at the top" of the catch: the front tab is full width only down to Z -33.2 (c1: a thin plate over
  the housing), recessed like the rear flange below.
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import lod as LOD
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP, WO, ledge_z
from rifle_parts2 import CATCH_PIVOT, ycyl


def catmull(P, n_per=6):
    """Open Catmull-Rom chain through the points (uniform parameter; endpoints kept)."""
    P = np.asarray(P, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    n_per = LOD.count(n_per, 2)                     # LOD: fewer spline points per span
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out)


# ======================================================================================== trigger group
TRIG_PIVOT = (318.0, -20.0)
TRIG_FACE_C = 0.8             # finger face: shallow concave across the 6.0 mm blade, crisp-broken edges (blade_mesh)

# one chain top-rear -> tip -> top-front (frame M, X/Z), from the rectified c1 / c6 close-ups (c6 + 4.6 mm) inside the
# side trace's envelope (spec side_profile_M "trigger")
TRIG_CHAIN = [
    # detail round 2b (2026-10-05): the rectified c1 read at 1 mm rows (review/detail/trigger_guard/r2b_trace.json) and
    # compressed into our opening: c1 draws the receiver bottom ~2.3 mm higher than the side trace (its opening is
    # taller in proportion), so its trigger rows Z -33.3 .. -57.6 map onto ours -35.6 .. -57.8 (x 0.914 in Z, X kept).
    # That keeps c1's broad top (the sloped shoulder reaching X 306-308 just below the flange, then a crisp knee) inside
    # our shorter opening; the side trace agrees (its trigger is broader at the top than round 2's).
    # rear edge
    (305.8, -34.7), (306.4, -35.33), (307.0, -36.24), (308.2, -37.15), (309.9, -38.07), (311.6, -38.98), (313.0, -39.75),
    (313.6, -40.6), (313.9, -41.72), (314.2, -43.55), (314.6, -45.38), (315.2, -47.21), (316.1, -49.04),
    (317.25, -50.86), (318.75, -52.69), (320.75, -54.52), (321.9, -55.43), (323.25, -56.35), (324.9, -57.2),
    (326.3, -57.7),
    # blunt rounded tip, ~2 mm across (c1: X 325.2-328.6 at its Z -57; the round-1 judge: "a fairly thick tip")
    (327.5, -58.0), (328.45, -57.85), (329.0, -57.3), (329.0, -56.6), (328.45, -56.0),
    # front (finger) edge
    (327.25, -55.43), (326.1, -54.52), (325.1, -53.5), (324.4, -52.69), (323.25, -50.86), (322.3, -49.04),
    (321.75, -47.21), (321.4, -45.38), (321.1, -43.55), (321.1, -41.72), (321.4, -39.9), (321.75, -38.98),
    (322.0, -38.07), (322.4, -37.15), (323.0, -36.24), (323.7, -35.33), (324.3, -34.7)]


def trigger_outline():
    return G.ccw(G.dedupe(G.dp_simplify(catmull(TRIG_CHAIN, 2), LOD.tol(0.05))))     # (0.05 mm DP: budget, shape kept; LOD: coarser)


_TRIG_DENSE = catmull(TRIG_CHAIN, 4)
_TRIG_APEX = int(np.argmin(np.hypot(_TRIG_DENSE[:, 0] - 329.1, _TRIG_DENSE[:, 1] + 57.0)))


TRIG_T = 3.0                  # blade half thickness (Y)
TRIG_REAR_R = 0.45            # rear edge / tip roll
TRIG_BREAK = 0.15             # finger face edge break


def _blade_params(Q):
    """Per-vertex (finger-face weight f, concave depth c, rear roll R) of the blade outline Q (CCW, XZ): the front
    chain gets the concave finger face, the rear chain and the tip the roll; both ramp down to a small floor at the blade
    top (hidden in the flange slot, under the stem) and are limited by the local blade width near the tip."""
    dense = _TRIG_DENSE
    j = np.array([int(np.argmin(np.hypot(dense[:, 0] - x, dense[:, 1] - z))) for x, z in Q])
    front = j > _TRIG_APEX - 6                     # the concave face runs round the tip's end too (any convex or
                                                   # flat end facing up-forward lit a bright knob in c1)
    ramp = np.clip((-34.75 - Q[:, 1]) / 1.0, 0.25, 1.0)
    rear_pts, front_pts = dense[: _TRIG_APEX + 1], dense[_TRIG_APEX + 1:]
    out = []
    for i, (x, z) in enumerate(Q):
        other = rear_pts if front[i] else front_pts
        w = float(np.min(np.hypot(other[:, 0] - x, other[:, 1] - z)))
        if front[i]:
            out.append((1.0, max(min(TRIG_FACE_C * ramp[i], 0.2 * w), 0.3 * ramp[i]), 0.0))
        else:
            out.append((0.0, 0.0, max(min(TRIG_REAR_R * ramp[i], 0.3 * w), 0.08)))
    return out


def _profile(f, c, R):
    """Rings from the side face to the middle of the blade edge: [(inset, y)] (4 rings; the middle ring y = 0)."""
    T = TRIG_T
    if f > 0.5:                                    # concave finger face with a small break at the side-face edge
        b = TRIG_BREAK
        y1, y2 = T - b, 0.5 * T
        return [(b, T), (c * (1 - (y1 / T) ** 2), y1), (c * (1 - (y2 / T) ** 2), y2), (c, 0.0)]
    ph = [math.radians(a) for a in (90.0, 60.0, 30.0)]
    return [(R * (1 - math.cos(a)), T - R + R * math.sin(a)) for a in ph] + [(0.0, 0.0)]


def blade_mesh():
    """The blade as a profiled extrusion of its outline (real geometry, no bevel modifier): rings from the -Y side face
    through the middle of the edge to the +Y side face, each outline vertex moved in along its bisector by its own
    profile. Finger face: shallow concave (c1 / c6 show a dark line, a light band and a dark outline along the front
    edge, i.e. the face's far half seen beside a crisp near edge); rear edge and tip: a small roll. Round 2's bevel-
    modifier rounds were clamped to ~0.06 mm by the cap triangulation, which left a flat 6 mm finger face that the c1
    camera (4.5 deg toward the muzzle) sees at grazing incidence: the white streak of the round-2 renders; a convex
    round only moved the streak to its silhouette."""
    Q = np.asarray(trigger_outline(), float)
    n = len(Q)
    prm = _blade_params(Q)
    e_in = []
    for i in range(n):
        d = Q[(i + 1) % n] - Q[i]
        d = d / np.linalg.norm(d)
        e_in.append(np.array([-d[1], d[0]]))
    e_in = np.array(e_in)
    dirs = []
    for i in range(n):
        v = e_in[i - 1] + e_in[i]
        v = v / np.linalg.norm(v)
        dirs.append(v / max(float(v @ e_in[i]), 0.5))
    profs = [_profile(*prm[i]) for i in range(n)]
    K = len(profs[0])
    rings = []
    for k in list(range(K)) + list(range(K - 2, -1, -1)):
        sgn = -1.0 if len(rings) < K - 1 else 1.0
        ring = []
        for i in range(n):
            inset, y = profs[i][k]
            x, z = Q[i] + dirs[i] * inset
            ring.append((x, sgn * y, z))
        rings.append(np.array(ring))
    return MS.loft(rings)


def _pred_trigger_other(mid, d, n1, n2, dih):
    """0.3 mm break on the sharp edges above the blade top (stem, pivot boss; inside the slot); the blade's edges are
    modelled rounds (blade_mesh)."""
    return 1.0 if dih >= 55.0 and mid[2] > -34.6 else 0.0


def trigger() -> PartDef:
    blade = blade_mesh()
    stem = [(313.6, -35.2), (321.2, -35.2), (320.6, -21.0), (315.4, -21.0)]
    uni = [MS.prism(stem, -3.0, 3.0), ycyl(TRIG_PIVOT[0], TRIG_PIVOT[1], 3.0, -3.0, 3.0, 24)]
    cut = [ycyl(TRIG_PIVOT[0], TRIG_PIVOT[1], 1.2, -4, 4, 16)]
    return PartDef("trigger", [blade], unions=uni, cutters=cut, bone="trigger", cls="C-fillet",
                   recipe=[(0.3, 1, "W", _pred_trigger_other)],
                   joint={"type": "hinge", "parent": "receiver", "pivot_M": [TRIG_PIVOT[0], 0, TRIG_PIVOT[1]],
                          "axis_M": [0, 1, 0], "range_deg": [0.0, 12.0], "clearance_mm": [0.1, 0.3]})


# ======================================================================================== guard loop
LOOP_W = 5.0                  # loop half width (Y)
Z_TOP = -34.4                 # loop top, 0.4 inside the flange (the joint is hidden in the flange)
R_OUT = (10.0, 11.0)          # outer corner radii rear / front (round 2b: c1 rectified rows, the front corner runs
R_IN = (6.0, 8.0)             # from Z -57.5 to X 341; inner corners rear R ~6 / front R ~8: round 2's 8 / 5.5 had
                              # them swapped, so our front corner read boxy)
TAB_Z = -33.2                 # front tab: lower edge of its full-width plate
BOT_DROP = 0.3                # bottom bar's outer edge below the side-trace line (c1: bar 0.6-1.4 mm deeper than ours)
SLOPE = 2.2 / 35.2            # bottom bar rises toward the front (side trace: Z -68.4 at X 312.1, -66.2 at 347.3)
CHANNEL = (1.0, 0.8)          # inner face: lip height (Y, from the side face) and channel depth (the stamped strip's
                              # open channel faces the trigger; c1 / 3/4 show the loop's inner face dark, and the c1
                              # camera's 5 deg down tilt otherwise shows a flat lit top face as a silver rim)
FSEG = 8                      # arc segments of the outline fillets (11.25 deg steps; 15 deg showed facets on the outer
                              # corners in the c1 crop)
BEAD_H = 0.45                 # side face = two rounded beads either side of a V groove (c1 / c6: three dark lines with
                              # two light lines between them along the whole loop; the inner edge reads dark)


def _zb(x):
    return -68.4 + (x - 312.1) * SLOPE


def loop_polygon():
    """The U loop in XZ (closed, CCW): outer chain top-rear -> rear-bottom -> front-bottom -> top-front, then the inner
    chain back. Returns (polygon, index of the outer chain's last point)."""
    o_rear0, o_rear1 = 299.0, 299.5        # rear leg outer edge X at the top / bottom (inside GRIP_LEG's cut)
    i_rear0, i_rear1 = 303.0, 303.2        # rear leg inner edge (leg 3.7-4.0 mm; trace 303.0-303.3)
    o_front, i_front = 355.15, 350.75      # front leg (4.4 mm; trace 350.6-355.2)
    t_bot = 3.25                           # bottom bar (trace 3.0-3.4)
    P = [(o_rear0, Z_TOP), (o_rear1, _zb(o_rear1) - BOT_DROP), (o_front, _zb(o_front) - BOT_DROP), (o_front, Z_TOP),
         (i_front, Z_TOP), (i_front, _zb(i_front) + t_bot), (i_rear1, _zb(i_rear1) + t_bot), (i_rear0, Z_TOP)]
    radii = [0.0, R_OUT[0], R_OUT[1], 0.0, 0.0, R_IN[1], R_IN[0], 0.0]
    Q = G.dedupe(G.fillet(np.array(P, float), 0.0, seg=FSEG, radii=radii))
    k = int(np.argmin(np.hypot(Q[:, 0] - o_front, Q[:, 1] - Z_TOP)))
    return Q, k


def loop_outline(rim=0.0):
    """Closed outline of the loop (side silhouette; kept for the review overlays)."""
    return G.ccw(loop_polygon()[0])


def loop_stations():
    """Section stations along the U: pairs (outer point, inner point), ordered rear-top -> front-top. The two chains
    have the same structure (top, rear corner arc, front corner arc, top; FSEG + 1 points per arc), so the k-th outer
    vertex pairs with the k-th inner vertex: the straight legs and the bottom bar are single spans, each corner is FSEG
    spans whose sections fan between the two (non-concentric) arcs."""
    Q, k = loop_polygon()
    O = Q[:k + 1]
    I = Q[k + 1:][::-1]                    # inner chain, rear-top -> front-top
    if len(O) != len(I):
        raise ValueError(f"loop chains differ: {len(O)} outer vs {len(I)} inner points")
    return [(np.asarray(o, float), np.asarray(i, float)) for o, i in zip(O, I)]


def section(w):
    """Half section (y >= 0) across the strip from the outer edge (u = w) to the inner edge (u = 0). FORM REALISM ROUND
    (2026-10-05): both realism judges read round 2b's section (two rounded beads either side of a V groove) as a
    wire-thin loop; the real guard is a stamped sheet strip. So: a stamped CHANNEL -- a flat web 10 wide (Y) on the
    outside (the bottom of the loop seen from below), its edges bent R BEND_R into flat flanges FLANGE_T thick whose
    outer faces are the flat side faces the side view shows (the traced 3.25-4.4 mm band), crisp 0.25 breaks on the
    flange ends, the channel open toward the trigger with its floor WEB_T in from the outer face. Returns [(u, y)]."""
    T = LOOP_W
    if FLAT_STRAP:
        # LAST SHAPE ROUND (ruling 6): the real guard loop is a WIDE FLAT STAMPED STRAP: flat outer and inner faces
        # 10 mm across (Y), flat side faces (the traced band), crisp EDGE_BRK breaks on the four edges. The round-2b
        # channel (open toward the trigger) read as a thin wire loop in the hero 3/4 view; from its 17 deg elevation
        # the strap's broad inner face now shows
        e = EDGE_BRK
        return [(w, T - e), (w - e * 0.29, T - e * 0.29), (w - e, T), (e, T), (e * 0.29, T - e * 0.29), (0.0, T - e)]
    rb, tf, tw = BEND_R, FLANGE_T, WEB_T
    cd = max(w - tw, 0.6)
    pts = [(w, T - rb)]
    for a in (30.0, 60.0):
        pts.append((w - rb + rb * math.cos(math.radians(a)), T - rb + rb * math.sin(math.radians(a))))
    pts += [(w - rb, T), (0.25, T), (0.0, T - 0.25), (0.0, T - tf), (cd + 0.4, T - tf), (cd, T - tf - 0.4)]
    return pts


FLAT_STRAP = True             # last shape round: flat strap section (False: round 2b's stamped channel)
EDGE_BRK = 0.35


BEND_R = 1.0                  # web-to-flange bend (outer radius) of the stamped strip
FLANGE_T = 1.0                # flange (side wall) thickness = the sheet
WEB_T = 1.6                   # web thickness (outer face to the channel floor)


def loop_mesh():
    rings = []
    for o, i in loop_stations():
        v = o - i
        w = float(np.hypot(*v))
        n = v / w
        half = section(w)
        ring2 = half + [(u, -y) for u, y in reversed(half)]
        rings.append(np.array([[i[0] + n[0] * u, y, i[1] + n[1] * u] for u, y in ring2]))
    return MS.loft(rings)


# ======================================================================================== guard
def cheek_outline():
    """Catch housing cheek (XZ): from the front leg to the housing front, down to the catch paddle's top (Z -54) with
    0.12-0.13 mm clearance to the paddle top's envelope over the 0-10 deg release (the line through the pivot's
    rotated foot: z = -54.06 + 0.1763 (x - 362) at 10 deg; behind X 362.4 the rest pose is the highest)."""
    cx, cz = CATCH_PIVOT
    zr = -54.0 + 0.13
    xf = 367.6
    zf = cz - 4.0 / math.cos(math.radians(10.0)) + math.tan(math.radians(10.0)) * (xf - cx) + 0.12
    # rear edge X 355.1: 0.05 into the front leg's outer face, so the leg's rolled outer edge stays visible beside the
    # housing (c1: a light line between leg and housing) and keeps its side-view outline; top into the flange
    return [(355.1, -34.7), (xf, -34.7), (xf, zf), (cx + 0.4, zr), (355.1, zr)]


def _pred_guard(mid, d, n1, n2, dih):
    """0.3 mm edge bevel on the flange, cheeks and pin heads; the loop carries its own section rolls (no bevel on its
    channel lips / groove) and the loop-flange / loop-cheek seams stay sharp (hidden under the receiver / inside the
    housing; bevelling them only added triangles)."""
    if dih < 55.0:
        return 0.0
    x, y, z = mid
    in_cheek = x > 355.0 and z > -54.3 and abs(y) > 3.7
    if 297.0 < x < 356.0 and z < -34.75 and not in_cheek:     # loop body
        return 0.0
    if 297.0 < x < 356.0 and -34.85 < z < -34.75:            # loop / flange seam
        return 0.0
    if in_cheek and x < 355.2:                               # cheek / front leg seam
        return 0.0
    if in_cheek and z < -52.8 and abs(d[1]) < 0.5:           # cheek bottom edges: crisp (a bevel here and the
        return 0.0                                           # paddle's top bevel made a lit V seam: a "bracket")
    return 1.0


def trigger_guard() -> PartDef:
    loop = loop_mesh()
    # flange under the receiver: recessed behind the front leg, the front tab full width over the catch housing
    # (front tab from X 345.7: c1's plate over the housing runs back past the front leg; the side trace's lip)
    xs_r = np.array([252.0, 255.0, 300.0, 346.3])
    xs_f = np.array([345.7, 360.0, 367.9])
    top_r = [(x, ledge_z(x) - GAP) for x in xs_r]
    top_f = [(x, ledge_z(x) - GAP) for x in xs_f]
    fl_in = WO - 1.25
    flange_r = MS.prism([(252.0, -34.8), (346.3, -34.8)] + top_r[::-1], -fl_in, fl_in)
    # front tab: full width only down to TAB_Z (c1: a thin plate, ~3.5 mm, with the housing below it; round 2's full-
    # height 5.3 mm tab read as "a separate block at the top" of the catch), recessed like the rear flange below that
    # (cut, so the tab stays one prism over the same footprint)
    flange_f = MS.prism([(345.7, -34.8), (367.9, -34.8)] + top_f[::-1], -WO, WO)
    # the leg's top strap under the tab: straight, 0.7 mm below the tab (side trace lip X 345.7-350.6, Z -35.6), no
    # gusset (round 1's sloped gusset read as a shelf)
    lip = MS.box(345.7, 350.9, -LOOP_W + 0.4, LOOP_W - 0.4, -35.5, -34.6)
    # catch housing cheeks either side of the catch tongue (Y 3.75-4.98, the tongue is +-3.5, the paddle +-5.0), the pin
    # a flat round head on a washer each side (c1)
    cheek_o = cheek_outline()
    cx, cz = CATCH_PIVOT
    uni = [flange_r, flange_f, lip, MS.prism(cheek_o, 3.75, 4.98), MS.prism(cheek_o, -4.98, -3.75),
           # integration r2b: low pin heads set in the plate (judges r2b, c1: "a recessed rivet near its middle";
           # ours stood out as a domed head on a washer): head r 1.7, 0.14 proud, no washer
           # last shape round (ruling 6, "riveted under the receiver"): the real front tower's catch rivet is a domed
           # head (scratch/realref AKM_1980: a round rivet head on the guard's front tower), r 1.9, 0.75 proud
           MS.revolve([(0.0, 0.0), (0.0, 1.9), (0.3, 1.78), (0.55, 1.35), (0.75, 0.0)], (cx, 4.96, cz), (0, 1, 0), 16),
           MS.revolve([(0.0, 0.0), (0.0, 1.9), (0.3, 1.78), (0.55, 1.35), (0.75, 0.0)], (cx, -4.96, cz), (0, -1, 0), 16),
           ycyl(cx, cz, 1.5, -5.0, 5.0, 12)]
    cut = [MS.box(301.5, 329.0, -3.25, 3.25, -35.2, -27.0),                 # trigger slot through the flange
           MS.box(345.0, 368.5, fl_in, WO + 1.0, -35.5, TAB_Z),             # tab recess below its plate, each side
           MS.box(345.0, 368.5, -WO - 1.0, -fl_in, -35.5, TAB_Z),
           MS.box(352.0, 355.6, -3.75, 3.75, -34.9, -51.6)]                 # catch tongue relief in the front leg
    return PartDef("trigger_guard", [loop], unions=uni, cutters=cut, cls="S-bend", smooth_deg=35.0,
                   recipe=[(0.3, 1, "W", _pred_guard)])


# ======================================================================================== module interface
OBJECTS = ('trigger', 'trigger_guard')            # registry keys built here (rifle_parts.ORDER)
CLOSEUPS = ('c6', 'c1', 'q34')          # sheet panels that are this part's shape authority (rifle_detail.py)


def build(spec, ctx):
    """Build this module's objects into ctx (gunlib.parts.BuildCtx). Returns {registry key: [objects]}; keys that
    ctx.only excludes come back empty. `spec` is the rifle GunSpec (the same object as rifle_common.SPEC)."""
    return {k: ctx.make(k, f) for k, f in (("trigger", trigger), ("trigger_guard", trigger_guard),)}
