"""Family h_backroom: warehouse rack, workbench, bubble mailers, tape gun, swing-lid bin, full trash bag and hand truck
(CARDSHOP_KIT_SPEC.md 3.H H1-H7; reference sheets 27, 28, 29: References/CardShop/csk_bag_mailers.png,
csk_backroom.png, csk_bins.png, notes in REFERENCE_LOG.md "Sheet 27/28/29 notes").

Flags as in spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = estimate with a
measured range. "sheet N" = the value or the form was measured off that reference sheet (the picture wins over E).

Frames: millimetres, +X to the viewer's right, +Y away from the customer (the back), +Z up. Pivots: the bottom centre
(the Seat) for everything that stands; the mailers lie on their back; the bin's swing flap (``_Lid``) has its origin on
its swing axis. No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import Item, Lod, Socket, _face_out, _planar, solve_grid
from .shapes import Builder

Vec3 = Tuple[float, float, float]

# =========================================================================== numbers

# LOD0 budgets (the spec's Tris column, E). Raised, with the reason logged in the report and the item notes:
#   Rack_Warehouse_1829 1500 -> 20000: sheet 28 draws keyhole slots on every upright face (2 columns on the front face,
#     1 on the side), about 400 of them, and they are the rack's defining detail; each is a real 8-sided pocket. The
#     fifth level (sheet 28) adds a deck and 4 beams.
#   Workbench_1524 1500 -> 5000: sheet 28 draws a slot column on each leg's front face and a hole column on its side.
#   TrashCan 800 -> 1200: the hollow inside (seen through the swinging flap, sheet 29) and the raised band's rounds.
#   TapeGun 800 -> 1200: sheet 27's three-spoke hub, the two side plates, the serrated blade and the clear guard.
BUDGETS = {
    "SM_CSK_Rack_Warehouse_1829": 20000,
    "SM_CSK_Workbench_1524": 5000,
    "SM_CSK_Mailer_S": 150, "SM_CSK_Mailer_L": 150,
    "SM_CSK_Mailer_S_Open": 150, "SM_CSK_Mailer_L_Open": 150,
    "SM_CSK_TapeGun": 1400,
    "SM_CSK_TrashCan": 1200, "SM_CSK_TrashCan_Lid": 200,
    "SM_CSK_TrashBag_Full": 600,
    "SM_CSK_HandTruck": 2500,
}

MAILER = dict(                    # H3, sheet 27 (2)
    sizes={"S": (100.0, 200.0, 5.0), "L": (150.0, 250.0, 6.0)},   # W x L x T, E (spec) = sheet 27 call-outs
    seal=4.5,                     # sheet 27: the crimped side seams (4.5 of 100 at the S)
    band=10.0,                    # sheet 27: the sealed flap band at the top end
    edge_t=1.0,                   # E: two plies of kraft + film at the seams
    shoulder=6.0,                 # sheet 27: the padded panel rises over ~6 from the seam (a flat puffy panel)
    flap=40.0,                    # E* (sheet 27 open views: the opened flap, ~35-40 long)
    strip=(16.0, 6.0, 0.3),       # sheet 27 open views: the white peel strip: width, gap from the fold, thickness (E)
    mouth=25.0,                   # E: depth of the open mouth pocket (the bubble lining shows inside)
    lip=10.0,                     # E: the back ply runs 10 past the front ply before the flap fold
)

BIN = dict(                       # H5, sheet 29 (1)
    r_top=200.0, r_bot=187.5,     # E (spec Ø 400) at the top; sheet 29: tapers to ~375 at the base
    h=700.0,                      # E (spec) = sheet 29
    band=(474.0, 522.0, 211.0),   # sheet 29: the raised band where the dome meets the body: z0, z1, outer radius
    foot_r=4.0,                   # E: the rounded bottom edge
    dome_c=178.0,                 # D: the dome rises from the band top (522) to 700; sheet 29: a slightly flat dome
    wall=3.0,                     # E: moulded wall
    floor=4.0,                    # E
    segs=(24, 16, 12),            # per LOD
    # the swing flap, as seen from the front (x, z): a superellipse (sheet 29: a rounded "D", its lower edge just above
    # the band, its top just in front of the apex)
    flap=(136.0, 609.0, 76.0, 2.2, 3.6),   # half width, centre z, half height, exponent above / below the centre
                                  # (sheet 29: a round top and a flatter lower edge along the band)
    gap=1.5,                      # E: the clearance round the flap (sheet 29: a dark outline groove)
    swing=(-45.0, 45.0),          # E: the flap rocks both ways on its pins (sheet 29 "Lid swinging")
)

TAPEGUN = dict(                   # H4, sheet 27 (3): 250 long (X, the blade at -X) x 75 wide (Y) x 180 tall (E = sheet)
    roll=(30.0, 125.0, 55.0, 38.0, 34.0, 48.0),   # sheet 27: roll centre x, z; tape OD/2, core OD/2, core ID/2, width
    hub=(33.5, 23.0, 6.0),        # grey hub: radius, half width, window pocket depth (sheet 27: three dark windows)
    windows=(14.0, 28.0, 64.0),   # window inner / outer radius, angular width (deg)
    plate=((-30.0, 60.0), (-2.0, 50.0), (38.0, 58.0), (56.0, 84.0), (48.0, 104.0), (20.0, 112.0), (-12.0, 108.0),
           (-30.0, 94.0)),        # sheet 27: the light grey side plate under the roll (x, z)
    plate_y=(25.5, 28.0),         # E: the plates' inner / outer faces (|y|)
    arm=((12.0, 110.0), (40.0, 100.0), (48.0, 126.0), (30.0, 143.0), (14.0, 134.0)),   # E: the far arm to the axle
    housing=(-104.0, -26.0, 22.0, 92.0, 31.0),   # sheet 27: the black front housing x0, x1, z0, z1, |y|
    cheek=(-98.0, -40.0, 28.0, 90.0, 8.0, 30.5, 35.5),   # the black cheek plates: x0, x1, z0, z1, corner R, |y| in/out
    screws=((-44.0, 79.0), (-37.0, 45.0)),       # sheet 27: two screws on each cheek (x, z); one on each grey plate
    plate_screw=(19.0, 57.0),
    blade=(-100.5, 1.0, 78.0, 92.0, 3.0, 27.0, 9),  # serrated blade: x, thickness, z0, z1, tooth height, |y|, teeth
    guard=((-97.0, 92.0), (-89.0, 140.0), 1.5, 25.0),  # clear guard: bottom (x, z), top (x, z), thickness, |y|
    roller=(-78.0, 24.0, 14.0, 28.0),            # the black pressure roller: x, z, r, |y|
    grip=((44.0, 0.0, 80.0), (114.0, 0.0, 12.0)),  # sheet 27: the raked pistol grip's axis, top to end
    tongue=(-103.0, 92.0, -110.0, 24.0),        # the tape's end hanging from the blade to the floor: x, z top, x bottom
)

TBAG = dict(                      # H6, sheet 29 (2)
    d=450.0,                      # E (spec) = sheet 29 call-out (the 450 line spans the bag's base exactly)
    h=610.0,                      # sheet 29: 610 to the tuft's top at the 450 line's scale (spec 600 E; the sheet's
                                  # 600 arrow is drawn from the knot to the floor, which the drawing's scale contradicts)
    # the radius profile (z, r), measured row by row off sheet 29 at 1 px = 1 mm: the base spreads to 464 at 45 up,
    # near-straight sides, round shoulders from ~390, the twisted neck tied at ~510, a ruffled tuft to 610
    prof=((0.0, 170.0), (14.0, 218.0), (50.0, 232.0), (130.0, 221.0), (230.0, 210.0), (330.0, 205.0),
          (390.0, 194.0), (430.0, 166.0), (460.0, 125.0), (482.0, 90.0), (497.0, 52.0), (506.0, 24.0),
          (515.0, 26.0), (532.0, 46.0), (560.0, 66.0), (586.0, 80.0), (600.0, 86.0), (610.0, 70.0)),
    knot=510.0,
    segs=(16, 10, 8),
    crumple=0.11,                 # E: +- radial crumple (fraction of r), deterministic hash (sheet 29: sharp creases)
    pleat=0.35,                   # E: pleat depth toward the neck (fraction of r)
)

# =========================================================================== small vector maths (as fam_a_shelving)


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


def _hash(*a: int) -> float:
    """A deterministic hash of integers to [0, 1) (as fam_b_pack)."""
    h = 0x811C9DC5
    for v in a:
        h ^= (int(v) * 0x9E3779B1) & 0xFFFFFFFF
        h = (h * 0x01000193) & 0xFFFFFFFF
        h ^= h >> 15
    h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
    h ^= h >> 12
    return h / 4294967296.0


# =========================================================================== shape helpers

def _box(b: Builder, mn, mx, mat: int, **kw) -> None:
    lo = tuple(min(mn[i], mx[i]) for i in range(3))
    hi = tuple(max(mn[i], mx[i]) for i in range(3))
    b.box(lo, hi, mat=mat, **kw)


def _obox(b: Builder, c: Vec3, ax: Vec3, ay: Vec3, az: Vec3, hx: float, hy: float, hz: float, mat: int) -> None:
    """An oriented box: centre ``c``, unit axes, half sizes."""
    v = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                v[i, j, k] = b.v(*_add(c, _add(_add(_mul(ax, i * hx), _mul(ay, j * hy)), _mul(az, k * hz))))
    for axis, vec in ((0, ax), (1, ay), (2, az)):
        for s in (-1, 1):
            ids = []
            for p, q in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [p, q]
                key.insert(axis, s)
                ids.append(v[tuple(key)])
            _face_out(b, ids, _mul(vec, s), mat)


def _earclip(P: Sequence[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """Ear-clipping triangulation of a simple polygon (either winding), as fam_a_shelving."""
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
            if any(inside(P[j], P[a], P[b_], P[c]) for j in reflex if j not in (a, b_, c)
                   and P[j] not in (P[a], P[b_], P[c])):
                continue
            tris.append((a, b_, c))
            idx.pop(k)
            break
        else:
            raise ValueError("ear clipping found no ear (the profile is not a simple polygon)")
    tris.append(tuple(idx))
    return tris


def _lathe(b: Builder, prof: Sequence[Tuple[float, float]], sides: int, mat: int, caps=(True, True),
           phase: float = 0.5, cx: float = 0.0, cy: float = 0.0, inward: bool = False) -> List[List[int]]:
    """A solid of revolution about the vertical axis through (cx, cy); ``prof`` [(r, z)] from the bottom up. A radius
    of 0 closes the end to a point (a fan). ``inward`` flips every face (a cavity). Returns the rings."""
    angs = [2 * math.pi * (k + phase) / sides for k in range(sides)]
    rings = []
    for r, z in prof:
        if r <= 1e-9:
            rings.append([b.v(cx, cy, z)])
        else:
            rings.append([b.v(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in angs])
    sg = -1.0 if inward else 1.0
    for i in range(len(prof) - 1):
        (r0, z0), (r1, z1) = prof[i], prof[i + 1]
        A, B = rings[i], rings[i + 1]
        for k in range(sides):
            k1 = (k + 1) % sides
            tm = angs[k] + math.pi / sides
            out = (sg * math.cos(tm) * (z1 - z0), sg * math.sin(tm) * (z1 - z0), sg * (r0 - r1))
            ids = ([A[k], A[k1]] if len(A) > 1 else [A[0]]) + ([B[k1], B[k]] if len(B) > 1 else [B[0]])
            _face_out(b, ids, out, mat)
    if caps[0] and len(rings[0]) > 1:
        b.fill([rings[0]], mat, 0, (0.0, 0.0, 1.0 if inward else -1.0))
    if caps[1] and len(rings[-1]) > 1:
        b.fill([rings[-1]], mat, 0, (0.0, 0.0, -1.0 if inward else 1.0))
    return rings


def _tube(b: Builder, pts: Sequence[Vec3], r: float, sides: int, mat: int, closed: bool = False,
          up: Vec3 = (0.0, 0.0, 1.0), caps: Tuple[bool, bool] = (False, False), phase: float = 0.5) -> None:
    """A round tube along a polyline, mitred at the joints (parallel-transported frame), as fam_a_shelving."""
    n = len(pts)
    segs = n if closed else n - 1
    d = [_unit(_sub(pts[(i + 1) % n], pts[i])) for i in range(segs)]
    nv = _sub(up, _mul(d[0], _dot(up, d[0])))
    if _dot(nv, nv) < 1e-9:
        nv = _sub((1.0, 0.0, 0.0), _mul(d[0], d[0][0]))
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
    angs = [2 * math.pi * (k + phase) / sides for k in range(sides)]
    rings = []
    for i in range(n):
        joint = closed or 0 < i < n - 1
        if joint:
            a = d[i - 1] if i > 0 else d[-1]
            c = d[i] if i < segs else d[-1]
            fn, fb = frames[i - 1] if i > 0 else frames[-1]
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
        j1 = (j + 1) % n
        axis_mid = _mul(_add(pts[j], pts[j1]), 0.5)
        for k in range(sides):
            k1 = (k + 1) % sides
            q = [rings[j][k], rings[j][k1], rings[j1][k1], rings[j1][k]]
            cen = _mul(_add(_add(b.verts[q[0]], b.verts[q[1]]), _add(b.verts[q[2]], b.verts[q[3]])), 0.25)
            _face_out(b, q, _sub(cen, axis_mid), mat)
    if not closed:
        if caps[0]:
            b.fill([rings[0]], mat, 0, _mul(d[0], -1.0))
        if caps[1]:
            b.fill([rings[-1]], mat, 0, d[-1])


def _area2(P) -> float:
    return sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))


def _frame(u: Vec3, v: Vec3):
    u = _unit(u)
    w = _unit(_cross(u, v))
    return u, _cross(w, u), w


def _to3(o: Vec3, u: Vec3, v: Vec3, w: Vec3, a: float, c: float, d: float = 0.0) -> Vec3:
    return _add(o, _add(_add(_mul(u, a), _mul(v, c)), _mul(w, d)))


def _plate(b: Builder, outline, o: Vec3, u: Vec3, v: Vec3, t0: float, t1: float, mat: int,
           pockets: Sequence[Tuple[Sequence[Tuple[float, float]], float, int]] = (), cap_mats=(None, None)) -> None:
    """A prism of the planar outline [(a, c)] (either winding) in the plane (o, u, v), from t0 to t1 along w = u x v.
    ``pockets`` [(outline, depth, floor_mat)] are sunk into the t1 face (depth < t1 - t0) or through when depth is
    None."""
    u, v, w = _frame(u, v)
    lo = [b.v(*_to3(o, u, v, w, a, c, t0)) for a, c in outline]
    hi = [b.v(*_to3(o, u, v, w, a, c, t1)) for a, c in outline]
    n = len(outline)
    sg = 1.0 if _area2(outline) > 0 else -1.0
    for i in range(n):
        j = (i + 1) % n
        (a0, c0), (a1, c1) = outline[i], outline[j]
        nx, ny = sg * (c1 - c0), -sg * (a1 - a0)          # the edge's outward normal in the plane
        _face_out(b, [lo[i], lo[j], hi[j], hi[i]], _add(_mul(u, nx), _mul(v, ny)), mat)
    holes_hi, holes_lo = [], []
    for pol, depth, fmat in pockets:
        top = [b.v(*_to3(o, u, v, w, a, c, t1)) for a, c in pol]
        bot_t = t0 if depth is None else t1 - depth
        bot = [b.v(*_to3(o, u, v, w, a, c, bot_t)) for a, c in pol]
        m = len(pol)
        sp = 1.0 if _area2(pol) > 0 else -1.0
        for i in range(m):
            j = (i + 1) % m
            nx, ny = -sp * (pol[j][1] - pol[i][1]), sp * (pol[j][0] - pol[i][0])   # into the pocket
            _face_out(b, [top[i], top[j], bot[j], bot[i]], _add(_mul(u, nx), _mul(v, ny)), fmat)
        holes_hi.append(top)
        if depth is None:
            holes_lo.append(bot)
        else:
            b.fill([bot], fmat, 0, w)
    b.fill([hi] + holes_hi, mat if cap_mats[1] is None else cap_mats[1], 0, w)
    b.fill([lo] + holes_lo, mat if cap_mats[0] is None else cap_mats[0], 0, _mul(w, -1.0))


def _lathe_ax(b: Builder, o: Vec3, axis: Vec3, prof: Sequence[Tuple[float, float]], sides: int, mat,
              caps=(True, True), phase: float = 0.5, ref: Vec3 = (0.0, 0.0, 1.0)) -> List[List[int]]:
    """A solid of revolution about ``axis`` through ``o``; ``prof`` [(r, t)] along the axis. ``mat`` may be a list
    (one material per profile band). r = 0 closes to a point."""
    a = _unit(axis)
    e1 = _sub(ref, _mul(a, _dot(ref, a)))
    if _dot(e1, e1) < 1e-9:
        e1 = _sub((1.0, 0.0, 0.0), _mul(a, a[0]))
    e1 = _unit(e1)
    e2 = _cross(a, e1)
    angs = [2 * math.pi * (k + phase) / sides for k in range(sides)]
    rings = []
    for r, t in prof:
        c = _add(o, _mul(a, t))
        if r <= 1e-9:
            rings.append([b.v(*c)])
        else:
            rings.append([b.v(*_add(c, _add(_mul(e1, r * math.cos(q)), _mul(e2, r * math.sin(q))))) for q in angs])
    for i in range(len(prof) - 1):
        A, B = rings[i], rings[i + 1]
        mt = mat[i] if isinstance(mat, (list, tuple)) else mat
        (r0, t0), (r1, t1) = prof[i], prof[i + 1]
        for k in range(sides):
            k1 = (k + 1) % sides
            q = angs[k] + math.pi / sides
            radial = _add(_mul(e1, math.cos(q)), _mul(e2, math.sin(q)))
            out = _add(_mul(radial, t1 - t0), _mul(a, r0 - r1))
            ids = ([A[k], A[k1]] if len(A) > 1 else [A[0]]) + ([B[k1], B[k]] if len(B) > 1 else [B[0]])
            _face_out(b, ids, out, mt)
    m0 = mat[0] if isinstance(mat, (list, tuple)) else mat
    m1 = mat[-1] if isinstance(mat, (list, tuple)) else mat
    if caps[0] and len(rings[0]) > 1:
        b.fill([rings[0]], m0, 0, _mul(a, -1.0))
    if caps[1] and len(rings[-1]) > 1:
        b.fill([rings[-1]], m1, 0, a)
    return rings


def _circle_pts(r: float, n: int, cx: float = 0.0, cy: float = 0.0, a0: float = 0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / n), cy + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def _grid_faces(b: Builder, G: List[List[int]], outward, mat: int, mats=None) -> None:
    """Quads over a vertex grid G[row][col]; ``outward`` is a vector or a function (row, col) -> vector."""
    for i in range(len(G) - 1):
        for j in range(len(G[0]) - 1):
            q = [G[i][j], G[i][j + 1], G[i + 1][j + 1], G[i + 1][j]]
            o = outward(i, j) if callable(outward) else outward
            _face_out(b, q, o, mats(i, j) if mats else mat)


def _aabb(b: Builder):
    xs = [v[0] for v in b.verts]
    ys = [v[1] for v in b.verts]
    zs = [v[2] for v in b.verts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _outward_check(b: Builder) -> int:
    """The build's `_Lid` winding test (mesh.check_outward) run on the builder: faces pointing at the centroid of
    their own loose part. Pure Python, for asserting while authoring."""
    parent = list(range(len(b.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for f in b.faces:
        for i in range(len(f.verts)):
            ra, rb = find(f.verts[i]), find(f.verts[(i + 1) % len(f.verts)])
            if ra != rb:
                parent[ra] = rb
    acc = {}
    for i, p in enumerate(b.verts):
        s = acc.setdefault(find(i), [0.0, 0.0, 0.0, 0])
        s[0] += p[0]
        s[1] += p[1]
        s[2] += p[2]
        s[3] += 1
    bad = 0
    for f in b.faces:
        P = [b.verts[i] for i in f.verts]
        n = (0.0, 0.0, 0.0)
        for a, c in zip(P, P[1:] + P[:1]):
            n = _add(n, _cross(a, c))
        cen = _mul(tuple(sum(p[k] for p in P) for k in range(3)), 1.0 / len(P))
        s = acc[find(f.verts[0])]
        cc = (s[0] / s[3], s[1] / s[3], s[2] / s[3])
        if _dot(_sub(cen, cc), n) < -1e-9:
            bad += 1
    return bad


# =========================================================================== H3 bubble mailers (sheet 27)

def _mailer_top(W: float, T: float, ys: Sequence[Tuple[float, float]]) -> Tuple[List[float], List[Tuple[float, float]]]:
    """The padded panel's columns (x, z-scale) across the width: flat crimp seams, a 6 mm puffy shoulder, a flat top."""
    m = MAILER
    xs = [-W / 2, -W / 2 + m["seal"], -W / 2 + m["seal"] + m["shoulder"]]
    xs = xs + [-x for x in reversed(xs)]
    return xs, list(ys)


def _mailer_sealed(size: str) -> Builder:
    """Sheet 27 sealed: a flat puffy padded panel inside 4.5 crimped side seams, the sealed flap band at the top end
    (+Y) and a rounded fold at the bottom end (-Y). Lying on its back: the back is flat on z = 0."""
    m = MAILER
    W, L, T = m["sizes"][size]
    et = m["edge_t"]
    band, sh = m["band"], m["shoulder"]
    b = Builder()
    xs = [-W / 2, -W / 2 + m["seal"], -W / 2 + m["seal"] + sh, W / 2 - m["seal"] - sh, W / 2 - m["seal"], W / 2]
    # rows (y, z at the padded columns); the seam columns stay at the edge thickness
    rows = [(-L / 2, T * 0.5), (-L / 2 + 1.5, T * 0.85), (-L / 2 + 5.0, T), (L / 2 - band - sh, T),
            (L / 2 - band, et), (L / 2, et)]
    G = []
    for y, zp in rows:
        row = []
        for j, x in enumerate(xs):
            z = zp if 1 < j < 4 else (et if zp >= et else zp)
            if j in (1, 4) and y < L / 2 - band - 1e-6:
                z = max(et, min(zp, et + 0.35 * (zp - et)))      # the shoulder's foot: the pad starts at the seam
            row.append(b.v(x, y, z))
        G.append(row)
    _grid_faces(b, G, (0.0, 0.0, 1.0), 0)
    # the perimeter: walls down to z = 0 and the flat back
    loop = [G[0][j] for j in range(len(xs))] + [G[i][-1] for i in range(1, len(rows))] + \
           [G[-1][j] for j in range(len(xs) - 2, -1, -1)] + [G[i][0] for i in range(len(rows) - 2, 0, -1)]
    bot = [b.v(b.verts[i][0], b.verts[i][1], 0.0) for i in loop]
    n = len(loop)
    for k in range(n):
        k1 = (k + 1) % n
        p, q = b.verts[loop[k]], b.verts[loop[k1]]
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        out = (mid[0] * (1.0 if abs(abs(mid[0]) - W / 2) < 1e-6 else 0.0),
               mid[1] * (1.0 if abs(abs(mid[1]) - L / 2) < 1e-6 else 0.0), 0.0)
        _face_out(b, [loop[k], loop[k1], bot[k1], bot[k]], out, 0)
    b.fill([bot], 0, 0, (0.0, 0.0, -1.0))
    return b


def _mailer_open(size: str) -> Builder:
    """Sheet 27 open: the front ply ends at the mouth; the back ply runs on past it into the opened flap, which lies
    flat with the white peel strip across it; the mouth pocket shows the bubble lining (M_CSK_Bubble)."""
    m = MAILER
    W, L, T = m["sizes"][size]
    et = m["edge_t"]
    sh = m["shoulder"]
    KRAFT, BUBBLE, STRIP = 0, 1, 2
    ym = L / 2 - m["lip"]                       # the mouth: the front ply's edge
    b = Builder()
    xs = [-W / 2, -W / 2 + m["seal"], -W / 2 + m["seal"] + sh, W / 2 - m["seal"] - sh, W / 2 - m["seal"], W / 2]
    rows = [(-L / 2, T * 0.5), (-L / 2 + 1.5, T * 0.85), (-L / 2 + 5.0, T), (ym - 4.0, T), (ym, T * 0.9)]
    G = []
    for y, zp in rows:
        row = []
        for j, x in enumerate(xs):
            if 1 < j < 4:
                z = zp
            elif j in (1, 4):
                z = max(et, min(zp, et + 0.35 * (zp - et)))
            else:
                z = et if zp >= et else zp
            row.append(b.v(x, y, z))
        G.append(row)
    _grid_faces(b, G, (0.0, 0.0, 1.0), KRAFT)
    nx = len(xs)
    # walls: -x side, fold end, +x side (the mouth end is the ring face below)
    side_l = [G[i][0] for i in range(len(rows) - 1, -1, -1)]
    fold = [G[0][j] for j in range(nx)]
    side_r = [G[i][-1] for i in range(len(rows))]
    path = side_l + fold[1:] + side_r[1:]
    bot = [b.v(b.verts[i][0], b.verts[i][1], 0.0) for i in path]
    for k in range(len(path) - 1):
        p, q = b.verts[path[k]], b.verts[path[k + 1]]
        mx_, my_ = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        out = (1.0 if mx_ > W / 2 - 1e-6 else (-1.0 if mx_ < -W / 2 + 1e-6 else 0.0),
               -1.0 if abs(my_ + L / 2) < 1e-6 else 0.0, 0.0)
        _face_out(b, [path[k], path[k + 1], bot[k + 1], bot[k]], out, KRAFT)
    # the mouth face at y = ym: the ply section round the opening (a trapezoid gape between the plies)
    top_row = G[-1]
    xo = W / 2 - m["seal"] - 1.0
    xt = W / 2 - m["seal"] - sh
    zb, zt = 1.2, T * 0.9 - 1.2
    hole = [b.v(-xo, ym, zb), b.v(xo, ym, zb), b.v(xt, ym, zt), b.v(-xt, ym, zt)]
    outer = [bot[0], bot[-1]] + list(reversed(top_row))       # (-x, 0) (+x, 0) then the top row from +x to -x
    b.fill([outer, hole], KRAFT, 0, (0.0, 1.0, 0.0))
    back = [b.v(-xo, ym - m["mouth"], zb), b.v(xo, ym - m["mouth"], zb), b.v(xt, ym - m["mouth"], zt),
            b.v(-xt, ym - m["mouth"], zt)]
    for k in range(4):
        k1 = (k + 1) % 4
        pa, pb = b.verts[hole[k]], b.verts[hole[k1]]
        cen = ((pa[0] + pb[0]) / 2, (pa[2] + pb[2]) / 2)
        _face_out(b, [hole[k], hole[k1], back[k1], back[k]], (-cen[0], 0.0, (zb + zt) / 2 - cen[1]), BUBBLE)
    _face_out(b, back, (0.0, 1.0, 0.0), BUBBLE)
    b.fill([bot], KRAFT, 0, (0.0, 0.0, -1.0))
    # the back ply's lip and the opened flap: one thin plate, 0.5 into the body; the peel strip on it
    y0, y1 = ym - 0.5, L / 2 + m["flap"]
    _box(b, (-W / 2 + 0.3, y0, 0.0), (W / 2 - 0.3, y1, et), KRAFT)
    sw, sg, st = m["strip"]
    ys0 = L / 2 + sg
    _box(b, (-W / 2 + m["seal"], ys0, et - 0.1), (W / 2 - m["seal"], ys0 + sw, et + st), STRIP)
    return b


def _mailer_contain(W: float, L: float, T: float) -> Tuple[Dict, Vec3]:
    m = MAILER
    et = m["edge_t"]
    x = W / 2 - m["seal"] - 0.5
    y0, y1 = -L / 2 + 1.5, L / 2 - m["band"]
    cav = [[-x, y0, et], [x, y1, T - et]]
    return {"Contents": {"socket": "Contents", "cavity_mm": cav, "accepts": ["Card", "CardProt"]}}, \
        (0.0, (y0 + y1) / 2, et)


def item_mailer(size: str, opened: bool = False) -> Item:
    m = MAILER
    W, L, T = m["sizes"][size]
    name = f"SM_CSK_Mailer_{size}" + ("_Open" if opened else "")
    b = _mailer_open(size) if opened else _mailer_sealed(size)
    contain, seat = _mailer_contain(W, L, T)
    ymax = L / 2 + (m["flap"] if opened else 0.0)
    zmax = T + (m["strip"][2] if opened else 0.0)
    mats = ["M_CSK_Kraft", "M_CSK_Bubble", "M_CSK_Paper"] if opened else ["M_CSK_Kraft"]
    pad = S.HANDHELD_HULL_MIN_T
    return Item(
        name=name, lods=[Lod(b)], materials=mats, projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Contents", seat, kind="CONTAIN"), Socket("Label", (0, 0, T)),
                 Socket("Grip", (0, -L / 2, T / 2))],
        hulls=[((-W / 2, -L / 2, 0.0), (W / 2, ymax, max(zmax, pad)))], cls=None, budget=BUDGETS[name],
        data={"footprint_mm": [W, ymax + L / 2, zmax], "pose": "lying on its back", "pivot": "bottom-centre",
              "states": ["Sealed", "Open"], "state": "Open" if opened else "Sealed",
              "other_state": name[:-5] if opened else name + "_Open", "contain": contain,
              "reference": "References/CardShop/csk_bag_mailers.png (sheet 27 (2))",
              "notes": ["Sheet 27: a flat puffy padded panel inside crimped side seams, the flap band at the top end, a "
                        "rounded fold at the bottom end. The seams' fine crimp ribs are surface detail (not modelled).",
                        "Open (sheet 27 notes add the state): the flap lies opened flat past the mouth with the white "
                        "peel strip on it; the mouth pocket shows the bubble lining (M_CSK_Bubble).",
                        "No label: sheet 27 shows plain kraft. The Label socket marks the face centre for one."]},
    )


# =========================================================================== H5 swing-lid bin (sheet 29)

def _dome_y(x: float, z: float, a: float, c: float, z0: float) -> float:
    """The front (-Y) surface of the dome ellipsoid x^2/a^2 + y^2/a^2 + (z - z0)^2/c^2 = 1 at (x, z)."""
    q = a * a * max(0.0, 1.0 - ((z - z0) / c) ** 2) - x * x
    return -math.sqrt(max(0.0, q))


def _flap_outline(n_pts: int, grow: float = 0.0) -> List[Tuple[float, float]]:
    """The flap as seen from the front (x, z), counter-clockwise seen from -Y; ``grow`` offsets it outward (mm)."""
    hw, zc, hh, e_top, e_bot = BIN["flap"]
    pts = []
    for i in range(n_pts):
        t = 2 * math.pi * i / n_pts - math.pi / 2
        c, s = math.cos(t), math.sin(t)
        e = e_top if s > 0 else e_bot
        x = (hw + grow) * math.copysign(abs(c) ** (2 / e), c)
        z = zc + (hh + grow) * math.copysign(abs(s) ** (2 / e), s)
        pts.append((-x, z))                         # (-x): counter-clockwise seen from the front (-Y)
    return pts


def _bin_profile(level: int, inner: bool):
    s = BIN
    rt, rb, H = s["r_top"], s["r_bot"], s["h"]
    z0b, z1b, rband = s["band"]
    c = s["dome_c"]
    w = s["wall"] if inner else 0.0
    rings = ((5, 4, 3) if not inner else (3, 2, 2))[level]
    body = lambda z: rb + (rt - rb) * z / z0b              # noqa: E731  the tapered wall's radius at z
    if inner:
        zf = s["floor"]
        prof = [(0.0, zf), (body(zf) - w - 6.0, zf), (body(zf + 6.0) - w, zf + 6.0), (rt - w, z1b)]
    else:
        fr = s["foot_r"]
        prof = [(0.0, 0.0), (rb - fr, 0.0), (body(fr), fr), (body(z0b), z0b)]
        if level < 2:
            prof += [(rband - 3.0, z0b), (rband, z0b + 3.0), (rband, z1b - 3.0), (rband - 3.0, z1b)]
        else:
            prof += [(rband, z0b), (rband, z1b)]
    a, cc = rt - w, c - w
    for k in range(rings + 1):
        phi = (math.pi / 2) * k / (rings + 1) if k else 0.0
        if k == 0:
            if not inner:
                prof.append((a, z1b))
            continue
        prof.append((a * math.cos(phi), z1b + cc * math.sin(phi)))
    prof.append((0.0, z1b + cc))
    return prof


def _bin_body(level: int) -> Lod:
    """Sheet 29: a matte grey round bin tapering slightly toward the base, a raised band where the dome lid meets the
    body, a dome top with an oval swing flap on its front. Hollow (3 wall, 4 floor): the flap's opening shows the
    inside. One closed shell (a lathe) with the cavity and the flap opening as exact cuts."""
    s = BIN
    segs = s["segs"][level]
    b = Builder()
    _lathe(b, _bin_profile(level, False), segs, 0)
    ops = []
    if level < 2:
        cav = Builder()
        _lathe(cav, _bin_profile(level, True), segs, 0)
        ops.append(("DIFFERENCE", cav))
        cut = Builder()
        n = (28, 16)[level]
        out = [(x, z) for x, z in _flap_outline(n, s["gap"])]
        f = [cut.v(x, -260.0, z) for x, z in out]
        k = [cut.v(x, 0.0, z) for x, z in out]
        cut.fill([f], 0, 0, (0.0, -1.0, 0.0))
        cut.fill([k], 0, 0, (0.0, 1.0, 0.0))
        for i in range(n):
            j = (i + 1) % n
            (xa, za), (xb, zb) = out[i], out[j]
            _face_out(cut, [f[i], f[j], k[j], k[i]], ((xa + xb) / 2, 0.0, (za + zb) / 2 - s["flap"][1]), 0)
        ops.append(("DIFFERENCE", cut))
    return Lod(b, ops=ops)


def _flap_pivot() -> Vec3:
    s = BIN
    hw, zc, hh = s["flap"][:3]
    z0 = s["band"][1]
    y = _dome_y(hw, zc, s["r_top"] - s["wall"], s["dome_c"] - s["wall"], z0)
    return (0.0, y, zc)


def _flap_builder(level: int) -> Builder:
    """The swing flap (sheet 29): the dome's surface inside the flap outline, a 3 mm rim, and a faceted back that
    closes it as one convex part (so the `_Lid` winding test holds; the back is inside the bin, unseen when closed
    and dark when it swings). Local frame: origin on the swing axis (X, through the pins at the flap's sides)."""
    s = BIN
    a, c, z0 = s["r_top"], s["dome_c"], s["band"][1]
    n = (20, 14, 8)[level]
    rings = (1.0, 0.72, 0.4)[: (3, 2, 1)[level]]
    px, py, pz = _flap_pivot()
    hw, zc, hh = s["flap"][:3]
    b = Builder()
    ol = _flap_outline(n)

    def on(x, z, inset=0.0):
        y = _dome_y(x, z, a - inset, c - inset, z0)
        return (x - px, y - py, z - pz)

    def nrm(v):                                      # the dome's outward normal at a local point
        x, y, z = v[0] + px, v[1] + py, v[2] + pz
        return (x / (a * a), y / (a * a), (z - z0) / (c * c))

    R = []
    for k in rings:
        R.append([b.v(*on(x * k, zc + (z - zc) * k)) for x, z in ol])
    ctr = b.v(*on(0.0, zc))
    for i in range(len(R) - 1):
        for j in range(n):
            j1 = (j + 1) % n
            q = [R[i][j], R[i][j1], R[i + 1][j1], R[i + 1][j]]
            _face_out(b, q, nrm(_mul(_add(b.verts[q[0]], b.verts[q[2]]), 0.5)), 0)
    for j in range(n):
        j1 = (j + 1) % n
        tri = [R[-1][j], R[-1][j1], ctr]
        _face_out(b, tri, nrm(b.verts[ctr]), 0)
    # the rim: 3 mm in along the dome's normal
    t = s["wall"]
    inner = [b.v(*on(x, z, t)) for x, z in ol]
    for j in range(n):
        j1 = (j + 1) % n
        (xa, za), (xb, zb) = ol[j], ol[j1]
        _face_out(b, [R[0][j], R[0][j1], inner[j1], inner[j]], ((xa + xb) / 2, 0.0, (za + zb) / 2 - zc), 0)
    # the back: a fan from the inner rim's centroid, pushed 5 mm further in
    cx = sum(b.verts[i][0] for i in inner) / n
    cy = sum(b.verts[i][1] for i in inner) / n + 5.0
    cz = sum(b.verts[i][2] for i in inner) / n
    back = b.v(cx, cy, cz)
    for j in range(n):
        j1 = (j + 1) % n
        _face_out(b, [inner[j1], inner[j], back], (0.0, 1.0, 0.0), 0)
    return b


def item_trashcan() -> Item:
    s = BIN
    rt, H = s["r_top"], s["h"]
    z0b, z1b, rband = s["band"]
    lods = [_bin_body(k) for k in range(3)]
    pv = _flap_pivot()
    hw, zc, hh = s["flap"][:3]
    ydrop = _dome_y(0.0, zc, rt, s["dome_c"], z1b)
    name = "SM_CSK_TrashCan"
    return Item(
        name=name, lods=lods, materials=["M_CSK_PlasticGrey"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Lid", pv), Socket("Drop", (0.0, ydrop, zc)),
                 Socket("Bag", (0.0, 0.0, s["floor"]))],
        hulls=[((-rband, -rband, 0.0), (rband, rband, z1b)), ((-rt, -rt, z1b), (rt, rt, H))],
        budget=BUDGETS[name],
        data={"footprint_mm": [2 * rband, 2 * rband, H], "pose": "upright", "pivot": "bottom-centre",
              "parts": {"Lid": {"mesh": "SM_CSK_TrashCan_Lid", "socket": "Lid", "type": "hinge", "axis": "X",
                                "range_deg": list(s["swing"])}},
              "reference": "References/CardShop/csk_bins.png (sheet 29 (1))",
              "notes": ["Sheet 29: Ø 400 at the top tapering to 375 at the base, a raised band (Ø 422, 44 tall) where "
                        "the dome meets the body, a dome with an oval swing flap on its front. Hollow (3 wall, 4 floor).",
                        "The flap (SM_CSK_TrashCan_Lid) rocks on the Lid socket's X axis (the pins at its sides): "
                        "negative angles tip its top in, as sheet 29's 'Lid swinging' frame.",
                        "Budget 800 -> 1200: the hollow inside, seen through the swinging flap, and the band's rounds."]},
    )


def item_trashcan_lid() -> Item:
    lods = [Lod(_flap_builder(k)) for k in range(3)]
    for L in lods:
        bad = _outward_check(L.builder)
        if bad:
            raise ValueError(f"TrashCan_Lid: {bad} faces fail the outward test")
    mn, mx = _aabb(lods[0].builder)
    name = "SM_CSK_TrashCan_Lid"
    return Item(
        name=name, lods=lods, materials=["M_CSK_PlasticGrey"], projections={},
        sockets=[Socket("Seat", (0, 0, 0))], hulls=[(mn, mx)], budget=BUDGETS[name],
        data={"part_of": "SM_CSK_TrashCan", "pivot": "the swing axis (X) through the flap's side pins",
              "notes": ["The flap is one convex part: the dome's surface inside the outline, a 3 mm rim, and a "
                        "faceted back inside the bin (the `_Lid` winding test needs convex parts)."]},
    )

# =========================================================================== H4 tape gun (sheet 27)

def _tapegun_lod(level: int) -> Lod:
    """Sheet 27: a black pistol-grip frame, a light grey side plate each side under the roll, a brown tape roll on a
    cardboard core, a grey hub with three dark windows and a centre bolt, the black front housing with a black cheek
    plate each side (two screws), a serrated steel blade under a clear guard, a black pressure roller under the front,
    a ribbed black rubber grip with a grey end cap, and the tape's end hanging from the blade to the floor."""
    t = TAPEGUN
    PL, GREY, HUB, TAPE, CORE, STEEL, CLEAR, RUB = range(8)
    far = level < 2
    segs = (16, 12, 8)[level]
    b = Builder()        # bevelled parts
    e = Builder()        # crisp small parts
    X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
    rx, rz, ro, rc, ri, rw = t["roll"]
    # the roll: tape + core in one annulus prism (the core's faces are cardboard)
    _lathe_ax(e, (rx, -rw / 2, rz), Y, [(ri, 0.0), (ro, 0.0), (ro, rw), (ri, rw)], segs, [TAPE, TAPE, TAPE],
              caps=(False, False))
    if level < 2:                                       # the core ring on the side faces (cardboard)
        for yy, sg in ((-rw / 2 - 0.3, -1.0), (rw / 2 + 0.3, 1.0)):
            ring_o = [e.v(rx + rc * math.cos(q), yy, rz + rc * math.sin(q)) for q in
                      (2 * math.pi * (k + 0.5) / segs for k in range(segs))]
            ring_i = [e.v(rx + (ri + 0.2) * math.cos(q), yy, rz + (ri + 0.2) * math.sin(q)) for q in
                      (2 * math.pi * (k + 0.5) / segs for k in range(segs))]
            e.fill([ring_o, ring_i], CORE, 0, (0.0, sg, 0.0))
    # the hub (a wheel inside the core): three window pockets on each face, a centre bolt on the near side
    hr, hw, wd = t["hub"]
    w0, w1, wa = t["windows"]
    hub_o = _circle_pts(hr, segs)
    pockets = []
    if level < 2:
        for k in range(3):
            a0 = math.radians(90.0 + 120.0 * k - wa / 2)
            a1 = math.radians(90.0 + 120.0 * k + wa / 2)
            n = 2
            win = [(w1 * math.cos(a0 + (a1 - a0) * i / n), w1 * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
            win += [(w0 * math.cos(a1 - (a1 - a0) * i / (n - 1)), w0 * math.sin(a1 - (a1 - a0) * i / (n - 1)))
                    for i in range(n)]
            pockets.append((win, wd, PL))
    # plane (x, z) seen from -Y: u = +X, v = +Z -> w = X x Z = -Y
    _plate(e, hub_o, (rx, 0.0, rz), X, Z, -hw, hw, HUB, pockets=pockets)          # the -Y face (w = -Y) pocketed
    _lathe_ax(e, (rx, -hw + 0.5, rz), (0.0, -1.0, 0.0), [(8.0, 0.0), (8.0, 3.0), (6.0, 5.0), (0.0, 5.0)] if level < 2
              else [(7.0, 0.0), (7.0, 4.0), (0.0, 4.0)], 6, HUB, caps=(False, False))
    # grey side plates, the far arm, the housing, the cheeks
    y0, y1 = t["plate_y"]
    for sg in ((-1.0, 1.0) if far else (-1.0,)):
        _plate(b, t["plate"], (0.0, sg * y0, 0.0), X, Z, 0.0, (y1 - y0), GREY) if sg < 0 else \
            _plate(b, t["plate"], (0.0, sg * y1, 0.0), X, Z, 0.0, (y1 - y0), GREY)
    if far:
        _plate(b, t["arm"], (0.0, y1 - 0.5, 0.0), X, Z, 0.0, (y1 - y0) - 0.5, GREY)
        _lathe_ax(e, (rx, hw - 1.0, rz), Y, [(0.0, 0.0), (9.0, 0.0), (9.0, y0 - hw + 1.5), (0.0, y0 - hw + 1.5)], 8,
                  PL, caps=(False, False))
    hx0, hx1, hz0, hz1, hy = t["housing"]
    _box(b, (hx0, -hy, hz0), (hx1, hy, hz1), PL)
    _box(b, (hx1 - 2.0, -y0 + 1.0, 46.0), (58.0, y0 - 1.0, 70.0), PL)      # the frame bar to the grip, under the roll
    cx0, cx1, cz0, cz1, cr, cyi, cyo = t["cheek"]
    cseg = (2, 1, 1)[level]
    ck = []
    for (qx, qz, a0) in ((cx1 - cr, cz0 + cr, -90.0), (cx1 - cr, cz1 - cr, 0.0), (cx0 + cr, cz1 - cr, 90.0),
                         (cx0 + cr, cz0 + cr, 180.0)):
        for i in range(cseg + 1):
            q = math.radians(a0 + 90.0 * i / cseg)
            ck.append((qx + cr * math.cos(q), qz + cr * math.sin(q)))
    for sg in ((-1.0, 1.0) if far else (-1.0,)):
        _plate(b, ck, (0.0, sg * (cyi if sg < 0 else cyo), 0.0), X, Z, 0.0, cyo - cyi, PL)
    if level < 2:                                       # screws: two on each cheek, one on each grey plate
        for sg in (-1.0,):                              # the near side (sheet 27 shows it)
            for (sx, sz), yb in [(p, cyo) for p in t["screws"]] + [(t["plate_screw"], y1)]:
                _lathe_ax(e, (sx, sg * (yb - 0.5), sz), (0.0, sg, 0.0), [(3.2, 0.0), (3.2, 2.0), (0.0, 2.0)], 6,
                          STEEL, caps=(False, False))
    # the serrated blade (in the YZ plane, teeth up) and the clear guard
    bx, bt, bz0, bz1, th, by, nt = t["blade"]
    if level == 2:
        nt = 1
    outline = [(-by, bz0), (by, bz0)]
    for i in range(nt, 0, -1):
        ya, yb_ = -by + 2 * by * i / nt, -by + 2 * by * (i - 1) / nt
        outline += [(ya, bz1), ((ya + yb_) / 2, bz1 + th)] if level < 2 else []
    outline += [(-by, bz1)] if level < 2 else [(by, bz1), (-by, bz1)]
    _plate(e, outline, (bx, 0.0, 0.0), Y, Z, 0.0, bt, STEEL)      # w = Y x Z = +X
    (gx0, gz0), (gx1, gz1), gt, gy = t["guard"]
    gl = math.hypot(gx1 - gx0, gz1 - gz0)
    ga = _unit((gx1 - gx0, 0.0, gz1 - gz0))
    gn = _cross(ga, Y)
    _obox(e, ((gx0 + gx1) / 2, 0.0, (gz0 + gz1) / 2), gn, Y, ga, gt / 2, gy, gl / 2, CLEAR)
    # the pressure roller
    ox, oz, orr, oy = t["roller"]
    _lathe_ax(e, (ox, -oy, oz), Y, [(0.0, 0.0), (orr, 0.0), (orr, 2 * oy), (0.0, 2 * oy)], (12, 8, 6)[level], RUB,
              caps=(False, False))
    # the ribbed grip and its grey end cap
    p0, p1 = t["grip"]
    ax = _sub(p1, p0)
    L = math.sqrt(_dot(ax, ax))
    prof = [(0.0, -2.0), (15.0, -2.0), (16.5, 5.0)]
    mats = [RUB, RUB]
    tt = 12.0
    k = 0
    while tt < L - 8.0 and level < 2:
        prof.append((17.5 if k % 2 == 0 else 16.0, tt))
        mats.append(RUB)
        tt += 10.0 if level == 0 else 20.0
        k += 1
    prof += [(17.0, L - 2.0), (17.8, L - 2.0), (17.8, L + 6.0), (13.0, L + 10.0), (0.0, L + 10.0)]
    mats += [RUB, RUB, GREY, GREY, GREY]
    _lathe_ax(e, p0, ax, prof, (10, 8, 6)[level], mats, caps=(False, False), ref=Y)
    # the tape's end: from the blade down to the floor
    tx0, tz0, tx1, tz1 = t["tongue"]
    tw = rw / 2
    tv = [e.v(tx0, -tw, tz0), e.v(tx0, tw, tz0), e.v(tx1, tw, tz1), e.v(tx1, -tw, tz1)]
    tn = _unit(_cross(_sub(e.verts[tv[1]], e.verts[tv[0]]), _sub(e.verts[tv[3]], e.verts[tv[0]])))
    tv2 = [e.v(*_add(e.verts[i], _mul(tn, 0.6))) for i in tv]
    for q, o in (([tv[0], tv[1], tv[2], tv[3]], _mul(tn, -1.0)), ([tv2[0], tv2[1], tv2[2], tv2[3]], tn)):
        _face_out(e, q, o, TAPE)
    for i in range(4):
        j = (i + 1) % 4
        mid = _mul(_add(e.verts[tv[i]], e.verts[tv[j]]), 0.5)
        cen = _mul(tuple(sum(e.verts[v][c] for v in tv) for c in range(3)), 0.25)
        _face_out(e, [tv[i], tv[j], tv2[j], tv2[i]], _sub(mid, cen), TAPE)
    return Lod(b, bevel_mm=0.8 if level == 0 else None, extra=e)


def _lod_zmin(lods: Sequence[Lod]) -> float:
    zs = [v[2] for L in lods for bb in (L.builder, L.extra) if bb is not None for v in bb.verts]
    return min(zs)


def _shift_all(lods: Sequence[Lod], dz: float) -> None:
    for L in lods:
        for bb in (L.builder, L.extra):
            if bb is not None:
                bb.verts = [(x, y, z + dz) for x, y, z in bb.verts]


def item_tapegun() -> Item:
    t = TAPEGUN
    lods = [_tapegun_lod(k) for k in range(3)]
    dz = -_lod_zmin(lods)                        # rest on the grip's end cap and the hanging tape end
    _shift_all(lods, dz)
    bbs = [L.builder for L in lods[:1]] + [lods[0].extra]
    xs = [v[0] for bb in bbs for v in bb.verts]
    ys = [v[1] for bb in bbs for v in bb.verts]
    zs = [v[2] for bb in bbs for v in bb.verts]
    mn, mx = (min(xs), min(ys), 0.0), (max(xs), max(ys), max(zs))
    p0, p1 = t["grip"]
    gc = _mul(_add(p0, p1), 0.5)
    name = "SM_CSK_TapeGun"
    return Item(
        name=name, lods=lods,
        materials=["M_CSK_Plastic", "M_CSK_Steel", "M_CSK_PlasticGrey", "M_CSK_Tape", "M_CSK_Board", "M_CSK_Metal",
                   "M_CSK_Acrylic", "M_CSK_Rubber"],
        projections={}, sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (gc[0], gc[1], gc[2] + dz))],
        hulls=[(mn, mx)], budget=BUDGETS[name],
        data={"footprint_mm": [round(mx[0] - mn[0], 1), round(mx[1] - mn[1], 1), round(mx[2], 1)],
              "pose": "resting on its grip end and the hanging tape end", "pivot": "bottom-centre of the frame",
              "reference": "References/CardShop/csk_bag_mailers.png (sheet 27 (3))",
              "notes": ["Sheet 27: pistol grip, grey side plates, a tape roll on a hub with three windows and a "
                        "centre bolt, a serrated blade with a clear guard, black cheek plates with two screws.",
                        "Budget 800 -> 1200: the three-window hub, the two side plates, the serrated blade and the "
                        "clear guard are all visible at arm's length (a handheld item)."]},
    )


# =========================================================================== H6 full trash bag (sheet 29)

def _bag_builder(level: int) -> Builder:
    """Sheet 29: a glossy black full bag, crumpled into sharp facets, round shoulders gathered into a twisted neck,
    a tie at the neck and a flared tuft above it. Deterministic: the crumple is a hash of (ring, segment)."""
    s = TBAG
    segs = s["segs"][level]
    prof = s["prof"] if level == 0 else [p for i, p in enumerate(s["prof"]) if i % 2 == 0 or i == len(s["prof"]) - 1]
    b = Builder()
    rings = []
    zn = s["knot"]
    last = len(prof) - 1
    for i, (z, r) in enumerate(prof):
        ring = []
        tuft = z > zn + 1.0
        for k in range(segs):
            t = 2 * math.pi * (k + 0.5 * (i % 2)) / segs
            near = max(0.0, 1.0 - abs(z - zn) / (130.0 if z > zn else 280.0))   # pleats run down from the neck
            tight = min(1.0, max(0.0, (r - 30.0) / 40.0))     # the tight twisted neck itself is not pleated
            depth = s["pleat"] * (1.3 if tuft else near) * tight
            pleat = (1.0 - depth) if k % 2 else 1.0
            amp = s["crumple"] * (2.5 if tuft else (0.3 if z < 1.0 else 1.0))
            cr = 1.0 + amp * (2 * _hash(i, k, 7) - 1)
            rr = r * pleat * cr
            tw = 0.3 * (2 * math.pi / segs) * near * (2 * _hash(i, k, 3) - 1)   # the twist round the neck
            if i == last:                             # the ruffled rim: petal tips at different heights
                zz = z + 12.0 * _hash(i, k, 11)
            else:
                gap = min(z - prof[i - 1][0], prof[i + 1][0] - z) if 0 < i else 0.0
                zz = z + min(9.0, 0.3 * gap) * (2 * _hash(i, k, 11) - 1)      # ragged rings that never cross
            tw += 0.25 * (2 * math.pi / segs) * (2 * _hash(i, k, 5) - 1) * (0.0 if z < 1.0 else 1.0)
            ring.append(b.v(rr * math.cos(t + tw), rr * math.sin(t + tw), zz))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(segs):
            k1 = (k + 1) % segs
            # a regular triangle lattice: every other ring is turned half a step
            tris = ((A[k], A[k1], B[k]), (A[k1], B[k1], B[k])) if i % 2 == 0 else \
                ((A[k], B[k1], B[k]), (A[k], A[k1], B[k1]))
            for tri in tris:
                P = [b.verts[j] for j in tri]
                cen = _mul(_add(_add(P[0], P[1]), P[2]), 1 / 3)
                _face_out(b, tri, (cen[0], cen[1], 0.0), 0)
    b.fill([rings[0]], 0, 0, (0.0, 0.0, -1.0))
    top = b.v(0.0, 0.0, prof[-1][0] - 14.0)          # the tuft's crumpled top, dipping in
    for k in range(segs):
        _face_out(b, [rings[-1][k], rings[-1][(k + 1) % segs], top], (0.0, 0.0, 1.0), 0)
    return b


def item_trashbag() -> Item:
    s = TBAG
    lods = [Lod(_bag_builder(k)) for k in range(3)]
    mn, mx = _aabb(lods[0].builder)
    name = "SM_CSK_TrashBag_Full"
    return Item(
        name=name, lods=lods, materials=["M_CSK_BagBlack"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, 0.0, 530.0))],
        hulls=[((mn[0], mn[1], 0.0), (mx[0], mx[1], mx[2]))], budget=BUDGETS[name],
        data={"footprint_mm": [mx[0] - mn[0], mx[1] - mn[1], mx[2]], "pose": "upright", "pivot": "bottom-centre",
              "reference": "References/CardShop/csk_bins.png (sheet 29 (2))",
              "notes": ["Sheet 29: a crumpled full body, round shoulders, a twisted tied neck and a flared tuft. The "
                        "crumple is deterministic (a hash of ring and segment), so every build is identical.",
                        "Grip: at the twisted neck, where a hand holds it."]},
    )


# =========================================================================== registry

ITEMS = {
    "h_backroom_mailer_s": lambda: item_mailer("S"),
    "h_backroom_mailer_l": lambda: item_mailer("L"),
    "h_backroom_mailer_s_open": lambda: item_mailer("S", True),
    "h_backroom_mailer_l_open": lambda: item_mailer("L", True),
    "h_backroom_tapegun": item_tapegun,
    "h_backroom_trashcan": item_trashcan,
    "h_backroom_trashcan_lid": item_trashcan_lid,
    "h_backroom_trashbag": item_trashbag,
}
