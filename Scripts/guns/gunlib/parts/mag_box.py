"""Straight box magazine (gunlib 0.2.0; GUN_BUILDING_STUDY 5.6, SMG_BUILD_PLAN 12, R16). Plain Python (numpy).

The real pattern of a straight double-stack magazine: a housing (polymer moulded or steel) whose section is a
rounded rectangle, a double stack tapering to a single-feed or double-feed top through the feed lips (the housing's
wall turned inward over the follower), a follower visible between the lips with the magazine empty, a floor plate
(slide-on cap or lock plate) at the bottom, a catch notch in the rear (or side) face whose top is the square bearing
face the catch nose sits on. Moulded housings add a raised spine rib (with the mould's parting line on its crest) and
recessed side panels ("ladder" channels crossed by flush ties). No cartridge is modelled unless the sheet shows one.

Frame = the magazine frame: origin at the well-entry centre (the ``Mag`` socket), +Z out of the well along the
insertion axis, +X forward, +Y = the gun's left. Every generator here builds in that frame; ``placement`` maps it
into the gun's frame M (``Mag_in_M`` and the mag axes of the spec's ``frames.mag``).

Construction: the housing is ONE closed shell built by construction (outer rings up the body, the top rim, the lip
rings and the cavity rings down to a hidden cavity floor): no boolean, so no run-out strip. Channels, the spine rib
and the catch notch are the only booleans (``PartDef`` unions / cutters, each >= 0.1 mm from other edges by
construction: the caller's numbers are checked by ``check_params``). Rounded section corners keep a segment count
per corner that gunlib.lod halves at LOD1.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .. import lod as _lod
from ..geo2d import rounded_rect
from ..mesh import Mesh, box, loft, prism


def section(length: float, thickness: float, r_front: float, r_rear: Optional[float] = None, seg: int = 4,
            n: Optional[int] = None) -> np.ndarray:
    """Rounded-rectangle section in the mag frame XY (x fore-aft centred on 0, y thickness), counter-clockwise,
    starting at the rear-right corner, 4 x (seg + 1) points (no point inside a straight side: a collinear vertex
    triangulates into a zero-area sliver), so every ring of a loft has the same parametrization.
    ``n`` resamples to a fixed count (rings of different corner radii must match)."""
    r_rear = r_front if r_rear is None else r_rear
    a0, a1, b0, b1 = -length / 2.0, length / 2.0, -thickness / 2.0, thickness / 2.0
    seg = _lod.count(seg, 1)
    pts = []
    # corners: rear-right (a0, b0), front-right (a1, b0), front-left (a1, b1), rear-left (a0, b1)
    for (cx, cy, s, r) in ((a1 - r_front, b0 + r_front, -90, r_front), (a1 - r_front, b1 - r_front, 0, r_front),
                           (a0 + r_rear, b1 - r_rear, 90, r_rear), (a0 + r_rear, b0 + r_rear, 180, r_rear)):
        t = np.radians(np.linspace(s, s + 90, seg + 1))
        pts.append(np.c_[cx + r * np.cos(t), cy + r * np.sin(t)])
    P = np.vstack(pts)
    k = 3 * (seg + 1)                                   # start at the rear-right corner's first point (no point on a
    P = np.vstack([P[k:], P[:k]])                       # straight side: a collinear vertex triangulates into a sliver)
    if n is not None:
        P = _resample_closed(P, n)
    return P


def _resample_closed(P, n):
    Q = np.vstack([P, P[:1]])
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0.0, d[-1], n, endpoint=False)
    return np.c_[np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])]


def lip_ring(inner: np.ndarray, opening: float, x_front: float, x_rear: float = -1e9, flare: float = 3.0) -> np.ndarray:
    """The feed-lip opening at the top: the inner ring squeezed across Y to ``opening`` between x_rear and x_front
    (the single-feed throat), easing back to the full inner width over ``flare`` mm ahead of x_front (the round's
    nose). A scale in Y keeps every point distinct and in order (same point count as ``inner``)."""
    Q = inner.copy()
    w = float(inner[:, 1].max() - inner[:, 1].min())
    s0 = min(1.0, opening / max(w, 1e-9))
    for i, (x, y) in enumerate(Q):
        if x < x_rear:
            continue
        u = 0.0 if x <= x_front else min(1.0, (x - x_front) / max(flare, 1e-6))
        Q[i, 1] = y * (s0 + (1.0 - s0) * u)
    return Q


def housing(sec_outer: np.ndarray, wall: float, z_bottom: float, z_top: float, lips: Optional[Dict] = None,
            cavity_floor_z: Optional[float] = None, taper: float = 0.0, sec_inner: Optional[np.ndarray] = None) -> Mesh:
    """The housing shell: outer rings z_bottom -> z_top (the section scaled by (1 + taper x (z - z_bottom)) about
    its centre), the top rim to the lip ring, the lip turn-down (lip height ``lips['height']``) to the full inner ring,
    the cavity walls down to ``cavity_floor_z`` and its floor. The bottom is closed (the floor plate covers it)."""
    n = len(sec_outer)
    c = sec_outer.mean(0)

    def scaled(P, z):
        s = 1.0 + taper * (z - z_bottom)
        return c + (P - c) * s

    if sec_inner is None:
        # an offset collapses rounded corners whose radius is under the wall (micro edges: UD); prefer sec_inner
        from ..geo2d import offset as _offset
        inner = _offset(sec_outer, -wall)
        inner = _resample_closed(inner, n) if len(inner) != n else inner
        k = int(np.argmin(np.linalg.norm(inner - sec_outer[0], axis=1)))
        inner = np.roll(inner, -k, axis=0)
    else:
        inner = np.asarray(sec_inner, float)
        if len(inner) != n:
            raise ValueError("sec_inner needs the outer section's point count (%d != %d)" % (len(inner), n))
    lips = lips or {}
    lip_h = float(lips.get("height", wall))
    lr = lip_ring(inner, lips["opening"], lips["x_front"], lips.get("x_rear", -1e9), lips.get("flare", 3.0)) if "opening" in lips \
        else inner
    zc = (z_top - 4.0 * wall) if cavity_floor_z is None else cavity_floor_z
    rings = []
    zs_out = [z_bottom, z_top]
    for z in zs_out:
        P = scaled(sec_outer, z)
        rings.append(np.c_[P, np.full(n, z)])
    # the top rim inward, then down the cavity
    Pl = scaled(lr, z_top)
    rings.append(np.c_[Pl, np.full(n, z_top)])
    Pi = scaled(inner, z_top - lip_h)
    rings.append(np.c_[Pi, np.full(n, z_top - lip_h)])
    Pc = scaled(inner, zc)
    rings.append(np.c_[Pc, np.full(n, zc)])
    return loft(rings, cap0=True, cap1=True)


def ladder_cutters(x0: float, x1: float, z0: float, z1: float, depth: float, side_y: float, ties: Sequence[float] = (),
                   tie_w: float = 3.0, r: float = 1.0) -> List[Mesh]:
    """Recessed side channels (one per side) from z0 to z1 between x0 and x1, ``depth`` into the wall at |y| =
    side_y, broken by flush ties (bands of ``tie_w`` mm where the wall stays) at the ``ties`` heights. Returns
    cutter prisms (rounded ends, radius r) for both sides."""
    zs = [z0] + sorted(t for t in ties if z0 < t < z1) + [z1]
    out = []
    for a, b in zip(zs[:-1], zs[1:]):
        a2 = a + (tie_w / 2.0 if a != z0 else 0.0)
        b2 = b - (tie_w / 2.0 if b != z1 else 0.0)
        if b2 - a2 < 2.0 * r + 0.2:
            continue
        outline = rounded_rect(x0, x1, a2, b2, r, seg=3)
        for s in (1.0, -1.0):
            y_in, y_out = s * (side_y - depth), s * (side_y + 1.0)
            out.append(prism(outline, min(y_in, y_out), max(y_in, y_out), "XZ"))
    return out


def notch_cutter(face_x: float, z_top: float, width: float, height: float, depth: float, rear: bool = True) -> Mesh:
    """The catch notch: a pocket ``depth`` into the rear (or front) face, ``width`` across Y, its TOP (the square
    bearing face the catch nose sits on) at z_top, ``height`` tall."""
    if rear:
        return box(face_x - 1.0, face_x + depth, -width / 2.0, width / 2.0, z_top - height, z_top)
    return box(face_x - depth, face_x + 1.0, -width / 2.0, width / 2.0, z_top - height, z_top)


def spine_rib(x_face: float, z0: float, z1: float, width: float, proud: float, front: bool = True) -> Mesh:
    """A raised spine rib on the front (or rear) face, ``proud`` mm, ``width`` across Y (unioned to the housing; it
    overlaps the wall by 0.5 mm so the union is clean)."""
    if front:
        return box(x_face - 0.5, x_face + proud, -width / 2.0, width / 2.0, z0, z1)
    return box(x_face - proud, x_face + 0.5, -width / 2.0, width / 2.0, z0, z1)


def follower(length_in: float, thick_in: float, r_in: float, z_top: float, height: float, clearance: float = 0.3,
             seg: int = 4) -> Mesh:
    """The follower: a block in the cavity (inner length / thickness / corner radius), ``clearance`` off the walls,
    top at z_top; its section is built, not offset (no collapsed corners)."""
    P = section(length_in - 2 * clearance, thick_in - 2 * clearance, max(1.0, r_in - clearance), None, seg)
    return prism(P, z_top - height, z_top, "XY")


def floor_plate(sec_outer: np.ndarray, z_top: float, thickness: float, overhang: float = 1.5, r: float = 3.0,
                tab_hole: Optional[Tuple[float, float, float]] = None) -> Tuple[Mesh, List[Mesh]]:
    """Floor plate (cap) below the housing: the housing section grown by ``overhang`` (the lip proud of the body),
    ``thickness`` tall, top at z_top - 0.01 (a butt joint). ``tab_hole`` (x, y, dia): the locking plate's hole in the
    bottom face (a 0.6 mm deep cutter; the tab shows flush in it). Returns (solid, cutters)."""
    from ..geo2d import offset as _offset
    P = _offset(sec_outer, overhang)
    m = prism(P, z_top - 0.01 - thickness, z_top - 0.01, "XY")
    cut = []
    if tab_hole:
        x, y, d = tab_hole
        from ..mesh import cylinder
        zb = z_top - 0.01 - thickness
        cut.append(cylinder((x, y, zb - 1.0), (x, y, zb + 0.6), d / 2.0, 32))
    return m, cut


def placement(origin_M, z_axis_M, x_axis_M) -> np.ndarray:
    """4x4 mag frame -> gun frame M (spec frames.mag: Mag_in_M, z_axis_in_M, x_axis_in_M)."""
    z = np.asarray(z_axis_M, float)
    z /= np.linalg.norm(z)
    x = np.asarray(x_axis_M, float)
    x = x - (x @ z) * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, np.asarray(origin_M, float)
    return M


def check_params(length, thickness, wall, lips=None, notch=None, ladder=None) -> List[str]:
    """Construction checks the generator relies on (UD: no feature closer than 0.1 mm to another edge)."""
    bad = []
    if wall < 1.0:
        bad.append("wall %.2f < 1.0 mm (moulded housing)" % wall)
    if lips and lips.get("opening", 0) >= thickness - 2 * wall:
        bad.append("lip opening not narrower than the inner width")
    if notch and notch.get("depth", 0) > wall - 0.1 + 1e-9 and not notch.get("through", False):
        bad.append("notch depth %.2f leaves < 0.1 mm of wall (declare through=True for a window)" % notch["depth"])
    if ladder and ladder.get("depth", 0) > wall - 0.6:
        bad.append("ladder depth %.2f leaves < 0.6 mm of wall" % ladder["depth"])
    return bad


def magazine(length: float, thickness: float, z_bottom: float, z_top: float, wall: float = 2.0,
             r_front: float = 3.0, r_rear: float = 2.5, lips: Optional[Dict] = None, notch: Optional[Dict] = None,
             ladder: Optional[Dict] = None, spine: Optional[Dict] = None, plate: Optional[Dict] = None,
             follower_depth: float = 6.0, seg: int = 4, M4=None, slot: str = "M_Mag", prefix: str = "magazine"):
    """PartDefs (gunlib.parts) for a straight box magazine in the mag frame (or placed by M4): the housing (with the
    notch, ladder channels and spine rib as booleans), the follower and the floor plate. Returns (parts, record)."""
    from . import PartDef
    sec = section(length, thickness, r_front, r_rear, seg)
    ri_f, ri_r = max(1.0, r_front - wall), max(1.0, r_rear - wall)    # >= 1.0: no cap sliver at 4 segments
    sec_in = section(length - 2 * wall, thickness - 2 * wall, ri_f, ri_r, seg)
    lips = lips or {"opening": max(8.0, thickness - 2 * wall - 6.0), "x_front": length / 2.0 - wall - 8.0,
                    "x_rear": -length / 2.0, "height": wall}
    z_cav = z_top - lips.get("height", wall) - follower_depth - 25.0
    shell = housing(sec, wall, z_bottom, z_top, lips, cavity_floor_z=z_cav, sec_inner=sec_in)
    cutters, unions = [], []
    if notch:
        cutters.append(notch_cutter(-length / 2.0, notch["z_top"], notch["width"], notch["height"], notch["depth"]))
    if ladder:
        cutters += ladder_cutters(ladder["x0"], ladder["x1"], ladder["z0"], ladder["z1"], ladder["depth"], thickness / 2.0,
                                  ladder.get("ties", ()), ladder.get("tie_w", 3.0), ladder.get("r", 1.0))
    if spine:
        unions.append(spine_rib(length / 2.0, spine["z0"], spine["z1"], spine["width"], spine["proud"], True))
    T = (lambda m: m) if M4 is None else (lambda m: m.transformed(M4))
    fz = z_top - lips.get("height", wall) - follower_depth
    fol = follower(length - 2 * wall, thickness - 2 * wall, min(ri_f, ri_r), fz, 20.0, seg=seg)
    pl = plate or {"thickness": 7.5, "overhang": 1.5}
    plate_m, plate_cut = floor_plate(sec, z_bottom, pl["thickness"], pl.get("overhang", 1.5),
                                     tab_hole=pl.get("tab_hole"))
    # P-round edges: 0.4 x 2 on the OUTSIDE convex ~90 deg edges only (the moulded corner radii are geometry; 0.4
    # keeps the rim radius under half a 1.0 mm ladder recess; the lips and the cavity keep their turned edges, so the
    # lip turn-down never takes a partial bevel)
    Minv = np.linalg.inv(np.eye(4) if M4 is None else np.asarray(M4, float))
    hx_in, hy_in = length / 2.0 - wall + 0.2, thickness / 2.0 - wall + 0.2

    def outside(mid, d, n1, n2, dih, convex):
        if not convex or not (60.0 <= dih <= 120.0):
            return 0.0
        q = Minv[:3, :3] @ mid + Minv[:3, 3]
        if abs(q[0]) < hx_in and abs(q[1]) < hy_in and q[2] > z_cav - 0.5:
            return 0.0                                           # the lips and the cavity
        return 1.0
    parts = (PartDef(prefix, [T(shell)], bone="magazine", cls="P-round", slot=slot, cutters=[T(c) for c in cutters],
                     unions=[T(u) for u in unions], recipe=[(0.4, 2, "WC", outside)],
                     joint={"type": "seated", "parent": "magwell"}),
             PartDef(prefix + "_follower", [T(fol)], bone="magazine", cls="P-round", slot=slot, recipe=[(0.3, 1, 50.0)],
                     joint={"type": "sliding", "parent": prefix}),
             PartDef(prefix + "_floor_plate", [T(plate_m)], bone="magazine", cls="P-round", slot=slot,
                     cutters=[T(c) for c in plate_cut], recipe=[(0.6, 2, 50.0)],
                     joint={"type": "butt", "parent": prefix, "gap_mm": [0.01, 0.05]}))
    rec = {"frame": "mag: origin Mag (well-entry centre), +Z out of the well, +X forward", "length": length,
           "thickness": thickness, "wall": wall, "z_bottom": z_bottom, "z_top": z_top, "lips": lips,
           "follower_top_z": fz, "notch": notch, "ladder": ladder, "spine": spine, "plate": pl,
           "checks": check_params(length, thickness, wall, lips, notch, ladder)}
    return parts, rec
