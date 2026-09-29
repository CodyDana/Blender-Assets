"""Card Shop Kit family b_pack: sealed product of CARDSHOP_KIT_SPEC.md 3.B rows B1-B3 and B7 (P3-P5).

    B1 booster pack: Open, Wrapper, Strip states (Sealed is geom.item_pack)   reference sheet 4 (csk_pack.png)
    B2 booster display box L + its lid (+ the sealed L, as the S)            reference sheet 5 (csk_booster_box.png)
    B3 telescoping collector box + lid                                       reference sheet 10 (1)
    B7 sealed starter-deck tuck box                                          reference sheet 10 (2)

The G1 items in geom.py are the worked examples, and this module reuses them: the pack's numbers (spec.PACK_STD), its
column / tooth layout and edge-band UV idea; the S box's shell, window cut, dieline, lid and sealed builders
(geom._box_shell, _window_outline, _dieline, item_box_lid, item_box_sealed) run with the L numbers.

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = a
spec estimate with a source range. Millimetres; Seat frame: +X right, +Y away from the customer, +Z up. Where a
sheet's picture disagrees with an E number the picture wins (logged on the number); where it disagrees with a printed
or M number, the number wins (REFERENCE_LOG "Scale rule for these sheets").

Noise (the crumpled wrapper, the torn edges) is a deterministic integer hash: no ``random`` module state, so every
build is byte-identical.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from . import geom as G
from . import spec as S
from .geom import (R_BACK, R_EDGE, R_FRONT, Item, Lod, Socket, _box_shell, _face_out, _planar, _prism_y,
                   _window_outline, inset)
from .shapes import Builder, rounded_rect

# =========================================================================== numbers

OPEN = dict(                    # B1 Open: sheet 4 (opened view + close-up); the rest is spec.PACK_STD
    tear=12.0,                  # E (spec): the tear strip is 67 x 12, so the mouth is 12 below the sealed top
    dip=8.0, dip_skew=0.35,     # sheet 4: the front skin's torn edge sags about 8 at the middle, lowest right of centre
    sag=1.0,                    # sheet 4: the back skin's edge is nearly straight (1 sag)
    gape=(6.5, 2.0, 30.0),      # sheet 4 "gaping slightly": front lifts 6.5, back drops 2.0, over the top 30 (E)
    jag=0.5,                    # sheet 4 close-up: the tear is a fine serration at the tooth pitch, +-0.5 (E)
    film=0.12,                  # E: foil laminate thickness (the silver inside is its own surface)
)

STRIP = dict(                   # B1 Strip: sheet 4 (the strip on its own)
    h=12.0,                     # E (spec 67 x 12); sheet 4 measures 12.1 at 19.4 px/mm
    jag=0.6,                    # sheet 4: the torn lower edge, irregular, +-0.6
    crumple=0.45,               # sheet 4: the torn foil below the seal strip is wrinkled, +-0.45
)

WRAPPER = dict(                 # B1 Wrapper: sheet 4 (the crumpled wrapper), lying back up (the fin seal shows)
    t=(0.45, 0.2, 0.3),         # E: body thickness (two skins), bottom skin only (the silver bites), crimp
    amp=2.0, creases=18,        # E: crumple crease height and count (sheet 4: sharp facets about 10-20 mm)
    jitter=(1.0, 1.5, 0.35),    # E: interior vertex jitter x, y, z (breaks the grid into irregular facets)
    ramp=0.35,                  # E: the torn top-skin edge round a bite
    # sheet 4: the top skin is torn away along both long edges, showing the silver inside of the bottom skin:
    # (side, centre y, half length, depth); left bite long and deep, right bite lower and shorter
    bites=((-1, 4.0, 34.0, 15.0), (1, -30.0, 24.0, 12.0)),
    bite_jag=1.2,               # E: torn-edge irregularity of a bite, per row
    margin=1.5,                 # E: the bite column's rest position off the edge where there is no bite
)

BOX_L = dict(                   # B2 L: sheet 5 (large); the S design (geom) with these numbers
    S.BOX_BOOSTER_S,
    w=190.0, d=76.0, h=140.0,   # E (spec: the M "typical" size [D9])
    packs=(2, 12),              # D (spec 3.B map): 2 across x 12 deep, standing
    pack_pitch=5.0,             # D (spec 3.B map)
    pack_gap=1.0,               # E: the two pack columns side by side, 1 apart (sheet 5 L: no centre divider)
    # sheet 5 L, measured on the opened 3/4 view (4.95 px/mm across, 3.6-3.7 px/mm down the front):
    window=(168.0, 129.0, 73.0, 6.0),   # die-cut width at the rim, at the bottom, depth, bottom corner R
    divider=None,               # sheet 5 L shows no centre divider (the S has one)
    tab=(92.0, 20.0, 6.0),      # header tab W x H x R: W measured (0.48 of the lid), H as the S (tab/lid ratio 0.4 both)
)

COLLECTOR = dict(               # B3: sheet 10 (1)
    w=190.0, d=89.0, h=165.0,   # E (spec; printed on sheet 10). The picture's top view reads ~155 deep: number wins
    board=2.0,                  # E (spec)
    lid_depth=123.0,            # sheet 10: the picture wins over the spec's E 30 (REFERENCE_LOG sheet 10 notes)
    band=42.0,                  # D: 165 - 123 (sheet 10: about 42 of light-blue base shows under the lid)
    clear=0.2,                  # E: sliding clearance a side between the neck and the lid
    neck_top=160.0,             # E: the navy neck (sheet 10 lid-lifted view) stops 3 under the lid's inner top
    tray_drop=3.0,              # sheet 10: the black tray sits a little under the navy neck rim (E 3)
    wall=1.5, rib=2.5,          # E: tray margins and ribs between pockets
    pack_floor=42.0,            # E: pack pocket floor; the packs' tops are 2 proud of the tray, 4 under the lid
    pack_pitch=4.0, pack_gap=3.0,   # D (spec: 2 x 4 standing on edge, 4 pitch); rib between the two columns E
    die=16.0,                   # M [D20]: the d6; 6 dice 2 x 3 (sheet 10)
    front=(36.0, 66.0, 70.0),   # E: dice, cards, sleeves pocket widths (dice 2 x 16 + 4; card 63 + 3; sleeve 66 + 4)
    card_h=88.0, sleeve_h=91.0,  # M [D1] card 88, sleeve 91 (standing: the pockets are 58 deep, see notes)
)

TUCK = dict(                    # B7: sheet 10 (2)
    w=70.0, d=30.0, h=95.0,     # E (spec, no source)
    board=0.4,                  # E: folding-carton board (the thumb cut's depth)
    notch=(30.0, 10.0, 8),      # sheet 10 close-up: half-moon thumb cut, width x depth, arc segments
    film=0.3, film_r=2.0,       # sheet 10 "shrink-wrapped": film clearance, soft vertical corners (as the S sealed box)
    tuck=15.0,                  # E: tuck flap depth (dieline only)
    bevel=0.3,                  # E: folded-board edge
)

BUDGETS = {
    "SM_CSK_Pack_Std_Open": 1950,       # spec 250 (E): 27 ribbed teeth + fin (as the Sealed, 1500) + the silver inside
    "SM_CSK_Pack_Std_Wrapper": 1750,    # spec 200 (E): both crimps' 27 teeth (sheet 4) + crumple facets
    "SM_CSK_Pack_Std_Strip": 750,       # spec 40 (E): 27 ribbed teeth + the torn edge (sheet 4)
    "SM_CSK_Box_Booster_L": 400,
    "SM_CSK_Box_Booster_L_Lid": 150,
    "SM_CSK_Box_Booster_L_Sealed": 400,
    "SM_CSK_Box_Collector": 600,
    "SM_CSK_Box_Collector_Lid": 300,
    "SM_CSK_Deck_Tuck": 150,
}

CLASSES = {                     # spec 4.2 (the same values as fam_a_shelving's; setdefault keeps the first)
    "BoxL": S.ItemClass("BoxL", (190.0, 76.0, 140.0), (200.0, 86.0)),
    "BoxC": S.ItemClass("BoxC", (190.0, 89.0, 165.0), (200.0, 99.0)),
}

R_IN_A, R_IN_B = 8, 9           # non-print planar regions in the U -1 tile (the silver inside, torn edges)

# =========================================================================== shared helpers


def _hash(*a: int) -> float:
    """A deterministic hash of integers to [0, 1)."""
    h = 0x811C9DC5
    for v in a:
        h ^= (int(v) * 0x9E3779B1) & 0xFFFFFFFF
        h = (h * 0x01000193) & 0xFFFFFFFF
        h ^= h >> 15
    h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
    h ^= h >> 12
    return h / 4294967296.0


def _smooth(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def _dedupe(ids: Sequence[int]) -> List[int]:
    out = []
    for i in ids:
        if not out or out[-1] != i:
            out.append(i)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _zip(b: Builder, A: Sequence[int], B: Sequence[int], up: bool, mat: int, region: int) -> None:
    """Triangulate the band between two rows of vertex ids (each sorted by x, same x span; row A at the lower y).
    ``up`` faces +Z. Shared ids (a pinched corner) drop their degenerate triangle."""
    i = j = 0
    while i < len(A) - 1 or j < len(B) - 1:
        adv_a = j == len(B) - 1 or (i < len(A) - 1 and b.verts[A[i + 1]][0] <= b.verts[B[j + 1]][0])
        tri = (A[i], A[i + 1], B[j]) if adv_a else (A[i], B[j + 1], B[j])
        if adv_a:
            i += 1
        else:
            j += 1
        if len(set(tri)) < 3:
            continue
        b.face(tri if up else tuple(reversed(tri)), mat, region)


def _band_proj(k: int, along, zmax: float):
    """The U -1 tile edge bands of geom._pack_edge_projections, with V scaled by this mesh's height."""
    return lambda x, y, z: (-0.99 + 0.245 * k + 0.235 * along(x, y), 0.02 + 0.2 * z / zmax)


def _pack_edge_proj(w: float, y0: float, h: float, zmax: float) -> Dict[int, object]:
    """Edge bands for a pack-like mesh spanning x in [-w/2, w/2], y in [y0, y0 + h]: -y end, +x side, +y end, -x
    side (regions R_EDGE .. R_EDGE + 3)."""
    return {R_EDGE: _band_proj(0, lambda x, y: (x + w / 2) / w, zmax),
            R_EDGE + 1: _band_proj(1, lambda x, y: (y - y0) / h, zmax),
            R_EDGE + 2: _band_proj(2, lambda x, y: (w / 2 - x) / w, zmax),
            R_EDGE + 3: _band_proj(3, lambda x, y: (y0 + h - y) / h, zmax)}


def _in_proj(w: float, y0: float, h: float, half: int):
    """Planar XY into the U -1 tile above the edge bands: half 0 = u -0.99..-0.51, half 1 = -0.49..-0.01."""
    u0 = -0.99 + 0.48 * half
    return lambda x, y, z: (u0 + 0.48 * (x + w / 2) / w, 0.3 + 0.68 * (y - y0) / h)


def _pack_cols(level: int):
    """(n2, coarse columns, teeth, ribs, fin) per LOD, as geom.item_pack: LOD0 27 ribbed teeth + fin, LOD1 9 teeth,
    LOD2 no teeth (4 columns). Columns are indices k of the crimp line x = -w/2 + w k / n2."""
    p = S.PACK_STD
    if level == 0:
        n2 = 2 * p["teeth"]
        fk0, fk1, fw0, fw1, _ = p["fin"]
        return n2, sorted({0, 2, 5, 10, 15, 20, fw0, fk0, n2 // 2, fk1, fw1, n2 - 20, n2 - 15, n2 - 10, n2 - 5,
                           n2 - 2, n2}), True, True, True
    if level == 1:
        return 18, [0, 2, 5, 9, 13, 16, 18], True, False, False
    return 4, [0, 1, 2, 3, 4], False, False, False


def _side_faces(b: Builder, top: List[List[int]], bot: List[List[int]], regions=(R_EDGE + 3, R_EDGE + 1)) -> None:
    """The two long sides of a pack-like shell: rows of (top ids, bottom ids) sorted by x; a pinched corner (top and
    bottom the same vertex) closes with a triangle."""
    for r in range(len(top) - 1):
        for side, (outward, region) in enumerate((((-1, 0, 0), regions[0]), ((1, 0, 0), regions[1]))):
            c = 0 if side == 0 else -1
            ids = _dedupe([bot[r][c], bot[r + 1][c], top[r + 1][c], top[r][c]])
            if len(ids) >= 3:
                _face_out(b, ids, outward, 0, region)


def _end_faces(b: Builder, top: List[int], bot: List[int], outward, region: int, mat: int = 0) -> None:
    """A serrated / torn end: quads between the top and bottom edge rows (x-sorted)."""
    for k in range(len(top) - 1):
        ids = _dedupe([bot[k], bot[k + 1], top[k + 1], top[k]])
        if len(ids) >= 3:
            _face_out(b, ids, outward, mat, region)


def _aabb(b: Builder):
    xs, ys, zs = zip(*b.verts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _hull(b: Builder):
    """One box hull over a handheld builder, at least 2 mm thick, centred (spec 4.6)."""
    (x0, y0, z0), (x1, y1, z1) = _aabb(b)
    zc, t = (z0 + z1) / 2, max(z1 - z0, S.HANDHELD_HULL_MIN_T)
    return ((x0, y0, zc - t / 2), (x1, y1, zc + t / 2))


# =========================================================================== B1 Open (sheet 4)

def _bump(u: float) -> float:
    """The front tear's sag profile across the mouth, 0 at the side folds, peak 1 right of centre."""
    a = OPEN["dip_skew"]
    peak = max((1 - t * t) * (1 + a * t) for t in (i / 200.0 for i in range(-200, 201)))
    return max(0.0, (1 - u * u) * (1 + a * u)) / peak


def _open_builder(level: int) -> Builder:
    """Sheet 4, opened: the top crimp torn off 12 below the sealed top along a fine serrated tear; the front skin's
    edge sags in the middle and both skins spread into a lens-shaped mouth; the foil's silver inside is a second
    surface (inner front + inner back, joined at the side folds and the bottom seal) with a lip along the tear. The
    bottom crimp, its 27 ribbed teeth and the back fin seal are the Sealed pack's (geom._pack_builder numbers).
    A closed shell: the outer skins, the inner skins and the lips meet at one pinched vertex at each mouth corner."""
    p, o = S.PACK_STD, OPEN
    w, h, et = p["w"], p["h"], p["edge_t"]
    n2, cols, teeth, ribs, fin = _pack_cols(level)
    fine = list(range(n2 + 1))
    crimp = fine if teeth else cols
    mouth = fine if level < 2 else cols
    fk0, fk1, fin_h = p["fin"][0], p["fin"][1], p["fin"][4]
    hb = (p["t"] - fin_h) / 2
    ys = h / 2 - p["crimp"]
    yj = ys + p["seal"]
    yt = h / 2 - o["tear"]
    gF, gB, gl = o["gape"]
    zm = hb + fin_h + gB                        # LOD0's lowest point (back skin, fin, mouth) at z 0
    film = o["film"]
    xk = lambda k: -w / 2 + w * k / n2
    vfr = {0: [0, .04, .12, .25, .45, .65, .82, .94, 1.0], 1: [0, .15, .5, .8, .93, 1.0]}.get(level, [0, .5, .85, 1.0])
    fine_from = {0: .94, 1: .93}.get(level, 2.0)      # rows next to the jagged mouth use every column (no fan folds)
    f_fb = {0: .65, 1: .5}.get(level, .5)            # the inner skins meet in a false bottom here (cards fill below)

    def half(x, y):
        fx = max(0.0, 1 - abs(2 * x / w) ** 4)
        fy = max(0.0, 1 - abs(y / ys) ** 4) if y < 0 else 1.0     # tapers into the bottom seal only
        return et / 2 + (hb - et / 2) * fx * fy

    def gape(x, y):
        return _smooth((y - (yt - gl)) / gl) * max(0.0, 1 - (2 * x / w) ** 2)

    def ymouth(k, front, jag):
        u = 2 * xk(k) / w
        y = yt - (o["dip"] * _bump(u) if front else o["sag"] * (1 - u * u))
        if jag and 0 < k < n2:
            y += (1 if k % 2 else -1) * o["jag"] * (0.6 + 0.8 * _hash(k, 7 if front else 11))
        return y

    def zF(k, y):
        x = xk(k)
        return zm + half(x, y) + gF * gape(x, y)

    def zB(k, y, with_fin=True):
        x = xk(k)
        f = fin_h if (with_fin and fin and fk0 <= k <= fk1 and y > -ys + 1e-9) else 0.0
        return zm - half(x, y) - gB * gape(x, y) - f

    b = Builder()
    rib = lambda k: ((p["rib"] if k % 2 else -p["rib"]) if ribs else 0.0)
    # the bottom crimp (sealed, as geom._pack_builder): teeth row, then the ribbed band's inner edge
    y_teeth = lambda k: -h / 2 + (0.0 if (k % 2 == 1 or not teeth) else p["tooth_d"])
    top_rows, bot_rows = [], []
    for yf in (y_teeth, lambda k: -yj):
        top_rows.append([b.v(xk(k), yf(k), zm + et / 2 + rib(k)) for k in crimp])
        bot_rows.append([b.v(xk(k), yf(k), zm - et / 2 + rib(k)) for k in crimp])
    corner = {k: b.v(xk(k), yt, zm) for k in (0, n2)}   # the torn corners: both skins pinched to one point
    shared = {}                                         # inner vertices on the side folds and the bottom seal

    def inner_shared(k, y):
        key = (k, round(y, 6))
        if key not in shared:
            shared[key] = b.v(xk(k), y, zm)
        return shared[key]

    # outer pillow rows, front (top) and back (bottom); the last row is the jagged mouth
    for f in vfr:
        last = f >= 1.0
        ks = mouth if (last or f >= fine_from) else cols
        rt, rb = [], []
        for k in ks:
            if last and k in (0, n2):
                rt.append(corner[k])
                rb.append(corner[k])
                continue
            yF = -ys + (ymouth(k, True, last) + ys) * f
            yB = -ys + (ymouth(k, False, last) + ys) * f
            rt.append(b.v(xk(k), yF, zF(k, yF)))
            rb.append(b.v(xk(k), yB, zB(k, yB)))
        top_rows.append(rt)
        bot_rows.append(rb)
    # inner rows: the outer rows from the false bottom up, offset by the film (the same columns, so the same
    # triangulation: an exact offset that never pokes through); the false-bottom row and the side columns are
    # shared front / back
    in_f, in_b = [], []
    for f in [f for f in vfr if f >= f_fb]:
        last = f >= 1.0
        ks = mouth if (last or f >= fine_from) else cols
        rf, rb = [], []
        for k in ks:
            if f == f_fb and k in (0, n2):
                continue                        # the false bottom's ends: front and back already meet there
            if last and k in (0, n2):
                rf.append(corner[k])
                rb.append(corner[k])
                continue
            yF = -ys + (ymouth(k, True, last) + ys) * f
            yB = -ys + (ymouth(k, False, last) + ys) * f
            if f == f_fb or k in (0, n2):
                v = inner_shared(k, yF)
                rf.append(v)
                rb.append(v)
                continue
            rf.append(b.v(xk(k), yF, zF(k, yF) - film))
            rb.append(b.v(xk(k), yB, zB(k, yB, with_fin=False) + film))
        in_f.append(rf)
        in_b.append(rb)
    for r in range(len(top_rows) - 1):
        _zip(b, top_rows[r], top_rows[r + 1], True, 0, R_FRONT)
        _zip(b, bot_rows[r], bot_rows[r + 1], False, 0, R_BACK)
    for r in range(len(in_f) - 1):
        _zip(b, in_f[r], in_f[r + 1], False, 1, R_IN_A)
        _zip(b, in_b[r], in_b[r + 1], True, 1, R_IN_B)
    _end_faces(b, top_rows[0], bot_rows[0], (0, -1, 0), R_EDGE)
    _side_faces(b, top_rows, bot_rows)
    # lips along the tear: outer mouth edge -> inner mouth edge, both skins (silver: the cut laminate)
    for outer, inner in ((top_rows[-1], in_f[-1]), (bot_rows[-1], in_b[-1])):
        for k in range(len(outer) - 1):
            ids = _dedupe([outer[k], outer[k + 1], inner[k + 1], inner[k]])
            if len(ids) >= 3:
                _face_out(b, ids, (0, 1, 0), 1, R_EDGE + 2)
    return b


def item_pack_open() -> Item:
    p, o = S.PACK_STD, OPEN
    w, h = p["w"], p["h"]
    lods = [Lod(_open_builder(k)) for k in range(3)]
    (x0, y0, z0), (x1, y1, z1) = _aabb(lods[0].builder)
    yt = h / 2 - o["tear"]
    gF, gB, _ = o["gape"]
    hb = (p["t"] - p["fin"][4]) / 2
    zm = hb + p["fin"][4] + gB
    z_face = zm + hb                                   # the front skin's top at the pack centre (no gape there)
    proj = {R_FRONT: _planar(-w / 2, -h / 2, w, h), R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0, mirror_x=True),
            R_IN_A: _in_proj(w, -h / 2, h, 0), R_IN_B: _in_proj(w, -h / 2, h, 1),
            **_pack_edge_proj(w, -h / 2, h, z1)}
    mouth_z = zm + (gF - gB) / 2 + 0.0                 # the mouth's centre between the two torn edges
    strip_zs = S.PACK_STD["edge_t"] / 2 + S.PACK_STD["rib"] + STRIP["crumple"]
    return Item(
        name="SM_CSK_Pack_Std_Open", lods=lods, materials=["M_CSK_Pack", "M_CSK_PackInner"], projections=proj,
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, -h / 2, zm)), Socket("Face", (0, 0, z_face)),
                 Socket("CardsOut", (0, yt, mouth_z), (-90.0, 0.0, 0.0)), Socket("Stack", (0, 0, z1))],
        hulls=[_hull(lods[0].builder)], cls=None, budget=BUDGETS["SM_CSK_Pack_Std_Open"],
        data={"footprint_mm": [round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3)], "states": ["Open"],
              "state_of": "SM_CSK_Pack_Std_Sealed", "pose": "lying on its back, the Sealed pack's frame",
              "strip": {"mesh": "SM_CSK_Pack_Std_Strip",
                        "spawn_mm": [0.0, h / 2 - STRIP["h"] / 2, round(zm - strip_zs, 4)],
                        "note": "the tear strip's Seat where it came off, in this frame"},
              "reference": "References/CardShop/csk_pack.png (sheet 4)",
              "notes": ["Sheet 4 opened: top crimp torn off 12 below the sealed top (the strip's height), fine serrated "
                        "tear, the front edge sags 8 right of centre, the mouth gapes (lens, about 12 open at the "
                        "centre); silver inside (M_CSK_PackInner) on the inner skins and the tear lips.",
                        "Same frame as SM_CSK_Pack_Std_Sealed (the swap is in place); the Seat is the sealed pack's.",
                        "The cards seen in the sheet's mouth are not part of the mesh (CardsOut socket).",
                        "class null: an opened pack is not stock; it does not go in Pack slots (its gape is thicker "
                        "than the 4 / 5 mm box pitch)."]},
    )


# =========================================================================== B1 Strip (sheet 4)

def _strip_builder(level: int) -> Builder:
    """Sheet 4, the tear strip on its own: the pack's top crimp (27 ribbed teeth, the flat seal strip) and 3 of
    wrinkled foil below it, torn along an irregular lower edge. 67 x 12 x 0.3 film, lying front up."""
    p, s = S.PACK_STD, STRIP
    w, h, et = p["w"], p["h"], p["edge_t"]
    hs = s["h"]
    n2, cols, teeth, ribs, _ = _pack_cols(level)
    fine = list(range(n2 + 1))
    crimp = fine if teeth else cols
    dy = h / 2 - hs / 2                          # pack y = strip y + dy
    y_rib = h / 2 - p["crimp"] + p["seal"] - dy
    y_seal = h / 2 - p["crimp"] - dy
    jag_cols = fine[::2] if level == 0 else cols if level == 2 else fine
    zc = et / 2 + p["rib"] + s["crumple"]        # every LOD: the lowest point near z 0
    xk = lambda k: -w / 2 + w * k / n2
    rib = lambda k: ((p["rib"] if k % 2 else -p["rib"]) if ribs else 0.0)
    b = Builder()
    rows = []                                    # (ks, y(k), dz(k)), from -y (the torn edge) to +y (the teeth)
    jag = lambda k: (s["jag"] * (2 * _hash(k, 3) - 1)) if 0 < k < n2 else 0.0      # an irregular tear
    wrinkle = lambda k, r: s["crumple"] * (2 * _hash(k, r, 5) - 1)
    y_jag = -hs / 2 + s["jag"] + 0.1                      # the torn edge's mean line (lowest tooth at -hs/2 + 0.1)
    y_mid = y_jag + s["jag"] + 0.65                       # a wrinkle row, at least 0.5 above the highest tooth
    rows.append((jag_cols, lambda k: y_jag + jag(k), lambda k: wrinkle(k, 1)))
    rows.append((jag_cols, lambda k: y_mid + 0.15 * (2 * _hash(k, 9) - 1), lambda k: wrinkle(k, 2)))
    rows.append((cols, lambda k: y_seal, lambda k: 0.0))
    rows.append((crimp, lambda k: y_rib, rib))
    rows.append((crimp, lambda k: hs / 2 - (0.0 if (k % 2 == 1 or not teeth) else p["tooth_d"]), rib))
    top, bot = [], []
    for ks, yf, dz in rows:
        top.append([b.v(xk(k), yf(k), zc + et / 2 + dz(k)) for k in ks])
        bot.append([b.v(xk(k), yf(k), zc - et / 2 + dz(k)) for k in ks])
    for r in range(len(rows) - 1):
        _zip(b, top[r], top[r + 1], True, 0, R_FRONT)
        _zip(b, bot[r], bot[r + 1], False, 0, R_BACK)
    _end_faces(b, top[0], bot[0], (0, -1, 0), R_EDGE)
    _end_faces(b, top[-1], bot[-1], (0, 1, 0), R_EDGE + 2)
    _side_faces(b, top, bot)
    return b


def item_pack_strip() -> Item:
    p, s = S.PACK_STD, STRIP
    w, h, hs = p["w"], p["h"], s["h"]
    lods = [Lod(_strip_builder(k)) for k in range(3)]
    (x0, y0, z0), (x1, y1, z1) = _aabb(lods[0].builder)
    proj = {R_FRONT: _planar(-w / 2, hs / 2 - h, w, h),            # the top 12 of the pack's front / back art
            R_BACK: _planar(-w / 2, hs / 2 - h, w, h, tile_u=1.0, mirror_x=True),
            **_pack_edge_proj(w, -hs / 2, hs, z1)}
    return Item(
        name="SM_CSK_Pack_Std_Strip", lods=lods, materials=["M_CSK_Pack"], projections=proj,
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, 0, (z0 + z1) / 2))],
        hulls=[_hull(lods[0].builder)], cls=None, budget=BUDGETS["SM_CSK_Pack_Std_Strip"],
        data={"footprint_mm": [round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3)], "states": ["Strip"],
              "state_of": "SM_CSK_Pack_Std_Sealed", "pose": "lying front up, teeth to +Y",
              "reference": "References/CardShop/csk_pack.png (sheet 4)",
              "notes": ["Sheet 4: the ribbed crimp with its 27 teeth, the flat seal strip, then wrinkled foil torn "
                        "along an irregular edge; UVs carry the top 12 of the pack art.", "Litter (spec 3.H)."]},
    )


# =========================================================================== B1 Wrapper (sheet 4)

def _crumple(x: float, y: float) -> float:
    """Crumple height: a sum of tent ridges and valleys along hashed crease lines (sharp at each crease)."""
    wr = WRAPPER
    c = 0.0
    for i in range(wr["creases"]):
        th = math.pi * _hash(i, 1)
        d = (_hash(i, 2) - 0.5) * 100.0
        r = 6.0 + 12.0 * _hash(i, 3)
        a = (0.5 + 0.5 * _hash(i, 4)) * (1.0 if _hash(i, 5) > 0.45 else -1.0)
        s = x * math.cos(th) + y * math.sin(th) - d
        c += a * max(0.0, 1.0 - abs(s) / r)
    return wr["amp"] * c + wr["jitter"][2] * (2 * _hash(int(round(x * 8)) + 5000, int(round(y * 8)) + 5000) - 1)


def _bite(side: int, y: float, j: int) -> float:
    """The depth of the torn-away top skin at ``y`` on ``side`` (-1 left, +1 right), 0 where the skin is whole."""
    wr = WRAPPER
    for s, yc, hl, depth in wr["bites"]:
        if s != side:
            continue
        t = (y - yc) / hl
        if abs(t) < 1.0:
            base = depth * (0.5 + 0.5 * math.cos(math.pi * t)) ** 0.6
            return max(0.0, base + wr["bite_jag"] * (2 * _hash(j, side + 7, 13) - 1) * min(1.0, base / 4.0))
    return 0.0


def _wrapper_builder(level: int) -> Builder:
    """Sheet 4, the empty wrapper: flattened and crumpled, lying back up (the fin seal shows), both crimps with their
    teeth, and the top skin torn away along both long edges showing the silver inside of the bottom skin (a real
    step: the bite cells sit on the bottom skin, the torn top-skin edge is a 0.35 ramp). Crumple is a sum of hashed
    crease tents, the same function for the top and the bottom surface, which share one triangulation."""
    p, wr = S.PACK_STD, WRAPPER
    w, h = p["w"], p["h"]
    t_hi, t_lo, t_cr = wr["t"]
    n2, _cols, teeth, ribs, fin = _pack_cols(level)
    crimp = list(range(n2 + 1)) if teeth else _cols
    J = {0: 11, 1: 7}.get(level, 4)
    inner = {0: [-14.0, -7.0, -3.72, -2.48, 2.48, 3.72, 7.0, 14.0], 1: [-11.0, 0.0, 11.0]}.get(level, [0.0])
    ys = h / 2 - p["crimp"]
    yj = ys + p["seal"]
    xk = lambda k: -w / 2 + w * k / n2
    rib = lambda k: ((p["rib"] if k % 2 else -p["rib"]) if ribs else 0.0)
    fin_x = S.PACK_STD["w"] * (S.PACK_STD["fin"][1] - S.PACK_STD["teeth"]) / (2 * S.PACK_STD["teeth"]) + 1e-6
    b = Builder()
    top_rows, bot_rows, low_rows = [], [], []

    def crimp_row(yf):
        tr, br = [], []
        for k in crimp:
            x, y = xk(k), yf(k)
            c = 0.6 * _crumple(x, y) + rib(k)
            br.append(b.v(x, y, c))
            tr.append(b.v(x, y, c + t_cr))
        return tr, br

    teeth_y = lambda sgn: (lambda k: sgn * (h / 2 - (0.0 if (k % 2 == 1 or not teeth) else p["tooth_d"])))
    for yf in (teeth_y(-1), lambda k: -yj):
        tr, br = crimp_row(yf)
        top_rows.append(tr)
        bot_rows.append(br)
        low_rows.append(None)
    for j in range(J + 1):
        y = -ys + 2 * ys * j / J
        bl, br_ = (_bite(-1, y, j), _bite(1, y, j)) if 0 < j < J else (0.0, 0.0)
        m, rp = wr["margin"], wr["ramp"]
        xl1, xr1 = -w / 2 + max(m, bl), w / 2 - max(m, br_)
        xl2, xr2 = xl1 + rp, xr1 - rp
        xs = [-w / 2, (-w / 2 + xl1) / 2, xl1, xl2, (xl2 + inner[0]) / 2, *inner, (inner[-1] + xr2) / 2, xr2, xr1,
              (xr1 + w / 2) / 2, w / 2]
        low_l, low_r = bl > m + 0.3, br_ > m + 0.3
        low = [low_l] * 3 + [False] * (len(xs) - 6) + [low_r] * 3
        tr, brow = [], []
        jx, jy, _ = wr["jitter"]
        for i, x0 in enumerate(xs):
            x, yv = x0, y
            if 0 < j < J and abs(x0) > 5.0 and 4 <= i <= len(xs) - 5:     # interior, off the fin: irregular facets
                x += jx * (2 * _hash(j, i, 21) - 1)
                yv += jy * (2 * _hash(j, i, 22) - 1)
            c = _crumple(x, yv)
            brow.append(b.v(x, yv, c))
            z = c + (t_lo if low[i] else t_hi)
            if fin and 0 < j < J and abs(x) <= fin_x:
                z += p["fin"][4]
            tr.append(b.v(x, yv, z))
        top_rows.append(tr)
        bot_rows.append(brow)
        low_rows.append(low)
    for yf in (lambda k: yj, teeth_y(1)):
        tr, br = crimp_row(yf)
        top_rows.append(tr)
        bot_rows.append(br)
        low_rows.append(None)
    SILVER, EDGE = 1, 2
    for r in range(len(top_rows) - 1):
        la, lb = low_rows[r], low_rows[r + 1]
        if la is None or lb is None:
            _zip(b, top_rows[r], top_rows[r + 1], True, 0, R_BACK)
            _zip(b, bot_rows[r], bot_rows[r + 1], False, 0, R_FRONT)
            continue
        A, B, Ab, Bb = top_rows[r], top_rows[r + 1], bot_rows[r], bot_rows[r + 1]
        n = len(A)
        for i in range(n - 1):
            kind = 0
            if i in (0, 1, n - 3, n - 2) and (la[i] or la[i + 1] or lb[i] or lb[i + 1]):
                kind = SILVER
            elif i in (2, n - 4) and (la[i] or la[i + 1] or lb[i] or lb[i + 1]):
                kind = EDGE
            mat, region = {0: (0, R_BACK), SILVER: (1, R_IN_A), EDGE: (0, R_IN_A)}[kind]
            diag = _hash(r, i, 17) > 0.5
            for quad, up, m_, reg in (((A[i], A[i + 1], B[i + 1], B[i]), True, mat, region),
                                      ((Ab[i], Ab[i + 1], Bb[i + 1], Bb[i]), False, 0, R_FRONT)):
                a, b_, c, d = quad
                tris = ((a, b_, c), (a, c, d)) if diag else ((a, b_, d), (b_, c, d))
                for tri in tris:
                    b.face(tri if up else tuple(reversed(tri)), m_, reg)
    _end_faces(b, top_rows[0], bot_rows[0], (0, -1, 0), R_EDGE)
    _end_faces(b, top_rows[-1], bot_rows[-1], (0, 1, 0), R_EDGE + 2)
    _side_faces(b, top_rows, bot_rows)
    zmin = min(v[2] for v in b.verts)
    return G._shift_z(b, -zmin)


def item_pack_wrapper() -> Item:
    p = S.PACK_STD
    w, h = p["w"], p["h"]
    lods = [Lod(_wrapper_builder(k)) for k in range(3)]
    (x0, y0, z0), (x1, y1, z1) = _aabb(lods[0].builder)
    zmax = max(_aabb(l.builder)[1][2] for l in lods)
    # lying back up: seen from above the back art reads the right way round (a 180 deg turn about Y of the pack)
    proj = {R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0), R_FRONT: _planar(-w / 2, -h / 2, w, h, mirror_x=True),
            R_IN_A: _in_proj(w, -h / 2, h, 0), **_pack_edge_proj(w, -h / 2, h, zmax)}
    return Item(
        name="SM_CSK_Pack_Std_Wrapper", lods=lods, materials=["M_CSK_Pack", "M_CSK_PackInner"], projections=proj,
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, -h / 2, z1 / 2)), Socket("Face", (0, 0, z1))],
        hulls=[_hull(lods[0].builder)], cls=None, budget=BUDGETS["SM_CSK_Pack_Std_Wrapper"],
        data={"footprint_mm": [round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3)], "states": ["Wrapper"],
              "state_of": "SM_CSK_Pack_Std_Sealed", "pose": "lying back up (the fin seal shows), as sheet 4",
              "reference": "References/CardShop/csk_pack.png (sheet 4)",
              "notes": ["Sheet 4 wrapper: flattened, crumpled facets, both crimps with teeth and ribs, the fin seal; "
                        "the top skin is torn away along both long edges and the silver inside shows there "
                        "(M_CSK_PackInner). The log's 'silver at the torn end' reads the sheet differently: the "
                        "sheet shows both crimps whole and the silver along the long sides; built to the picture.",
                        "Litter (spec 3.H); no CardsOut / Stack sockets (empty, not stock)."]},
    )


# =========================================================================== B2 booster box L (sheet 5)

class _AsBoxS:
    """Run a geom S-box builder with the L numbers (geom reads spec.BOX_BOOSTER_S), then restore them."""

    def __enter__(self):
        self.old = S.BOX_BOOSTER_S
        S.BOX_BOOSTER_S = BOX_L

    def __exit__(self, *exc):
        S.BOX_BOOSTER_S = self.old


def _box_l_body(level: int) -> Lod:
    """Sheet 5 L, opened: geom's carton (_box_shell) with the front die-cut window (_window_outline) at the L's
    measured size; no centre divider (sheet 5 L shows none)."""
    s = BOX_L
    D, bd = s["d"], s["board"]
    b = Builder()
    _box_shell(b, s, closed_top=False)
    cut = Builder()
    _prism_y(cut, _window_outline(s, (6, 2, 0)[level]), -D / 2 - 1.0, -D / 2 + bd + 1.0, mat=1)
    return Lod(b, bevel_mm=0.5 if level == 0 else None, ops=[("DIFFERENCE", cut)], bevel_first=True)


def item_box_booster_l() -> Item:
    s = BOX_L
    W, D, H, bd = s["w"], s["d"], s["h"], s["board"]
    proj, uv_size = G._dieline(s)
    pk = S.PACK_STD
    cols, rows = s["packs"]
    pitch = s["pack_pitch"]
    inner_x, inner_y0, inner_y1 = W / 2 - bd, -D / 2 + bd, D / 2 - bd
    y_start = inner_y0 + ((inner_y1 - inner_y0) - rows * pitch) / 2       # the 12 rows centred in the depth
    sockets = [Socket("Seat", (0, 0, 0))]
    n = 0
    for r in range(rows):
        for c in range(cols):
            n += 1
            x = (c - (cols - 1) / 2) * (pk["w"] + s["pack_gap"])
            y = y_start + pitch * r + (pitch + pk["t"]) / 2          # the pack fills [y - 4, y], centred in its pitch
            sockets.append(Socket(f"Pack_{n:02d}", (x, y, bd + pk["h"] / 2), (90.0, 0.0, 0.0), "CONTAIN"))
    sockets += [Socket("Lid", (0, D / 2, H)), Socket("Grip", (0, -D / 2, H / 2)),
                Socket("Face", (0, -D / 2, H / 2), (90.0, 0.0, 0.0)), Socket("Stack", (0, 0, H))]
    return Item(
        name="SM_CSK_Box_Booster_L", lods=[_box_l_body(k) for k in range(3)],
        materials=["M_CSK_BoxPrintL", "M_CSK_Board"], projections=proj, sockets=sockets,
        hulls=[((-W / 2, -D / 2, 0), (W / 2, D / 2, H))], cls="BoxL", budget=BUDGETS["SM_CSK_Box_Booster_L"],
        data={"footprint_mm": [W, D, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "contain": {"Pack": {"sockets": [f"Pack_{i:02d}" for i in range(1, n + 1)],
                                   "cavity_mm": [[-inner_x, inner_y0, bd], [inner_x, inner_y1, H]],
                                   "accepts": ["Pack"], "pose": "standing, +90 deg about X"}},
              "parts": {"Lid": {"mesh": "SM_CSK_Box_Booster_L_Lid", "socket": "Lid", "type": "hinge",
                                "axis": "X", "range_deg": [0, 200], "open_rot_deg": [s["header_rot"], 0.0, 0.0]}},
              "dieline_mm": list(uv_size), "reference": "References/CardShop/csk_booster_box.png (sheet 5, large)",
              "notes": ["Sheet 5 L opened: the S design at 190 x 76 x 140; die-cut window 168 / 129 wide, 73 deep "
                        "(measured on the sheet); no centre divider (the sheet's L has none); the lid is the header.",
                        "24 packs 2 x 12 at 5 pitch, standing, the rows centred in the 72 inner depth.",
                        "Sealed state: SM_CSK_Box_Booster_L_Sealed"]},
    )


def item_box_booster_l_lid() -> Item:
    with _AsBoxS():
        it = G.item_box_lid()
    it.name = "SM_CSK_Box_Booster_L_Lid"
    it.materials = ["M_CSK_BoxPrintL", "M_CSK_Board"]
    it.budget = BUDGETS[it.name]
    it.data = {"part_of": "SM_CSK_Box_Booster_L", "pivot": "hinge axis",
               "reference": "References/CardShop/csk_booster_box.png (sheet 5, large)",
               "notes": ["geom.item_box_lid with the L numbers: tab 92 x 20, R 6 (sheet 5 L)."]}
    return it


def item_box_booster_l_sealed() -> Item:
    with _AsBoxS():
        it = G.item_box_sealed()
    it.name = "SM_CSK_Box_Booster_L_Sealed"
    it.materials = ["M_CSK_BoxPrintL", "M_CSK_Board", "M_CSK_Film"]
    it.cls = "BoxL"
    it.budget = BUDGETS[it.name]
    it.data["reference"] = "References/CardShop/csk_booster_box.png (sheet 5, large sealed)"
    it.data["notes"] = ["geom.item_box_sealed with the L numbers (sheet 5 L sealed: closed, in shrink film)."]
    return it


# =========================================================================== B3 collector box (sheet 10)

_SIDE_N = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0))    # front, right, back, left


def _ring(b: Builder, hw: float, hd: float, z: float) -> List[int]:
    return [b.v(-hw, -hd, z), b.v(hw, -hd, z), b.v(hw, hd, z), b.v(-hw, hd, z)]


def _walls(b: Builder, lo: List[int], hi: List[int], sign: float, mat: int, regions=None) -> None:
    for k in range(4):
        n = tuple(sign * c for c in _SIDE_N[k])
        _face_out(b, [lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]], n, mat, regions[k] if regions else 0)


def _ledge(b: Builder, outer: List[int], inner: List[int], up: bool, mat: int, region: int = 0) -> None:
    for k in range(4):
        _face_out(b, [outer[k], outer[(k + 1) % 4], inner[(k + 1) % 4], inner[k]], (0, 0, 1 if up else -1), mat,
                  region)


def _collector_dims():
    c = COLLECTOR
    W, D, bd = c["w"], c["d"], c["board"]
    neck_o = (W / 2 - bd - c["clear"], D / 2 - bd - c["clear"])        # neck outer half sizes (lid inner - clear)
    neck_i = (neck_o[0] - bd, neck_o[1] - bd)
    zt = c["neck_top"] - c["tray_drop"]                                 # tray top
    yb = neck_i[1] - c["wall"]                                          # back pocket's back wall
    py0 = yb - 4 * c["pack_pitch"] - 1.0                                # 4 packs deep + 1 clearance
    fy1 = py0 - c["rib"]                                                # front pockets' back wall
    fy0 = -neck_i[1] + c["wall"]
    return dict(neck_o=neck_o, neck_i=neck_i, zt=zt, pack_y=(py0, yb), front_y=(fy0, fy1))


def _collector_pockets():
    """(name, x0, x1, y0, y1, floor z) of the tray pockets: 2 pack wells at the back; dice, cards, sleeves in front."""
    c = COLLECTOR
    k = _collector_dims()
    zt = k["zt"]
    py0, py1 = k["pack_y"]
    fy0, fy1 = k["front_y"]
    pw = S.PACK_STD["w"] + 2.0
    g = c["pack_gap"] / 2
    out = [("PackL", -g - pw, -g, py0, py1, c["pack_floor"]), ("PackR", g, g + pw, py0, py1, c["pack_floor"])]
    wd, wc, wsl = c["front"]
    total = wd + wc + wsl + 2 * c["rib"]
    x = -total / 2
    for name, wdt, floor in (("Dice", wd, zt - c["die"] - 2.0), ("Cards", wc, zt + 2.0 - c["card_h"]),
                             ("Sleeves", wsl, zt + 2.0 - c["sleeve_h"] - 2.0)):
        out.append((name, x, x + wdt, fy0, fy1, floor))
        x += wdt + c["rib"]
    return out


def _collector_dieline():
    """Collector dieline, one BoxesL cell (2048 x 1024 px at 2 px/mm = a 1024 x 512 mm sheet). Tile (0, 0) is the
    outside print, tile (1, 0) the navy liner (sheet 10: 'lid and base interiors are navy'), at the same places:
    base wrap (band + neck) v 0-160; lid wrap v 170-293; lid top v 300-389 (u 0-190); base bottom u 200-390."""
    c = COLLECTOR
    W, D = c["w"], c["d"]
    U, V = 1024.0, 512.0
    per = (lambda x, y: x + W / 2, lambda x, y: W + (y + D / 2), lambda x, y: W + D + (W / 2 - x),
           lambda x, y: 2 * W + D + (D / 2 - y))

    def m(fu, fv, tile_u=0.0):
        return lambda x, y, z: (tile_u + inset(fu(x, y, z) / U), inset(fv(x, y, z) / V))

    base, lid = {}, {}
    for k in range(4):
        pk = per[k]
        base[10 + k] = m(lambda x, y, z, pk=pk: pk(x, y), lambda x, y, z: z)
        base[20 + k] = m(lambda x, y, z, pk=pk: pk(x, y), lambda x, y, z: z, 1.0)
        lid[30 + k] = m(lambda x, y, z, pk=pk: pk(x, y), lambda x, y, z: 170.0 + z)
        lid[40 + k] = m(lambda x, y, z, pk=pk: pk(x, y), lambda x, y, z: 170.0 + z, 1.0)
    base[14] = m(lambda x, y, z: 200.0 + x + W / 2, lambda x, y, z: 300.0 + D / 2 - y)
    lid[34] = m(lambda x, y, z: x + W / 2, lambda x, y, z: 300.0 + y + D / 2)
    lid[44] = m(lambda x, y, z: x + W / 2, lambda x, y, z: 300.0 + y + D / 2, 1.0)
    return base, lid


def _collector_body(level: int) -> Lod:
    """Sheet 10: a shoulder-neck telescoping box. The light-blue base band (190 x 89 x 42) with a navy neck inset
    2.2 rising to 160 (the lid slides over it and rests on the band), a black vacuum-formed tray filling the neck,
    3 under its rim, with pockets: two pack wells (2 x 4 standing on edge) at the back and dice / cards / sleeves in
    front. One closed stepped shell, the tray unioned in, the pockets cut."""
    c = COLLECTOR
    W, D, bd = c["w"], c["d"], c["board"]
    k = _collector_dims()
    (no_x, no_y), (ni_x, ni_y), zt = k["neck_o"], k["neck_i"], k["zt"]
    PRINT, BOARD, TRAY = 0, 1, 2
    b = Builder()
    r0, r1 = _ring(b, W / 2, D / 2, 0.0), _ring(b, W / 2, D / 2, c["band"])
    r2, r3 = _ring(b, no_x, no_y, c["band"]), _ring(b, no_x, no_y, c["neck_top"])
    r4, r5 = _ring(b, ni_x, ni_y, c["neck_top"]), _ring(b, ni_x, ni_y, bd)
    _face_out(b, r0, (0, 0, -1), PRINT, 14)
    _walls(b, r0, r1, 1, PRINT, (10, 11, 12, 13))
    _ledge(b, r1, r2, True, BOARD)
    _walls(b, r2, r3, 1, PRINT, (10, 11, 12, 13))
    _ledge(b, r3, r4, True, BOARD)
    _walls(b, r5, r4, -1, PRINT, (20, 21, 22, 23))
    _face_out(b, r5, (0, 0, 1), BOARD)
    tray = Builder()
    tray.box((-ni_x - 0.5, -ni_y - 0.5, bd - 0.5), (ni_x + 0.5, ni_y + 0.5, zt), mat=TRAY)
    ops = [("UNION", tray)]
    if level < 2:
        for _name, x0, x1, y0, y1, z0 in _collector_pockets():
            cut = Builder()
            cut.box((x0, y0, z0), (x1, y1, zt + 1.0), mat=TRAY)
            ops.append(("DIFFERENCE", cut))
    return Lod(b, bevel_mm=0.5 if level == 0 else None, ops=ops, bevel_first=False)


def item_box_collector() -> Item:
    c = COLLECTOR
    W, D, H = c["w"], c["d"], c["h"]
    k = _collector_dims()
    zt = k["zt"]
    pockets = {p[0]: p for p in _collector_pockets()}
    base_proj, _ = _collector_dieline()
    pk = S.PACK_STD
    sockets = [Socket("Seat", (0, 0, 0))]
    py0, py1 = k["pack_y"]
    n = 0
    for r in range(4):
        for side in ("PackL", "PackR"):
            n += 1
            _, x0, x1, _, _, z0 = pockets[side]
            y = py0 + 0.5 + c["pack_pitch"] * (r + 1)                     # the pack fills [y - 4, y]
            sockets.append(Socket(f"Pack_{n:02d}", ((x0 + x1) / 2, y, z0 + pk["h"] / 2), (90.0, 0.0, 0.0), "CONTAIN"))
    contain = {"Pack": {"sockets": [f"Pack_{i:02d}" for i in range(1, n + 1)],
                        "cavity_mm": [[pockets["PackL"][1], py0, c["pack_floor"]],
                                      [pockets["PackR"][2], py1, H - c["board"]]],
                        "accepts": ["Pack"], "pose": "standing on edge, +90 deg about X"}}
    # Cards / Sleeves stand like the packs (+90 deg about X, the item's Seat = its centre): the socket is half the
    # item's height over the pocket floor, on the pocket's back wall, so a stack grows toward the customer
    for name, holds, rot, up in (("Dice", "6 x SM_CSK_Die_D6, 2 x 3 at 17 pitch, from the pocket floor centre",
                                  (0.0, 0.0, 0.0), 0.0),
                                 ("Cards", "a card stack standing, face to -Y (Seat = the card centre)",
                                  (90.0, 0.0, 0.0), c["card_h"] / 2),
                                 ("Sleeves", "a pack of 66 x 91 sleeves standing, face to -Y (Seat = its centre)",
                                  (90.0, 0.0, 0.0), c["sleeve_h"] / 2)):
        _, x0, x1, y0, y1, z0 = pockets[name]
        loc = ((x0 + x1) / 2, y1 if up else (y0 + y1) / 2, z0 + up)
        sockets.append(Socket(name, loc, rot, "CONTAIN"))
        contain[name] = {"socket": name, "cavity_mm": [[x0, y0, z0], [x1, y1, H - c["board"]]],
                         "accepts": ["Card"] if name == "Cards" else [], "holds": holds}
    sockets += [Socket("Lid", (0, 0, c["band"])), Socket("Stack", (0, 0, H))]
    return Item(
        name="SM_CSK_Box_Collector", lods=[_collector_body(i) for i in range(3)],
        materials=["M_CSK_BoxPrintL", "M_CSK_Board", "M_CSK_Tray"], projections=base_proj, sockets=sockets,
        hulls=[((-W / 2, -D / 2, 0), (W / 2, D / 2, c["neck_top"]))], cls="BoxC",
        budget=BUDGETS["SM_CSK_Box_Collector"],
        data={"footprint_mm": [W, D, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "contain": contain,
              "parts": {"Lid": {"mesh": "SM_CSK_Box_Collector_Lid", "socket": "Lid", "type": "slide", "axis": "Z",
                                "range_mm": [0, 130],
                                "note": "lift-off: past 118 the lid clears the neck and comes off"}},
              "reference": "References/CardShop/csk_collector_box.png (sheet 10 (1))",
              "notes": ["Sheet 10: telescoping shoulder box; lid depth 123 and 42 of base band (the picture wins over "
                        "the spec's E 30); navy neck and liner; black tray.",
                        "Tray: the spec's 2 x 4 packs standing on edge at the back (the sheet draws 8 in one row, "
                        "which needs about 155 of depth; the printed 89 wins), dice 2 x 3, and cards and sleeves "
                        "standing (58 deep pockets: a 63 x 88 card cannot lie flat in 89).",
                        "Closed = this + the lid at the Lid socket. The sheet's closed state is shrink-wrapped; no "
                        "film mesh is built (the spec lists none)."]},
    )


def _collector_lid_builder() -> Builder:
    """Sheet 10's lid, 190 x 89 x 123, board 2: five board slabs (top panel, two full-depth side walls, front and back
    walls between them), each a closed convex box, so every face points out of its own part (the lid is a cup; one
    shell would have its inside faces pointing at its own centre). Where two slabs meet, one sits 0.02 inside the
    other's face plane: no coplanar overlaps, no coincident vertices. Outside print tile (0, 0), navy liner (1, 0)."""
    c = COLLECTOR
    W, D, bd, L = c["w"], c["d"], c["board"], c["lid_depth"]
    e = 0.02
    PRINT, BOARD = 0, 1
    zt = L - bd                                                         # the walls' tops, under the top panel
    b = Builder()
    b.box((-W / 2 + e, -D / 2 + e, zt), (W / 2 - e, D / 2 - e, L), mat=PRINT,
          regions={"pz": 34, "nz": 44, "ny": 30, "px": 31, "py": 32, "nx": 33})
    for sx, outer, inner in ((1, 31, 41), (-1, 33, 43)):               # side walls: the inside of +X faces -X
        x0, x1 = sorted((sx * W / 2, sx * (W / 2 - bd)))
        b.box((x0, -D / 2, 0.0), (x1, D / 2, zt), mat=PRINT,
              regions={("px" if sx > 0 else "nx"): outer, ("nx" if sx > 0 else "px"): inner, "ny": 30, "py": 32},
              mats={"nz": BOARD, "pz": BOARD})
    for sy, outer, inner in ((-1, 30, 40), (1, 32, 42)):               # front / back walls between the sides
        y0, y1 = sorted((sy * (D / 2 - e), sy * (D / 2 - bd)))
        b.box((-W / 2 + bd, y0, 0.0), (W / 2 - bd, y1, zt), mat=PRINT,
              regions={("ny" if sy < 0 else "py"): outer, ("py" if sy < 0 else "ny"): inner},
              mats={"nz": BOARD, "pz": BOARD, "nx": BOARD, "px": BOARD})
    return b


def item_box_collector_lid() -> Item:
    c = COLLECTOR
    W, D, L = c["w"], c["d"], c["lid_depth"]
    _, lid_proj = _collector_dieline()
    return Item(
        name="SM_CSK_Box_Collector_Lid", lods=[Lod(_collector_lid_builder())],
        materials=["M_CSK_BoxPrintL", "M_CSK_Board"], projections=lid_proj, sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-W / 2, -D / 2, 0), (W / 2, D / 2, L))], budget=BUDGETS["SM_CSK_Box_Collector_Lid"],
        data={"part_of": "SM_CSK_Box_Collector", "pivot": "the rim centre = the closed position (Lid socket)",
              "reference": "References/CardShop/csk_collector_box.png (sheet 10 (1))",
              "notes": ["Sheet 10: navy lid 190 x 89 x 123, navy inside (liner, tile (1, 0))."]},
    )


# =========================================================================== B7 tuck box (sheet 10)

def _tuck_dieline():
    """Tuck-box dieline in tile (0, 0): front | right | back | left, the bottom under the front, the top over the back
    (it hinges there) and the tuck flap beyond it, which shows through the thumb cut. z is from the box's bottom."""
    t = TUCK
    W, D, H, f = t["w"], t["d"], t["h"], t["film"]
    U, V = 2 * (W + D), D + H + D + t["tuck"]

    def m(fu, fv):
        return lambda x, y, z: (inset(fu(x, y, z - f) / U), inset(fv(x, y, z - f) / V))
    return {
        10: m(lambda x, y, z: x + W / 2, lambda x, y, z: D + z),
        11: m(lambda x, y, z: W + (y + D / 2), lambda x, y, z: D + z),
        12: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: D + z),
        13: m(lambda x, y, z: 2 * W + D + (D / 2 - y), lambda x, y, z: D + z),
        14: m(lambda x, y, z: x + W / 2, lambda x, y, z: D - (y + D / 2)),
        15: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: D + H + (D / 2 - y)),
        16: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: 2 * D + H + (H - z)),
    }, (U, V)


def item_deck_tuck() -> Item:
    """Sheet 10 (2): a folding-carton tuck box, closed, in shrink film. The front panel's top edge has the half-moon
    thumb cut (a real 0.4 recess, the board's thickness) through which the tuck flap shows; the two-tone bands are
    print (the dieline)."""
    t = TUCK
    W, D, H, f, bd = t["w"], t["d"], t["h"], t["film"], t["board"]
    nw, nd, segs = t["notch"]
    b = Builder()
    b.box((-W / 2, -D / 2, f), (W / 2, D / 2, H + f), mat=0,
          regions={"ny": 10, "px": 11, "py": 12, "nx": 13, "nz": 14, "pz": 15})
    cut = Builder()
    top = H + f
    outline = [(-nw / 2, top + 1.0)] + [(nw / 2 * math.cos(math.pi + math.pi * i / segs),
                                         top + nd * math.sin(math.pi + math.pi * i / segs)) for i in range(segs + 1)]
    outline += [(nw / 2, top + 1.0)]
    y0, y1 = -D / 2 - 1.0, -D / 2 + bd
    fl = [cut.v(x, y0, z) for x, z in outline]
    bk = [cut.v(x, y1, z) for x, z in outline]
    cut.face(tuple(fl), 0)
    cut.face(tuple(reversed(bk)), 0, 16)            # the recess floor = the tuck flap's print
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        cut.face((fl[i], bk[i], bk[j], fl[j]), 0)
    film = Builder()
    film.prism(rounded_rect(W + 2 * f, D + 2 * f, t["film_r"], 2), 0.0, H + 2 * f, mat=1)
    proj, uv = _tuck_dieline()
    Hs = H + 2 * f
    return Item(
        name="SM_CSK_Deck_Tuck",
        lods=[Lod(b, bevel_mm=t["bevel"], ops=[("DIFFERENCE", cut)], bevel_first=True, extra=film)],
        materials=["M_CSK_BoxPrint", "M_CSK_Film"], projections=proj,
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, -D / 2 - f, Hs / 2)),
                 Socket("Face", (0, -D / 2 - f, Hs / 2), (90.0, 0.0, 0.0)), Socket("Stack", (0, 0, Hs))],
        hulls=[((-W / 2 - f, -D / 2 - f, 0), (W / 2 + f, D / 2 + f, Hs))], cls="Deck",
        budget=BUDGETS["SM_CSK_Deck_Tuck"],
        data={"footprint_mm": [W + 2 * f, D + 2 * f, Hs], "stack": {"socket": "Stack", "pitch_mm": Hs, "max": 4},
              "dieline_mm": list(uv), "reference": "References/CardShop/csk_collector_box.png (sheet 10 (2))",
              "notes": ["Sheet 10: closed tuck box with the half-moon thumb cut (30 x 10) in the front panel's top "
                        "edge; shrink film (sealed, as the sheet's first view); dark-red body over a light-red third "
                        "is print."]},
    )


# =========================================================================== registry

ITEMS = {
    "b_pack_open": item_pack_open,
    "b_pack_strip": item_pack_strip,
    "b_pack_wrapper": item_pack_wrapper,
    "b_pack_box_l": item_box_booster_l,
    "b_pack_box_l_lid": item_box_booster_l_lid,
    "b_pack_box_l_sealed": item_box_booster_l_sealed,
    "b_pack_collector": item_box_collector,
    "b_pack_collector_lid": item_box_collector_lid,
    "b_pack_tuck": item_deck_tuck,
}
