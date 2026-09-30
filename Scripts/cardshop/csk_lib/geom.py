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
    extra: Optional[Builder] = None     # small parts joined after the bevel and booleans (kept crisp, no cuts)


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


def add_slab_well(lod: Lod, s, body: int, window: int) -> None:
    """LOD0's card well, a sealed cavity with window-material floor and ceiling. It is cut as the LAST boolean: the
    parting-seam core that LOD0 unions back in (z t/2 +- 0.4) would otherwise refill the well, burying the card in
    opaque body (seen in Unreal 2026-09-29: cards vanished close up, where LOD0 shows)."""
    (_l, (_wx0, wy0, _wx1, wy1)) = _slab_openings(s)
    wcy = (wy0 + wy1) / 2
    ww, wh, wd = s["well"]
    zf = s["well_floor_z"]
    well = Builder()
    well.box((-ww / 2, wcy - wh / 2, zf), (ww / 2, wcy + wh / 2, zf + wd), mat=body, mats={"pz": window, "nz": window})
    lod.ops = list(lod.ops) + [("DIFFERENCE", well)]


def _slab_item(filled: bool) -> Item:
    s = S.SLAB_STD
    w, h, t = s["w"], s["h"], s["t"]
    (lx0, ly0, lx1, ly1), (wx0, wy0, wx1, wy1) = _slab_openings(s)
    wcy = (wy0 + wy1) / 2
    ww, wh, wd = s["well"]
    zf = s["well_floor_z"]
    body, window = 0, (0 if filled else 1)
    lods = [_slab_lod(s, k, body, window, filled) for k in range(3)]
    if not filled:
        add_slab_well(lods[0], s, body, window)
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

def _pack_builder(cols: List[int], vfr: List[float], teeth: bool, ribs: bool, fin: bool,
                  n_teeth: Optional[int] = None) -> Builder:
    """Reference sheet 4: a lens-shaped pillow (both faces domed) with a flat crimp on the mid-plane at both short ends:
    27 serrated teeth, one pressed rib per tooth, a 1.9 flat seal strip; a raised fin seal down the back centre.

    The crimp line has 2 * teeth + 1 points (k = 0..2n, x = -w/2 + w k / 2n; tips at odd k). ``cols`` are the k
    indices the pillow's columns use (a subset, so the rows join without T-junction gaps); ``vfr`` the pillow's row
    fractions 0..1 between the two seal strips."""
    p = S.PACK_STD
    w, h, t, et = p["w"], p["h"], p["t"], p["edge_t"]
    n2 = 2 * (n_teeth or p["teeth"])          # a far LOD may use fewer, larger teeth
    fk0, fk1, fw0, fw1, fin_h = p["fin"]
    hb = (t - fin_h) / 2                        # the pillow's half thickness
    zm = hb + fin_h                             # the crimp mid-plane (lowest point = the fin at z 0)
    ys = h / 2 - p["crimp"]                     # pillow ends / seal strip start
    yj = ys + p["seal"]                         # ribbed band start
    b = Builder()
    xk = lambda k: -w / 2 + w * k / n2

    def half(x, y):
        fx = max(0.0, 1.0 - abs(2 * x / w) ** 4)
        fy = max(0.0, 1.0 - abs(y / ys) ** 4)
        return et / 2 + (hb - et / 2) * fx * fy

    def fin_off(k, y):
        if not fin or abs(y) >= ys - 1e-9:
            return 0.0
        return fin_h if fk0 <= k <= fk1 else 0.0

    # rows: (y per k, z-offset per k, columns); built from -y to +y
    crimp_cols = list(range(n2 + 1)) if teeth else cols
    def edge_row(sign):
        ys_ = {k: sign * (h / 2 - (0.0 if (k % 2 == 1 or not teeth) else p["tooth_d"])) for k in crimp_cols}
        cz = {k: ((p["rib"] if k % 2 == 1 else -p["rib"]) if ribs else 0.0) for k in crimp_cols}
        return crimp_cols, ys_, cz
    rib_z = edge_row(1)[2]                      # the pleats run the full ribbed band; they rise inside the seal strip
    rows = [edge_row(-1), (crimp_cols, {k: -yj for k in crimp_cols}, rib_z)]
    for f in vfr:
        y = -ys + 2 * ys * f
        rows.append((cols, {k: y for k in cols}, None))
    rows += [(crimp_cols, {k: yj for k in crimp_cols}, rib_z), edge_row(1)]

    top, bot = [], []
    for ks, yk, cz in rows:
        rt, rb = {}, {}
        for k in ks:
            x, y = xk(k), yk[k]
            c = cz[k] if cz else 0.0
            hh = half(x, y) if abs(y) < ys - 1e-9 else et / 2
            rt[k] = b.v(x, y, zm + hh + c)
            rb[k] = b.v(x, y, zm - hh + c - fin_off(k, y))
        top.append((ks, rt))
        bot.append((ks, rb))

    def strip(ra, rb_, region, up):
        """Faces between row a (lower y) and row b; columns may differ (one a subset of the other)."""
        (ka, va), (kb, vb) = ra, rb_
        coarse = ka if len(ka) <= len(kb) else kb
        for c0, c1 in zip(coarse[:-1], coarse[1:]):
            la = [va[k] for k in ka if c0 <= k <= c1]
            lb = [vb[k] for k in kb if c0 <= k <= c1]
            poly = la + list(reversed(lb))
            b.face(tuple(poly) if up else tuple(reversed(poly)), 0, region)

    for r in range(len(rows) - 1):
        strip(top[r], top[r + 1], R_FRONT, True)
        strip(bot[r], bot[r + 1], R_BACK, False)
    # serrated ends (region R_EDGE at -y, R_EDGE + 2 at +y)
    for (ks, rt), (_, rb), region, sgn in ((top[0], bot[0], R_EDGE, -1), (top[-1], bot[-1], R_EDGE + 2, 1)):
        for k0, k1 in zip(ks[:-1], ks[1:]):
            q = (rb[k0], rb[k1], rt[k1], rt[k0])
            b.face(q if sgn < 0 else tuple(reversed(q)), 0, region)
    # long sides (R_EDGE + 3 at -x, R_EDGE + 1 at +x)
    for side, region in ((0, R_EDGE + 3), (1, R_EDGE + 1)):
        for r in range(len(rows) - 1):
            ka, kb = top[r][0], top[r + 1][0]
            k_a, k_b = (ka[0], kb[0]) if side == 0 else (ka[-1], kb[-1])
            q = (bot[r][1][k_a], bot[r + 1][1][k_b], top[r + 1][1][k_b], top[r][1][k_a])
            b.face(tuple(reversed(q)) if side == 0 else q, 0, region)
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
    n2 = 2 * p["teeth"]
    fk0, fk1, fw0, fw1, _ = p["fin"]
    k0 = sorted({0, 2, 5, 10, 15, 20, fw0, fk0, n2 // 2, fk1, fw1, n2 - 20, n2 - 15, n2 - 10, n2 - 5, n2 - 2, n2})
    lods = [Lod(_pack_builder(k0, [0, .04, .12, .25, .5, .75, .88, .96, 1], teeth=True, ribs=True, fin=True)),
            Lod(_pack_builder([0, 2, 5, 9, 13, 16, 18], [0, .1, .5, .9, 1], teeth=True, ribs=False, fin=False,
                              n_teeth=9)),
            Lod(_pack_builder([0, n2 // 4, n2 // 2, 3 * n2 // 4, n2], [0, .5, 1], teeth=False, ribs=False, fin=False))]
    return Item(
        name="SM_CSK_Pack_Std_Sealed", lods=lods, materials=["M_CSK_Pack"],
        projections={R_FRONT: _planar(-w / 2, -h / 2, w, h),
                     R_BACK: _planar(-w / 2, -h / 2, w, h, tile_u=1.0, mirror_x=True),
                     **_pack_edge_projections(w, h, t)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, -h / 2, t / 2)), Socket("Face", (0, 0, t)),
                 Socket("CardsOut", (0, h / 2, t / 2), (-90.0, 0.0, 0.0)), Socket("Stack", (0, 0, t))],
        hulls=[((-w / 2, -h / 2, 0), (w / 2, h / 2, t))], cls="Pack", budget=S.BUDGETS["SM_CSK_Pack_Std_Sealed"],
        data={"footprint_mm": [w, h, t], "stack": {"socket": "Stack", "pitch_mm": t, "max": 10},
              "states": ["Sealed"], "reference": "References/CardShop/csk_pack.png (sheet 4)",
              "notes": ["Sheet 4: 27 teeth, ribbed crimps, back fin seal. The Open / Strip / Wrapper states follow."]},
    )


# =========================================================================== B2 booster box S (+ lid)

def _dieline(s):
    """Dieline (spec 3.B, S: 440 x 305 mm): front | right | back | left in a 125-high row, the bottom panel under the
    front, the lid over the back with its tuck-flap tab above it (sheet 5). Returns the per-panel planar maps
    (region -> projection) and the sheet size. Region 16 is the lid's inside (the display header), mapped to the lid
    panel's place in tile (1, 0) so it reads the right way round when the lid stands up."""
    W, D, H = s["w"], s["d"], s["h"]
    U, V = 2 * (W + D), H + 2 * D + s["tab"][1]
    def m(fu, fv, tile_u=0.0):
        return lambda x, y, z: (tile_u + inset(fu(x, y, z) / U), inset(fv(x, y, z) / V))
    return {
        10: m(lambda x, y, z: x + W / 2, lambda x, y, z: D + z),                    # front (-Y)
        11: m(lambda x, y, z: W + (y + D / 2), lambda x, y, z: D + z),              # right (+X)
        12: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: D + z),          # back (+Y)
        13: m(lambda x, y, z: 2 * W + D + (D / 2 - y), lambda x, y, z: D + z),      # left (-X)
        14: m(lambda x, y, z: x + W / 2, lambda x, y, z: D - (y + D / 2)),          # bottom, under the front
        15: m(lambda x, y, z: W + D + (W / 2 - x), lambda x, y, z: D + H + (D / 2 - y)),  # lid top (body y; hinge +D/2)
        16: m(lambda x, y, z: W + D + (x + W / 2), lambda x, y, z: D + H + (D / 2 - y), tile_u=1.0),  # lid inside
    }, (U, V)


def _prism_y(b: Builder, outline_xz, y0: float, y1: float, mat: int = 0) -> None:
    """A closed prism along +Y from an outline in XZ (counter-clockwise seen from -Y)."""
    f = [b.v(x, y0, z) for x, z in outline_xz]
    k = [b.v(x, y1, z) for x, z in outline_xz]
    n = len(outline_xz)
    b.face(tuple(f), mat)
    b.face(tuple(reversed(k)), mat)
    for i in range(n):
        j = (i + 1) % n
        b.face((f[i], k[i], k[j], f[j]), mat)


def _window_outline(s, segs: int):
    """The front die-cut (sheet 5): a trapezoid from above the rim down, with rounded bottom corners (quadratic Bezier
    fillets); points in XZ, counter-clockwise seen from the front. ``segs`` 0 leaves the corners sharp."""
    H = s["h"]
    tw, bw, depth, r = s["window"]
    zb, zt = H - depth, H + 5.0
    xt = bw / 2 + (tw - bw) / 2 * (zt - zb) / depth          # the slanted sides extended to zt
    ln = math.hypot((tw - bw) / 2, depth)
    ux, uz = (tw - bw) / 2 / ln, depth / ln                   # unit vector up the right-hand side
    def fillet(p0, ctrl, p1):
        if segs == 0:
            return [ctrl]
        return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t * t * p1[0],
                 (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t * t * p1[1])
                for t in (k / segs for k in range(segs + 1))]
    cl, cr = (-bw / 2, zb), (bw / 2, zb)
    left = fillet((cl[0] - ux * r, zb + uz * r), cl, (cl[0] + r, zb))
    right = fillet((cr[0] - r, zb), cr, (cr[0] + ux * r, zb + uz * r))
    return [(-xt, zt)] + left + right + [(xt, zt)]


def _box_shell(b: Builder, s, closed_top: bool) -> None:
    """The carton: printed outside (regions 10-14), board rim, inner walls and floor; or a closed block."""
    W, D, H, bd = s["w"], s["d"], s["h"], s["board"]
    PRINT, BOARD = 0, 1
    o = [b.v(-W / 2, -D / 2, 0), b.v(W / 2, -D / 2, 0), b.v(W / 2, D / 2, 0), b.v(-W / 2, D / 2, 0),
         b.v(-W / 2, -D / 2, H), b.v(W / 2, -D / 2, H), b.v(W / 2, D / 2, H), b.v(-W / 2, D / 2, H)]
    b.face((o[0], o[3], o[2], o[1]), PRINT, 14)
    b.face((o[0], o[1], o[5], o[4]), PRINT, 10)
    b.face((o[1], o[2], o[6], o[5]), PRINT, 11)
    b.face((o[2], o[3], o[7], o[6]), PRINT, 12)
    b.face((o[3], o[0], o[4], o[7]), PRINT, 13)
    if closed_top:
        b.face((o[4], o[5], o[6], o[7]), PRINT, 15)
        return
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


def _box_body(s, level: int) -> Lod:
    """Sheet 5, opened: the carton with the front die-cut window torn out and the centre divider."""
    W, D, H, bd = s["w"], s["d"], s["h"], s["board"]
    b = Builder()
    _box_shell(b, s, closed_top=False)
    cut = Builder()
    _prism_y(cut, _window_outline(s, (6, 2, 0)[level]), -D / 2 - 1.0, -D / 2 + bd + 1.0, mat=1)
    dt, below = s["divider"]
    div = Builder()
    div.box((-dt / 2, -D / 2 + bd - 0.5, bd - 0.5), (dt / 2, D / 2 - bd + 0.5, H - below), mat=1)
    return Lod(b, bevel_mm=0.5 if level == 0 else None, ops=[("DIFFERENCE", cut), ("UNION", div)],
               bevel_first=True)


def item_box_booster() -> Item:
    s = S.BOX_BOOSTER_S
    W, D, H, bd = s["w"], s["d"], s["h"], s["board"]
    proj, _uv_size = _dieline(s)
    lods = [_box_body(s, k) for k in range(3)]
    # packs standing: 2 across x 18 deep at 4 pitch, either side of the centre divider; a pack's Seat frame turned
    # +90 deg about X (its length up, its face toward the customer), so it fills y in [s_y - 4, s_y]
    pk = S.PACK_STD
    cols, rows = s["packs"]
    pitch = s["pack_pitch"]
    dt = s["divider"][0]
    inner_x, inner_y0 = W / 2 - bd, -D / 2 + bd
    sockets = [Socket("Seat", (0, 0, 0))]
    n = 0
    for r in range(rows):
        for c in range(cols):
            n += 1
            x = (c - (cols - 1) / 2) * (pk["w"] + dt)
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
                                "axis": "X", "range_deg": [0, 200], "open_rot_deg": [s["header_rot"], 0.0, 0.0]}},
              "dieline_mm": list(_uv_size), "reference": "References/CardShop/csk_booster_box.png (sheet 5)",
              "notes": ["Opened state (sheet 5): front die-cut window, centre divider; the lid is the display header",
                        "Sealed state: SM_CSK_Box_Booster_S_Sealed"]},
    )


def item_box_lid() -> Item:
    """The lid (sheet 5): top panel + the tuck-flap tab in one board. Hinge frame: origin on the hinge axis at the
    rear top edge; closed, the lid covers y in [-D, 0]. Its inside is printed (region 16): stood up at the display
    pose it is the header the customer sees. The tab is modelled flat (the display look); the closed box is the
    separate _Sealed mesh."""
    s = S.BOX_BOOSTER_S
    W, D, bd = s["w"], s["d"], s["board"]
    tw, th, tr = s["tab"]
    proj, _ = _dieline(s)
    outline = [(-W / 2, 0.0), (-W / 2, -D), (-tw / 2, -D)]
    for cx, a0 in ((-tw / 2 + tr, 180.0), (tw / 2 - tr, 270.0)):
        outline += [(cx + tr * math.cos(math.radians(a0 + 90 * i / 3)), -D - th + tr + tr * math.sin(math.radians(a0 + 90 * i / 3)))
                    for i in range(4)]
    outline += [(tw / 2, -D), (W / 2, -D), (W / 2, 0.0)]
    # (down the left side, along the front with the tab, up the right side: counter-clockwise seen from +Z)
    b = Builder()
    b.prism(outline, 0.0, bd, mat=1, top=15, bottom=16, top_mat=0, bottom_mat=0)
    shift = lambda f: (lambda x, y, z: f(x, y + D / 2, z))
    return Item(
        name="SM_CSK_Box_Booster_S_Lid", lods=[Lod(b)], materials=["M_CSK_BoxPrint", "M_CSK_Board"],
        projections={15: shift(proj[15]), 16: shift(proj[16])}, sockets=[Socket("Seat", (0, 0, 0))],
        hulls=[((-W / 2, -D - th, 0), (W / 2, 0, bd))],
        budget=S.BUDGETS["SM_CSK_Box_Booster_S_Lid"], data={"part_of": "SM_CSK_Box_Booster_S", "pivot": "hinge axis"},
    )


def item_box_sealed() -> Item:
    """Sheet 5, sealed: the closed carton inside a shrink-film shell with soft vertical corners."""
    s = S.BOX_BOOSTER_S
    W, D, H, f = s["w"], s["d"], s["h"], s["film"]
    proj, _ = _dieline(s)
    b = Builder()
    _box_shell(b, s, closed_top=True)
    b.prism(rounded_rect(W + 2 * f, D + 2 * f, 2.0, 2), -f, H + f, mat=2)
    Hs = H + 2 * f
    return Item(
        name="SM_CSK_Box_Booster_S_Sealed", lods=[Lod(_shift_z(b, f), bevel_mm=0.4)],
        materials=["M_CSK_BoxPrint", "M_CSK_Board", "M_CSK_Film"], projections=proj,
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Grip", (0, -D / 2 - f, Hs / 2)),
                 Socket("Face", (0, -D / 2 - f, Hs / 2), (90.0, 0.0, 0.0)), Socket("Stack", (0, 0, Hs))],
        hulls=[((-W / 2 - f, -D / 2 - f, 0), (W / 2 + f, D / 2 + f, Hs))], cls="BoxS",
        budget=S.BUDGETS["SM_CSK_Box_Booster_S_Sealed"],
        data={"footprint_mm": [W + 2 * f, D + 2 * f, Hs], "stack": {"socket": "Stack", "pitch_mm": Hs, "max": 4},
              "reference": "References/CardShop/csk_booster_box.png (sheet 5)"},
    )


def _shift_z(b: Builder, dz: float) -> Builder:
    """Move every vertex of ``b`` up by ``dz`` (so a shell built from z = -dz sits on z = 0)."""
    b.verts = [(x, y, z + dz) for x, y, z in b.verts]
    return b


# =========================================================================== A1 showcase (1778) + glass + door

def _showcase_dims(L: float):
    s = S.SHOWCASE_FULL
    d, H, g, kick, post, rail = s["d"], s["h"], s["glass"], s["kick"], s["post"], s["rail"]
    deck_top = kick + s["base"]
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
    y0 = k["y_front_in"]
    full = k["y_track_front"] - y0 - 2.0         # a full-depth shelf: 1 mm clear of the glass and the track
    d1, d2 = d1 or full, d2 or full
    z_s1 = k["deck_top"] + gap1                  # S1 glass bottom
    z_s2 = z_s1 + g + gap2
    top_clear = k["top_under"] - s["led_channel"][1] - 1.0   # the LED channel hangs below the top
    y0 = y0 + 1.0
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


def _face_out(b: Builder, ids, outward, mat: int, region: int = 0) -> None:
    """Add a planar face whose winding makes its normal point along ``outward``."""
    import numpy as _np
    P = _np.array([b.verts[i] for i in ids])
    n = _np.zeros(3)
    for a, c in zip(P, _np.roll(P, -1, axis=0)):            # Newell normal
        n += _np.cross(a, c)
    b.face(tuple(ids) if _np.dot(n, outward) >= 0 else tuple(reversed(ids)), mat, region)


def _slotted_standard(b: Builder, sx: int, x_in: float, yc: float, z0: float, z1: float, slots: bool,
                      mat: int) -> None:
    """A slotted aluminium shelf standard on an end post's inner face (sheet 7 detail 5): a bar ``depth`` into the
    case, ``width`` along Y. Its inner face is a ladder of quads round real slot pockets (shared vertices)."""
    s = S.SHOWCASE_FULL
    wd, dp = s["standard"]
    sw, sh, pitch = s["slot"]
    xo, xf = sx * x_in, sx * (x_in - dp)                   # post side, slotted (inner) face
    xd = sx * (x_in - dp / 2)                               # slot bottom: half the bar deep
    ys = [yc - wd / 2, yc - sw / 2, yc + sw / 2, yc + wd / 2]
    bands = []                                              # (z_lo, z_hi, is_slot)
    z = z0
    if slots:
        zs = z0 + 20.0
        while zs + sh <= z1 - 20.0:
            bands.append((z, zs, False))
            bands.append((zs, zs + sh, True))
            z = zs + sh
            zs += pitch
    bands.append((z, z1, False))
    zb = [bands[0][0]] + [hi for _, hi, _ in bands]
    F = [[b.v(xf, y, zz) for y in ys] for zz in zb]         # the inner face grid: rows by z, 4 columns by y
    inward = (-sx, 0, 0)
    for r, (lo, hi, is_slot) in enumerate(bands):
        for c in range(3):
            if is_slot and c == 1:
                continue
            _face_out(b, [F[r][c], F[r][c + 1], F[r + 1][c + 1], F[r + 1][c]], inward, mat)
        if is_slot:                                         # the pocket: 4 walls + bottom
            d_ = [b.v(xd, ys[1], lo), b.v(xd, ys[2], lo), b.v(xd, ys[2], hi), b.v(xd, ys[1], hi)]
            h = [F[r][1], F[r][2], F[r + 1][2], F[r + 1][1]]
            zc = (lo + hi) / 2
            for a in range(4):
                e = (a + 1) % 4
                my = (b.verts[h[a]][1] + b.verts[h[e]][1]) / 2
                mz = (b.verts[h[a]][2] + b.verts[h[e]][2]) / 2
                _face_out(b, [h[a], h[e], d_[e], d_[a]], (0, yc - my, zc - mz), mat)
            _face_out(b, d_, inward, mat)
    # the post side and the four edges: plain quads sharing only the ladder's corners (the ladder's edge vertices
    # sit on their edges: boundary T-junctions, no coincident vertices, no collinear n-gon slivers)
    o = {(j, k): b.v(xo, ys[j], (z0, z1)[k]) for j in (0, 3) for k in (0, 1)}
    _face_out(b, [o[0, 0], o[3, 0], o[3, 1], o[0, 1]], (sx, 0, 0), mat)
    for j, ny in ((0, -1), (3, 1)):
        _face_out(b, [o[j, 0], F[0][j], F[-1][j], o[j, 1]], (0, ny, 0), mat)
    _face_out(b, [o[0, 0], o[3, 0], F[0][3], F[0][0]], (0, 0, -1), mat)
    _face_out(b, [o[0, 1], o[3, 1], F[-1][3], F[-1][0]], (0, 0, 1), mat)


def _showcase_body(L: float, level: int) -> Builder:
    """Sheets 6 + 7: aluminium posts and rails on a light-oak cabinet over a recessed black toe kick; the cabinet top
    is the cream deck; slotted standards with shelf pins inside the end posts; LED channel under the top front
    rail; rear door tracks."""
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    d, H, post, rail = k["d"], k["H"], k["post"], k["rail"]
    FRAME, KICK, LED, OAK, DECK = 0, 1, 2, 3, 4
    kick, ki = s["kick"], s["kick_inset"]
    b = Builder()
    b.box((-L / 2 + ki, -d / 2 + ki, 0), (L / 2 - ki, d / 2 - ki, kick), mat=KICK)            # recessed toe kick
    b.box((-L / 2 + 1.0, -d / 2 + 1.0, kick - 0.5), (L / 2 - 1.0, d / 2 - 1.0, k["deck_top"]), mat=OAK,
          mats={"pz": DECK})                                                                  # oak cabinet + deck
    px, py = L / 2 - post / 2, d / 2 - post / 2
    for sx in (-1, 1):                                                                        # corner posts
        for sy in (-1, 1):
            b.box((sx * px - post / 2, sy * py - post / 2, kick), (sx * px + post / 2, sy * py + post / 2, H),
                  mat=FRAME)
    if level < 2:
        inset = (post - rail) / 2
        zr0, zr1 = H - rail - inset, H - inset
        for sy in (-1, 1):                                                                    # top rails along X
            b.box((-px - 5.0, sy * py - rail / 2, zr0), (px + 5.0, sy * py + rail / 2, zr1), mat=FRAME)
        for sx in (-1, 1):                                                                    # top rails along Y
            b.box((sx * px - rail / 2, -py - 5.0, zr0), (sx * px + rail / 2, py + 5.0, zr1), mat=FRAME)
        th, td = s["track"]
        yt0 = k["y_track_front"]
        b.box((-k["x_in"] - 2.0, yt0, k["deck_top"]), (k["x_in"] + 2.0, yt0 + td, k["deck_top"] + th), mat=FRAME)
        b.box((-k["x_in"] - 2.0, yt0, zr0 - th), (k["x_in"] + 2.0, yt0 + td, zr0), mat=FRAME)
        cd, ch = s["led_channel"]                                                             # LED channel + diffuser
        yl = k["y_front_in"] + 3.0
        tu = k["top_under"]
        b.box((-k["x_in"] + 10.0, yl, tu - ch), (k["x_in"] - 10.0, yl + cd, tu + 0.5), mat=FRAME)
        b.box((-k["x_in"] + 12.0, yl + 2.0, tu - ch - 1.0), (k["x_in"] - 12.0, yl + cd - 2.0, tu - ch + 0.5), mat=LED)
    return b


def _showcase_parts(L: float, level: int) -> Optional[Builder]:
    """The slotted standards and shelf pins (joined after the bevel: crisp, and slots only on LOD0)."""
    if level == 2:
        return None
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    FRAME = 0
    yt0 = k["y_track_front"]
    b = Builder()
    if True:
        wd, dp = s["standard"]                                                                # standards + pins
        for sx in (-1, 1):
            for yc in (k["y_front_in"] + 1.0 + wd / 2, yt0 - 1.0 - wd / 2):
                _slotted_standard(b, sx, k["x_in"], yc, k["deck_top"], k["top_under"] - s["led_channel"][1] - 2.0,
                                  slots=(level == 0), mat=FRAME)
                pw, pl = s["pin"]
                for name, z, *_ in _levels(L)[1:]:
                    zb = z - k["g"]                      # the glass shelf's underside
                    x0 = sx * (k["x_in"] - dp)
                    b.box((min(x0, x0 - sx * pl), yc - pw / 2, zb - pw), (max(x0, x0 - sx * pl), yc + pw / 2, zb),
                          mat=FRAME)
    return b


def item_showcase(L: float = 1778.0) -> Item:
    k = _showcase_dims(L)
    s = S.SHOWCASE_FULL
    d, H, post = k["d"], k["H"], k["post"]
    lods = [Lod(_showcase_body(L, 0), bevel_mm=1.0, extra=_showcase_parts(L, 0)),
            Lod(_showcase_body(L, 1), extra=_showcase_parts(L, 1)), Lod(_showcase_body(L, 2))]
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
        # the door mesh has its lock at local +X: the right door is turned 180 deg so both locks meet at the centre
        sockets.append(Socket(f"Door_{side}", (cx, ty, door_z), (0.0, 0.0, 180.0 if side == "R" else 0.0)))
    cd, ch = s["led_channel"]
    sockets += [Socket("LED", (0, k["y_front_in"] + 3.0 + cd / 2, k["top_under"] - ch - 1.0), (180.0, 0.0, 0.0)),
                Socket("Snap_L", (-L / 2, 0, 0)), Socket("Snap_R", (L / 2, 0, 0))]
    travel = L / 2 - s["door_travel_off"]
    return Item(
        name=f"SM_CSK_Showcase_Full_{int(L)}", lods=lods,
        materials=["M_CSK_Frame", "M_CSK_Base", "M_CSK_LED", "M_CSK_Oak", "M_CSK_Deck"],
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
              "glass": f"SM_CSK_Showcase_Full_Glass_{int(L)}",
              "reference": "References/CardShop/csk_showcase_full.png + csk_showcase_detail.png (sheets 6, 7)"},
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
    xs = k["x_in"] - s["standard"][1] - 1.0                  # clear of the slotted standards
    for name, z, y0, y1, clear in lv[1:]:                                                            # shelves
        panes.append(((-xs, y0, z - g), (xs, y1, z)))
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
    ld, lp, lz = s["lock"]                              # cylinder lock clamped on the meeting edge (sheet 7 detail 4)
    xl = w / 2 - st - 18.0
    b.box((xl - 15.0, -g / 2 - 5.0, lz - 16.0), (xl + 15.0, g / 2 + 5.0, lz + 16.0), mat=1)
    _prism_y(b, [(xl + ld / 2 * math.cos(2 * math.pi * i / 12), lz + ld / 2 * math.sin(2 * math.pi * i / 12))
                 for i in range(12)], g / 2 + 4.0, g / 2 + 5.0 + lp, mat=1)
    return Item(name=f"SM_CSK_Showcase_Full_Door_{int(L)}", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Frame"],
                projections={}, sockets=[Socket("Grip", (w / 2 - st / 2, 0, h / 2))],
                hulls=[((-w / 2, -g / 2 - 1.5, 0), (w / 2, g / 2 + 1.5, h))],
                budget=S.BUDGETS["SM_CSK_Showcase_Full_Door_1778"],
                data={"part_of": f"SM_CSK_Showcase_Full_{int(L)}", "pivot": "bottom-centre at the closed position",
                      "size_mm": [w, g, h]})


ALL_ITEMS = {
    "card": item_card, "toploader": item_toploader, "toploader_130": lambda: item_toploader("130pt"), "slab": item_slab, "slab_filled": item_slab_filled,
    "pack": item_pack, "box": item_box_booster, "box_lid": item_box_lid, "box_sealed": item_box_sealed,
    "showcase": item_showcase,
    "showcase_glass": item_showcase_glass, "showcase_door": item_showcase_door,
}


# =========================================================================== family modules (P3-P5)
# Every csk_lib/fam_<family>.py adds its items here: ``ITEMS`` {key: item function}, optional ``CLASSES``
# {code: spec.ItemClass} for new placement classes. A family module never edits this file, spec.py, shapes.py or
# mesh.py, so parallel builders cannot conflict. Keys are prefixed with the family ("fam_b_collector").
def _load_families() -> None:
    import importlib
    import pkgutil
    from pathlib import Path
    for m in sorted(pkgutil.iter_modules([str(Path(__file__).parent)]), key=lambda m: m.name):
        if not m.name.startswith("fam_"):
            continue
        mod = importlib.import_module(f"{__package__}.{m.name}")
        for code, c in getattr(mod, "CLASSES", {}).items():
            S.CLASSES.setdefault(code, c)
        for key, fn in getattr(mod, "ITEMS", {}).items():
            if key in ALL_ITEMS:
                raise KeyError(f"{m.name}: item key {key!r} is already registered")
            ALL_ITEMS[key] = fn


_load_families()
