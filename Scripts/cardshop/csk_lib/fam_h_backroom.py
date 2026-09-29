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
    "SM_CSK_TapeGun": 1200,
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
    band=(478.0, 522.0, 211.0),   # sheet 29: the raised band where the dome meets the body: z0, z1, outer radius
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

TBAG = dict(                      # H6, sheet 29 (2)
    d=450.0,                      # E (spec) = sheet 29 call-out (the 450 line spans the bag's base exactly)
    h=610.0,                      # sheet 29: 610 to the tuft's top at the 450 line's scale (spec 600 E; the sheet's
                                  # 600 arrow is drawn from the knot to the floor, which the drawing's scale contradicts)
    # the radius profile (z, r), measured row by row off sheet 29 at 1 px = 1 mm: the base spreads to 464 at 45 up,
    # near-straight sides, round shoulders from ~390, the twisted neck tied at ~510, a ruffled tuft to 610
    prof=((0.0, 170.0), (14.0, 218.0), (50.0, 232.0), (130.0, 221.0), (230.0, 210.0), (330.0, 205.0),
          (390.0, 194.0), (430.0, 166.0), (460.0, 125.0), (482.0, 90.0), (497.0, 52.0), (506.0, 24.0),
          (515.0, 26.0), (530.0, 45.0), (560.0, 66.0), (588.0, 72.0), (602.0, 92.0), (610.0, 62.0)),
    knot=510.0,
    segs=(16, 10, 8),
    crumple=0.07,                 # E: +- radial crumple (fraction of r), deterministic hash
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
    for i, (z, r) in enumerate(prof):
        ring = []
        for k in range(segs):
            t = 2 * math.pi * (k + 0.5 * (i % 2)) / segs
            near = max(0.0, 1.0 - abs(z - zn) / 130.0)      # pleats gather toward the neck (and flare in the tuft)
            pleat = (1.0 - s["pleat"] * near) if k % 2 else 1.0
            cr = 1.0 + s["crumple"] * (2 * _hash(i, k, 7) - 1) * (0.3 if z < 1.0 else 1.0)
            rr = r * pleat * cr
            tw = 0.3 * (2 * math.pi / segs) * near * (2 * _hash(i, k, 3) - 1)   # the twist round the neck
            gap = min(z - prof[i - 1][0], prof[i + 1][0] - z) if 0 < i < len(prof) - 1 else 0.0
            zz = z + min(9.0, 0.3 * gap) * (2 * _hash(i, k, 11) - 1)      # ragged rings that never cross
            ring.append(b.v(rr * math.cos(t + tw), rr * math.sin(t + tw), zz))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(segs):
            k1 = (k + 1) % segs
            for tri in ((A[k], A[k1], B[k1]), (A[k], B[k1], B[k])) if (i + k) % 2 else \
                    ((A[k], A[k1], B[k]), (A[k1], B[k1], B[k])):
                P = [b.verts[j] for j in tri]
                cen = _mul(_add(_add(P[0], P[1]), P[2]), 1 / 3)
                _face_out(b, tri, (cen[0], cen[1], 0.0), 0)
    b.fill([rings[0]], 0, 0, (0.0, 0.0, -1.0))
    top = b.v(0.0, 0.0, prof[-1][0] - 12.0)          # the tuft's crumpled top, dipping in
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
    "h_backroom_trashcan": item_trashcan,
    "h_backroom_trashcan_lid": item_trashcan_lid,
    "h_backroom_trashbag": item_trashbag,
}
