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
    bin=(380.0, 68.0),         # E: the tray bin W x H behind the panel (sheet 26: about 2/3 of the panel height)
    bin_back=-200.0,           # E: the bin's back face (y); the tray is 408.5 long
    wall=2.0,                  # E: bin / insert outer wall
    div=3.0,                   # E: insert dividers
    note_len=166.0,            # sheet 26: the note slots take ~45 % of the tray depth, at the back
    pocket_d=40.0,             # E: pocket depth below the insert top
    notes=5, coin_cols=4, coin_rows=2,   # counts 5 / 8 E* (spec, sheet 26 call-out "5 note slots, 8 coin cups")
    lock=(22.0, 3.5, 55.5),    # sheet 26: round chrome lock, centred on the front: diameter, proud, z (E)
    travel=280.0,              # E (spec)
    clip=(7.0, 1.2, 3.0),      # sheet 26: a wire U clip per note slot: half spacing of the wires, wire r, barrel r (E)
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
          top_mat: Optional[int] = None) -> None:
    """A box in the frame ``fr``: [u0, u1] x [v0, v1] x [w0, w1]; the +W face may take its own region / material."""
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
        if key == "+w":
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


ITEMS = {
    "g_devices_cash_drawer": item_cash_drawer,
    "g_devices_cash_drawer_tray": item_cash_drawer_tray,
    "g_devices_bills": item_bills_stack,
    "g_devices_coin": item_coin,
}
