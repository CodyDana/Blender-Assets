"""Card Shop Kit family a_display: card tables, acrylic easels, slab risers, card stands and the oak wall unit
(CARDSHOP_KIT_SPEC.md 3.A rows A14-A16, plus SM_CSK_WallUnit_Oak from the style anchor; P3-P5).

    A14 glass-top card tables 08 / 10 / 12 + glass hood lids   reference sheet 22 (csk_card_table.png)
    A15 bent acrylic easels Slab / Card / Small                 reference sheet 23 (1) (csk_easels_risers.png)
    A16 slab riser block, 3-tier riser, card stands 1 and 9     reference sheet 23 (2), (3)
    --  oak wall unit 1200 x 400 x 2100 (no spec row)           reference sheet 36 (csk_wall_unit.png)

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = a
spec estimate with a source range. "sheet N" = the value or form is read off that reference sheet (the picture wins
over E numbers; M numbers win over the picture). Millimetres; Seat frame: +X right, +Y away from the customer, +Z up.

Fixed display slots (spec 4.2 "DISPLAY, fixed": card tables, easels, risers, stands) are ``Slot_NN`` / ``Item``
sockets in the item-Seat frame, pitched in the socket rotation. A leaning item rests on its bottom edge, so its Seat
(the centre of its back face) depends on its length: each socket is authored for one design item, and
``data["slots"]["seat_offset_mm"]`` gives the per-class shift along the socket's local +Y (up the lean).

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import Item, Lod, Socket, _face_out, _prism_y, solve_grid
from .shapes import Builder

# =========================================================================== numbers

TABLE = dict(                  # A14 card tables, sheet 22
    cols=(4, 5, 6),            # M [G1]: 8 / 10 / 12 slots in 2 rows (sheet 22 agrees)
    rows=2,
    pitch=(120.0, 150.0),      # E (spec: W = cols x 120 + 160, D = 2 x 150 + 160)
    d=460.0, h=914.0,          # E (spec); sheet 22 reads ~1.4x wider: the log says build to the spec numbers
    rim_t=20.0,                # E: oak tray board thickness (sheet 22 open view: slim oak rim)
    tray=(676.0, 761.0),       # E: oak tray band bottom / rim top: 85 (sheet 22 reads 60 front, 106 side, scaled)
    deck_down=40.0,            # E: felt deck 40 below the rim (sheet 22 open view: the deck sits ~40% down the band)
    tray_recess=4.0,           # E: the felt block's underside sits 4 up inside the oak band (a recessed bottom)
    overhang=5.0,              # sheet 22 side view: the oak tray stands ~5 proud of the legs and apron
    leg=40.0,                  # E: square steel leg section (sheet 22: slim square legs)
    glide=8.0,                 # sheet 22: dark glide caps under the legs, height (E)
    apron=(60.0, 20.0),        # E: apron height x thickness (sheet 22: a white apron under the tray)
    tilt=20.0,                 # sheet 22 plan view: cards tilted ~20 deg up at the back (E)
    stop=(20.0, 4.0, 6.0),     # sheet 22 plan view: a small dark stop under each card's front edge: W x D x H (E)
    stop_gap=3.0,              # E: stop back face in front of the item's bottom-back edge (a 7 thick slab clears it)
    rail_at=0.55,              # sheet 22 plan: the thin rail crosses each card 55% up from its bottom edge
    rail_t=3.0,                # E: rail (a thin black fin standing on the felt) thickness (sheet 22: thin lines)
    rail_run=110.0,            # sheet 22 plan: the rail runs ~ (cols - 1) x pitch + 110 (past the outer cards)
    row_front=10.0,            # E: the stop's front face 10 behind the row cell's front edge (cell = row pitch)
    tag_ahead=10.0,            # E: PriceTag socket this far in front of the item's bottom-back edge
    # glass hood (the _Lid mesh), sheet 22: glass top, front, sides and back, hinged at the back
    glass=6.0,                 # E: hood glass (the case glass is 6.35 M [D24]; the hood is lighter)
    glass_in=4.0,              # E: hood glass outer faces 4 in from the tray's outer faces (it sits on the rim)
    hood_front=123.0,          # sheet 22: hood 123 tall at the front ...
    # ... and h - rim at the back (153): the top slopes down to the front (sheet 22 side view, ~4 deg)
    open_deg=70.0,             # sheet 22: opens to about 70 deg (spec E 0-80; the picture wins)
    hinge_x=0.36,              # sheet 22 plan: the two hinges at +-0.36 W from the centre
    hinge=(40.0, 3.0, 35.0),   # E: hinge leaf width, barrel radius, leaf height
    knuckle=7.0,               # E: the lid's centre knuckle half-length (0.5 gap to the body's outer knuckles)
    lock=(14.0, 8.0, 30.0, 22.0),  # sheet 22 side view: a small round lock on the hood back, top right corner:
                                   # diameter, proud, in from the end, down from the top (E)
)

EASEL = dict(                  # A15 bent easels, sheet 23 (1); W x D x H all M [D31]
    t=3.0,                     # E (spec; sheet 23 "3 mm clear acrylic")
    lean=15.0,                 # E (spec: 15 deg back, matching the M 15 deg riser)
    r_in=1.0,                  # E: bend inner radius (bent acrylic, real folded profile)
    bend_segs=3,
    plate_end=5.0,             # E: the back plate's free lower end stops 5 above the floor (2 over the ledge)
    # name: W, D, H, lip (lip M [D31]; the slab lip is read off sheet 23), ledge clear (E), design item
    kinds={
        "Slab": (66.0, 57.0, 64.0, 16.0, 7.5, "Slab"),         # lip: sheet 23 reads ~16 (no call-out)
        "Card": (76.0, 60.0, 57.0, 25.0, 6.5, "CardProt"),     # sheet 23: a card in a thick clear holder
        "Small": (54.0, 54.0, 51.0, 19.0, 4.0, "Card"),        # sheet 23: a card in a thin frame
    },
)

RISER = dict(                  # A16 slab risers, sheet 23 (2)
    block=(200.0, 80.0, 25.0),  # M [D32]
    tier=(200.0, 150.0, 75.0),  # E (spec); sheet 23 agrees
    steps=3,                   # sheet 23 / log: 3 steps of 2 slots
    lean=15.0,                 # M [D32]
    pitch_x=100.0,             # E: 2 slots across (spec D: 2 x 94 <= 200); sheet 23 shows a gap between the pairs
    block_y=-5.0,              # E: the slab's bottom-back edge on the block (its leaning top stays over the block)
    tier_y=28.0,               # E: the slab's bottom-back edge 28 behind each tread's front edge
    # guide cheeks (sheet 23: short slanted clear guides either side of each slab, with the slab edge in a groove)
    cheek_h=20.0,              # sheet 23: they stand ~20 above the surface (E)
    cheek=(40.0, 43.0, 47.0),  # |x| from the slot centre: inner face, groove bottom, outer face (slab 85 over lugs)
    cheek_d=18.0,              # E: cheek depth (horizontal section)
    groove=8.0,                # E: groove width (horizontal section; the slab is 7 / cos 15 = 7.25)
    bevel=0.5,
)

STAND = dict(                  # A16 card stands, sheet 23 (3)
    one=(70.0, 40.0, 25.0),    # E (spec)
    nine=(70.0, 120.0, 25.0),  # sheet 23 log: 70 wide x 120 long x 25, decided 2026-09-29
    slots9=9, pitch9=12.0,     # sheet 23 log: 9 cross slots at 12 pitch
    lean=15.0,                 # E: the kit's 15 deg (sheet 23 shows the cards leaning slightly back)
    slot_w=3.2,                # E: horizontal slot width: cards, penny sleeves and 35pt top-loaders (2.0)
    slot_d=12.0,               # E: slot depth into the block
    one_y=-6.0,                # E: the 1-slot's back wall at the slot floor (the item's top ends over the block)
    bevel=0.3,
)

WALL = dict(                   # oak wall unit, sheet 36 (no spec row)
    w=1200.0, d=400.0, h=2100.0,  # sheet 36 call-outs (lead: 1200 x 400 x 2100)
    side_t=25.0,               # E: oak side panels, full height to the floor (sheet 36)
    shelf_t=30.0,              # sheet 36 notes: thick oak shelves, about 30
    shelves=3,                 # sheet 36: an oak top + 3 shelves above the cabinet (4 levels with the cabinet top)
    cab_h=900.0,               # sheet 36 call-out: white base cabinets 900 tall
    cab_top=40.0,              # E: white top thickness (sheet 36 reads 40-70)
    plinth=(100.0, 30.0),      # E: white plinth height, recess behind the door faces (sheet 36 detail)
    door_t=18.0,               # E
    gap=3.0,                   # E: door gaps
    knob=(22.0, 9.0, 8.0, 12.0),  # sheet 36: small round knobs: head diameter, stem diameter, head T, stem length (E)
    knob_pos=(40.0, 50.0),     # sheet 36: knob centre in from the pair's meeting edge, down from the door top (E)
    comps=3,                   # E: compartments per level
)

# LOD0 budgets: the spec's Tris column (E). Raised (logged): Riser_Slab_3 300 -> 500 and Stand_Card_9 150 -> 300,
# because each slot is real geometry (12 grooved guide cheeks; 9 through-slots).
BUDGETS = {
    "SM_CSK_CardTable": 1500, "SM_CSK_CardTable_Lid": 200,
    "SM_CSK_Easel": 150,
    "SM_CSK_Riser_Slab_1": 300, "SM_CSK_Riser_Slab_3": 500,
    "SM_CSK_Stand_Card_1": 150, "SM_CSK_Stand_Card_9": 300,
    "SM_CSK_WallUnit_Oak": 1500,     # lead: budget 1500
}

# the design items the fixed slots are authored for (length along the lean, thickness), from geom / spec.py
ITEM_LEN = {"Card": (S.CARD_STD["h"], S.CARD_STD["t"], "SM_CSK_Card_Std"),
            "CardProt": (S.TOPLOADER_35["h"], S.TOPLOADER_35["t"], "SM_CSK_TopLoader_35pt"),
            "Slab": (S.SLAB_STD["h"], S.SLAB_STD["t"], "SM_CSK_Slab_Std")}


# =========================================================================== shape helpers

def _box(b: Builder, mn, mx, mat: int, **kw) -> None:
    lo = tuple(min(mn[i], mx[i]) for i in range(3))
    hi = tuple(max(mn[i], mx[i]) for i in range(3))
    b.box(lo, hi, mat=mat, **kw)


def _prism_x(b: Builder, outline_yz, x0: float, x1: float, mat: int) -> None:
    """A closed prism along +X from an outline in (y, z), any winding."""
    area = sum(outline_yz[i][0] * outline_yz[(i + 1) % len(outline_yz)][1]
               - outline_yz[(i + 1) % len(outline_yz)][0] * outline_yz[i][1] for i in range(len(outline_yz)))
    pts = list(outline_yz) if area > 0 else list(reversed(outline_yz))
    a = [b.v(x0, y, z) for y, z in pts]
    c = [b.v(x1, y, z) for y, z in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        dy, dz = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
        _face_out(b, [a[i], a[j], c[j], c[i]], (0, dz, -dy), mat)
    b.fill([c], mat, 0, (1, 0, 0))
    b.fill([a], mat, 0, (-1, 0, 0))


def _cyl_y(b: Builder, xc: float, zc: float, r: float, y0: float, y1: float, segs: int, mat: int) -> None:
    _prism_y(b, [(xc + r * math.cos(2 * math.pi * (i + 0.5) / segs), zc + r * math.sin(2 * math.pi * (i + 0.5) / segs))
                 for i in range(segs)], y0, y1, mat=mat)


def _cyl_x(b: Builder, yc: float, zc: float, r: float, x0: float, x1: float, segs: int, mat: int) -> None:
    _prism_x(b, [(yc + r * math.cos(2 * math.pi * (i + 0.5) / segs), zc + r * math.sin(2 * math.pi * (i + 0.5) / segs))
                 for i in range(segs)], x0, x1, mat)


def _lean_prism(b: Builder, outline_xy, z0: float, z1: float, lean_deg: float, mat: int) -> None:
    """A prism whose horizontal section is ``outline_xy`` (CCW from +Z) at z0, sheared back (+Y) by ``lean_deg``
    from vertical as it rises: horizontal top and bottom faces, slanted sides."""
    k = math.tan(math.radians(lean_deg))
    lb = [b.v(x, y + k * z0, z0) for x, y in outline_xy]
    lt = [b.v(x, y + k * z1, z1) for x, y in outline_xy]
    n = len(outline_xy)
    for i in range(n):
        j = (i + 1) % n
        b.face((lb[i], lb[j], lt[j], lt[i]), mat)
    b.fill([lt], mat, 0, (0, 0, 1))
    b.fill([lb], mat, 0, (0, 0, -1))


def _translate(b: Builder, d) -> Builder:
    b.verts = [(x + d[0], y + d[1], z + d[2]) for x, y, z in b.verts]
    return b


def _bent_strip(path: Sequence[Tuple[float, float]], t: float, r_c: float, segs: int) -> List[Tuple[float, float]]:
    """The (y, z) outline of a bent sheet: centreline ``path`` (straight runs), every interior corner rounded with
    centreline radius ``r_c`` (tangent arcs), offset +-t/2 along the normals (exact for lines and arcs)."""
    P = [tuple(p) for p in path]
    pts, nls = [], []                       # centreline points and their left normals

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
        n1 = (-d1[1] * s, d1[0] * s)        # toward the turn side
        C = (A[0] + n1[0] * r_c, A[1] + n1[1] * r_c)
        a0 = math.atan2(A[1] - C[1], A[0] - C[0])
        for k in range(segs + 1):
            a = a0 + s * phi * k / segs
            p = (C[0] + r_c * math.cos(a), C[1] + r_c * math.sin(a))
            radial = ((p[0] - C[0]) / r_c, (p[1] - C[1]) / r_c)
            nl = (-radial[0], -radial[1]) if s > 0 else radial       # left normal
            pts.append(p)
            nls.append(nl)
    dn = unit(P[-2], P[-1])
    pts.append(P[-1])
    nls.append((-dn[1], dn[0]))
    h = t / 2
    left = [(p[0] + n[0] * h, p[1] + n[1] * h) for p, n in zip(pts, nls)]
    right = [(p[0] - n[0] * h, p[1] - n[1] * h) for p, n in zip(pts, nls)]
    return left + list(reversed(right))


def _lean_seat(y_bb: float, z_base: float, length: float, lean_deg: float) -> Tuple[Tuple[float, float], Tuple]:
    """(y, z) of the Seat (back-face centre) of an item standing on its bottom edge at (y_bb, z_base), leaning
    ``lean_deg`` back from vertical, and the socket rotation (X = 90 - lean: the item's face toward -Y)."""
    a = math.radians(lean_deg)
    return (y_bb + length / 2 * math.sin(a), z_base + length / 2 * math.cos(a)), (90.0 - lean_deg, 0.0, 0.0)


def _seat_offsets(classes: Sequence[str], design: str) -> Dict[str, List[float]]:
    L0 = ITEM_LEN[design][0]
    return {c: [0.0, round((ITEM_LEN[c][0] - L0) / 2, 3), 0.0] for c in classes}


# =========================================================================== A14 card table (sheet 22)

def _t_dims(cols: int) -> Dict:
    s = TABLE
    px, py = s["pitch"]
    W, D = cols * px + 160.0, s["rows"] * py + 160.0          # E (spec)
    t0, rim = s["tray"]
    deck = rim - s["deck_down"]
    a = math.radians(s["tilt"])
    rows = []
    for r in range(s["rows"]):
        yc = (r - (s["rows"] - 1) / 2) * py
        y_s = yc - py / 2 + s["row_front"] + s["stop"][1] + s["stop_gap"]   # the item's bottom-back edge
        rows.append(y_s)
    xs = [(c - (cols - 1) / 2) * px for c in range(cols)]
    Lc = ITEM_LEN["Card"][0]
    rail_s = s["rail_at"] * Lc                                  # contact distance up the card
    ax = (D / 2 + s["hinge"][1], rim + s["hinge"][1])          # hinge axis (y, z): just behind / above the rear rim
    return dict(W=W, D=D, t0=t0, rim=rim, deck=deck, a=a, rows=rows, xs=xs, rail_s=rail_s, axis=ax,
                ov=s["overhang"], rt=s["rim_t"])


def _t_body(cols: int, level: int) -> Tuple[Builder, Optional[Builder]]:
    """Sheet 22: four white square steel legs with dark glides and a white apron under a light-oak tray; a dark
    felt deck 40 below the rim; per row a thin black rail and a small black stop under each card's front edge; the
    fixed leaves and outer knuckles of the two rear hinges. Returns (base, extra): the rails, stops and hinges are
    joined after the bevel."""
    k = _t_dims(cols)
    s = TABLE
    OAK, FELT, STEEL, BLACK, METAL = 0, 1, 2, 3, 4
    W, D, t0, rim, deck, ov, rt = k["W"], k["D"], k["t0"], k["rim"], k["deck"], k["ov"], k["rt"]
    L, gl = s["leg"], s["glide"]
    ah, at = s["apron"]
    b = Builder()
    # tray: an oak ring (4 boards) and the felt block inside it (its underside recessed, oak)
    xo, yo = W / 2, D / 2
    xi, yi = W / 2 - rt, D / 2 - rt
    ob, ot = b.loop([(-xo, -yo), (xo, -yo), (xo, yo), (-xo, yo)], t0), b.loop([(-xo, -yo), (xo, -yo), (xo, yo), (-xo, yo)], rim)
    ib, it = b.loop([(-xi, -yi), (xi, -yi), (xi, yi), (-xi, yi)], t0), b.loop([(-xi, -yi), (xi, -yi), (xi, yi), (-xi, yi)], rim)
    for lb, lt, inward in ((ob, ot, False), (ib, it, True)):
        for i in range(4):
            j = (i + 1) % 4
            q = (lb[i], lb[j], lt[j], lt[i])
            b.face(tuple(reversed(q)) if inward else q, OAK)
    b.fill([ot, it], OAK, 0, (0, 0, 1))
    b.fill([ob, ib], OAK, 0, (0, 0, -1))
    fz0 = t0 + s["tray_recess"]
    b.box((-xi - 0.5, -yi - 0.5, fz0), (xi + 0.5, yi + 0.5, deck), mat=FELT, mats={"nz": OAK})
    # legs, glides, apron (flush with the legs' outer faces; the tray overhangs them by ``ov``)
    lx, ly = W / 2 - ov, D / 2 - ov
    top = fz0 + 0.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(b, (sx * lx, sy * ly, gl if level < 2 else 0.0), (sx * (lx - L), sy * (ly - L), top), STEEL)
            if level < 2:   # dark glides (the far LOD runs the legs to the floor)
                _box(b, (sx * (lx - 1.0), sy * (ly - 1.0), 0.0), (sx * (lx - L + 1.0), sy * (ly - L + 1.0), gl + 0.5),
                     BLACK)
    za = t0 - ah
    for sy in (-1, 1):      # front / back apron between the legs
        _box(b, (-lx + L - 0.5, sy * ly, za), (lx - L + 0.5, sy * (ly - at), top), STEEL)
    for sx in (-1, 1):      # end aprons
        _box(b, (sx * lx, -ly + L - 0.5, za), (sx * (lx - at), ly - L + 0.5, top), STEEL)
    if level == 2:
        return b, None
    e = Builder()
    # rails and stops (the card rests its bottom edge behind the stop and leans on the rail)
    a = k["a"]
    sw, sd, sh = s["stop"]
    run = (cols - 1) * s["pitch"][0] + s["rail_run"]
    for y_s in k["rows"]:
        y_r = y_s + k["rail_s"] * math.cos(a)               # the rail's front-top edge touches the item's back face
        z_r = deck + k["rail_s"] * math.sin(a)
        _box(e, (-run / 2, y_r, deck - 0.5), (run / 2, y_r + s["rail_t"], z_r), BLACK)
        for x in k["xs"]:
            yb = y_s - s["stop_gap"]
            _box(e, (x - sw / 2, yb - sd, deck - 0.5), (x + sw / 2, yb, deck + sh), BLACK)
    # rear hinges: the fixed leaf on the tray's back face + two outer knuckles on the axis
    hw, hr, hh = s["hinge"]
    ya, za_ = k["axis"]
    kn = s["knuckle"]
    for sx in (-1, 1):
        xc = sx * s["hinge_x"] * W
        _box(e, (xc - hw / 2, D / 2 - 0.5, rim - hh), (xc + hw / 2, D / 2 + 2.0, rim), METAL)
        if level == 0:
            for x0, x1 in ((xc - hw / 2, xc - kn - 0.5), (xc + kn + 0.5, xc + hw / 2)):
                _cyl_x(e, ya, za_, hr, x0, x1, 8, METAL)
            _box(e, (xc - hw / 2, D / 2 + 1.0, za_ - hr - 0.5), (xc - kn - 0.5, ya, za_), METAL)   # knuckle webs
            _box(e, (xc + kn + 0.5, D / 2 + 1.0, za_ - hr - 0.5), (xc + hw / 2, ya, za_), METAL)
    return b, e


def item_table(cols: int) -> Item:
    k = _t_dims(cols)
    s = TABLE
    n = cols * s["rows"]
    W, D, H, deck = k["W"], k["D"], s["h"], k["deck"]
    lods = []
    for lv in range(3):
        base, extra = _t_body(cols, lv)
        lods.append(Lod(base, bevel_mm=1.0 if lv == 0 else None, extra=extra))
    sockets = [Socket("Seat", (0, 0, 0))]
    names = []
    Lc = ITEM_LEN["Card"][0]
    a = k["a"]
    i = 0
    for y_s in k["rows"]:                       # Slot_01.. front row left to right, then the back row
        for x in k["xs"]:
            i += 1
            seat = (x, y_s + Lc / 2 * math.cos(a), deck + Lc / 2 * math.sin(a))
            sockets.append(Socket(f"Slot_{i:02d}", seat, (s["tilt"], 0.0, 0.0), kind="DISPLAY"))
            names.append(f"Slot_{i:02d}")
    i = 0
    for y_s in k["rows"]:
        for x in k["xs"]:
            i += 1
            sockets.append(Socket(f"PriceTag_{i:02d}", (x, y_s - s["tag_ahead"] - s["stop"][1] - s["stop_gap"], deck),
                                  kind="DISPLAY"))
    ya, za = k["axis"]
    sockets.append(Socket("Lid", (0, ya, za)))
    xi, yi = W / 2 - k["rt"], D / 2 - k["rt"]
    rt = k["rt"]
    tag = f"{n:02d}"
    return Item(
        name=f"SM_CSK_CardTable_{tag}", lods=lods,
        materials=["M_CSK_Oak", "M_CSK_Felt", "M_CSK_Steel", "M_CSK_Base", "M_CSK_Metal"],
        projections={}, sockets=sockets,
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, deck)),                               # legs, apron, deck
               ((-W / 2, -D / 2, deck), (W / 2, -yi, k["rim"])), ((-W / 2, yi, deck), (W / 2, D / 2, k["rim"])),
               ((-W / 2, -yi, deck), (-xi, yi, k["rim"])), ((xi, -yi, deck), (W / 2, yi, k["rim"]))],
        budget=BUDGETS["SM_CSK_CardTable"],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": ["Card", "CardProt", "Slab"],
              "slots": {"sockets": names, "count": n, "rows": s["rows"], "cols": cols,
                        "pitch_mm": list(s["pitch"]), "accepts": ["Card", "CardProt", "Slab"],
                        "pose": f"lying tilted {s['tilt']:g} deg up at the back (socket rot X), bottom edge on the "
                                "felt behind the stop, back face on the row rail",
                        "design_item": ITEM_LEN["Card"][2],
                        "seat_offset_mm": _seat_offsets(("Card", "CardProt", "Slab"), "Card"),
                        "cavity_mm": [[-xi, -yi, deck], [xi, yi, k["rim"] + s["hood_front"] - s["glass"]]]},
              "parts": {"Lid": {"mesh": f"SM_CSK_CardTable_Lid_{tag}", "socket": "Lid", "type": "hinge",
                                "axis": "X", "range_deg": [0, s["open_deg"]],
                                "open_rot_deg": [-s["open_deg"], 0.0, 0.0]}},
              "reference": "References/CardShop/csk_card_table.png (sheet 22)",
              "notes": ["Built to the spec size (sheet 22 reads about 1.4x wider; the log says spec numbers)",
                        "Legs and apron: white powder-coated steel, slot M_CSK_Steel (the spec's 'Frame (tint)')",
                        "Slots hold the card 20 deg up at the back on a rail, as sheet 22's plan and open views",
                        "Lid opens 0-70 deg (sheet 22 'about 70'; spec E 0-80)"]},
    )


def _t_lid(cols: int, level: int = 0) -> Builder:
    """Sheet 22: the glass hood: top (sloping down to the front), front, back and two side panes, glued edge to
    edge; the moving parts of the two rear hinges (a clamp on the back pane, a web, the centre knuckle); a small
    round lock on the back pane at the top right. Built in the table frame, then moved to the hinge frame."""
    k = _t_dims(cols)
    s = TABLE
    GLASS, METAL = 0, 1
    W, D, rim = k["W"], k["D"], k["rim"]
    g, gi = s["glass"], s["glass_in"]
    x0, x1 = -W / 2 + gi, W / 2 - gi
    yf, yb = -D / 2 + gi, D / 2 - gi
    zf, zbk = rim + s["hood_front"], s["h"]                  # top surface at the front and the back
    slope = (zbk - zf) / (yb - yf)
    ztop = lambda y: zf + (y - yf) * slope
    b = Builder()
    if level == 2:          # far LOD: the hood as one closed sloped block
        _prism_x(b, [(yf, rim), (yb, rim), (yb, ztop(yb)), (yf, ztop(yf))], x0, x1, GLASS)
        return _translate(b, (0.0, -k["axis"][0], -k["axis"][1]))
    _prism_x(b, [(yf, ztop(yf) - g), (yb, ztop(yb) - g), (yb, ztop(yb)), (yf, ztop(yf))], x0, x1, GLASS)   # top
    _box(b, (x0, yf, rim), (x1, yf + g, ztop(yf) - g + 0.5), GLASS)                                          # front
    _box(b, (x0, yb - g, rim), (x1, yb, ztop(yb - g) - g + 0.5), GLASS)                                      # back
    for sx in (-1, 1):                                                                                       # sides
        xa, xb = (x0, x0 + g) if sx < 0 else (x1 - g, x1)
        ya_, yb_ = yf + g - 0.5, yb - g + 0.5
        _prism_x(b, [(ya_, rim), (yb_, rim), (yb_, ztop(yb_) - g + 0.5), (ya_, ztop(ya_) - g + 0.5)], xa, xb, GLASS)
    hw, hr, hh = s["hinge"]
    ya, za = k["axis"]
    kn = s["knuckle"]
    for sx in (-1, 1):
        xc = sx * s["hinge_x"] * W
        _box(b, (xc - hw / 2, yb - g - 1.5, rim + 1.0), (xc + hw / 2, yb + 1.5, rim + hh), METAL)          # clamp
        if level == 0:
            _box(b, (xc - kn, yb + 1.0, za - hr + 0.5), (xc + kn, ya, za + hr - 0.5), METAL)               # web
            _cyl_x(b, ya, za, hr, xc - kn, xc + kn, 8, METAL)                                              # knuckle
    if level == 0:
        ld, lp, lx, lz = s["lock"]
        _cyl_y(b, x1 - lx, zbk - lz, ld / 2, yb - 0.5, yb + lp, 10, METAL)
    return _translate(b, (0.0, -ya, -za))


def item_table_lid(cols: int) -> Item:
    k = _t_dims(cols)
    s = TABLE
    W, D = k["W"], k["D"]
    ya, za = k["axis"]
    tag = f"{cols * s['rows']:02d}"
    lb = _t_lid(cols, 0)
    xs = [v[0] for v in lb.verts]
    ys = [v[1] for v in lb.verts]
    zs = [v[2] for v in lb.verts]
    gi = s["glass_in"]
    return Item(name=f"SM_CSK_CardTable_Lid_{tag}", lods=[Lod(lb), Lod(_t_lid(cols, 1)), Lod(_t_lid(cols, 2))], materials=["M_CSK_Glass", "M_CSK_Metal"],
                projections={}, sockets=[Socket("Seat", (0, 0, 0)),
                                         Socket("Grip", (0, -D / 2 + gi - ya, s["hood_front"] / 2 + k["rim"] - za))],
                hulls=[((-W / 2 + gi, -D / 2 + gi - ya, k["rim"] - za), (W / 2 - gi, D / 2 - gi - ya, s["h"] - za))],
                budget=BUDGETS["SM_CSK_CardTable_Lid"],
                data={"part_of": f"SM_CSK_CardTable_{tag}", "pivot": "hinge axis (X) behind the rear rim top edge",
                      "size_mm": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3),
                                  round(max(zs) - min(zs), 3)],
                      "notes": ["Sheet 22's open view shows a curved stay on the left: not built (see the report)"]})


# =========================================================================== A15 easels (sheet 23 (1))

def _easel_outline(kind: str) -> Tuple[List[Tuple[float, float]], float]:
    """The (y, z) outline of the bent strip: lip top -> down the front lip -> along the floor -> up the rear leg ->
    apex -> down the back plate (leaning ``lean`` back, the item's back face on its front face) -> free end.
    Returns the outline and y_bb (the item's bottom-back edge on the floor top)."""
    s = EASEL
    W, D, H, lip, clear, _ = s["kinds"][kind]
    t = s["t"]
    rc = s["r_in"] + t / 2
    a = math.radians(s["lean"])
    u = (math.sin(a), math.cos(a))                     # up the plate
    nb = (math.cos(a), -math.sin(a))                   # the plate's back normal
    y_bb = -D / 2 + t + clear
    q0 = (y_bb + nb[0] * t / 2, t + nb[1] * t / 2)      # the plate centreline at the floor-top line
    def plate(zc):                                     # centreline point of the plate at height zc
        sd = (zc - q0[1]) / u[1]
        return (q0[0] + u[0] * sd, zc)
    cy, ez = D / 2 - 6.0, H - 3.0
    for _ in range(12):                                # hit D and H exactly (the bends' outer arcs set the extents)
        path = [(-D / 2 + t / 2, lip), (-D / 2 + t / 2, t / 2), (cy, t / 2), plate(ez),
                plate(s["plate_end"] + t / 2 * math.sin(a) + 0.0)]
        out = _bent_strip(path, t, rc, s["bend_segs"])
        my, mz = max(p[0] for p in out), max(p[1] for p in out)
        cy += D / 2 - my
        ez += H - mz
    return out, y_bb


def item_easel(kind: str) -> Item:
    s = EASEL
    W, D, H, lip, clear, cls = s["kinds"][kind]
    out, y_bb = _easel_outline(kind)
    b = Builder()
    _prism_x(b, out, -W / 2, W / 2, 0)
    Li = ITEM_LEN[cls][0]
    (ys, zs), rot = _lean_seat(y_bb, s["t"], Li, s["lean"])
    name = f"SM_CSK_Easel_{kind}"
    return Item(
        name=name, lods=[Lod(b)], materials=["M_CSK_Acrylic"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Item", (0.0, ys, zs), rot, kind="DISPLAY")],
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))], budget=BUDGETS["SM_CSK_Easel"],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "slots": {"sockets": ["Item"], "accepts": [cls], "design_item": ITEM_LEN[cls][2],
                        "pose": f"standing on its bottom edge on the floor, leaning {s['lean']:g} deg back on the "
                                "back plate (socket rot X)",
                        "seat_offset_mm": _seat_offsets((cls,), cls),
                        "ledge_clear_mm": clear, "lip_mm": lip},
              "reference": "References/CardShop/csk_easels_risers.png (sheet 23 (1))",
              "notes": [f"One 3 mm strip, bent: front lip {lip:g}, floor, rear leg, apex, back plate at "
                        f"{s['lean']:g} deg; bends inner radius {s['r_in']:g}",
                        "LOD0 only (spec: 150); edges left crisp (no bevel: the budget)"]},
    )


# =========================================================================== A16 slab risers (sheet 23 (2))

def _cheek_outline(side: int, yc: float) -> List[Tuple[float, float]]:
    """Horizontal section of a guide cheek at x = side * (inner .. outer) from the slot centre, centred on yc, with
    the groove (the slab edge's pocket) opening toward the slot centre. CCW from +Z."""
    ci, cg, co = RISER["cheek"]
    hd, hg = RISER["cheek_d"] / 2, RISER["groove"] / 2
    pts = [(ci, yc - hd), (co, yc - hd), (co, yc + hd), (ci, yc + hd), (ci, yc + hg), (cg, yc + hg), (cg, yc - hg),
           (ci, yc - hg)]
    if side > 0:
        return pts
    return [(-x, y) for x, y in reversed(pts)]


def _cheeks(b: Builder, x_c: float, y_bb: float, z_base: float, grooved: bool) -> None:
    """The two slanted guide cheeks of one slab slot (sheet 23): standing on the surface at z_base, leaning with
    the slab, the slab's edges (over its side lugs) in their grooves."""
    s = RISER
    a = math.radians(s["lean"])
    T = S.SLAB_STD["t"]
    y_mid0 = y_bb - T / (2 * math.cos(a))             # the slab mid-plane's horizontal trace at z_base
    z0, z1 = z_base - 0.5, z_base + s["cheek_h"]
    yc0 = y_mid0 - (z_base) * math.tan(a)              # _lean_prism shears by tan(lean) * z from z = 0
    for side in (-1, 1):
        if grooved:
            ol = [(x_c + x, y) for x, y in _cheek_outline(side, yc0)]
        else:
            ci, _, co = s["cheek"]
            hd = s["cheek_d"] / 2
            xa, xb = sorted((x_c + side * ci, x_c + side * co))
            ol = [(xa, yc0 - hd), (xb, yc0 - hd), (xb, yc0 + hd), (xa, yc0 + hd)]
        _lean_prism(b, ol, z0, z1, s["lean"], 0)


def _riser_slots(kind: str) -> List[Tuple[float, float, float]]:
    """(x centre, y_bb, z_base) per slot."""
    s = RISER
    px = s["pitch_x"]
    out = []
    if kind == "block":
        W, D, H = s["block"]
        for c in (-1, 1):
            out.append((c * px / 2, s["block_y"], H))
    else:
        W, D, H = s["tier"]
        n = s["steps"]
        for k in range(n):
            y0 = -D / 2 + k * D / n
            for c in (-1, 1):
                out.append((c * px / 2, y0 + s["tier_y"], H * (k + 1) / n))
    return out


def _riser_lod(kind: str, level: int) -> Lod:
    s = RISER
    b = Builder()
    if kind == "block":
        W, D, H = s["block"]
        b.box((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H), mat=0)
    else:
        W, D, H = s["tier"]
        n = s["steps"]
        prof = [(-D / 2, 0.0), (D / 2, 0.0), (D / 2, H)]
        for k in range(n - 1, -1, -1):                 # the stepped top, from the back down to the front
            y0 = -D / 2 + k * D / n
            prof += [(y0, H * (k + 1) / n), (y0, H * k / n)] if k > 0 else [(y0, H * (k + 1) / n)]
        _prism_x(b, prof, -W / 2, W / 2, 0)
    if level == 2:
        return Lod(b)
    e = Builder()
    for x_c, y_bb, zb in _riser_slots(kind):
        _cheeks(e, x_c, y_bb, zb, grooved=(level == 0))
    return Lod(b, bevel_mm=s["bevel"] if level == 0 else None, extra=e)


def item_riser(kind: str) -> Item:
    s = RISER
    W, D, H = s["block"] if kind == "block" else s["tier"]
    name = "SM_CSK_Riser_Slab_1" if kind == "block" else "SM_CSK_Riser_Slab_3"
    Ls = ITEM_LEN["Slab"][0]
    sockets = [Socket("Seat", (0, 0, 0))]
    names = []
    for i, (x_c, y_bb, zb) in enumerate(_riser_slots(kind)):
        (ys, zs), rot = _lean_seat(y_bb, zb, Ls, s["lean"])
        names.append(f"Slot_{i + 1:02d}")
        sockets.append(Socket(names[-1], (x_c, ys, zs), rot, kind="DISPLAY"))
    zt = s["cheek_h"] + H
    return Item(
        name=name, lods=[_riser_lod(kind, k) for k in range(3)], materials=["M_CSK_Acrylic"], projections={},
        sockets=sockets,
        hulls=([((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))] if kind == "block" else
               [((-W / 2, -D / 2 + k * D / s["steps"], 0.0), (W / 2, -D / 2 + (k + 1) * D / s["steps"],
                                                             H * (k + 1) / s["steps"])) for k in range(s["steps"])]),
        budget=BUDGETS[name],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "slots": {"sockets": names, "accepts": ["Slab"], "design_item": ITEM_LEN["Slab"][2],
                        "pose": f"standing on its bottom edge, leaning {s['lean']:g} deg back (socket rot X), its "
                                "edges in the guide cheeks' grooves",
                        "seat_offset_mm": _seat_offsets(("Slab",), "Slab")},
              "reference": "References/CardShop/csk_easels_risers.png (sheet 23 (2))",
              "notes": ["A closed clear shell (the log: a solid clear block); each slot = two slanted guide "
                        "cheeks with a real groove for the slab edge (sheet 23)",
                        f"guide cheeks stand {s['cheek_h']:g} above the surface (top at {zt:g} on the block)"]},
    )


# =========================================================================== A16 card stands (sheet 23 (3))

def _stand_slots(nine: bool) -> List[float]:
    """y of each slot's back wall at the slot floor (the item's bottom-back edge)."""
    s = STAND
    if not nine:
        return [s["one_y"]]
    n, p = s["slots9"], s["pitch9"]
    w = s["slot_w"]
    k = math.tan(math.radians(s["lean"]))
    # centre the slots' top openings on the block: opening at the top spans [y - w + k d, y + k d]
    return [(i - (n - 1) / 2) * p + w / 2 - k * s["slot_d"] / 2 for i in range(n)]


def _stand_lod(nine: bool, level: int) -> Lod:
    s = STAND
    W, D, H = s["nine"] if nine else s["one"]
    b = Builder()
    b.box((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H), mat=0)
    if level == 2:
        return Lod(b)
    ops = []
    zf = H - s["slot_d"]
    k = math.tan(math.radians(s["lean"]))
    w = s["slot_w"]
    for y in _stand_slots(nine):
        c = Builder()
        z1 = H + 1.0
        _prism_x(c, [(y - w, zf), (y, zf), (y + k * (z1 - zf), z1), (y - w + k * (z1 - zf), z1)],
                 -W / 2 - 1.0, W / 2 + 1.0, 0)
        ops.append(("DIFFERENCE", c))
    return Lod(b, bevel_mm=s["bevel"] if level == 0 else None, ops=ops, bevel_first=True)


def item_stand(nine: bool) -> Item:
    s = STAND
    W, D, H = s["nine"] if nine else s["one"]
    name = "SM_CSK_Stand_Card_9" if nine else "SM_CSK_Stand_Card_1"
    zf = H - s["slot_d"]
    Lp = ITEM_LEN["CardProt"][0]
    sockets = [Socket("Seat", (0, 0, 0))]
    names = []
    for i, y in enumerate(_stand_slots(nine)):
        (ys, zs), rot = _lean_seat(y, zf, Lp, s["lean"])
        nm = f"Slot_{i + 1:02d}" if nine else "Item"
        names.append(nm)
        sockets.append(Socket(nm, (0.0, ys, zs), rot, kind="DISPLAY"))
    return Item(
        name=name, lods=[_stand_lod(nine, k) for k in range(3)], materials=["M_CSK_Acrylic"], projections={},
        sockets=sockets, hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))], budget=BUDGETS[name],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "slots": {"sockets": names, "accepts": ["Card", "CardProt"], "design_item": ITEM_LEN["CardProt"][2],
                        "pose": f"standing in a through-slot, leaning {s['lean']:g} deg back (socket rot X)",
                        "slot_mm": {"width_horizontal": s["slot_w"], "depth": s["slot_d"]},
                        "seat_offset_mm": _seat_offsets(("Card", "CardProt"), "CardProt")},
              "reference": "References/CardShop/csk_easels_risers.png (sheet 23 (3))",
              "notes": ["Solid clear block (the log: block stand); through-slots, so a 76.2 top-loader overhangs "
                        "the 70 block by 3.1 a side",
                        "Slot 3.2 wide: raw and sleeved cards and 35pt top-loaders (2.0); not the 4.8 130pt"]
                       + (["Sheet 23 log: 70 wide x 120 long x 25, 9 cross slots at 12 pitch (user-accepted)"]
                          if nine else [])},
    )


# =========================================================================== oak wall unit (sheet 36)

def _w_levels():
    """(name, floor z, y0, y1, clear height) for the cabinet top and the 3 shelves."""
    s = WALL
    d, h, st, n = s["d"], s["h"], s["shelf_t"], s["shelves"]
    step = (h - s["cab_h"]) / (n + 1)                   # sheet 36: equal spacing, cabinet top to the oak top
    floors = [s["cab_h"]] + [s["cab_h"] + step * (k + 1) for k in range(n)]
    out = []
    for i, z in enumerate(floors):
        z_next = floors[i + 1] - st if i + 1 < len(floors) else h - st
        out.append((f"L{i + 1}", z, -d / 2 + 0.5, d / 2 - 0.5, z_next - z))
    return out


def _w_body(level: int) -> Tuple[Builder, Optional[Builder]]:
    """Sheet 36: light-oak side panels full height to the floor; an oak top and 3 thick oak shelves between them,
    open to the wall; white base cabinet: plinth (recessed), carcass, 4 doors in 2 pairs, white top; small round
    knobs near each pair's meeting edges."""
    s = WALL
    OAK, WHITE, METAL = 0, 1, 2
    w, d, h, t, st = s["w"], s["d"], s["h"], s["side_t"], s["shelf_t"]
    xi = w / 2 - t
    b = Builder()
    for sx in (-1, 1):
        _box(b, (sx * w / 2, -d / 2, 0.0), (sx * xi, d / 2, h), OAK)
    y0, y1 = -d / 2 + 0.5, d / 2 - 0.5
    _box(b, (-xi - 0.5, y0, h - st), (xi + 0.5, y1, h - 0.5), OAK)                       # oak top
    for name, z, *_ in _w_levels()[1:]:
        _box(b, (-xi - 0.5, y0, z - st), (xi + 0.5, y1, z), OAK)                          # shelves
    ch, ct = s["cab_h"], s["cab_top"]
    ph, pr = s["plinth"]
    dt, gp = s["door_t"], s["gap"]
    _box(b, (-xi - 0.5, y0, ch - ct), (xi + 0.5, y1, ch), WHITE)                          # white top
    if level == 2:
        _box(b, (-xi - 0.5, -d / 2 + 0.2, 0.0), (xi + 0.5, y1, ch - ct + 0.5), WHITE)     # carcass + doors, one block
        return b, None
    _box(b, (-xi - 0.5, -d / 2 + pr, 0.0), (xi + 0.5, y1, ph + 0.5), WHITE)              # plinth
    _box(b, (-xi - 0.5, -d / 2 + dt + 0.5, ph), (xi + 0.5, y1, ch - ct + 0.5), WHITE)    # carcass
    dw = (2 * xi - 5 * gp) / 4
    zd0, zd1 = ph + gp, ch - ct - gp
    doors = []
    for i in range(4):
        xa = -xi + gp + i * (dw + gp)
        doors.append((xa, xa + dw))
        _box(b, (xa, -d / 2, zd0), (xa + dw, -d / 2 + dt, zd1), WHITE)
    e = Builder()
    hd, sd, ht, sl = s["knob"]
    kx, kz = s["knob_pos"]
    segs = 10 if level == 0 else 6
    for i, (xa, xb) in enumerate(doors):                 # pairs (0, 1) and (2, 3): knobs by the meeting edges
        xk = xb - kx if i % 2 == 0 else xa + kx
        zk = zd1 - kz
        yf = -d / 2
        _cyl_y(e, xk, zk, sd / 2, yf - sl, yf + 0.5, segs, METAL)
        if level == 0:
            _cyl_y(e, xk, zk, hd / 2, yf - sl - ht, yf - sl + 0.5, segs, METAL)
    return b, e


def item_wallunit() -> Item:
    s = WALL
    w, d, h = s["w"], s["d"], s["h"]
    xi = w / 2 - s["side_t"]
    lods = []
    for lv in range(3):
        base, extra = _w_body(lv)
        lods.append(Lod(base, bevel_mm=1.0 if lv == 0 else None, extra=extra))
    sockets = [Socket("Seat", (0, 0, 0))]
    levels = []
    width = 2 * xi
    accepts = S.SHOWCASE_ACCEPTS
    for name, z, y0, y1, clear in _w_levels():
        yc = (y0 + y1) / 2
        sockets.append(Socket(f"Level_{name}", (0, yc, z), kind="DISPLAY"))
        cw = width / s["comps"]
        for i in range(s["comps"]):
            cx = -width / 2 + cw * (i + 0.5)
            sockets.append(Socket(f"Compartment_{name}_{i + 1:02d}", (cx, yc, z), kind="DISPLAY"))
            sockets.append(Socket(f"PriceTag_{name}_{i + 1:02d}", (cx, y0 + 2.0, z), kind="DISPLAY"))
        grids = [g for g in (solve_grid(width, y1 - y0, clear, c) for c in accepts) if g]
        levels.append({"socket": f"Level_{name}", "interior_mm": [round(width, 3), round(y1 - y0, 3)],
                       "clear_h_mm": round(clear, 3), "compartments": s["comps"], "grids": grids})
    st = s["shelf_t"]
    hulls = [((-w / 2, -d / 2, 0.0), (-xi, d / 2, h)), ((xi, -d / 2, 0.0), (w / 2, d / 2, h)),
             ((-xi, -d / 2, 0.0), (xi, d / 2, s["cab_h"])), ((-xi, -d / 2, h - st), (xi, d / 2, h))]
    for name, z, *_ in _w_levels()[1:]:
        hulls.append(((-xi, -d / 2, z - st), (xi, d / 2, z)))
    return Item(
        name="SM_CSK_WallUnit_Oak", lods=lods, materials=["M_CSK_Oak", "M_CSK_Laminate", "M_CSK_Metal"],
        projections={}, sockets=sockets, hulls=hulls, budget=BUDGETS["SM_CSK_WallUnit_Oak"],
        data={"footprint_mm": [w, d, h], "pose": "upright", "pivot": "bottom-centre", "accepts": list(accepts),
              "levels": levels,
              "reference": "References/CardShop/csk_wall_unit.png (sheet 36)",
              "notes": ["Oak top + 3 oak shelves at equal spacing above the 900 cabinet: 4 display levels "
                        "(sheet 36; its notes' '4 shelves' counts the top)",
                        "Doors are closed, fixed parts of the body; the cabinet inside (shelf on pins, concealed "
                        "hinges) and the side panels' pin holes are not modelled (see the report)",
                        "7 hulls: 2 side panels, the cabinet, the oak top and 3 shelves"]},
    )


# =========================================================================== registry

ITEMS = {
    "a_display_table_08": lambda: item_table(4),
    "a_display_table_lid_08": lambda: item_table_lid(4),
    "a_display_table_10": lambda: item_table(5),
    "a_display_table_lid_10": lambda: item_table_lid(5),
    "a_display_table_12": lambda: item_table(6),
    "a_display_table_lid_12": lambda: item_table_lid(6),
    "a_display_easel_slab": lambda: item_easel("Slab"),
    "a_display_easel_card": lambda: item_easel("Card"),
    "a_display_easel_small": lambda: item_easel("Small"),
    "a_display_riser_1": lambda: item_riser("block"),
    "a_display_riser_3": lambda: item_riser("tier"),
    "a_display_stand_1": lambda: item_stand(False),
    "a_display_stand_9": lambda: item_stand(True),
    "a_display_wallunit": item_wallunit,
}
