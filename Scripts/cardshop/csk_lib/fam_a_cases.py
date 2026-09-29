"""Card Shop Kit family a_cases: the glass cases of CARDSHOP_KIT_SPEC.md 3.A rows A2-A6 (P3-P5).

    A2 half-vision showcase (1219, 1778) + Door + Glass (+ BayDoor)   reference sheet 16
    A3 frameless glass tower + Door + Glass                           reference sheet 17 (1)
    A4 lit framed wall/tower case 1016 + Door + Glass                 reference sheet 17 (2)
    A5 countertop case 900 + Lid + Glass                              reference sheet 18 (1)
    A6 wall slab case + Door                                          reference sheet 18 (2)

The family look is the built full-vision showcase (geom.item_showcase, sheets 6 + 7): square aluminium posts and
rails, light-oak cabinets with a cream deck, black kick, glass in its own ``_Glass`` mesh, moving parts as separate
meshes wired through ``data["parts"]``, display levels solved with ``solve_grid``. Sheets 16-18 are not on disk: the
build follows their notes in References/CardShop/REFERENCE_LOG.md. Where a sheet's proportions disagree with a spec
M number, the number wins; the picture wins over E numbers (each such change is logged on the item's dict).

Flags after each number, as spec.py: M = measured (source key), D = derived, E = estimate / design choice, E* = a
spec estimate with a source range. Millimetres; Seat frame: +X right, +Y away from the customer, +Z up.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import spec as S
from .geom import Item, Lod, Socket, _face_out, _prism_y, _slotted_standard, solve_grid
from .shapes import Builder, circle, rect

# =========================================================================== numbers

A2 = dict(                     # half-vision showcase, sheet 16
    lengths=(1219.0, 1778.0),  # M [D23]; v1 ships both (E)
    d=457.0, h=965.0,          # M [D23]
    glass=6.35,                # M [D24]
    glass_front_h=470.0,       # E*: front glass height (sets the deck at 475)
    bay_h=184.0,               # E*: storage bay clear height (sheet 16 reads about 250; the spec number is kept)
    carcass=19.0,              # E*: oak board thickness (end panels, bay top, bay shelf)
    shelf_d=254.0,             # E*: glass shelf depth, from the front glass
    # sheet 16: ONE glass shelf + the deck (the spec's 2 shelves were E; the picture wins)
    kick=60.0, kick_inset=10.0,  # sheet 16: black kick band about 60; inset 10 as A1 (sheet 7 detail 2)
    post=25.0, rail=20.0,      # E: as A1 (sheet 16: same aluminium trim)
    track=(15.0, 25.0),        # rear glass-door track height x depth, as A1 (E)
    door_overlap=25.0, door_travel_off=50.0, stile=15.0,   # rear doors as A1: W = L/2 + 25, travel L/2 - 50 (E)
    led_channel=(16.0, 9.0),   # LED channel under the top front rail, as A1 (sheet 16)
    lock=(22.0, 12.0, 150.0),  # door lock cylinder, as A1 (sheet 16: same rear doors as sheet 6)
    clip=(10.0, 22.0, 9.0),    # clear shelf clip: X out of the end panel, Y length, Z height (sheet 16 "clear clips"), E
    bay_door_t=16.0,           # E: oak sliding panel thickness
    bay_track=(10.0, 40.0),    # E: bay door track height x depth (aluminium U channel, two channels)
    pull=(110.0, 30.0, 5.0),   # E: recessed pull W x H x depth, on both faces (sheet 16 "recessed pull handles")
)

A3 = dict(                     # frameless glass tower, sheet 17 (1)
    w=457.0, d=457.0, h=1829.0,  # M [D25]
    glass=6.35,                # M [D24]
    base=152.0,                # E*: light-oak base (sheet 17)
    band=45.0,                 # sheet 17: black bottom band about 45, flush
    shelves=4, pitch=317.5,    # E*: 4 glass shelves at 317.5 pitch (5 levels with the deck; sheet 17 agrees)
    inset=3.0,                 # E: glass outer faces 3 in from the base edges
    gap=2.0,                   # E: door clearance to the side panes, the base and the top pane
    pole=(16.0, 5.0),          # sheet 17: thin aluminium light pole in the back corner: section, inner chamfer (E)
    pole_led=(5.0, 1.5),       # E: LED strip on the pole's inner chamfer: width x proud
    clip=(22.0, 24.0, 12.0),   # E: metal shelf clip wrapping a side pane: X reach inside the glass, Y length, Z
    corner=(28.0, 18.0),       # E: metal corner clip: leg length, height (sheet 17: clips at the fixed glass corners)
    patch=(56.0, 40.0, 3.0, 14.0),  # E: door patch hinge: X length, Z height, Y proud each face, pivot from door edge
    lock=(22.0, 12.0),         # round cylinder lock: diameter, proud (sheet 17; A1 lock size)
)

A4 = dict(                     # lit framed wall / tower case, sheet 17 (2)
    w=1016.0, d=457.0, h=1848.0,  # M [D26]
    glass=6.35,                # M [D24]
    base=203.0,                # E*: light-oak base (sheet 17)
    band=45.0,                 # sheet 17: black bottom band about 45, flush
    shelves=4,                 # count E; sheet 17 shows 4 (5 levels)
    post=25.0, rail=20.0,      # E: as A1 (sheet 17: same materials as sheet 6)
    track=(15.0, 25.0),        # front sliding-door tracks, as A1's (E)
    door_w=533.0,              # E: = L/2 + 25
    door_travel_off=50.0,      # E: travel = L/2 - 50, as A1
    stile=15.0,
    led=(8.0, 2.0),            # sheet 17: warm LED strips inside both front posts: width x proud (E)
    clip=(24.0, 24.0, 12.0),   # E: front shelf clips on the side glass (the tower's clip), X reach, Y length, Z
    lock=(40.0, 11.0, 22.0, 16.0),  # sheet 17: sliding-door lock on the bottom track at the centre: X, Y, Z, cyl dia
)

A5 = dict(                     # countertop case, sheet 18 (1)
    w=900.0, d=450.0, h=300.0,  # E (spec A5; fits the 610-deep counter). Sheet 18's silhouette reads ~2x: spec wins
    glass=6.35,                # M [D24]
    kick=20.0, kick_inset=5.0,  # E: sheet 18 "the same oak band + black kick base as the counters", scaled
    base=50.0,                 # E: oak band above the kick (deck at 70)
    post=20.0, rail=15.0,      # E: slimmer than A1's 25 / 20 for the small case
    lid_h=16.0, lid_rail=24.0,  # E: lid frame height and rail width (covers the stay's top)
    hinge_r=3.0,               # E: continuous rear hinge barrel radius (axis 1 behind and 1 above the rear top edge)
    stay=(110.0, 3.0, 10.0, 80.0),  # quadrant stay: radius, thickness X, radial width, lid travel (E; spec 0-80)
    guide=(8.5, 16.0, 12.0),   # E: stay guide block X x Y x Z under the end rail
)

A6 = dict(                     # wall slab case, sheet 18 (2)
    w=1000.0, d=90.0, h=700.0,  # E (spec A6)
    glass=6.35,                # M [D24]
    frame=25.0,                # E: aluminium frame member face width
    door_zone=12.0,            # E: front 12 of the 90 depth hold the glass front and its hinge
    back_t=12.0,               # E: light-oak back panel (sheet 18; the spec's felt back: the picture wins)
    rows=4, cols=10,           # D (spec): 10 x 4 = 40 slab slots, confirmed by sheet 18's filled view
    pitch_x=94.0,              # D: the Slab class pitch
    lean=10.0,                 # E (spec): slabs lean 10 deg back
    ledge=(3.0, 14.0, 3.0, 1.0),  # E: acrylic ledge floor thickness, lip height, lip thickness, slab clearance
    led=(8.0, 2.0),            # sheet 18: LED strips in the side posts: width x proud (E)
    hinge_r=5.0,               # E: top hinge barrel radius; axis 6 in front of the frame, just under the top member
    open_deg=90.0,             # sheet 18: the glass front opens to horizontal (spec E said 85; the picture wins)
)

# LOD0 budgets: the spec's Tris column (E); BayDoor is new (E). Raised: Showcase_Wall 2500 -> 3500, because its two
# full-height slotted standards (sheet 17 "slotted standards in the back corners", the sheet 7 hardware at 25 pitch)
# carry 128 real slot pockets, about 2,560 tris on their own.
BUDGETS = {
    "SM_CSK_Showcase_Half": 2500, "SM_CSK_Showcase_Half_Glass": 500, "SM_CSK_Showcase_Half_Door": 150,
    "SM_CSK_Showcase_Half_BayDoor": 150,
    "SM_CSK_Showcase_Tower": 1500, "SM_CSK_Showcase_Tower_Glass": 400, "SM_CSK_Showcase_Tower_Door": 150,
    "SM_CSK_Showcase_Wall": 3500, "SM_CSK_Showcase_Wall_Glass": 500, "SM_CSK_Showcase_Wall_Door": 150,
    "SM_CSK_Case_Counter": 1200, "SM_CSK_Case_Counter_Glass": 200, "SM_CSK_Case_Counter_Lid": 150,
    "SM_CSK_Case_WallSlab": 1500, "SM_CSK_Case_WallSlab_Door": 200,
}

SHOWCASE_ACCEPTS = S.SHOWCASE_ACCEPTS
COUNTER_ACCEPTS = ("Card", "CardProt", "Slab")      # spec A5: "for singles and slabs"


# =========================================================================== shape helpers

def _pocket_box(b: Builder, mn, mx, mat: int, pockets: Sequence[Dict] = (), mats: Optional[Dict[str, int]] = None
                ) -> None:
    """A closed axis-aligned box whose -Y / +Y faces may carry rectangular pockets (real recesses: 4 walls and a
    floor). ``pockets``: dicts with face 'ny' | 'py', x0 x1 z0 z1 (the opening), depth, mat."""
    (x0, y0, z0), (x1, y1, z1) = mn, mx
    mats = mats or {}
    c = [b.v(x0, y0, z0), b.v(x1, y0, z0), b.v(x1, y1, z0), b.v(x0, y1, z0),
         b.v(x0, y0, z1), b.v(x1, y0, z1), b.v(x1, y1, z1), b.v(x0, y1, z1)]
    sides = {"nz": (c[0], c[3], c[2], c[1]), "pz": (c[4], c[5], c[6], c[7]),
             "ny": (c[0], c[1], c[5], c[4]), "py": (c[2], c[3], c[7], c[6]),
             "nx": (c[3], c[0], c[4], c[7]), "px": (c[1], c[2], c[6], c[5])}
    normals = {"ny": (0, -1, 0), "py": (0, 1, 0)}
    for key, quad in sides.items():
        mine = [p for p in pockets if p["face"] == key]
        m = mats.get(key, mat)
        if not mine:
            b.face(quad, m)
            continue
        yf = y0 if key == "ny" else y1
        n = normals[key]
        holes = []
        for p in mine:
            yd = yf - n[1] * p["depth"]
            h = [b.v(p["x0"], yf, p["z0"]), b.v(p["x1"], yf, p["z0"]), b.v(p["x1"], yf, p["z1"]),
                 b.v(p["x0"], yf, p["z1"])]
            d_ = [b.v(p["x0"], yd, p["z0"]), b.v(p["x1"], yd, p["z0"]), b.v(p["x1"], yd, p["z1"]),
                  b.v(p["x0"], yd, p["z1"])]
            xc, zc = (p["x0"] + p["x1"]) / 2, (p["z0"] + p["z1"]) / 2
            pm = p.get("mat", m)
            for i in range(4):
                j = (i + 1) % 4
                mx_ = (b.verts[h[i]][0] + b.verts[h[j]][0]) / 2
                mz_ = (b.verts[h[i]][2] + b.verts[h[j]][2]) / 2
                _face_out(b, [h[i], h[j], d_[j], d_[i]], (xc - mx_, 0, zc - mz_), pm)
            _face_out(b, d_, n, pm)
            holes.append(h)
        b.fill([list(quad)] + holes, m, 0, n)


def _banded_block(b: Builder, x0, x1, y0, y1, zs: Sequence[float], side_mats: Sequence[int], top_mat: int,
                  bottom_mat: int) -> None:
    """A closed box whose sides change material at each z in ``zs`` (a flush band: no step, no seam)."""
    outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    loops = [b.loop(outline, z) for z in zs]
    for k in range(len(zs) - 1):
        lb, lt = loops[k], loops[k + 1]
        for i in range(4):
            j = (i + 1) % 4
            b.face((lb[i], lb[j], lt[j], lt[i]), side_mats[k])
    b.fill([loops[-1]], top_mat, 0, (0, 0, 1))
    b.fill([loops[0]], bottom_mat, 0, (0, 0, -1))


def _ring(b: Builder, outer, inner, z0: float, z1: float, mat: int) -> None:
    """A closed picture-frame ring: two CCW outlines (outer, hole) extruded from z0 to z1."""
    ob, ot = b.loop(outer, z0), b.loop(outer, z1)
    ib, it = b.loop(inner, z0), b.loop(inner, z1)
    for lb, lt, inward in ((ob, ot, False), (ib, it, True)):
        n = len(lb)
        for i in range(n):
            j = (i + 1) % n
            q = (lb[i], lb[j], lt[j], lt[i])
            b.face(tuple(reversed(q)) if inward else q, mat)
    b.fill([ot, it], mat, 0, (0, 0, 1))
    b.fill([ob, ib], mat, 0, (0, 0, -1))


def _prism_x(b: Builder, outline_yz, x0: float, x1: float, mat: int) -> None:
    """A closed prism along +X from an outline in (y, z); any winding (it is made CCW seen from +X)."""
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


def _arc_x(b: Builder, yc: float, zc: float, r: float, width: float, x0: float, x1: float,
           phis: Sequence[float], mat: int) -> None:
    """A curved bar round an X axis at (yc, zc): radial ``width`` centred on radius ``r``, from x0 to x1, through
    the angles ``phis`` (degrees; the point at angle p is (yc + r sin p, zc - r cos p): 0 = straight below)."""
    def d(p):
        a = math.radians(p)
        return math.sin(a), -math.cos(a)
    rows = []
    for p in phis:
        dy, dz = d(p)
        rows.append([b.v(x, yc + rr * dy, zc + rr * dz) for rr in (r - width / 2, r + width / 2) for x in (x0, x1)])
    # row layout: [in-x0, in-x1, out-x0, out-x1]
    for k in range(len(phis) - 1):
        a_, c_ = rows[k], rows[k + 1]
        pm = (phis[k] + phis[k + 1]) / 2
        dy, dz = d(pm)
        _face_out(b, [a_[0], a_[1], c_[1], c_[0]], (0, -dy, -dz), mat)     # inner
        _face_out(b, [a_[2], a_[3], c_[3], c_[2]], (0, dy, dz), mat)       # outer
        _face_out(b, [a_[0], a_[2], c_[2], c_[0]], (-1, 0, 0), mat)        # x0 side
        _face_out(b, [a_[1], a_[3], c_[3], c_[1]], (1, 0, 0), mat)         # x1 side
    for row, p, sgn in ((rows[0], phis[0], -1), (rows[-1], phis[-1], 1)):
        a = math.radians(p)
        tangent = (0, sgn * math.cos(a), sgn * math.sin(a))
        _face_out(b, [row[0], row[1], row[3], row[2]], tangent, mat)


def _box(b: Builder, mn, mx, mat: int, **kw) -> None:
    """Box with its corners sorted (so callers may pass mirrored coordinates)."""
    lo = tuple(min(mn[i], mx[i]) for i in range(3))
    hi = tuple(max(mn[i], mx[i]) for i in range(3))
    b.box(lo, hi, mat=mat, **kw)


def _cyl_y(b: Builder, xc: float, zc: float, r: float, y0: float, y1: float, segs: int, mat: int) -> None:
    _prism_y(b, [(xc + r * math.cos(2 * math.pi * i / segs), zc + r * math.sin(2 * math.pi * i / segs))
                 for i in range(segs)], y0, y1, mat=mat)


def _cyl_x(b: Builder, yc: float, zc: float, r: float, x0: float, x1: float, segs: int, mat: int) -> None:
    _prism_x(b, [(yc + r * math.cos(2 * math.pi * (i + 0.5) / segs), zc + r * math.sin(2 * math.pi * (i + 0.5) / segs))
                 for i in range(segs)], x0, x1, mat)


def _slide_door(w: float, h: float, g: float, st: float, lock: Optional[Tuple[float, float, float]]) -> Builder:
    """A1's rear sliding door (sheet 7 detail 3-4): glass leaf between two edge stiles; optionally the clamp and
    cylinder lock on the +X (meeting) edge, the cylinder toward +Y. Bottom-centre at the closed position."""
    b = Builder()
    b.box((-w / 2 + st, -g / 2, 0), (w / 2 - st, g / 2, h), mat=0)
    for sx in (-1, 1):
        b.box((sx * (w / 2 - st / 2) - st / 2, -g / 2 - 1.5, 0), (sx * (w / 2 - st / 2) + st / 2, g / 2 + 1.5, h),
              mat=1)
    if lock:
        ld, lp, lz = lock
        xl = w / 2 - st - 18.0
        b.box((xl - 15.0, -g / 2 - 5.0, lz - 16.0), (xl + 15.0, g / 2 + 5.0, lz + 16.0), mat=1)
        _cyl_y(b, xl, lz, ld / 2, g / 2 + 4.0, g / 2 + 5.0 + lp, 12, 1)
    return b


def _level_sockets(levels, width: float, n_comp: int, price_tags: bool, accepts) -> Tuple[List[Socket], List[Dict]]:
    """Level_*, Compartment_*, PriceTag_* sockets and the .csk.json level list with solve_grid grids.
    ``levels``: (name, z floor, y0, y1, clear height); the level is centred on x = 0."""
    sockets, data = [], []
    for name, z, y0, y1, clear in levels:
        yc = (y0 + y1) / 2
        sockets.append(Socket(f"Level_{name}", (0, yc, z), kind="DISPLAY"))
        cw = width / n_comp
        for i in range(n_comp):
            cx = -width / 2 + cw * (i + 0.5)
            sockets.append(Socket(f"Compartment_{name}_{i + 1:02d}", (cx, yc, z), kind="DISPLAY"))
            if price_tags:
                sockets.append(Socket(f"PriceTag_{name}_{i + 1:02d}", (cx, y0 + 2.0, z), kind="DISPLAY"))
        grids = [g for g in (solve_grid(width, y1 - y0, clear, c) for c in accepts) if g]
        data.append({"socket": f"Level_{name}", "interior_mm": [round(width, 3), round(y1 - y0, 3)],
                     "clear_h_mm": round(clear, 3), "compartments": n_comp, "grids": grids})
    return sockets, data


# =========================================================================== A2 half-vision showcase (sheet 16)

def _a2_dims(L: float) -> Dict:
    s = A2
    d, H, g, post, rail, cc = s["d"], s["h"], s["glass"], s["post"], s["rail"], s["carcass"]
    top_under = H - rail                                  # 945: underside of the top rails
    deck_top = top_under - s["glass_front_h"]             # 475: the deck (the cabinet top)
    bay_top = deck_top - cc                               # 456: underside of the deck board
    bay_bot = bay_top - s["bay_h"]                        # 272: bay floor
    xp = L / 2 - 1.0 - cc                                 # inner face of the oak end panels (outer face L/2 - 1)
    return dict(d=d, H=H, g=g, post=post, rail=rail, cc=cc, top_under=top_under, deck_top=deck_top,
                bay_top=bay_top, bay_bot=bay_bot, xp=xp, x_in=L / 2 - post,
                y_front_in=-d / 2 + post / 2 + g / 2, y_track_front=d / 2 - post / 2 - s["track"][1],
                bay_x=xp - 1.0,                           # bay opening half width (1 inside the end panels)
                bay_back=-d / 2 + 1.0 + cc)               # bay back wall = the inner face of the front panel


def _a2_levels(L: float):
    k = _a2_dims(L)
    s = A2
    g = k["g"]
    y0 = k["y_front_in"] + 1.0
    top_clear = k["top_under"] - s["led_channel"][1] - 1.0
    span = top_clear - k["deck_top"]                    # the glass zone, split in two by the one shelf (sheet 16)
    c = (span - g) / 2
    z_s1 = k["deck_top"] + c                            # shelf underside
    return [("Deck", k["deck_top"], y0, k["y_track_front"], c),
            ("S1", z_s1 + g, y0, y0 + s["shelf_d"], top_clear - (z_s1 + g))]


def _a2_bay(L: float):
    """Bay levels (name, z floor, y0, y1, clear): the bay floor and the oak internal shelf (sheet 16)."""
    k = _a2_dims(L)
    s = A2
    tr_h, tr_d = s["bay_track"]
    y1 = k["d"] / 2 - 2.0 - tr_d - 1.0                  # in front of the door track
    mid = k["bay_bot"] + (s["bay_h"] - k["cc"]) / 2     # internal shelf underside
    return [("Bay_01", k["bay_bot"], k["bay_back"], y1, mid - k["bay_bot"]),
            ("Bay_02", mid + k["cc"], k["bay_back"], y1, k["bay_top"] - (mid + k["cc"]))], mid


def _a2_body(L: float, level: int) -> Builder:
    """Sheet 16: recessed black kick; oak cabinet with a cream deck and the rear storage bay (a real pocket);
    full-height oak end panels; aluminium corner posts and top rails; rear glass-door tracks; LED channel under the
    top front rail; bay door tracks and the oak internal shelf."""
    k = _a2_dims(L)
    s = A2
    d, H, post, rail, cc = k["d"], k["H"], k["post"], k["rail"], k["cc"]
    FRAME, BASE, LED, OAK, DECK = 0, 1, 2, 3, 4
    kick, ki = s["kick"], s["kick_inset"]
    xp = k["xp"]
    b = Builder()
    b.box((-L / 2 + ki, -d / 2 + ki, 0), (L / 2 - ki, d / 2 - ki, kick), mat=BASE)                 # kick
    pockets = []
    if level < 2:                                                                                # the bay
        pockets = [dict(face="py", x0=-k["bay_x"], x1=k["bay_x"], z0=k["bay_bot"], z1=k["bay_top"],
                        depth=(d / 2 - 1.0) - k["bay_back"], mat=OAK)]
    # the cabinet runs 10 into the end panels (hidden), so the bay pocket keeps 11 of wall for the bevels
    _pocket_box(b, (-(xp + 10.0), -d / 2 + 1.0, kick - 0.5), (xp + 10.0, d / 2 - 1.0, k["deck_top"]), OAK, pockets,
                mats={"pz": DECK})
    for sx in (-1, 1):                                                                           # oak end panels
        _box(b, (sx * xp, -(d / 2 - post + 0.5), kick - 0.5), (sx * (L / 2 - 1.0), d / 2 - post + 0.5,
                                                                k["top_under"] + 1.5), OAK)
    px, py = L / 2 - post / 2, d / 2 - post / 2
    for sx in (-1, 1):                                                                           # corner posts
        for sy in (-1, 1):
            b.box((sx * px - post / 2, sy * py - post / 2, kick), (sx * px + post / 2, sy * py + post / 2, H),
                  mat=FRAME)
    if level < 2:
        inset = (post - rail) / 2
        zr0, zr1 = H - rail - inset, H - inset
        for sy in (-1, 1):                                                                       # top rails
            b.box((-px - 5.0, sy * py - rail / 2, zr0), (px + 5.0, sy * py + rail / 2, zr1), mat=FRAME)
        for sx in (-1, 1):
            b.box((sx * px - rail / 2, -py - 5.0, zr0), (sx * px + rail / 2, py + 5.0, zr1), mat=FRAME)
        th, td = s["track"]                                                                      # rear door tracks
        yt0 = k["y_track_front"]
        b.box((-xp - 0.5, yt0, k["deck_top"] - 0.5), (xp + 0.5, yt0 + td, k["deck_top"] + th), mat=FRAME)
        b.box((-xp - 0.5, yt0, zr0 - th), (xp + 0.5, yt0 + td, zr0 + 0.5), mat=FRAME)
        cd, ch = s["led_channel"]                                                                # LED channel
        yl = k["y_front_in"] + 3.0
        tu = k["top_under"]
        b.box((-xp - 0.5, yl, tu - ch), (xp + 0.5, yl + cd, tu + 0.5), mat=FRAME)
        b.box((-xp + 2.0, yl + 2.0, tu - ch - 1.0), (xp - 2.0, yl + cd - 2.0, tu - ch + 0.5), mat=LED)
        tr_h, tr_d = s["bay_track"]                                                              # bay door tracks
        bx = k["bay_x"] + 0.5
        yb1 = d / 2 - 2.0
        b.box((-bx, yb1 - tr_d, k["bay_bot"] - 0.5), (bx, yb1, k["bay_bot"] + tr_h), mat=FRAME)
        b.box((-bx, yb1 - tr_d, k["bay_top"] - tr_h), (bx, yb1, k["bay_top"] + 0.5), mat=FRAME)
        (_, _, by0, by1, _), _ = _a2_bay(L)[0]
        mid = _a2_bay(L)[1]
        b.box((-bx, by0 - 0.5, mid), (bx, by1, mid + cc), mat=OAK)                               # bay shelf
    return b


def _a2_glass(L: float) -> Tuple[Builder, List]:
    k = _a2_dims(L)
    s = A2
    g, d = k["g"], k["d"]
    b = Builder()
    yf = -d / 2 + k["post"] / 2 - g / 2
    zt = k["top_under"]
    panes = [((-k["x_in"], yf, k["deck_top"] - 0.5), (k["x_in"], yf + g, zt)),                              # front
             ((-k["xp"] + 0.5, -d / 2 + k["post"], zt + 2.0), (k["xp"] - 0.5, d / 2 - k["post"], zt + 2.0 + g))]  # top
    (_, _, _, _, _), (_, z1, y0, y1, _) = _a2_levels(L)
    xs = k["x_in"] - 1.0                                          # clear of the posts
    panes.append(((-xs, y0, z1 - g), (xs, y1, z1)))                                                           # shelf
    for mn, mx in panes:
        b.box(mn, mx, mat=0)
    cx, cy, cz = s["clip"]                                        # clear support clips on the end panels (sheet 16)
    for sx in (-1, 1):
        for yc in (y0 + 30.0, y1 - 30.0):
            _box(b, (sx * (k["xp"] + 0.5), yc - cy / 2, z1 - g - cz), (sx * (k["xp"] - cx), yc + cy / 2, z1 - g + 1.0),
                 0)
    return b, panes


def _a2_door_size(L: float):
    k = _a2_dims(L)
    th = A2["track"][0]
    return L / 2 + A2["door_overlap"], (k["top_under"] - th) - (k["deck_top"] + th) - 4.0


def _a2_baydoor_size(L: float):
    k = _a2_dims(L)
    tr_h = A2["bay_track"][0]
    w = k["bay_x"] + A2["door_overlap"]                  # half the opening + 25 overlap (as the glass doors)
    return w, (k["bay_top"] - tr_h) - (k["bay_bot"] + tr_h) - 2.0


def item_half(L: float) -> Item:
    k = _a2_dims(L)
    s = A2
    d, H, post = k["d"], k["H"], k["post"]
    lods = [Lod(_a2_body(L, 0), bevel_mm=1.0), Lod(_a2_body(L, 1)), Lod(_a2_body(L, 2))]
    width = 2 * (k["x_in"] - 1.0)
    sockets = [Socket("Seat", (0, 0, 0))]
    ls, levels = _level_sockets(_a2_levels(L), width, 4, True, SHOWCASE_ACCEPTS)
    sockets += ls
    bays, _ = _a2_bay(L)
    bay_data = []
    for name, z, y0, y1, clear in bays:
        sockets.append(Socket(name, (0, (y0 + y1) / 2, z), kind="DISPLAY"))
        bay_data.append({"socket": name, "interior_mm": [round(2 * k["bay_x"], 3), round(y1 - y0, 3)],
                         "clear_h_mm": round(clear, 3), "access": "rear, behind the oak sliding doors"})
    door_w, _ = _a2_door_size(L)
    th, td = s["track"]
    yt0 = k["y_track_front"]
    for side, sx, ty in (("L", -1, yt0 + td * 0.3), ("R", 1, yt0 + td * 0.7)):
        sockets.append(Socket(f"Door_{side}", (sx * (k["x_in"] - door_w / 2), ty, k["deck_top"] + th),
                              (0.0, 0.0, 180.0 if side == "R" else 0.0)))
    bw, _ = _a2_baydoor_size(L)
    tr_h, tr_d = s["bay_track"]
    yb1 = d / 2 - 2.0
    for side, sx, ty in (("L", -1, yb1 - tr_d * 0.72), ("R", 1, yb1 - tr_d * 0.28)):
        sockets.append(Socket(f"BayDoor_{side}", (sx * (k["bay_x"] - bw / 2), ty, k["bay_bot"] + tr_h + 1.0),
                              (0.0, 0.0, 180.0 if side == "R" else 0.0)))
    cd, ch = s["led_channel"]
    sockets += [Socket("LED", (0, k["y_front_in"] + 3.0 + cd / 2, k["top_under"] - ch - 1.0), (180.0, 0.0, 0.0)),
                Socket("Snap_L", (-L / 2, 0, 0)), Socket("Snap_R", (L / 2, 0, 0))]
    travel = L / 2 - s["door_travel_off"]
    bay_travel = 2 * k["bay_x"] - bw
    n = int(L)
    hulls = [((-L / 2, -d / 2, 0), (L / 2, d / 2, k["bay_bot"])),                         # cabinet below the bay
             ((-L / 2, -d / 2, k["bay_top"]), (L / 2, d / 2, k["deck_top"])),             # deck board
             ((-L / 2, -d / 2, k["bay_bot"]), (L / 2, k["bay_back"], k["bay_top"])),       # front panel of the bay
             ((-L / 2, -d / 2, k["deck_top"]), (-k["xp"], d / 2, H - post)),               # end panels (with posts)
             ((k["xp"], -d / 2, k["deck_top"]), (L / 2, d / 2, H - post)),
             ((-L / 2, -d / 2, H - post), (L / 2, d / 2, H))]                             # top frame
    return Item(
        name=f"SM_CSK_Showcase_Half_{n}", lods=lods,
        materials=["M_CSK_Frame", "M_CSK_Base", "M_CSK_LED", "M_CSK_Oak", "M_CSK_Deck"],
        projections={}, sockets=sockets, hulls=hulls, budget=BUDGETS["SM_CSK_Showcase_Half"],
        data={"footprint_mm": [L, d, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(SHOWCASE_ACCEPTS), "levels": levels, "bays": bay_data,
              "parts": {"Door_L": {"mesh": f"SM_CSK_Showcase_Half_Door_{n}", "socket": "Door_L", "type": "slide",
                                   "axis": "X", "range_mm": [0, travel]},
                        "Door_R": {"mesh": f"SM_CSK_Showcase_Half_Door_{n}", "socket": "Door_R", "type": "slide",
                                   "axis": "-X", "range_mm": [0, travel]},
                        "BayDoor_L": {"mesh": f"SM_CSK_Showcase_Half_BayDoor_{n}", "socket": "BayDoor_L",
                                      "type": "slide", "axis": "X", "range_mm": [0, round(bay_travel, 3)]},
                        "BayDoor_R": {"mesh": f"SM_CSK_Showcase_Half_BayDoor_{n}", "socket": "BayDoor_R",
                                      "type": "slide", "axis": "-X", "range_mm": [0, round(bay_travel, 3)]}},
              "glass": f"SM_CSK_Showcase_Half_Glass_{n}",
              "reference": "sheet 16 (csk_showcase_half.png, notes in REFERENCE_LOG.md); family: sheets 6 + 7",
              "notes": ["Sheet 16: one glass shelf + the deck (spec E* said 2 shelves)",
                        "Storage bay 184 clear (spec E*; sheet 16 reads ~250), oak internal shelf splits it",
                        "Carcass slot = M_CSK_Oak (sheet 16: light-oak carcass, the A1 cabinet MI)"]},
    )


def item_half_glass(L: float) -> Item:
    b, panes = _a2_glass(L)
    n = int(L)
    return Item(name=f"SM_CSK_Showcase_Half_Glass_{n}", lods=[Lod(b)], materials=["M_CSK_Glass"], projections={},
                sockets=[], hulls=panes, budget=BUDGETS["SM_CSK_Showcase_Half_Glass"],
                data={"part_of": f"SM_CSK_Showcase_Half_{n}", "attach": "same transform as the body",
                      "notes": ["Front + top panes, one shelf, four clear shelf clips (sheet 16)"]})


def item_half_door(L: float) -> Item:
    w, h = _a2_door_size(L)
    s = A2
    g, st = s["glass"], s["stile"]
    b = _slide_door(w, h, g, st, s["lock"])
    n = int(L)
    return Item(name=f"SM_CSK_Showcase_Half_Door_{n}", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Frame"],
                projections={}, sockets=[Socket("Grip", (w / 2 - st / 2, 0, h / 2))],
                hulls=[((-w / 2, -g / 2 - 1.5, 0), (w / 2, g / 2 + 1.5, h))],
                budget=BUDGETS["SM_CSK_Showcase_Half_Door"],
                data={"part_of": f"SM_CSK_Showcase_Half_{n}", "pivot": "bottom-centre at the closed position",
                      "size_mm": [w, g, h]})


def item_half_baydoor(L: float) -> Item:
    """Sheet 16: the storage bay's oak sliding panel doors with recessed pull handles (a pull on both faces at the
    +X end, so the right door, turned 180 degrees, has its pull at the centre too)."""
    w, h = _a2_baydoor_size(L)
    s = A2
    t = s["bay_door_t"]
    pw, ph, pd = s["pull"]
    xc = w / 2 - 25.0 - pw / 2
    pockets = [dict(face=f, x0=xc - pw / 2, x1=xc + pw / 2, z0=h / 2 - ph / 2, z1=h / 2 + ph / 2, depth=pd)
               for f in ("ny", "py")]
    b = Builder()
    _pocket_box(b, (-w / 2, -t / 2, 0), (w / 2, t / 2, h), 0, pockets)
    n = int(L)
    return Item(name=f"SM_CSK_Showcase_Half_BayDoor_{n}", lods=[Lod(b, bevel_mm=0.5)], materials=["M_CSK_Oak"],
                projections={}, sockets=[Socket("Grip", (xc, t / 2 - pd, h / 2))],
                hulls=[((-w / 2, -t / 2, 0), (w / 2, t / 2, h))], budget=BUDGETS["SM_CSK_Showcase_Half_BayDoor"],
                data={"part_of": f"SM_CSK_Showcase_Half_{n}", "pivot": "bottom-centre at the closed position",
                      "size_mm": [w, t, h],
                      "notes": ["New part (not in the spec's mesh list): the bay doors must slide to reach Bay_01..02"]})


# =========================================================================== A3 frameless glass tower (sheet 17)

def _a3_dims() -> Dict:
    s = A3
    W, D, H, g, e = s["w"], s["d"], s["h"], s["glass"], s["inset"]
    xo = W / 2 - e                        # glass outer faces
    xi = xo - g                           # glass inner faces (sides); the back pane's inner face is D/2 - e - g
    top0 = H - 1.5 - g                    # top pane underside (its top 1.5 under the corner clip caps)
    ps, pc = s["pole"]
    xr, yr = xi - 0.5, (D / 2 - e - g) - 0.5      # the pole's outer corner (back right), 0.5 off the glass
    return dict(W=W, D=D, H=H, g=g, xo=xo, xi=xi, yo=D / 2 - e, yi=D / 2 - e - g, top0=top0, base=s["base"],
                xr=xr, yr=yr, ps=ps, pc=pc, y_door_in=-D / 2 + e + g)


def _a3_levels():
    k = _a3_dims()
    s = A3
    g = k["g"]
    y0, y1 = k["y_door_in"] + 3.0, k["yi"] - 1.0
    lv = []
    zs = [k["base"] + s["pitch"] * i for i in range(s["shelves"] + 1)]     # level floors (shelf tops)
    for i, z in enumerate(zs):
        top = zs[i + 1] - g if i + 1 < len(zs) else k["top0"] - 1.0
        lv.append((f"L{i + 1}", z, y0, y1, top - z))
    return lv


def _a3_body(level: int) -> Builder:
    """Sheet 17 (1): light-oak base with a flush black band and the cream deck; a thin aluminium light pole with an
    LED strip in the back-right corner; metal shelf clips wrapping the side panes; metal corner clips at the fixed
    glass corners (the door's hinge corners carry the door's patch fittings instead)."""
    k = _a3_dims()
    s = A3
    W, D, H, g = k["W"], k["D"], k["H"], k["g"]
    OAK, BASE, DECK, METAL, FRAME, LED = 0, 1, 2, 3, 4, 5
    b = Builder()
    _banded_block(b, -W / 2, W / 2, -D / 2, D / 2, (0.0, s["band"], k["base"]), (BASE, OAK), DECK, BASE)
    xr, yr, ps, pc = k["xr"], k["yr"], k["ps"], k["pc"]
    pole = [(xr - ps + pc, yr - ps), (xr, yr - ps), (xr, yr), (xr - ps, yr), (xr - ps, yr - ps + pc)]
    b.prism(pole, k["base"] - 0.5, k["top0"] - 0.5, mat=FRAME)
    if level < 2:
        lw, lp = s["pole_led"]                     # LED strip on the chamfer, facing the case diagonal
        n = (-math.sqrt(0.5), -math.sqrt(0.5))
        mx_, my_ = xr - ps + pc / 2, yr - ps + pc / 2
        t = (-n[1], n[0])
        pts = [(mx_ + t[0] * lw / 2 + n[0] * a, my_ + t[1] * lw / 2 + n[1] * a) for a in (-0.5, lp)]
        pts += [(mx_ - t[0] * lw / 2 + n[0] * a, my_ - t[1] * lw / 2 + n[1] * a) for a in (lp, -0.5)]
        area = sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))
        b.prism(pts if area > 0 else list(reversed(pts)), k["base"] + 40.0, k["top0"] - 40.0, mat=LED)
    if level < 2:                                  # shelf clips: 4 per shelf, wrapping the side panes
        cx, cy, cz = s["clip"]
        yf, yb = -D / 2 + 60.0, D / 2 - 60.0
        for name, z, *_ in _a3_levels()[1:]:
            zb = z - g
            for sx in (-1, 1):
                for yc in (yf, yb):
                    _box(b, (sx * (k["xo"] + 1.5), yc - cy / 2, zb - cz), (sx * (k["xi"] - cx), yc + cy / 2, zb + 1.0),
                         METAL)
    cl, ch = s["corner"]                           # corner clips (level 2 keeps them: they carry the silhouette)
    for sx, sy in ((-1, 1), (1, 1), (1, -1)):
        for top in (True, False):
            leg = cl if sy > 0 else (W / 2 - 0.5) - (k["xi"] - 1.0)     # front: clear of the door leaf
            x0, x1 = sx * (W / 2 - 0.5), sx * (W / 2 - 0.5 - leg)
            y0, y1 = sy * (D / 2 - 0.5), sy * (D / 2 - 0.5 - cl)
            z0, z1 = (k["top0"] - ch, H) if top else (k["base"] - 0.5, k["base"] + ch)
            _box(b, (x0, y0, z0), (x1, y1, z1), METAL)
    return b


def _a3_door_geom():
    """Door frame: origin on the hinge axis at the door's bottom; the leaf runs +X from the hinge side."""
    k = _a3_dims()
    s = A3
    gap = s["gap"]
    xl, xr_ = -(k["xi"] - gap), k["xi"] - gap           # the leaf between the side panes
    pp = s["patch"][2]
    w = xr_ - xl
    z0 = k["base"] + gap
    h = (k["top0"] - gap) - z0
    y = -k["D"] / 2 + s["inset"] - pp                    # the patch fittings' front face
    return dict(w=w, h=h, pp=pp, axis=(xl, y, z0))


def item_tower() -> Item:
    k = _a3_dims()
    s = A3
    W, D, H = k["W"], k["D"], k["H"]
    lods = [Lod(_a3_body(0), bevel_mm=0.8), Lod(_a3_body(1)), Lod(_a3_body(2))]
    width = 2 * (k["xi"] - 1.0)
    ls, levels = _level_sockets(_a3_levels(), width, 2, False, SHOWCASE_ACCEPTS)
    dg = _a3_door_geom()
    ax = dg["axis"]
    lock_x = ax[0] + dg["w"] - 24.0
    mx_, my_ = k["xr"] - k["ps"] + k["pc"] / 2, k["yr"] - k["ps"] + k["pc"] / 2
    sockets = [Socket("Seat", (0, 0, 0))] + ls + [
        Socket("Door", ax),
        Socket("Lock", (lock_x, ax[1] - s["lock"][1], ax[2] + dg["h"] / 2)),
        Socket("LED", (mx_ - 2.0, my_ - 2.0, (k["base"] + k["top0"]) / 2), (90.0, 0.0, -45.0))]
    return Item(
        name="SM_CSK_Showcase_Tower", lods=lods,
        materials=["M_CSK_Oak", "M_CSK_Base", "M_CSK_Deck", "M_CSK_Metal", "M_CSK_Frame", "M_CSK_LED"],
        projections={}, sockets=sockets,
        hulls=[((-W / 2, -D / 2, 0), (W / 2, D / 2, k["base"])),
               ((k["xr"] - k["ps"], k["yr"] - k["ps"], k["base"]), (k["xr"], k["yr"], k["top0"]))],
        budget=BUDGETS["SM_CSK_Showcase_Tower"],
        data={"footprint_mm": [W, D, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(SHOWCASE_ACCEPTS), "levels": levels,
              "parts": {"Door": {"mesh": "SM_CSK_Showcase_Tower_Door", "socket": "Door", "type": "hinge",
                                 "axis": "Z", "range_deg": [0, 100], "open_rot_deg": [0.0, 0.0, -100.0]}},
              "glass": "SM_CSK_Showcase_Tower_Glass",
              "reference": "sheet 17 (1) (csk_tower_wallcase.png, notes in REFERENCE_LOG.md); sheet 6 right",
              "notes": ["Sheet 17: light pole in the back corner (not in the spec) is part of this mesh",
                        "The base top is the cream deck (M_CSK_Deck), as A1"]},
    )


def item_tower_glass() -> Item:
    k = _a3_dims()
    s = A3
    W, D, H, g = k["W"], k["D"], k["H"], k["g"]
    b = Builder()
    zb = k["base"] - 1.0                                   # panes sit 1 mm into the base
    zt = k["top0"] - 0.5
    panes = [((-k["xo"], -k["yo"], zb), (-k["xi"], k["yo"], zt)),                          # left
             ((k["xi"], -k["yo"], zb), (k["xo"], k["yo"], zt)),                            # right
             ((-k["xi"] + 0.5, k["yi"], zb), (k["xi"] - 0.5, k["yo"], zt)),                # back
             ((-k["xo"], -k["yo"], k["top0"]), (k["xo"], k["yo"], k["top0"] + g))]         # top
    for mn, mx in panes:
        b.box(mn, mx, mat=0)
    x1 = k["xi"] - 1.0
    nx, ny = k["xr"] - k["ps"] - 1.0, k["yr"] - k["ps"] - 1.0
    for name, z, y0, y1, _ in _a3_levels()[1:]:           # shelves, notched round the light pole
        outline = [(-x1, y0), (x1, y0), (x1, ny), (nx, ny), (nx, y1), (-x1, y1)]
        b.prism(outline, z - g, z, mat=0)
        panes.append(((-x1, y0, z - g), (x1, y1, z)))
    return Item(name="SM_CSK_Showcase_Tower_Glass", lods=[Lod(b)], materials=["M_CSK_Glass"], projections={},
                sockets=[], hulls=panes, budget=BUDGETS["SM_CSK_Showcase_Tower_Glass"],
                data={"part_of": "SM_CSK_Showcase_Tower", "attach": "same transform as the body",
                      "notes": ["3 side panes + top + 4 shelves = 8 hulls (spec E said 7): one per pane",
                                "The top pane is glass (the tower is frameless; sheet 17's corner clips hold it)"]})


def item_tower_door() -> Item:
    """Sheet 17: the hinged front glass door with chrome patch hinges at its top and bottom hinge-side corners and a
    round cylinder lock on the free edge at mid height. The pivot is the patch fittings' front hinge-side edge, so
    the whole door swings out and away from the side pane (nothing crosses x < -0.5 locally)."""
    s = A3
    dg = _a3_door_geom()
    g = A3["glass"]
    w, h, pp = dg["w"], dg["h"], dg["pp"]
    GLASS, METAL = 0, 1
    b = Builder()
    b.box((0.0, pp, 0), (w, pp + g, h), mat=GLASS)
    pl, pz, _, _ = s["patch"]
    for z0, z1 in ((-1.0, pz), (h - pz, h + 1.0)):
        b.box((-0.5, 0.0, z0), (pl, g + 2 * pp, z1), mat=METAL)
    ld, lp = s["lock"]
    xl = w - 24.0
    b.box((xl - 16.0, 0.0, h / 2 - 18.0), (w + 1.0, g + 2 * pp, h / 2 + 18.0), mat=METAL)
    _cyl_y(b, xl, h / 2, ld / 2, -lp, 0.5, 12, METAL)
    return Item(name="SM_CSK_Showcase_Tower_Door", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Metal"],
                projections={}, sockets=[Socket("Grip", (xl, -lp, h / 2))],
                hulls=[((-0.5, 0.0, -1.0), (w + 1.0, g + 2 * pp, h + 1.0))],
                budget=BUDGETS["SM_CSK_Showcase_Tower_Door"],
                data={"part_of": "SM_CSK_Showcase_Tower",
                      "pivot": "hinge axis (Z) on the patch fittings' front hinge-side edge, at the door's bottom",
                      "size_mm": [w, g, h]})


# =========================================================================== A4 lit framed wall case (sheet 17)

def _a4_dims() -> Dict:
    s = A4
    L, d, H, g, post, rail = s["w"], s["d"], s["h"], s["glass"], s["post"], s["rail"]
    x_in = L / 2 - post - 0.5                        # the posts stand 0.5 in from the base faces
    yt0 = -d / 2 + post / 2 + 0.5                    # front face of the front door tracks (the post centre line)
    return dict(L=L, d=d, H=H, g=g, post=post, rail=rail, base=s["base"], x_in=x_in, top_under=H - rail,
                yt0=yt0, y_track_back=yt0 + s["track"][1], y_back_in=d / 2 - post / 2 - 0.5 - g / 2,
                x_side_in=L / 2 - post / 2 - 0.5 - g / 2)


def _a4_levels():
    k = _a4_dims()
    s = A4
    g = k["g"]
    wd, dp = S.SHOWCASE_FULL["standard"]
    y0, y1 = k["y_track_back"] + 1.0, k["y_back_in"] - 1.0
    top = k["top_under"] - 1.0
    n = s["shelves"]
    c = (top - k["base"] - n * g) / (n + 1)
    lv = []
    for i in range(n + 1):
        z = k["base"] + i * (c + g)
        lv.append((f"L{i + 1}", z, y0, y1, c))
    return lv


def _a4_body(level: int) -> Builder:
    """Sheet 17 (2): light-oak base with a flush black band and the cream deck; the aluminium frame (posts standing
    on the base, top rails); front door tracks with the sliding-door lock at the centre of the bottom track; warm
    LED strips on the front posts' inner faces."""
    k = _a4_dims()
    s = A4
    L, d, H, post, rail = k["L"], k["d"], k["H"], k["post"], k["rail"]
    FRAME, BASE, LED, OAK, DECK = 0, 1, 2, 3, 4
    b = Builder()
    _banded_block(b, -L / 2, L / 2, -d / 2, d / 2, (0.0, s["band"], k["base"]), (BASE, OAK), DECK, BASE)
    px, py = L / 2 - post / 2 - 0.5, d / 2 - post / 2 - 0.5        # posts 0.5 in from the base faces
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * px - post / 2, sy * py - post / 2, k["base"]), (sx * px + post / 2, sy * py + post / 2, H),
                  mat=FRAME)
    inset = (post - rail) / 2                                       # top rails (LOD2 too: the silhouette)
    zr0, zr1 = H - rail - inset, H - inset
    for sy in (-1, 1):
        b.box((-px - 5.0, sy * py - rail / 2, zr0), (px + 5.0, sy * py + rail / 2, zr1), mat=FRAME)
    for sx in (-1, 1):
        b.box((sx * px - rail / 2, -py - 5.0, zr0), (sx * px + rail / 2, py + 5.0, zr1), mat=FRAME)
    if level < 2:
        th, td = s["track"]
        yt0 = k["yt0"]
        b.box((-k["x_in"] - 2.0, yt0, k["base"] - 0.5), (k["x_in"] + 2.0, yt0 + td, k["base"] + th), mat=FRAME)
        b.box((-k["x_in"] - 2.0, yt0, zr0 - th), (k["x_in"] + 2.0, yt0 + td, zr0 + 0.5), mat=FRAME)
        lx, ly, lz, ldia = s["lock"]                                # sliding-door lock on the bottom track
        b.box((-lx / 2, yt0 - ly + 3.0, k["base"] - 0.5), (lx / 2, yt0 + 3.0, k["base"] + lz), mat=FRAME)
        _cyl_y(b, 0.0, k["base"] + lz / 2, ldia / 2, yt0 - ly - 1.0, yt0 - ly + 3.5, 12, FRAME)
        lw, lp = s["led"]                                           # LED strips on the front posts
        for sx in (-1, 1):
            xf = sx * (px - post / 2)
            _box(b, (xf + sx * 0.5, -d / 2 + 4.0, k["base"] + 25.0), (xf - sx * lp, -d / 2 + 4.0 + lw,
                                                                      zr0 - 25.0), LED)
    return b


def _a4_parts(level: int) -> Optional[Builder]:
    """Slotted standards on the side posts in the back corners with steel pins, plus the tower's metal clips on the
    side glass at the front (after the bevel: crisp; slots on LOD0 only)."""
    if level == 2:
        return None
    k = _a4_dims()
    s = A4
    FRAME = 0
    g = k["g"]
    wd, dp = S.SHOWCASE_FULL["standard"]
    pw, pl = S.SHOWCASE_FULL["pin"]
    b = Builder()
    yc = k["y_back_in"] - 1.0 - wd / 2
    x_post = k["L"] / 2 - k["post"] - 0.5                          # the side posts' inner faces
    cx, cy, cz = s["clip"]
    yf = k["y_track_back"] + 30.0 + cy / 2
    for sx in (-1, 1):
        _slotted_standard(b, sx, x_post, yc, k["base"], k["top_under"] - 2.0, slots=(level == 0), mat=FRAME)
        for name, z, *_ in _a4_levels()[1:]:
            zb = z - g
            x0 = sx * (x_post - dp)
            _box(b, (x0 + sx * 0.5, yc - pw / 2, zb - pw), (x0 - sx * pl, yc + pw / 2, zb), FRAME)
            _box(b, (sx * (k["x_side_in"] + g + 1.5), yf - cy / 2, zb - cz),
                 (sx * (k["x_side_in"] - cx), yf + cy / 2, zb + 1.0), FRAME)
    return b


def _a4_door_size():
    k = _a4_dims()
    th = A4["track"][0]
    return A4["door_w"], (k["top_under"] - (k["post"] - k["rail"]) / 2 - th) - (k["base"] + th) - 4.0


def item_wall() -> Item:
    k = _a4_dims()
    s = A4
    L, d, H = k["L"], k["d"], k["H"]
    lods = [Lod(_a4_body(0), bevel_mm=1.0, extra=_a4_parts(0)), Lod(_a4_body(1), extra=_a4_parts(1)),
            Lod(_a4_body(2))]
    wd, dp = S.SHOWCASE_FULL["standard"]
    width = 2 * (k["L"] / 2 - k["post"] - 0.5 - dp - 1.0)
    ls, levels = _level_sockets(_a4_levels(), width, 3, False, SHOWCASE_ACCEPTS)
    door_w, _ = _a4_door_size()
    th, td = s["track"]
    sockets = [Socket("Seat", (0, 0, 0))] + ls
    for side, sx, ty in (("L", -1, k["yt0"] + td * 0.3), ("R", 1, k["yt0"] + td * 0.7)):
        sockets.append(Socket(f"Door_{side}", (sx * (k["x_in"] - door_w / 2), ty, k["base"] + th)))
    lx, ly, lz, ldia = s["lock"]
    sockets += [Socket("Lock", (0, k["yt0"] - ly - 1.0, k["base"] + lz / 2)),
                Socket("LED", (0, 0, k["top_under"] - 2.0), (180.0, 0.0, 0.0)),
                Socket("Snap_L", (-L / 2, 0, 0)), Socket("Snap_R", (L / 2, 0, 0))]
    travel = L / 2 - s["door_travel_off"]
    lw, lp = s["led"]
    px = L / 2 - k["post"] - 0.5
    return Item(
        name="SM_CSK_Showcase_Wall_1016", lods=lods,
        materials=["M_CSK_Frame", "M_CSK_Base", "M_CSK_LED", "M_CSK_Oak", "M_CSK_Deck"],
        projections={}, sockets=sockets,
        hulls=[((-L / 2, -d / 2, 0), (L / 2, d / 2, k["base"])),
               ((-L / 2, -d / 2, H - k["post"]), (L / 2, d / 2, H))],
        budget=BUDGETS["SM_CSK_Showcase_Wall"],
        data={"footprint_mm": [L, d, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(SHOWCASE_ACCEPTS), "levels": levels,
              "parts": {"Door_L": {"mesh": "SM_CSK_Showcase_Wall_Door_1016", "socket": "Door_L", "type": "slide",
                                   "axis": "X", "range_mm": [0, travel]},
                        "Door_R": {"mesh": "SM_CSK_Showcase_Wall_Door_1016", "socket": "Door_R", "type": "slide",
                                   "axis": "-X", "range_mm": [0, travel]}},
              "glass": "SM_CSK_Showcase_Wall_Glass_1016",
              "led_strips_mm": [[[sx * px, -d / 2 + 4.0 + lw / 2, k["base"] + 25.0],
                                 [sx * px, -d / 2 + 4.0 + lw / 2, H - k["rail"] - 27.5]] for sx in (-1, 1)],
              "reference": "sheet 17 (2) (csk_tower_wallcase.png, notes in REFERENCE_LOG.md); family: sheets 6 + 7",
              "notes": ["LED socket: top centre, pointing down; the two post strips are listed in led_strips_mm",
                        "Standards in the back corners (sheet 17); the shelves' front corners rest on the tower's "
                        "glass clips (a shelf needs 4 supports)"]},
    )


def item_wall_glass() -> Item:
    k = _a4_dims()
    s = A4
    L, d, g, post = k["L"], k["d"], k["g"], k["post"]
    b = Builder()
    zb, zt = k["base"] - 0.5, k["top_under"]
    panes = []
    for sx in (-1, 1):                                                                    # sides
        xo = sx * (L / 2 - post / 2 - 0.5)
        panes.append(((min(xo - sx * g / 2, xo + sx * g / 2), -d / 2 + post - 0.5, zb),
                      (max(xo - sx * g / 2, xo + sx * g / 2), d / 2 - post + 0.5, zt)))
    yb = d / 2 - post / 2 - 0.5
    panes.append(((-k["x_in"] + 0.5, yb - g / 2, zb), (k["x_in"] - 0.5, yb + g / 2, zt)))    # back
    panes.append(((-k["x_in"] + 0.5, -d / 2 + post, zt + 2.0), (k["x_in"] - 0.5, d / 2 - post, zt + 2.0 + g)))  # top
    wd, dp = S.SHOWCASE_FULL["standard"]
    xs = L / 2 - post - 0.5 - dp - 1.0
    for name, z, y0, y1, _ in _a4_levels()[1:]:
        panes.append(((-xs, y0, z - g), (xs, y1, z)))
    for mn, mx in panes:
        b.box(mn, mx, mat=0)
    return Item(name="SM_CSK_Showcase_Wall_Glass_1016", lods=[Lod(b)], materials=["M_CSK_Glass"], projections={},
                sockets=[], hulls=panes, budget=BUDGETS["SM_CSK_Showcase_Wall_Glass"],
                data={"part_of": "SM_CSK_Showcase_Wall_1016", "attach": "same transform as the body",
                      "notes": ["2 sides + back + top + 4 shelves = 8 panes and hulls (spec E said 6)"]})


def item_wall_door() -> Item:
    w, h = _a4_door_size()
    s = A4
    g, st = s["glass"], s["stile"]
    b = _slide_door(w, h, g, st, None)
    return Item(name="SM_CSK_Showcase_Wall_Door_1016", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Frame"],
                projections={}, sockets=[Socket("Grip", (w / 2 - st / 2, 0, h / 2))],
                hulls=[((-w / 2, -g / 2 - 1.5, 0), (w / 2, g / 2 + 1.5, h))], budget=BUDGETS["SM_CSK_Showcase_Wall_Door"],
                data={"part_of": "SM_CSK_Showcase_Wall_1016", "pivot": "bottom-centre at the closed position",
                      "size_mm": [w, g, h], "notes": ["The lock is on the bottom track (body), sheet 17"]})


# =========================================================================== A5 countertop case (sheet 18)

def _a5_dims() -> Dict:
    s = A5
    L, d, H, g, post, rail = s["w"], s["d"], s["h"], s["glass"], s["post"], s["rail"]
    top = H - s["lid_h"]                                  # body top = the lid's seat and the hinge axis height
    deck = s["kick"] + s["base"]
    r, st, sw, _ = s["stay"]
    xs1 = L / 2 - post - 0.5                             # stay: 0.5 inboard of the corner posts
    return dict(L=L, d=d, H=H, g=g, post=post, rail=rail, top=top, deck=deck, rail_bot=top - 0.5 - rail,
                x_in=L / 2 - post, y_in=d / 2 - post / 2 - g / 2, x_glass_in=L / 2 - post / 2 - g / 2,
                hinge=(d / 2 + 1.0, top + 1.0), xs=(xs1 - st, xs1))


def _a5_levels():
    k = _a5_dims()
    y = k["y_in"] - 1.0
    return [("Deck", k["deck"], -y, y, k["rail_bot"] - k["deck"] - 1.0)]


def _a5_body(level: int) -> Builder:
    """Sheet 18 (1): recessed black kick and the oak band (the counters' base), dark felt deck, aluminium corner
    posts and top rim rails; the lid's quadrant-stay guides under the end rails (LOD0-1)."""
    k = _a5_dims()
    s = A5
    L, d, post, rail = k["L"], k["d"], k["post"], k["rail"]
    FRAME, BASE, OAK, FELT = 0, 1, 2, 3
    kick, ki = s["kick"], s["kick_inset"]
    b = Builder()
    b.box((-L / 2 + ki, -d / 2 + ki, 0), (L / 2 - ki, d / 2 - ki, kick), mat=BASE)
    b.box((-L / 2 + 1.0, -d / 2 + 1.0, kick - 0.5), (L / 2 - 1.0, d / 2 - 1.0, k["deck"]), mat=OAK,
          mats={"pz": FELT})
    px, py = L / 2 - post / 2, d / 2 - post / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * px - post / 2, sy * py - post / 2, kick), (sx * px + post / 2, sy * py + post / 2, k["top"]),
                  mat=FRAME)
    zr0, zr1 = k["rail_bot"], k["top"] - 0.5
    for sy in (-1, 1):
        b.box((-px - 2.0, sy * py - rail / 2, zr0), (px + 2.0, sy * py + rail / 2, zr1), mat=FRAME)
    if level < 2:
        for sx in (-1, 1):
            b.box((sx * px - rail / 2, -py - 2.0, zr0), (sx * px + rail / 2, py + 2.0, zr1), mat=FRAME)
        r, st, sw, _ = s["stay"]
        gx, gy, gz = s["guide"]
        yh, zh = k["hinge"]
        xs0, xs1 = k["xs"]
        for sx in (-1, 1):                                   # guides: the stay passes vertically through them
            xg = L / 2 - k["post"] / 2 - k["rail"] / 2 + 0.5       # 0.5 into the end rail
            _box(b, (sx * xg, yh - r - gy / 2, zr0 - gz), (sx * (xg - gx), yh - r + gy / 2, zr0 + 0.5), FRAME)
    return b


def item_counter() -> Item:
    k = _a5_dims()
    s = A5
    L, d, H = k["L"], k["d"], k["H"]
    lods = [Lod(_a5_body(0), bevel_mm=0.8), Lod(_a5_body(1)), Lod(_a5_body(2))]
    width = 2 * (k["xs"][0] - 1.0)
    ls, levels = _level_sockets(_a5_levels(), width, 3, True, COUNTER_ACCEPTS)
    yh, zh = k["hinge"]
    sockets = [Socket("Seat", (0, 0, 0))] + ls + [
        Socket("Lid", (0, yh, zh)),
        Socket("Lock", (0, -d / 2, k["top"]))]
    return Item(
        name="SM_CSK_Case_Counter_900", lods=lods,
        materials=["M_CSK_Frame", "M_CSK_Base", "M_CSK_Oak", "M_CSK_Felt"],
        projections={}, sockets=sockets,
        hulls=[((-L / 2, -d / 2, 0), (L / 2, d / 2, k["deck"]))], budget=BUDGETS["SM_CSK_Case_Counter"],
        data={"footprint_mm": [L, d, H], "pose": "upright", "pivot": "bottom-centre",
              "accepts": list(COUNTER_ACCEPTS), "levels": levels,
              "parts": {"Lid": {"mesh": "SM_CSK_Case_Counter_Lid_900", "socket": "Lid", "type": "hinge",
                                "axis": "X", "range_deg": [0, s["stay"][3]],
                                "open_rot_deg": [-s["stay"][3], 0.0, 0.0]}},
              "glass": "SM_CSK_Case_Counter_Glass_900",
              "reference": "sheet 18 (1) (csk_counter_case_wallslab.png, notes in REFERENCE_LOG.md)",
              "notes": ["Built to the spec size 900 x 450 x 300 (sheet 18's silhouette reads about twice that)",
                        "Lock socket kept (spec) at the front rim centre; no lock is modelled (not in the notes)",
                        "Sheet 18's short version (about a third of the length) is not built (not in the spec)"]},
    )


def item_counter_glass() -> Item:
    k = _a5_dims()
    L, d, g, post = k["L"], k["d"], k["g"], k["post"]
    b = Builder()
    zb, zt = k["deck"] - 0.5, k["rail_bot"] + 0.5
    yf = d / 2 - post / 2
    xg = L / 2 - post / 2
    panes = [((-k["x_in"], -yf - g / 2, zb), (k["x_in"], -yf + g / 2, zt)),              # front
             ((-k["x_in"], yf - g / 2, zb), (k["x_in"], yf + g / 2, zt)),                # back
             ((-xg - g / 2, -d / 2 + post, zb), (-xg + g / 2, d / 2 - post, zt)),        # ends
             ((xg - g / 2, -d / 2 + post, zb), (xg + g / 2, d / 2 - post, zt))]
    for mn, mx in panes:
        b.box(mn, mx, mat=0)
    return Item(name="SM_CSK_Case_Counter_Glass_900", lods=[Lod(b)], materials=["M_CSK_Glass"], projections={},
                sockets=[], hulls=panes, budget=BUDGETS["SM_CSK_Case_Counter_Glass"],
                data={"part_of": "SM_CSK_Case_Counter_900", "attach": "same transform as the body"})


def item_counter_lid() -> Item:
    """Sheet 18 (1): the glass lid in an aluminium frame, hinged at the back (a continuous hinge barrel just behind
    the rear top edge), held by two quadrant side stays: arcs round the hinge axis that slide through the body's
    guides, so they follow the lid at every angle. Frame: origin on the hinge axis, 1 behind and 1 above the rear
    top edge; closed, the lid covers y in [-D - 1, -1], z in [-1, lid_h - 1]."""
    k = _a5_dims()
    s = A5
    L, d, g = k["L"], k["d"], k["g"]
    lh, lr = s["lid_h"], s["lid_rail"]
    GLASS, FRAME = 0, 1
    b = Builder()
    outer = rect(L, d, 0.0, -d / 2 - 1.0)
    inner = rect(L - 2 * lr, d - 2 * lr, 0.0, -d / 2 - 1.0)
    _ring(b, outer, inner, -1.0, lh - 1.0, FRAME)
    zg = lh - 4.0 - g
    b.box((-L / 2 + lr - 3.0, -d - 1.0 + lr - 3.0, zg), (L / 2 - lr + 3.0, -1.0 - lr + 3.0, zg + g), mat=GLASS)
    _cyl_x(b, 0.0, 0.0, s["hinge_r"], -L / 2 + 40.0, L / 2 - 40.0, 6, FRAME)
    r, st, sw, travel = s["stay"]
    xs0, xs1 = k["xs"]
    phis = [-2.5 + (travel + 2.5) * i / 4 for i in range(5)]
    for sx in (-1, 1):
        # lid-local arc: point at angle p is (y, z) = (-r cos p, -r sin p) round the axis (0, 0); _arc_x measures
        # p from straight below, so this is its angle 90 - p mirrored in y
        _arc_x(b, 0.0, 0.0, r, sw, min(sx * xs0, sx * xs1), max(sx * xs0, sx * xs1), [-(90.0 - p) for p in phis],
               FRAME)
    return Item(name="SM_CSK_Case_Counter_Lid_900", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Frame"],
                projections={}, sockets=[Socket("Grip", (0, -d - 1.0, lh / 2 - 1.0))],
                hulls=[((-L / 2, -d - 1.0, -1.0), (L / 2, -1.0, lh - 1.0))], budget=BUDGETS["SM_CSK_Case_Counter_Lid"],
                data={"part_of": "SM_CSK_Case_Counter_900", "pivot": "hinge axis (X) on the rear top edge",
                      "size_mm": [L, d, lh], "stay": {"radius_mm": r, "travel_deg": travel}})


# =========================================================================== A6 wall slab case (sheet 18)

def _a6_dims() -> Dict:
    s = A6
    W, D, H, f = s["w"], s["d"], s["h"], s["frame"]
    yf = -D + s["door_zone"]                            # the frame's front face
    zt = H / 2 - f                                      # the top member's underside
    return dict(W=W, D=D, H=H, f=f, yf=yf, xi=W / 2 - f, zi0=-H / 2 + f, zi1=zt, ybp=-1.0 - s["back_t"],
                axis=(yf - 1.0 - s["hinge_r"], zt - s["hinge_r"] - 1.0))


def _a6_rows():
    """Per row: the slab's bottom-back edge B (y, z), the socket (y, z). Slabs lean ``lean`` back, their top back
    edge 1 mm off the back panel."""
    k = _a6_dims()
    s = A6
    lean = math.radians(s["lean"])
    sh = S.SLAB_STD["h"]
    ybb = k["ybp"] - 1.0 - sh * math.sin(lean)
    pitch = (k["zi1"] - k["zi0"]) / s["rows"]
    rows = []
    for r in range(s["rows"]):
        zb = k["zi0"] + 17.5 + r * pitch
        seat = (ybb + sh / 2 * math.sin(lean), zb + sh / 2 * math.cos(lean))
        rows.append(((ybb, zb), seat))
    return rows


def _a6_ledge_outline(B):
    """The acrylic ledge profile (y, z) for a slab whose bottom-back edge is B: a floor square to the leaning slab,
    a lip in front of it, the back edge let into the back panel."""
    k = _a6_dims()
    s = A6
    lean = math.radians(s["lean"])
    ft, lip_h, lip_t, clr = s["ledge"]
    u = (-math.cos(lean), math.sin(lean))              # toward the customer, square to the slab
    n = (math.sin(lean), math.cos(lean))               # up the slab
    st = S.SLAB_STD["t"]
    P = lambda a, c: (B[0] + a * u[0] + c * n[0], B[1] + a * u[1] + c * n[1])
    yb = k["ybp"] + 0.5                                # 0.5 into the panel
    def at_y(c):                                       # the point on the line c = const at y = yb
        a = (B[0] + c * n[0] - yb) / math.cos(lean)
        return P(a, c)
    a_in, a_out = st + clr, st + clr + lip_t
    return [at_y(-ft), P(a_out, -ft), P(a_out, lip_h), P(a_in, lip_h), P(a_in, 0.0), at_y(0.0)]


def _a6_body(level: int) -> Builder:
    """Sheet 18 (2): aluminium perimeter frame, light-oak back panel, 4 slanted clear acrylic ledges, LED strips on
    the side members' inner faces, the fixed knuckles of the top hinge."""
    k = _a6_dims()
    s = A6
    W, D, H, f = k["W"], k["D"], k["H"], k["f"]
    FRAME, OAK, LED, ACRYL = 0, 1, 2, 3
    yf = k["yf"]
    b = Builder()
    for sx in (-1, 1):
        _box(b, (sx * W / 2, yf, -H / 2), (sx * k["xi"], 0.0, H / 2), FRAME)                       # side members
    for sz in (-1, 1):
        _box(b, (-k["xi"] - 0.5, yf + 0.5, sz * (H / 2 - 0.5)), (k["xi"] + 0.5, -0.5, sz * (H / 2 - f)), FRAME)
    b.box((-k["xi"] - 0.5, k["ybp"], k["zi0"] - 0.5), (k["xi"] + 0.5, -1.0, k["zi1"] + 0.5), mat=OAK)   # back
    xl = k["xi"] + 0.5
    for B, _ in _a6_rows():
        _prism_x(b, _a6_ledge_outline(B), -xl, xl, ACRYL)
    if level < 2:
        lw, lp = s["led"]
        for sx in (-1, 1):
            _box(b, (sx * (k["xi"] + 0.5), yf + 6.0, k["zi0"] + 15.0), (sx * (k["xi"] - lp), yf + 6.0 + lw,
                                                                         k["zi1"] - 15.0), LED)
        ya, za = k["axis"]
        hr = s["hinge_r"]
        for sx in (-1, 1):                              # fixed hinge knuckles + their leaves up the top member
            x0, x1 = sx * (k["xi"] - 30.0), sx * (k["xi"] - 1.0)
            _cyl_x(b, ya, za, hr, min(x0, x1), max(x0, x1), 8, FRAME)
            _box(b, (x0, yf - 2.5, za), (x1, yf + 1.0, k["zi1"] + 15.0), FRAME)
    return b


def item_wallslab() -> Item:
    k = _a6_dims()
    s = A6
    W, D, H = k["W"], k["D"], k["H"]
    lods = [Lod(_a6_body(0), bevel_mm=0.6), Lod(_a6_body(1)), Lod(_a6_body(2))]
    sockets = [Socket("Seat", (0, 0, 0))]
    names = []
    rows = _a6_rows()
    for r, (_, (ys, zs)) in enumerate(rows):
        for c in range(s["cols"]):
            x = (c - (s["cols"] - 1) / 2) * s["pitch_x"]
            nm = f"Slot_R{r + 1}_{c + 1:02d}"
            names.append(nm)
            sockets.append(Socket(nm, (x, ys, zs), (90.0 - s["lean"], 0.0, 0.0), kind="DISPLAY"))
    ya, za = k["axis"]
    sockets += [Socket("Door", (0, ya, za)),
                Socket("Lock", (0, -D, -H / 2 + k["f"] / 2)),
                Socket("LED", (0, (k["yf"] + k["ybp"]) / 2, k["zi1"] - 2.0), (180.0, 0.0, 0.0)),
                Socket("Snap_L", (-W / 2, 0, 0)), Socket("Snap_R", (W / 2, 0, 0))]
    yf = k["yf"]
    return Item(
        name="SM_CSK_Case_WallSlab", lods=lods,
        materials=["M_CSK_Frame", "M_CSK_Oak", "M_CSK_LED", "M_CSK_Acrylic"], projections={}, sockets=sockets,
        hulls=[((-W / 2, k["ybp"], -H / 2), (W / 2, 0.0, H / 2)),                        # back panel
               ((-W / 2, yf, -H / 2), (-k["xi"], 0.0, H / 2)), ((k["xi"], yf, -H / 2), (W / 2, 0.0, H / 2)),
               ((-W / 2, yf, k["zi1"]), (W / 2, 0.0, H / 2)), ((-W / 2, yf, -H / 2), (W / 2, 0.0, k["zi0"]))],
        budget=BUDGETS["SM_CSK_Case_WallSlab"],
        data={"footprint_mm": [W, D, H], "pose": "wall-mounted",
              "pivot": "Seat = the centre of the back face (the face it rests on: the wall)",
              "accepts": ["Slab"],
              "slots": {"class": "Slab", "sockets": names, "pose": f"leaning {s['lean']:g} deg back (socket rot X)",
                        "cavity_mm": [[-k["xi"], yf, k["zi0"]], [k["xi"], k["ybp"], k["zi1"]]]},
              "parts": {"Door": {"mesh": "SM_CSK_Case_WallSlab_Door", "socket": "Door", "type": "hinge",
                                 "axis": "X", "range_deg": [0, s["open_deg"]],
                                 "open_rot_deg": [-s["open_deg"], 0.0, 0.0]}},
              "reference": "sheet 18 (2) (csk_counter_case_wallslab.png, notes in REFERENCE_LOG.md)",
              "notes": ["Built to the spec size 1000 x 90 x 700 (sheet 18's silhouette reads about twice that)",
                        "Back = light oak (sheet 18; the spec's 'Back (felt)' slot: the picture wins)",
                        "Opens to horizontal, 0-90 (sheet 18; spec E 0-85)",
                        "46 sockets: the spec's 40 fixed slots + Door, Lock, LED, Snap_L, Snap_R + Seat",
                        "Lock socket kept (spec); no lock is modelled (not in the notes)",
                        "The sheet's door stays are not modelled: see the family report"]},
    )


def item_wallslab_door() -> Item:
    """Sheet 18 (2): the glass front on a top hinge. The barrel sits 6 in front of the frame just under the top
    member, between the two fixed knuckles; an aluminium clamp rail joins it to the glass, which hangs below it and
    covers the frame's sides and bottom. Frame: origin on the hinge axis. Every point stays in front of the frame
    (y < the frame face) through the whole swing."""
    k = _a6_dims()
    s = A6
    W, D, H, g = k["W"], k["D"], k["H"], s["glass"]
    ya, za = k["axis"]
    hr = s["hinge_r"]
    GLASS, FRAME = 0, 1
    y_front = -D + 0.5                                  # the glass front face, 0.5 inside the footprint
    gy0, gy1 = y_front - ya, y_front + g - ya           # local
    zb = (-H / 2 + 1.0) - za
    zg = -hr - 8.0                                      # glass top: under the fixed knuckles
    xr = k["xi"] - 31.0                                 # barrel and clamp rail half length
    b = Builder()
    b.box((-W / 2 + 1.0, gy0, zb), (W / 2 - 1.0, gy1, zg), mat=GLASS)
    b.box((-xr, gy0 - 1.5, zg - 6.0), (xr, gy1 + 1.5, -1.0), mat=FRAME)
    _cyl_x(b, 0.0, 0.0, hr, -xr, xr, 8, FRAME)
    return Item(name="SM_CSK_Case_WallSlab_Door", lods=[Lod(b)], materials=["M_CSK_Glass", "M_CSK_Frame"],
                projections={}, sockets=[Socket("Grip", (0, gy0, zb + 20.0))],
                hulls=[((-W / 2 + 1.0, gy0, zb), (W / 2 - 1.0, hr, hr))], budget=BUDGETS["SM_CSK_Case_WallSlab_Door"],
                data={"part_of": "SM_CSK_Case_WallSlab", "pivot": "hinge axis (X) at the top front",
                      "size_mm": [W - 2.0, g, -zb + hr]})


# =========================================================================== registry

ITEMS = {
    "a_cases_half_1219": lambda: item_half(1219.0),
    "a_cases_half_glass_1219": lambda: item_half_glass(1219.0),
    "a_cases_half_door_1219": lambda: item_half_door(1219.0),
    "a_cases_half_baydoor_1219": lambda: item_half_baydoor(1219.0),
    "a_cases_half_1778": lambda: item_half(1778.0),
    "a_cases_half_glass_1778": lambda: item_half_glass(1778.0),
    "a_cases_half_door_1778": lambda: item_half_door(1778.0),
    "a_cases_half_baydoor_1778": lambda: item_half_baydoor(1778.0),
    "a_cases_tower": item_tower,
    "a_cases_tower_glass": item_tower_glass,
    "a_cases_tower_door": item_tower_door,
    "a_cases_wall": item_wall,
    "a_cases_wall_glass": item_wall_glass,
    "a_cases_wall_door": item_wall_door,
    "a_cases_counter": item_counter,
    "a_cases_counter_glass": item_counter_glass,
    "a_cases_counter_lid": item_counter_lid,
    "a_cases_wallslab": item_wallslab,
    "a_cases_wallslab_door": item_wallslab_door,
}
