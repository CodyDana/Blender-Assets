"""Square-plate (senban) spec: pure data, no bpy.

SHURIKEN_STUDY.md 2.3: a square standing on a corner - four corner points on +X, +Y, -X,
-Y, four CONCAVE sides (one circular arc each), a square centre hole.  D4: C4 about Z,
mirror lines through the corners and through the side midpoints.

Geometry, in the wedge-local frame the generator authors (corner 0 on +X, the wedge from
-45 deg to +45 deg, its upper half-side running from the corner C to the side midpoint M+
on the 45 deg seam):

    corner radius   R_c  = side / sqrt 2                   (107.763 mm corner to corner at 76.2)
    arc             chord = side, sagitta h: radius rho = ((side/2)^2 + h^2) / 2h,
                    centre on the 45 deg line at d = side/2 - h + rho from the origin;
                    the plate lies OUTSIDE that circle (the side is concave)
    side midpoint   r_mid = side/2 - h                      (the inscribed radius)
    corner angle    2 alpha: the two arcs meet at the corner at 2 * 27.1 = 54.2 deg (at h = 6)
    hole            square of side a_h, 'parallel' = its sides parallel to the outer square's
                    sides, so its corners point at the outer corners (lie on the axes); each
                    corner filleted with radius r_f (a punched hole is never razor-cornered)
    ground facet    a rounded ground facet (quarter round of radius b, perpendicular to the
                    edge: b in plan, b deep) on both faces along the FULL length of every
                    concave side, the two facets of a corner meeting in a mitre (a ridge on
                    the corner's axis) - image F and chart I, see build_square_plate.py

Contours (all parametrised u = 0 on the corner's axis .. 1 on the 45 deg seam):

    hole contour H(u)       fillet over u in [0, fillet_u], then the straight half hole side
    plate edge B(u)         the facet's inner boundary: the arc offset b into the plate; at
                            u = 0 the point on the axis at arc-distance b (the mitre)
    facet contours          arc offsets s_k = b (1 - cos t_k), z_k = t/2 - b + b sin t_k
    outer edge E(u)         the arc itself (the wall top, z = +-(t/2 - b))
    hole offsets            the hole contour offset outward by delta (fillet radius r_f + delta),
                            same u samples: graded quads around the fillet's short chords
    plate rings             (1 - lam) H'(u) + lam B(u), H' the outermost offset contour, each
                            ring with its own u samples, zipped band to band
                            (shuriken_lib.geometry._zip_half)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from .spec import LOD_SCREEN_SIZES, MM

SQRT_HALF = math.sqrt(0.5)
QUARTER_TURN = 0.5 * math.pi
PLATE_LOD_CEILING = 2500            # study 4's LOD0 ceiling (project prop budget 1,000 to 5,000)
HOLE_ORIENTATIONS = ("parallel",)   # the only one implemented (image F): hole corners on the axes
EDGE_GRINDS = ("full_side",)        # the only one implemented (image F / chart I, source [42])
RING_SAMPLES = ("hole", "edge")


@dataclass(frozen=True)
class PlateLodSpec:
    """Segment counts for one square-plate LOD.  Counts are per HALF side (one eighth of the plate).

    ``edge_intervals``   chords of the concave half side, corner -> side midpoint (silhouette;
                         the plate edge and every facet contour use the same columns)
    ``fillet_segments``  chords of HALF a hole-corner fillet (2x per corner); 0 = sharp corner
    ``bevel_segments``   segments of the rounded ground-facet profile; 0 = no facet (the wall
                         is then full plate thickness and the plate runs to the edge)
    ``hole_intervals``   intervals of the straight part of the half hole side
    ``fillet_u``         share of the contour parameter the fillet takes on the hole contour,
                         so the rings fan the fillet's short chords out gradually
    ``offsets_mm``       hole-parallel contours at these distances outside the hole (the
                         hole's u samples; a filleted corner's chords grow with r_f + delta)
    ``rings``            intermediate plate contours between the outermost offset (or the
                         hole) and the plate edge: ``(samples, lam)`` with samples "hole" (the
                         hole contour's u list), "edge" (the edge's) or an int m (m uniform
                         intervals), lam in (0, 1) strictly increasing
    ``band``             (min, max) triangles.  Study 4's bands are for stars; for this plate
                         the ceiling is kept and no floor is applied (nothing is padded)
    """

    edge_intervals: int = 6
    fillet_segments: int = 2
    bevel_segments: int = 3
    hole_intervals: int = 1
    fillet_u: float = 0.3
    offsets_mm: Tuple[float, ...] = ()
    rings: Tuple[Tuple[Union[str, int], float], ...] = ()
    band: Tuple[int, int] = (0, PLATE_LOD_CEILING)
    note: str = ""

    @property
    def has_bevel(self) -> bool:
        return self.bevel_segments > 0

    @property
    def has_fillet(self) -> bool:
        return self.fillet_segments > 0

    def edge_u(self) -> List[float]:
        n = self.edge_intervals
        return [j / n for j in range(n)] + [1.0]

    def hole_u(self) -> List[float]:
        if not self.has_fillet:
            n = self.hole_intervals
            return [j / n for j in range(n)] + [1.0]
        f, fu = self.fillet_segments, self.fillet_u
        us = [fu * i / f for i in range(f)] + [fu]
        us += [fu + (1.0 - fu) * j / self.hole_intervals for j in range(1, self.hole_intervals)] + [1.0]
        return us

    def ring_u(self, samples) -> List[float]:
        if samples == "hole":
            return self.hole_u()
        if samples == "edge":
            return self.edge_u()
        m = int(samples)
        return [j / m for j in range(m)] + [1.0]

    def contour_intervals(self) -> List[int]:
        """Intervals per half side of every plate contour, hole -> offsets -> rings -> plate edge."""
        hole = len(self.hole_u()) - 1
        return ([hole] * (1 + len(self.offsets_mm)) + [len(self.ring_u(s)) - 1 for s, _lam in self.rings]
                + [self.edge_intervals])

    def validate(self) -> None:
        if self.edge_intervals < 1 or self.hole_intervals < 1:
            raise ValueError(f"edge_intervals and hole_intervals must be >= 1: {self}")
        if self.fillet_segments < 0 or self.bevel_segments < 0:
            raise ValueError(f"segment counts cannot be negative: {self}")
        if self.has_fillet and not 0.0 < self.fillet_u < 1.0:
            raise ValueError(f"fillet_u must be inside (0, 1): {self.fillet_u}")
        if any(b <= a for a, b in zip((0.0,) + tuple(self.offsets_mm), self.offsets_mm)):
            raise ValueError(f"offsets_mm must be positive and strictly increasing: {self.offsets_mm}")
        previous = 0.0
        for ring in self.rings:
            if len(ring) != 2:
                raise ValueError(f"rings entries are (samples, lam): {ring!r}")
            samples, lam = ring
            if not (samples in RING_SAMPLES or (isinstance(samples, int) and samples >= 1)):
                raise ValueError(f"ring samples must be one of {RING_SAMPLES} or an int >= 1: {samples!r}")
            if not previous < lam < 1.0:
                raise ValueError(f"ring lam values must increase strictly inside (0, 1): {self.rings}")
            previous = lam
        if self.band[0] >= self.band[1]:
            raise ValueError(f"band must be (min, max): {self.band}")


def plate_wedge_triangles(lod: PlateLodSpec) -> int:
    """Exact triangle count of one HALF side (an eighth of the plate) as the generator authors it.

    Any triangulation of a strip between polylines of a and b segments has a + b triangles, so
    the plate bands give sum(a + b) per face; the facet bands 2 N each; the outer wall 2 N and
    the hole wall 2 x (hole contour intervals).
    """
    counts = lod.contour_intervals()
    plate = sum(a + b for a, b in zip(counts, counts[1:]))
    facet = 2 * lod.edge_intervals * lod.bevel_segments
    return 2 * (plate + facet) + 2 * lod.edge_intervals + 2 * counts[0]


def plate_triangles(lod: PlateLodSpec) -> int:
    return 8 * plate_wedge_triangles(lod)


@dataclass(frozen=True)
class SquarePlateSpec:
    """Build-to numbers for the senban (study 2.3).  Millimetres, like RadialStarSpec."""

    form: str
    mesh_name: str
    side_mm: float                  # the square's side = chord between adjacent corners
    thickness_mm: float
    sagitta_mm: float               # depth of each concave side at its midpoint
    hole_side_mm: float
    hole_fillet_mm: float
    bevel_offset_mm: float          # rounded ground facet: b in plan and b deep, perpendicular to the edge
    mass_target_g: float
    lods: Tuple[PlateLodSpec, ...]
    hole_orientation: str = "parallel"
    edge_grind: str = "full_side"
    mass_tolerance_g: float = 2.0
    density_g_cm3: float = 7.85
    title: str = ""
    study_section: str = ""
    revision: int = 1
    physics_mass_kg: Optional[float] = None
    lod_screen_sizes: Tuple[float, ...] = LOD_SCREEN_SIZES
    # Tip wear ramps in over the last corner_wear_mm of radius.  The stars' ramp (0.55 of a 15-16 mm
    # taper) starts where the point is 5.5 - 6 mm wide; a 54.2 deg corner is that wide 5.8 mm in.
    corner_wear_mm: float = 5.8
    hull: str = "tip_prism"
    # LOD0 Smart UV island margin (None = the pack's --island-margin); see SquarePlateGeometry.
    island_margin: Optional[float] = None

    @property
    def points(self) -> int:
        return 4

    def outline(self) -> "PlateOutline":
        return PlateOutline.from_spec(self)

    def validate(self) -> None:
        if not self.mesh_name.startswith("SM_Shuriken_"):
            raise ValueError(f"mesh_name must be SM_Shuriken_<Form> (study 4 naming): {self.mesh_name}")
        if self.hole_orientation not in HOLE_ORIENTATIONS:
            raise ValueError(f"hole_orientation must be one of {HOLE_ORIENTATIONS}: {self.hole_orientation!r}")
        if self.edge_grind not in EDGE_GRINDS:
            raise ValueError(f"edge_grind must be one of {EDGE_GRINDS}: {self.edge_grind!r}")
        if self.hull != "tip_prism":
            raise ValueError("the square plate's hull is the 4-gon tip prism (its convex hull exactly)")
        if not self.lods:
            raise ValueError("at least LOD0 is required")
        if len(self.lod_screen_sizes) < len(self.lods) or any(
                b >= a for a, b in zip(self.lod_screen_sizes, self.lod_screen_sizes[1:])):
            raise ValueError(f"lod_screen_sizes must cover every LOD and strictly descend: {self.lod_screen_sizes}")
        for level, lod in enumerate(self.lods):
            lod.validate()
            predicted = plate_triangles(lod)
            if predicted > lod.band[1]:
                raise ValueError(f"{self.mesh_name} LOD{level}: {predicted} triangles predicted, over {lod.band}")
        self.outline().validate(self.lods)


@dataclass(frozen=True)
class PlateOutline:
    """Derived square-plate outline in metres (see the module docstring for the frame)."""

    n: int
    side: float
    thickness: float
    half_t: float
    r_tip: float            # corner radius
    sagitta: float
    rho: float              # side arc radius
    centre: float           # distance of the arc centre from the origin (on the 45 deg line)
    centre_q: float         # its x (= y) coordinate
    r_mid: float            # side-midpoint (inscribed) radius
    hole_side: float
    hole_a: float           # hole corner radius (sharp)
    hole_flat: float        # hole side-midpoint radius (half the across-flats)
    fillet: float
    fillet_x: float         # fillet centre on the axis
    bevel: float
    beta_corner: float      # arc angle of the corner, about the arc centre
    beta_mid: float         # arc angle of the side midpoint (5 pi / 4)
    corner_half_angle: float
    half_sector: float
    corner_wear: float

    @classmethod
    def from_spec(cls, spec: SquarePlateSpec) -> "PlateOutline":
        side = spec.side_mm * MM
        h = spec.sagitta_mm * MM
        half = 0.5 * side
        rho = (half * half + h * h) / (2.0 * h)
        centre = half - h + rho
        centre_q = centre * SQRT_HALF
        r_tip = side * SQRT_HALF
        hole_side = spec.hole_side_mm * MM
        hole_a = hole_side * SQRT_HALF
        fillet = spec.hole_fillet_mm * MM
        return cls(
            n=4, side=side, thickness=spec.thickness_mm * MM, half_t=0.5 * spec.thickness_mm * MM,
            r_tip=r_tip, sagitta=h, rho=rho, centre=centre, centre_q=centre_q, r_mid=half - h,
            hole_side=hole_side, hole_a=hole_a, hole_flat=0.5 * hole_side, fillet=fillet,
            fillet_x=hole_a - fillet * math.sqrt(2.0), bevel=spec.bevel_offset_mm * MM,
            beta_corner=math.atan2(-centre_q, r_tip - centre_q), beta_mid=1.25 * math.pi,
            corner_half_angle=math.atan2(centre_q - r_tip, centre_q), half_sector=0.25 * math.pi,
            corner_wear=spec.corner_wear_mm * MM,
        )

    # ------------------------------------------------------------------ contours (wedge-local, upper half)
    def arc_beta(self, u: float) -> float:
        # beta_corner is about -117 deg; the midpoint is at 225 deg = -135 deg going the short way
        return self.beta_corner + u * ((self.beta_mid - 2.0 * math.pi) - self.beta_corner)

    def edge_point(self, u: float, s: float) -> Tuple[float, float]:
        """Point at perpendicular distance ``s`` inside the concave edge, at edge parameter ``u``.

        u = 0 is the corner's axis (for s > 0 the mitre point, where the facets of the two sides
        meet), u = 1 the 45 deg seam.  Seam and axis points are constructed with x == y and
        y == 0 exactly, so the D4 vertex keys weld.
        """
        r = self.rho + s
        if u == 0.0:
            if s == 0.0:
                return self.r_tip, 0.0
            return self.centre_q - math.sqrt(r * r - self.centre_q * self.centre_q), 0.0
        if u == 1.0:
            q = (self.centre - r) * SQRT_HALF
            return q, q
        beta = self.arc_beta(u)
        return self.centre_q + r * math.cos(beta), self.centre_q + r * math.sin(beta)

    def hole_point(self, u: float, lod: PlateLodSpec, offset: float = 0.0) -> Tuple[float, float]:
        """Hole contour: the fillet (u in [0, fillet_u]) then the straight half side to the seam.

        ``offset`` (metres) moves it outward, parallel: the fillet radius grows to r_f + offset and
        the straight side moves along its normal (1, 1) / sqrt 2; a sharp corner is mitred.
        """
        mid = 0.5 * self.hole_a + offset * SQRT_HALF   # the hole side midpoint (x = y)
        if u == 1.0:
            return mid, mid
        if not lod.has_fillet or self.fillet == 0.0:
            corner = self.hole_a + offset * math.sqrt(2.0)
            return corner + u * (mid - corner), u * mid
        fu = lod.fillet_u
        r = self.fillet + offset
        if u < fu:
            if u == 0.0:
                return self.fillet_x + r, 0.0
            phi = self.half_sector * u / fu
            return self.fillet_x + r * math.cos(phi), r * math.sin(phi)
        tx, ty = self.fillet_x + r * SQRT_HALF, r * SQRT_HALF
        w = (u - fu) / (1.0 - fu)
        return tx + w * (mid - tx), ty + w * (mid - ty)

    def facet_profile(self, k: int, segments: int) -> Tuple[float, float]:
        """(s, z) of facet contour k: k = 0 the plate edge (s = b, z = t/2), k = K the wall top."""
        b = self.bevel
        if k == 0:
            return b, self.half_t
        if k == segments:
            return 0.0, self.half_t - b
        t = QUARTER_TURN * (1.0 - k / segments)
        return b * (1.0 - math.cos(t)), (self.half_t - b) + b * math.sin(t)

    def tip_extents(self):
        """(span_x, span_y): the corners are exactly on the axes."""
        return 2.0 * self.r_tip, 2.0 * self.r_tip

    def wear_range(self):
        return self.r_tip - self.corner_wear, self.r_tip

    def validate(self, lods) -> None:
        mm = lambda v: f"{v / MM:.3f} mm"  # noqa: E731
        if not 0.0 < self.sagitta < 0.5 * self.side:
            raise ValueError(f"sagitta {mm(self.sagitta)} must be inside (0, side/2)")
        if not 0.0 <= self.bevel < self.half_t:
            raise ValueError(f"facet {mm(self.bevel)} must leave a land: below half the thickness {mm(self.half_t)}")
        if not 0.0 <= self.fillet < 0.5 * self.hole_side:
            raise ValueError(f"hole fillet {mm(self.fillet)} must be under half the hole side")
        mitre_x = self.edge_point(0.0, self.bevel)[0]
        if not self.hole_a < mitre_x:
            raise ValueError(f"hole corner at {mm(self.hole_a)} reaches the facet mitre at {mm(mitre_x)}")
        if not self.hole_flat < self.r_mid - self.bevel:
            raise ValueError(f"hole flats at {mm(self.hole_flat)} reach the side facet at "
                             f"{mm(self.r_mid - self.bevel)}")
        for level, lod in enumerate(lods):
            if lod.offsets_mm:
                reach = max(lod.offsets_mm) * MM
                if not self.hole_flat + reach < 0.5 * (self.r_mid - self.bevel):
                    raise ValueError(f"LOD{level}: hole offset {mm(reach)} takes more than half the plate at the "
                                     "side midpoint")
            b = self.bevel if lod.has_bevel else 0.0
            for u in lod.edge_u()[1:]:
                x, y = self.edge_point(u, b)
                if not y > 0.0 or y > x + 1e-12:
                    raise ValueError(f"LOD{level}: plate-edge column u={u:.4f} leaves the half wedge ({x}, {y})")


# =========================================================================== analytic area


def _simpson(f, a: float, b: float, n: int = 2000) -> float:
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4 if i % 2 else 2) * f(a + i * h)
    return total * h / 3.0


def plate_analytic_area(spec: SquarePlateSpec, lod: Optional[PlateLodSpec] = None) -> dict:
    """Exact plan area of the senban outline (un-bevelled), term by term, in mm2 (pure Python).

    square side^2 - 4 circular segments (chord = side, sagitta h) - the hole (square minus the
    material its four fillets leave in the corners, (4 - pi) r_f^2).  With ``lod`` the
    polygonised figure the generator authors: each half-side arc as N chords (each chord lies
    OUTSIDE the concave edge and adds rho^2 (d - sin d) / 2 of plate), each half fillet as f
    chords (inside the fillet arc: the hole shrinks by r_f^2 (d - sin d) / 2 per chord), a
    sharp hole corner when the LOD has no fillet.  ``facet_volume_mm3`` is what the rounded
    ground facet removes: both faces, every side, the quarter-round depth d(s) = b - sqrt(2bs - s^2)
    integrated over the concave band (area element (rho + s) ds dbeta), minus the part of each
    band beyond the corner mitre (straight-edge approximation, s cot(alpha) of edge per depth).
    """
    s_ = spec.side_mm
    h = spec.sagitta_mm
    c = 0.5 * s_
    rho = (c * c + h * h) / (2.0 * h)
    phi = 2.0 * math.asin(c / rho)
    square = s_ * s_
    segment = rho * rho * (phi - math.sin(phi)) / 2.0
    hole_sharp = spec.hole_side_mm ** 2
    r_f = spec.hole_fillet_mm
    fillet_gain = (4.0 - math.pi) * r_f * r_f
    hole = hole_sharp - fillet_gain
    exact = square - 4.0 * segment - hole
    centre = c - h + rho
    r_tip = s_ / math.sqrt(2.0)
    cq = centre / math.sqrt(2.0)
    alpha = math.atan2(cq - r_tip, cq)
    b = spec.bevel_offset_mm
    depth = lambda s: b - math.sqrt(max(0.0, 2.0 * b * s - s * s))  # noqa: E731
    band = _simpson(lambda s: depth(s) * (rho + s), 0.0, b) if b > 0 else 0.0
    beyond = _simpson(lambda s: depth(s) * s, 0.0, b) / math.tan(alpha) if b > 0 else 0.0
    facet_per_side_face = phi * band - 2.0 * beyond
    facet = 2.0 * 4.0 * facet_per_side_face
    out = {
        "units": "mm2 (facet: mm3)",
        "square_side2": square,
        "arc_radius_mm": rho,
        "arc_angle_deg": math.degrees(phi),
        "segment_per_side": segment,
        "segments_total": 4.0 * segment,
        "hole_sharp_square": hole_sharp,
        "hole_fillet_material_left": fillet_gain,
        "hole": hole,
        "exact": exact,
        "corner_to_corner_mm": s_ * math.sqrt(2.0),
        "corner_included_deg": 2.0 * math.degrees(alpha),
        "perimeter_mm": 4.0 * rho * phi,
        "facet_quarter_round_section_mm2": b * b * (1.0 - math.pi / 4.0),
        "facet_volume_mm3": facet,
        "facet_mass_g": facet / 1000.0 * spec.density_g_cm3,
    }
    if lod is not None:
        n = lod.edge_intervals
        delta = 0.5 * phi / n
        edge_gain = 8.0 * n * rho * rho * (delta - math.sin(delta)) / 2.0
        if lod.has_fillet and r_f > 0:
            fd = 0.25 * math.pi / lod.fillet_segments
            fillet_gain_poly = 8.0 * lod.fillet_segments * r_f * r_f * (fd - math.sin(fd)) / 2.0
            hole_poly = hole - fillet_gain_poly
        else:
            fillet_gain_poly = 0.0
            hole_poly = hole_sharp
        out.update({
            "polygon_edge_chords": 8 * n,
            "polygon_edge_gain": edge_gain,
            "polygon_edge_chord_sagitta_mm": rho * (1.0 - math.cos(0.5 * delta)),
            "polygon_fillet_chords": 8 * lod.fillet_segments if lod.has_fillet else 0,
            "polygon_hole_area": hole_poly,
            "polygon_hole_shrink": hole - hole_poly,
            "polygonised": square - 4.0 * segment + edge_gain - hole_poly,
        })
    return out


__all__ = ["EDGE_GRINDS", "HOLE_ORIENTATIONS", "PLATE_LOD_CEILING", "PlateLodSpec", "PlateOutline", "SQRT_HALF",
           "SquarePlateSpec", "plate_analytic_area", "plate_triangles", "plate_wedge_triangles"]
