"""Card Shop Kit family fg_counter: play tables, the folding chair, the cash counter and the kraft bag
(CARDSHOP_KIT_SPEC.md 3.F rows F1, F2 and 3.G rows G1, G11; P3-P5).

    F1  folding tournament tables 914 / 1524 / 1829 (2 / 4 / 6 seats)    reference sheet 24 (csk_play_area.png)
    F2  steel folding chair, Open + Folded (the Folded state is added)   reference sheet 24
    G1  cash counter 1397 (cash wrap)                                    reference sheet 25 (csk_counter_pos.png)
    G11 kraft paper bag, Open + Flat (the Flat state is added)           reference sheet 27 (csk_bag_mailers.png)

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = a
spec estimate with a source range. "sheet N" = the value or form is read off that reference sheet (the picture wins
over E numbers; M numbers win over the picture). Millimetres; Seat frame: +X right, +Y away from the customer, +Z up.
A socket's rotation follows the kit rule "an item's front faces -Y in its own frame": rot (0, 0, 180) turns a chair,
a device or a person to face +Y.

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .geom import R_BACK, R_FRONT, Item, Lod, Socket, _face_out, _planar, inset
from .shapes import Builder, rounded_rect

Vec3 = Tuple[float, float, float]

# =========================================================================== numbers

TABLE = dict(                  # F1 folding tournament tables, sheet 24
    lengths={2: 914.0, 4: 1524.0, 6: 1829.0},   # seats -> length: 914 / 1524 M [D33]; 1829 E (spec)
    d=762.0, h=737.0,          # D 762 E, H 737 M [D33]; sheet 24 call-outs agree
    matches={2: 1, 4: 2, 6: 3},  # spec: one match = 2 facing mats; 3 matches on 1829 (D); log: user accepted
    top_t=50.0,                # sheet 24: a thick blow-moulded top edge (E 50)
    corner_r=40.0,             # sheet 24: rounded plan corners (E radius)
    edge_r=(10.0, 4.0),        # sheet 24: the rounded top edge / the small round under it (E radii)
    leg_d=25.4,                # E: 1 in steel tube (sheet 24: slim grey tube legs)
    leg_in=136.0,              # sheet 24 (1829 view): leg tops 136 in from the table ends
    leg_y=70.0,                # sheet 24: the front and back legs 70 in from the long edges (E)
    splay=40.0,                # sheet 24: the lower legs kink out toward the table end, foot 40 further out
    knee_z=305.0,              # sheet 24: the kink at the cross brace, about 0.4 of the leg height
    bar=(330.0, 19.0),         # sheet 24: cross brace between the front and back legs: height, tube diameter (E)
    brace=(560.0, 250.0, 20.0, 5.0),  # sheet 24: folding strut from the leg (z) to the underside (inward x),
                                      # flat bar W x T (E)
    bracket=(50.0, 40.0, 14.0),  # sheet 24: small grey brackets under the top at the leg and strut ends (E)
    cap=(30.0, 30.0),          # sheet 24: black foot caps, diameter x height (E)
    mat=(609.6, 355.6, 2.0),   # E5 playmat (M [D19]): the Mat sockets place two facing mats per match
    deck_in=(60.0, 70.0),      # E: Deck socket in from the mat's right-hand end / far edge (the mat's deck corner)
    chair_y=640.0,             # E: chair Seat 640 off the centre line: seat front 11 under the table edge
)

CHAIR = dict(                  # F2 steel folding chair, sheet 24
    w=450.0, d=520.0, h=800.0, seat_h=445.0,   # E (spec); sheet 24 call-outs agree
    tube=22.0,                 # E: 7/8 in steel tube (sheet 24: slim black tube frame)
    cap=(26.0, 32.0),          # sheet 24: black foot caps, diameter x height (E)
    main_x=212.0,              # D: the front feet are 450 wide over the caps (225 - 13)
    rear_x=188.0,              # E: the rear legs run inside the main frame (212 - 22 - 2 clear)
    top_r=70.0,                # sheet 24: the back frame's rounded top corners (E radius)
    pivot_z=470.0,             # sheet 24: the rear legs pivot on the main frame at seat-top level
    bar_z=170.0,               # sheet 24: the two low cross bars (front legs, rear legs)
    bar_d=16.0,                # E
    seat=(350.0, 360.0, 40.0),  # E: seat pan W x D x plan corner R (inside the rear legs; sheet 24 proportions)
    seat_y0=-270.0,            # sheet 24: the seat front sits just ahead of the front feet
    pan=(400.0, 420.0),        # E: the steel seat pan band (sheet 24: a black rim under the pad)
    pad=(5.0, 8.0),            # E: the vinyl pad's inset on the pan and its rounded top edge radius
    back=(690.0, 8.0, 14.0, 6.0),  # back pad: starts 690 up the main tube (sheet 24: the top ~21 % of the height),
                                   # 8 behind / 14 in front of the frame plane, front edge round 6 (E)
    folded_seat_z=(300.0, 660.0),  # E: the Folded state's seat, turned up inside the frame
)
# The main frame: front feet at y = -(d/2 - cap r); the back top is placed so the rear legs pivot half way
# (y_pivot = 0): folded, all four feet then stand on the floor (D). Sheet 24 reads the back top ~60-80 in front of
# the rear feet; this gives 79.

COUNTER = dict(                # G1 cash counter, sheet 25
    w=1397.0,                  # M [D34]
    d=610.0,                   # E* (bottom of a 610-914 range)
    h=965.0,                   # E (spec, lines up with the 965 showcases); sheet 25 agrees
    top_t=60.0,                # sheet 25: a thick white top (measured ~60-70 against the 965 call-out)
    top_r=(20.0, 12.0),        # sheet 25: plan corner R, rounded top edge R (E radii)
    overhang=25.0,             # sheet 25: the top overhangs the carcass all round (E 25)
    kick=(90.0, 40.0),         # sheet 25: recessed black kick: height (measured ~0.14 x the oak), recess (E)
    panel=25.0,                # E: carcass boards (sheet 25: thick oak panels)
    part_x=150.0,              # sheet 25 staff view: the partition between the bag bay (+X) and the knee space (-X)
    shelf=(500.0, 20.0, 20.0),  # sheet 25: the bay's white middle shelf: underside z, thickness, set back (E)
    housing=(440.0, 130.0, 450.0, 20.0),  # sheet 25: the cash-drawer housing under the top: inner W x H, depth,
                                          # board (fits G2 409 x 417 x 112, M [D35])
    grommet_top=(-200.0, 120.0, 31.0, 40.0),   # sheet 25: top grommet x, y, hole R, flange R (60 hole, E)
    grommet_panel=(-436.0, 195.0, 35.0, 50.0),  # sheet 25: modesty-panel grommet x, z, pocket R, flange R
                                               # (sheet 25 reads ~100-120 over the flange; E 100)
)

BAG = dict(                    # G11 kraft paper bag, sheet 27
    w=250.0, d=130.0, h=300.0,  # E (spec); sheet 27 call-outs agree
    t=0.5,                     # E: kraft paper thickness
    cuff=40.0,                 # E: the turned-over top band inside the rim (the handles are glued under it)
    gusset=(5.0, 14.0),        # sheet 27: the side gussets fold in along their centre crease: in at z 65 / at the rim
    crease=(80.0, 0.8),        # sheet 27: the front's bottom-fold crease: height, depth
    handle=(5.5, 45.0, 105.0, 38.0),  # sheet 27: twisted paper cord diameter, leg half-spread, loop height above
                                      # the rim, glued length below the rim (E)
    twist=40.0,                # E: the cord's twist, degrees per segment (real twisted faces)
    flat_t=3.0,                # sheet 27 (Folded flat): the flat bag's layered edge (E 3)
    flat_notch=(2.5, 0.6),     # sheet 27: the gusset fold between the layers at the long edges: depth, half height
    flat_handles=((45.0, 4.0, 16.0, 0.0), (39.0, 2.9, 10.0, 6.0)),  # sheet 27: the two loops lying out of the mouth,
                                               # nested: half-spread, centre height, lift angle, top short of the other (E)
)

# LOD0 budgets: the spec's Tris column (E). The added states take their parent's budget.
BUDGETS = {
    "SM_CSK_Table_Play": 1000,
    "SM_CSK_Chair_Folding": 1200, "SM_CSK_Chair_Folding_Folded": 1200,
    "SM_CSK_Counter_1397": 2000,
    "SM_CSK_Bag_Paper": 400, "SM_CSK_Bag_Paper_Flat": 400,
}

REF24 = "References/CardShop/csk_play_area.png (sheet 24)"
REF25 = "References/CardShop/csk_counter_pos.png (sheet 25)"
REF27 = "References/CardShop/csk_bag_mailers.png (sheet 27)"


# =========================================================================== small vector maths

def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def _rotate(v, k, ang):
    """Rodrigues: ``v`` about the unit axis ``k`` by ``ang`` radians."""
    c, s = math.cos(ang), math.sin(ang)
    return _add(_add(_mul(v, c), _mul(_cross(k, v), s)), _mul(k, _dot(k, v) * (1 - c)))


def _perp(d):
    """Two unit vectors perpendicular to the unit ``d`` (and to each other)."""
    a = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    e1 = _unit(_sub(a, _mul(d, _dot(a, d))))
    return e1, _cross(d, e1)


# =========================================================================== shape helpers

def _box(b: Builder, mn, mx, mat: int, **kw) -> None:
    lo = tuple(min(mn[i], mx[i]) for i in range(3))
    hi = tuple(max(mn[i], mx[i]) for i in range(3))
    b.box(lo, hi, mat=mat, **kw)


def _earclip(P: Sequence[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """Ear-clipping triangulation of a simple polygon (either winding); zero-area ears are never cut."""
    n = len(P)
    area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    idx = list(range(n)) if area > 0 else list(range(n - 1, -1, -1))

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9

    tris = []
    while len(idx) > 3:
        m = len(idx)
        reflex = [j for k, j in enumerate(idx) if cross(P[idx[k - 1]], P[j], P[idx[(k + 1) % m]]) <= 1e-9]
        for k in range(m):
            a, b_, c = idx[k - 1], idx[k], idx[(k + 1) % m]
            if cross(P[a], P[b_], P[c]) <= 1e-9:
                continue
            if any(inside(P[j], P[a], P[b_], P[c]) for j in reflex if j not in (a, b_, c)):
                continue
            tris.append((a, b_, c))
            idx.pop(k)
            break
        else:
            raise ValueError("ear clipping found no ear")
    tris.append(tuple(idx))
    return tris


def _tube(b: Builder, pts: Sequence[Vec3], r: float, sides: int, mat: int, up: Vec3 = (0.0, 0.0, 1.0),
          caps: Tuple[bool, bool] = (False, False), twist_deg: float = 0.0, phase: float = 0.5) -> None:
    """A round tube along an open polyline, mitred at the joints (parallel-transported frame seeded by ``up``).
    ``twist_deg`` turns each successive ring (a twisted cord: helical faces). Open ends are left open unless
    ``caps`` (an open end sits inside another part)."""
    n = len(pts)
    segs = n - 1
    d = [_unit(_sub(pts[i + 1], pts[i])) for i in range(segs)]
    nv = _sub(up, _mul(d[0], _dot(up, d[0])))
    if _dot(nv, nv) < 1e-9:
        nv = _perp(d[0])[0]
    nv = _unit(nv)
    frames = [(nv, _cross(d[0], nv))]
    for j in range(1, segs):
        a, c = d[j - 1], d[j]
        ax = _cross(a, c)
        s = math.sqrt(_dot(ax, ax))
        fn, fb = frames[-1]
        if s > 1e-9:
            ang = math.atan2(s, _dot(a, c))
            ax = _mul(ax, 1.0 / s)
            fn, fb = _rotate(fn, ax, ang), _rotate(fb, ax, ang)
        frames.append((fn, fb))
    rings = []
    for i in range(n):
        joint = 0 < i < n - 1
        tw = math.radians(twist_deg) * i
        angs = [2 * math.pi * (k + phase) / sides + tw for k in range(sides)]
        if joint:
            a, c = d[i - 1], d[i]
            fn, fb = frames[i - 1]
            m = _unit(_add(a, c))
        else:
            fn, fb = frames[0] if i == 0 else frames[-1]
        ring = []
        for t in angs:
            o = _add(_mul(fn, r * math.cos(t)), _mul(fb, r * math.sin(t)))
            if joint:
                o = _add(o, _mul(a, -_dot(o, m) / _dot(a, m)))
            ring.append(b.v(*_add(pts[i], o)))
        rings.append(ring)
    for j in range(segs):
        axis_mid = _mul(_add(pts[j], pts[j + 1]), 0.5)
        for k in range(sides):
            k1 = (k + 1) % sides
            q = [rings[j][k], rings[j][k1], rings[j + 1][k1], rings[j + 1][k]]
            cen = _mul(_add(_add(b.verts[q[0]], b.verts[q[1]]), _add(b.verts[q[2]], b.verts[q[3]])), 0.25)
            _face_out(b, q, _sub(cen, axis_mid), mat)
    if caps[0]:
        b.fill([rings[0]], mat, 0, _mul(d[0], -1.0))
    if caps[1]:
        b.fill([rings[-1]], mat, 0, d[-1])


def _floor_cap(b: Builder, foot: Vec3, d: Vec3, r: float, h: float, sides: int, mat: int) -> None:
    """A foot cap on a leg: a cylinder round the leg axis ``d`` (unit, pointing up the leg) through ``foot`` (on the
    floor), cut flat by the floor (z = 0) and square across the axis at ``h`` up the leg."""
    e1, e2 = _perp(d)
    bot, top = [], []
    for k in range(sides):
        t = 2 * math.pi * (k + 0.5) / sides
        o = _add(_mul(e1, r * math.cos(t)), _mul(e2, r * math.sin(t)))
        p = _add(foot, o)
        p = _sub(p, _mul(d, p[2] / d[2]))                  # slide along the axis onto the floor
        bot.append(b.v(*p))
        top.append(b.v(*_add(_add(foot, _mul(d, h)), o)))
    for k in range(sides):
        k1 = (k + 1) % sides
        q = [bot[k], bot[k1], top[k1], top[k]]
        cen = _mul(_add(_add(b.verts[q[0]], b.verts[q[1]]), _add(b.verts[q[2]], b.verts[q[3]])), 0.25)
        axis_pt = _add(foot, _mul(d, _dot(_sub(cen, foot), d)))
        _face_out(b, q, _sub(cen, axis_pt), mat)
    b.fill([bot], mat, 0, (0.0, 0.0, -1.0))
    b.fill([top], mat, 0, d)


def _revolve(b: Builder, c: Vec3, axis: Vec3, prof: Sequence[Tuple[float, float]], sides: int, mat: int) -> None:
    """Revolve a CLOSED profile [(r, a)] (a = distance along ``axis`` from ``c``) about the axis: a ring solid
    (grommets). The profile may wind either way."""
    e1, e2 = _perp(axis)
    n = len(prof)
    area = sum(prof[i][0] * prof[(i + 1) % n][1] - prof[(i + 1) % n][0] * prof[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    angs = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    rings = [[b.v(*_add(_add(c, _mul(axis, a)), _add(_mul(e1, r * math.cos(t)), _mul(e2, r * math.sin(t)))))
              for t in angs] for r, a in prof]
    for i in range(n):
        j = (i + 1) % n
        (r0, a0), (r1, a1) = prof[i], prof[j]
        on_r, on_a = (a1 - a0) * sgn, -(r1 - r0) * sgn        # the profile edge's outward normal in (r, a)
        for k in range(sides):
            k1 = (k + 1) % sides
            tm = (angs[k] + angs[k1]) / 2 if k1 else angs[k] + math.pi / sides
            radial = _add(_mul(e1, math.cos(tm)), _mul(e2, math.sin(tm)))
            _face_out(b, [rings[i][k], rings[i][k1], rings[j][k1], rings[j][k]],
                      _add(_mul(radial, on_r), _mul(axis, on_a)), mat)


def _cyl_axis(b: Builder, c: Vec3, axis: Vec3, r: float, a0: float, a1: float, sides: int, mat: int) -> None:
    """A closed cylinder of radius ``r`` along the unit ``axis`` from ``c + a0 axis`` to ``c + a1 axis``."""
    e1, e2 = _perp(axis)
    angs = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    rings = [[b.v(*_add(_add(c, _mul(axis, a)), _add(_mul(e1, r * math.cos(t)), _mul(e2, r * math.sin(t)))))
              for t in angs] for a in (a0, a1)]
    for k in range(sides):
        k1 = (k + 1) % sides
        tm = (angs[k] + angs[k1]) / 2 if k1 else angs[k] + math.pi / sides
        _face_out(b, [rings[0][k], rings[0][k1], rings[1][k1], rings[1][k]],
                  _add(_mul(e1, math.cos(tm)), _mul(e2, math.sin(tm))), mat)
    b.fill([rings[0]], mat, 0, _mul(axis, -1.0))
    b.fill([rings[1]], mat, 0, axis)


def _obox(b: Builder, p0: Vec3, p1: Vec3, side: Vec3, w: float, t: float, mat: int) -> None:
    """A flat bar from ``p0`` to ``p1``: width ``w`` along ``side`` (projected square to the bar), thickness ``t``."""
    ax = _unit(_sub(p1, p0))
    sd = _unit(_sub(side, _mul(ax, _dot(side, ax))))
    nn = _cross(ax, sd)
    v = {}
    for i, p in ((0, p0), (1, p1)):
        for j in (-1, 1):
            for k in (-1, 1):
                v[i, j, k] = b.v(*_add(p, _add(_mul(sd, j * w / 2), _mul(nn, k * t / 2))))
    quads = {(0, None, None): ((0, -1, -1), (0, -1, 1), (0, 1, 1), (0, 1, -1)),
             (1, None, None): ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1))}
    _face_out(b, [v[q] for q in quads[(0, None, None)]], _mul(ax, -1.0), mat)
    _face_out(b, [v[q] for q in quads[(1, None, None)]], ax, mat)
    for j in (-1, 1):
        _face_out(b, [v[0, j, -1], v[1, j, -1], v[1, j, 1], v[0, j, 1]], _mul(sd, j), mat)
    for k in (-1, 1):
        _face_out(b, [v[0, -1, k], v[1, -1, k], v[1, 1, k], v[0, 1, k]], _mul(nn, k), mat)


def _rr(w: float, d: float, r: float, segs: int, ins: float = 0.0, cx: float = 0.0, cy: float = 0.0):
    """A rounded rectangle inset by ``ins`` (same point count for every inset, so lofts stitch)."""
    pts = rounded_rect(w - 2 * ins, d - 2 * ins, max(r - ins, 0.5), segs)
    return [(x + cx, y + cy) for x, y in pts]


def _loft(b: Builder, outlines: Sequence[Tuple[Sequence[Tuple[float, float]], float]], mat: int,
          top: Optional[int] = 0, bottom: Optional[int] = 0, top_holes=(), bottom_holes=()) -> Tuple[List, List]:
    """Stack CCW outlines of equal point count at rising z and skin them (rounded edges as real rings). Caps are
    planar fills; ``*_holes`` are extra loops (vertex id lists) cut out of the caps. Returns (first, last) loop."""
    loops = [b.loop(o, z) for o, z in outlines]
    n = len(outlines[0][0])
    for la, lb in zip(loops[:-1], loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            b.face((la[i], la[j], lb[j], lb[i]), mat)
    if top is not None:
        b.fill([loops[-1], *top_holes], mat, top, (0, 0, 1))
    if bottom is not None:
        b.fill([loops[0], *bottom_holes], mat, bottom, (0, 0, -1))
    return loops[0], loops[-1]


def _round_rings(t: float, z0: float, r_top: float, r_bot: float, segs_top: int, segs_bot: int,
                 base_ins: float = 0.0) -> List[Tuple[float, float]]:
    """(inset, z) rings of a slab ``t`` thick from ``z0``: a quarter round ``r_top`` on the top edge and ``r_bot`` on
    the bottom edge, ``segs`` segments each (0 = square)."""
    rings = []
    if segs_bot and r_bot > 0:
        for k in range(segs_bot + 1):
            a = math.radians(90.0 * k / segs_bot)
            rings.append((base_ins + r_bot - r_bot * math.sin(a), z0 + r_bot - r_bot * math.cos(a)))
    else:
        rings.append((base_ins, z0))
    if segs_top and r_top > 0:
        for k in range(segs_top + 1):
            a = math.radians(90.0 * k / segs_top)
            rings.append((base_ins + r_top - r_top * math.cos(a), z0 + t - r_top + r_top * math.sin(a)))
    else:
        rings.append((base_ins, z0 + t))
    return rings


# =========================================================================== F1 play tables

def _tb_legs(L: float):
    """Leg geometry for one table: [(sx, sy, top point, knee points, foot point)]."""
    s = TABLE
    zt = s["h"] - s["top_t"]
    out = []
    for sx in (-1, 1):
        xt = sx * (L / 2 - s["leg_in"])
        xf = xt + sx * s["splay"]
        for sy in (-1, 1):
            y = sy * (s["d"] / 2 - s["leg_y"])
            top = (xt, y, zt + 0.5)
            knee = [(xt + sx * 4.0, y, s["knee_z"]), (xt, y, s["knee_z"] + 35.0)]   # bottom first
            out.append((sx, sy, top, knee, (xf, y, 0.0)))
    return out


def _tb_body(L: float, level: int) -> Tuple[Builder, Optional[Builder]]:
    """Sheet 24: a white blow-moulded top with rounded plan corners, a thick edge rounded over at the top and
    under at the bottom; per end a grey trestle leg frame: two tube legs kinked out toward the end below a cross
    brace, black foot caps, a folding flat-bar strut from each leg to the underside, small brackets under the
    top."""
    s = TABLE
    TOP, STEEL, RUBBER = 0, 1, 2
    D, t = s["d"], s["top_t"]
    zt = s["h"] - t
    b = Builder()
    segs = (4, 3, 1)[level]
    rt, rb = s["edge_r"]
    rings = _round_rings(t, zt, rt, rb, (3, 1, 0)[level], (2, 1, 0)[level])
    _loft(b, [(_rr(L, D, s["corner_r"], segs, ins), z) for ins, z in rings], TOP)
    r = s["leg_d"] / 2
    sides = (8, 6, 4)[level]
    cd, ch = s["cap"]
    for sx, sy, top, knee, foot in _tb_legs(L):
        low = _unit(_sub(knee[0], foot))                           # the lower leg's axis, pointing up
        start = _add(foot, _mul(low, 12.0 / low[2]))                # the tube starts inside the cap
        if level < 2:
            _tube(b, [start, *knee, top], r, sides, STEEL, up=(0.0, 1.0, 0.0))
            _floor_cap(b, foot, low, cd / 2, ch, sides, RUBBER)
        else:
            _tube(b, [(foot[0], foot[1], 0.0), top], r, sides, STEEL, up=(0.0, 1.0, 0.0), caps=(True, False))
    zb, bd = s["bar"]
    for sx in (-1, 1):                                              # cross brace between the front and back legs
        xt = sx * (L / 2 - s["leg_in"])
        yl = D / 2 - s["leg_y"]
        _tube(b, [(xt, -yl, zb), (xt, yl, zb)], bd / 2, (8, 6, 4)[level], STEEL, up=(0.0, 0.0, 1.0))
    if level == 2:
        return b, None
    e = Builder()
    zs, inward, bw, bt = s["brace"]
    bw_, bdp, bh = s["bracket"]
    for sx, sy, top, knee, foot in _tb_legs(L):
        xt, y = top[0], top[1]
        p0 = (xt - sx * (r - 3.0), y, zs)
        p1 = (xt - sx * inward, y, zt - bh / 2)
        _obox(e, p0, p1, (0.0, 1.0, 0.0), bw, bt, STEEL)             # folding strut
        if level == 0:
            _box(e, (xt - bw_ / 2, y - bdp / 2, zt - bh), (xt + bw_ / 2, y + bdp / 2, zt + 0.5), STEEL)
            _box(e, (p1[0] - bw_ / 2, y - bdp / 2, zt - bh), (p1[0] + bw_ / 2, y + bdp / 2, zt + 0.5), STEEL)
    return b, e


def item_table(seats: int) -> Item:
    s = TABLE
    L, D, H = s["lengths"][seats], s["d"], s["h"]
    m_count = s["matches"][seats]
    mw, md, mt = s["mat"]
    lods = [Lod(b, extra=e) for b, e in (_tb_body(L, k) for k in range(3))]
    sockets = [Socket("Seat", (0, 0, 0))]
    pitch = L / m_count                                  # the matches share the length evenly (1829: 609.7 >= 609.6)
    ym = D / 4                                           # mat centres: 2 x 356 = 712 <= 762 (D), 12.7 from the edges
    di, dd = s["deck_in"]
    chairs = []
    zones = []
    for m in range(1, m_count + 1):
        xm = -L / 2 + pitch * (m - 0.5)
        zones.append(xm)
        # player A sits on the customer side (-Y) facing +Y; the mat's top edge points away from its player
        sockets.append(Socket(f"Mat_{m}A", (xm, -ym, H)))
        sockets.append(Socket(f"Mat_{m}B", (xm, ym, H), (0.0, 0.0, 180.0)))
        # the deck on each player's mat, at the player's right-hand far corner (E)
        sockets.append(Socket(f"Deck_{m}A", (xm + mw / 2 - di, -ym + md / 2 - dd, H + mt)))
        sockets.append(Socket(f"Deck_{m}B", (xm - mw / 2 + di, ym - md / 2 + dd, H + mt), (0.0, 0.0, 180.0)))
        sockets.append(Socket(f"Zone_{m}", (xm, 0.0, H)))
        chairs += [(xm, -s["chair_y"], 180.0), (xm, s["chair_y"], 0.0)]
    for i, (x, y, rz) in enumerate(chairs, 1):          # chair Seat targets, each chair facing the table
        sockets.append(Socket(f"Chair_{i:02d}", (x, y, 0.0), (0.0, 0.0, rz)))
    legs = _tb_legs(L)
    xin, xout = L / 2 - s["leg_in"] - s["leg_d"] / 2 - 1.0, L / 2 - s["leg_in"] + s["splay"] + s["cap"][0] / 2
    yl = D / 2 - s["leg_y"] + s["cap"][0] / 2
    zt = H - s["top_t"]
    return Item(
        name=f"SM_CSK_Table_Play_{seats}", lods=lods,
        materials=["M_CSK_TableTop", "M_CSK_Steel", "M_CSK_Rubber"], projections={}, sockets=sockets,
        hulls=[((-L / 2, -D / 2, zt), (L / 2, D / 2, H)),
               ((-xout, -yl, 0.0), (-xin, yl, zt)), ((xin, -yl, 0.0), (xout, yl, zt))],
        budget=BUDGETS["SM_CSK_Table_Play"],
        data={"footprint_mm": [L, D, H], "pose": "upright", "pivot": "bottom-centre", "seats": seats,
              "matches": m_count, "match_pitch_mm": round(pitch, 3),
              "mat_mm": [mw, md, mt], "chair": "SM_CSK_Chair_Folding",
              "sockets_note": ("Mat_<m>A/B: playmat Seat (the centre of its back face) on the top; A on the "
                               "customer side (-Y), B turned 180. Deck_<m>A/B: on the mat at the player's "
                               "right-hand far corner. Zone_<m>: the match centre. Chair_NN: the chair's Seat, "
                               "facing the table (odd = side A, even = side B)."),
              "reference": REF24,
              "notes": ["Sheet 24: white top, thick rounded edge, grey trestle legs kinked out below a cross brace, "
                        "folding struts, black foot caps",
                        "3 matches on the 1829 table as the spec (D); sheet 24 draws one match per table (the "
                        "1524 / 914 layout); the user accepted this pick (log 2026-09-29)",
                        "Deck socket position on the mat is E (the playmat's own zones are E5's)"]},
    )


# =========================================================================== F2 folding chair

def _ch_dims():
    s = CHAIR
    cr = s["cap"][0] / 2
    yf, yr = -(s["d"] / 2 - cr), s["d"] / 2 - cr
    zt = s["h"] - s["tube"] / 2
    k = (yr - yf) / (2.0 * s["pivot_z"])               # tan of the main tube's lean: pivot half way (y 0), D
    ytop = yf + zt * k
    u = _unit((0.0, ytop - yf, zt))
    stop = math.hypot(ytop - yf, zt)                    # main tube length, foot axis point to the top centre line
    nf = _cross((1.0, 0.0, 0.0), u)                     # the frame plane's front normal (toward the sitter)
    yp = yf + s["pivot_z"] * k
    return dict(yf=yf, yr=yr, zt=zt, u=u, stop=stop, nf=nf, yp=yp, sp=s["pivot_z"] / u[2], k=k)


def _ch_frame(b: Builder, place, level: int, STEEL: int, VINYL: int, RUBBER: int, feet: bool) -> None:
    """The main frame (front legs running up into the back posts and over the top, one tube), its low cross bar,
    the back pad, the foot caps. ``place(s, x, n)`` maps frame-plane coordinates (s up the tube from the foot axis
    point, x across, n along the front normal) to the item frame."""
    s = CHAIR
    k = _ch_dims()
    mx, r, R = s["main_x"], s["tube"] / 2, s["top_r"]
    stop = k["stop"]
    sides = (10, 6, 4)[level]
    arc = (4, 2, 1)[level]
    s0 = 14.0 / k["u"][2]
    path = [place(s0, -mx, 0.0)]
    for i in range(arc + 1):
        a = math.radians(90.0 * i / arc)
        path.append(place(stop - R + R * math.sin(a), -(mx - R) - R * math.cos(a), 0.0))
    for i in range(arc, -1, -1):
        a = math.radians(90.0 * i / arc)
        path.append(place(stop - R + R * math.sin(a), (mx - R) + R * math.cos(a), 0.0))
    path.append(place(s0, mx, 0.0))
    nf = _sub(place(0.0, 0.0, 1.0), place(0.0, 0.0, 0.0))
    _tube(b, path, r, sides, STEEL, up=nf)
    sb = s["bar_z"] / k["u"][2]
    _tube(b, [place(sb, -mx, 0.0), place(sb, mx, 0.0)], s["bar_d"] / 2, (8, 6, 4)[level], STEEL, up=nf)
    # back pad: between the posts (4 into each tube), its top following the frame's top corners
    b0, nb, nfr, fr = s["back"]
    ro = R - r + 4.0

    def outline(ins: float):
        pts = [(-(mx - r + 4.0) + ins, b0 + ins), ((mx - r + 4.0) - ins, b0 + ins)]
        n_arc = (4, 2, 1)[level]
        rr = ro - ins
        for side in (1, -1):
            rng = range(n_arc + 1) if side == 1 else range(n_arc, -1, -1)
            for i in rng:
                a = math.radians(90.0 * i / n_arc)
                pts.append((side * ((mx - R) + rr * math.cos(a)), stop - R + rr * math.sin(a)))
        return pts                                      # (x, s): CCW seen from the front

    if level < 2:                                       # a small round at the back, the padded round at the front
        rings = [(outline(2.0), -nb), (outline(0.0), -nb + 2.0), (outline(0.0), nfr - fr), (outline(fr), nfr)]
    else:
        rings = [(outline(0.0), -nb), (outline(0.0), nfr)]
    loops = [[b.v(*place(sv, x, n)) for x, sv in o] for o, n in rings]
    m = len(rings[0][0])
    for la, lb in zip(loops[:-1], loops[1:]):
        for i in range(m):
            j = (i + 1) % m
            q = [la[i], la[j], lb[j], lb[i]]
            cen = _mul(_add(_add(b.verts[q[0]], b.verts[q[1]]), _add(b.verts[q[2]], b.verts[q[3]])), 0.25)
            mid = place(0.5 * (b0 + stop), 0.0, 0.0)
            _face_out(b, q, _sub(cen, _add(mid, _mul(nf, _dot(_sub(cen, mid), nf)))), VINYL)
    b.fill([loops[0]], VINYL, 0, _mul(nf, -1.0))
    b.fill([loops[-1]], VINYL, 0, nf)
    if feet:
        up = _unit(_sub(place(1.0, 0.0, 0.0), place(0.0, 0.0, 0.0)))
        for sx in (-1, 1):
            foot = place(0.0, sx * mx, 0.0)
            if level < 2:
                _floor_cap(b, foot, up, s["cap"][0] / 2, s["cap"][1], sides, RUBBER)


def _ch_rear(b: Builder, foot_y: float, top_pt, level: int, STEEL: int, RUBBER: int, fold_dir=None) -> None:
    """The rear legs (two tubes inside the main frame, pivoting on it), their low cross bar and foot caps.
    ``top_pt(x)`` is the pivot point on each side; the legs run from (x, foot_y, 0) up to it."""
    s = CHAIR
    rx, r = s["rear_x"], s["tube"] / 2
    sides = (10, 6, 4)[level]
    ends = []
    for sx in (-1, 1):
        foot = (sx * rx, foot_y, 0.0)
        top = top_pt(sx * rx)
        v = _unit(_sub(top, foot))
        start = _add(foot, _mul(v, 14.0 / v[2]))
        _tube(b, [start, _add(top, _mul(v, 16.0))], r, sides, STEEL, up=(1.0, 0.0, 0.0), caps=(False, True))
        if level < 2:
            _floor_cap(b, foot, v, s["cap"][0] / 2, s["cap"][1], sides, RUBBER)
        ends.append((foot, v))
    (f0, v0), (f1, v1) = ends
    t = s["bar_z"] / v0[2]
    _tube(b, [_add(f0, _mul(v0, t)), _add(f1, _mul(v1, t))], s["bar_d"] / 2, (8, 6, 4)[level], STEEL,
          up=(0.0, 0.0, 1.0))


def _ch_seat(b: Builder, to_world, level: int, STEEL: int, VINYL: int) -> None:
    """The seat in its open pose coordinates (x, y, z), mapped by ``to_world``: a steel pan band, a vinyl pad with a
    rounded top edge, and a bracket to the main tube on each side."""
    s = CHAIR
    k = _ch_dims()
    W, Dp, cr = s["seat"]
    y0 = s["seat_y0"]
    yc = y0 + Dp / 2
    z0, z1 = s["pan"]
    pin, pr = s["pad"]
    segs = (4, 2, 1)[level]

    def loft(outlines, mat):
        loops = [[b.v(*to_world((x, y, z))) for x, y in o] for o, z in outlines]
        n = len(outlines[0][0])
        cz = 0.5 * (outlines[0][1] + outlines[-1][1])
        for la, lb in zip(loops[:-1], loops[1:]):
            for i in range(n):
                j = (i + 1) % n
                q = [la[i], la[j], lb[j], lb[i]]
                cen = _mul(_add(_add(b.verts[q[0]], b.verts[q[1]]), _add(b.verts[q[2]], b.verts[q[3]])), 0.25)
                _face_out(b, q, _sub(cen, to_world((0.0, yc, cz))), mat)
        top_n = _sub(to_world((0.0, 0.0, 1.0)), to_world((0.0, 0.0, 0.0)))
        b.fill([loops[-1]], mat, 0, top_n)
        b.fill([loops[0]], mat, 0, _mul(top_n, -1.0))

    pan = [(2.0, z0), (0.0, z0 + 2.0), (0.0, z1 - 1.5), (1.5, z1)] if level < 2 else [(0.0, z0), (0.0, z1)]
    loft([(_rr(W, Dp, cr, segs, ins, 0.0, yc), z) for ins, z in pan], STEEL)     # the pan's rolled edges
    ring = _round_rings(s["seat_h"] - (z1 - 2.0), z1 - 2.0, pr, 0.0, (3, 1, 0)[level], 0, pin)
    loft([(_rr(W, Dp, cr, segs, ins, 0.0, yc), z) for ins, z in ring], VINYL)
    if level < 2:                                       # side brackets to the main tube (sheet 24: hidden hangers)
        zb = z0 + 3.0
        ym = k["yf"] + zb * k["k"]
        for sx in (-1, 1):
            xa, xb = sx * (W / 2 - 3.0), sx * (s["main_x"] - 4.0)
            lo = (min(xa, xb), ym - 15.0, zb)
            hi = (max(xa, xb), ym + 15.0, zb + 10.0)
            c = [to_world((x, y, z)) for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])]
            ids = [b.v(*p) for p in c]
            cen = to_world(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
            for quad in ((0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)):
                q = [ids[i] for i in quad]
                fc = _mul(_add(_add(b.verts[q[0]], b.verts[q[1]]), _add(b.verts[q[2]], b.verts[q[3]])), 0.25)
                _face_out(b, q, _sub(fc, cen), STEEL)


def _ch_open(level: int) -> Builder:
    s = CHAIR
    k = _ch_dims()
    STEEL, VINYL, RUBBER = 0, 1, 2
    u, nf, yf = k["u"], k["nf"], k["yf"]

    def place(sv, x, n):
        return (x, yf + u[1] * sv + nf[1] * n, u[2] * sv + nf[2] * n)

    b = Builder()
    _ch_frame(b, place, level, STEEL, VINYL, RUBBER, feet=True)
    pv = place(k["sp"], 0.0, 0.0)
    _ch_rear(b, k["yr"], lambda x: (x, pv[1], pv[2]), level, STEEL, RUBBER)
    _ch_seat(b, lambda p: p, level, STEEL, VINYL)
    if level < 2:                                       # pivot bolts through both tubes
        for sx in (-1, 1):
            x0, x1 = sx * (s["rear_x"] - s["tube"] / 2 + 2.0), sx * (s["main_x"] + s["tube"] / 2 + 3.0)
            _tube(b, [(x0, pv[1], pv[2]), (x1, pv[1], pv[2])], 5.0, (8, 6)[level], STEEL, caps=(True, True))
    return b


def _ch_folded(level: int) -> Builder:
    """Sheet 24 Folded: the main frame stands upright on its front feet, the rear legs fold up behind it (parallel,
    in the plane 22 behind), the seat turns up inside the frame, its pad toward the back."""
    s = CHAIR
    k = _ch_dims()
    STEEL, VINYL, RUBBER = 0, 1, 2
    gap = s["tube"]

    def place(sv, x, n):
        return (x, -n, sv)

    b = Builder()
    _ch_frame(b, place, level, STEEL, VINYL, RUBBER, feet=True)
    zp = k["sp"]
    _ch_rear(b, gap, lambda x: (x, gap, zp), level, STEEL, RUBBER)
    zf0, zf1 = s["folded_seat_z"]
    y0 = s["seat_y0"]
    yface = 24.0                                        # the pad top's plane: its hangers reach the main tubes

    def to_world(p):
        x, y, z = p
        return (x, yface + (z - s["seat_h"]), zf1 - (y - y0))

    _ch_seat(b, to_world, level, STEEL, VINYL)
    if level < 2:
        for sx in (-1, 1):
            x0, x1 = sx * (s["rear_x"] - s["tube"] / 2 + 2.0), sx * (s["main_x"] + s["tube"] / 2 + 3.0)
            _tube(b, [(x0, gap / 2, zp), (x1, gap / 2, zp)], 5.0, (8, 6)[level], STEEL, caps=(True, True))
    return b


def item_chair() -> Item:
    s = CHAIR
    k = _ch_dims()
    W, Dp, _ = s["seat"]
    yc = s["seat_y0"] + Dp / 2
    lods = [Lod(_ch_open(k)) for k in range(3)]        # rounds are modelled (no auto bevel: budget)
    top = (0.0, k["yf"] + k["u"][1] * k["stop"], k["zt"])
    hw, hd = s["w"] / 2, s["d"] / 2
    return Item(
        name="SM_CSK_Chair_Folding", lods=lods, materials=["M_CSK_SteelBlack", "M_CSK_Vinyl", "M_CSK_Rubber"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Sit", (0.0, yc, s["seat_h"])),
                 Socket("Grip", top)],
        hulls=[((-hw, -hd, 0.0), (hw, hd, s["pan"][0])),
               ((-W / 2, s["seat_y0"], s["pan"][0]), (W / 2, s["seat_y0"] + Dp, s["seat_h"])),
               ((-hw, k["yp"] - 15.0, s["seat_h"]), (hw, top[1] + s["tube"] / 2, s["h"]))],
        budget=BUDGETS["SM_CSK_Chair_Folding"],
        data={"footprint_mm": [s["w"], s["d"], s["h"]], "pose": "upright", "pivot": "bottom-centre",
              "front": "-Y (the sitter faces -Y)", "states": ["Open", "Folded"],
              "folded": "SM_CSK_Chair_Folding_Folded", "seat_h_mm": s["seat_h"],
              "reference": REF24,
              "notes": ["Sheet 24: black tube frame (front legs run up into the back posts and over the top), rear "
                        "legs pivoting on it at seat level, two low cross bars, padded black vinyl seat on a steel "
                        "pan and a padded back, black foot caps",
                        "Back top 79 in front of the rear feet (sheet 24 reads 60-80): chosen so the pivot sits half "
                        "way and all four feet stand when folded (D)"]},
    )


def item_chair_folded() -> Item:
    s = CHAIR
    k = _ch_dims()
    lods = [Lod(_ch_folded(k)) for k in range(3)]
    H = k["stop"] + s["tube"] / 2
    hw = s["w"] / 2
    return Item(
        name="SM_CSK_Chair_Folding_Folded", lods=lods,
        materials=["M_CSK_SteelBlack", "M_CSK_Vinyl", "M_CSK_Rubber"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, 0.0, k["stop"]))],
        hulls=[((-hw, -25.0, 0.0), (hw, s["tube"] + s["cap"][0] / 2, H))],
        budget=BUDGETS["SM_CSK_Chair_Folding_Folded"],
        data={"footprint_mm": [s["w"], round(s["tube"] + s["cap"][0] / 2 + 25.0, 3), round(H, 3)],
              "pose": "upright, folded flat", "pivot": "bottom-centre (the main frame's plane)",
              "state_of": "SM_CSK_Chair_Folding", "reference": REF24,
              "notes": [f"Height {H:.0f}: the folded frame stands at its tube length. Sheet 24's folded view repeats "
                        "the open 800 call-out; a frame that reaches 800 open at this lean cannot fold shorter "
                        "(logged deviation)"]},
    )


# =========================================================================== G1 cash counter

def _ct_dims():
    s = COUNTER
    W, D, H = s["w"], s["d"], s["h"]
    ov, p = s["overhang"], s["panel"]
    kh, ki = s["kick"]
    zt = H - s["top_t"]
    cx, cy = W / 2 - ov, D / 2 - ov                     # carcass half sizes
    px = s["part_x"]
    return dict(W=W, D=D, H=H, zt=zt, cx=cx, cy=cy, p=p, kh=kh, ki=ki, px=px,
                bay=(px + p / 2, cx - p), knee=(-cx + p, px - p / 2), yin=-cy + p)


def _ct_lod(level: int) -> Lod:
    """Sheet 25: a light-oak carcass on a recessed black kick under a thick white top that overhangs all round,
    its top edge rounded. Customer side (-Y): a plain oak panel. Staff side (+Y): the bag bay at +X (open, a white
    middle shelf, the oak bottom as the bag shelf), a partition to the floor, the knee space at -X with the cash
    drawer housing slung under the top from the partition, a round grommet low in the modesty panel and one in
    the top."""
    s = COUNTER
    k = _ct_dims()
    OAK, TOP, BLACK = 0, 1, 2
    W, D, H, zt, cx, cy, p, kh, ki = (k[n] for n in ("W", "D", "H", "zt", "cx", "cy", "p", "kh", "ki"))
    bx0, bx1 = k["bay"]
    nx0, nx1 = k["knee"]
    yin = k["yin"]
    b = Builder()
    b.box((-cx, -cy, kh), (cx, cy, zt + 0.5), mat=OAK)    # the carcass block (one closed shell), 0.5 into the top
    ops = []
    bay = Builder()
    bay.box((bx0, yin, kh + p), (bx1, cy + 1.0, zt + 1.0), mat=OAK)
    knee = Builder()
    knee.box((nx0, yin, kh - 1.0), (nx1, cy + 1.0, zt + 1.0), mat=OAK)
    ops += [("DIFFERENCE", bay), ("DIFFERENCE", knee)]
    gx, gz, gr, gf = s["grommet_panel"]
    if level == 0:                                         # the modesty-panel grommet's pocket (a blind cup)
        cup = Builder()
        _cyl_axis(cup, (gx, yin + 1.0, gz), (0.0, -1.0, 0.0), gr, 0.0, 14.0, 16, BLACK)
        ops.append(("DIFFERENCE", cup))
    e = Builder()
    # worktop: rounded plan corners, the top edge rounded over (real rings), a small round under; the grommet hole
    cr, er = s["top_r"]
    segs = (4, 3, 1)[level]
    rings = _round_rings(s["top_t"], zt, er, 2.0, (3, 1, 0)[level], (1, 1, 0)[level])
    gtx, gty, ghr, gfr = s["grommet_top"]
    outlines = [(_rr(W, D, cr, segs, ins), z) for ins, z in rings]
    if level == 0:
        hs = 16
        hole = [(gtx + ghr * math.cos(2 * math.pi * (i + 0.5) / hs), gty + ghr * math.sin(2 * math.pi * (i + 0.5) / hs))
                for i in range(hs)]
        ht, hb = e.loop(hole, H), e.loop(hole, zt)
        _loft(e, outlines, TOP, top_holes=[ht], bottom_holes=[hb])
        for i in range(hs):
            j = (i + 1) % hs
            q = [ht[i], ht[j], hb[j], hb[i]]
            mx_, my_ = (hole[i][0] + hole[j][0]) / 2, (hole[i][1] + hole[j][1]) / 2
            _face_out(e, q, (gtx - mx_, gty - my_, 0.0), TOP)
        # the grommet liner: a black sleeve with a flange on the top
        _revolve(e, (gtx, gty, H), (0.0, 0.0, 1.0),
                 [(ghr - 4.5, -40.0), (ghr - 0.5, -40.0), (ghr - 0.5, -0.5), (gfr, -0.5), (gfr, 2.0),
                  (gfr - 1.5, 3.5), (ghr - 4.5, 3.5)], 16, BLACK)
        # the modesty-panel grommet's flange ring, 3 proud of the panel's inner face
        _revolve(e, (gx, yin, gz), (0.0, 1.0, 0.0),
                 [(gr - 0.5, -0.5), (gf, -0.5), (gf, 2.0), (gf - 1.5, 3.0), (gr - 0.5, 3.0)], 16, BLACK)
    else:
        _loft(e, outlines, TOP)
    # kick: recessed along the customer side, both ends and under the bay; open under the knee space
    y0k = -cy + ki
    _box(e, (-cx + ki + 0.5, y0k, 0.0), (cx - ki - 0.5, y0k + 18.0, kh + 0.5), BLACK)          # front board
    _box(e, (-cx + ki, y0k + 17.0, 0.0), (-cx + ki + 18.0, cy - ki, kh + 0.5), BLACK)          # -X end board
    _box(e, (bx0 - 0.5, y0k + 17.0, 0.0), (cx - ki, cy - ki, kh + 0.5), BLACK)                 # bay plinth
    _box(e, (bx0 - p, y0k + 19.0, 0.0), (bx0, cy - 0.5, kh + 0.5), OAK)                        # partition foot
    if level < 2:
        sz, st, sb = s["shelf"]                                                                 # bay middle shelf
        _box(e, (bx0 - 0.5, yin - 0.5, sz), (bx1 + 0.5, cy - sb, sz + st), TOP)
        hw, hh, hd, hb = s["housing"]                                                           # drawer housing
        zf = zt - hh
        xs = nx1 - hw
        _box(e, (xs - hb + 0.5, cy - hd + 0.5, zf - hb), (nx1 + 0.5, cy - 0.5, zf), OAK)       # its floor
        _box(e, (xs - hb, cy - hd, zf - hb), (xs, cy, zt + 0.5), OAK)                           # its side
    return Lod(b, bevel_mm=1.5 if level == 0 else None, ops=ops, bevel_first=True, extra=e)


def item_counter() -> Item:
    s = COUNTER
    k = _ct_dims()
    W, D, H, zt, cx, cy, p, kh = (k[n] for n in ("W", "D", "H", "zt", "cx", "cy", "p", "kh"))
    bx0, bx1 = k["bay"]
    nx0, nx1 = k["knee"]
    hw, hh, hd, hb = s["housing"]
    lods = [_ct_lod(i) for i in range(3)]
    R = (0.0, 0.0, 180.0)                     # faces the staff (+Y)
    drawer = ((nx1 - hw / 2), cy - 5.0 - 417.0 / 2, zt - hh)
    sockets = [
        Socket("Seat", (0, 0, 0)),
        Socket("POS", (-340.0, 60.0, H), R),                 # screen faces the staff, beside the top grommet
        Socket("Drawer", drawer),                            # G2 Seat (closed), its tray slides to the staff (+Y)
        Socket("Terminal", (260.0, -190.0, H)),              # customer side, facing the customer
        Socket("Printer", (40.0, 130.0, H), R),
        Socket("Scanner", (430.0, 90.0, H), R),
        Socket("Drop", (-80.0, -170.0, H)),                  # the customer's item drop
        Socket("PriceGun", (590.0, 190.0, H), R),
        Socket("Bag", ((bx0 + bx1) / 2, (k["yin"] + cy) / 2, kh + p)),   # the bag shelf (the bay's oak bottom)
        Socket("Phone", (-560.0, 190.0, H), R),
        Socket("Staff", ((nx0 + nx1) / 2, cy + 320.0, 0.0)),  # where the staff stands, facing the customer (-Y)
        Socket("Snap_L", (-W / 2, 0.0, 0.0)), Socket("Snap_R", (W / 2, 0.0, 0.0)),
    ]
    return Item(
        name="SM_CSK_Counter_1397", lods=lods, materials=["M_CSK_Oak", "M_CSK_Laminate", "M_CSK_Base"],
        projections={}, sockets=sockets,
        hulls=[((-W / 2, -D / 2, zt), (W / 2, D / 2, H)),                     # worktop
               ((bx0 - p, -cy, 0.0), (cx, cy, zt)),                          # bay pedestal + partition
               ((-cx, -cy, 0.0), (bx0 - p, -cy + p, zt)),                     # modesty / customer panel
               ((-cx, -cy + p, 0.0), (-cx + p, cy, zt))],                     # -X end panel
        budget=BUDGETS["SM_CSK_Counter_1397"],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "run": "Snap_L / Snap_R at the worktop ends", "slots": "Carcass = M_CSK_Oak, Top = M_CSK_Laminate "
              "(worktop + bay shelf), Trim = M_CSK_Base (kick, grommets)",
              "drawer": {"socket": "Drawer", "mesh": "SM_CSK_CashDrawer", "housing_inner_mm": [hw, hd, hh]},
              "bag_shelf": {"socket": "Bag", "clear_mm": [round(bx1 - bx0, 3), round(cy - k["yin"], 3),
                                                          round(s["shelf"][0] - kh - p, 3)],
                            "middle_shelf_z_mm": s["shelf"][0] + s["shelf"][1]},
              "reference": REF25,
              "notes": ["Sheet 25 layout: bag bay at +X (the staff's left), knee space at -X with the drawer "
                        "housing under the top against the partition, grommet low in the modesty panel and one in "
                        "the top; the customer side is a plain panel (the modesty grommet is a blind cup, so the "
                        "customer face stays plain as drawn)",
                        "Device sockets: sheet 25's two views place the devices differently; the layout here is E "
                        "(screen near the top grommet, terminal on the customer side)",
                        "4 hulls (spec 3): the knee space needs the modesty and end panels as their own boxes"]},
    )


# =========================================================================== G11 kraft paper bag

def _offset_poly(pts, d: float):
    """Inward offset of a CCW polygon by ``d`` (mitred)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1])
        e1 = (p2[0] - p1[0], p2[1] - p1[1])
        l0, l1 = math.hypot(*e0), math.hypot(*e1)
        n0 = (-e0[1] / l0, e0[0] / l0)
        n1 = (-e1[1] / l1, e1[0] / l1)
        m = (n0[0] + n1[0], n0[1] + n1[1])
        ml = math.hypot(*m)
        m = (m[0] / ml, m[1] / ml)
        c = m[0] * n1[0] + m[1] * n1[1]
        out.append((p1[0] + m[0] * d / c, p1[1] + m[1] * d / c))
    return out


def _bag_ring(z: float, dent: float = 0.0):
    """The bag's outer section at height z: front and back panels, each side gusset folded in along its centre."""
    s = BAG
    w, d, h = s["w"] / 2, s["d"] / 2, s["h"]
    g65, gtop = s["gusset"]
    g = g65 * z / 65.0 if z <= 65.0 else g65 + (gtop - g65) * (z - 65.0) / (h - 65.0)
    return [(-w, -d + dent), (w, -d + dent), (w - g, 0.0), (w, d), (-w, d), (-w + g, 0.0)]


def _bag_handle(b: Builder, y: float, level: int, mat: int) -> None:
    s = BAG
    hd, hx, hh, hg = s["handle"]
    top = s["h"] + hh - hd / 2
    zc = top - hx
    n_arc = (7, 4, 2)[level]
    path = [(-hx, y, s["h"] - hg), (-hx, y, zc)]
    for i in range(1, n_arc):
        a = math.pi - math.pi * i / n_arc
        path.append((hx * math.cos(a), y, zc + hx * math.sin(a)))
    path += [(hx, y, zc), (hx, y, s["h"] - hg)]
    _tube(b, path, hd / 2, (6, 4, 3)[level], mat, up=(0.0, 1.0, 0.0), caps=(level < 2, level < 2),
          twist_deg=s["twist"] if level == 0 else 0.0)


def _bag_open(level: int) -> Builder:
    """Sheet 27 Open: a paper shell (outside + inside skins, rim), side gussets folded in along their centre
    crease with the bottom gusset triangles as real folds, the front's bottom-fold crease, the turned top band
    inside, two twisted paper handles glued inside the front and back walls."""
    s = BAG
    t, h = s["t"], s["h"]
    KRAFT, PRINT = 0, 1
    cz, cd = s["crease"]
    b = Builder()
    if level == 0:
        zs = [0.0, 65.0, cz, h]
        dents = [0.0, 0.0, cd, 0.0]
    elif level == 1:
        zs, dents = [0.0, 65.0, h], [0.0, 0.0, 0.0]
    else:
        zs, dents = [0.0, h], [0.0, 0.0]
    outer = [[b.v(x, y, z) for x, y in _bag_ring(z, dn)] for z, dn in zip(zs, dents)]
    # inner skin: offset by t (2 t in the turned top band); the inside floor at z = t
    if level == 0:
        izs = [(t, t, 0.0), (65.0, t, 0.0), (cz, t, cd), (h - s["cuff"], t, 0.0), (h - s["cuff"], 2 * t, 0.0),
               (h, 2 * t, 0.0)]
    elif level == 1:
        izs = [(t, t, 0.0), (65.0, t, 0.0), (h, t, 0.0)]
    else:
        izs = [(t, t, 0.0), (h, t, 0.0)]
    inner = [[b.v(x, y, z) for x, y in _offset_poly(_bag_ring(z, dn), off)] for z, off, dn in izs]

    def band(ra, rb, lower: bool, flip: bool):
        """Faces between two 6-point rings. Front (0-1) and back (3-4) panels: print regions on the outside;
        the gusset halves are split into triangles, their diagonal from the outer corner at the lower ring to the
        crease at the upper ring (the bottom gusset triangle's fold on the lowest band)."""
        for i in range(6):
            j = (i + 1) % 6
            if i in (0, 3):
                q = (ra[i], ra[j], rb[j], rb[i])
                reg = 0 if flip else (R_FRONT if i == 0 else R_BACK)
                mat = KRAFT if flip else PRINT
                b.face(tuple(reversed(q)) if flip else q, mat, reg)
                continue
            if i in (1, 4):          # corner -> crease: diagonal corner(low) - crease(high)
                tris = [(ra[i], ra[j], rb[j]), (ra[i], rb[j], rb[i])]
            else:                    # crease -> corner: diagonal corner(low) - crease(high)
                tris = [(ra[i], ra[j], rb[i]), (ra[j], rb[j], rb[i])]
            for tr in tris:
                b.face(tuple(reversed(tr)) if flip else tr, KRAFT)

    for a, c in zip(outer[:-1], outer[1:]):
        band(a, c, True, False)
    for a, c in zip(inner[:-1], inner[1:]):
        if [b.verts[a[0]][2]] == [b.verts[c[0]][2]]:          # the turned band's lower edge: a ring facing down
            for i in range(6):
                j = (i + 1) % 6
                b.face((a[j], a[i], c[i], c[j]), KRAFT)
            continue
        band(a, c, True, True)
    ot, it = outer[-1], inner[-1]
    for i in range(6):                                        # the rim
        j = (i + 1) % 6
        b.face((ot[i], ot[j], it[j], it[i]), KRAFT)
    b.fill([outer[0]], KRAFT, 0, (0, 0, -1))
    b.fill([inner[0]], KRAFT, 0, (0, 0, 1))
    hy = s["d"] / 2 - (2 * t if level == 0 else t) - s["handle"][0] / 2 - 0.3
    for y in (-hy, hy):
        _bag_handle(b, y, level, KRAFT)
    return b


def _bag_projections():
    s = BAG
    w, h = s["w"], s["h"]
    return {R_FRONT: lambda x, y, z: (inset((x + w / 2) / w), inset(z / h)),
            R_BACK: lambda x, y, z: (1.0 + inset((w / 2 - x) / w), inset(z / h))}


def item_bag() -> Item:
    s = BAG
    w, d, h, t = s["w"], s["d"], s["h"], s["t"]
    hd, hx, hh, hg = s["handle"]
    gtop = s["gusset"][1]
    lods = [Lod(_bag_open(k)) for k in range(3)]
    cav = [[-(w / 2 - t - gtop), -(d / 2 - 2 * t), t], [w / 2 - t - gtop, d / 2 - 2 * t, h]]
    return Item(
        name="SM_CSK_Bag_Paper", lods=lods, materials=["M_CSK_Kraft", "M_CSK_BagPrint"],
        projections=_bag_projections(),
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Contents", (0.0, 0.0, t), (0.0, 0.0, 90.0), kind="CONTAIN"),
                 Socket("Grip", (0.0, 0.0, h + hh - hd / 2))],
        hulls=[((-w / 2, -d / 2, 0.0), (w / 2, d / 2, h))],
        budget=BUDGETS["SM_CSK_Bag_Paper"],
        data={"footprint_mm": [w, d, h], "pose": "upright", "pivot": "bottom-centre", "states": ["Open", "Flat"],
              "flat": "SM_CSK_Bag_Paper_Flat", "handles_top_mm": h + hh,
              "contain": {"Contents": {"socket": "Contents", "cavity_mm": cav,
                                       "accepts": ["Card", "CardProt", "Slab", "Pack", "Deck"],
                                       "pose": "lying, turned 90 deg about Z (length across the bag)"}},
              "print": "front / back outer panels: M_CSK_BagPrint, UV0 tiles (0,0) / (1,0) (the shop-logo cell)",
              "reference": REF27,
              "notes": ["Sheet 27: gussets folded in along the centre crease with the bottom triangles, the front's "
                        "bottom-fold crease, a turned top band inside, twisted paper handles (real twisted faces)",
                        "Handles rise 105 above the rim (sheet 27); the render bounds are 300 + 105 tall",
                        "A BoxS fits the bag unturned (140 x 80); the Contents socket is turned for the long flat "
                        "classes (a slab is 134 long, the bag 128 deep inside)"]},
    )


def _bag_flat_lod(level: int) -> Builder:
    """Sheet 27 Folded flat: the knocked-down bag lying on its back, front up (flat-item pose): a layered slab with
    the gusset fold showing between the layers along both long edges, the bottom-fold crease across the front, and
    the two handle loops lying out of the mouth, nested, springing up off the table."""
    s = BAG
    w, h = s["w"] / 2, s["h"] / 2
    T = s["flat_t"]
    nd, nh = s["flat_notch"]
    KRAFT, PRINT = 0, 1
    cz, cd = s["crease"]
    b = Builder()

    def prof(top: float):
        if level == 2:
            return [(-w, 0.0), (w, 0.0), (w, top), (-w, top)]
        return [(-w, 0.0), (w, 0.0), (w, T / 2 - nh), (w - nd, T / 2), (w, T / 2 + nh), (w, top), (-w, top),
                (-w, T / 2 + nh), (-w + nd, T / 2), (-w, T / 2 - nh)]

    yc = -h + cz
    if level == 0:
        secs = [(-h, prof(T)), (yc - 1.0, prof(T)), (yc, prof(T - cd / 2)), (yc + 1.0, prof(T)), (h, prof(T))]
    else:
        secs = [(-h, prof(T)), (h, prof(T))]
    rings = [[b.v(x, y, z) for x, z in p] for y, p in secs]
    n = len(secs[0][1])
    itop = n // 2 if level == 2 else 5                        # the top edge: point itop -> itop + 1
    for ra, rb in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            q = [ra[i], rb[i], rb[j], ra[j]]
            p0, p1 = secs[0][1][i], secs[0][1][j]
            nrm = (p1[1] - p0[1], 0.0, -(p1[0] - p0[0]))       # outward in XZ for a CCW (x, z) profile
            if i == itop:
                _face_out(b, q, (0, 0, 1), PRINT, R_FRONT)
            elif i == 0:
                _face_out(b, q, (0, 0, -1), PRINT, R_BACK)
            else:
                _face_out(b, q, nrm, KRAFT)
    tris = _earclip(secs[0][1])
    for ring, nrm in ((rings[0], (0, -1, 0)), (rings[-1], (0, 1, 0))):
        for tr in tris:
            _face_out(b, [ring[tr[0]], ring[tr[1]], ring[tr[2]]], nrm, KRAFT)
    hd, _, hh, _ = s["handle"]
    n_arc = (7, 4, 2)[level]
    for hx, zc, lift, short in s["flat_handles"]:
        a = math.radians(lift)
        leg = hh - hd / 2 - hx - short

        def pt(x, sv):
            return (x, h + 0.5 + sv * math.cos(a), zc + sv * math.sin(a))

        path = [pt(-hx, 0.0), pt(-hx, leg)]
        for i in range(1, n_arc):
            ang = math.pi - math.pi * i / n_arc
            path.append(pt(hx * math.cos(ang), leg + hx * math.sin(ang)))
        path += [pt(hx, leg), pt(hx, 0.0)]
        up = (0.0, -math.sin(a), math.cos(a))
        _tube(b, path, hd / 2, (6, 4, 3)[level], KRAFT, up=up, caps=(True, True),
              twist_deg=s["twist"] if level == 0 else 0.0)
    return b


def item_bag_flat() -> Item:
    s = BAG
    w, h, T = s["w"], s["h"], s["flat_t"]
    hd, _, hh, _ = s["handle"]
    lods = [Lod(_bag_flat_lod(k)) for k in range(3)]
    pad = max(0.0, (2.0 - T) / 2)
    return Item(
        name="SM_CSK_Bag_Paper_Flat", lods=lods, materials=["M_CSK_Kraft", "M_CSK_BagPrint"],
        projections={R_FRONT: _planar(-w / 2, -h / 2, w, h),
                     R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, h / 2 + hh - hd, T)), Socket("Stack", (0, 0, T))],
        hulls=[((-w / 2, -h / 2, -pad), (w / 2, h / 2, T + pad))],
        budget=BUDGETS["SM_CSK_Bag_Paper_Flat"],
        data={"footprint_mm": [w, h, T], "pose": "flat, front up, top edge +Y", "pivot": "centre of the back face",
              "state_of": "SM_CSK_Bag_Paper", "stack": {"socket": "Stack", "pitch_mm": T, "max": 25},
              "reference": REF27,
              "notes": ["Sheet 27 'Folded flat': handles lie out of the mouth (+Y), springing up off the table",
                        "The two loops are nested (half-spread 45 and 39) so the cords never cross"]},
    )


# =========================================================================== registry

ITEMS = {
    "fg_counter_table_2": lambda: item_table(2),
    "fg_counter_table_4": lambda: item_table(4),
    "fg_counter_table_6": lambda: item_table(6),
    "fg_counter_chair": item_chair,
    "fg_counter_chair_folded": item_chair_folded,
    "fg_counter_counter": item_counter,
    "fg_counter_bag": item_bag,
    "fg_counter_bag_flat": item_bag_flat,
}
