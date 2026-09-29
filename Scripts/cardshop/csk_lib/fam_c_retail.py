"""Card Shop Kit family c_retail: singles & protection (CARDSHOP_KIT_SPEC.md 3.C rows C1-C7) and the eight retail
accessories of row B8 (P3-P5).

    C1 SM_CSK_Card_Small                                       reference sheet 1 (csk_card.png)
    C2 SM_CSK_CardStack_{10,30,90}                             reference sheet 1
    C3 SM_CSK_Sleeve_Penny                                     reference sheet 8 (1) (csk_sleeves_holders.png)
    C4 SM_CSK_Sleeve_Deck_{Std,Small}                          reference sheet 8 (2)
    C5 SM_CSK_TopLoader_35pt_Filled                            reference sheet 2 (csk_toploader.png)
    C6 SM_CSK_Holder_SemiRigid                                 reference sheet 8 (3)
    C7 SM_CSK_Holder_Magnetic + _Front + _Back + _Filled       reference sheet 8 (4)
    B8 SM_CSK_Retail_{SleeveBox100, TopLoaderPack25, PennyPack100, DiceClam, BinderWrapped, PlaymatTube,
       DeckBoxPack, CleanerBottle}                             reference sheet 12 (2)-(9) (csk_blister_retail.png)

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = a spec
estimate with a source range. "sheet N" = read off that reference sheet (the picture wins over E numbers; M and D
numbers and the sheet's own printed dimensions win over the picture's proportions: REFERENCE_LOG "Scale rule"). On
sheet 12 the picture's vertical and horizontal scales disagree with its printed sizes by up to 15 %, so horizontal
features are scaled by the printed width and vertical ones by the printed height.

Frames (spec 4.2): millimetres, pivot = Seat. Cards, sleeves and holders lie on their back (face up, +Y = the card's
top edge, the open end). The B8 accessories stand upright (W x D x H as the spec's table: +X right, +Y away from the
customer, +Z up); a hanging item's `Hang` socket is the apex of its euro slot's peak on the tab mid-plane with an
identity rotation, so item world = hook point x inverse(Hang) hangs it plumb, face to the customer.

Print (spec 4.1): the cards and sleeves use the card tiles (front (0,0), back (1,0)). Every B8 accessory is one cell of
the Boxes atlas (`M_CSK_BoxPrint`): its printed panels are laid out as a dieline inside tile (0,0) (regions 10+, as the
booster box), and each item's `.csk.json` carries the layout (`print_layout`: panel rectangles in sheet mm) and the
sheet-12 colour blocks (`print_art`) so the art pass can paint the two-tone cells. Dice pips are "baked detail" (spec):
the dice's visible faces are print panels.

No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import R_BACK, R_FRONT, Item, Lod, Socket, _face_out, _planar, _toploader_lod, inset
from .shapes import Builder, circle, rect, rounded_rect

Vec3 = Tuple[float, float, float]
R_EDGE_BAND = 4                     # the card stacks' edge-stripe band (U -1 tile)

# =========================================================================== numbers: C rows

STACK = dict(                       # C2, sheet 1 (three squared-up stacks with rounded corners)
    w=63.0, h=88.0, r=3.0,          # M [D1] card; R 3 E (as C1)
    heights=(10.0, 30.0, 90.0),     # spec (10 = 33 cards at 0.30, D)
    segs=3,                         # 4 points a corner: 16 x 4 - 4 = 60 tris, the spec's budget exactly
    edge_tile_mm=90.0,              # the edge band's V spans 90 mm of stack in every size: one stripe texture fits all
)

PENNY = dict(                       # C3, sheet 8 (1)
    w=66.7, h=92.1,                 # M in inches [D3]
    t=0.5, film=0.05,               # spec: 2 skins 0.4 apart + 2 x 0.05 film (D/E)
    taper=1.75,                     # sheet 8 end view: a lens mouth, the skins meet in a welded knife edge; the full
                                    # gap spans |x| <= 31.6 so a 63 card lies flat (E)
    seam=0.3,                       # E: side weld (the inner lens ends 0.3 inside the edge)
    bottom=1.0,                     # E: bottom weld
)

DECK_SLEEVE = dict(                 # C4, sheet 8 (2)
    sizes={"Std": (66.0, 91.0), "Small": (62.0, 89.0)},   # M [D1]
    t=0.6, film=0.1,                # E: 100-micron film, 0.4 card gap (card 0.30)
    wrap=1.0,                       # sheet 8: the coloured back wraps round both long edges and the bottom, ~1 mm seen
                                    # from the front (built as the slanted edge faces)
    clear=1.2,                      # E: pocket wall inside the outer edge
)

TL_FILLED = dict(                   # C5 Filled: the G1 top-loader (spec.TOPLOADER_35, sheet 2) + the card print
    print_d=0.05,                   # the card print lies 0.05 under the clear-coat skin (a region split, as the slab)
    print_d_far=0.2,                # LOD2: 0.05 walls met LOD2's corners in 0.004 mm^2 tris, which Unreal drops
)

SEMI = dict(                        # C6, sheet 8 (3)
    w=84.1, h=123.8,                # M in inches [D5]
    t=1.0, skin=0.25,               # E: 2 x 0.25 sheets + a 0.5 pocket (holds a penny-sleeved card, 0.5)
    r=3.0,                          # sheet 8: rounded outer corners (reads 3)
    border=4.0,                     # sheet 8: the flat welded border round the pocket, ~4 wide
    pocket_r=3.0,                   # sheet 8: the pocket's bottom corners are rounded like the outline
    tab=(22.3, 10.1, 2.7),          # sheet 8 measured (2.96 px/mm): W x H above the top edge x corner R. The spec's
                                    # E 30 x 12 and the first note's 28 x 9 read larger; the picture wins
    tab_t=(0.03, 0.22),             # the tab is the back sheet's extension (z 0.03..0.22 inside the 0.25 sheet)
)

MAG = dict(                         # C7, sheet 8 (4)
    w=74.3, h=110.4, t=6.0,         # M [D6] outer; T 6 E
    r=3.6,                          # sheet 8: outer corner R (reads 3.6 at 8.4 px/mm)
    well=(67.6, 94.7), well_r=2.5,  # E* well; R 2.5 E (sheet 8: rounded well corners)
    well_d=0.5,                     # E: a 0.5 recess in each half = a 1.0 card well (>= 0.76, the thickest card, M)
    magnet=6.0, magnet_d=0.4,       # Ø 6 E (sheet 8 agrees); the magnet disc sits 0.4 under each face
    magnet_xy=(30.65, 51.3),        # sheet 8: 6.5 in from the side edge; 3.9 from the top edge (the picture's 6
                                    # would cut the E* well: the well wins)
    groove=0.3,                     # the parting line: a 0.3 chamfer on each half's meeting rim (sheet 8 side view)
    open_mm=30.0,                   # E: the halves pull apart along Z
)

# =========================================================================== numbers: B8 (sheet 12)

EURO = dict(fillet=0.8)             # E: the concave fillets where the peak meets the slot's top edge (sheet 12 draws
                                    # them round)

SLEEVE_BOX = dict(                  # B8 SleeveBox100, sheet 12 (2)
    w=72.0, d=42.0, h=98.0,         # E (spec)
    tab=24.0,                       # sheet 12: 23.5-25.7 by view (spec E 40); flush with the back panel
    tab_t=0.8, tab_r=2.8,           # E: a double board; sheet 12 corner R 2.8
    slot=(24.4, 5.4, 3.4, 13.0),    # sheet 12 euro slot: length, height, peak R, centre below the tab top
    split=36.0,                     # sheet 12: the light bottom band is 36 of the 98
    bevel=0.5,                      # folded board edges
    colours=("#862a30", "#e35b55"), # sheet 12 (sampled): dark top, light bottom
)

TL_PACK = dict(                     # B8 TopLoaderPack25, sheet 12 (3)
    w=82.0, d=35.0, h=108.0,        # E (spec): the bag without the header
    header=42.3,                    # sheet 12 (spec E 30): navy 26.1 over a light-blue band 16.2
    band=16.2,
    header_t=1.2,                   # E: folded card, two 0.4 boards and the bag's seal between
    slot=(20.4, 5.2, 3.25, 12.3),   # sheet 12
    seal=(1.5, 3.0),                # the bag: flat bottom seal to 1.5, full depth from 3.0 (a tight pillow bag)
    top=(105.0, 106.5, 5.0),        # full depth to 105, flat seal from 106.5; the seal runs 5 up into the header
    chamfer=2.5,                    # the bag's rounded long edges (the stack's corners must stay inside)
    stack=(76.2, 101.6, 33.0, 3.5),  # the 25 top-loaders: M [D4] outline, 33 thick (fits the 35 bag), corner R 3.5
    colours=("#1b3b73", "#5a9ce3"),
)

PENNY_PACK = dict(                  # B8 PennyPack100, sheet 12 (4)
    w=72.0, d=12.0, h=97.0,         # E (spec)
    header=37.0,                    # sheet 12 (spec E 25): dark red 22.3 over a light-red band 14.7
    band=14.7,
    header_t=1.2,
    slot=(20.3, 4.6, 3.0, 10.6),    # sheet 12
    seal=(1.5, 3.0),
    top=(95.5, 96.3, 5.0),
    chamfer=1.5,
    stack=(66.7, 92.1, 10.0, 0.0),  # 100 penny sleeves: M [D3] outline x 100 x 0.1 (D)
    colours=("#97292e", "#f16a61"),
)

DICE_CLAM = dict(                   # B8 DiceClam, sheet 12 (5)
    w=60.0, d=25.0, h=130.0,        # E (spec, incl. the tab). The picture is drawn 176 tall at its 60 width; the
                                    # printed 130 wins, so the dice layout is compressed vertically (see notes)
    r=5.0,                          # sheet 12: clam corner R
    sheet_t=0.6,                    # E: the sealed back + flange (two 0.3 PET films)
    slot=(25.6, 5.4, 3.5, 11.6),    # sheet 12 (the clam's own slot, in the clear tab)
    tab=18.6,                       # sheet 12: the flat clear tab above the card compartment
    plateau=(2.7, 3.0, 4.0),        # sheet 12: compartment inset from the sides, proud of the flange, bottom margin
    card=(1.8, 0.5, 3.0),           # the insert card: inset in the compartment, thickness, corner R (E)
    card_slot=(24.2, 4.7, 3.4, 11.3),  # sheet 12: the insert card's own euro slot (below the clam's)
    die=16.0,                       # M [D20] d6
    cols=18.4,                      # sheet 12: column pitch (16 + 2.4)
    rows=(80.5, 60.5, 40.5, 18.5),  # E from sheet 12: row centres (2 + 2 + 2 + 1 dice); pitch 20 / 20 / 22
    bubble=(44.0, 83.0, 49.5, 4.0, 2.0),  # sheet 12: dice bubble W x H, centre z, corner R; front chamfer 2 (E)
    split=28.0,                     # sheet 12: the lime band starts just above the bottom die
    colours=("#3f4e2e", "#889642"), die_colour="#0e3885",
)

BINDER = dict(                      # B8 BinderWrapped, sheet 12 (6)
    w=250.0, d=55.0, h=295.0,       # E (spec) overall, film included
    film=0.4,                       # E: shrink-film clearance
    spine_r=6.0, fore_r=2.0,        # sheet 12: padded spine with round edges; square-ish fore-edge corners
    rim=2.0,                        # E: the padded covers' rounded rims (a 45-degree chamfer ring, printed)
    board=3.5,                      # E: cover thickness at the fore-edge
    recess=3.0,                     # sheet 12: the covers stand proud of the page block at the top, bottom and fore-edge
    split=97.0,                     # sheet 12: the light-purple bottom band (~1/3 of 295)
    colours=("#2e254d", "#664b9b"),
)

TUBE = dict(                        # B8 PlaymatTube, sheet 12 (7)
    r_cap=35.0, h=380.0,            # E (spec) Ø 70 x 380 (the caps are the widest part)
    r_tube=33.5,                    # E: the caps slip over the tube (1.5 wall)
    cap=40.0,                       # sheet 12: caps 39-42 tall
    cap_chamfer=2.0,                # sheet 12: softly rounded cap rims
    label=(40.0, 219.0, 98.0),      # sheet 12: the label starts at the bottom cap, 219 long, lime 98 under dark green
    roll=(22.5, 356.0),             # E5 Rolled Ø 45 x 356 (D). The picture draws the roll fuller (~Ø 58); D wins
    sides=14,                       # 14 sides: 25.7 deg < the 30-deg sharp-edge rule, so the round parts shade smooth
    colours=("#344126", "#88993d"),
)

DECK_PACK = dict(                   # B8 DeckBoxPack, sheet 12 (8)
    w=82.0, d=86.0, h=116.0,        # E (spec)
    tab=25.0, tab_t=0.8, tab_r=2.8,  # sheet 12: a hang tab above the back panel (spec lists none; the picture wins)
    slot=(22.0, 5.1, 3.2, 12.7),    # sheet 12
    window=(59.3, 86.5, 52.45, 4.3),  # sheet 12: die-cut W x H, centre z, corner R (9.2 above the bottom, 20.3 below
                                    # the top, centred)
    deckbox=(76.0, 80.0, 108.0),    # E4 outer (spec E); it sits centred, 3 behind the front board
    flap=(43.8, 0.8),               # sheet 12: the deck box's flap lid ends 43.8 above the carton bottom; 0.8 proud
    split=38.0,                     # sheet 12: the light-blue band is 38 of the 116
    bevel=0.5,
    colours=("#273c6e", "#4c8fd9"), deckbox_colour="#2c5eb1",
)

BOTTLE = dict(                      # B8 CleanerBottle, sheet 12 (9): 60 ml, Ø 40 x 140 (E, spec)
    # lathe profile (r, z) of the clear PET bottle, sheet 12 scaled to the printed Ø 40 x 140
    body=((18.5, 0.0), (20.0, 2.0), (20.0, 7.3), (20.0, 85.8), (17.0, 92.0), (12.5, 96.0), (12.0, 99.5)),
    label=(7.3, 85.8, 30.7),        # sheet 12: label from 7.3 to 85.8; the light band is the bottom 30.7
    collar=(13.5, 98.5, 115.5, 7.0),  # sheet 12: the white ribbed collar Ø 27 x 17; the pump stem R 7
    head=(7.0, 115.5, 133.0),       # sheet 12: the white pump head Ø 14 inside the overcap
    cap=(10.25, 115.5, 140.0),      # sheet 12: the clear overcap Ø 20.5 x 24.5
    sides=16,
    colours=("#731c23", "#da4e4b"),
)

# LOD0 budgets: the spec's Tris column (E). Raised (logged in the report):
#   Retail_PennyPack100 150 -> 220: the euro slot is a real hole through the header, and the pillow bag and the
#     sleeve stack are real forms (the TopLoader pack's construction at 300).
#   Retail_PlaymatTube 300: kept (14-sided round parts).
#   Holder_Magnetic_Front / _Back: no spec row of their own (the C7 row's 800 is the closed holder); 500 each (E).
BUDGETS = {
    "SM_CSK_Card_Small": 96,
    "SM_CSK_CardStack": 60,
    "SM_CSK_Sleeve_Penny": 60,
    "SM_CSK_Sleeve_Deck": 80,
    "SM_CSK_TopLoader_35pt_Filled": 396,      # spec "300 (+ 96)": the holder + the card
    "SM_CSK_Holder_SemiRigid": 150,
    "SM_CSK_Holder_Magnetic": 800,
    "SM_CSK_Holder_Magnetic_Half": 500,
    "SM_CSK_Holder_Magnetic_Filled": 800,
    "SM_CSK_Retail_SleeveBox100": 200,
    "SM_CSK_Retail_TopLoaderPack25": 300,
    "SM_CSK_Retail_PennyPack100": 220,
    "SM_CSK_Retail_DiceClam": 400,
    "SM_CSK_Retail_BinderWrapped": 500,
    "SM_CSK_Retail_PlaymatTube": 300,
    "SM_CSK_Retail_DeckBoxPack": 300,
    "SM_CSK_Retail_CleanerBottle": 400,
}

# The Small card has its own class so the Small deck sleeve's contain test seats the Small card (a Std card does not
# fit a 62-wide sleeve). Pitch = footprint + 10 (spec 4.2).
CLASSES = {
    "CardSmall": S.ItemClass("CardSmall", (59.0, 86.0, 0.3), (69.0, 96.0)),
}

PRINT, FILM = 0, 1                  # B8 slot order: every accessory lists M_CSK_BoxPrint first


# =========================================================================== shared helpers

def _loop_xz(b: Builder, pts, y: float) -> List[int]:
    return [b.v(x, y, z) for x, z in pts]


def _area2(pts) -> float:
    return sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, list(pts[1:]) + [pts[0]]))


def _ccw(pts):
    return list(pts) if _area2(pts) > 0 else list(reversed(pts))


def _walls_xz(b: Builder, pts, a: List[int], c: List[int], hole: bool, mat: int, region: int = 0) -> None:
    """Side walls between two loops of an XZ outline (``a`` at the front y, ``c`` behind). Solid outlines face out,
    holes face into the hole."""
    n = len(pts)
    sgn = -1.0 if hole else 1.0
    for i in range(n):
        j = (i + 1) % n
        dx, dz = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
        _face_out(b, [a[i], a[j], c[j], c[i]], (sgn * dz, 0.0, -sgn * dx), mat, region)


def _slab_y(b: Builder, outline, holes, y0: float, y1: float, mat: int, front: int = 0, back: int = 0,
            front_mat: Optional[int] = None, back_mat: Optional[int] = None, side_mat: Optional[int] = None) -> None:
    """A flat plate along Y (front face at y0 faces -Y, back at y1 faces +Y) from a CCW XZ outline with holes."""
    outline = _ccw(outline)
    holes = [_ccw(h) for h in holes]
    of, ob = _loop_xz(b, outline, y0), _loop_xz(b, outline, y1)
    sm = mat if side_mat is None else side_mat
    _walls_xz(b, outline, of, ob, False, sm)
    hf, hb = [], []
    for h in holes:
        a, c = _loop_xz(b, h, y0), _loop_xz(b, h, y1)
        _walls_xz(b, h, a, c, True, sm)
        hf.append(a)
        hb.append(c)
    b.fill([of] + hf, mat if front_mat is None else front_mat, front, (0, -1, 0))
    b.fill([ob] + hb, mat if back_mat is None else back_mat, back, (0, 1, 0))


def _prism_xz(b: Builder, outline, y0: float, y1: float, mat: int, front: Optional[int] = 0,
              back: Optional[int] = 0, front_mat: Optional[int] = None) -> Tuple[List[int], List[int]]:
    """A prism along Y from an XZ outline; ``front`` / ``back`` None leaves that cap open."""
    outline = _ccw(outline)
    of, ob = _loop_xz(b, outline, y0), _loop_xz(b, outline, y1)
    _walls_xz(b, outline, of, ob, False, mat)
    if front is not None:
        b.fill([of], mat if front_mat is None else front_mat, front, (0, -1, 0))
    if back is not None:
        b.fill([ob], mat, back, (0, 1, 0))
    return of, ob


def _stitch(b: Builder, ra: List[int], rc: List[int], out_dir: Callable[[int], Vec3], mat: int,
            region=0) -> None:
    """Quads between two rings of equal length; ``out_dir(i)`` is the wanted normal of quad i; ``region`` an int or a
    function of the quad index."""
    n = len(ra)
    for i in range(n):
        j = (i + 1) % n
        reg = region(i) if callable(region) else region
        _face_out(b, [ra[i], ra[j], rc[j], rc[i]], out_dir(i), mat, reg)


def _rrect_xz(w: float, h: float, r: float, segs: int, cx: float = 0.0, cz: float = 0.0):
    return [(x + cx, y + cz) for x, y in rounded_rect(w, h, r, segs)] if segs > 0 else rect(w, h, cx, cz)


def _top_rounded(w: float, z0: float, z1: float, r: float, segs: int, cx: float = 0.0):
    """A tab outline in XZ: square bottom corners at z0, rounded top corners (R ``r``) at z1; CCW."""
    pts = [(cx - w / 2, z0), (cx + w / 2, z0)]
    for c_x, a0 in ((cx + w / 2 - r, 0.0), (cx - w / 2 + r, 90.0)):
        n = max(segs, 1)
        pts += [(c_x + r * math.cos(math.radians(a0 + 90.0 * k / n)), z1 - r + r * math.sin(math.radians(a0 + 90.0 * k / n)))
                for k in range(n + 1)]
    return pts


def _euro_slot(cx: float, cz: float, length: float, height: float, peak_r: float, segs_end: int, segs_peak: int,
               fillet: float = EURO["fillet"]):
    """Sheet 12's euro hang slot: a rounded slot (stadium) with a half-round peak on its top edge, joined by small
    concave fillets. XZ points, CCW; ``segs_peak`` 0 = a plain slot (far LODs)."""
    r = height / 2
    xr = length / 2 - r
    zt = cz + r
    pts = [(cx + xr + r * math.cos(math.radians(-90 + 180 * k / segs_end)),
            cz + r * math.sin(math.radians(-90 + 180 * k / segs_end))) for k in range(segs_end + 1)]
    if segs_peak > 0:
        f = fillet if segs_peak >= 4 else 0.0
        if f > 0:
            xf = math.sqrt((peak_r + f) ** 2 - f * f)
            a_t = math.atan2(f, xf)                      # the tangent point's direction on the peak circle
            # right fillet: centre (cx + xf, zt + f), from the slot's top line (angle -90) round to the peak
            fr = [(cx + xf + f * math.cos(t), zt + f + f * math.sin(t))
                  for t in _arc(-math.pi / 2, math.atan2(-f, -xf), 2)]
            pts += [(cx + xf, zt)] + fr[1:-1]
            pts += [(cx + peak_r * math.cos(t), zt + peak_r * math.sin(t))
                    for t in _arc(a_t, math.pi - a_t, segs_peak)]
            fl = [(cx - xf + f * math.cos(t), zt + f + f * math.sin(t))
                  for t in _arc(math.atan2(-f, xf), -math.pi / 2, 2)]
            pts += fl[1:-1] + [(cx - xf, zt)]
        else:
            pts += [(cx + peak_r * math.cos(math.pi * k / segs_peak), zt + peak_r * math.sin(math.pi * k / segs_peak))
                    for k in range(segs_peak + 1)]
    pts += [(cx - xr + r * math.cos(math.radians(90 + 180 * k / segs_end)),
             cz + r * math.sin(math.radians(90 + 180 * k / segs_end))) for k in range(segs_end + 1)]
    return pts


def _arc(a0: float, a1: float, n: int) -> List[float]:
    """n + 1 angles from a0 to a1 the short way round."""
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    return [a0 + d * k / n for k in range(n + 1)]


def _slot_apex(cz: float, height: float, peak_r: float) -> float:
    return cz + height / 2 + peak_r


class Sheet:
    """A print dieline inside UV tile (0,0) (spec 4.1: boxes use regions 10+). Each panel is one region with a map
    (x, y, z) -> (s, t) in panel millimetres, placed at (u0, v0) on the sheet; the sheet is scaled to the tile."""

    def __init__(self):
        self.panels: Dict[int, Tuple[str, Callable, float, float, float, float]] = {}
        self.next_region = 10

    def add(self, name: str, fn: Callable, w: float, h: float, u0: float, v0: float, region: Optional[int] = None) -> int:
        if region is None:
            region = self.next_region
        self.next_region = max(self.next_region, region + 1)
        self.panels[region] = (name, fn, w, h, u0, v0)
        return region

    def planar(self, name: str, o: Vec3, eu: Vec3, ev: Vec3, w: float, h: float, u0: float, v0: float) -> int:
        def fn(x, y, z, o=o, eu=eu, ev=ev):
            p = (x - o[0], y - o[1], z - o[2])
            return (p[0] * eu[0] + p[1] * eu[1] + p[2] * eu[2], p[0] * ev[0] + p[1] * ev[1] + p[2] * ev[2])
        return self.add(name, fn, w, h, u0, v0)

    def size(self) -> Tuple[float, float]:
        U = max(p[4] + p[2] for p in self.panels.values())
        V = max(p[5] + p[3] for p in self.panels.values())
        return U, V

    def projections(self) -> Dict[int, Callable]:
        U, V = self.size()
        out = {}
        for region, (_n, fn, w, h, u0, v0) in self.panels.items():
            def proj(x, y, z, fn=fn, u0=u0, v0=v0, w=w, h=h):
                s, t = fn(x, y, z)
                s = min(max(s, 0.0), w)
                t = min(max(t, 0.0), h)
                return (inset((u0 + s) / U), inset((v0 + t) / V))
            out[region] = proj
        return out

    def layout(self) -> Dict:
        U, V = self.size()
        return {"tile": [0, 0], "sheet_mm": [round(U, 3), round(V, 3)],
                "panels": {n: [round(u0, 3), round(v0, 3), round(w, 3), round(h, 3)]
                           for (n, _f, w, h, u0, v0) in self.panels.values()}}


def _box_panels(sh: Sheet, W: float, D: float, H: float, z0: float = 0.0, gap: float = 4.0,
                v_base: float = 0.0) -> Dict[str, int]:
    """Box dieline: bottom | [front right back left] row | top over the front. Returns region ids by side."""
    g = gap
    vb = v_base
    vr = vb + D + g
    reg = {}
    reg["nz"] = sh.planar("bottom", (-W / 2, D / 2, z0), (1, 0, 0), (0, -1, 0), W, D, 0.0, vb)
    reg["ny"] = sh.planar("front", (-W / 2, -D / 2, z0), (1, 0, 0), (0, 0, 1), W, H, 0.0, vr)
    reg["px"] = sh.planar("right", (W / 2, -D / 2, z0), (0, 1, 0), (0, 0, 1), D, H, W + g, vr)
    reg["py"] = sh.planar("back", (W / 2, D / 2, z0), (-1, 0, 0), (0, 0, 1), W, H, W + D + 2 * g, vr)
    reg["nx"] = sh.planar("left", (-W / 2, D / 2, z0), (0, -1, 0), (0, 0, 1), D, H, 2 * W + D + 3 * g, vr)
    reg["pz"] = sh.planar("top", (-W / 2, -D / 2, z0 + H), (1, 0, 0), (0, 1, 0), W, D, 0.0, vr + H + g)
    return reg


def _two_tone(layout: Dict, panels: Sequence[str], split_from_bottom: Dict[str, float], colours, extra=()) -> List:
    """print_art: the sheet-12 colour blocks as sheet rectangles [u0, v0, w, h, colour] (dark over light)."""
    out = []
    P = layout["panels"]
    for n in panels:
        u0, v0, w, h = P[n]
        s = split_from_bottom.get(n)
        if s is None:
            out.append([u0, v0, w, h, colours[0]])
        else:
            s = min(max(s, 0.0), h)
            out.append([u0, v0, w, s, colours[1]])
            out.append([u0, v0 + s, w, h - s, colours[0]])
    return out + list(extra)


def _hang_data(T: float, apex: Vec3) -> Dict:
    return {"socket": "Hang", "T_mm": T, "pitch_mm": T + 2.0,
            "note": "Hang = the euro slot's peak apex on the tab mid-plane, identity rotation: item world = hook "
                    "point x inverse(Hang) hangs the item plumb, its front toward the customer"}


def _upright_sockets(W: float, D: float, H: float, H_all: float, hang: Optional[Vec3] = None) -> List[Socket]:
    s = [Socket("Seat", (0, 0, 0))]
    if hang is not None:
        s.append(Socket("Hang", hang))
    s += [Socket("Stack", (0, 0, H_all)), Socket("Face", (0, -D / 2, H / 2), (90.0, 0.0, 0.0)),
          Socket("Grip", (0, -D / 2, H / 2))]
    return s


# =========================================================================== C1 small card

def item_card_small() -> Item:
    c = S.CARD_SMALL
    b = Builder()
    b.prism(rounded_rect(c["w"], c["h"], c["r"], c["corner_segs"]), 0.0, c["t"], top=R_FRONT, bottom=R_BACK)
    x0, y0, t = -c["w"] / 2, -c["h"] / 2, c["t"]
    pad = S.HANDHELD_HULL_MIN_T / 2
    return Item(
        name="SM_CSK_Card_Small", lods=[Lod(b)], materials=["M_CSK_Card"],
        projections={R_FRONT: _planar(x0, y0, c["w"], c["h"]),
                     R_BACK: _planar(x0, y0, c["w"], c["h"], tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Face", (0, 0, t)), Socket("Grip", (0, y0, t / 2))],
        hulls=[((x0, y0, t / 2 - pad), (-x0, -y0, t / 2 + pad))], cls="CardSmall",
        budget=BUDGETS["SM_CSK_Card_Small"],
        data={"footprint_mm": [c["w"], c["h"], t], "stack": {"socket": "Face", "pitch_mm": t, "max": 5},
              "reference": "References/CardShop/csk_card.png (sheet 1)",
              "notes": ["C1 Small: the Std card (geom.item_card) at 59 x 86 (M [D1]); same tiles and slot.",
                        "Class CardSmall (59 x 86, pitch 69 x 96): the Small deck sleeve holds only this card."]},
    )


# =========================================================================== C2 card stacks

def item_card_stack(H: float) -> Item:
    s = STACK
    w, h = s["w"], s["h"]
    pts = rounded_rect(w, h, s["r"], s["segs"])
    b = Builder()
    b.prism(pts, 0.0, H, top=R_FRONT, bottom=R_BACK, side=R_EDGE_BAND)
    per = sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
    cum = [0.0]
    for i in range(len(pts)):
        cum.append(cum[-1] + math.dist(pts[i], pts[(i + 1) % len(pts)]))
    lookup = {(round(p[0], 4), round(p[1], 4)): cum[i] for i, p in enumerate(pts)}
    E = s["edge_tile_mm"]

    def edge(x, y, z):
        # arc length round the outline (the seam at point 0, the -Y side right corner); the last column wraps to per
        a = lookup.get((round(x, 4), round(y, 4)), 0.0)
        return (-1.0 + inset(a / per), inset(z / E))

    # the seam face (last point -> first point) must reach u = per, not 0: a second band region for that face
    name = f"SM_CSK_CardStack_{int(H)}"
    x0, y0 = -w / 2, -h / 2
    n = len(pts)
    for f in b.faces:
        if f.region == R_EDGE_BAND and (0 in [v % n for v in f.verts]) and ((n - 1) in [v % n for v in f.verts]):
            f.region = R_EDGE_BAND + 1
    def edge_seam(x, y, z):
        a = lookup.get((round(x, 4), round(y, 4)), 0.0)
        if a == 0.0:
            a = per
        return (-1.0 + inset(a / per), inset(z / E))
    return Item(
        name=name, lods=[Lod(b)], materials=["M_CSK_Card"],
        projections={R_FRONT: _planar(x0, y0, w, h), R_BACK: _planar(x0, y0, w, h, tile_u=1.0, mirror_x=True),
                     R_EDGE_BAND: edge, R_EDGE_BAND + 1: edge_seam},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Top", (0, 0, H))],
        hulls=[((x0, y0, 0.0), (-x0, -y0, H))], cls=None, budget=BUDGETS["SM_CSK_CardStack"],
        data={"footprint_mm": [w, h, H], "cards": int(round(H / S.CARD_STD["t"])),
              "edge_band": {"tile": [-1, 0], "u": "arc length round the outline / perimeter",
                            "v_mm_per_tile": E,
                            "note": "one stripe texture serves all three stacks: 0.30 mm per card over 90 mm of V"},
              "reference": "References/CardShop/csk_card.png (sheet 1)",
              "notes": ["Sheet 1: squared-up stacks with the card's rounded corners and layered edge lines "
                        "(edge-stripe texture)."]},
    )


# =========================================================================== C3 penny sleeve

def item_sleeve_penny() -> Item:
    p = PENNY
    w, h, T, f = p["w"], p["h"], p["t"], p["film"]
    xf = w / 2 - p["taper"]
    zc = T / 2
    xi = w / 2 - p["seam"]
    outer = [(-w / 2, zc), (-xf, 0.0), (xf, 0.0), (w / 2, zc), (xf, T), (-xf, T)]
    inner = [(-xi, zc), (-xf, f), (xf, f), (xi, zc), (xf, T - f), (-xf, T - f)]
    y0, y1 = -h / 2, h / 2
    yf = y0 + p["bottom"]
    b = Builder()
    # profile in (x, z), extruded along Y; the pocket opens at +Y
    ob = [b.v(x, y0, z) for x, z in outer]
    ot = [b.v(x, y1, z) for x, z in outer]
    ib = [b.v(x, yf, z) for x, z in inner]
    it = [b.v(x, y1, z) for x, z in inner]
    cx = lambda i, pts: ((pts[i][0] + pts[(i + 1) % 6][0]) / 2, (pts[i][1] + pts[(i + 1) % 6][1]) / 2)
    for i in range(6):
        j = (i + 1) % 6
        mx, mz = cx(i, outer)
        _face_out(b, [ob[i], ob[j], ot[j], ot[i]], (mx, 0.0, mz - zc), 0)
        mx, mz = cx(i, inner)
        _face_out(b, [ib[i], ib[j], it[j], it[i]], (-mx, 0.0, zc - mz), 0)
    b.fill([ob], 0, 0, (0, -1, 0))                     # the welded bottom end
    b.fill([ib], 0, 0, (0, 1, 0))                      # the pocket floor
    b.fill([ot, it], 0, 0, (0, 1, 0))                  # the lens-shaped mouth rim
    pad = S.HANDHELD_HULL_MIN_T / 2
    card = (0.0, yf + S.CARD_STD["h"] / 2, f)
    return Item(
        name="SM_CSK_Sleeve_Penny", lods=[Lod(b)], materials=["M_CSK_Film"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Card", card, kind="CONTAIN")],
        hulls=[((-w / 2, -h / 2, zc - pad), (w / 2, h / 2, zc + pad))], cls="Card",
        budget=BUDGETS["SM_CSK_Sleeve_Penny"],
        data={"footprint_mm": [w, h, T],
              "contain": {"Card": {"socket": "Card", "cavity_mm": [[-xf, yf, f], [xf, y1, T - f]],
                                   "accepts": ["Card"], "note": "a raw card (C1); the sleeved card is class Card"}},
              "reference": "References/CardShop/csk_sleeves_holders.png (sheet 8)",
              "notes": ["Sheet 8: a clear pouch open on the top short edge; the end view's lens-shaped mouth is the "
                        "hexagonal section (the skins meet in welded knife edges at the sides). The crinkled film is "
                        "texture (M_CSK_Film), not geometry."]},
    )


# =========================================================================== C4 deck sleeves

def item_sleeve_deck(size: str) -> Item:
    p = DECK_SLEEVE
    w, h = p["sizes"][size]
    T, f, a, cl = p["t"], p["film"], p["wrap"], p["clear"]
    FILMM, BACK = 0, 1
    b = Builder()
    B = [b.v(-w / 2, -h / 2, 0), b.v(w / 2, -h / 2, 0), b.v(w / 2, h / 2, 0), b.v(-w / 2, h / 2, 0)]
    F = [b.v(-w / 2 + a, -h / 2 + a, T), b.v(w / 2 - a, -h / 2 + a, T), b.v(w / 2 - a, h / 2, T),
         b.v(-w / 2 + a, h / 2, T)]
    _face_out(b, B, (0, 0, -1), BACK, R_BACK)                       # the coloured back (sleeve-back art)
    _face_out(b, F, (0, 0, 1), FILMM)                               # the clear front
    _face_out(b, [B[0], F[0], F[3], B[3]], (-T, 0, a), BACK)        # the back wrapping round the long edges ...
    _face_out(b, [B[1], B[2], F[2], F[1]], (T, 0, a), BACK)
    _face_out(b, [B[0], B[1], F[1], F[0]], (0, -T, a), BACK)        # ... and the bottom
    xi, yf, z0, z1 = w / 2 - cl, -h / 2 + cl, f, T - f
    I = [b.v(-xi, h / 2, z0), b.v(xi, h / 2, z0), b.v(xi, h / 2, z1), b.v(-xi, h / 2, z1)]
    J = [b.v(-xi, yf, z0), b.v(xi, yf, z0), b.v(xi, yf, z1), b.v(-xi, yf, z1)]
    _face_out(b, J, (0, 1, 0), BACK)                                # pocket floor
    _face_out(b, [J[0], J[1], I[1], I[0]], (0, 0, 1), BACK)         # inside of the back
    _face_out(b, [J[3], J[2], I[2], I[3]], (0, 0, -1), FILMM)       # inside of the front film
    _face_out(b, [J[0], J[3], I[3], I[0]], (1, 0, 0), BACK)
    _face_out(b, [J[1], J[2], I[2], I[1]], (-1, 0, 0), BACK)
    b.fill([[B[3], B[2], F[2], F[3]], I], BACK, 0, (0, 1, 0))       # the open top: the sleeve's cut edge
    card = S.CARD_STD if size == "Std" else S.CARD_SMALL
    name = f"SM_CSK_Sleeve_Deck_{size}"
    pad = S.HANDHELD_HULL_MIN_T / 2
    return Item(
        name=name, lods=[Lod(b)], materials=["M_CSK_Film", "M_CSK_SleeveBack"],
        projections={R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Card", (0.0, yf + card["h"] / 2, z0), kind="CONTAIN")],
        hulls=[((-w / 2, -h / 2, T / 2 - pad), (w / 2, h / 2, T / 2 + pad))], cls="CardProt",
        budget=BUDGETS["SM_CSK_Sleeve_Deck"],
        data={"footprint_mm": [w, h, T],
              "contain": {"Card": {"socket": "Card", "cavity_mm": [[-xi, yf, z0], [xi, h / 2, z1]],
                                   "accepts": ["Card" if size == "Std" else "CardSmall"],
                                   "note": "a raw card only (a penny-sleeved card does not fit a deck sleeve)"}},
              "reference": "References/CardShop/csk_sleeves_holders.png (sheet 8)",
              "notes": ["Sheet 8: clear front, matte coloured back (M_CSK_SleeveBack, back tile (1,0)) that wraps "
                        "round both long edges and the bottom as a ~1 mm border seen from the front: the slanted "
                        "edge faces. Open at the top. T 0.6 E."]},
    )


# =========================================================================== C5 top-loader, filled

def _toploader_filled_lod(level: int) -> Lod:
    s = S.TOPLOADER_35
    lod = _toploader_lod(s, level)
    h, t, ih = s["h"], s["t"], s["in_h"]
    c = S.CARD_STD
    ycard = h / 2 - ih + c["h"] / 2
    d = TL_FILLED["print_d_far" if level == 2 else "print_d"]
    segs = (4, 2, 0)[level]
    card = [(x, y + ycard) for x, y in (rounded_rect(c["w"], c["h"], c["r"], segs) if segs else rect(c["w"], c["h"]))]
    front, back = Builder(), Builder()
    front.prism(card, t - d, t + 1.0, top=0, bottom=R_FRONT)
    back.prism(card, -1.0, d, top=R_BACK, bottom=0)
    lod.ops = list(lod.ops) + [("DIFFERENCE", front), ("DIFFERENCE", back)]
    return lod


def item_toploader_filled() -> Item:
    s = S.TOPLOADER_35
    w, h, t = s["w"], s["h"], s["t"]
    c = S.CARD_STD
    ycard = h / 2 - s["in_h"] + c["h"] / 2
    x0, y0 = -c["w"] / 2, ycard - c["h"] / 2
    name = "SM_CSK_TopLoader_35pt_Filled"
    return Item(
        name=name, lods=[_toploader_filled_lod(k) for k in range(3)], materials=["M_CSK_TopLoaderFilled"],
        projections={R_FRONT: _planar(x0, y0, c["w"], c["h"]),
                     R_BACK: _planar(x0, y0, c["w"], c["h"], tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Face", (0, 0, t)), Socket("Grip", (0, -h / 2, t / 2)),
                 Socket("Stack", (0, 0, t))],
        hulls=[((-w / 2, -h / 2, 0), (w / 2, h / 2, t))], cls="CardProt", budget=BUDGETS[name],
        data={"footprint_mm": [w, h, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 20},
              "reference": "References/CardShop/csk_toploader.png (sheet 2)",
              "notes": ["The G1 top-loader shape (geom._toploader_lod: rounded corners, pocket, thumb notch) with "
                        "the card inside: 1 opaque Clear Coat section (spec 4.5), the card's front and back print "
                        "0.05 under the skins (card tiles (0,0) / (1,0)), the card seated at the pocket floor "
                        "as SM_CSK_TopLoader_35pt's Card socket."]},
    )


# =========================================================================== C6 semi-rigid holder

def item_holder_semirigid() -> Item:
    p = SEMI
    w, h, T, sk, bo = p["w"], p["h"], p["t"], p["skin"], p["border"]
    tw, th, tr = p["tab"]
    b = Builder()
    b.prism(rounded_rect(w, h, p["r"], 2), 0.0, T)
    xi, yf = w / 2 - bo, -h / 2 + bo
    pr = p["pocket_r"]
    pocket_pts = [(-xi, h / 2 + 2.0)]
    for cx, a0 in ((-xi + pr, 180.0), (xi - pr, 270.0)):
        pocket_pts += [(cx + pr * math.cos(math.radians(a0 + 45.0 * k)), yf + pr + pr * math.sin(math.radians(a0 + 45.0 * k)))
                       for k in range(3)]
    pocket_pts += [(xi, h / 2 + 2.0)]
    pocket = Builder()
    pocket.prism(pocket_pts, sk, T - sk)
    tab = Builder()
    z0, z1 = p["tab_t"]
    tab.prism([(x, z) for x, z in _top_rounded(tw, h / 2 - 1.0, h / 2 + th, tr, 2)], z0, z1)
    pad = S.HANDHELD_HULL_MIN_T / 2
    card = (0.0, yf + S.CARD_STD["h"] / 2, sk)
    name = "SM_CSK_Holder_SemiRigid"
    return Item(
        name=name, lods=[Lod(b, ops=[("DIFFERENCE", pocket)], extra=tab)], materials=["M_CSK_PVC"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Card", card, kind="CONTAIN")],
        hulls=[((-w / 2, -h / 2, T / 2 - pad), (w / 2, h / 2 + th, T / 2 + pad))], cls="CardProt",
        budget=BUDGETS[name],
        data={"footprint_mm": [w, h + th, T],
              "contain": {"Card": {"socket": "Card", "cavity_mm": [[-xi, yf, sk], [xi, h / 2, T - sk]],
                                   "accepts": ["Card"], "note": "a raw or penny-sleeved card (0.5 pocket)"}},
              "reference": "References/CardShop/csk_sleeves_holders.png (sheet 8)",
              "notes": ["Sheet 8: two clear stiff sheets welded round a 4 mm border (sides and bottom), open at the "
                        "top; the pull tab is the back sheet's extension at the top centre, 22.3 x 10.1 R 2.7 "
                        "(measured; spec E 30 x 12)."]},
    )


# =========================================================================== C7 magnetic holder

def _mag_rings(segs: int):
    m = MAG
    w, h = m["w"], m["h"]
    ww, wh = m["well"]
    O = rounded_rect(w, h, m["r"], segs)
    Oi = rounded_rect(w - 2 * m["groove"], h - 2 * m["groove"], m["r"] - m["groove"], segs)
    Wn = rounded_rect(ww, wh, m["well_r"], max(1, segs - 1))
    return O, Oi, Wn


def _mag_face(b: Builder, O, Wn, z: float, up: bool, body: int, window: int, magnets: int,
              card: Optional[Tuple[List, int]] = None) -> List[int]:
    """One face of a half at height z: the border (Body) with magnet pockets, the window region (Window, or for the
    filled holder a body ring round the card print)."""
    m = MAG
    n = (0, 0, 1) if up else (0, 0, -1)
    lo = b.loop(O, z)
    lw = b.loop(Wn, z)
    holes = []
    if magnets:
        mx, my = m["magnet_xy"]
        dz = -m["magnet_d"] if up else m["magnet_d"]
        for sx in (-1, 1):
            for sy in (-1, 1):
                pts = circle(m["magnet"] / 2, magnets, sx * mx, sy * my)
                top, bot = b.loop(pts, z), b.loop(pts, z + dz)
                for i in range(magnets):
                    j = (i + 1) % magnets
                    cxm, cym = (pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2
                    _face_out(b, [top[i], top[j], bot[j], bot[i]], (sx * mx - cxm, sy * my - cym, 0.0), body)
                b.fill([bot], body, 0, n)
                holes.append(top)
    b.fill([lo, lw] + holes, body, 0, n)
    if card is None:
        b.fill([lw], window, 0, n)
    else:
        pts, region = card
        lc = b.loop(pts, z)
        b.fill([lw, lc], body, 0, n)
        b.fill([lc], body, region, n)
    return lo


def _mag_cavity(b: Builder, Wn, z0: float, z1: float, body: int, window: int) -> None:
    """The closed holder's card well: a sealed cavity (faces point into it); floor and ceiling are window."""
    a, c = b.loop(Wn, z0), b.loop(Wn, z1)
    n = len(Wn)
    for i in range(n):
        j = (i + 1) % n
        mx, my = (Wn[i][0] + Wn[j][0]) / 2, (Wn[i][1] + Wn[j][1]) / 2
        _face_out(b, [a[i], a[j], c[j], c[i]], (-mx, -my, 0.0), body)
    b.fill([a], window, 0, (0, 0, 1))
    b.fill([c], window, 0, (0, 0, -1))


def _mag_sides(b: Builder, rings: Sequence[Tuple[Sequence, float]], body: int, first: List[int],
               last: List[int]) -> None:
    """Stitch the side bands between consecutive (outline, z) rings (all the same point count); the end rings are
    the faces' own outline loops (``first`` / ``last``), so no vertex is duplicated."""
    loops = [first] + [b.loop(o, z) for o, z in rings[1:-1]] + [last]
    for (o0, z0), (o1, z1), l0, l1 in zip(rings[:-1], rings[1:], loops[:-1], loops[1:]):
        n = len(o0)
        for i in range(n):
            j = (i + 1) % n
            dx, dy = o0[j][0] - o0[i][0], o0[j][1] - o0[i][1]
            # outward in XY: right for the vertical bands and the parting chamfers (which lean in or out)
            _face_out(b, [l0[i], l0[j], l1[j], l1[i]], (dy, -dx, 0.0), body)


def _mag_closed(level: int, filled: bool) -> Lod:
    m = MAG
    T = m["t"]
    segs = (4, 2, 1)[level]
    O, Oi, Wn = _mag_rings(segs)
    g = m["groove"] if level < 2 else 0.0
    body, window = 0, (0 if filled else 1)
    mags = (8, 0, 0)[level]
    b = Builder()
    card = None
    cardb = None
    if filled:
        c = S.CARD_STD
        cp = rounded_rect(c["w"], c["h"], c["r"], max(1, segs))
        card, cardb = (cp, R_FRONT), (cp, R_BACK)
    top = _mag_face(b, O, Wn, T, True, body, window, mags, card)
    bot = _mag_face(b, O, Wn, 0.0, False, body, window, mags, cardb)
    zm = T / 2
    if g > 0:
        rings = [(O, 0.0), (O, zm - g), (Oi, zm), (O, zm + g), (O, T)]
    else:
        rings = [(O, 0.0), (O, T)]
    _mag_sides(b, rings, body, bot, top)
    if not filled and level < 2:
        _mag_cavity(b, Wn, zm - m["well_d"], zm + m["well_d"], body, window)
    return Lod(b)


def _mag_half(level: int, front: bool) -> Lod:
    """One half as a separate part (the opening state): the outer face, the sides with the parting chamfer, the inner
    face with its well recess and magnets; in the closed holder's frame (front z 3..6, back 0..3)."""
    m = MAG
    T = m["t"]
    zm = T / 2
    segs = (4, 2, 1)[level]
    O, Oi, Wn = _mag_rings(segs)
    g = m["groove"] if level < 2 else 0.0
    mags = (8, 0, 0)[level]
    body, window = 0, 1
    b = Builder()
    z_out, z_in = (T, zm) if front else (0.0, zm)
    up = front
    lout = _mag_face(b, O, Wn, z_out, up, body, window, mags)
    # inner face: border with magnets round the well recess
    sgn = -1.0 if front else 1.0                     # the inner face's normal direction along z
    lo = b.loop(Oi if g > 0 else O, z_in)
    lw = b.loop(Wn, z_in)
    holes = []
    if mags:
        mx, my = m["magnet_xy"]
        dz = -sgn * m["magnet_d"]
        for sx in (-1, 1):
            for sy in (-1, 1):
                pts = circle(m["magnet"] / 2, mags, sx * mx, sy * my)
                top, bot = b.loop(pts, z_in), b.loop(pts, z_in + dz)
                for i in range(mags):
                    j = (i + 1) % mags
                    cxm, cym = (pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2
                    _face_out(b, [top[i], top[j], bot[j], bot[i]], (sx * mx - cxm, sy * my - cym, 0.0), body)
                b.fill([bot], body, 0, (0, 0, sgn))
                holes.append(top)
    b.fill([lo, lw] + holes, body, 0, (0, 0, sgn))
    zw = z_in - sgn * m["well_d"]
    lw2 = b.loop(Wn, zw)
    n = len(Wn)
    for i in range(n):
        j = (i + 1) % n
        mx_, my_ = (Wn[i][0] + Wn[j][0]) / 2, (Wn[i][1] + Wn[j][1]) / 2
        _face_out(b, [lw[i], lw[j], lw2[j], lw2[i]], (-mx_, -my_, 0.0), body)
    b.fill([lw2], window, 0, (0, 0, sgn))
    if g > 0:
        rings = [(Oi, z_in), (O, z_in - sgn * g), (O, z_out)]
    else:
        rings = [(O, z_in), (O, z_out)]
    ends = (lo, lout)
    if not front:
        rings = list(reversed(rings))
        ends = (lout, lo)
    _mag_sides(b, rings, body, *ends)
    return Lod(b)


def _mag_item(kind: str) -> Item:
    m = MAG
    w, h, T = m["w"], m["h"], m["t"]
    zm = T / 2
    ww, wh = m["well"]
    wd = m["well_d"]
    c = S.CARD_STD
    ref = "References/CardShop/csk_sleeves_holders.png (sheet 8)"
    cav = [[-ww / 2, -wh / 2, zm - wd], [ww / 2, wh / 2, zm + wd]]
    part = {"Front": {"mesh": "SM_CSK_Holder_Magnetic_Front", "socket": "Half", "type": "slide", "axis": "Z",
                      "range_mm": [0.0, m["open_mm"]]}}
    if kind == "closed":
        name = "SM_CSK_Holder_Magnetic"
        lods = [_mag_closed(k, False) for k in range(3)]
        mats = ["M_CSK_MagHolderBody", "M_CSK_MagHolderWindow"]
        sockets = [Socket("Seat", (0, 0, 0)), Socket("Card", (0, 0, zm - wd), kind="CONTAIN"),
                   Socket("Face", (0, 0, T)), Socket("Grip", (0, -h / 2, zm)), Socket("Stack", (0, 0, T))]
        hull = ((-w / 2, -h / 2, 0), (w / 2, h / 2, T))
        data = {"footprint_mm": [w, h, T], "stack": {"socket": "Stack", "pitch_mm": T, "max": 20},
                "contain": {"Card": {"socket": "Card", "cavity_mm": cav, "accepts": ["Card"]}},
                "states": {"closed": name, "open": ["SM_CSK_Holder_Magnetic_Back", "SM_CSK_Holder_Magnetic_Front"],
                           "filled": "SM_CSK_Holder_Magnetic_Filled"}}
        cls, budget = "CardProt", BUDGETS["SM_CSK_Holder_Magnetic"]
    elif kind == "filled":
        name = "SM_CSK_Holder_Magnetic_Filled"
        lods = [_mag_closed(k, True) for k in range(3)]
        mats = ["M_CSK_MagHolderFilled"]
        sockets = [Socket("Seat", (0, 0, 0)), Socket("Face", (0, 0, T)), Socket("Grip", (0, -h / 2, zm)),
                   Socket("Stack", (0, 0, T))]
        hull = ((-w / 2, -h / 2, 0), (w / 2, h / 2, T))
        data = {"footprint_mm": [w, h, T], "stack": {"socket": "Stack", "pitch_mm": T, "max": 20}}
        cls, budget = "CardProt", BUDGETS["SM_CSK_Holder_Magnetic_Filled"]
    else:
        front = kind == "front"
        name = "SM_CSK_Holder_Magnetic_Front" if front else "SM_CSK_Holder_Magnetic_Back"
        lods = [_mag_half(k, front) for k in range(3)]
        mats = ["M_CSK_MagHolderBody", "M_CSK_MagHolderWindow"]
        if front:
            sockets = [Socket("Seat", (0, 0, 0)), Socket("Face", (0, 0, T)), Socket("Grip", (0, -h / 2, 0.75 * T))]
            hull = ((-w / 2, -h / 2, zm), (w / 2, h / 2, T))
            data = {"part_of": "SM_CSK_Holder_Magnetic_Back", "pivot": "the closed holder's Seat (closed position)"}
        else:
            sockets = [Socket("Seat", (0, 0, 0)), Socket("Card", (0, 0, zm - wd), kind="CONTAIN"),
                       Socket("Half", (0, 0, 0)), Socket("Grip", (0, -h / 2, 0.25 * T))]
            hull = ((-w / 2, -h / 2, 0), (w / 2, h / 2, zm))
            data = {"parts": part, "pivot": "the closed holder's Seat",
                    "contain": {"Card": {"socket": "Card", "cavity_mm": [[-ww / 2, -wh / 2, zm - wd],
                                                                          [ww / 2, wh / 2, zm]], "accepts": ["Card"]}}}
        cls, budget = None, BUDGETS["SM_CSK_Holder_Magnetic_Half"]
    proj = {}
    if kind == "filled":
        proj = {R_FRONT: _planar(-c["w"] / 2, -c["h"] / 2, c["w"], c["h"]),
                R_BACK: _planar(-c["w"] / 2, -c["h"] / 2, c["w"], c["h"], tile_u=1.0, mirror_x=True)}
    data.update({"reference": ref,
                 "notes": ["Sheet 8: rounded-corner outer shape, a rounded card well, 4 round magnets in the border "
                           "corners (pockets 0.4 deep on both faces of each half; the Body section is opaque, spec), "
                           "the parting line as a 0.3 chamfer on each half's meeting rim. Halves pull apart along Z "
                           "(no hinge); each half's pivot is the closed position."]})
    return Item(name=name, lods=lods, materials=mats, projections=proj, sockets=sockets, hulls=[hull], cls=cls,
                budget=budget, data=data)


# =========================================================================== B8: box with a hang tab

def _tab(b: Builder, W: float, D: float, H: float, p: Dict, level: int, mat: int, front_r: int, back_r: int) -> float:
    """The hang tab (sheet 12): a board flush with the back panel, rising p["tab"] above the box top (sunk 1 into
    it, 0.05 inside the back face), rounded top corners and a euro slot cut through. Returns the slot apex z."""
    tab, tt, tr = p["tab"], p["tab_t"], p["tab_r"]
    L, Hs, pr, below = p["slot"]
    z1 = H + tab
    outline = _top_rounded(W, H - 1.0, z1, tr, (3, 1, 1)[level])
    cz = z1 - below
    holes = [] if level == 2 else [_euro_slot(0.0, cz, L, Hs, pr, (4, 1)[level], (6, 2)[level])]
    y1 = D / 2 - 0.05
    _slab_y(b, outline, holes, y1 - tt, y1, mat, front=front_r, back=back_r)
    return _slot_apex(cz, Hs, pr)


def _tab_panels(sh: Sheet, W: float, D: float, H: float, p: Dict, gap: float, v_top: float) -> Tuple[int, int]:
    """The tab's back face continues the back panel's art (above it); its front face goes above the top panel."""
    tab = p["tab"]
    y1 = D / 2 - 0.05
    P = sh.layout()["panels"]
    ub = P["back"][0]
    vb = P["back"][1] + P["back"][3]
    rb = sh.planar("tab_back", (W / 2, y1, H - 1.0), (-1, 0, 0), (0, 0, 1), W, tab + 1.0, ub, vb - 1.0 + gap)
    rf = sh.planar("tab_front", (-W / 2, y1 - p["tab_t"], H - 1.0), (1, 0, 0), (0, 0, 1), W, tab + 1.0, 0.0, v_top)
    return rf, rb


def item_sleeve_box() -> Item:
    p = SLEEVE_BOX
    W, D, H = p["w"], p["d"], p["h"]
    sh = Sheet()
    g = 4.0
    reg = _box_panels(sh, W, D, H, gap=g)
    v_top = sh.layout()["panels"]["top"][1] + D + g
    rf, rb = _tab_panels(sh, W, D, H, p, g, v_top)
    lods = []
    apex = 0.0
    for k in range(3):
        b = Builder()
        b.box((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H), mat=PRINT, regions=reg)
        t = Builder()
        apex = _tab(t, W, D, H, p, k, PRINT, rf, rb)
        lods.append(Lod(b, bevel_mm=p["bevel"] if k == 0 else None, extra=t))
    name = "SM_CSK_Retail_SleeveBox100"
    lay = sh.layout()
    Hall = H + p["tab"]
    y_tab = D / 2 - 0.05 - p["tab_t"] / 2
    split = p["split"]
    art = _two_tone(lay, ["front", "right", "back", "left"], {k: split for k in ("front", "right", "back", "left")},
                    p["colours"]) + _two_tone(lay, ["top", "bottom", "tab_front", "tab_back"], {}, p["colours"])
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint"], projections=sh.projections(),
        sockets=_upright_sockets(W, D, H, Hall, (0.0, y_tab, apex)),
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H)), ((-W / 2, D / 2 - 2.0, H), (W / 2, D / 2, Hall))],
        cls="Hang", budget=BUDGETS[name],
        data={"footprint_mm": [W, D, Hall], "hang": _hang_data(D, (0.0, y_tab, apex)),
              "stack": {"socket": "Stack", "pitch_mm": Hall, "max": 4},
              "print_layout": lay, "print_art": art,
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (2))",
              "notes": ["Sheet 12: a 72 x 42 x 98 carton, dark red over a light-red bottom band (36), with a hang tab "
                        "flush with the back panel: 24 tall (spec E 40; the notes read ~25), R 2.8 corners, a euro "
                        "slot 24.4 x 5.4 with an R 3.4 peak, cut through.",
                        "Holds a 66 x 91 sleeve pack in 68 x 38 x 94 (D); modelled closed (no contents socket)."]},
    )


# =========================================================================== B8: bag with a header (TL / penny)

def _bag_ring(w: float, d: float, cx: float, cy: float, n: int = 8):
    """The bag's section, CCW in XY: a rectangle with chamfered long edges (8 points; ``n`` 4 = a plain rectangle).
    At the flat welded seals the chamfer runs 3 along X and 0.1 across, so the seal ends have no sliver faces."""
    x, y = w / 2, d / 2
    if n == 4:
        return [(-x, -y), (x, -y), (x, y), (-x, y)]
    cy = min(cy, y * 0.9)
    return [(-x, -y + cy), (-x + cx, -y), (x - cx, -y), (x, -y + cy), (x, y - cy), (x - cx, y), (-x + cx, y),
            (-x, y - cy)]


def _bag(b: Builder, p: Dict, level: int, mat: int) -> None:
    """A clear pillow bag (sheet 12 side views): flat welded seals at the bottom and top (0.3 thick), full depth
    between; the top seal runs up into the header (hidden)."""
    W, D, H = p["w"], p["d"], p["h"]
    s0, s1 = p["seal"]
    f0, f1, into = p["top"]
    flat = 0.3
    zs = [[(0.0, flat), (s0, flat), (s1, D), (f0, D), (f1, flat), (H + into, flat)],
          [(0.0, flat), (s1, D), (f0, D), (H + into, flat)],
          [(0.0, D), (H + into, D)]][level]
    c = p["chamfer"]
    n = 8 if level == 0 else 4
    rings = []
    for z, d in zs:
        pts = _bag_ring(W, d, c if d > 1.0 else 3.0, c if d > 1.0 else 0.1, n)
        rings.append((pts, b.loop(pts, z)))
    for (pa, la), (pc, lc) in zip(rings[:-1], rings[1:]):
        def out(i, pa=pa):
            j = (i + 1) % len(pa)
            return (pa[j][1] - pa[i][1], -(pa[j][0] - pa[i][0]), 0.0)
        _stitch(b, la, lc, out, mat)
    b.fill([rings[0][1]], mat, 0, (0, 0, -1))
    b.fill([rings[-1][1]], mat, 0, (0, 0, 1))


def _header(b: Builder, p: Dict, level: int, mat: int, fr: int, br: int) -> float:
    W, H, hh, ht = p["w"], p["h"], p["header"], p["header_t"]
    L, Hs, pr, below = p["slot"]
    z1 = H + hh
    cz = z1 - below
    outline = rect(W, hh, 0.0, H + hh / 2)
    holes = [] if level == 2 else [_euro_slot(0.0, cz, L, Hs, pr, (4, 1)[level], (6, 2)[level])]
    _slab_y(b, outline, holes, -ht / 2, ht / 2, mat, front=fr, back=br)
    return _slot_apex(cz, Hs, pr)


def _bag_item(kind: str) -> Item:
    tl = kind == "tl"
    p = TL_PACK if tl else PENNY_PACK
    W, D, H, hh, ht = p["w"], p["d"], p["h"], p["header"], p["header_t"]
    sw, sh_, st, sr = p["stack"]
    sheet = Sheet()
    g = 4.0
    fr = sheet.planar("header_front", (-W / 2, -ht / 2, H), (1, 0, 0), (0, 0, 1), W, hh, 0.0, 0.0)
    br = sheet.planar("header_back", (W / 2, ht / 2, H), (-1, 0, 0), (0, 0, 1), W, hh, W + g, 0.0)
    CONT = 2
    lods = []
    apex = 0.0
    z_stack = p["seal"][1] + 0.2
    for k in range(3):
        b = Builder()
        apex = _header(b, p, k, PRINT, fr, br)
        _bag(b, p, k, FILM)
        segs = (4, 1, 0)[k] if sr > 0 else 0
        outline = _rrect_xz(sw, sh_, sr, segs, 0.0, z_stack + sh_ / 2) if segs else rect(sw, sh_, 0.0, z_stack + sh_ / 2)
        _prism_xz(b, outline, -st / 2, st / 2, CONT)
        lods.append(Lod(b))
    name = "SM_CSK_Retail_TopLoaderPack25" if tl else "SM_CSK_Retail_PennyPack100"
    Hall = H + hh
    lay = sheet.layout()
    art = _two_tone(lay, ["header_front", "header_back"], {"header_front": p["band"], "header_back": p["band"]},
                    p["colours"])
    what = ("25 top-loaders (M [D4] 76.2 x 101.6, a 33-thick block: 25 x the kit's 2.0 E would be 50, more than the "
            "bag's 35)" if tl else "100 penny sleeves (M [D3] 66.7 x 92.1 x 10)")
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Film", "M_CSK_PVC" if tl else "M_CSK_FilmStack"],
        projections=sheet.projections(),
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Hang", (0.0, 0.0, apex)), Socket("Stack", (0, 0, Hall)),
                 Socket("Face", (0, -D / 2, z_stack + sh_ / 2), (90.0, 0.0, 0.0)),
                 Socket("Grip", (0, -ht / 2, H + hh / 2))],
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H)), ((-W / 2, -1.0, H), (W / 2, 1.0, Hall))],
        cls="Hang", budget=BUDGETS[name],
        data={"footprint_mm": [W, D, Hall], "hang": _hang_data(D, (0.0, 0.0, apex)),
              "stack": {"socket": "Stack", "pitch_mm": Hall, "max": 4},
              "print_layout": lay, "print_art": art,
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (%d))" % (3 if tl else 4),
              "notes": [f"Sheet 12: a clear pillow bag {W:g} x {D:g} x {H:g} (flat welded seals, full depth between) "
                        f"holding {what}, under a folded header card {hh:g} tall (spec E {30 if tl else 25}; the "
                        f"picture wins), two-tone, with a euro slot cut through."]
              + ([] if tl else ["The header's perforated tear line (sheet 12) is a 1 mm detail on clear film: not "
                                "modelled."])},
    )


# =========================================================================== B8: dice clamshell

def item_dice_clam() -> Item:
    p = DICE_CLAM
    W, D, H = p["w"], p["d"], p["h"]
    yb = D / 2
    st = p["sheet_t"]
    yf_sheet = yb - st                                    # the flange's front face
    inset_, proud, bottom = p["plateau"]
    pz0, pz1 = bottom, H - p["tab"]
    pw = W - 2 * inset_
    ci, ct, cr = p["card"]
    cw, cz0, cz1 = pw - 2 * ci, pz0 + 1.5, pz1 - 1.5
    y_card1 = yf_sheet - 0.05
    y_card0 = y_card1 - ct
    bw, bh, bcz, br, bch = p["bubble"]
    die = p["die"]
    y_die1 = y_card0 + 0.3                                # the dice sink 0.3 into the card (their backs hidden)
    y_die0 = y_die1 - die
    sheet = Sheet()
    g = 4.0
    ch = cz1 - cz0
    rcf = sheet.planar("card_front", (-cw / 2, y_card0, cz0), (1, 0, 0), (0, 0, 1), cw, ch, 0.0, 0.0)
    rcb = sheet.planar("card_back", (cw / 2, y_card1, cz0), (-1, 0, 0), (0, 0, 1), cw, ch, cw + g, 0.0)
    xs = (-p["cols"] / 2, p["cols"] / 2)
    rows = p["rows"]
    dice = [(x, rows[r]) for r in range(3) for x in xs] + [(0.0, rows[3])]
    face_regions = []
    u = 2 * (cw + g)
    for i, (dx, dz) in enumerate(dice):
        x0, x1, z0, z1 = dx - die / 2, dx + die / 2, dz - die / 2, dz + die / 2
        fr = {}
        v = 0.0
        # front, top, bottom, left, right: each its own 16 x 16 cell in a column per die
        fr["ny"] = sheet.planar(f"die{i + 1}_front", (x0, y_die0, z0), (1, 0, 0), (0, 0, 1), die, die, u, v)
        v += die + g
        fr["pz"] = sheet.planar(f"die{i + 1}_top", (x0, y_die0, z1), (1, 0, 0), (0, 1, 0), die, die, u, v)
        v += die + g
        fr["nz"] = sheet.planar(f"die{i + 1}_bottom", (x0, y_die1, z0), (1, 0, 0), (0, -1, 0), die, die, u, v)
        v += die + g
        fr["nx"] = sheet.planar(f"die{i + 1}_left", (x0, y_die1, z0), (0, -1, 0), (0, 0, 1), die, die, u, v)
        v += die + g
        fr["px"] = sheet.planar(f"die{i + 1}_right", (x1, y_die0, z0), (0, 1, 0), (0, 0, 1), die, die, u, v)
        face_regions.append(fr)
        u += die + g
    lods = []
    apex = 0.0
    L, Hs, pr, below = p["slot"]
    cz = H - below
    apex = _slot_apex(cz, Hs, pr)
    cL, cHs, cpr, cbelow = p["card_slot"]
    for k in range(3):
        b = Builder()
        segs = (2, 0, 0)[k]
        rr = lambda w_, h_, r_, cz_: _rrect_xz(w_, h_, r_, segs, 0.0, cz_) if segs else rect(w_, h_, 0.0, cz_)
        # the clear clam: back sheet + flange (with the euro slot), the card compartment plateau, the dice bubble
        holes = [] if k == 2 else [_euro_slot(0.0, cz, L, Hs, pr, (3, 1)[k], (4, 2)[k])]
        _slab_y(b, rr(W, H, p["r"], H / 2), holes, yf_sheet, yb, FILM)
        if k < 2:
            _prism_xz(b, rr(pw, pz1 - pz0, p["r"], (pz0 + pz1) / 2), yf_sheet - proud, yf_sheet + 0.1, FILM, back=None)
        bub = rr(bw, bh, br, bcz)
        ybf = -D / 2
        if k == 0:                                         # drafted-free walls and a 2 mm chamfer round the front
            bub_in = rr(bw - 2 * bch, bh - 2 * bch, max(br - bch, 0.5), bcz)
            pa, pc = _ccw(bub), _ccw(bub_in)
            la = _loop_xz(b, pa, yf_sheet - proud + 0.1)
            lb = _loop_xz(b, pa, ybf + bch)
            lc = _loop_xz(b, pc, ybf)
            _walls_xz(b, pa, lb, la, False, FILM)
            n = len(pa)
            for i in range(n):
                j = (i + 1) % n
                mx, mz = (pa[i][0] + pa[j][0]) / 2, (pa[i][1] + pa[j][1]) / 2
                _face_out(b, [lb[i], lb[j], lc[j], lc[i]], (mx, -2.0 * max(bw, bh) / 50, mz - bcz), FILM)
            b.fill([lc], FILM, 0, (0, -1, 0))
        else:
            _prism_xz(b, bub, ybf, yf_sheet - proud + 0.1, FILM, back=None)
        # the insert card (print), with its own euro slot
        c_holes = [] if k == 2 else [_euro_slot(0.0, cz1 - cbelow, cL, cHs, cpr, (3, 1)[k], (4, 2)[k])]
        _slab_y(b, rr(cw, ch, cr, (cz0 + cz1) / 2), c_holes, y_card0, y_card1, PRINT, front=rcf, back=rcb)
        # the dice: open cubes (the backs sink into the card), each visible face a print cell; the far LOD keeps
        # the fronts only
        for (dx, dz), fr in zip(dice, face_regions):
            lo_, hi_ = (dx - die / 2, y_die0, dz - die / 2), (dx + die / 2, y_die1, dz + die / 2)
            if k < 2:
                b.box(lo_, hi_, mat=PRINT, regions=fr, skip=("py",))
            else:
                q = [b.v(lo_[0], y_die0, lo_[2]), b.v(hi_[0], y_die0, lo_[2]), b.v(hi_[0], y_die0, hi_[2]),
                     b.v(lo_[0], y_die0, hi_[2])]
                _face_out(b, q, (0, -1, 0), PRINT, fr["ny"])
        lods.append(Lod(b))
    name = "SM_CSK_Retail_DiceClam"
    lay = sheet.layout()
    split = p["split"] - cz0
    art = _two_tone(lay, ["card_front", "card_back"], {"card_front": split, "card_back": split}, p["colours"])
    art += [[*lay["panels"][n], p["die_colour"]] for n in lay["panels"] if n.startswith("die")]
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Film"], projections=sheet.projections(),
        sockets=_upright_sockets(W, D, H, H, (0.0, yb - st / 2, apex)),
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))], cls="Hang", budget=BUDGETS[name],
        data={"footprint_mm": [W, D, H], "hang": _hang_data(D, (0.0, yb - st / 2, apex)),
              "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "print_layout": lay, "print_art": art,
              "dice": {"count": 7, "size_mm": die, "layout": "2 x 3 + 1 centred below (sheet 12)",
                       "pips": "baked detail: each die's front, top, bottom, left and right faces are print cells "
                               "(die<N>_<face> panels); the pip faces are the art's choice"},
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (5))",
              "notes": ["Sheet 12: a clear clamshell (flat clear tab with a euro slot, a raised card compartment, a "
                        "dice bubble with a chamfered front), a dark-green / lime insert card with its own euro slot, "
                        "7 blue d6 (M 16) as 2 x 3 + 1.",
                        "The picture is drawn 176 tall at its 60 width; the spec's 130 (incl. the tab) wins, so the "
                        "rows are compressed (pitch 20 / 20 / 22 against the picture's 21 / 21 / 27) and the insert's "
                        "slot sits 4.8 above the bubble (picture ~12)."]},
    )


# =========================================================================== B8: binder in shrink film

def _binder_outline(W: float, D: float, rs: float, rf: float, segs_s: int, segs_f: int, off: float = 0.0):
    """Plan outline (XY, CCW) of the closed binder: spine at -X with round corners R rs, fore-edge corners R rf."""
    x0, x1, y0, y1 = -W / 2 - off, W / 2 + off, -D / 2 - off, D / 2 + off
    rs, rf = rs + off, rf + off
    pts = []
    for (cx, cy, a0, r, n) in ((x1 - rf, y0 + rf, -90.0, rf, segs_f), (x1 - rf, y1 - rf, 0.0, rf, segs_f),
                               (x0 + rs, y1 - rs, 90.0, rs, segs_s), (x0 + rs, y0 + rs, 180.0, rs, segs_s)):
        pts += [(cx + r * math.cos(math.radians(a0 + 90.0 * k / n)), cy + r * math.sin(math.radians(a0 + 90.0 * k / n)))
                for k in range(n + 1)]
    return pts


def _inset_outline(pts, d: float):
    """Offset a convex CCW outline inward by d (vertex normals from the neighbouring edges)."""
    n = len(pts)
    out = []
    for i in range(n):
        a, c, e = pts[i - 1], pts[i], pts[(i + 1) % n]
        n1 = (c[1] - a[1], -(c[0] - a[0]))
        n2 = (e[1] - c[1], -(e[0] - c[0]))
        l1, l2 = math.hypot(*n1) or 1.0, math.hypot(*n2) or 1.0
        nx, ny = n1[0] / l1 + n2[0] / l2, n1[1] / l1 + n2[1] / l2
        ln = math.hypot(nx, ny) or 1.0
        cosh = max(0.3, (nx * n1[0] / l1 + ny * n1[1] / l1) / ln)
        out.append((c[0] - nx / ln * d / cosh, c[1] - ny / ln * d / cosh))
    return out


def item_binder_wrapped() -> Item:
    p = BINDER
    f = p["film"]
    W, D, H = p["w"] - 2 * f, p["d"] - 2 * f, p["h"] - 2 * f
    rim = p["rim"]
    sheet = Sheet()
    g = 4.0
    # book-cover dieline: back | spine | front (the front cover faces the customer, -Y; the spine at -X)
    rb = sheet.planar("back", (W / 2, D / 2, f), (-1, 0, 0), (0, 0, 1), W, H, 0.0, 0.0)
    rs = sheet.planar("spine", (-W / 2, D / 2, f), (0, -1, 0), (0, 0, 1), D, H, W + g, 0.0)
    rfr = sheet.planar("front", (-W / 2, -D / 2, f), (1, 0, 0), (0, 0, 1), W, H, W + D + 2 * g, 0.0)
    rtop = sheet.planar("top", (-W / 2, -D / 2, f + H), (1, 0, 0), (0, 1, 0), W, D, 0.0, H + g)
    rbot = sheet.planar("bottom", (-W / 2, D / 2, f), (1, 0, 0), (0, -1, 0), W, D, W + g, H + g)
    BASE = 2
    lods = []
    for k in range(3):
        segs_s, segs_f = (3, 1, 1)[k], (2, 1, 1)[k]
        O = _binder_outline(W, D, p["spine_r"], p["fore_r"], segs_s, segs_f)

        def side_region(i, O=O):
            j = (i + 1) % len(O)
            mx, my = (O[i][0] + O[j][0]) / 2, (O[i][1] + O[j][1]) / 2
            if mx < -W / 2 + p["spine_r"] + 1e-6:
                return rs
            if my < 0 and abs(my + D / 2) < p["spine_r"]:
                return rfr
            if my > 0 and abs(my - D / 2) < p["spine_r"]:
                return rb
            return 0
        b = Builder()
        if k == 0:
            Oi = _inset_outline(O, rim)
            zs = [(Oi, f), (O, f + rim), (O, f + H - rim), (Oi, f + H)]
        else:
            Oi = O
            zs = [(O, f), (O, f + H)]
        loops = [b.loop(o, z) for o, z in zs]
        for li, (la, lc) in enumerate(zip(loops[:-1], loops[1:])):
            oa = zs[li][0]
            up = 0.0 if len(zs) == 2 or li == 1 else (-1.0 if li == 0 else 1.0)

            def out(i, oa=oa, up=up):
                j = (i + 1) % len(oa)
                return (oa[j][1] - oa[i][1], -(oa[j][0] - oa[i][0]), up * math.hypot(oa[j][0] - oa[i][0], oa[j][1] - oa[i][1]))
            _stitch(b, la, lc, out, PRINT, side_region)
        b.fill([loops[0]], PRINT, rbot, (0, 0, -1))
        b.fill([loops[-1]], PRINT, rtop, (0, 0, 1))
        ops = []
        if k < 2:
            # the covers and spine stand proud of the page block at the top (sheet 12 side view: an inset
            # rectangle): a pocket inside the flat top face, clear of the rims (so no cut crosses a chamfer)
            rc, bd = p["recess"], p["board"]
            c = Builder()
            c.box((-W / 2 + p["spine_r"] + 2.0, -D / 2 + bd, f + H - rc), (W / 2 - rim - 1.0, D / 2 - bd, f + H + 5.0),
                  mat=BASE)
            ops.append(("DIFFERENCE", c))
        # the shrink film: a clear shell 0.4 out, soft rims
        film = Builder()
        Of = _binder_outline(W, D, p["spine_r"], p["fore_r"], segs_s, segs_f, off=f)
        if k == 0:
            Ofi = _inset_outline(Of, 1.5)
            fz = [(Ofi, 0.0), (Of, 1.5), (Of, H + 2 * f - 1.5), (Ofi, H + 2 * f)]
        else:
            fz = [(Of, 0.0), (Of, H + 2 * f)]
        fl = [film.loop(o, z) for o, z in fz]
        for li, (la, lc) in enumerate(zip(fl[:-1], fl[1:])):
            oa = fz[li][0]
            up = 0.0 if len(fz) == 2 or li == 1 else (-1.0 if li == 0 else 1.0)

            def outf(i, oa=oa, up=up):
                j = (i + 1) % len(oa)
                return (oa[j][1] - oa[i][1], -(oa[j][0] - oa[i][0]), up * math.hypot(oa[j][0] - oa[i][0], oa[j][1] - oa[i][1]))
            _stitch(film, la, lc, outf, FILM)
        film.fill([fl[0]], FILM, 0, (0, 0, -1))
        film.fill([fl[-1]], FILM, 0, (0, 0, 1))
        lods.append(Lod(b, ops=ops, extra=film if k < 2 else None))
    name = "SM_CSK_Retail_BinderWrapped"
    Wo, Do, Ho = p["w"], p["d"], p["h"]
    lay = sheet.layout()
    sp = p["split"] - f
    art = _two_tone(lay, ["back", "spine", "front"], {"back": sp, "spine": sp, "front": sp}, p["colours"]) + \
        _two_tone(lay, ["top"], {}, p["colours"]) + _two_tone(lay, ["bottom"], {}, p["colours"][::-1])
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Film", "M_CSK_Base"],
        projections=sheet.projections(),
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Stack", (0, 0, Ho)), Socket("Face", (0, -Do / 2, Ho / 2), (90.0, 0.0, 0.0)),
                 Socket("Grip", (0, -Do / 2, Ho / 2))],
        hulls=[((-Wo / 2, -Do / 2, 0.0), (Wo / 2, Do / 2, Ho))], cls="Binder", budget=BUDGETS[name],
        data={"footprint_mm": [Wo, Do, Ho], "stack": {"socket": "Stack", "pitch_mm": Ho, "max": 4},
              "pose": "standing, the front cover toward the customer (-Y), the spine at -X",
              "print_layout": lay, "print_art": art,
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (6))",
              "notes": ["Sheet 12: a padded binder (round spine edges, chamfered rims, the covers and spine 3 proud "
                        "of the page block at the top), purple two-tone (the light band is the bottom "
                        "97), in a clear shrink-film shell 0.4 out with soft rims. The crinkles and the stitched edges "
                        "are texture / normal detail.",
                        "The prompt's sticker is not in the picture: none is built (REFERENCE_LOG sheet 12)."]},
    )


# =========================================================================== B8: lathe items (tube, bottle)

def _ring_xy(r: float, sides: int, z: float, b: Builder, phase: float = 0.0) -> List[int]:
    return [b.v(r * math.sin(phase + 2 * math.pi * i / sides), r * math.cos(phase + 2 * math.pi * i / sides), z)
            for i in range(sides)]


def _lathe(b: Builder, prof: Sequence[Tuple[float, float]], sides: int, mat, region=0, cap0: bool = False,
           cap1: bool = False, inward: bool = False) -> List[List[int]]:
    """Revolve a (r, z) profile about Z, listed with the material on its left (up the outside, inward across a top,
    outward across an underside). ``mat`` / ``region`` may be functions of the band index (region also of the column);
    column 0 starts at +Y (the back seam). ``inward`` flips every face."""
    rings = [_ring_xy(r, sides, z, b) for r, z in prof]
    for k, (ra, rc) in enumerate(zip(rings[:-1], rings[1:])):
        (r0, z0), (r1, z1) = prof[k], prof[k + 1]
        m = mat(k) if callable(mat) else mat
        for i in range(sides):
            j = (i + 1) % sides
            a = 2 * math.pi * (i + 0.5) / sides
            nr = (z1 - z0)
            nz = -(r1 - r0)
            d = (math.sin(a) * nr, math.cos(a) * nr, nz)
            if inward:
                d = tuple(-x for x in d)
            reg = region(k, i) if callable(region) else region
            _face_out(b, [ra[i], ra[j], rc[j], rc[i]], d, m, reg)
    if cap0:
        b.fill([rings[0]], mat(0) if callable(mat) else mat, 0, (0, 0, -1))
    if cap1:
        b.fill([rings[-1]], mat(len(prof) - 2) if callable(mat) else mat, 0, (0, 0, 1))
    return rings


def _wrap_panels(sheet: Sheet, r: float, z0: float, z1: float, sides: int, u0: float, v0: float) -> Tuple[int, int]:
    """A label wrapped round a cylinder: two regions (faces on either side of the back seam at +Y) sharing one panel,
    u = arc length from the seam, so no face straddles the seam."""
    C = 2 * math.pi * r

    def ang(x, y, back_half):
        a = math.atan2(x, y) % (2 * math.pi)          # 0 at +Y (the seam), pi at -Y (the front)
        if back_half and a < 1e-6:
            a = 2 * math.pi
        return a

    ra = sheet.add("label_a", lambda x, y, z: (ang(x, y, False) * r, z - z0), C, z1 - z0, u0, v0)
    rb = sheet.add("label_b", lambda x, y, z: (ang(x, y, True) * r, z - z0), C, z1 - z0, u0, v0)
    return ra, rb


def item_playmat_tube() -> Item:
    p = TUBE
    rc, H, cap, ch = p["r_cap"], p["h"], p["cap"], p["cap_chamfer"]
    rt = p["r_tube"]
    lz0, llen, lsplit = p["label"]
    lz1 = lz0 + llen
    rr, rlen = p["roll"]
    sheet = Sheet()
    CAP, RUB = 2, 3
    lods = []
    for k in range(3):
        n = (p["sides"], 8, 6)[k]
        sh = Sheet()
        reg_a, reg_b = _wrap_panels(sh, rt, lz0, lz1, n, 0.0, 0.0)
        if k == 0:
            sheet = sh
        b = Builder()
        # caps: cups over the tube ends (sheet 12: black, softly rounded rims); far LODs drop the rim chamfer and
        # the cup's lip
        for bottom in (True, False):
            # the bottom cap's profile with the material on its left (the _lathe convention): the base chamfer, the
            # side, then the lip inward; the top cap is its mirror
            if k == 0:
                prof = [(rc - ch, 0.0), (rc, ch), (rc, cap), (rt, cap)]
            elif k == 1:
                prof = [(rc, 0.0), (rc, cap), (rt, cap)]
            else:
                prof = [(rc, 0.0), (rc, cap)]
            if not bottom:
                prof = [(r, H - z) for r, z in reversed(prof)]
            rings = _lathe(b, prof, n, CAP)
            end = rings[0] if bottom else rings[-1]
            b.fill([end], CAP, 0, (0, 0, -1) if bottom else (0, 0, 1))
            if k == 2:                                   # the far LOD's plain cylinder: close its inner end too
                inner = rings[-1] if bottom else rings[0]
                b.fill([inner], CAP, 0, (0, 0, 1) if bottom else (0, 0, -1))
        # the clear tube (label print from the bottom cap up, film above); ends sunk 0.5 into the caps
        seam = lambda kk, i, n=n: (reg_a if (i + 0.5) / n < 0.5 else reg_b) if kk == 0 else 0
        _lathe(b, [(rt, cap - 0.5), (rt, lz1), (rt, H - cap + 0.5)], n, lambda kk: PRINT if kk == 0 else FILM, seam)
        # the rolled playmat inside (E5 Rolled, D Ø 45 x 356), its ends hidden in the caps
        if k < 2:
            z0 = (H - rlen) / 2
            _lathe(b, [(rr, z0), (rr, z0 + rlen)], n, RUB)
        lods.append(Lod(b))
    name = "SM_CSK_Retail_PlaymatTube"
    lay = sheet.layout()
    art = [[*lay["panels"]["label_a"][:3], lsplit, p["colours"][1]],
           [lay["panels"]["label_a"][0], lsplit, lay["panels"]["label_a"][2], llen - lsplit, p["colours"][0]]]
    projs = sheet.projections()
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Film", "M_CSK_Base", "M_CSK_Rubber"],
        projections=projs,
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Stack", (0, 0, H)), Socket("Face", (0, -rc, H / 2), (90.0, 0.0, 0.0)),
                 Socket("Grip", (0, -rc, H / 2))],
        hulls=[((-rc, -rc, 0.0), (rc, rc, H))], cls="Retail", budget=BUDGETS[name],
        data={"footprint_mm": [2 * rc, 2 * rc, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "pose": "standing on a cap", "print_layout": lay, "print_art": art,
              "label": {"panel": "label_a + label_b share one wrap panel; u = arc length from the back seam (+Y)"},
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (7))",
              "notes": ["Sheet 12: a clear tube with black cup caps (40 tall, softly rounded rims), a two-tone green "
                        "label wrap (lime 98 under dark green 121) from the bottom cap up, the rolled mat inside.",
                        "The roll is E5 Rolled Ø 45 x 356 (D from the flat mat); the picture draws it fuller (~Ø 58).",
                        "The small dot on the cap top (sheet 12, second tube) is not modelled."]},
    )


def item_cleaner_bottle() -> Item:
    p = BOTTLE
    lz0, lz1, lsplit = p["label"]
    rco, zc0, zc1, rstem = p["collar"]
    rh, zh0, zh1 = p["head"]
    rcap, zp0, zp1 = p["cap"]
    PLAST = 2
    lods = []
    sheet = Sheet()
    for k in range(3):
        n = (p["sides"], 8, 6)[k]
        sh = Sheet()
        r_label = p["body"][2][0]
        ra, rb = _wrap_panels(sh, r_label, lz0, lz1, n, 0.0, 0.0)
        if k == 0:
            sheet = sh
        b = Builder()
        neck = p["body"][-1]
        prof = [list(p["body"]),
                [(19.0, 0.0), (20.0, lz0), (20.0, lz1), (17.0, 92.0), neck],
                [(20.0, 0.0), (20.0, lz0), (20.0, lz1), neck]][k]
        li = [i for i, (r, z) in enumerate(prof) if abs(z - lz0) < 1e-6][0]
        mat = lambda kk, li=li: PRINT if kk == li else FILM
        reg = lambda kk, i, li=li, n=n, ra=ra, rb=rb: (ra if (i + 0.5) / n < 0.5 else rb) if kk == li else 0
        _lathe(b, prof, n, mat, reg, cap0=True)
        # the white pump: the ribbed collar (ribs are normal detail) and the head, under the clear overcap
        _lathe(b, [(neck[0] - 0.5, zc0), (rco, zc0), (rco, zc1), (rstem, zc1)] if k < 2 else
               [(neck[0] - 0.5, zc0), (rco, zc0), (rco, zc1), (rcap - 0.5, zc1)], n, PLAST)
        if k < 2:
            _lathe(b, [(rh, zh0 - 0.5), (rh, zh1)], n, PLAST, cap1=True)
        _lathe(b, [(rcap, zp0 - 0.5), (rcap, zp1)], n, FILM, cap1=True)
        lods.append(Lod(b))
    name = "SM_CSK_Retail_CleanerBottle"
    lay = sheet.layout()
    u0, v0, w, h = lay["panels"]["label_a"]
    art = [[u0, v0, w, lsplit, p["colours"][1]], [u0, v0 + lsplit, w, h - lsplit, p["colours"][0]]]
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Film", "M_CSK_PlasticWhite"],
        projections=sheet.projections(),
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Stack", (0, 0, zp1)), Socket("Face", (0, -20.0, 46.0), (90.0, 0.0, 0.0)),
                 Socket("Grip", (0, -20.0, 46.0))],
        hulls=[((-20.0, -20.0, 0.0), (20.0, 20.0, zp1))], cls="Retail", budget=BUDGETS[name],
        data={"footprint_mm": [40.0, 40.0, zp1], "stack": {"socket": "Stack", "pitch_mm": zp1, "max": 4},
              "print_layout": lay, "print_art": art,
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (9))",
              "notes": ["Sheet 12: a clear PET bottle (round base, shoulder to a neck), a white ribbed collar and pump "
                        "head under a clear overcap, a two-tone red label (light band the bottom 30.7) from 7.3 to "
                        "85.8. M_CSK_PlasticWhite is the white pump.",
                        "Not modelled: the collar's ribs (normal detail), the nozzle hole, the dip tube."]},
    )


# =========================================================================== B8: deck box in a window box

def item_deck_box_pack() -> Item:
    p = DECK_PACK
    W, D, H = p["w"], p["d"], p["h"]
    ww, wh, wcz, wr = p["window"]
    dbw, dbd, dbh = p["deckbox"]
    y_db = -dbd / 2                                       # the deck box's front face (centred in the carton)
    fz, fp = p["flap"]
    BOARD, PLAST = 1, 2
    sh = Sheet()
    g = 4.0
    reg = _box_panels(sh, W, D, H, gap=g)
    v_top = sh.layout()["panels"]["top"][1] + D + g
    rf, rb = _tab_panels(sh, W, D, H, p, g, v_top)
    lods = []
    apex = 0.0
    for k in range(3):
        b = Builder()
        b.box((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H), mat=PRINT, regions=reg)
        cut = Builder()
        segs = (4, 2, 0)[k]
        win = _rrect_xz(ww, wh, wr, segs, 0.0, wcz) if segs else rect(ww, wh, 0.0, wcz)
        # the die-cut window: its walls are the board edge and the carton's inside, its floor the deck box front
        _prism_xz(cut, win, -D / 2 - 1.0, y_db, BOARD, front=0, back=0)
        cut.fills[-1].mat = PLAST
        extra = Builder()
        apex = _tab(extra, W, D, H, p, k, PRINT, rf, rb)
        # the deck box's flap lid (sheet 12): 0.8 proud, its bottom edge across the window, hidden above it
        extra.box((-ww / 2 - 3.0, y_db - fp, fz), (ww / 2 + 3.0, y_db + 0.1, wcz + wh / 2 + 3.0), mat=PLAST)
        lods.append(Lod(b, bevel_mm=p["bevel"] if k == 0 else None, bevel_first=True, ops=[("DIFFERENCE", cut)],
                        extra=extra))
    name = "SM_CSK_Retail_DeckBoxPack"
    lay = sh.layout()
    Hall = H + p["tab"]
    y_tab = D / 2 - 0.05 - p["tab_t"] / 2
    split = p["split"]
    art = _two_tone(lay, ["front", "right", "back", "left"], {k: split for k in ("front", "right", "back", "left")},
                    p["colours"]) + _two_tone(lay, ["top", "tab_front", "tab_back"], {}, p["colours"]) + \
        _two_tone(lay, ["bottom"], {}, p["colours"][::-1])
    return Item(
        name=name, lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Board", "M_CSK_Plastic"],
        projections=sh.projections(),
        sockets=_upright_sockets(W, D, H, Hall, (0.0, y_tab, apex)),
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H)), ((-W / 2, D / 2 - 2.0, H), (W / 2, D / 2, Hall))],
        cls="Deck", budget=BUDGETS[name],
        data={"footprint_mm": [W, D, Hall], "hang": _hang_data(D, (0.0, y_tab, apex)),
              "stack": {"socket": "Stack", "pitch_mm": Hall, "max": 4},
              "print_layout": lay, "print_art": art,
              "reference": "References/CardShop/csk_blister_retail.png (sheet 12 (8))",
              "notes": ["Sheet 12: a navy / light-blue carton (the light band is the bottom 38) with a hang tab and a "
                        "rounded die-cut window 59.3 x 86.5 R 4.3 showing the deck box (E4 76 x 80 x 108, centred, "
                        "3 behind the front board) with its flap lid 0.8 proud.",
                        "The picture draws the deck box as wide as the window with the flap's rounded corners inside "
                        "it; E4's 76 width wins, so the flap edge crosses the window straight.",
                        "The hang tab is in the picture but not the spec: built, with a Hang socket; the class stays "
                        "Deck, whose footprint (H 116) does not count the 25 tab."]},
    )


# =========================================================================== registry

ITEMS = {
    "c_retail_card_small": item_card_small,
    "c_retail_stack_10": lambda: item_card_stack(10.0),
    "c_retail_stack_30": lambda: item_card_stack(30.0),
    "c_retail_stack_90": lambda: item_card_stack(90.0),
    "c_retail_sleeve_penny": item_sleeve_penny,
    "c_retail_sleeve_deck_std": lambda: item_sleeve_deck("Std"),
    "c_retail_sleeve_deck_small": lambda: item_sleeve_deck("Small"),
    "c_retail_toploader_filled": item_toploader_filled,
    "c_retail_semirigid": item_holder_semirigid,
    "c_retail_magnetic": lambda: _mag_item("closed"),
    "c_retail_magnetic_front": lambda: _mag_item("front"),
    "c_retail_magnetic_back": lambda: _mag_item("back"),
    "c_retail_magnetic_filled": lambda: _mag_item("filled"),
    "c_retail_sleevebox": item_sleeve_box,
    "c_retail_tlpack": lambda: _bag_item("tl"),
    "c_retail_pennypack": lambda: _bag_item("penny"),
    "c_retail_diceclam": item_dice_clam,
    "c_retail_binder": item_binder_wrapped,
    "c_retail_tube": item_playmat_tube,
    "c_retail_deckboxpack": item_deck_box_pack,
    "c_retail_bottle": item_cleaner_bottle,
}
