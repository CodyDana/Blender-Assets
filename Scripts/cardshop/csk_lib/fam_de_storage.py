"""Card Shop Kit family de_storage: the thick slab, the grading-return box and the card storage boxes
(CARDSHOP_KIT_SPEC.md 3.D rows D2, D4 and 3.E rows E1, E2; P3-P5).

    D2 SM_CSK_Slab_Thick                                   reference sheet 3 (csk_slab.png, the 8 mm side view)
    D4 SM_CSK_Box_GradeReturn + _Lid                       reference sheet 9 (csk_grade_return.png)
    E1 SM_CSK_Box_Row_{100,400,800} + SM_CSK_Box_Row_Lid_{100,400,800}         reference sheet 13 (1)
    E2 SM_CSK_Box_Monster_{3200,5000} + SM_CSK_Box_Monster_Lid_{3200,5000}     reference sheet 13 (2)

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice. "sheet N" =
the value or form is read off that reference sheet (the picture wins over E numbers; M numbers win over the picture,
REFERENCE_LOG "Scale rule for these sheets"). Millimetres; Seat frame: +X right, +Y away from the customer, +Z up.

Board boxes (sheets 9 and 13): white board outside, kraft inside and on every cut edge. Each box is one closed
"tray" shell on a 4 x 4 vertex grid, so the side walls' cut ends show as kraft strips on the front and back faces
(the butt joints of sheets 9 and 13) with no T-junctions; hand holes and the finger cut are exact boolean cuts with
kraft cut faces; dividers and the foam insert are joined after the bevel. The D4 lid is built from convex board
slabs (its name ends ``_Lid``, so the kit runs the outward-winding check on it, as on the collector lid).

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from . import spec as S
from .geom import (R_BACK, R_FRONT, R_LABEL, Item, Lod, Socket, _face_out, _planar, _prism_y, _slab_lod,
                   _slab_openings, add_slab_well)
from .shapes import Builder, rect

# =========================================================================== numbers

SLAB_THICK = dict(S.SLAB_STD,  # D2: the D1 design (sheet 3) at the thick size; every face-layout number as D1
                  t=8.0,       # E: top of the M range (T 5-8, [D7]); sheet 3 side view 2 is the 8 mm slab
                  well=(65.0, 90.0, 3.4),   # well depth 3.4 (E >= 3.30 D, the 130 pt card gap)
                  well_floor_z=2.3)         # D: (8.0 - 3.4) / 2, equal skins front and back

GRADE = dict(                  # D4, sheet 9
    w=150.0, d=125.0, h=170.0,  # E (spec): closed height; the base is W x D, the lid telescopes over it
    bd=4.0,                    # E (spec): board; inner 142 x 117 x 162 (D)
    lid=60.0,                  # sheet 9 closed view: the lid skirt is 0.35 H (reads 60-61)
    clear=0.5,                 # E: lid-to-base clearance a side
    fold_c=1.5,                # E: the lid's folded top edges (sheet 9 corner close-up: rounded folds)
    label=(85.0, 55.0, 0.2),   # sheet 9: blank label centred on the lid top, reads 83 x 51 (affine) -> W x D, proud
    foam_drop=20.0,            # sheet 9 notes: the foam top is about 20 below the rim
    slots=8, pitch=14.0,       # M [G4] 8 cards per submission; 14 pitch D (spec: 8 x 14 = 112); sheet 9 reads 13.7
    slot=(9.0, 87.0),          # E: slot W (the 8.0 thick slab + 1) x L (the slab 85.0 over its lugs + 2)
    slot_floor=30.0,           # D: the 134 slab stands on its short edge, top at 164 = 2 under the lid (sheet 9:
                               # the slabs rise about 18 above the foam and stay under the rim)
)

ROW = dict(                    # E1, sheet 13 (1); outer / inner M [D16]
    w=104.8, h=76.2,           # M: outer W x H; the length runs away from the customer (sheet 13: the 104.8 end with
                               # the finger cut is the front, and the lid hinges at the back top edge)
    lengths={100: (85.7, 63.5), 400: (200.0, 177.8), 800: (381.0, 358.8)},   # M: outer / inner length
    in_w=95.3, in_h=69.9,      # M: inner W x H
    bd=3.0,                    # E (spec): board; the lid top, the front flap and the front wall
    gap=0.2,                   # E: front flap to front wall
    flap=36.0,                 # sheet 13 closed views: the front flap covers the top 34-37 (0.45-0.48 H)
    flap_r=4.0,                # sheet 13: rounded bottom corners of the flap
    fold_c=1.2,                # E: the lid's folds (top to flap), a chamfer
    notch=(26.0, 11.0),        # sheet 13: the half-moon finger cut, W x depth (26 x 10-12 in every view)
    ear=(24.0, 1.5, 12.0),     # sheet 13 open views: the lid's side dust flaps: height, thickness, front corner R.
                               # 1.5 (E, not board 3): closed, they tuck inside the side walls and the M inner 95.3
                               # must still take a sleeved card (class Card 92.1)
    bevel=0.5,
)

MONSTER = {                    # E2, sheet 13 (2); outer W x D x H M [D16] (the closed box = the lid's outside)
    3200: dict(w=336.6, d=406.4, h=103.2, rows=4),
    5000: dict(w=419.1, d=495.3, h=104.8, rows=5),
}
MON = dict(
    bd=3.0,                    # E (as E1)
    clear=0.5,                 # E: lid-to-base clearance a side
    lid=57.5,                  # sheet 13 closed views: the lid skirt is 0.55 H (reads 57-58 on both sizes; spec E 40)
    hole=(90.0, 30.0),         # E (spec): stadium hand hole W x H; sheet 13 reads 87-100 x 22-35
    hole_up=4.0,               # sheet 13 closed views: the hole's lower edge sits just above the lid skirt's edge
    div_t=3.0,                 # E: fold-up divider (double-ply fold, rounded top)
    div_drop=8.0,              # sheet 13 open views: the divider tops sit just under the rim, at the cards' tops
)

BUDGETS = {
    "SM_CSK_Slab_Thick": 1200,
    "SM_CSK_Box_GradeReturn": 500,
    "SM_CSK_Box_GradeReturn_Lid": 150,
    **{f"SM_CSK_Box_Row_{n}": 300 for n in ROW["lengths"]},
    **{f"SM_CSK_Box_Row_Lid_{n}": 150 for n in ROW["lengths"]},
    **{f"SM_CSK_Box_Monster_{n}": 600 for n in MONSTER},
    # raised 200 -> 300: the two hand holes are real cuts through the skirt (sheet 13) and the folded edges are
    # bevelled; base + lid stay inside the spec's combined 800
    **{f"SM_CSK_Box_Monster_Lid_{n}": 300 for n in MONSTER},
}

# placement classes (spec 4.2 "Storage: per size, + 10"): footprint = the closed box's outside
CLASSES = {
    **{f"StorageRow{n}": S.ItemClass(f"StorageRow{n}", (ROW["w"], L, ROW["h"]), (ROW["w"] + 10.0, L + 10.0))
       for n, (L, _) in ROW["lengths"].items()},
    **{f"StorageMonster{n}": S.ItemClass(f"StorageMonster{n}", (m["w"], m["d"], m["h"]), (m["w"] + 10.0, m["d"] + 10.0))
       for n, m in MONSTER.items()},
    # D4 is not in the spec's class table; proposed so the box can use shelf grids (lid outside, + 10)
    "BoxGrade": S.ItemClass("BoxGrade", (GRADE["w"] + 2 * (GRADE["bd"] + GRADE["clear"]),
                                         GRADE["d"] + 2 * (GRADE["bd"] + GRADE["clear"]), GRADE["h"]),
                            (169.0, 144.0)),
}

WHITE, KRAFT, THIRD = 0, 1, 2            # material slots: white board, kraft board, the item's third material
REF9 = "References/CardShop/csk_grade_return.png (sheet 9)"
REF13 = "References/CardShop/csk_storage_boxes.png (sheet 13)"


# =========================================================================== shared board-box builders

def _tray(b: Builder, xs: Sequence[float], ys: Sequence[float], z0: float, z1: float, zf: float,
          m: Dict[str, int]) -> None:
    """One closed tray shell, open at z1: outer box xs[0]..xs[3] x ys[0]..ys[3] x z0..z1, the cavity xs[1]..xs[2] x
    ys[1]..ys[2] down to the floor zf. Every face lies on the 4 x 4 grid of xs x ys, so the side walls' cut ends are
    their own faces on the front and back (``strip``), the rim is split into walls and corners, and nothing has a
    T-junction. ``m`` maps the face kinds to material slots: bottom, side, end, strip, rim_side, rim_end,
    rim_corner, in_side, in_end, floor."""
    X, Y = xs, ys
    B = [[b.v(X[i], Y[j], z0) for j in range(4)] for i in range(4)]
    T = [[b.v(X[i], Y[j], z1) for j in range(4)] for i in range(4)]
    F = {(i, j): b.v(X[i], Y[j], zf) for i in (1, 2) for j in (1, 2)}
    for i in range(3):
        for j in range(3):
            _face_out(b, [B[i][j], B[i + 1][j], B[i + 1][j + 1], B[i][j + 1]], (0, 0, -1), m["bottom"])
            if (i, j) != (1, 1):
                kind = "rim_corner" if i != 1 and j != 1 else ("rim_side" if i != 1 else "rim_end")
                _face_out(b, [T[i][j], T[i + 1][j], T[i + 1][j + 1], T[i][j + 1]], (0, 0, 1), m[kind])
    for j, n in ((0, -1), (3, 1)):                  # front / back: the side walls' ends are the outer strips
        for i in range(3):
            _face_out(b, [B[i][j], B[i + 1][j], T[i + 1][j], T[i][j]], (0, n, 0), m["end" if i == 1 else "strip"])
    for i, n in ((0, -1), (3, 1)):                  # left / right
        for j in range(3):
            _face_out(b, [B[i][j], B[i][j + 1], T[i][j + 1], T[i][j]], (n, 0, 0), m["side"])
    _face_out(b, [T[1][1], T[2][1], F[2, 1], F[1, 1]], (0, 1, 0), m["in_end"])
    _face_out(b, [T[1][2], T[2][2], F[2, 2], F[1, 2]], (0, -1, 0), m["in_end"])
    _face_out(b, [T[1][1], T[1][2], F[1, 2], F[1, 1]], (1, 0, 0), m["in_side"])
    _face_out(b, [T[2][1], T[2][2], F[2, 2], F[2, 1]], (-1, 0, 0), m["in_side"])
    _face_out(b, [F[1, 1], F[2, 1], F[2, 2], F[1, 2]], (0, 0, 1), m["floor"])


def _cup(b: Builder, xs: Sequence[float], ys: Sequence[float], z0: float, z1: float, zf: float, outer: int,
         inner: int) -> None:
    """The far-LOD tray: 14 quads, outside one material, rim and inside the other."""
    x0, ix0, ix1, x1 = xs
    y0, iy0, iy1, y1 = ys
    o = [b.v(x0, y0, z0), b.v(x1, y0, z0), b.v(x1, y1, z0), b.v(x0, y1, z0)]
    t = [b.v(x0, y0, z1), b.v(x1, y0, z1), b.v(x1, y1, z1), b.v(x0, y1, z1)]
    it = [b.v(ix0, iy0, z1), b.v(ix1, iy0, z1), b.v(ix1, iy1, z1), b.v(ix0, iy1, z1)]
    fl = [b.v(ix0, iy0, zf), b.v(ix1, iy0, zf), b.v(ix1, iy1, zf), b.v(ix0, iy1, zf)]
    n4 = ((0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))
    _face_out(b, o, (0, 0, -1), outer)
    for k in range(4):
        q = (k + 1) % 4
        _face_out(b, [o[k], o[q], t[q], t[k]], n4[k], outer)
        _face_out(b, [t[k], t[q], it[q], it[k]], (0, 0, 1), inner)
        _face_out(b, [it[k], it[q], fl[q], fl[k]], tuple(-c for c in n4[k]), inner)
    _face_out(b, fl, (0, 0, 1), inner)


def _flip_z(b: Builder, h: float) -> Builder:
    """Mirror ``b`` in z (z -> h - z) and re-wind every face, so a tray built open-up becomes a lid open-down."""
    b.verts = [(x, y, h - z) for x, y, z in b.verts]
    for f in b.faces:
        f.verts = tuple(reversed(f.verts))
    for fl in b.fills:
        fl.normal = (fl.normal[0], fl.normal[1], -fl.normal[2])
    return b


def _prism_x(b: Builder, outline_yz, x0: float, x1: float, mat: int = 0, lo_mat=None, hi_mat=None,
             side_mats: Sequence[int] = ()) -> None:
    """A closed prism along +X from an outline in YZ (counter-clockwise seen from +X). ``lo_mat`` / ``hi_mat`` are
    the -X / +X caps, ``side_mats[i]`` the side face of edge i -> i + 1 (default ``mat``)."""
    lo = [b.v(x0, y, z) for y, z in outline_yz]
    hi = [b.v(x1, y, z) for y, z in outline_yz]
    n = len(outline_yz)
    b.fill([lo], mat if lo_mat is None else lo_mat, 0, (-1, 0, 0))
    b.fill([hi], mat if hi_mat is None else hi_mat, 0, (1, 0, 0))
    for i in range(n):
        j = (i + 1) % n
        b.face((lo[i], lo[j], hi[j], hi[i]), side_mats[i] if i < len(side_mats) else mat)


def _arc(cx: float, cz: float, r: float, a0: float, a1: float, segs: int) -> List[Tuple[float, float]]:
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / segs)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / segs))) for k in range(segs + 1)]


def _stadium_xz(w: float, h: float, zc: float, segs: int) -> List[Tuple[float, float]]:
    """A stadium (slot) outline in XZ centred on x = 0, counter-clockwise seen from -Y."""
    r = h / 2
    a = w / 2 - r
    return _arc(a, zc, r, -90.0, 90.0, segs) + _arc(-a, zc, r, 90.0, 270.0, segs)


def _slot_cutter(outline_xz, y0: float, y1: float, mat: int) -> Builder:
    c = Builder()
    _prism_y(c, outline_xz, y0, y1, mat=mat)
    return c


BOARD_MATS = dict(bottom=WHITE, side=WHITE, end=WHITE, strip=KRAFT, rim_side=KRAFT, rim_end=KRAFT,
                  rim_corner=KRAFT, in_side=KRAFT, in_end=KRAFT, floor=KRAFT)


# =========================================================================== D2 thick slab (sheet 3)

def item_slab_thick() -> Item:
    """geom's D1 slab (sheet 3: stepped rim, label and window recesses, weld seam, stacking lugs) built from the
    8 mm dict: the well is 3.4 deep between two 2.3 skins. Sheet 3's side views draw the 7 and the 8 mm slabs
    with the same face design, so only the thickness and the well change."""
    s = SLAB_THICK
    w, h, t = s["w"], s["h"], s["t"]
    (lx0, ly0, lx1, ly1), (wx0, wy0, wx1, wy1) = _slab_openings(s)
    wcy = (wy0 + wy1) / 2
    ww, wh, wd = s["well"]
    zf = s["well_floor_z"]
    lods = [_slab_lod(s, k, 0, 1, False) for k in range(3)]
    add_slab_well(lods[0], s, 0, 1)
    cw, ch = S.CARD_STD["w"], S.CARD_STD["h"]
    x_lug = w / 2 + s["lug"][2]
    return Item(
        name="SM_CSK_Slab_Thick", lods=lods, materials=["M_CSK_SlabBody", "M_CSK_SlabWindow"],
        projections={R_LABEL: _planar(lx0, ly0, lx1 - lx0, ly1 - ly0, tile_v=1.0),
                     R_FRONT: _planar(-cw / 2, wcy - ch / 2, cw, ch),
                     R_BACK: _planar(-cw / 2, wcy - ch / 2, cw, ch, tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Card", (0, wcy, zf), kind="CONTAIN"),
                 Socket("Label", (0, (ly0 + ly1) / 2, t - s["label_d"])), Socket("Face", (0, 0, t)),
                 Socket("Grip", (0, -h / 2, t / 2)), Socket("Stack", (0, 0, t))],
        hulls=[((-w / 2, -h / 2, 0), (w / 2, h / 2, t))], cls="Slab", budget=BUDGETS["SM_CSK_Slab_Thick"],
        data={"footprint_mm": [2 * x_lug, h, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 10},
              "label_rect_mm": [lx0, ly0, lx1 - lx0, ly1 - ly0],
              "contain": {"Card": {"socket": "Card", "cavity_mm": [[-ww / 2, wcy - wh / 2, zf],
                                                                   [ww / 2, wcy + wh / 2, zf + wd]],
                                   "accepts": ["Card"], "note": "3.4 deep: takes cards up to 130 pt (3.30)"}},
              "reference": "References/CardShop/csk_slab.png (sheet 3, the 8 mm side view)",
              "notes": ["geom._slab_lod with the 8 mm dict (fam_de_storage.SLAB_THICK): the D1 face design, "
                        "well 65 x 90 x 3.4 between 2.3 skins; lugs 0.5 proud, so the render width is 85.0."]},
    )


# =========================================================================== D4 grading-return box (sheet 9)

def _grade_dims():
    g = GRADE
    W, D, bd = g["w"], g["d"], g["bd"]
    hb = g["h"] - bd                                # base height: the lid's top board rests on its rim
    return dict(W=W, D=D, bd=bd, hb=hb, foam_top=hb - g["foam_drop"],
                xs=(-W / 2, -W / 2 + bd, W / 2 - bd, W / 2), ys=(-D / 2, -D / 2 + bd, D / 2 - bd, D / 2),
                LW=W + 2 * (bd + g["clear"]), LD=D + 2 * (bd + g["clear"]))


def _slot_x(k: int) -> float:
    return (k - (GRADE["slots"] - 1) / 2) * GRADE["pitch"]


def _foam(slots: bool) -> Builder:
    """Sheet 9's grey foam insert: a block filling the base up to 20 under the rim, sunk 0.5 into the walls and the
    floor, with 8 slots running front to back (one closed shell: the top is a face with 8 holes)."""
    g, k = GRADE, _grade_dims()
    FOAM = THIRD
    x1, y1 = k["W"] / 2 - k["bd"] + 0.5, k["D"] / 2 - k["bd"] + 0.5
    z0, zt = k["bd"] - 0.5, k["foam_top"]
    b = Builder()
    if not slots:
        b.box((-x1, -y1, z0), (x1, y1, zt), mat=FOAM)
        return b
    lo = [b.v(-x1, -y1, z0), b.v(x1, -y1, z0), b.v(x1, y1, z0), b.v(-x1, y1, z0)]
    hi = [b.v(-x1, -y1, zt), b.v(x1, -y1, zt), b.v(x1, y1, zt), b.v(-x1, y1, zt)]
    _face_out(b, lo, (0, 0, -1), FOAM)
    n4 = ((0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))
    for i in range(4):
        _face_out(b, [lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i]], n4[i], FOAM)
    sw, sl = g["slot"]
    holes = []
    for s in range(g["slots"]):
        xc = _slot_x(s)
        top = [b.v(x, y, zt) for x, y in rect(sw, sl, xc)]
        bot = [b.v(x, y, g["slot_floor"]) for x, y in rect(sw, sl, xc)]
        for i in range(4):
            _face_out(b, [top[i], top[(i + 1) % 4], bot[(i + 1) % 4], bot[i]], tuple(-c for c in n4[i]), FOAM)
        _face_out(b, bot, (0, 0, 1), FOAM)
        holes.append(top)
    b.fill([hi] + holes, FOAM, 0, (0, 0, 1))
    return b


def _grade_base_lod(level: int) -> Lod:
    k = _grade_dims()
    b = Builder()
    if level == 0:
        _tray(b, k["xs"], k["ys"], 0.0, k["hb"], k["bd"], BOARD_MATS)
    else:
        _cup(b, k["xs"], k["ys"], 0.0, k["hb"], k["bd"], WHITE, KRAFT)
    return Lod(b, bevel_mm=0.5 if level == 0 else None, bevel_first=True, extra=_foam(slots=level < 2))


def item_grade_return() -> Item:
    """Sheet 9, the base: white corrugated board, 4 thick, kraft inside and on the cut edges (the side walls' ends
    show as kraft strips on the front and back faces, the rim is a cut edge), and the grey foam insert with 8 slots
    running front to back. The slabs stand on their short edge, side by side along X, face to +X."""
    g, k = GRADE, _grade_dims()
    hb = k["hb"]
    sw, sl = g["slot"]
    t = SLAB_THICK["t"]
    h2 = S.SLAB_STD["h"] / 2
    sockets = [Socket("Seat", (0, 0, 0))]
    # slab Seat frame turned (90, 0, 90): slab x -> +Y, slab y -> +Z, slab z (its back-to-face) -> +X
    for s in range(g["slots"]):
        sockets.append(Socket(f"Slab_{s + 1:02d}", (_slot_x(s) - t / 2, 0.0, g["slot_floor"] + h2), (90.0, 0.0, 90.0),
                              "CONTAIN"))
    sockets.append(Socket("Lid", (0, 0, g["h"] - g["lid"])))
    return Item(
        name="SM_CSK_Box_GradeReturn", lods=[_grade_base_lod(i) for i in range(3)],
        materials=["M_CSK_BoardWhite", "M_CSK_Board", "M_CSK_Foam"], projections={}, sockets=sockets,
        hulls=[((-k["W"] / 2, -k["D"] / 2, 0), (k["W"] / 2, k["D"] / 2, hb))], cls="BoxGrade",
        budget=BUDGETS["SM_CSK_Box_GradeReturn"],
        data={"footprint_mm": [k["LW"], k["LD"], g["h"]],
              "contain": {"Slab": {"sockets": [f"Slab_{i:02d}" for i in range(1, g["slots"] + 1)],
                                   "cavity_mm": [[_slot_x(0) - sw / 2, -sl / 2, g["slot_floor"]],
                                                 [_slot_x(g["slots"] - 1) + sw / 2, sl / 2, hb]],
                                   "accepts": ["Slab"],
                                   "pose": "standing on the short edge in the foam slots, (90, 0, 90): face to +X; "
                                           "the Seat is the slab's back face, so a 7 mm slab sits 0.5 off the slot "
                                           "wall"}},
              "parts": {"Lid": {"mesh": "SM_CSK_Box_GradeReturn_Lid", "socket": "Lid", "type": "slide",
                                "axis": "Z", "range_mm": [0, 70],
                                "note": "lift-off: past 56 the lid clears the base and comes off"}},
              "reference": REF9,
              "notes": ["Sheet 9: base 150 x 125 x 166 (the lid's 4 top board makes the 170), kraft inside; the lid "
                        "telescopes over it (159 x 134 x 60). Foam top 20 under the rim; 8 slots 9 x 87 at 14 pitch, "
                        "floor at 30, so a standing 134 slab tops out at 164, under the closed lid.",
                        "The sheet's single-slab cavity panel is a different product (AI drift): not built."]},
    )


def _grade_lid_builder() -> Builder:
    """Sheet 9's telescoping lid, 159 x 134 x 60, board 4: a top panel with folded (chamfered) edges over four skirt
    slabs, each a closed convex box. The side skirts run the full depth, so their cut ends are the kraft strips on
    the front and back (sheet 9 corner close-up); front and back skirts sit between them 0.02 inside (the top panel
    0.04 inside the outer faces), and every
    skirt sinks 0.5 into the top panel (no coplanar faces, no coincident vertices). The blank label lies on top."""
    g, k = GRADE, _grade_dims()
    W, D, bd, L, c, e = k["LW"], k["LD"], k["bd"], g["lid"], g["fold_c"], 0.04
    LABEL = THIRD
    b = Builder()
    zt = L - bd
    x1, y1 = W / 2 - e, D / 2 - e
    lo = [b.v(-x1, -y1, zt), b.v(x1, -y1, zt), b.v(x1, y1, zt), b.v(-x1, y1, zt)]
    mid = [b.v(-x1, -y1, L - c), b.v(x1, -y1, L - c), b.v(x1, y1, L - c), b.v(-x1, y1, L - c)]
    top = [b.v(-x1 + c, -y1 + c, L), b.v(x1 - c, -y1 + c, L), b.v(x1 - c, y1 - c, L), b.v(-x1 + c, y1 - c, L)]
    n4 = ((0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))
    _face_out(b, lo, (0, 0, -1), KRAFT)
    _face_out(b, top, (0, 0, 1), WHITE)
    for i in range(4):
        j = (i + 1) % 4
        _face_out(b, [lo[i], lo[j], mid[j], mid[i]], n4[i], WHITE)
        _face_out(b, [mid[i], mid[j], top[j], top[i]], tuple(0.7 * a + (0.7 if q == 2 else 0) for q, a in
                                                            enumerate(n4[i])), WHITE)
    for sx in (-1, 1):                                  # side skirts, full depth
        xa, xb = sorted((sx * W / 2, sx * (W / 2 - bd)))
        b.box((xa, -D / 2, 0.0), (xb, D / 2, zt + 0.5), mat=WHITE,
              mats={("nx" if sx > 0 else "px"): KRAFT, "ny": KRAFT, "py": KRAFT, "nz": KRAFT, "pz": KRAFT})
    for sy in (-1, 1):                                  # front / back skirts between them
        ya, yb = sorted((sy * (D / 2 - e / 2), sy * (D / 2 - bd)))
        b.box((-W / 2 + bd - 0.5, ya, 0.0), (W / 2 - bd + 0.5, yb, zt + 0.5), mat=WHITE,
              mats={("py" if sy < 0 else "ny"): KRAFT, "nz": KRAFT, "pz": KRAFT, "nx": KRAFT, "px": KRAFT})
    lw, ld, lt = g["label"]
    b.box((-lw / 2, -ld / 2, L - 0.3), (lw / 2, ld / 2, L + lt), mat=LABEL, regions={"pz": R_LABEL})
    return b


def item_grade_return_lid() -> Item:
    g, k = GRADE, _grade_dims()
    W, D, L = k["LW"], k["LD"], g["lid"]
    lw, ld, lt = g["label"]
    return Item(
        name="SM_CSK_Box_GradeReturn_Lid", lods=[Lod(_grade_lid_builder())],
        materials=["M_CSK_BoardWhite", "M_CSK_Board", "M_CSK_Label"],
        projections={R_LABEL: _planar(-lw / 2, -ld / 2, lw, ld, tile_v=1.0)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Label", (0, 0, L + lt))],
        hulls=[((-W / 2, -D / 2, 0), (W / 2, D / 2, L + lt))], budget=BUDGETS["SM_CSK_Box_GradeReturn_Lid"],
        data={"part_of": "SM_CSK_Box_GradeReturn", "pivot": "the skirt's bottom centre = the closed position (Lid)",
              "size_mm": [W, D, L], "label_rect_mm": [-lw / 2, -ld / 2, lw, ld], "reference": REF9,
              "notes": ["Sheet 9: telescoping lift-off lid, folded top edges, kraft inside and on the cut ends, a "
                        "blank white label (85 x 55, 0.2 proud) on top; Label socket on its face."]},
    )


# =========================================================================== E1 row boxes (sheet 13 (1))

def _row_dims(n: int):
    r = ROW
    L, inner = r["lengths"][n]
    W, H, bd = r["w"], r["h"], r["bd"]
    hb = H - bd                                     # the base's walls; the lid's top board makes the 76.2
    y0 = -L / 2 + bd + r["gap"]                     # the base's front face (the flap lies in front of it)
    iy0 = y0 + bd                                   # the front wall is one board (sheet 13: thin cut edge, notch)
    iy1 = iy0 + inner                               # M inner length
    side = (W - r["in_w"]) / 2                      # M: 4.75, the folded double side wall (white inside)
    return dict(L=L, inner=inner, W=W, H=H, bd=bd, hb=hb, zf=hb - r["in_h"], side=side,
                xs=(-W / 2, -W / 2 + side, W / 2 - side, W / 2), ys=(y0, iy0, iy1, L / 2), back=L / 2 - iy1)


def _row_notch(k, segs: int) -> Builder:
    """The finger cut (sheet 13): a U through the front wall, 26 wide, its round bottom 11 below the closed flap's
    edge, so it shows as a half-moon under the flap and opens from the rim when the lid is up."""
    r = ROW
    nw, nd = r["notch"]
    rr = nw / 2
    zb = k["H"] - r["flap"] - nd
    out = [(-rr, k["H"] + 5.0)] + _arc(0.0, zb + rr, rr, 180.0, 360.0, segs) + [(rr, k["H"] + 5.0)]
    return _slot_cutter(out, k["ys"][0] - 1.0, k["ys"][1] + 1.0, KRAFT)


def _row_base_lod(n: int, level: int) -> Lod:
    k = _row_dims(n)
    b = Builder()
    mats = dict(BOARD_MATS, rim_side=WHITE, rim_corner=WHITE, in_side=WHITE)   # folded double sides: white
    if level < 2:
        _tray(b, k["xs"], k["ys"], 0.0, k["hb"], k["zf"], mats)
    else:
        _cup(b, k["xs"], k["ys"], 0.0, k["hb"], k["zf"], WHITE, KRAFT)
    ops = [("DIFFERENCE", _row_notch(k, (12, 6)[level]))] if level < 2 else []
    return Lod(b, bevel_mm=ROW["bevel"] if level == 0 else None, ops=ops, bevel_first=True)


def _card_long_edge_rot() -> Tuple[float, float, float]:
    """The card's Seat frame standing on its long edge, face to -Y: card x -> -Z, card y -> +X, card z -> -Y."""
    return (90.0, 90.0, 0.0)


def item_row_box(n: int) -> Item:
    """Sheet 13 (1), the base: white board outside; the side walls are folded double (M 4.75: white inside, a white
    folded rim), the ends are single board with kraft cut edges; the half-moon finger cut in the front wall."""
    r, k = ROW, _row_dims(n)
    W, L, H, hb, zf = k["W"], k["L"], k["H"], k["hb"], k["zf"]
    x_ear = r["in_w"] / 2 - r["ear"][1] - 0.1       # the closed lid's dust flaps narrow the cavity
    iy0, iy1 = k["ys"][1], k["ys"][2]
    cards = {"raw": math.floor((k["inner"] - 1.0) / 0.3), "penny_sleeved": math.floor((k["inner"] - 1.0) / 0.5)}
    return Item(
        name=f"SM_CSK_Box_Row_{n}", lods=[_row_base_lod(n, i) for i in range(3)],
        materials=["M_CSK_BoardWhite", "M_CSK_Board"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)),
                 Socket("Cards_Start", (0, iy0 + 1.0, zf + S.CARD_STD["w"] / 2), _card_long_edge_rot(), "CONTAIN"),
                 Socket("Lid", (0, L / 2, H)),
                 Socket("Label", (0, k["ys"][0], (H - r["flap"] - r["notch"][1]) / 2), (90.0, 0.0, 0.0)),
                 Socket("Stack", (0, 0, H))],
        hulls=[((k["xs"][0], k["ys"][0], 0), (k["xs"][3], k["ys"][3], zf)),
               ((k["xs"][0], k["ys"][0], zf), (k["xs"][1], k["ys"][3], hb)),
               ((k["xs"][2], k["ys"][0], zf), (k["xs"][3], k["ys"][3], hb)),
               ((k["xs"][1], k["ys"][0], zf), (k["xs"][2], iy0, hb)),
               ((k["xs"][1], iy1, zf), (k["xs"][2], k["ys"][3], hb))],
        cls=f"StorageRow{n}", budget=BUDGETS[f"SM_CSK_Box_Row_{n}"],
        data={"footprint_mm": [W, L, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 5},
              "contain": {"Card": {"socket": "Cards_Start", "cavity_mm": [[-x_ear, iy0, zf], [x_ear, iy1, hb]],
                                   "accepts": ["Card"], "row": {"axis": "+Y", "pitch_mm": {"raw": 0.3,
                                                                                         "penny_sleeved": 0.5},
                                                                "max": cards},
                                   "pose": "standing on the long edge, face to -Y (the customer); the row grows "
                                           "toward +Y; the Seat is the card's back face, 1.0 off the front wall"}},
              "parts": {"Lid": {"mesh": f"SM_CSK_Box_Row_Lid_{n}", "socket": "Lid", "type": "hinge", "axis": "X",
                                "range_deg": [0, 180], "open_rot_deg": [-100.0, 0.0, 0.0],
                                "note": "opens about -X (negative angles); sheet 13 open pose ~100 deg"}},
              "reference": REF13,
              "notes": [f"Outer {W} x {L} x {H}, inner {r['in_w']} x {k['inner']} x {r['in_h']} (M [D16]).",
                        f"M needs 22.2 of end structure: flap 3 + gap 0.2 + front wall 3 (sheet 13: thin, with the "
                        f"finger cut) + a folded back end {k['back']:.1f} (hidden under the lid in every view).",
                        "Label socket: on the front wall under the finger cut (the sheet shows no label)."]},
    )


def _row_lid_builder(n: int) -> Builder:
    """Sheet 13's fold-over lid in its hinge frame (origin on the hinge axis at the back top edge; closed it covers
    y in [-L, 0], z in [-36, 0]): the top panel with a folded (chamfered) front edge, the front flap with rounded
    bottom corners lying over the front wall, and two side dust flaps that tuck inside the side walls."""
    r, k = ROW, _row_dims(n)
    W, L, bd, c = k["W"], k["L"], r["bd"], r["fold_c"]
    e = 0.02
    b = Builder()
    yf = -L + e                                     # the top panel's front face, 0.02 behind the flap's face
    # the top panel: (fold chamfer, front end, underside, hinge end, top); kraft inside and on the cut ends
    _prism_x(b, [(yf + c, 0.0), (yf, -c), (yf, -bd), (0.0, -bd), (0.0, 0.0)], -W / 2 + e, W / 2 - e, WHITE,
             lo_mat=KRAFT, hi_mat=KRAFT, side_mats=(WHITE, KRAFT, KRAFT, WHITE, WHITE))
    fr = r["flap_r"]
    ztop = -c - 0.1                                 # the flap's top sinks into the top panel, under the fold
    zb = -r["flap"]
    out = ([(-W / 2, ztop)] + _arc(-W / 2 + fr, zb + fr, fr, 180.0, 270.0, 3)
           + _arc(W / 2 - fr, zb + fr, fr, 270.0, 360.0, 3) + [(W / 2, ztop)])
    f = [b.v(x, -L, z) for x, z in out]
    bk = [b.v(x, -L + bd, z) for x, z in out]
    b.fill([f], WHITE, 0, (0, -1, 0))
    b.fill([bk], KRAFT, 0, (0, 1, 0))
    for i in range(len(out)):
        j = (i + 1) % len(out)
        _face_out(b, [f[i], f[j], bk[j], bk[i]], _edge_normal(out[i], out[j]), KRAFT)
    eh, et, er = r["ear"]
    ya = k["ys"][1] + 0.5 - L / 2                   # the ears run between the end walls (lid frame: y - L/2)
    yb = k["ys"][2] - 0.5 - L / 2
    za, zb2 = -bd - eh, -bd + 0.5
    ear = [(yb, zb2), (yb, za), (ya + er, za)] + _arc(ya + er, za + er, er, 270.0, 180.0, 4)[1:] + [(ya, zb2)]
    ear = ear[::-1]                                  # counter-clockwise seen from +X
    x_in = r["in_w"] / 2 - 0.1
    for sx in (-1, 1):
        xa, xb = sorted((sx * x_in, sx * (x_in - et)))
        _prism_x(b, ear, xa, xb, KRAFT, lo_mat=WHITE if sx < 0 else KRAFT, hi_mat=WHITE if sx > 0 else KRAFT)
    return b


def _edge_normal(p, q):
    """The outward normal (in XZ, as a 3-vector) of the edge p -> q of a counter-clockwise XZ outline seen from -Y."""
    dx, dz = q[0] - p[0], q[1] - p[1]
    return (dz, 0.0, -dx)


def item_row_box_lid(n: int) -> Item:
    r, k = ROW, _row_dims(n)
    W, L = k["W"], k["L"]
    return Item(
        name=f"SM_CSK_Box_Row_Lid_{n}", lods=[Lod(_row_lid_builder(n))],
        materials=["M_CSK_BoardWhite", "M_CSK_Board"], projections={},
        sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-W / 2, -L, -r["flap"]), (W / 2, 0.0, 0.0))], budget=BUDGETS[f"SM_CSK_Box_Row_Lid_{n}"],
        data={"part_of": f"SM_CSK_Box_Row_{n}", "pivot": "hinge axis at the back top edge (Lid socket)",
              "reference": REF13,
              "notes": ["Sheet 13: kraft inside (the open views); the flap covers the top 36 of the front, the dust "
                        "flaps (1.5, E) tuck inside the side walls."]},
    )


# =========================================================================== E2 monster boxes (sheet 13 (2))

def _mon_dims(n: int):
    m, c = MONSTER[n], MON
    bd, cl = c["bd"], c["clear"]
    W, D, H = m["w"] - 2 * (bd + cl), m["d"] - 2 * (bd + cl), m["h"] - bd
    iw = W - 2 * bd
    rw = (iw - (m["rows"] - 1) * c["div_t"]) / m["rows"]
    z_lid = m["h"] - c["lid"]
    zc = z_lid + c["hole_up"] + c["hole"][1] / 2            # hand hole centre, the same for the base and the lid
    return dict(W=W, D=D, hb=H, bd=bd, rows=m["rows"], rw=rw, z_lid=z_lid, hole_zc=zc, OW=m["w"], OD=m["d"],
                OH=m["h"], xs=(-W / 2, -W / 2 + bd, W / 2 - bd, W / 2), ys=(-D / 2, -D / 2 + bd, D / 2 - bd, D / 2))


def _row_x(k, i: int) -> Tuple[float, float]:
    x0 = k["xs"][1] + i * (k["rw"] + MON["div_t"])
    return x0, x0 + k["rw"]


def _dividers(k, round_top: bool) -> Builder:
    """Fold-up row dividers (sheet 13): double-ply board strips standing on the floor between the rows, their tops
    folded round, 8 under the rim; sunk 0.5 into the floor and the end walls."""
    c = MON
    b = Builder()
    td = c["div_t"]
    ztop = k["hb"] - c["div_drop"]
    y0, y1 = k["ys"][1] - 0.5, k["ys"][2] + 0.5
    for i in range(1, k["rows"]):
        xc = _row_x(k, i)[0] - td / 2
        if round_top:
            out = [(xc - td / 2, k["bd"] - 0.5), (xc + td / 2, k["bd"] - 0.5)] + _arc(xc, ztop - td / 2, td / 2, 0.0,
                                                                                       180.0, 4)
            _prism_y(b, out, y0, y1, mat=WHITE)
        else:
            b.box((xc - td / 2, y0, k["bd"] - 0.5), (xc + td / 2, y1, ztop), mat=WHITE)
    return b


def _hole_cutter(k, y0: float, y1: float, zc: float, segs: int) -> Builder:
    w, h = MON["hole"]
    return _slot_cutter(_stadium_xz(w, h, zc, segs), y0, y1, KRAFT)


def _mon_base_lod(n: int, level: int) -> Lod:
    k = _mon_dims(n)
    b = Builder()
    if level < 2:
        _tray(b, k["xs"], k["ys"], 0.0, k["hb"], k["bd"], BOARD_MATS)
        ops = [("DIFFERENCE", _hole_cutter(k, k["ys"][0] - 1.0, k["ys"][3] + 1.0, k["hole_zc"], (6, 3)[level]))]
    else:
        _cup(b, k["xs"], k["ys"], 0.0, k["hb"], k["bd"], WHITE, KRAFT)
        ops = []
    return Lod(b, bevel_mm=0.5 if level == 0 else None, ops=ops, bevel_first=True,
               extra=_dividers(k, round_top=level == 0))


def item_monster_box(n: int) -> Item:
    """Sheet 13 (2), the base: white board, kraft inside and on the cut edges, stadium hand holes through both ends
    (front and back, the short faces), fold-up white dividers making the rows, which run front to back; the cards
    stand on their short edge, face to -Y."""
    k = _mon_dims(n)
    zf = k["bd"]
    sockets = [Socket("Seat", (0, 0, 0))]
    rows = []
    for i in range(k["rows"]):
        xa, xb = _row_x(k, i)
        sockets.append(Socket(f"Row_{i + 1:02d}", ((xa + xb) / 2, k["ys"][1] + 1.0, zf + S.CARD_STD["h"] / 2),
                              (90.0, 0.0, 0.0), "CONTAIN"))
        rows.append({"socket": f"Row_{i + 1:02d}", "x_mm": [round(xa, 3), round(xb, 3)]})
    sockets += [Socket("Lid", (0, 0, k["z_lid"])), Socket("Stack", (0, 0, k["OH"]))]
    inner_len = k["ys"][2] - k["ys"][1]
    xs, ys = k["xs"], k["ys"]
    return Item(
        name=f"SM_CSK_Box_Monster_{n}", lods=[_mon_base_lod(n, i) for i in range(3)],
        materials=["M_CSK_BoardWhite", "M_CSK_Board"], projections={}, sockets=sockets,
        hulls=[((xs[0], ys[0], 0), (xs[3], ys[3], zf)),
               ((xs[0], ys[0], zf), (xs[1], ys[3], k["hb"])), ((xs[2], ys[0], zf), (xs[3], ys[3], k["hb"])),
               ((xs[1], ys[0], zf), (xs[2], ys[1], k["hb"])), ((xs[1], ys[2], zf), (xs[2], ys[3], k["hb"]))],
        cls=f"StorageMonster{n}", budget=BUDGETS[f"SM_CSK_Box_Monster_{n}"],
        data={"footprint_mm": [k["OW"], k["OD"], k["OH"]], "stack": {"socket": "Stack", "pitch_mm": k["OH"], "max": 4},
              "contain": {"Card": {"sockets": [r["socket"] for r in rows],
                                   "cavity_mm": [[xs[1], ys[1], zf], [xs[2], ys[2], k["hb"]]],
                                   "accepts": ["Card"], "rows": rows,
                                   "row": {"axis": "+Y", "pitch_mm": {"raw": 0.3, "penny_sleeved": 0.5},
                                           "max": {"raw": math.floor((inner_len - 1.0) / 0.3),
                                                   "penny_sleeved": math.floor((inner_len - 1.0) / 0.5)}},
                                   "pose": "standing on the short edge, face to -Y; each row grows toward +Y from "
                                           "its socket (the card's back face, 1.0 off the front wall)"}},
              "parts": {"Lid": {"mesh": f"SM_CSK_Box_Monster_Lid_{n}", "socket": "Lid", "type": "slide", "axis": "Z",
                                "range_mm": [0, 70], "note": "lift-off: past 54.5 the lid clears the base"}},
              "reference": REF13,
              "notes": [f"Closed outer {k['OW']} x {k['OD']} x {k['OH']} (M [D16]) = the lid; the base is "
                        f"{k['W']:.1f} x {k['D']:.1f} x {k['hb']:.1f} (lid board 3 + 0.5 clearance a side).",
                        f"{k['rows']} rows of {k['rw']:.1f} between 3.0 dividers; hand holes 90 x 30 (E) through both "
                        "ends at the lid's hole height.",
                        "Sheet 13 conflict (decided 2026-09-29): the telescoping lift-off lid of the closed views is "
                        "built; the open views' hinged lid is the lid set aside.",
                        "Hulls: floor and 4 walls (5; the dividers get none: contained cards are NoCollision)."]},
    )


def _mon_lid_lod(n: int, level: int) -> Lod:
    """The telescoping lid (sheet 13 closed views): a tray built open-up and mirrored, so its folded top is white
    outside and kraft inside, the skirt's cut edge and the side skirts' ends kraft; the hand holes through the front
    and back skirts, level with the base's."""
    k, c = _mon_dims(n), MON
    OW, OD, L, bd = k["OW"], k["OD"], c["lid"], c["bd"]
    xs = (-OW / 2, -OW / 2 + bd, OW / 2 - bd, OW / 2)
    ys = (-OD / 2, -OD / 2 + bd, OD / 2 - bd, OD / 2)
    b = Builder()
    if level < 2:
        _tray(b, xs, ys, 0.0, L, bd, BOARD_MATS)
    else:
        _cup(b, xs, ys, 0.0, L, bd, WHITE, KRAFT)
    _flip_z(b, L)
    ops = []
    if level < 2:
        ops = [("DIFFERENCE", _hole_cutter(k, ys[0] - 1.0, ys[3] + 1.0, k["hole_zc"] - k["z_lid"], (6, 3)[level]))]
    return Lod(b, bevel_mm=0.8 if level == 0 else None, ops=ops, bevel_first=True)


def item_monster_lid(n: int) -> Item:
    k, c = _mon_dims(n), MON
    OW, OD, L = k["OW"], k["OD"], c["lid"]
    return Item(
        name=f"SM_CSK_Box_Monster_Lid_{n}", lods=[_mon_lid_lod(n, i) for i in range(3)],
        materials=["M_CSK_BoardWhite", "M_CSK_Board"], projections={}, sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-OW / 2, -OD / 2, 0), (OW / 2, OD / 2, L))], budget=BUDGETS[f"SM_CSK_Box_Monster_Lid_{n}"],
        data={"part_of": f"SM_CSK_Box_Monster_{n}", "pivot": "the skirt's bottom centre = the closed position (Lid)",
              "size_mm": [OW, OD, L], "reference": REF13,
              "notes": ["Sheet 13: lid skirt 57.5 (0.55 H on both sizes; spec E 40), hand holes in both ends."]},
    )


# =========================================================================== registry

ITEMS = {
    "de_storage_slab_thick": item_slab_thick,
    "de_storage_grade": item_grade_return,
    "de_storage_grade_lid": item_grade_return_lid,
    **{f"de_storage_row_{n}": (lambda n=n: item_row_box(n)) for n in ROW["lengths"]},
    **{f"de_storage_row_lid_{n}": (lambda n=n: item_row_box_lid(n)) for n in ROW["lengths"]},
    **{f"de_storage_monster_{n}": (lambda n=n: item_monster_box(n)) for n in MONSTER},
    **{f"de_storage_monster_lid_{n}": (lambda n=n: item_monster_lid(n)) for n in MONSTER},
}
