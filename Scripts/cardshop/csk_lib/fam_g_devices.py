"""Card Shop Kit family g_devices: the counter's POS devices and money (CARDSHOP_KIT_SPEC.md 3.G rows G2-G10; P3-P5).

    G2  steel cash drawer + its sliding tray (5 note slots with clips, 8 coin cups)   reference sheet 26 panel 1
    G3  countertop card terminal (wedge, keypad, screen, card slot)                    sheet 26 panel 2
    G4  clamshell receipt printer + its lid (the lid is added as a hinged part)        sheet 26 panel 3
    G5  POS screen on a stand                                                          sheet 26 panel 4
    G6  handheld scanner + its cradle                                                  sheet 26 panel 5
    G7  pistol-grip price labeller                                                     sheet 26 panel 6
    G8  plain note stack + coin (no currency design)                                   sheet 26 panel 1 (the notes and
                                                                                       coins in the drawer)
    G9  smartphone                                                                     sheet 26 panel 7
    G10 laptop + its lid                                                               sheet 26 panel 8

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = a
spec estimate with a source range. "sheet 26" = the value or form is read off References/CardShop/csk_pos_devices.png
(the picture wins over E numbers; M numbers win over the picture). Millimetres; Seat frame: +X right, +Y away from
the customer, +Z up. Every device's front faces -Y in its own frame (the kit rule), except the cash drawer: the spec
row slides its tray toward the staff (+Y), so the drawer's front (the lock face) is at +Y, as the counter's `Drawer`
socket expects. The spec's "W x D x H" sizes of the long handheld devices are read as sizes, not axes: the long axis
of the terminal, scanner and labeller runs along Y (front = -Y), as sheet 26 draws them.

Directional sockets (Beam, PaperOut, LabelOut, CardSlot, Screen, Tap) point their local +Z out of the device, the
G1 pack's `CardsOut` convention.

Every shape is our own generic design (spec 3.G "original design"); no product silhouettes, no marks, no currency art.
No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import R_BACK, R_FRONT, Item, Lod, Socket, _face_out, _planar, inset
from .shapes import Builder, rect, rounded_rect

Vec3 = Tuple[float, float, float]
REF = "References/CardShop/csk_pos_devices.png (sheet 26)"

# =========================================================================== numbers

DRAWER = dict(                 # G2 cash drawer, sheet 26 panel 1
    w=409.0, d=417.0, h=112.0,  # M [D35]
    frame=(7.0, 8.0, 6.0),     # sheet 26: the housing's front frame round the tray opening: sides, top, bottom (E)
    back=6.0,                  # E: the housing's back wall
    r=2.5,                     # sheet 26: softly rounded housing edges (E radius, 2 segments)
    panel=(395.0, 96.0, 16.0),  # sheet 26: the tray's front panel W x H x T, flush with the housing front (E)
    bin=(380.0, 84.0),         # sheet 26: the tray bin W x H behind the panel; the insert's top sits ~10 under
                               # the panel's top edge (E)
    bin_back=-200.0,           # E: the bin's back face (y); the tray is 408.5 long
    wall=2.0,                  # E: bin / insert outer wall
    div=3.0,                   # E: insert dividers
    note_len=166.0,            # sheet 26: the note slots take ~45 % of the tray depth, at the back
    pocket_d=32.0,             # sheet 26: the coins and notes sit ~30 under the insert's top (E)
    notes=5, coin_cols=4, coin_rows=2,   # counts 5 / 8 E* (spec, sheet 26 call-out "5 note slots, 8 coin cups")
    lock=(22.0, 3.5, 55.5),    # sheet 26: round chrome lock, centred on the front: diameter, proud, z (E)
    travel=385.0,              # sheet 26 (wins over the spec's 280 E): the tray is drawn out until the clip barrels
                               # sit under the housing's front edge, every slot in view (a full-extension slide)
    clip=(9.0, 1.5, 3.5),      # sheet 26: a wire U clip per note slot: half spacing of the wires, wire r, barrel r (E)
)

TERMINAL = dict(               # G3 countertop card terminal, sheet 26 panel 2 (front = -Y: card slot, keys)
    w=81.0, l=168.0, h=56.0,   # E* (spec [D36])
    # side profile (y, z), counter-clockwise seen from +X (sheet 26: a wedge, low at the keypad end, the screen on
    # the steeper rear deck, a vertical back, and an undercut under the rear with a foot at the back): E values
    front_h=22.0, deck_break=(4.0, 40.0), rear_top=(66.0, 56.0), back_top=50.0,
    undercut=(24.0, 34.0, 60.0, 68.0, 12.0),   # y where the arch leaves the counter, reaches its top, leaves the
                                               # top, lands; arch height (E, sheet 26)
    bevel=5.0,                 # sheet 26: soft moulded edges (3 segments)
    screen=(56.0, 42.0, 1.6, 9.0),   # sheet 26: the colour screen W x H, recess depth, v start on the rear deck (E)
    key=(16.0, 8.0, 2.2, 0.8),       # E: numeric key W x H, proud, top inset (sheet 26: 3 columns, 4 rows)
    fkey=(17.0, 9.0),                # E: function key W x H (red / yellow / green, the front row)
    soft=(15.0, 6.0, 19.0),          # E: soft key W x H (the middle one is 19 wide), the row under the screen
    cols=21.0,                       # E: key column spacing (u)
    rows=(10.0, 23.0, 34.0, 45.0, 56.0, 68.0),   # E: key-row centres along the keypad deck (v from the front edge)
    slot=(62.0, 2.6, 26.0, 8.0),     # sheet 26: the card slot across the front face: W x H, depth, z centre (E)
)

PRINTER = dict(                # G4 clamshell receipt printer, sheet 26 panel 3 (front = -Y: the paper exit)
    w=152.0, d=179.0, h=118.0,  # sheet 26 call-outs: 152 across the front, 179 deep (the spec's 179 x 152 E read as
                                # W x D is swapped: the picture wins over E), H 118 E
    body_h=100.0,              # sheet 26: the body's top (the front ledge); the lid closes over it to 118 (E)
    r=4.0,                     # sheet 26: rounded body edges (E radius, 2 segments)
    seam=(80.0, 0.8, 0.6),     # sheet 26: the parting line round the body: z, height, depth (E)
    bay=(92.0, -44.0, 62.0, 38.0),   # E: the paper bay W, y front, y back, floor z (sheet 26: the roll sits in it)
    roll=(80.0, 38.0, 9.0),    # paper 80 wide M [D37]; roll radius 38 E (sheet 26: it stands ~14 over the body top);
                               # core radius E
    front_panel=(-56.0, 60.0, 4.0, 42.0, 2.0),   # sheet 26: the recessed panel low on the front: x0, x1, z0, z1, depth
    tear=(90.0, 7.0, 2.0),     # sheet 26: the tear bar at the paper exit W x D x proud (E)
    button=(12.0, 10.0, 2.0, -56.0, -75.0),      # sheet 26: the square feed key on the ledge: W x D x proud, x, y (E)
    hinge=(82.0, 110.0),       # E: the lid's hinge axis (y, z)
    lid_t=3.0, skirt=3.0,      # E: lid wall thicknesses
    lid_front=-45.0,           # E: the lid's front edge (over the bay's front, behind the tear bar)
    platen=(40.0, 6.0),        # sheet 26: the platen roller along the lid's front edge: half length, radius (E)
    boss=(8.0, 3.0, 2.5),      # sheet 26: the round hinge bosses: radius, proud, pin radius (E)
    open_deg=-105.0,           # sheet 26: the lid swung up and back, a little past vertical (E)
)

POS = dict(                    # G5 POS screen on a stand, sheet 26 panel 4 (front = -Y: the screen)
    disp=(360.0, 230.0, 26.0),  # E (spec): the display W x H; thickness E
    disp_r=10.0,               # sheet 26: rounded display corners (E radius)
    edge=(1.5, 6.0),           # E: the round on the front edge / on the back edge
    bezel=(12.0, 14.0, 16.0),  # sheet 26: thin black bezel: sides, top, bottom (E)
    recess=1.0,                # E: the screen sits 1 under the bezel
    tilt=12.0,                 # sheet 26: the display leans back (E, degrees)
    centre=(0.0, 175.0),       # E: the display centre (y, z): its lower edge ~62 over the counter (sheet 26)
    base=(200.0, 200.0, 14.0, 12.0),   # E (spec): base W x D; thickness and plan corner radius E
    base_edge=(4.0, 3.0),      # sheet 26: the base's rounded top edge and chamfered foot (E)
    neck=(96.0, 30.0, 2.0),    # sheet 26: the neck W x D (about half the base wide), y of its front face (E)
    cam=2.2,                   # sheet 26: the camera dot in the top bezel (E radius)
)

SCANNER = dict(                # G6 handheld scanner, sheet 26 panel 5 (front = -Y: the nose)
    w=70.0, l=160.0, h=95.0,   # E (spec); sheet 26 call-outs agree (70 across, 160 long, 95 high)
    head_rear=22.0,            # sheet 26: the head runs from the nose (y -80) back to y +22 (E)
    head_z=73.0,               # E: the head's centre height (top at 95)
    # head sections along the nose axis (from the rear): (distance, W, H, corner r); sheet 26: a rounded body that
    # flares into a wider nose bezel at the front (E values)
    head=((0.0, 32.0, 18.0, 8.0), (4.0, 48.0, 30.0, 12.0), (13.0, 56.0, 38.0, 14.0), (72.0, 58.0, 40.0, 14.0),
          (86.0, 70.0, 44.0, 15.0), (102.0, 70.0, 44.0, 15.0)),
    window=(58.0, 32.0, 11.0, 9.0),   # sheet 26: the recessed window in the nose: W x H, depth, corner r (E)
    grip=((0.0, 2.0, 60.0), (0.0, 46.0, 11.0)),   # sheet 26: the grip axis from under the head down-back to the
                                                   # foot (points, E)
    grip_sec=((8.0, 38.0, 48.0), (18.0, 33.0, 44.0), (34.0, 30.0, 42.0), (52.0, 29.0, 40.0), (64.0, 28.0, 40.0)),
                               # (z, W, D): horizontal sections centred on the raked axis, flaring into the foot;
                               # the lowest sits inside the foot, the highest inside the head
    foot=(64.0, 100.0, 12.0, 27.0, 30.0),   # sheet 26: the flat pill-shaped foot W x L x H, corner r, y centre (E)
    trigger=(13.0, (13.0, 24.0), (1.0, 14.0), 3.0),  # sheet 26: the blue-grey trigger just under the head, in front
                                                      # of the grip: W, v, w, top inset (E)
)

CRADLE = dict(                 # G6 cradle, sheet 26 panel 5 (sizes E, read against the scanner in the picture)
    base=(104.0, 94.0, 14.0),  # sheet 26: a plinth band at the foot: W x D, corner r (E)
    plinth_h=10.0, step=3.0,   # E
    top=(84.0, 58.0, 12.0),    # sheet 26: the body tapers to its top, most in depth: W x D, corner r (E)
    h=100.0,                   # sheet 26: about as tall as the scanner (E)
    dip=32.0,                  # sheet 26: the saddle dips deep between two ears at the sides (E)
    cup=(72.0, 46.0, 15.0, 45.0),   # E: the cup the scanner's nose drops into: W x D, corner r, floor z
    ear_r=7.0,                 # sheet 26: the ears' rounded top edge (E radius; real rings)
)

LABELLER = dict(               # G7 pistol-grip price labeller, sheet 26 panel 6 (front = -Y: the print head)
    w=45.0, l=190.0, h=125.0,  # E (spec); sheet 26 call-outs agree (45 across, 190 long, 125 high)
    # side profiles (y, z), counter-clockwise seen from +X; E values read off sheet 26 panel 6
    body=((-95.0, 0.0), (-10.0, 0.0), (20.0, 34.0), (34.0, 60.0), (34.0, 84.0), (20.0, 92.0), (-56.0, 72.0),
          (-56.0, 98.0), (-95.0, 98.0)),          # the main body: head block at the front, the roll bed behind
    plate=((-58.0, 58.0), (-14.0, 58.0), (30.0, 70.0), (33.5, 85.0), (27.0, 102.0), (13.0, 114.0), (-3.0, 118.0),
           (-18.0, 114.0), (-29.0, 104.0), (-44.0, 88.0), (-58.0, 88.0)),   # the round-topped roll cover plates
    plate_t=4.0,               # E: the cover plates' thickness (one each side)
    handle=((22.0, 74.0), (95.0, 90.0), (98.0, 97.0), (95.0, 104.0), (88.0, 107.0), (22.0, 97.0)),
    handle_w=28.0,             # sheet 26: the fixed upper handle, narrower than the body (E)
    lever=((12.0, 42.0), (70.0, 46.0), (78.0, 40.0), (82.0, 6.0), (86.0, 0.0), (93.0, 1.5), (95.0, 12.0),
           (90.0, 46.0), (82.0, 56.0), (12.0, 58.0)),   # sheet 26: the lower lever, its end hooked down to the counter
    lever_w=24.0,
    chamfer=1.5,               # E: the moulded edge chamfer of the plates, handle and lever
    bevel=2.0,                 # E: the body's rounded edges (2 segments)
    nose=(40.0, 4.0, 40.0, 98.0),   # sheet 26: the print-head frame proud of the front: W, proud, z0, z1 (E)
    window=(24.0, 5.0, 80.0, 95.0),  # sheet 26: the window at the head's top: W, depth, z0, z1 (E)
    slider=(16.0, 8.0, 3.5),   # sheet 26: the red selector in the window: W x H, proud of the window floor (E)
    exit=(28.0, 3.0, 45.5),    # E: the label exit slot: W x H, z centre
    strip=(23.0, 0.4, ((-97.0, 45.5), (-104.0, 42.0), (-110.0, 30.0), (-113.0, 14.0), (-112.0, 4.0),
                       (-106.0, 0.6))),   # sheet 26: the label strip hanging from the exit to the counter: W, T,
                                          # centre line (label 19.8 x 11.2 M [D38] on a backing strip, E)
    roll=(30.0, 26.0, (-28.0, 96.0)),  # sheet 26: the label roll radius, width, centre (y, z) (E); top at 126
    hub=(25.0, 3.0),           # sheet 26: the blue spool flange on the far (-X) side: radius, thickness (E)
    boss=(5.0, 0.6, (-2.0, 20.0)),   # sheet 26: the round screw boss low on each side: r, proud of the body, (y, z) (E)
)

PHONE = dict(                  # G9 smartphone, sheet 26 panel 7 (lies on its back, screen up, top = +Y)
    w=72.0, l=150.0, t=8.0,    # E (spec); sheet 26 call-outs agree
    r=9.0,                     # sheet 26: rounded plan corners (E radius)
    edge=(1.2, 1.6),           # E: the round on the glass edge / on the back edge
    bezel=(2.4, 2.6),          # sheet 26: a thin black bezel: sides, top / bottom (E)
    screen_r=7.0,              # E: the screen's own corner radius
    cam=(1.4, 6.0),            # sheet 26: the hole-punch camera: radius, centre below the screen's top edge (E)
    buttons=((41.5, 11.0), (12.5, 13.0)),   # sheet 26: the two keys on the right edge: y centre, length (E)
    button=(0.6, 2.0),         # E: how far they stand proud, their height (centred on the edge)
)

LAPTOP = dict(                 # G10 laptop + lid, sheet 26 panel 8 (hinge at +Y, keyboard front = -Y)
    w=320.0, d=220.0, h=16.0,  # E (spec, closed); sheet 26 call-outs agree
    base_t=9.0, lid_t=7.0,     # sheet 26: the lid reads a little thinner than the base (E split of the 16)
    r=10.0,                    # sheet 26: rounded plan corners (E radius)
    base_edge=(1.5, 2.5),      # E: the base's top / bottom edge rounds
    well=(284.0, 108.0, -26.0, 1.5, 3.0),   # sheet 26: the keyboard well W x D, front y, depth, corner r (E)
    pad=(110.0, 66.0, -100.0, 0.4),         # sheet 26: the touchpad W x D, front y, depth (E)
    notch=(60.0, 6.0, 2.0),    # sheet 26: the opening notch at the front edge's top centre: W, D, depth (E)
    ports=((-44.0, 9.0, 3.2), (-28.0, 13.0, 5.5), (-12.0, 4.0, 4.0)),   # sheet 26: 3 ports on the left side: y,
                                                                         # W, H (E); 6 deep
    key_gap=3.0, key_t=1.3, key_ins=0.6,    # E: keycap gap, height over the well floor, top inset
    fn_h=9.0,                  # E: the function row's key depth
    rows=((1.0,) * 13 + (2.0,),
          (1.5,) + (1.0,) * 12 + (1.5,),
          (1.75,) + (1.0,) * 11 + (2.25,),
          (2.25,) + (1.0,) * 10 + (2.75,),
          (1.0, 1.0, 1.0, 1.25, 5.5, 1.25, 1.0, 1.0, "UD", 1.0)),   # key widths in units (15 u a row); "UD" = the
                                                                     # up / down pair (half height)
    bezel=(8.0, 10.0, 14.0),   # sheet 26: thin black bezel: sides, top (the lid's free edge), bottom (hinge side) (E)
    cam=1.5,                   # sheet 26: the camera dot in the top bezel (E radius)
    open_deg=-110.0,           # sheet 26: the open pose (E)
    range_deg=(-130.0, 0.0),   # E (spec 0-130)
)

MONEY = dict(                  # G8 generic money, no currency design (spec 6)
    stack=(150.0, 70.0, 10.0),  # E (spec): the stack's render bounds
    note=(148.0, 68.0),        # E: one note; the stack's notes are offset by up to 1 mm (loose notes)
    layers=5,                  # E: 5 note bundles of 2 mm (the kit's stack look; each bundle a slab)
    coin=(24.0, 2.0),          # E (spec): diameter x thickness
    coin_edge=0.45,            # E: the coin's rounded rim (a chamfer ring each face)
)

BUDGETS = {                    # LOD0 triangle budgets: the spec's "Tris" column, raises logged
    "SM_CSK_CashDrawer": 800,
    "SM_CSK_CashDrawer_Tray": 700,      # spec 400: 13 real pockets + 5 wire clips on barrels + the lock (sheet 26)
    "SM_CSK_Terminal_Card": 800,
    "SM_CSK_Printer_Receipt": 450,      # spec 700 for the printer; split 450 body + 250 lid (the lid is added)
    "SM_CSK_Printer_Receipt_Lid": 250,
    "SM_CSK_POS_Screen": 800,
    "SM_CSK_Scanner": 600,
    "SM_CSK_Scanner_Cradle": 300,       # spec 200: the saddle and the cup are real cuts, the ears rounded (sheet 26)
    "SM_CSK_PriceGun": 1200,
    "SM_CSK_Phone": 300,
    "SM_CSK_Laptop": 1200,             # spec 500: sheet 26 draws a full keyboard; 78 real keycaps are 780 tris
    "SM_CSK_Laptop_Lid": 300,
    "SM_CSK_Bills_Stack": 100,
    "SM_CSK_Coin": 120,
}

# kit placement classes for the tray's contain test (spec 4.2 style: footprint W x D x H, pitch = + 10)
CLASSES = {
    "Bill": S.ItemClass("Bill", (150.0, 70.0, 10.0), (160.0, 80.0)),
    "Coin": S.ItemClass("Coin", (24.0, 24.0, 2.0), (34.0, 34.0)),
}


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
    a = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    e1 = _unit(_sub(a, _mul(d, _dot(a, d))))
    return e1, _cross(d, e1)


def _rx(p, deg):
    """Rotate the point ``p`` about the X axis by ``deg`` (right hand)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c)


class Frame:
    """A local frame: world = o + u U + v V + w W (U, V, W orthonormal, right-handed)."""

    def __init__(self, o: Vec3, U: Vec3, V: Vec3):
        self.o, self.U, self.V = o, _unit(U), _unit(V)
        self.W = _cross(self.U, self.V)

    def p(self, u, v, w) -> Vec3:
        return _add(self.o, _add(_mul(self.U, u), _add(_mul(self.V, v), _mul(self.W, w))))

    def d(self, u, v, w) -> Vec3:
        return _add(_mul(self.U, u), _add(_mul(self.V, v), _mul(self.W, w)))


def _merge(dst: Builder, src: Builder, pt: Callable[[Vec3], Vec3], dr: Callable[[Vec3], Vec3]) -> None:
    """Append ``src`` to ``dst`` with every vertex mapped by ``pt`` (a rigid motion; ``dr`` maps directions)."""
    base = len(dst.verts)
    for p in src.verts:
        dst.v(*pt(p))
    for f in src.faces:
        dst.face(tuple(i + base for i in f.verts), f.mat, f.region)
    for fl in src.fills:
        dst.fill([[i + base for i in lp] for lp in fl.loops], fl.mat, fl.region, dr(fl.normal))


def _merge_frame(dst: Builder, src: Builder, fr: Frame) -> None:
    _merge(dst, src, lambda p: fr.p(*p), lambda d: fr.d(*d))


def _merge_rx(dst: Builder, src: Builder, deg: float, off: Vec3 = (0.0, 0.0, 0.0)) -> None:
    _merge(dst, src, lambda p: _add(_rx(p, deg), off), lambda d: _rx(d, deg))


# =========================================================================== shape helpers

def _box(b: Builder, mn, mx, mat: int, **kw) -> None:
    lo = tuple(min(mn[i], mx[i]) for i in range(3))
    hi = tuple(max(mn[i], mx[i]) for i in range(3))
    b.box(lo, hi, mat=mat, **kw)


def _cyl_axis(b: Builder, c: Vec3, axis: Vec3, r: float, a0: float, a1: float, sides: int, mat: int,
              caps: Tuple[bool, bool] = (True, True), cap_regions: Tuple[int, int] = (0, 0),
              cap_mats: Optional[Tuple[int, int]] = None) -> Tuple[List[int], List[int]]:
    """A cylinder of radius ``r`` along the unit ``axis`` from ``c + a0 axis`` to ``c + a1 axis``."""
    e1, e2 = _perp(axis)
    angs = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    rings = [[b.v(*_add(_add(c, _mul(axis, a)), _add(_mul(e1, r * math.cos(t)), _mul(e2, r * math.sin(t)))))
              for t in angs] for a in (a0, a1)]
    for k in range(sides):
        k1 = (k + 1) % sides
        tm = (angs[k] + angs[k1]) / 2 if k1 else angs[k] + math.pi / sides
        _face_out(b, [rings[0][k], rings[0][k1], rings[1][k1], rings[1][k]],
                  _add(_mul(e1, math.cos(tm)), _mul(e2, math.sin(tm))), mat)
    cm = cap_mats or (mat, mat)
    if caps[0]:
        b.fill([rings[0]], cm[0], cap_regions[0], _mul(axis, -1.0))
    if caps[1]:
        b.fill([rings[1]], cm[1], cap_regions[1], axis)
    return rings[0], rings[1]


def _revolve(b: Builder, c: Vec3, axis: Vec3, prof: Sequence[Tuple[float, float]], sides: int, mat: int,
             closed: bool = True, cap_first: bool = False, cap_last: bool = False) -> None:
    """Revolve a profile [(r, a)] (a = distance along ``axis`` from ``c``) about the axis. ``closed`` joins the last
    profile point to the first (a ring solid); otherwise the ends at r > 0 are capped with flat discs when asked."""
    e1, e2 = _perp(axis)
    n = len(prof)
    angs = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
    rings = [[b.v(*_add(_add(c, _mul(axis, a)), _add(_mul(e1, r * math.cos(t)), _mul(e2, r * math.sin(t)))))
              for t in angs] for r, a in prof]
    # the outward side of each profile edge: away from the profile's centroid, in (r, a)
    cr = sum(p[0] for p in prof) / n
    ca = sum(p[1] for p in prof) / n
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        (r0, a0), (r1, a1) = prof[i], prof[j]
        on_r, on_a = (a1 - a0), -(r1 - r0)
        mr, ma = (r0 + r1) / 2 - cr, (a0 + a1) / 2 - ca
        if closed and on_r * mr + on_a * ma < 0:
            on_r, on_a = -on_r, -on_a
        if not closed:                               # an open profile runs round the solid: normal points out
            if on_r * mr + on_a * ma < 0:
                on_r, on_a = -on_r, -on_a
        for k in range(sides):
            k1 = (k + 1) % sides
            tm = (angs[k] + angs[k1]) / 2 if k1 else angs[k] + math.pi / sides
            radial = _add(_mul(e1, math.cos(tm)), _mul(e2, math.sin(tm)))
            _face_out(b, [rings[i][k], rings[i][k1], rings[j][k1], rings[j][k]],
                      _add(_mul(radial, on_r), _mul(axis, on_a)), mat)
    if cap_first:
        b.fill([rings[0]], mat, 0, _mul(axis, -1.0 if prof[0][1] <= prof[-1][1] else 1.0))
    if cap_last:
        b.fill([rings[-1]], mat, 0, _mul(axis, 1.0 if prof[-1][1] >= prof[0][1] else -1.0))


def _tube(b: Builder, pts: Sequence[Vec3], r: float, sides: int, mat: int, up: Vec3 = (0.0, 0.0, 1.0),
          caps: Tuple[bool, bool] = (True, True)) -> None:
    """A round wire along an open polyline, mitred at the joints (parallel-transported frame)."""
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
        angs = [2 * math.pi * (k + 0.5) / sides for k in range(sides)]
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


def _rr(w: float, d: float, r: float, segs: int, ins: float = 0.0, cx: float = 0.0, cy: float = 0.0):
    """A rounded rectangle inset by ``ins`` (same point count for every inset, so lofts stitch)."""
    pts = rounded_rect(w - 2 * ins, d - 2 * ins, max(r - ins, 0.3), segs)
    return [(x + cx, y + cy) for x, y in pts]


def _loft(b: Builder, outlines: Sequence[Tuple[Sequence[Tuple[float, float]], float]], mat: int,
          top: Optional[int] = 0, bottom: Optional[int] = 0, top_holes=(), bottom_holes=(),
          top_mat: Optional[int] = None, bottom_mat: Optional[int] = None) -> Tuple[List, List]:
    """Stack CCW outlines of equal point count at rising z and skin them; planar caps (with optional hole loops)."""
    loops = [b.loop(o, z) for o, z in outlines]
    n = len(outlines[0][0])
    for la, lb in zip(loops[:-1], loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            b.face((la[i], la[j], lb[j], lb[i]), mat)
    if top is not None:
        b.fill([loops[-1], *top_holes], mat if top_mat is None else top_mat, top, (0, 0, 1))
    if bottom is not None:
        b.fill([loops[0], *bottom_holes], mat if bottom_mat is None else bottom_mat, bottom, (0, 0, -1))
    return loops[0], loops[-1]


def _round_rings(t: float, z0: float, r_top: float, r_bot: float, segs_top: int, segs_bot: int,
                 base_ins: float = 0.0) -> List[Tuple[float, float]]:
    """(inset, z) rings of a slab ``t`` thick from ``z0`` with a quarter round ``r_top`` / ``r_bot`` on its top /
    bottom edge, ``segs`` segments each (0 = square)."""
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


def _prism_x(b: Builder, outline_yz: Sequence[Tuple[float, float]], x0: float, x1: float, mat: int,
             cap_mat: Optional[int] = None) -> Tuple[List[int], List[int]]:
    """A closed prism along +X from a (possibly concave) outline in YZ; planar filled caps."""
    lo = [b.v(x0, y, z) for y, z in outline_yz]
    hi = [b.v(x1, y, z) for y, z in outline_yz]
    n = len(outline_yz)
    area = sum(outline_yz[i][0] * outline_yz[(i + 1) % n][1] - outline_yz[(i + 1) % n][0] * outline_yz[i][1]
               for i in range(n))
    for i in range(n):
        j = (i + 1) % n
        (y0, z0), (y1, z1) = outline_yz[i], outline_yz[j]
        out = (0.0, z1 - z0, -(y1 - y0)) if area > 0 else (0.0, -(z1 - z0), y1 - y0)
        _face_out(b, [lo[i], lo[j], hi[j], hi[i]], out, mat)
    cm = mat if cap_mat is None else cap_mat
    b.fill([lo], cm, 0, (-1.0, 0.0, 0.0))
    b.fill([hi], cm, 0, (1.0, 0.0, 0.0))
    return lo, hi


def _area(P) -> float:
    n = len(P)
    return 0.5 * sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))


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


def _chamfer_prism_x(b: Builder, outline_yz, x0: float, x1: float, c: float, mat: int) -> None:
    """A prism along +X from a CCW (y, z) outline whose two end faces are chamfered by ``c`` (real 45-degree
    faces: the moulded edge of a plastic part). ``c`` 0 gives a plain prism."""
    assert _area(outline_yz) > 0, "outline must be counter-clockwise in (y, z)"
    if c <= 0:
        _prism_x(b, outline_yz, x0, x1, mat)
        return
    ins = _offset_poly(outline_yz, c)
    rings = [(ins, x0), (outline_yz, x0 + c), (outline_yz, x1 - c), (ins, x1)]
    loops = [[b.v(x, y, z) for y, z in o] for o, x in rings]
    n = len(outline_yz)
    for k, sx in enumerate((-1.0, 0.0, 1.0)):
        for i in range(n):
            j = (i + 1) % n
            (y0, z0), (y1, z1) = outline_yz[i], outline_yz[j]
            ln = math.hypot(y1 - y0, z1 - z0)
            out = (sx, (z1 - z0) / ln, -(y1 - y0) / ln)
            _face_out(b, [loops[k][i], loops[k][j], loops[k + 1][j], loops[k + 1][i]], out, mat)
    b.fill([loops[0]], mat, 0, (-1.0, 0.0, 0.0))
    b.fill([loops[-1]], mat, 0, (1.0, 0.0, 0.0))


def _key(b: Builder, fr: Frame, cu: float, cv: float, w: float, h: float, t: float, ins: float, mat: int,
         sink: float = 0.4) -> None:
    """A key cap on the surface frame ``fr`` (w = 0 on the surface): a frustum ``w`` x ``h``, ``t`` proud, its top
    inset ``ins`` all round; open bottom ``sink`` below the surface (hidden inside the body)."""
    bot = [fr.p(cu + x, cv + y, -sink) for x, y in rect(w, h)]
    top = [fr.p(cu + x, cv + y, t) for x, y in rect(w - 2 * ins, h - 2 * ins)]
    lb = [b.v(*p) for p in bot]
    lt = [b.v(*p) for p in top]
    for i in range(4):
        j = (i + 1) % 4
        mid = _mul(_add(_add(bot[i], bot[j]), _add(top[i], top[j])), 0.25)
        _face_out(b, [lb[i], lb[j], lt[j], lt[i]], _sub(mid, fr.p(cu, cv, t / 2)), mat)
    _face_out(b, lt, fr.W, mat)


def _obox(b: Builder, fr: Frame, u0, u1, v0, v1, w0, w1, mat: int, top_region: int = 0,
          top_mat: Optional[int] = None, faces: Optional[dict] = None) -> None:
    """A box in the frame ``fr``: [u0, u1] x [v0, v1] x [w0, w1]; the +W face may take its own region / material;
    ``faces`` {"-w": (mat, region), ...} overrides any side."""
    P = {(i, j, k): b.v(*fr.p((u0, u1)[i], (v0, v1)[j], (w0, w1)[k])) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    quads = {
        "-u": ([P[0, 0, 0], P[0, 1, 0], P[0, 1, 1], P[0, 0, 1]], fr.d(-1, 0, 0)),
        "+u": ([P[1, 0, 0], P[1, 1, 0], P[1, 1, 1], P[1, 0, 1]], fr.d(1, 0, 0)),
        "-v": ([P[0, 0, 0], P[1, 0, 0], P[1, 0, 1], P[0, 0, 1]], fr.d(0, -1, 0)),
        "+v": ([P[0, 1, 0], P[1, 1, 0], P[1, 1, 1], P[0, 1, 1]], fr.d(0, 1, 0)),
        "-w": ([P[0, 0, 0], P[1, 0, 0], P[1, 1, 0], P[0, 1, 0]], fr.d(0, 0, -1)),
        "+w": ([P[0, 0, 1], P[1, 0, 1], P[1, 1, 1], P[0, 1, 1]], fr.d(0, 0, 1)),
    }
    for key, (q, out) in quads.items():
        if faces and key in faces:
            _face_out(b, q, out, faces[key][0], faces[key][1])
        elif key == "+w":
            _face_out(b, q, out, mat if top_mat is None else top_mat, top_region)
        else:
            _face_out(b, q, out, mat)


def _frame_planar(fr: Frame, u0: float, v0: float, w: float, h: float, tile_u: float = 0.0,
                  tile_v: float = 0.0, flip_u: bool = False):
    """A print projection in the plane of ``fr``: the rect [u0, u0 + w] x [v0, v0 + h] -> one 0-1 tile."""
    def proj(x, y, z):
        d = _sub((x, y, z), fr.o)
        u = (_dot(d, fr.U) - u0) / w
        if flip_u:
            u = 1.0 - u
        return (tile_u + inset(u), tile_v + inset((_dot(d, fr.V) - v0) / h))
    return proj


# =========================================================================== G2 cash drawer + tray

def _dr_dims():
    s = DRAWER
    w, d, h = s["w"], s["d"], s["h"]
    fs, ft, fb = s["frame"]
    yf = d / 2                                  # the housing front (+Y, the staff side)
    pw, ph, pt = s["panel"]
    bw, bh = s["bin"]
    zb = fb + 2.0                               # the tray's underside (2 over the housing floor)
    zp0 = fb + 1.0                              # the panel's lower edge (1 inside the opening)
    return dict(w=w, d=d, h=h, fs=fs, ft=ft, fb=fb, yf=yf, pw=pw, ph=ph, pt=pt, bw=bw, bh=bh, zb=zb, zp0=zp0,
                ox=w / 2 - fs, oz=(fb, h - ft))


def _drawer_lod(level: int) -> Lod:
    """Sheet 26 panel 1: a black steel sleeve with softly rounded edges, open at the front, where a frame
    (the folded edge of the sheet) runs round the tray opening."""
    k = _dr_dims()
    s = DRAWER
    STEEL = 0
    b = Builder()
    b.box((-k["w"] / 2, -k["d"] / 2, 0.0), (k["w"] / 2, k["d"] / 2, k["h"]), mat=STEEL)
    if level == 2:
        return Lod(b)
    bay = Builder()
    bay.box((-k["ox"], -k["d"] / 2 + s["back"], k["oz"][0]), (k["ox"], k["yf"] + 1.0, k["oz"][1]), mat=STEEL)
    if level == 0:
        return Lod(b, bevel_mm=s["r"], bevel_segments=2, bevel_first=True, ops=[("DIFFERENCE", bay)])
    return Lod(b, ops=[("DIFFERENCE", bay)])


def item_cash_drawer() -> Item:
    k = _dr_dims()
    w, d, h = k["w"], k["d"], k["h"]
    ty = (DRAWER["bin_back"] + k["yf"]) / 2
    return Item(
        name="SM_CSK_CashDrawer", lods=[_drawer_lod(i) for i in range(3)], materials=["M_CSK_SteelBlack"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Tray", (0.0, ty, k["zb"]))],
        hulls=[((-w / 2, -d / 2, h - k["ft"]), (w / 2, d / 2, h)),               # top
               ((-w / 2, -d / 2, 0.0), (w / 2, d / 2, k["fb"])),                 # floor
               ((-w / 2, -d / 2, k["fb"]), (-k["ox"], d / 2, h - k["ft"])),      # sides
               ((k["ox"], -d / 2, k["fb"]), (w / 2, d / 2, h - k["ft"])),
               ((-k["ox"], -d / 2, k["fb"]), (k["ox"], -d / 2 + DRAWER["back"], h - k["ft"]))],   # back
        budget=BUDGETS["SM_CSK_CashDrawer"],
        data={"footprint_mm": [w, d, h], "pose": "upright", "pivot": "bottom-centre",
              "front": "+Y (the staff side; the tray slides toward +Y, spec G2)",
              "parts": {"Tray": {"mesh": "SM_CSK_CashDrawer_Tray", "socket": "Tray", "type": "slide", "axis": "Y",
                                 "range_mm": [0, DRAWER["travel"]]}},
              "reference": REF,
              "notes": ["Sheet 26 panel 1: the black steel housing with rounded edges and a front frame round the "
                        "opening; the tray (panel, lock, bin, insert, clips) is the separate sliding part",
                        "5 hulls: the housing's walls, so the tray can slide inside"]},
    )


def _tray_layout():
    """Pocket rectangles in the drawer frame: notes (5, at the back) and coins (2 rows x 4, at the front)."""
    k = _dr_dims()
    s = DRAWER
    bw, wall, dv = s["bin"][0], s["wall"], s["div"]
    xi0, xi1 = -bw / 2 + wall, bw / 2 - wall
    yi0 = s["bin_back"] + wall
    yi1 = k["yf"] - k["pt"] - wall - 0.5 + 0.5          # the insert's front wall behind the panel
    ztop = k["zb"] + s["bin"][1]
    zfl = ztop - s["pocket_d"]
    n = s["notes"]
    nw = (xi1 - xi0 - (n - 1) * dv) / n
    notes = [(xi0 + i * (nw + dv), yi0, xi0 + i * (nw + dv) + nw, yi0 + s["note_len"]) for i in range(n)]
    cols, rows = s["coin_cols"], s["coin_rows"]
    cw = (xi1 - xi0 - (cols - 1) * dv) / cols
    y0 = yi0 + s["note_len"] + dv
    ch = (yi1 - y0 - (rows - 1) * dv) / rows
    coins = [(xi0 + c * (cw + dv), y0 + r * (ch + dv), xi0 + c * (cw + dv) + cw, y0 + r * (ch + dv) + ch)
             for r in range(rows) for c in range(cols)]
    return dict(notes=notes, coins=coins, ztop=ztop, zfl=zfl, xi=(xi0, xi1), yi=(yi0, yi1))


def _tray_lod(level: int) -> Lod:
    """Sheet 26 panel 1: the front panel with its round chrome lock, the steel bin behind it, and the black
    plastic insert: 5 note slots at the back, each with a wire U clip on a barrel at the back wall, and the coin
    cups in front of them (real pockets, cut)."""
    k = _dr_dims()
    s = DRAWER
    STEEL, PLASTIC, METAL = 0, 1, 2
    L = _tray_layout()
    pw, ph, pt = k["pw"], k["ph"], k["pt"]
    yf = k["yf"]
    b = Builder()
    b.box((-pw / 2, yf - pt, k["zp0"]), (pw / 2, yf, k["zp0"] + ph), mat=STEEL)        # the front panel
    ops = []
    bin_ = Builder()
    bw, bh = s["bin"]
    bin_.box((-bw / 2, s["bin_back"], k["zb"]), (bw / 2, yf - pt + 0.5, k["zb"] + bh), mat=STEEL,
             mats={"pz": PLASTIC})
    ops.append(("UNION", bin_))
    if level < 2:
        for x0, y0, x1, y1 in L["notes"] + L["coins"]:
            c = Builder()
            c.box((x0, y0, L["zfl"]), (x1, y1, L["ztop"] + 1.0), mat=PLASTIC)
            ops.append(("DIFFERENCE", c))
    else:
        (xi0, xi1), (yi0, yi1) = L["xi"], L["yi"]
        c = Builder()
        c.box((xi0, yi0, L["ztop"] - 6.0), (xi1, yi1, L["ztop"] + 1.0), mat=PLASTIC)
        ops.append(("DIFFERENCE", c))
    e = Builder()
    ld, lp, lz = s["lock"]
    if level < 2:                                   # the lock: a chrome cylinder with a keyhole
        _cyl_axis(e, (0.0, yf, lz), (0.0, 1.0, 0.0), ld / 2, -0.5, lp, (12, 10)[level], METAL, caps=(False, True))
        if level == 0:
            _box(e, (-0.9, yf + lp - 0.3, lz - 3.5), (0.9, yf + lp + 0.25, lz + 2.0), PLASTIC)
            _cyl_axis(e, (0.0, yf, lz + 2.0), (0.0, 1.0, 0.0), 1.6, lp - 0.3, lp + 0.25, 6, PLASTIC,
                      caps=(False, True))
    if level < 2:                                   # the note clips: a wire U from a barrel on the back wall
        hx, wr, br = s["clip"]
        yb = s["bin_back"] + 1.0
        zt = L["ztop"]
        zn = L["zfl"] + MONEY["stack"][2] + wr + 0.5       # the clip tip rests just over a full note stack
        for x0, y0, x1, y1 in L["notes"]:
            cx = (x0 + x1) / 2
            if level == 0:
                _cyl_axis(e, (cx, yb + br, zt + br - 0.5), (1.0, 0.0, 0.0), br, -hx - 3.0, hx + 3.0, 6, METAL)
            if level == 0:
                p = [(cx - hx, yb + br, zt + br - 0.5), (cx - hx, yb + 80.0, zn), (cx - hx + 1.0, yb + 94.0, zn + 7.0),
                     (cx + hx - 1.0, yb + 94.0, zn + 7.0), (cx + hx, yb + 80.0, zn), (cx + hx, yb + br, zt + br - 0.5)]
                _tube(e, p, wr, 4, METAL, up=(0.0, 0.0, 1.0), caps=(False, False))    # both ends inside the barrel
            else:                                   # far: one wire down the slot's middle
                p = [(cx, yb, zt + br - 0.5), (cx, yb + 80.0, zn), (cx, yb + 94.0, zn + 7.0)]
                _tube(e, p, wr * 1.5, 3, METAL)
    if level == 0:
        return Lod(b, bevel_mm=1.5, bevel_segments=1, bevel_first=True, ops=ops, extra=e)
    return Lod(b, ops=ops, extra=e if level < 2 else None)


def item_cash_drawer_tray() -> Item:
    k = _dr_dims()
    s = DRAWER
    L = _tray_layout()
    ty = (s["bin_back"] + k["yf"]) / 2
    zb = k["zb"]
    piv = (0.0, ty, zb)                             # the tray's pivot: its underside centre, closed

    def sh(p):
        return (p[0] - piv[0], p[1] - piv[1], p[2] - piv[2])
    lods = [_tray_lod(i) for i in range(3)]
    for lod in lods:                                # move everything into the tray's own frame (origin = pivot)
        for bb in [lod.builder, lod.extra] + [c for _, c in lod.ops]:
            if bb is not None:
                bb.verts = [sh(p) for p in bb.verts]
    sockets = [Socket("Seat", (0, 0, 0))]
    for i, (x0, y0, x1, y1) in enumerate(L["notes"]):
        sockets.append(Socket(f"Bill_{i + 1:02d}", sh(((x0 + x1) / 2, (y0 + y1) / 2, L["zfl"])), (0.0, 0.0, 90.0)))
    for i, (x0, y0, x1, y1) in enumerate(L["coins"]):
        sockets.append(Socket(f"Coin_{i + 1:02d}", sh(((x0 + x1) / 2, (y0 + y1) / 2, L["zfl"]))))
    sockets.append(Socket("Grip", sh((0.0, k["yf"], k["zp0"] + k["ph"] / 2)), (-90.0, 0.0, 0.0)))
    (xi0, xi1), (yi0, yi1) = L["xi"], L["yi"]
    y_notes1 = L["notes"][0][3]
    pw = k["pw"]
    return Item(
        name="SM_CSK_CashDrawer_Tray", lods=lods, materials=["M_CSK_SteelBlack", "M_CSK_Plastic", "M_CSK_Metal"],
        projections={}, sockets=sockets,
        hulls=[(sh((-pw / 2, s["bin_back"], zb)), sh((pw / 2, k["yf"], k["zp0"] + k["ph"])))],
        budget=BUDGETS["SM_CSK_CashDrawer_Tray"],
        data={"part_of": "SM_CSK_CashDrawer", "pivot": "the tray's underside centre in the closed position",
              "slide": {"axis": "+Y", "range_mm": [0, s["travel"]]},
              "contain": {
                  "Bill": {"sockets": [f"Bill_{i:02d}" for i in range(1, s["notes"] + 1)],
                           "cavity_mm": [list(sh((xi0, yi0, L["zfl"]))), list(sh((xi1, y_notes1, L["ztop"])))],
                           "accepts": ["Bill"], "pose": "turned 90 deg about Z (the notes run front to back)"},
                  "Coin": {"sockets": [f"Coin_{i:02d}" for i in range(1, len(L["coins"]) + 1)],
                           "cavity_mm": [list(sh((xi0, L["coins"][0][1], L["zfl"]))),
                                         list(sh((xi1, yi1, L["ztop"])))],
                           "accepts": ["Coin"]}},
              "reference": REF,
              "notes": ["Sheet 26 panel 1 draws 2 rows x 5 coin cups; the sheet's call-out, the log and the spec say 8, "
                        "so the cups are 2 rows x 4 (E*, logged)",
                        "Bill_NN / Coin_NN sit on the pocket floors and move with the tray"]},
    )


# =========================================================================== G8 money

def item_bills_stack() -> Item:
    """Plain notes, no currency design: 5 note bundles, each a slab offset up to 1 mm (loose notes). The top and
    bottom faces carry the generic money print (Signs atlas cell, UV0 tiles front / back); the edges read as the
    print master's edge colour."""
    m = MONEY
    W, D, H = m["stack"]
    nw, nd = m["note"]
    n = m["layers"]
    t = H / n
    offs = [(0.0, 0.0), (0.9, -0.6), (-0.8, 0.7), (0.6, 0.9), (0.0, 0.0)]       # E: the bundles' offsets
    b = Builder()
    for i in range(n):
        ox, oy = offs[i]
        z0 = i * t - (0.3 if i else 0.0)
        z1 = (i + 1) * t
        regions = {}
        if i == n - 1:
            regions["pz"] = R_FRONT
        if i == 0:
            regions["nz"] = R_BACK
        skip = [] if i in (0, n - 1) else []
        b.box((-nw / 2 + ox, -nd / 2 + oy, z0), (nw / 2 + ox, nd / 2 + oy, z1), mat=0, regions=regions, skip=skip)
    # the offsets stay inside the stack bounds: 148 + 2 x 1 = 150, 68 + 2 x 1 = 70
    return Item(
        name="SM_CSK_Bills_Stack", lods=[Lod(b)], materials=["M_CSK_Money"],
        projections={R_FRONT: _planar(-nw / 2, -nd / 2, nw, nd),
                     R_BACK: _planar(-nw / 2, -nd / 2, nw, nd, tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, -D / 2, H / 2)), Socket("Stack", (0.0, 0.0, H))],
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))], cls="Bill", budget=BUDGETS["SM_CSK_Bills_Stack"],
        data={"footprint_mm": [W, D, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "reference": REF, "print": "T_CSK_Signs generic money cell (spec 4.1); no real currency design",
              "notes": ["Sheet 26 shows loose notes in the drawer, no stack: the stack is 5 slightly offset "
                        "bundles, the kit's plain look"]},
    )


def item_coin() -> Item:
    """A plain coin (no design): a disc with a rounded rim."""
    m = MONEY
    dia, t = m["coin"]
    r, e = dia / 2, m["coin_edge"]
    b = Builder()
    sides = 15
    prof = [(r - e, 0.0), (r, e), (r, t - e), (r - e, t)]
    _revolve(b, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), prof, sides, 0, closed=False, cap_first=True, cap_last=True)
    return Item(
        name="SM_CSK_Coin", lods=[Lod(b)], materials=["M_CSK_Coin"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, -r, t / 2)), Socket("Stack", (0.0, 0.0, t))],
        hulls=[((-r, -r, 0.0), (r, r, t))], cls="Coin", budget=BUDGETS["SM_CSK_Coin"],
        data={"footprint_mm": [dia, dia, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 20},
              "reference": REF, "notes": ["Plain disc with a rounded rim; gold / silver / copper are MIs"]},
    )


# =========================================================================== G3 card terminal

def _term_profile():
    t = TERMINAL
    L = t["l"] / 2
    by, bz = t["deck_break"]
    ry, rz = t["rear_top"]
    u0, u1, u2, u3, uh = t["undercut"]
    return [(-L, 0.0), (u0, 0.0), (u1, uh), (u2, uh), (u3, 0.0), (L, 0.0), (L, t["back_top"]), (ry, rz),
            (by, bz), (-L, t["front_h"])]


def _term_frames():
    """The keypad deck frame (origin at the front top edge) and the screen deck frame (origin at the break)."""
    t = TERMINAL
    L = t["l"] / 2
    by, bz = t["deck_break"]
    ry, rz = t["rear_top"]
    kd = Frame((0.0, -L, t["front_h"]), (1.0, 0.0, 0.0), (0.0, by + L, bz - t["front_h"]))
    sd = Frame((0.0, by, bz), (1.0, 0.0, 0.0), (0.0, ry - by, rz - bz))
    return kd, sd


def _term_lod(level: int) -> Lod:
    """Sheet 26 panel 2: a wedge body, the keypad on the low front deck (3 soft keys under the screen, a 3 x 4
    numeric block, red / yellow / green function keys at the front), the colour screen recessed in the steeper rear
    deck, the card slot across the front face, an undercut under the rear."""
    t = TERMINAL
    PLASTIC, SCREEN, KEYS, RED, YEL, GRN = range(6)
    W = t["w"]
    kd, sd = _term_frames()
    b = Builder()
    _prism_x(b, _term_profile(), -W / 2, W / 2, PLASTIC)
    sw, sh, sdp, sv = t["screen"]
    ops = []
    e = Builder()
    if level < 2:
        cut = Builder()                                  # the screen recess: its floor is the screen (0-1 island)
        _obox(cut, sd, -sw / 2, sw / 2, sv, sv + sh, -sdp, 6.0, PLASTIC, faces={"-w": (SCREEN, R_FRONT)})
        ops.append(("DIFFERENCE", cut))
        slot = Builder()
        slw, slh, sld, slz = t["slot"]
        slot.box((-slw / 2, -t["l"] / 2 - 1.0, slz - slh / 2), (slw / 2, -t["l"] / 2 + sld, slz + slh / 2), mat=KEYS)
        ops.append(("DIFFERENCE", slot))
    else:                                                # far: the screen as a thin plate on the deck
        _obox(e, sd, -sw / 2, sw / 2, sv, sv + sh, -0.5, 0.3, PLASTIC, faces={"+w": (SCREEN, R_FRONT)})
    kw, kh, kt, ki = t["key"]
    cs = t["cols"]
    r = t["rows"]
    if level == 0:
        for u, m in ((-cs, RED), (0.0, YEL), (cs, GRN)):
            _key(e, kd, u, r[0], t["fkey"][0], t["fkey"][1], kt, ki, m)
        for v in r[1:5]:
            for u in (-cs, 0.0, cs):
                _key(e, kd, u, v, kw, kh, kt, ki, KEYS)
        sw_, sh_, smid = t["soft"]
        for u, w_ in ((-cs, sw_), (0.0, smid), (cs, sw_)):
            _key(e, kd, u, r[5], w_, sh_, kt * 0.8, ki, KEYS)
    elif level == 1:                                     # mid: the key block as one plate, the colour keys kept
        for u, m in ((-cs, RED), (0.0, YEL), (cs, GRN)):
            _key(e, kd, u, r[0], t["fkey"][0], t["fkey"][1], kt, ki, m)
        _key(e, kd, 0.0, (r[1] + r[5]) / 2, 2 * cs + kw, r[5] - r[1] + kh, kt * 0.6, 1.0, KEYS)
    if level == 0:
        return Lod(b, bevel_mm=t["bevel"], bevel_segments=3, bevel_first=True, ops=ops, extra=e)
    if level == 1:
        return Lod(b, bevel_mm=t["bevel"], bevel_segments=1, bevel_first=True, ops=ops, extra=e)
    return Lod(b, ops=ops, extra=e)


def item_terminal() -> Item:
    t = TERMINAL
    W, Lt, H = t["w"], t["l"], t["h"]
    kd, sd = _term_frames()
    sw, sh, sdp, sv = t["screen"]
    tilt = math.degrees(math.atan2(sd.V[2], sd.V[1]))
    sc = sd.p(0.0, sv + sh / 2, -sdp)
    slw, slh, sld, slz = t["slot"]
    return Item(
        name="SM_CSK_Terminal_Card", lods=[_term_lod(i) for i in range(3)],
        materials=["M_CSK_Plastic", "M_CSK_Screen", "M_CSK_Rubber", "M_CSK_AccentRed", "M_CSK_AccentYellow",
                   "M_CSK_AccentGreen"],
        projections={R_FRONT: _frame_planar(sd, -sw / 2, sv, sw, sh)},
        sockets=[Socket("Seat", (0, 0, 0)),
                 Socket("CardSlot", (0.0, -Lt / 2, slz), (90.0, 0.0, 0.0)),         # +Z out of the slot (-Y)
                 Socket("Tap", sc, (tilt, 0.0, 0.0)),                               # the screen, +Z out of it
                 Socket("Grip", (0.0, 40.0, H / 2))],
        hulls=[((-W / 2, -Lt / 2, 0.0), (W / 2, Lt / 2, H))], budget=BUDGETS["SM_CSK_Terminal_Card"],
        data={"footprint_mm": [W, Lt, H], "pose": "upright", "pivot": "bottom-centre", "front": "-Y (card slot, keys)",
              "screen": {"slot": "M_CSK_Screen", "uv0": "0-1 tile", "size_mm": [sw, sh]},
              "reference": REF,
              "notes": ["Sheet 26 panel 2: wedge body, 3 soft + 12 numeric + 3 function keys (red / yellow / green), "
                        "a recessed colour screen on the rear deck, the card slot across the front, an undercut under "
                        "the rear. Key legends are not modelled (print).",
                        "Spec size 168 x 81 x 56 is W x D x H; the sheet draws 81 across the front, so the long axis "
                        "runs along Y (front = -Y, the kit rule)"]},
    )


# =========================================================================== G4 receipt printer + lid

def _printer_lod(level: int) -> Lod:
    """Sheet 26 panel 3: a black box body with rounded edges and a parting line round it, a recessed panel low on
    the front, the front ledge with the tear bar and a square feed key, the paper bay behind it holding the 80 mm
    roll (the lid is the separate hinged part)."""
    p = PRINTER
    PLASTIC, PAPER, BOARD, STEEL = range(4)
    W, D, Hb = p["w"], p["d"], p["body_h"]
    b = Builder()
    b.box((-W / 2, -D / 2, 0.0), (W / 2, D / 2, Hb), mat=PLASTIC)
    ops = []
    bw, by0, by1, bz = p["bay"]
    bay = Builder()
    bay.box((-bw / 2, by0, bz), (bw / 2, by1, Hb + 1.0), mat=PLASTIC)
    ops.append(("DIFFERENCE", bay))
    if level == 0:
        sz, sh, sd = p["seam"]
        cut = Builder()
        cut.box((-W / 2 - 2, -D / 2 - 2, sz - sh / 2), (W / 2 + 2, D / 2 + 2, sz + sh / 2), mat=PLASTIC)
        core = Builder()
        core.box((-W / 2 + sd, -D / 2 + sd, sz - sh / 2 - 0.3), (W / 2 - sd, D / 2 - sd, sz + sh / 2 + 0.3),
                 mat=PLASTIC)
        ops += [("DIFFERENCE", cut), ("UNION", core)]
    if level < 2:
        x0, x1, z0, z1, dp = p["front_panel"]
        fp = Builder()
        fp.box((x0, -D / 2 - 1.0, z0), (x1, -D / 2 + dp, z1), mat=PLASTIC)
        ops.append(("DIFFERENCE", fp))
    e = Builder()
    rw, rr, rc = p["roll"]
    ry = (by0 + by1) / 2
    rz = bz + rr - 0.5                                  # the roll rests on the bay floor
    _cyl_axis(e, (0.0, ry, rz), (1.0, 0.0, 0.0), rr, -rw / 2, rw / 2, (16, 10, 6)[level], PAPER)
    if level < 2:
        _cyl_axis(e, (0.0, ry, rz), (1.0, 0.0, 0.0), rc, -rw / 2 - 0.4, rw / 2 + 0.4, (8, 6)[level], BOARD)
        tw, td, tp = p["tear"]
        _box(e, (-tw / 2, by0 - td, Hb - 0.5), (tw / 2, by0 - 0.5, Hb + tp), STEEL)
        kw, kd, kp, kx, ky = p["button"]
        _box(e, (kx - kw / 2, ky - kd / 2, Hb - 0.5), (kx + kw / 2, ky + kd / 2, Hb + kp), PLASTIC)
    if level == 0:
        return Lod(b, bevel_mm=p["r"], bevel_segments=2, bevel_first=True, ops=ops, extra=e)
    return Lod(b, ops=ops, extra=e)


def item_printer() -> Item:
    p = PRINTER
    W, D, H, Hb = p["w"], p["d"], p["h"], p["body_h"]
    hy, hz = p["hinge"]
    by0 = p["bay"][1]
    return Item(
        name="SM_CSK_Printer_Receipt", lods=[_printer_lod(i) for i in range(3)],
        materials=["M_CSK_Plastic", "M_CSK_Paper", "M_CSK_Board", "M_CSK_SteelDark"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Lid", (0.0, hy, hz)),
                 Socket("PaperOut", (0.0, by0 - 1.0, Hb + 1.0), (20.0, 0.0, 0.0))],     # +Z up and a little forward
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, Hb))], budget=BUDGETS["SM_CSK_Printer_Receipt"],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre", "front": "-Y (paper exit)",
              "parts": {"Lid": {"mesh": "SM_CSK_Printer_Receipt_Lid", "socket": "Lid", "type": "hinge", "axis": "X",
                                "range_deg": [p["open_deg"], 0], "open_rot_deg": [p["open_deg"], 0.0, 0.0]}},
              "reference": REF,
              "notes": ["Sheet 26 panel 3 draws the lid open over the 80 mm roll; the lid is a separate hinged part "
                        "(spec: parts none) so the printer can stand closed on the counter; open_rot_deg is the "
                        "sheet's pose",
                        "Size: the sheet's call-outs put 152 across the front and 179 deep (the spec's 179 x 152 E)"]},
    )


def _printer_lid_lod(level: int) -> Lod:
    """The clamshell lid in its hinge frame (origin on the hinge axis, closed): top plate, side skirts and a front
    wall as separate convex blocks (a shell), the platen roller along the front edge inside, round hinge bosses
    with pins (sheet 26)."""
    p = PRINTER
    PLASTIC, RUBBER, METAL = range(3)
    W, Hb, H = p["w"], p["body_h"], p["h"]
    hy, hz = p["hinge"]
    t, sk = p["lid_t"], p["skirt"]
    yf = p["lid_front"] - hy
    z0, z1 = Hb - hz, H - hz                           # the lid's bottom edge (on the body top) and its top
    b = Builder()
    b.box((-W / 2, yf, z1 - t), (W / 2, 0.0, z1), mat=PLASTIC)                          # top plate (bevelled)
    e = Builder()
    for sx in (-1, 1):                                                                 # side skirts
        _box(e, (sx * (W / 2 - 0.3), yf + 0.8, z0), (sx * (W / 2 - sk), -0.8, z1 - 0.5), PLASTIC)
    e.box((-W / 2 + sk - 0.5, yf + 0.8, z0 + 4.0), (W / 2 - sk + 0.5, yf + t, z1 - 0.5), mat=PLASTIC)  # front wall
    if level < 2:
        pl, pr = p["platen"]
        _cyl_axis(e, (0.0, yf + t + pr + 2.0, z0 + 4.0 + pr * 0.5), (1.0, 0.0, 0.0), pr, -pl, pl, (8, 6)[level],
                  RUBBER)
        br, bp, pin = p["boss"]
        for sx in ((-1, 1) if level == 0 else ()):     # the inner end is inside the skirt: no cap there
            _cyl_axis(e, (0.0, 0.0, 0.0), (float(sx), 0.0, 0.0), br, W / 2 - 1.0, W / 2 + bp, (10, 8)[level],
                      PLASTIC, caps=(False, True))
            if level == 0:
                _cyl_axis(e, (0.0, 0.0, 0.0), (float(sx), 0.0, 0.0), pin, W / 2 + bp - 0.5, W / 2 + bp + 0.6, 6,
                          METAL, caps=(False, True))
    if level == 0:
        return Lod(b, bevel_mm=1.2, bevel_segments=1, extra=e)
    return Lod(b, extra=e)


def item_printer_lid() -> Item:
    p = PRINTER
    W, Hb, H = p["w"], p["body_h"], p["h"]
    hy, hz = p["hinge"]
    yf = p["lid_front"] - hy
    br, bp, _ = p["boss"]
    return Item(
        name="SM_CSK_Printer_Receipt_Lid", lods=[_printer_lid_lod(i) for i in range(3)],
        materials=["M_CSK_Plastic", "M_CSK_Rubber", "M_CSK_Metal"], projections={},
        sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-W / 2, yf, Hb - hz), (W / 2, 0.0, H - hz))], budget=BUDGETS["SM_CSK_Printer_Receipt_Lid"],
        data={"part_of": "SM_CSK_Printer_Receipt", "pivot": "hinge axis (X), closed pose",
              "open_rot_deg": [p["open_deg"], 0.0, 0.0], "reference": REF},
    )


# =========================================================================== G5 POS screen

def _pos_frame() -> Frame:
    p = POS
    t = math.radians(p["tilt"])
    yc, zc = p["centre"]
    return Frame((0.0, yc, zc), (1.0, 0.0, 0.0), (0.0, math.sin(t), math.cos(t)))    # W: the screen's facing (-Y, up)


def _pos_screen_rect():
    p = POS
    W, H, _ = p["disp"]
    bs, bt, bb = p["bezel"]
    return -W / 2 + bs, -H / 2 + bb, W - 2 * bs, H - bt - bb      # u0, v0, w, h


def _pos_lod(level: int) -> Lod:
    """Sheet 26 panel 4: a slim display with rounded corners and a thin black bezel, leaning back on a short wide
    neck that rises from a square base plate with a rounded top edge."""
    p = POS
    PLASTIC, SCREEN = range(2)
    fr = _pos_frame()
    W, H, T = p["disp"]
    segs = (3, 2, 0)[level]
    loc = Builder()
    if level < 2:
        rf, rb = p["edge"]
        rings = _round_rings(T, -T / 2, rf, rb, (1, 0)[level], (2, 1)[level])
        _loft(loc, [(_rr(W, H, p["disp_r"], segs, ins), z) for ins, z in rings], PLASTIC)
    else:
        loc.box((-W / 2, -H / 2, -T / 2), (W / 2, H / 2, T / 2), mat=PLASTIC)
    b = Builder()
    _merge_frame(b, loc, fr)
    u0, v0, sw, sh = _pos_screen_rect()
    ops = []
    e = Builder()
    if level < 2:
        cut = Builder()
        _obox(cut, fr, u0, u0 + sw, v0, v0 + sh, T / 2 - p["recess"], T / 2 + 5.0, PLASTIC,
              faces={"-w": (SCREEN, R_FRONT)})
        ops.append(("DIFFERENCE", cut))
    else:
        _obox(e, fr, u0, u0 + sw, v0, v0 + sh, T / 2 - 0.5, T / 2 + 0.2, PLASTIC, faces={"+w": (SCREEN, R_FRONT)})
    if level == 0:                                                  # the camera dot, centred in the top bezel
        cv = H / 2 - p["bezel"][1] / 2
        _cyl_axis(e, fr.p(0.0, cv, 0.0), fr.W, p["cam"], T / 2 - 0.5, T / 2 + 0.3, 8, SCREEN, caps=(False, True))
    # the base plate
    bw, bd, bt, br = p["base"]
    re, rc = p["base_edge"]
    bsegs = (4, 2, 0)[level]
    if level < 2:
        rings = [(rc, 0.0), (0.0, rc)] + [(ins, z) for ins, z in _round_rings(bt - rc, rc, re, 0.0,
                                                                                (2, 1)[level], 0)][1:]
        _loft(e, [(_rr(bw, bd, br, bsegs, ins), z) for ins, z in rings], PLASTIC)
    else:
        e.box((-bw / 2, -bd / 2, 0.0), (bw / 2, bd / 2, bt), mat=PLASTIC)
    # the neck: a vertical block from the base into the display's back, and a mount block square to the display
    nw, nd, ny = p["neck"]
    back = fr.p(0.0, -H / 2 + 60.0, -T / 2)             # a point on the display's back, low down
    ztop = back[2] + 25.0
    e.box((-nw / 2, ny, bt - 1.0), (nw / 2, ny + nd, ztop), mat=PLASTIC)
    if level < 2:
        _obox(e, fr, -nw / 2 + 4.0, nw / 2 - 4.0, -H / 2 + 30.0, -H / 2 + 100.0, -T / 2 - 16.0, -T / 2 + 4.0, PLASTIC)
    return Lod(b, ops=ops, extra=e)


def item_pos_screen() -> Item:
    p = POS
    fr = _pos_frame()
    W, H, T = p["disp"]
    bw, bd, bt, _ = p["base"]
    u0, v0, sw, sh = _pos_screen_rect()
    sc = fr.p(u0 + sw / 2, v0 + sh / 2, T / 2 - p["recess"])
    top = fr.p(0.0, H / 2, T / 2)
    return Item(
        name="SM_CSK_POS_Screen", lods=[_pos_lod(i) for i in range(3)], materials=["M_CSK_Plastic", "M_CSK_Screen"],
        projections={R_FRONT: _frame_planar(fr, u0, v0, sw, sh)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Screen", sc, (90.0 - p["tilt"], 0.0, 0.0))],
        hulls=[((-bw / 2, -bd / 2, 0.0), (bw / 2, bd / 2, bt)),
               ((-W / 2, fr.p(0, -H / 2, T / 2)[1], fr.p(0, -H / 2, 0)[2] - T / 2),
                (W / 2, fr.p(0, H / 2, -T / 2)[1], top[2]))],
        budget=BUDGETS["SM_CSK_POS_Screen"],
        data={"footprint_mm": [W, bd, round(top[2], 1)], "pose": "upright", "pivot": "bottom-centre",
              "front": "-Y (screen)", "screen": {"slot": "M_CSK_Screen", "uv0": "0-1 tile", "size_mm": [sw, sh]},
              "reference": REF,
              "notes": ["Sheet 26 panel 4: 360 x 230 display on a 200 x 200 base; the back of the display is not "
                        "drawn, so it is plain (rounded back edge) with the neck's mount block"]},
    )


# =========================================================================== G6 scanner + cradle

def _sc_head_frame() -> Frame:
    s = SCANNER
    return Frame((0.0, s["head_rear"], s["head_z"]), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))   # W = -Y (the nose)


def _sc_grip_frame() -> Frame:
    s = SCANNER
    p0, p1 = s["grip"]
    w = _unit(_sub(p1, p0))
    u = (1.0, 0.0, 0.0)
    return Frame(p0, u, _cross(w, u))


def _scanner_lod(level: int) -> Lod:
    """Sheet 26 panel 5: a rounded head that flares into a nose bezel round a recessed window, a pistol grip
    raked back to a flat pill-shaped foot (so it stands on the counter), a blue-grey trigger."""
    s = SCANNER
    PLASTIC, WINDOW, TRIG = range(3)
    segs = (3, 1, 1)[level]
    hf = _sc_head_frame()
    loc = Builder()
    secs = (s["head"], tuple(s["head"][i] for i in (0, 2, 3, 4, 5)), (s["head"][0], s["head"][3], s["head"][5]))[level]
    _loft(loc, [(_rr(w, h, r, segs), z) for z, w, h, r in secs], PLASTIC)
    b = Builder()
    _merge_frame(b, loc, hf)
    ops = []
    ww, wh, wd, wr = s["window"]
    nose = s["head"][-1][0]
    cut = Builder()
    cl = Builder()
    _loft(cl, [(_rr(ww, wh, wr, segs), nose - wd), (_rr(ww, wh, wr, segs), nose + 5.0)], PLASTIC,
          bottom_mat=WINDOW)
    _merge_frame(cut, cl, hf)
    ops.append(("DIFFERENCE", cut))
    e = Builder()
    gf = _sc_grip_frame()
    (_, gy0, gz0), (_, gy1, gz1) = s["grip"]
    gsecs = (s["grip_sec"], tuple(s["grip_sec"][i] for i in (0, 2, 4)), (s["grip_sec"][0], s["grip_sec"][-1]))[level]
    _loft(e, [(_rr(w, d, min(w, d) / 2 - 3.0, (2, 2, 1)[level], 0.0, 0.0, gy0 + (gz0 - z) * (gy1 - gy0) / (gz0 - gz1)),
               z) for z, w, d in gsecs], PLASTIC)
    fw, fl, fh, fr, fy = s["foot"]
    fsegs = (4, 2, 1)[level]
    rings = _round_rings(fh, 0.0, 4.0, 1.5, (2, 1, 0)[level], (1, 0, 0)[level])
    _loft(e, [(_rr(fw, fl, fr, fsegs, ins, 0.0, fy), z) for ins, z in rings], PLASTIC)
    tw, (tv0, tv1), (tw0, tw1), ti = s["trigger"]
    if level < 2:                                       # a finger key: a frustum off the grip's front face
        tf = Frame(gf.p(0.0, tv0, (tw0 + tw1) / 2), (1.0, 0.0, 0.0), _mul(gf.W, -1.0))
        _key(e, tf, 0.0, 0.0, tw, tw1 - tw0, tv1 - tv0, ti, TRIG, sink=4.0)
    return Lod(b, ops=ops, extra=e)


def item_scanner() -> Item:
    s = SCANNER
    hf = _sc_head_frame()
    gf = _sc_grip_frame()
    nose = s["head"][-1][0]
    win = hf.p(0.0, 0.0, nose - s["window"][2])
    fw, fl, fh, fr, fy = s["foot"]
    return Item(
        name="SM_CSK_Scanner", lods=[_scanner_lod(i) for i in range(3)],
        materials=["M_CSK_Plastic", "M_CSK_ScanWindow", "M_CSK_AccentBlue"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", gf.p(0.0, 0.0, 26.0)),
                 Socket("Beam", win, (90.0, 0.0, 0.0))],                    # +Z out of the window (-Y)
        hulls=[((-s["w"] / 2, -s["l"] / 2, 0.0), (s["w"] / 2, fy + fl / 2, s["h"]))],
        budget=BUDGETS["SM_CSK_Scanner"],
        data={"footprint_mm": [s["w"], s["l"], s["h"]], "pose": "upright (stands on its foot)",
              "pivot": "bottom-centre of the foot's plan", "front": "-Y (nose)", "reference": REF,
              "notes": ["Sheet 26 panel 5: head with a flared nose bezel and a recessed window (M_CSK_ScanWindow, "
                        "emissive), a raked pistol grip, a flat pill foot, a blue-grey trigger (M_CSK_AccentBlue)",
                        "Spec size 160 x 70 x 95 is read as a size: the long axis runs along Y (nose = -Y)"]},
    )


def _cradle_lod(level: int) -> Lod:
    """Sheet 26 panel 5: a tapered block on a plinth band, its top dipping in a saddle between two ears at the
    sides, a cup in the middle that the scanner's nose drops into."""
    c = CRADLE
    PLASTIC = 0
    bw, bd, br = c["base"]
    tw, td, tr = c["top"]
    H, ph, st = c["h"], c["plinth_h"], c["step"]
    segs = (2, 1, 1)[level]

    def ring(w, d, r):
        return rounded_rect(w, d, r, segs)
    b = Builder()
    if level == 0:                                      # plinth band, a step in, the taper, a rounded top edge
        er = c["ear_r"]
        z0 = ph + 0.8
        w0, d0, r0 = bw - 2 * st, bd - 2 * st, br - st

        def at(z, ins=0.0):
            f = (z - z0) / (H - z0)
            w, d, r = w0 + (tw - w0) * f, d0 + (td - d0) * f, r0 + (tr - r0) * f
            return ring(w - 2 * ins, d - 2 * ins, max(r - ins, 1.0))
        top = [(at(H - er + er * math.sin(math.radians(a)), er - er * math.cos(math.radians(a))),
                H - er + er * math.sin(math.radians(a))) for a in (0.0, 45.0, 90.0)]
        _loft(b, [(ring(bw, bd, br), 0.0), (ring(bw, bd, br), ph), (at(z0), z0)] + top, PLASTIC)
    elif level == 1:                                    # mid: the plinth band and the taper, a square top
        _loft(b, [(ring(bw, bd, br), 0.0), (ring(bw, bd, br), ph), (ring(tw, td, tr), H)], PLASTIC)
    else:
        _loft(b, [(ring(bw, bd, br), 0.0), (ring(tw, td, tr), H)], PLASTIC)
    ops = []
    dip = c["dip"]
    half = tw / 2 - 10.0                                   # the ears' inner edge
    R = (half * half + dip * dip) / (2 * dip)
    sad = Builder()
    _cyl_axis(sad, (0.0, 0.0, H - dip + R), (0.0, 1.0, 0.0), R, -bd, bd, (16, 10, 8)[level], PLASTIC)
    ops.append(("DIFFERENCE", sad))
    cw, cd, cr, cz = c["cup"]
    if level < 2:
        cup = Builder()
        _loft(cup, [(rounded_rect(cw, cd, cr, segs), cz), (rounded_rect(cw, cd, cr, segs), H + 5.0)], PLASTIC)
        ops.append(("DIFFERENCE", cup))
    return Lod(b, ops=ops)


def item_cradle() -> Item:
    c = CRADLE
    s = SCANNER
    bw, bd, _ = c["base"]
    H = c["h"]
    cz = c["cup"][3]
    nose = s["head"][-1][0]
    # the scanner parked nose-down in the cup, its grip toward the cradle's front: rot (90, 0, 180) sends the
    # scanner's -Y (nose) to -Z and its foot to -Y; the nose centre lands on the cup floor
    nose_c = (0.0, s["head_rear"] - nose, s["head_z"])
    loc = (0.0, -nose_c[2], cz - nose_c[1])
    return Item(
        name="SM_CSK_Scanner_Cradle", lods=[_cradle_lod(i) for i in range(3)], materials=["M_CSK_Plastic"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Scanner", loc, (90.0, 0.0, 180.0))],
        hulls=[((-bw / 2, -bd / 2, 0.0), (bw / 2, bd / 2, H - c["dip"]))], budget=BUDGETS["SM_CSK_Scanner_Cradle"],
        data={"footprint_mm": [bw, bd, H], "pose": "upright", "pivot": "bottom-centre", "part_of": "SM_CSK_Scanner",
              "reference": REF,
              "notes": ["Sheet 26 panel 5 shows the cradle beside the scanner, not in use: how the scanner sits in it "
                        "is E (nose down in the cup, grip toward the front)"]},
    )


# =========================================================================== G7 price labeller

def _strip_outline(centre, t: float):
    """A thin ribbon's (y, z) outline round a polyline (counter-clockwise)."""
    left, right = [], []
    n = len(centre)
    for i in range(n):
        a = centre[max(i - 1, 0)]
        c = centre[min(i + 1, n - 1)]
        dy, dz = c[0] - a[0], c[1] - a[1]
        ln = math.hypot(dy, dz)
        ny, nz = -dz / ln, dy / ln
        left.append((centre[i][0] + ny * t / 2, centre[i][1] + nz * t / 2))
        right.append((centre[i][0] - ny * t / 2, centre[i][1] - nz * t / 2))
    poly = right + list(reversed(left))
    return poly if _area(poly) > 0 else list(reversed(poly))


def _labeller_lod(level: int) -> Lod:
    """Sheet 26 panel 6: a body with the print head at the front (a proud frame with the red selector in a window
    at the top and the label exit below it), the label roll on top between two round-topped cover plates, a blue
    spool flange on the far side, a fixed handle raked back and a lower lever whose end hooks down to the counter,
    the label strip hanging from the exit."""
    g = LABELLER
    PLASTIC, PAPER, RED, BLUE = range(4)
    W = g["w"]
    ch = g["chamfer"] if level == 0 else 0.0
    b = Builder()
    _prism_x(b, list(g["body"]), -W / 2 + 0.6, W / 2 - 0.6, PLASTIC)    # the cover plates stand 0.6 proud of it
    ops = []
    nw, npr, nz0, nz1 = g["nose"]
    front = g["body"][0][0]
    nose = Builder()
    nose.box((-nw / 2, front - npr, nz0), (nw / 2, front + 2.0, nz1), mat=PLASTIC)
    ops.append(("UNION", nose))
    if level < 2:
        ww, wd, wz0, wz1 = g["window"]
        win = Builder()
        win.box((-ww / 2, front - npr - 1.0, wz0), (ww / 2, front - npr + wd, wz1), mat=PLASTIC)
        ops.append(("DIFFERENCE", win))
        ew, eh, ez = g["exit"]
        ex = Builder()
        ex.box((-ew / 2, front - npr - 1.0, ez - eh / 2), (ew / 2, front + 12.0, ez + eh / 2), mat=PLASTIC)
        ops.append(("DIFFERENCE", ex))
    e = Builder()
    pt = g["plate_t"]
    if level < 2:
        for sx in (-1, 1):                              # the roll cover plates, 0.6 proud of the body's sides
            xo, xi = sx * W / 2, sx * (W / 2 - pt)
            _chamfer_prism_x(e, list(g["plate"]), min(xo, xi), max(xo, xi), ch, PLASTIC)
    else:                                               # far: one full-width plate block
        _prism_x(e, list(g["plate"]), -W / 2, W / 2, PLASTIC)
    hw, lw = g["handle_w"], g["lever_w"]
    _chamfer_prism_x(e, list(g["handle"]), -hw / 2, hw / 2, (2.0 if level == 0 else 0.0), PLASTIC)
    _chamfer_prism_x(e, list(g["lever"]), -lw / 2, lw / 2, ch, PLASTIC)
    rr_, rw, (ry, rz) = g["roll"]
    _cyl_axis(e, (0.0, ry, rz), (1.0, 0.0, 0.0), rr_, -rw / 2, rw / 2, (18, 12, 6)[level], PAPER)
    hr, ht = g["hub"]
    if level < 2:
        _cyl_axis(e, (0.0, ry, rz), (1.0, 0.0, 0.0), hr, -rw / 2 - ht, -rw / 2 + 0.5, (18, 12)[level], BLUE,
                  caps=(True, False))
    if level < 2:
        sw_, sh_, sp = g["slider"]
        ww, wd, wz0, wz1 = g["window"]
        yw = front - npr + wd                            # the window's floor
        _box(e, (-sw_ / 2, yw - sp, (wz0 + wz1) / 2 - sh_ / 2), (sw_ / 2, yw + 0.5, (wz0 + wz1) / 2 + sh_ / 2), RED)
        st_w, st_t, line = g["strip"]
        _prism_x(e, _strip_outline(list(line), st_t), -st_w / 2, st_w / 2, PAPER)
    if level == 0:
        br, bp, (by, bz) = g["boss"]
        for sx in (-1.0, 1.0):
            _cyl_axis(e, (sx * (W / 2 - 0.6), by, bz), (sx, 0.0, 0.0), br, -0.5, bp, 10, PLASTIC, caps=(False, True))
        return Lod(b, bevel_mm=g["bevel"], bevel_segments=2, bevel_first=True, ops=ops, extra=e)
    return Lod(b, ops=ops, extra=e)


def item_price_gun() -> Item:
    g = LABELLER
    W = g["w"]
    front = g["body"][0][0]
    npr = g["nose"][1]
    ew, eh, ez = g["exit"]
    return Item(
        name="SM_CSK_PriceGun", lods=[_labeller_lod(i) for i in range(3)],
        materials=["M_CSK_Plastic", "M_CSK_Paper", "M_CSK_AccentRed", "M_CSK_AccentBlue"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)),
                 Socket("Grip", (0.0, 60.0, 90.0)),                                  # the fixed handle
                 Socket("LabelOut", (0.0, front - npr, ez), (90.0, 0.0, 0.0))],    # +Z out of the exit (-Y)
        hulls=[((-W / 2, -g["l"] / 2 - 18.0, 0.0), (W / 2, g["l"] / 2 + 3.0, g["h"] + 1.0))],
        budget=BUDGETS["SM_CSK_PriceGun"],
        data={"footprint_mm": [W, 193.0, 126.0], "pose": "upright (stands on its body and lever hook)",
              "pivot": "bottom-centre of the 190 body", "front": "-Y (print head, label exit)",
              "label_mm": [19.8, 11.2], "reference": REF,
              "notes": ["Sheet 26 panel 6: print head with the red selector, the label roll on top between round "
                        "cover plates with a blue spool flange, fixed handle, lower lever hooked down to the counter, "
                        "the label strip hanging to the counter (its red label borders are print, not modelled)",
                        "The hanging label strip adds 18 in front of the 190 body (render bounds)"]},
    )


# =========================================================================== G9 phone

def _phone_screen_rect():
    p = PHONE
    bs, bt = p["bezel"]
    return p["w"] - 2 * bs, p["l"] - 2 * bt


def _phone_lod(level: int) -> Lod:
    """Sheet 26 panel 7: a slab with rounded corners and rounded edges, a flush screen with a thin black bezel and a
    hole-punch camera near its top, two keys on the right edge."""
    p = PHONE
    PLASTIC, SCREEN = range(2)
    W, L, T = p["w"], p["l"], p["t"]
    sw, sh = _phone_screen_rect()
    b = Builder()
    if level == 2:
        _, top = b.prism(rect(W, L), 0.0, T, mat=PLASTIC, top=None)
        scr = [b.v(x, y, T) for x, y in rect(sw, sh)]
        b.fill([top, scr], PLASTIC, 0, (0, 0, 1))
        b.fill([scr], SCREEN, R_FRONT, (0, 0, 1))
        return Lod(b)
    segs = (4, 1)[level]
    rf, rb = p["edge"]
    rings = _round_rings(T, 0.0, rf, rb, 1, (2, 1)[level])
    _, top = _loft(b, [(_rr(W, L, p["r"], segs, ins), z) for ins, z in rings], PLASTIC, top=None)
    scr = b.loop(_rr(sw, sh, p["screen_r"], segs), T)
    b.fill([top, scr], PLASTIC, 0, (0, 0, 1))
    if level == 0:
        cr, cy = p["cam"]
        cam = b.loop(rounded_rect(2 * cr, 2 * cr, cr * 0.999, 2) if False else
                     [(cr * math.cos(2 * math.pi * k / 8), sh / 2 - cy + cr * math.sin(2 * math.pi * k / 8))
                      for k in range(8)], T)
        b.fill([scr, cam], SCREEN, R_FRONT, (0, 0, 1))
        b.fill([cam], PLASTIC, 0, (0, 0, 1))
        bp, bh = p["button"]
        for yc, ln in p["buttons"]:
            b.box((W / 2 - 1.0, yc - ln / 2, T / 2 - bh / 2), (W / 2 + bp, yc + ln / 2, T / 2 + bh / 2), mat=PLASTIC)
    else:
        b.fill([scr], SCREEN, R_FRONT, (0, 0, 1))
    return Lod(b)


def item_phone() -> Item:
    p = PHONE
    W, L, T = p["w"], p["l"], p["t"]
    sw, sh = _phone_screen_rect()
    return Item(
        name="SM_CSK_Phone", lods=[_phone_lod(i) for i in range(3)], materials=["M_CSK_Plastic", "M_CSK_Screen"],
        projections={R_FRONT: _planar(-sw / 2, -sh / 2, sw, sh)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0.0, -L / 2, T / 2)), Socket("Screen", (0.0, 0.0, T))],
        hulls=[((-W / 2, -L / 2, 0.0), (W / 2, L / 2, T))], budget=BUDGETS["SM_CSK_Phone"],
        data={"footprint_mm": [W, L, T], "pose": "lying on its back, screen up", "pivot": "bottom-centre",
              "top": "+Y (camera end)", "screen": {"slot": "M_CSK_Screen", "uv0": "0-1 tile", "size_mm": [sw, sh]},
              "reference": REF,
              "notes": ["Sheet 26 panel 7: thin bezel, hole-punch camera in the screen, two keys on the right edge; "
                        "the back is not drawn, so it is plain"]},
    )


# =========================================================================== G10 laptop + lid

def _lt_keys(level: int):
    """Keycap rects (x0, y0, x1, y1) on the well floor: the function row, then 5 rows at the unit pitch."""
    t = LAPTOP
    ww, wd, wy, _, _ = t["well"]
    g = t["key_gap"]
    m = 3.0                                          # the well margin round the keys
    x0, x1 = -ww / 2 + m, ww / 2 - m
    u = (x1 - x0 + g) / 15.0                         # one unit incl. its gap
    y_top = wy + wd - m
    keys = []
    fn = t["fn_h"]
    n = 14
    fw = (x1 - x0 + g) / n
    for i in range(n):
        keys.append((x0 + i * fw, y_top - fn, x0 + (i + 1) * fw - g, y_top))
    y = y_top - fn - g
    for row in t["rows"]:
        x = x0
        for k in row:
            if k == "UD":
                hh = (u - g - g / 2) / 2
                keys.append((x, y - hh, x + u - g, y))
                keys.append((x, y - u + g, x + u - g, y - u + g + hh))
                x += u
                continue
            keys.append((x, y - (u - g), x + k * u - g, y))
            x += k * u
        y -= u
    return keys


def _laptop_lod(level: int) -> Lod:
    """Sheet 26 panel 8: an aluminium base with rounded corners and edges, the keyboard well with its keycaps,
    the touchpad, the opening notch at the front and ports on the left side."""
    t = LAPTOP
    ALU, PLASTIC = range(2)
    W, D, Tb = t["w"], t["d"], t["base_t"]
    segs = (3, 2, 1)[level]
    b = Builder()
    rt, rb = t["base_edge"]
    rings = _round_rings(Tb, 0.0, rt, rb, (2, 1, 0)[level], (2, 1, 0)[level])
    _loft(b, [(_rr(W, D, t["r"], segs, ins), z) for ins, z in rings], ALU)
    ops = []
    ww, wd, wy, wdp, wr = t["well"]
    well = Builder()
    well.prism([(x, y + wy + wd / 2) for x, y in rounded_rect(ww, wd, wr, (2, 1, 1)[level])], Tb - wdp, Tb + 1.0,
               mat=PLASTIC)
    ops.append(("DIFFERENCE", well))
    if level < 2:
        pw, pd, py, pdp = t["pad"]
        pad = Builder()
        pad.prism([(x, y + py + pd / 2) for x, y in rounded_rect(pw, pd, 3.0, (2, 1)[level])], Tb - pdp, Tb + 1.0,
                  mat=ALU)
        ops.append(("DIFFERENCE", pad))
    if level == 0:
        nw, nd, ndp = t["notch"]
        notch = Builder()
        notch.box((-nw / 2, -D / 2 - 1.0, Tb - ndp), (nw / 2, -D / 2 + nd, Tb + 1.0), mat=ALU)
        ops.append(("DIFFERENCE", notch))
        for y, pw_, ph in t["ports"]:
            port = Builder()
            port.box((-W / 2 - 1.0, y - pw_ / 2, Tb / 2 - ph / 2), (-W / 2 + 6.0, y + pw_ / 2, Tb / 2 + ph / 2),
                     mat=PLASTIC)
            ops.append(("DIFFERENCE", port))
    e = Builder()
    zf = Tb - wdp
    fr = Frame((0.0, 0.0, zf), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    if level == 0:
        for x0, y0, x1, y1 in _lt_keys(level):
            _key(e, fr, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, t["key_t"], t["key_ins"], PLASTIC)
    elif level == 1:                                  # mid: the caps as flat tops (2 tris each) over the well floor
        for x0, y0, x1, y1 in _lt_keys(level):
            q = [e.v(x, y, zf + t["key_t"]) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            e.face(tuple(q), PLASTIC)
    return Lod(b, ops=ops, extra=e if level < 2 else None)


def item_laptop() -> Item:
    t = LAPTOP
    W, D, Tb, Tl = t["w"], t["d"], t["base_t"], t["lid_t"]
    hy, hz = D / 2 - Tl / 2, Tb + Tl / 2
    return Item(
        name="SM_CSK_Laptop", lods=[_laptop_lod(i) for i in range(3)], materials=["M_CSK_Aluminium", "M_CSK_Plastic"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Lid", (0.0, hy, hz)), Socket("Grip", (0.0, -D / 2, Tb / 2))],
        hulls=[((-W / 2, -D / 2, 0.0), (W / 2, D / 2, Tb))], budget=BUDGETS["SM_CSK_Laptop"],
        data={"footprint_mm": [W, D, t["h"]], "pose": "lying flat", "pivot": "bottom-centre",
              "front": "-Y (keyboard front edge); hinge at +Y",
              "parts": {"Lid": {"mesh": "SM_CSK_Laptop_Lid", "socket": "Lid", "type": "hinge", "axis": "X",
                                "range_deg": list(t["range_deg"]), "open_rot_deg": [t["open_deg"], 0.0, 0.0]}},
              "reference": REF,
              "notes": ["Sheet 26 panel 8: 78 keycaps in a recessed well, the touchpad, the opening notch, 3 ports "
                        "on the left side; the hinge axis runs along the rear edge at the lid's mid-thickness, and "
                        "the lid's rear edge is a full round about it, so it clears the base at every angle",
                        "Key legends are not modelled (print)"]},
    )


def _lid_screen_rect():
    t = LAPTOP
    W, D, Tl = t["w"], t["d"], t["lid_t"]
    bs, btop, bbot = t["bezel"]
    r = Tl / 2
    y_front, y_back = -D + r, 0.0                   # the flat face runs from the front round to the rear round
    return (-W / 2 + r + bs, y_front + btop, W / 2 - r - bs, y_back - bbot)


def _laptop_lid_lod(level: int) -> Lod:
    """The lid in its hinge frame (origin on the axis, closed; the lid covers y in [-D + Tl/2, Tl/2]): a slab
    whose edges are a full round (the rear edge rounds about the hinge axis), the screen flush in a thin black
    bezel on its inner face, the camera dot in the top bezel."""
    t = LAPTOP
    ALU, PLASTIC, SCREEN = range(3)
    W, D, Tl = t["w"], t["d"], t["lid_t"]
    r = Tl / 2
    cy = -D / 2 + r                                  # the plan centre (the lid spans D along y)
    sx0, sy0, sx1, sy1 = _lid_screen_rect()
    b = Builder()
    if level == 2:
        bot, _ = b.prism(rect(W, D, 0.0, cy), -r, r, mat=ALU, bottom=None)
        scr = [b.v(x, y, -r) for x, y in ((sx0, sy0), (sx0, sy1), (sx1, sy1), (sx1, sy0))]
        b.fill([bot, scr], PLASTIC, 0, (0, 0, -1))
        b.fill([scr], SCREEN, R_FRONT, (0, 0, -1))
        return Lod(b)
    segs = (3, 1)[level]
    angs = (-90.0, -45.0, 0.0, 45.0, 90.0) if level == 0 else (-90.0, 0.0, 90.0)
    rings = [(r - r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in angs]
    bot, _ = _loft(b, [(_rr(W, D, t["r"], segs, ins, 0.0, cy), z) for ins, z in rings], ALU, bottom=None)
    scr = b.loop([(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)], -r)
    if level == 0:
        cyc = (sy0 + (-D + r + r)) / 2 - 0.5         # centred in the top bezel
        cam = b.loop([(t["cam"] * math.cos(2 * math.pi * k / 8), cyc + t["cam"] * math.sin(2 * math.pi * k / 8))
                      for k in range(8)], -r)
        b.fill([bot, scr, cam], PLASTIC, 0, (0, 0, -1))
        b.fill([cam], SCREEN, 0, (0, 0, -1))
    else:
        b.fill([bot, scr], PLASTIC, 0, (0, 0, -1))
    b.fill([scr], SCREEN, R_FRONT, (0, 0, -1))
    return Lod(b)


def item_laptop_lid() -> Item:
    t = LAPTOP
    W, D, Tl = t["w"], t["d"], t["lid_t"]
    r = Tl / 2
    sx0, sy0, sx1, sy1 = _lid_screen_rect()

    def proj(x, y, z):                                # upright when the lid is open: u to +X, v up toward the free edge
        return (inset((x - sx0) / (sx1 - sx0)), inset((sy1 - y) / (sy1 - sy0)))
    return Item(
        name="SM_CSK_Laptop_Lid", lods=[_laptop_lid_lod(i) for i in range(3)],
        materials=["M_CSK_Aluminium", "M_CSK_Plastic", "M_CSK_Screen"], projections={R_FRONT: proj},
        sockets=[Socket("Seat", (0, 0, 0)),
                 Socket("Screen", ((sx0 + sx1) / 2, (sy0 + sy1) / 2, -r), (180.0, 0.0, 0.0))],   # +Z out of it
        hulls=[((-W / 2, -D + r, -r), (W / 2, r, r))], budget=BUDGETS["SM_CSK_Laptop_Lid"],
        data={"part_of": "SM_CSK_Laptop", "pivot": "hinge axis (X), closed pose",
              "open_rot_deg": [t["open_deg"], 0.0, 0.0],
              "screen": {"slot": "M_CSK_Screen", "uv0": "0-1 tile, upright when open",
                         "size_mm": [round(sx1 - sx0, 3), round(sy1 - sy0, 3)]},
              "reference": REF},
    )


ITEMS = {
    "g_devices_cash_drawer": item_cash_drawer,
    "g_devices_cash_drawer_tray": item_cash_drawer_tray,
    "g_devices_bills": item_bills_stack,
    "g_devices_coin": item_coin,
    "g_devices_terminal": item_terminal,
    "g_devices_printer": item_printer,
    "g_devices_printer_lid": item_printer_lid,
    "g_devices_pos": item_pos_screen,
    "g_devices_scanner": item_scanner,
    "g_devices_cradle": item_cradle,
    "g_devices_price_gun": item_price_gun,
    "g_devices_phone": item_phone,
    "g_devices_laptop": item_laptop,
    "g_devices_laptop_lid": item_laptop_lid,
}
