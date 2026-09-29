"""Family ij_shell: signage and decor (CARDSHOP_KIT_SPEC.md 3.I I1-I5) and the shop shell, entry door and lights
(3.J J1-J3; J4 the scale figure is dropped by the user). Reference sheets 30-34: References/CardShop/csk_signs_tags.png,
csk_posters_storefront.png, csk_shell.png, csk_entry_door.png, csk_lights.png; notes in REFERENCE_LOG.md
"Sheet 30..34 notes".

Flags as in spec.py: M = measured (source key), D = derived, E = estimate / design choice. "sheet N" = the value or
the form was measured off that reference sheet (the picture wins over E; a printed call-out wins over the picture).

Frames: millimetres, +X to the viewer's right, +Y away from the customer (the back), +Z up.
* Wall-hung items (posters, storefront sign, the window sign's suction cup): Seat = the centre of the back face on
  the wall / glass plane (y = 0); the item stands out toward -Y.
* Ceiling-hung items (hanging sign, lights): Seat = the ceiling contact (z = 0); the item hangs below.
* Shell modules: an end-corner pivot (HOUSE, ASSET_GUIDELINES.md 1): walls x 0..2000 with the shop (interior) face at
  y = 0 and the outside face at y = 150; floor top and ceiling underside at z = 0.
* The door frame fits the Wall_Door opening in the wall's own frame (interior face y = 0); the leaf, the sign plate
  and the track spot are separate meshes pivoting on their hinge / flip / tilt axes.
No bpy here: pure data through shapes.Builder.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .geom import R_BACK, R_FRONT, Item, Lod, Socket, _face_out, inset
from .shapes import Builder, circle, rect

Vec3 = Tuple[float, float, float]

# =========================================================================== budgets

# LOD0 budgets: the spec's Tris column (E). Changes, logged in the report and the item notes:
#   Sign_OpenClosed_Plate 60 -> 150: sheet 30 draws R6 corners and two cord holes; the holes alone are 64 tris.
#   PriceTag_Hook 80 -> 90: sheet 30's clip barrel is round (8 sides; 6 read as a hex nut).
#   Sign_Hanging 100 -> 150: sheet 30 draws two cable suspenders with ceiling cups and grippers on an aluminium frame.
#   TrackHead 400 is split 150 (adapter + stem, fixed) + 250 (the tilting spot): the spec's "the head pivots on its
#     tilt axis" needs the tilting body as its own mesh (moving parts ship separately).
#   Shell_Wall_Window_2000_Glass (new, 100): fixed panes live in their own _Glass mesh (spec 4.5).
BUDGETS = {
    "SM_CSK_Sign_OpenClosed": 300, "SM_CSK_Sign_OpenClosed_Plate": 150,
    "SM_CSK_PriceTag_Shelf": 80, "SM_CSK_PriceTag_Tent": 80, "SM_CSK_PriceTag_Hook": 90,
    "SM_CSK_Poster_A2": 200, "SM_CSK_Poster_A1": 200,
    "SM_CSK_Sign_Storefront": 400,
    "SM_CSK_Sign_Hanging": 150,
    "SM_CSK_Shell_Wall_2000": 600, "SM_CSK_Shell_Wall_Window_2000": 600, "SM_CSK_Shell_Wall_Window_2000_Glass": 100,
    "SM_CSK_Shell_Wall_Door_2000": 600, "SM_CSK_Shell_Floor_2000": 600, "SM_CSK_Shell_Ceiling_2000": 600,
    "SM_CSK_Door_Entry": 800, "SM_CSK_Door_Entry_Frame": 400,
    "SM_CSK_Light_Panel600": 200, "SM_CSK_Light_Track2000": 300, "SM_CSK_Light_TrackHead": 150,
    "SM_CSK_Light_TrackHead_Spot": 250, "SM_CSK_Light_Pendant": 600,
}

# =========================================================================== numbers

SIGN = dict(                       # I1, sheet 30 (1)
    plate=(300.0, 150.0, 5.0),     # E (spec) = sheet 30 (a 2:1 plate)
    corner_r=6.0,                  # sheet 30: 12 px at 2.07 px/mm
    hole=(9.0, 29.0, 14.0),        # sheet 30: hole diameter, centre in from the side, down from the top
    cup=(70.0, 8.0),               # sheet 30: suction cup diameter (150 px at 2.07 px/mm); height E
    tab=(14.0, 12.0),              # sheet 30: the cup's pull tab below its rim: width, length
    hook=(22.0, 36.0, 6.0),        # sheet 30: hook tab width, drop from the cup centre to the cord (75 px), thickness E
    lip=(5.0, 8.0),                # sheet 30: the hook's forward lip that holds the cord: reach, height (E)
    drop=141.0,                    # sheet 30: the cord drops 141 from the hook to the plate top (292 px)
    y_plate=-14.0,                 # E: the plate hangs 14 off the glass (mid thickness)
    cord_r=1.5,                    # sheet 30: a 3 mm black cord
    knot=4.0,                      # sheet 30: the knot above each hole (radius)
    flip_deg=(0.0, 180.0),         # spec: the plate flips 180 deg about Z
)

TAG_SHELF = dict(                  # I2 shelf-edge strip clip, sheet 30 (2)
    w=76.0,                        # E (spec) = sheet 30
    insert=(70.0, 32.0, 0.4),      # E (spec 32 = the label) / sheet 30: the white insert W x H x T
    t=1.2,                         # E: the clear extrusion's wall
    face_y=-13.0,                  # sheet 30 side view: the front panel stands 13 off the shelf face (9.4 px/mm)
    face_h=47.0,                   # sheet 30: the front panel's height (360 px at 7.57 px/mm), the top curl included
    flange=16.0,                   # sheet 30: the top flange runs 16 back over the shelf top
    tongue=25.0,                   # sheet 30: the clip tongue runs 25 down the shelf's front face
    lip=(3.0, 3.0),                # sheet 30: the J curl at the bottom that holds the insert: reach, height
    chamfer=1.0,                   # E: the rounded top curl, as a chamfer
)

TAG_TENT = dict(                   # I2 folded tent card, sheet 30 (2)
    w=60.0, slant=40.0,            # E (spec 60 x 40) = sheet 30 (the face reads 1.5 : 1)
    half_angle=20.0,               # sheet 30: each face leans about 20 deg off vertical
    t=1.5,                         # E: clear A-frame wall
    card=(56.0, 0.4),              # sheet 30: the white folded insert (a 2 mm clear rim at the sides): W x T
    ridge=0.8,                     # E: the clear fold's flat
)

TAG_HOOK = dict(                   # I2 hook scan plate, sheet 30 (2)
    w=76.0, h=38.0, t=3.0,         # E (spec 76 x 38) = sheet 30; T E
    r=3.0,                         # sheet 30: rounded corners
    insert=(70.0, 32.0, 0.4),      # sheet 30: the white insert inside the clear sleeve
    barrel=(9.0, 10.0),            # sheet 30: the clip barrel on the left edge that takes the hook tip: dia, length
)

POSTER = dict(                     # I3, sheet 31 (1)
    sizes={"A2": (420.0, 594.0), "A1": (594.0, 841.0)},   # E (spec, ISO 216) = sheet 31 call-outs (outer frame)
    face=20.0,                     # sheet 31: the frame's face width (24 px at 1.18 px/mm)
    depth=16.0,                    # sheet 31 corner detail: the profile is about as deep as it is wide (E 16)
    chamfer=(1.5, 0.8),            # sheet 31: the rounded outer front edge and the fine inner edge, as chamfers (E)
    recess=3.0,                    # E: the poster lies 3 below the frame face
    mitre_gap=0.25,                # sheet 31: the mitred corners read as a fine line (each bar stops 0.25 short)
)

STOREFRONT = dict(                 # I4, sheet 31 (2)
    w=1829.0, d=100.0, h=457.0,    # E (spec) = sheet 31 call-outs
    bezel=(12.0, 8.0),             # sheet 31: the black frame's face width, and the diffuser's recess behind it
    standoff=12.0,                 # sheet 31: the box stands off the wall by the bracket plates' thickness (E 12)
    plate=(70.0, 12.0),            # sheet 31: the wall plates: width (26 px at 0.38 px/mm), thickness E
    arm=(100.0, 40.0),             # sheet 31: arm length from the box end to the plate (84-115), square section (E)
    arm_z=0.25,                    # sheet 31: arms at 1/4 and 3/4 of the height (perspective corrected)
    bolt=(12.0, 5.0, 35.0),        # sheet 31: two bolt heads per plate: dia, proud, in from the plate ends
)

HANGING = dict(                    # I5, sheet 30 (3)
    w=600.0, t=10.0,               # E (spec)
    h=145.0,                       # sheet 30: the panel reads 4.15 : 1 (spec 200 E; the picture wins, width kept)
    frame=5.0,                     # sheet 30: the thin aluminium frame's face width
    panel_recess=1.5,              # E: the printed panel sits 1.5 inside the frame on each face
    cable_x=250.0,                 # sheet 30: the suspenders stand about 50 in from each end
    cable=(0.8, 100.0),            # sheet 30: steel cable radius (E), drop between cup and gripper (96 mm)
    cup=(8.5, 15.0),               # sheet 30: ceiling cup radius, height (17 x 15)
    gripper=(6.0, 25.0),           # sheet 30: cable gripper radius, height (12 x 25, E 20-25)
)

WALL = dict(                       # J1, sheet 32
    w=2000.0, t=150.0, h=3000.0,   # E (spec) = sheet 32 call-outs
    skirting=(150.0, 10.0),        # sheet 32: black skirting 150 tall; proud 10 (E) on the shop face
    window=(1600.0, 2400.0, 300.0),  # sheet 32 window module: frame outer W x H, sill height (centred in X)
    win_frame=(50.0, 70.0),        # sheet 32: black frame face width (45-50), depth E (centred in the wall)
    mullion=(0.35, 0.25),          # sheet 32: the mullion stands 35 % across from the left, the transom 25 % down
    glass=10.0,                    # E: the glazing unit's thickness
    glass_pocket=10.0,             # E: panes run 10 into the frame
    door=(600.0, 1000.0, 2200.0),  # sheet 32: the opening starts 600 from the left end (both views), 1000 x 2200
)

FLOOR = dict(w=2000.0, t=20.0, edge=1.5)          # E (spec); sheet 32: a fine join = a 1.5 chamfer on the top edges
CEILING = dict(
    w=2000.0, t=20.0,              # E (spec)
    tiles=2,                       # sheet 32 notes: white acoustic tiles 2 x 2 per module
    bar=24.0,                      # E: T-bar face (15/16 in); half bars on the module edges, so modules join to 24
    step=3.0,                      # sheet 32 detail: the tile face sits 3 above the bar face
)

DOOR = dict(                       # J2, sheet 33
    frame=(1000.0, 150.0, 2200.0),  # E (spec) = sheet 33 call-outs
    leaf=(900.0, 45.0, 2100.0),    # E (spec) = sheet 33 call-outs
    gap=3.0,                       # E: leaf clearance at the jambs and the head
    threshold=(5.0, 3.0),          # sheet 33: a stainless threshold plate: thickness; the leaf clears it by 3 (E)
    stop=15.0,                     # sheet 33 top view: the leaf closes against a 15 stop behind it
    stile=(80.0, 80.0, 100.0),     # sheet 33: leaf stiles, top rail, bottom rail face widths
    bead=(12.0, 12.5),             # sheet 33: the glazing bead: width, recess from each face (E)
    glass=10.0,                    # E
    axis_off=8.0,                  # E: the hinge axis stands 8 in front of the leaf's outside face
    hinges=((300.0, 1000.0, 1710.0), 120.0, 7.0, 23.0),  # sheet 33: 3 hinge centres (from the floor), knuckle
                                   # length, knuckle radius, leaf width (E)
    pull=(105.0, 760.0, 15.0, 52.0, 1000.0, 10.0, 40.0),  # sheet 33: bar centre from the free edge, length, radius,
                                   # stand-off to the bar axis, centre height, post radius, posts in from the bar ends
    bell=(39.0, 72.0, 29.0, 4.5),  # sheet 33: bell rim radius, body height, backplate radius, backplate thickness
                                   # (scaled to the header: the sheet's bell is as tall as the header)
    open_deg=(0.0, 100.0),         # E (spec)
)

PANEL = dict(w=600.0, t=12.0, frame=10.0, recess=1.0)   # J3, sheet 34 (1): E (spec) = call-outs; frame sheet 34

TRACK = dict(                      # J3, sheet 34 (2)
    l=2000.0,                      # E (spec) = sheet 34
    w=20.0, h=35.0,                # sheet 34: the section inset reads 20 wide, the rail 35 tall (spec 35 x 20 E:
                                   # the picture wins)
    wall=2.0, slot=8.0, lip=2.0,   # sheet 34 section: channel wall, bottom slot width, lip height (E)
    heads=6,                       # E (spec): Head_01..06 at fixed, even spacing
)

HEAD = dict(                       # J3, sheet 34 (2) detail
    puck=(15.0, 22.0),             # sheet 34: round adapter: radius, height
    stem=(4.5, 40.0),              # sheet 34: stem radius, length
    body=(35.0, 150.0),            # E (spec) = sheet 34 call-outs: radius, length
    knuckle=(50.0, 6.0, 16.0, 5.0),  # sheet 34: the stem meets the body 1/3 from its rear: distance from the rear,
                                   # barrel radius, barrel length, gap above the body
    bezel=(4.0, 22.0, 13.0),       # sheet 34: front bezel ring width, reflector depth, reflector bottom radius
    tilt=(0.0, 90.0, 45.0),        # E: tilt range (0 = aimed level at -Y, + = down) and the sheet's display pose
)

PENDANT = dict(                    # J3, sheet 34 (3)
    shade=(150.0, 250.0),          # E (spec) = sheet 34 call-outs: rim radius, height
    # sheet 34 (measured row by row at 1.96 mm/px): the dome's radius fraction at height fractions
    prof=((0.0, 1.0), (0.25, 0.98), (0.5, 0.915), (0.68, 0.835), (0.8, 0.74), (0.9, 0.6), (0.97, 0.42),
          (1.0, 0.2)),
    wall=1.2,                      # E: spun steel
    collar=(31.0, 38.0),           # sheet 34: the cord collar on the dome: radius, height
    cord=(3.0, 1000.0),            # sheet 34: cord radius (6 mm) and the printed 1000 drop
    canopy=(50.0, 30.0),           # sheet 34 detail: round ceiling canopy radius, height
    segs=(16, 12, 8),
)

# =========================================================================== small maths


def _v3(a: Sequence[float]) -> Vec3:
    return (float(a[0]), float(a[1]), float(a[2]))


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    return (a[0] / n, a[1] / n, a[2] / n)


def _area2(poly) -> float:
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


# the natural 2D axes (u, v) of a prism along each axis t, and t itself
AXES = {"x": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),     # (y, z)
        "y": ((1, 0, 0), (0, 0, 1), (0, 1, 0)),     # (x, z)
        "z": ((1, 0, 0), (0, 1, 0), (0, 0, 1))}     # (x, y)


def _pt(axis: str, u: float, v: float, t: float) -> Vec3:
    U, V, T = AXES[axis]
    return (u * U[0] + v * V[0] + t * T[0], u * U[1] + v * V[1] + t * T[1], u * U[2] + v * V[2] + t * T[2])


def _dir(axis: str, du: float, dv: float, dt: float = 0.0) -> Vec3:
    return _pt(axis, du, dv, dt)


def _extrude(b: Builder, axis: str, outer, t0: float, t1: float, mat: int = 0, holes: Sequence = (),
             side_mats: Optional[Sequence[int]] = None, hole_mats: Optional[Sequence[int]] = None,
             cap_mats: Optional[Tuple[int, int]] = None, cap_regions: Tuple[int, int] = (0, 0),
             caps: Tuple[bool, bool] = (True, True)) -> None:
    """A prism along ``axis`` from t0 < t1 of the 2D outline ``outer`` (counter-clockwise in the axis's natural
    (u, v): x-prism (y, z), y-prism (x, z), z-prism (x, y)) with optional holes (also counter-clockwise). Windings come
    from the outward directions, so the caller never orders faces. ``side_mats`` per outer edge (edge i = point i to
    i + 1), ``hole_mats`` per hole, ``cap_mats`` / ``cap_regions`` = (t0 cap, t1 cap)."""
    assert t1 > t0
    polys = [(list(outer), False)] + [(list(h), True) for h in holes]
    rings0, rings1 = [], []
    T = AXES[axis][2]
    for k, (poly, is_hole) in enumerate(polys):
        assert _area2(poly) > 0, f"outline {k} is not counter-clockwise"
        r0 = [b.v(*_pt(axis, u, v, t0)) for u, v in poly]
        r1 = [b.v(*_pt(axis, u, v, t1)) for u, v in poly]
        rings0.append(r0)
        rings1.append(r1)
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            du, dv = poly[j][0] - poly[i][0], poly[j][1] - poly[i][1]
            nrm = _dir(axis, dv, -du)                  # right of the edge = outside for a CCW outline
            if is_hole:
                nrm = _mul(nrm, -1.0)
                m = hole_mats[k - 1] if hole_mats else mat
            else:
                m = side_mats[i] if side_mats else mat
            _face_out(b, [r0[i], r0[j], r1[j], r1[i]], nrm, m)
    cm = cap_mats or (mat, mat)
    if caps[0]:
        b.fill(rings0, cm[0], cap_regions[0], _mul(T, -1.0))
    if caps[1]:
        b.fill(rings1, cm[1], cap_regions[1], T)


def _box(b: Builder, mn, mx, mat: int = 0, **kw) -> None:
    b.box(_v3(mn), _v3(mx), mat=mat, **kw)


def _cyl(b: Builder, axis: str, cu: float, cv: float, r: float, t0: float, t1: float, segs: int, mat: int = 0,
         caps=(True, True), phase: float = 0.0) -> None:
    pts = [(cu + r * math.cos(phase + 2 * math.pi * i / segs), cv + r * math.sin(phase + 2 * math.pi * i / segs))
           for i in range(segs)]
    _extrude(b, axis, pts, t0, t1, mat, caps=caps)


def _revolve(b: Builder, axis: str, cu: float, cv: float, profile, segs: int, mats, side: int = 1,
             phase: float = 0.0, regions=None) -> None:
    """Revolve the polyline ``profile`` [(r, t), ...] about the line (cu, cv) along ``axis``. Points with r = 0 are
    single apex vertices. ``side`` +1: the surface faces the right of the profile's direction in (r, t) (outward
    for a profile running up the outside from the rim), -1 the left. ``mats`` / ``regions`` per profile segment."""
    U, V, T = AXES[axis]
    rings = []
    for r, t in profile:
        if r < 1e-9:
            rings.append([b.v(*_pt(axis, cu, cv, t))])
        else:
            rings.append([b.v(*_pt(axis, cu + r * math.cos(phase + 2 * math.pi * i / segs),
                                    cv + r * math.sin(phase + 2 * math.pi * i / segs), t)) for i in range(segs)])
    for k in range(len(profile) - 1):
        (r0, t0), (r1, t1) = profile[k], profile[k + 1]
        nr, nt = side * (t1 - t0), -side * (r1 - r0)
        m = mats[k] if isinstance(mats, (list, tuple)) else mats
        reg = regions[k] if regions else 0
        a, c = rings[k], rings[k + 1]
        for i in range(segs):
            j = (i + 1) % segs
            ang = phase + 2 * math.pi * (i + 0.5) / segs
            radial = _add(_mul(U, math.cos(ang)), _mul(V, math.sin(ang)))
            nrm = _add(_mul(radial, nr), _mul(T, nt))
            if len(a) == 1 and len(c) == 1:
                continue
            if len(a) == 1:
                ids = [a[0], c[i], c[j]]
            elif len(c) == 1:
                ids = [a[i], a[j], c[0]]
            else:
                ids = [a[i], a[j], c[j], c[i]]
            _face_out(b, ids, nrm, m, reg)


def _rod(b: Builder, p0: Vec3, p1: Vec3, r: float, sides: int, mat: int = 0, caps=(True, True)) -> None:
    """A closed ``sides``-gon prism of radius r from p0 to p1 (cords, cables, bars at any angle)."""
    d = _unit(_sub(p1, p0))
    ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    e1 = _unit(_cross(d, ref))
    e2 = _cross(d, e1)
    ring = lambda p: [b.v(*_add(p, _add(_mul(e1, r * math.cos(2 * math.pi * i / sides)),
                                         _mul(e2, r * math.sin(2 * math.pi * i / sides))))) for i in range(sides)]
    a, c = ring(p0), ring(p1)
    for i in range(sides):
        j = (i + 1) % sides
        ang = 2 * math.pi * (i + 0.5) / sides
        nrm = _add(_mul(e1, math.cos(ang)), _mul(e2, math.sin(ang)))
        _face_out(b, [a[i], a[j], c[j], c[i]], nrm, mat)
    if caps[0]:
        _face_out(b, a, _mul(d, -1.0), mat)
    if caps[1]:
        _face_out(b, c, d, mat)


def _octa(b: Builder, c: Vec3, r: float, mat: int = 0) -> None:
    """A small octahedron (a knot, a clapper)."""
    x, y, z = c
    px, nx, py, ny, pz, nz = (b.v(x + r, y, z), b.v(x - r, y, z), b.v(x, y + r, z), b.v(x, y - r, z),
                              b.v(x, y, z + r), b.v(x, y, z - r))
    for sx, vx in ((1, px), (-1, nx)):
        for sy, vy in ((1, py), (-1, ny)):
            for sz, vz in ((1, pz), (-1, nz)):
                _face_out(b, [vx, vy, vz], (sx, sy, sz), mat)


def _proj_xz(x0: float, z0: float, w: float, h: float, tile_u: float = 0.0, tile_v: float = 0.0,
             mirror: bool = False):
    """A planar print map of the rect (x0, z0, w, h) in XZ onto one 0-1 tile, for faces seen from -Y (``mirror`` for
    faces seen from +Y, so the art reads the right way round)."""
    def proj(x, y, z):
        u = (x - x0) / w
        if mirror:
            u = 1.0 - u
        return (tile_u + inset(u), tile_v + inset((z - z0) / h))
    return proj


def _lod_segs(level: int, s0: int, s1: int, s2: int) -> int:
    return (s0, s1, s2)[level]


# =========================================================================== I1 open/closed window sign (sheet 30)

def _sign_geom():
    s = SIGN
    pw, ph, pt = s["plate"]
    hd, hx, hz = s["hole"]
    z_hook = -s["hook"][1]
    z_top = z_hook - s["drop"]                   # the plate's top edge (below the cup centre)
    return dict(pw=pw, ph=ph, pt=pt, hr=hd / 2, hx=pw / 2 - hx, hz=hz, z_hook=z_hook, z_top=z_top, yp=s["y_plate"])


def _sign_hanger(level: int) -> Builder:
    """The suction cup (a shallow clear dome with a pull tab), the clear J hook, and the black cord: from the hook
    down to a knot over each hole, then down both faces of the plate into the hole (sheet 30)."""
    s, k = SIGN, _sign_geom()
    PVC, CORD = 0, 1
    b = Builder()
    cr, ch = s["cup"][0] / 2, s["cup"][1]
    segs = _lod_segs(level, 16, 8, 6)
    # the cup: back disc on the glass (y 0), a 1.5 rim, a shallow cone, a small flat nose
    _revolve(b, "y", 0.0, 0.0, [(0.0, 0.0), (cr, 0.0), (cr, -1.5), (10.0, -ch), (0.0, -ch)], segs, PVC, side=-1)
    tw, tl = s["tab"]
    if level < 2:
        _box(b, (-tw / 2, -1.3, -cr - tl), (tw / 2, -0.3, -cr + 6.0), PVC)            # pull tab
    hw, hd_, ht = s["hook"]
    lr, lh = s["lip"]
    yb = -ch + 0.5                                                                    # hook back face (in the nose)
    zb = k["z_hook"] - 3.0                                                            # hook bottom
    # the hook tab (sheet 30: a flat tab with a round top, from just above the cup centre down to the lip)
    tr = hw / 2
    na = (5, 2, 1)[level]
    tab_o = [(-tr, zb), (tr, zb)] + [(tr * math.cos(math.pi * i / na), 12.0 - tr + tr * math.sin(math.pi * i / na))
                                     for i in range(na + 1)]
    _extrude(b, "y", tab_o, yb - ht, yb, PVC)
    if level < 2:
        _box(b, (-hw / 2, yb - ht - lr, zb), (hw / 2, yb - ht + 0.5, zb + lh), PVC)   # its forward lip
    yc = yb - ht - lr / 2                                                             # the cord rests in the lip
    top = (0.0, yc, k["z_hook"])
    sides = 4 if level == 0 else 3
    cr_ = s["cord_r"]
    for sx in (-1, 1):
        x = sx * k["hx"]
        knot = (x, k["yp"], k["z_top"] + s["knot"] + 1.0)
        _rod(b, top, knot, cr_, sides, CORD)
        if level == 0:
            _octa(b, knot, s["knot"], CORD)
        if level == 0:                                                                # over the edge into the hole
            zh = k["z_top"] - k["hz"]
            for yy in (k["yp"] - k["pt"] / 2 - cr_, k["yp"] + k["pt"] / 2 + cr_):
                _rod(b, (x, yy, knot[2]), (x, yy, zh), cr_, 3, CORD)
    return b


def item_sign_openclosed() -> Item:
    s, k = SIGN, _sign_geom()
    cr = s["cup"][0] / 2
    lods = [Lod(_sign_hanger(i)) for i in range(3)]
    return Item(
        name="SM_CSK_Sign_OpenClosed", lods=lods, materials=["M_CSK_PVC", "M_CSK_Cord"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)),
                 Socket("Plate", (0.0, k["yp"], k["z_top"]))],
        hulls=[((-cr, -26.0, -cr - s["tab"][1]), (cr, 0.0, cr))],
        budget=BUDGETS["SM_CSK_Sign_OpenClosed"],
        data={"footprint_mm": [k["pw"], 26.0, cr - k["z_top"] + k["ph"]], "pose": "on glass",
              "pivot": "Seat = Mount = the suction cup's centre on the glass (y 0); the sign hangs toward -Y",
              "parts": {"Plate": {"mesh": "SM_CSK_Sign_OpenClosed_Plate", "socket": "Plate", "type": "hinge",
                                  "axis": "Z", "range_deg": list(s["flip_deg"]),
                                  "open_rot_deg": [0.0, 0.0, s["flip_deg"][1]]}},
              "reference": "sheet 30 (1) (csk_signs_tags.png, notes in REFERENCE_LOG.md)",
              "notes": ["Sheet 30: a black cord on a clear suction cup with a hook (spec 'chain + suction hook, "
                        "Metal': the picture wins, so the slots are PVC + Cord)",
                        "The cord is knotted over each hole and runs over the plate's top edge into the hole on "
                        "both faces; the plate is symmetric under its 180 deg flip, so the cord fits both ways"]},
    )


def item_sign_openclosed_plate() -> Item:
    s, k = SIGN, _sign_geom()
    pw, ph, pt = k["pw"], k["ph"], k["pt"]
    b = Builder()
    r = s["corner_r"]
    pts = []
    for cx, cz, a0 in ((pw / 2 - r, -ph + r, -90.0), (pw / 2 - r, -r, 0.0), (-pw / 2 + r, -r, 90.0),
                       (-pw / 2 + r, -ph + r, 180.0)):
        for i in range(4):
            a = math.radians(a0 + 30.0 * i)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    holes = [[(sx * k["hx"] + k["hr"] * math.cos(2 * math.pi * i / 8 + math.pi / 8),
               -k["hz"] + k["hr"] * math.sin(2 * math.pi * i / 8 + math.pi / 8)) for i in range(8)]
             for sx in (-1, 1)]
    # front (-Y, region FRONT) = the cap at t0; back (+Y, region BACK) = the cap at t1
    _extrude(b, "y", pts, -pt / 2, pt / 2, 0, holes=holes, cap_regions=(R_FRONT, R_BACK))
    return Item(
        name="SM_CSK_Sign_OpenClosed_Plate", lods=[Lod(b)], materials=["M_CSK_Sign"],
        projections={R_FRONT: _proj_xz(-pw / 2, -ph, pw, ph),
                     R_BACK: _proj_xz(-pw / 2, -ph, pw, ph, tile_u=1.0, mirror=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Face", (0, -pt / 2, -ph / 2), (90.0, 0.0, 0.0))],
        hulls=[((-pw / 2, -pt / 2, -ph), (pw / 2, pt / 2, 0.0))],
        budget=BUDGETS["SM_CSK_Sign_OpenClosed_Plate"],
        data={"part_of": "SM_CSK_Sign_OpenClosed", "footprint_mm": [pw, pt, ph],
              "pivot": "the flip axis (Z) at the top edge's centre, mid thickness",
              "print": "Signs atlas: front (-Y) tile (0,0) = OPEN, back (+Y) tile (1,0) = CLOSED",
              "notes": ["Budget 60 -> 150: sheet 30's R6 corners and two cord holes"]},
    )


# =========================================================================== I2 price tags (sheet 30)

def _tag_sockets(face: Vec3, rot: Vec3, normal: Vec3) -> List[Socket]:
    return [Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)), Socket("Face", face, rot),
            Socket("Text", _add(face, _mul(normal, 0.5)), rot)]


def item_pricetag_shelf() -> Item:
    """Sheet 30: a clear extrusion that hooks over the shelf edge: a top flange on the shelf top, a tongue down the
    shelf's front face, and a front panel standing 13 off it with a J curl at the bottom that holds the white
    insert. Mount = the shelf's front top edge (y 0 = the shelf face, z 0 = the shelf top)."""
    s = TAG_SHELF
    w, t, yf, fh, fl, tg, c = s["w"], s["t"], s["face_y"], s["face_h"], s["flange"], s["tongue"], s["chamfer"]
    lr, lh = s["lip"]
    iw, ih, it = s["insert"]
    PVC, INS = 0, 1
    yo = yf - t                                     # the front panel's outer face
    prof = [(yo, -fh + t), (yf + lr, -fh + t), (yf + lr, -fh + t + lh), (yf + lr - t, -fh + t + lh),
            (yf + lr - t, -fh + 2 * t), (yf, -fh + 2 * t), (yf, 0.0), (-t, 0.0), (-t, -tg), (0.0, -tg),
            (0.0, 0.0), (fl, 0.0), (fl, t), (yo + c, t), (yo, t - c)]
    # (y, z) in the x-prism's natural axes; make it counter-clockwise
    if _area2(prof) < 0:
        prof.reverse()
    b = Builder()
    _extrude(b, "x", prof, -w / 2, w / 2, PVC)
    zi0 = -fh + 2 * t + 0.3
    _box(b, (-iw / 2, yf + 0.1, zi0), (iw / 2, yf + 0.1 + it, zi0 + ih), INS, regions={"ny": R_FRONT})
    face = (0.0, yf + 0.1, zi0 + ih / 2)
    return Item(
        name="SM_CSK_PriceTag_Shelf", lods=[Lod(b)], materials=["M_CSK_PVC", "M_CSK_PriceTag"],
        projections={R_FRONT: _proj_xz(-iw / 2, zi0, iw, ih)},
        sockets=_tag_sockets(face, (90.0, 0.0, 0.0), (0, -1, 0)),
        hulls=[((-w / 2, yo, -fh + t), (w / 2, fl, t))],
        budget=BUDGETS["SM_CSK_PriceTag_Shelf"],
        data={"footprint_mm": [w, fl - yo, fh], "pose": "clipped over a shelf edge",
              "pivot": "Seat = Mount = the shelf's front top edge (y 0 shelf face, z 0 shelf top), centred",
              "digits": {"face": "Face", "rect_mm": [-iw / 2, zi0, iw, ih]},
              "reference": "sheet 30 (2) (csk_signs_tags.png)",
              "notes": ["Sheet 30: the clip hooks over the shelf edge (a flange on top, a tongue down the face); "
                        "its front panel is 47 tall with a 32 insert (spec 76 x 32 x 2 E = the insert)",
                        "The small grey spacer seen in the side view is not modelled (hidden from the front)"]},
    )


def item_pricetag_tent() -> Item:
    """Sheet 30: a clear A-frame (two 40 faces leaning 20 deg, a small flat fold) with a white folded insert behind
    both faces."""
    s = TAG_TENT
    w, L, a, t = s["w"], s["slant"], math.radians(s["half_angle"]), s["t"]
    cw, ct = s["card"]
    PVC, INS = 0, 1
    sa, ca = math.sin(a), math.cos(a)
    c0 = L * sa * ca                                # the outer front line: -ca y + sa z = c0 (and its mirror)

    def line_pts(d, z_lo, rf):
        """The A-frame outline offset d inward: foot front, apex (a flat of half-width rf), foot back."""
        c = c0 - d
        zap = c / sa
        yfoot = (sa * z_lo - c) / ca
        if rf > 0:
            zr = (c + ca * (-rf)) / sa
            return [(yfoot, z_lo), (-rf, zr), (rf, zr), (-yfoot, z_lo)]
        return [(yfoot, z_lo), (0.0, zap), (-yfoot, z_lo)]

    outer = line_pts(0.0, 0.0, s["ridge"])
    inner = line_pts(t, 0.0, 0.0)
    prof = outer + list(reversed(inner))            # front foot, ridge, back foot, then back along the inside
    if _area2(prof) < 0:
        prof.reverse()
    b = Builder()
    _extrude(b, "x", prof, -w / 2, w / 2, PVC)
    zc0 = 0.6
    co = line_pts(t + 0.1, zc0, 0.0)
    ci = line_pts(t + 0.1 + ct, zc0, 0.0)
    cprof = co + list(reversed(ci))
    if _area2(cprof) < 0:
        cprof.reverse()
    # the card's outer faces carry the print: tag them after extruding (front = the -Y face, back = the +Y face)
    n0 = len(b.faces)
    _extrude(b, "x", cprof, -cw / 2, cw / 2, INS)
    zt = co[1][1]
    for f in b.faces[n0:]:
        ys = [b.verts[i][1] for i in f.verts]
        zs = [b.verts[i][2] for i in f.verts]
        xs = [b.verts[i][0] for i in f.verts]
        if max(xs) - min(xs) < cw - 1e-6 or max(zs) - min(zs) < 1.0:
            continue
        on_outer = all(abs(ca * abs(y) + sa * z - (c0 - t - 0.1)) < 1e-6 for y, z in zip(ys, zs))
        if on_outer:
            f.region = R_FRONT if sum(ys) < 0 else R_BACK
    face_c = (0.0, (sa * (zt / 2) - (c0 - t - 0.1)) / ca, zt / 2)
    fy_out = (sa * (zt / 2) - c0) / ca
    face = (0.0, fy_out, zt / 2)
    return Item(
        name="SM_CSK_PriceTag_Tent", lods=[Lod(b)], materials=["M_CSK_Acrylic", "M_CSK_PriceTag"],
        projections={R_FRONT: _proj_xz(-cw / 2, zc0, cw, zt - zc0),
                     R_BACK: _proj_xz(-cw / 2, zc0, cw, zt - zc0, tile_u=1.0, mirror=True)},
        sockets=_tag_sockets(face, (90.0 - s["half_angle"], 0.0, 0.0), (0.0, -ca, sa)),
        hulls=[((-w / 2, outer[0][0], 0.0), (w / 2, -outer[0][0], outer[1][1]))],
        budget=BUDGETS["SM_CSK_PriceTag_Tent"],
        data={"footprint_mm": [w, -2 * outer[0][0], outer[1][1]], "pose": "standing on a counter",
              "digits": {"face": "Face", "insert_centre_mm": list(face_c)},
              "reference": "sheet 30 (2) (csk_signs_tags.png)",
              "notes": ["Sheet 30: a clear A-frame with a white folded insert behind both faces; each face 60 x 40 "
                        "(spec E) leaning 20 deg (sheet 30)"]},
    )


def item_pricetag_hook() -> Item:
    """Sheet 30: a clear rounded plate with a white insert, and a small clip barrel on its left edge that takes the
    hook's wire tip along +X. Mount = the barrel's open end on its axis (the wire enters along +X)."""
    s = TAG_HOOK
    w, h, t, r = s["w"], s["h"], s["t"], s["r"]
    iw, ih, it = s["insert"]
    bd, bl = s["barrel"]
    PVC, INS, CHROME = 0, 1, 2
    pts = []
    for cx, cz, a0 in ((w / 2 - r, -h / 2 + r, -90.0), (w / 2 - r, h / 2 - r, 0.0), (-w / 2 + r, h / 2 - r, 90.0),
                       (-w / 2 + r, -h / 2 + r, 180.0)):
        for i in range(3):
            a = math.radians(a0 + 45.0 * i)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    b = Builder()
    _extrude(b, "y", pts, -t / 2, t / 2, PVC)
    _box(b, (-iw / 2, -it / 2, -ih / 2), (iw / 2, it / 2, ih / 2), INS, regions={"ny": R_FRONT})
    xb1 = -w / 2 + 1.0
    _cyl(b, "x", 0.0, 0.0, bd / 2, xb1 - bl, xb1, 8, CHROME, phase=math.pi / 8)
    mount = (xb1 - bl, 0.0, 0.0)
    return Item(
        name="SM_CSK_PriceTag_Hook", lods=[Lod(b)], materials=["M_CSK_PVC", "M_CSK_PriceTag", "M_CSK_Chrome"],
        projections={R_FRONT: _proj_xz(-iw / 2, -ih / 2, iw, ih)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", mount), Socket("Face", (0.0, -it / 2, 0.0), (90.0, 0, 0)),
                 Socket("Text", (0.0, -t / 2 - 0.5, 0.0), (90.0, 0.0, 0.0))],
        hulls=[((xb1 - bl, -max(t / 2, 1.0) - 0.5, -h / 2), (w / 2, max(t / 2, 1.0) + 0.5, h / 2))],
        budget=BUDGETS["SM_CSK_PriceTag_Hook"],
        data={"footprint_mm": [w + bl - 1.0, t, h], "pose": "on a hook tip",
              "pivot": "Seat = the plate centre; Mount = the clip barrel's open end, the wire along +X",
              "reference": "sheet 30 (2) (csk_signs_tags.png)",
              "notes": ["Sheet 30: the barrel sits on the plate's left edge with its axis in the plate's plane; "
                        "the plate's own wire (the A8 hook) is not part of this mesh"]},
    )


# =========================================================================== I3 posters (sheet 31)

def _mitred_frame(b: Builder, W: float, H: float, profile, gap: float, mat: int) -> None:
    """Four mitred bars round a W x H (outer) rectangle in XZ, each stopping ``gap`` short of the mitre plane (the
    mitre line). ``profile`` [(o, d)]: inset from the outer edge, depth toward -Y from the wall; convex."""
    corners = [(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)]
    oc = sum(p[0] for p in profile) / len(profile)
    dc = sum(p[1] for p in profile) / len(profile)
    for k in range(4):
        (x0, z0), (x1, z1) = corners[k], corners[(k + 1) % 4]
        L = math.hypot(x1 - x0, z1 - z0)
        a = ((x1 - x0) / L, (z1 - z0) / L)
        n = (-a[1], a[0])                             # inward
        starts, ends = [], []
        for o, d in profile:
            sx, sz = x0 + n[0] * o + a[0] * (o + gap), z0 + n[1] * o + a[1] * (o + gap)
            ex, ez = x1 + n[0] * o - a[0] * (o + gap), z1 + n[1] * o - a[1] * (o + gap)
            starts.append(b.v(sx, -d, sz))
            ends.append(b.v(ex, -d, ez))
        m = len(profile)
        for i in range(m):
            j = (i + 1) % m
            (oi, di), (oj, dj) = profile[i], profile[j]
            mo, md = (oi + oj) / 2 - oc, (di + dj) / 2 - dc
            # the edge normal in (o, d) pointing away from the profile's centre
            eo, ed = dj - di, -(oj - oi)
            if eo * mo + ed * md < 0:
                eo, ed = -eo, -ed
            nrm = (n[0] * eo, -ed, n[1] * eo)
            _face_out(b, [starts[i], starts[j], ends[j], ends[i]], nrm, mat)
        _face_out(b, starts, (-a[0] + n[0], 0.0, -a[1] + n[1]), mat)
        _face_out(b, ends, (a[0] + n[0], 0.0, a[1] + n[1]), mat)


def _poster_item(size: str) -> Item:
    s = POSTER
    W, H = s["sizes"][size]
    F, D, (c1, c2), rec = s["face"], s["depth"], s["chamfer"], s["recess"]
    FRAME, PRINT = 0, 1
    prof = [(0.0, 0.0), (0.0, D - c1), (c1, D), (F - c2, D), (F, D - c2), (F, 0.0)]
    b = Builder()
    _mitred_frame(b, W, H, prof, s["mitre_gap"], FRAME)
    pw, ph = W - 2 * F + 4.0, H - 2 * F + 4.0         # the poster + backing board run 2 under the bars
    _box(b, (-pw / 2, -(D - rec), -ph / 2), (pw / 2, -0.5, ph / 2), PRINT, regions={"ny": R_FRONT})
    name = f"SM_CSK_Poster_{size}"
    return Item(
        name=name, lods=[Lod(b)], materials=["M_CSK_PowderBlack", "M_CSK_Poster"],
        projections={R_FRONT: _proj_xz(-pw / 2, -ph / 2, pw, ph)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0))],
        hulls=[((-W / 2, -D, -H / 2), (W / 2, 0.0, H / 2))],
        budget=BUDGETS[name],
        data={"footprint_mm": [W, D, H], "pose": "wall-mounted",
              "pivot": "Seat = Mount = the centre of the back face (the wall)",
              "print": {"atlas": "T_CSK_Signs", "visible_mm": [W - 2 * F, H - 2 * F]},
              "reference": "sheet 31 (1) (csk_posters_storefront.png)",
              "notes": ["Sheet 31: slim black snap frame, 20 face, mitred corners (a 0.35 mitre line), rounded "
                        "outer edge; the A-size call-outs are the frame's outer size, as the sheet draws them",
                        "Closed state only (the snap profile's open state is not a spec part)"]},
    )


def item_poster_a2() -> Item:
    return _poster_item("A2")


def item_poster_a1() -> Item:
    return _poster_item("A1")


# =========================================================================== I4 storefront lightbox (sheet 31)

def _storefront_body(level: int) -> Builder:
    s = STOREFRONT
    W, D, H = s["w"], s["d"], s["h"]
    bz, rec = s["bezel"]
    so = s["standoff"]
    BLACK, LIT = 0, 1
    b = Builder()
    yb, yf = -so, -so - D                                            # back, front of the box
    _box(b, (-W / 2, yf + rec, -H / 2), (W / 2, yb, H / 2), BLACK, mats={"ny": LIT}, regions={"ny": R_FRONT})
    if level < 2:                                                    # the front bezel over the diffuser's edge
        _extrude(b, "y", rect(W, H), yf, yf + rec + 1.0, BLACK, holes=[rect(W - 2 * bz, H - 2 * bz)])
    return b


def _storefront_brackets(level: int) -> Builder:
    s = STOREFRONT
    W, H = s["w"], s["h"]
    so = s["standoff"]
    pw, pt = s["plate"]
    al, asec = s["arm"]
    bd, bp, bin_ = s["bolt"]
    BLACK = 0
    b = Builder()
    for sx in (-1, 1):
        xi, xo = W / 2 + al, W / 2 + al + pw                         # the plate's inner / outer edges
        lo, hi = sorted((sx * xi, sx * xo))
        _box(b, (lo, -pt, -H / 2), (hi, 0.0, H / 2), BLACK)          # wall plate
        for zc in (-H * s["arm_z"], H * s["arm_z"]):                 # the two arms
            ax0, ax1 = sorted((sx * (W / 2 - 1.0), sx * (xi + 1.0)))
            _box(b, (ax0, -so - asec, zc - asec / 2), (ax1, -so + 0.5, zc + asec / 2), BLACK)
        if level == 0:
            for zc in (-H / 2 + bin_, H / 2 - bin_):                 # bolt heads
                _cyl(b, "y", sx * (xi + pw / 2), zc, bd / 2, -pt - bp, -pt + 0.5, 6, BLACK, phase=math.pi / 6)
    return b


def item_sign_storefront() -> Item:
    s = STOREFRONT
    W, D, H = s["w"], s["d"], s["h"]
    so = s["standoff"]
    xo = W / 2 + s["arm"][0] + s["plate"][0]
    lods = [Lod(_storefront_body(0), bevel_mm=1.0, extra=_storefront_brackets(0)),
            Lod(_storefront_body(1), extra=_storefront_brackets(1)),
            Lod(_storefront_body(2), extra=_storefront_brackets(2))]
    rec = s["bezel"][1]
    return Item(
        name="SM_CSK_Sign_Storefront", lods=lods, materials=["M_CSK_PowderBlack", "M_CSK_SignLit"],
        projections={R_FRONT: _proj_xz(-W / 2, -H / 2, W, H)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)),
                 Socket("Face", (0.0, -so - D + rec, 0.0), (90.0, 0.0, 0.0))],
        hulls=[((-W / 2, -so - D, -H / 2), (W / 2, -so, H / 2)),
               ((-xo, -so - s["arm"][1], -H / 2), (-W / 2, 0.0, H / 2)),
               ((W / 2, -so - s["arm"][1], -H / 2), (xo, 0.0, H / 2))],
        budget=BUDGETS["SM_CSK_Sign_Storefront"],
        data={"footprint_mm": [2 * xo, so + D, H], "pose": "wall-mounted",
              "pivot": "Seat = Mount = the wall plane at the box's centre",
              "print": "Signs atlas cell on the diffuser (region FRONT); M_CSK_SignLit = print + emissive (lit / "
                       "unlit by its MI)",
              "reference": "sheet 31 (2) (csk_posters_storefront.png)",
              "notes": ["Sheet 31: a black box with a 12 bezel over a white diffuser recessed 8; two black wall "
                        "plates outboard of the ends, each with two square arms into the box end and two bolts",
                        "The box stands off the wall by the plates' 12 (the picture reads close to the wall)"]},
    )


# =========================================================================== I5 ceiling-hung category sign (sheet 30)

def item_sign_hanging() -> Item:
    s = HANGING
    W, H, T, f, pr = s["w"], s["h"], s["t"], s["frame"], s["panel_recess"]
    cx = s["cable_x"]
    crad, drop = s["cable"]
    cur, cuh = s["cup"]
    gr, gh = s["gripper"]
    FRAME, PRINT, STEEL = 0, 1, 2
    z_top = -(cuh + drop + gh)                     # the frame's top edge
    zc = z_top - H / 2
    b = Builder()
    outer = [(x, z + zc) for x, z in rect(W, H)]
    inner = [(x, z + zc) for x, z in rect(W - 2 * f, H - 2 * f)]
    _extrude(b, "y", outer, -T / 2, T / 2, FRAME, holes=[inner])
    pw, ph = W - 2 * f + 2.0, H - 2 * f + 2.0
    _box(b, (-pw / 2, -T / 2 + pr, zc - ph / 2), (pw / 2, T / 2 - pr, zc + ph / 2), PRINT,
         regions={"ny": R_FRONT, "py": R_BACK})
    for sx in (-1, 1):
        x = sx * cx
        _cyl(b, "z", x, 0.0, cur, -cuh, 0.0, 6, STEEL)                                   # ceiling cup
        _cyl(b, "z", x, 0.0, gr, z_top - 0.5, z_top + gh, 6, STEEL)                      # gripper
        _rod(b, (x, 0.0, -cuh - 0.5), (x, 0.0, z_top + gh + 0.5), crad, 3, STEEL)        # cable
    return Item(
        name="SM_CSK_Sign_Hanging", lods=[Lod(b)], materials=["M_CSK_Frame", "M_CSK_Sign", "M_CSK_Chrome"],
        projections={R_FRONT: _proj_xz(-pw / 2, zc - ph / 2, pw, ph),
                     R_BACK: _proj_xz(-pw / 2, zc - ph / 2, pw, ph, tile_u=1.0, mirror=True)},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount_L", (-cx, 0.0, 0.0)), Socket("Mount_R", (cx, 0.0, 0.0))],
        hulls=[((-W / 2, -T / 2, z_top - H), (W / 2, T / 2, z_top))],
        budget=BUDGETS["SM_CSK_Sign_Hanging"],
        data={"footprint_mm": [W, T, -z_top + H], "pose": "ceiling-hung",
              "pivot": "Seat = the ceiling plane between the two cups; Mount_L / Mount_R = the cups' ceiling faces",
              "print": "Signs atlas category cell: front (-Y) tile (0,0), back (+Y) tile (1,0)",
              "reference": "sheet 30 (3) (csk_signs_tags.png)",
              "notes": ["Sheet 30: the panel reads 4.15 : 1, so it is 600 x 145 (spec 600 x 200 E; the picture wins)",
                        "Budget 100 -> 150: two cable suspenders with ceiling cups and grippers (sheet 30)",
                        "The cable drop is the sheet's 100; a longer drop needs a longer cable (open question)"]},
    )


# =========================================================================== J1 shell modules (sheet 32)

def _wall_body(kind: str, level: int) -> Builder:
    """The wall slab: plaster faces, the end faces' bottom 150 black (the skirting band), and the opening's reveals
    (plaster for the window, the black lining for the door). The skirting is a real strip, proud of the shop face."""
    s = WALL
    W, T, H = s["w"], s["t"], s["h"]
    sk, skp = s["skirting"]
    PLASTER, SKIRT, BLACK = 0, 1, 2
    b = Builder()
    if kind == "door":
        x0, dw, dh = s["door"]
        x1 = x0 + dw
        outer = [(0.0, 0.0), (x0, 0.0), (x0, dh), (x1, dh), (x1, 0.0), (W, 0.0), (W, sk), (W, H), (0.0, H), (0.0, sk)]
        mats = [PLASTER, BLACK, BLACK, BLACK, PLASTER, SKIRT, PLASTER, PLASTER, PLASTER, SKIRT]
        _extrude(b, "y", outer, 0.0, T, PLASTER, side_mats=mats)
        for a, c in ((0.0, x0), (x1, W)):
            _box(b, (a, -skp, 0.0), (c, 0.5, sk), SKIRT)
        return b
    outer = [(0.0, 0.0), (W, 0.0), (W, sk), (W, H), (0.0, H), (0.0, sk)]
    mats = [PLASTER, SKIRT, PLASTER, PLASTER, PLASTER, SKIRT]
    holes = []
    if kind == "window":
        ww, wh, wz = s["window"]
        holes = [[(W / 2 - ww / 2, wz), (W / 2 + ww / 2, wz), (W / 2 + ww / 2, wz + wh), (W / 2 - ww / 2, wz + wh)]]
    _extrude(b, "y", outer, 0.0, T, PLASTER, side_mats=mats, holes=holes, hole_mats=[PLASTER] * len(holes))
    _box(b, (0.0, -skp, 0.0), (W, 0.5, sk), SKIRT)
    return b


def _window_frame(level: int) -> Builder:
    """Sheet 32: a black frame in the opening (1 into the reveals), a mullion 35 % across and a transom 25 % down."""
    s = WALL
    W, T = s["w"], s["t"]
    ww, wh, wz = s["window"]
    fw, fd = s["win_frame"]
    mx, tz = s["mullion"]
    BLACK = 2
    b = Builder()
    y0, y1 = (T - fd) / 2, (T + fd) / 2
    xl, xr, zb, zt = W / 2 - ww / 2, W / 2 + ww / 2, wz, wz + wh
    _extrude(b, "y", [(xl - 1, zb - 1), (xr + 1, zb - 1), (xr + 1, zt + 1), (xl - 1, zt + 1)], y0, y1, BLACK,
             holes=[[(xl + fw, zb + fw), (xr - fw, zb + fw), (xr - fw, zt - fw), (xl + fw, zt - fw)]])
    xm = xl + mx * ww
    zm = zt - tz * wh
    yi0, yi1 = y0 + 5.0, y1 - 5.0                  # the bars sit 5 behind the outer frame's faces (E)
    _box(b, (xm - fw / 2, yi0, zb + fw - 1.0), (xm + fw / 2, yi1, zt - fw + 1.0), BLACK)
    spans = (((xl + fw - 1.0, xm - fw / 2 + 1.0), (xm + fw / 2 - 1.0, xr - fw + 1.0)) if level < 2 else
             ((xl + fw - 1.0, xr - fw + 1.0),))    # LOD2: one transom box through the mullion
    for a, c in spans:
        _box(b, (a, yi0 + 0.5, zm - fw / 2), (c, yi1 - 0.5, zm + fw / 2), BLACK)
    return b


def _window_panes():
    s = WALL
    W, T = s["w"], s["t"]
    ww, wh, wz = s["window"]
    fw = s["win_frame"][0]
    mx, tz = s["mullion"]
    g, pk = s["glass"], s["glass_pocket"]
    xl, xr, zb, zt = W / 2 - ww / 2, W / 2 + ww / 2, wz, wz + wh
    xm, zm = xl + mx * ww, zt - tz * wh
    xs = [(xl + fw - pk, xm - fw / 2 + pk), (xm + fw / 2 - pk, xr - fw + pk)]
    zs = [(zb + fw - pk, zm - fw / 2 + pk), (zm + fw / 2 - pk, zt - fw + pk)]
    yg0 = T / 2 - g / 2
    return [((a, yg0, c), (bb, yg0 + g, d)) for a, bb in xs for c, d in zs]


def _wall_item(kind: str) -> Item:
    s = WALL
    W, T, H = s["w"], s["t"], s["h"]
    sk, skp = s["skirting"]
    names = {"plain": "SM_CSK_Shell_Wall_2000", "window": "SM_CSK_Shell_Wall_Window_2000",
             "door": "SM_CSK_Shell_Wall_Door_2000"}
    name = names[kind]
    mats = ["M_CSK_Plaster", "M_CSK_Base", "M_CSK_PowderBlack"]
    if kind == "window":
        def main(k):
            b = _wall_body(kind, k)
            f = _window_frame(k)
            off = len(b.verts)
            b.verts += f.verts
            b.faces += [type(fc)(tuple(i + off for i in fc.verts), fc.mat, fc.region) for fc in f.faces]
            b.fills += [type(fl)([[i + off for i in lp] for lp in fl.loops], fl.mat, fl.region, fl.normal)
                        for fl in f.fills]
            return b
        lods = [Lod(main(0), bevel_mm=1.0), Lod(main(1)), Lod(main(2))]
    else:
        lods = [Lod(_wall_body(kind, 0))]
    sockets = [Socket("Seat", (0, 0, 0)), Socket("Snap_L", (0, 0, 0)), Socket("Snap_R", (W, 0, 0))]
    hulls = [((0.0, -skp, 0.0), (W, T, H))]
    notes = ["Sheet 32: white plaster, a black skirting 150 tall (10 proud, on the shop face only: the sheet shows "
             "no outside face); the end faces' bottom 150 is black, as the sheet's wall ends show"]
    data = {"footprint_mm": [W, T + skp, H], "pose": "upright, modular",
            "pivot": "end corner: the shop face (y 0) at the left end, floor level; the outside face is y 150",
            "reference": "sheet 32 (csk_shell.png, notes in REFERENCE_LOG.md)"}
    if kind == "window":
        ww, wh, wz = s["window"]
        xl, xr = W / 2 - ww / 2, W / 2 + ww / 2
        hulls = [((0.0, -skp, 0.0), (xl, T, H)), ((xr, -skp, 0.0), (W, T, H)),
                 ((xl, -skp, 0.0), (xr, T, wz)), ((xl, 0.0, wz + wh), (xr, T, H))]
        data["glass"] = "SM_CSK_Shell_Wall_Window_2000_Glass"
        notes.append("Sheet 32 window module: a 1600 x 2400 black frame on a 300 sill, centred; the mullion stands "
                     "35 % across and the transom 25 % down (both views agree); the panes are the _Glass mesh")
    if kind == "door":
        x0, dw, dh = s["door"]
        hulls = [((0.0, -skp, 0.0), (x0, T, H)), ((x0 + dw, -skp, 0.0), (W, T, H)), ((x0, 0.0, dh), (x0 + dw, T, H))]
        sockets.append(Socket("Mount_DoorFrame", (x0 + dw / 2, 0.0, 0.0)))
        data["fits"] = {"SM_CSK_Door_Entry_Frame": "Mount_DoorFrame"}
        notes.append("Sheet 32: the 1000 x 2200 opening starts 600 from the left end (both views); its reveals are "
                     "the black lining; SM_CSK_Door_Entry_Frame fills it exactly at Mount_DoorFrame")
    data["notes"] = notes + ["UV2 metre tiling is not generated by csk_lib (mesh.py writes UV0 + UV1 only)"]
    return Item(name=name, lods=lods, materials=mats, projections={}, sockets=sockets, hulls=hulls,
                budget=BUDGETS[name], data=data)


def item_wall() -> Item:
    return _wall_item("plain")


def item_wall_window() -> Item:
    return _wall_item("window")


def item_wall_door() -> Item:
    return _wall_item("door")


def item_wall_window_glass() -> Item:
    b = Builder()
    panes = _window_panes()
    for mn, mx in panes:
        _box(b, mn, mx, 0)
    return Item(name="SM_CSK_Shell_Wall_Window_2000_Glass", lods=[Lod(b)], materials=["M_CSK_Glass"],
                projections={}, sockets=[Socket("Seat", (0, 0, 0))], hulls=panes,
                budget=BUDGETS["SM_CSK_Shell_Wall_Window_2000_Glass"],
                data={"part_of": "SM_CSK_Shell_Wall_Window_2000", "attach": "same transform as the wall",
                      "notes": ["Fixed panes live in their own _Glass mesh (spec 4.5); 4 panes, 10 thick (E), "
                                "running 10 into the frame"]})


def item_floor() -> Item:
    s = FLOOR
    W, T = s["w"], s["t"]
    b = Builder()
    _box(b, (0.0, 0.0, -T), (W, W, 0.0), 0)
    return Item(name="SM_CSK_Shell_Floor_2000", lods=[Lod(b, bevel_mm=s["edge"])], materials=["M_CSK_FloorVinyl"],
                projections={},
                sockets=[Socket("Seat", (0, 0, 0)), Socket("Snap_L", (0, 0, 0)), Socket("Snap_R", (W, 0, 0))],
                hulls=[((0.0, 0.0, -T), (W, W, 0.0))], budget=BUDGETS["SM_CSK_Shell_Floor_2000"],
                data={"footprint_mm": [W, W, T], "pose": "floor, modular",
                      "pivot": "corner; the walking surface is z 0 (the slab is below it)",
                      "reference": "sheet 32 (csk_shell.png)",
                      "notes": ["Sheet 32 'floor module join': the fine join is a 1.5 chamfer on the top edges",
                                "UV2 metre tiling is not generated by csk_lib (mesh.py writes UV0 + UV1 only)"]})


def _ceiling(level: int) -> Builder:
    """Sheet 32: white acoustic tiles 2 x 2 in an aluminium T-grid. One closed solid: the grid's face (with half
    bars on the module edges, so two modules make a full bar), each tile a 3 recess above it. LOD2: the same
    pattern flat (no step)."""
    s = CEILING
    W, T, n, bar = s["w"], s["t"], s["tiles"], s["bar"]
    st = s["step"] if level < 2 else 0.0
    GRID, TILE = 0, 1
    b = Builder()
    pitch = W / n
    holes = []
    for i in range(n):
        for j in range(n):
            x0 = i * pitch + (bar / 2)
            y0 = j * pitch + (bar / 2)
            holes.append([(x0, y0), (x0 + pitch - bar, y0), (x0 + pitch - bar, y0 + pitch - bar),
                          (x0, y0 + pitch - bar)])
    outer = [(0.0, 0.0), (W, 0.0), (W, W), (0.0, W)]
    lo = [b.v(x, y, 0.0) for x, y in outer]
    hi = [b.v(x, y, T) for x, y in outer]
    hole_lo = [[b.v(x, y, 0.0) for x, y in h] for h in holes]
    b.fill([lo] + hole_lo, GRID, 0, (0, 0, -1))
    b.fill([hi], TILE, 0, (0, 0, 1))
    for i in range(4):
        j = (i + 1) % 4
        (x_i, y_i), (x_j, y_j) = outer[i], outer[j]
        _face_out(b, [lo[i], lo[j], hi[j], hi[i]], (y_j - y_i, -(x_j - x_i), 0.0), GRID)
    for h, hl in zip(holes, hole_lo):
        if st > 0:
            hh = [b.v(x, y, st) for x, y in h]
            for i in range(4):
                j = (i + 1) % 4
                (x_i, y_i), (x_j, y_j) = h[i], h[j]
                _face_out(b, [hl[i], hl[j], hh[j], hh[i]], (-(y_j - y_i), x_j - x_i, 0.0), GRID)
        else:
            hh = hl
        _face_out(b, hh, (0, 0, -1), TILE)
    return b


def item_ceiling() -> Item:
    s = CEILING
    W, T = s["w"], s["t"]
    lods = [Lod(_ceiling(0), bevel_mm=0.5), Lod(_ceiling(1)), Lod(_ceiling(2))]
    return Item(name="SM_CSK_Shell_Ceiling_2000", lods=lods,
                materials=["M_CSK_Frame", "M_CSK_CeilingTile"], projections={},
                sockets=[Socket("Seat", (0, 0, 0)), Socket("Snap_L", (0, 0, 0)), Socket("Snap_R", (W, 0, 0))],
                hulls=[((0.0, 0.0, 0.0), (W, W, T))], budget=BUDGETS["SM_CSK_Shell_Ceiling_2000"],
                data={"footprint_mm": [W, W, T], "pose": "ceiling, modular",
                      "pivot": "corner on the grid's underside (z 0 = the ceiling plane; set it on the walls' top)",
                      "reference": "sheet 32 (csk_shell.png)",
                      "notes": ["Sheet 32: 2 x 2 tiles per module in a 24 T-grid (half bars at the module edges)",
                                "The 600 LED panel (J3) does not drop into a 976 tile cell: it mounts on the tile "
                                "face (open question)",
                                "UV2 metre tiling is not generated by csk_lib (mesh.py writes UV0 + UV1 only)"]})


# =========================================================================== J2 entry door (sheet 33)

def _door_dims():
    s = DOOR
    FW, FD, FH = s["frame"]
    LW, LT, LH = s["leaf"]
    g = s["gap"]
    th, tg = s["threshold"]
    xj = LW / 2 + g                                 # jamb inner faces
    zl0 = th + tg                                   # leaf bottom
    zh = zl0 + LH + g                               # header underside
    ax = (-xj, FD + s["axis_off"], zl0)             # hinge axis (at the leaf bottom), outside the exterior face
    return dict(FW=FW, FD=FD, FH=FH, LW=LW, LT=LT, LH=LH, g=g, xj=xj, zl0=zl0, zh=zh, ax=ax, th=th)


def _door_frame_main(level: int) -> Builder:
    k = _door_dims()
    FW, FD, FH, xj, zh = k["FW"], k["FD"], k["FH"], k["xj"], k["zh"]
    BLACK = 0
    b = Builder()
    u = [(-FW / 2, 0.0), (-xj, 0.0), (-xj, zh), (xj, zh), (xj, 0.0), (FW / 2, 0.0), (FW / 2, FH), (-FW / 2, FH)]
    _extrude(b, "y", u, 0.0, FD, BLACK)
    return b


def _door_frame_parts(level: int) -> Builder:
    s = DOOR
    k = _door_dims()
    FD, xj, zh, th = k["FD"], k["xj"], k["zh"], k["th"]
    BLACK, STEEL = 0, 1
    b = Builder()
    st = s["stop"]
    if level < 2:                                   # the stop behind the leaf (sheet 33 top view)
        xs = xj - st
        u = [(-xj - 1.0, 0.0), (-xs, 0.0), (-xs, zh - st), (xs, zh - st), (xs, 0.0), (xj + 1.0, 0.0),
             (xj + 1.0, zh + 1.0), (-xj - 1.0, zh + 1.0)]
        _extrude(b, "y", u, 0.5, FD - k["LT"] - 0.5, BLACK)
    _box(b, (-xj + 1.0, 0.5, 0.0), (xj - 1.0, FD - 0.5, th), STEEL)            # threshold plate
    (hz, hl, hr, hw) = s["hinges"]
    if level == 0:                                  # the hinges' frame leaves on the jamb's outside face
        for z in hz:
            _box(b, (-xj - hw, FD - 0.5, z - hl / 2), (-xj - 1.5, FD + 2.0, z + hl / 2), STEEL)
    # the bell (sheet 33): a round backplate on the header's outside face, a short arm, the bell, a clapper
    rr, bh, pr, pt = s["bell"]
    zhc = (zh + k["FH"]) / 2
    segs = (10, 8, 6)[level]
    if level < 2:
        _cyl(b, "y", 0.0, zhc, pr, FD - 0.5, FD + pt, segs, STEEL)
    yb = FD + pt + rr
    z0 = zh + 6.0
    prof = [(0.0, bh), (0.32 * rr, bh * 0.96), (0.56 * rr, bh * 0.81), (0.69 * rr, bh * 0.56), (0.79 * rr, bh * 0.28),
            (rr, bh * 0.06), (rr, 0.0), (0.82 * rr, 0.0), (0.0, bh * 0.14)]
    if level == 2:
        prof = [(0.0, bh), (0.6 * rr, bh * 0.8), (rr, 0.0), (0.0, 0.0)]
    _revolve(b, "z", 0.0, yb, [(r, z0 + t) for r, t in prof], segs, STEEL, side=-1)
    if level < 2:
        _cyl(b, "z", 0.0, yb, 3.5, z0 + bh - 1.0, z0 + bh + 8.0, 6, STEEL)                  # knob
        _box(b, (-3.0, FD + pt - 0.5, z0 + bh + 2.0), (3.0, yb + 1.0, z0 + bh + 7.0), STEEL)  # arm to the backplate
        _octa(b, (0.0, yb, z0 - 3.0), 4.0, STEEL)                                            # clapper
    return b


def item_door_frame() -> Item:
    s = DOOR
    k = _door_dims()
    FW, FD, FH, xj, zh = k["FW"], k["FD"], k["FH"], k["xj"], k["zh"]
    lods = [Lod(_door_frame_main(0), bevel_mm=1.0, extra=_door_frame_parts(0)),
            Lod(_door_frame_main(1), extra=_door_frame_parts(1)),
            Lod(_door_frame_main(2), extra=_door_frame_parts(2))]
    rr, bh, pr, pt = s["bell"]
    return Item(
        name="SM_CSK_Door_Entry_Frame", lods=lods, materials=["M_CSK_PowderBlack", "M_CSK_Chrome"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Door", k["ax"]),
                 Socket("Bell", (0.0, FD + pt + rr, zh + 6.0 + bh / 2))],
        hulls=[((-FW / 2, 0.0, 0.0), (-xj, FD, FH)), ((xj, 0.0, 0.0), (FW / 2, FD, FH)),
               ((-xj, 0.0, zh), (xj, FD, FH))],
        budget=BUDGETS["SM_CSK_Door_Entry_Frame"],
        data={"footprint_mm": [FW, FD, FH], "pose": "upright, in the Wall_Door opening",
              "pivot": "the bottom centre of the shop (interior) face, as the wall's Mount_DoorFrame; the street "
                       "face is y 150",
              "parts": {"Door": {"mesh": "SM_CSK_Door_Entry", "socket": "Door", "type": "hinge", "axis": "Z",
                                 "range_deg": list(s["open_deg"]), "open_rot_deg": [0.0, 0.0, 90.0],
                                 "opens": "outward (+Y, the street side); + about Z"}},
              "fits": "SM_CSK_Shell_Wall_Door_2000 at Mount_DoorFrame",
              "reference": "sheet 33 (csk_entry_door.png, notes in REFERENCE_LOG.md)",
              "notes": ["Printed call-outs win over the picture's proportions: 1000 frame and 900 leaf give 47 jambs "
                        "(the picture reads 85); 2200 / 2100 give an 89 header",
                        "Sheet 33: a 15 stop behind the leaf, a stainless threshold plate, the hinges' frame "
                        "leaves on the right jamb, the bell centred on the header's street face (scaled to the "
                        "header)"]},
    )


def _door_leaf_main(level: int) -> Builder:
    """The leaf in its hinge frame: the axis is the Z line through the origin; the leaf spans x 3..903 (the free
    edge at +X), y -53..-8 (the street face at y -8), z 0..2100."""
    s = DOOR
    k = _door_dims()
    LW, LT, LH, g = k["LW"], k["LT"], k["LH"], k["g"]
    so, rt, rb = s["stile"]
    BLACK = 0
    ao = s["axis_off"]
    x0, x1 = g, g + LW
    y0, y1 = -ao - LT, -ao
    b = Builder()
    _extrude(b, "y", rect(LW, LH, (x0 + x1) / 2, LH / 2), y0, y1, BLACK,
             holes=[[(x0 + so, rb), (x1 - so, rb), (x1 - so, LH - rt), (x0 + so, LH - rt)]])
    return b


def _door_leaf_parts(level: int) -> Builder:
    s = DOOR
    k = _door_dims()
    LW, LT, LH, g = k["LW"], k["LT"], k["LH"], k["g"]
    so, rt, rb = s["stile"]
    bw, brec = s["bead"]
    BLACK, GLASS, STEEL = 0, 1, 2
    ao = s["axis_off"]
    x0, x1 = g, g + LW
    y0, y1 = -ao - LT, -ao
    ym = (y0 + y1) / 2
    b = Builder()
    ox0, ox1, oz0, oz1 = x0 + so, x1 - so, rb, LH - rt
    if level < 2:                                   # glazing bead, recessed from both faces
        _extrude(b, "y", [(ox0 - 1, oz0 - 1), (ox1 + 1, oz0 - 1), (ox1 + 1, oz1 + 1), (ox0 - 1, oz1 + 1)],
                 y0 + brec, y1 - brec, BLACK,
                 holes=[[(ox0 + bw, oz0 + bw), (ox1 - bw, oz0 + bw), (ox1 - bw, oz1 - bw), (ox0 + bw, oz1 - bw)]])
    gl = s["glass"]
    _box(b, (ox0 + bw - 6.0, ym - gl / 2, oz0 + bw - 6.0), (ox1 - bw + 6.0, ym + gl / 2, oz1 - bw + 6.0), GLASS)
    # the pull bar on the street face (sheet 33): a long round bar on two posts
    pc, pl, prad, pso, pz, postr, pin = s["pull"]
    xp = x1 - pc
    yp = y1 + pso
    segs = (12, 8, 6)[level]
    _cyl(b, "z", xp, yp, prad, pz - pl / 2, pz + pl / 2, segs, STEEL)
    if level < 2:
        for zz in (pz - pl / 2 + pin, pz + pl / 2 - pin):
            _cyl(b, "y", xp, zz, postr, y1 - 0.5, yp, (8, 6, 6)[level], STEEL)
    hz, hl, hr, hw = s["hinges"]
    for z in hz:                                    # knuckles on the axis (they turn in place)
        zc = z - k["zl0"]
        _cyl(b, "z", 0.0, 0.0, hr, zc - hl / 2, zc + hl / 2, (8, 6, 6)[level], STEEL)
        if level == 0:
            _box(b, (0.0, y1 - 0.5, zc - hl / 2 + 2.0), (hw, -hr + 2.0, zc + hl / 2 - 2.0), STEEL)
    return b


def item_door_leaf() -> Item:
    s = DOOR
    k = _door_dims()
    LW, LT, LH, g = k["LW"], k["LT"], k["LH"], k["g"]
    ao = s["axis_off"]
    lods = [Lod(_door_leaf_main(0), bevel_mm=1.0, extra=_door_leaf_parts(0)),
            Lod(_door_leaf_main(1), extra=_door_leaf_parts(1)),
            Lod(_door_leaf_main(2), extra=_door_leaf_parts(2))]
    pc, pl, prad, pso, pz, postr, pin = s["pull"]
    x1 = g + LW
    yg = -ao - LT / 2 - s["glass"] / 2              # the glass's shop-side face
    rt = s["stile"][1]
    zc_sign = LH - rt - 45.0 - SIGN["cup"][0] / 2   # the sign's suction cup: on the glass under the top rail
    return Item(
        name="SM_CSK_Door_Entry", lods=lods, materials=["M_CSK_PowderBlack", "M_CSK_Glass", "M_CSK_Chrome"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Handle", (x1 - pc, -ao + pso, pz)),
                 Socket("Sign", (g + LW / 2, yg, zc_sign))],
        hulls=[((g, -ao - LT, 0.0), (g + LW, -ao, LH))],
        budget=BUDGETS["SM_CSK_Door_Entry"],
        data={"part_of": "SM_CSK_Door_Entry_Frame", "footprint_mm": [LW, LT, LH],
              "pivot": "the hinge axis (Z) at the leaf's bottom, 8 outside its street face; the leaf runs to +X",
              "notes": ["Sheet 33: black stiles 80 / top rail 80 / bottom rail 100, a glazing bead, a full glass "
                        "pane (a moving pane stays in the moving mesh), a 760 stainless pull bar on two posts on "
                        "the street face, 3 hinge knuckles on the axis",
                        "Sign = the I1 sign's Seat on the glass's shop side, under the top rail (the sheet hangs it "
                        "a little higher, from the rail)"]},
    )


# =========================================================================== J3 lights (sheet 34)

def item_light_panel() -> Item:
    s = PANEL
    W, T, f, rec = s["w"], s["t"], s["frame"], s["recess"]
    FRAME, LED = 0, 1
    b = Builder()
    _extrude(b, "z", rect(W, W), -T, 0.0, FRAME, holes=[rect(W - 2 * f, W - 2 * f)])
    _box(b, (-(W / 2 - f + 1.0), -(W / 2 - f + 1.0), -T + rec), (W / 2 - f + 1.0, W / 2 - f + 1.0, -0.5), LED)
    return Item(
        name="SM_CSK_Light_Panel600", lods=[Lod(b, bevel_mm=0.5)], materials=["M_CSK_Frame", "M_CSK_LED"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)),
                 Socket("Light", (0.0, 0.0, -T + rec), (0.0, 90.0, 0.0))],
        hulls=[((-W / 2, -W / 2, -T), (W / 2, W / 2, 0.0))],
        budget=BUDGETS["SM_CSK_Light_Panel600"],
        data={"footprint_mm": [W, W, T], "pose": "ceiling",
              "pivot": "Seat = Mount = the top face's centre (the ceiling); Light aims its +X down",
              "reference": "sheet 34 (1) (csk_lights.png)",
              "notes": ["Sheet 34: a thin aluminium edge frame round a white diffuser (M_CSK_LED: lit / unlit)"]},
    )


def _track_rail(level: int) -> Builder:
    s = TRACK
    L, w, h, wl, sl, lp = s["l"], s["w"], s["h"], s["wall"], s["slot"], s["lip"]
    BLACK, WHITE = 0, 1
    b = Builder()
    # section (y, z): a channel open at the bottom through a slot between two lips (sheet 34 inset)
    prof = [(-w / 2, -h), (-sl / 2, -h), (-sl / 2, -h + lp), (-w / 2 + wl, -h + lp), (-w / 2 + wl, -wl),
            (w / 2 - wl, -wl), (w / 2 - wl, -h + lp), (sl / 2, -h + lp), (sl / 2, -h), (w / 2, -h), (w / 2, 0.0),
            (-w / 2, 0.0)]
    if _area2(prof) < 0:
        prof.reverse()
    if level == 2:
        prof = [(-w / 2, -h), (w / 2, -h), (w / 2, 0.0), (-w / 2, 0.0)]
    ec = 2.0
    _extrude(b, "x", prof, -L / 2 + ec - 0.5, L / 2 - ec + 0.5, BLACK)
    if level < 2:
        for sx in (-1, 1):                          # end caps
            a, c = sorted((sx * (L / 2 - ec), sx * L / 2))
            _box(b, (a, -w / 2 - 0.3, -h - 0.3), (c, w / 2 + 0.3, 0.3), BLACK)
        _box(b, (-L / 2 + ec, -w / 2 + wl + 0.5, -h + lp + 1.0), (L / 2 - ec, w / 2 - wl - 0.5, -h + lp + 3.0),
             WHITE)                                 # the conductor strip seen through the slot
    return b


def item_light_track() -> Item:
    s = TRACK
    L, w, h, n = s["l"], s["w"], s["h"], s["heads"]
    lods = [Lod(_track_rail(0), bevel_mm=0.4), Lod(_track_rail(1)), Lod(_track_rail(2))]
    heads = [Socket(f"Head_{i + 1:02d}", (-L / 2 + L * (i + 0.5) / n, 0.0, -h)) for i in range(n)]
    return Item(
        name="SM_CSK_Light_Track2000", lods=lods, materials=["M_CSK_PowderBlack", "M_CSK_PlasticWhite"],
        projections={}, sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0))] + heads,
        hulls=[((-L / 2, -w / 2, -h), (L / 2, w / 2, 0.0))],
        budget=BUDGETS["SM_CSK_Light_Track2000"],
        data={"footprint_mm": [L, w, h], "pose": "ceiling",
              "pivot": "Seat = Mount = the top face's centre (the ceiling)",
              "heads": {"mesh": "SM_CSK_Light_TrackHead", "sockets": [x.name for x in heads],
                        "pitch_mm": L / n},
              "reference": "sheet 34 (2) (csk_lights.png)",
              "notes": ["Sheet 34: the rail is 20 wide x 35 tall (the section inset and the 35 call-out; spec "
                        "35 x 20 E: the picture wins); a channel with a bottom slot, end caps",
                        "No Light socket on the rail: the heads carry the light"]},
    )


def _head_fixed(level: int) -> Builder:
    s = HEAD
    pr, ph = s["puck"]
    sr, sl = s["stem"]
    kd, kr, kl, kg = s["knuckle"]
    BLACK = 0
    b = Builder()
    _cyl(b, "z", 0.0, 0.0, pr, -ph, 0.0, (12, 8, 6)[level], BLACK)
    _cyl(b, "z", 0.0, 0.0, sr, -ph - sl, -ph + 0.5, (8, 6, 6)[level], BLACK)
    return b


def item_light_trackhead() -> Item:
    s = HEAD
    pr, ph = s["puck"]
    sr, sl = s["stem"]
    kr = s["knuckle"][1]
    z_axis = -ph - sl - kr + 1.0                    # the tilt axis: the stem ends 1 into the spot's barrel
    return Item(
        name="SM_CSK_Light_TrackHead", lods=[Lod(_head_fixed(0))], materials=["M_CSK_PowderBlack"], projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)), Socket("Tilt", (0.0, 0.0, z_axis))],
        hulls=[((-pr, -pr, -ph - sl), (pr, pr, 0.0))],
        budget=BUDGETS["SM_CSK_Light_TrackHead"],
        data={"footprint_mm": [2 * pr, 2 * pr, ph + sl], "pose": "on a track Head_* socket",
              "pivot": "Seat = Mount = the adapter's top (the rail's underside); turn it about Z to pan",
              "parts": {"Spot": {"mesh": "SM_CSK_Light_TrackHead_Spot", "socket": "Tilt", "type": "hinge",
                                 "axis": "X", "range_deg": [s["tilt"][0], s["tilt"][1]],
                                 "open_rot_deg": [s["tilt"][2], 0.0, 0.0],
                                 "tilt": "0 = aimed level at -Y, + = down; the sheet shows about 45"}},
              "reference": "sheet 34 (2) detail (csk_lights.png)",
              "notes": ["Split from the spec's single TrackHead: the adapter and stem stay put, the spot body "
                        "tilts on the knuckle (spec: 'the head pivots on its tilt axis'); the round adapter "
                        "(sheet 34 detail with the call-outs) lets it pan by its attach rotation"]},
    )


def _head_spot(level: int) -> Builder:
    """The spot in its tilt frame: the knuckle barrel on the X axis through the origin; the body (dia 70 x 150) below
    it, aimed at -Y, its rear 50 behind the axis; a front bezel ring and a recessed reflector cone with the lens."""
    s = HEAD
    r, L = s["body"]
    kd, kr, kl, kg = s["knuckle"]
    bz, rd, rr = s["bezel"]
    BLACK, LED = 0, 1
    zc = -(kr + kg + r)                             # the body axis
    y_rear, y_front = kd, kd - L
    segs = (16, 12, 8)[level]
    b = Builder()
    # one revolve (shared rings, no coincident vertices): rear cap, barrel, bezel, recess lip | reflector, lens
    if level < 2:
        prof = [(0.0, y_rear), (r, y_rear), (r, y_front), (r - bz, y_front), (r - bz - 1.5, y_front + 3.0),
                (rr, y_front + rd), (0.0, y_front + rd)]
        mats = [BLACK, BLACK, BLACK, BLACK, LED, LED]
    else:
        prof = [(0.0, y_rear), (r, y_rear), (r, y_front), (r - bz, y_front), (0.0, y_front + 1.0)]
        mats = [BLACK, BLACK, BLACK, LED]
    _revolve(b, "y", 0.0, zc, prof, segs, mats, side=-1, phase=math.pi / segs)
    # the knuckle: a barrel on the tilt axis and a lug down into the body
    _cyl(b, "x", 0.0, 0.0, kr, -kl / 2, kl / 2, (8, 6, 6)[level], BLACK)
    if level < 2:
        _box(b, (-kl / 2 + 2.0, -kr * 0.7, zc + r - 3.0), (kl / 2 - 2.0, kr * 0.7, -kr * 0.5), BLACK)
    return b


def item_light_trackhead_spot() -> Item:
    s = HEAD
    r, L = s["body"]
    kd, kr, kl, kg = s["knuckle"]
    zc = -(kr + kg + r)
    lods = [Lod(_head_spot(i)) for i in range(3)]
    return Item(
        name="SM_CSK_Light_TrackHead_Spot", lods=lods, materials=["M_CSK_PowderBlack", "M_CSK_LED"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Light", (0.0, kd - L + s["bezel"][1], zc), (0.0, 0.0, -90.0))],
        hulls=[((-r, kd - L, zc - r), (r, kd, kr))],
        budget=BUDGETS["SM_CSK_Light_TrackHead_Spot"],
        data={"part_of": "SM_CSK_Light_TrackHead", "footprint_mm": [2 * r, L, 2 * r + kr + kg],
              "pivot": "the tilt axis (X) through the knuckle barrel; at 0 the spot aims level at -Y",
              "notes": ["Sheet 34: a plain black cylinder with a thin front bezel and a recessed reflector (lit / "
                        "unlit by M_CSK_LED); Light at the lens, its +X along the beam"]},
    )


def _pendant(level: int) -> Builder:
    s = PENDANT
    R, Hs = s["shade"]
    wl = s["wall"]
    cr, ch = s["collar"]
    cdr, cdl = s["cord"]
    kr, kh = s["canopy"]
    segs = s["segs"][level]
    PAINT, CORD, LED = 0, 1, 2
    b = Builder()
    _cyl(b, "z", 0.0, 0.0, kr, -kh, 0.0, segs, PAINT)                                    # canopy
    z_c0 = -kh - cdl                                                                     # the cord's bottom
    _rod(b, (0.0, 0.0, -kh + 0.5), (0.0, 0.0, z_c0 - 1.0), cdr, (6, 6, 4)[level], CORD)  # cord
    _cyl(b, "z", 0.0, 0.0, cr, z_c0 - ch, z_c0, segs, PAINT)                             # collar
    z_top = z_c0 - ch + 0.6                         # the dome's top: the collar sinks 0.6 into its 1.2 wall
    z_rim = z_top - Hs
    prof = list(s["prof"]) if level == 0 else ([s["prof"][i] for i in (0, 2, 4, 5, 6, 7)] if level == 1 else
                                               [s["prof"][i] for i in (0, 3, 5, 7)])
    outer = [(R * f, z_rim + Hs * t) for t, f in prof]
    inner = [(max(R * f - wl, 1.0), z_rim + (Hs - wl) * t) for t, f in prof]
    if level > 0:
        inner = [inner[0], inner[len(inner) // 2], inner[-1]]
    # one closed thin shell: the inside (lit) from its top down to the rim, the rim, the outside up to its top
    path = [(0.0, inner[-1][1])] + list(reversed(inner)) + outer + [(0.0, outer[-1][1])]
    n_in = len(inner)
    mats = [LED] * n_in + [PAINT] * (len(path) - 1 - n_in)
    _revolve(b, "z", 0.0, 0.0, path, segs, mats, side=1)
    return b


def item_light_pendant() -> Item:
    s = PENDANT
    R, Hs = s["shade"]
    cr, ch = s["collar"]
    cdr, cdl = s["cord"]
    kr, kh = s["canopy"]
    z_top = -kh - cdl - ch + 0.6
    z_rim = z_top - Hs
    lods = [Lod(_pendant(i)) for i in range(3)]
    return Item(
        name="SM_CSK_Light_Pendant", lods=lods, materials=["M_CSK_PowderBlack", "M_CSK_Cord", "M_CSK_LED"],
        projections={},
        sockets=[Socket("Seat", (0, 0, 0)), Socket("Mount", (0, 0, 0)),
                 Socket("Light", (0.0, 0.0, z_top - 40.0), (0.0, 90.0, 0.0))],
        hulls=[((-R, -R, z_rim), (R, R, z_top + ch)), ((-kr, -kr, -kh), (kr, kr, 0.0))],
        budget=BUDGETS["SM_CSK_Light_Pendant"],
        data={"footprint_mm": [2 * R, 2 * R, -z_rim], "pose": "ceiling-hung",
              "pivot": "Seat = Mount = the canopy's top (the ceiling); Light inside the dome, +X down",
              "tint": "M_CSK_PowderBlack MI: matte black (default) or matte white (sheet 34)",
              "reference": "sheet 34 (3) (csk_lights.png)",
              "notes": ["Sheet 34: the dome profile measured row by row; 300 x 250 and the 1000 cord are the "
                        "printed call-outs (the drawing's cord is shorter than its label)",
                        "The inside of the shade is M_CSK_LED (it glows in the lit state)"]},
    )


# =========================================================================== registry

ITEMS = {
    "ij_shell_sign_openclosed": item_sign_openclosed,
    "ij_shell_sign_openclosed_plate": item_sign_openclosed_plate,
    "ij_shell_pricetag_shelf": item_pricetag_shelf,
    "ij_shell_pricetag_tent": item_pricetag_tent,
    "ij_shell_pricetag_hook": item_pricetag_hook,
    "ij_shell_poster_a2": item_poster_a2,
    "ij_shell_poster_a1": item_poster_a1,
    "ij_shell_sign_storefront": item_sign_storefront,
    "ij_shell_sign_hanging": item_sign_hanging,
    "ij_shell_wall": item_wall,
    "ij_shell_wall_window": item_wall_window,
    "ij_shell_wall_window_glass": item_wall_window_glass,
    "ij_shell_wall_door": item_wall_door,
    "ij_shell_floor": item_floor,
    "ij_shell_ceiling": item_ceiling,
    "ij_shell_door_entry": item_door_leaf,
    "ij_shell_door_entry_frame": item_door_frame,
    "ij_shell_light_panel600": item_light_panel,
    "ij_shell_light_track2000": item_light_track,
    "ij_shell_light_trackhead": item_light_trackhead,
    "ij_shell_light_trackhead_spot": item_light_trackhead_spot,
    "ij_shell_light_pendant": item_light_pendant,
}
