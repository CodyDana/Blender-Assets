"""Kunai spec (library 3.11): pure data and pure-Python geometry, no bpy.

References/Kunai/KUNAI_STUDY.md is the authority: section 4 (the BUILD-TO table) and section 5 (modelling notes).  The
study's table was written for the three-prong ("winged") kunai; the user then asked for the PLAIN kunai and skipped the
winged one "for now", so this module builds the plain form: the study's blade, grip, wrap, ring and lettering band with
the prongs and the crotch removed, and the fork plane turned into a normal kunai SHOULDER where the 16 mm blade base
meets the 6 mm bare neck and the grip.  The prongs stay a spec option (``KunaiSpec.prongs``, default False): the winged
head is not built by this library version (see ``KunaiPlan``), so it can come back from this generator later.

Design frame (millimetres, every number here): X along the long axis, +X toward the tip; Y across in the blade plane;
Z through the thickness (+Z is the lettering face); X = 0 is the SHOULDER.  The tip is at X = +140, the ring's far end
at X = -140.  The stored mesh is this frame shifted along X by the mass-weighted centre (``shift``, about -22 mm) and
scaled to metres, so the object origin IS the centre of mass (study 5: steel at 7.85 g/cm3, the wrap at its own
densities - never Origin to Center of Mass (Volume), which counts the 20 mm grip as steel).

The steel HEAD (one closed shell) is the blade and the front neck.  The blade is the study's leaf: straight from 16 mm
wide at the shoulder to 36 mm at X = 35 (a kite corner), then h = 18 (1 - u)(1 + 0.25 u) to the tip, in a full
DIAMOND section at forged-replica thickness (3.11, the blade-section rework, option C: a ridge down the axis at the neck's
5.0 mm stock to X = 5, rising to 7.0 mm at X = 24.42 and held to X = 35, then linear to 1.6 mm at X = 135; flat faces
falling to a 0.3 mm un-ground edge, so they run out into the knife grind's 0.15 mm land; up to 3.10.1 it was a 5.0 mm
ridge over a 1.5 mm edge - SECTION_3_10_1).  Both blade edges carry the pack's knife grind (35 deg per side to a 0.15 mm land, the facets
solved against the diamond face); past the APEX (where the grind reaches the ridge, ~5 mm from the tip) the facets meet
in a ridge on the axis and the point ends in a 0.15 mm vertical chisel edge (tip radius 0.075 mm).  The front neck is
flat 16 x 5 mm stock (the tang) with the stars' non-cutting treatment (a 0.45 mm chamfer at the grind angle over a
wall).  THE SHOULDER: at X = 0 the outline turns 16 deg (the blade's base edges flare out of the neck's straight
sides); the chamfer runs round that concave corner and 0.4 mm on, and the knife grind RUNS OUT into it over 3 mm (the
stars' root run-out, 3.9.1 taper); where the flat neck stock meets the diamond the plateau ends in a V-shaped PLUNGE
line - one planar plunge triangle per side from the stock face down to the grind line, the plunge of a ground blade.

Behind the shoulder: the WRAP (the tape itself, X -102..-6: a flat 10 mm cotton tape wound as a 9 mm-pitch helix, so
1 mm of every turn lies on the turn before and its exposed edge stands one tape thickness proud - 20 mm over those
ridges, 19 mm over a single layer - and wound DOWN onto the tang over the last TAPER_L at both ends), the REAR NECK (the bare tang between the wrap and the ring,
16 x 5 mm tapering to 12 x 4.4 mm so its faces never lie in the ring's faces, its end buried in the ring) and the RING
(ID 20, OD 32 mm, 5 mm stock, its edges rounded r 1 mm: a flat forged ring, not a wire torus).  The tang under the wrap
is never visible and is not modelled; its 16 x 5 mm section is counted analytically in the steel mass.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

from .spec import LOD_SCREEN_SIZES

TAN_GRIND = math.tan(math.radians(35.0))

# The study's hard numbers (section 4), mm.  SOURCED / DERIVED / ESTIMATE flags live in the build script's build_to.
OVERALL = 280.0
X_TIP = 140.0
BLADE_BASE_HALF = 8.0         # 16 mm at the shoulder (study: "main blade width at the fork", ESTIMATE)
BLADE_MAX_HALF = 18.0         # 36 mm max width (DERIVED)
BLADE_MAX_AT = 35.0
LEAF_BULGE = 0.25
# 3.11 blade section (option C, user-picked 2026-09-26; WorkFiles/kunai/blade_section/options/OPTIONS.md): a full
# diamond at forged-replica thickness (the research sources' forged replicas are 6.35-8 mm).  The reference photo's front
# face slope is 0.215 (ridge half-thickness minus edge half-thickness over the half width); 3.10.1's 5.0 mm ridge over a
# 1.5 mm edge gave 0.088, this section ~0.19 (10.4 deg mid-blade against the photo's 10.5 deg).
RIDGE_BASE = 7.0              # ridge thickness held from the ramp's end to the kite corner (x 24.42 .. 35)
RIDGE_TIP = 1.6
RIDGE_TIP_AT = 135.0
# A ridge above the neck's 5 mm stock has to meet the flat plateau at the plunge at STOCK height: it is STOCK up to
# RIDGE_RAMP[0] and rises linearly to RIDGE_BASE at RIDGE_RAMP[1] (LOD0's base station 2 of 3 sits at x 24.423, on the
# held part, so every LOD that keeps that station carries the full 7.0 mm there).
RIDGE_RAMP = (5.0, 24.42)
EDGE_T = 0.3                  # un-ground edge thickness: the diamond faces run to the knife grind (1.5 mm up to 3.10.1)
# The section this library shipped up to 3.10.1 (kept for the report's before / after figures).
SECTION_3_10_1 = {"RIDGE_BASE": 5.0, "RIDGE_TIP": 1.6, "RIDGE_TIP_AT": 135.0, "EDGE_T": 1.5, "RIDGE_RAMP": None}
LAND = 0.15
STOCK = 5.0
NECK_HALF_W = 8.0             # the bare front neck = the 16 x 5 mm tang (study: tang 16 x 5)
REAR_X = -6.5                 # the head's hidden rear face, 0.5 mm inside the wrap's front cap
CHAMFER = 0.45                # non-cutting edges: the stars' scallop chamfer (plan width, at the grind angle)
RUNOUT = 3.0                  # the knife grind runs out over this arc length into the chamfer (spec.GRIND_RUNOUT_MM)
CHAMFER_RUN = 0.4             # chamfer along the blade's base edge between the shoulder corner and the run-out

WRAP_X0, WRAP_X1 = -102.0, -6.0    # study: grip wrapped X -102 to -6 (96 mm), 6 mm bare neck -6..0
# The tape wrap is GEOMETRY from 3.10.1 (the plain kunai's review: a normal-map-only helix on a smooth 16-gon read as a
# moulded rubber / knurled grip - no overlap in the silhouette).  Flat cotton tape (study 4: 10 mm wide, 9 mm pitch)
# wound as a helix: 1 mm of every turn lies ON the turn before, so the exposed edge of each turn stands one tape
# thickness proud, the tape bends back down onto the core over the next ~2 mm, and the rest of the turn is flat.
WRAP_R = 10.0                      # 20 mm grip over the wrap (study): over the OVERLAP ridges (core 18 + 2 x 0.5 mm)
TAPE_W = 10.0                      # study 4: the tape's width
TAPE_PITCH = 9.0                   # ... and its pitch: the 1 mm overlap is the doubled layer
TAPE_T = 0.5                       # one layer, compressed; the study's "1 mm tape" is the doubled overlap
WRAP_R_FLAT = WRAP_R - TAPE_T      # 19 mm over a single layer
TAPE_RISE = 0.02                   # phase: the exposed edge's riser (0.18 mm along the axis)
# The bend's phase is CHOSEN so that where these two profile lines are clipped at the wrap's ends they cross the grip's
# vertex lines with room to spare: 97.5 / 360 puts the end crossings 7.5 deg (0.19 mm of x) off the nearest vertex
# line at both ends, and Unreal's importer drops a triangle thinner than about 0.05 mm.
TAPE_BEND = 97.5 / 360.0 - 0.02    # phase: the bend from the overlap ridge back onto the core (2.25 mm)
# LOD1 / LOD2 carry no tape relief (0.5 mm is 0.5 px at the 0.89 m switch): one radius, the profile's mean
WRAP_R_SMOOTH = WRAP_R_FLAT + 0.5 * TAPE_T * (TAPE_RISE + TAPE_BEND)
TAPER_L = 6.0                      # both ends: the tape wound DOWN onto the tang over this length (a lashing)
LASH_T = 1.0                       # the lashing's thickness over the tang there (the wound-down layers)
LASH_CORNER = 1.2                  # the corner radius of its section
BAND_X0, BAND_X1 = -90.0, -18.0    # the 72 mm lettering band, 12 mm clear of each wrap end (study)
BAND_ARC = 12.0                    # mm of arc on the 20 mm grip
BAND_HALF_DEG = math.degrees(0.5 * BAND_ARC / WRAP_R)   # 34.377 deg either side of +Z
NECK_X0, NECK_X2 = -100.0, -110.5  # rear neck: hidden start inside the wrap, buried end inside the ring
NECK_HALF = (8.0, 2.5)             # half width, half thickness where it leaves the wrap (the tang's section)
NECK_END_HALF = (6.0, 2.2)         # ... at the buried end: under the ring's 2.5 mm half stock, inside its flat
NECK_CHAMFER = 0.6
RING_CX = -124.0                   # study: ring centre X = -124, ID 20 (SOURCED), OD 32 (DERIVED)
RING_R = 13.0                      # section centre radius
RING_A, RING_B = 3.0, 2.5          # half the radial width (6 mm) and half the stock (5 mm)
RING_ROUND = 1.0                   # edges rounded r 1 mm (study: "edges rounded r 1 mm")

STEEL_G_CM3 = 7.85
CORE_G_CM3 = 0.70                  # wooden core, the middle of the study's 0.6-0.8
TAPE_G_CM3 = 0.75                  # wound cotton tape, the middle of 0.6-0.9
CORE_R = 9.0                       # 18 mm core under a 1 mm tape wrap (study)

# the winged head's numbers (study 4), kept for the day the prongs come back (KunaiSpec.prongs; not built in 3.10)
WINGED = {"prong_angle_deg": 38.0, "prong_length_mm": 60.0, "prong_root_offset_mm": 13.0, "prong_root_width_mm": 14.0,
          "crotch_fillet_mm": 2.0, "paused_work": "WorkFiles/kunai/winged_wip_scripts_2026-09-19 (untested)"}


# =========================================================================== basic curves


def h_blade(x: float) -> float:
    """Blade half width at design x (0 <= x <= 140)."""
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
    """Full ridge thickness (mm) at design x: STOCK to RIDGE_RAMP[0], rising to RIDGE_BASE at RIDGE_RAMP[1], held to the
    kite corner, then linear to RIDGE_TIP at RIDGE_TIP_AT (and RIDGE_TIP beyond)."""
    if x <= BLADE_MAX_AT:
        if RIDGE_RAMP is not None:
            x0, x1 = RIDGE_RAMP
            if x <= x0:
                return STOCK
            if x < x1:
                return STOCK + (RIDGE_BASE - STOCK) * (x - x0) / (x1 - x0)
        return RIDGE_BASE
    t = RIDGE_BASE + (RIDGE_TIP - RIDGE_BASE) * (x - BLADE_MAX_AT) / (RIDGE_TIP_AT - BLADE_MAX_AT)
    return max(RIDGE_TIP, t)


def ridge_knots_x() -> List[float]:
    """Every x where the ridge profile bends (the head hull samples the ridge line there)."""
    xs = [BLADE_MAX_AT, RIDGE_TIP_AT]
    if RIDGE_RAMP is not None:
        xs += list(RIDGE_RAMP)
    return sorted(set(xs))


def z_blade_face(x: float, y: float) -> float:
    """Top of the un-ground blade diamond at (x, y): linear from the EDGE_T edge to the ridge."""
    h = h_blade(min(max(x, 0.0), X_TIP))
    if h <= 1e-12:
        return 0.5 * EDGE_T
    t = ridge_blade(x)
    return 0.5 * (EDGE_T + (t - EDGE_T) * max(0.0, 1.0 - abs(y) / h))


def solve_inset(face, ex: float, ey: float, bx: float, by: float, c: float, land_half: float,
                s_axis: float) -> Tuple[float, bool]:
    """Perpendicular inset s of the knife grind line at an edge point: the 35 deg facet (land_half + s tan) meets the
    face ``face(x, y)``.  Returns (s, past_apex); past the apex the facet reaches the axis (s_axis) first."""
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


def grip_angles(sides: int) -> List[float]:
    """Vertex angles (radians, from +Z toward +Y) of a grip ring: an even number of EQUAL faces starting at -Z, so -Z
    (the seam of the wrap's UV island) and +Z (the lettering face) are both vertex lines on every LOD.

    Up to 3.10 the band's edges (+-BAND_HALF_DEG) were vertex lines too, because the lettering band was its own UV
    island; 3.10.1 unrolls the band inside the wrap's own island (one continuous straight unroll, no island seam across
    the grip - the review found the seam read as an outlined panel), so the grip's faces are equal again."""
    if sides < 8 or sides % 2:
        raise ValueError(f"grip: {sides} sides (an even number, at least 8)")
    return [-math.pi + 2.0 * math.pi * k / sides for k in range(sides)]


def tape_phase(x: float, phi: float) -> float:
    """Helix phase of the tape at design x and grip angle phi (turns; the integer part counts turns from the ring end).

    One turn of the tape advances TAPE_PITCH along the axis; a line of constant phase is one edge of the tape.  The
    geometry and M_Kunai_Wrap share this function, so the baked fray / crest detail sits on the modelled tape edge."""
    return (x - WRAP_X0) / TAPE_PITCH + phi / (2.0 * math.pi)


def tape_radius(q: float) -> float:
    """Radius (mm) of the tape surface at helix phase ``q``: the exposed edge's riser, the bend back onto the core,
    then the flat run of the turn (see the WRAP_ constants)."""
    f = q - math.floor(q)
    if f <= TAPE_RISE:
        return WRAP_R_FLAT + TAPE_T * f / TAPE_RISE
    if f <= TAPE_RISE + TAPE_BEND:
        return WRAP_R - TAPE_T * (f - TAPE_RISE) / TAPE_BEND
    return WRAP_R_FLAT


def _smoothstep(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def lash_section(front: bool) -> Tuple[float, float, float]:
    """(half width, half thickness, corner radius) of the wrap's end section: the tape wound down onto the tang.

    Front (blade side, x = WRAP_X1) the tang is the 16 x 5 mm neck; rear (x = WRAP_X0) it is the rear neck's section
    there.  LASH_T of wound tape all round, with LASH_CORNER corners."""
    if front:
        hw, ht = NECK_HALF_W, 0.5 * STOCK
    else:
        t = (WRAP_X0 - NECK_X0) / (NECK_X2 - NECK_X0)
        hw = NECK_HALF[0] + (NECK_END_HALF[0] - NECK_HALF[0]) * t
        ht = NECK_HALF[1] + (NECK_END_HALF[1] - NECK_HALF[1]) * t
    return hw + LASH_T, ht + LASH_T, LASH_CORNER


def lash_radius(phi: float, section: Tuple[float, float, float]) -> float:
    """Polar radius (mm) at grip angle phi of a rounded-rectangle section (half width, half thickness, corner r)."""
    half_w, half_t, rc = section
    a, b = half_w - rc, half_t - rc
    sy, cz = math.sin(phi), math.cos(phi)

    def outside(t: float) -> float:
        return math.hypot(max(abs(t * sy) - a, 0.0), max(abs(t * cz) - b, 0.0)) - rc
    lo, hi = 0.0, math.hypot(half_w, half_t) + rc
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if outside(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def wrap_radius(x: float, phi: float, relief: bool = True, taper: bool = True, envelope: bool = False) -> float:
    """The wrap surface's radius at design x and grip angle phi: the tape helix, eased into the wound-down lashing
    sections over TAPER_L at both ends (which is how a tape wrap really finishes, and what keeps the front end from
    towering over the 6 mm bare neck - the review's dark-slot finding).

    ``envelope`` takes the tape at its ridge radius everywhere instead of its local phase: the surface the collider
    has to contain, whatever the helix does between two hull stations."""
    r = WRAP_R if envelope else (tape_radius(tape_phase(x, phi)) if relief else WRAP_R_SMOOTH)
    if not taper:
        return r
    if x >= WRAP_X1 - TAPER_L:
        s = _smoothstep((x - (WRAP_X1 - TAPER_L)) / TAPER_L)
        return (1.0 - s) * r + s * lash_radius(phi, lash_section(True))
    if x <= WRAP_X0 + TAPER_L:
        s = _smoothstep(((WRAP_X0 + TAPER_L) - x) / TAPER_L)
        return (1.0 - s) * r + s * lash_radius(phi, lash_section(False))
    return r


# =========================================================================== LOD spec


@dataclass(frozen=True)
class KunaiLodSpec:
    """One kunai LOD.  Counts are intervals; ``land`` 0 = the edge line (LOD2), -1 = the un-ground reference (no grind,
    1.5 mm edges); ``chamfer`` 0 = square non-cutting edges."""

    blade_base_intervals: int = 3        # plunge station -> the kite corner (x = 35)
    # 3.11: the base stations as fractions of plunge station -> kite corner (first 0, increasing, < 1), in place of
    # blade_base_intervals equal steps; () = the equal steps.  LOD2 keeps LOD0's plunge station and its station 2 of 3
    # (x 24.42, the end of the ridge ramp), so its ridge follows the 5 -> 7 mm ramp instead of cutting across it.
    blade_base_fractions: Tuple[float, ...] = ()
    blade_leaf_intervals: int = 14       # kite corner -> the apex
    blade_tip_intervals: int = 2         # apex -> tip
    neck_intervals: int = 1              # shoulder corner -> the rear corner (the bare neck, into the wrap)
    rear_intervals: int = 2              # the hidden rear face
    land: float = LAND
    chamfer: float = CHAMFER
    plateau_steiner: int = 1             # interior points of the plateau triangulation
    grip_sides: int = 16
    tape_relief: bool = True             # the tape's overlap ridges as geometry (LOD0); False = one smooth radius
    taper_rings: int = 2                 # extra rings inside each wound-down end (the lashing's curve)
    ring_segments: int = 24
    ring_section: str = "round"          # "round" (8 points: flats, walls and r 1 rounds with arc normals) | "square"
    neck_chamfer: float = NECK_CHAMFER
    band: Tuple[int, int] = (1000, 2000)
    note: str = ""

    def base_fractions(self) -> Tuple[float, ...]:
        if self.blade_base_fractions:
            return tuple(float(f) for f in self.blade_base_fractions)
        return tuple(i / self.blade_base_intervals for i in range(self.blade_base_intervals))

    def validate(self) -> None:
        grip_angles(self.grip_sides)
        fr = self.base_fractions()
        if not fr or fr[0] != 0.0 or any(b <= a for a, b in zip(fr, fr[1:])) or fr[-1] >= 1.0:
            raise ValueError(f"blade base stations: {fr} (first 0, strictly increasing, below 1)")
        if self.ring_segments % 4:
            raise ValueError("ring_segments must be a multiple of 4 (vertices on the long axis and across it)")
        if self.taper_rings < 0:
            raise ValueError(f"taper_rings: {self.taper_rings}")
        if self.ring_section not in ("round", "square"):
            raise ValueError(f"ring_section: {self.ring_section}")


def unground_lod(lod: KunaiLodSpec) -> KunaiLodSpec:
    """The same LOD authored without any grind, chamfer or round: the mass gate's reference (EDGE_T blade edges, square
    neck edges, a square-section ring - the study's un-ground steel)."""
    return replace(lod, land=-1.0, chamfer=0.0, neck_chamfer=0.0, ring_section="square")


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
    chain: str = "front"         # front | rear (the UV wall strips)
    tag: str = ""
    axis: bool = False           # inner point on the axis (shared with the other half)


@dataclass
class Station:
    """One diamond section: the knife column and the ridge point R (None past the apex)."""
    at: float
    col: int
    ridge: Optional[Tuple[float, float, float]]
    past_apex: bool


@dataclass
class KunaiOutline:
    """Everything the generator authors for one LOD's head, upper half (y >= 0), design mm."""
    lod: KunaiLodSpec
    cols: List[Col]
    blade: List[Station]
    plunge: Tuple[int, int, Tuple[float, float, float]]    # (ctop col, first knife col, ridge point)
    runout: Tuple[int, int]                                 # (ctop col, first knife col)
    plateau: List[Tuple[float, float]]                      # boundary polygon (CCW), mm
    steiner: List[Tuple[float, float]]
    info: Dict[str, object] = field(default_factory=dict)


class KunaiPlan:
    """The analytic head: shoulder, run-out, plunge, apex - computed once, sampled per LOD.

    ``prongs`` (the winged head) is refused: the fork, the crotch fillets and the prong edges are not part of this
    library version.  The paused winged work (WINGED["paused_work"]) solved them against the same diamond and knife
    columns; adding them here is a new outline chain (prong edge stations and two crotch fillets between the blade's
    base edge and the prong's inner edge), not a new generator."""

    def __init__(self, prongs: bool = False) -> None:
        if prongs:
            raise NotImplementedError("the winged (three-prong) kunai is not built in library 3.10: the user skipped it "
                                      "'for now'; its paused work is in " + WINGED["paused_work"])
        self.e1 = _unit(BLADE_MAX_AT, BLADE_MAX_HALF - BLADE_BASE_HALF)      # the base edge, shoulder -> kite corner
        self.b1 = (self.e1[1], -self.e1[0])                                   # its inward normal (toward -y)
        self.shoulder = (0.0, BLADE_BASE_HALF)
        self.ctop = (self.shoulder[0] + CHAMFER_RUN * self.e1[0], self.shoulder[1] + CHAMFER_RUN * self.e1[1])
        self.x_plunge = self.shoulder[0] + (CHAMFER_RUN + RUNOUT) * self.e1[0]
        self.x_apex = self._blade_apex()

    # ------------------------------------------------------------------ helpers
    def blade_col(self, x: float, land_half: float) -> Tuple[Col, bool, float]:
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
                      zone="knife")
            return col, False, 0.0
        s_axis = ey * c / (-b[1])                         # perpendicular inset at which the inner point reaches y = 0
        s, past = solve_inset(z_blade_face, x, ey, b[0], b[1], c, land_half, s_axis)
        k = s / c
        ix, iy = x + k * b[0], ey + k * b[1]
        if past:
            iy = 0.0
        iz = land_half + s * TAN_GRIND
        col = Col(ex=x, ey=ey, bx=b[0], by=b[1], s=s, c=c, ix=ix, iy=iy, iz=iz, zw=land_half, zone="knife", axis=past)
        return col, past, s

    def _blade_apex(self) -> float:
        def g(x):
            _col, past, _s = self.blade_col(x, 0.5 * LAND)
            return 1.0 if past else -1.0
        return _bisect(g, BLADE_MAX_AT + 1.0, X_TIP - 0.01, 70)

    def grind_width(self, x: float, land: float = LAND) -> float:
        """Plan width (mm) of the knife grind at design x (perpendicular to the edge)."""
        return self.blade_col(x, 0.5 * land)[2]

    # ------------------------------------------------------------------ one LOD
    def outline(self, lod: KunaiLodSpec) -> KunaiOutline:
        land_half = 0.5 * lod.land if lod.land >= 0.0 else -1.0
        unground = lod.land < 0.0
        ch = lod.chamfer
        z_plate = 0.5 * STOCK
        cols: List[Col] = []
        blade: List[Station] = []

        def chamfer_col(x, y, b, c, chain, tag):
            k = ch / c
            return Col(ex=x, ey=y, bx=b[0], by=b[1], s=ch, c=c, ix=x + k * b[0], iy=y + k * b[1], iz=z_plate,
                       zw=z_plate - ch * TAN_GRIND, zone="chamfer", chain=chain, tag=tag)

        # ---- blade stations (increasing x)
        xa = self.x_apex
        xp = self.x_plunge
        xs = [xp + (BLADE_MAX_AT - xp) * f for f in lod.base_fractions()]
        xs += [BLADE_MAX_AT + (xa - BLADE_MAX_AT) * i / lod.blade_leaf_intervals for i in range(lod.blade_leaf_intervals)]
        xs += [xa + (X_TIP - xa) * i / lod.blade_tip_intervals for i in range(lod.blade_tip_intervals)]
        stations = []
        for x in xs:
            col, past, _s = self.blade_col(x, land_half)
            if x == xa and not unground:
                past = True
                col.iy, col.axis = 0.0, True
            col.tag = "station"
            stations.append((x, col, past))
        tip_z = 0.5 * EDGE_T if unground else max(land_half, 0.0)
        tip = Col(ex=X_TIP, ey=0.0, ix=X_TIP, iy=0.0, iz=tip_z, zw=tip_z, zone="tip", tag="tip", axis=True)
        # front chain: tip, blade stations descending
        cols.append(tip)
        for x, col, past in reversed(stations):
            cols.append(col)
            blade.append(Station(at=x, col=len(cols) - 1,
                                 ridge=None if past else (col.ix, 0.0, 0.5 * ridge_blade(col.ix)), past_apex=past))
        blade.reverse()
        i_first = len(cols) - 1                           # the first full-knife station (the plunge station)
        # the run-out end: a chamfer column on the base edge, CHAMFER_RUN past the shoulder corner
        cols.append(chamfer_col(self.ctop[0], self.ctop[1], self.b1, 1.0, "front", "ctop"))
        i_ctop = len(cols) - 1
        # the shoulder: a concave corner (the blade's base edge flares 16 deg out of the neck's straight side), mitred
        n_neck = (0.0, -1.0)
        b = _unit(self.b1[0] + n_neck[0], self.b1[1] + n_neck[1])
        c = b[0] * n_neck[0] + b[1] * n_neck[1]
        cols.append(chamfer_col(self.shoulder[0], self.shoulder[1], b, c, "front", "shoulder"))
        # the bare neck's side (into the wrap)
        for j in range(1, lod.neck_intervals):
            x = self.shoulder[0] + (REAR_X - self.shoulder[0]) * j / lod.neck_intervals
            cols.append(chamfer_col(x, NECK_HALF_W, n_neck, 1.0, "front", "neck"))
        # rear corner (neck side -> the hidden rear face), convex, mitred; it starts the rear chain
        n_rf = (1.0, 0.0)
        b = _unit(n_neck[0] + n_rf[0], n_neck[1] + n_rf[1])
        c = b[0] * n_rf[0] + b[1] * n_rf[1]
        cols.append(chamfer_col(REAR_X, NECK_HALF_W, b, c, "rear", "rear_corner"))
        i_rear_corner = len(cols) - 1
        for j in range(1, lod.rear_intervals):
            y = NECK_HALF_W * (1.0 - j / lod.rear_intervals)
            cols.append(chamfer_col(REAR_X, y, n_rf, 1.0, "rear", "rear"))
        cols.append(chamfer_col(REAR_X, 0.0, n_rf, 1.0, "rear", "rear_axis"))
        cols[-1].axis = True

        # ---- the plunge: the ridge at stock height over the first station, the chamfer's run-out end, the grind line
        first = cols[i_first]
        ridge_p = (first.ix, 0.0, 0.5 * ridge_blade(first.ix))
        plunge = (i_ctop, i_first, ridge_p)

        # ---- plateau boundary (CCW): the axis from the rear face to the plunge ridge, the plunge line to the chamfer's
        # run-out end, then the chamfer line back round the shoulder, along the neck, round the rear corner and down
        # the rear face
        poly = [(cols[-1].ix, 0.0), (ridge_p[0], 0.0)]
        for i in range(i_ctop, len(cols) - 1):
            poly.append((cols[i].ix, cols[i].iy))
        steiner = []
        if lod.plateau_steiner:
            steiner.append((0.5 * (REAR_X + ch + first.ix) - 1.0, 0.45 * NECK_HALF_W))
            if lod.plateau_steiner > 1:
                steiner.append((REAR_X + 2.0, 0.75 * NECK_HALF_W))
        info = {"x_plunge_mm": xp, "x_apex_mm": xa, "ctop_mm": list(self.ctop), "shoulder_mm": list(self.shoulder),
                "plunge_ridge_mm": list(ridge_p), "first_knife_inner_mm": [first.ix, first.iy, first.iz],
                "i_rear_corner": i_rear_corner}
        return KunaiOutline(lod=lod, cols=cols, blade=blade, plunge=plunge, runout=(i_ctop, i_first), plateau=poly,
                            steiner=steiner, info=info)

    # ------------------------------------------------------------------ reference outline (LOD independent)
    def reference_chains(self, step: float = 0.05) -> Dict[str, List[Tuple[float, float]]]:
        """Dense polylines of the two upper-half chains of the analytic outline: ``front`` from the tip along the leaf
        and the base edge to the shoulder, the neck side to the rear corner; ``rear`` down the hidden rear face.  The
        wall UV strips unroll every LOD's wall faces by the arc length of the nearest point on these."""
        front = [(X_TIP, 0.0)]
        n = int((X_TIP - self.shoulder[0]) / step)
        for i in range(1, n):
            x = X_TIP - (X_TIP - self.shoulder[0]) * i / n
            front.append((x, h_blade(x)))
        front.append(self.shoulder)
        n = max(2, int((self.shoulder[0] - REAR_X) / step))
        for i in range(1, n + 1):
            front.append((self.shoulder[0] + (REAR_X - self.shoulder[0]) * i / n, NECK_HALF_W))
        rear = [(REAR_X, NECK_HALF_W)]
        n = 400
        for i in range(1, n + 1):
            rear.append((REAR_X, NECK_HALF_W * (1.0 - i / n)))
        return {"front": front, "rear": rear}


# =========================================================================== the spec


@dataclass(frozen=True)
class KunaiSpec:
    """Build-to numbers of a kunai form (study section 4, plain: prongs off).  Millimetres, like every pack spec."""

    form: str
    mesh_name: str
    lods: Tuple[KunaiLodSpec, ...]
    mass_target_g: float                     # the mass gate: the UN-GROUND steel (study basis, plain: 153.0 g)
    mass_tolerance_g: float = 2.0
    assembled_target_g: float = 167.4        # study basis, plain: 164.8-170.0 g assembled (DERIVED), reported
    density_g_cm3: float = STEEL_G_CM3
    title: str = ""
    study_section: str = "4"
    revision: int = 1
    physics_mass_kg: Optional[float] = None
    lod_screen_sizes: Tuple[float, ...] = LOD_SCREEN_SIZES
    prongs: bool = False                     # the winged (three-prong) head: an option for later, OFF (not built)
    grip_x_mm: float = -54.0                 # design x of SOCKET_Grip (mid grip)
    trail_x_mm: float = -140.0               # design x of SOCKET_Trail (the ring's far end)
    tip_x_mm: float = 140.0                  # design x of SOCKET_Tip
    ring_x_mm: float = RING_CX               # design x of SOCKET_Ring (the ring centre)
    hero_yaw_deg: float = 0.0
    # 3.11: the hero's glossy-only blade key (render.hero_blade_key): (elevation deg, azimuth deg, width m, height m)
    # at 0.62 m before the hero rig scale; None = none
    hero_blade_key: Optional[Tuple[float, float, float, float]] = None
    steel_px: int = 2048                     # T_Kunai_<Form>_BC / _ORM / _N (UV tile u 0..1)
    wrap_px: int = 1024                      # T_Kunai_Wrap_BC / _ORM / _N (UV tile u 1..2)
    lettering_px: Tuple[int, int] = (1536, 256)   # T_Kunai_Lettering: a single-channel mask, shipped blank
    steel_px_per_mm: float = 13.5
    wrap_px_per_mm: float = 10.0
    study_mass_range_g: Optional[Tuple[float, float]] = None
    study_mass_typical_g: Optional[Tuple[float, float]] = None

    @property
    def points(self) -> int:
        return 1

    def validate(self) -> None:
        if not self.mesh_name.startswith("SM_"):
            raise ValueError(f"mesh_name must start with SM_: {self.mesh_name}")
        if self.prongs:
            KunaiPlan(prongs=True)               # raises: the winged head is not part of this library version
        if len(self.lod_screen_sizes) < len(self.lods) or any(
                b >= a for a, b in zip(self.lod_screen_sizes, self.lod_screen_sizes[1:])):
            raise ValueError(f"lod_screen_sizes must cover every LOD and strictly descend: {self.lod_screen_sizes}")
        for lod in self.lods:
            lod.validate()


__all__ = [
    "BAND_ARC", "BAND_HALF_DEG", "BAND_X0", "BAND_X1", "BLADE_BASE_HALF", "BLADE_MAX_AT", "BLADE_MAX_HALF", "CHAMFER",
    "CORE_G_CM3", "CORE_R", "Col", "EDGE_T", "KunaiLodSpec", "KunaiOutline",
    "KunaiPlan", "KunaiSpec", "LAND", "LASH_CORNER", "LASH_T", "NECK_CHAMFER", "NECK_END_HALF", "NECK_HALF",
    "NECK_HALF_W", "NECK_X0",
    "NECK_X2", "OVERALL", "REAR_X", "RIDGE_BASE", "RIDGE_RAMP", "RIDGE_TIP", "RIDGE_TIP_AT", "RING_A", "RING_B", "RING_CX", "RING_R", "RING_ROUND", "RUNOUT",
    "SECTION_3_10_1", "STEEL_G_CM3", "STOCK", "Station", "TAN_GRIND", "TAPE_BEND", "TAPE_G_CM3", "TAPE_PITCH", "TAPE_RISE", "TAPE_T",
    "TAPE_W", "TAPER_L", "WINGED", "WRAP_R", "WRAP_R_FLAT", "WRAP_R_SMOOTH", "WRAP_X0", "WRAP_X1", "X_TIP",
    "dh_blade", "grip_angles", "h_blade", "lash_radius", "lash_section", "ridge_blade", "ridge_knots_x", "solve_inset", "tape_phase",
    "tape_radius", "unground_lod", "wrap_radius", "z_blade_face",
]
