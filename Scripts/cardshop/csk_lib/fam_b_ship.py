"""Card Shop Kit family b_ship: the distributor carton, the delivery boxes and the hanging blister
(CARDSHOP_KIT_SPEC.md 3.B rows B4, B5, B6; P3-P5).

    B4 SM_CSK_Carton_Box6_{Closed,Open,Flat}              reference sheet 11 (1) (csk_cartons.png)
    B5 SM_CSK_Box_Ship_{S,M,L}_{Closed,Open} + _Flat       reference sheet 11 (2)
    B6 SM_CSK_Blister_Pack                                 reference sheet 12 (1) (csk_blister_retail.png)

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice. "sheet N" =
the value or form is read off that reference sheet (the picture wins over E numbers; M numbers win over the picture).
Millimetres; Seat frame: +X right, +Y away from the customer, +Z up.

Cartons are regular slotted cartons (RSC), 4 mm corrugated board:
* Closed: the taped block. The tape is a thin raised strip along the top seam and down both ends, following the
  folded (bevelled) edge; a crisp line across each end marks the top flap joint (sheet 11 closed views).
* Open: the walls, floor and four real top flaps, each a folded board rising from its fold line with a real bend
  (sheet 11 open views: back flap up, end flaps splayed, front flap folded out past level).
* Flat: knocked down for trash: the tube folded flat, two board layers (8 mm), the flap slots and the fold lines as
  real geometry; the two outer edges are the 180-degree folds (rounded).
The blister is lying on its back (card down, bubble up; the header with the euro slot toward +Y), like a pack.

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import R_BACK, R_FRONT, R_LABEL, Item, Lod, Socket, _face_out, _planar, inset, solve_grid
from .shapes import Builder, rounded_rect

# =========================================================================== numbers

CARTON = dict(                 # B4, sheet 11 (1)
    L=492.0, W=152.0, H=137.0,  # D (spec: inner 484 x 144 x 129 = 6 x 80 + 4, 140 + 4, 125 + 4; board 4 a side)
    bd=4.0,                    # E (spec)
    boxes=6, box_pitch=80.0,   # D: 6 BoxS standing in a row, turned 90 deg (sheet 11 open view)
    tape_w=36.0,               # sheet 11 closed view reads 37 (a 36 mm tape; E would be 48)
    tab=45.0,                  # sheet 11: the tape runs 45 down each end
    label=(95.0, 75.0, 31.0),  # sheet 11: blank label on the -X end, W (along Y) x H, bottom edge z; centred on Y
    label_t=0.1,               # E: the label stands 0.1 proud; the tape tab lies over its top (sheet 11 close-up)
)

SHIP = {                       # B5, sheet 11 (2): outer L x W x H, all E (spec); inner = outer - 8 (E)
    "S": (305.0, 229.0, 102.0),
    "M": (406.0, 305.0, 254.0),
    "L": (610.0, 406.0, 406.0),
}
SHIP_BD = 4.0                  # E (spec: inner = outer - 8)
SHIP_TAPE_W = 48.0             # E: 48 mm tape (sheet 11 draws 40-78 by size, inconsistently)
SHIP_TAB = 0.88                # sheet 11: the tape runs down each end to ~10% of H above the floor (reads 0.85-0.9)
SHIP_FLAT = "M"                # the one _Flat mesh is the M box knocked down (D 711 x 559; spec E 700 x 450)

RSC = dict(                    # shared carton construction
    fold_r=1.5,                # E: LOD0 bevel on the folded edges
    tape_t=0.2,                # E: the tape stands 0.2 proud (lead: thin raised strips)
    sink=0.5,                  # guide: add-on parts sink 0.5 into the board (no touching faces)
    joint=(0.8, 0.6),          # sheet 11 closed views: a line across each end at the top flap joint (groove H x depth)
    flap_t=3.8,                # D: board 4 less 0.2, so a flap root sits 0.1 inside the wall faces
    flap_r=2.2,                # E: fold centreline radius (inner radius 0.3)
    flap_root=4.0,             # E: a flap's root runs 4 down inside its wall (hidden)
    end_gap=1.0,               # E: an end flap stops 1 short of the long walls
    slot=8.0,                  # sheet 11 flats draw the flap slots ~8-9 wide (E, RSC slot centred on the score); the
                               # flat's half slot at each fold = the fold radius (board 4), so the edges line up
    pose=dict(back=15.0, front=100.0, ends=45.0),   # sheet 11 open views (all four): deg outward from vertical
    score=(1.2, 0.6),          # flat: V crease at every fold line, width x depth (E; sheet 11 draws the fold lines)
    fold_segs=3,               # flat: segments of the 180-degree fold at each outer edge (half round, r = board 4)
)

BLISTER = dict(                # B6, sheet 12 (1)
    w=180.0, h=250.0,          # E (spec; no source)
    t=20.0,                    # E (spec) overall; sheet 12 side view: a bubble about 20 deep (spec bubble 14: E)
    card_t=0.6,                # E: blister board
    card_r=4.0,                # sheet 12: corner R 4.2
    slot=(38.3, 8.6, 19.5),    # sheet 12 euro slot: length x height, centre below the top edge (spec E 30 x 10)
    peak_r=6.0,                # sheet 12: the peak is a half round r 6 on the slot's top edge (reads 5.7 high)
    film=0.4,                  # E: PET wall
    cup=(78.0, 136.0, 6.0),    # one cup per pack: base W x H, corner R. Sheet 12 reads the dome 159 wide over both
                               # cups; the height is the pack (M 117) + 9.5 a side (the sheet's packs are drawn 142)
    web=1.0,                   # sheet 12: the thin divider line between the two cups
    flange=8.0,                # sheet 12: flange 8 round the cups (174 wide; the card is 180)
    flange_r=8.0,              # E
    bubble_cy=-25.3,           # sheet 12: the bubble's centre 150.3 below the card's top edge. The sheet's bubble is
                               # taller (flange 174) because its packs are drawn 142 long; ours holds the M 117 pack,
                               # so it is centred where the sheet's is (header 74, bottom margin 24; sheet 64 / 13)
    draft=3.0,                 # E: thermoform draft, deg (sheet 12 side view: near-vertical walls)
    top_c=3.0,                 # E: 45-degree chamfer round the top face (sheet 12: softly rounded top edges)
    sink=0.2,                  # the flange's underside sits 0.2 inside the card (no touching faces)
)

# LOD0 budgets: the spec's Tris column (E). Raised (logged in the report):
#   Carton_Box6_Flat 100 -> 300: the knocked-down flat carries its slots, two rounded folds and 6 fold-line creases as
#     real geometry (sheet 11 draws every fold line); Box_Ship_Flat uses the same construction (spec 300-700).
#   Blister_Pack 300 -> 500: the twin-cup PET bubble is a closed thin shell (outer + inner skin, flange) and the euro
#     slot with its peak is a real hole through the card.
BUDGETS = {
    "SM_CSK_Carton_Box6_Closed": 500, "SM_CSK_Carton_Box6_Open": 800, "SM_CSK_Carton_Box6_Flat": 300,
    "SM_CSK_Box_Ship_Closed": 300, "SM_CSK_Box_Ship_Open": 700, "SM_CSK_Box_Ship_Flat": 300,
    "SM_CSK_Blister_Pack": 500,
}

# placement classes (spec 4.2 "Carton / BoxShip: per size, + 20"). Codes are CamelCase with no underscores, so the
# per-size delivery box classes are BoxShipS / BoxShipM / BoxShipL. Footprint = render bounds (tape and label proud).
CLASSES = {
    "Carton": S.ItemClass("Carton", (492.4, 152.0, 137.2), (512.0, 172.0)),
    **{f"BoxShip{k}": S.ItemClass(f"BoxShip{k}", (L + 0.4, W, H + 0.2), (L + 20.0, W + 20.0))
       for k, (L, W, H) in SHIP.items()},
}

SHIP_CONTENTS = ("Pack", "BoxS", "Retail", "Slab")   # spec B5: the Contents grids (classes registered at build time)
CB, TAPE, LAB = 0, 1, 2                                 # carton material slots


# =========================================================================== shape helpers

def _box(b: Builder, mn, mx, mat: int, **kw) -> None:
    lo = tuple(min(mn[i], mx[i]) for i in range(3))
    hi = tuple(max(mn[i], mx[i]) for i in range(3))
    b.box(lo, hi, mat=mat, **kw)


def _area2(pts) -> float:
    return sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, list(pts[1:]) + [pts[0]]))


def _prism_ax(b: Builder, outline, axis: str, a0: float, a1: float, mat: int, region: int = 0) -> None:
    """A closed prism along X (``outline`` in (y, z)) or Y (``outline`` in (x, z)), any winding."""
    pts = list(outline) if _area2(outline) > 0 else list(reversed(outline))

    def P(u, v, a):
        return (a, u, v) if axis == "x" else (u, a, v)
    A = [b.v(*P(u, v, a0)) for u, v in pts]
    C = [b.v(*P(u, v, a1)) for u, v in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        du, dv = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
        _face_out(b, [A[i], A[j], C[j], C[i]], P(dv, -du, 0.0), mat, region)
    ax = (1.0, 0.0, 0.0) if axis == "x" else (0.0, 1.0, 0.0)
    b.fill([C], mat, region, ax)
    b.fill([A], mat, region, tuple(-c for c in ax))


def _bent_strip(path: Sequence[Tuple[float, float]], t: float, r_c: float, segs: int) -> List[Tuple[float, float]]:
    """The 2D outline of a bent sheet: centreline ``path`` (straight runs), every interior corner rounded with
    centreline radius ``r_c`` (tangent arcs), offset +-t/2 along the normals. (Copied from fam_a_display.)"""
    P = [tuple(p) for p in path]
    pts, nls = [], []

    def unit(a, c):
        dy, dz = c[0] - a[0], c[1] - a[1]
        ln = math.hypot(dy, dz)
        return dy / ln, dz / ln

    d0 = unit(P[0], P[1])
    pts.append(P[0])
    nls.append((-d0[1], d0[0]))
    for i in range(1, len(P) - 1):
        d1, d2 = unit(P[i - 1], P[i]), unit(P[i], P[i + 1])
        cross = d1[0] * d2[1] - d1[1] * d2[0]
        dot = max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1]))
        phi = math.acos(dot)
        s = 1.0 if cross > 0 else -1.0
        lt = r_c * math.tan(phi / 2)
        A = (P[i][0] - d1[0] * lt, P[i][1] - d1[1] * lt)
        n1 = (-d1[1] * s, d1[0] * s)
        C = (A[0] + n1[0] * r_c, A[1] + n1[1] * r_c)
        a0 = math.atan2(A[1] - C[1], A[0] - C[0])
        for k in range(segs + 1):
            a = a0 + s * phi * k / segs
            p = (C[0] + r_c * math.cos(a), C[1] + r_c * math.sin(a))
            radial = ((p[0] - C[0]) / r_c, (p[1] - C[1]) / r_c)
            nl = (-radial[0], -radial[1]) if s > 0 else radial
            pts.append(p)
            nls.append(nl)
    dn = unit(P[-2], P[-1])
    pts.append(P[-1])
    nls.append((-dn[1], dn[0]))
    h = t / 2
    left = [(p[0] + n[0] * h, p[1] + n[1] * h) for p, n in zip(pts, nls)]
    right = [(p[0] - n[0] * h, p[1] - n[1] * h) for p, n in zip(pts, nls)]
    return left + list(reversed(right))


def _ring_strip(b: Builder, lo: List[int], hi: List[int], centre: Tuple[float, float], sign: float, mat: int,
                up: float = 0.0) -> None:
    """Quads between two equal-count rings; ``sign`` +1 faces away from ``centre`` (an outer skin), -1 toward it."""
    n = len(lo)
    for i in range(n):
        j = (i + 1) % n
        ids = [lo[i], lo[j], hi[j], hi[i]]
        mx = sum(b.verts[k][0] for k in ids) / 4 - centre[0]
        my = sum(b.verts[k][1] for k in ids) / 4 - centre[1]
        _face_out(b, ids, (sign * mx, sign * my, up), mat)


# =========================================================================== cartons (B4, B5)

def _tape(b: Builder, L: float, W: float, H: float, tw: float, tab: float, chamfer: float, mat: int) -> None:
    """The tape: one strip along the top seam and down both ends (sheet 11), 0.2 proud, its inside sunk 0.5 in the
    board; it follows the folded (bevelled) top edges, so no gap shows under it."""
    tp, si = RSC["tape_t"], RSC["sink"]
    zb = H - tab
    outer = [(-L / 2 - tp, zb)]
    if chamfer > 0:
        outer += [(-L / 2 - tp, H - chamfer), (-L / 2 + chamfer, H + tp), (L / 2 - chamfer, H + tp),
                  (L / 2 + tp, H - chamfer)]
    else:
        outer += [(-L / 2 - tp, H + tp), (L / 2 + tp, H + tp)]
    outer.append((L / 2 + tp, zb))
    if chamfer > 0:                      # the sunk inside follows the bevel too (stays inside the board)
        inner = [(L / 2 - si, zb), (L / 2 - si, H - chamfer), (L / 2 - chamfer, H - si),
                 (-L / 2 + chamfer, H - si), (-L / 2 + si, H - chamfer), (-L / 2 + si, zb)]
    else:
        inner = [(L / 2 - si, zb), (L / 2 - si, H - si), (-L / 2 + si, H - si), (-L / 2 + si, zb)]
    _prism_ax(b, outer + inner, "y", -tw / 2, tw / 2, mat)


def _label_proj(L: float, lw: float, lh: float, lz0: float):
    """The -X end label onto the label tile (0, 1): seen from outside, +U runs toward -Y."""
    return lambda x, y, z: (inset((lw / 2 - y) / lw), 1.0 + inset((z - lz0) / lh))


def _label(b: Builder, L: float, mat: int) -> None:
    lw, lh, lz0 = CARTON["label"]
    lt = CARTON["label_t"]
    _box(b, (-L / 2 - lt, -lw / 2, lz0), (-L / 2 + 0.4, lw / 2, lz0 + lh), mat, regions={"nx": R_LABEL})


def _rsc_closed(L: float, W: float, H: float, bd: float, tw: float, tab: float, label: bool, level: int) -> Lod:
    """Sheet 11 closed: the block with folded (bevelled) edges, a crisp joint line across each end at the top flap
    joint, the tape along the top seam and down both ends, and (B4) the blank label on the -X end."""
    b = Builder()
    b.box((-L / 2, -W / 2, 0.0), (L / 2, W / 2, H), mat=CB)
    ops = []
    if level == 0:
        gh, gd = RSC["joint"]
        zj = H - bd
        for sx in (-1, 1):
            g = Builder()
            _box(g, (sx * (L / 2 - gd), -W / 2 - 1.0, zj - gh / 2), (sx * (L / 2 + 1.0), W / 2 + 1.0, zj + gh / 2), CB)
            ops.append(("DIFFERENCE", g))
    ex = Builder()
    if level < 2:
        _tape(ex, L, W, H, tw, tab, RSC["fold_r"] if level == 0 else 0.0, TAPE)
    else:                                                   # far: the top strip only
        tp, si = RSC["tape_t"], RSC["sink"]
        _box(ex, (-L / 2 - tp, -tw / 2, H - si), (L / 2 + tp, tw / 2, H + tp), TAPE)
    if label:
        _label(ex, L, LAB)
    return Lod(b, bevel_mm=RSC["fold_r"] if level == 0 else None, ops=ops, bevel_first=True, extra=ex)


def _open_shell(b: Builder, L: float, W: float, Hw: float, bd: float) -> None:
    """The open carton body: outer walls and bottom, the board rim, inner walls and floor (one closed shell)."""
    x0, x1, y0, y1 = -L / 2, L / 2, -W / 2, W / 2
    o = [b.v(x0, y0, 0), b.v(x1, y0, 0), b.v(x1, y1, 0), b.v(x0, y1, 0),
         b.v(x0, y0, Hw), b.v(x1, y0, Hw), b.v(x1, y1, Hw), b.v(x0, y1, Hw)]
    it = [b.v(x0 + bd, y0 + bd, Hw), b.v(x1 - bd, y0 + bd, Hw), b.v(x1 - bd, y1 - bd, Hw), b.v(x0 + bd, y1 - bd, Hw)]
    ib = [b.v(x0 + bd, y0 + bd, bd), b.v(x1 - bd, y0 + bd, bd), b.v(x1 - bd, y1 - bd, bd), b.v(x0 + bd, y1 - bd, bd)]
    _face_out(b, [o[0], o[1], o[2], o[3]], (0, 0, -1), CB)
    sides = ((0, 1, (0, -1, 0)), (1, 2, (1, 0, 0)), (2, 3, (0, 1, 0)), (3, 0, (-1, 0, 0)))
    for a, c, n in sides:
        _face_out(b, [o[a], o[c], o[c + 4], o[a + 4]], n, CB)                   # outer wall
        _face_out(b, [o[a + 4], o[c + 4], it[c], it[a]], (0, 0, 1), CB)          # rim
        _face_out(b, [it[a], it[c], ib[c], ib[a]], tuple(-v for v in n), CB)     # inner wall
    _face_out(b, [ib[0], ib[1], ib[2], ib[3]], (0, 0, 1), CB)                     # inner floor


def _flap_section(c: float, Hw: float, out: float, phi: float, depth: float, level: int):
    """A top flap's section across its fold: (u, z) with u the wall-normal coordinate. ``c`` the wall's centre line,
    ``out`` +1 / -1 the outward direction, ``phi`` degrees outward from vertical, ``depth`` fold to free edge."""
    a = math.radians(phi)
    d = (out * math.sin(a), math.cos(a))
    p1 = (c, Hw)
    p2 = (c + d[0] * depth, Hw + d[1] * depth)
    t = RSC["flap_t"]
    if level == 2:                                          # far: a plain board from the fold
        nx, nz = -d[1], d[0]
        p0 = (c - d[0] * 1.0, Hw - d[1] * 1.0)
        return [(p0[0] + nx * t / 2, p0[1] + nz * t / 2), (p2[0] + nx * t / 2, p2[1] + nz * t / 2),
                (p2[0] - nx * t / 2, p2[1] - nz * t / 2), (p0[0] - nx * t / 2, p0[1] - nz * t / 2)]
    p0 = (c, Hw - RSC["flap_root"])
    return _bent_strip([p0, p1, p2], t, RSC["flap_r"], (3, 1)[level])


def _rsc_flaps(b: Builder, L: float, W: float, Hw: float, bd: float, level: int) -> None:
    """Sheet 11 open views: four real top flaps, W/2 deep (they meet at the centre when closed), each bent at its
    fold line: the back flap up (leaning back), the end flaps splayed out, the front flap folded out past level."""
    pose, hs = RSC["pose"], RSC["slot"] / 2
    depth = W / 2
    for sy, phi in ((-1, pose["front"]), (1, pose["back"])):          # long flaps: prisms along X
        sec = _flap_section(sy * (W / 2 - bd / 2), Hw, sy, phi, depth, level)
        _prism_ax(b, sec, "x", -L / 2 + hs, L / 2 - hs, CB)
    ye = W / 2 - bd - RSC["end_gap"]
    for sx in (-1, 1):                                                  # end flaps: prisms along Y
        sec = _flap_section(sx * (L / 2 - bd / 2), Hw, sx, pose["ends"], depth, level)
        _prism_ax(b, sec, "y", -ye, ye, CB)


def _rsc_open(L: float, W: float, H: float, bd: float, label: bool, level: int) -> Lod:
    Hw = H - bd                          # the fold line: the closed flaps lie from Hw to H
    b = Builder()
    _open_shell(b, L, W, Hw, bd)
    ex = Builder()
    _rsc_flaps(ex, L, W, Hw, bd, level)
    if label:
        _label(ex, L, 1)                 # the open carton has no tape slot: Label is material 1
    return Lod(b, bevel_mm=RSC["fold_r"] if level == 0 else None, extra=ex)


def _open_hulls(L: float, W: float, H: float, bd: float):
    """Spec: 5 hulls (floor + 4 walls); the flaps have no collision."""
    Hw = H - bd
    return [((-L / 2, -W / 2, 0.0), (L / 2, W / 2, bd)),
            ((-L / 2, -W / 2, bd), (L / 2, -W / 2 + bd, Hw)), ((-L / 2, W / 2 - bd, bd), (L / 2, W / 2, Hw)),
            ((-L / 2, -W / 2 + bd, bd), (-L / 2 + bd, W / 2 - bd, Hw)),
            ((L / 2 - bd, -W / 2 + bd, bd), (L / 2, W / 2 - bd, Hw))]


def _flat_dims(L: float, W: float, H: float, bd: float):
    """Knocked down (sheet 11 notes, decided 2026-09-29): (L + W) x (H + W) x 2 boards (D)."""
    return L + W, H + W, 2 * bd


def _v_groove(axis: str, c: float, a0: float, a1: float, z_face: float, down: bool) -> Builder:
    """A V crease cutter: ``score`` wide at the face, ``score`` deep, running along ``axis`` at u = c."""
    w, d = RSC["score"]
    k = 1.0 + 1.0 / d                    # the cutter rises 1 above the face; its width there keeps w at the face
    sgn = -1.0 if down else 1.0          # down: the groove is in the top face, cutting downward
    tip = z_face + sgn * d
    top = z_face - sgn * 1.0
    g = Builder()
    _prism_ax(g, [(c - w / 2 * k, top), (c + w / 2 * k, top), (c, tip)], axis, a0, a1, CB)
    return g


def _rsc_flat(L: float, W: float, H: float, bd: float, level: int) -> Lod:
    """The knocked-down carton (sheet 11): the body band with a half-round 180-degree fold at each outer edge, the
    top and bottom flap rows (unioned on), the flap slots (top layer at the L|W panel score, bottom layer mirrored;
    half slots at the folds), and V creases on every fold line of both faces."""
    Lf, Wf, T = _flat_dims(L, W, H, bd)
    hs = RSC["slot"] / 2
    xs = -Lf / 2 + L                    # the top layer's L | W panel score; the bottom layer's is at -xs
    if level == 2:                      # far: the notched outline, one prism
        b = Builder()
        pts = [(-Lf / 2 + hs, -Wf / 2), (Lf / 2 - hs, -Wf / 2), (Lf / 2 - hs, -H / 2), (Lf / 2, -H / 2),
               (Lf / 2, H / 2), (Lf / 2 - hs, H / 2), (Lf / 2 - hs, Wf / 2), (-Lf / 2 + hs, Wf / 2),
               (-Lf / 2 + hs, H / 2), (-Lf / 2, H / 2), (-Lf / 2, -H / 2), (-Lf / 2 + hs, -H / 2)]
        b.prism(pts, 0.0, T, mat=CB)
        return Lod(b)
    r = T / 2
    n = RSC["fold_segs"] if level == 0 else 2
    prof = [(Lf / 2 - r + r * math.cos(math.pi * (-0.5 + k / n)), r + r * math.sin(math.pi * (-0.5 + k / n)))
            for k in range(n + 1)]
    prof += [(-Lf / 2 + r + r * math.cos(math.pi * (0.5 + k / n)), r + r * math.sin(math.pi * (0.5 + k / n)))
             for k in range(n + 1)]
    b = Builder()
    _prism_ax(b, prof, "y", -H / 2, H / 2, CB)
    ops = []
    for sy in (-1, 1):                                     # flap rows, 1 into the band (exact union)
        f = Builder()
        _box(f, (-Lf / 2 + hs, sy * (H / 2 - 1.0), 0.0), (Lf / 2 - hs, sy * Wf / 2, T), CB)
        ops.append(("UNION", f))
    for sx, z0, z1 in ((1, bd, T + 1.0), (-1, -1.0, bd)):   # slots: top layer at +xs, bottom layer at -xs
        for sy in (-1, 1):
            s = Builder()
            _box(s, (sx * xs - hs, sy * (H / 2 - 0.4), z0), (sx * xs + hs, sy * (Wf / 2 + 1.0), z1), CB)
            ops.append(("DIFFERENCE", s))
    if level == 0:                                         # fold-line creases, both faces
        for down, zf in ((True, T), (False, 0.0)):
            for sy in (-1, 1):
                ops.append(("DIFFERENCE", _v_groove("x", sy * H / 2, -Lf / 2 - 1.0, Lf / 2 + 1.0, zf, down)))
            xc = xs if down else -xs
            ops.append(("DIFFERENCE", _v_groove("y", xc, -H / 2, H / 2, zf, down)))
    return Lod(b, ops=ops)


def _carton_socks_boxes() -> List[Socket]:
    c = CARTON
    n, p, bd = c["boxes"], c["box_pitch"], c["bd"]
    return [Socket(f"Box_{i + 1:02d}", ((i - (n - 1) / 2) * p, 0.0, bd), (0.0, 0.0, 90.0), "CONTAIN")
            for i in range(n)]


def _carton_common(state: str) -> Dict:
    c = CARTON
    L, W, H, bd = c["L"], c["W"], c["H"], c["bd"]
    cav = [[-L / 2 + bd, -W / 2 + bd, bd], [L / 2 - bd, W / 2 - bd, H - bd]]
    return {"states": {"Closed": "SM_CSK_Carton_Box6_Closed", "Open": "SM_CSK_Carton_Box6_Open",
                       "Flat": "SM_CSK_Carton_Box6_Flat"}, "state": state, "state_swap": "spec 5.3",
            "reference": "References/CardShop/csk_cartons.png (sheet 11)",
            "contain": {"BoxS": {"sockets": [f"Box_{i:02d}" for i in range(1, c["boxes"] + 1)], "cavity_mm": cav,
                                 "accepts": ["BoxS"],
                                 "pose": "standing, turned 90 deg about Z (the box's 80 depth along the carton)"}}}


def item_carton_closed() -> Item:
    c = CARTON
    L, W, H, bd = c["L"], c["W"], c["H"], c["bd"]
    lw, lh, lz0 = c["label"]
    tp = RSC["tape_t"]
    name = "SM_CSK_Carton_Box6_Closed"
    data = _carton_common("Closed")
    data.update({"footprint_mm": [L + 2 * tp, W, H + tp],
                 "stack": {"socket": "Stack", "pitch_mm": H + tp, "max": 4},
                 "notes": ["Sheet 11 closed: kraft RSC, 36 tape along the top seam and 45 down each end, a blank "
                           "95 x 75 label on the -X end under the tape tab, a joint line across each end at the top "
                           "flap joint. Stack pitch = H + the 0.2 tape."]})
    return Item(
        name=name, lods=[_rsc_closed(L, W, H, bd, c["tape_w"], c["tab"], True, k) for k in range(3)],
        materials=["M_CSK_Cardboard", "M_CSK_Tape", "M_CSK_Label"],
        projections={R_LABEL: _label_proj(L, lw, lh, lz0)},
        sockets=[Socket("Seat", (0, 0, 0))] + _carton_socks_boxes() + [
            Socket("Label", (-L / 2 - c["label_t"], 0.0, lz0 + lh / 2), (0.0, -90.0, 0.0)),
            Socket("Grip_L", (-L / 2, 0.0, H / 2)), Socket("Grip_R", (L / 2, 0.0, H / 2)),
            Socket("Stack", (0.0, 0.0, H + tp))],
        hulls=[((-L / 2, -W / 2, 0.0), (L / 2, W / 2, H))], cls="Carton", budget=BUDGETS[name], data=data)


def item_carton_open() -> Item:
    c = CARTON
    L, W, H, bd = c["L"], c["W"], c["H"], c["bd"]
    lw, lh, lz0 = c["label"]
    name = "SM_CSK_Carton_Box6_Open"
    data = _carton_common("Open")
    data.update({"class_when_closed": "Carton",
                 "flap_pose_deg": dict(RSC["pose"]),
                 "notes": ["Sheet 11 open: four real top flaps bent at their fold lines (back up, ends splayed, "
                           "front folded out); no Stack or tape (the tape is cut). The label stays on the -X end "
                           "(the sheet's open view leaves it off; kept so the state swap is consistent)."]})
    return Item(
        name=name, lods=[_rsc_open(L, W, H, bd, True, k) for k in range(3)],
        materials=["M_CSK_Cardboard", "M_CSK_Label"],
        projections={R_LABEL: _label_proj(L, lw, lh, lz0)},
        sockets=[Socket("Seat", (0, 0, 0))] + _carton_socks_boxes() + [
            Socket("Label", (-L / 2 - c["label_t"], 0.0, lz0 + lh / 2), (0.0, -90.0, 0.0)),
            Socket("Grip_L", (-L / 2, 0.0, H / 2)), Socket("Grip_R", (L / 2, 0.0, H / 2))],
        hulls=_open_hulls(L, W, H, bd), cls=None, budget=BUDGETS[name], data=data)


def item_carton_flat() -> Item:
    c = CARTON
    L, W, H, bd = c["L"], c["W"], c["H"], c["bd"]
    Lf, Wf, T = _flat_dims(L, W, H, bd)
    name = "SM_CSK_Carton_Box6_Flat"
    return Item(
        name=name, lods=[_rsc_flat(L, W, H, bd, k) for k in range(3)], materials=["M_CSK_Cardboard"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip_L", (-Lf / 2, 0.0, T / 2)),
                 Socket("Grip_R", (Lf / 2, 0.0, T / 2)), Socket("Stack", (0.0, 0.0, T))],
        hulls=[((-Lf / 2, -Wf / 2, 0.0), (Lf / 2, Wf / 2, T))], cls=None, budget=BUDGETS[name],
        data={"footprint_mm": [Lf, Wf, T], "state": "Flat", "pose": "lying (litter)",
              "states": _carton_common("Flat")["states"],
              "stack": {"socket": "Stack", "pitch_mm": T, "max": 10},
              "reference": "References/CardShop/csk_cartons.png (sheet 11)",
              "notes": ["Knocked down, D (L + W) x (H + W) = 644 x 289 x 8 (sheet 11 notes, decided 2026-09-29): "
                        "top layer = the L panel then the W panel, bottom layer mirrored; 8 flap slots, "
                        "half-round folds at both outer edges, V creases on every fold line. The glue flap "
                        "(between the layers, hidden) is not modelled."]})


# ---- B5 delivery boxes

def _ship_contents(L: float, W: float, H: float, bd: float) -> Dict:
    Li, Wi, Hi = L - 2 * bd, W - 2 * bd, H - 2 * bd
    grids, skipped = [], []
    for cls in SHIP_CONTENTS:
        if cls not in S.CLASSES:
            skipped.append(cls)
            continue
        g = solve_grid(Li, Wi, Hi, cls)
        if g:
            grids.append(g)
        else:
            skipped.append(cls)
    d = {"socket": "Contents", "cavity_mm": [[-Li / 2, -Wi / 2, bd], [Li / 2, Wi / 2, H - bd]],
         "interior_mm": [Li, Wi], "clear_h_mm": Hi, "accepts": [g["class"] for g in grids], "grids": grids,
         "note": "one floor layer per class from the Contents socket (floor centre), geom.solve_grid (10 margin)"}
    if skipped:
        d["not_gridded"] = skipped
    return d


def _ship_common(size: str, state: str) -> Dict:
    L, W, H = SHIP[size]
    return {"size": size, "state": state, "states": {"Closed": f"SM_CSK_Box_Ship_{size}_Closed",
                                                     "Open": f"SM_CSK_Box_Ship_{size}_Open",
                                                     "Flat": "SM_CSK_Box_Ship_Flat"},
            "state_swap": "spec 5.3", "reference": "References/CardShop/csk_cartons.png (sheet 11)",
            "contain": {"Contents": _ship_contents(L, W, H, SHIP_BD)}}


def item_ship_closed(size: str) -> Item:
    L, W, H = SHIP[size]
    bd = SHIP_BD
    tp = RSC["tape_t"]
    tab = round(SHIP_TAB * H, 1)
    name = f"SM_CSK_Box_Ship_{size}_Closed"
    data = _ship_common(size, "Closed")
    data.update({"footprint_mm": [L + 2 * tp, W, H + tp], "stack": {"socket": "Stack", "pitch_mm": H + tp, "max": 4},
                 "notes": [f"Sheet 11 closed: kraft RSC, 48 tape along the top seam and {tab:g} down each end, a "
                           "joint line across each end; no label (the sheet shows none; the Label socket marks "
                           "where one goes). Stack pitch = H + the 0.2 tape."]})
    return Item(
        name=name, lods=[_rsc_closed(L, W, H, bd, SHIP_TAPE_W, tab, False, k) for k in range(3)],
        materials=["M_CSK_Cardboard", "M_CSK_Tape"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Contents", (0.0, 0.0, bd), kind="CONTAIN"),
                 Socket("Label", (-L / 2, 0.0, H / 2), (0.0, -90.0, 0.0)), Socket("Tape", (0.0, 0.0, H + tp)),
                 Socket("Grip", (0.0, -W / 2, H / 2)), Socket("Stack", (0.0, 0.0, H + tp))],
        hulls=[((-L / 2, -W / 2, 0.0), (L / 2, W / 2, H))], cls=f"BoxShip{size}", budget=BUDGETS["SM_CSK_Box_Ship_Closed"],
        data=data)


def item_ship_open(size: str) -> Item:
    L, W, H = SHIP[size]
    bd = SHIP_BD
    name = f"SM_CSK_Box_Ship_{size}_Open"
    data = _ship_common(size, "Open")
    data.update({"class_when_closed": f"BoxShip{size}", "flap_pose_deg": dict(RSC["pose"]),
                 "notes": ["Sheet 11 open (flaps up): four real top flaps W/2 deep, bent at their fold lines; no "
                           "Stack or Tape socket (nothing stacks on raised flaps; the tape is cut)."]})
    return Item(
        name=name, lods=[_rsc_open(L, W, H, bd, False, k) for k in range(3)], materials=["M_CSK_Cardboard"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Contents", (0.0, 0.0, bd), kind="CONTAIN"),
                 Socket("Label", (-L / 2, 0.0, H / 2), (0.0, -90.0, 0.0)), Socket("Grip", (0.0, -W / 2, H / 2))],
        hulls=_open_hulls(L, W, H, bd), cls=None, budget=BUDGETS["SM_CSK_Box_Ship_Open"], data=data)


def item_ship_flat() -> Item:
    L, W, H = SHIP[SHIP_FLAT]
    bd = SHIP_BD
    Lf, Wf, T = _flat_dims(L, W, H, bd)
    name = "SM_CSK_Box_Ship_Flat"
    return Item(
        name=name, lods=[_rsc_flat(L, W, H, bd, k) for k in range(3)], materials=["M_CSK_Cardboard"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, -Wf / 2, T / 2)), Socket("Stack", (0.0, 0.0, T))],
        hulls=[((-Lf / 2, -Wf / 2, 0.0), (Lf / 2, Wf / 2, T))], cls=None, budget=BUDGETS[name],
        data={"footprint_mm": [Lf, Wf, T], "state": "Flat", "pose": "lying (litter)", "size": SHIP_FLAT,
              "stack": {"socket": "Stack", "pitch_mm": T, "max": 10},
              "reference": "References/CardShop/csk_cartons.png (sheet 11)",
              "notes": [f"The M box knocked down: D (L + W) x (H + W) = {Lf:g} x {Wf:g} x {T:g} (spec E 700 x 450 "
                        "matches no box; sheet 11 notes: build the knocked-down flat). Same construction as the "
                        "carton flat."]})


# =========================================================================== B6 blister

def _euro_slot(segs_end: int, segs_peak: int) -> List[Tuple[float, float]]:
    """Sheet 12: a rounded slot with a half-round peak on its top edge, CCW, in the card frame."""
    p = BLISTER
    sl, sh, below = p["slot"]
    r, pr = sh / 2, p["peak_r"]
    ys = p["h"] / 2 - below
    xr = sl / 2 - r
    pts = [(xr + r * math.cos(math.radians(-90 + 180 * k / segs_end)),
            ys + r * math.sin(math.radians(-90 + 180 * k / segs_end))) for k in range(segs_end + 1)]
    pts += [(pr * math.cos(math.pi * k / segs_peak), ys + r + pr * math.sin(math.pi * k / segs_peak))
            for k in range(segs_peak + 1)]
    pts += [(-xr + r * math.cos(math.radians(90 + 180 * k / segs_end)),
             ys + r * math.sin(math.radians(90 + 180 * k / segs_end))) for k in range(segs_end + 1)]
    return pts


def _blister_card(b: Builder, level: int, mat: int) -> None:
    p = BLISTER
    t = p["card_t"]
    if level == 2:
        b.box((-p["w"] / 2, -p["h"] / 2, 0.0), (p["w"] / 2, p["h"] / 2, t), mat=mat,
              regions={"pz": R_FRONT, "nz": R_BACK})
        return
    outer = rounded_rect(p["w"], p["h"], p["card_r"], (2, 1)[level])
    hole = _euro_slot((4, 2)[level], (6, 3)[level])
    ob, ot = b.loop(outer, 0.0), b.loop(outer, t)
    hb, ht = b.loop(hole, 0.0), b.loop(hole, t)
    for pts, lb, lt, sgn in ((outer, ob, ot, 1.0), (hole, hb, ht, -1.0)):
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            du, dv = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
            _face_out(b, [lb[i], lb[j], lt[j], lt[i]], (sgn * dv, -sgn * du, 0.0), mat)
    b.fill([ot, ht], mat, R_FRONT, (0, 0, 1))
    b.fill([ob, hb], mat, R_BACK, (0, 0, -1))


def _cup_centres():
    p = BLISTER
    cw, ch, _ = p["cup"]
    yc = p["bubble_cy"]
    xc = (cw + p["web"]) / 2
    return [(-xc, yc), (xc, yc)]


def _blister_bubble(b: Builder, level: int, mat: int) -> None:
    """Sheet 12: a clear twin-cup bubble (one cup per pack, a thin divider line between them) on a flat flange.
    A closed thin shell: outer skin (flange top, drafted walls, a 45-degree chamfer, the top), the flange's outer
    edge, and the inner skin 0.4 in, whose base ring sits in the card's top (hidden)."""
    p = BLISTER
    cw, ch, cr = p["cup"]
    f, T = p["film"], p["t"]
    zb = p["card_t"] - p["sink"]              # flange underside / inner skin base (inside the card)
    zf = p["card_t"] + f                      # flange top / outer skin base
    tc = p["top_c"] if level == 0 else 0.0
    z1 = T - tc
    d1 = (z1 - zf) * math.tan(math.radians(p["draft"]))
    segs = (2, 1)[level]
    cups = _cup_centres()
    yc = cups[0][1]
    fw = cw * 2 + p["web"] + 2 * p["flange"]
    fh = ch + 2 * p["flange"]

    def ring(cx, cy, w, h, r, z):
        return b.loop([(x + cx, y + cy) for x, y in rounded_rect(w, h, max(r, 0.5), segs)], z)

    def inset_ring(cx, cy, i, z):
        return ring(cx, cy, cw - 2 * i, ch - 2 * i, cr - i, z)

    outer_bases, inner_bases = [], []
    k225 = math.tan(math.radians(22.5))
    for cx, cy in cups:
        o0 = inset_ring(cx, cy, 0.0, zf)
        i0 = inset_ring(cx, cy, f, zb)
        rings_o = [o0, inset_ring(cx, cy, d1, z1)]
        rings_i = [i0, inset_ring(cx, cy, d1 + f, z1 - (f * k225 if tc else f))]
        if tc:
            rings_o.append(inset_ring(cx, cy, d1 + tc, T))
            rings_i.append(inset_ring(cx, cy, d1 + tc + f * k225, T - f))
        for lo, hi in zip(rings_o[:-1], rings_o[1:]):
            _ring_strip(b, lo, hi, (cx, cy), 1.0, mat, up=0.0)
        for lo, hi in zip(rings_i[:-1], rings_i[1:]):
            _ring_strip(b, lo, hi, (cx, cy), -1.0, mat, up=0.0)
        b.fill([rings_o[-1]], mat, 0, (0, 0, 1))
        b.fill([rings_i[-1]], mat, 0, (0, 0, -1))
        outer_bases.append(o0)
        inner_bases.append(i0)
    fl = [(x, y + yc) for x, y in rounded_rect(fw, fh, p["flange_r"], segs)]
    ft, fb = b.loop(fl, zf), b.loop(fl, zb)
    n = len(fl)
    for i in range(n):
        j = (i + 1) % n
        du, dv = fl[j][0] - fl[i][0], fl[j][1] - fl[i][1]
        _face_out(b, [fb[i], fb[j], ft[j], ft[i]], (dv, -du, 0.0), mat)
    b.fill([ft] + outer_bases, mat, 0, (0, 0, 1))
    b.fill([fb] + inner_bases, mat, 0, (0, 0, -1))


def _blister_lod(level: int) -> Lod:
    p = BLISTER
    PRINT, FILM = 0, 1
    b = Builder()
    _blister_card(b, level, PRINT)
    if level == 2:                                          # far: the bubble as one clear block
        cups = _cup_centres()
        cw, ch, _ = p["cup"]
        xw = cw + p["web"] / 2
        b.box((-xw, cups[0][1] - ch / 2, p["card_t"] - p["sink"]), (xw, cups[0][1] + ch / 2, p["t"]), mat=FILM)
        return Lod(b)
    _blister_bubble(b, level, FILM)
    return Lod(b)


def item_blister() -> Item:
    p = BLISTER
    w, h, T, ct = p["w"], p["h"], p["t"], p["card_t"]
    cw, ch, _ = p["cup"]
    f = p["film"]
    sl, sh, below = p["slot"]
    y_apex = h / 2 - below + sh / 2 + p["peak_r"]
    cups = _cup_centres()
    pk = S.PACK_STD
    name = "SM_CSK_Blister_Pack"
    # the pack cavity (both cups as one box, for the kit's fit test): the inner skin at the height of a pack's top
    z_pack = ct + pk["t"]
    di = f + (z_pack - ct - f) * math.tan(math.radians(p["draft"]))
    cav = [[cups[0][0] - cw / 2 + di, cups[0][1] - ch / 2 + di, ct],
           [cups[1][0] + cw / 2 - di, cups[1][1] + ch / 2 - di, T - f]]
    return Item(
        name=name, lods=[_blister_lod(k) for k in range(3)], materials=["M_CSK_BoxPrint", "M_CSK_Film"],
        projections={R_FRONT: _planar(-w / 2, -h / 2, w, h),
                     R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)),
                 Socket("Hang", (0.0, y_apex, ct / 2), (-90.0, 0.0, 0.0)),
                 Socket("Pack_01", (cups[0][0], cups[0][1], ct), kind="CONTAIN"),
                 Socket("Pack_02", (cups[1][0], cups[1][1], ct), kind="CONTAIN"),
                 Socket("Face", (0.0, 0.0, T)), Socket("Stack", (0.0, 0.0, T))],
        hulls=[((-w / 2, -h / 2, 0.0), (w / 2, h / 2, T))], cls="Hang", budget=BUDGETS[name],
        data={"footprint_mm": [w, h, T], "pose": "lying on its back (card down, header toward +Y); hangs by Hang",
              "hang": {"socket": "Hang", "T_mm": T, "pitch_mm": T + 2.0,
                       "note": "the Hang socket is the euro slot's peak on the card mid-plane, rotated -90 about X: "
                               "item world = hook point x inverse(Hang) hangs it plumb, bubble toward the customer"},
              "stack": {"socket": "Stack", "pitch_mm": T, "max": 4},
              "contain": {"Pack": {"sockets": ["Pack_01", "Pack_02"], "cavity_mm": cav, "accepts": ["Pack"],
                                   "pose": "lying face up, side by side, one per cup"}},
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12)",
              "notes": ["Sheet 12: printed card (two-tone print on the front and back tiles), euro slot with a "
                        "half-round peak cut through the card, clear twin-cup PET bubble with a thin divider on an "
                        "8 flange; the bubble is 19.4 deep (sheet 12 side view; spec bubble 14 was E)."]},
    )


# =========================================================================== registry

ITEMS = {
    "b_ship_carton_closed": item_carton_closed,
    "b_ship_carton_open": item_carton_open,
    "b_ship_carton_flat": item_carton_flat,
    **{f"b_ship_{k.lower()}_closed": (lambda k=k: item_ship_closed(k)) for k in SHIP},
    **{f"b_ship_{k.lower()}_open": (lambda k=k: item_ship_open(k)) for k in SHIP},
    "b_ship_flat": item_ship_flat,
    "b_ship_blister": item_blister,
}
