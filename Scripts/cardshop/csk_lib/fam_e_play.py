"""Card Shop Kit family e_play: the binder system, the deck box, the playmat and the dice
(CARDSHOP_KIT_SPEC.md 3.E rows E3-E6; P3-P5).

    E3 SM_CSK_Binder_{Body,Cover,Page,Closed}        reference sheet 14 (csk_binder.png)
    E4 SM_CSK_DeckBox + SM_CSK_DeckBox_Lid           reference sheet 15 (1) (csk_deckbox_playmat_dice.png)
    E5 SM_CSK_Playmat_{Flat,Rolled}                  reference sheet 15 (2)
    E6 SM_CSK_Die_{D6,D20} + SM_CSK_Token_22         reference sheet 15 (3)

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice. "sheet N" =
the value or form is read off that reference sheet (the picture wins over E numbers; M numbers win over the picture).
Millimetres; Seat frame: +X right, +Y away from the customer, +Z up.

Construction notes:
* Round parts are sampled finer than 30 degrees per facet (the kit's sharp-edge rule, mesh.mark_sharp), so they shade
  smooth; flat faces keep crisp edges.
* The binder is modelled OPEN FLAT (sheet 14's open view: front cover, spine and back cover lie in one plane). Pages
  can only turn over O-rings when the spine lies flat; the closed binder is the separate merged Closed mesh.
* The deck-box lid is built from convex parts (its name ends ``_Lid``, so the kit runs the outward-winding check).

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Sequence, Tuple

from . import spec as S
from .geom import R_FRONT, R_LABEL, Item, Lod, Socket, _face_out, _planar, _prism_y, inset
from .shapes import Builder, circle, rounded_rect

# =========================================================================== numbers

BINDER = dict(                  # E3, sheet 14
    w=247.7, h=292.1,           # cover, M [D17] (closed width, spine face to fore edge)
    spine=57.0,                 # sheet 14 spine view: the black spine band measures 56.4 (spec 51 E, range 25-76 E)
    t=4.0,                      # E: padded cover board thickness
    band=38.0,                  # sheet 14 front view: the black spine band reaches 38 from the spine face (note: ~40)
    corner_r=3.0,               # sheet 14: slightly rounded cover corners (E)
    pad_bevel=1.2,              # E: the padded edges, a 2-segment round
    page=(220.7, 293.7),        # M [D17]
    pocket=(65.1, 90.5),        # M [D17], 3 x 3 on both faces
    hole_pitch=108.0,           # M [D17]: 3 holes
    hole_d=7.0, hole_inset=9.3,  # sheet 14 (open view): hole Ø and its centre's distance from the page's left edge
    strip=17.4,                 # D: 220.7 - 3 x 65.1 - 2 seams - right margin (sheet 14 measures ~19)
    seam=2.5, margin_r=3.0,     # E, sheet 14: welded seams between pockets; right margin
    core=0.3, pad=0.45,         # E: the page's welded core film and each pocket's raised pad (a card is 0.30)
    rail=(22.0, 7.0),           # sheet 14 close-up: chrome dome rail, width x height (open view measures 21-24)
    rail_len=266.0,             # E: the rail between the boosters (sheet 14: the mechanism spans nearly the full height)
    booster=(11.0, 7.5, 9.0, 1.5, 4.5),  # sheet 14: lever booster ends, length, height, stud Ø, stud height, stud offset
    ring_od=40.0, wire=3.5,     # sheet 14: O-ring outer Ø (open view 39-45) and wire Ø
    ring_x=20.0,                # D: rail centre from the spine fold; the page (M) must end inside the fore edge
    clip=(14.0, 8.0, 13.0),     # sheet 14 close-up: the knuckle where each ring's ends meet: X x Y, top z
    ring_gap_deg=15.0,          # the ring's ends meet inside the clip, 15 deg either side of the bottom
    stations=20,                # spec: Ring_01..20 page stations on the arc (E)
)

DECKBOX = dict(                 # E4, sheet 15 (1)
    w=76.0, d=80.0, h=108.0,    # E (spec); sheet 15 prints the same call-outs
    in_w=68.0, in_d=71.0, in_h=100.0,   # M [D18]
    floor=4.0,                  # D: (108 - 100) split evenly between the floor and the lid top (E)
    lid=41.5,                   # sheet 15: the lid covers the top 38 % (41.5 of 108)
    corner_r=3.0, corner_segs=4,  # sheet 15: slightly rounded vertical edges (E)
    dip=(19.0, 11.85, 9.4, 0.1),  # sheet 15: wave dip half-width at the seam 19, half-width of its flat bottom 11.85,
                                  # depth 9.4; 0.1 = the shoulder's entry slope (7 deg, so the cut is never tangent)
    bevel=0.5, lid_chamfer=0.8,   # E: crisp moulded edges
    pin=(3.0, 35.0),            # sheet 15 open views: the hinge pin at the back top edge, Ø x length
    open_deg=110.0,             # E (spec): 0-110
    sleeve=(66.0, 91.0),        # C4 Std deck sleeve, M [D1]: the cards stand in the box on the sleeve's short edge
    card_pitch=0.66,            # E: 100 sleeved cards in 66 of the 71 inner depth
)

PLAYMAT = dict(                 # E5, sheet 15 (2)
    w=609.6, h=355.6, t=2.0,    # M [D19]
    corner_r=10.0,              # sheet 15: rounded corners (~10)
    band=2.0,                   # E (spec): the stitched edge band
    side_z=1.5, round=0.5,      # E: the binding rounds over the top edge: vertical to 1.5, then 0.5 in to the top
    segs=5,
    roll_core=10.0,             # E (spec D: 20 core): the inner radius where the roll starts
    roll_gap=0.1,               # E: 1.9 thick layers at the 2.0 pitch (M thickness), so the spiral reads at the ends
    roll_facets=16,             # facets per turn (22.5 deg: round shading under the 30-deg rule)
    roll_chamfer=0.3,           # sheet 15: the red line at each wrap's edge in the black roll end
)

D6 = dict(size=16.0,            # M [D20]
          r=2.0,                # sheet 15: rounded corners (measured ~2)
          pip_d=3.0, pip_off=4.1,  # sheet 15: pip Ø and offset from the face centre
          pip_depth=0.95,       # E: drilled cone dimple, steeper than 30 deg so its rim reads crisp
          pip_sides=10)
D20 = dict(face_to_face=22.0,   # E (spec 22); sheet 15's silhouette (~26-27 across) matches 22 face to face
           chamfer=0.07)        # E: edge chamfer as a fraction of each face's inradius (0.55 mm wide), sheet 15 crisp edges
TOKEN = dict(d=22.0, t=2.0,     # E (spec) = sheet 15 call-outs
             chamfer=0.3, sides=18)  # sheet 15: slightly softened edge

# LOD0 budgets: the spec's Tris column (E). Raised (logged in the report):
#   Binder_Body 1500 -> 1800: three O-rings of round wire need 13 sides (27.7 deg < the 30-deg sharp rule) x 16
#     segments to shade round: ~1250 tris of the 1700.
#   Playmat_Rolled 600 -> 1200: the spiral end (sheet 15) is a real wound strip (16 facets a turn over 5.8 turns) with
#     a 0.3 cloth chamfer on each wrap's edge, the red lines of sheet 15's black roll end.
#   Die_D6 300 -> 800: 21 real pip dimples (10-sided cones) and round edges of 4 segments.
#   Token_22 100 -> 150: an 18-sided disc with chamfered rims on both faces (still LOD0 only).
BUDGETS = {
    "SM_CSK_Binder_Body": 1800,
    "SM_CSK_Binder_Cover": 300,
    "SM_CSK_Binder_Page": 400,
    "SM_CSK_Binder_Closed": 800,
    "SM_CSK_DeckBox": 600,
    "SM_CSK_DeckBox_Lid": 300,
    "SM_CSK_Playmat_Flat": 200,
    "SM_CSK_Playmat_Rolled": 1200,
    "SM_CSK_Die_D6": 800,
    "SM_CSK_Die_D20": 500,
    "SM_CSK_Token_22": 150,
}

# Binder: spec 4.2 class (E3 Closed + Retail_BinderWrapped), standing, front toward -Y; pitch = spine + 2 along Y
CLASSES = {
    "Binder": S.ItemClass("Binder", (250.0, BINDER["spine"], 295.0), (260.0, BINDER["spine"] + 2.0)),
}

REF14 = "References/CardShop/csk_binder.png (sheet 14)"
REF15 = "References/CardShop/csk_deckbox_playmat_dice.png (sheet 15)"


# =========================================================================== small helpers

def _add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def _mul(v, s):
    return tuple(c * s for c in v)


def _norm(v):
    L = math.sqrt(sum(c * c for c in v))
    return tuple(c / L for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _centre(b: Builder, ids) -> Tuple[float, float, float]:
    P = [b.verts[i] for i in ids]
    return tuple(sum(p[k] for p in P) / len(P) for k in range(3))


def _ring_loops(b: Builder, rings, pts2) -> List[List[int]]:
    """Loops of an outline ``pts2`` (XY, CCW) at each (inset d, z) in ``rings``; the outline must be a function of d."""
    return [b.loop(pts2(d), z) for d, z in rings]


def _bridge(b: Builder, la, lb, mat: int, region: int = 0, up: float = 0.0, closed: bool = True,
            centre=(0.0, 0.0)) -> None:
    """Quads between two loops of equal length, each wound to face away from ``centre`` in plan (plus ``up`` in Z)."""
    n = len(la)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        ids = [la[i], la[j], lb[j], lb[i]]
        c = _centre(b, ids)
        _face_out(b, ids, (c[0] - centre[0], c[1] - centre[1], up), mat, region)


def _cyl(b: Builder, axis: str, c0, length: float, r: float, sides: int, mat: int, caps=(True, True)) -> None:
    """A closed cylinder along ``axis`` ('x' | 'y' | 'z') starting at point ``c0``."""
    ax = "xyz".index(axis)
    u, v = [k for k in range(3) if k != ax]
    rings = []
    for s in (0.0, length):
        ring = []
        for i in range(sides):
            p = list(c0)
            p[ax] += s
            a = 2 * math.pi * i / sides
            p[u] += r * math.cos(a)
            p[v] += r * math.sin(a)
            ring.append(b.v(*p))
        rings.append(ring)
    ctr = list(c0)
    ctr[ax] += length / 2
    for i in range(sides):
        j = (i + 1) % sides
        ids = [rings[0][i], rings[0][j], rings[1][j], rings[1][i]]
        c = _centre(b, ids)
        _face_out(b, ids, tuple(c[k] - ctr[k] if k != ax else 0.0 for k in range(3)), mat)
    n = [0.0, 0.0, 0.0]
    for k, ring in enumerate(rings):
        if caps[k]:
            n = [0.0, 0.0, 0.0]
            n[ax] = -1.0 if k == 0 else 1.0
            b.fill([ring], mat, 0, tuple(n))


# =========================================================================== E6 dice and token (sheet 15 (3))

# d6 faces: (number, outward normal, u, v) with u x v = n (u right, v up, seen from outside). Sheet 15 shows 2 on top
# and 4 in front; its right face repeats a 4, which no real die has: 6 is used (adjacent to 2 and 4, and it keeps the
# four corner pips the picture shows). Opposites sum to 7; 1-2-3 run counter-clockwise round their corner (western).
_D6_FACES = (
    (2, (0, 0, 1), (1, 0, 0), (0, 1, 0)),
    (5, (0, 0, -1), (1, 0, 0), (0, -1, 0)),
    (4, (0, -1, 0), (1, 0, 0), (0, 0, 1)),
    (3, (0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    (6, (1, 0, 0), (0, 1, 0), (0, 0, 1)),
    (1, (-1, 0, 0), (0, -1, 0), (0, 0, 1)),
)
_PIPS = {1: [(0, 0)], 2: [(-1, 1), (1, -1)], 3: [(-1, 1), (0, 0), (1, -1)],
         4: [(-1, -1), (1, -1), (1, 1), (-1, 1)], 5: [(-1, -1), (1, -1), (1, 1), (-1, 1), (0, 0)],
         6: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)]}


def _d6_face(b: Builder, level: int, num: int, n, u, v, h: float, corners: List[int]) -> None:
    """The flat centre of one face with its pips: LOD0 real cone dimples, LOD1 flush hexagons, LOD2 none. Pip faces
    are region R_FRONT (the ink mask: UV0 tile (0, 0)); everything else is region 0 (the U -1 tile)."""
    d = D6
    o, rp = d["pip_off"], d["pip_d"] / 2
    holes = []
    ctr = _add(_mul(n, h), (0.0, 0.0, h))
    if level < 2:
        k = d["pip_sides"] if level == 0 else 6
        for pu, pv in _PIPS[num]:
            P = _add(ctr, _mul(u, pu * o), _mul(v, pv * o))
            rim = [b.v(*_add(P, _mul(u, rp * math.cos(2 * math.pi * i / k)), _mul(v, rp * math.sin(2 * math.pi * i / k))))
                   for i in range(k)]
            holes.append(rim)
            if level == 0:
                apex = b.v(*_add(P, _mul(n, -d["pip_depth"])))
                for i in range(k):
                    b.face((rim[i], rim[(i + 1) % k], apex), 0, R_FRONT)
            else:
                b.face(tuple(rim), 0, R_FRONT)
    b.fill([corners] + holes, 0, 0, tuple(float(c) for c in n))


def _d6_builder(level: int) -> Builder:
    """A rounded cube on a welded grid: each face's grid lines sit at the flat face's edges and at 22.5-degree steps
    round the edge radius (LOD0; 45 degrees on LOD1/2), projected onto the rounded box (clamp + radius)."""
    d = D6
    h, r = d["size"] / 2, d["r"]
    c = h - r
    m = 2 if level == 0 else 1
    ts = [c + r * math.tan(math.radians(45.0 * k / m)) for k in range(m + 1)]
    T = [-t for t in reversed(ts)] + ts
    b = Builder()
    cache: Dict[Tuple[float, float, float], int] = {}

    def vid(p):
        inner = [max(-c, min(c, q)) for q in p]
        dd = [p[i] - inner[i] for i in range(3)]
        L = math.sqrt(sum(x * x for x in dd))
        out = tuple(inner[i] + r * dd[i] / L for i in range(3)) if L > 1e-9 else tuple(p)
        out = (out[0], out[1], out[2] + h)
        key = tuple(round(x, 5) for x in out)
        if key not in cache:
            cache[key] = b.v(*out)
        return cache[key]

    for num, n, u, v in _D6_FACES:
        g = [[vid(_add(_mul(n, h), _mul(u, T[i]), _mul(v, T[j]))) for j in range(len(T))] for i in range(len(T))]
        for i in range(len(T) - 1):
            for j in range(len(T) - 1):
                q = [g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]]
                if i == m and j == m:
                    _d6_face(b, level, num, n, u, v, h, q)
                else:
                    b.face(tuple(q), 0, 0)
    return b


def _d6_proj(x: float, y: float, z: float):
    """Pip ink UVs: each face's pips in its own cell of tile (0, 0) (3 x 2 cells, cell = face number - 1)."""
    h = D6["size"] / 2
    p = (x, y, z - h)
    ax = max(range(3), key=lambda i: abs(p[i]))
    sgn = 1 if p[ax] > 0 else -1
    for num, n, u, v in _D6_FACES:
        if n[ax] == sgn:
            break
    pu, pv = _dot(p, u), _dot(p, v)
    col, row = (num - 1) % 3, (num - 1) // 3
    return (inset((col + (pu + h) / (2 * h)) / 3), inset((row + (pv + h) / (2 * h)) / 2))


def item_die_d6() -> Item:
    s = D6["size"]
    return Item(
        name="SM_CSK_Die_D6", lods=[Lod(_d6_builder(k)) for k in range(3)], materials=["M_CSK_Resin"],
        projections={R_FRONT: _d6_proj},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, 0, s / 2))],
        hulls=[((-s / 2, -s / 2, 0.0), (s / 2, s / 2, s))], budget=BUDGETS["SM_CSK_Die_D6"],
        data={"footprint_mm": [s, s, s], "reference": REF15,
              "pip_ink": {"uv0": "pip faces in tile (0, 0), one 1/3 x 1/2 cell per face (cell = number - 1); every "
                                 "other face in the U -1 tile: ink = UV0.u >= 0"},
              "faces": {"top": 2, "front": 4, "right": 6, "left": 1, "back": 3, "bottom": 5},
              "notes": ["Sheet 15: 16 mm, rounded corners (R 2), white pips as real 10-sided cone dimples (Ø 3.0, "
                        "0.95 deep, 4.1 off centre).",
                        "Sheet 15 draws a 4 on both visible sides; a die cannot, so the right face is a 6 (a western "
                        "die: opposites sum to 7, 1-2-3 counter-clockwise)."]},
    )


def _d20_builder() -> Builder:
    """Icosahedron resting on a face, 22 face to face, with every edge and vertex planed (a crisp 0.55 chamfer):
    each face is inset toward its centre, edges become quads, vertices pentagons (116 tris)."""
    p = (1 + 5 ** 0.5) / 2
    V = [(-1, p, 0), (1, p, 0), (-1, -p, 0), (1, -p, 0), (0, -1, p), (0, 1, p), (0, -1, -p), (0, 1, -p),
         (p, 0, -1), (p, 0, 1), (-p, 0, -1), (-p, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    ri_unit = p * p / (2 * math.sqrt(3))            # inradius of edge 1
    a = D20["face_to_face"] / 2 / ri_unit           # edge length (14.55)
    sc = a / 2                                      # V has edge 2
    V = [_mul(v, sc) for v in V]
    # rotate face 0's centre to -Z (Rodrigues)
    g0 = _norm(_mul(_add(V[F[0][0]], V[F[0][1]], V[F[0][2]]), 1 / 3))
    t = (0.0, 0.0, -1.0)
    k = _cross(g0, t)
    sa, ca = math.sqrt(_dot(k, k)), _dot(g0, t)
    k = _norm(k)

    def rot(v):
        return _add(_mul(v, ca), _mul(_cross(k, v), sa), _mul(k, _dot(k, v) * (1 - ca)))
    V = [rot(v) for v in V]
    ri = D20["face_to_face"] / 2
    s = D20["chamfer"]
    b = Builder()
    P = {}
    for fi, f in enumerate(F):
        g = _mul(_add(*[V[i] for i in f]), 1 / 3)
        for i in f:
            q = _add(V[i], _mul(_add(g, _mul(V[i], -1)), s))
            P[(fi, i)] = b.v(q[0], q[1], q[2] + ri)
        _face_out(b, [P[(fi, i)] for i in f], g, 0)
    edges: Dict[Tuple[int, int], List[int]] = {}
    for fi, f in enumerate(F):
        for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            edges.setdefault(tuple(sorted(e)), []).append(fi)
    for (i, j), (f1, f2) in edges.items():
        _face_out(b, [P[(f1, i)], P[(f1, j)], P[(f2, j)], P[(f2, i)]], _add(V[i], V[j]), 0)
    for vi, vv in enumerate(V):
        around = [fi for fi, f in enumerate(F) if vi in f]
        n = _norm(vv)
        e1 = _norm(_cross(n, (0.3, 0.5, 0.8)))
        e2 = _cross(n, e1)
        pts = sorted(around, key=lambda fi: math.atan2(_dot(_add(b.verts[P[(fi, vi)]], (0, 0, -ri)), e2),
                                                         _dot(_add(b.verts[P[(fi, vi)]], (0, 0, -ri)), e1)))
        _face_out(b, [P[(fi, vi)] for fi in pts], n, 0)
    return b


def item_die_d20() -> Item:
    b = _d20_builder()
    xs = [v[0] for v in b.verts]
    ys = [v[1] for v in b.verts]
    zs = [v[2] for v in b.verts]
    return Item(
        name="SM_CSK_Die_D20", lods=[Lod(b)], materials=["M_CSK_Resin"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, 0, D20["face_to_face"] / 2))],
        hulls=[((min(xs), min(ys), 0.0), (max(xs), max(ys), max(zs)))], budget=BUDGETS["SM_CSK_Die_D20"],
        data={"footprint_mm": [round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs), 2)],
              "reference": REF15,
              "notes": ["Sheet 15: blank faces, crisp edges. 22 face to face (the spec's 22; the picture's silhouette "
                        "of ~26-27 across matches it); edges and vertices chamfered 0.55 so the crisp edges catch "
                        "light. Rests on a face (Seat = that face's centre)."]},
    )


def _token_builder() -> Builder:
    tk = TOKEN
    R, t, c, n = tk["d"] / 2, tk["t"], tk["chamfer"], tk["sides"]
    b = Builder()
    loops = [b.loop(circle(rr, n), z) for rr, z in ((R - c, 0.0), (R, c), (R, t - c), (R - c, t))]
    b.fill([loops[0]], 0, 0, (0, 0, -1))
    for la, lb, up in ((loops[0], loops[1], -1.0), (loops[1], loops[2], 0.0), (loops[2], loops[3], 1.0)):
        _bridge(b, la, lb, 0, up=up * R)
    b.fill([loops[3]], 0, 0, (0, 0, 1))
    return b


def item_token() -> Item:
    tk = TOKEN
    R, t = tk["d"] / 2, tk["t"]
    return Item(
        name="SM_CSK_Token_22", lods=[Lod(_token_builder())], materials=["M_CSK_Resin"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, 0, t / 2))],
        hulls=[((-R, -R, 0.0), (R, R, t))], budget=BUDGETS["SM_CSK_Token_22"],
        data={"footprint_mm": [2 * R, 2 * R, t], "reference": REF15,
              "notes": ["Sheet 15: a 22 x 2 disc with a slightly softened edge (0.3 chamfers on both rims)."]},
    )


# =========================================================================== E5 playmat (sheet 15 (2))

def _mat_outline(d: float, segs: int):
    p = PLAYMAT
    return rounded_rect(p["w"] - 2 * d, p["h"] - 2 * d, p["corner_r"] - d, segs)


def _mat_flat_builder(level: int) -> Builder:
    """Flat mat, face up: the rubber base (bottom), the stitched binding (the side, rounding over the top edge and a
    2-wide band on top), and the printed cloth top inside the band."""
    p = PLAYMAT
    PRINT, STITCH, RUBBER = 0, 1, 2
    t = p["t"]
    segs = (p["segs"], 2, 1)[level]
    if level == 0:
        rings = [(0.0, 0.0), (0.0, p["side_z"]), (p["round"], t), (p["band"], t)]
    elif level == 1:
        rings = [(0.0, 0.0), (0.0, t), (p["band"], t)]
    else:
        rings = [(0.0, 0.0), (0.0, t)]
    b = Builder()
    loops = [b.loop(_mat_outline(d, segs), z) for d, z in rings]
    b.fill([loops[0]], RUBBER, 0, (0, 0, -1))
    for k in range(len(loops) - 1):
        (d0, z0), (d1, z1) = rings[k], rings[k + 1]
        up = 0.0 if z1 > z0 and d1 == d0 else 1e6 if z1 == z0 else 1.0
        _bridge(b, loops[k], loops[k + 1], STITCH, up=up)
    b.fill([loops[-1]], PRINT, R_FRONT, (0, 0, 1))
    return b


def item_playmat_flat() -> Item:
    p = PLAYMAT
    w, h, t, bd = p["w"], p["h"], p["t"], p["band"]
    x0, y0 = -w / 2 + bd, -h / 2 + bd
    cw, ch = S.CARD_STD["w"], S.CARD_STD["h"]
    xz = w / 2 - bd - 10.0 - cw / 2 - 12.0             # E: the deck column, 10 in from the band plus a finger gap
    return Item(
        name="SM_CSK_Playmat_Flat", lods=[Lod(_mat_flat_builder(k)) for k in range(3)],
        materials=["M_CSK_Playmat", "M_CSK_Stitch", "M_CSK_Rubber"],
        projections={R_FRONT: _planar(x0, y0, w - 2 * bd, h - 2 * bd)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Zone_Play", (-45.0, 0.0, t), kind="DISPLAY"),
                 Socket("Zone_Deck", (xz, (ch + 22.0) / 2, t), kind="DISPLAY"),
                 Socket("Zone_Discard", (xz, -(ch + 22.0) / 2, t), kind="DISPLAY")],
        hulls=[((-w / 2, -h / 2, 0.0), (w / 2, h / 2, t))], budget=BUDGETS["SM_CSK_Playmat_Flat"],
        data={"footprint_mm": [w, h, t], "pose": "lying face up, the long edge along X (the player sits at -Y)",
              "states": {"Flat": "SM_CSK_Playmat_Flat", "Rolled": "SM_CSK_Playmat_Rolled"},
              "print": {"tile": [0, 0], "rect_mm": [x0, y0, w - 2 * bd, h - 2 * bd],
                        "note": "the cloth top inside the stitched band; the Playmats atlas cell (2 px/mm)"},
              "zones": {"note": "E: a play area left of centre; the deck and discard piles stacked in the right "
                                "column (card Seats face up, top edge +Y)"},
              "reference": REF15,
              "notes": ["Sheet 15: red cloth top, black rubber base, darker stitched edge, rounded corners (R 10).",
                        "The stitched binding (slot M_CSK_Stitch) wraps the side and rounds 0.5 over the top edge "
                        "into a 2-wide band; the stitch pattern is texture / normal detail."]},
    )


def _roll_numbers():
    p = PLAYMAT
    t = p["t"]
    lay = t - p["roll_gap"]
    r0 = p["roll_core"]
    a = r0 + lay / 2                                  # centreline radius at the start
    A = t / (4 * math.pi)
    L = p["w"]
    Phi = (-a + math.sqrt(a * a + 4 * A * L)) / (2 * A)   # L = a Phi + t Phi^2 / 4 pi (centreline length = 609.6)
    return t, lay, r0, a, Phi, L


def _roll_theta0():
    """The mat's outer (free) end lies at the back, 60 deg below the axis line (hidden from the front)."""
    *_, Phi, _L = _roll_numbers()
    return math.radians(-60.0) - Phi


def _roll_axis_z() -> float:
    """Axis height so the outer surface just touches the floor."""
    t, lay, r0, a, Phi, L = _roll_numbers()
    th0 = _roll_theta0()
    zmin = 0.0
    n = 4000
    for i in range(n + 1):
        f = Phi * i / n
        r = r0 + t * f / (2 * math.pi) + lay
        zmin = min(zmin, r * math.sin(f + th0))
    return -zmin


def _roll_builder(per_turn: int, chamfer: bool = True) -> Builder:
    """Sheet 15 rolled mat: the 609.6 long mat wound cloth side out round a Ø 20 core (a 2.0 pitch Archimedean
    spiral of 1.9 layers), axis along X, 355.6 long. Sheet 15's roll end is black rubber with a red line at each
    wrap: the ends are rubber, and each wrap's outer (cloth) edge has a 0.3 chamfer in the cloth print."""
    p = PLAYMAT
    PRINT, RUBBER = 0, 1
    t, lay, r0, a, Phi, L = _roll_numbers()
    th0 = _roll_theta0()
    zc = _roll_axis_z()
    X = p["h"] / 2
    c = p["roll_chamfer"] if chamfer else 0.0
    dphi = 2 * math.pi / per_turn                   # the same angles on every turn: the wraps' facets stay parallel,
    phis = [i * dphi for i in range(int(Phi / dphi) + 1)]   # so the 0.1 gaps never close (no crossing chords)
    if Phi - phis[-1] > 1e-6:                        # the short last facet stays: merging it would misalign the
        phis.append(Phi)                            # outer wrap and cross the one inside it
    b = Builder()

    def pt(r, f, x):
        th = f + th0
        return (x, r * math.cos(th), zc + r * math.sin(th))
    rin = [r0 + t * f / (2 * math.pi) for f in phis]
    I = {sx: [b.v(*pt(r, f, sx * X)) for r, f in zip(rin, phis)] for sx in (-1, 1)}
    Os = {sx: [b.v(*pt(r + lay, f, sx * (X - c))) for r, f in zip(rin, phis)] for sx in (-1, 1)}
    Oe = {sx: [b.v(*pt(r + lay - c, f, sx * X)) for r, f in zip(rin, phis)] for sx in (-1, 1)} if c else Os
    n = len(phis)
    for k in range(n - 1):
        fm = (phis[k] + phis[k + 1]) / 2
        radial = (0.0, math.cos(fm + th0), math.sin(fm + th0))
        _face_out(b, [I[-1][k], I[-1][k + 1], I[1][k + 1], I[1][k]], _mul(radial, -1), RUBBER)
        _face_out(b, [Os[-1][k], Os[-1][k + 1], Os[1][k + 1], Os[1][k]], radial, PRINT, R_FRONT)
        for sx in (-1, 1):
            if c:                                   # the cloth edge chamfer
                _face_out(b, [Os[sx][k], Os[sx][k + 1], Oe[sx][k + 1], Oe[sx][k]], _add(radial, (float(sx), 0, 0)),
                          PRINT, R_FRONT)
            _face_out(b, [I[sx][k], I[sx][k + 1], Oe[sx][k + 1], Oe[sx][k]], (float(sx), 0.0, 0.0), RUBBER)
    for k, sgn, reg in ((0, -1, R_ROLL_END), (n - 1, 1, R_ROLL_END + 1)):   # the mat's short edges (core end, free end)
        tang = (0.0, -math.sin(phis[k] + th0) * sgn, math.cos(phis[k] + th0) * sgn)
        ring = [I[-1][k], Oe[-1][k]] + ([Os[-1][k], Os[1][k]] if c else []) + [Oe[1][k], I[1][k]]
        _face_out(b, ring, tang, RUBBER, reg)
    return b


R_ROLL_END = 5          # the roll's two short end faces: their own bands in tile (1, 0) (smart project packs their
                        # 0.3 mm chamfer corners to zero UV area)


def _roll_end_proj(end: int):
    t, lay, r0, a, Phi, L = _roll_numbers()
    zc = _roll_axis_z()
    X = PLAYMAT["h"] / 2
    rin = r0 + t * (0.0 if end == 0 else Phi) / (2 * math.pi)

    def proj(x, y, z):
        rr = math.hypot(y, z - zc) - rin
        return (1.0 + inset(0.5 * end + 0.48 * (x + X) / (2 * X)), inset(0.02 + 0.2 * rr / lay))
    return proj


def _roll_proj(x: float, y: float, z: float):
    """The flat mat's print wrapped on: u = centreline length from the core end / 609.6, v = along the roll axis."""
    t, lay, r0, a, Phi, L = _roll_numbers()
    th0 = _roll_theta0()
    zc = _roll_axis_z()
    X = PLAYMAT["h"] / 2
    r = math.hypot(y, z - zc)
    th = math.atan2(z - zc, y) - th0
    best = None
    for kk in range(-40, 40):
        f = th + 2 * math.pi * kk
        if -0.05 <= f <= Phi + 0.05:
            e = abs(r - (r0 + t * f / (2 * math.pi) + lay))
            if best is None or e < best[0]:
                best = (e, f)
    f = min(max(best[1], 0.0), Phi)
    s = a * f + t * f * f / (4 * math.pi)
    return (inset(s / L), inset((x + X) / (2 * X)))


def _roll_tube(sides: int) -> Builder:
    """LOD2: a plain tube at the roll's mean outer radius, resting on the floor."""
    t, lay, r0, a, Phi, L = _roll_numbers()
    X = PLAYMAT["h"] / 2
    zc = _roll_axis_z()
    b = Builder()
    ro = zc
    rings = {}
    for key, rr in (("o", ro), ("i", r0)):
        for sx in (-1, 1):
            rings[key, sx] = [b.v(sx * X, rr * math.cos(2 * math.pi * i / sides), zc + rr * math.sin(2 * math.pi * i / sides))
                              for i in range(sides)]
    for i in range(sides):
        j = (i + 1) % sides
        am = 2 * math.pi * (i + 0.5) / sides
        radial = (0.0, math.cos(am), math.sin(am))
        _face_out(b, [rings["o", -1][i], rings["o", -1][j], rings["o", 1][j], rings["o", 1][i]], radial, 0)
        _face_out(b, [rings["i", -1][i], rings["i", -1][j], rings["i", 1][j], rings["i", 1][i]], _mul(radial, -1), 1)
    for sx in (-1, 1):
        b.fill([rings["o", sx], rings["i", sx]], 1, 0, (float(sx), 0.0, 0.0))
    return b


def item_playmat_rolled() -> Item:
    p = PLAYMAT
    t, lay, r0, a, Phi, L = _roll_numbers()
    zc = _roll_axis_z()
    X = p["h"] / 2
    R = r0 + t * Phi / (2 * math.pi) + lay
    return Item(
        name="SM_CSK_Playmat_Rolled",
        lods=[Lod(_roll_builder(p["roll_facets"])), Lod(_roll_builder(8, chamfer=False)), Lod(_roll_tube(12))],
        materials=["M_CSK_Playmat", "M_CSK_Rubber"],
        projections={R_FRONT: _roll_proj, R_ROLL_END: _roll_end_proj(0), R_ROLL_END + 1: _roll_end_proj(1)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, 0, zc))],
        hulls=[((-X, -R, 0.0), (X, R, zc + R))], budget=BUDGETS["SM_CSK_Playmat_Rolled"],
        data={"footprint_mm": [2 * X, round(2 * R, 2), round(zc + R, 2)],
              "pose": "lying, the roll axis along X",
              "states": {"Flat": "SM_CSK_Playmat_Flat", "Rolled": "SM_CSK_Playmat_Rolled"},
              "roll": {"turns": round(Phi / (2 * math.pi), 2), "core_d_mm": 2 * r0, "pitch_mm": t,
                       "outer_d_mm": [round(2 * (r0 + t * (Phi - 2 * math.pi) / (2 * math.pi) + lay), 2),
                                      round(2 * R, 2)], "axis_z_mm": round(zc, 3)},
              "print": {"tile": [0, 0], "u": "centreline length from the core end / 609.6 (the flat mat's X)",
                        "v": "along the roll axis (the flat mat's Y)"},
              "reference": REF15,
              "notes": ["Sheet 15: cloth side out, the black base showing in the spiral end with a red line at each "
                        "wrap (a 0.3 cloth chamfer on each wrap's outer edge). The spiral winds from "
                        "a Ø 20 core at the M 2.0 pitch; its outer Ø runs 43.0-47.0 round the last turn (spec Ø 45 "
                        "is the D mean). 1.9 layers leave 0.1 gaps so the spiral reads at the ends.",
                        "The mat's free end is at the back, below the axis."]},
    )


# =========================================================================== E4 deck box (sheet 15 (1))

def _dip_half(segs: int, ext: float = 0.0) -> List[Tuple[float, float]]:
    """The right half of the wave dip, from the seam down to the flat bottom, as (x, dz) with dz <= 0 below the seam.
    ``ext`` > 0 prepends a point on the shoulder's entry line that far (in t) above the seam."""
    xt, xb, D, k = DECKBOX["dip"]
    pts = []
    if ext:
        pts.append((xt + (xt - xb) * ext, D * k * ext))
    for i in range(segs + 1):
        t = i / segs
        pts.append((xt - (xt - xb) * t, -D * ((1 - math.cos(math.pi * t)) / 2 * (1 - k) + k * t)))
    return pts


def _dip_profile(segs: int, ext: float) -> List[Tuple[float, float]]:
    """The full dip left to right along its bottom: left shoulder, down, the flat, up, right shoulder."""
    right = _dip_half(segs, ext)
    left = [(-x, z) for x, z in right]
    return left + list(reversed(right))


def _deck_outline(segs: int):
    c = DECKBOX
    return rounded_rect(c["w"], c["d"], c["corner_r"], segs)


def _deckbox_lod(level: int) -> Lod:
    """Sheet 15 base: a rounded-corner plastic tub up to the seam (66.5), the 68 x 71 cavity (M) on a 4 floor, the
    front wall's finger scoop matching the lid's wave dip, the hinge pin at the back top edge."""
    c = DECKBOX
    W, D, H = c["w"], c["d"], c["h"]
    zs = H - c["lid"]
    PLASTIC, CHROME = 0, 1
    segs = (c["corner_segs"], 1, 1)[level]
    pts = _deck_outline(segs)
    n = len(pts)
    b = Builder()
    lb, lt = b.loop(pts, 0.0), b.loop(pts, zs)
    for i in range(n):
        j = (i + 1) % n
        front = abs(pts[i][1] + D / 2) < 1e-6 and abs(pts[j][1] + D / 2) < 1e-6
        b.face((lb[i], lb[j], lt[j], lt[i]), PLASTIC, R_FRONT if front else 0)
    b.fill([lb], PLASTIC, 0, (0, 0, -1))
    b.fill([lt], PLASTIC, 0, (0, 0, 1))
    ops = []
    cav = Builder()
    iw, idp = c["in_w"], c["in_d"]
    cav.box((-iw / 2, -idp / 2, c["floor"]), (iw / 2, idp / 2, zs + 5.0), mat=PLASTIC)
    ops.append(("DIFFERENCE", cav))
    if level < 2:
        prof = _dip_profile((6, 3)[level], 0.5)
        cut = Builder()
        outline = [(x, zs + z) for x, z in prof] + [(prof[-1][0], zs + 5.0), (prof[0][0], zs + 5.0)]
        _prism_y(cut, outline, -D / 2 - 1.0, -D / 2 + (D - idp) / 2 + 1.0, mat=PLASTIC)
        ops.append(("DIFFERENCE", cut))
    extra = None
    if level == 0:
        extra = Builder()
        pd, pl = c["pin"]
        _cyl(extra, "x", (-pl / 2, D / 2, zs), pl, pd / 2, 13, CHROME)
    return Lod(b, bevel_mm=c["bevel"] if level == 0 else None, ops=ops, bevel_first=True, extra=extra)


def item_deckbox() -> Item:
    c = DECKBOX
    W, D, H = c["w"], c["d"], c["h"]
    zs = H - c["lid"]
    iw, idp, fl = c["in_w"], c["in_d"], c["floor"]
    sw, sh = c["sleeve"]
    iy0 = -idp / 2
    cards_loc = (0.0, iy0 + 1.0, fl + sh / 2)
    n_cards = int((idp - 1.0 - 4.0) // c["card_pitch"]) + 1
    return Item(
        name="SM_CSK_DeckBox", lods=[_deckbox_lod(k) for k in range(3)], materials=["M_CSK_Plastic", "M_CSK_Chrome"],
        projections={R_FRONT: lambda x, y, z: (inset((x + W / 2) / W), inset(z / zs))},
        sockets=[Socket("Seat", (0, 0, 0)),
                 Socket("Cards", cards_loc, (90.0, 0.0, 0.0), "CONTAIN"),
                 Socket("Lid", (0.0, D / 2, zs)),
                 Socket("Grip", (0.0, -D / 2, zs / 2)),
                 Socket("Stack", (0.0, 0.0, H))],
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, zs))], cls="Deck", budget=BUDGETS["SM_CSK_DeckBox"],
        data={"footprint_mm": [W, D, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "contain": {"Card": {"socket": "Cards", "cavity_mm": [[-iw / 2, -idp / 2, fl], [iw / 2, idp / 2, H - fl]],
                                   "accepts": ["Card"],
                                   "row": {"axis": "+Y", "pitch_mm": {"raw": S.CARD_STD["t"], "penny_sleeved": 0.5,
                                                                      "deck_sleeved": c["card_pitch"]},
                                           "max": n_cards},
                                   "pose": "standing upright, face to -Y; the Seat is the card's back face centre, "
                                           "1.0 off the front wall, at the height of a sleeved card (91) standing on "
                                           "the floor"}},
              "parts": {"Lid": {"mesh": "SM_CSK_DeckBox_Lid", "socket": "Lid", "type": "hinge", "axis": "X",
                                "range_deg": [0, c["open_deg"]], "open_rot_deg": [-c["open_deg"], 0.0, 0.0],
                                "note": "opens about -X (negative angles); pivot on the rear top edge of the base"}},
              "emblem": {"tile": [0, 0], "face": "the base's front face (below the scoop)",
                         "note": "UV only: sheet 15 shows the box plain; the Plastic material can print an emblem "
                                 "cell there (spec slot 'Print (emblem)')"},
              "reference": REF15,
              "notes": ["Sheet 15: blue matte plastic, 76 x 80 x 108, slightly rounded vertical edges (R 3); the lid "
                        "covers the top 41.5 (38 %), its front edge has a shallow wave dip (38 wide at the seam, "
                        "23.7 across its flat bottom, 9.4 deep) that fills the base's matching finger scoop.",
                        "Inside 68 x 71 x 100 (M): 4 walls (X), 4.5 (Y), 4 floor and lid top.",
                        "The hinge pin (Ø 3 x 35) sits on the rear top edge, on the hinge axis (sheet 15 open views)."]},
    )


def _deck_lid_builder(level: int) -> Builder:
    """Sheet 15 lid in its hinge frame (origin on the hinge axis at the base's rear top edge; closed, the lid covers
    y in [-80, 0], z in [0, 41.5], its front tongue down to -9.4): a chamfered top plate over four wall slabs and the
    wave-dip tongue, each a convex part (the outward-winding check). Parts meet 0.02 inside each other's faces."""
    c = DECKBOX
    W, D = c["w"], c["d"]
    Lh = c["lid"]
    e = 0.02
    tw = (W - c["in_w"]) / 2
    td = (D - c["in_d"]) / 2
    top_t = c["h"] - c["in_h"] - c["floor"]
    segs = (c["corner_segs"], 1, 1)[level]
    r = c["corner_r"]
    b = Builder()
    oy = -D / 2                                     # body y -> lid y

    def rr(dw, dr):
        return [(x, y + oy) for x, y in rounded_rect(W - 2 * dw, D - 2 * dw, max(0.3, r - dr), segs)]
    z0 = Lh - top_t
    xi = W / 2 - tw
    if level == 2:                                  # far LOD: five convex slabs, no tongue (the base drops its scoop)
        b.box((-W / 2 + e, -D + e, z0), (W / 2 - e, -e, Lh))
        for sx in (-1, 1):
            b.box((min(sx * W / 2, sx * xi), -D, 0.0), (max(sx * W / 2, sx * xi), 0.0, z0 + 0.5))
        for y0_, y1_ in ((-D + e, -D + td), (-td, -e)):
            b.box((-xi - 0.5, y0_, 0.0), (xi + 0.5, y1_, z0 + 0.5))
        return b
    if level == 0:                                  # the top plate, its top rim chamfered
        ch = c["lid_chamfer"]
        loops = [b.loop(rr(e, e), z0), b.loop(rr(e, e), Lh - ch), b.loop(rr(ch, ch), Lh)]
        b.fill([loops[0]], 0, 0, (0, 0, -1))
        _bridge(b, loops[0], loops[1], 0, centre=(0.0, oy))
        _bridge(b, loops[1], loops[2], 0, up=1.0, centre=(0.0, oy))
        b.fill([loops[2]], 0, 0, (0, 0, 1))
    else:
        b.prism(rr(e, e), z0, Lh)
    pts = rounded_rect(W, D, r, segs)
    k = segs + 1
    zw = z0 + 0.5
    for side in (1, -1):                            # side walls: full depth, the rounded corners
        if side > 0:
            ol = [(xi, -D / 2)] + pts[0:2 * k] + [(xi, D / 2)]
        else:
            ol = [(-xi, D / 2)] + pts[2 * k:4 * k] + [(-xi, -D / 2)]
        b.prism([(x, y + oy) for x, y in ol], 0.0, zw)
    xw = xi + 0.5
    b.box((-xw, -D / 2 + e + oy, 0.0), (xw, -D / 2 + td + oy, zw))      # front wall above the seam
    b.box((-xw, D / 2 - td + oy, 0.0), (xw, D / 2 - e + oy, zw))        # back wall
    prof = _dip_profile((6, 3)[level], 0.0)         # the tongue that fills the base's scoop, rising 0.5 into the
    xt = DECKBOX["dip"][0]                          # wall above the seam (hidden)
    _prism_y(b, [(-xt, 0.5)] + prof + [(xt, 0.5)], -D / 2 + 2 * e + oy, -D / 2 + td - e + oy, mat=0)
    return b


def item_deckbox_lid() -> Item:
    c = DECKBOX
    W, D = c["w"], c["d"]
    return Item(
        name="SM_CSK_DeckBox_Lid", lods=[Lod(_deck_lid_builder(k)) for k in range(3)], materials=["M_CSK_Plastic"],
        projections={}, sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-W / 2, -D, 0.0), (W / 2, 0.0, c["lid"]))], budget=BUDGETS["SM_CSK_DeckBox_Lid"],
        data={"part_of": "SM_CSK_DeckBox", "pivot": "hinge axis at the base's rear top edge (the Lid socket)",
              "reference": REF15,
              "notes": ["Sheet 15: the lid is the top 41.5 of the box, its front edge dipping 9.4 in a wave that fills "
                        "the base's finger scoop; top rim chamfered 0.8."]},
    )


# =========================================================================== E3 binder (sheet 14)

COVER, SPINE, CHROME = 0, 1, 2


def _panel(b: Builder, xs: float, xf: float, y0: float, y1: float, z0: float, z1: float, outer_top: bool,
           band_w: float, segs: int, round_fore: bool = True) -> None:
    """A padded cover board (Z prism) from its spine end ``xs`` to its fore edge ``xf`` (either order). Plan corners
    rounded at the fore edge. The outer face (top if ``outer_top``) is the navy field with the black spine band
    ``band_w`` wide at the spine end; the inner face, the spine-end face and the band's edges are black."""
    r = BINDER["corner_r"]
    sg = 1.0 if xf > xs else -1.0
    xb = xs + sg * band_w
    loc = [(0.0, y0), (abs(xb - xs), y0)]            # in a local frame: spine end at 0, fore edge at +L
    L = abs(xf - xs)
    if round_fore and segs:
        for cx, cy, a0 in ((L - r, y0 + r, -90.0), (L - r, y1 - r, 0.0)):
            for i in range(segs + 1):
                a = math.radians(a0 + 90.0 * i / segs)
                loc.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    else:
        loc += [(L, y0), (L, y1)]
    loc += [(abs(xb - xs), y1), (0.0, y1)]
    pts = [(xs + sg * x, y) for x, y in loc]
    n = len(pts)
    lb, lt = b.loop(pts, z0), b.loop(pts, z1)
    cx = (xs + xf) / 2
    for i in range(n):
        j = (i + 1) % n
        band_edge = i in (0, n - 2, n - 1)
        ids = [lb[i], lb[j], lt[j], lt[i]]
        c = _centre(b, ids)
        _face_out(b, ids, (c[0] - cx, c[1] - (y0 + y1) / 2, 0.0), SPINE if band_edge else COVER)
    outer, inner = (lt, lb) if outer_top else (lb, lt)
    no = (0.0, 0.0, 1.0 if outer_top else -1.0)
    _face_out(b, [outer[0], outer[1], outer[n - 2], outer[n - 1]], no, SPINE)
    b.fill([outer[1:n - 1]], COVER, 0, no)
    b.fill([inner], SPINE, 0, _mul(no, -1))


def _binder_dims():
    k = BINDER
    wc = k["w"] - k["t"]                            # cover board width, spine fold to fore edge (243.7)
    x0 = -(k["spine"] + wc) / 2                     # open flat: the spine's fold with the front cover
    xb = x0 + k["spine"]                            # the spine's fold with the back cover
    xe = xb + wc                                    # the back cover's fore edge
    xc = xb + k["ring_x"]                           # rail and ring centre
    R = (k["ring_od"] - k["wire"]) / 2              # ring centreline radius
    zc = k["clip"][2] - 3.0 + R                     # ring bottom (centreline) 3 below the clip top
    zp = k["clip"][2] + 0.2 + k["core"] / 2 + k["pad"] + 0.05   # page mid-plane at rest: its pads clear the clips
    dx = math.sqrt(R * R - (zc - zp) ** 2)          # the ring crosses the page plane here (the hole centre)
    return dict(wc=wc, x0=x0, xb=xb, xe=xe, xc=xc, R=R, zc=zc, zp=zp, dx=dx, hh=k["h"] / 2)


def _ring(b: Builder, xc: float, y: float, zc: float, R: float, rw: float, sides: int, segs: int, gap_deg: float) -> None:
    """An O-ring of round wire in the XZ plane, open ``gap_deg`` either side of its bottom (the ends meet inside the
    clip): ``segs`` segments round the arc, ``sides`` round the wire."""
    a0 = math.radians(-90.0 + gap_deg)
    a1 = math.radians(270.0 - gap_deg)
    rings = []
    for s in range(segs + 1):
        a = a0 + (a1 - a0) * s / segs
        ca, sa = math.cos(a), math.sin(a)
        P = (xc + R * ca, y, zc + R * sa)
        ring = []
        for i in range(sides):
            be = 2 * math.pi * i / sides
            ring.append(b.v(P[0] + rw * math.cos(be) * ca, P[1] + rw * math.sin(be), P[2] + rw * math.cos(be) * sa))
        rings.append((P, ring))
    for s in range(segs):
        (P0, r0), (P1, r1) = rings[s], rings[s + 1]
        for i in range(sides):
            j = (i + 1) % sides
            ids = [r0[i], r0[j], r1[j], r1[i]]
            c = _centre(b, ids)
            Pm = _mul(_add(P0, P1), 0.5)
            _face_out(b, ids, _add(c, _mul(Pm, -1)), CHROME)


def _binder_hardware(level: int) -> Builder:
    """Sheet 14's ring mechanism on the back cover by the spine: a chrome dome rail, lever-booster ends with a round
    stud, a knuckle clip under each ring and three O-rings at the M hole pitch (108)."""
    k, m = BINDER, _binder_dims()
    b = Builder()
    xc, t = m["xc"], k["t"]
    rw_, rh = k["rail"]
    half = k["rail_len"] / 2
    if level < 2:                                   # dome rail: a circular arc 22 wide x 7 high, sunk 0.5
        Rr = ((rw_ / 2) ** 2 + rh ** 2) / (2 * rh)
        zr = t + rh - Rr
        a_end = math.asin((rw_ / 2) / Rr)
        prof = [(xc - rw_ / 2, t - 0.5), (xc + rw_ / 2, t - 0.5)]
        n_arc = 6
        for i in range(n_arc + 1):
            a = -a_end + 2 * a_end * i / n_arc      # from the right edge over the top to the left
            prof.append((xc + Rr * math.sin(-a), zr + Rr * math.cos(a)))
        _prism_y(b, prof, -half, half, mat=CHROME)
    else:
        b.box((xc - rw_ / 2, -half, t - 0.5), (xc + rw_ / 2, half, t + rh), mat=CHROME)
    bl, bh, sd, sh, so = k["booster"]
    for sy in (-1, 1):                              # lever boosters: a round-ended block and its stud
        y_in = sy * (half - 1.0)
        na = 7 if level < 2 else 2                  # the round end: a half disc (sheet 14 close-up)
        pts = [(xc - rw_ / 2, 0.0), (xc + rw_ / 2, 0.0)] + \
            [(xc + rw_ / 2 * math.cos(math.pi * i / na), rw_ / 2 * math.sin(math.pi * i / na)) for i in range(1, na)]
        pts = [(x, y_in + sy * max(y, 0.0) + sy * (bl - rw_ / 2)) if y > 0 else (x, y_in) for x, y in pts]
        if sy < 0:
            pts = list(reversed(pts))
        b.prism(pts, t - 0.5, t + bh, mat=CHROME)
        if level == 0:
            _cyl(b, "z", (xc, sy * (half + so), t + bh - 0.2), sh + 0.2, sd / 2, 13, CHROME, caps=(False, True))
    cw, cd, ctop = k["clip"]
    R, zc = m["R"], m["zc"]
    for yr in (-k["hole_pitch"], 0.0, k["hole_pitch"]):
        if level < 2:
            b.box((xc - cw / 2, yr - cd / 2, t + rh - 3.0), (xc + cw / 2, yr + cd / 2, ctop), mat=CHROME)
        sides, segs = ((13, 16), (8, 10), (4, 6))[level]
        _ring(b, xc, yr, zc, R, k["wire"] / 2, sides, segs, k["ring_gap_deg"] if level < 2 else 30.0)
    return b


def _binder_body_builder(level: int) -> Builder:
    """Open flat (sheet 14 open view): the spine panel and the back cover, both padded, meeting at a hinge crease."""
    k, m = BINDER, _binder_dims()
    t, hh = k["t"], m["hh"]
    b = Builder()
    segs = (3, 1, 0)[level]
    b.box((m["x0"], -hh, 0.0), (m["xb"], hh, t), mat=SPINE, regions={"nz": R_LABEL})
    _panel(b, m["xb"] - 0.5, m["xe"], -hh, hh, 0.0, t, False, k["band"] - t + 0.5, segs, round_fore=level < 2)
    return b


def _ring_stations():
    """Ring_01..20: the page's pivot (its middle hole) along the middle ring's arc, from the page lying flat on the
    right (at rest on the clips) over the top to lying flat on the left; the page turns 0 -> 180 about Y."""
    k, m = BINDER, _binder_dims()
    a0 = math.atan2(m["zp"] - m["zc"], m["dx"])
    a1 = math.pi - a0
    out = []
    n = k["stations"]
    for i in range(n):
        f = i / (n - 1)
        a = a0 + (a1 - a0) * f
        loc = (m["xc"] + m["R"] * math.cos(a), 0.0, m["zc"] + m["R"] * math.sin(a))
        out.append(Socket(f"Ring_{i + 1:02d}", tuple(round(v, 4) for v in loc), (0.0, round(-180.0 * f, 4), 0.0)))
    return out


def item_binder_body() -> Item:
    k, m = BINDER, _binder_dims()
    t, hh = k["t"], m["hh"]
    lods = [Lod(_binder_body_builder(0), bevel_mm=k["pad_bevel"], bevel_segments=2, extra=_binder_hardware(0)),
            Lod(_binder_body_builder(1), extra=_binder_hardware(1)),
            Lod(_binder_body_builder(2), extra=_binder_hardware(2))]
    xc, R = m["xc"], m["R"]
    rw_ = k["rail"][0]
    half = k["rail_len"] / 2 + k["booster"][0] - 1.0
    top = m["zc"] + R + k["wire"] / 2
    return Item(
        name="SM_CSK_Binder_Body", lods=lods,
        materials=["M_CSK_BinderCover", "M_CSK_BinderSpine", "M_CSK_Chrome"],
        projections={R_LABEL: _planar(m["x0"], -hh, k["spine"], k["h"], tile_v=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Cover", (m["x0"], 0.0, t))] + _ring_stations(),
        hulls=[((m["x0"], -hh, 0.0), (m["xe"], hh, t)),
               ((xc - rw_ / 2, -half, t), (xc + rw_ / 2, half, k["rail"][1] + t)),
               ((xc - R - k["wire"] / 2, -k["hole_pitch"] - 4.0, k["rail"][1] + t),
                (xc + R + k["wire"] / 2, k["hole_pitch"] + 4.0, top))],
        budget=BUDGETS["SM_CSK_Binder_Body"],
        data={"footprint_mm": [round(m["xe"] - m["x0"], 3), k["h"], round(top, 3)],
              "pose": "open flat on its back, spine panel at -X, the rings up (sheet 14 open view)",
              "parts": {"Cover": {"mesh": "SM_CSK_Binder_Cover", "socket": "Cover", "type": "hinge", "axis": "Y",
                                  "range_deg": [0, 150], "open_rot_deg": [0.0, 0.0, 0.0],
                                  "note": "modelled lying open flat (0); positive Y angles lift it over the spine; "
                                          "past ~150 it meets the ring tops. The closed binder is the Closed mesh"},
                        "Page": {"mesh": "SM_CSK_Binder_Page", "sockets": [f"Ring_{i:02d}" for i in
                                                                           range(1, k["stations"] + 1)],
                                 "type": "path", "note": "attach a page at Ring_01 (at rest on the right); a turn "
                                 "moves its pivot along Ring_01..20 over the ring arc, rotating 0 -> 180 about Y; "
                                 "Ring_20 = lying on the left"}},
              "rings": {"centre_x_mm": round(xc, 3), "centre_z_mm": round(m["zc"], 3), "radius_mm": round(R, 3),
                        "y_mm": [-k["hole_pitch"], 0.0, k["hole_pitch"]]},
              "label": {"tile": [0, 1], "face": "the spine's outer face (underneath when open flat)"},
              "reference": REF14,
              "notes": ["Sheet 14: navy padded covers, the black spine band wrapping 34 onto each cover, black "
                        "inside; stitch lines (4 in from the edges) are normal-map detail.",
                        "Rings: sheet 14's round O-rings (3) on a chrome dome rail with lever boosters at both ends "
                        "(the spec/prompt said D-rings; the picture wins).",
                        "Open flat: pages can only turn over the rings with the spine flat; the spine (57, sheet 14) "
                        "lies between the covers."]},
    )


def item_binder_cover() -> Item:
    """The front cover, lying open flat left of the spine; pivot on its fold with the spine (inner face level)."""
    k, m = BINDER, _binder_dims()
    t, hh, wc = k["t"], m["hh"], m["wc"]

    def build(level):
        b = Builder()
        _panel(b, 0.0, -wc, -hh, hh, -t, 0.0, False, k["band"] - t, (3, 1, 0)[level], round_fore=level < 2)
        return b
    return Item(
        name="SM_CSK_Binder_Cover",
        lods=[Lod(build(0), bevel_mm=k["pad_bevel"], bevel_segments=2), Lod(build(1)), Lod(build(2))],
        materials=["M_CSK_BinderCover", "M_CSK_BinderSpine"], projections={},
        sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-wc, -hh, -t), (0.0, hh, 0.0))], budget=BUDGETS["SM_CSK_Binder_Cover"],
        data={"part_of": "SM_CSK_Binder_Body", "pivot": "the fold with the spine, at the inner face (Cover socket)",
              "reference": REF14,
              "notes": ["Sheet 14: navy outside with the 34 black band at the spine end, black inside."]},
    )


def _page_layout():
    """Pocket rects (x0, y0, x1, y1) in the page frame (origin = the middle hole's centre on the mid-plane), rows
    from the top, columns from the hole strip; and the page rect."""
    k = BINDER
    pw, ph = k["page"]
    qx, qy = k["pocket"]
    px0 = -k["hole_inset"]
    s = k["seam"]
    mv = (ph - 3 * qy - 2 * s) / 2
    rects = []
    for r in range(3):
        y1 = ph / 2 - mv - r * (qy + s)
        for c in range(3):
            x0 = px0 + k["strip"] + c * (qx + s)
            rects.append((x0, y1 - qy, x0 + qx, y1))
    return rects, (px0, -ph / 2, px0 + pw, ph / 2)


def _page_builder(level: int) -> Builder:
    """Sheet 14's 9-pocket page: a welded core film with 3 punched holes, and a raised pocket pad for each of the 9
    pockets on both faces; the gaps between pads are the welded seams."""
    k = BINDER
    rects, (x0, y0, x1, y1) = _page_layout()
    hc, pad = k["core"] / 2, k["pad"]
    b = Builder()
    outer = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if level < 2:
        sides = (10, 6)[level]
        holes2 = [circle(k["hole_d"] / 2, sides, 0.0, yh) for yh in (-k["hole_pitch"], 0.0, k["hole_pitch"])]
        lb, lt = b.loop(outer, -hc), b.loop(outer, hc)
        hb = [b.loop(hp, -hc) for hp in holes2]
        ht = [b.loop(hp, hc) for hp in holes2]
        _bridge(b, lb, lt, 0, centre=((x0 + x1) / 2, 0.0))
        for hp, bl, tl in zip(holes2, hb, ht):            # the hole walls face into the hole
            yh = sum(q[1] for q in hp) / len(hp)
            for i in range(sides):
                j = (i + 1) % sides
                ids = [bl[i], bl[j], tl[j], tl[i]]
                c = _centre(b, ids)
                _face_out(b, ids, (-c[0], yh - c[1], 0.0), 0)
        b.fill([lt] + ht, 0, 0, (0, 0, 1))
        b.fill([lb] + hb, 0, 0, (0, 0, -1))
    else:
        b.box((x0, y0, -hc), (x1, y1, hc))
    for (rx0, ry0, rx1, ry1) in rects:
        if level == 0:
            b.box((rx0, ry0, hc - 0.05), (rx1, ry1, hc + pad))
            b.box((rx0, ry0, -hc - pad), (rx1, ry1, -hc + 0.05))
        else:
            b.face((b.v(rx0, ry0, hc + pad), b.v(rx1, ry0, hc + pad), b.v(rx1, ry1, hc + pad), b.v(rx0, ry1, hc + pad)))
            b.face((b.v(rx0, ry1, -hc - pad), b.v(rx1, ry1, -hc - pad), b.v(rx1, ry0, -hc - pad), b.v(rx0, ry0, -hc - pad)))
    return b


def item_binder_page() -> Item:
    k = BINDER
    rects, (x0, y0, x1, y1) = _page_layout()
    hc, pad = k["core"] / 2, k["pad"]
    socks = [Socket("Seat", (0, 0, 0))]
    front, back = [], []
    for i, (rx0, ry0, rx1, ry1) in enumerate(rects):
        cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
        front.append(Socket(f"Pocket_F{i + 1:02d}", (round(cx, 4), round(cy, 4), hc), kind="CONTAIN"))
    for i in range(9):                                 # numbered as seen from the back: top-left = page top-right
        r, c = divmod(i, 3)
        rx0, ry0, rx1, ry1 = rects[r * 3 + (2 - c)]
        cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
        back.append(Socket(f"Pocket_B{i + 1:02d}", (round(cx, 4), round(cy, 4), -hc), (0.0, 180.0, 0.0), "CONTAIN"))
    xa, xb_ = rects[0][0], rects[2][2]
    ya, yb = rects[6][1], rects[0][3]
    return Item(
        name="SM_CSK_Binder_Page", lods=[Lod(_page_builder(i)) for i in range(3)], materials=["M_CSK_Film"],
        projections={}, sockets=socks + front + back,
        hulls=[((x0, y0, -1.0), (x1, y1, 1.0))], budget=BUDGETS["SM_CSK_Binder_Page"],
        data={"footprint_mm": [k["page"][0], k["page"][1], round(2 * (hc + pad), 3)], "part_of": "SM_CSK_Binder_Body",
              "pivot": "the middle hole's centre on the page mid-plane (attach to Ring_NN)",
              "contain": {"CardFront": {"sockets": [s.name for s in front], "accepts": ["Card"],
                                        "cavity_mm": [[xa, ya, hc], [xb_, yb, hc + pad]]},
                          "CardBack": {"sockets": [s.name for s in back], "accepts": ["Card"],
                                       "cavity_mm": [[xa, ya, -hc - pad], [xb_, yb, -hc]]}},
              "reference": REF14,
              "notes": ["Sheet 14: clear 9-pocket page (M 220.7 x 293.7, pockets M 65.1 x 90.5), 3 punched holes "
                        "at the M 108 pitch, welded seams (2.5) between raised pocket pads; weld dots and the "
                        "pocket lips are texture.",
                        "M conflict: the page (293.7) is 1.6 taller than the cover (292.1), so it overhangs 0.8 top "
                        "and bottom in the open binder (open question)."]},
    )


def _binder_closed_builder(level: int) -> Builder:
    """Closed binder lying (then stood up): back cover, front cover, the spine panel standing between them, all
    padded; the page block inside (sheet 14 closed views)."""
    k = BINDER
    t, hh = k["t"], k["h"] / 2
    xo = -k["w"] / 2
    xi = xo + t
    xe = k["w"] / 2
    sp = k["spine"]
    segs = (3, 1, 0)[level]
    b = Builder()
    b.box((xo, -hh, 0.0), (xi, hh, sp), mat=SPINE, regions={"nx": R_LABEL})
    _panel(b, xi - 0.5, xe, -hh, hh, 0.0, t, False, k["band"] - t + 0.5, segs, round_fore=level < 2)
    _panel(b, xi - 0.5, xe, -hh, hh, sp - t, sp, True, k["band"] - t + 0.5, segs, round_fore=level < 2)
    return b


def _binder_pages_block() -> Builder:
    k, m = BINDER, _binder_dims()
    t, hh = k["t"], k["h"] / 2
    xi = -k["w"] / 2 + t
    xe = k["w"] / 2
    x0 = xi + k["ring_x"] + m["dx"] - k["hole_inset"]      # the pages' left edge, as in the open binder
    b = Builder()
    b.box((x0, -hh + 1.0, t + 0.5), (xe - 1.2, hh - 1.0, k["spine"] - t - 0.5), mat=2)
    return b


def _stand_up(b: Builder) -> Builder:
    """Lying closed (front cover up, top edge +Y) -> standing: front cover toward -Y, top edge up, spine at -X."""
    sp, hh = BINDER["spine"], BINDER["h"] / 2
    b.verts = [(x, sp / 2 - z, y + hh) for x, y, z in b.verts]
    return b


def item_binder_closed() -> Item:
    k = BINDER
    W, D, H = k["w"], k["spine"], k["h"]
    lods = [Lod(_stand_up(_binder_closed_builder(0)), bevel_mm=k["pad_bevel"], bevel_segments=2,
                extra=_stand_up(_binder_pages_block())),
            Lod(_stand_up(_binder_closed_builder(1)), extra=_stand_up(_binder_pages_block())),
            Lod(_stand_up(_binder_closed_builder(2)), extra=_stand_up(_binder_pages_block()))]
    return Item(
        name="SM_CSK_Binder_Closed", lods=lods,
        materials=["M_CSK_BinderCover", "M_CSK_BinderSpine", "M_CSK_BinderPages"],
        projections={R_LABEL: lambda x, y, z: (inset((D / 2 - y) / D), 1.0 + inset(z / H))},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Stack", (0, 0, H)),
                 Socket("Face", (0, -D / 2, H / 2), (90.0, 0.0, 0.0))],
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))], cls="Binder", budget=BUDGETS["SM_CSK_Binder_Closed"],
        data={"footprint_mm": [W, D, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "pose": "standing, the front cover toward the customer (-Y), the spine at -X",
              "label": {"tile": [0, 1], "face": "the spine (-X)"},
              "reference": REF14,
              "notes": ["Sheet 14 closed views: navy padded covers, a 57 black spine whose band wraps 34 onto each "
                        "cover, rounded padded edges.",
                        "The page block inside is opaque (M_CSK_BinderPages, for bulk shelf dressing); it stops 1 "
                        "inside the covers top and bottom (the M page is 1.6 taller than the M cover)."]},
    )


# =========================================================================== registry

ITEMS = {
    "e_play_die_d6": item_die_d6,
    "e_play_die_d20": item_die_d20,
    "e_play_token_22": item_token,
    "e_play_playmat_flat": item_playmat_flat,
    "e_play_playmat_rolled": item_playmat_rolled,
    "e_play_deckbox": item_deckbox,
    "e_play_deckbox_lid": item_deckbox_lid,
    "e_play_binder_body": item_binder_body,
    "e_play_binder_cover": item_binder_cover,
    "e_play_binder_page": item_binder_page,
    "e_play_binder_closed": item_binder_closed,
}
