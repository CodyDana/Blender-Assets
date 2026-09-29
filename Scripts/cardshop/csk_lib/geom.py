"""Parametric geometry for the G1 spike items (CARDSHOP_KIT_SPEC.md 3.A1, 3.B1-B2, 3.C1, 3.C5, 3.D1, 3.D3).

Each ``item_*`` function returns an ``Item``: per-LOD builders, material slot names, the print projections, the
sockets (in the item's Seat frame, mm and degrees), box hulls, and the kit data the ``.csk.json`` needs. No bpy here
except through ``mesh.Builder`` (pure data), so the numbers stay reviewable.

Print regions (UV0 tiles, spec 4.1): 1 = front (0,0), 2 = back (1,0), 3 = label (0,1); boxes use 10+ for the dieline
panels, all inside tile (0,0).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import spec as S
from .shapes import Builder, chamfer_rect, circle, rect, rounded_rect

Vec3 = Tuple[float, float, float]
R_FRONT, R_BACK, R_LABEL = 1, 2, 3
R_EDGE = 4          # 4..7: a pack's four sealed edges (U -1 tile bands)


@dataclass
class Socket:
    name: str
    loc: Vec3                      # mm, item frame
    rot: Vec3 = (0.0, 0.0, 0.0)    # degrees XYZ Euler, the orientation wanted in Unreal
    kind: str = "UTILITY"          # DISPLAY | CONTAIN | UTILITY (spec 4.2)


@dataclass
class Lod:
    builder: Builder
    bevel_mm: Optional[float] = None
    ops: List[Tuple[str, Builder]] = field(default_factory=list)     # booleans: ("DIFFERENCE" | "UNION", shell)
    bevel_segments: int = 1
    bevel_first: bool = False           # bevel the base shell before the booleans (crisp cut edges)


@dataclass
class Item:
    name: str
    lods: List[Lod]
    materials: List[str]
    projections: Dict[int, object]
    sockets: List[Socket] = field(default_factory=list)
    hulls: List[Tuple[Vec3, Vec3]] = field(default_factory=list)
    cls: Optional[str] = None
    data: Dict = field(default_factory=dict)     # extra .csk.json content (contain grids, levels, parts ...)
    budget: int = 0


def _planar(x0: float, y0: float, w: float, h: float, tile_u: float = 0.0, tile_v: float = 0.0,
            mirror_x: bool = False):
    """XY planar map of the rect (x0, y0, w, h) onto one 0-1 tile. ``mirror_x`` for faces seen from below."""
    def proj(x, y, z):
        u = (x - x0) / w
        if mirror_x:
            u = 1.0 - u
        return (tile_u + inset(u), tile_v + inset((y - y0) / h))
    return proj


UV_INSET = 0.001     # print UVs sit 0.1% inside their tile: floor() in the print master never picks a neighbour tile


def inset(t: float) -> float:
    return UV_INSET + t * (1.0 - 2.0 * UV_INSET)


# =========================================================================== C1 card

def item_card() -> Item:
    c = S.CARD_STD
    b = Builder()
    b.prism(rounded_rect(c["w"], c["h"], c["r"], c["corner_segs"]), 0.0, c["t"], top=R_FRONT, bottom=R_BACK)
    x0, y0 = -c["w"] / 2, -c["h"] / 2
    t = c["t"]
    pad = S.HANDHELD_HULL_MIN_T / 2
    return Item(
        name="SM_CSK_Card_Std", lods=[Lod(b)], materials=["M_CSK_Card"],
        projections={R_FRONT: _planar(x0, y0, c["w"], c["h"]),
                     R_BACK: _planar(x0, y0, c["w"], c["h"], tile_u=1.0, mirror_x=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Face", (0, 0, t)), Socket("Grip", (0, y0, t / 2))],
        hulls=[((x0, y0, t / 2 - pad), (-x0, -y0, t / 2 + pad))],      # padded to 2 mm, centred (spec 4.6)
        cls="Card", budget=S.BUDGETS["SM_CSK_Card_Std"],
        data={"footprint_mm": [c["w"], c["h"], t], "stack": {"socket": "Face", "pitch_mm": t, "max": 5}},
    )


# =========================================================================== C5 top-loader (reference sheet 2)

def _toploader_lod(s, level: int) -> Lod:
    """Rounded outer shell; the pocket and the thumb notch are boolean cuts (References/CardShop/csk_toploader.png)."""
    w, h, t, iw, ih, gap = s["w"], s["h"], s["t"], s["in_w"], s["in_h"], s["gap"]
    skin = (t - gap) / 2
    y_top, y_floor = h / 2, h / 2 - ih
    segs = (4, 2, 1)[level]
    b = Builder()
    b.prism(rounded_rect(w, h, s["corner_r"], segs) if level < 2 else rect(w, h), 0.0, t)
    pocket = Builder()
    pocket.box((-iw / 2, y_floor, skin), (iw / 2, y_top + 5.0, t - skin))
    ops = [("DIFFERENCE", pocket)]
    if level < 2:                                   # the thumb notch: through the front skin at the open end
        notch = Builder()
        hw, d = s["notch_w"] / 2, s["notch_d"]
        nr = (hw * hw + d * d) / (2 * d)            # the arc through the two edge points and the bottom point
        notch.prism(circle(nr, (20, 12)[level], 0.0, y_top + nr - d), t - skin - 0.2, t + 1.0)
        ops.append(("DIFFERENCE", notch))
    return Lod(b, bevel_mm=0.25 if level == 0 else None, ops=ops, bevel_segments=1, bevel_first=True)


def item_toploader(pt: str = "35pt") -> Item:
    s = dict(S.TOPLOADER_35, **(S.TOPLOADER_130 if pt == "130pt" else {}))
    w, h, t, iw, ih, gap = s["w"], s["h"], s["t"], s["in_w"], s["in_h"], s["gap"]
    skin = (t - gap) / 2
    y_top, y_floor = h / 2, h / 2 - ih
    name = f"SM_CSK_TopLoader_{pt}"
    card_seat = (0.0, y_floor + S.CARD_STD["h"] / 2, skin)
    return Item(
        name=name, lods=[_toploader_lod(s, k) for k in range(3)], materials=["M_CSK_PVC"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Card", card_seat, kind="CONTAIN"), Socket("Face", (0, 0, t)),
                 Socket("Grip", (0, -h / 2, t / 2)), Socket("Stack", (0, 0, t))],
        hulls=[((-w / 2, -h / 2, 0), (w / 2, h / 2, t))],
        cls="CardProt", budget=S.BUDGETS["SM_CSK_TopLoader_35pt"],
        data={"footprint_mm": [w, h, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 20},
              "contain": {"Card": {"socket": "Card", "cavity_mm": [[-iw / 2, y_floor, skin], [iw / 2, y_top, t - skin]],
                                   "accepts": ["Card"]}},
              "reference": "References/CardShop/csk_toploader.png (sheet 2)"},
    )


# =========================================================================== D1 / D3 slab

def _chamfer_inset(s, d: float):
    """The slab outline inset by ``d`` (45-degree chamfers shrink by 2 d tan 22.5)."""
    return chamfer_rect(s["w"] - 2 * d, s["h"] - 2 * d, max(0.2, s["chamfer"] - 2 * d * math.tan(math.pi / 8)))


def _slab_openings(s):
    lw, lh, lcy = s["label"]
    ww, wh, wcy = s["window"]
    return (-lw / 2, lcy - lh / 2, lw / 2, lcy + lh / 2), (-ww / 2, wcy - wh / 2, ww / 2, wcy + wh / 2)


def _slab_lod2(s, body: int, window: int, filled: bool) -> Builder:
    """Far LOD: the chamfered block, each face split into frame, label and window (or card print)."""
    w, h, t = s["w"], s["h"], s["t"]
    (lx0, ly0, lx1, ly1), (wx0, wy0, wx1, wy1) = _slab_openings(s)
    b = Builder()
    lb, lt = b.prism(chamfer_rect(w, h, s["chamfer"]), 0.0, t, mat=body, top=None, bottom=None)
    for z, loop, up in ((t, lt, True), (0.0, lb, False)):
        n = (0, 0, 1) if up else (0, 0, -1)
        lab = [b.v(x, y, z) for x, y in ((lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1))]
        win = [b.v(x, y, z) for x, y in ((wx0, wy0), (wx1, wy0), (wx1, wy1), (wx0, wy1))]
        b.fill([loop, lab, win], body, 0, n)
        b.face(tuple(lab) if up else tuple(reversed(lab)), body, R_LABEL if up else 0)
        if filled:                                  # the gasket ring round the card print
            cw, ch = S.CARD_STD["w"], S.CARD_STD["h"]
            card = [b.v(x, y, z) for x, y in rect(cw, ch, 0.0, (wy0 + wy1) / 2)]
            b.fill([win, card], body, 0, n)
            b.face(tuple(card) if up else tuple(reversed(card)), body, R_FRONT if up else R_BACK)
        else:
            b.face(tuple(win) if up else tuple(reversed(win)), window, 0)
    return b


def _slab_lod(s, level: int, body: int, window: int, filled: bool) -> Lod:
    """Reference sheet 3: an outer rim with a step inside it, a raised frame plateau with a label recess and a
    window recess separated by a cross bar, on the front and the back; stacking lugs on the long sides; the filled
    slab's window shows a white gasket ring round the card. All real geometry (booleans on a chamfered block)."""
    w, h, t = s["w"], s["h"], s["t"]
    if level == 2:
        return Lod(_slab_lod2(s, body, window, filled))
    (lx0, ly0, lx1, ly1), (wx0, wy0, wx1, wy1) = _slab_openings(s)
    b = Builder()
    b.prism(chamfer_rect(w, h, s["chamfer"]), 0.0, t, mat=body)
    ops = []
    rim, step, sd = s["rim"], s["step"], s["step_d"]
    for up in (True, False):
        zin = (lambda d: t - d) if up else (lambda d: d)        # a depth below the face, as a z
        zout = t + 1.0 if up else -1.0
        def cut(outline, depth, mat=body, region=0):
            c = Builder()
            z0, z1 = sorted((zin(depth), zout))
            floor = dict(bottom=region, bottom_mat=mat, top=0) if up else dict(top=region, top_mat=mat, bottom=0)
            c.prism(outline, z0, z1, mat=body, **floor)
            ops.append(("DIFFERENCE", c))
        if level == 0:                                  # the step ring: cut the field, then add the plateau back
            cut(_chamfer_inset(s, rim), sd)
            plateau = Builder()
            z0, z1 = sorted((zin(sd + 0.2), zin(0.0)))
            plateau.prism(_chamfer_inset(s, rim + step), z0, z1, mat=body)
            ops.append(("UNION", plateau))
        cut(rect(lx1 - lx0, ly1 - ly0, 0.0, (ly0 + ly1) / 2), s["label_d"], body, R_LABEL if up else 0)
        wrect = rect(wx1 - wx0, wy1 - wy0, 0.0, (wy0 + wy1) / 2)
        if filled:                                      # gasket ring (body) round the card print, 0.1 below it
            cut(wrect, s["window_d"], body, 0)
            cw, ch = S.CARD_STD["w"], S.CARD_STD["h"]
            cut(rect(cw, ch, 0.0, (wy0 + wy1) / 2), s["window_d"] + 0.1, body, R_FRONT if up else R_BACK)
        else:
            cut(wrect, s["window_d"], window, 0)
    if level == 0:
        seam = Builder()                            # the parting seam of the two welded shells: a 0.4 groove
        seam.prism(chamfer_rect(w + 2, h + 2, s["chamfer"] + 1), t / 2 - 0.25, t / 2 + 0.25)
        ops.append(("DIFFERENCE", seam))
        core = Builder()
        core.prism(_chamfer_inset(s, 0.4), t / 2 - 0.4, t / 2 + 0.4)
        ops.append(("UNION", core))
        ll, lz, lp, lyc = s["lug"]
        for sx in (-1, 1):
            for sy in (-1, 1):
                lug = Builder()
                x_in, x_out = sx * (w / 2 - 0.5), sx * (w / 2 + lp)
                lug.box((min(x_in, x_out), sy * lyc - ll / 2, t / 2 - lz / 2),
                        (max(x_in, x_out), sy * lyc + ll / 2, t / 2 + lz / 2), mat=body)
                ops.append(("UNION", lug))
    return Lod(b, bevel_mm=0.3 if level == 0 else None, ops=ops, bevel_segments=1, bevel_first=True)


def _slab_item(filled: bool) -> Item:
    s = S.SLAB_STD
    w, h, t = s["w"], s["h"], s["t"]
    (lx0, ly0, lx1, ly1), (wx0, wy0, wx1, wy1) = _slab_openings(s)
    wcy = (wy0 + wy1) / 2
    ww, wh, wd = s["well"]
    zf = s["well_floor_z"]
    body, window = 0, (0 if filled else 1)
    lods = [_slab_lod(s, k, body, window, filled) for k in range(3)]
    if not filled:              # LOD0: the card well, a sealed cavity (faces point inward)
        lods[0].builder.box((-ww / 2, wcy - wh / 2, zf), (ww / 2, wcy + wh / 2, zf + wd), mat=body, inward=True,
                            mats={"pz": window, "nz": window})
    cw, ch = S.CARD_STD["w"], S.CARD_STD["h"]
    name = "SM_CSK_Slab_Std_Filled" if filled else "SM_CSK_Slab_Std"
    x_lug = w / 2 + s["lug"][2]
    sockets = [Socket("Seat", (0, 0, 0)), Socket("Label", (0, (ly0 + ly1) / 2, t - s["label_d"])),
               Socket("Face", (0, 0, t)), Socket("Grip", (0, -h / 2, t / 2)), Socket("Stack", (0, 0, t))]
    data = {"footprint_mm": [2 * x_lug, h, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 10},
            "label_rect_mm": [lx0, ly0, lx1 - lx0, ly1 - ly0],
            "reference": "References/CardShop/csk_slab.png (sheet 3)",
            "notes": ["Sheet 3: stepped rim, label and window recesses, side stacking lugs (0.5 proud, so the "
                      "render width is 85.0). The lugs' matching recesses are not modelled (not visible)."]}
    if not filled:
        sockets.insert(1, Socket("Card", (0, wcy, zf), kind="CONTAIN"))
        data["contain"] = {"Card": {"socket": "Card", "cavity_mm": [[-ww / 2, wcy - wh / 2, zf],
                                                                    [ww / 2, wcy + wh / 2, zf + wd]],
                                    "accepts": ["Card"]}}
    return Item(
        name=name, lods=lods,
        materials=["M_CSK_SlabFilled"] if filled else ["M_CSK_SlabBody", "M_CSK_SlabWindow"],
        projections={R_LABEL: _planar(lx0, ly0, lx1 - lx0, ly1 - ly0, tile_v=1.0),
                     R_FRONT: _planar(-cw / 2, wcy - ch / 2, cw, ch),
                     R_BACK: _planar(-cw / 2, wcy - ch / 2, cw, ch, tile_u=1.0, mirror_x=True)},
        sockets=sockets, hulls=[((-w / 2, -h / 2, 0), (w / 2, h / 2, t))], cls="Slab",
        budget=S.BUDGETS[name], data=data,
    )


def item_slab() -> Item:
    return _slab_item(filled=False)


def item_slab_filled() -> Item:
    return _slab_item(filled=True)


# =========================================================================== B1 pack (sealed)

def _pack_builder(nx: int, ny: int, teeth: int) -> Builder:
    p = S.PACK_STD
    w, h, t, et, cr = p["w"], p["h"], p["t"], p["edge_t"], p["crimp"]
    b = Builder()
    # rows in Y: crimp band (flat, et thick) | body (pillow) | crimp band; columns in X across the width
    body_y0, body_y1 = -h / 2 + cr, h / 2 - cr
    ys = [-h / 2, body_y0] + [body_y0 + (body_y1 - body_y0) * j / ny for j in range(1, ny)] + [body_y1, h / 2]
    xs = [-w / 2 + w * i / nx for i in range(nx + 1)]

    def height(x, y):
        if y <= body_y0 or y >= body_y1:
            return et
        fx = 1.0 - abs(2 * x / w) ** 3
        fy = 1.0 - abs((2 * y - (body_y0 + body_y1)) / (body_y1 - body_y0)) ** 4
        return et + (t - et) * max(0.0, fx) * max(0.0, fy)

    tooth = min(1.2, cr * 0.2)
    top, bot = [], []
    for j, y in enumerate(ys):
        rt, rb = [], []
        for i, x in enumerate(xs):
            yy = y
            if j in (0, len(ys) - 1) and teeth:      # serrated ends: every other point pulled in by one tooth
                if (i % 2) == 1:
                    yy = y + (tooth if j == 0 else -tooth)
            rt.append(b.v(x, yy, height(x, yy)))
            on_rim = j in (0, len(ys) - 1) or i in (0, len(xs) - 1)
            rb.append(b.v(x, yy, 0.0) if on_rim else None)     # the flat bottom only needs its rim
        top.append(rt)
        bot.append(rb)
    nyr = len(ys) - 1
    for j in range(nyr):
        for i in range(nx):
            b.face((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), 0, R_FRONT)
    # the flat bottom as one filled face (the back print)
    ring = [bot[0][i] for i in range(nx + 1)] + [bot[j][nx] for j in range(1, nyr + 1)] + \
           [bot[nyr][i] for i in range(nx - 1, -1, -1)] + [bot[j][0] for j in range(nyr - 1, 0, -1)]
    b.fill([ring], 0, R_BACK, (0, 0, -1))
    # edges: top rim to bottom rim all round (thin sealed edge)
    for i in range(nx):
        b.face((bot[0][i], bot[0][i + 1], top[0][i + 1], top[0][i]), 0, R_EDGE)
        b.face((bot[nyr][i + 1], bot[nyr][i], top[nyr][i], top[nyr][i + 1]), 0, R_EDGE + 2)
    for j in range(nyr):
        b.face((bot[j + 1][0], bot[j][0], top[j][0], top[j + 1][0]), 0, R_EDGE + 3)
        b.face((bot[j][nx], bot[j + 1][nx], top[j + 1][nx], top[j][nx]), 0, R_EDGE + 1)
    return b


def _pack_edge_projections(w: float, h: float, t: float):
    """The thin sealed edges: each side its own band in the U -1..0 tile (smart project collapses 0.3 mm strips
    to zero width, which Unreal's tangent build warns about)."""
    def band(k, along):
        return lambda x, y, z: (-0.99 + 0.245 * k + 0.235 * along(x, y), 0.02 + 0.2 * z / t)
    return {R_EDGE: band(0, lambda x, y: (x + w / 2) / w), R_EDGE + 1: band(1, lambda x, y: (y + h / 2) / h),
            R_EDGE + 2: band(2, lambda x, y: (w / 2 - x) / w), R_EDGE + 3: band(3, lambda x, y: (h / 2 - y) / h)}


def item_pack() -> Item:
    p = S.PACK_STD
    w, h, t = p["w"], p["h"], p["t"]
    lods = [Lod(_pack_builder(10, 6, p["teeth"])), Lod(_pack_builder(6, 3, 6)), Lod(_pack_builder(2, 2, 0))]
    return Item(
        name="SM_CSK_Pack_Std_Sealed", lods=lods, materials=["M_CSK_Pack"],
        projections={R_FRONT: _planar(-w / 2, -h / 2, w, h),
                     R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0, mirror_x=True),
                     **_pack_edge_projections(w, h, t)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, -h / 2, t / 2)), Socket("Face", (0, 0, t)),
                 Socket("CardsOut", (0, h / 2, t / 2), (-90.0, 0.0, 0.0)), Socket("Stack", (0, 0, t))],
        hulls=[((-w / 2, -h / 2, 0), (w / 2, h / 2, t))], cls="Pack", budget=S.BUDGETS["SM_CSK_Pack_Std_Sealed"],
        data={"footprint_mm": [w, h, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 10},
              "states": ["Sealed"], "notes": ["G1: Open / Wrapper / Strip states and the back fin seal come in P3"]},
    )


# =========================================================================== B2 booster box S (+ lid)

def _dieline(s):
    """Dieline (spec 3.B, S: 440 x 285 mm): front | right | back | left in a 125-high row, the bottom panel under the
    front, the lid flap over the back. Returns the per-panel planar maps (region -> projection)."""
    W, D, H = s["w"], s["d"], s["h"]
    U, V = 2 * (W + D), H + 2 * D
    def m(fu, fv):
        return lambda x, y, z: (inset(fu(x, y, z) / U), inset(fv(x, y, z) / V))
    return {
        10: m(lambda x, y, z: x + W / 2, lambda x, y, z: D + z),                    # front (-Y)
        11: m(lambda x, y, z: W + (y + D / 2), lambda x, y, z: D + z),              # right (+X)
        12: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: D + z),          # back (+Y)
        13: m(lambda x, y, z: 2 * W + D + (D / 2 - y), lambda x, y, z: D + z),      # left (-X)
        14: m(lambda x, y, z: x + W / 2, lambda x, y, z: D - (y + D / 2)),          # bottom, under the front
        15: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: D + H + (D / 2 - y)),  # lid top (body y; hinge +D/2)
    }, (U, V)


def _box_body(s, level: int) -> Builder:
    W, D, H, bd = s["w"], s["d"], s["h"], s["board"]
    b = Builder()
    PRINT, BOARD = 0, 1
    if level == 2:
        b.box((-W / 2, -D / 2, 0), (W / 2, D / 2, H), mat=PRINT,
              regions={"ny": 10, "px": 11, "py": 12, "nx": 13, "nz": 14}, mats={"pz": BOARD})
        return b
    o = [b.v(-W / 2, -D / 2, 0), b.v(W / 2, -D / 2, 0), b.v(W / 2, D / 2, 0), b.v(-W / 2, D / 2, 0),
         b.v(-W / 2, -D / 2, H), b.v(W / 2, -D / 2, H), b.v(W / 2, D / 2, H), b.v(-W / 2, D / 2, H)]
    b.face((o[0], o[3], o[2], o[1]), PRINT, 14)
    b.face((o[0], o[1], o[5], o[4]), PRINT, 10)
    b.face((o[1], o[2], o[6], o[5]), PRINT, 11)
    b.face((o[2], o[3], o[7], o[6]), PRINT, 12)
    b.face((o[3], o[0], o[4], o[7]), PRINT, 13)
    it = [b.v(-W / 2 + bd, -D / 2 + bd, H), b.v(W / 2 - bd, -D / 2 + bd, H), b.v(W / 2 - bd, D / 2 - bd, H),
          b.v(-W / 2 + bd, D / 2 - bd, H)]
    ot = [o[4], o[5], o[6], o[7]]
    for k in range(4):                      # the rim (board edge), facing up
        b.face((ot[k], ot[(k + 1) % 4], it[(k + 1) % 4], it[k]), BOARD)
    ib = [b.v(-W / 2 + bd, -D / 2 + bd, bd), b.v(W / 2 - bd, -D / 2 + bd, bd), b.v(W / 2 - bd, D / 2 - bd, bd),
          b.v(-W / 2 + bd, D / 2 - bd, bd)]
    for k in range(4):                      # inner walls face into the box
        b.face((it[k], it[(k + 1) % 4], ib[(k + 1) % 4], ib[k]), BOARD)
    b.face((ib[0], ib[1], ib[2], ib[3]), BOARD)   # inner floor, facing up
    return b


def item_box_booster() -> Item:
    s = S.BOX_BOOSTER_S
    W, D, H, bd = s["w"], s["d"], s["h"], s["board"]
    proj, _uv_size = _dieline(s)
    lods = [Lod(_box_body(s, 0), bevel_mm=0.5), Lod(_box_body(s, 1)), Lod(_box_body(s, 2))]
    # packs standing: 2 across x 18 deep at 4 pitch; a pack's Seat frame turned +90 deg about X (its length up,
    # its face toward the customer), so it fills y in [s_y - 4, s_y]
    pk = S.PACK_STD
    cols, rows = s["packs"]
    pitch = s["pack_pitch"]
    inner_x, inner_y0 = W / 2 - bd, -D / 2 + bd
    sockets = [Socket("Seat", (0, 0, 0))]
    n = 0
    for r in range(rows):
        for c in range(cols):
            n += 1
            x = (c - (cols - 1) / 2) * pk["w"]
            y = inner_y0 + pitch * (r + 1)
            sockets.append(Socket(f"Pack_{n:02d}", (x, y, bd + pk["h"] / 2), (90.0, 0.0, 0.0), "CONTAIN"))
    sockets += [Socket("Lid", (0, D / 2, H)), Socket("Grip", (0, -D / 2, H / 2)),
                Socket("Face", (0, -D / 2, H / 2), (90.0, 0.0, 0.0)), Socket("Stack", (0, 0, H))]
    return Item(
        name="SM_CSK_Box_Booster_S", lods=lods, materials=["M_CSK_BoxPrint", "M_CSK_Board"], projections=proj,
        sockets=sockets, hulls=[((-W / 2, -D / 2, 0), (W / 2, D / 2, H))], cls="BoxS",
        budget=S.BUDGETS["SM_CSK_Box_Booster_S"],
        data={"footprint_mm": [W, D, H], "stack": {"socket": "Stack", "pitch_mm": H, "max": 4},
              "contain": {"Pack": {"sockets": [f"Pack_{i:02d}" for i in range(1, n + 1)],
                                   "cavity_mm": [[-inner_x, inner_y0, bd], [inner_x, D / 2 - bd, H]],
                                   "accepts": ["Pack"], "pose": "standing, +90 deg about X"}},
              "parts": {"Lid": {"mesh": "SM_CSK_Box_Booster_S_Lid", "socket": "Lid", "type": "hinge",
                                "axis": "X", "range_deg": [0, 200], "open_rot_deg": [-160.0, 0.0, 0.0]}},
              "dieline_mm": list(_uv_size)},
    )


def item_box_lid() -> Item:
    s = S.BOX_BOOSTER_S
    W, D, bd = s["w"], s["d"], s["board"]
    proj, _ = _dieline(s)
    b = Builder()
    # hinge frame: origin on the hinge axis at the rear top edge; closed, the lid covers y in [-D, 0]
    b.box((-W / 2, -D, 0), (W / 2, 0, bd), mat=0, regions={"pz": 15}, mats={"nz": 1, "ny": 1, "px": 1, "nx": 1,
                                                                             "py": 1})
    lid_proj = {15: (lambda f: (lambda x, y, z: f(x, y + D / 2, z)))(proj[15])}
    return Item(
        name="SM_CSK_Box_Booster_S_Lid", lods=[Lod(b)], materials=["M_CSK_BoxPrint", "M_CSK_Board"],
        projections=lid_proj, sockets=[Socket("Seat", (0, 0, 0))], hulls=[((-W / 2, -D, 0), (W / 2, 0, bd))],
        budget=S.BUDGETS["SM_CSK_Box_Booster_S_Lid"], data={"part_of": "SM_CSK_Box_Booster_S", "pivot": "hinge axis"},
    )


# =========================================================================== A1 showcase (1778) + glass + door

def _showcase_dims(L: float):
    s = S.SHOWCASE_FULL
    d, H, g, kick, deck, post, rail = s["d"], s["h"], s["glass"], s["kick"], s["deck"], s["post"], s["rail"]
    deck_top = kick + deck
    top_under = H - rail                         # underside of the top rails / top glass bearing
    x_in = L / 2 - post                          # inner face of the posts
    y_front_in = -d / 2 + post / 2 + g / 2        # inside face of the front glass (glass centred on the post line)
    track_d = s["track"][1]
    y_track_front = d / 2 - post / 2 - track_d    # front face of the rear door tracks
    return dict(d=d, H=H, g=g, kick=kick, deck_top=deck_top, top_under=top_under, x_in=x_in, post=post, rail=rail,
                y_front_in=y_front_in, y_track_front=y_track_front)


def _levels(L: float):
    """(name, z floor, y0, y1, clear height) for Deck, S1, S2 (mm, showcase frame)."""
    s = S.SHOWCASE_FULL
    k = _showcase_dims(L)
    g = k["g"]
    (d1, gap1), (d2, gap2) = s["shelves"]
    z_s1 = k["deck_top"] + gap1                  # S1 glass bottom
    z_s2 = z_s1 + g + gap2
    top_clear = k["top_under"] - 5.0             # the LED strip hangs 5 below the top
    y0 = k["y_front_in"]
    return [
        ("Deck", k["deck_top"], y0, k["y_track_front"], z_s1 - k["deck_top"]),
        ("S1", z_s1 + g, y0, y0 + d1, z_s2 - (z_s1 + g)),
        ("S2", z_s2 + g, y0, y0 + d2, top_clear - (z_s2 + g)),
    ]


def solve_grid(width: float, depth: float, clear_h: float, cls: str) -> Optional[Dict]:
    c = S.CLASSES[cls]
    px, py = c.pitch
    if c.footprint[2] > clear_h:
        return None
    cols = int((width - 2 * S.GRID_MARGIN) // px)
    rows = int((depth - 2 * S.GRID_MARGIN) // py)
    if cols < 1 or rows < 1:
        return None
    return {"class": cls, "cols": cols, "rows": rows, "pitch_mm": [px, py],
            "first_mm": [-(cols - 1) * px / 2, -(rows - 1) * py / 2]}


def _showcase_body(L: float, level: int) -> Builder:
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    d, H, post, rail = k["d"], k["H"], k["post"], k["rail"]
    FRAME, BASE, LED = 0, 1, 2
    b = Builder()
    b.box((-L / 2, -d / 2, 0), (L / 2, d / 2, s["kick"]), mat=BASE)                        # kick base
    b.box((-k["x_in"], -d / 2 + post, s["kick"] - 0.5), (k["x_in"], d / 2 - post, k["deck_top"]), mat=BASE)  # deck
    px, py = L / 2 - post / 2, d / 2 - post / 2
    for sx in (-1, 1):                                                                    # corner posts
        for sy in (-1, 1):
            b.box((sx * px - post / 2, sy * py - post / 2, s["kick"] - 1.0), (sx * px + post / 2, sy * py + post / 2, H),
                  mat=FRAME)
    if level < 2:
        inset = (post - rail) / 2
        zr0, zr1 = H - rail - inset, H - inset
        for sy in (-1, 1):                                                                # top rails along X
            b.box((-px - 5.0, sy * py - rail / 2, zr0), (px + 5.0, sy * py + rail / 2, zr1), mat=FRAME)
        for sx in (-1, 1):                                                                # top rails along Y
            b.box((sx * px - rail / 2, -py - 5.0, zr0), (sx * px + rail / 2, py + 5.0, zr1), mat=FRAME)
        th, td = s["track"]
        yt0 = k["y_track_front"]
        b.box((-k["x_in"] - 2.0, yt0, k["deck_top"]), (k["x_in"] + 2.0, yt0 + td, k["deck_top"] + th), mat=FRAME)
        b.box((-k["x_in"] - 2.0, yt0, zr0 - th), (k["x_in"] + 2.0, yt0 + td, zr0), mat=FRAME)
        b.box((-k["x_in"] + 10.0, k["y_front_in"] + 5.0, k["top_under"] - 5.0),
              (k["x_in"] - 10.0, k["y_front_in"] + 15.0, k["top_under"] - 1.0), mat=LED)      # LED strip
    return b


def item_showcase(L: float = 1778.0) -> Item:
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    d, H, post = k["d"], k["H"], k["post"]
    lods = [Lod(_showcase_body(L, 0), bevel_mm=1.0), Lod(_showcase_body(L, 1)), Lod(_showcase_body(L, 2))]
    sockets = [Socket("Seat", (0, 0, 0))]
    levels = []
    for name, z, y0, y1, clear in _levels(L):
        width = 2 * k["x_in"]
        yc = (y0 + y1) / 2
        sockets.append(Socket(f"Level_{name}", (0, yc, z), kind="DISPLAY"))
        comp_w = width / 4
        for i in range(4):
            cx = -width / 2 + comp_w * (i + 0.5)
            sockets.append(Socket(f"Compartment_{name}_{i + 1:02d}", (cx, yc, z), kind="DISPLAY"))
            sockets.append(Socket(f"PriceTag_{name}_{i + 1:02d}", (cx, y0 + 2.0, z), kind="DISPLAY"))
        grids = [g for g in (solve_grid(width, y1 - y0, clear, c) for c in S.SHOWCASE_ACCEPTS) if g]
        levels.append({"socket": f"Level_{name}", "interior_mm": [round(width, 3), round(y1 - y0, 3)],
                       "clear_h_mm": round(clear, 3), "compartments": 4, "grids": grids})
    door_w = L / 2 + s["door_overlap"]
    th, td = s["track"]
    yt0 = k["y_track_front"]
    door_z = k["deck_top"] + th
    for side, sx, ty in (("L", -1, yt0 + td * 0.3), ("R", 1, yt0 + td * 0.7)):
        cx = sx * (k["x_in"] - door_w / 2)
        sockets.append(Socket(f"Door_{side}", (cx, ty, door_z)))
    sockets += [Socket("LED", (0, k["y_front_in"] + 10.0, k["top_under"] - 5.0), (180.0, 0.0, 0.0)),
                Socket("Snap_L", (-L / 2, 0, 0)), Socket("Snap_R", (L / 2, 0, 0))]
    travel = L / 2 - s["door_travel_off"]
    return Item(
        name=f"SM_CSK_Showcase_Full_{int(L)}", lods=lods, materials=["M_CSK_Frame", "M_CSK_Base", "M_CSK_LED"],
        projections={}, sockets=sockets,
        hulls=[((-L / 2, -d / 2, 0), (L / 2, d / 2, k["deck_top"])),
               ((-L / 2, -d / 2, H - post), (L / 2, d / 2, H))],
        budget=S.BUDGETS["SM_CSK_Showcase_Full_1778"],
        data={"footprint_mm": [L, d, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(S.SHOWCASE_ACCEPTS), "levels": levels,
              "parts": {"Door_L": {"mesh": f"SM_CSK_Showcase_Full_Door_{int(L)}", "socket": "Door_L", "type": "slide",
                                   "axis": "X", "range_mm": [0, travel]},
                        "Door_R": {"mesh": f"SM_CSK_Showcase_Full_Door_{int(L)}", "socket": "Door_R", "type": "slide",
                                   "axis": "-X", "range_mm": [0, travel]}},
              "glass": f"SM_CSK_Showcase_Full_Glass_{int(L)}"},
    )


def item_showcase_glass(L: float = 1778.0) -> Item:
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    g, d = k["g"], k["d"]
    b = Builder()
    panes = []
    yf = -d / 2 + k["post"] / 2 - g / 2
    zt = k["top_under"]
    panes.append(((-k["x_in"], yf, k["deck_top"]), (k["x_in"], yf + g, zt)))                       # front
    for sx in (-1, 1):                                                                               # ends
        xo = sx * (L / 2 - k["post"] / 2)
        panes.append(((min(xo - sx * g / 2, xo + sx * g / 2), -d / 2 + k["post"], k["deck_top"]),
                      (max(xo - sx * g / 2, xo + sx * g / 2), d / 2 - k["post"], zt)))
    panes.append(((-k["x_in"], -d / 2 + k["post"], zt + 2.0), (k["x_in"], d / 2 - k["post"], zt + 2.0 + g)))  # top
    lv = _levels(L)
    for (name, z, y0, y1, clear), (depth, _gap) in zip(lv[1:], s["shelves"]):                         # shelves
        panes.append(((-k["x_in"] + 1.0, y0, z - g), (k["x_in"] - 1.0, y0 + depth, z)))
    for mn, mx in panes:
        b.box(mn, mx, mat=0)
    return Item(name=f"SM_CSK_Showcase_Full_Glass_{int(L)}", lods=[Lod(b)], materials=["M_CSK_Glass"],
                projections={}, sockets=[], hulls=panes, budget=S.BUDGETS["SM_CSK_Showcase_Full_Glass_1778"],
                data={"part_of": f"SM_CSK_Showcase_Full_{int(L)}", "attach": "same transform as the body"})


def item_showcase_door(L: float = 1778.0) -> Item:
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    g, st = k["g"], s["stile"]
    w = L / 2 + s["door_overlap"]
    h = (k["top_under"] - s["track"][0]) - (k["deck_top"] + s["track"][0]) - 4.0
    b = Builder()
    b.box((-w / 2 + st, -g / 2, 0), (w / 2 - st, g / 2, h), mat=0)                    # glass leaf
    for sx in (-1, 1):                                                                  # edge stiles
        b.box((sx * (w / 2 - st / 2) - st / 2, -g / 2 - 1.5, 0), (sx * (w / 2 - st / 2) + st / 2, g / 2 + 1.5, h),
              mat=1)
    return Item(name=f"SM_CSK_Showcase_Full_Door_{int(L)}", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Frame"],
                projections={}, sockets=[Socket("Grip", (w / 2 - st / 2, 0, h / 2))],
                hulls=[((-w / 2, -g / 2 - 1.5, 0), (w / 2, g / 2 + 1.5, h))],
                budget=S.BUDGETS["SM_CSK_Showcase_Full_Door_1778"],
                data={"part_of": f"SM_CSK_Showcase_Full_{int(L)}", "pivot": "bottom-centre at the closed position",
                      "size_mm": [w, g, h]})


ALL_ITEMS = {
    "card": item_card, "toploader": item_toploader, "toploader_130": lambda: item_toploader("130pt"), "slab": item_slab, "slab_filled": item_slab_filled,
    "pack": item_pack, "box": item_box_booster, "box_lid": item_box_lid, "showcase": item_showcase,
    "showcase_glass": item_showcase_glass, "showcase_door": item_showcase_door,
}
