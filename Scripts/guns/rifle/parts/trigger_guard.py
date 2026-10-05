"""Detail part TRIGGER GUARD (+ TRIGGER): the guard loop with its flange under the receiver and the mag
catch cheeks + pin, and the trigger (hinged, bone "trigger").

Owns the objects: trigger, trigger_guard. Authority close-ups: c6 PISTOL GRIP AND TRIGGER (LEFT, drawn from the true
left), c1 (right) and the 3/4 view. Interfaces: the receiver's bottom ledge (ledge_z), the trigger slot
(X 301.5-329, Y +-3.25), TRIG_PIVOT (B3 trigger sweep), CATCH_PIVOT (mag_catch in receiver_right), the grip's front
leg cut GRIP_LEG (grip: X 298.4-303.3 above Z -60).

Detail pass round 2 (2026-10-05). Method: the c1 / c6 close-ups rectified onto the part's own XZ plane at the solved
part cameras (trigger_guard_r2.py rectify), read in mm and drawn over our outlines; the side trace keeps scale,
position and the per-part L2 outline. Round-1 blind tells fixed here:
- loop SECTION (judge: "thick flat strap with an even silver rim inside" vs the reference's "thin rod-like bow"):
  the rectified close-ups show three thin dark lines with light lines between them all round the loop, i.e. a stamped
  strip with rolled outer edges and a pressed centre groove, not a flat strap with a lit inner edge. The loop is now
  a loft of that section along the U (rings between the outer and inner chains, nearest-point pairs): outer roll
  0.8 mm (faces down / out, reads dark), centre V-groove 0.8 x 0.3 mm with a flat bottom (one lit and one dark slope
  = the light / dark line pair), inner edge only 0.25 mm (the round-1 0.6 mm roll on the inner edge lit the chrome
  rim). The outline (outer R 10 / 9.5, inner R 8 / 5.5, legs 4.0 / 4.4, bottom 3.25) is unchanged: c1 and c6
  rectified agree with it within ~0.5 mm, and it holds the side L2;
- front leg (judge: "meets the receiver with a visible step or shelf"): the lip gusset under the flange is gone, the
  leg's inner edge runs straight up into the flange as in c1;
- catch housing (judge: "boxy bracket with a gap"): the cheeks now reach down to the catch paddle's top (Z -54) with a
  0.12-0.13 mm swept clearance (their bottom follows the paddle top's envelope over the 0-10 deg release), so the
  tongue recess that read as a gap is closed and the housing reads as one block down to the paddle's chamfer (c1,
  side trace: housing to Z -57 / -58); the pin is a flat round head on a washer (c1: ring + centre head), no diamond;
- trigger (judge: "thinner blade, needle-like curl, forward hook/spur at the top"): the blade re-traced from c1 and
  c6 (c6 sits 4.6 mm rearward in its own frame; after that shift the two agree within 0.3 mm on the rear edge): a
  single concave flare at the top (no shelf + knee), a broader blade (6.3 mm at mid, 4.9 mm lower), a blunt rounded
  tip 2.4 mm tall (the side trace's tip end is 2.7 mm), rolled rear edge and tip 0.4 mm, a rounded finger face (1.2 mm x 2 each side).
"""
from __future__ import annotations

import math

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.parts import PartDef
from rifle_parts import GAP, WO, ledge_z
from rifle_parts2 import CATCH_PIVOT, ycyl


def catmull(P, n_per=6):
    """Open Catmull-Rom chain through the points (uniform parameter; endpoints kept)."""
    P = np.asarray(P, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
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

# one chain top-rear -> tip -> top-front (frame M, X/Z), from the rectified c1 / c6 close-ups (c6 + 4.6 mm) inside the
# side trace's envelope (spec side_profile_M "trigger")
TRIG_CHAIN = [
    # rear edge: one concave flare from the slot into the blade (c1: X 310.1 / 311.8 / 313.3 at Z -36 / -37 / -38)
    # (c1 / c6 put the flare ~1.5 mm higher than the side trace; this sits between them, inside the side L2)
    (306.0, -34.7), (306.9, -35.5), (308.6, -36.6), (310.6, -37.7), (312.4, -38.8), (313.5, -40.2), (314.0, -41.9),
    (314.5, -44.2), (315.4, -46.9), (316.8, -49.6), (318.7, -52.2), (321.1, -54.5), (323.8, -56.4), (326.4, -57.6),
    # integration round (2026-10-05; round-2 judges on c1 and c6: "a slender tapering curve ending in a fine point",
    # "a pronounced forward hook at the top", ours "thicker, even in width, blunter"): a finer tip (1.3 mm), the lower
    # front edge 0.9 mm in toward the rear edge (the blade tapers), the top-front curving further forward
    (327.6, -57.9), (328.5, -57.6), (328.95, -57.15), (328.5, -56.55), (327.5, -55.25),
    (326.6, -54.0), (325.3, -52.7), (324.1, -51.1), (323.0, -49.3), (322.2, -47.3), (321.6, -45.1), (321.3, -42.7),
    (321.4, -40.3), (321.9, -37.9), (322.9, -36.1), (324.2, -35.1), (325.2, -34.7)]


def trigger_outline():
    return G.ccw(G.dedupe(G.dp_simplify(catmull(TRIG_CHAIN, 2), 0.03)))     # (0.03 mm DP: budget, shape kept)


_TRIG_DENSE = catmull(TRIG_CHAIN, 4)
_TRIG_APEX = int(np.argmin(np.hypot(_TRIG_DENSE[:, 0] - 329.0, _TRIG_DENSE[:, 1] + 57.0)))


def _blade_edge(mid, d, n1, n2, dih):
    """+1 rear edge / tip, -1 front edge, 0 not a blade outline edge (between a flat side, normal +-Y, and the outline
    wall, below the receiver Z < -35.3)."""
    if dih < 60.0 or mid[2] > -35.3 or abs(d[1]) > 0.5:
        return 0
    if not (abs(n1[1]) > 0.9 or abs(n2[1]) > 0.9):
        return 0
    j = int(np.argmin(np.hypot(_TRIG_DENSE[:, 0] - mid[0], _TRIG_DENSE[:, 1] - mid[2])))
    return 1 if j <= _TRIG_APEX else -1


def _pred_trigger_rear(mid, d, n1, n2, dih):
    """Rolled rear edge and round tip (0.4 mm)."""
    return 1.0 if _blade_edge(mid, d, n1, n2, dih) == 1 else 0.0


def _pred_trigger_front(mid, d, n1, n2, dih):
    """Front (finger) face rounded 1.2 mm x 2 each side (c1: a dark edge with one thin light line along it; a crisp or
    0.4 mm rolled edge lit a chrome streak on the wall sliver the c1 camera sees from 5 deg above)."""
    return 1.0 if _blade_edge(mid, d, n1, n2, dih) == -1 else 0.0


def trigger() -> PartDef:
    blade = MS.prism(trigger_outline(), -3.0, 3.0)
    stem = [(313.6, -35.2), (321.2, -35.2), (320.6, -21.0), (315.4, -21.0)]
    uni = [MS.prism(stem, -3.0, 3.0), ycyl(TRIG_PIVOT[0], TRIG_PIVOT[1], 3.0, -3.0, 3.0, 24)]
    cut = [ycyl(TRIG_PIVOT[0], TRIG_PIVOT[1], 1.2, -4, 4, 16)]
    return PartDef("trigger", [blade], unions=uni, cutters=cut, bone="trigger", cls="C-fillet",
                   recipe=[(0.4, 2, "W", _pred_trigger_rear), (1.2, 2, "W", _pred_trigger_front), (0.3, 1, 55.0)],
                   joint={"type": "hinge", "parent": "receiver", "pivot_M": [TRIG_PIVOT[0], 0, TRIG_PIVOT[1]],
                          "axis_M": [0, 1, 0], "range_deg": [0.0, 12.0], "clearance_mm": [0.1, 0.3]})


# ======================================================================================== guard loop
LOOP_W = 5.0                  # loop half width (Y)
Z_TOP = -34.4                 # loop top, 0.4 inside the flange (the joint is hidden in the flange)
R_OUT = (10.0, 9.5)           # outer corner radii rear / front (c6 / c1 rectified, side trace)
R_IN = (8.0, 5.5)             # inner corner radii rear / front
SLOPE = 2.2 / 35.2            # bottom bar rises toward the front (side trace: Z -68.4 at X 312.1, -66.2 at 347.3)
ROLL_OUT, ROLL_IN = 0.8, 0.25  # section: rolled outer edge / small inner edge radius (mm)
GROOVE = (0.4, 0.15, 0.3)     # centre groove: half width at the face, half width of the flat bottom, depth
GROOVE_AT = 0.5               # groove centre as a fraction of the strip width from the inner edge
CHANNEL = (1.0, 0.8)          # inner face: lip height (Y, from the side face) and channel depth (the stamped strip's
                              # open channel faces the trigger; c1 / 3/4 show the loop's inner face dark, and the c1
                              # camera's 5 deg down tilt otherwise shows a flat lit top face as a silver rim)
FSEG = 6                      # arc segments of the outline fillets (15 deg steps)


def _zb(x):
    return -68.4 + (x - 312.1) * SLOPE


def loop_polygon():
    """The U loop in XZ (closed, CCW): outer chain top-rear -> rear-bottom -> front-bottom -> top-front, then the inner
    chain back. Returns (polygon, index of the outer chain's last point)."""
    o_rear0, o_rear1 = 299.0, 299.5        # rear leg outer edge X at the top / bottom (inside GRIP_LEG's cut)
    i_rear0, i_rear1 = 303.0, 303.2        # rear leg inner edge (leg 3.7-4.0 mm; trace 303.0-303.3)
    o_front, i_front = 355.15, 350.75      # front leg (4.4 mm; trace 350.6-355.2)
    t_bot = 3.25                           # bottom bar (trace 3.0-3.4)
    P = [(o_rear0, Z_TOP), (o_rear1, _zb(o_rear1)), (o_front, _zb(o_front)), (o_front, Z_TOP),
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
    """Half section (y >= 0) across the strip from the outer edge (u = w) to the inner edge (u = 0): rolled outer edge,
    centre groove with a flat bottom, small inner roll. Returns [(u, y)]."""
    T, ro, ri = LOOP_W, ROLL_OUT, ROLL_IN
    gh, gb, gd = GROOVE
    um = GROOVE_AT * w
    pts = [(w, T - ro)]
    for a in (30.0, 60.0):
        r = math.radians(a)
        pts.append((w - ro + ro * math.cos(r), T - ro + ro * math.sin(r)))
    pts += [(w - ro, T), (um + gh, T), (um + gb, T - gd), (um - gb, T - gd), (um - gh, T), (ri, T)]
    r = math.radians(135.0)
    pts += [(ri + ri * math.cos(r), T - ri + ri * math.sin(r)), (0.0, T - ri)]
    lip, cd = CHANNEL
    pts += [(0.0, T - lip), (cd, T - lip)]
    return pts


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
    flange_f = MS.prism([(345.7, -34.8), (367.9, -34.8)] + top_f[::-1], -WO, WO)
    # the leg's top strap under the tab: straight, 0.7 mm below the tab (side trace lip X 345.7-350.6, Z -35.6), no
    # gusset (round 1's sloped gusset read as a shelf)
    lip = MS.box(345.7, 350.9, -LOOP_W + 0.4, LOOP_W - 0.4, -35.5, -34.6)
    # catch housing cheeks either side of the catch tongue (Y 3.75-4.98, the tongue is +-3.5, the paddle +-5.0), the pin
    # a flat round head on a washer each side (c1)
    cheek_o = cheek_outline()
    cx, cz = CATCH_PIVOT
    uni = [flange_r, flange_f, lip, MS.prism(cheek_o, 3.75, 4.98), MS.prism(cheek_o, -4.98, -3.75),
           ycyl(cx, cz, 2.1, 4.96, 5.2, 16), ycyl(cx, cz, 2.1, -5.2, -4.96, 16),          # washers
           ycyl(cx, cz, 1.3, 5.15, 5.5, 12), ycyl(cx, cz, 1.3, -5.5, -5.15, 12),          # pin heads
           ycyl(cx, cz, 1.5, -5.4, 5.4, 12)]
    cut = [MS.box(301.5, 329.0, -3.25, 3.25, -35.2, -27.0),                 # trigger slot through the flange
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
