"""Family a_shelving: slatwall, hooks, slatwall shelf, gondola shelving, wire rack and box tier shelf
(CARDSHOP_KIT_SPEC.md 3.A7-A13; reference sheets 19, 20, 21, notes in References/CardShop/REFERENCE_LOG.md).

Flags as in spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = estimate with a
measured range. "sheet N" = the value or the form comes from that reference sheet's notes (the picture wins over E).

Frames: millimetres, +X to the viewer's right, +Y away from the customer, +Z up. The slatwall panels and the gondola
sections pivot on an end corner (spec A7, A10: "end-corner pivot"); the hooks and shelves pivot on their mount point
(the groove / upright slot they hang in), so a Groove_* or Mount_* socket seats them directly; the wire rack and the box
tier shelf pivot on their bottom centre.

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import Item, Lod, Socket, _face_out, solve_grid
from .shapes import Builder

Vec3 = Tuple[float, float, float]

# =========================================================================== numbers

# spec 4.2 classes the box tier shelf and the shelves accept but G1 did not define (footprint + 10 pitch, D)
CLASSES = {
    "BoxL": S.ItemClass("BoxL", (190.0, 76.0, 140.0), (200.0, 86.0)),
    "BoxC": S.ItemClass("BoxC", (190.0, 89.0, 165.0), (200.0, 99.0)),
}

SLAT = dict(                      # A7, sheet 19
    t=19.0,                       # E (spec)
    h=2400.0,                     # E (spec)
    pitch=76.2,                   # M [D27]
    grooves=31,                   # D floor(2400 / 76.2)
    neck=11.0, neck_d=5.0,        # E: the T-slot opening (Z) and its depth; sheet 19 shows a T-slot profile
    head=24.0, head_d=6.0,        # E: the T's head (undercut), total groove depth 11 of 19
    lip_c=1.0,                    # E: crisp chamfer on the groove lips
    edge_c=1.0,                   # E: chamfer on the panel's outer edges
)

HOOK = dict(                      # A8, sheet 19
    wire=4.76,                    # M [D28] (sheet 19: 4.8)
    lengths=(102.0, 203.0, 305.0),  # E (spec: v1 picks), inside 25-305 E*
    plate=(38.0, 45.0, 1.5),      # E: the flat back plate W x H x T; its top bends into the groove (sheet 19)
    tab_top=-3.8,                 # E: the bend's top face, below the groove centre (inside the 11 opening)
    leg=(5.5, 7.0, -10.5),        # E: the down-leg behind the lower lip: y0, y1, bottom z
    arm_z=-36.0,                  # E: the arm's axis below the groove centre (welded low on the plate)
    kink=(22.0, 30.0),            # E: the short upward kink near the tip (sheet 19): run, angle deg
    price_plate=(40.0, 28.0, 1.2, 30.0),  # E: W x H x T, tilted back from vertical toward the viewer (sheet 19)
    hang_start=12.0,              # E: the hang run starts this far in front of the plate
)

SHELF_SLAT = dict(                # A9, sheet 19
    w=1000.0, d=305.0, t=19.0,    # E (spec)
    bracket_x=375.0,              # E: the two blade brackets' centres (+-)
    blade_t=3.0,                  # E
    blade_h=(100.0, 24.0),        # E: blade height at the wall, at the tip (sheet 19: tapered blade)
    lip=(4.0, 6.0),               # E: the bracket's front lip: thickness, height above the board (sheet 19)
    clear_h=280.0,                # E: the level's clear height (the next shelf 4 grooves up)
)

GONDOLA = dict(                   # A10, sheet 20
    w=1219.0, h=1372.0,           # M [D30]
    endcap_w=610.0,               # sheet 20 (end cap 610 x 1372)
    deck_d=406.0,                 # E* (range 406-559; sheet 20 406)
    kick=100.0,                   # E: the deck top / kick plate top
    deck_z0=10.0,                 # E: the base sits on 10 mm levelling feet (sheet 20: feet under the base)
    upright=(30.0, 30.0),         # E: section X x Y (single); double: 30 x 40 (slotted both faces)
    upright_double_d=40.0,        # E
    slot=(5.0, 12.0, 25.4, 4.0),  # slot W x H (E), pitch 25.4 (E*), pocket depth (E); rectangular (sheet 20)
    slots=49,                     # D: floor((1372 - 100 - 27) / 25.4) slots above the deck
    grooves=16,                   # D floor((1372 - 100) / 76.2)
    mount_pitch=101.6,            # E (spec: every 4th slot)
    mount_first=2,                # E: the first mount 2 x 101.6 above the deck (a lower shelf leaves no room)
    foot=(12.0, 10.0),            # E: levelling foot radius, height
    panel_t=19.0,                 # E: the slatwall back (as A7)
)

GSHELF = dict(                    # A11, sheet 20
    w=1219.0,                     # E* (spec)
    depths=(305.0, 406.0),        # E* (spec; sheet 20)
    pan=(30.0, 1.2),              # E: steel pan flange depth, sheet thickness
    lip=(38.0, 3.0, 12.0, 6.0),   # price channel: height 38 (E, spec), proud of the top 3, face bottom / top
                                  # projection (sheet 20: a sloped face)
    top_above_mount=8.0,          # E: shelf top above the upper hook slot's centre
    bracket=(3.0, 80.0, 20.0),    # E: bracket plate thickness, height at the upright, height at the tip
    clear_h=280.0,                # E: the level's clear height
)

GCORNER = dict(                   # A11 corner, sheet 20
    size=610.0,                   # E (spec; sheet 20 610 x 610 x 1372)
    shelf_d=305.0,                # E: the L shelves (the smaller A11 depth)
    shelf_z=(354.0, 608.0, 862.0, 1116.0),   # E: 4 shelves splitting deck-to-top in fifths (sheet 20: 4 shelves)
    slab=30.0,                    # E: shelf thickness (the pan flange)
    budget=2000,                  # E (spec)
)

RACK = dict(                      # A12, sheet 21
    w=914.0, d=457.0, h=1829.0,   # E (spec)
    post_r=12.7,                  # E: 25.4 chrome post
    post_inset=19.0,              # E: post centre from the outer edge (the collar radius)
    groove=(25.4, 0.9, 0.6),      # E: ring grooves (sheet 21): pitch, depth, width of the step
    decks=5,                      # sheet 21: 5 decks (top + 4); the spec's 4 was E
    deck_first=152.4, deck_pitch=406.4,   # E: deck tops on the 25.4 groove grid (6 and 16 grooves)
    truss=25.0,                   # E: rim-to-rim height of the truss edge (sheet 21: zigzag rod between two rims)
    rim_r=3.0, wire_r=2.0,        # E: rim and mat / zigzag wire radii
    mat_pitch=25.4,               # E: mat wires front to back
    zig=30.0,                     # E: horizontal run of one zigzag leg
    collar=(19.0, 16.0, 40.0),    # E: the corner collar: bottom radius, top radius, height
    foot=(17.0, 13.5, 20.0),      # E: black levelling foot: bottom radius, top radius, height (sheet 21)
    budget=14000,                 # raised from 7000 (E): 5 decks (sheet 21) and 4 ring-grooved posts (sheet 21)
)

TIER = dict(                      # A13, sheet 21
    w=1219.0, d=457.0, h=1372.0,  # E (spec)
    side_t=19.0,                  # E: oak side panels
    top_d=152.4,                  # E: the side panels' narrow top (sheet 21: tapered, narrow at the top)
    deck_z=252.0,                 # sheet 21: tiers 280 apart starting at 252 (252 + 4 x 280 = 1372)
    pitch=280.0,                  # sheet 21
    tilt=10.0,                    # E (spec) = sheet 21: shelves tilted back 10 deg
    lip=(12.0, 25.0),             # sheet 21: 25 front lip; thickness E
    board=19.0,                   # E: white shelf and deck boards
    kick=(60.0, 30.0),            # E: black kick height, recess (sheet 21: black kick under the oak front)
    step=76.2,                    # D: the front slope's step per tier ((457 - 152.4) / 4)
)

BUDGETS = {
    "SM_CSK_Slatwall_1000x2400": 3000, "SM_CSK_Slatwall_2000x2400": 3000,
    "SM_CSK_Hook_Slat_102": 400, "SM_CSK_Hook_Slat_203": 400, "SM_CSK_Hook_Slat_305": 400,
    "SM_CSK_Shelf_Slat_1000": 600,
    "SM_CSK_Gondola_Single_1372": 4000, "SM_CSK_Gondola_EndCap_1372": 4000, "SM_CSK_Gondola_Double_1372": 6000,
    "SM_CSK_Gondola_Shelf_305": 500, "SM_CSK_Gondola_Shelf_406": 500,
    "SM_CSK_Gondola_Corner_1372": GCORNER["budget"],
    "SM_CSK_Rack_Wire_914": RACK["budget"],
    "SM_CSK_Shelf_BoxTier_1219": 1200,
}

SHELF_ACCEPTS = ("Pack", "BoxS", "BoxL", "BoxC", "Deck")
TIER_ACCEPTS = ("BoxS", "BoxL", "BoxC")          # + Retail (per item: no fixed grid)

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


# =========================================================================== shape helpers

def _sweep(b: Builder, prof, path, cap_mat: int, caps=(True, True)) -> Tuple[List[int], List[int]]:
    """Sweep a closed profile ``prof`` [(n, z, mat of the edge to the next point)] along an open polyline ``path``
    [(x, y)] in XY (mitred corners). ``n`` is the offset to the left of the path direction, z is absolute. The caps
    are planar fills. Returns the first and last rings."""
    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1]
               for i in range(len(prof)))
    sgn = 1.0 if area > 0 else -1.0
    dirs = []
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
        ln = math.hypot(x1 - x0, y1 - y0)
        dirs.append(((x1 - x0) / ln, (y1 - y0) / ln))
    lefts = [(-dy, dx) for dx, dy in dirs]
    normals = []
    for i in range(len(path)):
        if i == 0:
            normals.append(lefts[0])
        elif i == len(path) - 1:
            normals.append(lefts[-1])
        else:
            mx, my = lefts[i - 1][0] + lefts[i][0], lefts[i - 1][1] + lefts[i][1]
            ln = math.hypot(mx, my)
            mx, my = mx / ln, my / ln
            c = mx * lefts[i][0] + my * lefts[i][1]
            normals.append((mx / c, my / c))
    rings = [[b.v(px + nx * n, py + ny * n, z) for n, z, _ in prof] for (px, py), (nx, ny) in zip(path, normals)]
    m = len(prof)
    for j in range(len(path) - 1):
        lx, ly = lefts[j]
        for k in range(m):
            k1 = (k + 1) % m
            dn, dz = prof[k1][0] - prof[k][0], prof[k1][1] - prof[k][1]
            on, oz = dz * sgn, -dn * sgn                          # the profile edge's outward normal
            _face_out(b, [rings[j][k], rings[j][k1], rings[j + 1][k1], rings[j + 1][k]],
                      (lx * on, ly * on, oz), prof[k][2])
    if caps[0]:
        b.fill([rings[0]], cap_mat, 0, (-dirs[0][0], -dirs[0][1], 0.0))
    if caps[1]:
        b.fill([rings[-1]], cap_mat, 0, (dirs[-1][0], dirs[-1][1], 0.0))
    return rings[0], rings[-1]


def _prism_x(b: Builder, prof, x0: float, x1: float, cap_mat: int, caps=(True, True)) -> None:
    """A prism along +X of the profile [(y, z, mat)]."""
    _sweep(b, prof, [(x0, 0.0), (x1, 0.0)], cap_mat, caps)


def _plain(pts, mat: int):
    return [(p[0], p[1], mat) for p in pts]


def _tube(b: Builder, pts: Sequence[Vec3], r: float, sides: int, mat: int, closed: bool = False,
          up: Vec3 = (0.0, 0.0, 1.0), caps: Tuple[bool, bool] = (False, False), phase: float = 0.5) -> None:
    """A round wire along a polyline, mitred at the joints (parallel-transported frame). ``up`` seeds the frame; for
    a planar loop or zigzag pass the plane normal so the frame closes on itself. Open ends are left open unless
    ``caps`` (they sit inside another part)."""
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


def _lathe(b: Builder, cx: float, cy: float, prof: Sequence[Tuple[float, float]], sides: int, mat: int,
           caps: Tuple[bool, bool] = (True, True), phase: float = 0.5) -> None:
    """A solid of revolution about a vertical axis; ``prof`` [(r, z)] from the bottom up."""
    angs = [2 * math.pi * (k + phase) / sides for k in range(sides)]
    rings = [[b.v(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in angs] for r, z in prof]
    for i in range(len(prof) - 1):
        (r0, z0), (r1, z1) = prof[i], prof[i + 1]
        for k in range(sides):
            k1 = (k + 1) % sides
            tm = (angs[k] + angs[k1]) / 2 if k1 else angs[k] + math.pi / sides
            out = (math.cos(tm) * (z1 - z0), math.sin(tm) * (z1 - z0), r0 - r1)
            _face_out(b, [rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k]], out, mat)
    if caps[0]:
        b.fill([rings[0]], mat, 0, (0.0, 0.0, -1.0))
    if caps[1]:
        b.fill([rings[-1]], mat, 0, (0.0, 0.0, 1.0))


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


def _slotted_bar(b: Builder, x0: float, x1: float, y0: float, y1: float, z0: float, z1: float,
                 slot_faces: Sequence[str], slot_zs: Sequence[float], slot: Tuple[float, float, float],
                 mat: int, chamfer: float = 1.0) -> None:
    """A rectangular steel upright with a column of real slot pockets on its -Y face ("ny") and / or +Y face ("py")
    (sheet 20: slotted uprights, rectangular slots), its four long edges chamfered. Each slotted face is a ladder of
    quads round the pockets (shared vertices); the plain faces and the chamfers share only the ladders' corners
    (boundary T-junctions, no coincident vertices). The ends are octagon fills."""
    sw, sh, sd = slot
    c = chamfer
    xc = (x0 + x1) / 2
    xs = [x0 + c, xc - sw / 2, xc + sw / 2, x1 - c]
    bands = []
    z = z0
    for zc in slot_zs:
        lo, hi = zc - sh / 2, zc + sh / 2
        bands.append((z, lo, False))
        bands.append((lo, hi, True))
        z = hi
    bands.append((z, z1, False))
    corners = {}
    for face in ("ny", "py"):
        yf = y0 if face == "ny" else y1
        out = (0.0, -1.0 if face == "ny" else 1.0, 0.0)
        if face not in slot_faces:
            for col in (0, 3):
                for k, zz in ((0, z0), (1, z1)):
                    corners[face, col, k] = b.v(xs[col], yf, zz)
            _face_out(b, [corners[face, 0, 0], corners[face, 3, 0], corners[face, 3, 1], corners[face, 0, 1]], out, mat)
            continue
        yd = yf + (sd if face == "ny" else -sd)
        zb = [bands[0][0]] + [hi for _, hi, _ in bands]
        F = [[b.v(x, yf, zz) for x in xs] for zz in zb]
        for r, (lo, hi, is_slot) in enumerate(bands):
            for col in range(3):
                if is_slot and col == 1:
                    continue
                _face_out(b, [F[r][col], F[r][col + 1], F[r + 1][col + 1], F[r + 1][col]], out, mat)
            if is_slot:
                d_ = [b.v(xs[1], yd, lo), b.v(xs[2], yd, lo), b.v(xs[2], yd, hi), b.v(xs[1], yd, hi)]
                h = [F[r][1], F[r][2], F[r + 1][2], F[r + 1][1]]
                zc = (lo + hi) / 2
                for a in range(4):
                    e = (a + 1) % 4
                    mx = (b.verts[h[a]][0] + b.verts[h[e]][0]) / 2
                    mz = (b.verts[h[a]][2] + b.verts[h[e]][2]) / 2
                    _face_out(b, [h[a], h[e], d_[e], d_[a]], (xc - mx, 0.0, zc - mz), mat)
                _face_out(b, d_, out, mat)
        for col in (0, 3):
            corners[face, col, 0] = F[0][col]
            corners[face, col, 1] = F[-1][col]
    rings = []
    for k, zz in ((0, z0), (1, z1)):
        q = corners
        rings.append([q["ny", 0, k], q["ny", 3, k], b.v(x1, y0 + c, zz), b.v(x1, y1 - c, zz), q["py", 3, k],
                      q["py", 0, k], b.v(x0, y1 - c, zz), b.v(x0, y0 + c, zz)])
    ym = (y0 + y1) / 2
    for i in (1, 2, 3, 5, 6, 7):                    # the chamfers and the two plain side faces
        i1 = (i + 1) % 8
        pa, pb = b.verts[rings[0][i]], b.verts[rings[0][i1]]
        out = ((pa[0] + pb[0]) / 2 - xc, (pa[1] + pb[1]) / 2 - ym, 0.0)
        _face_out(b, [rings[0][i], rings[0][i1], rings[1][i1], rings[1][i]], out, mat)
    b.fill([rings[0]], mat, 0, (0.0, 0.0, -1.0))
    b.fill([rings[1]], mat, 0, (0.0, 0.0, 1.0))


# =========================================================================== slatwall profile (A7, A10, A11 corner)

FACE, CORE = 0, 1           # material indices in every slatwall mesh: white face, bare MDF


def _groove_run(yf: float, inward: float, zcs: Sequence[float], level: int, s=SLAT):
    """The points up one grooved face at y = yf (the material lies toward ``inward``): [(y, z, mat of the edge to the
    next point)], bottom to top. level 0: the T-slot with chamfered lips (sheet 19); 1: the T-slot, sharp lips;
    2: a rectangular groove the depth of the opening; 3: a flat band (MDF strip) on the face."""
    n, nd, h, hd, c = s["neck"], s["neck_d"], s["head"], s["head_d"], s["lip_c"]
    out = []
    for zc in zcs:
        y = lambda d: yf + inward * d
        if level == 3:
            out += [(yf, zc - n / 2, CORE), (yf, zc + n / 2, FACE)]
        elif level == 2:
            out += [(yf, zc - n / 2, CORE), (y(nd + hd), zc - n / 2, CORE), (y(nd + hd), zc + n / 2, CORE),
                    (yf, zc + n / 2, FACE)]
        else:
            lip_lo = [(yf, zc - n / 2 - c, CORE), (y(c), zc - n / 2, CORE)] if level == 0 else [(yf, zc - n / 2, CORE)]
            lip_hi = [(y(c), zc + n / 2, CORE), (yf, zc + n / 2 + c, FACE)] if level == 0 else [(yf, zc + n / 2, FACE)]
            out += lip_lo + [(y(nd), zc - n / 2, CORE), (y(nd), zc - h / 2, CORE), (y(nd + hd), zc - h / 2, CORE),
                             (y(nd + hd), zc + h / 2, CORE), (y(nd), zc + h / 2, CORE), (y(nd), zc + n / 2, CORE)]
            out += lip_hi
    return out


def _slat_profile(yf: float, yb: float, z0: float, z1: float, front: Optional[Sequence[float]],
                  back: Optional[Sequence[float]], level: int, ce: float = SLAT["edge_c"]):
    """The closed (y, z, mat) profile of a slatwall board between y = yf (front, faces -Y) and yb (back, faces +Y),
    z0..z1, with grooves at ``front`` / ``back`` centres (None: a plain MDF face). Outer edges chamfered ``ce``."""
    fmat = FACE if front is not None else CORE
    bmat = FACE if back is not None else CORE
    P = [(yf, z0 + ce, fmat)]
    if front:
        P += _groove_run(yf, 1.0, front, level)
    P += [(yf, z1 - ce, CORE), (yf + ce, z1, CORE), (yb - ce, z1, CORE), (yb, z1 - ce, bmat)]
    if back:
        U = _groove_run(yb, -1.0, back, level)
        for i in range(len(U) - 1, -1, -1):
            P.append((U[i][0], U[i][1], U[i - 1][2] if i > 0 else FACE))
    P += [(yb, z0 + ce, CORE), (yb - ce, z0, CORE), (yf + ce, z0, CORE)]
    return P


def _groove_centres(z0: float, z1: float, count: int, pitch: float) -> List[float]:
    first = z0 + ((z1 - z0) - (count - 1) * pitch) / 2
    return [first + k * pitch for k in range(count)]


# =========================================================================== level sockets

def _level(name: str, loc: Vec3, width: float, depth: float, clear: float, accepts, comps: Sequence[Vec3],
           tags: Sequence[Tuple[Vec3, Vec3]], rot: Vec3 = (0.0, 0.0, 0.0), extra: Optional[Dict] = None):
    """Level + Compartment + PriceTag sockets and the level's .csk.json entry (grids from solve_grid)."""
    socks = [Socket(f"Level_{name}", loc, rot, "DISPLAY")]
    for i, c in enumerate(comps):
        socks.append(Socket(f"Compartment_{name}_{i + 1:02d}", c, rot, "DISPLAY"))
    for i, (t, trot) in enumerate(tags):
        socks.append(Socket(f"PriceTag_{name}_{i + 1:02d}", t, trot, "DISPLAY"))
    grids = [g for g in (solve_grid(width, depth, clear, c) for c in accepts) if g]
    lv = {"socket": f"Level_{name}", "interior_mm": [round(width, 3), round(depth, 3)],
          "clear_h_mm": round(clear, 3), "compartments": len(comps), "grids": grids}
    if extra:
        lv.update(extra)
    return socks, lv


# =========================================================================== A7 slatwall panel

def item_slatwall(w: float) -> Item:
    """Sheet 19: a 19 MDF panel, white faces, bare MDF in the grooves and on the edges, 31 T-slot grooves at 76.2
    through the full width (the T profile shows at the panel ends). Pivot: the bottom-left corner of the back (wall)
    face; the panel runs to +X, its face at y = -19."""
    s = SLAT
    T, H = s["t"], s["h"]
    zcs = _groove_centres(0.0, H, s["grooves"], s["pitch"])
    lods = []
    for level in (0, 2, 3):
        b = Builder()
        _prism_x(b, _slat_profile(-T, 0.0, 0.0, H, zcs, None, level), 0.0, w, CORE)
        lods.append(Lod(b))
    name = f"SM_CSK_Slatwall_{int(w)}x{int(H)}"
    sockets = [Socket("Seat", (0, 0, 0))]
    sockets += [Socket(f"Groove_{k + 1:02d}", (0.0, -T, zc)) for k, zc in enumerate(zcs)]
    sockets += [Socket("Snap_L", (0, 0, 0)), Socket("Snap_R", (w, 0, 0))]
    return Item(
        name=name, lods=lods, materials=["M_CSK_Slatwall", "M_CSK_MDF"], projections={}, sockets=sockets,
        hulls=[((0.0, -T, 0.0), (w, 0.0, H))], budget=BUDGETS[name],
        data={"footprint_mm": [w, T, H], "pose": "upright, back on the wall",
              "pivot": "end corner: bottom-left of the back (wall) face; the face is at y = -19",
              "rails": [{"sockets": "Groove_01..31", "axis": "X", "length_mm": w, "pitch_mm": s["pitch"],
                         "note": "each socket is the left end of a groove, on the face plane at the groove centre; "
                                 "hooks and brackets slide along +X"}],
              "groove_mm": {"opening": s["neck"], "opening_depth": s["neck_d"], "head": s["head"],
                            "head_depth": s["head_d"], "profile": "T-slot"},
              "reference": "sheet 19 (csk_slatwall.png, notes in REFERENCE_LOG.md)",
              "notes": ["Sheet 19 shows bare MDF in the grooves and no aluminium inserts, so the spec's Insert slot "
                        "is not modelled (M_CSK_MDF instead)."]},
    )


# =========================================================================== A8 hook

def _hook_lod(L: float, level: int) -> Lod:
    h = HOOK
    pw, ph, pt = h["plate"]
    zt = h["tab_top"]
    ly0, ly1, lz = h["leg"]
    zb = zt - ph
    CH = 0
    b = Builder()
    if level < 2:           # the back plate bent into the groove: front plate, tab, down-leg behind the lower lip
        prof = [(-pt, zb), (-pt, zt), (ly1, zt), (ly1, lz), (ly0, lz), (ly0, zt - pt), (0.0, zt - pt), (0.0, zb)]
    else:
        prof = [(-pt, zb), (-pt, zt), (0.0, zt), (0.0, zb)]
    _prism_x(b, _plain(prof, CH), -pw / 2, pw / 2, CH)
    r = h["wire"] / 2
    za = h["arm_z"]
    run, ang = h["kink"]
    tip = (0.0, -L, za + run * math.tan(math.radians(ang)))
    path = [(0.0, -pt + 0.7, za), (0.0, -(L - run), za), tip]
    _tube(b, path, r, (8, 6, 4)[level], CH, up=(1.0, 0.0, 0.0))
    ppw, pph, ppt, tilt = h["price_plate"]
    t = math.radians(tilt)
    nrm = (0.0, -math.cos(t), math.sin(t))                  # the plate's face normal: toward the viewer, tipped up
    upv = (0.0, math.sin(t), math.cos(t))
    c = _add(tip, _mul(nrm, ppt / 2 - 0.3))                 # the wire's end sits 0.3 into the plate's back
    _obox(b, c, (1.0, 0.0, 0.0), upv, nrm, ppw / 2, pph / 2, ppt / 2, CH)
    return Lod(b, bevel_mm=0.3 if level == 0 else None)


def item_hook(L: float) -> Item:
    """Sheet 19: a flat back plate whose top bends into the groove and drops behind the lower lip, a straight 4.76
    wire arm, a short upward kink near the tip and a flat price plate at the tip, tilted toward the viewer.
    Pivot = Mount: the groove centre on the slatwall face plane (the plate's back lies on y = 0, the wall is +Y)."""
    h = HOOK
    pw, ph, pt = h["plate"]
    zb = h["tab_top"] - ph
    r = h["wire"] / 2
    za = h["arm_z"]
    run, ang = h["kink"]
    ppw, pph, ppt, tilt = h["price_plate"]
    t = math.radians(tilt)
    tip = (0.0, -L, za + run * math.tan(math.radians(ang)))
    nrm = (0.0, -math.cos(t), math.sin(t))
    face = _add(tip, _mul(nrm, ppt - 0.3))
    upv = (0.0, math.sin(t), math.cos(t))
    c = _add(tip, _mul(nrm, ppt / 2 - 0.3))
    corners = [_add(c, _add(_mul(upv, j * pph / 2), _mul(nrm, k * ppt / 2))) for j in (-1, 1) for k in (-1, 1)]
    ymin = min(p[1] for p in corners)
    top = max(p[2] for p in corners)
    name = f"SM_CSK_Hook_Slat_{int(L)}"
    hang_y = -(pt + h["hang_start"])
    hang_run = (L - run) - pt - h["hang_start"]
    return Item(
        name=name, lods=[_hook_lod(L, k) for k in range(3)], materials=["M_CSK_Chrome"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)),
                 Socket("Hang_Start", (0.0, hang_y, za + r), kind="CONTAIN"),
                 Socket("Label", face, (90.0 - tilt, 0.0, 0.0))],
        hulls=[((-pw / 2, ymin, zb), (pw / 2, h["leg"][1], top))], budget=BUDGETS[name],
        data={"footprint_mm": [pw, round(h["leg"][1] - ymin, 3), round(top - zb, 3)], "pose": "hangs in a slatwall groove",
              "pivot": "Mount: groove centre on the slatwall face plane (seat it on a Groove_* socket)",
              "hang": {"socket": "Hang_Start", "axis": "-Y", "run_mm": round(hang_run, 3), "class": "Hang",
                       "pitch": "item T + 2 (spec 4.2)"},
              "label": "Label socket: +Z is the price plate's face normal (tilted %g deg toward the viewer)" % tilt,
              "reference": "sheet 19 (csk_slatwall.png)"},
    )


# =========================================================================== A9 slatwall shelf

def _blade_profile(level: int, s=SHELF_SLAT, h=HOOK):
    """The blade bracket in YZ (sheet 19: tapered blade, front lip), back edge on y = 0 with two tongues that enter
    the grooves at z = 0 and z = -76.2 and drop behind the lower lips."""
    D = s["d"]
    top = 4.5                                       # the board's underside is z = 4 (0.5 sink)
    hw, ht = s["blade_h"]
    lt, lh = s["lip"]
    yl = -(D + 1.0) - 0.5                           # the lip's back face, 0.5 in front of the board's front edge
    board_top = 4.0 + s["t"]
    pts = [(0.0, top), (yl, top), (yl, board_top + lh), (yl - lt, board_top + lh), (yl - lt, top - ht),
           (0.0, top - hw)]
    if level < 2:
        ly0, ly1, lz = h["leg"]
        for zc in (-SLAT["pitch"], 0.0):
            pts += [(0.0, zc - 5.0), (ly0, zc - 5.0), (ly0, zc + lz), (ly1, zc + lz), (ly1, zc + 1.0), (0.0, zc + 1.0)]
    return pts


def item_shelf_slat() -> Item:
    """Sheet 19: a 1000 x 305 white board on two tapered blade brackets with a front lip. Pivot = the upper tongues'
    groove centre on the slatwall face plane, between the brackets (seat Mount_L / Mount_R on one groove)."""
    s = SHELF_SLAT
    W, D, T = s["w"], s["d"], s["t"]
    xb, bt = s["bracket_x"], s["blade_t"]
    BOARD, CH = 0, 1
    y0, y1 = -(D + 1.0), -1.0
    zb0, zb1 = 4.0, 4.0 + T
    lods = []
    for level in range(3):
        b = Builder()
        b.box((-W / 2, y0, zb0), (W / 2, y1, zb1), mat=BOARD)
        for sx in (-1, 1):
            _prism_x(b, _plain(_blade_profile(level), CH), sx * xb - bt / 2, sx * xb + bt / 2, CH)
        lods.append(Lod(b, bevel_mm=0.5 if level == 0 else None))
    hw = s["blade_h"][0]
    yc = (y0 + y1) / 2
    comps = [(x, yc, zb1) for x in (-W / 3, 0.0, W / 3)]
    tags = [((x, y0, (zb0 + zb1) / 2), (0.0, 0.0, 0.0)) for x in (-W / 3, 0.0, W / 3)]
    lsocks, lv = _level("S1", (0.0, yc, zb1), W, D, s["clear_h"], SHELF_ACCEPTS, comps, tags)
    name = "SM_CSK_Shelf_Slat_1000"
    lt, lh = s["lip"]
    return Item(
        name=name, lods=lods, materials=["M_CSK_Laminate", "M_CSK_Chrome"], projections={},
        sockets=[Socket("Seat", (0, 0, 0))] + lsocks + [Socket("Mount_L", (-xb, 0, 0)), Socket("Mount_R", (xb, 0, 0))],
        hulls=[((-W / 2, y0 - 0.5 - lt, 4.5 - hw), (W / 2, 0.0, zb1))], budget=BUDGETS[name],
        data={"footprint_mm": [W, D + 1.5 + lt, zb1 + lh - (4.5 - hw)], "pose": "hangs on a slatwall",
              "pivot": "the upper tongues' groove centre on the slatwall face plane, centred between the brackets",
              "accepts": list(SHELF_ACCEPTS), "levels": [lv],
              "mount": "seat on a Groove_* socket moved +X to the shelf centre (Mount_L / Mount_R fall on the "
                       "same groove); the lower tongues take the groove 76.2 below",
              "reference": "sheet 19 (csk_slatwall.png)",
              "notes": ["Sheet 19: 'a white board on two tapered blade brackets with a front lip'. The lip is read as "
                        "the brackets' upturned tips in front of the board (open question)."]},
    )


# =========================================================================== A10 gondola

def _gondola_dims(kind: str):
    g = GONDOLA
    W = g["endcap_w"] if kind == "EndCap" else g["w"]
    double = kind == "Double"
    ux, uy = g["upright"]
    if double:
        ud = g["upright_double_d"]
        up_y = (-ud / 2, ud / 2)
        panel_y = (-ud / 2 + 1.0, ud / 2 - 1.0)
        decks = [("F", -ud / 2 - g["deck_d"], -ud / 2), ("B", ud / 2, ud / 2 + g["deck_d"])]
    else:
        up_y = (-uy, 0.0)
        panel_y = (-uy + 1.0, -uy + 1.0 + g["panel_t"])
        decks = [("F", -uy - g["deck_d"], -uy)]
    return dict(W=W, double=double, ux=ux, up_y=up_y, panel_y=panel_y, decks=decks)


def _gondola_mounts():
    g = GONDOLA
    zs = []
    j = g["mount_first"]
    while g["kick"] + j * g["mount_pitch"] <= g["h"] - 40.0:
        zs.append(g["kick"] + j * g["mount_pitch"])
        j += 1
    return zs


def _gondola_lod(kind: str, level: int) -> Lod:
    g = GONDOLA
    k = _gondola_dims(kind)
    W, ux, (uy0, uy1), (py0, py1) = k["W"], k["ux"], k["up_y"], k["panel_y"]
    STEEL, FACE_, CORE_ = 0, 1, 2
    z0d, zk, H = g["deck_z0"], g["kick"], g["h"]
    base = Builder()
    for side, ya, yb in k["decks"]:                            # base deck: its front face is the kick plate
        ya2, yb2 = (ya, yb + 0.5) if side == "F" else (ya - 0.5, yb)
        base.box((0.0, ya2, z0d + 0.5), (W, yb2, zk), mat=STEEL)
    extra = Builder()
    sw, sh, pitch, sd = g["slot"]
    slot_zs = [zk + pitch * (i + 1) for i in range(g["slots"])] if level == 0 else []
    faces = ("ny", "py") if k["double"] else ("ny",)
    for x0 in (0.0, W - ux):                                   # slotted uprights (sheet 20)
        _slotted_bar(extra, x0, x0 + ux, uy0, uy1, z0d, H, faces if level == 0 else (), slot_zs, (sw, sh, sd), STEEL)
    zcs = _groove_centres(zk, H, g["grooves"], SLAT["pitch"])
    plevel = (0, 1, 3)[level]
    prof = _slat_profile(py0, py1, z0d + 0.5, H - 1.0, zcs, zcs if k["double"] else None, plevel)
    prof = [(y, z, (FACE_, CORE_)[m]) for y, z, m in prof]
    _prism_x(extra, prof, ux - 0.5, W - ux + 0.5, CORE_, caps=(False, False))     # ends hidden in the uprights
    fr, fh = g["foot"]
    ys = sorted({(uy0 + uy1) / 2} | {ya + fr + 4.0 if ya < 0 else yb - fr - 4.0 for _, ya, yb in k["decks"]})
    for x in (ux / 2, W - ux / 2):
        for y in ys:
            if level < 2:
                _lathe(extra, x, y, [(fr, 0.0), (fr, fh + 1.0)], (8, 6)[level], STEEL)
            else:
                extra.box((x - fr, y - fr, 0.0), (x + fr, y + fr, fh + 1.0), mat=STEEL)
    return Lod(base, bevel_mm=1.0 if level == 0 else None, extra=extra)


def item_gondola(kind: str) -> Item:
    """Sheet 20: a slatwall back (horizontal slats, so the A8 hooks fit) between slotted steel uprights, a grey
    steel base deck whose front is the kick plate, levelling feet under the base. Shelves are separate (A11).
    Single / EndCap: the back on y = 0 (pivot: bottom-left rear corner), facing -Y. Double: the same back to back on
    a shared central upright, pivot on the left end of the centre line."""
    g = GONDOLA
    k = _gondola_dims(kind)
    W, ux, (uy0, uy1), (py0, py1) = k["W"], k["ux"], k["up_y"], k["panel_y"]
    zk, H = g["kick"], g["h"]
    zcs = _groove_centres(zk, H, g["grooves"], SLAT["pitch"])
    mounts = _gondola_mounts()
    sockets = [Socket("Seat", (0, 0, 0))]
    levels = []
    rails = []
    for side, ya, yb in k["decks"]:
        back = side == "B"
        rot = (0.0, 0.0, 180.0) if back else (0.0, 0.0, 0.0)
        name = "Deck" if not k["double"] else f"Deck{side}"
        yc = (ya + yb) / 2
        yfront = yb if back else ya
        xs = [W / 6, W / 2, 5 * W / 6]
        if back:
            xs = xs[::-1]
        comps = [(x, yc, zk) for x in xs]
        tags = [((x, yfront, (g["deck_z0"] + zk) / 2), rot) for x in xs]
        ls, lv = _level(name, (W / 2, yc, zk), W, g["deck_d"], H - zk, SHELF_ACCEPTS, comps, tags, rot,
                        {"note": "open to the top; fitted A11 shelves cut the clear height"})
        sockets += ls
        levels.append(lv)
        yface_up = uy1 if back else uy0
        yface_panel = py1 if back else py0
        xl = W - ux if back else ux
        rails.append({"kind": "groove", "side": side, "first_mm": [xl, yface_panel, round(zcs[0], 3)],
                      "rot_deg": list(rot), "pitch_mm": SLAT["pitch"], "count": len(zcs), "length_mm": W - 2 * ux,
                      "note": "left end of each groove seen from that side; hooks slide along the socket's +X"})
        rails.append({"kind": "mount", "side": side, "first_mm": [W / 2, yface_up, mounts[0]], "rot_deg": list(rot),
                      "pitch_mm": g["mount_pitch"], "count": len(mounts),
                      "note": "an A11 shelf's Seat goes here (its brackets hook the slots at x = %g and %g)"
                              % (ux / 2, W - ux / 2)})
        for j, z in enumerate(mounts):
            sockets.append(Socket(f"Mount_{side}_{j + 1:02d}", (W / 2, yface_up, z), rot))
        if not k["double"]:
            sockets += [Socket(f"Groove_{side}_{j + 1:02d}", (xl, yface_panel, zc), rot) for j, zc in enumerate(zcs)]
    sockets += [Socket("Snap_L", (0, 0, 0)), Socket("Snap_R", (W, 0, 0))]
    hulls = [((0.0, uy0, 0.0), (ux, uy1, H)), ((W - ux, uy0, 0.0), (W, uy1, H)), ((ux, py0, 0.0), (W - ux, py1, H))]
    for _, ya, yb in k["decks"]:
        hulls.append(((0.0, ya, 0.0), (W, yb, zk)))
    name = f"SM_CSK_Gondola_{kind}_1372"
    ymin = min(ya for _, ya, _ in k["decks"])
    ymax = max(max(yb for _, _, yb in k["decks"]), uy1)
    notes = ["Sheet 20: slotted uprights (rectangular slots on 25.4), slatwall back, grey steel base and kick plate, "
             "levelling feet. The A11 shelves hook into the slots (Mount_* sockets / the mount rails)."]
    if k["double"]:
        notes.append("Double: 73 sockets would exceed the 40 fixture limit, so the 32 grooves are published as rails "
                     "(first groove + pitch + count per side) instead of Groove_* sockets.")
    if kind == "EndCap":
        notes.append("End cap 610 wide from sheet 20 (the spec row gives only the 1219 section).")
    return Item(
        name=name, lods=[_gondola_lod(kind, lv) for lv in range(3)],
        materials=["M_CSK_Steel", "M_CSK_Slatwall", "M_CSK_MDF"], projections={}, sockets=sockets, hulls=hulls,
        budget=BUDGETS[name],
        data={"footprint_mm": [W, ymax - ymin, H], "pose": "upright",
              "pivot": ("end corner: bottom-left of the rear face" if not k["double"]
                        else "left end of the centre line, on the floor"),
              "accepts": list(SHELF_ACCEPTS), "levels": levels, "rails": rails,
              "reference": "sheet 20 (csk_gondola.png, notes in REFERENCE_LOG.md)", "notes": notes},
    )


# =========================================================================== A11 gondola shelf

def _gshelf_bracket(depth: float, level: int):
    s = GSHELF
    t, hb, ht = s["bracket"]
    zs = s["top_above_mount"]
    top = zs - s["pan"][1] + 0.5                     # 0.5 up into the pan's top sheet
    tip = -(depth - 20.0)
    pts = [(0.0, top), (tip, top), (tip, top - ht), (0.0, top - hb)]
    if level < 2:                                    # two hook tongues into the upright slots (sheet 20 slot detail)
        sw, sh, pitch, sd = GONDOLA["slot"]
        for zc in (-pitch, 0.0):
            pts += [(0.0, zc - sh / 2 + 1.0), (sd - 0.5, zc - sh / 2 + 1.0), (sd - 0.5, zc + 1.5), (0.0, zc + 1.5)]
    return pts


def _price_channel(depth: float):
    """The front price channel profile (n = offset into the shelf, z): sheet 20, a sloped face, 38 high."""
    s = GSHELF
    hgt, proud, fb, ft = s["lip"]
    zs = s["top_above_mount"]
    zt, zb = zs + proud, zs + proud - hgt
    return [(0.5, zb), (-fb, zb), (-ft, zt), (0.5, zt)]


def item_gondola_shelf(depth: float) -> Item:
    """Sheet 20: a flat steel shelf (a pan with turned-down flanges) on two end brackets that hook into the upright
    slots, with a 38 price channel on the front edge (a white / clear extrusion with a sloped face).
    Pivot = the upper hook slot's centre on the upright face, centred between the brackets (= a gondola Mount_*)."""
    s = GSHELF
    W = s["w"]
    fl, st = s["pan"]
    zs = s["top_above_mount"]
    t = s["bracket"][0]
    xb = W / 2 - GONDOLA["upright"][0] / 2
    STEEL, STRIP = 0, 1
    y0, y1 = -depth, -1.0
    lods = []
    for level in range(3):
        b = Builder()
        if level < 2:                                   # the pan: an inverted U (top sheet + front and back flanges)
            pan = [(y0, zs - fl), (y0, zs), (y1, zs), (y1, zs - fl), (y1 - st, zs - fl), (y1 - st, zs - st),
                   (y0 + st, zs - st), (y0 + st, zs - fl)]
        else:
            pan = [(y0, zs - fl), (y0, zs), (y1, zs), (y1, zs - fl)]
        _prism_x(b, _plain(pan, STEEL), -W / 2, W / 2, STEEL)
        for sx in (-1, 1):
            _prism_x(b, _plain(_gshelf_bracket(depth, level), STEEL), sx * xb - t / 2, sx * xb + t / 2, STEEL)
        ch = [(y0 + n, z) for n, z in _price_channel(depth)]       # n (into the shelf) -> y
        _prism_x(b, _plain(ch, STRIP), -W / 2, W / 2, STRIP)
        lods.append(Lod(b, bevel_mm=0.5 if level == 0 else None))
    hgt, proud, fb, ft = s["lip"]
    yc = (y0 + y1) / 2
    face_y = y0 - (fb + ft) / 2
    face_z = zs + proud - hgt / 2
    slope = math.degrees(math.atan2(fb - ft, hgt))
    comps = [(x, yc, zs) for x in (-W / 3, 0.0, W / 3)]
    tags = [((x, face_y, face_z), (-slope, 0.0, 0.0)) for x in (-W / 3, 0.0, W / 3)]
    lsocks, lv = _level("S1", (0.0, yc, zs), W, depth - 1.0, s["clear_h"], SHELF_ACCEPTS, comps, tags)
    name = f"SM_CSK_Gondola_Shelf_{int(depth)}"
    zlow = zs - s["pan"][1] + 0.5 - s["bracket"][1]
    return Item(
        name=name, lods=lods, materials=["M_CSK_Steel", "M_CSK_PriceStrip"], projections={},
        sockets=[Socket("Seat", (0, 0, 0))] + lsocks + [Socket("Mount_L", (-xb, 0, 0)), Socket("Mount_R", (xb, 0, 0))],
        hulls=[((-W / 2, y0 - fb, zlow), (W / 2, 0.0, zs))], budget=BUDGETS[name],
        data={"footprint_mm": [W, depth + fb, zs + proud - zlow], "pose": "hangs on gondola uprights",
              "pivot": "the upper hook slot's centre on the upright face, centred between the brackets",
              "accepts": list(SHELF_ACCEPTS), "levels": [lv],
              "mount": "seat on a gondola Mount_<Side>_NN socket; the brackets take the slots at the uprights' "
                       "centres (x = +-%g)" % xb,
              "reference": "sheet 20 (csk_gondola.png)"},
    )


# =========================================================================== A11 inside corner

def _corner_lod(level: int) -> Lod:
    g, c = GONDOLA, GCORNER
    S0 = c["size"]
    ux = g["upright"][0]
    STEEL, FACE_, CORE_, STRIP = 0, 1, 2, 3
    z0d, zk, H = g["deck_z0"], g["kick"], g["h"]
    Dd, Ds = g["deck_d"], c["shelf_d"]
    base = Builder()
    e = ux - 0.5                                    # the deck and shelves start 0.5 in front of the backs
    deck = [(e, -S0), (e + Dd, -S0), (e + Dd, -(e + Dd)), (S0, -(e + Dd)), (S0, -e), (e, -e)]
    base.prism(deck, z0d + 0.5, zk, mat=STEEL)
    extra = Builder()
    for zs in c["shelf_z"]:                         # the L shelves, one piece per level (sheet 20)
        L = [(e, -S0), (e + Ds, -S0), (e + Ds, -(e + Ds)), (S0, -(e + Ds)), (S0, -e), (e, -e)]
        base.prism(L, zs - c["slab"], zs, mat=STEEL)
        prof = [(n, z - GSHELF["top_above_mount"] + zs, STRIP) for n, z in _price_channel(Ds)]
        _sweep(base, prof, [(e + Ds, -S0), (e + Ds, -(e + Ds)), (S0, -(e + Ds))], STRIP)
        if level < 2:                               # end brackets on the two end uprights
            t, hb, ht = GSHELF["bracket"]
            top = zs - c["slab"] + 0.5
            br = [(0.0, top), (-(Ds - 20.0), top), (-(Ds - 20.0), top - ht), (0.0, top - hb)]
            xr = S0 - ux / 2
            _prism_x(base, _plain([(y - e, z) for y, z in br], STEEL), xr - t / 2, xr + t / 2, STEEL)
            yl = -S0 + ux / 2                       # along +Y the sweep's n is -X, so n = y - e gives x = e - y
            _sweep(base, _plain([(y - e, z) for y, z in br], STEEL), [(0.0, yl - t / 2), (0.0, yl + t / 2)], STEEL)
    for x0, y0 in ((0.0, -ux), (S0 - ux, -ux), (0.0, -S0)):          # corner post + two end uprights (bevelled)
        base.box((x0, y0, z0d), (x0 + ux, y0 + ux, H), mat=STEEL)
    zcs = _groove_centres(zk, H, g["grooves"], SLAT["pitch"])
    plevel = (0, 1, 3)[level]
    py0, py1 = -ux + 1.0, -ux + 1.0 + g["panel_t"]
    prof = [(y, z, (FACE_, CORE_)[m]) for y, z, m in _slat_profile(py0, py1, z0d + 0.5, H - 1.0, zcs, None, plevel)]
    _prism_x(extra, prof, ux - 0.5, S0 - ux + 0.5, CORE_, caps=(False, False))    # rear back, faces -Y
    prof_l = [(-y, z, m) for y, z, m in prof]                                        # left back, faces +X
    _sweep(extra, prof_l, [(0.0, -(ux - 0.5)), (0.0, -(S0 - ux + 0.5))], CORE_, caps=(False, False))
    fr, fh = g["foot"]
    for x, y in ((ux / 2, -ux / 2), (S0 - ux / 2, -ux / 2), (ux / 2, -S0 + ux / 2), (S0 - 20.0, -(e + Dd) + 20.0),
                 (e + Dd - 20.0, -(e + Dd) + 20.0), (e + Dd - 20.0, -S0 + 20.0)):
        if level < 2:
            _lathe(extra, x, y, [(fr, 0.0), (fr, fh + 1.0)], (8, 6)[level], STEEL)
        else:
            extra.box((x - fr, y - fr, 0.0), (x + fr, y + fr, fh + 1.0), mat=STEEL)
    return Lod(base, bevel_mm=0.8 if level == 0 else None, extra=extra)


def item_gondola_corner() -> Item:
    """Sheet 20: the inside corner, 610 x 610 x 1372: slatwall on both backs, an L-shaped base deck and 4 L-shaped
    shelves that run round the corner (one piece per level) with the price channel along both front edges.
    Pivot: the corner of the two walls (floor); the rear back runs along +X, the left back along -Y."""
    g, c = GONDOLA, GCORNER
    S0 = c["size"]
    ux = g["upright"][0]
    e = ux - 0.5
    zk, H = g["kick"], g["h"]
    Dd, Ds = g["deck_d"], c["shelf_d"]
    sockets = [Socket("Seat", (0, 0, 0))]
    levels = []
    hgt, proud, fb, ft = GSHELF["lip"]
    slope = math.degrees(math.atan2(fb - ft, hgt))
    lvls = [("Deck", zk, Dd)] + [(f"S{i + 1}", z, Ds) for i, z in enumerate(c["shelf_z"])]
    for i, (name, z, D) in enumerate(lvls):
        xa, ya = (e + S0) / 2, -(e + D / 2)       # the grid: the rear arm (the left arm's extension is compartment 01)
        comps = [((e + e + D) / 2, -(e + D + S0) / 2, z), ((e + e + D) / 2, -(e + D / 2), z), ((e + D + S0) / 2, ya, z)]
        if name == "Deck":
            tz, tr = (g["deck_z0"] + zk) / 2, 0.0
            tf = 0.0
        else:
            tz, tr = z + proud - hgt / 2, -slope
            tf = (fb + ft) / 2
        tags = [((e + D + tf, -(e + D + S0) / 2, tz), (tr, 0.0, 90.0)),
                ((e + D + 40.0, -(e + D + tf), tz), (tr, 0.0, 0.0)),
                (((e + D + S0) / 2, -(e + D + tf), tz), (tr, 0.0, 0.0))]
        # clear height: to the next shelf's price channel bottom (its lowest edge over this level), or the top
        nxt = lvls[i + 1][1] + proud - hgt if i + 1 < len(lvls) else H
        ls, lv = _level(name, (xa, ya, z), S0 - e, D, nxt - z, SHELF_ACCEPTS, comps, tags,
                        extra={"note": "L-shaped level: the grid is the rear arm; the left arm's extension "
                                       "(Compartment_%s_01) is compartment-only" % name})
        sockets += ls
        levels.append(lv)
    sockets += [Socket("Snap_L", (0.0, -S0, 0.0), (0.0, 0.0, 90.0)), Socket("Snap_R", (S0, 0.0, 0.0))]
    zcs = _groove_centres(zk, H, g["grooves"], SLAT["pitch"])
    rails = [{"kind": "groove", "side": "rear", "first_mm": [ux, -ux + 1.0, round(zcs[0], 3)], "rot_deg": [0, 0, 0],
              "pitch_mm": SLAT["pitch"], "count": len(zcs), "length_mm": S0 - 2 * ux},
             {"kind": "groove", "side": "left", "first_mm": [ux - 1.0, -(S0 - ux), round(zcs[0], 3)],
              "rot_deg": [0, 0, 90], "pitch_mm": SLAT["pitch"], "count": len(zcs), "length_mm": S0 - 2 * ux}]
    name = "SM_CSK_Gondola_Corner_1372"
    return Item(
        name=name, lods=[_corner_lod(lv) for lv in range(3)],
        materials=["M_CSK_Steel", "M_CSK_Slatwall", "M_CSK_MDF", "M_CSK_PriceStrip"], projections={},
        sockets=sockets,
        hulls=[((0.0, -ux, 0.0), (S0, 0.0, H)), ((0.0, -S0, 0.0), (ux, -ux, H)),
               ((e, -(e + Dd), 0.0), (S0, -e, zk)), ((e, -S0, 0.0), (e + Dd, -(e + Dd), zk))],
        budget=BUDGETS[name],
        data={"footprint_mm": [S0, S0, H], "pose": "upright, in an inside corner",
              "pivot": "the corner of the two walls, on the floor; Snap_R joins a Single's Snap_L along +X, "
                       "Snap_L a Single's Snap_R (that run turned +90 deg)",
              "accepts": list(SHELF_ACCEPTS), "levels": levels, "rails": rails,
              "reference": "sheet 20 (csk_gondola.png)",
              "notes": ["Fixed L shelves, so the corner's uprights are plain (no slots) and it has no Mount "
                        "sockets; the spec's Mount_L / Mount_R belong to the separate shelves.",
                        "4 hulls (spec): the two backs and the two arms of the base deck; the L shelves have none."]},
    )


# =========================================================================== A12 wire rack

def _rack_posts():
    r = RACK
    px, py = r["w"] / 2 - r["post_inset"], r["d"] / 2 - r["post_inset"]
    return [(sx * px, sy * py) for sy in (-1, 1) for sx in (-1, 1)], px, py


def _rack_decks():
    r = RACK
    return [r["deck_first"] + i * r["deck_pitch"] for i in range(r["decks"])]


def _zigzag(a: float, b_: float, n: int, zt: float, zb: float, along, start_low: bool = True):
    pts = []
    for i in range(n + 1):
        u = a + (b_ - a) * i / n
        low = (i % 2 == 0) == start_low
        pts.append(along(u, zb if low else zt))
    return pts


def _rack_lod(level: int) -> Lod:
    r = RACK
    CH, BLACK = 0, 1
    b = Builder()
    posts, px, py = _rack_posts()
    decks = _rack_decks()
    pr = r["post_r"]
    fr0, fr1, fh = r["foot"]
    cr0, cr1, chh = r["collar"]
    pitch, gd, gw = r["groove"]
    post_sides = (8, 8, 6)[level]
    for x, y in posts:
        _lathe(b, x, y, [(fr0, 0.0), (fr1, fh)], post_sides, BLACK)            # black levelling foot (sheet 21)
        prof = [(pr, fh - 1.0)]
        if level == 0:                                                        # ring grooves (sheet 21)
            zg = pitch
            while zg < r["h"] - 12.0:
                hidden = zg < fh + 6.0 or any(zt - chh - 2.0 < zg < zt + 4.0 for zt in decks)
                if not hidden:
                    prof += [(pr, zg - gw), (pr - gd, zg)]
                zg += pitch
        prof += [(pr, r["h"] - 1.0), (pr - 1.0, r["h"])]
        _lathe(b, x, y, prof, post_sides, CH, caps=(False, True))
    for zt in decks:
        zr = zt - r["rim_r"]                        # the top rim; the mat wires lie on it, flush with the deck top
        zbr = zr - r["truss"]                       # the bottom rim
        rim_s = (8, 6, 4)[level]
        wire_s = (4, 4, 3)[level]
        for z in (zr, zbr):                         # the two rim loops through the post centres (inside the collars)
            _tube(b, [(-px, -py, z), (px, -py, z), (px, py, z), (-px, py, z)], r["rim_r"], rim_s, CH, closed=True)
        nm = int((2 * px - 2 * cr0) // r["mat_pitch"]) + 1 if level < 2 else 17
        span = (nm - 1) * (r["mat_pitch"] if level < 2 else 2 * r["mat_pitch"])
        for i in range(nm):                         # mat wires, front to back
            x = -span / 2 + span * i / (nm - 1)
            _tube(b, [(x, -py, zt - r["wire_r"]), (x, py, zt - r["wire_r"])], r["wire_r"], wire_s, CH,
                  up=(0.0, 0.0, 1.0), phase=0.0)
        zig = r["zig"] * (1, 2, 4)[level]
        for sy in (-1, 1):                          # the truss zigzags (sheet 21), long sides
            a, b_ = -px + cr1, px - cr1
            n = max(2, int(round((b_ - a) / zig / 2)) * 2)
            _tube(b, _zigzag(a, b_, n, zr, zbr, lambda u, z: (u, sy * py, z)), r["wire_r"], wire_s, CH,
                  up=(0.0, 1.0, 0.0))
        for sx in (-1, 1):                          # short sides
            a, b_ = -py + cr1, py - cr1
            n = max(2, int(round((b_ - a) / zig / 2)) * 2)
            _tube(b, _zigzag(a, b_, n, zr, zbr, lambda u, z: (sx * px, u, z)), r["wire_r"], wire_s, CH,
                  up=(1.0, 0.0, 0.0))
        for x, y in posts:                          # the corner collars (tapered sleeves)
            _lathe(b, x, y, [(cr0, zt - chh + 2.0), (cr1, zt + 2.0)], (8, 8, 4)[level], CH)
    return Lod(b)


def item_rack_wire() -> Item:
    """Sheet 21: a chrome wire rack, 914 x 457 x 1829, 4 round posts with ring grooves on 25.4, 5 wire decks
    (top + 4) with truss edges (a zigzag rod between a top and a bottom rim) and front-to-back mat wires, tapered
    corner collars, black levelling feet. Pivot: bottom centre."""
    r = RACK
    W, D, H = r["w"], r["d"], r["h"]
    posts, px, py = _rack_posts()
    cr0 = r["collar"][0]
    decks = _rack_decks()
    depth = r["rim_r"] + r["truss"] + r["rim_r"]
    iw, idp = 2 * (px - cr0), 2 * (py - cr0)
    sockets = [Socket("Seat", (0, 0, 0))]
    levels = []
    hulls = []
    for i, zt in enumerate(decks):
        name = f"L{i + 1}"
        clear = r["deck_pitch"] - depth
        comps = [(-iw / 4, 0.0, zt), (iw / 4, 0.0, zt)]
        tags = [((-iw / 4, -py - r["rim_r"], zt - r["rim_r"]), (0.0, 0.0, 0.0)),
                ((iw / 4, -py - r["rim_r"], zt - r["rim_r"]), (0.0, 0.0, 0.0))]
        ls, lv = _level(name, (0.0, 0.0, zt), iw, idp, clear, SHELF_ACCEPTS, comps, tags)
        sockets += ls
        levels.append(lv)
        hulls.append(((-W / 2, -D / 2, zt - depth), (W / 2, D / 2, zt)))
    sockets += [Socket("Snap_L", (-W / 2, 0, 0)), Socket("Snap_R", (W / 2, 0, 0))]
    name = "SM_CSK_Rack_Wire_914"
    return Item(
        name=name, lods=[_rack_lod(k) for k in range(3)], materials=["M_CSK_Chrome", "M_CSK_Base"], projections={},
        sockets=sockets, hulls=hulls, budget=BUDGETS[name],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(SHELF_ACCEPTS), "levels": levels,
              "reference": "sheet 21 (csk_wire_rack_box_shelf.png)",
              "notes": ["Sheet 21 shows 5 decks (the spec's 4 was E): levels L1..L5.",
                        "Budget 7000 -> %d: the fifth deck and the sheet's ring-grooved posts (60 visible grooves a "
                        "post at 25.4, about 7.7k tris) are real geometry." % r["budget"],
                        "Hulls: one per deck (spec: 5); the posts have none."]},
    )


# =========================================================================== A13 box tier shelf

def _tier_frame(k: int):
    """Tier k (2..4, the shelves): front-top point O (y, z), the plank's depth axis u and normal w (tilted back)."""
    t = TIER
    a = math.radians(t["tilt"])
    yf = -t["d"] / 2 + t["step"] * (k - 1)
    zf = t["deck_z"] + t["pitch"] * (k - 1)
    u = (math.cos(a), -math.sin(a))                # toward the back and down: the shelf tilts back
    w = (math.sin(a), math.cos(a))
    L = (t["d"] / 2 - yf) / math.cos(a)
    return (yf, zf), u, w, L


def _tier_pt(O, u, w, uu, ww):
    return (O[0] + u[0] * uu + w[0] * ww, O[1] + u[1] * uu + w[1] * ww)


def _tier_lod(level: int) -> Lod:
    t = TIER
    W, D, H = t["w"], t["d"], t["h"]
    OAK, BLACK, WHITE = 0, 1, 2
    st, bd = t["side_t"], t["board"]
    xi = W / 2 - st                                   # the side panels' inner faces
    b = Builder()
    side = [(-D / 2, 0.0), (D / 2, 0.0), (D / 2, H), (D / 2 - t["top_d"], H), (-D / 2, t["deck_z"])]
    for sx in (-1, 1):                                 # tapered oak side panels (sheet 21)
        x0 = sx * (W / 2) if sx < 0 else xi
        _prism_x(b, _plain(side, OAK), x0, x0 + st, OAK)
    kh, kr = t["kick"]
    zd = t["deck_z"]
    if level < 2:
        b.box((-xi - 0.5, -D / 2 + kr, 0.0), (xi + 0.5, D / 2 - kr, kh + 0.5), mat=BLACK)          # recessed kick
        b.box((-xi - 0.5, -D / 2 + 2.0, kh), (xi + 0.5, D / 2 - 0.5, zd - bd + 0.5), mat=OAK)   # oak cabinet
    else:
        b.box((-xi - 0.5, -D / 2 + 2.0, 0.0), (xi + 0.5, D / 2 - 0.5, zd - bd + 0.5), mat=OAK)      # no kick
    b.box((-xi - 0.5, -D / 2, zd - bd), (xi + 0.5, D / 2, zd), mat=WHITE)                      # the white deck
    lt, lh = t["lip"]
    for k in (2, 3, 4):                                # 3 white shelves tilted back 10 deg, 25 front lip
        O, u, w, L = _tier_frame(k)
        uv = [(0.0, -bd), (L, -bd), (L, 0.0), (lt, 0.0), (lt, lh), (0.0, lh)] if level < 2 else \
            [(0.0, -bd), (L, -bd), (L, 0.0), (0.0, lh)]
        prof = _plain([_tier_pt(O, u, w, a, c) for a, c in uv], WHITE)
        _prism_x(b, prof, -xi - 0.5, xi + 0.5, WHITE)
    return Lod(b, bevel_mm=1.0 if level == 0 else None)


def item_box_tier() -> Item:
    """Sheet 21: tapered light-oak side panels (full depth at the base, narrow at the top), a base cabinet with an oak
    front over a recessed black kick, a white deck on it (tier 1, 252), then 3 white shelves 280 apart, each tilted
    back 10 deg with a 25 front lip (tiers 2-4). The shelf fronts step back 76.2 a tier along the sides' sloped
    front edge. Pivot: bottom centre."""
    t = TIER
    W, D, H = t["w"], t["d"], t["h"]
    st, bd = t["side_t"], t["board"]
    xi = W / 2 - st
    lt, lh = t["lip"]
    a = math.radians(t["tilt"])
    sockets = [Socket("Seat", (0, 0, 0))]
    levels = []
    xs = [-2 * xi / 3 + 2 * xi / 3 * i for i in range(3)]
    hulls = [((-W / 2, -D / 2, 0.0), (-xi, D / 2, H)), ((xi, -D / 2, 0.0), (W / 2, D / 2, H)),
             ((-xi, -D / 2, 0.0), (xi, D / 2, t["deck_z"]))]
    shelf_hull = {}
    for k in (2, 3, 4):
        O, u, w, L = _tier_frame(k)
        mid = _tier_pt(O, u, w, (lt + L) / 2, 0.0)
        low = _tier_pt(O, u, w, L, -bd)
        front = _tier_pt(O, u, w, 0.0, -bd)
        shelf_hull[k] = ((-xi, front[0], low[1]), (xi, D / 2, mid[1]))
        hulls.append(shelf_hull[k])
    for k in (1, 2, 3, 4):
        name = f"T{k}"
        if k == 1:
            loc = (0.0, 0.0, t["deck_z"])
            rot = (0.0, 0.0, 0.0)
            depth = D
            clear = shelf_hull[2][0][2] - t["deck_z"]
            tags = [((x, -D / 2, t["deck_z"] - bd / 2), rot) for x in xs]
            comps = [(x, 0.0, t["deck_z"]) for x in xs]
            extra = {"note": "flat deck; clear height to the lowest point of the tier 2 shelf"}
        else:
            O, u, w, L = _tier_frame(k)
            mid = _tier_pt(O, u, w, (lt + L) / 2, 0.0)
            loc = (0.0, mid[0], mid[1])
            rot = (-t["tilt"], 0.0, 0.0)
            depth = L - lt
            clear = (t["step"] * math.sin(a) + t["pitch"] * math.cos(a)) - bd
            face = _tier_pt(O, u, w, 0.0, lh / 2)
            tags = [((x, face[0], face[1]), rot) for x in xs]
            comps = [(x, mid[0], mid[1]) for x in xs]
            extra = {"tilt_deg": t["tilt"], "tilt_axis": "X",
                     "note": "tilted level: the grid lies in the Level socket's frame (rotated -10 deg about X, "
                             "the shelf tilts back); interior depth and clear height are measured in that frame"}
        ls, lv = _level(name, loc, 2 * xi, depth, clear, TIER_ACCEPTS, comps, tags, rot, extra)
        sockets += ls
        levels.append(lv)
    sockets += [Socket("Snap_L", (-W / 2, 0, 0)), Socket("Snap_R", (W / 2, 0, 0))]
    name = "SM_CSK_Shelf_BoxTier_1219"
    return Item(
        name=name, lods=[_tier_lod(k) for k in range(3)], materials=["M_CSK_Oak", "M_CSK_Base", "M_CSK_Laminate"],
        projections={}, sockets=sockets, hulls=hulls, budget=BUDGETS[name],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(TIER_ACCEPTS) + ["Retail"], "levels": levels,
              "reference": "sheet 21 (csk_wire_rack_box_shelf.png)",
              "notes": ["Sheet 21: tiers 280 apart starting at 252: deck 252, shelves 532 / 812 / 1092 (at the lip's "
                        "foot), sides to 1372 (= 252 + 4 x 280).",
                        "Retail is accepted per item (no fixed grid).",
                        "Hulls: 2 sides, the base, and one box per shelf up to the plank's mid-depth top (a flat "
                        "stand-in for the 10 deg plank; hull boxes are axis-aligned)."]},
    )


# =========================================================================== registry

ITEMS = {
    "a_shelving_slatwall_1000": lambda: item_slatwall(1000.0),
    "a_shelving_slatwall_2000": lambda: item_slatwall(2000.0),
    "a_shelving_hook_102": lambda: item_hook(102.0),
    "a_shelving_hook_203": lambda: item_hook(203.0),
    "a_shelving_hook_305": lambda: item_hook(305.0),
    "a_shelving_shelf_slat": item_shelf_slat,
    "a_shelving_gondola_single": lambda: item_gondola("Single"),
    "a_shelving_gondola_double": lambda: item_gondola("Double"),
    "a_shelving_gondola_endcap": lambda: item_gondola("EndCap"),
    "a_shelving_gondola_shelf_305": lambda: item_gondola_shelf(305.0),
    "a_shelving_gondola_shelf_406": lambda: item_gondola_shelf(406.0),
    "a_shelving_gondola_corner": item_gondola_corner,
    "a_shelving_rack_wire": item_rack_wire,
    "a_shelving_box_tier": item_box_tier,
}
