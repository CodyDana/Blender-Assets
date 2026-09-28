"""Kunai spec (library 3.10): pure data and pure-Python geometry, no bpy.

References/Kunai/KUNAI_STUDY.md, section 4 (the BUILD-TO table is authoritative) and section 5 (modelling notes).
The winged three-prong look the user chose: a leaf main blade, two side prongs rooted at the fork plane, a round
wrapped grip and a ring pommel.  No lettering is modelled; the grip carries a blank band for the user's own.

Design frame (millimetres, every number here): X along the long axis, +X toward the tip; Y across in the blade plane;
Z through the thickness; X = 0 is the fork plane.  The tip is at X = +140, the ring's far end at X = -140.  The stored
mesh is this frame shifted along X by the mass-weighted centre (``shift``, about -19 mm) and scaled to metres, so
the object origin IS the centre of mass (study 5: steel at 7.85 g/cm3, the wrap at its own densities - never Origin
to Center of Mass (Volume), which counts the 20 mm grip as steel).

The steel head is built like the stars (a hub with arms): a flat 5 mm PLATEAU (the fork block, the stock the three
blades are forged from) and three DIAMOND blades - the main blade and the two prongs - each a ridge down its axis
with flat faces falling to a 1.5 mm un-ground edge (the study's shallow diamond).  Each blade leaves the plateau at
a PLUNGE station: its ridge is at stock height there, and one planar plunge triangle per side joins the plateau to
the first diamond section (the plunge line of a ground knife).  The cutting edges (both blade edges, both edges of
each prong) carry the pack's knife grind, 35 deg per side to a 0.15 mm land; past each blade's APEX (where the grind
reaches the ridge) the two facets meet in a ridge on the axis and the point ends in a 0.15 mm vertical chisel edge
(tip radius 0.075 mm).  At the plunge the grind RUNS OUT over 3 mm into the plateau's 0.45 mm chamfer + wall (the
stars' root run-out); the crotch between blade and prong is a small fillet at plateau thickness (the stars' scallop,
treated as a cavity corner); the rear shoulders and the (hidden) rear face carry the chamfer too.

The main blade outline is the study's: straight from 16 mm wide at the fork to 36 mm at X = 35 (a kite corner),
then h = 18 (1 - u)(1 + 0.25 u) to the tip.  The prongs: root centre (0, +-13), axis 38 deg off the main axis, 60 mm
long, half width w = 7 (1 - f)(1 + 0.25 f); tips at (47.28, +-49.94).  Ridges: blade 5.0 mm to X = 35 then linear to
1.6 mm at X = 135; prongs 5.0 mm at their plunge, linear to 1.6 mm at the tip.

Everything behind the fork (grip, neck, ring) is separate closed shells that interpenetrate where they join, the
usual game-asset construction: the WRAP (a 20 mm cylinder with 6 mm collars of doubled tape at both ends, 21.2 mm
over the collars; the tape helix is a baked normal map), the NECK (the bare tang between the wrap and the ring,
16 x 5 mm tapering to 8 x 4 mm, its end buried in the ring) and the RING (a true torus: 13 mm centre radius, a
6 mm radial x 5 mm elliptical section: ID 20, OD 32 mm).  The tang under the wrap is never visible and is not
modelled; its 16 x 5 mm section is counted analytically in the steel volume.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

from .spec import LOD_SCREEN_SIZES, MM

TAN_GRIND = math.tan(math.radians(35.0))

# The study's hard numbers (section 4), mm.  ESTIMATE / DERIVED / SOURCED flags live in the build script's build_to.
OVERALL = 280.0
X_TIP = 140.0
BLADE_BASE_HALF = 8.0
BLADE_MAX_HALF = 18.0
BLADE_MAX_AT = 35.0
LEAF_BULGE = 0.25
RIDGE_BASE = 5.0
RIDGE_TIP = 1.6
RIDGE_TIP_AT = 135.0
EDGE_T = 1.5                  # un-ground edge thickness ("1.5 mm shoulder")
LAND = 0.15
STOCK = 5.0
PRONG_ANGLE_DEG = 38.0
PRONG_L = 60.0
PRONG_ROOT_OFF = 13.0
PRONG_ROOT_HALF = 7.0
REAR_X = -6.0                 # the head's hidden rear face (inside the wrap)
REAR_HALF = 8.0               # the tang half width where the head meets it
CHAMFER = 0.45                # plateau-zone chamfer (plan width) at the grind angle: the stars' scallop chamfer
RUNOUT = 3.0                  # the knife grind runs out over this arc length into the chamfer (spec.GRIND_RUNOUT_MM)
CHAMFER_RUN = 0.4             # plateau-zone edge between the fillet and the run-out
FILLET_R = 0.8                # crotch fillet (study ESTIMATE 2 mm: in a 27 deg V that moves the notch 6.5 mm out)

WRAP_X0, WRAP_X1 = -102.5, -5.5    # wrap end planes (its front cap sits 0.5 mm inside the steel shoulder)
WRAP_R = 10.0
COLLAR_R = 10.6
COLLAR_L = 6.0
COLLAR_BEVEL = 0.3
BAND_X0, BAND_X1 = -90.0, -18.0    # the lettering band on the grip's +Z face
BAND_HALF_DEG = 36.0               # +-36 deg about the top: 12.57 mm of arc at r = 10 (a grip vertex line at LOD0-2)
NECK_X0, NECK_X1, NECK_X2 = -100.0, -102.5, -110.5   # hidden start, the wrap's rear cap plane, the buried end
NECK_HALF = (8.0, 2.5)             # half width, half thickness at the wrap
NECK_END_HALF = (4.0, 2.0)         # ... at the buried end
NECK_CHAMFER = 0.6
RING_CX = -124.0
RING_R = 13.0
RING_A, RING_B = 3.0, 2.5          # elliptical section semi-axes: radial, z

STEEL_G_CM3 = 7.85
CORE_G_CM3 = 0.70                  # wooden core, the middle of the study's 0.6-0.8
TAPE_G_CM3 = 0.75                  # wound cotton tape, the middle of 0.6-0.9
CORE_R = 9.0                       # 18 mm core under a 1 mm tape wrap


# =========================================================================== basic curves


def h_blade(x: float) -> float:
    """Main blade half width at design x (0 <= x <= 140)."""
    if x <= BLADE_MAX_AT:
        return BLADE_BASE_HALF + (BLADE_MAX_HALF - BLADE_BASE_HALF) * x / BLADE_MAX_AT
    u = (x - BLADE_MAX_AT) / (X_TIP - BLADE_MAX_AT)
    return BLADE_MAX_HALF * (1.0 - u) * (1.0 + LEAF_BULGE * u)


def dh_blade(x: float, side: int = 0) -> float:
    """dh/dx; at the kite corner (x = 35) side -1 / +1 picks the one-sided derivative."""
    if x < BLADE_MAX_AT or (x == BLADE_MAX_AT and side < 0):
        return (BLADE_MAX_HALF - BLADE_BASE_HALF) / BLADE_MAX_AT
    u = (x - BLADE_MAX_AT) / (X_TIP - BLADE_MAX_AT)
    return BLADE_MAX_HALF * (-(1.0 + LEAF_BULGE * u) + LEAF_BULGE * (1.0 - u)) / (X_TIP - BLADE_MAX_AT)


def ridge_blade(x: float) -> float:
    if x <= BLADE_MAX_AT:
        return RIDGE_BASE
    t = RIDGE_BASE + (RIDGE_TIP - RIDGE_BASE) * (x - BLADE_MAX_AT) / (RIDGE_TIP_AT - BLADE_MAX_AT)
    return max(RIDGE_TIP, t)


class Prong:
    """The upper prong's frame (y > 0); the lower prong is its mirror in y."""

    def __init__(self, u_plunge: float = 0.0) -> None:
        a = math.radians(PRONG_ANGLE_DEG)
        self.d = (math.cos(a), math.sin(a))              # axis direction
        self.n = (-math.sin(a), math.cos(a))             # + side = the OUTER edge
        self.c = (0.0, PRONG_ROOT_OFF)
        self.u_plunge = u_plunge

    def w(self, u: float) -> float:
        f = u / PRONG_L
        return PRONG_ROOT_HALF * (1.0 - f) * (1.0 + LEAF_BULGE * f)

    def dw(self, u: float) -> float:
        f = u / PRONG_L
        return PRONG_ROOT_HALF * (-(1.0 + LEAF_BULGE * f) + LEAF_BULGE * (1.0 - f)) / PRONG_L

    def ridge(self, u: float) -> float:
        if u <= self.u_plunge:
            return RIDGE_BASE
        return RIDGE_BASE + (RIDGE_TIP - RIDGE_BASE) * (u - self.u_plunge) / (PRONG_L - self.u_plunge)

    def xy(self, u: float, v: float) -> Tuple[float, float]:
        return (self.c[0] + u * self.d[0] + v * self.n[0], self.c[1] + u * self.d[1] + v * self.n[1])

    def uv(self, x: float, y: float) -> Tuple[float, float]:
        dx, dy = x - self.c[0], y - self.c[1]
        return dx * self.d[0] + dy * self.d[1], dx * self.n[0] + dy * self.n[1]

    def edge(self, u: float, side: int) -> Tuple[float, float]:
        """Outline point of the outer (side +1) or inner (side -1) edge."""
        return self.xy(u, side * self.w(u))

    def edge_frame(self, u: float, side: int):
        """(tangent toward +u, inward unit normal) of an edge in xy."""
        dw = self.dw(u)
        tu, tv = 1.0, side * dw
        norm = math.hypot(tu, tv)
        tu, tv = tu / norm, tv / norm
        nu, nv = side * tv, -side * tu                   # rotate toward the axis
        # check: inward means toward v = 0
        if nv * side > 0.0:
            nu, nv = -nu, -nv
        t = (tu * self.d[0] + tv * self.n[0], tu * self.d[1] + tv * self.n[1])
        n = (nu * self.d[0] + nv * self.n[0], nu * self.d[1] + nv * self.n[1])
        return t, n


# =========================================================================== height fields (half heights, mm)


def z_blade_face(x: float, y: float) -> float:
    """Top of the un-ground blade diamond at (x, y): linear from the 1.5 mm edge to the ridge."""
    h = h_blade(min(max(x, 0.0), X_TIP))
    if h <= 1e-12:
        return 0.5 * EDGE_T
    t = ridge_blade(x)
    return 0.5 * (EDGE_T + (t - EDGE_T) * (1.0 - abs(y) / h))


def z_prong_face(p: Prong, x: float, y: float) -> float:
    u, v = p.uv(x, y)
    w = p.w(min(max(u, 0.0), PRONG_L))
    if w <= 1e-12:
        return 0.5 * EDGE_T
    return 0.5 * (EDGE_T + (p.ridge(u) - EDGE_T) * (1.0 - abs(v) / w))


def solve_inset(face, ex: float, ey: float, bx: float, by: float, c: float, land_half: float,
                s_axis: float) -> Tuple[float, bool]:
    """Perpendicular inset s of the knife grind line at an edge point: the 35 deg facet (land_half + s tan) meets the
    face ``face(x, y)``.  Returns (s, past_apex); past the apex the facet reaches the part's axis (s_axis) first."""
    def f(s):
        k = s / c
        return face(ex + k * bx, ey + k * by) - (land_half + s * TAN_GRIND)
    if f(s_axis) >= 0.0:
        return s_axis, True
    lo, hi = 0.0, s_axis
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), False


def _bisect(fn, lo: float, hi: float, iters: int = 90) -> float:
    flo = fn(lo)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = fn(mid)
        if (fm > 0.0) == (flo > 0.0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _unit(x: float, y: float) -> Tuple[float, float]:
    n = math.hypot(x, y)
    return x / n, y / n


# =========================================================================== LOD spec


@dataclass(frozen=True)
class KunaiLodSpec:
    """One kunai LOD.  Counts are intervals; ``land`` 0 = the edge line (LOD2), ``chamfer`` 0 = square edges."""

    blade_base_intervals: int = 3        # plunge -> the kite corner (x = 35)
    blade_leaf_intervals: int = 14       # corner -> the apex
    blade_tip_intervals: int = 2         # apex -> tip
    prong_intervals: int = 8             # plunge -> the prong apex
    prong_tip_intervals: int = 2
    fillet_segments: int = 3
    outer_chamfer_intervals: int = 2     # the prong's outer edge, run-out end -> root corner
    rear_intervals: int = 2              # the hidden rear face
    land: float = LAND
    chamfer: float = CHAMFER
    plateau_steiner: int = 1             # interior points of the plateau triangulation (0 / 1 / 2 rows)
    grip_sides: int = 20
    collars: str = "bevel"               # "bevel" | "step" | "none"
    ring_segments: int = 24
    ring_section: int = 8
    neck_chamfer: float = NECK_CHAMFER
    band: Tuple[int, int] = (1600, 2800)
    note: str = ""

    def validate(self) -> None:
        if self.grip_sides % 10:
            raise ValueError("grip_sides must be a multiple of 10: the band edges (+-36 deg) and the bottom seam are "
                             f"vertex lines ({self.grip_sides})")
        if self.ring_segments % 2 or self.ring_section % 2:
            raise ValueError("ring segment counts must be even (seams at vertex lines)")
        if self.collars not in ("bevel", "step", "none"):
            raise ValueError(f"collars: {self.collars}")


def unground_lod(lod: KunaiLodSpec) -> KunaiLodSpec:
    """The same LOD authored without any grind or chamfer: the mass gate's reference (knife columns inset 0 at the
    1.5 mm edge, plateau edges square)."""
    return replace(lod, land=-1.0, chamfer=0.0, neck_chamfer=0.0)


# =========================================================================== columns


@dataclass
class Col:
    ex: float
    ey: float
    bx: float = 0.0
    by: float = 0.0
    s: float = 0.0
    c: float = 1.0
    ix: float = 0.0
    iy: float = 0.0
    iz: float = 0.0
    zw: float = 0.0
    zone: str = "knife"          # knife | chamfer | tip
    part: str = "blade"          # blade | prong_in | prong_out | plateau
    chain: str = "front"         # front | outer | rear (the UV wall strips)
    tag: str = ""
    axis: bool = False           # inner point on the part's axis (shared with the other side)
    key: Optional[tuple] = None  # identity of a shared axis point


@dataclass
class Station:
    """One diamond section: the knife columns on both sides share the ridge point R (None past the apex)."""
    part: str
    at: float                    # x (blade) or u (prong) of the outline station
    cols: Tuple[int, ...]        # indices of the knife columns (blade: 1, prong: inner, outer)
    ridge: Optional[Tuple[float, float, float]]
    past_apex: bool


@dataclass
class KunaiOutline:
    """Everything the generator authors for one LOD, upper half (y >= 0), design mm."""
    lod: KunaiLodSpec
    cols: List[Col]
    blade: List[Station]
    prong: List[Station]
    plunges: List[Tuple[str, int, int, Tuple[float, float, float]]]   # (part, c_top col, c_0 col, ridge point)
    runouts: List[Tuple[int, int]]                                     # (chamfer-side col, knife-side col)
    plateau: List[Tuple[float, float]]                                 # boundary polygon (CCW), mm
    plateau_keys: List[tuple]                                          # ("col", i) / ("ridge", part) per point
    steiner: List[Tuple[float, float]]
    info: Dict[str, float] = field(default_factory=dict)


class KunaiGeometryPlan:
    """The analytic head: crotch, fillet, plunges, apexes - computed once, sampled per LOD."""

    def __init__(self) -> None:
        self.prong = Prong()
        p = self.prong
        # crotch: the blade's straight base edge y = 8 + x (10/35) meets the prong's inner edge
        slope = (BLADE_MAX_HALF - BLADE_BASE_HALF) / BLADE_MAX_AT

        def gap(u):
            x, y = p.edge(u, -1)
            return y - (BLADE_BASE_HALF + slope * x)
        self.u_crotch = _bisect(gap, 0.5, 12.0)
        self.crotch = p.edge(self.u_crotch, -1)
        # fillet of radius r tangent to the blade line and the prong curve, its centre in the V (in the air)
        e1 = _unit(1.0, slope)                            # along the blade edge, away from the crotch
        n1 = (-e1[1], e1[0])                              # blade line normal toward +y (the air side of the V)

        def centre(u):
            t, n_in = p.edge_frame(u, -1)
            return (p.edge(u, -1)[0] - FILLET_R * n_in[0], p.edge(u, -1)[1] - FILLET_R * n_in[1])

        def dist_line(u):
            ox, oy = centre(u)
            return (ox - self.crotch[0]) * n1[0] + (oy - self.crotch[1]) * n1[1] - FILLET_R
        self.u_t2 = _bisect(dist_line, self.u_crotch + 1e-6, self.u_crotch + 12.0)
        self.fillet_centre = centre(self.u_t2)
        ox, oy = self.fillet_centre
        k = (ox - self.crotch[0]) * e1[0] + (oy - self.crotch[1]) * e1[1]
        self.t1 = (self.crotch[0] + k * e1[0], self.crotch[1] + k * e1[1])
        self.t2 = p.edge(self.u_t2, -1)
        # blade: chamfer run, run-out, plunge station (arc lengths along the straight base edge)
        self.x_ctop_b = self.t1[0] + CHAMFER_RUN * e1[0]
        self.x_plunge_b = self.x_ctop_b + RUNOUT * e1[0]
        # prong inner edge: arc length along the curve
        self.u_ctop_in = self._advance(-1, self.u_t2, CHAMFER_RUN)
        self.u_plunge = self._advance(-1, self.u_ctop_in, RUNOUT)
        p.u_plunge = self.u_plunge
        self.u_ctop_out = self._advance(+1, self.u_plunge, -RUNOUT)
        # apexes (where the knife grind reaches the ridge)
        self.x_apex = self._blade_apex()
        self.u_apex = self._prong_apex()

    # ------------------------------------------------------------------ helpers
    def _advance(self, side: int, u0: float, length: float) -> float:
        """u at arc length ``length`` from u0 along a prong edge (negative = backward)."""
        p, steps = self.prong, 400
        du = (6.0 if length > 0 else -6.0) * abs(length) / 4.0 / steps
        u, acc = u0, 0.0
        target = abs(length)
        while acc < target:
            a, b = p.edge(u, side), p.edge(u + du, side)
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            if acc + seg >= target:
                return u + du * (target - acc) / seg
            acc += seg
            u += du
        return u

    def blade_col(self, x: float, land_half: float, corner_side: int = 0) -> Tuple[Col, bool, float]:
        """A knife column of the +y blade edge at design x (the kite corner is mitred)."""
        ey = h_blade(x)
        if x == BLADE_MAX_AT:
            t_a = _unit(1.0, dh_blade(x, -1))
            t_b = _unit(1.0, dh_blade(x, +1))
            n_a, n_b = (t_a[1], -t_a[0]), (t_b[1], -t_b[0])       # inward (toward -y)
            b = _unit(n_a[0] + n_b[0], n_a[1] + n_b[1])
            c = b[0] * n_a[0] + b[1] * n_a[1]
        else:
            t = _unit(1.0, dh_blade(x))
            b, c = (t[1], -t[0]), 1.0
        if land_half < 0.0:                               # un-ground reference: no grind at all
            col = Col(ex=x, ey=ey, bx=b[0], by=b[1], s=0.0, c=c, ix=x, iy=ey, iz=0.5 * EDGE_T, zw=0.5 * EDGE_T,
                      zone="knife", part="blade")
            return col, False, 0.0
        s_axis = ey * c / (-b[1])                         # perpendicular inset at which the inner point reaches y = 0
        s, past = solve_inset(z_blade_face, x, ey, b[0], b[1], c, land_half, s_axis)
        k = s / c
        ix, iy = x + k * b[0], ey + k * b[1]
        if past:
            iy = 0.0
        iz = land_half + s * TAN_GRIND
        col = Col(ex=x, ey=ey, bx=b[0], by=b[1], s=s, c=c, ix=ix, iy=iy, iz=iz, zw=land_half, zone="knife",
                  part="blade", axis=past)
        return col, past, s

    def prong_col(self, u: float, side: int, land_half: float) -> Tuple[Col, bool, float]:
        p = self.prong
        ex, ey = p.edge(u, side)
        t, n = p.edge_frame(u, side)
        part = "prong_out" if side > 0 else "prong_in"
        if land_half < 0.0:
            return (Col(ex=ex, ey=ey, bx=n[0], by=n[1], s=0.0, c=1.0, ix=ex, iy=ey, iz=0.5 * EDGE_T,
                        zw=0.5 * EDGE_T, zone="knife", part=part), False, 0.0)
        # distance along n to the prong axis (v = 0)
        nv = n[0] * p.n[0] + n[1] * p.n[1]
        s_axis = abs(p.w(u) / nv)
        s, past = solve_inset(lambda x, y: z_prong_face(p, x, y), ex, ey, n[0], n[1], 1.0, land_half, s_axis)
        ix, iy = ex + s * n[0], ey + s * n[1]
        if past:                                          # snap onto the axis through one shared computation
            nu = n[0] * p.d[0] + n[1] * p.d[1]
            ix, iy = p.xy(u + s_axis * nu, 0.0)
        iz = land_half + s * TAN_GRIND
        return (Col(ex=ex, ey=ey, bx=n[0], by=n[1], s=s, c=1.0, ix=ix, iy=iy, iz=iz, zw=land_half, zone="knife",
                    part=part, axis=past), past, s)

    def _blade_apex(self) -> float:
        def g(x):
            _col, past, _s = self.blade_col(x, 0.5 * LAND)
            return 1.0 if past else -1.0
        return _bisect(g, BLADE_MAX_AT + 1.0, X_TIP - 0.01, 70)

    def _prong_apex(self) -> float:
        def g(u):
            _col, past, _s = self.prong_col(u, +1, 0.5 * LAND)
            return 1.0 if past else -1.0
        return _bisect(g, self.u_plunge + 1.0, PRONG_L - 0.01, 70)

    # ------------------------------------------------------------------ one LOD
    def outline(self, lod: KunaiLodSpec) -> KunaiOutline:
        p = self.prong
        land_half = 0.5 * lod.land if lod.land >= 0.0 else -1.0
        unground = lod.land < 0.0
        ch = lod.chamfer
        z_plate = 0.5 * STOCK
        cols: List[Col] = []
        blade: List[Station] = []
        prong: List[Station] = []

        def chamfer_col(x, y, b, c, part, chain, tag=""):
            k = ch / c
            return Col(ex=x, ey=y, bx=b[0], by=b[1], s=ch, c=c, ix=x + k * b[0], iy=y + k * b[1], iz=z_plate,
                       zw=z_plate - ch * TAN_GRIND, zone="chamfer", part=part, chain=chain, tag=tag)

        # ---- blade stations (increasing x), then the front chain runs from the tip backward
        xa = self.x_apex
        xs = [self.x_plunge_b + (BLADE_MAX_AT - self.x_plunge_b) * i / lod.blade_base_intervals
              for i in range(lod.blade_base_intervals)]
        xs += [BLADE_MAX_AT + (xa - BLADE_MAX_AT) * i / lod.blade_leaf_intervals
               for i in range(lod.blade_leaf_intervals)]
        if unground:
            # no apex without a grind: the diamond runs to the last station before the tip
            xs += [xa + (X_TIP - xa) * i / lod.blade_tip_intervals for i in range(lod.blade_tip_intervals)]
        else:
            xs += [xa + (X_TIP - xa) * i / lod.blade_tip_intervals for i in range(lod.blade_tip_intervals)]
        blade_cols = []
        for x in xs:
            col, past, _s = self.blade_col(x, land_half)
            if x == xa and not unground:
                past = True
                col.iy, col.axis = 0.0, True
            col.tag = "station"
            blade_cols.append((x, col, past))
        tip = Col(ex=X_TIP, ey=0.0, ix=X_TIP, iy=0.0, iz=max(land_half, 0.0) if not unground else 0.5 * EDGE_T,
                  zw=max(land_half, 0.0) if not unground else 0.5 * EDGE_T, zone="tip", part="blade", tag="tip",
                  axis=True)
        if unground:
            tip.iz = tip.zw = 0.5 * EDGE_T
        # front chain: tip, blade stations descending
        cols.append(tip)
        for x, col, past in reversed(blade_cols):
            col.chain = "front"
            cols.append(col)
            blade.append(Station(part="blade", at=x, cols=(len(cols) - 1,),
                                 ridge=None if past else (col.ix, 0.0, 0.5 * ridge_blade(col.ix)), past_apex=past))
        blade.reverse()
        c0_b = len(cols) - 1
        e1 = _unit(1.0, (BLADE_MAX_HALF - BLADE_BASE_HALF) / BLADE_MAX_AT)
        b1 = (e1[1], -e1[0])
        ctop_b = chamfer_col(self.x_ctop_b, h_blade(self.x_ctop_b), b1, 1.0, "plateau", "front", "ctop")
        cols.append(ctop_b)
        i_ctop_b = len(cols) - 1
        cols.append(chamfer_col(self.t1[0], self.t1[1], b1, 1.0, "plateau", "front", "t1"))
        # fillet: from T1 to T2 around the centre (concave: the material is outside the circle)
        ox, oy = self.fillet_centre
        a1 = math.atan2(self.t1[1] - oy, self.t1[0] - ox)
        a2 = math.atan2(self.t2[1] - oy, self.t2[0] - ox)
        while a2 < a1:
            a2 += 2.0 * math.pi
        if a2 - a1 > math.pi:
            a2 -= 2.0 * math.pi
        for j in range(1, lod.fillet_segments):
            a = a1 + (a2 - a1) * j / lod.fillet_segments
            px, py = ox + FILLET_R * math.cos(a), oy + FILLET_R * math.sin(a)
            cols.append(chamfer_col(px, py, (math.cos(a), math.sin(a)), 1.0, "plateau", "front", "fillet"))
        _t, n_t2 = p.edge_frame(self.u_t2, -1)
        cols.append(chamfer_col(self.t2[0], self.t2[1], n_t2, 1.0, "plateau", "front", "t2"))
        ex, ey = p.edge(self.u_ctop_in, -1)
        _t, n_ci = p.edge_frame(self.u_ctop_in, -1)
        cols.append(chamfer_col(ex, ey, n_ci, 1.0, "plateau", "front", "ctop"))
        i_ctop_in = len(cols) - 1
        # prong stations (increasing u)
        ua = self.u_apex
        us = [self.u_plunge + (ua - self.u_plunge) * i / lod.prong_intervals for i in range(lod.prong_intervals)]
        us += [ua + (PRONG_L - ua) * i / lod.prong_tip_intervals for i in range(lod.prong_tip_intervals)]
        inner, outer = [], []
        for u in us:
            ci, past_i, _ = self.prong_col(u, -1, land_half)
            co, past_o, _ = self.prong_col(u, +1, land_half)
            if u == ua and not unground:
                past_i = past_o = True
                ci.ix, ci.iy = co.ix, co.iy = p.xy(u + ci.s * (ci.bx * p.d[0] + ci.by * p.d[1]), 0.0)
                ci.axis = co.axis = True
            if past_i and not unground:                   # the SAME axis point for both sides, bit for bit
                ci.ix, ci.iy = co.ix, co.iy
            ci.tag = co.tag = "station"
            inner.append((u, ci, past_i))
            outer.append((u, co, past_o))
        c0_in = len(cols)
        for u, ci, _p in inner:
            ci.chain = "front"
            cols.append(ci)
        ptip = Col(ex=p.xy(PRONG_L, 0.0)[0], ey=p.xy(PRONG_L, 0.0)[1], zone="tip", part="prong_in", tag="ptip",
                   axis=True, chain="front")
        ptip.ix, ptip.iy = ptip.ex, ptip.ey
        ptip.iz = ptip.zw = (max(land_half, 0.0) if not unground else 0.5 * EDGE_T)
        cols.append(ptip)
        i_ptip = len(cols) - 1
        # outer chain: prong tip (shared) then the outer stations descending
        c_out_first = len(cols)
        for (u, co, past) in reversed(outer):
            co.chain = "outer"
            cols.append(co)
        c0_out = len(cols) - 1
        for k, ((u, ci, past_i), (_u2, co, _po)) in enumerate(zip(inner, outer)):
            i_in = c0_in + k
            i_out = c0_out - k
            ridge = None if past_i else p.xy(0.5 * ((ci.ix - p.c[0]) * p.d[0] + (ci.iy - p.c[1]) * p.d[1]
                                                    + (co.ix - p.c[0]) * p.d[0] + (co.iy - p.c[1]) * p.d[1]), 0.0)
            if ridge is not None:
                u_r = (ridge[0] - p.c[0]) * p.d[0] + (ridge[1] - p.c[1]) * p.d[1]
                ridge = (ridge[0], ridge[1], 0.5 * p.ridge(u_r))
            prong.append(Station(part="prong", at=u, cols=(i_in, i_out), ridge=ridge, past_apex=past_i))
        # outer run-out end, chamfer back to the root corner
        ex, ey = p.edge(self.u_ctop_out, +1)
        _t, n_co = p.edge_frame(self.u_ctop_out, +1)
        cols.append(chamfer_col(ex, ey, n_co, 1.0, "plateau", "outer", "ctop"))
        i_ctop_out = len(cols) - 1
        for j in range(1, lod.outer_chamfer_intervals):
            u = self.u_ctop_out * (1.0 - j / lod.outer_chamfer_intervals)
            ex, ey = p.edge(u, +1)
            _t, n_u = p.edge_frame(u, +1)
            cols.append(chamfer_col(ex, ey, n_u, 1.0, "plateau", "outer", "outer_chamfer"))
        # root corner (mitre between the outer edge and the shoulder)
        root = p.edge(0.0, +1)
        rear = (REAR_X, REAR_HALF)
        t_out, n_out = p.edge_frame(0.0, +1)
        t_sh = _unit(rear[0] - root[0], rear[1] - root[1])
        n_sh = (t_sh[1], -t_sh[0])
        if n_sh[0] * (0.0 - root[0]) + n_sh[1] * (0.0 - root[1]) < 0.0:     # inward = toward the head's centre
            n_sh = (-n_sh[0], -n_sh[1])
        b = _unit(n_out[0] + n_sh[0], n_out[1] + n_sh[1])
        c = b[0] * n_sh[0] + b[1] * n_sh[1]
        cols.append(chamfer_col(root[0], root[1], b, c, "plateau", "outer", "root"))
        i_root = len(cols) - 1
        # rear corner (shoulder -> rear face x = REAR_X) and the rear face down to the axis
        n_rf = (1.0, 0.0)
        b = _unit(n_sh[0] + n_rf[0], n_sh[1] + n_rf[1])
        c = b[0] * n_rf[0] + b[1] * n_rf[1]
        cols.append(chamfer_col(rear[0], rear[1], b, c, "plateau", "rear", "rear_corner"))
        for j in range(1, lod.rear_intervals):
            y = REAR_HALF * (1.0 - j / lod.rear_intervals)
            cols.append(chamfer_col(REAR_X, y, n_rf, 1.0, "plateau", "rear", "rear"))
        cols.append(chamfer_col(REAR_X, 0.0, n_rf, 1.0, "plateau", "rear", "rear_axis"))
        cols[-1].axis = True
        cols[i_root].chain = "rear"     # the root corner starts the rear chain (it also ends the outer chain)

        # ---- plunges and run-outs
        rb = blade[0].ridge
        ri = prong[0].ridge
        plunges = [("blade", i_ctop_b, c0_b, rb), ("prong_in", i_ctop_in, c0_in, ri), ("prong_out", i_ctop_out,
                                                                                         c0_out, ri)]
        runouts = [(i_ctop_b, c0_b), (i_ctop_in, c0_in), (i_ctop_out, c0_out)]

        # ---- plateau boundary (CCW): the axis from the rear face to the blade ridge, the blade plunge top line,
        # the chamfer line round the crotch, the prong's two plunge top lines, the outer chamfer line, the shoulder,
        # the rear face
        poly, keys = [], []

        def add(pt, key):
            poly.append((pt[0], pt[1]))
            keys.append(key)
        add((cols[-1].ix, 0.0), ("col", len(cols) - 1))
        add((rb[0], 0.0), ("ridge", "blade"))
        for i in range(i_ctop_b, i_ctop_in + 1):
            add((cols[i].ix, cols[i].iy), ("col", i))
        add((ri[0], ri[1]), ("ridge", "prong"))
        for i in range(i_ctop_out, len(cols) - 1):
            add((cols[i].ix, cols[i].iy), ("col", i))
        steiner = []
        if lod.plateau_steiner:
            steiner += [(0.5 * (cols[-1].ix + rb[0]), 0.45 * REAR_HALF)]
            steiner += [(0.5 * (REAR_X + ri[0]) + 0.5, 0.5 * (REAR_HALF + ri[1]) + 1.0)]
            if lod.plateau_steiner > 1:
                steiner += [(0.35 * rb[0], 0.8 * REAR_HALF), (0.5 * (REAR_X + root[0]) + 3.0, 14.0)]
        info = {"x_plunge_blade": self.x_plunge_b, "x_ctop_blade": self.x_ctop_b, "u_plunge_prong": self.u_plunge,
                "u_ctop_in": self.u_ctop_in, "u_ctop_out": self.u_ctop_out, "x_apex_blade": self.x_apex,
                "u_apex_prong": self.u_apex, "crotch": self.crotch, "u_crotch": self.u_crotch,
                "fillet_centre": self.fillet_centre, "t1": self.t1, "t2": self.t2}
        return KunaiOutline(lod=lod, cols=cols, blade=blade, prong=prong, plunges=plunges, runouts=runouts,
                            plateau=poly, plateau_keys=keys, steiner=steiner, info=info)

    # ------------------------------------------------------------------ reference outline for the wall strips
    def reference_chains(self, step: float = 0.05) -> Dict[str, List[Tuple[float, float]]]:
        """Dense polylines of the three upper-half chains (the analytic outline, LOD-independent): the wall UV strips
        unroll every LOD's wall faces by the arc length of the nearest point on these."""
        p = self.prong
        front = [(X_TIP, 0.0)]
        n = int((X_TIP - self.t1[0]) / step)
        for i in range(1, n):
            x = X_TIP - (X_TIP - self.t1[0]) * i / n
            front.append((x, h_blade(x)))
        front.append(self.t1)
        ox, oy = self.fillet_centre
        a1 = math.atan2(self.t1[1] - oy, self.t1[0] - ox)
        a2 = math.atan2(self.t2[1] - oy, self.t2[0] - ox)
        while a2 < a1:
            a2 += 2.0 * math.pi
        if a2 - a1 > math.pi:
            a2 -= 2.0 * math.pi
        for j in range(1, 40):
            a = a1 + (a2 - a1) * j / 40
            front.append((ox + FILLET_R * math.cos(a), oy + FILLET_R * math.sin(a)))
        n = int((PRONG_L - self.u_t2) / step)
        for i in range(n + 1):
            front.append(p.edge(self.u_t2 + (PRONG_L - self.u_t2) * i / n, -1))
        outer = []
        n = int(PRONG_L / step)
        for i in range(n + 1):
            outer.append(p.edge(PRONG_L * (1.0 - i / n), +1))
        root = p.edge(0.0, +1)
        rear = [root]
        n = 400
        for i in range(1, n + 1):
            rear.append((root[0] + (REAR_X - root[0]) * i / n, root[1] + (REAR_HALF - root[1]) * i / n))
        for i in range(1, n + 1):
            rear.append((REAR_X, REAR_HALF * (1.0 - i / n)))
        return {"front": front, "outer": outer, "rear": rear}


# =========================================================================== the spec


@dataclass(frozen=True)
class KunaiSpec:
    """Build-to numbers of SM_Kunai (study section 4).  Millimetres, like every pack spec."""

    form: str
    mesh_name: str
    lods: Tuple[KunaiLodSpec, ...]
    mass_target_g: float                     # the mass gate: the UN-GROUND steel (study: 176.9 g)
    mass_tolerance_g: float = 2.0
    assembled_target_g: float = 190.0        # study: 187-192 g (DERIVED), reported
    density_g_cm3: float = STEEL_G_CM3
    title: str = ""
    study_section: str = "4"
    revision: int = 1
    physics_mass_kg: Optional[float] = 0.19
    lod_screen_sizes: Tuple[float, ...] = LOD_SCREEN_SIZES
    grip_x_mm: float = -54.0                 # design x of SOCKET_Grip (mid grip)
    trail_x_mm: float = -140.0               # design x of SOCKET_Trail (the ring's far end)
    hero_yaw_deg: float = 0.0
    texture_px: Tuple[int, int] = (4096, 2048)
    steel_px_per_mm: float = 13.5
    wrap_px_per_mm: float = 10.0
    letter_px_per_mm: float = 15.0
    study_mass_range_g: Optional[Tuple[float, float]] = None
    study_mass_typical_g: Optional[Tuple[float, float]] = None

    @property
    def points(self) -> int:
        return 3

    def validate(self) -> None:
        if not self.mesh_name.startswith("SM_"):
            raise ValueError(f"mesh_name must start with SM_: {self.mesh_name}")
        if len(self.lod_screen_sizes) < len(self.lods) or any(
                b >= a for a, b in zip(self.lod_screen_sizes, self.lod_screen_sizes[1:])):
            raise ValueError(f"lod_screen_sizes must cover every LOD and strictly descend: {self.lod_screen_sizes}")
        for lod in self.lods:
            lod.validate()


__all__ = [
    "BAND_HALF_DEG", "BAND_X0", "BAND_X1", "BLADE_BASE_HALF", "BLADE_MAX_AT", "BLADE_MAX_HALF", "CHAMFER", "COLLAR_BEVEL",
    "COLLAR_L", "COLLAR_R", "CORE_G_CM3", "CORE_R", "Col", "EDGE_T", "FILLET_R", "KunaiGeometryPlan", "KunaiLodSpec",
    "KunaiOutline", "KunaiSpec", "LAND", "NECK_CHAMFER", "NECK_END_HALF", "NECK_HALF", "NECK_X0", "NECK_X1", "NECK_X2",
    "OVERALL", "PRONG_L", "Prong", "REAR_HALF", "REAR_X", "RIDGE_BASE", "RING_A", "RING_B", "RING_CX", "RING_R",
    "RUNOUT", "STEEL_G_CM3", "STOCK", "Station", "TAN_GRIND", "TAPE_G_CM3", "WRAP_R", "WRAP_X0", "WRAP_X1", "X_TIP",
    "dh_blade", "h_blade", "ridge_blade", "solve_inset", "unground_lod", "z_blade_face", "z_prong_face",
]
