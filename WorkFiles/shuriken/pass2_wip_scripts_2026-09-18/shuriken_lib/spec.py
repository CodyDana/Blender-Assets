"""Form specs for the radial-star shuriken: pure data, no bpy.

A form is one ``RadialStarSpec`` (build-to numbers in millimetres, straight from
References/Shuriken/SHURIKEN_STUDY.md section 2) plus a chain of ``LodSpec`` segment
counts.  ``Outline`` turns the millimetres into the metre values the generator uses,
with exactly the arithmetic the rev-2 four-point script used, so the four-point
rebuilds bit-for-bit.

LOD strategy (study 4's table, replacing rev 2's Decimate):

    LOD0  1.0   1,200-2,500   full outline, bevels, hole ring
    LOD1  0.5     500-900     halve the hole ring and the bevel segments
    LOD2  0.25    120-250     drop the bevel and the hole entirely

Every LOD is authored by the same parametric generator at its own segment counts,
so each is a clean, exactly C_n mesh that genuinely differs from LOD0.
``study_lod_chain`` derives LOD1/LOD2 from a LOD0 by those rules; a form may also
spell its LODs out by hand.

Edge treatment (knife grind, style pass 2, 2026-09-18; supersedes the first style pass's
0.4 x thickness chamfer capped at half its width in depth):

* Every CUTTING edge - the arm's parallel edges and its taper edges - is knife ground on
  both faces: ``ChamferProfile.knife``, one flat facet at ``grind_angle_deg`` from the face
  that runs down until only ``edge_land_mm`` of vertical wall is left between the two
  facets (the reference's bevels converge to a ~0.1 mm land; the pack allows <= 0.25 mm).
  Its plan width follows from the thickness, the angle and the land.  Past the apex the
  facets meet in a ridge and the point ends in a vertical edge the height of the land.
* The concave hub arcs (the scallops between the arms) are not cutting edges: they keep a
  small chamfer (``scallop_chamfer_mm`` wide, at the same angle) over a tall vertical wall,
  as the reference's scallops do, and the centre hole a small 45 deg deburr chamfer
  (``hole_chamfer_mm``).
* At the arm root the knife grind RUNS OUT into the scallop chamfer over
  ``grind_runout_mm`` at constant angle (only its width changes, so every run-out facet quad
  stays planar), the way a wheel cannot grind into a concave corner.
* The mass gate is evaluated on the un-ground plate (outline x thickness), which the grind
  does not change; the ground mass is reported as a finish property (see measure.py).

``bevel_segments`` is the number of profile segments (1 = one flat facet).  The LOD flags
(``scallop``, ``hole_bevel``, ``runout_station``, ``knife_land``, ``pyramid_tip``) let LOD2
keep a single-facet grind inside its triangle band: its facets meet in a sharp edge line
(land 0), the scallops are square, the grind runs out over the whole parallel run and the
shoulder ring caps straight onto the point.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional, Tuple

MM = 0.001                  # 1 Blender unit = 1 m (study 4)
SNAP = 1e-9                 # every vertex is snapped to 1 nm; duplicates become impossible
# Style pass 1 defaults, kept for chamfer_profile() callers only (the pack now uses the knife grind).
CHAMFER_WIDTH_FRACTION = 0.4
CHAMFER_DEPTH_FRACTION = 0.5
CHAMFER_ROUND_FRACTION = 0.25
# Knife grind (style pass 2).  Measured on the study-only reference LP/HP (read, never shipped):
# facets 38 deg from the face, ~0.12 mm land at 197 mm (0.06 mm at the pack's 100 mm scale).
GRIND_ANGLE_DEG = 35.0          # per-side grind angle from the face (decision A: about 25-35 deg)
EDGE_LAND_MM = 0.15             # vertical land left between the two facets on every cutting edge (<= 0.25)
MAX_EDGE_LAND_MM = 0.25
SCALLOP_CHAMFER_MM = 0.45       # plan width of the small chamfer on the concave hub arcs (at the grind angle)
HOLE_CHAMFER_MM = 0.30          # plan width of the centre hole's deburr chamfer
HOLE_CHAMFER_DEG = 45.0
GRIND_RUNOUT_MM = 3.0           # the knife grind runs out into the scallop chamfer over this length at the root


def rotate(k: int, n: int, x: float, y: float):
    """Rotate (x, y) by k n-th turns.

    Multiples of a quarter turn are done without trig (sign flips and swaps), so a C4
    form's four arms land on bit-identical floats - the property rev 2 relied on for an
    exactly C4 LOD0.  Any other turn uses cos/sin of the exact fraction 2*pi*k/n.
    """
    k %= n
    if (4 * k) % n == 0:
        q = (4 * k // n) % 4
        if q == 0:
            return x, y
        if q == 1:
            return -y, x
        if q == 2:
            return -x, -y
        return y, -x
    angle = 2.0 * math.pi * k / n
    c, s = math.cos(angle), math.sin(angle)
    return c * x - s * y, s * x + c * y


LOD0_BAND = (1200, 2500)
LOD1_BAND = (500, 900)
LOD2_BAND = (120, 250)
# Study 4's table lists screen sizes 1.0 / 0.5 / 0.25.  On a ~10 cm prop those thresholds
# switch far too early: Unreal's screen size is S = 2 max(P00, P11) / 2 * R / d, i.e.
# S = 1.778 R / d for a 16:9 view at 90 deg horizontal FOV, so with R = 50 mm LOD1 took
# over at 0.18 m and LOD2 (no hole, no bevel) at 0.36 m - a star held in first person or
# lying on a table rendered its lowest LOD.  Study 4's own rationale ("a 10 cm prop is
# sub-pixel within a few metres, so LOD2 can be aggressive") is met by thresholds set
# from distance instead: LOD1 at S = 0.10 (0.89 m for R = 50 mm, the star ~108 px tall at
# 1080p, LOD1's 0.3-0.4 mm deviation < 0.5 px) and LOD2 at S = 0.035 (2.5 m, ~38 px; the
# filled 9.5 mm hole is ~3.6 px, the arms deviate < 0.3 px).  One pack-wide set, applied
# through the .sockets.json sidecar (pipeline.export_fbx's lod_screen_sizes override).
STUDY_LOD_SCREEN_SIZES = (1.0, 0.5, 0.25)
LOD_SCREEN_SIZES = (1.0, 0.10, 0.035)
REFERENCE_HFOV_DEG = 90.0
REFERENCE_ASPECT = 16.0 / 9.0
HULL_METHODS = ("pipeline", "tip_prism")
RING_KINDS = ("seam", "hole", "arm", "rim")


# The pack thresholds above were set for a star of tip radius ~50 mm (LOD1 at ~0.89 m, LOD2 at
# ~2.54 m).  S = 1.778 R / d, so a form with a different bounding radius keeps the same switch
# DISTANCES by scaling S with R (study 4, amended 2026-09-17).
LOD_REFERENCE_RADIUS_MM = 50.0


def scaled_lod_screen_sizes(radius_mm: float, sizes=LOD_SCREEN_SIZES,
                            reference_mm: float = LOD_REFERENCE_RADIUS_MM, digits: int = 4) -> Tuple[float, ...]:
    """Pack screen sizes rescaled for a form of bounding radius ``radius_mm``.

    LOD0 stays 1.0; every other threshold is multiplied by radius / 50 mm and rounded to
    ``digits`` decimals (1e-4 of screen size is ~0.1 % of the switch distance), so the switch
    distances stay the pack's ~0.89 m and ~2.54 m whatever the form's size.
    """
    factor = radius_mm / reference_mm
    return tuple([float(sizes[0])] + [round(float(s) * factor, digits) for s in sizes[1:]])


def screen_size_distance_m(screen_size: float, radius_m: float, hfov_deg: float = REFERENCE_HFOV_DEG,
                           aspect: float = REFERENCE_ASPECT) -> float:
    """Camera distance at which Unreal's ComputeBoundsScreenSize returns ``screen_size``.

    ScreenSize = 2 max(0.5 P[0][0], 0.5 P[1][1]) R / d with P[0][0] = 1 / tan(hfov / 2) and
    P[1][1] = aspect / tan(hfov / 2) (horizontal FOV kept), so d = max(1, aspect) R /
    (tan(hfov / 2) S).
    """
    multiple = max(1.0, aspect) / math.tan(math.radians(0.5 * hfov_deg))
    return multiple * radius_m / screen_size


@dataclass(frozen=True)
class ChamferProfile:
    """The ground chamfer's cross-section: a flat facet with a tiny round-over at the wall.

    In the section plane perpendicular to the edge, ``s`` is the plan inset from the rim wall
    (0 on the wall, ``width`` where the flat plate begins) and ``drop`` is the depth below the
    plate face.  The facet is the straight line from the corner C = (0, depth) to the plate
    edge E = (width, 0); the round-over of radius ``round`` is tangent to the wall and to the
    facet at C, so the wall top sits ``tangent`` below C and the facet is straight from its
    own tangent point up to E.  ``levels(K)`` samples it in K segments from the wall top to
    the plate edge: K = 1 is one chord from the wall top to E, K = 2 is the round-over as one
    chord (wall tangent point to facet tangent point) plus the flat facet, K >= 3 subdivides
    the flat facet further.  All in metres.
    """

    width: float
    depth: float
    round: float

    @classmethod
    def knife(cls, thickness: float, angle_deg: float, land: float, round_: float = 0.0) -> "ChamferProfile":
        """The knife grind: a facet at ``angle_deg`` from the face down to a vertical ``land`` (metres).

        depth = t/2 - land/2 - (the round-over's tangent length), width = depth / tan(angle), so
        the two faces' facets leave exactly ``land`` of vertical wall at the edge.  ``land`` 0
        makes the facets meet in a sharp edge line (LOD2).
        """
        alpha = math.radians(angle_deg)
        tangent = round_ / math.tan(0.5 * (0.5 * math.pi + alpha)) if round_ > 0.0 else 0.0
        depth = 0.5 * thickness - 0.5 * land - tangent
        return cls(width=depth / math.tan(alpha), depth=depth, round=round_)

    @classmethod
    def at_angle(cls, width: float, angle_deg: float) -> "ChamferProfile":
        """A plain flat chamfer of plan ``width`` at ``angle_deg`` from the face (no round-over)."""
        return cls(width=width, depth=width * math.tan(math.radians(angle_deg)), round=0.0)

    def land(self, thickness: float) -> float:
        """Vertical wall left between the two faces' facets on a plate of ``thickness`` (metres)."""
        return thickness - 2.0 * self.wall_top_drop

    @property
    def angle_deg(self) -> float:
        return math.degrees(self.facet_angle)

    @property
    def facet_angle(self) -> float:
        """Facet inclination from the plate face, radians."""
        return math.atan2(self.depth, self.width)

    @property
    def tangent(self) -> float:
        """Distance from the corner C to each tangent point of the round-over."""
        # interior angle at C between the wall (down) and the facet: 90 deg + facet angle
        return self.round / math.tan(0.5 * (0.5 * math.pi + self.facet_angle))

    @property
    def wall_top_drop(self) -> float:
        """Depth of the wall top below the plate face (the facet corner plus the round-over)."""
        return self.depth + self.tangent

    def _facet_dir(self):
        length = math.hypot(self.width, self.depth)
        return self.width / length, -self.depth / length     # unit vector C -> E in (s, drop)

    def drop_at(self, s: float) -> float:
        """Depth below the plate face at plan inset ``s`` (0 = the wall top, width = the plate)."""
        if s <= 0.0:
            return self.wall_top_drop
        if s >= self.width:
            return 0.0
        ux, uz = self._facet_dir()
        t = self.tangent
        s_ft = t * ux                                 # plan inset of the facet tangent point
        if s >= s_ft or t <= 0.0:
            return self.depth + uz * (s / ux)
        # on the round-over: the circle centre is ``round`` inside the wall and ``round`` inside the facet
        cx, cz = self.round, self.depth + t
        return cz - math.sqrt(max(0.0, self.round * self.round - (s - cx) ** 2))

    def levels(self, segments: int):
        """``segments + 1`` (s, drop) samples from the wall top (s = 0) to the plate edge."""
        if segments <= 0:
            return [(0.0, 0.0)]
        w, d, t = self.width, self.depth, self.tangent
        if segments == 1 or t <= 0.0:
            return ([(0.0, self.wall_top_drop)]
                    + [(w * k / segments, self.drop_at(w * k / segments)) for k in range(1, segments)]
                    + [(w, 0.0)])
        ux, uz = self._facet_dir()
        s_ft, drop_ft = t * ux, d + t * uz             # facet tangent point
        # The round-over is ONE chord, wall tangent point -> facet tangent point (a tiny secondary
        # bevel at ~58 deg): a two-chord arc would put a 0.02 mm sliver at 74 deg on every edge,
        # steeper than Smart UV Project's 66 deg limit, so it would leave the plate island and
        # the island's footprint would stop short of the outline (LOD2's plate corners then fall
        # outside it and get clamped).  The remaining segments subdivide the flat facet.
        out = [(0.0, self.wall_top_drop), (s_ft, drop_ft)]
        flat_segments = segments - 1
        for k in range(1, flat_segments):
            f = k / flat_segments
            out.append((s_ft + (w - s_ft) * f, drop_ft * (1.0 - f)))
        return out + [(w, 0.0)]

    def section_area(self, segments: int = 0) -> float:
        """Area of the material the chamfer removes per unit edge length (one face), m2.

        With ``segments`` the polygonised profile the generator authors (its chords cut a
        little more than the round); 0 = the smooth profile (integrated at 4000 steps).
        """
        if segments > 0:
            pts = self.levels(segments)
        else:
            pts = [(self.width * k / 4000, self.drop_at(self.width * k / 4000)) for k in range(4001)]
        area = 0.0
        for (s0, d0), (s1, d1) in zip(pts, pts[1:]):
            area += 0.5 * (d0 + d1) * (s1 - s0)        # area under the drop curve
        return area

    def validate(self, half_t: float, allow_zero_land: bool = False) -> None:
        if not 0.0 < self.width:
            raise ValueError(f"chamfer width must be positive: {self.width}")
        if not 0.0 < self.depth:
            raise ValueError(f"chamfer depth must be positive: {self.depth}")
        if not 0.0 <= self.round:
            raise ValueError(f"chamfer round-over cannot be negative: {self.round}")
        limit_ok = (self.wall_top_drop <= half_t + 0.5 * SNAP) if allow_zero_land else (self.wall_top_drop < half_t)
        if not limit_ok:
            raise ValueError(f"chamfer depth {self.wall_top_drop / MM:.3f} mm (with its round-over) must "
                             f"leave a land: below half the thickness {half_t / MM:.3f} mm")


def chamfer_profile(thickness_mm: float, width_mm: Optional[float], depth_mm: Optional[float],
                    round_mm: Optional[float]) -> ChamferProfile:
    """The profile for a plate of ``thickness_mm``; None picks the pack default for that term."""
    width = CHAMFER_WIDTH_FRACTION * thickness_mm if width_mm is None else width_mm
    depth = CHAMFER_DEPTH_FRACTION * width if depth_mm is None else depth_mm
    rnd = CHAMFER_ROUND_FRACTION * depth if round_mm is None else round_mm
    return ChamferProfile(width=width * MM, depth=depth * MM, round=rnd * MM)


@dataclass(frozen=True)
class LodSpec:
    """Segment counts for one LOD.  Counts are per wedge (one 360/n sector) unless noted.

    ``columns``            quads across the arm (``columns + 1`` plate columns)
    ``notch_segments``     hub segments per HALF notch (the notch arc is silhouette)
    ``hole_segments``      hole-ring segments per wedge; 0 drops the hole and the hub
                           becomes a disc fanned from the centre
    ``bevel_segments``     segments of the chamfer profile (ChamferProfile.levels); 0 drops
                           the chamfer (LOD2)
    ``straight_intervals`` intervals from the hub arc to the shoulder (the last station is
                           the shoulder itself, authored as a mitred ring)
    ``taper_intervals``    chamfered: shoulder to the chamfer apex (where the two facets
                           meet); plain: shoulder to tip.  This is the knob the builder
                           raises when a LOD lands under its band floor (it adds no shape,
                           so it is the honest pad)
    ``tip_intervals``      chamfered only: apex to the point (the ridge roof; with a flat
                           facet one interval is exact)
    ``band``               (min, max) triangles, study 4
    ``hub_rings``          empty (default): the hole ring is bridged k:1 straight onto the
                           hub rim (the four-point's shipped topology; needs the hub
                           segments to be a multiple of the hole segments).  Otherwise a
                           tuple of ``(kind, t)`` intermediate rings between the hole ring
                           (or the axis, without a hole) and the hub rim, at radius
                           ``r_in + t (r_hub - r_in)``, joined band by band with a
                           mirror-symmetric zipper (quads where the rings line up, one
                           triangle per extra segment).  Kinds: ``seam`` (1 segment per
                           wedge), ``hole`` (the hole ring's angles), ``arm`` (the rim's
                           seam, arm-corner and arm-root angles, without the interior notch
                           points) and ``rim`` (every rim angle).  This replaces a long
                           k:1 fan - a pinwheel of slivers when the hole is small and the
                           hub large - with graded, near-square faces.

    Knife-grind flags (style pass 2; all True/False defaults are LOD0's):
    ``scallop``            the notch arcs carry the small scallop chamfer and the knife grind
                           runs out into it at the root; False = square notch walls and the
                           grind runs out to nothing at the root corner
    ``hole_bevel``         the centre hole carries its deburr chamfer (one segment)
    ``runout_station``     a station at the end of the grind run-out (``Outline.x_run``);
                           False = the run-out spans the first straight interval
    ``knife_land``         the facets leave the spec's edge land; False = they meet in a sharp
                           edge line (land 0, no wall quads on the cutting edges)
    ``pyramid_tip``        no apex / roof stations: the shoulder ring caps straight onto the
                           point (the plate slopes to it); needs taper_intervals = 1 and
                           tip_intervals = 0
    """

    columns: int = 4
    notch_segments: int = 2
    hole_segments: int = 4
    bevel_segments: int = 3
    straight_intervals: int = 3
    taper_intervals: int = 4
    tip_intervals: int = 2
    band: Tuple[int, int] = LOD0_BAND
    note: str = ""
    hub_rings: Tuple[Tuple[str, float], ...] = ()
    scallop: bool = True
    hole_bevel: bool = True
    runout_station: bool = True
    knife_land: bool = True
    pyramid_tip: bool = False

    @property
    def hub_segments(self) -> int:
        """Hub-ring segments per wedge: both half notches plus the arm root arc."""
        return 2 * self.notch_segments + self.columns

    @property
    def has_hole(self) -> bool:
        return self.hole_segments > 0

    @property
    def has_bevel(self) -> bool:
        return self.bevel_segments > 0

    @property
    def has_scallop(self) -> bool:
        return self.has_bevel and self.scallop

    @property
    def has_hole_bevel(self) -> bool:
        return self.has_hole and self.hole_bevel and self.has_bevel

    @property
    def has_runout_station(self) -> bool:
        return self.has_bevel and self.runout_station

    def ring_segments(self, kind: str) -> int:
        """Segments per wedge of an intermediate hub ring of ``kind``."""
        if kind == "seam":
            return 1
        if kind == "hole":
            return self.hole_segments
        if kind == "arm":
            return self.columns + 2
        if kind == "rim":
            return self.hub_segments
        raise ValueError(f"unknown hub ring kind {kind!r}; expected one of {RING_KINDS}")

    def hub_band_segments(self) -> Tuple[int, ...]:
        """Segments per wedge of every hub ring from the inside out (0 = the axis point)."""
        inner = self.hole_segments if self.has_hole else 0
        return (inner,) + tuple(self.ring_segments(kind) for kind, _t in self.hub_rings) + (self.hub_segments,)

    def validate(self) -> None:
        if self.columns < 1 or self.notch_segments < 1 or self.straight_intervals < 1:
            raise ValueError(f"columns, notch_segments and straight_intervals must be >= 1: {self}")
        if self.taper_intervals < 1:
            raise ValueError(f"taper_intervals must be >= 1: {self}")
        if self.hole_segments < 0 or self.bevel_segments < 0 or self.tip_intervals < 0:
            raise ValueError(f"segment counts cannot be negative: {self}")
        if self.pyramid_tip:
            if not self.has_bevel or self.taper_intervals != 1 or self.tip_intervals != 0:
                raise ValueError(f"pyramid_tip needs a bevel, taper_intervals = 1 and tip_intervals = 0: {self}")
        elif self.has_bevel and self.tip_intervals < 1:
            raise ValueError("a bevelled LOD needs tip_intervals >= 1 (apex to point)")
        previous = 0.0
        for ring in self.hub_rings:
            if len(ring) != 2 or ring[0] not in RING_KINDS:
                raise ValueError(f"hub_rings entries are (kind, t) with kind in {RING_KINDS}: {ring!r}")
            kind, t = ring
            if not previous < t < 1.0:
                raise ValueError(f"hub ring t values must increase strictly inside (0, 1): {self.hub_rings}")
            if kind == "hole" and not self.has_hole:
                raise ValueError("a 'hole' hub ring needs a hole (hole_segments > 0)")
            previous = t
        if self.has_hole and not self.hub_rings and self.hub_segments % self.hole_segments:
            raise ValueError(
                f"hub segments per wedge ({self.hub_segments} = 2 x {self.notch_segments} notch + "
                f"{self.columns} columns) must be a multiple of hole_segments ({self.hole_segments}) "
                f"so the hole ring bridges to the hub ring k:1 without T-junctions")
        if self.band[0] >= self.band[1]:
            raise ValueError(f"band must be (min, max): {self.band}")


def wedge_triangles(lod: LodSpec) -> int:
    """Exact triangle count of one wedge as the generator authors it (tested against it).

    Lets a spec pick LOD counts that land in band before any geometry exists.  Terms:
    hub region (annulus bridged to the hole ring, or a disc fan without a hole), notch
    walls, scallop chamfer bands, hole wall and hole chamfer, and the arm: every bridge
    between two full cross-sections is 4 cols plate triangles + 8 K facet + 4 wall (0 wall
    when the facets meet in an edge line, ``knife_land`` False); the root bridge without a
    scallop starts from the collapsed corner (4 K facet triangles, 4 or 2 wall); the bridge
    onto the apex loses half its plate (the columns weld to the ridge), the roof bridges
    have no plate, and the cap onto the point has 4 K + wall.  A pyramid tip caps the
    shoulder ring straight onto the point: 2 cols + 4 K + wall.
    """
    cols, notch, hub = lod.columns, lod.notch_segments, lod.hub_segments
    k = lod.bevel_segments
    tris = 4 * notch + (8 * k * notch if lod.has_scallop else 0)
    if lod.hub_rings:
        # Any triangulation of a band between rings of a and b segments has a + b triangles
        # (the axis point counts as 0 segments: a fan), top and bottom.
        bands = lod.hub_band_segments()
        tris += 2 * sum(a + b for a, b in zip(bands, bands[1:]))
        if lod.has_hole:
            tris += 2 * lod.hole_segments
    elif lod.has_hole:
        tris += 2 * (hub + lod.hole_segments) + 2 * lod.hole_segments
    else:
        tris += 2 * hub
    if lod.has_hole_bevel:
        tris += 4 * lod.hole_segments                                   # hole chamfer, top and bottom
    if not lod.has_bevel:
        full = 4 * cols + 4
        tris += lod.straight_intervals * full                          # hub arc -> shoulder
        tris += (lod.taper_intervals - 1) * (4 * cols + 4) + 2 * cols + 4
        return tris
    wall = 4 if lod.knife_land else 0
    full = 4 * cols + 8 * k + wall
    root = full if lod.has_scallop else 4 * cols + 4 * k + (4 if lod.knife_land else 2)
    bridges = (1 if lod.has_runout_station else 0) + lod.straight_intervals   # root -> ... -> shoulder
    tris += root + (bridges - 1) * full
    if lod.pyramid_tip:
        tris += 2 * cols + 4 * k + wall                                 # shoulder straight onto the point
        return tris
    tris += (lod.taper_intervals - 1) * full                           # shoulder -> apex
    tris += 2 * cols + 8 * k + wall                                     # last bridge onto the apex
    tris += (lod.tip_intervals - 1) * (8 * k + wall) + 4 * k + wall     # roof and tip cap
    return tris


def lod_triangles(lod: LodSpec, points: int) -> int:
    return points * wedge_triangles(lod)


def _first_fitting(candidates, points: int, band) -> LodSpec:
    """First valid candidate whose triangle count is not over the band ceiling."""
    tried = []
    for lod in candidates:
        try:
            lod.validate()
        except ValueError:
            continue
        count = lod_triangles(lod, points)
        tried.append((count, lod))
        if count <= band[1]:
            return lod
    detail = ", ".join(f"{count}" for count, _lod in tried)
    raise ValueError(f"no study-4 LOD candidate fits under {band[1]} triangles for C{points} "
                     f"(candidates gave {detail}); spell this LOD out by hand")


def study_lod_chain(lod0: LodSpec, points: int) -> Tuple[LodSpec, LodSpec, LodSpec]:
    """LOD0 plus LOD1/LOD2 derived by study 4's table, sized for a C_points star.

    LOD1 halves the hole ring and the bevel segments (rounded up: a one-segment knife
    facet stays one segment); it also drops what never carried shape - extra plate columns
    and extra intervals on the flat parallel run - and halves the ruled taper intervals, but
    keeps the notch arc (silhouette) and the intervals past the bevel apex.  LOD2 drops the
    hole but, knife grind pass (decision D), keeps a single-facet grind on every cutting
    edge: its facets meet in a sharp edge line (land 0), the scallops are square, the grind
    runs out over the whole parallel run and the shoulder caps straight onto the point
    (``pyramid_tip``), which is what fits a C8 inside 250 triangles.

    Triangles scale with n, so when the preferred counts would overshoot the band ceiling
    (a C8 LOD2 at 2 columns and 2 notch segments is 320 triangles) coarser candidates are
    tried in order: fewer roof intervals, then a coarser notch arc, then one column.  A
    LOD under its band floor is padded later by author_lod (taper intervals only).
    """
    lod0.validate()
    if lod_triangles(lod0, points) > lod0.band[1]:
        raise ValueError(f"LOD0 is {lod_triangles(lod0, points)} triangles, over {lod0.band}")
    hole1 = math.ceil(lod0.hole_segments / 2) if lod0.has_hole else 0
    bevel1 = math.ceil(lod0.bevel_segments / 2) if lod0.has_bevel else 0
    tip1 = lod0.tip_intervals if lod0.has_bevel else 0
    note1 = "study 4 LOD1: hole ring and bevel segments halved"
    lod1_candidates = []
    for notch in (lod0.notch_segments, max(1, lod0.notch_segments // 2), 1):
        for cols in (max(2, lod0.columns // 2), 1):
            for tip in (tip1, min(tip1, 1)):
                for hole in (hole1, 1 if hole1 else 0):
                    lod1_candidates.append(LodSpec(
                        columns=cols, notch_segments=notch, hole_segments=hole, bevel_segments=bevel1,
                        straight_intervals=1, taper_intervals=max(1, lod0.taper_intervals // 2),
                        tip_intervals=tip, band=LOD1_BAND, note=note1))
    lod1 = _first_fitting(lod1_candidates, points, LOD1_BAND)
    note2 = "study 4 LOD2: hole dropped; single-facet knife grind to an edge line, square scallops, pyramid tip"
    lod2_candidates = [
        LodSpec(columns=cols, notch_segments=notch, hole_segments=0, bevel_segments=1,
                straight_intervals=1, taper_intervals=1, tip_intervals=0, band=LOD2_BAND, note=note2,
                scallop=False, hole_bevel=False, runout_station=False, knife_land=False, pyramid_tip=True)
        for notch, cols in ((lod0.notch_segments, 2), (max(1, lod0.notch_segments // 2), 2), (1, 2), (1, 1))
    ]
    lod2 = _first_fitting(lod2_candidates, points, LOD2_BAND)
    lod0 = replace(lod0, note=lod0.note or "study 4 LOD0: full outline, bevel, hole ring")
    return lod0, lod1, lod2


@dataclass(frozen=True)
class RadialStarSpec:
    """Build-to numbers for a C_n hira-shuriken: parallel-sided arms off a round hub.

    Outline rule (study 2.1, shared by 2.2 / 2.4 / 2.7): parallel-sided arms off a ROUND
    hub, tapering only near the tip, no edge concavity; the notch between arms is the
    hub circle itself, not a vee.  +X points at arm 0 on every form (study 4 pivot rule).
    """

    form: str                       # CLI key, e.g. "four_point"
    mesh_name: str                  # "SM_Shuriken_FourPoint"
    points: int                     # n; the mesh is exactly C_n
    tip_circle_mm: float            # tip-circle diameter (= tip-to-tip across for even n)
    thickness_mm: float
    arm_width_mm: float
    hub_radius_mm: float
    hole_diameter_mm: float         # minimum opening: the hole polygon is circumscribed
    tip_included_deg: float
    mass_target_g: float
    lods: Tuple[LodSpec, ...]
    # Knife grind (style pass 2, decision A): per-side grind angle from the face and the vertical
    # land left at the edge on every cutting edge (the width follows); the scallops' small chamfer
    # (plan width, at the grind angle), the hole's deburr chamfer and the root run-out length.
    grind_angle_deg: float = GRIND_ANGLE_DEG
    edge_land_mm: float = EDGE_LAND_MM
    scallop_chamfer_mm: float = SCALLOP_CHAMFER_MM
    hole_chamfer_mm: float = HOLE_CHAMFER_MM
    hole_chamfer_deg: float = HOLE_CHAMFER_DEG
    grind_runout_mm: float = GRIND_RUNOUT_MM
    # Study min-max (and typical) mass for the form, grams: the ground mass is REPORTED against it.
    study_mass_range_g: Optional[Tuple[float, float]] = None
    study_mass_typical_g: Optional[Tuple[float, float]] = None
    # The study mass gate (outline proportions against a real sourced object) is evaluated on
    # the UN-GROUND plate (outline x thickness); the ground mass is reported, not gated.
    mass_tolerance_g: float = 2.0
    density_g_cm3: float = 7.85
    grip_angle_deg: Optional[float] = None   # default 180/n: the rim notch between arms 0 and 1
    title: str = ""
    study_section: str = ""
    revision: int = 1
    # UCX hull: "pipeline" = pipeline.make_ucx_hull (convex hull of LOD0, collapse-decimated to
    # <= hull_verts; the four-point's shipped hull), "tip_prism" = the n-gon prism through the
    # tips at full plate thickness (2n vertices, exactly C_n, encloses the mesh by construction
    # - the build refuses it if any LOD0 vertex falls outside).
    hull: str = "pipeline"
    # Study 4 physics: an explicit Mass in KG override per form (the FBX cannot carry it).
    physics_mass_kg: Optional[float] = None
    lod_screen_sizes: Tuple[float, ...] = LOD_SCREEN_SIZES

    def outline(self) -> "Outline":
        return Outline.from_spec(self)

    def chamfer(self) -> ChamferProfile:
        """The knife grind profile of the cutting edges (metres)."""
        return ChamferProfile.knife(self.thickness_mm * MM, self.grind_angle_deg, self.edge_land_mm * MM)

    def validate(self) -> None:
        if not 0.0 < self.edge_land_mm <= MAX_EDGE_LAND_MM:
            raise ValueError(f"edge_land_mm must be in (0, {MAX_EDGE_LAND_MM}]: {self.edge_land_mm}")
        if not 15.0 <= self.grind_angle_deg <= 60.0:
            raise ValueError(f"grind_angle_deg out of range: {self.grind_angle_deg}")
        if self.points < 2:
            raise ValueError("a radial star needs at least 2 points")
        if not self.mesh_name.startswith("SM_Shuriken_"):
            raise ValueError(f"mesh_name must be SM_Shuriken_<Form> (study 4 naming): {self.mesh_name}")
        if not self.lods:
            raise ValueError("at least LOD0 is required")
        if self.hull not in HULL_METHODS:
            raise ValueError(f"hull must be one of {HULL_METHODS}: {self.hull!r}")
        if len(self.lod_screen_sizes) < len(self.lods) or any(
                b >= a for a, b in zip(self.lod_screen_sizes, self.lod_screen_sizes[1:])):
            raise ValueError(f"lod_screen_sizes must cover every LOD and strictly descend: {self.lod_screen_sizes}")
        for level, lod in enumerate(self.lods):
            lod.validate()
            predicted = lod_triangles(lod, self.points)
            if predicted > lod.band[1]:
                raise ValueError(f"{self.mesh_name} LOD{level}: {predicted} triangles predicted, over "
                                 f"its band {lod.band}; reduce its LodSpec counts")
        self.outline().validate(self.lods)


@dataclass(frozen=True)
class Outline:
    """Derived outline in metres.  Arithmetic order matches rev 2 exactly."""

    n: int
    r_tip: float
    thickness: float
    half_t: float
    arm_width: float
    half_w: float
    r_hub: float
    hole_diameter: float
    r_hole: float
    tip_included_deg: float
    half_tip_rad: float
    taper_len: float
    x_taper: float
    arm_half_angle: float
    chamfer: ChamferProfile
    chamfer_w: float        # plan width of the knife grind, perpendicular to the edge
    chamfer_y: float        # its y inset on the taper edge (which leans half the tip angle off x)
    x_apex: float           # past here the arm is narrower than two grinds: the facets meet in a ridge
    half_sector: float
    scallop: ChamferProfile = None        # the small chamfer on the concave hub arcs
    hole_chamfer: ChamferProfile = None   # the centre hole's deburr chamfer
    grind_angle_deg: float = GRIND_ANGLE_DEG
    edge_land: float = EDGE_LAND_MM * MM
    runout: float = GRIND_RUNOUT_MM * MM
    x_run: float = 0.0      # arm-local x where the knife grind has run out to full width (root + runout)

    @classmethod
    def from_spec(cls, spec: RadialStarSpec) -> "Outline":
        r_tip = 0.5 * spec.tip_circle_mm * MM
        thickness = spec.thickness_mm * MM
        arm_width = spec.arm_width_mm * MM
        half_w = 0.5 * arm_width
        r_hub = spec.hub_radius_mm * MM
        hole_diameter = spec.hole_diameter_mm * MM
        half_tip_rad = math.radians(0.5 * spec.tip_included_deg)
        taper_len = half_w / math.tan(half_tip_rad)
        x_taper = r_tip - taper_len
        chamfer = spec.chamfer()
        # The grind width is perpendicular to the ground edge, which leans half the tip
        # angle off x on the taper, so its y component there is width / cos(half tip angle).
        chamfer_y = chamfer.width / math.cos(half_tip_rad)
        runout = spec.grind_runout_mm * MM
        x_root0 = math.sqrt(r_hub * r_hub - half_w * half_w) if half_w < r_hub else float("nan")
        return cls(
            n=spec.points,
            r_tip=r_tip,
            thickness=thickness,
            half_t=0.5 * thickness,
            arm_width=arm_width,
            half_w=half_w,
            r_hub=r_hub,
            hole_diameter=hole_diameter,
            r_hole=0.5 * hole_diameter,
            tip_included_deg=spec.tip_included_deg,
            half_tip_rad=half_tip_rad,
            taper_len=taper_len,
            x_taper=x_taper,
            arm_half_angle=math.asin(half_w / r_hub) if half_w < r_hub else float("nan"),
            chamfer=chamfer,
            chamfer_w=chamfer.width,
            chamfer_y=chamfer_y,
            # Past x_apex the arm is narrower than two chamfers, so the facets meet in a ridge.
            x_apex=r_tip - chamfer_y / math.tan(half_tip_rad),
            half_sector=math.pi / spec.points,
            scallop=ChamferProfile.at_angle(spec.scallop_chamfer_mm * MM, spec.grind_angle_deg),
            hole_chamfer=ChamferProfile.at_angle(spec.hole_chamfer_mm * MM, spec.hole_chamfer_deg),
            grind_angle_deg=spec.grind_angle_deg,
            edge_land=spec.edge_land_mm * MM,
            runout=runout,
            x_run=x_root0 + runout,
        )

    @property
    def sector(self) -> float:
        return 2.0 * self.half_sector

    def hole_polygon_radius(self, hole_total: int) -> float:
        """Circumscribed hole polygon, so the *minimum* opening is the stated diameter."""
        return self.r_hole / math.cos(math.pi / hole_total)

    def half_width(self, x: float) -> float:
        """Half width of the arm at ``x``: parallel-sided, tapering only near the tip."""
        if x <= self.x_taper:
            return self.half_w
        return max(0.0, (self.r_tip - x) * math.tan(self.half_tip_rad))

    def chamfer_of(self, lod: "LodSpec") -> float:
        """Plan width of the knife grind this LOD carries (0 when it has none)."""
        return self.chamfer_w if lod.has_bevel else 0.0

    def knife_of(self, lod: "LodSpec") -> ChamferProfile:
        """The cutting-edge profile of this LOD: the spec's knife, or (``knife_land`` False) the
        same plan width run down to the mid-plane, so the two facets meet in an edge line."""
        if lod.knife_land:
            return self.chamfer
        return ChamferProfile(width=self.chamfer.width, depth=self.half_t, round=0.0)

    def scallop_of(self, lod: "LodSpec") -> float:
        """Plan width of the scallop chamfer on this LOD's notch arcs (0 when square)."""
        return self.scallop.width if lod.has_scallop else 0.0

    def scallop_levels(self, lod: "LodSpec"):
        """(inset, drop) levels of the notch arcs and the arm root (K + 1 of them, collapsed
        onto the corner when the LOD has no scallop chamfer)."""
        k = lod.bevel_segments
        if not lod.has_bevel:
            return [(0.0, 0.0)]
        if not lod.has_scallop:
            return [(0.0, 0.0)] * (k + 1)
        return self.scallop.levels(k)

    def rim_radius(self, lod: "LodSpec") -> float:
        """Radius of the hub PLATE's outer ring: the notch arc inset by the scallop chamfer."""
        return self.r_hub - self.scallop_of(lod)

    def rim_half_w(self, lod: "LodSpec") -> float:
        """Half width of the arm PLATE at the root (where the knife grind has run out to the
        scallop chamfer) on this LOD."""
        return self.half_w - self.scallop_of(lod)

    def hole_plate_radius(self, lod: "LodSpec") -> float:
        """Corner radius of the ring where the hole chamfer meets the plate (the hole polygon's
        own radius without a hole chamfer)."""
        total = lod.hole_segments * self.n
        r_poly = self.hole_polygon_radius(total)
        if not lod.has_hole_bevel:
            return r_poly
        return r_poly + self.hole_chamfer.width / math.cos(math.pi / total)

    def x_root(self, inset: float) -> float:
        """Arm-local x where the arm edge inset by ``inset`` meets the notch arc inset by the same.

        The root is a concave corner, so the two inset curves (the line y = half_w - inset
        and the circle r = r_hub - inset) intersect there: the chamfer bands meet in a mitre
        line running from the outline corner (inset 0) inward to the plate corner.
        """
        r, y = self.r_hub - inset, self.half_w - inset
        return math.sqrt(r * r - y * y)

    def validate(self, lods) -> None:
        mm = lambda v: f"{v / MM:.3f} mm"  # noqa: E731
        if not self.half_w < self.r_hub:
            raise ValueError(f"arm half width {mm(self.half_w)} must be below the hub radius {mm(self.r_hub)}")
        if not self.arm_half_angle < self.half_sector:
            raise ValueError(
                f"arms overlap at the hub: each arm needs {math.degrees(2 * self.arm_half_angle):.2f} deg "
                f"of a {math.degrees(self.sector):.2f} deg sector; raise the hub radius above "
                f"{mm(self.half_w / math.sin(self.half_sector))} or narrow the arm")
        if not self.r_hub < self.x_taper:
            raise ValueError(f"no parallel run: the taper starts at {mm(self.x_taper)}, inside the hub")
        if not 0.0 < self.r_hole < self.r_hub:
            raise ValueError("hole must be smaller than the hub")
        self.chamfer.validate(self.half_t)
        self.scallop.validate(self.half_t)
        self.hole_chamfer.validate(self.half_t)
        if not self.chamfer_w < self.half_w:
            raise ValueError(f"grind width {mm(self.chamfer_w)} must be below the arm half width {mm(self.half_w)}")
        if not self.scallop.width < self.chamfer_w:
            raise ValueError(f"scallop chamfer {mm(self.scallop.width)} must be narrower than the knife grind "
                             f"{mm(self.chamfer_w)} it runs out into")
        if not self.x_taper < self.x_apex < self.r_tip:
            raise ValueError(
                f"grind stations out of order: shoulder {mm(self.x_taper)}, apex {mm(self.x_apex)}, "
                f"tip {mm(self.r_tip)}")
        if not self.x_root(0.0) < self.x_run < self.x_taper:
            raise ValueError(f"grind run-out ends at {mm(self.x_run)}, outside the parallel run "
                             f"{mm(self.x_root(0.0))} .. {mm(self.x_taper)}")
        for level, lod in enumerate(lods):
            if lod.has_bevel:
                self.knife_of(lod).validate(self.half_t, allow_zero_land=not lod.knife_land)
            if lod.has_hole:
                if self.hole_plate_radius(lod) >= self.rim_radius(lod):
                    raise ValueError(f"LOD{level}: hole polygon (with its chamfer) reaches the hub plate's rim")
            for kind, t in lod.hub_rings:
                r = self.hub_ring_radius(lod, t)
                if not self.hub_inner_radius(lod) < r < self.rim_radius(lod):
                    raise ValueError(f"LOD{level}: hub ring {kind} at {mm(r)} is outside the hub plate")

    def hub_inner_radius(self, lod: "LodSpec") -> float:
        """Radius the hub rings are measured from: the hole plate ring's corners, or the axis."""
        return self.hole_plate_radius(lod) if lod.has_hole else 0.0

    def hub_ring_radius(self, lod: "LodSpec", t: float) -> float:
        """Intermediate hub ring radius: ``t`` of the way from the hole ring to the plate rim."""
        r_in = self.hub_inner_radius(lod)
        return r_in + t * (self.rim_radius(lod) - r_in)

    def tip_extents(self):
        """(span_x, span_y) of the tip circle points, exact for quarter-turn forms."""
        xs, ys = [], []
        for k in range(self.n):
            x, y = rotate(k, self.n, self.r_tip, 0.0)
            xs.append(x)
            ys.append(y)
        return max(xs) - min(xs), max(ys) - min(ys)


# =========================================================================== analytic area


def analytic_area(spec: RadialStarSpec, lod: Optional[LodSpec] = None) -> dict:
    """Exact plan area of the UN-bevelled outline, term by term, in mm2 (pure Python).

    This is the number a study cross-check should quote.  Hub disc minus the round hole,
    plus n arms; each arm is

    * the parallel run OUTSIDE the hub circle: the strip |y| <= w/2 from the hub arc out
      to the shoulder, i.e. ``w * x_taper`` minus the circular cap
      ``integral_{-w/2}^{w/2} sqrt(r^2 - y^2) dy = (w/2) sqrt(r^2 - w^2/4) + r^2 asin(w/2r)``;
    * plus the taper triangle ``(w/2) * L``, ``L = (w/2) / tan(tip/2)``.

    ``arms_from_hub_radius_mm2`` is what the sum gives when each run is counted from the
    line x = r (a plain rectangle ``w * (x_taper - r)``) instead of from the hub arc: that
    drops n circular slivers of ``w r - cap`` each.  It is the slip behind study 2.1's
    first 1647 mm2 (corrected to 1668) and behind study 2.2's 3055 mm2.

    With ``lod`` the polygonised figure the generator authors is added: each notch arc
    becomes chords (a chord of angle phi loses ``r^2 (phi - sin phi) / 2``) and the hole
    becomes the circumscribed m-gon (``m r_h^2 tan(pi/m)``).  The arm-root arc is interior
    (hub fan and arm row share its chords), so it costs nothing.  What the ground chamfer
    removes is not in any of these figures: that is a volume, measured on the mesh.
    """
    n = spec.points
    r_tip = 0.5 * spec.tip_circle_mm
    w = spec.arm_width_mm
    h = 0.5 * w
    r = spec.hub_radius_mm
    r_h = 0.5 * spec.hole_diameter_mm
    half_tip = math.radians(0.5 * spec.tip_included_deg)
    taper_len = h / math.tan(half_tip)
    x_taper = r_tip - taper_len
    cap = h * math.sqrt(r * r - h * h) + r * r * math.asin(h / r)
    run = w * x_taper - cap
    triangle = h * taper_len
    hub = math.pi * r * r
    hole = math.pi * r_h * r_h
    exact = hub - hole + n * (run + triangle)
    sliver = w * r - cap
    out = {
        "units": "mm2",
        "points": n,
        "hub_disc": hub,
        "hole_disc": hole,
        "hub_minus_hole": hub - hole,
        "arm_parallel_run_outside_hub": run,
        "arm_rectangle_to_shoulder": w * x_taper,
        "arm_circular_cap_inside_hub": cap,
        "arm_taper_triangle": triangle,
        "arm_total": run + triangle,
        "arms_total": n * (run + triangle),
        "taper_len_mm": taper_len,
        "x_taper_mm": x_taper,
        "exact": exact,
        "root_sliver_per_arm": sliver,
        "arms_from_hub_radius_mm2": exact - n * sliver,
        "arm_angle_at_hub_deg": 2.0 * math.degrees(math.asin(h / r)),
        "clear_hub_per_sector_deg": 360.0 / n - 2.0 * math.degrees(math.asin(h / r)),
    }
    if lod is not None:
        phi = (math.pi / n - math.asin(h / r)) / lod.notch_segments
        chords = 2 * lod.notch_segments * n
        notch_loss = chords * 0.5 * r * r * (phi - math.sin(phi))
        m = lod.hole_segments * n
        hole_poly = m * r_h * r_h * math.tan(math.pi / m) if m else 0.0
        hole_excess = hole_poly - hole if m else -hole
        out.update({
            "polygon_notch_chords": chords,
            "polygon_notch_chord_loss": notch_loss,
            "polygon_hole_segments": m,
            "polygon_hole_area": hole_poly,
            "polygon_hole_excess": hole_excess,
            "polygonised": exact - notch_loss - hole_excess,
        })
    return out


def numeric_outline_area(spec: RadialStarSpec, samples: int = 4096) -> float:
    """Shoelace area (mm2) of a finely sampled outline minus a finely sampled hole.

    An independent check on ``analytic_area``'s formula: no integral, no cap term, just the
    boundary walked point by point (``samples`` points per edge piece, per wedge).
    """
    n = spec.points
    r_tip = 0.5 * spec.tip_circle_mm
    h = 0.5 * spec.arm_width_mm
    r = spec.hub_radius_mm
    half_tip = math.radians(0.5 * spec.tip_included_deg)
    x_taper = r_tip - h / math.tan(half_tip)
    x_root = math.sqrt(r * r - h * h)
    arm_half = math.asin(h / r)
    half_sector = math.pi / n
    m = samples
    wedge = []
    for i in range(m):                    # lower half notch, up to the arm edge
        a = -half_sector + (half_sector - arm_half) * i / m
        wedge.append((r * math.cos(a), r * math.sin(a)))
    for i in range(m):                    # lower arm edge, root to shoulder
        wedge.append((x_root + (x_taper - x_root) * i / m, -h))
    for i in range(m):                    # lower taper edge to the point
        wedge.append((x_taper + (r_tip - x_taper) * i / m, -h * (1.0 - i / m)))
    for i in range(m):                    # upper taper edge back to the shoulder
        wedge.append((r_tip - (r_tip - x_taper) * i / m, h * i / m))
    for i in range(m):                    # upper arm edge back to the root
        wedge.append((x_taper - (x_taper - x_root) * i / m, h))
    for i in range(m):                    # upper half notch
        a = arm_half + (half_sector - arm_half) * i / m
        wedge.append((r * math.cos(a), r * math.sin(a)))
    points = []
    for k in range(n):
        c, s = math.cos(2.0 * math.pi * k / n), math.sin(2.0 * math.pi * k / n)
        points += [(c * x - s * y, s * x + c * y) for x, y in wedge]
    twice = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        twice += x1 * y2 - x2 * y1
    hole_m = 6 * m * n
    r_h = 0.5 * spec.hole_diameter_mm
    hole = 0.5 * hole_m * r_h * r_h * math.sin(2.0 * math.pi / hole_m)
    return abs(twice) * 0.5 - hole
